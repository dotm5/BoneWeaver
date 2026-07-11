"""Validation operator shell."""

import bpy
from bpy.props import EnumProperty

from ..contracts import OPERATOR_IDS
from ..core.runtime_store import get_plan, has_plan, put_report
from ..core.serialization import build_diagnostic_report
from ..core.validation import capture_neutral_meshes, validate_post_apply


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
        runtime = context.window_manager.uecp_runtime
        if not runtime.plan_id or not has_plan(runtime.plan_id):
            return {"CANCELLED"}
        plan = get_plan(runtime.plan_id)
        baseline = capture_neutral_meshes(plan)
        validation = validate_post_apply(context, plan, baseline)
        put_report(build_diagnostic_report(plan, validation, runtime.snapshot_id or None))
        runtime.last_error = "" if validation.success else validation.issues[0]
        return {"FINISHED"}
