"""Rows -> API models."""

from __future__ import annotations

from app.models import SyncRun
from app.schemas.api import RunSummary


def run_summary(run: SyncRun, integration_name: str | None = None) -> RunSummary:
    out = RunSummary.model_validate(run)
    out.integration_name = integration_name
    if run.finished_at:
        out.duration_ms = int((run.finished_at - run.started_at).total_seconds() * 1000)
    return out
