"""Read UEFormat metadata and generic joint state without changing the rig."""

from __future__ import annotations

import json
import re

import bpy

from .context_guard import ContextStateGuard
from .quick_reorient_models import QuickBoneState, QuickSourceMetadata


_METADATA_KEYS = (
    "orig_loc", "orig_quat", "reorient_direction", "post_quat", "is_socket"
)
_CONTROL_TOKENS = frozenset(
    {"ik", "fk", "ctrl", "control", "pole", "effector", "target", "virtual"}
)


def _finite_tuple(value, length: int):
    if value is None:
        return None
    try:
        result = tuple(float(component) for component in value)
    except (TypeError, ValueError):
        return None
    return result if len(result) == length else None


def is_socket_bone(name: str, metadata: QuickSourceMetadata) -> bool:
    tokens = tuple(
        token for token in re.split(r"[^a-z0-9]+", name.casefold()) if token
    )
    return bool(
        metadata.is_socket
        or "socket" in tokens
        or any("socket" in collection.casefold() for collection in metadata.collection_names)
    )


def is_external_control(name: str) -> bool:
    tokens = frozenset(
        token for token in re.split(r"[^a-z0-9]+", name.casefold()) if token
    )
    return bool(tokens & _CONTROL_TOKENS)


def detect_source(metadata: dict[str, QuickSourceMetadata]) -> tuple[str, bool]:
    has_metadata = any(
        item.orig_loc is not None and item.orig_quat is not None
        for item in metadata.values()
    )
    already = any(item.reorient_direction is not None for item in metadata.values())
    if has_metadata and already:
        return "UEFORMAT_ALREADY_REORIENTED", True
    if has_metadata:
        return "UEFORMAT_METADATA", False
    return "GENERIC_JOINT_HIERARCHY", False


def read_allowed_child_map(armature) -> dict[str, tuple[str, ...]]:
    raw = armature.data.get("boneweaver_allowed_reorient_children")
    if raw is None:
        raw = armature.get("boneweaver_allowed_reorient_children")
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except json.JSONDecodeError:
            return {}
    if not hasattr(raw, "items"):
        return {}
    result = {}
    for name, children in raw.items():
        if isinstance(children, str):
            children = (children,)
        try:
            result[str(name)] = tuple(sorted(str(child) for child in children))
        except TypeError:
            continue
    return result


def capture_quick_source(context, armature):
    states = []
    metadata = {}
    with ContextStateGuard(context):
        if context.object and context.object.mode != "OBJECT":
            bpy.ops.object.mode_set(mode="OBJECT")
        bpy.ops.object.select_all(action="DESELECT")
        armature.select_set(True)
        context.view_layer.objects.active = armature
        armature.data.use_mirror_x = False
        bpy.ops.object.mode_set(mode="EDIT")
        for bone in sorted(armature.data.edit_bones, key=lambda item: item.name):
            flags = tuple(sorted(key for key in _METADATA_KEYS if key in bone))
            collections = tuple(
                sorted(collection.name for collection in getattr(bone, "collections", ()))
            )
            item_metadata = QuickSourceMetadata(
                orig_loc=_finite_tuple(bone.get("orig_loc"), 3),
                orig_quat=_finite_tuple(bone.get("orig_quat"), 4),
                reorient_direction=_finite_tuple(bone.get("reorient_direction"), 3),
                is_socket=bool(bone.get("is_socket", False)),
                collection_names=collections,
            )
            metadata[bone.name] = item_metadata
            matrix = bone.matrix.copy()
            states.append(
                QuickBoneState(
                    bone_name=bone.name,
                    parent_name=bone.parent.name if bone.parent else None,
                    child_names=tuple(sorted(child.name for child in bone.children)),
                    head=tuple(float(value) for value in bone.head),
                    tail=tuple(float(value) for value in bone.tail),
                    roll=float(bone.roll),
                    matrix=tuple(
                        float(matrix[row][column])
                        for row in range(4)
                        for column in range(4)
                    ),
                    length=float(bone.length),
                    use_connect=bool(bone.use_connect),
                    use_deform=bool(bone.use_deform),
                    source_metadata_flags=flags,
                )
            )
        bpy.ops.object.mode_set(mode="OBJECT")
    return tuple(states), metadata
