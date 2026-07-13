"""Module-local immutable Plan store; Blender files persist only IDs and snapshots."""

from __future__ import annotations

from dataclasses import dataclass

from .hierarchy_index import ArmatureHierarchyIndex
from .hierarchy_inspection import HierarchyInspectionInput, HierarchyInspectionPlan
from .models import ConversionPlan
from .quick_reorient_models import QuickReorientPlan
from .semantic_models import SemanticDiscoveryPlan


_PLAN_STORE: dict[str, ConversionPlan] = {}
_QUICK_PLAN_STORE: dict[str, QuickReorientPlan] = {}
_LAST_REPORT: dict | None = None
_PREVIEW_CACHE: tuple = ()
_PERFORMANCE: dict[str, dict] = {}
_HIERARCHY_INSPECTION: "HierarchyInspectionSession | None" = None
_USED_INSPECTION_SCOPE: "FrozenInspectionScope | None" = None
_SEMANTIC_DISCOVERY: "SemanticDiscoverySession | None" = None
_USED_SEMANTIC_SCOPE: "FrozenSemanticScope | None" = None
_ANALYSIS_SCOPES: dict[str, "FrozenInspectionScope | FrozenSemanticScope"] = {}


@dataclass(frozen=True, slots=True)
class HierarchyInspectionSession:
    """One RNA-free hierarchy inspection and the inputs needed to rebuild it."""

    plan: HierarchyInspectionPlan
    index: ArmatureHierarchyIndex
    snapshot: HierarchyInspectionInput
    source_filepath: str
    armature_data_name: str
    manual_branch_continuations: tuple[tuple[str, str], ...] = ()


@dataclass(frozen=True, slots=True)
class FrozenInspectionScope:
    """Explicitly accepted hierarchy names for a later Analyze invocation."""

    inspection_id: str
    armature_object_name: str
    armature_data_name: str
    armature_fingerprint: str
    source_filepath: str
    bone_names: tuple[str, ...]
    manual_branch_continuations: tuple[tuple[str, str], ...] = ()
    reference_only_tip_helper_names: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class SemanticDiscoverySession:
    """One immutable discovery plan plus the user's explicit confirmations."""

    plan: SemanticDiscoveryPlan
    discovery_plan_id: str
    source_filepath: str
    armature_data_name: str
    confirmed_chain_ids: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class FrozenSemanticScope:
    """Confirmed semantic names frozen for one later Analyze invocation."""

    discovery_plan_id: str
    armature_object_name: str
    armature_data_name: str
    armature_fingerprint: str
    source_filepath: str
    bone_names: tuple[str, ...]
    confirmed_chain_ids: tuple[str, ...]


def put_plan(plan: ConversionPlan) -> None:
    _PLAN_STORE[plan.plan_id] = plan


def get_plan(plan_id: str) -> ConversionPlan:
    return _PLAN_STORE[plan_id]


def has_plan(plan_id: str) -> bool:
    return plan_id in _PLAN_STORE


def clear_plans() -> None:
    global _LAST_REPORT, _PREVIEW_CACHE, _HIERARCHY_INSPECTION, _USED_INSPECTION_SCOPE
    global _SEMANTIC_DISCOVERY, _USED_SEMANTIC_SCOPE
    _PLAN_STORE.clear()
    _QUICK_PLAN_STORE.clear()
    _LAST_REPORT = None
    _PREVIEW_CACHE = ()
    _PERFORMANCE.clear()
    _HIERARCHY_INSPECTION = None
    _USED_INSPECTION_SCOPE = None
    _SEMANTIC_DISCOVERY = None
    _USED_SEMANTIC_SCOPE = None
    _ANALYSIS_SCOPES.clear()


def put_quick_plan(plan: QuickReorientPlan) -> None:
    _QUICK_PLAN_STORE[plan.plan_id] = plan


def get_quick_plan(plan_id: str) -> QuickReorientPlan:
    return _QUICK_PLAN_STORE[plan_id]


def has_quick_plan(plan_id: str) -> bool:
    return plan_id in _QUICK_PLAN_STORE


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


def put_hierarchy_inspection(session: HierarchyInspectionSession) -> None:
    global _HIERARCHY_INSPECTION
    _HIERARCHY_INSPECTION = session


def get_hierarchy_inspection() -> HierarchyInspectionSession | None:
    return _HIERARCHY_INSPECTION


def clear_hierarchy_inspection(*, clear_used_scope: bool = True) -> None:
    global _HIERARCHY_INSPECTION, _USED_INSPECTION_SCOPE
    _HIERARCHY_INSPECTION = None
    if clear_used_scope:
        _USED_INSPECTION_SCOPE = None


def put_used_inspection_scope(scope: FrozenInspectionScope | None) -> None:
    global _USED_INSPECTION_SCOPE
    _USED_INSPECTION_SCOPE = scope


def get_used_inspection_scope() -> FrozenInspectionScope | None:
    return _USED_INSPECTION_SCOPE


def put_semantic_discovery(session: SemanticDiscoverySession) -> None:
    global _SEMANTIC_DISCOVERY
    _SEMANTIC_DISCOVERY = session


def get_semantic_discovery() -> SemanticDiscoverySession | None:
    return _SEMANTIC_DISCOVERY


def clear_semantic_discovery(*, clear_used_scope: bool = True) -> None:
    global _SEMANTIC_DISCOVERY, _USED_SEMANTIC_SCOPE
    _SEMANTIC_DISCOVERY = None
    if clear_used_scope:
        _USED_SEMANTIC_SCOPE = None


def put_used_semantic_scope(scope: FrozenSemanticScope | None) -> None:
    global _USED_SEMANTIC_SCOPE
    _USED_SEMANTIC_SCOPE = scope


def get_used_semantic_scope() -> FrozenSemanticScope | None:
    return _USED_SEMANTIC_SCOPE


def bind_analysis_scope(
    plan_id: str,
    scope: FrozenInspectionScope | FrozenSemanticScope | None,
) -> None:
    if scope is None:
        _ANALYSIS_SCOPES.pop(plan_id, None)
    else:
        _ANALYSIS_SCOPES[plan_id] = scope


def get_analysis_scope(plan_id: str) -> FrozenInspectionScope | FrozenSemanticScope | None:
    return _ANALYSIS_SCOPES.get(plan_id)
