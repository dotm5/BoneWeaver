"""Add-on preferences for opt-in developer diagnostics."""

import bpy
from bpy.props import BoolProperty

from ..contracts import ADDON_ID


class UECP_AddonPreferences(bpy.types.AddonPreferences):
    bl_idname = ADDON_ID

    enable_developer_diagnostics: BoolProperty(
        name="Enable Developer Diagnostics",
        description="Show internal plan, schema, fingerprint, and performance controls",
        default=False,
    )

    def draw(self, _context):
        self.layout.prop(self, "enable_developer_diagnostics")
