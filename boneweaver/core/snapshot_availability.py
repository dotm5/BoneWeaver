"""Read-only discovery of snapshots that can still be offered for restore."""

from __future__ import annotations

import json
import math

import bpy
from mathutils import Vector
from .fingerprint import modifier_digest, weight_digest


def _roll_distance(first: float, second: float) -> float:
    return abs((first - second + math.pi) % (2.0 * math.pi) - math.pi)


def _payload_from_text(text):
    try:
        payload = json.loads(text.as_string())
    except (AttributeError, TypeError, ValueError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def snapshot_payload_is_restorable(payload) -> bool:
    if payload.get("kind") != "boneweaver.snapshot" or payload.get("status") != "APPLIED":
        return False
    armature_info = payload.get("armature", {})
    objects = getattr(bpy.data, "objects", None)
    if objects is None:
        return False
    armature = objects.get(armature_info.get("object_name", ""))
    if armature is None or armature.type != "ARMATURE" or armature.data.name != armature_info.get("data_name"):
        return False
    expected = payload.get("expected_post_bones")
    if not isinstance(expected, dict) or not expected:
        return False
    for name, digest in payload.get("mesh_digests", {}).items():
        mesh = objects.get(name)
        if mesh is None or weight_digest(mesh) != digest:
            return False
    for name, digest in payload.get("modifier_digests", {}).items():
        mesh = objects.get(name)
        if mesh is None or modifier_digest(mesh) != digest:
            return False
    for name, state in expected.items():
        bone = armature.data.bones.get(name)
        if bone is None or not isinstance(state, dict):
            return False
        try:
            head = Vector(state["head"])
            tail = Vector(state["tail"])
            _axis, current_roll = bone.AxisRollFromMatrix(bone.matrix_local.to_3x3())
            matches = (
                (bone.head_local - head).length <= 1.0e-7
                and (bone.tail_local - tail).length <= 1.0e-6
                and _roll_distance(float(current_roll), float(state["roll"])) <= 1.0e-5
                and bool(bone.use_connect) == bool(state["use_connect"])
                and (bone.parent.name if bone.parent else None) == state.get("parent_name")
            )
        except (KeyError, TypeError, ValueError):
            return False
        if not matches:
            return False
    return True


def snapshot_text_is_restorable(text_name: str) -> bool:
    texts = getattr(bpy.data, "texts", None)
    if texts is None:
        return False
    text = texts.get(text_name)
    payload = _payload_from_text(text) if text is not None else None
    return bool(payload and snapshot_payload_is_restorable(payload))


def discover_latest_restorable_snapshot() -> tuple[str, str]:
    candidates = []
    for text in getattr(bpy.data, "texts", ()):
        if not text.name.startswith("BONEWEAVER_SNAPSHOT::"):
            continue
        payload = _payload_from_text(text)
        if payload and snapshot_payload_is_restorable(payload):
            candidates.append((str(payload.get("created_at", "")), text.name,
                               str(payload.get("snapshot_id", text.name.split("::", 1)[-1]))))
    latest = max(candidates, default=None)
    return (latest[2], latest[1]) if latest else ("", "")
