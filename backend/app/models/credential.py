"""Stored API credentials, encrypted at rest.

Integrations reference a credential by id instead of embedding secrets, so a
key can be rotated in one place and never appears in integration JSON.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UTCDateTime


class Credential(Base, TimestampMixin):
    __tablename__ = "credentials"

    id: Mapped[int] = mapped_column(primary_key=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(80))
    auth_type: Mapped[str] = mapped_column(String(16))  # bearer | api_key | basic
    # Non-secret settings: header name for api_key, username for basic.
    header_name: Mapped[str | None] = mapped_column(String(64), default=None)
    username: Mapped[str | None] = mapped_column(String(120), default=None)
    # The secret (token, key or password), Fernet-encrypted. Never returned by the API.
    secret_encrypted: Mapped[str] = mapped_column(Text)
    secret_hint: Mapped[str | None] = mapped_column(String(16), default=None)  # "••••3456"
    last_used_at: Mapped[datetime | None] = mapped_column(UTCDateTime(), default=None)
