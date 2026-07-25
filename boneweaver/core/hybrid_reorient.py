"""Force-complete multi-feature planning with per-bone UEFormat fallback."""

from __future__ import annotations

import dataclasses
import math

from mathutils import Matrix, Vector

from ..contracts import QUICK_REORIENT_MODE_HYBRID
from .canonical import sha256
from .models import ValidationIssue
from .quick_reorient import build_quick_reorient_plan


_EPSILON = 1.0e-7
_MULTI_FEATURE_PREFIX = "MULTI_FEATURE:"
_UEFORMAT_FALLBACK_PREFIX = "UEFORMAT_FALLBACK:"


def _warning(code, message, *, bones=(), details=()):
    return ValidationIssue(
        "WARNING",
        code,
        code.casefold(),
        message,
        tuple(bones),
        details=tuple(details),
    )


def _as_advisory(issue):
    return ValidationIssue(
        "WARNING",
        issue.code,
        issue.message_key,
        issue.message,
        issue.bone_names,
        issue.object_names,
        issue.node_ids,
        issue.edge_ids,
        issue.details,
    )


def _matrix3(state):
    return Matrix(
        tuple(
            tuple(state.matrix[row * 4 + column] for column in range(3))
            for row in range(3)
        )
    )


def _finite_vector(value):
    try:
        vector = Vector(value)
    except (TypeError, ValueError):
        return None
    if len(vector) != 3 or not all(math.isfinite(float(item)) for item in vector):
        return None
    return vector


def _reliable_precision_proposal(
    proposal,
    *,
    state,
    terminal_solution,
    branch_resolution,
    minimum_confidence,
):
    tail = _finite_vector(proposal.proposed_tail)
    reference = _finite_vector(proposal.proposed_roll_reference_z)
    if tail is None or reference is None:
        return False
    if (tail - Vector(state.head)).length <= _EPSILON:
        return False
    if not math.isfinite(float(proposal.confidence)):
        return False

    if branch_resolution is not None:
        return bool(
            branch_resolution.selected_child_name
            and branch_resolution.result == "HIGH"
            and not branch_resolution.requires_confirmation
        )
    if terminal_solution is not None:
        return bool(
            terminal_solution.resolution_class == "AUTO_CONFIDENT"
            and not terminal_solution.requires_confirmation
            and terminal_solution.confidence >= minimum_confidence
        )
    return bool(
        proposal.terminal_source == "UNIQUE_DIRECT_CHILD_HEAD"
        and proposal.confidence >= minimum_confidence
    )


def _precision_source(proposal, terminal_solution, branch_resolution):
    if branch_resolution is not None:
        return f"{_MULTI_FEATURE_PREFIX}BRANCH_HIGH"
    if terminal_solution is not None:
        return f"{_MULTI_FEATURE_PREFIX}{terminal_solution.source}"
    return f"{_MULTI_FEATURE_PREFIX}{proposal.terminal_source}"


def _overlay_precision(base_plan, precision_plan, *, minimum_confidence):
    states = {state.bone_name: state for state in base_plan.bone_states}
    precision_by_name = {
        proposal.bone_name: proposal for proposal in precision_plan.proposals
    }
    terminal_by_name = {
        solution.bone_name: solution for solution in precision_plan.terminal_solutions
    }
    branch_by_name = {
        resolution.branch_bone_name: resolution
        for resolution in precision_plan.branch_resolutions
    }
    proposals = []
    precision_names = []
    fallback_names = []
    for fallback in base_plan.proposals:
        if fallback.skipped:
            proposals.append(fallback)
            continue
        precision = precision_by_name.get(fallback.bone_name)
        terminal = terminal_by_name.get(fallback.bone_name)
        branch = branch_by_name.get(fallback.bone_name)
        if precision is None or not _reliable_precision_proposal(
            precision,
            state=states[fallback.bone_name],
            terminal_solution=terminal,
            branch_resolution=branch,
            minimum_confidence=minimum_confidence,
        ):
            proposals.append(fallback)
            fallback_names.append(fallback.bone_name)
            continue

        state = states[fallback.bone_name]
        tail = Vector(precision.proposed_tail)
        direction = tail - Vector(state.head)
        local_direction = None
        if direction.length > _EPSILON:
            local = _matrix3(state).inverted_safe() @ direction.normalized()
            local_direction = tuple(float(value) for value in local)
        proposals.append(
            dataclasses.replace(
                fallback,
                source=_precision_source(precision, terminal, branch),
                target_direction_local=local_direction,
                target_tail=tuple(float(value) for value in tail),
                target_roll_reference=tuple(
                    float(value) for value in precision.proposed_roll_reference_z
                ),
                target_length=float(direction.length),
            )
        )
        precision_names.append(fallback.bone_name)

    return tuple(proposals), tuple(precision_names), tuple(fallback_names)


def _replace_plan(base_plan, proposals, issues):
    plan = dataclasses.replace(
        base_plan,
        proposals=tuple(proposals),
        issues=tuple(
            sorted(
                issues,
                key=lambda item: (
                    item.severity,
                    item.code,
                    item.bone_names,
                    item.object_names,
                ),
            )
        ),
    )
    payload = dataclasses.asdict(plan)
    payload.pop("plan_id")
    return dataclasses.replace(plan, plan_id=sha256(payload))


def build_hybrid_reorient_plan(context, *, precision_builder=None):
    """Build a whole-Armature plan that can never be blocked by recognition."""
    base_plan = build_quick_reorient_plan(
        context,
        connect_linear_chains=True,
        mode=QUICK_REORIENT_MODE_HYBRID,
    )
    if base_plan is None or base_plan.already_normalized:
        return base_plan

    if precision_builder is None:
        from .planner import build_plan as precision_builder

    scope_names = tuple(
        proposal.bone_name for proposal in base_plan.proposals if not proposal.skipped
    )
    issues = list(base_plan.issues)
    try:
        precision_plan = precision_builder(context, scope_names=scope_names)
    except Exception as error:
        issues.append(
            _warning(
                "BONEWEAVER_HYBRID_MULTI_FEATURE_UNAVAILABLE",
                "Multi-feature planning failed; every eligible bone used the UEFormat fallback",
                details=(("error", str(error)),),
            )
        )
        return _replace_plan(base_plan, base_plan.proposals, issues)

    if precision_plan is None:
        issues.append(
            _warning(
                "BONEWEAVER_HYBRID_MULTI_FEATURE_UNAVAILABLE",
                "Multi-feature planning returned no plan; every eligible bone used the UEFormat fallback",
            )
        )
        return _replace_plan(base_plan, base_plan.proposals, issues)

    issues.extend(_as_advisory(issue) for issue in precision_plan.issues)
    minimum_confidence = float(
        getattr(context.scene.boneweaver_settings, "minimum_confidence", 0.7)
    )
    proposals, precision_names, fallback_names = _overlay_precision(
        base_plan,
        precision_plan,
        minimum_confidence=minimum_confidence,
    )
    if fallback_names:
        issues.append(
            _warning(
                "BONEWEAVER_HYBRID_UEFORMAT_FALLBACK_USED",
                (
                    f"{len(fallback_names)} bones were not confidently recognized "
                    "and used the automatic UEFormat fallback"
                ),
                bones=fallback_names,
            )
        )
    if precision_names:
        issues.append(
            _warning(
                "BONEWEAVER_HYBRID_MULTI_FEATURE_USED",
                f"{len(precision_names)} bones used confident multi-feature results",
                bones=precision_names,
            )
        )
    return _replace_plan(base_plan, proposals, issues)


def is_multi_feature_source(source: str) -> bool:
    return source.startswith(_MULTI_FEATURE_PREFIX)


def is_ueformat_fallback_source(source: str) -> bool:
    return source.startswith(_UEFORMAT_FALLBACK_PREFIX)
