"""Blender RNA properties for persistent settings and transient UI state."""

import bpy
from bpy.props import (
    BoolProperty,
    CollectionProperty,
    EnumProperty,
    FloatProperty,
    FloatVectorProperty,
    IntProperty,
    PointerProperty,
    StringProperty,
)

from .constants import enum_items
from .contracts import (
    BoneForwardAxis,
    ExclusivityMode,
    MeshScope,
    OverrideMode,
    PhysicsProfile,
    PlanState,
    RadialReferenceMode,
    RollMode,
    ScopeMode,
    TerminalMode,
    TipLengthMode,
)


class UECP_PG_TerminalOverride(bpy.types.PropertyGroup):
    bone_name: StringProperty(name="Bone")
    mode: EnumProperty(items=enum_items(OverrideMode), default=OverrideMode.NONE.value)
    reference_object: PointerProperty(type=bpy.types.Object)
    direction: FloatVectorProperty(size=3, default=(0.0, 1.0, 0.0), subtype="DIRECTION")
    length: FloatProperty(default=0.0, min=0.0)
    mesh_object_name: StringProperty()
    vertex_index: IntProperty(default=-1, min=-1)
    enabled: BoolProperty(default=True)


class UECP_PG_Settings(bpy.types.PropertyGroup):
    scope_mode: EnumProperty(items=enum_items(ScopeMode), default=ScopeMode.SELECTED_BONES.value)
    mesh_scope: EnumProperty(items=enum_items(MeshScope), default=MeshScope.ALL_ASSOCIATED_MESHES.value)
    physics_profile: EnumProperty(items=enum_items(PhysicsProfile), default=PhysicsProfile.BONEX_ROTATION_CHAIN.value)
    terminal_mode: EnumProperty(items=enum_items(TerminalMode), default=TerminalMode.AUTO_HYBRID.value)
    bone_forward_axis: EnumProperty(items=enum_items(BoneForwardAxis), default=BoneForwardAxis.AUTO.value)
    tip_length_mode: EnumProperty(items=enum_items(TipLengthMode), default=TipLengthMode.AUTO_EVIDENCE.value)
    absolute_tip_length: FloatProperty(default=0.0, min=0.0)
    roll_mode: EnumProperty(items=enum_items(RollMode), default=RollMode.MINIMAL_TWIST.value)
    radial_reference_mode: EnumProperty(items=enum_items(RadialReferenceMode), default=RadialReferenceMode.ARMATURE_ORIGIN.value)
    radial_reference_object: PointerProperty(type=bpy.types.Object)
    radial_reference_bone: StringProperty(default="")
    minimum_weight: FloatProperty(default=0.02, min=0.0, max=1.0)
    weight_exponent: FloatProperty(default=2.0, min=0.25, max=8.0)
    use_vertex_area_weight: BoolProperty(default=True)
    exclusivity_mode: EnumProperty(items=enum_items(ExclusivityMode), default=ExclusivityMode.CHAIN_NORMALIZED.value)
    terminal_percentile: FloatProperty(default=0.90, min=0.50, max=0.999)
    minimum_candidate_score: FloatProperty(default=0.62, min=0.0, max=1.0)
    candidate_minimum_margin: FloatProperty(default=0.08, min=0.0, max=1.0)
    minimum_confidence: FloatProperty(default=0.70, min=0.0, max=1.0)
    medium_confidence: FloatProperty(default=0.50, min=0.0, max=1.0)
    minimum_length_ratio: FloatProperty(default=0.25, min=0.01, max=2.0)
    maximum_length_ratio: FloatProperty(default=2.0, min=0.1, max=10.0)
    maximum_auto_bend_degrees: FloatProperty(default=115.0, min=0.0, max=180.0)
    parallel_transport_weight: FloatProperty(default=0.65, min=0.0, max=1.0)
    old_axis_weight: FloatProperty(default=0.35, min=0.0, max=1.0)
    enable_segment_sampling_hints: BoolProperty(default=True)
    long_segment_ratio_warning: FloatProperty(default=2.5, min=1.0, max=20.0)
    virtual_preview_subdivision_max: IntProperty(default=8, min=0, max=50)
    strict_whole_armature_pose: BoolProperty(default=True)
    validate_full_mesh: BoolProperty(default=True)
    create_role_collections: BoolProperty(default=False)
    preview_show_joint_graph: BoolProperty(default=True)
    preview_show_virtual_tips: BoolProperty(default=True)
    preview_show_candidate_axes: BoolProperty(default=True)
    preview_show_old_axes: BoolProperty(default=True)
    preview_show_new_axes: BoolProperty(default=True)
    preview_show_weight_centroid: BoolProperty(default=True)
    preview_axis_scale: FloatProperty(default=0.1, min=1.0e-9)
    position_epsilon_factor: FloatProperty(default=1.0e-7, min=1.0e-10, max=1.0e-3)
    last_export_directory: StringProperty(default="", subtype="DIR_PATH")
    terminal_overrides: CollectionProperty(type=UECP_PG_TerminalOverride)


class UECP_PG_Runtime(bpy.types.PropertyGroup):
    state: EnumProperty(items=enum_items(PlanState), default=PlanState.IDLE.value)
    plan_id: StringProperty(default="")
    plan_fingerprint: StringProperty(default="")
    plan_summary: StringProperty(default="")
    snapshot_id: StringProperty(default="")
    snapshot_text_name: StringProperty(default="")
    issue_count_info: IntProperty(default=0, min=0)
    issue_count_warning: IntProperty(default=0, min=0)
    issue_count_blocker: IntProperty(default=0, min=0)
    active_chain_index: IntProperty(default=0, min=0)
    active_proposal_index: IntProperty(default=0, min=0)
    preview_enabled: BoolProperty(default=False)
    last_error: StringProperty(default="")
    generation: IntProperty(default=0, min=0)
    is_busy: BoolProperty(default=False)


class UECP_PG_ChainItem(bpy.types.PropertyGroup):
    chain_id: StringProperty()
    root_name: StringProperty()
    leaf_name: StringProperty()
    resolved: BoolProperty(default=False)


class UECP_PG_BoneProposalItem(bpy.types.PropertyGroup):
    bone_name: StringProperty()
    role: StringProperty()
    confidence: FloatProperty(default=0.0, min=0.0, max=1.0)


class UECP_PG_IssueItem(bpy.types.PropertyGroup):
    severity: StringProperty()
    code: StringProperty()
    message: StringProperty()


PROPERTY_CLASSES = (
    UECP_PG_TerminalOverride,
    UECP_PG_Settings,
    UECP_PG_Runtime,
    UECP_PG_ChainItem,
    UECP_PG_BoneProposalItem,
    UECP_PG_IssueItem,
)


def register_properties() -> None:
    bpy.types.Scene.uecp_settings = PointerProperty(type=UECP_PG_Settings)
    bpy.types.WindowManager.uecp_runtime = PointerProperty(type=UECP_PG_Runtime)
    for window_manager in bpy.data.window_managers:
        runtime = window_manager.uecp_runtime
        runtime.state = PlanState.IDLE.value
        runtime.plan_id = ""
        runtime.plan_fingerprint = ""
        runtime.plan_summary = ""
        runtime.snapshot_id = ""
        runtime.snapshot_text_name = ""
        runtime.issue_count_info = 0
        runtime.issue_count_warning = 0
        runtime.issue_count_blocker = 0
        runtime.active_chain_index = 0
        runtime.active_proposal_index = 0
        runtime.preview_enabled = False
        runtime.last_error = ""
        runtime.generation = 0
        runtime.is_busy = False


def unregister_properties() -> None:
    if hasattr(bpy.types.WindowManager, "uecp_runtime"):
        del bpy.types.WindowManager.uecp_runtime
    if hasattr(bpy.types.Scene, "uecp_settings"):
        del bpy.types.Scene.uecp_settings
