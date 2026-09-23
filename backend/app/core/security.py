"""Passwords, sessions, credential encryption and webhook tokens."""

from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
from cryptography.fernet import Fernet, InvalidToken

from app.core.config import settings

SESSION_COOKIE_NAME = "databridge_session"
JWT_ALGORITHM = "HS256"

# 128 * r * N = 16 MiB per hash. maxmem must be passed explicitly: OpenSSL's
# default ceiling is 32 MiB and silently rejects anything above it.
SCRYPT_N = 2**14
SCRYPT_R = 8
SCRYPT_P = 1
SCRYPT_MAXMEM = 256 * 1024 * 1024


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(
        password.encode(), salt=salt, n=SCRYPT_N, r=SCRYPT_R, p=SCRYPT_P,
        dklen=32, maxmem=SCRYPT_MAXMEM,
    )
    return "scrypt${}${}${}${}${}".format(
        SCRYPT_N, SCRYPT_R, SCRYPT_P,
        base64.b64encode(salt).decode(), base64.b64encode(digest).decode(),
    )


def verify_password(password: str, stored: str) -> bool:
    try:
        scheme, n, r, p, salt_b64, digest_b64 = stored.split("$")
        if scheme != "scrypt":
            return False
        expected = base64.b64decode(digest_b64)
        digest = hashlib.scrypt(
            password.encode(), salt=base64.b64decode(salt_b64),
            n=int(n), r=int(r), p=int(p), dklen=len(expected), maxmem=SCRYPT_MAXMEM,
        )
    except (ValueError, TypeError):
        return False
    return hmac.compare_digest(digest, expected)


# Verifying against this when the email is unknown keeps "no such user" and
# "wrong password" equally slow, so response time does not reveal accounts.
DUMMY_PASSWORD_HASH = hash_password(secrets.token_urlsafe(16))


def create_access_token(user_id: int) -> str:
    now = datetime.now(timezone.utc)
    return jwt.encode(
        {
            "sub": str(user_id),
            "iat": int(now.timestamp()),
            "exp": int((now + timedelta(minutes=settings.access_token_ttl_minutes)).timestamp()),
            "jti": secrets.token_urlsafe(8),
        },
        settings.secret_key,
        algorithm=JWT_ALGORITHM,
    )


def read_access_token(token: str) -> dict[str, Any] | None:
    try:
        return jwt.decode(token, settings.secret_key, algorithms=[JWT_ALGORITHM])
    except jwt.PyJWTError:
        return None


# --- Credential encryption -----------------------------------------------------------------
def _fernet() -> Fernet:
    key = settings.credentials_key
    if not key:
        # Development fallback: a stable key derived from SECRET_KEY. Production requires
        # CREDENTIALS_KEY (enforced in config) so rotating one doesn't silently rotate the other.
        key = base64.urlsafe_b64encode(hashlib.sha256(("credentials:" + settings.secret_key).encode()).digest()).decode()
    return Fernet(key.encode())


def encrypt_secret(plaintext: str) -> str:
    return _fernet().encrypt(plaintext.encode()).decode()


def decrypt_secret(ciphertext: str) -> str:
    try:
        return _fernet().decrypt(ciphertext.encode()).decode()
    except InvalidToken as exc:
        raise ValueError("Stored credential can't be decrypted — was CREDENTIALS_KEY changed?") from exc


def mask(secret: str | None) -> str | None:
    """"••••1a2b" — enough to recognise a key, never enough to use it."""
    if not secret:
        return None
    return "••••" + secret[-4:] if len(secret) > 8 else "••••"


def generate_webhook_token() -> str:
    return secrets.token_urlsafe(24)


def hash_token(raw: str) -> str:
    """Webhook tokens are looked up by digest, so the index never holds the token itself."""
    return hashlib.sha256(raw.encode()).hexdigest()
