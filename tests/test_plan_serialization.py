from __future__ import annotations

import json
import unittest
from pathlib import Path

import bpy
import ue_chain_prep

from tests.fixture_builders import clear_scene, make_bound_mesh, make_chain
from ue_chain_prep.core.runtime_store import get_plan
from ue_chain_prep.core.serialization import conversion_plan_to_data, dumps


class PlanSerializationTests(unittest.TestCase):
    def setUp(self) -> None:
        clear_scene()
        ue_chain_prep.register()
        rig = make_chain()
        make_bound_mesh(rig)

    def tearDown(self) -> None:
        ue_chain_prep.unregister()
        clear_scene()

    def test_plan_json_round_trip_matches_closed_top_level_schema(self) -> None:
        bpy.ops.uecp.analyze()
        plan = get_plan(bpy.context.window_manager.uecp_runtime.plan_id)
        payload = conversion_plan_to_data(plan)
        round_trip = json.loads(dumps(payload))
        self.assertEqual(round_trip, payload)
        schema_path = Path(__file__).resolve().parents[1] / "ue_chain_prep" / "schemas" / "conversion-plan.schema.json"
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        self.assertEqual(set(payload), set(schema["properties"]))
        self.assertTrue(set(schema["required"]).issubset(payload))
        self.assertEqual(payload["plan_id"], plan.plan_id)
        self.assertIn("branch_resolutions", payload)
        self.assertIn("topology_ledger", payload)


if __name__ == "__main__":
    unittest.main()
