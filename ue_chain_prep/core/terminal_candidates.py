"""Deterministic terminal evidence generation, scoring, and ambiguity handling."""

from __future__ import annotations

import math
import statistics

from .canonical import sha256
from .models import (
    BoneState,
    TerminalCandidate,
    TerminalCandidateCluster,
    TerminalCandidateScore,
    TerminalSolution,
    WeightCloudStats,
)


def _normalize(vector):
    length = math.sqrt(sum(value * value for value in vector))
    return tuple(float(value / length) for value in vector) if length > 1.0e-12 else None


def _dot(a, b):
    return sum(a[i] * b[i] for i in range(3))


_CANDIDATE_PRIORITY = {
    "MANUAL": 0,
    "DIRECT_CHILD": 1,
    "WEIGHT_PRINCIPAL_AXIS": 2,
    "WEIGHT_PLANAR_BLEND": 3,
    "WEIGHT_CENTROID": 4,
    "PARENT_TANGENT": 5,
    "IMPORTED_AXIS": 6,
    "ORIGINAL_DISPLAY_AXIS": 7,
}


def _candidate_sort_key(item):
    return (
        -item.score.total,
        _CANDIDATE_PRIORITY.get(item.kind, 99),
        item.axis_label or "",
        item.candidate_id,
    )


def cluster_candidates(candidates, *, merge_angle_degrees=7.5):
    """Merge near-parallel evidence before ambiguity margins are calculated."""
    ranked = tuple(sorted(candidates, key=_candidate_sort_key))
    cosine_limit = math.cos(math.radians(max(0.0, float(merge_angle_degrees))))
    groups = []
    for candidate in ranked:
        target = next(
            (
                members for members in groups
                if any(_dot(candidate.direction, member.direction) >= cosine_limit for member in members)
            ),
            None,
        )
        if target is None:
            groups.append([candidate])
        else:
            target.append(candidate)
    clusters = []
    for members in groups:
        ordered = tuple(sorted(members, key=_candidate_sort_key))
        weights = tuple(max(0.05, member.score.total) for member in ordered)
        combined = tuple(
            sum(member.direction[index] * weight for member, weight in zip(ordered, weights))
            for index in range(3)
        )
        direction = _normalize(combined) or ordered[0].direction
        kinds = tuple(sorted({member.kind for member in ordered}))
        support_bonus = min(0.12, 0.04 * max(0, len(kinds) - 1))
        score = min(1.0, max(member.score.total for member in ordered) + support_bonus)
        member_ids = tuple(sorted(member.candidate_id for member in ordered))
        cluster_id = sha256((member_ids, float(merge_angle_degrees)))
        clusters.append(
            TerminalCandidateCluster(
                cluster_id, direction, score, support_bonus, member_ids, kinds,
            )
        )
    return tuple(sorted(clusters, key=lambda cluster: (-cluster.score, cluster.cluster_id)))


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
    metadata_reliable = bool({str(flag).lower() for flag in state.importer_metadata_flags}.intersection(
        {"orig_loc", "orig_quat", "post_quat"}
    ))
    axis_prior = (1.0 if explicit_axis else (0.5 if metadata_reliable else 0.1)) if kind == "IMPORTED_AXIS" else 0.0
    ratio = length / max(reference_length or length, 1.0e-12)
    length_score = max(0.0, 1.0 - 0.5 * abs(math.log(max(ratio, 1.0e-12), 2.0)))
    penalties = 0.0
    if parent_direction:
        bend = math.degrees(math.acos(max(-1.0, min(1.0, _dot(direction, parent_direction)))))
        if bend > maximum_auto_bend_degrees:
            penalties = min(0.5, (bend - maximum_auto_bend_degrees) / 180.0)
    if kind == "IMPORTED_AXIS" and not explicit_axis and not metadata_reliable and mesh_support < 0.5 and continuity < 0.75:
        penalties += 0.1
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
        return TerminalSolution(bone_name, "UNRESOLVED", None, (), None, tuple(head), (0.0,0.0,0.0), 0.0, 0.0, 0.0, True, ("UECP_VIRTUAL_TIP_INVALID",), "UNRESOLVED")
    score = TerminalCandidateScore(1.0, 1.0, 1.0, 1.0, 1.0, 0.0, 1.0)
    candidate_id = sha256((bone_name, kind, source, direction, length))
    candidate = TerminalCandidate(candidate_id, kind, None, direction, length, length, tuple(float(value) for value in tail), score, (source,), ())
    resolution_class = "MANUAL" if source == "MANUAL_OVERRIDE" or kind == "MANUAL" else "AUTO_CONFIDENT"
    return TerminalSolution(bone_name, source, candidate_id, (candidate,), None, candidate.tail, direction, length, 1.0, 1.0, False, (source,), resolution_class)


def _unresolved_fallback(state, code):
    return TerminalSolution(
        state.name, "UNRESOLVED", None, (), None, tuple(state.head),
        (0.0, 0.0, 0.0), 0.0, 0.0, 0.0, True, (code,), "UNRESOLVED",
    )


def safe_parent_chain_fallback(
    state: BoneState,
    bone_states,
    *,
    epsilon=1.0e-7,
    unresolved_branch=False,
    reliable_weight_direction=None,
    reliable_weight_confidence=0.0,
    reliable_confidence_threshold=0.7,
):
    """Build the deterministic low-confidence leaf fallback from upstream heads."""
    by_name = {bone.name: bone for bone in bone_states}
    if unresolved_branch:
        return _unresolved_fallback(state, "UECP_BRANCH_AMBIGUOUS")
    flags = {str(flag).upper() for flag in state.importer_metadata_flags}
    normalized_name = state.name.lower()
    if state.is_socket or flags.intersection({"SOCKET", "IK", "CONTROL", "HELPER"}) or any(
        token in normalized_name for token in ("socket", "_ik", "ctrl", "control")
    ):
        return _unresolved_fallback(state, "UECP_TERMINAL_FALLBACK_INELIGIBLE")
    parent = by_name.get(state.parent_name)
    if parent is None:
        return _unresolved_fallback(state, "UECP_TERMINAL_PARENT_UNAVAILABLE")
    incoming = tuple(float(state.head[index] - parent.head[index]) for index in range(3))
    incoming_length = math.sqrt(sum(value * value for value in incoming))
    if not math.isfinite(incoming_length) or incoming_length <= epsilon:
        return _unresolved_fallback(state, "UECP_COINCIDENT_HELPER")
    direction = tuple(value / incoming_length for value in incoming)
    reliable = _normalize(reliable_weight_direction) if reliable_weight_direction is not None else None
    if (
        reliable is not None
        and reliable_weight_confidence >= reliable_confidence_threshold
        and _dot(direction, reliable) <= -0.5
    ):
        return _unresolved_fallback(state, "UECP_WEIGHT_DIRECTION_CONFLICT")
    lengths = []
    child = state
    current_parent = parent
    while current_parent is not None and len(lengths) < 3:
        segment = math.dist(child.head, current_parent.head)
        if math.isfinite(segment) and segment > epsilon:
            lengths.append(segment)
        child = current_parent
        current_parent = by_name.get(current_parent.parent_name)
    if not lengths:
        return _unresolved_fallback(state, "UECP_TERMINAL_LENGTH_EVIDENCE_INVALID")
    length = float(statistics.median(lengths))
    tail = tuple(float(state.head[index] + direction[index] * length) for index in range(3))
    score = TerminalCandidateScore(0.0, 1.0, 1.0, 0.0, 1.0, 0.0, 0.65)
    candidate_id = sha256((state.name, "PARENT_CHAIN_EXTRAPOLATION", direction, length))
    candidate = TerminalCandidate(
        candidate_id, "PARENT_TANGENT", None, direction, length, length, tail,
        score, ("PARENT_CHAIN_EXTRAPOLATION",), (),
    )
    return TerminalSolution(
        state.name, "PARENT_CHAIN_EXTRAPOLATION", candidate_id, (candidate,), None,
        tail, direction, length, 0.65, 1.0, True,
        ("UECP_TERMINAL_SAFE_FALLBACK_USED",), "AUTO_SAFE_FALLBACK",
    )


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


def select_candidate(
    bone_name,
    candidates,
    *,
    minimum_score=0.62,
    minimum_margin=0.08,
    minimum_confidence=0.5,
    candidate_direction_merge_angle_degrees=7.5,
):
    ranked = tuple(sorted(candidates, key=_candidate_sort_key))
    if not ranked:
        return TerminalSolution(bone_name, "UNRESOLVED", None, (), None, (0.0,0.0,0.0), (0.0,0.0,0.0), 0.0, 0.0, 0.0, True, ("UECP_TERMINAL_CANDIDATE_SCORE_TOO_LOW",), "UNRESOLVED")
    clusters = cluster_candidates(
        ranked, merge_angle_degrees=candidate_direction_merge_angle_degrees,
    )
    top_cluster = clusters[0]
    runner_up = clusters[1] if len(clusters) > 1 else None
    top = next(candidate for candidate in ranked if candidate.candidate_id in top_cluster.member_candidate_ids)
    margin = top_cluster.score - runner_up.score if runner_up else top_cluster.score
    evidence = []
    if top_cluster.score < minimum_score:
        evidence.append("UECP_TERMINAL_CANDIDATE_SCORE_TOO_LOW")
    if runner_up and margin < minimum_margin:
        evidence.append("UECP_TERMINAL_CANDIDATE_AMBIGUOUS")
    confidence = min(1.0, 0.75 * top_cluster.score + 0.25 * min(1.0, margin / max(minimum_margin, 1.0e-12)))
    requires = bool(evidence) or confidence < minimum_confidence
    resolution_class = "UNRESOLVED" if requires else "AUTO_CONFIDENT"
    tail = tuple(top.tail[index] - top.direction[index] * top.clamped_length + top_cluster.direction[index] * top.clamped_length for index in range(3))
    return TerminalSolution(
        bone_name, "HYBRID_CANDIDATE_SCORE", top.candidate_id, ranked, None,
        tail, top_cluster.direction, top.clamped_length, confidence,
        max(0.0, margin), requires, tuple(evidence), resolution_class, clusters,
    )
