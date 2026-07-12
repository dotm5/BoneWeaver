from __future__ import annotations

import unittest
import json

import bpy

import boneweaver


class RegistrationTests(unittest.TestCase):
    def tearDown(self) -> None:
        boneweaver.unregister()

    def test_register_unregister_three_cycles_without_rna_leaks(self) -> None:
        boneweaver.unregister()
        for _ in range(3):
            boneweaver.register()
            self.assertTrue(hasattr(bpy.types.Scene, "boneweaver_settings"))
            self.assertTrue(hasattr(bpy.types.WindowManager, "boneweaver_runtime"))
            self.assertTrue(hasattr(bpy.types, "BONEWEAVER_OT_analyze"))
            self.assertTrue(hasattr(bpy.types, "BONEWEAVER_PT_main"))
            boneweaver.unregister()
            self.assertFalse(hasattr(bpy.types.Scene, "boneweaver_settings"))
            self.assertFalse(hasattr(bpy.types.WindowManager, "boneweaver_runtime"))
            self.assertFalse(hasattr(bpy.types, "BONEWEAVER_OT_analyze"))
            self.assertFalse(hasattr(bpy.types, "BONEWEAVER_PT_main"))

    def test_settings_defaults_match_contract(self) -> None:
        boneweaver.register()
        settings = bpy.context.scene.boneweaver_settings
        runtime = bpy.context.window_manager.boneweaver_runtime
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
        boneweaver.register()
        for name in (
            "BONEWEAVER_OT_analyze", "BONEWEAVER_OT_apply", "BONEWEAVER_OT_validate",
            "BONEWEAVER_OT_preview_toggle", "BONEWEAVER_OT_restore_snapshot",
            "BONEWEAVER_OT_export_report", "BONEWEAVER_OT_clear_runtime",
        ):
            self.assertTrue(hasattr(bpy.types, name), name)

    def test_partial_registration_failure_rolls_back_classes_properties_and_handlers(self) -> None:
        import boneweaver.registration as registration
        from boneweaver.controllers.session import SessionController
        boneweaver.unregister()
        original = registration.register_translations
        registration.register_translations = lambda: (_ for _ in ()).throw(RuntimeError("forced"))
        try:
            with self.assertRaisesRegex(RuntimeError, "forced"):
                boneweaver.register()
        finally:
            registration.register_translations = original
        self.assertFalse(hasattr(bpy.types.Scene, "boneweaver_settings"))
        self.assertFalse(hasattr(bpy.types, "BONEWEAVER_OT_analyze"))
        self.assertNotIn(SessionController.on_load_pre, bpy.app.handlers.load_pre)

    def test_reregister_rediscovers_latest_persistent_snapshot_text(self) -> None:
        from tests.fixture_builders import clear_scene, make_chain
        from boneweaver.core.armature_reader import read_bone_states
        from boneweaver.controllers.session import SessionController
        clear_scene()
        rig = make_chain(name="SnapshotRig", count=1)
        state = read_bone_states(rig, ("Bone_0",))[0]
        name = "BONEWEAVER_SNAPSHOT::persisted"
        text = bpy.data.texts.get(name) or bpy.data.texts.new(name)
        text.clear()
        payload = {
            "kind": "boneweaver.snapshot", "status": "APPLIED", "snapshot_id": "persisted",
            "created_at": "2026-07-11T23:58:00+00:00",
            "armature": {"object_name": rig.name, "data_name": rig.data.name},
            "expected_post_bones": {
                state.name: {"head": state.head, "tail": state.tail, "roll": state.roll,
                             "use_connect": state.use_connect, "parent_name": state.parent_name}
            },
        }
        text.write(json.dumps(payload))
        rolled_back = bpy.data.texts.new("BONEWEAVER_SNAPSHOT::rolled-back")
        rolled_back.write(json.dumps({**payload, "status": "ROLLED_BACK", "snapshot_id": "rolled-back",
                                      "created_at": "2026-07-11T23:59:00+00:00"}))
        boneweaver.unregister()
        boneweaver.register()
        runtime = bpy.context.window_manager.boneweaver_runtime
        self.assertEqual("persisted", runtime.snapshot_id)
        self.assertEqual(name, runtime.snapshot_text_name)
        self.assertTrue(runtime.snapshot_available)
        runtime.snapshot_id = ""
        runtime.snapshot_text_name = ""
        SessionController.on_load_post(None)
        self.assertEqual(name, runtime.snapshot_text_name)
        self.assertTrue(runtime.snapshot_available)
        bpy.data.texts.remove(text)
        bpy.data.texts.remove(rolled_back)
        clear_scene()


if __name__ == "__main__":
    unittest.main()
