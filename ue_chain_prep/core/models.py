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


@dataclass(frozen=True, slots=True)
class PhysicsNode:
    node_id: str
    kind: str
    bone_name: str | None
    joint_position: tuple[float, float, float]
    rest_rotation: tuple[float, float, float, float] | None
    local_x: tuple[float, float, float] | None
    local_y: tuple[float, float, float] | None
    local_z: tuple[float, float, float] | None
    parent_node_id: str | None
    child_node_ids: tuple[str, ...]
    is_kinematic: bool
    source: str


@dataclass(frozen=True, slots=True)
class PhysicsEdge:
    edge_id: str
    kind: str
    parent_node_id: str
    child_node_id: str
    rest_vector: tuple[float, float, float]
    rest_length: float
    source: str


@dataclass(frozen=True, slots=True)
class PhysicsChain:
    chain_id: str
    node_ids: tuple[str, ...]
    edge_ids: tuple[str, ...]
    real_bone_names: tuple[str, ...]
    root_node_id: str
    terminal_node_id: str
    has_virtual_tip: bool
    branch_parent_node_id: str | None
    resolved: bool
    issue_codes: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class PhysicsGraph:
    graph_id: str
    node_ids: tuple[str, ...]
    edge_ids: tuple[str, ...]
    nodes: tuple[PhysicsNode, ...]
    edges: tuple[PhysicsEdge, ...]
    chains: tuple[PhysicsChain, ...]
    issue_codes: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class WeightCloudStats:
    bone_name: str
    mesh_names: tuple[str, ...]
    sample_count: int
    effective_sample_count: float
    total_statistical_weight: float
    centroid: tuple[float, float, float] | None
    principal_axis: tuple[float, float, float] | None
    eigenvalues: tuple[float, float, float] | None
    linearity: float
    planarity: float
    sphericity: float
    positive_projection_fraction: float
    centroid_distance_ratio: float
    direction_agreement: float
    length_percentile: float | None
    cloud_class: str
    confidence: float
    warnings: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class TerminalCandidateScore:
    mesh_support: float
    chain_continuity: float
    cloud_shape_suitability: float
    imported_axis_prior: float
    length_plausibility: float
    penalties: float
    total: float


@dataclass(frozen=True, slots=True)
class TerminalCandidate:
    candidate_id: str
    kind: str
    axis_label: str | None
    direction: tuple[float, float, float]
    raw_length: float
    clamped_length: float
    tail: tuple[float, float, float]
    score: TerminalCandidateScore
    evidence: tuple[str, ...]
    issue_codes: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class TerminalSolution:
    bone_name: str
    source: str
    selected_candidate_id: str | None
    candidates: tuple[TerminalCandidate, ...]
    virtual_tip_node_id: str | None
    tail: tuple[float, float, float]
    direction: tuple[float, float, float]
    length: float
    confidence: float
    score_margin: float
    requires_confirmation: bool
    evidence: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class BoneProposal:
    bone_name: str
    chain_id: str
    source_edge_id: str
    role: str
    original_head: tuple[float, float, float]
    original_tail: tuple[float, float, float]
    original_roll: float
    proposed_tail: tuple[float, float, float]
    proposed_roll_reference_z: tuple[float, float, float]
    final_use_connect: bool
    terminal_source: str
    confidence: float
    issue_codes: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class SegmentSamplingHint:
    edge_id: str
    segment_length: float
    reference_length: float
    length_ratio: float
    suggested_virtual_subdivisions: int
    severity: str
    message_key: str
