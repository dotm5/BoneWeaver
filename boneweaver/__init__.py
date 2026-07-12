"""BoneWeaver Blender extension entry point."""

from __future__ import annotations

from .contracts import ADDON_VERSION
from .registration import register, unregister


bl_info = {
    "name": "BoneWeaver",
    "author": "dotm5",
    "version": tuple(int(part) for part in ADDON_VERSION.split(".")),
    "blender": (4, 2, 0),
    "location": "View3D > Sidebar > BoneWeaver",
    "description": "Prepare Unreal-style joint hierarchies for Blender bone physics",
    "category": "Rigging",
}


__all__ = ["register", "unregister"]
