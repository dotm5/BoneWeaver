from __future__ import annotations

import unittest

import bpy

import ue_chain_prep


class RegistrationTests(unittest.TestCase):
    def tearDown(self) -> None:
        ue_chain_prep.unregister()

    def test_register_unregister_three_cycles_without_rna_leaks(self) -> None:
        ue_chain_prep.unregister()
        for _ in range(3):
            ue_chain_prep.register()
            self.assertTrue(hasattr(bpy.types.Scene, "uecp_settings"))
            self.assertTrue(hasattr(bpy.types.WindowManager, "uecp_runtime"))
            self.assertTrue(hasattr(bpy.types, "UECP_OT_analyze"))
            self.assertTrue(hasattr(bpy.types, "UECP_PT_main"))
            ue_chain_prep.unregister()
            self.assertFalse(hasattr(bpy.types.Scene, "uecp_settings"))
            self.assertFalse(hasattr(bpy.types.WindowManager, "uecp_runtime"))
            self.assertFalse(hasattr(bpy.types, "UECP_OT_analyze"))
            self.assertFalse(hasattr(bpy.types, "UECP_PT_main"))

    def test_settings_defaults_match_contract(self) -> None:
        ue_chain_prep.register()
        settings = bpy.context.scene.uecp_settings
        runtime = bpy.context.window_manager.uecp_runtime
        self.assertEqual(settings.scope_mode, "SELECTED_BONES")
        self.assertEqual(settings.mesh_scope, "ALL_ASSOCIATED_MESHES")
        self.assertEqual(settings.physics_profile, "BONEX_ROTATION_CHAIN")
        self.assertEqual(settings.branch_resolution_mode, "AUTO_MAIN_PATH")
        self.assertEqual(settings.terminal_mode, "AUTO_HYBRID")
        self.assertEqual(settings.bone_forward_axis, "AUTO")
        self.assertEqual(settings.roll_mode, "MINIMAL_TWIST")
        self.assertEqual(settings.validation_tolerance_mode, "AUTO_PRODUCTION")
        self.assertAlmostEqual(settings.minimum_candidate_score, 0.62)
        self.assertAlmostEqual(settings.candidate_minimum_margin, 0.08)
        self.assertAlmostEqual(settings.candidate_direction_merge_angle_degrees, 7.5)
        self.assertEqual(runtime.state, "IDLE")
        self.assertFalse(runtime.is_busy)

    def test_operator_shells_are_registered(self) -> None:
        ue_chain_prep.register()
        for name in (
            "UECP_OT_analyze", "UECP_OT_apply", "UECP_OT_validate",
            "UECP_OT_preview_toggle", "UECP_OT_restore_snapshot",
            "UECP_OT_export_report", "UECP_OT_clear_runtime",
        ):
            self.assertTrue(hasattr(bpy.types, name), name)


if __name__ == "__main__":
    unittest.main()
