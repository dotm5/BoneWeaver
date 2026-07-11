"""Immutable data captured during analysis."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ValidationIssue:
    severity: str
    code: str
    message_key: str
    message: str
    bone_names: tuple[str, ...] = ()
    object_names: tuple[str, ...] = ()
    node_ids: tuple[str, ...] = ()
    edge_ids: tuple[str, ...] = ()
    details: tuple[tuple[str, str], ...] = ()


@dataclass(frozen=True, slots=True)
class BoneState:
    name: str
    parent_name: str | None
    child_names: tuple[str, ...]
    head: tuple[float, float, float]
    tail: tuple[float, float, float]
    roll: float
    matrix_local: tuple[float, ...]
    local_x: tuple[float, float, float]
    local_y: tuple[float, float, float]
    local_z: tuple[float, float, float]
    use_connect: bool
    use_deform: bool
    inherit_scale: str
    use_inherit_rotation: bool
    bbone_segments: int
    is_socket: bool
    importer_metadata_flags: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class MeshBindingRef:
    object_name: str
    modifier_name: str


@dataclass(frozen=True, slots=True)
class PreflightResult:
    armature_object_name: str | None
    armature_data_name: str | None
    selected_bone_names: tuple[str, ...]
    mesh_names: tuple[str, ...]
    bone_states: tuple[BoneState, ...]
    issues: tuple[ValidationIssue, ...]
