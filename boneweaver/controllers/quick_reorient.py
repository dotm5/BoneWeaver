"""Authoritative one-button Quick Reorient workflow transitions."""

from __future__ import annotations

import bpy

from ..core.quick_reorient import build_quick_reorient_plan
from ..core.quick_transaction import (
    apply_quick_plan,
    discover_latest_quick_snapshot,
    restore_quick_snapshot,
)
from ..core.runtime_store import put_quick_plan
from .selection import SelectionController


class QuickReorientController:
    @staticmethod
    def _ensure_editable_armature(context):
        armature, _source = SelectionController.armature_from_context(context)
        if armature is None:
            return None
        if context.object and context.object.mode != "OBJECT":
            bpy.ops.object.mode_set(mode="OBJECT")
        bpy.ops.object.select_all(action="DESELECT")
        armature.hide_set(False)
        armature.hide_viewport = False
        armature.select_set(True)
        context.view_layer.objects.active = armature
        if armature.library or armature.data.library:
            bpy.ops.object.make_local(type="SELECT_OBDATA")
            armature = context.view_layer.objects.active
        if armature.data.users > 1:
            armature.data = armature.data.copy()
        return armature

    @staticmethod
    def clear_runtime(context, *, rediscover_snapshot: bool = False) -> None:
        runtime = getattr(context.window_manager, "boneweaver_runtime", None)
        if runtime is None:
            return
        runtime.quick_state = "IDLE"
        runtime.quick_plan_id = ""
        runtime.quick_source = ""
        runtime.quick_summary = ""
        runtime.quick_snapshot_text_name = ""
        runtime.quick_total_bones = 0
        runtime.quick_processed_bones = 0
        runtime.quick_component_count = 0
        runtime.quick_connected_edges = 0
        runtime.quick_mutation_count = 0
        runtime.quick_blocker_count = 0
        runtime.quick_warning_count = 0
        runtime.quick_already_normalized = False
        if rediscover_snapshot:
            QuickReorientController.refresh_snapshot(context)

    @staticmethod
    def refresh_snapshot(context) -> None:
        runtime = getattr(context.window_manager, "boneweaver_runtime", None)
        if runtime is None:
            return
        text_name = discover_latest_quick_snapshot()
        runtime.quick_snapshot_text_name = text_name
        if text_name:
            runtime.quick_state = "RESTORABLE"
            runtime.quick_summary = "发现可恢复的全自动转换快照"

    @staticmethod
    def can_run(context) -> bool:
        runtime = getattr(context.window_manager, "boneweaver_runtime", None)
        armature, _source = SelectionController.armature_from_context(context)
        return bool(runtime and not runtime.is_busy and armature is not None)

    @staticmethod
    def can_restore(context) -> bool:
        runtime = getattr(context.window_manager, "boneweaver_runtime", None)
        return bool(
            runtime
            and not runtime.is_busy
            and runtime.quick_snapshot_text_name
            and runtime.quick_state == "RESTORABLE"
        )

    @staticmethod
    def _populate_runtime(runtime, plan) -> None:
        runtime.quick_plan_id = plan.plan_id
        runtime.quick_source = plan.source_adapter
        runtime.quick_total_bones = len(plan.bone_states)
        runtime.quick_processed_bones = sum(
            not proposal.skipped for proposal in plan.proposals
        )
        runtime.quick_component_count = len(plan.linked_components)
        runtime.quick_connected_edges = sum(
            proposal.target_use_connect for proposal in plan.proposals
        )
        runtime.quick_blocker_count = 0
        runtime.quick_warning_count = len(plan.issues)
        runtime.quick_already_normalized = plan.already_normalized

    @classmethod
    def run(cls, context) -> bool:
        runtime = context.window_manager.boneweaver_runtime
        runtime.is_busy = True
        runtime.quick_state = "ANALYZING"
        runtime.quick_summary = "正在分析整个骨架"
        runtime.quick_mutation_count = 0
        try:
            cls._ensure_editable_armature(context)
            plan = build_quick_reorient_plan(context)
            if plan is None:
                runtime.quick_state = "ERROR"
                runtime.quick_summary = "未找到可编辑骨架"
                runtime.last_error = "BONEWEAVER_QUICK_NO_ACTIVE_ARMATURE"
                return False
            put_quick_plan(plan)
            cls._populate_runtime(runtime, plan)

            runtime.quick_state = "APPLYING"
            runtime.quick_summary = "正在强制完成自动转换"
            result = apply_quick_plan(context, plan, strict_validation=False)
            runtime.quick_snapshot_text_name = result.snapshot_text_name
            runtime.quick_mutation_count = result.mutation_count
            runtime.quick_connected_edges = result.connected_edge_count
            runtime.quick_warning_count += len(result.validation_issues)
            if not result.success:
                runtime.quick_state = "ROLLED_BACK" if result.rolled_back else "ERROR"
                runtime.quick_summary = (
                    "验证失败，已自动恢复"
                    if result.rolled_back
                    else "转换失败且自动恢复失败"
                )
                runtime.last_error = (
                    result.error or "BONEWEAVER_QUICK_POST_VALIDATION_FAILED"
                )
                return False

            runtime.quick_state = "RESTORABLE"
            summary = (
                f"完成：{result.mutation_count} 根骨骼已修改，"
                f"{result.connected_edge_count} 条原生连接"
            )
            if runtime.quick_warning_count:
                summary += f"；自动兼容 {runtime.quick_warning_count} 项限制"
            runtime.quick_summary = summary
            runtime.last_error = ""
            return True
        except Exception as error:
            runtime.quick_state = "ERROR"
            runtime.quick_summary = "全自动转换发生内部错误"
            runtime.last_error = str(error)
            return False
        finally:
            runtime.is_busy = False

    @staticmethod
    def restore(context) -> bool:
        runtime = context.window_manager.boneweaver_runtime
        runtime.is_busy = True
        try:
            success, error = restore_quick_snapshot(
                context, runtime.quick_snapshot_text_name
            )
            if not success:
                runtime.last_error = error or "BONEWEAVER_QUICK_RESTORE_CONFLICT"
                return False
            runtime.quick_state = "RESTORED"
            runtime.quick_summary = "已恢复全自动转换前的精确状态"
            runtime.quick_snapshot_text_name = ""
            runtime.last_error = ""
            return True
        finally:
            runtime.is_busy = False
