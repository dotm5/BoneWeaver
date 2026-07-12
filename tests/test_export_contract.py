from __future__ import annotations

import copy
import json
from pathlib import Path
import types
import unittest

import bpy
import boneweaver

from tests.fixture_builders import clear_scene, make_bound_mesh, make_chain
from boneweaver.core.export_contract import (
    ExportReadinessError,
    build_export_manifest,
    evaluate_export_readiness,
)
from boneweaver.core.models import TopologyProjectionLedger
from boneweaver.core.runtime_store import get_plan


def valid_fixture():
    topology = TopologyProjectionLedger(
        selected_bone_count=3,
        selected_hierarchy_edge_count=2,
        linear_edge_count=2,
        branch_node_count=0,
        branch_edge_count=0,
        resolved_branch_count=0,
        unresolved_branch_count=0,
        external_child_edge_count=0,
        virtual_tip_count=1,
        proposal_count=3,
        mutation_record_count=3,
        skipped_by_design_count=0,
        mutation_target_count=3,
        reference_only_tip_helper_count=0,
    )
    proposals = tuple(
        types.SimpleNamespace(bone_name=f"B{index}") for index in range(3)
    )
    plan = types.SimpleNamespace(
        plan_id="a" * 64,
        algorithm_version="algorithm-v2",
        schema_version="4.0.0",
        addon_version="0.1.0",
        profile="BONEX_ROTATION_CHAIN",
        tip_helper_usage="REFERENCE_ONLY",
        physics_graph=types.SimpleNamespace(graph_id="b" * 64),
        bone_states=(),
        issues=(),
        proposals=proposals,
        tip_helpers=(),
        branch_resolutions=(),
        topology_ledger=topology,
    )
    snapshot = {
        "status": "APPLIED",
        "plan_id": plan.plan_id,
        "profile": plan.profile,
        "tip_helper_usage": plan.tip_helper_usage,
        "mutation_targets": tuple(proposal.bone_name for proposal in proposals),
        "reference_only_tip_helpers": (),
        "tip_helpers": (),
        "mutation_records": [
            {"bone_name": f"B{index}", "proposal_id": str(index), "tail_changed": True}
            for index in range(3)
        ],
        "topology_ledger": topology.__dict__ if hasattr(topology, "__dict__") else {
            field: getattr(topology, field) for field in topology.__slots__
        },
        "post_validation": {
            "success": True,
            "weight_digest_changes": 0,
            "base_mesh_digest_changes": 0,
            "modifier_digest_changes": 0,
            "non_target_bone_changes": 0,
            "issues": [],
            "mesh_validation_results": [{"result": "PASS"}],
        },
    }
    return plan, snapshot


def dataclasses_replace(value, **changes):
    import dataclasses
    return dataclasses.replace(value, **changes)


class ExportContractPureTests(unittest.TestCase):
    def test_all_required_conditions_allow_export(self) -> None:
        plan, snapshot = valid_fixture()
        report = evaluate_export_readiness(
            plan, runtime_state="RESTORABLE", snapshot_payload=snapshot,
            snapshot_present=True, plan_stale=False,
        )
        self.assertTrue(report.ready, report.reasons)
        self.assertEqual(report.mutation_record_count, 3)
        self.assertEqual(report.changed_bone_count, 3)

    def test_each_critical_missing_condition_rejects_export(self) -> None:
        plan, snapshot = valid_fixture()
        blocked_plan = copy.copy(plan)
        blocked_plan.issues = (types.SimpleNamespace(severity="BLOCKER"),)
        cases = {
            "no_plan": {"plan": None, "expected": "BONEWEAVER_EXPORT_PLAN_MISSING"},
            "stale": {"plan_stale": True, "expected": "BONEWEAVER_EXPORT_PLAN_STALE"},
            "not_applied": {"runtime_state": "ANALYZED", "expected": "BONEWEAVER_EXPORT_APPLY_NOT_SUCCESSFUL"},
            "no_snapshot": {"snapshot_present": False, "expected": "BONEWEAVER_EXPORT_SNAPSHOT_MISSING"},
            "rolled_back": {"snapshot": {**snapshot, "status": "ROLLED_BACK"}, "expected": "BONEWEAVER_EXPORT_APPLY_NOT_SUCCESSFUL"},
            "no_mutation": {"snapshot": {**snapshot, "mutation_records": []}, "expected": "BONEWEAVER_EXPORT_NO_ACTUAL_MUTATION"},
            "weight_digest_failure": {"snapshot": {**snapshot, "post_validation": {**snapshot["post_validation"], "weight_digest_changes": 1}}, "expected": "BONEWEAVER_WEIGHT_DIGEST_CHANGED"},
            "base_digest_failure": {"snapshot": {**snapshot, "post_validation": {**snapshot["post_validation"], "base_mesh_digest_changes": 1}}, "expected": "BONEWEAVER_BASE_MESH_CHANGED"},
            "modifier_digest_failure": {"snapshot": {**snapshot, "post_validation": {**snapshot["post_validation"], "modifier_digest_changes": 1}}, "expected": "BONEWEAVER_MODIFIER_DIGEST_CHANGED"},
            "non_target_failure": {"snapshot": {**snapshot, "post_validation": {**snapshot["post_validation"], "non_target_bone_changes": 1}}, "expected": "BONEWEAVER_NON_TARGET_BONE_CHANGED"},
            "neutral_failure": {"snapshot": {**snapshot, "post_validation": {**snapshot["post_validation"], "mesh_validation_results": [{"result": "FAIL_AND_ROLLBACK"}]}}, "expected": "BONEWEAVER_NEUTRAL_MESH_CHANGED"},
            "unresolved_branch": {"snapshot": {**snapshot, "topology_ledger": {**snapshot["topology_ledger"], "unresolved_branch_count": 1}}, "expected": "BONEWEAVER_BRANCH_AMBIGUOUS"},
            "ledger_conservation": {"snapshot": {**snapshot, "topology_ledger": {**snapshot["topology_ledger"], "selected_bone_count": 4}}, "expected": "BONEWEAVER_EXPORT_TOPOLOGY_LEDGER_INCOMPLETE"},
            "tip_helper_mismatch": {"snapshot": {**snapshot, "reference_only_tip_helpers": ("unexpected",)}, "expected": "BONEWEAVER_EXPORT_TIP_HELPER_MISMATCH"},
            "plan_blocker": {"plan": blocked_plan, "expected": "BONEWEAVER_EXPORT_UNRESOLVED_BLOCKER"},
        }
        for label, changes in cases.items():
            with self.subTest(label=label):
                candidate_plan = changes.get("plan", plan)
                candidate_snapshot = changes.get("snapshot", snapshot)
                report = evaluate_export_readiness(
                    candidate_plan,
                    runtime_state=changes.get("runtime_state", "RESTORABLE"),
                    snapshot_payload=candidate_snapshot,
                    snapshot_present=changes.get("snapshot_present", True),
                    plan_stale=changes.get("plan_stale", False),
                )
                self.assertFalse(report.ready)
                self.assertIn(changes["expected"], report.reasons)


class ExportContractBlenderTests(unittest.TestCase):
    def setUp(self) -> None:
        clear_scene()
        boneweaver.register()
        self.rig = make_chain()
        self.mesh, _ = make_bound_mesh(self.rig)
        for name in ("Bone_1", "Bone_2"):
            group = self.mesh.vertex_groups.new(name=name)
            group.add([0, 1, 2], 1.0, "REPLACE")
        settings = bpy.context.scene.boneweaver_settings
        settings.minimum_candidate_score = 0.40
        settings.candidate_minimum_margin = 0.001
        settings.minimum_confidence = 0.40
        self.output_dir = Path(__file__).resolve().parents[1] / "test-output" / "export-contract"
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def tearDown(self) -> None:
        boneweaver.unregister()
        clear_scene()

    def test_unapplied_plan_cannot_save_conversion_copy(self) -> None:
        bpy.ops.boneweaver.analyze()
        output = self.output_dir / "must-not-exist.blend"
        if output.exists():
            output.unlink()
        result = bpy.ops.boneweaver.export_conversion(filepath=str(output))
        self.assertEqual(result, {"CANCELLED"})
        self.assertFalse(output.exists())

    def test_successful_conversion_writes_manifest_and_preserves_source(self) -> None:
        source = self.output_dir / "source.blend"
        output = self.output_dir / "converted.blend"
        for path in (source, output, self.output_dir / "conversion-audit.json"):
            if path.exists():
                path.unlink()
        bpy.ops.wm.save_as_mainfile(filepath=str(source))
        source_hash_before = __import__("hashlib").sha256(source.read_bytes()).hexdigest()
        source_time_before = source.stat().st_mtime_ns
        bpy.ops.boneweaver.analyze()
        runtime = bpy.context.window_manager.boneweaver_runtime
        self.assertEqual(bpy.ops.boneweaver.apply(plan_id=runtime.plan_id), {"FINISHED"})
        plan = get_plan(runtime.plan_id)
        result = bpy.ops.boneweaver.export_conversion(filepath=str(output))
        self.assertEqual(result, {"FINISHED"})
        self.assertTrue(output.exists())
        audit_path = self.output_dir / "conversion-audit.json"
        payload = json.loads(audit_path.read_text(encoding="utf-8"))
        self.assertEqual(payload["plan_id"], plan.plan_id)
        self.assertGreater(len(payload["mutation_records"]), 0)
        self.assertIn("topology_ledger", payload)
        self.assertEqual(__import__("hashlib").sha256(source.read_bytes()).hexdigest(), source_hash_before)
        self.assertEqual(source.stat().st_mtime_ns, source_time_before)
        self.assertIn("BONEWEAVER_EXPORT_MANIFEST", bpy.data.texts)


if __name__ == "__main__":
    unittest.main()
