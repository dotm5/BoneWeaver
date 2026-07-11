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
class WeightComponentStats:
    vertex_count: int
    statistical_weight: float
    centroid: tuple[float, float, float]
    principal_axis: tuple[float, float, float] | None


@dataclass(frozen=True, slots=True)
class PerMeshWeightCloudStats:
    mesh_name: str
    component_count: int
    components: tuple[WeightComponentStats, ...]
    dominant_weight_ratio: float
    selected_centroid: tuple[float, float, float] | None
    selected_principal_axis: tuple[float, float, float] | None
    selected_statistical_weight: float


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
    per_mesh_clouds: tuple[PerMeshWeightCloudStats, ...] = ()
    component_strategy: str = "DOMINANT_COMPONENT"


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
class TerminalCandidateCluster:
    cluster_id: str
    direction: tuple[float, float, float]
    score: float
    support_bonus: float
    member_candidate_ids: tuple[str, ...]
    evidence_kinds: tuple[str, ...]


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
    resolution_class: str = "UNRESOLVED"
    candidate_clusters: tuple[TerminalCandidateCluster, ...] = ()


@dataclass(frozen=True, slots=True)
class BranchCandidate:
    child_bone_name: str
    immediate_edge_length: float
    longest_downstream_path_length: float
    branch_depth: int
    deform_weight_mass: float
    weighted_vertex_count: int
    direction_continuity: float
    naming_continuity: float
    penalties: tuple[tuple[str, float], ...]
    score: float


@dataclass(frozen=True, slots=True)
class BranchResolution:
    branch_bone_name: str
    mode: str
    candidates: tuple[BranchCandidate, ...]
    selected_child_name: str | None
    side_child_names: tuple[str, ...]
    score: float
    margin: float
    result: str
    requires_confirmation: bool
    issue_codes: tuple[str, ...]


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
    proposal_id: str = ""


@dataclass(frozen=True, slots=True)
class BoneMutationRecord:
    bone_name: str
    proposal_id: str
    chain_id: str
    role: str
    tail_changed: bool
    roll_changed: bool
    use_connect_changed: bool
    old_tail: tuple[float, float, float]
    new_tail: tuple[float, float, float]
    old_roll: float
    new_roll: float
    old_use_connect: bool
    new_use_connect: bool
    reason_codes: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class TopologyProjectionLedger:
    selected_bone_count: int
    selected_hierarchy_edge_count: int
    linear_edge_count: int
    branch_node_count: int
    branch_edge_count: int
    resolved_branch_count: int
    unresolved_branch_count: int
    external_child_edge_count: int
    virtual_tip_count: int
    proposal_count: int
    mutation_record_count: int
    skipped_by_design_count: int


@dataclass(frozen=True, slots=True)
class SegmentSamplingHint:
    edge_id: str
    segment_length: float
    reference_length: float
    length_ratio: float
    suggested_virtual_subdivisions: int
    severity: str
    message_key: str


@dataclass(frozen=True, slots=True)
class MeshBindingState:
    object_name: str
    data_name: str
    vertex_count: int
    polygon_count: int
    armature_modifier_names: tuple[str, ...]
    selected_armature_modifier_name: str
    object_matrix_world: tuple[float, ...]
    mesh_to_armature_matrix: tuple[float, ...]
    vertex_group_names: tuple[str, ...]
    vertex_group_digest: str
    modifier_digest: str
    base_mesh_digest: str


@dataclass(frozen=True, slots=True)
class ConversionPlan:
    kind: str
    schema_version: str
    algorithm_version: str
    addon_version: str
    plan_id: str
    source_fingerprint: str
    settings_fingerprint: str
    armature_object_name: str
    armature_data_name: str
    profile: str
    scoring_profile: tuple[tuple[str, float], ...]
    mesh_states: tuple[MeshBindingState, ...]
    bone_states: tuple[BoneState, ...]
    physics_graph: PhysicsGraph
    weight_clouds: tuple[WeightCloudStats, ...]
    terminal_solutions: tuple[TerminalSolution, ...]
    proposals: tuple[BoneProposal, ...]
    segment_sampling_hints: tuple[SegmentSamplingHint, ...]
    issues: tuple[ValidationIssue, ...]
    branch_resolutions: tuple[BranchResolution, ...] = ()
    topology_ledger: TopologyProjectionLedger | None = None


@dataclass(frozen=True, slots=True)
class TransactionResult:
    success: bool
    rolled_back: bool
    snapshot_id: str
    snapshot_text_name: str
    error: str | None
    mutation_records: tuple[BoneMutationRecord, ...] = ()
    topology_ledger: TopologyProjectionLedger | None = None
    apply_time: float = 0.0
    validation_time: float = 0.0
