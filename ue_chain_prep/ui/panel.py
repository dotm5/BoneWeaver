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
        inference_box.prop(settings, "tip_length_mode")
        if settings.tip_length_mode == "ABSOLUTE":
            inference_box.prop(settings, "absolute_tip_length")
        inference_box.prop(settings, "minimum_candidate_score")
        inference_box.prop(settings, "candidate_minimum_margin")
        inference_box.prop(settings, "minimum_confidence")
        inference_box.prop(settings, "roll_mode")
        if settings.roll_mode == "RADIAL_REFERENCE":
            inference_box.prop(settings, "radial_reference_mode")
            inference_box.prop(settings, "radial_reference_object")
            inference_box.prop(settings, "radial_reference_bone")
        elif settings.roll_mode == "PARALLEL_TRANSPORT":
            inference_box.prop(settings, "parallel_transport_weight")
            inference_box.prop(settings, "old_axis_weight")

        evidence_box = layout.box()
        evidence_box.label(text="Weight Evidence")
        evidence_box.prop(settings, "minimum_weight")
        evidence_box.prop(settings, "weight_exponent")
        evidence_box.prop(settings, "use_vertex_area_weight")
        evidence_box.prop(settings, "exclusivity_mode")
        evidence_box.prop(settings, "terminal_percentile")

        preview_box = layout.box()
        preview_box.label(text="Preview & Diagnostics")
        preview_box.prop(settings, "enable_segment_sampling_hints")
        preview_box.prop(settings, "long_segment_ratio_warning")
        preview_box.prop(settings, "position_epsilon_factor")
        preview_box.label(text=f"Issues: {runtime.issue_count_blocker} blockers · {runtime.issue_count_warning} warnings")

        if context.window_manager.uecp_chain_items:
            layout.template_list("UECP_UL_chains", "", context.window_manager, "uecp_chain_items", runtime, "active_chain_index", rows=3)
        if context.window_manager.uecp_proposal_items:
            layout.template_list("UECP_UL_proposals", "", context.window_manager, "uecp_proposal_items", runtime, "active_proposal_index", rows=4)
        if context.window_manager.uecp_issue_items:
            layout.template_list("UECP_UL_issues", "", context.window_manager, "uecp_issue_items", runtime, "active_chain_index", rows=4)

        row = layout.row(align=True)
        row.operator(OPERATOR_IDS["analyze"])
        row.operator(OPERATOR_IDS["preview_toggle"])
        layout.operator(OPERATOR_IDS["apply"])
        row = layout.row(align=True)
        row.operator(OPERATOR_IDS["validate"])
        row.operator(OPERATOR_IDS["restore_snapshot"])
        layout.operator(OPERATOR_IDS["export_report"])
        layout.operator(OPERATOR_IDS["clear_runtime"])
