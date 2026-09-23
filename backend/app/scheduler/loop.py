"""A single in-process scheduler.

Every tick it finds enabled, scheduled integrations whose ``next_run_at`` has
passed and starts them, a few at a time. ``next_run_at`` is pushed forward
*before* the run starts, so a slow run can't be picked up twice. Run exactly
one API process with the scheduler enabled (or move this to a worker).
"""

from __future__ import annotations

import asyncio
import logging

from sqlalchemy import select

from app.db.base import utcnow
from app.db.session import SessionLocal
from app.models import Integration
from app.scheduler.schedule import next_run_after
from app.services import runner

logger = logging.getLogger("databridge.scheduler")
MAX_PER_TICK = 5
_tasks: set[asyncio.Task] = set()


async def tick(wait: bool = False) -> list[int]:
    now = utcnow()
    started: list[tuple[int, int]] = []
    with SessionLocal() as db:
        due = db.execute(
            select(Integration).where(
                Integration.enabled.is_(True),
                Integration.schedule != "manual",
                Integration.source_type == "rest",
                Integration.next_run_at.is_not(None),
                Integration.next_run_at <= now,
            ).order_by(Integration.next_run_at).limit(MAX_PER_TICK)
        ).scalars().all()
        for integration in due:
            integration.next_run_at = next_run_after(integration.schedule, now)
            if runner.is_running(integration.id):
                continue
            run = runner.start_run(db, integration, "schedule")
            started.append((integration.id, run.id))
        db.commit()
    coroutines = [runner.execute(run_id) for _, run_id in started]
    if wait:
        await asyncio.gather(*coroutines)
    else:
        # Don't hold up the next tick behind a slow run.
        for coroutine in coroutines:
            task = asyncio.create_task(coroutine)
            _tasks.add(task)
            task.add_done_callback(_tasks.discard)
    return [run_id for _, run_id in started]


async def run_forever(every_seconds: int) -> None:
    logger.info("Scheduler running every %ss", every_seconds)
    while True:
        try:
            await tick()
        except Exception:  # noqa: BLE001
            logger.exception("Scheduler tick failed")
        await asyncio.sleep(every_seconds)
