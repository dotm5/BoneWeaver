"""Pure hierarchy selection and immutable inspection-plan construction."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from .canonical import sha256
from .hierarchy_index import ArmatureHierarchyIndex
from .semantic_names import extract_semantic_stem, extract_sequence_index, extract_side_marker


HIERARCHY_INSPECTION_SCHEMA_VERSION = "1.0.0"
HIERARCHY_INSPECTION_ALGORITHM_VERSION = "hierarchy-inspection-v1"


class StableHierarchyEnum(str, Enum):
    """String enum whose values are persisted in inspection snapshots."""


class HierarchySelectionMode(StableHierarchyEnum):
    LINEAR_CHAIN = "LINEAR_CHAIN"
    FULL_SUBTREE = "FULL_SUBTREE"
    SAME_STEM_CHAIN = "SAME_STEM_CHAIN"
    MAIN_PATH_TO_LEAF = "MAIN_PATH_TO_LEAF"
    SELECTED_ROOTS_AND_DESCENDANTS = "SELECTED_ROOTS_AND_DESCENDANTS"


class HierarchyInspectionError(ValueError):
    """Raised when an inspection request cannot be represented safely."""


def _unique_names(values) -> tuple[str, ...]:
    result = {str(value) for value in values}
    if "" in result:
        raise HierarchyInspectionError("bone name collections must not contain empty strings")
    return tuple(sorted(result, key=lambda name: (name.casefold(), name)))


def _pair_tuple(values, *, label: str) -> tuple[tuple[str, str], ...]:
    result: dict[str, str] = {}
    for raw_key, raw_value in values:
        key = str(raw_key)
        value = str(raw_value)
        if not key or not value:
            raise HierarchyInspectionError(f"{label} entries must contain non-empty strings")
        if key in result and result[key] != value:
            raise HierarchyInspectionError(f"{label} contains conflicting entries for {key!r}")
        result[key] = value
    return tuple(sorted(result.items(), key=lambda item: (item[0].casefold(), item[0], item[1])))


@dataclass(frozen=True, slots=True)
class HierarchyInspectionInput:
    """Blender-free snapshot of everything that may affect an inspection.

    Branch continuations are provided as frozen name pairs.  A later controller
    may adapt G01 Branch Resolver results into those pairs without coupling this
    module to the conversion planner or to Blender RNA.
    """

    armature_object_name: str
    armature_fingerprint: str
    active_bone_name: str
    selection_mode: str
    selected_bone_names: tuple[str, ...] = ()
    branch_continuations: tuple[tuple[str, str], ...] = ()
    tip_helper_names: tuple[str, ...] = ()
    excluded_helper_names: tuple[str, ...] = ()
    semantic_categories: tuple[tuple[str, str], ...] = ()

    def __post_init__(self) -> None:
        mode = (
            self.selection_mode.value
            if isinstance(self.selection_mode, HierarchySelectionMode)
            else str(self.selection_mode)
        )
        try:
            HierarchySelectionMode(mode)
        except ValueError as exc:
            raise HierarchyInspectionError(f"unsupported hierarchy selection mode {mode!r}") from exc
        for field_name in ("armature_object_name", "armature_fingerprint", "active_bone_name"):
            if not str(getattr(self, field_name)):
                raise HierarchyInspectionError(f"{field_name} must not be empty")
        tip_helpers = _unique_names(self.tip_helper_names)
        excluded_helpers = _unique_names(self.excluded_helper_names)
        overlap = set(tip_helpers).intersection(excluded_helpers)
        if overlap:
            names = ", ".join(sorted(overlap))
            raise HierarchyInspectionError(f"helpers cannot be both tip and excluded: {names}")
        object.__setattr__(self, "armature_object_name", str(self.armature_object_name))
        object.__setattr__(self, "armature_fingerprint", str(self.armature_fingerprint))
        object.__setattr__(self, "active_bone_name", str(self.active_bone_name))
        object.__setattr__(self, "selection_mode", mode)
        object.__setattr__(self, "selected_bone_names", _unique_names(self.selected_bone_names))
        object.__setattr__(
            self,
            "branch_continuations",
            _pair_tuple(self.branch_continuations, label="branch_continuations"),
        )
        object.__setattr__(self, "tip_helper_names", tip_helpers)
        object.__setattr__(self, "excluded_helper_names", excluded_helpers)
        object.__setattr__(
            self,
            "semantic_categories",
            _pair_tuple(self.semantic_categories, label="semantic_categories"),
        )


@dataclass(frozen=True, slots=True)
class HierarchyInspectionPlan:
    """Frozen hierarchy result containing names only, never Blender RNA."""

    inspection_id: str
    armature_object_name: str
    armature_fingerprint: str
    active_bone_name: str
    parent_context_name: str | None
    selection_mode: str
    selected_bone_names: tuple[str, ...]
    branch_bone_names: tuple[str, ...]
    side_branch_root_names: tuple[str, ...]
    tip_helper_names: tuple[str, ...]
    excluded_helper_names: tuple[str, ...]
    semantic_categories: tuple[tuple[str, str], ...]
    issue_codes: tuple[str, ...]

    def __post_init__(self) -> None:
        try:
            mode = HierarchySelectionMode(self.selection_mode).value
        except ValueError as exc:
            raise HierarchyInspectionError(
                f"plan contains unsupported hierarchy selection mode {self.selection_mode!r}"
            ) from exc
        if not self.inspection_id:
            raise HierarchyInspectionError("inspection_id must not be empty")
        object.__setattr__(self, "inspection_id", str(self.inspection_id))
        object.__setattr__(self, "armature_object_name", str(self.armature_object_name))
        object.__setattr__(self, "armature_fingerprint", str(self.armature_fingerprint))
        object.__setattr__(self, "active_bone_name", str(self.active_bone_name))
        object.__setattr__(
            self,
            "parent_context_name",
            None if self.parent_context_name is None else str(self.parent_context_name),
        )
        object.__setattr__(self, "selection_mode", mode)
        for field_name in (
            "selected_bone_names",
            "branch_bone_names",
            "side_branch_root_names",
            "tip_helper_names",
            "excluded_helper_names",
            "issue_codes",
        ):
            values = tuple(dict.fromkeys(str(value) for value in getattr(self, field_name)))
            object.__setattr__(self, field_name, values)
        object.__setattr__(
            self,
            "semantic_categories",
            tuple((str(name), str(category)) for name, category in self.semantic_categories),
        )


@dataclass(slots=True)
class _InspectionAccumulator:
    selected: set[str]
    branches: set[str]
    side_branch_roots: set[str]
    excluded_helpers: set[str]
    issues: set[str]


def _child_partition(
    index: ArmatureHierarchyIndex,
    bone_name: str,
    excluded_helpers: set[str],
    accumulator: _InspectionAccumulator,
) -> tuple[str, ...]:
    children = index.children_of(bone_name)
    encountered_excluded = tuple(name for name in children if name in excluded_helpers)
    accumulator.excluded_helpers.update(encountered_excluded)
    return tuple(name for name in children if name not in excluded_helpers)


def _walk_subtrees(
    index: ArmatureHierarchyIndex,
    root_names: tuple[str, ...],
    excluded_helpers: set[str],
    accumulator: _InspectionAccumulator,
) -> None:
    stack = list(reversed(root_names))
    while stack:
        current = stack.pop()
        if current in accumulator.selected:
            continue
        accumulator.selected.add(current)
        children = _child_partition(index, current, excluded_helpers, accumulator)
        if len(children) > 1:
            accumulator.branches.add(current)
        stack.extend(reversed(children))


def _walk_linear(
    index: ArmatureHierarchyIndex,
    root_name: str,
    excluded_helpers: set[str],
    accumulator: _InspectionAccumulator,
) -> None:
    current = root_name
    while True:
        accumulator.selected.add(current)
        children = _child_partition(index, current, excluded_helpers, accumulator)
        if not children:
            return
        if len(children) > 1:
            accumulator.branches.add(current)
            accumulator.side_branch_roots.update(children)
            accumulator.issues.add("UECP_HIERARCHY_BRANCH_AMBIGUOUS")
            return
        current = children[0]


def _is_next_stem_bone(parent_name: str, child_name: str) -> bool:
    if extract_semantic_stem(parent_name) != extract_semantic_stem(child_name):
        return False
    parent_side = extract_side_marker(parent_name)
    child_side = extract_side_marker(child_name)
    if parent_side is not None and child_side != parent_side:
        return False
    parent_index = extract_sequence_index(parent_name)
    child_index = extract_sequence_index(child_name)
    if parent_index is None:
        return True
    return child_index is not None and child_index == parent_index + 1


def _walk_same_stem(
    index: ArmatureHierarchyIndex,
    root_name: str,
    excluded_helpers: set[str],
    tip_helpers: set[str],
    accumulator: _InspectionAccumulator,
) -> None:
    current = root_name
    while True:
        accumulator.selected.add(current)
        children = _child_partition(index, current, excluded_helpers, accumulator)
        if not children:
            return
        matching = tuple(
            name
            for name in children
            if name in tip_helpers or _is_next_stem_bone(current, name)
        )
        if len(children) > 1:
            accumulator.branches.add(current)
        if len(matching) > 1:
            accumulator.side_branch_roots.update(children)
            accumulator.issues.add("UECP_HIERARCHY_STEM_AMBIGUOUS")
            return
        if not matching:
            if len(children) > 1:
                accumulator.side_branch_roots.update(children)
            accumulator.issues.add("UECP_HIERARCHY_STEM_NO_CONTINUATION")
            return
        continuation = matching[0]
        accumulator.side_branch_roots.update(name for name in children if name != continuation)
        current = continuation


def _walk_main_path(
    index: ArmatureHierarchyIndex,
    root_name: str,
    excluded_helpers: set[str],
    continuations: dict[str, str],
    accumulator: _InspectionAccumulator,
) -> None:
    current = root_name
    while True:
        accumulator.selected.add(current)
        children = _child_partition(index, current, excluded_helpers, accumulator)
        if not children:
            return
        if len(children) == 1:
            current = children[0]
            continue
        accumulator.branches.add(current)
        continuation = continuations.get(current)
        if continuation not in children:
            accumulator.side_branch_roots.update(children)
            accumulator.issues.add(
                "UECP_HIERARCHY_CONTINUATION_INVALID"
                if continuation is not None
                else "UECP_HIERARCHY_BRANCH_AMBIGUOUS"
            )
            return
        accumulator.side_branch_roots.update(name for name in children if name != continuation)
        current = continuation


def build_hierarchy_inspection_plan(
    index: ArmatureHierarchyIndex,
    snapshot: HierarchyInspectionInput,
) -> HierarchyInspectionPlan:
    """Build one deterministic read-only inspection plan from frozen inputs."""
    active = snapshot.active_bone_name
    if active not in index:
        raise HierarchyInspectionError(f"active bone {active!r} is not present in hierarchy")

    mode = HierarchySelectionMode(snapshot.selection_mode)
    known_selected = index.order_names(snapshot.selected_bone_names)
    missing_selected = set(snapshot.selected_bone_names) - set(known_selected)
    accumulator = _InspectionAccumulator(set(), set(), set(), set(), set())
    if missing_selected:
        accumulator.issues.add("UECP_HIERARCHY_SELECTED_BONE_MISSING")
    excluded_helpers = set(snapshot.excluded_helper_names)

    if mode is HierarchySelectionMode.SELECTED_ROOTS_AND_DESCENDANTS:
        # In multi-root mode the current selection is the complete source of
        # roots.  Blender can retain an active Bone after it is deselected; that
        # stale active context must not silently expand a third subtree.
        roots = known_selected
        _walk_subtrees(index, roots, excluded_helpers, accumulator)
    elif mode is HierarchySelectionMode.FULL_SUBTREE:
        _walk_subtrees(index, (active,), excluded_helpers, accumulator)
    elif mode is HierarchySelectionMode.LINEAR_CHAIN:
        _walk_linear(index, active, excluded_helpers, accumulator)
    elif mode is HierarchySelectionMode.SAME_STEM_CHAIN:
        _walk_same_stem(
            index,
            active,
            excluded_helpers,
            set(snapshot.tip_helper_names),
            accumulator,
        )
    elif mode is HierarchySelectionMode.MAIN_PATH_TO_LEAF:
        _walk_main_path(
            index,
            active,
            excluded_helpers,
            dict(snapshot.branch_continuations),
            accumulator,
        )

    selected_names = index.order_names(accumulator.selected)
    branch_names = index.order_names(accumulator.branches)
    side_branch_roots = index.order_names(accumulator.side_branch_roots)
    tip_helpers = index.order_names(set(selected_names).intersection(snapshot.tip_helper_names))
    encountered_excluded = index.order_names(accumulator.excluded_helpers)
    categories_by_name = dict(snapshot.semantic_categories)
    semantic_categories = tuple(
        (name, categories_by_name[name])
        for name in selected_names
        if name in categories_by_name
    )
    issue_codes = tuple(sorted(accumulator.issues))
    parent_context = index.parent_of(active)

    identity_payload = (
        HIERARCHY_INSPECTION_SCHEMA_VERSION,
        HIERARCHY_INSPECTION_ALGORITHM_VERSION,
        snapshot,
        tuple((name, index.parent_by_child[name]) for name in index.bone_order),
        selected_names,
        branch_names,
        side_branch_roots,
        tip_helpers,
        encountered_excluded,
        semantic_categories,
        issue_codes,
    )
    inspection_id = sha256(identity_payload)
    return HierarchyInspectionPlan(
        inspection_id=inspection_id,
        armature_object_name=snapshot.armature_object_name,
        armature_fingerprint=snapshot.armature_fingerprint,
        active_bone_name=active,
        parent_context_name=parent_context,
        selection_mode=mode.value,
        selected_bone_names=selected_names,
        branch_bone_names=branch_names,
        side_branch_root_names=side_branch_roots,
        tip_helper_names=tip_helpers,
        excluded_helper_names=encountered_excluded,
        semantic_categories=semantic_categories,
        issue_codes=issue_codes,
    )


def hierarchy_inspection_plan_to_data(plan: HierarchyInspectionPlan) -> dict[str, object]:
    """Return a JSON-serializable, schema-shaped inspection payload."""
    return {
        "kind": "HIERARCHY_INSPECTION_PLAN",
        "schema_version": HIERARCHY_INSPECTION_SCHEMA_VERSION,
        "algorithm_version": HIERARCHY_INSPECTION_ALGORITHM_VERSION,
        "inspection_id": plan.inspection_id,
        "armature_object_name": plan.armature_object_name,
        "armature_fingerprint": plan.armature_fingerprint,
        "active_bone_name": plan.active_bone_name,
        "parent_context_name": plan.parent_context_name,
        "selection_mode": plan.selection_mode,
        "selected_bone_names": list(plan.selected_bone_names),
        "branch_bone_names": list(plan.branch_bone_names),
        "side_branch_root_names": list(plan.side_branch_root_names),
        "tip_helper_names": list(plan.tip_helper_names),
        "excluded_helper_names": list(plan.excluded_helper_names),
        "semantic_categories": [list(item) for item in plan.semantic_categories],
        "issue_codes": list(plan.issue_codes),
    }


def hierarchy_inspection_summary(plan: HierarchyInspectionPlan) -> dict[str, object]:
    """Return compact UI/report counts plus the frozen selected scope."""
    return {
        "inspection_id": plan.inspection_id,
        "active_bone_name": plan.active_bone_name,
        "parent_context_name": plan.parent_context_name,
        "selection_mode": plan.selection_mode,
        "selected_bone_names": list(plan.selected_bone_names),
        "bone_count": len(plan.selected_bone_names),
        "branch_count": len(plan.branch_bone_names),
        "side_branch_count": len(plan.side_branch_root_names),
        "tip_helper_count": len(plan.tip_helper_names),
        "excluded_helper_count": len(plan.excluded_helper_names),
        "issue_codes": list(plan.issue_codes),
    }
