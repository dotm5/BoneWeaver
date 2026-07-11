"""Pure user-facing workflow state derived from Blender/runtime summaries."""

from __future__ import annotations

from dataclasses import dataclass

from ..contracts import OPERATOR_IDS, PlanAvailability, PlanState, WorkflowStage
from ..core.fingerprint import settings_fingerprint
from ..core.runtime_store import has_plan
from ..controllers.selection import SelectionController
from .draw import is_preview_enabled


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
        rollback_failed = runtime_summary.last_error == "UECP_ROLLBACK_FAILED"
        stage = WorkflowStage.ROLLBACK_FAILED if rollback_failed else WorkflowStage.ERROR
        title = "自动恢复失败" if rollback_failed else "转换未完成"
        description = ("请立即撤销或关闭文件而不保存。" if rollback_failed
                       else "请查看错误详情后重置本次会话。")
        return PanelViewState(stage.value, result=_result(stage, title, description, runtime_summary),
                              primary_action=_action("clear_runtime", "重置本次会话", "FILE_REFRESH", primary=True), **common)

    if runtime_summary.state in {PlanState.RESTORABLE.value, PlanState.APPLIED.value}:
        stage = WorkflowStage.APPLIED
        secondary = ((_action("restore_snapshot", "恢复转换前状态", "LOOP_BACK"),)
                     if snapshot_summary.available else ())
        return PanelViewState(stage.value,
                              result=_result(stage, "转换完成", "骨骼已更新并通过安全验证。", runtime_summary),
                              primary_action=_action("check_and_preview", "检查另一条骨骼链", "VIEWZOOM", primary=True),
                              secondary_actions=secondary, **common)

    has_plan_identity = bool(runtime_summary.plan_id)
    if has_plan_identity and PlanAvailability(plan_availability) == PlanAvailability.MISSING:
        stage = WorkflowStage.PLAN_LOST
        return PanelViewState(stage.value, result=_result(stage, "分析结果已不可用", "请重新检查。", runtime_summary),
                              primary_action=_action("check_and_preview", "重新检查", "FILE_REFRESH", primary=True), **common)
    if available and runtime_summary.settings_signature and runtime_summary.settings_signature != current_settings_signature:
        stage = WorkflowStage.STALE_SETTINGS
        return PanelViewState(stage.value, result=_result(stage, "设置已经改变", "请重新检查后再应用。", runtime_summary),
                              primary_action=_action("check_and_preview", "重新检查", "FILE_REFRESH", primary=True), **common)
    if available and runtime_summary.selection_signature and runtime_summary.selection_signature != current_selection_signature:
        stage = WorkflowStage.STALE_SELECTION
        return PanelViewState(stage.value, result=_result(stage, "当前选择已经改变", "上次结果不再针对当前骨骼选择。", runtime_summary),
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
}


def panel_view_state_from_context(context) -> PanelViewState:
    """Read Blender state once at the UI boundary, then call the pure mapper."""
    armature, source_kind = SelectionController.armature_from_context(context)
    selection_signature = SelectionController.signature(context)
    selected_count = len(SelectionController.selected_bone_names(context, armature)) if armature else 0
    runtime = context.window_manager.uecp_runtime
    settings = context.scene.uecp_settings
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
    snapshot_available = bool(runtime.snapshot_text_name and context.blend_data.texts.get(runtime.snapshot_text_name))
    snapshot = SnapshotSummary(snapshot_available, runtime.snapshot_text_name, runtime.plan_bone_count)
    return derive_panel_view_state(
        context_summary, runtime_summary, availability, selection_signature,
        settings_fingerprint(settings), snapshot,
    )
