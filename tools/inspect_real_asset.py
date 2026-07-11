"""Read-only inventory for a loaded UECP real-asset blend file."""

from __future__ import annotations

import json

import bpy


def main():
    armatures = []
    for obj in sorted((item for item in bpy.data.objects if item.type == "ARMATURE"), key=lambda item: item.name):
        selected = tuple(sorted(bone.name for bone in obj.pose.bones if bone.select))
        armatures.append(
            {
                "object_name": obj.name,
                "data_name": obj.data.name,
                "bone_count": len(obj.data.bones),
                "selected_bone_count": len(selected),
                "selected_bones": selected,
                "bones": [
                    {
                        "name": bone.name,
                        "parent": bone.parent.name if bone.parent else None,
                        "children": sorted(child.name for child in bone.children),
                        "use_deform": bool(bone.use_deform),
                    }
                    for bone in sorted(obj.data.bones, key=lambda item: item.name)
                ],
                "active": bpy.context.view_layer.objects.active == obj,
            }
        )
    meshes = []
    for obj in sorted((item for item in bpy.data.objects if item.type == "MESH"), key=lambda item: item.name):
        modifiers = [
            {"name": modifier.name, "type": modifier.type, "object": getattr(getattr(modifier, "object", None), "name", None)}
            for modifier in obj.modifiers
        ]
        meshes.append(
            {
                "object_name": obj.name,
                "vertex_count": len(obj.data.vertices),
                "polygon_count": len(obj.data.polygons),
                "vertex_group_count": len(obj.vertex_groups),
                "modifiers": modifiers,
            }
        )
    payload = {
        "filepath": bpy.data.filepath,
        "armatures": armatures,
        "meshes": meshes,
        "uecp_texts": sorted(text.name for text in bpy.data.texts if text.name.startswith("UECP_")),
    }
    print("UECP_REAL_ASSET_INVENTORY=" + json.dumps(payload, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
