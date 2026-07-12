"""Conflict-aware restoration of only tail, roll, and use_connect."""

from __future__ import annotations

import json
import math
from contextlib import contextmanager

import bpy
from mathutils import Vector

from .context_guard import ContextStateGuard
from .fingerprint import modifier_digest, weight_digest
from .validation import armature_state_matches


def _roll_distance(first, second):
    return abs((first - second + math.pi) % (2.0 * math.pi) - math.pi)


@contextmanager
def _mirror_disabled(armature):
    original = bool(armature.data.use_mirror_x)
    armature.data.use_mirror_x = False
    try:
        yield
    finally:
        armature.data.use_mirror_x = original


def restore_snapshot(context, text_name):
    text = bpy.data.texts.get(text_name)
    if text is None:
        return False, "UECP_RESTORE_CONFLICT"
    payload = json.loads(text.as_string())
    armature_info = payload["armature"]
    armature = bpy.data.objects.get(armature_info["object_name"])
    if armature is None or armature.data.name != armature_info["data_name"]:
        return False, "UECP_RESTORE_CONFLICT"
    for name, digest in payload.get("mesh_digests", {}).items():
        mesh = bpy.data.objects.get(name)
        if mesh is None or weight_digest(mesh) != digest:
            return False, "UECP_RESTORE_CONFLICT"
    for name, digest in payload.get("modifier_digests", {}).items():
        mesh = bpy.data.objects.get(name)
        if mesh is None or modifier_digest(mesh) != digest:
            return False, "UECP_RESTORE_CONFLICT"
    expected = payload["expected_post_bones"]
    pre = payload["pre_bones"]
    with ContextStateGuard(context), _mirror_disabled(armature):
        if context.object and context.object.mode != "OBJECT":
            bpy.ops.object.mode_set(mode="OBJECT")
        context.view_layer.update()
        whole_post_state = payload.get("whole_armature_post_state")
        if whole_post_state and not armature_state_matches(armature, whole_post_state):
            return False, "UECP_RESTORE_CONFLICT"
        bpy.ops.object.select_all(action="DESELECT")
        armature.select_set(True)
        context.view_layer.objects.active = armature
        bpy.ops.object.mode_set(mode="EDIT")
        conflict = False
        for name, state in expected.items():
            bone = armature.data.edit_bones.get(name)
            if bone is None:
                conflict = True
                break
            if (bone.head - Vector(state["head"])).length > 1.0e-7:
                conflict = True
            if (bone.tail - Vector(state["tail"])).length > 1.0e-6:
                conflict = True
            if _roll_distance(float(bone.roll), float(state["roll"])) > 1.0e-5:
                conflict = True
            if bool(bone.use_connect) != bool(state["use_connect"]):
                conflict = True
            parent_name = bone.parent.name if bone.parent else None
            if parent_name != state.get("parent_name"):
                conflict = True
        if conflict:
            bpy.ops.object.mode_set(mode="OBJECT")
            return False, "UECP_RESTORE_CONFLICT"
        for name in pre:
            armature.data.edit_bones[name].use_connect = False
        for name, state in pre.items():
            bone = armature.data.edit_bones[name]
            bone.tail = state["tail"]
            bone.roll = state["roll"]
        for name, state in pre.items():
            armature.data.edit_bones[name].use_connect = state["use_connect"]
        bpy.ops.object.mode_set(mode="OBJECT")
    payload["status"] = "RESTORED"
    text.clear()
    text.write(json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2))
    return True, None
