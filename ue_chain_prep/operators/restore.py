"""Snapshot restore operator shell."""

import bpy
from bpy.props import BoolProperty, StringProperty

from ..contracts import OPERATOR_IDS


class UECP_OT_restore_snapshot(bpy.types.Operator):
    bl_idname = OPERATOR_IDS["restore_snapshot"]
    bl_label = "Restore UECP Snapshot"
    bl_options = {"REGISTER", "UNDO"}

    snapshot_text_name: StringProperty()
    allow_partial: BoolProperty(default=False)

    def execute(self, context):
        self.report({"ERROR"}, "No restorable snapshot is available")
        return {"CANCELLED"}
