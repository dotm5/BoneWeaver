"""Scoped idempotent terminal and branch override helpers."""

from __future__ import annotations

from .canonical import sha256


def armature_structural_fingerprint(armature_obj):
    payload = tuple(
        (
            bone.name,
            bone.parent.name if bone.parent else None,
            tuple(float(value) for value in bone.head_local),
        )
        for bone in sorted(armature_obj.data.bones, key=lambda item: item.name)
    )
    return sha256((armature_obj.data.name, payload))


def _terminal_scope_matches(item, armature_data_name, fingerprint, bone_name, chain_id):
    return (
        item.armature_data_name == armature_data_name
        and item.armature_structural_fingerprint == fingerprint
        and item.bone_name == bone_name
        and item.chain_id == chain_id
    )


def upsert_terminal_override(
    collection,
    *,
    armature_data_name,
    armature_structural_fingerprint,
    bone_name,
    chain_id,
    mode,
    reference_object=None,
    direction=(0.0, 1.0, 0.0),
    length=0.0,
    mesh_object_name="",
    vertex_index=-1,
    enabled=True,
):
    item = next(
        (
            candidate for candidate in collection
            if _terminal_scope_matches(
                candidate, armature_data_name, armature_structural_fingerprint,
                bone_name, chain_id,
            )
        ),
        None,
    )
    if item is None:
        item = collection.add()
    else:
        pointer = item.as_pointer()
        duplicates = [
            index for index in range(len(collection))
            if collection[index].as_pointer() != pointer
            and _terminal_scope_matches(
                collection[index], armature_data_name,
                armature_structural_fingerprint, bone_name, chain_id,
            )
        ]
        for index in reversed(duplicates):
            collection.remove(index)
    item.armature_data_name = armature_data_name
    item.armature_structural_fingerprint = armature_structural_fingerprint
    item.bone_name = bone_name
    item.chain_id = chain_id
    item.mode = mode
    item.reference_object = reference_object
    item.direction = direction
    item.length = length
    item.mesh_object_name = mesh_object_name
    item.vertex_index = vertex_index
    item.enabled = enabled
    return item


def find_terminal_override(
    collection,
    *,
    armature_data_name,
    armature_structural_fingerprint,
    bone_name,
    chain_id,
):
    for item in collection:
        if (
            item.enabled
            and item.mode != "NONE"
            and _terminal_scope_matches(
                item, armature_data_name, armature_structural_fingerprint,
                bone_name, chain_id,
            )
        ):
            return item, False
    legacy = any(
        item.enabled
        and item.mode != "NONE"
        and item.bone_name == bone_name
        and not item.armature_data_name
        and not item.armature_structural_fingerprint
        for item in collection
    )
    return None, legacy


def _branch_scope_matches(item, armature_data_name, fingerprint, branch_bone_name):
    return (
        item.armature_data_name == armature_data_name
        and item.armature_structural_fingerprint == fingerprint
        and item.branch_bone_name == branch_bone_name
    )


def upsert_branch_override(
    collection,
    *,
    armature_data_name,
    armature_structural_fingerprint,
    branch_bone_name,
    selected_child_name,
    enabled=True,
):
    matches = [
        index for index, item in enumerate(collection)
        if _branch_scope_matches(
            item, armature_data_name, armature_structural_fingerprint,
            branch_bone_name,
        )
    ]
    if matches:
        item = collection[matches[0]]
        for index in reversed(matches[1:]):
            collection.remove(index)
    else:
        item = collection.add()
    item.armature_data_name = armature_data_name
    item.armature_structural_fingerprint = armature_structural_fingerprint
    item.branch_bone_name = branch_bone_name
    item.selected_child_name = selected_child_name
    item.enabled = enabled
    return item


def find_branch_override(
    collection,
    *,
    armature_data_name,
    armature_structural_fingerprint,
    branch_bone_name,
):
    for item in collection:
        if item.enabled and _branch_scope_matches(
            item, armature_data_name, armature_structural_fingerprint,
            branch_bone_name,
        ):
            return item, False
    legacy = any(
        item.enabled
        and item.branch_bone_name == branch_bone_name
        and not item.armature_data_name
        and not item.armature_structural_fingerprint
        for item in collection
    )
    return None, legacy


def remove_stale_overrides(settings, *, armature_data_name, armature_structural_fingerprint):
    removed = 0
    for collection in (settings.terminal_overrides, settings.branch_overrides):
        for index in reversed(range(len(collection))):
            item = collection[index]
            item_data_name = item.armature_data_name
            item_fingerprint = item.armature_structural_fingerprint
            if not item_data_name and not item_fingerprint:
                continue
            if item_data_name != armature_data_name or item_fingerprint != armature_structural_fingerprint:
                collection.remove(index)
                removed += 1
    return removed
