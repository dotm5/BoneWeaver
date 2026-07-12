"""Snapshot recovery and explicit revalidation."""

import bpy

from ...contracts import OPERATOR_IDS
from ..view_model import recovery_panel_view_from_context


class BONEWEAVER_PT_recovery(bpy.types.Panel):
    bl_idname = "BONEWEAVER_PT_recovery"
    bl_label = "恢复与历史"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "BoneWeaver"
    bl_parent_id = "BONEWEAVER_PT_main"
    bl_options = {"DEFAULT_CLOSED"}

    def draw(self, context):
        layout = self.layout
        view = recovery_panel_view_from_context(context)
        if view.snapshot_available:
            layout.label(text="已保存恢复快照", icon="RECOVER_LAST")
            layout.operator(OPERATOR_IDS["restore_snapshot"], icon="LOOP_BACK")
        else:
            layout.label(text="尚无恢复快照", icon="INFO")
        row = layout.row()
        row.enabled = view.validation_available
        row.operator(OPERATOR_IDS["validate"], icon="CHECKMARK")
