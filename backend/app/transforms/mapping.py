"""Applying a mapping to one record."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.transforms.functions import TRANSFORMS
from app.transforms.paths import MISSING, get_path, set_path

PATH = r"^[A-Za-z0-9_\-$]+(\.[A-Za-z0-9_\-$]+){0,7}$"


class TransformError(Exception):
    def __init__(self, field: str, message: str) -> None:
        super().__init__(f"{field}: {message}")
        self.field = field
        self.message = message


class MappingRule(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    source: str = Field(pattern=PATH, max_length=200)
    target: str = Field(pattern=PATH, max_length=200)
    transform: str = "none"
    argument: str | None = Field(default=None, max_length=200)
    required: bool = False
    default: str | None = Field(default=None, max_length=200)

    @field_validator("transform")
    @classmethod
    def _known(cls, value: str) -> str:
        if value not in TRANSFORMS:
            raise ValueError(f"unknown transform {value!r}")
        return value

    @model_validator(mode="after")
    def _argument(self) -> "MappingRule":
        if TRANSFORMS[self.transform].needs_argument and not self.argument:
            raise ValueError(f"the {self.transform} transform needs a value")
        return self


def apply_mapping(record: dict[str, Any], rules: list[MappingRule]) -> dict[str, Any]:
    """Build the destination record. Raises TransformError on the first bad field."""
    out: dict[str, Any] = {}
    for rule in rules:
        value = get_path(record, rule.source)
        if value is MISSING or value is None or value == "":
            if rule.required:
                raise TransformError(rule.target, f"Missing required field: {rule.source}")
            if rule.default is None:
                continue
            value = rule.default
        try:
            value = TRANSFORMS[rule.transform].fn(value, rule.argument)
        except ValueError as exc:
            raise TransformError(rule.target, f"{rule.source} — {exc}") from None
        set_path(out, rule.target, value)
    return out


def preview_mapping(record: dict[str, Any], rules: list[MappingRule]) -> dict[str, Any]:
    """For the mapping editor: the output, or where it breaks."""
    try:
        return {"ok": True, "output": apply_mapping(record, rules), "error": None}
    except TransformError as exc:
        return {"ok": False, "output": None, "error": str(exc)}
