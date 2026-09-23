"""What a failed record looks like when a user inspects it.

Keys are kept so the record can be recognised; values of anything that looks
personal or secret are hidden, long strings are cut, and depth is limited.
The full payload is never stored.
"""

from __future__ import annotations

import re
from typing import Any

SENSITIVE = re.compile(
    r"(pass(word)?|secret|token|api[_-]?key|auth|session|cookie|e?-?mail|phone|mobile|ssn|social|"
    r"card|cvv|iban|account[_-]?(no|number)|dob|birth|address|street|zip|postal)",
    re.IGNORECASE,
)
MAX_STRING = 60
MAX_ITEMS = 5
MAX_DEPTH = 3
HIDDEN = "••• hidden"


def mask(value: Any, key: str = "", depth: int = 0) -> Any:
    if key and SENSITIVE.search(key):
        return HIDDEN if not isinstance(value, dict | list) else HIDDEN
    if depth >= MAX_DEPTH:
        return "…"
    if isinstance(value, dict):
        out = {k: mask(v, str(k), depth + 1) for k, v in list(value.items())[:30]}
        if len(value) > 30:
            out["…"] = f"{len(value) - 30} more fields"
        return out
    if isinstance(value, list):
        items = [mask(v, key, depth + 1) for v in value[:MAX_ITEMS]]
        return items + ([f"… {len(value) - MAX_ITEMS} more"] if len(value) > MAX_ITEMS else [])
    if isinstance(value, str) and len(value) > MAX_STRING:
        return value[:MAX_STRING] + "…"
    return value
