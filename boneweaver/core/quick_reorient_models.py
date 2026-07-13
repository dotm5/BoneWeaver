"""Immutable contracts for whole-armature automatic reorientation."""

from __future__ import annotations

from dataclasses import dataclass

from .models import ValidationIssue


@dataclass(frozen=True, slots=True)
class QuickBoneState:
    bone_name: str
    parent_name: str | None
    child_names: tuple[str, ...]
    head: tuple[float, float, float]
    tail: tuple[float, float, float]
    roll: float
    matrix: tuple[float, ...]
    length: float
    use_connect: bool
    use_deform: bool
    source_metadata_flags: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class QuickSourceMetadata:
    orig_loc: tuple[float, float, float] | None = None
    orig_quat: tuple[float, float, float, float] | None = None
    reorient_direction: tuple[float, float, float] | None = None
    is_socket: bool = False
    collection_names: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class QuickBoneProposal:
    bone_name: str
    source: str
    target_direction_local: tuple[float, float, float] | None
    target_tail: tuple[float, float, float]
    target_roll_reference: tuple[float, float, float]
    target_length: float
    target_use_connect: bool
    component_id: str | None
    branch_boundary: bool
    skipped: bool
    skip_reason: str | None


@dataclass(frozen=True, slots=True)
class LinkedChainComponent:
    component_id: str
    bone_names: tuple[str, ...]
    root_bone_name: str
    leaf_bone_name: str
    parent_branch_name: str | None
    contains_weightless_leaf: bool


@dataclass(frozen=True, slots=True)
class QuickReorientPlan:
    kind: str
    schema_version: str
    algorithm_version: str
    addon_version: str
    plan_id: str
    source_fingerprint: str
    source_adapter: str
    armature_object_name: str
    armature_data_name: str
    already_reoriented: bool
    already_normalized: bool
    connect_linear_chains: bool
    bone_states: tuple[QuickBoneState, ...]
    proposals: tuple[QuickBoneProposal, ...]
    linked_components: tuple[LinkedChainComponent, ...]
    issues: tuple[ValidationIssue, ...]


@dataclass(frozen=True, slots=True)
class QuickTransactionResult:
    success: bool
    rolled_back: bool
    snapshot_id: str
    snapshot_text_name: str
    mutation_count: int
    connected_edge_count: int
    validation_issues: tuple[str, ...]
    error: str | None
