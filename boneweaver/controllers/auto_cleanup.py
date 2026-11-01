"""One user-facing automatic cleanup workflow; diagnostics stay in snapshots."""
from __future__ import annotations

import json
import bpy

from ..core.armature_reader import resolve_active_armature
from ..core.auto_cleanup import (
    PREFIX, build_cleanup_plan, apply_cleanup_plan,
    latest_cleanup_snapshot, restore_cleanup_snapshot,
)


class AutoCleanupController:
    @staticmethod
    def can_run(context):
        runtime = getattr(context.window_manager, "boneweaver_runtime", None)
        return bool(runtime and not runtime.is_busy and resolve_active_armature(context))

    @staticmethod
    def can_restore(context):
        runtime = getattr(context.window_manager, "boneweaver_runtime", None)
        return bool(runtime and not runtime.is_busy and
                    latest_cleanup_snapshot(resolve_active_armature(context)))

    @staticmethod
    def refresh_snapshot(context):
        runtime = getattr(context.window_manager, "boneweaver_runtime", None)
        if runtime is None:
            return
        name = latest_cleanup_snapshot(resolve_active_armature(context))
        if name:
            runtime.quick_snapshot_text_name = name
            runtime.quick_state = "RESTORABLE"
            runtime.quick_summary = "可恢复自动整理前的骨架"

    @staticmethod
    def run(context, mode="AUTO"):
        runtime = context.window_manager.boneweaver_runtime
        runtime.is_busy = True
        runtime.quick_state = "ANALYZING"
        runtime.quick_summary = "正在筛选骨骼并整理"
        runtime.last_error = ""
        try:
            plan = build_cleanup_plan(context, mode=mode)
            name, result = apply_cleanup_plan(context, plan)
            runtime.quick_snapshot_text_name = name
            runtime.quick_total_bones = len(plan.quick_plan.bone_states)
            runtime.quick_processed_bones = result["reoriented"]
            runtime.quick_mutation_count = result["reoriented"] + result["connected"] + result["deleted"]
            runtime.quick_state = "RESTORABLE"
            runtime.quick_summary = f"整理完成：重定向 {result['reoriented']} 根，连接 {result['connected']} 根，清理辅助骨 {result['deleted']} 根"
            return True
        except Exception as error:
            runtime.quick_state = "ERROR"
            runtime.quick_summary = "未完成整理：" + str(error)
            runtime.last_error = str(error)
            return False
        finally:
            runtime.is_busy = False

    @staticmethod
    def restore(context):
        runtime = context.window_manager.boneweaver_runtime
        name = latest_cleanup_snapshot(resolve_active_armature(context))
        runtime.is_busy = True
        try:
            success = restore_cleanup_snapshot(context, name)
            runtime.quick_state = "RESTORED" if success else "ERROR"
            runtime.quick_summary = "已恢复整理前骨架与末端骨" if success else "检测到后续修改或备份缺失，未覆盖当前骨架"
            if success:
                runtime.quick_snapshot_text_name = ""
            return success
        finally:
            runtime.is_busy = False
