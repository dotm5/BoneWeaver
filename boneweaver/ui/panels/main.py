"""Simple automatic cleanup workflow."""

import bpy

from ...controllers.auto_cleanup import AutoCleanupController
from ..view_model import panel_view_state_from_context


class BONEWEAVER_PT_main(bpy.types.Panel):
    bl_idname = "BONEWEAVER_PT_main"
    bl_label = "BoneWeaver"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "BoneWeaver"

    def draw(self, context):
        layout = self.layout
        view = panel_view_state_from_context(context)
        runtime = context.window_manager.boneweaver_runtime
        target = layout.box()
        target.label(text=f"骨架：{view.target.armature_name or '未找到'}", icon="ARMATURE_DATA")
        if view.target.source_kind == "ARMATURE_MODIFIER":
            target.label(text="来源：当前模型的骨架修改器")
        row = layout.row()
        row.scale_y = 1.5
        row.enabled = AutoCleanupController.can_run(context)
        row.operator("boneweaver.auto_cleanup", text="全自动整理", icon="PLAY").mode = "AUTO"
        for mode, label in (
            ("REORIENT", "仅父子重定向"),
            ("CONNECT", "仅连接骨链"),
            ("CLEANUP", "仅清理辅助骨"),
        ):
            row = layout.row()
            row.enabled = AutoCleanupController.can_run(context)
            row.operator("boneweaver.auto_cleanup", text=label).mode = mode
        if runtime.quick_summary:
            icon = "ERROR" if runtime.quick_state in {"ERROR", "ROLLED_BACK", "BLOCKED"} else "INFO"
            layout.label(text=runtime.quick_summary, icon=icon)
        if AutoCleanupController.can_restore(context):
            layout.operator("boneweaver.restore_auto_cleanup", text="恢复整理前状态", icon="LOOP_BACK")
