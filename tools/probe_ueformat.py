"""Import one UEFormat model in factory-startup Blender and emit a JSON snapshot."""

from __future__ import annotations

import argparse
import importlib
import json
import math
import os
import sys
import traceback
from pathlib import Path

import bpy


def _args() -> argparse.Namespace:
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument(
        "--module-root",
        help="Directory containing an isolated io_scene_ueformat package copy",
    )
    return parser.parse_args(argv)


def _vec3(value: object) -> list[float]:
    result = [float(component) for component in value]
    if len(result) != 3 or not all(math.isfinite(component) for component in result):
        raise ValueError(f"expected finite vec3, got {result!r}")
    return result


def _armature_snapshot(obj: bpy.types.Object) -> dict[str, object]:
    bones = []
    for bone in sorted(obj.data.bones, key=lambda item: item.name):
        matrix = bone.matrix_local.to_3x3()
        bones.append(
            {
                "name": bone.name,
                "parent": bone.parent.name if bone.parent else None,
                "children": sorted(child.name for child in bone.children),
                "head": _vec3(bone.head_local),
                "tail": _vec3(bone.tail_local),
                "local_x": _vec3(matrix.col[0]),
                "local_y": _vec3(matrix.col[1]),
                "local_z": _vec3(matrix.col[2]),
                "use_connect": bool(bone.use_connect),
                "use_deform": bool(bone.use_deform),
            }
        )
    return {
        "object_name": obj.name,
        "data_name": obj.data.name,
        "bone_count": len(bones),
        "root_bones": sorted(bone.name for bone in obj.data.bones if bone.parent is None),
        "bones": bones,
    }


def main() -> int:
    args = _args()
    source = Path(args.input).resolve(strict=True)
    output = Path(args.output).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)

    if args.module_root:
        module_root = Path(args.module_root).resolve(strict=True)
        sys.path.insert(0, str(module_root))
        extension = importlib.import_module("io_scene_ueformat")
    else:
        extension = importlib.import_module("bl_ext.user_default.io_scene_ueformat")
    extension.register()
    try:
        existing_object_names = frozenset(bpy.data.objects.keys())
        result = bpy.ops.uf.import_uemodel(
            directory=str(source.parent),
            files=[{"name": source.name}],
        )
        if "FINISHED" not in result:
            raise RuntimeError(f"UEFormat import returned {result!r}")

        armatures = sorted(
            (
                obj
                for obj in bpy.data.objects
                if obj.name not in existing_object_names and obj.type == "ARMATURE"
            ),
            key=lambda obj: obj.name,
        )
        meshes = sorted(
            (
                obj
                for obj in bpy.data.objects
                if obj.name not in existing_object_names and obj.type == "MESH"
            ),
            key=lambda obj: obj.name,
        )
        if not armatures or not meshes:
            raise RuntimeError(
                "UEFormat import did not create both an Armature and a Mesh: "
                f"armatures={len(armatures)}, meshes={len(meshes)}"
            )
        payload = {
            "source": str(source),
            "blender_version": bpy.app.version_string,
            "blender_version_tuple": list(bpy.app.version),
            "ueformat_module": extension.__name__,
            "ueformat_file": str(Path(extension.__file__).resolve()),
            "armature_count": len(armatures),
            "mesh_count": len(meshes),
            "armatures": [_armature_snapshot(obj) for obj in armatures],
            "meshes": [
                {
                    "object_name": obj.name,
                    "data_name": obj.data.name,
                    "vertex_count": len(obj.data.vertices),
                    "polygon_count": len(obj.data.polygons),
                    "vertex_group_count": len(obj.vertex_groups),
                    "armature_modifiers": [
                        {
                            "name": modifier.name,
                            "target": modifier.object.name if modifier.object else None,
                        }
                        for modifier in obj.modifiers
                        if modifier.type == "ARMATURE"
                    ],
                }
                for obj in meshes
            ],
        }
        output.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        print(
            "BONEWEAVER_UEFORMAT_PROBE_OK",
            json.dumps(
                {
                    "armatures": len(armatures),
                    "meshes": len(meshes),
                    "output": str(output),
                },
                sort_keys=True,
            ),
        )
        return 0
    finally:
        extension.unregister()


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except SystemExit:
        raise
    except BaseException:  # Blender otherwise reports script errors with process code 0.
        traceback.print_exc()
        sys.stdout.flush()
        sys.stderr.flush()
        os._exit(1)
