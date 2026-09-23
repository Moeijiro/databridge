"""Authentication and ownership. Anything you don't own is a 404."""

from __future__ import annotations

from typing import TypeVar

from fastapi import Depends, Request, status
from sqlalchemy.orm import Session

from app.core.errors import APIError
from app.core.security import SESSION_COOKIE_NAME, read_access_token
from app.db.session import get_db
from app.models import Credential, Integration, SyncRun, User

T = TypeVar("T", Credential, Integration)


def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    token = request.cookies.get(SESSION_COOKIE_NAME)
    payload = read_access_token(token) if token else None
    user = db.get(User, int(payload["sub"])) if payload else None
    if user is None:
        raise APIError("unauthenticated", "Sign in to continue.", status.HTTP_401_UNAUTHORIZED)
    return user


def owned(db: Session, model: type[T], object_id: int, user: User, label: str) -> T:
    obj = db.get(model, object_id)
    if obj is None or obj.owner_id != user.id:
        raise APIError("not_found", f"{label} not found.", status.HTTP_404_NOT_FOUND)
    return obj


def owned_run(db: Session, run_id: int, user: User) -> SyncRun:
    run = db.get(SyncRun, run_id)
    if run is None or db.get(Integration, run.integration_id).owner_id != user.id:
        raise APIError("not_found", "Run not found.", status.HTTP_404_NOT_FOUND)
    return run
