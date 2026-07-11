"""Snapshot recovery and explicit revalidation."""

import bpy

from ...contracts import OPERATOR_IDS


class UECP_PT_recovery(bpy.types.Panel):
    bl_idname = "UECP_PT_recovery"
    bl_label = "恢复与历史"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "UE Chain Prep"
    bl_parent_id = "UECP_PT_main"
    bl_options = {"DEFAULT_CLOSED"}

    def draw(self, context):
        layout = self.layout
        runtime = context.window_manager.uecp_runtime
        if runtime.snapshot_text_name:
            layout.label(text="已保存恢复快照", icon="RECOVER_LAST")
            layout.operator(OPERATOR_IDS["restore_snapshot"], icon="LOOP_BACK")
        else:
            layout.label(text="尚无恢复快照", icon="INFO")
        layout.operator(OPERATOR_IDS["validate"], icon="CHECKMARK")
