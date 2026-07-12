"""Run read-only Analyze and conditional Apply/Validate/Restore on one UEFormat asset."""

from __future__ import annotations

import argparse
import importlib
import json
import os
import sys
import traceback
from pathlib import Path

import bpy


def main() -> int:
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--module-root", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--chain", required=True, help="Comma-separated bone names")
    parser.add_argument("--epsilon-factor", type=float)
    args = parser.parse_args(argv)
    source = Path(args.input).resolve(strict=True)
    output = Path(args.output).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(root))
    sys.path.insert(0, str(Path(args.module_root).resolve(strict=True)))

    ueformat = importlib.import_module("io_scene_ueformat")
    ueformat.register()
    import boneweaver
    from boneweaver.core.runtime_store import get_plan, get_report

    boneweaver.register()
    try:
        before_names = frozenset(bpy.data.objects.keys())
        result = bpy.ops.uf.import_uemodel(
            directory=str(source.parent), files=[{"name": source.name}]
        )
        if "FINISHED" not in result:
            raise RuntimeError(f"UEFormat import returned {result!r}")
        armatures = [obj for obj in bpy.data.objects if obj.name not in before_names and obj.type == "ARMATURE"]
        if len(armatures) != 1:
            raise RuntimeError(f"expected one imported Armature, got {len(armatures)}")
        armature = armatures[0]
        bpy.ops.object.select_all(action="DESELECT")
        armature.select_set(True)
        bpy.context.view_layer.objects.active = armature
        requested = tuple(name.strip() for name in args.chain.split(",") if name.strip())
        missing = tuple(name for name in requested if name not in armature.pose.bones)
        if missing:
            raise RuntimeError(f"chain bones missing: {missing}")
        for pose_bone in armature.pose.bones:
            pose_bone.select = pose_bone.name in requested
        if args.epsilon_factor is not None:
            bpy.context.scene.boneweaver_settings.position_epsilon_factor = args.epsilon_factor

        object_count = len(bpy.data.objects)
        bone_count = len(armature.data.bones)
        analyze_result = bpy.ops.boneweaver.analyze()
        runtime = bpy.context.window_manager.boneweaver_runtime
        plan = get_plan(runtime.plan_id)
        payload = {
            "source": str(source),
            "blender_version": bpy.app.version_string,
            "chain": requested,
            "position_epsilon_factor": bpy.context.scene.boneweaver_settings.position_epsilon_factor,
            "analyze_result": sorted(analyze_result),
            "plan_id": plan.plan_id,
            "graph_id": plan.physics_graph.graph_id,
            "blockers": [issue.code for issue in plan.issues if issue.severity == "BLOCKER"],
            "warnings": [issue.code for issue in plan.issues if issue.severity == "WARNING"],
            "real_nodes": sum(node.kind == "REAL_BONE" for node in plan.physics_graph.nodes),
            "virtual_tips": sum(node.kind == "VIRTUAL_TIP" for node in plan.physics_graph.nodes),
            "hierarchy_edges": sum(edge.kind == "HIERARCHY_SEGMENT" for edge in plan.physics_graph.edges),
            "object_count_unchanged_after_analyze": len(bpy.data.objects) == object_count,
            "bone_count_unchanged_after_analyze": len(armature.data.bones) == bone_count,
            "apply_result": "NOT_RUN_BLOCKED",
            "restore_result": "NOT_RUN",
        }
        if not payload["blockers"]:
            apply_result = bpy.ops.boneweaver.apply(plan_id=runtime.plan_id)
            payload["apply_result"] = sorted(apply_result)
            payload["apply_error"] = runtime.last_error
            payload["snapshot_text_name"] = runtime.snapshot_text_name
            if runtime.snapshot_text_name in bpy.data.texts:
                payload["snapshot"] = json.loads(bpy.data.texts[runtime.snapshot_text_name].as_string())
            if "FINISHED" in apply_result:
                bpy.ops.boneweaver.validate()
                payload["diagnostic"] = get_report()
                restore_result = bpy.ops.boneweaver.restore_snapshot(snapshot_text_name=runtime.snapshot_text_name)
                payload["restore_result"] = sorted(restore_result)
                payload["object_count_unchanged_after_restore"] = len(bpy.data.objects) == object_count
                payload["bone_count_unchanged_after_restore"] = len(armature.data.bones) == bone_count
        output.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print("BONEWEAVER_REAL_SMOKE_OK", json.dumps({"output": str(output), "blockers": payload["blockers"], "apply": payload["apply_result"]}, ensure_ascii=True))
        return 0
    finally:
        boneweaver.unregister()
        ueformat.unregister()


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except SystemExit:
        raise
    except BaseException:
        traceback.print_exc()
        sys.stdout.flush()
        sys.stderr.flush()
        os._exit(1)
