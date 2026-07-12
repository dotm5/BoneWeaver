from __future__ import annotations

import dataclasses
import types
import unittest

from tests.test_branch_resolution import bag_fixture
from boneweaver.core.branch_resolution import resolve_branch
from boneweaver.core.graph_projection import build_proposals
from boneweaver.core.models import BoneMutationRecord, BoneProposal
from boneweaver.core.mutation_ledger import (
    build_mutation_records,
    build_topology_projection_ledger,
    validate_mutation_records,
)
from boneweaver.core.physics_graph import build_physics_graph


def proposal(name="Bone", proposal_id="proposal-1"):
    return BoneProposal(
        bone_name=name,
        chain_id="chain-1",
        source_edge_id="edge-1",
        role="DYNAMIC",
        original_head=(0, 0, 0),
        original_tail=(0, 1, 0),
        original_roll=0.0,
        proposed_tail=(0, 2, 0),
        proposed_roll_reference_z=(0, 0, 1),
        final_use_connect=True,
        terminal_source="UNIQUE_DIRECT_CHILD_HEAD",
        confidence=1.0,
        issue_codes=(),
        proposal_id=proposal_id,
    )


class MutationLedgerTests(unittest.TestCase):
    def test_each_changed_field_is_recorded_against_proposal(self) -> None:
        plan = types.SimpleNamespace(proposals=(proposal(),))
        before = {"Bone": {"tail": (0, 1, 0), "roll": 0.0, "use_connect": False}}
        after = {"Bone": {"tail": (0, 2, 0), "roll": 0.25, "use_connect": True}}
        records = build_mutation_records(plan, before, after)
        self.assertEqual(len(records), 1)
        record = records[0]
        self.assertEqual(record.proposal_id, "proposal-1")
        self.assertTrue(record.tail_changed)
        self.assertTrue(record.roll_changed)
        self.assertTrue(record.use_connect_changed)
        self.assertEqual(record.old_tail, (0.0, 1.0, 0.0))
        self.assertEqual(record.new_tail, (0.0, 2.0, 0.0))
        self.assertEqual(validate_mutation_records(plan, before, after, records), ())

    def test_unrecorded_change_fails_validation(self) -> None:
        plan = types.SimpleNamespace(proposals=(proposal(),))
        before = {"Bone": {"tail": (0, 1, 0), "roll": 0.0, "use_connect": False}}
        after = {"Bone": {"tail": (0, 2, 0), "roll": 0.0, "use_connect": False}}
        issues = validate_mutation_records(plan, before, after, ())
        self.assertIn("BONEWEAVER_UNRECORDED_BONE_MUTATION", issues)

    def test_record_without_frozen_proposal_fails_validation(self) -> None:
        plan = types.SimpleNamespace(proposals=(proposal(),))
        before = {"Bone": {"tail": (0, 1, 0), "roll": 0.0, "use_connect": False}}
        after = {"Bone": {"tail": (0, 1, 0), "roll": 0.0, "use_connect": False}}
        rogue = BoneMutationRecord(
            "Other", "missing", "chain-x", "DYNAMIC", True, False, False,
            (0, 1, 0), (0, 2, 0), 0.0, 0.0, False, False,
            ("TAIL_PROJECTED",),
        )
        issues = validate_mutation_records(plan, before, after, (rogue,))
        self.assertIn("BONEWEAVER_MUTATION_WITHOUT_PROPOSAL", issues)

    def test_noop_proposal_does_not_create_false_mutation(self) -> None:
        plan = types.SimpleNamespace(proposals=(proposal(),))
        state = {"Bone": {"tail": (0, 1, 0), "roll": 0.0, "use_connect": False}}
        self.assertEqual(build_mutation_records(plan, state, state), ())

    def test_topology_ledger_accounts_for_linear_and_branch_edges(self) -> None:
        bones = bag_fixture()
        graph = build_physics_graph(bones)
        resolution = resolve_branch("bag_r_03", bones)
        proposals = build_proposals(
            graph, bones, "BONEX_ROTATION_CHAIN", branch_resolutions=(resolution,)
        )
        ledger = build_topology_projection_ledger(
            bones, graph, proposals, (resolution,), mutation_record_count=0,
        )
        self.assertEqual(ledger.selected_bone_count, 7)
        self.assertEqual(ledger.selected_hierarchy_edge_count, 6)
        self.assertEqual(ledger.linear_edge_count, 4)
        self.assertEqual(ledger.branch_node_count, 1)
        self.assertEqual(ledger.branch_edge_count, 2)
        self.assertEqual(ledger.resolved_branch_count, 1)
        self.assertEqual(ledger.unresolved_branch_count, 0)
        self.assertEqual(ledger.proposal_count, len(proposals))
        self.assertEqual(
            ledger.selected_hierarchy_edge_count,
            ledger.linear_edge_count + ledger.branch_edge_count,
        )


if __name__ == "__main__":
    unittest.main()
