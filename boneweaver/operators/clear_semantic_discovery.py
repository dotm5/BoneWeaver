"""Clear semantic discovery runtime state."""

import bpy

from ..contracts import OPERATOR_IDS
from ..controllers.semantic_discovery import SemanticDiscoveryController


class BONEWEAVER_OT_clear_semantic_discovery(bpy.types.Operator):
    bl_idname = OPERATOR_IDS["clear_semantic_discovery"]
    bl_label = "Clear Semantic Discovery"

    @classmethod
    def poll(cls, context):
        runtime = getattr(context.window_manager, "boneweaver_runtime", None)
        return bool(runtime and not runtime.is_busy and runtime.semantic_discovery_active)

    def execute(self, context):
        SemanticDiscoveryController.clear(context)
        return {"FINISHED"}
