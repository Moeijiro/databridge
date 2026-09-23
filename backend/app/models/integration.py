"""An integration: one source, one destination, a field mapping and a schedule."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, Boolean, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UpdatedMixin, UTCDateTime


class Integration(Base, UpdatedMixin):
    __tablename__ = "integrations"

    id: Mapped[int] = mapped_column(primary_key=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(120))
    description: Mapped[str | None] = mapped_column(String(500), default=None)

    source_type: Mapped[str] = mapped_column(String(16))        # rest | webhook
    source_config: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    source_credential_id: Mapped[int | None] = mapped_column(ForeignKey("credentials.id", ondelete="SET NULL"), default=None)

    destination_type: Mapped[str] = mapped_column(String(16))   # rest | webhook
    destination_config: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    destination_credential_id: Mapped[int | None] = mapped_column(ForeignKey("credentials.id", ondelete="SET NULL"), default=None)

    mapping: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    schedule: Mapped[str] = mapped_column(String(16), default="manual")  # manual | 15m | hourly | daily
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)

    # Webhook sources: POST /hooks/{token}. Stored encrypted; shown to the owner only.
    webhook_token_encrypted: Mapped[str | None] = mapped_column(String(255), default=None)
    webhook_token_hash: Mapped[str | None] = mapped_column(String(64), unique=True, index=True, default=None)

    last_run_at: Mapped[datetime | None] = mapped_column(UTCDateTime(), default=None)
    last_run_status: Mapped[str | None] = mapped_column(String(16), default=None)
    next_run_at: Mapped[datetime | None] = mapped_column(UTCDateTime(), default=None, index=True)
