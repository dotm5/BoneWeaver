"""Initial N-panel surface for the stable settings contract."""

import bpy

from ..contracts import OPERATOR_IDS


class UECP_PT_main(bpy.types.Panel):
    bl_idname = "UECP_PT_main"
    bl_label = "UE Chain Prep"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "UE Chain Prep"

    def draw(self, context):
        layout = self.layout
        settings = context.scene.uecp_settings
        runtime = context.window_manager.uecp_runtime

        context_box = layout.box()
        context_box.label(text=f"Plan State: {runtime.state}")
        context_box.label(text=f"Active: {context.active_object.name if context.active_object else 'None'}")

        scope_box = layout.box()
        scope_box.prop(settings, "scope_mode")
        scope_box.prop(settings, "mesh_scope")
        scope_box.prop(settings, "physics_profile")

        inference_box = layout.box()
        inference_box.prop(settings, "terminal_mode")
        inference_box.prop(settings, "bone_forward_axis")
        inference_box.prop(settings, "roll_mode")

        row = layout.row(align=True)
        row.operator(OPERATOR_IDS["analyze"])
        row.operator(OPERATOR_IDS["preview_toggle"])
        layout.operator(OPERATOR_IDS["apply"])
        layout.operator(OPERATOR_IDS["clear_runtime"])
