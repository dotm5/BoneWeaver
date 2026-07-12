"""Conservative, read-only classification of selected terminal helper bones."""

from __future__ import annotations

import math
import re
import statistics
from collections.abc import Iterable, Mapping

from ..contracts import BoneSemanticRole, TerminalSource
from .models import BoneState, TipHelperClassification


_STRONG_EXCLUSION_TOKENS = frozenset(
    {
        "attach",
        "camera",
        "control",
        "corrective",
        "ctrl",
        "effector",
        "fk",
        "ik",
        "muzzle",
        "pole",
        "roll",
        "socket",
        "target",
        "twist",
        "weapon",
    }
)
_POSITIVE_NAME_TOKENS = frozenset({"dummy", "end", "nub", "terminal", "tip"})
_DEPENDENCY_ISSUE_CODES = frozenset(
    {"UECP_RELATED_CONSTRAINT", "UECP_RELATED_DRIVER", "UECP_BONE_PARENTED_OBJECT"}
)


def _length(vector) -> float:
    return math.sqrt(sum(float(component) * float(component) for component in vector))


def _sub(first, second):
    return tuple(float(first[index] - second[index]) for index in range(3))


def _name_tokens(name: str) -> tuple[str, ...]:
    separated = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "_", str(name))
    return tuple(token.lower() for token in re.findall(r"[A-Za-z]+|\d+|[\u4e00-\u9fff]+", separated))


def _has_strong_exclusion(state: BoneState) -> bool:
    if state.is_socket:
        return True
    tokens = _name_tokens(state.name) + tuple(str(flag).lower() for flag in state.importer_metadata_flags)
    return any(
        token == excluded or token.startswith(excluded)
        for token in tokens
        for excluded in _STRONG_EXCLUSION_TOKENS
    )


def _has_explicit_socket_control_evidence(state: BoneState | None, name: str) -> bool:
    """Return whether a child is explicitly excluded as Socket/Control.

    Child names can refer to bones outside the frozen selection, so this check
    deliberately accepts strong name evidence when no BoneState is available.
    Generic helper exclusions such as IK/Twist are not enough for this narrow
    exception.
    """

    if state is not None and state.is_socket:
        return True
    tokens = list(_name_tokens(name))
    if state is not None:
        tokens.extend(str(flag).lower() for flag in state.importer_metadata_flags)
    return any(
        token == excluded or token.startswith(excluded)
        for token in tokens
        for excluded in ("socket", "control", "ctrl")
    )


def _positive_name_evidence(name: str) -> tuple[str, ...]:
    tokens = _name_tokens(name)
    matches = {
        token
        for token in tokens
        if any(token == positive or token.startswith(positive) for positive in _POSITIVE_NAME_TOKENS)
    }
    if "末端" in str(name):
        matches.add("末端")
    return tuple(sorted(matches))


def _has_dependency_issue(issues: Iterable, names: set[str]) -> bool:
    for issue in issues:
        if getattr(issue, "code", "") not in _DEPENDENCY_ISSUE_CODES:
            continue
        bone_names = set(getattr(issue, "bone_names", ()) or ())
        if not bone_names or bone_names.intersection(names):
            return True
    return False


def _clouds_by_name(weight_clouds) -> dict[str, object]:
    if isinstance(weight_clouds, Mapping):
        return dict(weight_clouds)
    return {
        cloud.bone_name: cloud
        for cloud in weight_clouds
        if getattr(cloud, "bone_name", None) is not None
    }


def _has_zero_effective_weight(cloud, epsilon: float) -> bool:
    if cloud is None:
        return False
    return (
        abs(float(getattr(cloud, "total_statistical_weight", math.inf))) <= epsilon
        and abs(float(getattr(cloud, "effective_sample_count", math.inf))) <= epsilon
    )


def _upstream_lengths(parent: BoneState, by_name: Mapping[str, BoneState], epsilon: float):
    lengths = []
    current = parent
    for _ in range(3):
        ancestor = by_name.get(current.parent_name)
        if ancestor is None:
            break
        length = _length(_sub(current.head, ancestor.head))
        if math.isfinite(length) and length > epsilon:
            lengths.append(length)
        current = ancestor
    return tuple(lengths)


def classify_tip_helpers(
    bone_states: tuple[BoneState, ...],
    weight_clouds,
    issues=(),
    *,
    epsilon: float = 1.0e-7,
    minimum_length_ratio: float = 0.25,
    maximum_length_ratio: float = 2.0,
    maximum_upstream_bend_degrees: float = 135.0,
) -> tuple[TipHelperClassification, ...]:
    """Return only high-confidence reference-only helpers, sorted by bone name.

    Missing evidence rejects classification. Names can strengthen a result but can
    never make an otherwise ineligible bone pass.
    """

    by_name = {state.name: state for state in bone_states}
    clouds = _clouds_by_name(weight_clouds)
    results = []
    minimum_ratio = max(0.0, float(minimum_length_ratio))
    maximum_ratio = max(minimum_ratio, float(maximum_length_ratio))
    maximum_bend = max(0.0, min(180.0, float(maximum_upstream_bend_degrees)))
    minimum_direction_cosine = math.cos(math.radians(maximum_bend))

    for state in sorted(bone_states, key=lambda item: item.name):
        if not _has_zero_effective_weight(clouds.get(state.name), epsilon):
            continue
        parent = by_name.get(state.parent_name)
        if parent is None or not parent.use_deform:
            continue
        parent_cloud = clouds.get(parent.name)
        if parent_cloud is None or (
            float(getattr(parent_cloud, "total_statistical_weight", 0.0)) <= epsilon
            and float(getattr(parent_cloud, "effective_sample_count", 0.0)) <= epsilon
        ):
            continue
        if len(parent.child_names) != 1 or parent.child_names[0] != state.name:
            continue
        if _has_strong_exclusion(state) or _has_strong_exclusion(parent):
            continue
        excluded_children = tuple(
            child_name
            for child_name in state.child_names
            if _has_explicit_socket_control_evidence(by_name.get(child_name), child_name)
        )
        if len(excluded_children) != len(state.child_names):
            continue
        if _has_dependency_issue(issues, {state.name, parent.name}):
            continue

        offset = _sub(state.head, parent.head)
        helper_length = _length(offset)
        if not math.isfinite(helper_length) or helper_length <= epsilon:
            continue

        upstream_lengths = _upstream_lengths(parent, by_name, epsilon)
        if upstream_lengths:
            reference_length = float(statistics.median(upstream_lengths))
        else:
            reference_length = _length(_sub(parent.tail, parent.head))
        if not math.isfinite(reference_length) or reference_length <= epsilon:
            continue
        length_ratio = helper_length / reference_length
        if not math.isfinite(length_ratio) or not minimum_ratio <= length_ratio <= maximum_ratio:
            continue

        direction_cosine = None
        upstream_parent = by_name.get(parent.parent_name)
        if upstream_parent is not None:
            upstream = _sub(parent.head, upstream_parent.head)
            upstream_length = _length(upstream)
            if upstream_length > epsilon:
                direction_cosine = sum(upstream[index] * offset[index] for index in range(3)) / (
                    upstream_length * helper_length
                )
                direction_cosine = max(-1.0, min(1.0, direction_cosine))
                if direction_cosine < minimum_direction_cosine:
                    continue

        positive_tokens = _positive_name_evidence(state.name)
        evidence = {
            "IN_SCOPE_UNIQUE_CHILD_OF_DEFORM_PARENT",
            "NONZERO_REASONABLE_PARENT_HELPER_LENGTH",
            "NO_DEPENDENCY_ISSUE",
            "NO_STRONG_HELPER_EXCLUSION",
            "NO_CHILD_OR_EXPLICIT_SOCKET_CONTROL_CHILDREN",
            "ZERO_EFFECTIVE_WEIGHT",
            f"PARENT_HELPER_LENGTH_RATIO:{length_ratio:.6f}",
        }
        for child_name in excluded_children:
            evidence.add(f"EXCLUDED_SOCKET_CONTROL_CHILD:{child_name}")
        if direction_cosine is not None:
            evidence.add(f"UPSTREAM_DIRECTION_COSINE:{direction_cosine:.6f}")
        for token in positive_tokens:
            evidence.add(f"POSITIVE_NAME_TOKEN:{token}")
        confidence = 0.90 if direction_cosine is not None else 0.85
        if positive_tokens:
            confidence = min(0.95, confidence + 0.05)
        results.append(
            TipHelperClassification(
                bone_name=state.name,
                parent_bone_name=parent.name,
                role=BoneSemanticRole.EXISTING_TIP_HELPER.value,
                reference_only=True,
                mutation_target=False,
                requires_own_tail=False,
                source=TerminalSource.EXISTING_TIP_HELPER_HEAD.value,
                confidence=confidence,
                evidence=tuple(sorted(evidence)),
                excluded_child_names=excluded_children,
            )
        )

    return tuple(sorted(results, key=lambda item: (item.bone_name, item.parent_bone_name)))
