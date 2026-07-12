"""Record a manual hierarchy branch continuation without editing bones."""

import bpy
from bpy.props import StringProperty

from ..contracts import OPERATOR_IDS
from ..controllers.hierarchy_inspection import HierarchyInspectionController


class UECP_OT_set_branch_continuation(bpy.types.Operator):
    bl_idname = OPERATOR_IDS["set_branch_continuation"]
    bl_label = "Set Branch Continuation"
    bl_options = {"REGISTER"}

    branch_bone_name: StringProperty(name="分叉骨骼")
    selected_child_name: StringProperty(name="延续子骨骼")

    @classmethod
    def poll(cls, context):
        runtime = getattr(context.window_manager, "uecp_runtime", None)
        return bool(
            runtime
            and not runtime.is_busy
            and runtime.hierarchy_inspection_active
            and runtime.hierarchy_branch_count > 0
        )

    def execute(self, context):
        try:
            HierarchyInspectionController.set_branch_continuation(
                context,
                self.branch_bone_name,
                self.selected_child_name,
            )
        except (RuntimeError, ValueError, KeyError) as exc:
            context.window_manager.uecp_runtime.last_error = str(exc)
            self.report({"WARNING"}, str(exc))
            return {"CANCELLED"}
        return {"FINISHED"}
