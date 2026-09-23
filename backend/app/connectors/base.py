"""The connector contracts and their configs."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator

from app.connectors.auth import ResolvedAuth

# Secrets belong in stored credentials; these header names are refused in plain config.
SECRET_HEADERS = {"authorization", "x-api-key", "api-key", "cookie", "proxy-authorization"}


class _Config(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    @field_validator("headers", check_fields=False)
    @classmethod
    def _no_secret_headers(cls, value: dict[str, str]) -> dict[str, str]:
        if len(value) > 20:
            raise ValueError("at most 20 headers")
        for name in value:
            if name.lower() in SECRET_HEADERS:
                raise ValueError(f"put {name} in a stored credential, not in plain headers")
        return value


class RestSourceConfig(_Config):
    url: HttpUrl
    method: Literal["GET", "POST"] = "GET"
    headers: dict[str, str] = {}
    params: dict[str, str] = {}
    # Where the list of records is in the response: "" for a top-level list, "data", "results.items"…
    records_path: str = Field(default="", max_length=120)
    pagination: Literal["none", "page"] = "none"
    page_param: str = Field(default="page", max_length=40)
    max_pages: int = Field(default=10, ge=1, le=50)


class WebhookSourceConfig(_Config):
    records_path: str = Field(default="", max_length=120)


class RestDestinationConfig(_Config):
    # May contain {field} placeholders filled from the mapped record, e.g. .../customers/{id}
    url: str = Field(min_length=8, max_length=2000)
    method: Literal["POST", "PUT", "PATCH"] = "POST"
    headers: dict[str, str] = {}


class WebhookDestinationConfig(_Config):
    url: HttpUrl
    headers: dict[str, str] = {}


@dataclass(slots=True)
class FetchResult:
    records: list[dict[str, Any]]
    pages: int = 1
    elapsed_ms: int = 0


@dataclass(slots=True)
class SendResult:
    ok: bool
    status: int | None
    attempts: int
    error: str | None = None
    elapsed_ms: int = 0


@dataclass(slots=True)
class TestResult:
    ok: bool
    message: str
    status: int | None = None
    elapsed_ms: int | None = None
    details: dict[str, Any] = field(default_factory=dict)


class SourceConnector(Protocol):
    type: str
    config_model: type[_Config]

    async def fetch(self, config: Any, auth: ResolvedAuth, inbound: Any = None) -> FetchResult: ...
    async def test(self, config: Any, auth: ResolvedAuth) -> TestResult: ...


class DestinationConnector(Protocol):
    type: str
    config_model: type[_Config]

    async def send(self, config: Any, auth: ResolvedAuth, record: dict[str, Any], context: dict[str, Any]) -> SendResult: ...
    async def test(self, config: Any, auth: ResolvedAuth) -> TestResult: ...


class ConnectorError(Exception):
    """The whole fetch failed (as opposed to one record)."""
