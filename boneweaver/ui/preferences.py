"""Add-on preferences for opt-in developer diagnostics."""

import bpy
from bpy.props import BoolProperty, FloatVectorProperty

from ..contracts import ADDON_ID


def _hierarchy_color_changed(_preferences, context) -> None:
    from ..controllers.hierarchy_overlay import HierarchyOverlayController
    HierarchyOverlayController.refresh(context)


class BONEWEAVER_AddonPreferences(bpy.types.AddonPreferences):
    bl_idname = ADDON_ID

    enable_developer_diagnostics: BoolProperty(
        name="Enable Developer Diagnostics",
        description="Show internal plan, schema, fingerprint, and performance controls",
        default=False,
    )
    hierarchy_parent_color: FloatVectorProperty(
        name="Parent Context", subtype="COLOR", size=4,
        min=0.0, max=1.0, default=(1.0, 0.78, 0.08, 1.0),
        update=_hierarchy_color_changed,
    )
    hierarchy_active_color: FloatVectorProperty(
        name="Active Root", subtype="COLOR", size=4,
        min=0.0, max=1.0, default=(1.0, 0.18, 0.06, 1.0),
        update=_hierarchy_color_changed,
    )
    hierarchy_descendant_color: FloatVectorProperty(
        name="Selected Descendant", subtype="COLOR", size=4,
        min=0.0, max=1.0, default=(0.0, 0.78, 1.0, 1.0),
        update=_hierarchy_color_changed,
    )
    hierarchy_main_continuation_color: FloatVectorProperty(
        name="Main Continuation", subtype="COLOR", size=4,
        min=0.0, max=1.0, default=(0.0, 0.68, 0.52, 1.0),
        update=_hierarchy_color_changed,
    )
    hierarchy_branch_color: FloatVectorProperty(
        name="Branch Node", subtype="COLOR", size=4,
        min=0.0, max=1.0, default=(0.72, 0.18, 0.92, 1.0),
        update=_hierarchy_color_changed,
    )
    hierarchy_side_branch_color: FloatVectorProperty(
        name="Side Branch", subtype="COLOR", size=4,
        min=0.0, max=1.0, default=(0.48, 0.52, 0.58, 0.85),
        update=_hierarchy_color_changed,
    )
    hierarchy_tip_helper_color: FloatVectorProperty(
        name="Existing Tip Helper", subtype="COLOR", size=4,
        min=0.0, max=1.0, default=(0.88, 0.38, 0.08, 1.0),
        update=_hierarchy_color_changed,
    )
    hierarchy_excluded_helper_color: FloatVectorProperty(
        name="Excluded Helper", subtype="COLOR", size=4,
        min=0.0, max=1.0, default=(0.48, 0.03, 0.03, 1.0),
        update=_hierarchy_color_changed,
    )

    def draw(self, _context):
        layout = self.layout
        layout.prop(self, "enable_developer_diagnostics")
        colors = layout.box()
        colors.label(text="Hierarchy Overlay Colors")
        colors.prop(self, "hierarchy_parent_color")
        colors.prop(self, "hierarchy_active_color")
        colors.prop(self, "hierarchy_descendant_color")
        colors.prop(self, "hierarchy_main_continuation_color")
        colors.prop(self, "hierarchy_branch_color")
        colors.prop(self, "hierarchy_side_branch_color")
        colors.prop(self, "hierarchy_tip_helper_color")
        colors.prop(self, "hierarchy_excluded_helper_color")
