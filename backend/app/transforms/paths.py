"""Dotted paths: ``customer.address.city``, ``items.0.sku``."""

from __future__ import annotations

from typing import Any

MISSING = object()
MAX_DEPTH = 8


def get_path(obj: Any, path: str) -> Any:
    """The value at ``path``, or ``MISSING``. List indexes are plain numbers."""
    current = obj
    for part in path.split(".")[:MAX_DEPTH]:
        if isinstance(current, dict):
            if part not in current:
                return MISSING
            current = current[part]
        elif isinstance(current, list) and part.isdigit():
            index = int(part)
            if index >= len(current):
                return MISSING
            current = current[index]
        else:
            return MISSING
    return current


def set_path(obj: dict[str, Any], path: str, value: Any) -> None:
    """Write ``value`` at ``path``, creating intermediate objects."""
    parts = path.split(".")[:MAX_DEPTH]
    current = obj
    for part in parts[:-1]:
        nxt = current.get(part)
        if not isinstance(nxt, dict):
            nxt = {}
            current[part] = nxt
        current = nxt
    current[parts[-1]] = value
