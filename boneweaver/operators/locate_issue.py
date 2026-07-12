"""Select and focus an issue bone without changing the Plan."""

import bpy
from bpy.props import IntProperty, StringProperty

from ..contracts import OPERATOR_IDS
from ..controllers.selection import SelectionController


class BONEWEAVER_OT_locate_issue(bpy.types.Operator):
    bl_idname = OPERATOR_IDS["locate_issue"]
    bl_label = "在视图中定位骨骼"

    issue_index: IntProperty(default=-1)
    bone_name: StringProperty(default="")

    def execute(self, context):
        if not SelectionController.locate_bone(context, self.bone_name):
            self.report({"WARNING"}, "无法定位相关骨骼")
            return {"CANCELLED"}
        return {"FINISHED"}
