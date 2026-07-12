from __future__ import annotations

import json
import tomllib
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "boneweaver"


class SchemaAndManifestTests(unittest.TestCase):
    def test_manifest_identity(self) -> None:
        manifest = tomllib.loads((PACKAGE / "blender_manifest.toml").read_text(encoding="utf-8"))
        self.assertEqual(manifest["id"], "boneweaver")
        self.assertEqual(manifest["version"], "0.2.0")
        self.assertEqual(manifest["blender_version_min"], "4.2.0")
        self.assertEqual(manifest["type"], "add-on")

    def test_all_schema_documents_parse_and_are_closed(self) -> None:
        expected = {
            "settings.schema.json": "boneweaver://schema/settings/4.0.0",
            "conversion-plan.schema.json": "boneweaver://schema/conversion-plan/4.0.0",
            "snapshot.schema.json": "boneweaver://schema/snapshot/4.0.0",
            "diagnostic-report.schema.json": "boneweaver://schema/diagnostic-report/4.0.0",
            "export-manifest.schema.json": "boneweaver://schema/export-manifest/4.0.0",
            "hierarchy-inspection.schema.json": "boneweaver://schema/hierarchy-inspection/1.0.0",
            "semantic-rule-set.schema.json": "boneweaver://schemas/semantic-rule-set.schema.json",
            "semantic-discovery-plan.schema.json": "boneweaver://schemas/semantic-discovery-plan/2.0.0",
        }
        for filename, schema_id in expected.items():
            with self.subTest(filename=filename):
                payload = json.loads((PACKAGE / "schemas" / filename).read_text(encoding="utf-8"))
                self.assertEqual(payload["$schema"], "https://json-schema.org/draft/2020-12/schema")
                self.assertEqual(payload["$id"], schema_id)
                self.assertEqual(payload["type"], "object")
                self.assertFalse(payload["additionalProperties"])
                self.assertTrue(payload["required"])
        diagnostic = json.loads((PACKAGE / "schemas" / "diagnostic-report.schema.json").read_text(encoding="utf-8"))
        for field in ("branch_resolutions", "topology_ledger"):
            self.assertIn(field, diagnostic["required"])
            self.assertIn(field, diagnostic["properties"])

    def test_conversion_plan_schema_contains_physics_graph_contract(self) -> None:
        payload = json.loads((PACKAGE / "schemas" / "conversion-plan.schema.json").read_text(encoding="utf-8"))
        self.assertEqual(payload["properties"]["kind"], {"const": "boneweaver.conversion_plan"})
        self.assertIn("physics_graph", payload["required"])
        self.assertIn("physicsNode", payload["$defs"])
        self.assertIn("physicsEdge", payload["$defs"])
        self.assertIn("terminalCandidate", payload["$defs"])
        self.assertIn("proposal", payload["$defs"])


if __name__ == "__main__":
    unittest.main()
