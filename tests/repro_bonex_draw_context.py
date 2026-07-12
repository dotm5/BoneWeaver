"""Reproduce BoneX 1.2.6 mutating an Armature object during UI draw.

This is a real-window diagnostic harness rather than part of unittest discovery.
It exits Blender after the first draw attempt and prints a stable result marker.
"""

from __future__ import annotations

import os
import sys

import bpy


BONEX_PARENT = os.environ.get(
    "BONEX_PARENT",
    r"C:\Users\70560\AppData\Roaming\Blender Foundation\Blender\5.2\extensions\user_default",
)
sys.path.insert(0, BONEX_PARENT)

from bonex.utils import const, utils  # noqa: E402


_result: str | None = None


def _draw_probe(_header, _context) -> None:
    global _result
    if _result is not None:
        return
    armature_obj = bpy.data.objects["BONEWEAVER_BoneX_Draw_Probe"]
    try:
        utils.get_armature_soft_connections(armature_obj)
    except Exception as exc:  # The exact Blender context exception is the signal.
        _result = f"FAIL {type(exc).__name__}: {exc}"
    else:
        payload = armature_obj.get(const.rigidbody_data_name)
        serialized = payload.to_dict() if hasattr(payload, "to_dict") else payload
        _result = f"PASS bonex_data={serialized!r}"
    print("BONEWEAVER_BONEX_DRAW_RESULT", _result, flush=True)


def _finish() -> float | None:
    if _result is None:
        return 0.05
    bpy.types.TOPBAR_HT_upper_bar.remove(_draw_probe)
    bpy.ops.wm.quit_blender()
    return None


armature_data = bpy.data.armatures.new("BONEWEAVER_BoneX_Draw_Probe_Data")
armature_obj = bpy.data.objects.new("BONEWEAVER_BoneX_Draw_Probe", armature_data)
bpy.context.scene.collection.objects.link(armature_obj)
bpy.context.view_layer.objects.active = armature_obj
armature_obj.select_set(True)

bpy.types.TOPBAR_HT_upper_bar.append(_draw_probe)
bpy.app.timers.register(_finish, first_interval=0.05)
