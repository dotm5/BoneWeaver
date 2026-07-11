"""Module-local immutable Plan store; Blender files persist only IDs and snapshots."""

from __future__ import annotations

from .models import ConversionPlan


_PLAN_STORE: dict[str, ConversionPlan] = {}


def put_plan(plan: ConversionPlan) -> None:
    _PLAN_STORE[plan.plan_id] = plan


def get_plan(plan_id: str) -> ConversionPlan:
    return _PLAN_STORE[plan_id]


def has_plan(plan_id: str) -> bool:
    return plan_id in _PLAN_STORE


def clear_plans() -> None:
    _PLAN_STORE.clear()
