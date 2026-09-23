"""Turn a stored credential into request headers."""

from __future__ import annotations

import base64
from dataclasses import dataclass


@dataclass(slots=True)
class ResolvedAuth:
    """A decrypted credential, alive only for the duration of one run or test."""

    auth_type: str = "none"          # none | bearer | api_key | basic
    secret: str | None = None
    header_name: str | None = None
    username: str | None = None

    def headers(self) -> dict[str, str]:
        if self.auth_type == "bearer" and self.secret:
            return {"Authorization": f"Bearer {self.secret}"}
        if self.auth_type == "api_key" and self.secret:
            return {self.header_name or "X-API-Key": self.secret}
        if self.auth_type == "basic" and self.secret is not None:
            token = base64.b64encode(f"{self.username or ''}:{self.secret}".encode()).decode()
            return {"Authorization": f"Basic {token}"}
        return {}


NO_AUTH = ResolvedAuth()
