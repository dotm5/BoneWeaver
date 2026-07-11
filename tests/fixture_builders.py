from __future__ import annotations

import bpy


def clear_scene() -> None:
    if bpy.context.object and bpy.context.object.mode != "OBJECT":
        bpy.ops.object.mode_set(mode="OBJECT")
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for collection in (bpy.data.meshes, bpy.data.armatures, bpy.data.actions):
        for datablock in tuple(collection):
            if datablock.users == 0:
                collection.remove(datablock)


def make_chain(*, name: str = "Rig", count: int = 3, selected: tuple[str, ...] | None = None):
    data = bpy.data.armatures.new(f"{name}Data")
    obj = bpy.data.objects.new(name, data)
    bpy.context.scene.collection.objects.link(obj)
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")
    parent = None
    names = []
    for index in range(count):
        bone = data.edit_bones.new(f"Bone_{index}")
        bone.head = (0.0, float(index), 0.0)
        bone.tail = (0.0, float(index) + 0.2, 0.0)
        bone.parent = parent
        bone.use_connect = False
        names.append(bone.name)
        parent = bone
    bpy.ops.object.mode_set(mode="OBJECT")
    selected_names = set(selected if selected is not None else names)
    for pose_bone in obj.pose.bones:
        pose_bone.select = pose_bone.name in selected_names
    if hasattr(data.bones, "active"):
        data.bones.active = data.bones[names[0]]
    return obj


def make_bound_mesh(armature, *, name: str = "Mesh"):
    data = bpy.data.meshes.new(f"{name}Data")
    data.from_pydata([(0, 0, 0), (0, 1, 0), (0.2, 1, 0)], [], [(0, 1, 2)])
    obj = bpy.data.objects.new(name, data)
    bpy.context.scene.collection.objects.link(obj)
    group = obj.vertex_groups.new(name="Bone_0")
    group.add([0, 1, 2], 1.0, "REPLACE")
    modifier = obj.modifiers.new(name="Armature", type="ARMATURE")
    modifier.object = armature
    return obj, modifier


def make_bag_branch(*, name: str = "BranchRig"):
    data = bpy.data.armatures.new(f"{name}Data")
    obj = bpy.data.objects.new(name, data)
    bpy.context.scene.collection.objects.link(obj)
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    specs = (
        ("bag_r_02", None, (0, 0, 0)),
        ("bag_r_03", "bag_r_02", (0, 1, 0)),
        ("bag_r_04", "bag_r_03", (0, 2, 0)),
        ("bag_r_05", "bag_r_04", (0, 3, 0)),
        ("bag_r_06", "bag_r_05", (0, 4, 0)),
        ("bag_r_03a_01", "bag_r_03", (0.5, 1.7, 0)),
        ("bag_r_03a_02", "bag_r_03a_01", (1.0, 2.4, 0)),
    )
    bpy.ops.object.mode_set(mode="EDIT")
    for bone_name, parent_name, head in specs:
        bone = data.edit_bones.new(bone_name)
        bone.head = head
        bone.tail = (head[0] + 0.15, head[1] + 0.15, head[2])
        bone.parent = data.edit_bones.get(parent_name) if parent_name else None
        bone.use_connect = False
    data.edit_bones["bag_r_03a_01"].use_connect = True
    bpy.ops.object.mode_set(mode="OBJECT")
    for pose_bone in obj.pose.bones:
        pose_bone.select = True
    data.bones.active = data.bones["bag_r_02"]
    return obj
