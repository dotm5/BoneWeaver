"""Analyze operator shell; G02+ supplies the pure analysis pipeline."""

import bpy

from ..contracts import OPERATOR_IDS, PlanState
from ..core.planner import build_plan
from ..core.runtime_store import put_plan


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
            plan = build_plan(context)
            if plan is None:
                runtime.last_error = "UECP_NO_ACTIVE_ARMATURE"
                return {"CANCELLED"}
            counts = {"INFO": 0, "WARNING": 0, "BLOCKER": 0}
            for issue in plan.issues:
                counts[issue.severity] = counts.get(issue.severity, 0) + 1
            runtime.issue_count_info = counts["INFO"]
            runtime.issue_count_warning = counts["WARNING"]
            runtime.issue_count_blocker = counts["BLOCKER"]
            runtime.plan_summary = (
                f"{len(plan.bone_states)} bones, "
                f"{len(plan.mesh_states)} meshes, {len(plan.issues)} issues"
            )
            put_plan(plan)
            runtime.plan_id = plan.plan_id
            runtime.plan_fingerprint = plan.source_fingerprint
            runtime.state = PlanState.ANALYZED.value
            runtime.generation += 1
            runtime.last_error = ""
            return {"FINISHED"}
        finally:
            runtime.is_busy = False
