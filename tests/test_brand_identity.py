from __future__ import annotations

import json
import unittest
from pathlib import Path

import bpy
import boneweaver


ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "boneweaver"


class BoneWeaverIdentityTests(unittest.TestCase):
    def test_public_and_runtime_identity_is_closed(self) -> None:
        boneweaver.register()
        self.addCleanup(boneweaver.unregister)
        self.assertEqual(boneweaver.bl_info["name"], "BoneWeaver")
        self.assertEqual(boneweaver.bl_info["version"], (0, 2, 0))
        self.assertTrue(PACKAGE.is_dir())
        legacy_package = ROOT / "ue_chain_prep"
        self.assertFalse((legacy_package / "__init__.py").exists())
        self.assertFalse((legacy_package / "blender_manifest.toml").exists())
        manifest = (PACKAGE / "blender_manifest.toml").read_text("utf-8")
        self.assertIn('id = "boneweaver"', manifest)
        self.assertIn('name = "BoneWeaver"', manifest)
        self.assertTrue(hasattr(bpy.types.Scene, "boneweaver_settings"))
        self.assertFalse(hasattr(bpy.types.Scene, "uecp_settings"))

    def test_schema_and_rule_identity_is_boneweaver(self) -> None:
        payloads = [
            json.loads(path.read_text("utf-8"))
            for path in sorted((PACKAGE / "schemas").glob("*.json"))
        ]
        self.assertTrue(payloads)
        self.assertTrue(all("uecp" not in json.dumps(item).lower() for item in payloads))
        rules = json.loads((PACKAGE / "rules" / "default-ue-secondary.json").read_text("utf-8"))
        self.assertNotIn("uecp", json.dumps(rules).lower())


if __name__ == "__main__":
    unittest.main()
