"""Sync runs, failed records, the dashboard and inbound webhooks."""

from __future__ import annotations

import asyncio
import json
from datetime import timedelta

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import JSONResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, owned_run
from app.core import rate_limit
from app.core.errors import APIError
from app.core.security import hash_token
from app.db.base import utcnow
from app.db.session import get_db
from app.models import FailedRecord, Integration, SyncRun, User
from app.schemas.api import FailedRecordOut, RunDetail, RunSummary
from app.services import runner
from app.services.present import run_summary

router = APIRouter(tags=["runs"])
MAX_WEBHOOK_BYTES = 1024 * 1024
_background: set[asyncio.Task] = set()


@router.get("/api/runs", response_model=list[RunSummary], summary="Recent runs across your integrations")
def list_runs(
    integration_id: int | None = None,
    status: str | None = Query(default=None, pattern="^(running|success|partial|failed)$"),
    limit: int = Query(default=50, ge=1, le=200),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[RunSummary]:
    query = (select(SyncRun, Integration.name).join(Integration, Integration.id == SyncRun.integration_id)
             .where(Integration.owner_id == user.id))
    if integration_id:
        query = query.where(SyncRun.integration_id == integration_id)
    if status:
        query = query.where(SyncRun.status == status)
    rows = db.execute(query.order_by(SyncRun.started_at.desc(), SyncRun.id.desc()).limit(limit)).all()
    return [run_summary(run, name) for run, name in rows]


@router.get("/api/runs/{run_id}", response_model=RunDetail, summary="One run, with its live stage and log")
def get_run(run_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> RunDetail:
    run = owned_run(db, run_id, user)
    summary = run_summary(run, db.get(Integration, run.integration_id).name)
    return RunDetail(**summary.model_dump(), log=run.log)


@router.get("/api/runs/{run_id}/failures", response_model=list[FailedRecordOut], summary="Failed records (masked)")
def run_failures(run_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> list[FailedRecord]:
    owned_run(db, run_id, user)
    return list(db.execute(select(FailedRecord).where(FailedRecord.run_id == run_id)
                           .order_by(FailedRecord.record_index).limit(500)).scalars())


@router.get("/api/dashboard", summary="Totals and recent runs")
def dashboard(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    since = utcnow() - timedelta(days=7)
    owned_ids = select(Integration.id).where(Integration.owner_id == user.id)
    integrations = db.execute(select(Integration).where(Integration.owner_id == user.id)).scalars().all()
    by_status = dict(db.execute(select(SyncRun.status, func.count()).where(
        SyncRun.integration_id.in_(owned_ids), SyncRun.started_at >= since).group_by(SyncRun.status)).all())
    totals = db.execute(select(func.coalesce(func.sum(SyncRun.records_read), 0), func.coalesce(func.sum(SyncRun.records_successful), 0),
                               func.coalesce(func.sum(SyncRun.records_failed), 0)).where(
        SyncRun.integration_id.in_(owned_ids), SyncRun.started_at >= since)).one()
    days = []
    for offset in range(6, -1, -1):
        day_start = (utcnow() - timedelta(days=offset)).replace(hour=0, minute=0, second=0, microsecond=0)
        ok, failed = db.execute(select(func.coalesce(func.sum(SyncRun.records_successful), 0),
                                       func.coalesce(func.sum(SyncRun.records_failed), 0)).where(
            SyncRun.integration_id.in_(owned_ids), SyncRun.started_at >= day_start,
            SyncRun.started_at < day_start + timedelta(days=1))).one()
        days.append({"day": day_start.date().isoformat(), "successful": ok, "failed": failed})
    recent = db.execute(select(SyncRun, Integration.name).join(Integration, Integration.id == SyncRun.integration_id)
                        .where(Integration.owner_id == user.id).order_by(SyncRun.started_at.desc(), SyncRun.id.desc()).limit(8)).all()
    return {
        "stats": {
            "active_integrations": sum(1 for i in integrations if i.enabled),
            "total_integrations": len(integrations),
            "successful_syncs": by_status.get("success", 0),
            "partial_syncs": by_status.get("partial", 0),
            "failed_syncs": by_status.get("failed", 0),
            "records_processed": int(totals[0]),
            "records_successful": int(totals[1]),
            "records_failed": int(totals[2]),
        },
        "days": days,
        "recent_runs": [run_summary(run, name).model_dump(mode="json") for run, name in recent],
    }


@router.post("/hooks/{token}", status_code=202, summary="Inbound webhook: starts a sync run")
async def inbound_webhook(token: str, request: Request, db: Session = Depends(get_db)) -> JSONResponse:
    """Public by design — the unguessable token is the credential. Returns 202 with the run id;
    the run continues in the background."""
    rate_limit.check(f"hook:{hash_token(token)[:16]}", times=60, seconds=60)
    integration = db.execute(select(Integration).where(Integration.webhook_token_hash == hash_token(token))).scalar_one_or_none()
    if integration is None or integration.source_type != "webhook":
        raise APIError("not_found", "Unknown webhook.", 404)
    if not integration.enabled:
        raise APIError("disabled", "This integration is disabled.", 409)
    length = int(request.headers.get("content-length") or 0)
    if length > MAX_WEBHOOK_BYTES:
        raise APIError("payload_too_large", "Webhook payloads are limited to 1 MB.", 413)
    raw = await request.body()
    if len(raw) > MAX_WEBHOOK_BYTES:
        raise APIError("payload_too_large", "Webhook payloads are limited to 1 MB.", 413)
    try:
        payload = json.loads(raw or b"null")
    except ValueError:
        raise APIError("invalid_json", "The webhook body must be JSON.", 400) from None
    if not isinstance(payload, dict | list):
        raise APIError("invalid_json", "The webhook body must be a JSON object or array.", 400)
    run = runner.start_run(db, integration, "webhook")
    task = asyncio.create_task(runner.execute(run.id, inbound=payload))
    _background.add(task)
    task.add_done_callback(_background.discard)
    return JSONResponse({"accepted": True, "run_id": run.id}, status_code=202)
