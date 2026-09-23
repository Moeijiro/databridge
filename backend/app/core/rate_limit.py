"""A small fixed-window limiter.

In process, so nothing extra has to be installed. Behind several workers,
point ``_HITS`` at Redis; the call sites do not change.
"""

from __future__ import annotations

import time
from collections import defaultdict

from fastapi import Request

from app.core.errors import APIError

_HITS: dict[str, list[float]] = defaultdict(list)


def client_ip(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def check(key: str, times: int, seconds: int = 60) -> None:
    now = time.monotonic()
    hits = [stamp for stamp in _HITS[key] if stamp > now - seconds]
    if len(hits) >= times:
        retry_after = max(1, int(seconds - (now - hits[0])))
        _HITS[key] = hits
        raise APIError(
            "rate_limit_exceeded",
            f"Too many requests. Try again in {retry_after}s.",
            429,
            {"Retry-After": str(retry_after)},
        )
    hits.append(now)
    _HITS[key] = hits


class RateLimiter:
    """``Depends(RateLimiter(times=10, seconds=60, scope="login"))`` — per IP."""

    def __init__(self, times: int, seconds: int = 60, scope: str = "default") -> None:
        self.times = times
        self.seconds = seconds
        self.scope = scope

    async def __call__(self, request: Request) -> None:
        check(f"{self.scope}:{client_ip(request)}", self.times, self.seconds)


def reset_rate_limits() -> None:
    """Used by the test suite; never called at runtime."""
    _HITS.clear()
