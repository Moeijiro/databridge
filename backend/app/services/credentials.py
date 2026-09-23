"""Resolving a credential for one run or one test — and nothing longer."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.connectors.auth import NO_AUTH, ResolvedAuth
from app.core.security import decrypt_secret
from app.db.base import utcnow
from app.models import Credential


def resolve(db: Session, credential_id: int | None, owner_id: int) -> ResolvedAuth:
    if credential_id is None:
        return NO_AUTH
    credential = db.get(Credential, credential_id)
    if credential is None or credential.owner_id != owner_id:
        return NO_AUTH  # deleted since the integration was saved — the request goes out unauthenticated and fails loudly
    credential.last_used_at = utcnow()
    return ResolvedAuth(credential.auth_type, decrypt_secret(credential.secret_encrypted),
                        credential.header_name, credential.username)
