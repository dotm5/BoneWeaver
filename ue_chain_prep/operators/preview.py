"""Preview operator shell."""

import bpy

from ..contracts import OPERATOR_IDS


class UECP_OT_preview_toggle(bpy.types.Operator):
    bl_idname = OPERATOR_IDS["preview_toggle"]
    bl_label = "Toggle Chain Preview"

    def execute(self, context):
        self.report({"ERROR"}, "No analyzed plan is available for preview")
        return {"CANCELLED"}
