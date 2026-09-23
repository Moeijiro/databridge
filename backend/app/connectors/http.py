"""The one way DataBridge makes outbound requests.

* URL validation and SSRF protection: http(s) only, no credentials in the URL,
  and the resolved address must be public — no loopback, private, link-local
  or metadata ranges. The built-in demo APIs (PUBLIC_API_URL/demo/…) are the
  single exception.
* Redirects are not followed (a redirect could point somewhere internal).
* Responses are streamed and capped at MAX_RESPONSE_MB.
* ``send_with_retries`` retries timeouts, network errors, 429 and 5xx with
  exponential back-off. 4xx (other than 429) is a permanent answer and is
  never retried.
"""

from __future__ import annotations

import asyncio
import ipaddress
import json
import socket
import time
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlsplit

import httpx

from app.core.config import settings

_transport: httpx.AsyncBaseTransport | None = None
USER_AGENT = "DataBridge/1.0 (+integration sync)"


def set_transport(transport: httpx.AsyncBaseTransport | None) -> None:
    """Test hook: route outbound requests through a mock or the app itself."""
    global _transport
    _transport = transport


class UnsafeURL(ValueError):
    pass


class RequestFailed(Exception):
    """A request that never produced an HTTP response (timeout, DNS, refused, too large)."""

    def __init__(self, message: str, retryable: bool = True) -> None:
        super().__init__(message)
        self.retryable = retryable


def is_demo_url(url: str) -> bool:
    return url.startswith(f"{settings.public_api_url}/demo/")


def _blocked(ip: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    return (
        ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_multicast
        or ip.is_reserved or ip.is_unspecified or getattr(ip, "is_site_local", False)
    )


async def validate_url(url: str) -> None:
    parts = urlsplit(url)
    if parts.scheme not in ("http", "https"):
        raise UnsafeURL("Only http:// and https:// URLs are allowed.")
    if parts.username or parts.password:
        raise UnsafeURL("Put credentials in a stored credential, not in the URL.")
    if not parts.hostname:
        raise UnsafeURL("The URL has no host.")
    if is_demo_url(url):
        return
    host = parts.hostname
    try:
        ip = ipaddress.ip_address(host)
        addresses = [ip]
    except ValueError:
        if host == "localhost" or host.endswith((".localhost", ".local", ".internal")):
            raise UnsafeURL("Internal hostnames aren't allowed.") from None
        try:
            infos = await asyncio.get_running_loop().getaddrinfo(host, parts.port or 443, type=socket.SOCK_STREAM)
        except socket.gaierror:
            raise UnsafeURL(f"Can't resolve {host}.") from None
        addresses = [ipaddress.ip_address(info[4][0]) for info in infos]
    if any(_blocked(a) for a in addresses):
        raise UnsafeURL("That address is on a private or internal network.")


@dataclass(slots=True)
class HttpResponse:
    status: int
    elapsed_ms: int
    body: bytes
    content_type: str

    def json(self) -> Any:
        return json.loads(self.body or b"null")

    @property
    def ok(self) -> bool:
        return 200 <= self.status < 300

    def error_message(self) -> str:
        """Pull a human message out of an error body: message / error / detail."""
        try:
            data = self.json()
        except ValueError:
            text = self.body.decode(errors="replace").strip()
            return text[:200] or f"HTTP {self.status}"
        if isinstance(data, dict):
            for key in ("message", "error", "detail", "title"):
                value = data.get(key)
                if isinstance(value, str) and value:
                    return value[:200]
                if isinstance(value, dict) and isinstance(value.get("message"), str):
                    return value["message"][:200]
        return f"HTTP {self.status}"


async def request(method: str, url: str, *, headers: dict[str, str] | None = None,
                  params: dict[str, Any] | None = None, json_body: Any = None,
                  content: bytes | None = None) -> HttpResponse:
    await validate_url(url)
    limit = settings.max_response_bytes
    started = time.perf_counter()
    try:
        async with httpx.AsyncClient(timeout=settings.http_timeout_seconds, follow_redirects=False,
                                     transport=_transport) as client:
            async with client.stream(method, url, headers={"User-Agent": USER_AGENT, **(headers or {})},
                                     params=params, json=json_body if content is None else None,
                                     content=content) as response:
                chunks, size = [], 0
                async for chunk in response.aiter_bytes():
                    size += len(chunk)
                    if size > limit:
                        raise RequestFailed(f"Response larger than {settings.max_response_mb} MB", retryable=False)
                    chunks.append(chunk)
    except httpx.TimeoutException:
        raise RequestFailed(f"Timed out after {settings.http_timeout_seconds:g} s") from None
    except httpx.TransportError as exc:
        raise RequestFailed(f"Network error: {type(exc).__name__}") from None
    elapsed = int((time.perf_counter() - started) * 1000)
    if 300 <= response.status_code < 400:
        raise RequestFailed(f"HTTP {response.status_code} redirect — redirects aren't followed", retryable=False)
    return HttpResponse(response.status_code, elapsed, b"".join(chunks), response.headers.get("content-type", ""))


def retryable_status(status: int) -> bool:
    return status == 429 or status >= 500


async def send_with_retries(method: str, url: str, **kwargs: Any) -> tuple[HttpResponse | None, int, str | None]:
    """(response, attempts, error). ``response`` is None when no HTTP answer ever came back."""
    attempts = settings.retry_attempts
    error: str | None = None
    for attempt in range(1, attempts + 1):
        try:
            response = await request(method, url, **kwargs)
        except UnsafeURL:
            raise
        except RequestFailed as exc:
            error = str(exc)
            if not exc.retryable or attempt == attempts:
                return None, attempt, error
        else:
            if not retryable_status(response.status) or attempt == attempts:
                return response, attempt, None
            error = f"HTTP {response.status}"
        await asyncio.sleep(settings.retry_base_delay_seconds * (2 ** (attempt - 1)))
    return None, attempts, error
