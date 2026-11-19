"""Input validation helpers shared by the pure simulation modules."""

from __future__ import annotations

from collections.abc import Iterable


def require_non_negative(value: int, label: str) -> int:
    if value < 0:
        raise ValueError(f"{label} must be zero or greater.")
    return value


def require_positive(value: int, label: str) -> int:
    if value <= 0:
        raise ValueError(f"{label} must be greater than zero.")
    return value


def require_unique(values: Iterable[str], label: str) -> None:
    seen: set[str] = set()
    for value in values:
        if value in seen:
            raise ValueError(f"{label} '{value}' is repeated. Each entry must be unique.")
        seen.add(value)
