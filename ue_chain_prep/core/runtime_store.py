"""Module-local immutable Plan store; Blender files persist only IDs and snapshots."""

from __future__ import annotations

from .models import ConversionPlan


_PLAN_STORE: dict[str, ConversionPlan] = {}
_LAST_REPORT: dict | None = None
_PREVIEW_CACHE: tuple = ()
_PERFORMANCE: dict[str, dict] = {}


def put_plan(plan: ConversionPlan) -> None:
    _PLAN_STORE[plan.plan_id] = plan


def get_plan(plan_id: str) -> ConversionPlan:
    return _PLAN_STORE[plan_id]


def has_plan(plan_id: str) -> bool:
    return plan_id in _PLAN_STORE


def clear_plans() -> None:
    global _LAST_REPORT, _PREVIEW_CACHE
    _PLAN_STORE.clear()
    _LAST_REPORT = None
    _PREVIEW_CACHE = ()
    _PERFORMANCE.clear()


def put_report(report: dict) -> None:
    global _LAST_REPORT
    _LAST_REPORT = report


def get_report() -> dict | None:
    return _LAST_REPORT


def put_preview_cache(cache) -> None:
    global _PREVIEW_CACHE
    _PREVIEW_CACHE = tuple(cache)


def get_preview_cache() -> tuple:
    return _PREVIEW_CACHE


def put_performance(plan_id: str, metrics: dict) -> None:
    _PERFORMANCE[plan_id] = dict(metrics)


def get_performance(plan_id: str) -> dict:
    return dict(_PERFORMANCE.get(plan_id, {}))
