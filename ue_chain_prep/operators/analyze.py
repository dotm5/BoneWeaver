"""Analyze operator shell; G02+ supplies the pure analysis pipeline."""

import bpy

from ..contracts import OPERATOR_IDS


class UECP_OT_analyze(bpy.types.Operator):
    bl_idname = OPERATOR_IDS["analyze"]
    bl_label = "Analyze UE Bone Chains"
    bl_options = {"REGISTER"}

    @classmethod
    def poll(cls, context):
        runtime = getattr(context.window_manager, "uecp_runtime", None)
        return runtime is not None and not runtime.is_busy

    def execute(self, context):
        self.report({"INFO"}, "Analysis pipeline will be enabled by the next implementation stage")
        return {"CANCELLED"}
