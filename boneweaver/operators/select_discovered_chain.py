"""Explicit confirmation and selection bridge for one discovered chain."""

import bpy
from bpy.props import StringProperty

from ..contracts import OPERATOR_IDS
from ..controllers.semantic_discovery import (
    SemanticDiscoveryController,
    SemanticDiscoveryRuntimeError,
)


class BONEWEAVER_OT_select_discovered_chain(bpy.types.Operator):
    bl_idname = OPERATOR_IDS["select_discovered_chain"]
    bl_label = "Confirm and Select Discovered Chain"
    bl_options = {"REGISTER", "UNDO"}

    chain_id: StringProperty(default="")

    @classmethod
    def poll(cls, context):
        runtime = getattr(context.window_manager, "boneweaver_runtime", None)
        return bool(runtime and not runtime.is_busy and runtime.semantic_discovery_active)

    def execute(self, context):
        try:
            SemanticDiscoveryController.select_chain(context, self.chain_id)
        except SemanticDiscoveryRuntimeError as exc:
            context.window_manager.boneweaver_runtime.last_error = str(exc)
            return {"CANCELLED"}
        return {"FINISHED"}
