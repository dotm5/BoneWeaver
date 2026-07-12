"""Formal G01/G02 acceptance on an isolated UEFormat asset copy."""

from __future__ import annotations

import argparse
import hashlib
import importlib
import json
import os
import sys
import traceback
from pathlib import Path

import bpy


def _arguments():
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--module-root", required=True)
    parser.add_argument("--output-dir", required=True)
    return parser.parse_args(argv)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _bone_geometry(armature):
    return tuple(
        (
            bone.name,
            bone.parent.name if bone.parent else None,
            tuple(float(value) for value in bone.head_local),
            tuple(float(value) for value in bone.tail_local),
            bool(bone.use_connect),
        )
        for bone in armature.data.bones
    )


def _selection(armature):
    return tuple(
        pose_bone.name for pose_bone in armature.pose.bones if pose_bone.select
    )


def _weight_digest(mesh):
    return tuple(
        (
            vertex.index,
            tuple(sorted((item.group, float(item.weight)) for item in vertex.groups)),
        )
        for vertex in mesh.data.vertices
    )


def _select(armature, names, *, active):
    requested = set(names)
    for pose_bone in armature.pose.bones:
        pose_bone.select = pose_bone.name in requested
    armature.data.bones.active = armature.data.bones[active]


def main() -> int:
    args = _arguments()
    source_model = Path(args.input).resolve(strict=True)
    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    report_path = output_dir / "real-acceptance.json"
    source_blend = output_dir / "source-import.blend"
    converted_blend = output_dir / "converted.blend"

    root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(root))
    sys.path.insert(0, str(Path(args.module_root).resolve(strict=True)))
    ueformat = importlib.import_module("io_scene_ueformat")
    ueformat.register()
    import boneweaver
    from boneweaver.controllers.hierarchy_inspection import HierarchyInspectionController
    from boneweaver.controllers.hierarchy_overlay import HierarchyOverlayController
    from boneweaver.controllers.semantic_discovery import SemanticDiscoveryController
    from boneweaver.core.export_contract import file_signature
    from boneweaver.core.runtime_store import (
        get_performance,
        get_plan,
        get_semantic_discovery,
    )
    from boneweaver.core.serialization import to_data

    boneweaver.register()
    report = {
        "status": "STARTED",
        "source_model": str(source_model),
        "source_model_sha256": _sha256(source_model),
        "blender_version": bpy.app.version_string,
    }
    exit_code = 1
    try:
        before_objects = set(bpy.data.objects.keys())
        imported = bpy.ops.uf.import_uemodel(
            directory=str(source_model.parent), files=[{"name": source_model.name}],
        )
        if imported != {"FINISHED"}:
            raise RuntimeError(f"UEFormat import failed: {imported!r}")
        armatures = [
            item for item in bpy.data.objects
            if item.name not in before_objects and item.type == "ARMATURE"
        ]
        meshes = [
            item for item in bpy.data.objects
            if item.name not in before_objects and item.type == "MESH"
        ]
        if len(armatures) != 1 or len(meshes) != 1:
            raise RuntimeError(
                f"expected one Armature/Mesh, got {len(armatures)}/{len(meshes)}"
            )
        armature = armatures[0]
        mesh = meshes[0]
        bpy.ops.object.select_all(action="DESELECT")
        armature.select_set(True)
        bpy.context.view_layer.objects.active = armature
        report["armature"] = armature.name
        report["bone_count"] = len(armature.data.bones)
        report["mesh_vertex_count"] = len(mesh.data.vertices)

        geometry_before = _bone_geometry(armature)
        weights_before = _weight_digest(mesh)
        _select(armature, ("hair_l_01",), active="hair_l_01")
        semantic_selection_before = _selection(armature)
        semantic_result = bpy.ops.boneweaver.discover_secondary_chains()
        if semantic_result != {"FINISHED"}:
            raise RuntimeError(
                bpy.context.window_manager.boneweaver_runtime.last_error
                or "semantic discovery failed"
            )
        semantic = get_semantic_discovery()
        if semantic is None:
            raise RuntimeError("semantic session missing")
        main_names = {
            item.bone_name
            for item in semantic.plan.bone_evidence
            if item.category == "MAIN_SKELETON"
        }
        auto_or_suggest_main = tuple(sorted(
            item.bone_name
            for item in semantic.plan.bone_evidence
            if item.bone_name in main_names
            and item.discovery_class in {"AUTO_INCLUDE", "SUGGEST_INCLUDE"}
        ))
        report["semantic"] = {
            "operator": sorted(semantic_result),
            "chain_count": len(semantic.plan.chains),
            "class_counts": {
                value: sum(chain.discovery_class == value for chain in semantic.plan.chains)
                for value in ("AUTO_INCLUDE", "SUGGEST_INCLUDE", "AMBIGUOUS")
            },
            "hair_roots": sorted(
                chain.root_bone_name
                for chain in semantic.plan.chains
                if chain.category in {"HAIR", "RIBBON"}
            ),
            "main_auto_or_suggest": auto_or_suggest_main,
            "selection_unchanged": _selection(armature) == semantic_selection_before,
            "geometry_unchanged": _bone_geometry(armature) == geometry_before,
            "weights_unchanged": _weight_digest(mesh) == weights_before,
        }
        if auto_or_suggest_main:
            raise RuntimeError(f"main skeleton semantic false positives: {auto_or_suggest_main}")
        if not report["semantic"]["hair_roots"]:
            raise RuntimeError("no real hair/ribbon semantic chains were discovered")
        if not all((
            report["semantic"]["selection_unchanged"],
            report["semantic"]["geometry_unchanged"],
            report["semantic"]["weights_unchanged"],
        )):
            raise RuntimeError("semantic discovery mutated scene state")
        SemanticDiscoveryController.clear(bpy.context)

        runtime = bpy.context.window_manager.boneweaver_runtime
        runtime.hierarchy_selection_mode = "LINEAR_CHAIN"
        _select(armature, ("Bip001-L-Finger0",), active="Bip001-L-Finger0")
        finger_selection_before = _selection(armature)
        finger_plan = HierarchyInspectionController.inspect(bpy.context)
        finger_cache = HierarchyOverlayController.build_cache(bpy.context)
        report["finger_inspection"] = {
            "selected": finger_plan.selected_bone_names,
            "parent": finger_plan.parent_context_name,
            "branches": finger_plan.branch_bone_names,
            "roles": sorted({item.role for item in finger_cache.labels}),
            "selection_unchanged": _selection(armature) == finger_selection_before,
        }
        expected_finger = (
            "Bip001-L-Finger0", "Bip001-L-Finger01", "Bip001-L-Finger02",
        )
        if finger_plan.selected_bone_names != expected_finger:
            raise RuntimeError(
                f"finger hierarchy mismatch: {finger_plan.selected_bone_names!r}"
            )
        if finger_plan.parent_context_name != "Bip001-L-Hand":
            raise RuntimeError("finger parent context mismatch")
        if not report["finger_inspection"]["selection_unchanged"]:
            raise RuntimeError("hierarchy Inspect changed selection")
        HierarchyInspectionController.clear(bpy.context)

        _select(armature, ("Bip001-Spine",), active="Bip001-Spine")
        spine_plan = HierarchyInspectionController.inspect(bpy.context)
        report["spine_inspection"] = {
            "selected": spine_plan.selected_bone_names,
            "branches": spine_plan.branch_bone_names,
            "side_roots": spine_plan.side_branch_root_names,
            "issues": spine_plan.issue_codes,
        }
        if spine_plan.selected_bone_names != ("Bip001-Spine",):
            raise RuntimeError("spine linear inspection did not stop at the first branch")
        if "BONEWEAVER_HIERARCHY_BRANCH_AMBIGUOUS" not in spine_plan.issue_codes:
            raise RuntimeError("spine branch ambiguity was not reported")
        HierarchyInspectionController.clear(bpy.context)

        # A generated image has no external payload for Blender to pack, so it
        # does not exercise the non-empty packed-image export/reopen path. Save
        # a real PNG first, reload it, then remove the external file after the
        # packed payload has been embedded in the .blend.
        fixture_path = output_dir / "packed-image-fixture.png"
        image = bpy.data.images.new("BONEWEAVER_Real_Acceptance_Packed_Source", width=1, height=1)
        image.generated_color = (0.2, 0.6, 1.0, 1.0)
        image.filepath_raw = str(fixture_path)
        image.file_format = "PNG"
        image.save()
        bpy.data.images.remove(image)
        image = bpy.data.images.load(str(fixture_path))
        image.name = "BONEWEAVER_Real_Acceptance_Packed"
        # Keep the image datablock in the saved file even though this acceptance
        # fixture deliberately does not alter the imported asset's materials.
        image.use_fake_user = True
        image.pack()
        if not image.packed_file:
            raise RuntimeError("packed-image fixture did not create an embedded payload")
        fixture_path.unlink()
        bpy.ops.wm.save_as_mainfile(filepath=str(source_blend))
        source_before = file_signature(source_blend)

        hair_chain = ("hair_l_01", "hair_l_02", "hair_l_03", "hair_l_04")
        _select(armature, hair_chain, active=hair_chain[0])
        settings = bpy.context.scene.boneweaver_settings
        settings.scope_mode = "SELECTED_BONES"
        settings.mesh_scope = "ALL_ASSOCIATED_MESHES"
        settings.validation_tolerance_mode = "AUTO_PRODUCTION"
        analyze_result = bpy.ops.boneweaver.analyze()
        plan = get_plan(runtime.plan_id)
        blockers = tuple(
            item.code for item in plan.issues if item.severity == "BLOCKER"
        )
        report["conversion"] = {
            "analyze": sorted(analyze_result),
            "plan_id": plan.plan_id,
            "schema_version": plan.schema_version,
            "algorithm_version": plan.algorithm_version,
            "target_count": len(plan.bone_states),
            "proposal_count": len(plan.proposals),
            "tip_helpers": [to_data(item) for item in plan.tip_helpers],
            "blockers": blockers,
            "warnings": [item.code for item in plan.issues if item.severity == "WARNING"],
            "performance": get_performance(plan.plan_id),
        }
        if blockers:
            raise RuntimeError(f"real Analyze blockers: {blockers}")
        apply_result = bpy.ops.boneweaver.apply(plan_id=runtime.plan_id)
        report["conversion"]["apply"] = sorted(apply_result)
        report["conversion"]["apply_error"] = runtime.last_error
        if apply_result != {"FINISHED"}:
            raise RuntimeError(runtime.last_error or "real Apply failed")
        report["conversion"]["performance"] = get_performance(plan.plan_id)

        export_result = bpy.ops.boneweaver.export_conversion(filepath=str(converted_blend))
        report["conversion"]["export"] = sorted(export_result)
        report["conversion"]["export_error"] = runtime.last_error
        if export_result != {"FINISHED"}:
            raise RuntimeError(runtime.last_error or "real export failed")
        audit = json.loads((output_dir / "conversion-audit.json").read_text("utf-8"))
        reopen = json.loads((output_dir / "reopen-validation.json").read_text("utf-8"))
        report["conversion"]["audit"] = audit
        report["conversion"]["reopen"] = reopen
        report["source_blend"] = str(source_blend)
        report["converted_blend"] = str(converted_blend)
        report["source_unchanged"] = file_signature(source_blend) == source_before
        report["packed_image_count"] = audit.get("packed_image_count")
        if not report["source_unchanged"]:
            raise RuntimeError("disposable source blend changed during export")
        if not reopen.get("success"):
            raise RuntimeError("independent reopen validation failed")
        if int(audit.get("packed_image_count", 0)) < 1:
            raise RuntimeError("non-empty packed-image path was not exercised")

        report["status"] = "PASS"
        exit_code = 0
    except Exception as error:
        report["status"] = "FAIL"
        report["error"] = str(error)
        report["traceback"] = traceback.format_exc()
    finally:
        try:
            HierarchyInspectionController.clear(bpy.context)
        except Exception:
            pass
        report_path.write_text(
            json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
            encoding="utf-8",
        )
        print("BONEWEAVER_G01_G02_REAL_RESULT", report["status"], report.get("error", ""))
        boneweaver.unregister()
        ueformat.unregister()
        sys.stdout.flush()
        sys.stderr.flush()
        os._exit(exit_code)


if __name__ == "__main__":
    main()
