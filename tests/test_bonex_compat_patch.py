from __future__ import annotations

import importlib.util
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
TOOL_PATH = ROOT / "tools" / "patch_bonex_1_2_6.py"


VULNERABLE_GETTER = '''def get_armature_soft_connections(armature_obj):
    """获取armature对象的soft_connections数据"""
    if not armature_obj.get(const.rigidbody_data_name):
        armature_obj[const.rigidbody_data_name] = {}

    armature_data = armature_obj[const.rigidbody_data_name]
    if const.soft_connections_key not in armature_data:
        armature_data[const.soft_connections_key] = []

    return armature_data[const.soft_connections_key]
'''


class BoneXCompatibilityPatchTests(unittest.TestCase):
    @staticmethod
    def _load_module():
        spec = importlib.util.spec_from_file_location("patch_bonex_1_2_6", TOOL_PATH)
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        return module

    def test_transform_makes_soft_connection_getter_read_only(self) -> None:
        self.assertTrue(TOOL_PATH.exists(), "BoneX compatibility patch tool is missing")
        module = self._load_module()

        patched, changed = module.patch_source(VULNERABLE_GETTER)

        self.assertTrue(changed)
        self.assertIn("armature_data = armature_obj.get(const.rigidbody_data_name)", patched)
        self.assertIn("return armature_data.get(const.soft_connections_key, [])", patched)
        self.assertNotIn('armature_obj[const.rigidbody_data_name] = {}', patched)

    def test_installation_patch_is_version_guarded_idempotent_and_reversible(self) -> None:
        module = self._load_module()
        self.assertTrue(
            hasattr(module, "apply_installation"),
            "reversible installation patch workflow is missing",
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "bonex"
            utils_dir = root / "utils"
            utils_dir.mkdir(parents=True)
            (root / "blender_manifest.toml").write_text(
                'schema_version = "1.0.0"\nid = "bonex"\nversion = "1.2.6"\n',
                encoding="utf-8",
            )
            source_path = utils_dir / "utils.py"
            source_path.write_text(VULNERABLE_GETTER, encoding="utf-8")

            first = module.apply_installation(root)
            second = module.apply_installation(root)

            self.assertTrue(first.changed)
            self.assertFalse(second.changed)
            self.assertTrue(first.backup_path.exists())
            self.assertEqual(first.backup_path.read_text(encoding="utf-8"), VULNERABLE_GETTER)
            self.assertNotEqual(source_path.read_text(encoding="utf-8"), VULNERABLE_GETTER)

            restored = module.restore_installation(root)

            self.assertTrue(restored.changed)
            self.assertEqual(source_path.read_text(encoding="utf-8"), VULNERABLE_GETTER)

    def test_cli_apply_check_and_restore_emit_machine_readable_results(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "bonex"
            utils_dir = root / "utils"
            utils_dir.mkdir(parents=True)
            (root / "blender_manifest.toml").write_text(
                'schema_version = "1.0.0"\nid = "bonex"\nversion = "1.2.6"\n',
                encoding="utf-8",
            )
            (utils_dir / "utils.py").write_text(VULNERABLE_GETTER, encoding="utf-8")

            applied = subprocess.run(
                [sys.executable, str(TOOL_PATH), "--bonex-root", str(root), "--apply"],
                capture_output=True,
                text=True,
                check=False,
            )
            checked = subprocess.run(
                [sys.executable, str(TOOL_PATH), "--bonex-root", str(root), "--check"],
                capture_output=True,
                text=True,
                check=False,
            )
            restored = subprocess.run(
                [sys.executable, str(TOOL_PATH), "--bonex-root", str(root), "--restore"],
                capture_output=True,
                text=True,
                check=False,
            )

            self.assertEqual(applied.returncode, 0, applied.stderr)
            self.assertIn('"action": "apply"', applied.stdout)
            self.assertIn('"changed": true', applied.stdout)
            self.assertEqual(checked.returncode, 0, checked.stderr)
            self.assertIn('"status": "patched"', checked.stdout)
            self.assertEqual(restored.returncode, 0, restored.stderr)
            self.assertIn('"action": "restore"', restored.stdout)


if __name__ == "__main__":
    unittest.main()
