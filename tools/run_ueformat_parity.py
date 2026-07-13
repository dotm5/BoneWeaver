"""A/B geometry parity between a fixed UEFormat revision and BoneWeaver Stage A."""

from __future__ import annotations

import argparse
import json
import math
import os
import sys
import traceback
from pathlib import Path

import bpy
from mathutils import Vector


UEFORMAT_AUDIT_COMMIT = "8da96d65f669ca688dbf7c0141f800605a6c16e6"


def _args():
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--module-root", required=True)
    return parser.parse_args(argv)


def _clear_scene():
    if bpy.context.object and bpy.context.object.mode != "OBJECT":
        bpy.ops.object.mode_set(mode="OBJECT")
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for collection in (bpy.data.meshes, bpy.data.armatures):
        for datablock in tuple(collection):
            if datablock.users == 0:
                collection.remove(datablock)


def _import(source, *, reorient):
    bpy.context.scene.uf_settings.reorient_bones = reorient
    result = bpy.ops.uf.import_uemodel(
        directory=str(source.parent),
        files=[{"name": source.name}],
    )
    if result != {"FINISHED"}:
        raise RuntimeError(f"UEFormat import failed: {result}")
    armatures = [obj for obj in bpy.context.scene.objects if obj.type == "ARMATURE"]
    if len(armatures) != 1:
        raise RuntimeError(f"expected one Armature, got {len(armatures)}")
    return armatures[0]


def _geometry(armature):
    result = {}
    for bone in armature.data.bones:
        segment = bone.tail_local - bone.head_local
        result[bone.name] = {
            "head": tuple(float(value) for value in bone.head_local),
            "tail": tuple(float(value) for value in bone.tail_local),
            "direction": (
                tuple(float(value) for value in segment.normalized())
                if segment.length
                else (0.0, 0.0, 0.0)
            ),
            "length": float(segment.length),
            "parent": bone.parent.name if bone.parent else None,
            "socket": bool(bone.get("is_socket", False)),
        }
    return result


def main():
    args = _args()
    source = Path(args.input).resolve(strict=True)
    output = Path(args.output).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    root = Path(__file__).resolve().parents[1]
    module_root = Path(args.module_root).resolve(strict=True)
    sys.path.insert(0, str(module_root))
    sys.path.insert(0, str(root))

    import importlib

    extension = importlib.import_module("io_scene_ueformat")
    extension.register()
    import boneweaver
    from boneweaver.core.quick_reorient import build_quick_reorient_plan
    from boneweaver.core.quick_transaction import apply_quick_plan, restore_quick_snapshot
    from tools.run_quick_reorient_real import _activate

    try:
        ueformat_armature = _import(source, reorient=True)
        ueformat_geometry = _geometry(ueformat_armature)
        _clear_scene()

        source_armature = _import(source, reorient=False)
        source_geometry = _geometry(source_armature)
        boneweaver.register()
        try:
            _activate(source_armature)
            plan = build_quick_reorient_plan(
                bpy.context, connect_linear_chains=False
            )
            if plan is None:
                raise RuntimeError("BoneWeaver did not resolve the imported Armature")
            blockers = [issue.code for issue in plan.issues if issue.severity == "BLOCKER"]
            if blockers:
                raise RuntimeError(f"BoneWeaver Stage A blockers: {blockers}")
            transaction = apply_quick_plan(bpy.context, plan)
            if not transaction.success:
                raise RuntimeError(
                    "BoneWeaver Stage A failed: "
                    f"{transaction.error}; issues={transaction.validation_issues}"
                )
            boneweaver_geometry = _geometry(source_armature)
            restored, restore_error = restore_quick_snapshot(
                bpy.context, transaction.snapshot_text_name
            )
            if not restored:
                raise RuntimeError(f"BoneWeaver restore failed: {restore_error}")
        finally:
            boneweaver.unregister()

        direction_errors = {}
        length_errors = {}
        head_errors = {}
        socket_errors = {}
        parent_errors = []
        comparable_names = {
            proposal.bone_name for proposal in plan.proposals if not proposal.skipped
        }
        extra_socket_adapter_names = {
            name
            for name in ueformat_geometry
            if name not in comparable_names and not ueformat_geometry[name]["socket"]
        }
        adapter_affected_parents = {
            state.bone_name
            for state in plan.bone_states
            if any(child in extra_socket_adapter_names for child in state.child_names)
        }
        for name, expected in ueformat_geometry.items():
            actual = boneweaver_geometry[name]
            source_state = source_geometry[name]
            if expected["parent"] != actual["parent"]:
                parent_errors.append(name)
            head_errors[name] = (Vector(expected["head"]) - Vector(actual["head"])).length
            if name in adapter_affected_parents:
                continue
            if expected["socket"] or name not in comparable_names:
                socket_errors[name] = max(
                    (Vector(source_state["head"]) - Vector(actual["head"])).length,
                    (Vector(source_state["tail"]) - Vector(actual["tail"])).length,
                    abs(source_state["length"] - actual["length"]),
                )
                continue
            expected_direction = Vector(expected["direction"])
            actual_direction = Vector(actual["direction"])
            dot = max(-1.0, min(1.0, expected_direction.dot(actual_direction)))
            direction_errors[name] = math.degrees(math.acos(dot))
            length_errors[name] = abs(expected["length"] - actual["length"])

        max_direction = max(direction_errors.values(), default=0.0)
        max_length = max(length_errors.values(), default=0.0)
        max_head = max(head_errors.values(), default=0.0)
        max_socket = max(socket_errors.values(), default=0.0)
        success = bool(
            max_direction <= 0.05
            and max_length <= 2.0e-7
            and max_head <= 1.0e-7
            and max_socket <= 1.0e-7
            and not parent_errors
        )
        payload = {
            "status": "PASS" if success else "FAIL",
            "source": str(source),
            "ueformat_commit": UEFORMAT_AUDIT_COMMIT,
            "ueformat_version": "1.0.0",
            "ueformat_license": "GPL-3.0-or-later",
            "comparison_bones": len(direction_errors),
            "socket_bones": len(socket_errors),
            "extra_socket_adapter_names": sorted(extra_socket_adapter_names),
            "excluded_parents_due_extra_socket_adapter": sorted(adapter_affected_parents),
            "largest_direction_errors": sorted(
                direction_errors.items(), key=lambda item: (-item[1], item[0])
            )[:10],
            "largest_length_errors": sorted(
                length_errors.items(), key=lambda item: (-item[1], item[0])
            )[:10],
            "maximum_direction_error_degrees": max_direction,
            "maximum_length_error": max_length,
            "maximum_head_error": max_head,
            "maximum_socket_error": max_socket,
            "parent_errors": parent_errors,
            "known_differences": [
                "BoneWeaver uses align_roll minimal twist",
                "BoneWeaver does not rewrite UEFormat post_quat animation metadata",
                "Native linked-chain reconstruction was disabled for this parity comparison",
            ],
        }
        output.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        print(
            "BONEWEAVER_UEFORMAT_PARITY_RESULT",
            json.dumps(payload, ensure_ascii=False, sort_keys=True),
        )
        return 0 if success else 1
    finally:
        extension.unregister()


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except SystemExit as error:
        sys.stdout.flush()
        sys.stderr.flush()
        os._exit(int(error.code or 0))
    except BaseException:
        traceback.print_exc()
        sys.stdout.flush()
        sys.stderr.flush()
        os._exit(1)
