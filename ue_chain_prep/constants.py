"""Internal defaults derived from the stable public contract."""

from __future__ import annotations

from .contracts import StableStringEnum


def enum_items(enum_type: type[StableStringEnum]) -> tuple[tuple[str, str, str], ...]:
    return tuple((item.value, item.value.replace("_", " ").title(), "") for item in enum_type)


POSITION_EPSILON_MINIMUM = 1.0e-7
DIRECTION_EPSILON = 1.0e-7
