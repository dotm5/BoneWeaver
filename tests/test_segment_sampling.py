from __future__ import annotations

import unittest

from tests.test_physics_graph import state
from ue_chain_prep.core.physics_graph import build_physics_graph
from ue_chain_prep.core.segment_sampling import build_sampling_hints


class SegmentSamplingTests(unittest.TestCase):
    def test_long_edge_produces_hint_without_changing_graph(self) -> None:
        bones = (
            state("B0", None, ("B1",), (0,0,0)),
            state("B1", "B0", ("B2",), (0,1,0)),
            state("B2", "B1", ("B3",), (0,2,0)),
            state("B3", "B2", (), (0,7,0)),
        )
        graph = build_physics_graph(bones)
        before = graph
        hints = build_sampling_hints(graph, ratio_warning=2.5, subdivision_max=8)
        self.assertEqual(graph, before)
        self.assertEqual(len(hints), 1)
        self.assertEqual(hints[0].edge_id, "hierarchy:B2->B3")
        self.assertGreaterEqual(hints[0].suggested_virtual_subdivisions, 4)


if __name__ == "__main__":
    unittest.main()
