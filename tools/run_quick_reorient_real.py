"""Read-only real-asset acceptance for one-button Quick Reorient."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import sys
import traceback
from pathlib import Path

import bpy
from mathutils import Vector


_OPERATORS = {
    "UEFORMAT_AUTO": lambda: bpy.ops.boneweaver.quick_reorient_auto(),
    "LINKS_ONLY": lambda: bpy.ops.boneweaver.quick_reorient_links_only(),
    "HYBRID_MULTI_FEATURE": lambda: bpy.ops.boneweaver.quick_reorient_hybrid_auto(),
}


def _sha256(path: Path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest().upper()


def _activate(armature):
    if bpy.context.object and bpy.context.object.mode != "OBJECT":
        bpy.ops.object.mode_set(mode="OBJECT")
    bpy.ops.object.select_all(action="DESELECT")
    armature.hide_set(False)
    armature.hide_viewport = False
    armature.select_set(True)
    bpy.context.view_layer.objects.active = armature


def _state_map(states):
    return {state.bone_name: state for state in states}


def _roll_distance(first, second):
    return abs((float(first) - float(second) + math.pi) % (2.0 * math.pi) - math.pi)


def _states_match(before, after):
    before_map = _state_map(before)
    after_map = _state_map(after)
    if set(before_map) != set(after_map):
        return False
    for name, old in before_map.items():
        new = after_map[name]
        if (
            old.parent_name != new.parent_name
            or (Vector(old.head) - Vector(new.head)).length > 1.0e-7
            or (Vector(old.tail) - Vector(new.tail)).length > 1.0e-6
            or _roll_distance(old.roll, new.roll) > 1.0e-5
            or old.use_connect != new.use_connect
            or old.use_deform != new.use_deform
            or old.source_metadata_flags != new.source_metadata_flags
        ):
            return False
    return True


def _invariant_changes(before, after):
    before_map = _state_map(before)
    after_map = _state_map(after)
    names = sorted(set(before_map) | set(after_map))
    return {
        "bone_name_set_changed": set(before_map) != set(after_map),
        "head_changes": [
            name for name in names
            if name not in before_map or name not in after_map
            or (Vector(before_map[name].head) - Vector(after_map[name].head)).length > 1.0e-7
        ],
        "parent_changes": [
            name for name in names
            if name not in before_map or name not in after_map
            or before_map[name].parent_name != after_map[name].parent_name
        ],
    }


def _component_for_tokens(plan, tokens):
    def matches(name):
        segments = tuple(
            segment for segment in re.split(r"[^a-z0-9]+", name.casefold()) if segment
        )
        return any(
            any(segment.startswith(token) for segment in segments) for token in tokens
        )

    candidates = [
        component for component in plan.linked_components
        if len(component.bone_names) > 1
        and any(matches(name) for name in component.bone_names)
    ]
    return min(
        candidates,
        key=lambda item: (item.root_bone_name.casefold(), item.component_id),
    ) if candidates else None


def _native_selection_checks(armature, plan):
    categories = {
        "finger": ("finger", "thumb", "index", "middle", "pinky"),
        "hair": ("hair",),
        "ribbon": ("ribbon",),
        "spine": ("spine",),
    }
    checks = {}
    _activate(armature)
    for collection in armature.data.collections_all:
        collection.is_visible = True
        collection.is_solo = False
    for bone in armature.data.bones:
        bone.hide = False
        bone.hide_select = False
    for label, tokens in categories.items():
        component = _component_for_tokens(plan, tokens)
        if component is None:
            checks[label] = {"status": "NOT_FOUND", "expected": [], "actual": []}
            continue
        active_name = component.bone_names[len(component.bone_names) // 2]
        bpy.ops.object.mode_set(mode="EDIT")
        bpy.ops.armature.select_all(action="DESELECT")
        bpy.ops.object.mode_set(mode="OBJECT")
        for pose_bone in armature.pose.bones:
            pose_bone.select = pose_bone.name == active_name
        armature.data.bones.active = armature.data.bones[active_name]
        bpy.ops.object.mode_set(mode="EDIT")
        result = bpy.ops.armature.select_linked()
        actual = sorted(bone.name for bone in armature.data.edit_bones if bone.select)
        expected = sorted(component.bone_names)
        checks[label] = {
            "status": "PASS" if result == {"FINISHED"} and actual == expected else "FAIL",
            "active": active_name,
            "component_id": component.component_id,
            "expected": expected,
            "actual": actual,
        }
        bpy.ops.object.mode_set(mode="OBJECT")
    return checks


def run_loaded_scene(
    source: Path,
    output: Path,
    *,
    expected_adapter: str | None = None,
    mode: str = "UEFORMAT_AUTO",
):
    from boneweaver.core.quick_source_adapter import capture_quick_source
    from boneweaver.core.runtime_store import get_quick_plan

    source_hash_before = _sha256(source)
    armatures = sorted(
        (obj for obj in bpy.context.scene.objects if obj.type == "ARMATURE"),
        key=lambda obj: (
            bool(sum(len(bone.constraints) for bone in obj.pose.bones))
            or bool(obj.animation_data and obj.animation_data.drivers),
            -len(obj.data.bones),
            obj.name,
        ),
    )
    if not armatures:
        raise RuntimeError("real asset contains no Armature")
    armature = armatures[0]
    _activate(armature)
    before, _metadata = capture_quick_source(bpy.context, armature)
    first_apply = _OPERATORS[mode]()
    runtime = bpy.context.window_manager.boneweaver_runtime
    plan = get_quick_plan(runtime.quick_plan_id) if runtime.quick_plan_id else None
    if first_apply != {"FINISHED"} or plan is None:
        blockers = [issue.code for issue in plan.issues if issue.severity == "BLOCKER"] if plan else []
        raise RuntimeError(
            f"{mode} one-button conversion failed: "
            f"{first_apply}, {blockers}, {runtime.last_error}"
        )
    first_snapshot_name = runtime.quick_snapshot_text_name
    first_mutations = runtime.quick_mutation_count
    after_apply, _metadata = capture_quick_source(bpy.context, armature)
    invariants = _invariant_changes(before, after_apply)
    selections = _native_selection_checks(armature, plan)

    second_apply = _OPERATORS[mode]()
    second_plan = get_quick_plan(runtime.quick_plan_id)
    second_mutations = runtime.quick_mutation_count
    second_snapshot_name = runtime.quick_snapshot_text_name
    restore_second = bpy.ops.boneweaver.quick_reorient_restore()
    runtime.quick_snapshot_text_name = first_snapshot_name
    runtime.quick_state = "RESTORABLE"
    restore_first = bpy.ops.boneweaver.quick_reorient_restore()
    restored, _metadata = capture_quick_source(bpy.context, armature)
    source_hash_after = _sha256(source)
    snapshot = json.loads(bpy.data.texts[first_snapshot_name].as_string())
    failed_selection = [name for name, item in selections.items() if item["status"] == "FAIL"]
    success = bool(
        (expected_adapter is None or plan.source_adapter == expected_adapter)
        and plan.mode == mode
        and second_apply == {"FINISHED"}
        and second_plan.already_normalized
        and second_mutations == 0
        and restore_second == {"FINISHED"}
        and restore_first == {"FINISHED"}
        and _states_match(before, restored)
        and source_hash_before == source_hash_after
        and not invariants["bone_name_set_changed"]
        and not invariants["head_changes"]
        and not invariants["parent_changes"]
        and not failed_selection
    )
    payload = {
        "status": "PASS" if success else "FAIL",
        "source": str(source),
        "source_hash_before": source_hash_before,
        "source_hash_after": source_hash_after,
        "blender_version": bpy.app.version_string,
        "armature": armature.name,
        "mode": mode,
        "source_adapter": plan.source_adapter,
        "already_reoriented": plan.already_reoriented,
        "total_bones": len(plan.bone_states),
        "processed_bones": sum(not proposal.skipped for proposal in plan.proposals),
        "multi_feature_bones": sum(
            proposal.source.startswith("MULTI_FEATURE:")
            for proposal in plan.proposals
            if not proposal.skipped
        ),
        "ueformat_fallback_bones": sum(
            proposal.source.startswith("UEFORMAT_FALLBACK:")
            for proposal in plan.proposals
            if not proposal.skipped
        ),
        "skipped_sockets": sum(proposal.skip_reason == "SOCKET" for proposal in plan.proposals),
        "component_count": len(plan.linked_components),
        "connected_edges": snapshot.get("connected_edge_count", 0),
        "first_mutation_count": first_mutations,
        "native_linked_selection": selections,
        "integrity": invariants,
        "mesh_digest_count": len(snapshot.get("mesh_digests", {})),
        "idempotence": {
            "already_normalized": second_plan.already_normalized,
            "second_mutation_count": second_mutations,
        },
        "restore_exact": _states_match(before, restored),
        "issues": [issue.code for issue in plan.issues],
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print("BONEWEAVER_QUICK_REAL_RESULT", json.dumps(payload, ensure_ascii=False, sort_keys=True))
    return 0 if success else 1


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--mode", choices=tuple(_OPERATORS), default="UEFORMAT_AUTO")
    args = parser.parse_args(argv)
    source = Path(args.input).resolve(strict=True)
    root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(root))
    import boneweaver
    boneweaver.register()
    try:
        return run_loaded_scene(
            source,
            Path(args.output).resolve(),
            mode=args.mode,
        )
    finally:
        boneweaver.unregister()


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
