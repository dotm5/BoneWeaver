"""Analyze operator shell; G02+ supplies the pure analysis pipeline."""

import bpy

from ..contracts import OPERATOR_IDS
from ..core.preflight import run_preflight


class UECP_OT_analyze(bpy.types.Operator):
    bl_idname = OPERATOR_IDS["analyze"]
    bl_label = "Analyze UE Bone Chains"
    bl_options = {"REGISTER"}

    @classmethod
    def poll(cls, context):
        runtime = getattr(context.window_manager, "uecp_runtime", None)
        return runtime is not None and not runtime.is_busy

    def execute(self, context):
        runtime = context.window_manager.uecp_runtime
        runtime.is_busy = True
        try:
            result = run_preflight(context)
            counts = {"INFO": 0, "WARNING": 0, "BLOCKER": 0}
            for issue in result.issues:
                counts[issue.severity] = counts.get(issue.severity, 0) + 1
            runtime.issue_count_info = counts["INFO"]
            runtime.issue_count_warning = counts["WARNING"]
            runtime.issue_count_blocker = counts["BLOCKER"]
            runtime.plan_summary = (
                f"{len(result.selected_bone_names)} bones, "
                f"{len(result.mesh_names)} meshes, {len(result.issues)} issues"
            )
            runtime.generation += 1
            if result.armature_object_name is None:
                runtime.last_error = "UECP_NO_ACTIVE_ARMATURE"
                return {"CANCELLED"}
            runtime.last_error = ""
            return {"FINISHED"}
        finally:
            runtime.is_busy = False
