from __future__ import annotations

import dataclasses
import types
import unittest

from tests.test_physics_graph import state
from ue_chain_prep.core.graph_projection import build_proposals
from ue_chain_prep.core.models import ValidationIssue
from ue_chain_prep.core.mutation_ledger import build_topology_projection_ledger
from ue_chain_prep.core.physics_graph import build_physics_graph
from ue_chain_prep.core.tip_helpers import classify_tip_helpers


def _cloud(name, *, weighted):
    return types.SimpleNamespace(
        bone_name=name,
        total_statistical_weight=3.0 if weighted else 0.0,
        effective_sample_count=3.0 if weighted else 0.0,
    )


def _fixture(helper_name="hair_03"):
    bones = (
        state("hair_01", None, ("hair_02",), (0, 0, 0), tail=(0, 0.2, 0)),
        state("hair_02", "hair_01", (helper_name,), (0, 1, 0), tail=(0, 1.2, 0)),
        state(helper_name, "hair_02", (), (0, 2, 0), tail=(0, 2.2, 0)),
    )
    clouds = (
        _cloud("hair_01", weighted=True),
        _cloud("hair_02", weighted=True),
        _cloud(helper_name, weighted=False),
    )
    return bones, clouds


class TipHelperTests(unittest.TestCase):
    def test_zero_weight_terminal_is_classified_without_name_guessing(self) -> None:
        bones, clouds = _fixture("hair_03")
        helpers = classify_tip_helpers(bones, clouds)
        self.assertEqual(len(helpers), 1)
        helper = helpers[0]
        self.assertEqual(helper.bone_name, "hair_03")
        self.assertEqual(helper.parent_bone_name, "hair_02")
        self.assertEqual(helper.role, "EXISTING_TIP_HELPER")
        self.assertTrue(helper.reference_only)
        self.assertFalse(helper.mutation_target)
        self.assertFalse(helper.requires_own_tail)
        self.assertEqual(helper.source, "EXISTING_TIP_HELPER_HEAD")
        self.assertIn("ZERO_EFFECTIVE_WEIGHT", helper.evidence)

    def test_positive_tip_name_strengthens_but_does_not_create_identity(self) -> None:
        bones, clouds = _fixture("hair_end")
        helper = classify_tip_helpers(bones, clouds)[0]
        self.assertTrue(any(
            code.startswith("POSITIVE_NAME_TOKEN:") for code in helper.evidence
        ))
        weighted = clouds[:-1] + (_cloud("hair_end", weighted=True),)
        self.assertFalse(classify_tip_helpers(bones, weighted))

    def test_socket_control_twist_and_dependency_evidence_exclude_helpers(self) -> None:
        for helper_name in ("ik_end", "fk_end", "socket_end", "twist_end", "control_end"):
            with self.subTest(name=helper_name):
                bones, clouds = _fixture(helper_name)
                self.assertFalse(classify_tip_helpers(bones, clouds))

        bones, clouds = _fixture("hair_end")
        socket_bones = bones[:-1] + (dataclasses.replace(bones[-1], is_socket=True),)
        self.assertFalse(classify_tip_helpers(socket_bones, clouds))
        issue = ValidationIssue(
            "BLOCKER", "UECP_RELATED_CONSTRAINT", "constraint", "constraint",
            bone_names=("hair_end",),
        )
        self.assertFalse(classify_tip_helpers(bones, clouds, (issue,)))

    def test_graph_proposal_and_ledger_keep_helper_reference_only(self) -> None:
        bones, clouds = _fixture("hair_end")
        helpers = classify_tip_helpers(bones, clouds)
        graph = build_physics_graph(bones, tip_helpers=helpers)
        helper_node = next(node for node in graph.nodes if node.bone_name == "hair_end")
        self.assertEqual(helper_node.semantic_role, "EXISTING_TIP_HELPER")
        self.assertTrue(helper_node.reference_only)
        self.assertFalse(helper_node.mutation_target)
        self.assertFalse(helper_node.requires_own_tail)

        proposals = build_proposals(graph, bones, "BONEX_ROTATION_CHAIN")
        self.assertEqual({item.bone_name for item in proposals}, {"hair_01", "hair_02"})
        parent = next(item for item in proposals if item.bone_name == "hair_02")
        self.assertEqual(parent.proposed_tail, bones[-1].head)
        self.assertEqual(parent.terminal_source, "EXISTING_TIP_HELPER_HEAD")

        ledger = build_topology_projection_ledger(
            bones, graph, proposals, (), mutation_record_count=0,
        )
        self.assertEqual(ledger.selected_bone_count, 3)
        self.assertEqual(ledger.mutation_target_count, 2)
        self.assertEqual(ledger.reference_only_tip_helper_count, 1)
        self.assertEqual(ledger.skipped_by_design_count, 0)
        self.assertEqual(ledger.proposal_count, ledger.mutation_target_count)


if __name__ == "__main__":
    unittest.main()
