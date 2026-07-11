"""Formal 85-bone x1.blend backend-hardening regression pipeline."""

from __future__ import annotations

import dataclasses
import json
import os
import sys
import traceback
from pathlib import Path

import bpy


TARGET_PREFIXES = ("bag_", "chest_", "cloak_", "earring_", "hair_", "part_", "ribbon_")


def main():
    root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(root))
    import ue_chain_prep
    from ue_chain_prep.core.export_contract import file_signature, load_snapshot_payload
    from ue_chain_prep.core.runtime_store import get_performance, get_plan
    from ue_chain_prep.core.serialization import to_data

    output_dir = root / "test-output" / "backend-hardening-real-model"
    output_dir.mkdir(parents=True, exist_ok=True)
    report_path = output_dir / "real-run.json"
    output_blend = output_dir / "x1-uecp-converted.blend"
    source = Path(bpy.data.filepath)
    source_before = file_signature(source)
    result = {
        "source_path": str(source),
        "source_sha256_before": source_before[0],
        "source_timestamp_before": source_before[1],
        "output_blend": str(output_blend),
        "status": "STARTED",
    }
    exit_code = 1
    try:
        ue_chain_prep.register()
        armature = next(obj for obj in bpy.context.scene.objects if obj.type == "ARMATURE")
        bpy.context.view_layer.objects.active = armature
        armature.select_set(True)
        targets = tuple(sorted(bone.name for bone in armature.pose.bones if bone.name.startswith(TARGET_PREFIXES)))
        for bone in armature.pose.bones:
            bone.select = bone.name in targets
        result["target_bones"] = targets
        result["target_bone_count"] = len(targets)
        if len(targets) != 85:
            raise RuntimeError(f"expected 85 target bones, got {len(targets)}")
        settings = bpy.context.scene.uecp_settings
        settings.scope_mode = "SELECTED_BONES"
        settings.mesh_scope = "ALL_ASSOCIATED_MESHES"
        settings.validation_tolerance_mode = "AUTO_PRODUCTION"
        settings.branch_resolution_mode = "AUTO_MAIN_PATH"
        settings.candidate_direction_merge_angle_degrees = 7.5
        settings.terminal_overrides.clear()
        settings.branch_overrides.clear()
        analyze_result = bpy.ops.uecp.analyze()
        runtime = bpy.context.window_manager.uecp_runtime
        result["analyze_operator"] = sorted(analyze_result)
        plan = get_plan(runtime.plan_id)
        result["plan_id"] = plan.plan_id
        result["graph_id"] = plan.physics_graph.graph_id
        result["algorithm_version"] = plan.algorithm_version
        result["schema_version"] = plan.schema_version
        result["issues"] = [to_data(issue) for issue in plan.issues]
        result["issue_counts"] = {
            severity: sum(issue.severity == severity for issue in plan.issues)
            for severity in ("INFO", "WARNING", "BLOCKER")
        }
        result["terminal_counts"] = {
            resolution_class: sum(solution.resolution_class == resolution_class for solution in plan.terminal_solutions)
            for resolution_class in ("AUTO_CONFIDENT", "AUTO_SAFE_FALLBACK", "MANUAL", "UNRESOLVED")
        }
        result["branch_resolutions"] = [to_data(item) for item in plan.branch_resolutions]
        result["proposal_count"] = len(plan.proposals)
        result["proposal_bones"] = [proposal.bone_name for proposal in plan.proposals]
        result["topology_ledger_before_apply"] = to_data(plan.topology_ledger)
        result["performance"] = get_performance(plan.plan_id)
        if runtime.issue_count_blocker:
            raise RuntimeError(f"analyze produced {runtime.issue_count_blocker} blockers")
        apply_result = bpy.ops.uecp.apply(plan_id=runtime.plan_id)
        result["apply_operator"] = sorted(apply_result)
        result["runtime_state_after_apply"] = runtime.state
        result["apply_error"] = runtime.last_error
        if apply_result != {"FINISHED"}:
            raise RuntimeError(runtime.last_error or "apply failed")
        result["performance"] = get_performance(plan.plan_id)
        snapshot = load_snapshot_payload(runtime.snapshot_text_name)
        result["snapshot_id"] = runtime.snapshot_id
        result["snapshot_text_name"] = runtime.snapshot_text_name
        result["post_validation"] = snapshot.get("post_validation")
        result["mutation_records"] = snapshot.get("mutation_records")
        result["mutation_record_count"] = len(snapshot.get("mutation_records", ()))
        result["topology_ledger_after_apply"] = snapshot.get("topology_ledger")
        export_result = bpy.ops.uecp.export_conversion(filepath=str(output_blend))
        result["export_operator"] = sorted(export_result)
        result["export_error"] = runtime.last_error
        if export_result != {"FINISHED"}:
            raise RuntimeError(runtime.last_error or "export failed")
        result["conversion_audit"] = json.loads((output_dir / "conversion-audit.json").read_text(encoding="utf-8"))
        result["reopen_validation"] = json.loads((output_dir / "reopen-validation.json").read_text(encoding="utf-8"))
        source_after = file_signature(source)
        result["source_sha256_after"] = source_after[0]
        result["source_timestamp_after"] = source_after[1]
        result["source_unchanged"] = source_after == source_before
        if not result["source_unchanged"]:
            raise RuntimeError("source blend signature changed")
        if not result["reopen_validation"].get("success"):
            raise RuntimeError("independent reopen validation failed")
        result["status"] = "PASS"
        exit_code = 0
    except Exception as error:
        result["status"] = "FAIL"
        result["error"] = str(error)
        result["traceback"] = traceback.format_exc()
        try:
            source_after = file_signature(source)
            result["source_sha256_after"] = source_after[0]
            result["source_timestamp_after"] = source_after[1]
            result["source_unchanged"] = source_after == source_before
        except Exception:
            pass
    finally:
        report_path.write_text(
            json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
            encoding="utf-8",
        )
        print("UECP_REAL_BACKEND_RESULT", result["status"], result.get("error", ""))
        sys.stdout.flush()
        sys.stderr.flush()
        os._exit(exit_code)


if __name__ == "__main__":
    main()
