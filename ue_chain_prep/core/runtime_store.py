"""Module-local immutable Plan store; Blender files persist only IDs and snapshots."""

from __future__ import annotations

from .models import ConversionPlan


_PLAN_STORE: dict[str, ConversionPlan] = {}
_LAST_REPORT: dict | None = None


def put_plan(plan: ConversionPlan) -> None:
    _PLAN_STORE[plan.plan_id] = plan


def get_plan(plan_id: str) -> ConversionPlan:
    return _PLAN_STORE[plan_id]


def has_plan(plan_id: str) -> bool:
    return plan_id in _PLAN_STORE


def clear_plans() -> None:
    global _LAST_REPORT
    _PLAN_STORE.clear()
    _LAST_REPORT = None


def put_report(report: dict) -> None:
    global _LAST_REPORT
    _LAST_REPORT = report


def get_report() -> dict | None:
    return _LAST_REPORT
