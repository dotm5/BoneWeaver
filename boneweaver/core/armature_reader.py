"""Read stable armature semantics without changing Blender mode."""

from __future__ import annotations

import math

from .models import BoneState


def resolve_active_armature(context):
    active = context.view_layer.objects.active
    if active is None:
        return None
    if active.type == "ARMATURE":
        return active
    return active.find_armature() if hasattr(active, "find_armature") else None


def selected_bone_names(context, armature_obj) -> tuple[str, ...]:
    if context.mode == "EDIT_ARMATURE" and context.object == armature_obj:
        names = (bone.name for bone in armature_obj.data.edit_bones if bone.select)
    elif context.mode == "POSE" and context.object == armature_obj:
        names = (bone.name for bone in context.selected_pose_bones or ())
    else:
        data_bones = tuple(armature_obj.data.bones)
        if data_bones and hasattr(data_bones[0], "select"):
            names = (bone.name for bone in data_bones if bone.select)
        else:
            names = (bone.name for bone in armature_obj.pose.bones if bone.select)
    return tuple(sorted(set(names)))


def resolve_scope_names(context, armature_obj, scope_mode: str) -> tuple[str, ...]:
    selected = selected_bone_names(context, armature_obj)
    if scope_mode == "SELECTED_BONES":
        return selected
    if scope_mode == "SELECTED_ROOTS_AND_DESCENDANTS":
        selected_set = set(selected)
        roots = [
            armature_obj.data.bones[name]
            for name in selected
            if not any(ancestor.name in selected_set for ancestor in armature_obj.data.bones[name].parent_recursive)
        ]
        names = set()
        for root in roots:
            names.add(root.name)
            names.update(child.name for child in root.children_recursive)
        return tuple(sorted(names))
    if scope_mode == "ACTIVE_BONE_COLLECTION":
        collection = getattr(armature_obj.data.collections, "active", None)
        return tuple(sorted(bone.name for bone in collection.bones)) if collection else ()
    raise ValueError(f"unsupported scope mode: {scope_mode}")


def _vec3(value) -> tuple[float, float, float]:
    result = tuple(float(component) for component in value)
    if len(result) != 3 or not all(math.isfinite(component) for component in result):
        raise ValueError("non-finite vec3")
    return result


def read_bone_states(armature_obj, names: tuple[str, ...]) -> tuple[BoneState, ...]:
    states = []
    for name in sorted(names):
        bone = armature_obj.data.bones[name]
        matrix = bone.matrix_local.copy()
        matrix3 = matrix.to_3x3()
        _, roll = bone.AxisRollFromMatrix(matrix3)
        metadata = tuple(
            key for key in ("orig_loc", "orig_quat", "post_quat") if key in bone
        )
        states.append(
            BoneState(
                name=bone.name,
                parent_name=bone.parent.name if bone.parent else None,
                child_names=tuple(sorted(child.name for child in bone.children)),
                head=_vec3(bone.head_local),
                tail=_vec3(bone.tail_local),
                roll=float(roll),
                matrix_local=tuple(float(matrix[row][column]) for row in range(4) for column in range(4)),
                local_x=_vec3(matrix3.col[0].normalized()),
                local_y=_vec3(matrix3.col[1].normalized()),
                local_z=_vec3(matrix3.col[2].normalized()),
                use_connect=bool(bone.use_connect),
                use_deform=bool(bone.use_deform),
                inherit_scale=str(bone.inherit_scale),
                use_inherit_rotation=bool(bone.use_inherit_rotation),
                bbone_segments=int(bone.bbone_segments),
                is_socket=bool(bone.get("is_socket", False)),
                importer_metadata_flags=metadata,
            )
        )
    return tuple(states)
