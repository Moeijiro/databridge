"""One sync run, end to end.

    fetch ──► map + transform ──► send (with retries) ──► done

The run row is updated as it goes (stage, counters, log lines), so the UI can
poll it and animate the flow while it's happening. A failure of the whole run
(source unreachable, bad JSON) marks it ``failed``; a failure of individual
records is stored per record and the run ends ``partial``.
"""

from __future__ import annotations

import asyncio
import logging
import time
from collections import Counter
from typing import Any

from sqlalchemy.orm import Session

from app.connectors import DESTINATIONS, SOURCES
from app.connectors.base import ConnectorError
from app.connectors.http import UnsafeURL
from app.db.base import utcnow
from app.db.session import SessionLocal
from app.models import FailedRecord, Integration, SyncRun
from app.scheduler.schedule import next_run_after
from app.services import credentials
from app.services.masking import mask
from app.transforms import MappingRule, TransformError, apply_mapping

logger = logging.getLogger("databridge.runner")
SEND_CONCURRENCY = 5
FLUSH_EVERY_SECONDS = 0.4
_running: set[int] = set()  # integration ids with a run in progress in this process


def is_running(integration_id: int) -> bool:
    return integration_id in _running


def _log(run: SyncRun, message: str, level: str = "info") -> None:
    run.log = [*run.log, {"at": utcnow().isoformat(), "level": level, "message": message}][-200:]


def start_run(db: Session, integration: Integration, trigger: str) -> SyncRun:
    run = SyncRun(integration_id=integration.id, trigger=trigger, status="running", stage="fetch", log=[])
    _log(run, "Fetching…" if integration.source_type == "rest" else "Webhook received")
    db.add(run)
    db.commit()
    return run


async def execute(run_id: int, inbound: Any = None) -> None:
    """Run a started SyncRun to completion. Never raises."""
    with SessionLocal() as db:
        run = db.get(SyncRun, run_id)
        integration = db.get(Integration, run.integration_id)
        _running.add(integration.id)
        try:
            await _execute(db, run, integration, inbound)
        except Exception as exc:  # noqa: BLE001 — a bug must still end the run cleanly
            logger.exception("Run %s crashed", run_id)
            run.status, run.error_summary = "failed", f"Internal error: {type(exc).__name__}"
            _log(run, run.error_summary, "error")
        finally:
            _running.discard(integration.id)
            run.stage, run.finished_at = "done", utcnow()
            integration.last_run_at, integration.last_run_status = run.finished_at, run.status
            integration.next_run_at = next_run_after(integration.schedule, run.finished_at) if integration.enabled else None
            db.commit()


async def _execute(db: Session, run: SyncRun, integration: Integration, inbound: Any) -> None:
    source = SOURCES[integration.source_type]
    destination = DESTINATIONS[integration.destination_type]
    source_config = source.config_model.model_validate(integration.source_config)
    destination_config = destination.config_model.model_validate(integration.destination_config)
    rules = [MappingRule.model_validate(rule) for rule in integration.mapping]
    source_auth = credentials.resolve(db, integration.source_credential_id, integration.owner_id)
    destination_auth = credentials.resolve(db, integration.destination_credential_id, integration.owner_id)

    # 1. Fetch
    try:
        fetched = await source.fetch(source_config, source_auth, inbound)
    except (ConnectorError, UnsafeURL) as exc:
        run.status, run.error_summary = "failed", f"Fetch failed: {exc}"
        _log(run, run.error_summary, "error")
        return
    records = fetched.records
    run.records_read = len(records)
    _log(run, f"{len(records)} records received" + (f" from {fetched.pages} pages" if fetched.pages > 1 else ""))
    run.stage = "map"
    db.commit()

    # 2. Map and transform
    _log(run, "Transforming…")
    ready: list[tuple[int, dict[str, Any], dict[str, Any]]] = []
    for index, record in enumerate(records, start=1):
        try:
            ready.append((index, record, apply_mapping(record, rules)))
        except TransformError as exc:
            run.records_failed += 1
            run.records_processed += 1
            db.add(FailedRecord(run_id=run.id, record_index=index, stage="transform", error=str(exc)[:500],
                                attempts=0, preview=mask(record)))
    if run.records_failed:
        _log(run, f"{run.records_failed} records couldn't be transformed", "warning")
    run.stage = "send"
    _log(run, f"Sending {len(ready)} records…")
    db.commit()

    # 3. Send, a few at a time, flushing progress to the database as we go
    semaphore = asyncio.Semaphore(SEND_CONCURRENCY)
    context = {"integration": integration.name, "run_id": run.id}
    last_flush = time.monotonic()
    errors: Counter[str] = Counter()

    async def send_one(index: int, original: dict, mapped: dict) -> None:
        nonlocal last_flush
        async with semaphore:
            result = await destination.send(destination_config, destination_auth, mapped, context)
        run.records_processed += 1
        run.retries += max(result.attempts - 1, 0)
        if result.ok:
            run.records_successful += 1
        else:
            run.records_failed += 1
            errors[result.error or "Unknown error"] += 1
            db.add(FailedRecord(run_id=run.id, record_index=index, stage="send", status_code=result.status,
                                error=(result.error or "Unknown error")[:500], attempts=result.attempts, preview=mask(original)))
        if time.monotonic() - last_flush > FLUSH_EVERY_SECONDS:
            last_flush = time.monotonic()
            db.commit()

    await asyncio.gather(*(send_one(i, o, m) for i, o, m in ready))

    # 4. Summarise
    run.status = "success" if run.records_failed == 0 else ("failed" if run.records_successful == 0 else "partial")
    _log(run, f"{run.records_successful} successful · {run.records_failed} failed"
         + (f" · {run.retries} retries" if run.retries else ""),
         "info" if run.status == "success" else "warning")
    if run.records_failed:
        summary = [f"{count}× {message}" for message, count in errors.most_common(3)]
        transform_failures = run.records_failed - sum(errors.values())
        if transform_failures:
            summary.insert(0, f"{transform_failures}× failed to transform")
        run.error_summary = "; ".join(summary)[:1000]
