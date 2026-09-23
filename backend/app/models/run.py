"""Sync runs and the records that failed in them."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, UTCDateTime, utcnow


class SyncRun(Base):
    __tablename__ = "sync_runs"
    __table_args__ = (Index("ix_runs_integration_started", "integration_id", "started_at"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    integration_id: Mapped[int] = mapped_column(ForeignKey("integrations.id", ondelete="CASCADE"))
    trigger: Mapped[str] = mapped_column(String(16))  # manual | schedule | webhook
    # running -> success | partial (some records failed) | failed (the run itself failed)
    status: Mapped[str] = mapped_column(String(16), default="running", index=True)
    # Where the run is right now, for the live flow view: fetch | map | send | done
    stage: Mapped[str] = mapped_column(String(16), default="fetch")
    started_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utcnow)
    finished_at: Mapped[datetime | None] = mapped_column(UTCDateTime(), default=None)
    records_read: Mapped[int] = mapped_column(default=0)
    records_processed: Mapped[int] = mapped_column(default=0)
    records_successful: Mapped[int] = mapped_column(default=0)
    records_failed: Mapped[int] = mapped_column(default=0)
    retries: Mapped[int] = mapped_column(default=0)
    error_summary: Mapped[str | None] = mapped_column(Text, default=None)
    log: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)  # [{at, level, message}]

    failures: Mapped[list["FailedRecord"]] = relationship(back_populates="run", cascade="all, delete-orphan")


class FailedRecord(Base):
    __tablename__ = "failed_records"

    id: Mapped[int] = mapped_column(primary_key=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("sync_runs.id", ondelete="CASCADE"), index=True)
    record_index: Mapped[int] = mapped_column()          # 1-based position in the batch
    stage: Mapped[str] = mapped_column(String(16))        # transform | send
    status_code: Mapped[int | None] = mapped_column(default=None)
    error: Mapped[str] = mapped_column(String(500))
    attempts: Mapped[int] = mapped_column(default=1)
    # Masked, truncated view of the record: keys kept, sensitive values hidden.
    preview: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utcnow)

    run: Mapped[SyncRun] = relationship(back_populates="failures")
