"""Translation registration; full message catalog is added with the final UI."""

import bpy

from .contracts import ADDON_ID


TRANSLATIONS = {
    "zh_HANS": {
        ("*", "UE Chain Prep"): "UE 骨链准备",
        ("Operator", "Analyze UE Bone Chains"): "分析 UE 骨骼链",
    }
}


def register() -> None:
    bpy.app.translations.register(ADDON_ID, TRANSLATIONS)


def unregister() -> None:
    try:
        bpy.app.translations.unregister(ADDON_ID)
    except RuntimeError:
        pass
