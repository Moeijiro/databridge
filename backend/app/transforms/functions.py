"""The transforms. Each takes the value (and an optional argument) and returns
the new value, or raises ValueError with a message a user can act on."""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

_NUMBER = re.compile(r"^[+-]?(\d{1,3}(,\d{3})+|\d+)?(\.\d+)?$")
TRUE = {"true", "yes", "y", "1", "on"}
FALSE = {"false", "no", "n", "0", "off", ""}


def _as_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def to_number(value: Any, _: str | None = None) -> int | float:
    if isinstance(value, bool):
        raise ValueError(f"can't convert {value!r} to a number")
    if isinstance(value, int | float):
        return value
    text = _as_text(value).strip().replace(" ", "")
    for symbol in "$€£":
        text = text.replace(symbol, "")
    if not text or not _NUMBER.match(text):
        raise ValueError(f"can't convert {_as_text(value)[:40]!r} to a number")
    number = float(text.replace(",", ""))
    return int(number) if number.is_integer() and "." not in text else number


def to_boolean(value: Any, _: str | None = None) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, int | float):
        return value != 0
    text = _as_text(value).strip().lower()
    if text in TRUE:
        return True
    if text in FALSE:
        return False
    raise ValueError(f"can't convert {text[:40]!r} to true/false")


@dataclass(frozen=True, slots=True)
class Transform:
    label: str
    fn: Callable[[Any, str | None], Any]
    needs_argument: bool = False
    argument_label: str | None = None


TRANSFORMS: dict[str, Transform] = {
    "none": Transform("No change", lambda v, _: v),
    "prefix": Transform("Add prefix", lambda v, a: f"{a or ''}{_as_text(v)}", True, "Prefix"),
    "suffix": Transform("Add suffix", lambda v, a: f"{_as_text(v)}{a or ''}", True, "Suffix"),
    "to_number": Transform("To number", to_number),
    "to_boolean": Transform("To true/false", to_boolean),
    "to_string": Transform("To text", lambda v, _: _as_text(v)),
    "lowercase": Transform("Lowercase", lambda v, _: _as_text(v).lower()),
    "uppercase": Transform("Uppercase", lambda v, _: _as_text(v).upper()),
    "trim": Transform("Trim spaces", lambda v, _: _as_text(v).strip()),
}
