"""Freeze explicitly confirmed discovery names for the next Analyze."""

import bpy

from ..contracts import OPERATOR_IDS
from ..controllers.semantic_discovery import (
    SemanticDiscoveryController,
    SemanticDiscoveryRuntimeError,
)


class BONEWEAVER_OT_use_discovered_chains(bpy.types.Operator):
    bl_idname = OPERATOR_IDS["use_discovered_chains"]
    bl_label = "Use Confirmed Discovered Chains"
    bl_options = {"REGISTER"}

    @classmethod
    def poll(cls, context):
        runtime = getattr(context.window_manager, "boneweaver_runtime", None)
        return bool(
            runtime
            and not runtime.is_busy
            and runtime.semantic_discovery_active
            and runtime.semantic_confirmed_count > 0
        )

    def execute(self, context):
        try:
            SemanticDiscoveryController.use_confirmed_chains(context)
        except SemanticDiscoveryRuntimeError as exc:
            context.window_manager.boneweaver_runtime.last_error = str(exc)
            return {"CANCELLED"}
        return {"FINISHED"}
