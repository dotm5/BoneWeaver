from __future__ import annotations

import unittest

import bpy
import ue_chain_prep

from tests.fixture_builders import clear_scene, make_bound_mesh, make_chain
from ue_chain_prep.core.runtime_store import get_plan
from ue_chain_prep.core.overrides import armature_structural_fingerprint, upsert_terminal_override


class PlannerSettingsTests(unittest.TestCase):
    def setUp(self) -> None:
        clear_scene()
        ue_chain_prep.register()
        self.rig = make_chain()
        self.mesh, _ = make_bound_mesh(self.rig)

    def tearDown(self) -> None:
        settings = bpy.context.scene.uecp_settings
        settings.terminal_mode = "AUTO_HYBRID"
        settings.bone_forward_axis = "AUTO"
        settings.roll_mode = "MINIMAL_TWIST"
        settings.minimum_candidate_score = 0.62
        settings.candidate_minimum_margin = 0.08
        settings.minimum_confidence = 0.70
        settings.terminal_overrides.clear()
        settings.branch_overrides.clear()
        ue_chain_prep.unregister()
        clear_scene()

    def plan(self):
        self.assertEqual(bpy.ops.uecp.analyze(), {"FINISHED"})
        return get_plan(bpy.context.window_manager.uecp_runtime.plan_id)

    def test_explicit_manual_override_is_frozen_as_authoritative_solution(self) -> None:
        chain_id = self.plan().physics_graph.chains[0].chain_id
        override = upsert_terminal_override(
            bpy.context.scene.uecp_settings.terminal_overrides,
            armature_data_name=self.rig.data.name,
            armature_structural_fingerprint=armature_structural_fingerprint(self.rig),
            bone_name="Bone_2",
            chain_id=chain_id,
            mode="EXPLICIT_DIRECTION_LENGTH",
            direction=(1.0, 0.0, 0.0),
            length=2.0,
        )
        plan = self.plan()
        solution = plan.terminal_solutions[0]
        self.assertEqual(solution.source, "MANUAL_OVERRIDE")
        self.assertEqual(solution.tail, (2.0, 2.0, 0.0))
        self.assertFalse(solution.requires_confirmation)
        self.assertEqual(solution.resolution_class, "MANUAL")

    def test_low_confidence_leaf_uses_safe_parent_fallback_without_blocking(self) -> None:
        settings = bpy.context.scene.uecp_settings
        settings.minimum_candidate_score = 0.99
        settings.candidate_minimum_margin = 0.99
        settings.minimum_confidence = 0.99
        plan = self.plan()
        solution = next(item for item in plan.terminal_solutions if item.bone_name == "Bone_2")
        self.assertEqual(solution.source, "PARENT_CHAIN_EXTRAPOLATION")
        self.assertEqual(solution.resolution_class, "AUTO_SAFE_FALLBACK")
        self.assertTrue(solution.requires_confirmation)
        self.assertIn("Bone_2", {proposal.bone_name for proposal in plan.proposals})
        fallback_issues = [issue for issue in plan.issues if "Bone_2" in issue.bone_names]
        self.assertIn("WARNING", {issue.severity for issue in fallback_issues})
        self.assertNotIn("BLOCKER", {issue.severity for issue in fallback_issues})
        self.assertEqual(len(settings.terminal_overrides), 0)

    def test_legacy_unscoped_override_warns_and_is_not_applied(self) -> None:
        legacy = bpy.context.scene.uecp_settings.terminal_overrides.add()
        legacy.bone_name = "Bone_2"
        legacy.mode = "EXPLICIT_DIRECTION_LENGTH"
        legacy.direction = (1, 0, 0)
        legacy.length = 9.0
        plan = self.plan()
        solution = next(item for item in plan.terminal_solutions if item.bone_name == "Bone_2")
        self.assertNotEqual(solution.source, "MANUAL_OVERRIDE")
        migration = [issue for issue in plan.issues if issue.code == "UECP_LEGACY_OVERRIDE_UNSCOPED"]
        self.assertEqual(len(migration), 1)
        self.assertEqual(migration[0].severity, "WARNING")

    def test_imported_forward_axis_only_filters_to_requested_axis(self) -> None:
        settings = bpy.context.scene.uecp_settings
        settings.terminal_mode = "IMPORTED_FORWARD_AXIS_ONLY"
        settings.bone_forward_axis = "X_POSITIVE"
        solution = self.plan().terminal_solutions[0]
        self.assertEqual({candidate.kind for candidate in solution.candidates}, {"IMPORTED_AXIS"})
        self.assertEqual({candidate.axis_label for candidate in solution.candidates}, {"X_POSITIVE"})

    def test_roll_mode_changes_frozen_roll_reference(self) -> None:
        settings = bpy.context.scene.uecp_settings
        settings.roll_mode = "RADIAL_REFERENCE"
        radial = self.plan()
        settings.roll_mode = "MINIMAL_TWIST"
        minimal = self.plan()
        self.assertNotEqual(
            tuple(proposal.proposed_roll_reference_z for proposal in radial.proposals),
            tuple(proposal.proposed_roll_reference_z for proposal in minimal.proposals),
        )


if __name__ == "__main__":
    unittest.main()
