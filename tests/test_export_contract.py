from __future__ import annotations

import copy
import json
from pathlib import Path
import types
import unittest

import bpy
import ue_chain_prep

from tests.fixture_builders import clear_scene, make_bound_mesh, make_chain
from ue_chain_prep.core.export_contract import (
    ExportReadinessError,
    build_export_manifest,
    evaluate_export_readiness,
)
from ue_chain_prep.core.models import TopologyProjectionLedger
from ue_chain_prep.core.runtime_store import get_plan


def valid_fixture():
    topology = TopologyProjectionLedger(3, 2, 2, 0, 0, 0, 0, 0, 1, 3, 3, 0)
    plan = types.SimpleNamespace(
        plan_id="a" * 64,
        algorithm_version="algorithm-v2",
        schema_version="3.1.0",
        addon_version="0.1.0",
        physics_graph=types.SimpleNamespace(graph_id="b" * 64),
        issues=(),
        proposals=(object(), object(), object()),
        branch_resolutions=(),
        topology_ledger=dataclasses_replace(topology, mutation_record_count=0),
    )
    snapshot = {
        "status": "APPLIED",
        "plan_id": plan.plan_id,
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
        cases = {
            "no_plan": {"plan": None},
            "stale": {"plan_stale": True},
            "not_applied": {"runtime_state": "ANALYZED"},
            "no_snapshot": {"snapshot_present": False},
            "rolled_back": {"snapshot": {**snapshot, "status": "ROLLED_BACK"}},
            "no_mutation": {"snapshot": {**snapshot, "mutation_records": []}},
            "digest_failure": {"snapshot": {**snapshot, "post_validation": {**snapshot["post_validation"], "weight_digest_changes": 1}}},
            "neutral_failure": {"snapshot": {**snapshot, "post_validation": {**snapshot["post_validation"], "mesh_validation_results": [{"result": "FAIL_AND_ROLLBACK"}]}}},
            "unresolved_branch": {"snapshot": {**snapshot, "topology_ledger": {**snapshot["topology_ledger"], "unresolved_branch_count": 1}}},
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
                self.assertTrue(report.reasons)


class ExportContractBlenderTests(unittest.TestCase):
    def setUp(self) -> None:
        clear_scene()
        ue_chain_prep.register()
        self.rig = make_chain()
        self.mesh, _ = make_bound_mesh(self.rig)
        for name in ("Bone_1", "Bone_2"):
            group = self.mesh.vertex_groups.new(name=name)
            group.add([0, 1, 2], 1.0, "REPLACE")
        settings = bpy.context.scene.uecp_settings
        settings.minimum_candidate_score = 0.40
        settings.candidate_minimum_margin = 0.001
        settings.minimum_confidence = 0.40
        self.output_dir = Path(__file__).resolve().parents[1] / "test-output" / "export-contract"
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def tearDown(self) -> None:
        ue_chain_prep.unregister()
        clear_scene()

    def test_unapplied_plan_cannot_save_conversion_copy(self) -> None:
        bpy.ops.uecp.analyze()
        output = self.output_dir / "must-not-exist.blend"
        if output.exists():
            output.unlink()
        result = bpy.ops.uecp.export_conversion(filepath=str(output))
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
        bpy.ops.uecp.analyze()
        runtime = bpy.context.window_manager.uecp_runtime
        self.assertEqual(bpy.ops.uecp.apply(plan_id=runtime.plan_id), {"FINISHED"})
        plan = get_plan(runtime.plan_id)
        result = bpy.ops.uecp.export_conversion(filepath=str(output))
        self.assertEqual(result, {"FINISHED"})
        self.assertTrue(output.exists())
        audit_path = self.output_dir / "conversion-audit.json"
        payload = json.loads(audit_path.read_text(encoding="utf-8"))
        self.assertEqual(payload["plan_id"], plan.plan_id)
        self.assertGreater(len(payload["mutation_records"]), 0)
        self.assertIn("topology_ledger", payload)
        self.assertEqual(__import__("hashlib").sha256(source.read_bytes()).hexdigest(), source_hash_before)
        self.assertEqual(source.stat().st_mtime_ns, source_time_before)
        self.assertIn("UECP_EXPORT_MANIFEST", bpy.data.texts)


if __name__ == "__main__":
    unittest.main()
