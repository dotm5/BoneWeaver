"""Read-only hierarchy inspection operator."""

import bpy

from ..contracts import OPERATOR_IDS
from ..controllers.hierarchy_inspection import HierarchyInspectionController
from ..controllers.selection import SelectionController


class BONEWEAVER_OT_inspect_active_hierarchy(bpy.types.Operator):
    bl_idname = OPERATOR_IDS["inspect_active_hierarchy"]
    bl_label = "Inspect Active Hierarchy"
    bl_options = {"REGISTER"}

    @classmethod
    def poll(cls, context):
        runtime = getattr(context.window_manager, "boneweaver_runtime", None)
        armature, _source = SelectionController.armature_from_context(context)
        if runtime is None or runtime.is_busy or armature is None:
            return False
        if context.mode == "POSE" and context.object == armature:
            return getattr(context, "active_pose_bone", None) is not None
        if context.mode == "EDIT_ARMATURE" and context.object == armature:
            return getattr(armature.data.edit_bones, "active", None) is not None
        return getattr(armature.data.bones, "active", None) is not None

    def execute(self, context):
        try:
            HierarchyInspectionController.inspect(context)
        except (RuntimeError, ValueError, KeyError) as exc:
            context.window_manager.boneweaver_runtime.last_error = str(exc)
            self.report({"WARNING"}, str(exc))
            return {"CANCELLED"}
        return {"FINISHED"}
