"""Integrations: CRUD, Run now, connection tests and mapping preview."""

from __future__ import annotations

import asyncio

from fastapi import APIRouter, Depends, Response
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, owned
from app.api.routes.credentials import credential_out
from app.connectors import DESTINATIONS, SOURCES
from app.connectors.http import UnsafeURL, validate_url
from app.core import rate_limit
from app.core.config import settings
from app.core.errors import APIError
from app.core.security import decrypt_secret, encrypt_secret, generate_webhook_token, hash_token
from app.db.base import utcnow
from app.db.session import get_db
from app.models import Credential, Integration, SyncRun, User
from app.scheduler.schedule import next_run_after
from app.schemas.api import (
    ConnectionTestIn,
    IntegrationIn,
    IntegrationOut,
    IntegrationPatch,
    MappingPreviewIn,
    RunSummary,
    TestOut,
)
from app.services import credentials, runner
from app.services.present import run_summary
from app.transforms import TRANSFORMS, preview_mapping

router = APIRouter(prefix="/api", tags=["integrations"])
_background: set[asyncio.Task] = set()


def _config_error(exc: ValidationError, where: str) -> APIError:
    first = exc.errors()[0]
    field = ".".join(str(p) for p in first["loc"])
    return APIError("validation_error", f"{where}.{field}: {first['msg'].removeprefix('Value error, ')}", 422)


async def _validated(db: Session, user: User, payload: IntegrationIn) -> tuple[dict, dict]:
    try:
        source = SOURCES[payload.source_type].config_model.model_validate(payload.source_config)
    except ValidationError as exc:
        raise _config_error(exc, "source") from None
    try:
        destination = DESTINATIONS[payload.destination_type].config_model.model_validate(payload.destination_config)
    except ValidationError as exc:
        raise _config_error(exc, "destination") from None
    for label, url in (("source", getattr(source, "url", None)), ("destination", getattr(destination, "url", None))):
        if url is None:
            continue
        try:
            await validate_url(str(url).replace("{", "").replace("}", ""))
        except UnsafeURL as exc:
            raise APIError("unsafe_url", f"{label} URL: {exc}", 422) from None
    for credential_id in (payload.source_credential_id, payload.destination_credential_id):
        if credential_id is not None:
            owned(db, Credential, credential_id, user, "Credential")
    return source.model_dump(mode="json"), destination.model_dump(mode="json")


def integration_out(db: Session, integration: Integration, with_runs: bool = True) -> IntegrationOut:
    def cred(credential_id: int | None):  # noqa: ANN202
        row = db.get(Credential, credential_id) if credential_id else None
        return credential_out(db, row) if row else None

    webhook_url = None
    if integration.source_type == "webhook" and integration.webhook_token_encrypted:
        webhook_url = f"{settings.public_api_url}/hooks/{decrypt_secret(integration.webhook_token_encrypted)}"
    runs = []
    if with_runs:
        runs = [run_summary(r) for r in db.execute(select(SyncRun).where(SyncRun.integration_id == integration.id)
                                                   .order_by(SyncRun.started_at.desc(), SyncRun.id.desc()).limit(10)).scalars()]
    return IntegrationOut(
        id=integration.id, name=integration.name, description=integration.description,
        source_type=integration.source_type, source_config=integration.source_config,
        source_credential=cred(integration.source_credential_id),
        destination_type=integration.destination_type, destination_config=integration.destination_config,
        destination_credential=cred(integration.destination_credential_id),
        mapping=integration.mapping, schedule=integration.schedule, enabled=integration.enabled,  # type: ignore[arg-type]
        webhook_url=webhook_url, last_run_at=integration.last_run_at, last_run_status=integration.last_run_status,
        next_run_at=integration.next_run_at, created_at=integration.created_at, updated_at=integration.updated_at,
        running=runner.is_running(integration.id), recent_runs=runs,
    )


def _ensure_webhook_token(integration: Integration) -> None:
    if integration.source_type == "webhook" and not integration.webhook_token_hash:
        token = generate_webhook_token()
        integration.webhook_token_encrypted = encrypt_secret(token)
        integration.webhook_token_hash = hash_token(token)


@router.get("/integrations", response_model=list[IntegrationOut])
def list_integrations(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> list[IntegrationOut]:
    rows = db.execute(select(Integration).where(Integration.owner_id == user.id).order_by(Integration.created_at.desc())).scalars()
    return [integration_out(db, row, with_runs=False) for row in rows]


@router.post("/integrations", response_model=IntegrationOut, status_code=201)
async def create_integration(payload: IntegrationIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> IntegrationOut:
    source, destination = await _validated(db, user, payload)
    integration = Integration(
        owner_id=user.id, name=payload.name, description=payload.description,
        source_type=payload.source_type, source_config=source, source_credential_id=payload.source_credential_id,
        destination_type=payload.destination_type, destination_config=destination,
        destination_credential_id=payload.destination_credential_id,
        mapping=[rule.model_dump() for rule in payload.mapping], schedule=payload.schedule, enabled=payload.enabled,
    )
    integration.next_run_at = next_run_after(payload.schedule, utcnow()) if payload.enabled else None
    _ensure_webhook_token(integration)
    db.add(integration)
    db.commit()
    return integration_out(db, integration)


@router.get("/integrations/{integration_id}", response_model=IntegrationOut)
def get_integration(integration_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> IntegrationOut:
    return integration_out(db, owned(db, Integration, integration_id, user, "Integration"))


@router.put("/integrations/{integration_id}", response_model=IntegrationOut)
async def replace_integration(integration_id: int, payload: IntegrationIn, user: User = Depends(get_current_user),
                              db: Session = Depends(get_db)) -> IntegrationOut:
    integration = owned(db, Integration, integration_id, user, "Integration")
    source, destination = await _validated(db, user, payload)
    for field, value in {
        "name": payload.name, "description": payload.description, "source_type": payload.source_type,
        "source_config": source, "source_credential_id": payload.source_credential_id,
        "destination_type": payload.destination_type, "destination_config": destination,
        "destination_credential_id": payload.destination_credential_id,
        "mapping": [rule.model_dump() for rule in payload.mapping], "schedule": payload.schedule, "enabled": payload.enabled,
    }.items():
        setattr(integration, field, value)
    integration.next_run_at = next_run_after(payload.schedule, utcnow()) if payload.enabled else None
    _ensure_webhook_token(integration)
    db.commit()
    return integration_out(db, integration)


@router.patch("/integrations/{integration_id}", response_model=IntegrationOut)
def patch_integration(integration_id: int, payload: IntegrationPatch, user: User = Depends(get_current_user),
                      db: Session = Depends(get_db)) -> IntegrationOut:
    integration = owned(db, Integration, integration_id, user, "Integration")
    changes = payload.model_dump(exclude_unset=True)
    if changes.get("schedule") and changes["schedule"] != "manual" and integration.source_type == "webhook":
        raise APIError("validation_error", "Webhook sources can't have a schedule.", 422)
    for field, value in changes.items():
        if value is not None:
            setattr(integration, field, value)
    integration.next_run_at = next_run_after(integration.schedule, utcnow()) if integration.enabled else None
    db.commit()
    return integration_out(db, integration)


@router.delete("/integrations/{integration_id}", status_code=204)
def delete_integration(integration_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> Response:
    db.delete(owned(db, Integration, integration_id, user, "Integration"))
    db.commit()
    return Response(status_code=204)


@router.post("/integrations/{integration_id}/rotate-webhook", response_model=IntegrationOut)
def rotate_webhook(integration_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> IntegrationOut:
    integration = owned(db, Integration, integration_id, user, "Integration")
    if integration.source_type != "webhook":
        raise APIError("not_webhook", "Only webhook sources have a webhook URL.", 409)
    integration.webhook_token_hash = None
    _ensure_webhook_token(integration)
    db.commit()
    return integration_out(db, integration)


@router.post("/integrations/{integration_id}/run", response_model=RunSummary, status_code=202, summary="Run now")
async def run_now(integration_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> RunSummary:
    integration = owned(db, Integration, integration_id, user, "Integration")
    if integration.source_type != "rest":
        raise APIError("webhook_source", "Webhook integrations run when a webhook arrives. Send one to the webhook URL.", 409)
    if runner.is_running(integration.id):
        raise APIError("already_running", "This integration is already running.", 409)
    rate_limit.check(f"run:{user.id}", times=20, seconds=60)
    run = runner.start_run(db, integration, "manual")
    task = asyncio.create_task(runner.execute(run.id))
    _background.add(task)
    task.add_done_callback(_background.discard)
    return run_summary(run)


async def _test(db: Session, user: User, kind: str, payload: ConnectionTestIn) -> TestOut:
    rate_limit.check(f"test:{user.id}", times=30, seconds=60)
    registry = SOURCES if kind == "source" else DESTINATIONS
    try:
        config = registry[payload.type].config_model.model_validate(payload.config)
    except ValidationError as exc:
        raise _config_error(exc, kind) from None
    if payload.credential_id is not None:
        owned(db, Credential, payload.credential_id, user, "Credential")
    auth = credentials.resolve(db, payload.credential_id, user.id)
    result = await registry[payload.type].test(config, auth)
    db.commit()  # last_used_at
    return TestOut(ok=result.ok, message=result.message, status=result.status, elapsed_ms=result.elapsed_ms, details=result.details)


@router.post("/connections/test-source", response_model=TestOut, summary="Test a source without saving")
async def test_source(payload: ConnectionTestIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> TestOut:
    return await _test(db, user, "source", payload)


@router.post("/connections/test-destination", response_model=TestOut, summary="Test a destination without writing")
async def test_destination(payload: ConnectionTestIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> TestOut:
    return await _test(db, user, "destination", payload)


@router.post("/mapping/preview", summary="Apply a mapping to a sample record")
def mapping_preview(payload: MappingPreviewIn, user: User = Depends(get_current_user)) -> dict:
    return preview_mapping(payload.sample, payload.mapping)


@router.get("/meta", summary="Transforms, schedules and demo endpoints for the editor")
def meta(user: User = Depends(get_current_user)) -> dict:
    base = settings.public_api_url
    return {
        "transforms": [{"name": n, "label": t.label, "needs_argument": t.needs_argument, "argument_label": t.argument_label}
                       for n, t in TRANSFORMS.items()],
        "schedules": [{"value": "manual", "label": "Manual"}, {"value": "15m", "label": "Every 15 minutes"},
                      {"value": "hourly", "label": "Hourly"}, {"value": "daily", "label": "Daily"}],
        "demo": {
            "source_customers": f"{base}/demo/source/customers",
            "source_orders": f"{base}/demo/source/orders",
            "destination_customers": f"{base}/demo/destination/customers",
            "destination_orders": f"{base}/demo/destination/orders",
            "destination_webhook": f"{base}/demo/destination/webhook",
        },
    }
