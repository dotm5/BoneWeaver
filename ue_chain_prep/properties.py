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
    BranchResolutionMode,
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
    TipHelperUsage,
    ValidationToleranceMode,
    WeightIslandPolicy,
)
from .core.hierarchy_inspection import HierarchySelectionMode


PHYSICS_PROFILE_ITEMS = (
    (PhysicsProfile.BONEX_ROTATION_CHAIN.value, "BoneX · 稳定旋转链", ""),
    (PhysicsProfile.BONEX_TRANSLATION_ALLOWED.value, "BoneX · 允许平移", ""),
    (PhysicsProfile.WIGGLE2_ROTATION_CHAIN.value, "Wiggle · 稳定旋转链", ""),
    (PhysicsProfile.WIGGLE2_STRETCH_CHAIN.value, "Wiggle · 可伸缩链", ""),
    (PhysicsProfile.GEOMETRY_ONLY.value, "仅整理骨骼链", ""),
    (
        PhysicsProfile.VISUAL_CHAIN_CLEANUP.value,
        "主体骨视觉整理",
        "仅在不保留原 UE 动画时显式使用；分叉必须手动指定",
    ),
)
TIP_HELPER_USAGE_ITEMS = (
    (
        TipHelperUsage.REFERENCE_ONLY.value,
        "仅作为方向参考（推荐）",
        "不转换末端提示骨自身",
    ),
    (
        TipHelperUsage.INCLUDE_AS_PHYSICS_TERMINAL.value,
        "显式转换为物理末端",
        "仅限主体骨视觉整理，且 Helper 不得有排除子骨",
    ),
)


def _algorithm_setting_changed(_settings, context) -> None:
    runtime = getattr(getattr(context, "window_manager", None), "uecp_runtime", None)
    if runtime is None or not runtime.plan_id:
        return
    from .controllers.preview import PreviewController
    PreviewController.disable(context)
    if runtime.state == PlanState.ANALYZED.value:
        runtime.state = PlanState.STALE.value
    runtime.last_error = "UECP_SETTINGS_CHANGED_AFTER_ANALYZE"


def _preview_setting_changed(settings, context) -> None:
    from .controllers.preview import PreviewController
    runtime = getattr(getattr(context, "window_manager", None), "uecp_runtime", None)
    if runtime is not None and runtime.plan_id:
        from .core.runtime_store import get_plan, has_plan
        from .ui.draw import build_plan_cache
        if has_plan(runtime.plan_id):
            PreviewController.rebuild(context, build_plan_cache(get_plan(runtime.plan_id), settings))
            return
    PreviewController.tag_redraw(context)


def _hierarchy_overlay_setting_changed(_runtime, context) -> None:
    from .controllers.hierarchy_overlay import HierarchyOverlayController
    HierarchyOverlayController.sync_options(context)


class UECP_PG_TerminalOverride(bpy.types.PropertyGroup):
    armature_data_name: StringProperty(default="")
    armature_structural_fingerprint: StringProperty(default="")
    bone_name: StringProperty(name="Bone")
    chain_id: StringProperty(default="")
    mode: EnumProperty(items=enum_items(OverrideMode), default=OverrideMode.NONE.value)
    reference_object: PointerProperty(type=bpy.types.Object)
    direction: FloatVectorProperty(size=3, default=(0.0, 1.0, 0.0), subtype="DIRECTION")
    length: FloatProperty(default=0.0, min=0.0)
    mesh_object_name: StringProperty()
    vertex_index: IntProperty(default=-1, min=-1)
    enabled: BoolProperty(default=True)


class UECP_PG_BranchOverride(bpy.types.PropertyGroup):
    armature_data_name: StringProperty(default="")
    armature_structural_fingerprint: StringProperty(default="")
    branch_bone_name: StringProperty(default="")
    selected_child_name: StringProperty(default="")
    enabled: BoolProperty(default=True)


class UECP_PG_Settings(bpy.types.PropertyGroup):
    scope_mode: EnumProperty(items=enum_items(ScopeMode), default=ScopeMode.SELECTED_BONES.value, update=_algorithm_setting_changed)
    mesh_scope: EnumProperty(items=enum_items(MeshScope), default=MeshScope.ALL_ASSOCIATED_MESHES.value, update=_algorithm_setting_changed)
    physics_profile: EnumProperty(items=PHYSICS_PROFILE_ITEMS, default=PhysicsProfile.BONEX_ROTATION_CHAIN.value, update=_algorithm_setting_changed)
    tip_helper_usage: EnumProperty(
        items=TIP_HELPER_USAGE_ITEMS,
        default=TipHelperUsage.REFERENCE_ONLY.value,
        update=_algorithm_setting_changed,
    )
    branch_resolution_mode: EnumProperty(
        items=enum_items(BranchResolutionMode),
        default=BranchResolutionMode.AUTO_MAIN_PATH.value,
        update=_algorithm_setting_changed,
    )
    terminal_mode: EnumProperty(items=enum_items(TerminalMode), default=TerminalMode.AUTO_HYBRID.value, update=_algorithm_setting_changed)
    bone_forward_axis: EnumProperty(items=enum_items(BoneForwardAxis), default=BoneForwardAxis.AUTO.value, update=_algorithm_setting_changed)
    tip_length_mode: EnumProperty(items=enum_items(TipLengthMode), default=TipLengthMode.AUTO_EVIDENCE.value, update=_algorithm_setting_changed)
    absolute_tip_length: FloatProperty(default=0.0, min=0.0, update=_algorithm_setting_changed)
    roll_mode: EnumProperty(items=enum_items(RollMode), default=RollMode.MINIMAL_TWIST.value, update=_algorithm_setting_changed)
    radial_reference_mode: EnumProperty(items=enum_items(RadialReferenceMode), default=RadialReferenceMode.ARMATURE_ORIGIN.value, update=_algorithm_setting_changed)
    radial_reference_object: PointerProperty(type=bpy.types.Object, update=_algorithm_setting_changed)
    radial_reference_bone: StringProperty(default="", update=_algorithm_setting_changed)
    minimum_weight: FloatProperty(default=0.02, min=0.0, max=1.0, update=_algorithm_setting_changed)
    weight_exponent: FloatProperty(default=2.0, min=0.25, max=8.0, update=_algorithm_setting_changed)
    use_vertex_area_weight: BoolProperty(default=True, update=_algorithm_setting_changed)
    exclusivity_mode: EnumProperty(items=enum_items(ExclusivityMode), default=ExclusivityMode.CHAIN_NORMALIZED.value, update=_algorithm_setting_changed)
    weight_island_policy: EnumProperty(
        items=enum_items(WeightIslandPolicy),
        default=WeightIslandPolicy.DOMINANT_COMPONENT.value,
        update=_algorithm_setting_changed,
    )
    terminal_percentile: FloatProperty(default=0.90, min=0.50, max=0.999, update=_algorithm_setting_changed)
    minimum_candidate_score: FloatProperty(default=0.62, min=0.0, max=1.0, update=_algorithm_setting_changed)
    candidate_minimum_margin: FloatProperty(default=0.08, min=0.0, max=1.0, update=_algorithm_setting_changed)
    candidate_direction_merge_angle_degrees: FloatProperty(default=7.5, min=0.0, max=45.0, update=_algorithm_setting_changed)
    minimum_confidence: FloatProperty(default=0.70, min=0.0, max=1.0, update=_algorithm_setting_changed)
    medium_confidence: FloatProperty(default=0.50, min=0.0, max=1.0, update=_algorithm_setting_changed)
    minimum_length_ratio: FloatProperty(default=0.25, min=0.01, max=2.0, update=_algorithm_setting_changed)
    maximum_length_ratio: FloatProperty(default=2.0, min=0.1, max=10.0, update=_algorithm_setting_changed)
    maximum_auto_bend_degrees: FloatProperty(default=115.0, min=0.0, max=180.0, update=_algorithm_setting_changed)
    parallel_transport_weight: FloatProperty(default=0.65, min=0.0, max=1.0, update=_algorithm_setting_changed)
    old_axis_weight: FloatProperty(default=0.35, min=0.0, max=1.0, update=_algorithm_setting_changed)
    enable_segment_sampling_hints: BoolProperty(default=True, update=_algorithm_setting_changed)
    long_segment_ratio_warning: FloatProperty(default=2.5, min=1.0, max=20.0, update=_algorithm_setting_changed)
    virtual_preview_subdivision_max: IntProperty(default=8, min=0, max=50, update=_algorithm_setting_changed)
    strict_whole_armature_pose: BoolProperty(default=True, update=_algorithm_setting_changed)
    validate_full_mesh: BoolProperty(default=True, update=_algorithm_setting_changed)
    create_role_collections: BoolProperty(
        default=False,
        description="Deprecated compatibility field; Apply never writes Bone Collections",
    )
    preview_show_joint_graph: BoolProperty(default=True, update=_preview_setting_changed)
    preview_show_virtual_tips: BoolProperty(default=True, update=_preview_setting_changed)
    preview_show_candidate_axes: BoolProperty(default=True, update=_preview_setting_changed)
    preview_show_old_axes: BoolProperty(default=True, update=_preview_setting_changed)
    preview_show_new_axes: BoolProperty(default=True, update=_preview_setting_changed)
    preview_show_weight_centroid: BoolProperty(default=True, update=_preview_setting_changed)
    preview_axis_scale: FloatProperty(default=0.1, min=1.0e-9, update=_preview_setting_changed)
    validation_tolerance_mode: EnumProperty(
        items=enum_items(ValidationToleranceMode),
        default=ValidationToleranceMode.AUTO_PRODUCTION.value,
        update=_algorithm_setting_changed,
    )
    position_epsilon_factor: FloatProperty(default=1.0e-7, min=1.0e-10, max=1.0e-3, update=_algorithm_setting_changed)
    last_export_directory: StringProperty(default="", subtype="DIR_PATH")
    semantic_source_adapter_rule_path: StringProperty(
        default="", subtype="FILE_PATH",
        description="Optional Source Adapter semantic rule set",
        update=_algorithm_setting_changed,
    )
    semantic_game_rule_path: StringProperty(
        default="", subtype="FILE_PATH",
        description="Optional game semantic rule set",
        update=_algorithm_setting_changed,
    )
    semantic_user_rule_path: StringProperty(
        default="", subtype="FILE_PATH",
        description="Optional user semantic rule set with highest precedence",
        update=_algorithm_setting_changed,
    )
    terminal_overrides: CollectionProperty(type=UECP_PG_TerminalOverride)
    branch_overrides: CollectionProperty(type=UECP_PG_BranchOverride)


class UECP_PG_Runtime(bpy.types.PropertyGroup):
    state: EnumProperty(items=enum_items(PlanState), default=PlanState.IDLE.value)
    plan_id: StringProperty(default="")
    plan_fingerprint: StringProperty(default="")
    plan_summary: StringProperty(default="")
    snapshot_id: StringProperty(default="")
    snapshot_text_name: StringProperty(default="")
    snapshot_available: BoolProperty(default=False)
    issue_count_info: IntProperty(default=0, min=0)
    issue_count_warning: IntProperty(default=0, min=0)
    issue_count_blocker: IntProperty(default=0, min=0)
    active_chain_index: IntProperty(default=0, min=0)
    active_proposal_index: IntProperty(default=0, min=0)
    active_issue_index: IntProperty(default=0, min=0)
    selection_signature: StringProperty(default="")
    settings_signature: StringProperty(default="")
    plan_bone_count: IntProperty(default=0, min=0)
    plan_chain_count: IntProperty(default=0, min=0)
    terminal_reliable_count: IntProperty(default=0, min=0)
    terminal_attention_count: IntProperty(default=0, min=0)
    details_loaded: BoolProperty(default=False)
    preview_enabled: BoolProperty(default=False)
    last_error: StringProperty(default="")
    generation: IntProperty(default=0, min=0)
    is_busy: BoolProperty(default=False)
    hierarchy_inspection_active: BoolProperty(default=False)
    hierarchy_scope_used: BoolProperty(default=False)
    hierarchy_inspection_id: StringProperty(default="")
    hierarchy_active_bone_name: StringProperty(default="")
    hierarchy_parent_context_name: StringProperty(default="")
    hierarchy_selection_mode: EnumProperty(
        items=enum_items(HierarchySelectionMode),
        default=HierarchySelectionMode.LINEAR_CHAIN.value,
    )
    hierarchy_armature_fingerprint: StringProperty(default="")
    hierarchy_source_filepath: StringProperty(default="")
    hierarchy_bone_count: IntProperty(default=0, min=0)
    hierarchy_branch_count: IntProperty(default=0, min=0)
    hierarchy_tip_helper_count: IntProperty(default=0, min=0)
    hierarchy_excluded_helper_count: IntProperty(default=0, min=0)
    hierarchy_overlay_enabled: BoolProperty(default=False)
    hierarchy_show_names: BoolProperty(default=True, update=_hierarchy_overlay_setting_changed)
    hierarchy_show_parent: BoolProperty(default=True, update=_hierarchy_overlay_setting_changed)
    hierarchy_show_side_branches: BoolProperty(default=True, update=_hierarchy_overlay_setting_changed)
    hierarchy_show_tip_helpers: BoolProperty(default=True, update=_hierarchy_overlay_setting_changed)
    hierarchy_branch_bone_name: StringProperty(default="")
    hierarchy_selected_child_name: StringProperty(default="")
    semantic_discovery_active: BoolProperty(default=False)
    semantic_scope_used: BoolProperty(default=False)
    semantic_discovery_plan_id: StringProperty(default="")
    semantic_armature_fingerprint: StringProperty(default="")
    semantic_source_filepath: StringProperty(default="")
    semantic_chain_count: IntProperty(default=0, min=0)
    semantic_confirmed_count: IntProperty(default=0, min=0)
    semantic_active_chain_index: IntProperty(default=0, min=0)


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
    bone_name: StringProperty()


class UECP_PG_SemanticChainItem(bpy.types.PropertyGroup):
    chain_id: StringProperty()
    root_name: StringProperty()
    category: StringProperty()
    discovery_class: StringProperty()
    discovery_score: FloatProperty(default=0.0, min=0.0, max=1.0)
    branch_count: IntProperty(default=0, min=0)
    reason_codes: StringProperty()
    confirmed: BoolProperty(default=False)


PROPERTY_CLASSES = (
    UECP_PG_TerminalOverride,
    UECP_PG_BranchOverride,
    UECP_PG_Settings,
    UECP_PG_Runtime,
    UECP_PG_ChainItem,
    UECP_PG_BoneProposalItem,
    UECP_PG_IssueItem,
    UECP_PG_SemanticChainItem,
)


def register_properties() -> None:
    bpy.types.Scene.uecp_settings = PointerProperty(type=UECP_PG_Settings)
    bpy.types.WindowManager.uecp_runtime = PointerProperty(type=UECP_PG_Runtime)
    bpy.types.WindowManager.uecp_chain_items = CollectionProperty(type=UECP_PG_ChainItem)
    bpy.types.WindowManager.uecp_proposal_items = CollectionProperty(type=UECP_PG_BoneProposalItem)
    bpy.types.WindowManager.uecp_issue_items = CollectionProperty(type=UECP_PG_IssueItem)
    bpy.types.WindowManager.uecp_semantic_chain_items = CollectionProperty(
        type=UECP_PG_SemanticChainItem,
    )
    from .core.snapshot_availability import discover_latest_restorable_snapshot
    latest_snapshot_id, latest_snapshot_name = discover_latest_restorable_snapshot()
    for window_manager in getattr(bpy.data, "window_managers", ()):
        runtime = window_manager.uecp_runtime
        runtime.state = PlanState.IDLE.value
        runtime.plan_id = ""
        runtime.plan_fingerprint = ""
        runtime.plan_summary = ""
        runtime.snapshot_id = latest_snapshot_id
        runtime.snapshot_text_name = latest_snapshot_name
        runtime.snapshot_available = bool(latest_snapshot_name)
        runtime.issue_count_info = 0
        runtime.issue_count_warning = 0
        runtime.issue_count_blocker = 0
        runtime.active_chain_index = 0
        runtime.active_proposal_index = 0
        runtime.active_issue_index = 0
        runtime.selection_signature = ""
        runtime.settings_signature = ""
        runtime.plan_bone_count = 0
        runtime.plan_chain_count = 0
        runtime.terminal_reliable_count = 0
        runtime.terminal_attention_count = 0
        runtime.details_loaded = False
        runtime.preview_enabled = False
        runtime.last_error = ""
        runtime.generation = 0
        runtime.is_busy = False
        runtime.hierarchy_inspection_active = False
        runtime.hierarchy_scope_used = False
        runtime.hierarchy_inspection_id = ""
        runtime.hierarchy_active_bone_name = ""
        runtime.hierarchy_parent_context_name = ""
        runtime.hierarchy_selection_mode = HierarchySelectionMode.LINEAR_CHAIN.value
        runtime.hierarchy_armature_fingerprint = ""
        runtime.hierarchy_source_filepath = ""
        runtime.hierarchy_bone_count = 0
        runtime.hierarchy_branch_count = 0
        runtime.hierarchy_tip_helper_count = 0
        runtime.hierarchy_excluded_helper_count = 0
        runtime.hierarchy_overlay_enabled = False
        runtime.hierarchy_show_names = True
        runtime.hierarchy_show_parent = True
        runtime.hierarchy_show_side_branches = True
        runtime.hierarchy_show_tip_helpers = True
        runtime.hierarchy_branch_bone_name = ""
        runtime.hierarchy_selected_child_name = ""
        runtime.semantic_discovery_active = False
        runtime.semantic_scope_used = False
        runtime.semantic_discovery_plan_id = ""
        runtime.semantic_armature_fingerprint = ""
        runtime.semantic_source_filepath = ""
        runtime.semantic_chain_count = 0
        runtime.semantic_confirmed_count = 0
        runtime.semantic_active_chain_index = 0


def unregister_properties() -> None:
    for name in (
        "uecp_semantic_chain_items",
        "uecp_issue_items",
        "uecp_proposal_items",
        "uecp_chain_items",
    ):
        if hasattr(bpy.types.WindowManager, name):
            delattr(bpy.types.WindowManager, name)
    if hasattr(bpy.types.WindowManager, "uecp_runtime"):
        del bpy.types.WindowManager.uecp_runtime
    if hasattr(bpy.types.Scene, "uecp_settings"):
        del bpy.types.Scene.uecp_settings
