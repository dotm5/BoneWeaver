"""Read-only semantic chain discovery and geometry evidence.

The module intentionally works on immutable bone snapshots. Blender integration is
limited to adapters at the public entry points; scoring never edits RNA data.
"""

from __future__ import annotations

from dataclasses import dataclass
from collections.abc import Mapping
import math
import re
import statistics

from .canonical import sha256
from .semantic_models import (
    DiscoveredChain,
    GeometryProjectionNeed,
    SecondaryBoneCategory,
    SemanticBoneEvidence,
    SemanticDiscoveryClass,
    SemanticDiscoveryPlan,
)
from .semantic_names import (
    extract_semantic_stem,
    extract_sequence_index,
    extract_side_marker,
    normalize_bone_name,
    tokenize_bone_name,
)
from .semantic_rule_loader import load_default_rule_set, merge_rule_sets


SEMANTIC_DISCOVERY_SCHEMA_VERSION = "2.0.0"
SEMANTIC_DISCOVERY_ALGORITHM_VERSION = "semantic-discovery-v0.2.0"

_EXCLUSION_CATEGORIES = frozenset({
    SecondaryBoneCategory.MAIN_SKELETON.value,
    SecondaryBoneCategory.SOCKET.value,
    SecondaryBoneCategory.IK_CONTROL.value,
    SecondaryBoneCategory.TWIST_DEFORM.value,
    SecondaryBoneCategory.FACIAL.value,
})
_CLASS_RANK = {
    SemanticDiscoveryClass.EXCLUDE.value: 0,
    SemanticDiscoveryClass.AMBIGUOUS.value: 1,
    SemanticDiscoveryClass.SUGGEST_INCLUDE.value: 2,
    SemanticDiscoveryClass.AUTO_INCLUDE.value: 3,
}
_EXCLUSION_REASON_BY_CATEGORY = {
    SecondaryBoneCategory.MAIN_SKELETON.value: "BONEWEAVER_SEMANTIC_EXCLUDE_MAIN_SKELETON",
    SecondaryBoneCategory.SOCKET.value: "BONEWEAVER_SEMANTIC_EXCLUDE_SOCKET",
    SecondaryBoneCategory.IK_CONTROL.value: "BONEWEAVER_SEMANTIC_EXCLUDE_IK_CONTROL",
    SecondaryBoneCategory.TWIST_DEFORM.value: "BONEWEAVER_SEMANTIC_EXCLUDE_TWIST_DEFORM",
    SecondaryBoneCategory.FACIAL.value: "BONEWEAVER_SEMANTIC_EXCLUDE_FACIAL",
}


@dataclass(frozen=True, slots=True)
class UniformDisplayLengthEvidence:
    detected: bool
    representative_length: float
    cluster_ratio: float
    hierarchy_distance_spread_ratio: float


@dataclass(frozen=True, slots=True)
class GeometryProjectionAssessment:
    need: str
    mismatch_score: float
    direction_angle_degrees: float
    bone_length: float
    hierarchy_distance: float
    length_ratio: float
    tail_child_distance: float
    reason_codes: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class _CategoryDecision:
    category: str
    maximum_class: str
    semantic_score: float
    metadata_score: float
    exclusion_penalty: float
    category_conflict: bool
    reason_codes: tuple[str, ...]


def _subtract(first, second) -> tuple[float, float, float]:
    return tuple(float(first[index]) - float(second[index]) for index in range(3))


def _length(vector) -> float:
    return math.sqrt(sum(float(value) * float(value) for value in vector))


def _distance(first, second) -> float:
    return _length(_subtract(first, second))


def _angle_degrees(first, second) -> float:
    first_length = _length(first)
    second_length = _length(second)
    if first_length <= 1.0e-12 or second_length <= 1.0e-12:
        return 180.0
    cosine = sum(float(a) * float(b) for a, b in zip(first, second)) / (first_length * second_length)
    return math.degrees(math.acos(max(-1.0, min(1.0, cosine))))


def detect_uniform_imported_display_length(armature) -> UniformDisplayLengthEvidence:
    """Detect importer-style uniform short display bones without modifying input.

    `armature` may be an iterable of immutable bone snapshots or an object exposing
    `bone_states`. Only non-root bones participate, matching the public contract.
    """
    states = tuple(getattr(armature, "bone_states", armature))
    by_name = {state.name: state for state in states}
    lengths = []
    hierarchy_distances = []
    for state in states:
        if state.parent_name is None or state.parent_name not in by_name:
            continue
        bone_length = _distance(state.tail, state.head)
        edge_length = _distance(state.head, by_name[state.parent_name].head)
        if bone_length > 1.0e-12 and edge_length > 1.0e-12:
            lengths.append(bone_length)
            hierarchy_distances.append(edge_length)
    if len(lengths) < 4:
        return UniformDisplayLengthEvidence(False, 0.0, 0.0, 0.0)
    representative = statistics.median(lengths)
    tolerance = max(representative * 0.10, 1.0e-8)
    cluster_ratio = sum(abs(value - representative) <= tolerance for value in lengths) / len(lengths)
    minimum_distance = min(hierarchy_distances)
    spread_ratio = max(hierarchy_distances) / minimum_distance if minimum_distance > 1.0e-12 else math.inf
    median_distance = statistics.median(hierarchy_distances)
    detected = (
        cluster_ratio >= 0.70
        and spread_ratio >= 1.50
        and representative / median_distance <= 0.35
    )
    return UniformDisplayLengthEvidence(detected, representative, cluster_ratio, spread_ratio)


def assess_geometry_projection(
    bone,
    bones_by_name: dict,
    uniform_display_length: UniformDisplayLengthEvidence | None = None,
) -> GeometryProjectionAssessment:
    """Classify display geometry while deferring leaves and branches to solvers."""
    children = tuple(name for name in bone.child_names if name in bones_by_name)
    bone_length = _distance(bone.tail, bone.head)
    if len(children) != 1:
        reasons = ("BONEWEAVER_SEMANTIC_BRANCH_DETECTED",) if len(children) > 1 else ()
        return GeometryProjectionAssessment(
            GeometryProjectionNeed.UNRESOLVED.value, 0.0, 0.0, bone_length,
            0.0, 0.0, 0.0, reasons,
        )

    child = bones_by_name[children[0]]
    display_direction = _subtract(bone.tail, bone.head)
    hierarchy_direction = _subtract(child.head, bone.head)
    hierarchy_distance = _length(hierarchy_direction)
    tail_child_distance = _distance(bone.tail, child.head)
    angle = _angle_degrees(display_direction, hierarchy_direction)
    length_ratio = bone_length / hierarchy_distance if hierarchy_distance > 1.0e-12 else 0.0
    epsilon = max(1.0e-5, hierarchy_distance * 1.0e-4)
    if tail_child_distance <= epsilon:
        return GeometryProjectionAssessment(
            GeometryProjectionNeed.NOT_REQUIRED.value, 0.0, angle, bone_length,
            hierarchy_distance, length_ratio, tail_child_distance,
            ("BONEWEAVER_SEMANTIC_ALREADY_CONTINUOUS",),
        )

    uniform = uniform_display_length or UniformDisplayLengthEvidence(False, 0.0, 0.0, 0.0)
    tail_distance_ratio = tail_child_distance / hierarchy_distance if hierarchy_distance > 1.0e-12 else math.inf
    required = (
        hierarchy_distance <= 1.0e-12
        or bone_length <= 1.0e-12
        or angle >= 45.0
        or length_ratio < 0.50
        or (uniform.detected and length_ratio < 0.75 and tail_distance_ratio > 0.20)
        or tail_distance_ratio > 0.65
    )
    reasons = ["BONEWEAVER_SEMANTIC_TAIL_CHILD_MISMATCH"]
    if uniform.detected:
        reasons.append("BONEWEAVER_SEMANTIC_UNIFORM_DISPLAY_LENGTH")
    if required:
        need = GeometryProjectionNeed.REQUIRED.value
        score = 1.0
    else:
        need = GeometryProjectionNeed.RECOMMENDED.value
        score = 0.55
    return GeometryProjectionAssessment(
        need, score, angle, bone_length, hierarchy_distance, length_ratio,
        tail_child_distance, tuple(sorted(reasons)),
    )


def _value(source, key, default=None):
    if source is None:
        return default
    if isinstance(source, Mapping):
        return source.get(key, default)
    return getattr(source, key, default)


def _index_weight_summaries(weight_summaries):
    if weight_summaries is None:
        return {}
    if isinstance(weight_summaries, Mapping):
        return dict(weight_summaries)
    return {
        item.bone_name: item
        for item in weight_summaries
        if getattr(item, "bone_name", None)
    }


def _metadata_for_bone(state, metadata_by_bone):
    metadata = {
        str(flag).casefold(): True
        for flag in getattr(state, "importer_metadata_flags", ())
    }
    if bool(getattr(state, "is_socket", False)):
        metadata["is_socket"] = True
    supplied = (metadata_by_bone or {}).get(state.name, {})
    if isinstance(supplied, Mapping):
        metadata.update({str(key).casefold(): value for key, value in supplied.items()})
    return metadata


def _metadata_categories(metadata, rules):
    categories = set()
    for key, category in rules.metadata_rules.items():
        value = metadata.get(str(key).casefold())
        normalized_value = value.strip().upper() if isinstance(value, str) else value
        if normalized_value not in (None, False, 0, "", "NONE", "UNKNOWN"):
            categories.add(str(category).upper())
    return tuple(sorted(categories))


def _category_decision(state, rules, metadata, main_patterns):
    tokens = frozenset(tokenize_bone_name(state.name))
    normalized_name = normalize_bone_name(state.name)
    metadata_categories = _metadata_categories(metadata, rules)
    exclusions = []
    if (
        bool(getattr(state, "is_socket", False))
        or tokens.intersection(rules.socket_tokens)
        or SecondaryBoneCategory.SOCKET.value in metadata_categories
    ):
        exclusions.append(SecondaryBoneCategory.SOCKET.value)
    if tokens.intersection(rules.ik_control_tokens) or SecondaryBoneCategory.IK_CONTROL.value in metadata_categories:
        exclusions.append(SecondaryBoneCategory.IK_CONTROL.value)
    if tokens.intersection(rules.twist_deform_tokens) or SecondaryBoneCategory.TWIST_DEFORM.value in metadata_categories:
        exclusions.append(SecondaryBoneCategory.TWIST_DEFORM.value)
    if tokens.intersection(rules.facial_tokens) or SecondaryBoneCategory.FACIAL.value in metadata_categories:
        exclusions.append(SecondaryBoneCategory.FACIAL.value)
    if (
        tokens.intersection(rules.main_skeleton_tokens)
        or any(pattern.search(normalized_name) for pattern in main_patterns)
        or SecondaryBoneCategory.MAIN_SKELETON.value in metadata_categories
    ):
        exclusions.append(SecondaryBoneCategory.MAIN_SKELETON.value)
    if exclusions:
        category = sorted(set(exclusions))[0]
        reasons = tuple(sorted(_EXCLUSION_REASON_BY_CATEGORY[item] for item in set(exclusions)))
        return _CategoryDecision(
            category, SemanticDiscoveryClass.EXCLUDE.value, 0.0,
            1.0 if metadata_categories else 0.5, 1.0, len(set(exclusions)) > 1,
            reasons,
        )

    strong = tokens.intersection(rules.strong_include_tokens)
    medium = tokens.intersection(rules.medium_include_tokens)
    generic = tokens.intersection(rules.generic_include_tokens)
    reasons = []
    if strong:
        semantic_score = 1.0
        reasons.append("BONEWEAVER_SEMANTIC_STRONG_INCLUDE_TOKEN")
    elif medium:
        semantic_score = 0.65
        reasons.append("BONEWEAVER_SEMANTIC_MEDIUM_INCLUDE_TOKEN")
    elif generic:
        semantic_score = 0.25
        reasons.append("BONEWEAVER_SEMANTIC_GENERIC_INCLUDE_TOKEN")
    else:
        semantic_score = 0.0

    matches = []
    for category, rule in sorted(rules.category_rules.items()):
        matched = tokens.intersection(rule.tokens)
        if matched:
            matches.append((len(matched), category, rule.maximum_class))
    for category in metadata_categories:
        if category not in _EXCLUSION_CATEGORIES:
            matches.append((1000, category, SemanticDiscoveryClass.AUTO_INCLUDE.value))
    maximum_class = SemanticDiscoveryClass.AMBIGUOUS.value
    category_conflict = False
    if matches:
        best_count = max(item[0] for item in matches)
        best = tuple(item for item in matches if item[0] == best_count)
        best_categories = tuple(sorted({item[1] for item in best}))
        if len(best_categories) == 1:
            category = best_categories[0]
            maximum_class = min(
                (item[2] for item in best if item[1] == category),
                key=lambda item: _CLASS_RANK[item],
            )
            reasons.append("BONEWEAVER_SEMANTIC_CATEGORY_MATCH")
        else:
            category = SecondaryBoneCategory.UNKNOWN_SECONDARY.value
            category_conflict = True
            reasons.append("BONEWEAVER_SEMANTIC_CATEGORY_CONFLICT")
    else:
        category = SecondaryBoneCategory.UNKNOWN_SECONDARY.value
    metadata_score = 1.0 if metadata_categories else (0.65 if metadata else 0.5)
    if metadata_categories:
        reasons.append("BONEWEAVER_SEMANTIC_METADATA_MATCH")
        semantic_score = max(semantic_score, 0.85)
    if not bool(getattr(state, "use_deform", True)):
        reasons.append("BONEWEAVER_SEMANTIC_NON_DEFORM_REVIEW")
        maximum_class = min(
            (maximum_class, SemanticDiscoveryClass.SUGGEST_INCLUDE.value),
            key=lambda item: _CLASS_RANK[item],
        )
    return _CategoryDecision(
        category, maximum_class, semantic_score, metadata_score, 0.0,
        category_conflict, tuple(sorted(set(reasons))),
    )


def _family_compatible(first, second):
    if first.semantic_stem != second.semantic_stem:
        return False
    if first.side is not None and second.side is not None and first.side != second.side:
        return False
    return (
        first.category == second.category
        or first.category == SecondaryBoneCategory.UNKNOWN_SECONDARY.value
        or second.category == SecondaryBoneCategory.UNKNOWN_SECONDARY.value
    )


def _sequence_index_from_rules(name, patterns):
    for token in reversed(tokenize_bone_name(name)):
        if any(pattern.fullmatch(token) for pattern in patterns):
            numeric = re.match(r"^(\d+)", token)
            if numeric is not None:
                return int(numeric.group(1))
    return extract_sequence_index(name)


def _weight_score(summary):
    if summary is None:
        return 0.0, ("BONEWEAVER_SEMANTIC_WEIGHT_EVIDENCE_UNAVAILABLE",)
    sample_count = max(0, int(_value(summary, "sample_count", 0) or 0))
    effective_sample_count = max(
        0.0, float(_value(summary, "effective_sample_count", 0.0) or 0.0),
    )
    total_weight = max(0.0, float(_value(summary, "total_statistical_weight", 0.0) or 0.0))
    confidence = max(0.0, min(1.0, float(_value(summary, "confidence", 0.0) or 0.0)))
    warnings = set(_value(summary, "warnings", ()) or ())
    if (
        sample_count < 3
        or effective_sample_count < 2.0
        or total_weight <= 0.0
        or "BONEWEAVER_INSUFFICIENT_WEIGHT_CLOUD" in warnings
    ):
        return 0.0, ("BONEWEAVER_SEMANTIC_NO_WEIGHT_SUPPORT",)
    sample_support = min(1.0, sample_count / 8.0)
    score = max(confidence, 0.70 * sample_support)
    return score, ("BONEWEAVER_SEMANTIC_WEIGHT_SUPPORT",)


def _cap_class(discovery_class, maximum_class):
    return min((discovery_class, maximum_class), key=lambda item: _CLASS_RANK[item])


def _classify_bone(decision, score, hierarchy_score, sequence_score, weight_score):
    if decision.exclusion_penalty > 0.0:
        return SemanticDiscoveryClass.EXCLUDE.value
    if decision.category_conflict:
        return SemanticDiscoveryClass.AMBIGUOUS.value
    if (
        score >= 0.80
        and decision.semantic_score >= 0.65
        and hierarchy_score >= 0.65
        and sequence_score >= 0.35
        and weight_score > 0.0
    ):
        result = SemanticDiscoveryClass.AUTO_INCLUDE.value
    elif (
        score >= 0.55
        and decision.semantic_score >= 0.25
        and (hierarchy_score >= 0.50 or weight_score >= 0.70)
    ):
        result = SemanticDiscoveryClass.SUGGEST_INCLUDE.value
    elif decision.semantic_score > 0.0 or weight_score >= 0.70:
        result = SemanticDiscoveryClass.AMBIGUOUS.value
    else:
        result = SemanticDiscoveryClass.EXCLUDE.value
    return _cap_class(result, decision.maximum_class)


def _build_bone_evidence(states, rules, weight_by_bone, metadata_by_bone):
    by_name = {state.name: state for state in states}
    uniform = detect_uniform_imported_display_length(states)
    main_patterns = tuple(re.compile(pattern) for pattern in rules.main_skeleton_patterns)
    sequence_patterns = tuple(re.compile(pattern) for pattern in rules.sequence_patterns)
    decisions = {
        state.name: _category_decision(
            state,
            rules,
            _metadata_for_bone(state, metadata_by_bone),
            main_patterns,
        )
        for state in states
    }
    identity = {
        state.name: SemanticBoneEvidence(
            bone_name=state.name,
            normalized_name=normalize_bone_name(state.name),
            semantic_stem=extract_semantic_stem(state.name),
            category=decisions[state.name].category,
            semantic_tokens=tokenize_bone_name(state.name),
            side=extract_side_marker(state.name),
            sequence_index=_sequence_index_from_rules(state.name, sequence_patterns),
            semantic_score=decisions[state.name].semantic_score,
            hierarchy_score=0.0,
            sequence_score=0.0,
            weight_score=0.0,
            geometry_mismatch_score=0.0,
            metadata_score=decisions[state.name].metadata_score,
            exclusion_penalty=decisions[state.name].exclusion_penalty,
            reason_codes=decisions[state.name].reason_codes,
            geometry_projection_need=GeometryProjectionNeed.UNRESOLVED.value,
            discovery_class=SemanticDiscoveryClass.EXCLUDE.value,
            discovery_score=0.0,
        )
        for state in states
    }
    evidence = []
    for state in states:
        base = identity[state.name]
        neighbors = []
        if state.parent_name in identity:
            neighbors.append(identity[state.parent_name])
        neighbors.extend(identity[name] for name in state.child_names if name in identity)
        compatible = tuple(item for item in neighbors if _family_compatible(base, item))
        hierarchy_score = 1.0 if compatible else (0.25 if neighbors else 0.0)
        reasons = set(base.reason_codes)
        if compatible:
            reasons.add("BONEWEAVER_SEMANTIC_HIERARCHY_CONTINUITY")
        consecutive = any(
            base.sequence_index is not None
            and item.sequence_index is not None
            and abs(base.sequence_index - item.sequence_index) == 1
            for item in compatible
        )
        missing_sequence = bool(compatible) and any(
            base.sequence_index is None or item.sequence_index is None
            for item in compatible
        )
        if consecutive:
            sequence_score = 1.0
            reasons.add("BONEWEAVER_SEMANTIC_SEQUENCE_CONTINUITY")
        elif missing_sequence:
            sequence_score = 0.65
            reasons.add("BONEWEAVER_SEMANTIC_SEQUENCE_IMPLICIT")
        elif compatible:
            sequence_score = 0.35
            reasons.add("BONEWEAVER_SEMANTIC_SEQUENCE_GAP")
        else:
            sequence_score = 0.25 if base.sequence_index is not None else 0.0
        weight_score, weight_reasons = _weight_score(weight_by_bone.get(state.name))
        reasons.update(weight_reasons)
        geometry = assess_geometry_projection(state, by_name, uniform)
        reasons.update(geometry.reason_codes)
        geometry_support = max(0.5, geometry.mismatch_score)
        score = max(0.0, min(1.0, (
            0.30 * base.semantic_score
            + 0.25 * hierarchy_score
            + 0.15 * sequence_score
            + 0.15 * weight_score
            + 0.10 * geometry_support
            + 0.05 * base.metadata_score
            - base.exclusion_penalty
        )))
        discovery_class = _classify_bone(
            decisions[state.name], score, hierarchy_score, sequence_score, weight_score,
        )
        if (
            discovery_class == SemanticDiscoveryClass.EXCLUDE.value
            and decisions[state.name].semantic_score <= 0.0
            and weight_score < 0.70
        ):
            reasons.add("BONEWEAVER_SEMANTIC_NO_SECONDARY_EVIDENCE")
        evidence.append(
            SemanticBoneEvidence(
                bone_name=base.bone_name,
                normalized_name=base.normalized_name,
                semantic_stem=base.semantic_stem,
                category=base.category,
                semantic_tokens=base.semantic_tokens,
                side=base.side,
                sequence_index=base.sequence_index,
                semantic_score=base.semantic_score,
                hierarchy_score=hierarchy_score,
                sequence_score=sequence_score,
                weight_score=weight_score,
                geometry_mismatch_score=geometry.mismatch_score,
                metadata_score=base.metadata_score,
                exclusion_penalty=base.exclusion_penalty,
                reason_codes=tuple(sorted(reasons)),
                geometry_projection_need=geometry.need,
                discovery_class=discovery_class,
                discovery_score=score,
            )
        )
    return tuple(sorted(evidence, key=lambda item: item.bone_name))


def _candidate_components(states, evidence_by_name):
    candidates = {
        name for name, item in evidence_by_name.items()
        if item.discovery_class != SemanticDiscoveryClass.EXCLUDE.value
        and item.category not in _EXCLUSION_CATEGORIES
    }
    adjacency = {name: set() for name in candidates}
    for state in states:
        if state.name not in candidates:
            continue
        for child_name in state.child_names:
            if (
                child_name in candidates
                and _family_compatible(evidence_by_name[state.name], evidence_by_name[child_name])
            ):
                adjacency[state.name].add(child_name)
                adjacency[child_name].add(state.name)
    remaining = set(candidates)
    components = []
    while remaining:
        root = min(remaining)
        remaining.remove(root)
        stack = [root]
        component = []
        while stack:
            name = stack.pop()
            component.append(name)
            for neighbor in sorted(adjacency[name], reverse=True):
                if neighbor in remaining:
                    remaining.remove(neighbor)
                    stack.append(neighbor)
        components.append(tuple(sorted(component)))
    return tuple(sorted(components))


def _chain_from_component(component, states_by_name, evidence_by_name, armature_fingerprint, rule_set_ids):
    component_set = set(component)
    roots = tuple(sorted(
        name for name in component
        if states_by_name[name].parent_name not in component_set
    ))
    if not roots:
        raise ValueError("semantic candidate component has no hierarchy root")
    root_name = roots[0]
    ordered_names = []
    visited = set()
    stack = [root_name]
    while stack:
        name = stack.pop()
        if name in visited:
            continue
        visited.add(name)
        ordered_names.append(name)
        children = sorted(
            (child for child in states_by_name[name].child_names if child in component_set),
            reverse=True,
        )
        stack.extend(children)
    ordered_names.extend(sorted(component_set - visited))
    component = tuple(ordered_names)
    branch_names = tuple(sorted(
        name for name in component
        if sum(child in component_set for child in states_by_name[name].child_names) > 1
    ))
    leaf_names = tuple(sorted(
        name for name in component
        if not any(child in component_set for child in states_by_name[name].child_names)
    ))
    categories = tuple(sorted({
        evidence_by_name[name].category
        for name in component
        if evidence_by_name[name].category != SecondaryBoneCategory.UNKNOWN_SECONDARY.value
    }))
    category = categories[0] if len(categories) == 1 else SecondaryBoneCategory.UNKNOWN_SECONDARY.value
    classes = {evidence_by_name[name].discovery_class for name in component}
    if SemanticDiscoveryClass.AMBIGUOUS.value in classes or len(categories) > 1:
        discovery_class = SemanticDiscoveryClass.AMBIGUOUS.value
    elif SemanticDiscoveryClass.SUGGEST_INCLUDE.value in classes:
        discovery_class = SemanticDiscoveryClass.SUGGEST_INCLUDE.value
    else:
        discovery_class = SemanticDiscoveryClass.AUTO_INCLUDE.value
    reasons = {
        code
        for name in component
        for code in evidence_by_name[name].reason_codes
    }
    reasons.add("BONEWEAVER_SEMANTIC_CHAIN_GROUPED")
    if branch_names:
        reasons.add("BONEWEAVER_SEMANTIC_BRANCH_REVIEW_REQUIRED")
        discovery_class = _cap_class(
            discovery_class, SemanticDiscoveryClass.SUGGEST_INCLUDE.value,
        )
    if len(categories) > 1 or len(roots) > 1:
        reasons.add("BONEWEAVER_SEMANTIC_CHAIN_CATEGORY_CONFLICT")
        discovery_class = SemanticDiscoveryClass.AMBIGUOUS.value
    score = min(evidence_by_name[name].discovery_score for name in component)
    discovery_id = sha256((
        SEMANTIC_DISCOVERY_ALGORITHM_VERSION,
        armature_fingerprint,
        tuple(rule_set_ids),
        root_name,
        component,
        category,
        discovery_class,
    ))
    return DiscoveredChain(
        discovery_id=discovery_id,
        root_bone_name=root_name,
        bone_names=component,
        category=category,
        discovery_class=discovery_class,
        discovery_score=score,
        needs_projection_count=sum(
            evidence_by_name[name].geometry_projection_need
            in {GeometryProjectionNeed.REQUIRED.value, GeometryProjectionNeed.RECOMMENDED.value}
            for name in component
        ),
        already_valid_count=sum(
            evidence_by_name[name].geometry_projection_need == GeometryProjectionNeed.NOT_REQUIRED.value
            for name in component
        ),
        branch_bone_names=branch_names,
        leaf_bone_names=leaf_names,
        reason_codes=tuple(sorted(reasons)),
    )


def build_semantic_discovery_plan(
    bone_states,
    *,
    armature_object_name="",
    armature_fingerprint="",
    merged_rules=None,
    weight_summaries=None,
    metadata_by_bone=None,
):
    """Build a deterministic RNA-free discovery plan from immutable snapshots."""
    states = tuple(sorted(tuple(bone_states), key=lambda item: item.name))
    if len({state.name for state in states}) != len(states):
        raise ValueError("bone states must have unique names")
    if metadata_by_bone is not None and not isinstance(metadata_by_bone, Mapping):
        raise TypeError("metadata_by_bone must be a mapping keyed by bone name")
    rules = merged_rules or merge_rule_sets((load_default_rule_set(),))
    fingerprint = str(armature_fingerprint) if armature_fingerprint else sha256(states)
    weight_by_bone = _index_weight_summaries(weight_summaries)
    evidence = _build_bone_evidence(
        states, rules, weight_by_bone, metadata_by_bone or {},
    )
    evidence_by_name = {item.bone_name: item for item in evidence}
    states_by_name = {state.name: state for state in states}
    chains = tuple(sorted(
        (
            _chain_from_component(
                component, states_by_name, evidence_by_name,
                fingerprint, rules.rule_set_ids,
            )
            for component in _candidate_components(states, evidence_by_name)
        ),
        key=lambda item: (item.root_bone_name, item.category, item.bone_names, item.discovery_id),
    ))
    return SemanticDiscoveryPlan(
        kind="SEMANTIC_DISCOVERY_PLAN",
        schema_version=SEMANTIC_DISCOVERY_SCHEMA_VERSION,
        algorithm_version=SEMANTIC_DISCOVERY_ALGORITHM_VERSION,
        armature_object_name=str(armature_object_name),
        armature_fingerprint=fingerprint,
        rule_set_ids=tuple(rules.rule_set_ids),
        chains=chains,
        bone_evidence=evidence,
        excluded_bones=tuple(
            item.bone_name for item in evidence
            if item.discovery_class == SemanticDiscoveryClass.EXCLUDE.value
        ),
        ambiguous_bones=tuple(
            item.bone_name for item in evidence
            if item.discovery_class == SemanticDiscoveryClass.AMBIGUOUS.value
        ),
    )
