"""Deterministic terminal evidence generation, scoring, and ambiguity handling."""

from __future__ import annotations

import math

from .canonical import sha256
from .models import BoneState, TerminalCandidate, TerminalCandidateScore, TerminalSolution, WeightCloudStats


def _normalize(vector):
    length = math.sqrt(sum(value * value for value in vector))
    return tuple(float(value / length) for value in vector) if length > 1.0e-12 else None


def _dot(a, b):
    return sum(a[i] * b[i] for i in range(3))


def _candidate(state, kind, label, direction, length, cloud, parent_direction, *, raw_length=None, maximum_auto_bend_degrees=180.0, explicit_axis=False, reference_length=None):
    direction = _normalize(direction)
    if direction is None:
        return None
    centroid_direction = _normalize(tuple(cloud.centroid[i] - state.head[i] for i in range(3))) if cloud.centroid else None
    mesh_support = max(0.0, _dot(direction, centroid_direction)) if centroid_direction else 0.0
    if cloud.principal_axis:
        mesh_support = max(mesh_support, max(0.0, _dot(direction, cloud.principal_axis)))
    continuity = 0.5 * (1.0 + _dot(direction, parent_direction)) if parent_direction else 0.5
    if cloud.cloud_class == "LINEAR":
        suitability = 1.0 if kind == "WEIGHT_PRINCIPAL_AXIS" else (0.7 if kind == "IMPORTED_AXIS" else 0.6)
    elif cloud.cloud_class == "PLANAR":
        suitability = 1.0 if kind in {"WEIGHT_CENTROID", "WEIGHT_PLANAR_BLEND"} else 0.5
    elif cloud.cloud_class == "ISOTROPIC":
        suitability = 1.0 if kind == "PARENT_TANGENT" else 0.3
    else:
        suitability = 1.0 if kind == "PARENT_TANGENT" else (0.5 if kind == "IMPORTED_AXIS" else 0.2)
    axis_prior = (1.0 if explicit_axis else 0.5) if kind == "IMPORTED_AXIS" else 0.0
    ratio = length / max(reference_length or length, 1.0e-12)
    length_score = max(0.0, 1.0 - 0.5 * abs(math.log(max(ratio, 1.0e-12), 2.0)))
    penalties = 0.0
    if parent_direction:
        bend = math.degrees(math.acos(max(-1.0, min(1.0, _dot(direction, parent_direction)))))
        if bend > maximum_auto_bend_degrees:
            penalties = min(0.5, (bend - maximum_auto_bend_degrees) / 180.0)
    total = max(0.0, 0.40 * mesh_support + 0.25 * continuity + 0.15 * suitability + 0.10 * axis_prior + 0.10 * length_score - penalties)
    score = TerminalCandidateScore(mesh_support, continuity, suitability, axis_prior, length_score, penalties, total)
    tail = tuple(state.head[i] + direction[i] * length for i in range(3))
    candidate_id = sha256((state.name, kind, label, direction, length))
    return TerminalCandidate(candidate_id, kind, label, direction, raw_length or length, length, tail, score, (), ())


def authoritative_solution(bone_name, head, tail, *, source, kind):
    direction_vector = tuple(float(tail[index] - head[index]) for index in range(3))
    length = math.sqrt(sum(value * value for value in direction_vector))
    direction = _normalize(direction_vector)
    if direction is None:
        return TerminalSolution(bone_name, "UNRESOLVED", None, (), None, tuple(head), (0.0,0.0,0.0), 0.0, 0.0, 0.0, True, ("UECP_VIRTUAL_TIP_INVALID",))
    score = TerminalCandidateScore(1.0, 1.0, 1.0, 1.0, 1.0, 0.0, 1.0)
    candidate_id = sha256((bone_name, kind, source, direction, length))
    candidate = TerminalCandidate(candidate_id, kind, None, direction, length, length, tuple(float(value) for value in tail), score, (source,), ())
    return TerminalSolution(bone_name, source, candidate_id, (candidate,), None, candidate.tail, direction, length, 1.0, 1.0, False, (source,))


def generate_candidates(
    state: BoneState, cloud: WeightCloudStats, *, parent_direction, reference_length,
    length_override=None, minimum_length_ratio=0.25, maximum_length_ratio=2.0,
    maximum_auto_bend_degrees=115.0, explicit_axis_label=None,
):
    parent_direction = _normalize(parent_direction) if parent_direction is not None else None
    raw_length = length_override or cloud.length_percentile or float(reference_length) or math.dist(state.head, state.tail)
    reference = max(float(reference_length) or raw_length, 1.0e-7)
    length = max(min(raw_length, maximum_length_ratio * reference), minimum_length_ratio * reference, 1.0e-7)
    axes = (
        ("X_POSITIVE", state.local_x), ("X_NEGATIVE", tuple(-v for v in state.local_x)),
        ("Y_POSITIVE", state.local_y), ("Y_NEGATIVE", tuple(-v for v in state.local_y)),
        ("Z_POSITIVE", state.local_z), ("Z_NEGATIVE", tuple(-v for v in state.local_z)),
    )
    common = {"raw_length": raw_length, "maximum_auto_bend_degrees": maximum_auto_bend_degrees, "reference_length": reference}
    candidates = [_candidate(state, "IMPORTED_AXIS", label, axis, length, cloud, parent_direction, explicit_axis=label == explicit_axis_label, **common) for label, axis in axes]
    if cloud.principal_axis:
        candidates.append(_candidate(state, "WEIGHT_PRINCIPAL_AXIS", None, cloud.principal_axis, length, cloud, parent_direction, **common))
    if cloud.centroid:
        candidates.append(_candidate(state, "WEIGHT_CENTROID", None, tuple(cloud.centroid[i] - state.head[i] for i in range(3)), length, cloud, parent_direction, **common))
    if cloud.cloud_class == "PLANAR" and cloud.centroid and parent_direction:
        centroid_direction = _normalize(tuple(cloud.centroid[i] - state.head[i] for i in range(3)))
        blend = tuple(0.55 * centroid_direction[i] + 0.45 * parent_direction[i] for i in range(3))
        candidates.append(_candidate(state, "WEIGHT_PLANAR_BLEND", None, blend, length, cloud, parent_direction, **common))
    if parent_direction:
        candidates.append(_candidate(state, "PARENT_TANGENT", None, parent_direction, length, cloud, parent_direction, **common))
    original = tuple(state.tail[i] - state.head[i] for i in range(3))
    candidates.append(_candidate(state, "ORIGINAL_DISPLAY_AXIS", None, original, length, cloud, parent_direction, **common))
    return tuple(candidate for candidate in candidates if candidate is not None)


def select_candidate(bone_name, candidates, *, minimum_score=0.62, minimum_margin=0.08, minimum_confidence=0.5):
    priority = {"MANUAL": 0, "DIRECT_CHILD": 1, "WEIGHT_PRINCIPAL_AXIS": 2, "WEIGHT_PLANAR_BLEND": 3, "WEIGHT_CENTROID": 4, "PARENT_TANGENT": 5, "IMPORTED_AXIS": 6, "ORIGINAL_DISPLAY_AXIS": 7}
    ranked = tuple(sorted(candidates, key=lambda item: (-item.score.total, priority.get(item.kind, 99), item.axis_label or "", item.candidate_id)))
    if not ranked:
        return TerminalSolution(bone_name, "UNRESOLVED", None, (), None, (0.0,0.0,0.0), (0.0,0.0,0.0), 0.0, 0.0, 0.0, True, ("UECP_TERMINAL_CANDIDATE_SCORE_TOO_LOW",))
    top = ranked[0]
    distinct_runner_up = next(
        (candidate for candidate in ranked[1:] if _dot(top.direction, candidate.direction) < 1.0 - 1.0e-9),
        None,
    )
    margin = top.score.total - distinct_runner_up.score.total if distinct_runner_up else top.score.total
    evidence = []
    if top.score.total < minimum_score:
        evidence.append("UECP_TERMINAL_CANDIDATE_SCORE_TOO_LOW")
    if distinct_runner_up and margin < minimum_margin:
        evidence.append("UECP_TERMINAL_CANDIDATE_AMBIGUOUS")
    confidence = min(1.0, 0.75 * top.score.total + 0.25 * min(1.0, margin / max(minimum_margin, 1.0e-12)))
    requires = bool(evidence) or confidence < minimum_confidence
    return TerminalSolution(bone_name, "HYBRID_CANDIDATE_SCORE", top.candidate_id, ranked, None, top.tail, top.direction, top.clamped_length, confidence, max(0.0, margin), requires, tuple(evidence))
