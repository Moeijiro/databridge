"""Stored credentials. Secrets go in, never come out."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Response
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, owned
from app.core.security import encrypt_secret, mask
from app.db.session import get_db
from app.models import Credential, Integration, User
from app.schemas.api import CredentialIn, CredentialOut, CredentialPatch

router = APIRouter(prefix="/api/credentials", tags=["credentials"])


def credential_out(db: Session, credential: Credential) -> CredentialOut:
    out = CredentialOut.model_validate(credential)
    out.used_by = db.scalar(select(func.count()).select_from(Integration).where(
        or_(Integration.source_credential_id == credential.id, Integration.destination_credential_id == credential.id))) or 0
    return out


@router.get("", response_model=list[CredentialOut])
def list_credentials(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> list[CredentialOut]:
    rows = db.execute(select(Credential).where(Credential.owner_id == user.id).order_by(Credential.name)).scalars()
    return [credential_out(db, row) for row in rows]


@router.post("", response_model=CredentialOut, status_code=201)
def create_credential(payload: CredentialIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> CredentialOut:
    credential = Credential(
        owner_id=user.id, name=payload.name, auth_type=payload.auth_type, header_name=payload.header_name,
        username=payload.username, secret_encrypted=encrypt_secret(payload.secret), secret_hint=mask(payload.secret),
    )
    db.add(credential)
    db.commit()
    return credential_out(db, credential)


@router.patch("/{credential_id}", response_model=CredentialOut)
def update_credential(credential_id: int, payload: CredentialPatch, user: User = Depends(get_current_user),
                      db: Session = Depends(get_db)) -> CredentialOut:
    credential = owned(db, Credential, credential_id, user, "Credential")
    changes = payload.model_dump(exclude_unset=True)
    if changes.get("secret"):
        credential.secret_encrypted = encrypt_secret(changes.pop("secret"))
        credential.secret_hint = mask(payload.secret)
    for field, value in changes.items():
        if value is not None:
            setattr(credential, field, value)
    db.commit()
    return credential_out(db, credential)


@router.delete("/{credential_id}", status_code=204)
def delete_credential(credential_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> Response:
    db.delete(owned(db, Credential, credential_id, user, "Credential"))
    db.commit()
    return Response(status_code=204)
