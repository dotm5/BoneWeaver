"""Preview operator shell."""

import bpy

from ..contracts import OPERATOR_IDS
from ..contracts import PlanState
from ..core.runtime_store import get_preview_cache
from ..ui.draw import disable_preview, enable_preview, is_preview_enabled


class UECP_OT_preview_toggle(bpy.types.Operator):
    bl_idname = OPERATOR_IDS["preview_toggle"]
    bl_label = "Toggle Chain Preview"

    def execute(self, context):
        runtime = context.window_manager.uecp_runtime
        if runtime.state not in {PlanState.ANALYZED.value, PlanState.RESTORABLE.value}:
            disable_preview()
            runtime.preview_enabled = False
            return {"CANCELLED"}
        if is_preview_enabled():
            disable_preview()
            runtime.preview_enabled = False
        else:
            enable_preview(get_preview_cache())
            runtime.preview_enabled = True
        return {"FINISHED"}
