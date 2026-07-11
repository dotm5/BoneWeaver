"""Deterministic projection of a graph branch onto one Blender bone tail."""

from __future__ import annotations

import math
import re
from dataclasses import dataclass

from .models import BranchCandidate, BranchResolution


@dataclass(frozen=True, slots=True)
class BranchResolutionDefaults:
    longest_path_weight: float = 0.50
    deform_weight_mass_weight: float = 0.20
    direction_continuity_weight: float = 0.15
    branch_depth_weight: float = 0.10
    naming_continuity_weight: float = 0.05
    high_score: float = 0.65
    high_margin: float = 0.15
    medium_score: float = 0.55
    medium_margin: float = 0.08
    no_deform_weight_penalty: float = 0.30
    socket_penalty: float = 0.35
    control_penalty: float = 0.35
    invalid_path_penalty: float = 0.30
    short_decorative_penalty: float = 0.15


BRANCH_RESOLUTION_DEFAULTS = BranchResolutionDefaults()


def _distance(first, second):
    return math.sqrt(sum((float(first[index]) - float(second[index])) ** 2 for index in range(3)))


def _normalize(vector):
    length = math.sqrt(sum(float(value) * float(value) for value in vector))
    return tuple(float(value) / length for value in vector) if length > 1.0e-12 else None


def _dot(first, second):
    return sum(first[index] * second[index] for index in range(3))


def _subtree_names(root_name, by_name):
    result = []
    stack = [root_name]
    while stack:
        name = stack.pop()
        if name in result or name not in by_name:
            continue
        result.append(name)
        stack.extend(sorted((child for child in by_name[name].child_names if child in by_name), reverse=True))
    return tuple(result)


def _longest_path_and_depth(parent_name, child_name, by_name):
    if parent_name not in by_name or child_name not in by_name:
        return 0.0, 0
    immediate = _distance(by_name[parent_name].head, by_name[child_name].head)
    descendants = tuple(child for child in by_name[child_name].child_names if child in by_name)
    if not descendants:
        return immediate, 1
    continuations = tuple(_longest_path_and_depth(child_name, descendant, by_name) for descendant in descendants)
    best_length, best_depth = max(continuations, key=lambda item: (item[0], item[1]))
    return immediate + best_length, 1 + best_depth


def _naming_continuity(parent_name, child_name):
    parent_match = re.match(r"^(.*?)(\d+)$", parent_name)
    child_match = re.match(r"^(.*?)(\d+)$", child_name)
    if parent_match and child_match and parent_match.group(1) == child_match.group(1):
        if int(child_match.group(2)) == int(parent_match.group(2)) + 1:
            return 1.0
        return 0.5
    common = 0
    for first, second in zip(parent_name, child_name):
        if first != second:
            break
        common += 1
    return min(0.5, common / max(len(parent_name), len(child_name), 1))


def resolve_branch(
    branch_bone_name,
    bone_states,
    *,
    deform_weight_mass=None,
    weighted_vertex_count=None,
    mode="AUTO_MAIN_PATH",
    manual_selected_child=None,
    defaults=BRANCH_RESOLUTION_DEFAULTS,
):
    by_name = {bone.name: bone for bone in bone_states}
    branch = by_name[branch_bone_name]
    child_names = tuple(sorted(child for child in branch.child_names if child in by_name))
    mass_by_name = deform_weight_mass or {}
    count_by_name = weighted_vertex_count or {}
    if len(child_names) < 2:
        return BranchResolution(branch_bone_name, mode, (), None, (), 0.0, 0.0, "NOT_A_BRANCH", False, ())
    parent = by_name.get(branch.parent_name)
    if parent is not None:
        incoming = _normalize(tuple(branch.head[index] - parent.head[index] for index in range(3)))
    else:
        incoming = _normalize(branch.local_y)
    raw = []
    maximum_immediate = max(_distance(branch.head, by_name[name].head) for name in child_names)
    for child_name in child_names:
        child = by_name[child_name]
        immediate = _distance(branch.head, child.head)
        path_length, depth = _longest_path_and_depth(branch_bone_name, child_name, by_name)
        subtree = _subtree_names(child_name, by_name)
        mass = sum(float(mass_by_name.get(name, 0.0)) for name in subtree)
        vertex_count = sum(int(count_by_name.get(name, 0)) for name in subtree)
        outgoing = _normalize(tuple(child.head[index] - branch.head[index] for index in range(3)))
        continuity = 0.5 * (1.0 + _dot(incoming, outgoing)) if incoming and outgoing else 0.0
        penalties = []
        flags = {str(flag).upper() for flag in child.importer_metadata_flags}
        lowered = child.name.lower()
        if child.is_socket or "SOCKET" in flags or "socket" in lowered:
            penalties.append(("SOCKET", defaults.socket_penalty))
        if flags.intersection({"IK", "CONTROL"}) or any(token in lowered for token in ("_ik", "ctrl", "control")):
            penalties.append(("IK_OR_CONTROL", defaults.control_penalty))
        if path_length <= 1.0e-7 or depth <= 0:
            penalties.append(("NO_VALID_DOWNSTREAM_SEGMENT", defaults.invalid_path_penalty))
        if maximum_immediate > 1.0e-7 and immediate < maximum_immediate * 0.1 and depth <= 1:
            penalties.append(("EXTREMELY_SHORT_DECORATIVE_CHAIN", defaults.short_decorative_penalty))
        raw.append((child_name, immediate, path_length, depth, mass, vertex_count, continuity, _naming_continuity(branch.name, child_name), tuple(penalties)))
    max_path = max(item[2] for item in raw) or 1.0
    max_mass = max(item[4] for item in raw)
    max_depth = max(item[3] for item in raw) or 1
    candidates = []
    for child_name, immediate, path_length, depth, mass, vertex_count, continuity, naming, penalties in raw:
        if max_mass > 0.0 and mass <= 0.0:
            penalties = penalties + (("NO_DEFORM_WEIGHT", defaults.no_deform_weight_penalty),)
        normalized_path = path_length / max_path
        normalized_mass = mass / max_mass if max_mass > 0.0 else 0.0
        normalized_depth = depth / max_depth
        if mode == "LONGEST_PATH_ONLY":
            score = normalized_path - sum(value for _, value in penalties)
        elif mode == "DIRECTION_CONTINUITY":
            score = continuity - sum(value for _, value in penalties)
        else:
            score = (
                defaults.longest_path_weight * normalized_path
                + defaults.deform_weight_mass_weight * normalized_mass
                + defaults.direction_continuity_weight * continuity
                + defaults.branch_depth_weight * normalized_depth
                + defaults.naming_continuity_weight * naming
                - sum(value for _, value in penalties)
            )
        candidates.append(
            BranchCandidate(
                child_name, immediate, path_length, depth, mass, vertex_count,
                continuity, naming, penalties, max(0.0, min(1.0, score)),
            )
        )
    ranked = tuple(sorted(candidates, key=lambda item: (-item.score, item.child_bone_name)))
    if mode == "KEEP_ORIGINAL":
        return BranchResolution(branch_bone_name, mode, ranked, None, child_names, 0.0, 0.0, "KEEP_ORIGINAL", False, ())
    if mode == "MANUAL_ONLY":
        if manual_selected_child in child_names:
            return BranchResolution(
                branch_bone_name, mode, ranked, manual_selected_child,
                tuple(name for name in child_names if name != manual_selected_child),
                1.0, 1.0, "MANUAL", False, (),
            )
        return BranchResolution(branch_bone_name, mode, ranked, None, child_names, 0.0, 0.0, "AMBIGUOUS", True, ("UECP_BRANCH_AMBIGUOUS",))
    winner = ranked[0]
    runner_up = ranked[1]
    margin = max(0.0, winner.score - runner_up.score)
    if winner.score >= defaults.high_score and margin >= defaults.high_margin:
        result = "HIGH"
        requires_confirmation = False
    elif winner.score >= defaults.medium_score and margin >= defaults.medium_margin:
        result = "MEDIUM"
        requires_confirmation = True
    else:
        return BranchResolution(branch_bone_name, mode, ranked, None, child_names, winner.score, margin, "AMBIGUOUS", True, ("UECP_BRANCH_AMBIGUOUS",))
    return BranchResolution(
        branch_bone_name, mode, ranked, winner.child_bone_name,
        tuple(name for name in child_names if name != winner.child_bone_name),
        winner.score, margin, result, requires_confirmation, (),
    )
