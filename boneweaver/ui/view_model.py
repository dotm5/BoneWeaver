"""Pure user-facing workflow state derived from Blender/runtime summaries."""

from __future__ import annotations

from dataclasses import dataclass

from ..contracts import OPERATOR_IDS, PlanAvailability, PlanState, WorkflowStage
from ..core.fingerprint import settings_fingerprint
from ..core.runtime_store import has_plan
from ..controllers.selection import SelectionController
from .draw import is_preview_enabled
from ..core.snapshot_availability import snapshot_text_is_restorable


@dataclass(frozen=True, slots=True)
class ActionView:
    operator_id: str
    label: str
    icon: str = "NONE"
    enabled: bool = True
    disabled_reason: str = ""
    is_primary: bool = False


@dataclass(frozen=True, slots=True)
class TargetSummaryView:
    armature_name: str | None
    selected_bone_count: int
    chain_count: int | None
    profile_label: str
    source_kind: str


@dataclass(frozen=True, slots=True)
class ResultSummaryView:
    status_kind: str
    title: str
    description: str
    bone_count: int = 0
    chain_count: int = 0
    terminal_reliable_count: int = 0
    terminal_attention_count: int = 0
    blocker_count: int = 0
    warning_count: int = 0


@dataclass(frozen=True, slots=True)
class PanelViewState:
    workflow_stage: str
    target: TargetSummaryView
    result: ResultSummaryView | None
    primary_action: ActionView | None
    secondary_actions: tuple[ActionView, ...] = ()
    notice_lines: tuple[str, ...] = ()
    preview_active: bool = False
    plan_available: bool = False
    snapshot_available: bool = False


@dataclass(frozen=True, slots=True)
class BlenderContextSummary:
    armature_name: str | None
    selected_bone_count: int
    chain_count: int | None
    profile_label: str
    source_kind: str
    selection_signature: str


@dataclass(frozen=True, slots=True)
class RuntimeSummary:
    state: str = PlanState.IDLE.value
    plan_id: str = ""
    selection_signature: str = ""
    settings_signature: str = ""
    bone_count: int = 0
    chain_count: int = 0
    terminal_reliable_count: int = 0
    terminal_attention_count: int = 0
    blocker_count: int = 0
    warning_count: int = 0
    preview_active: bool = False
    is_busy: bool = False
    last_error: str = ""


@dataclass(frozen=True, slots=True)
class SnapshotSummary:
    available: bool = False
    text_name: str = ""
    bone_count: int = 0


@dataclass(frozen=True, slots=True)
class AdvancedPanelView:
    show_absolute_length: bool
    show_radial_reference: bool
    show_parallel_transport: bool
    override_count: int


@dataclass(frozen=True, slots=True)
class DetailsPanelView:
    active_data: object
    window_manager: object
    chain_count: int
    bone_count: int
    blocker_count: int
    warning_count: int
    details_loaded: bool
    has_chains: bool
    has_issues: bool
    has_proposals: bool
    active_issue_index: int
    selected_issue_bone: str


@dataclass(frozen=True, slots=True)
class RecoveryPanelView:
    snapshot_available: bool
    validation_available: bool


@dataclass(frozen=True, slots=True)
class DeveloperPanelView:
    plan_state: str
    plan_id: str
    source_fingerprint: str
    last_error: str


@dataclass(frozen=True, slots=True)
class QuickReorientView:
    button_enabled: bool
    state: str
    summary: str
    source: str
    mode_label: str
    automation_detail: str
    processed_bones: int
    total_bones: int
    component_count: int
    connected_edges: int
    blocker_count: int
    warning_count: int
    restore_enabled: bool


def _action(key: str, label: str, icon: str, *, enabled: bool = True,
            reason: str = "", primary: bool = False) -> ActionView:
    return ActionView(OPERATOR_IDS[key], label, icon, enabled, reason, primary)


def _result(stage: WorkflowStage, title: str, description: str,
            runtime: RuntimeSummary) -> ResultSummaryView:
    return ResultSummaryView(
        stage.value, title, description, runtime.bone_count, runtime.chain_count,
        runtime.terminal_reliable_count, runtime.terminal_attention_count,
        runtime.blocker_count, runtime.warning_count,
    )


def derive_panel_view_state(
    blender_context_summary: BlenderContextSummary,
    runtime_summary: RuntimeSummary,
    plan_availability: PlanAvailability | str,
    current_selection_signature: str,
    current_settings_signature: str,
    snapshot_summary: SnapshotSummary,
) -> PanelViewState:
    """Map technical session facts to one deterministic user workflow stage."""
    target = TargetSummaryView(
        blender_context_summary.armature_name,
        blender_context_summary.selected_bone_count,
        blender_context_summary.chain_count,
        blender_context_summary.profile_label,
        blender_context_summary.source_kind,
    )
    available = PlanAvailability(plan_availability) == PlanAvailability.AVAILABLE
    common = dict(target=target, preview_active=runtime_summary.preview_active,
                  plan_available=available, snapshot_available=snapshot_summary.available)

    if not blender_context_summary.armature_name:
        return PanelViewState(WorkflowStage.NO_CONTEXT.value, result=None, primary_action=None,
                              notice_lines=("未找到可用骨架，请选中骨架或带骨架修改器的模型。",), **common)

    if runtime_summary.is_busy:
        stage = WorkflowStage.APPLYING if runtime_summary.state == PlanState.APPLYING.value else WorkflowStage.ANALYZING
        label = "正在应用转换" if stage == WorkflowStage.APPLYING else "正在检查"
        action = _action("check_and_preview", label, "TIME", enabled=False,
                         reason="当前操作完成后才能继续。", primary=True)
        return PanelViewState(stage.value, result=_result(stage, label, "请稍候。", runtime_summary),
                              primary_action=action, **common)

    if runtime_summary.state == PlanState.ERROR.value:
        rollback_failed = runtime_summary.last_error == "BONEWEAVER_ROLLBACK_FAILED"
        stage = WorkflowStage.ROLLBACK_FAILED if rollback_failed else WorkflowStage.ERROR
        title = "自动恢复失败" if rollback_failed else "转换未完成"
        description = ("请立即撤销或关闭文件而不保存。" if rollback_failed
                       else "请查看错误详情后重置本次会话。")
        return PanelViewState(stage.value, result=_result(stage, title, description, runtime_summary),
                              primary_action=_action("clear_runtime", "重置本次会话", "FILE_REFRESH", primary=True), **common)

    has_plan_identity = bool(runtime_summary.plan_id)
    if has_plan_identity and PlanAvailability(plan_availability) == PlanAvailability.MISSING:
        stage = WorkflowStage.PLAN_LOST
        return PanelViewState(stage.value, result=_result(stage, "分析结果已不可用", "请重新检查。", runtime_summary),
                              primary_action=_action("check_and_preview", "重新检查", "FILE_REFRESH", primary=True), **common)

    if runtime_summary.state in {PlanState.RESTORABLE.value, PlanState.APPLIED.value}:
        stage = WorkflowStage.APPLIED
        secondary = ((_action("restore_snapshot", "恢复转换前状态", "LOOP_BACK"),)
                     if snapshot_summary.available else ())
        return PanelViewState(stage.value,
                              result=_result(stage, "转换完成", "骨骼已更新并通过安全验证。", runtime_summary),
                              primary_action=_action("check_and_preview", "检查另一条骨骼链", "VIEWZOOM", primary=True),
                              secondary_actions=secondary, **common)

    if available and runtime_summary.settings_signature and runtime_summary.settings_signature != current_settings_signature:
        stage = WorkflowStage.STALE_SETTINGS
        return PanelViewState(stage.value, result=_result(stage, "设置已经改变", "请重新检查后再应用。", runtime_summary),
                              primary_action=_action("check_and_preview", "重新检查", "FILE_REFRESH", primary=True), **common)
    if available and runtime_summary.selection_signature and runtime_summary.selection_signature != current_selection_signature:
        stage = WorkflowStage.STALE_SELECTION
        return PanelViewState(stage.value, result=_result(stage, "当前选择已经改变", "上次结果不再针对当前骨骼选择。", runtime_summary),
                              primary_action=_action("check_and_preview", "重新检查", "FILE_REFRESH", primary=True), **common)
    if available and runtime_summary.state == PlanState.STALE.value:
        stage = WorkflowStage.STALE_SELECTION
        return PanelViewState(stage.value, result=_result(stage, "模型内容已经改变", "请重新检查后再应用。", runtime_summary),
                              primary_action=_action("check_and_preview", "重新检查", "FILE_REFRESH", primary=True), **common)

    if available and runtime_summary.blocker_count:
        stage = WorkflowStage.BLOCKED
        return PanelViewState(stage.value, result=_result(stage, "暂时不能转换", "请先处理阻断问题。", runtime_summary),
                              primary_action=_action("check_and_preview", "重新检查", "FILE_REFRESH", primary=True), **common)
    if available:
        stage = WorkflowStage.NEEDS_ATTENTION if runtime_summary.warning_count else WorkflowStage.READY_TO_APPLY
        title = "可以转换，但建议先确认" if runtime_summary.warning_count else "可以转换"
        secondary = (_action("preview_toggle", "显示/隐藏预览", "HIDE_OFF"),
                     _action("check_and_preview", "重新检查", "FILE_REFRESH"))
        return PanelViewState(stage.value, result=_result(stage, title, "安全检查已完成。", runtime_summary),
                              primary_action=_action("apply", "应用转换", "CHECKMARK", primary=True),
                              secondary_actions=secondary, **common)

    stage = WorkflowStage.READY_TO_ANALYZE
    return PanelViewState(stage.value, result=None,
                          primary_action=_action("check_and_preview", "检查并预览", "VIEWZOOM", primary=True),
                          notice_lines=("将检查骨骼链方向、末端位置、权重和安全状态，不会修改模型。",), **common)


_PROFILE_LABELS = {
    "BONEX_ROTATION_CHAIN": "BoneX · 稳定旋转链",
    "BONEX_TRANSLATION_ALLOWED": "BoneX · 允许平移",
    "WIGGLE2_ROTATION_CHAIN": "Wiggle · 稳定旋转链",
    "WIGGLE2_STRETCH_CHAIN": "Wiggle · 可伸缩链",
    "GEOMETRY_ONLY": "仅整理骨骼链",
    "VISUAL_CHAIN_CLEANUP": "主体骨视觉整理",
}


def panel_view_state_from_context(context) -> PanelViewState:
    """Read Blender state once at the UI boundary, then call the pure mapper."""
    armature, source_kind = SelectionController.armature_from_context(context)
    selection_signature = SelectionController.signature(context)
    selected_count = len(SelectionController.selected_bone_names(context, armature)) if armature else 0
    runtime = context.window_manager.boneweaver_runtime
    settings = context.scene.boneweaver_settings
    availability = (PlanAvailability.AVAILABLE if runtime.plan_id and has_plan(runtime.plan_id)
                    else PlanAvailability.MISSING if runtime.plan_id else PlanAvailability.NONE)
    context_summary = BlenderContextSummary(
        armature.name if armature else None,
        selected_count,
        runtime.plan_chain_count or None,
        _PROFILE_LABELS.get(settings.physics_profile, settings.physics_profile),
        source_kind,
        selection_signature,
    )
    runtime_summary = RuntimeSummary(
        state=runtime.state,
        plan_id=runtime.plan_id,
        selection_signature=runtime.selection_signature,
        settings_signature=runtime.settings_signature,
        bone_count=runtime.plan_bone_count,
        chain_count=runtime.plan_chain_count,
        terminal_reliable_count=runtime.terminal_reliable_count,
        terminal_attention_count=runtime.terminal_attention_count,
        blocker_count=runtime.issue_count_blocker,
        warning_count=runtime.issue_count_warning,
        preview_active=is_preview_enabled(),
        is_busy=runtime.is_busy,
        last_error=runtime.last_error,
    )
    texts = getattr(context.blend_data, "texts", None)
    snapshot_available = bool(
        runtime.snapshot_available and runtime.snapshot_text_name
        and texts is not None and texts.get(runtime.snapshot_text_name)
    )
    snapshot = SnapshotSummary(snapshot_available, runtime.snapshot_text_name, runtime.plan_bone_count)
    return derive_panel_view_state(
        context_summary, runtime_summary, availability, selection_signature,
        settings_fingerprint(settings), snapshot,
    )


def advanced_panel_view_from_context(context) -> AdvancedPanelView:
    settings = context.scene.boneweaver_settings
    return AdvancedPanelView(
        settings.tip_length_mode == "ABSOLUTE",
        settings.roll_mode == "RADIAL_REFERENCE",
        settings.roll_mode == "PARALLEL_TRANSPORT",
        len(settings.terminal_overrides),
    )


def details_panel_view_from_context(context) -> DetailsPanelView:
    wm = context.window_manager
    state = wm.boneweaver_runtime
    issue_index = min(state.active_issue_index, max(0, len(wm.boneweaver_issue_items) - 1))
    issue_bone = wm.boneweaver_issue_items[issue_index].bone_name if wm.boneweaver_issue_items else ""
    return DetailsPanelView(
        state, wm, state.plan_chain_count, state.plan_bone_count,
        state.issue_count_blocker, state.issue_count_warning, state.details_loaded,
        bool(wm.boneweaver_chain_items), bool(wm.boneweaver_issue_items), bool(wm.boneweaver_proposal_items),
        issue_index, issue_bone,
    )


def recovery_panel_view_from_context(context) -> RecoveryPanelView:
    state = context.window_manager.boneweaver_runtime
    snapshot_available = snapshot_text_is_restorable(state.snapshot_text_name)
    return RecoveryPanelView(snapshot_available, bool(state.plan_id and has_plan(state.plan_id)))


def developer_panel_view_from_context(context) -> DeveloperPanelView:
    state = context.window_manager.boneweaver_runtime
    return DeveloperPanelView(state.state, state.plan_id, state.plan_fingerprint, state.last_error)


def quick_reorient_view_from_context(context) -> QuickReorientView:
    runtime = context.window_manager.boneweaver_runtime
    armature, _source = SelectionController.armature_from_context(context)
    texts = getattr(context.blend_data, "texts", None)
    snapshot_exists = bool(
        texts is not None
        and runtime.quick_snapshot_text_name
        and texts.get(runtime.quick_snapshot_text_name)
    )
    mode_labels = {
        "UEFORMAT_AUTO": "原版 UEFormat 兼容自动转换",
        "LINKS_ONLY": "仅重建层级连接",
        "HYBRID_MULTI_FEATURE": "实验性多特征混合转换",
    }
    automation_detail = ""
    if runtime.quick_mode == "HYBRID_MULTI_FEATURE":
        automation_detail = (
            f"多特征采用 {runtime.quick_precision_bones} 根 · "
            f"UEFormat 自动回退 {runtime.quick_fallback_bones} 根"
        )
    return QuickReorientView(
        button_enabled=bool(armature is not None and not runtime.is_busy),
        state=runtime.quick_state,
        summary=runtime.quick_summary,
        source=runtime.quick_source,
        mode_label=mode_labels.get(runtime.quick_mode, ""),
        automation_detail=automation_detail,
        processed_bones=runtime.quick_processed_bones,
        total_bones=runtime.quick_total_bones,
        component_count=runtime.quick_component_count,
        connected_edges=runtime.quick_connected_edges,
        blocker_count=0,
        warning_count=runtime.quick_warning_count,
        restore_enabled=bool(
            snapshot_exists
            and runtime.quick_state == "RESTORABLE"
            and not runtime.is_busy
        ),
    )
