from __future__ import annotations

import unittest

import bpy
import ue_chain_prep

from tests.fixture_builders import clear_scene, make_bound_mesh, make_chain
from ue_chain_prep.core.runtime_store import get_plan


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
        settings.terminal_overrides.clear()
        ue_chain_prep.unregister()
        clear_scene()

    def plan(self):
        self.assertEqual(bpy.ops.uecp.analyze(), {"FINISHED"})
        return get_plan(bpy.context.window_manager.uecp_runtime.plan_id)

    def test_explicit_manual_override_is_frozen_as_authoritative_solution(self) -> None:
        override = bpy.context.scene.uecp_settings.terminal_overrides.add()
        override.bone_name = "Bone_2"
        override.mode = "EXPLICIT_DIRECTION_LENGTH"
        override.direction = (1.0, 0.0, 0.0)
        override.length = 2.0
        plan = self.plan()
        solution = plan.terminal_solutions[0]
        self.assertEqual(solution.source, "MANUAL_OVERRIDE")
        self.assertEqual(solution.tail, (2.0, 2.0, 0.0))
        self.assertFalse(solution.requires_confirmation)

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
