"""Sign-up, sign-in, sign-out."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import settings
from app.core.errors import APIError
from app.core.rate_limit import RateLimiter
from app.core.security import DUMMY_PASSWORD_HASH, SESSION_COOKIE_NAME, create_access_token, hash_password, verify_password
from app.db.session import get_db
from app.models import User
from app.schemas.api import LoginIn, RegisterIn, UserOut

router = APIRouter(prefix="/api", tags=["auth"])
limit = RateLimiter(times=10, seconds=60, scope="auth")


def _session(response: Response, user: User) -> None:
    response.set_cookie(SESSION_COOKIE_NAME, create_access_token(user.id), max_age=settings.access_token_ttl_minutes * 60,
                        httponly=True, secure=settings.cookie_secure, samesite=settings.cookie_samesite, path="/")


@router.post("/auth/register", response_model=UserOut, status_code=201)
def register(payload: RegisterIn, response: Response, db: Session = Depends(get_db), _: None = Depends(limit)) -> User:
    if not settings.allow_registration:
        raise APIError("registration_disabled", "Registration is closed.", 403)
    email = payload.email.lower()
    if db.execute(select(User).where(User.email == email)).scalar_one_or_none():
        raise APIError("email_taken", "That email is already registered.", 409)
    user = User(email=email, name=payload.name, password_hash=hash_password(payload.password))
    db.add(user)
    db.commit()
    _session(response, user)
    return user


@router.post("/auth/login", response_model=UserOut)
def login(payload: LoginIn, response: Response, db: Session = Depends(get_db), _: None = Depends(limit)) -> User:
    user = db.execute(select(User).where(User.email == payload.email.strip().lower())).scalar_one_or_none()
    valid = verify_password(payload.password, user.password_hash if user else DUMMY_PASSWORD_HASH)
    if user is None or not valid:
        raise APIError("invalid_credentials", "Incorrect email or password.", 401)
    _session(response, user)
    return user


@router.post("/auth/logout", status_code=204)
def logout(response: Response) -> Response:
    response.delete_cookie(SESSION_COOKIE_NAME, path="/")
    response.status_code = status.HTTP_204_NO_CONTENT
    return response


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)) -> User:
    return user
