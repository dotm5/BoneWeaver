"""Read-only semantic chain discovery and geometry evidence.

The module intentionally works on immutable bone snapshots. Blender integration is
limited to adapters at the public entry points; scoring never edits RNA data.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
import statistics

from .semantic_models import GeometryProjectionNeed


SEMANTIC_DISCOVERY_SCHEMA_VERSION = "1.0.0"
SEMANTIC_DISCOVERY_ALGORITHM_VERSION = "semantic-discovery-v0.1.1"


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
        reasons = ("UECP_SEMANTIC_BRANCH_DETECTED",) if len(children) > 1 else ()
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
            ("UECP_SEMANTIC_ALREADY_CONTINUOUS",),
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
    reasons = ["UECP_SEMANTIC_TAIL_CHILD_MISMATCH"]
    if uniform.detected:
        reasons.append("UECP_SEMANTIC_UNIFORM_DISPLAY_LENGTH")
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
