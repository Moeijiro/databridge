"""Request and response models."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, StringConstraints, field_validator, model_validator

from app.transforms import MappingRule

Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=120)]


class Input(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


# --- Auth --------------------------------------------------------------------------------
class RegisterIn(Input):
    email: EmailStr
    password: Annotated[str, StringConstraints(min_length=10, max_length=128)]
    name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=80)]


class LoginIn(Input):
    email: Annotated[str, StringConstraints(max_length=320)]
    password: Annotated[str, StringConstraints(max_length=128)]


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    email: str
    name: str
    is_demo: bool


# --- Credentials ----------------------------------------------------------------------------
class CredentialIn(Input):
    name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=80)]
    auth_type: Literal["bearer", "api_key", "basic"]
    secret: Annotated[str, StringConstraints(min_length=1, max_length=4000)]
    header_name: Annotated[str, StringConstraints(pattern=r"^[A-Za-z0-9-]{1,64}$")] | None = None
    username: Annotated[str, StringConstraints(max_length=120)] | None = None

    @model_validator(mode="after")
    def _shape(self) -> "CredentialIn":
        if self.auth_type == "api_key" and not self.header_name:
            self.header_name = "X-API-Key"
        if self.auth_type == "basic" and not self.username:
            raise ValueError("basic auth needs a username")
        return self


class CredentialPatch(Input):
    name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=80)] | None = None
    secret: Annotated[str, StringConstraints(min_length=1, max_length=4000)] | None = None  # rotate
    header_name: Annotated[str, StringConstraints(pattern=r"^[A-Za-z0-9-]{1,64}$")] | None = None
    username: Annotated[str, StringConstraints(max_length=120)] | None = None


class CredentialOut(BaseModel):
    """Never includes the secret — only a hint like ••••3456."""

    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    auth_type: str
    header_name: str | None
    username: str | None
    secret_hint: str | None
    last_used_at: datetime | None
    created_at: datetime
    used_by: int = 0


# --- Integrations ----------------------------------------------------------------------------
Schedule = Literal["manual", "15m", "hourly", "daily"]


class IntegrationIn(Input):
    name: Name
    description: Annotated[str, StringConstraints(max_length=500)] | None = None
    source_type: Literal["rest", "webhook"]
    source_config: dict[str, Any] = {}
    source_credential_id: int | None = None
    destination_type: Literal["rest", "webhook"]
    destination_config: dict[str, Any]
    destination_credential_id: int | None = None
    mapping: list[MappingRule] = Field(default_factory=list, max_length=100)
    schedule: Schedule = "manual"
    enabled: bool = True

    @field_validator("mapping")
    @classmethod
    def _unique_targets(cls, rules: list[MappingRule]) -> list[MappingRule]:
        targets = [rule.target for rule in rules]
        duplicates = {t for t in targets if targets.count(t) > 1}
        if duplicates:
            raise ValueError(f"target field used twice: {', '.join(sorted(duplicates))}")
        return rules

    @model_validator(mode="after")
    def _webhook_schedule(self) -> "IntegrationIn":
        if self.source_type == "webhook" and self.schedule != "manual":
            raise ValueError("webhook sources run when a webhook arrives, so they can't have a schedule")
        return self


class IntegrationPatch(Input):
    enabled: bool | None = None
    schedule: Schedule | None = None
    name: Name | None = None


class RunSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    integration_id: int
    integration_name: str | None = None
    trigger: str
    status: Literal["running", "success", "partial", "failed"]
    stage: str
    started_at: datetime
    finished_at: datetime | None
    records_read: int
    records_processed: int
    records_successful: int
    records_failed: int
    retries: int
    error_summary: str | None
    duration_ms: int | None = None


class RunDetail(RunSummary):
    log: list[dict[str, Any]]


class FailedRecordOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    record_index: int
    stage: str
    status_code: int | None
    error: str
    attempts: int
    preview: dict[str, Any]


class IntegrationOut(BaseModel):
    id: int
    name: str
    description: str | None
    source_type: str
    source_config: dict[str, Any]
    source_credential: CredentialOut | None
    destination_type: str
    destination_config: dict[str, Any]
    destination_credential: CredentialOut | None
    mapping: list[MappingRule]
    schedule: Schedule
    enabled: bool
    webhook_url: str | None
    last_run_at: datetime | None
    last_run_status: str | None
    next_run_at: datetime | None
    created_at: datetime
    updated_at: datetime
    running: bool = False
    recent_runs: list[RunSummary] = []


class TestOut(BaseModel):
    ok: bool
    message: str
    status: int | None
    elapsed_ms: int | None
    details: dict[str, Any] = {}


class ConnectionTestIn(Input):
    type: Literal["rest", "webhook"]
    config: dict[str, Any]
    credential_id: int | None = None


class MappingPreviewIn(Input):
    sample: dict[str, Any]
    mapping: list[MappingRule] = Field(max_length=100)
