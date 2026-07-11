"""Validation operator shell."""

import bpy
from bpy.props import EnumProperty

from ..contracts import OPERATOR_IDS


class UECP_OT_validate(bpy.types.Operator):
    bl_idname = OPERATOR_IDS["validate"]
    bl_label = "Validate Current Conversion"
    bl_options = {"REGISTER"}

    validation_scope: EnumProperty(
        items=(
            ("CURRENT_PLAN", "Current Plan", ""),
            ("LAST_SNAPSHOT", "Last Snapshot", ""),
        ),
        default="CURRENT_PLAN",
    )

    def execute(self, context):
        self.report({"ERROR"}, "No validation target is available")
        return {"CANCELLED"}
