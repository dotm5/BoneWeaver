from __future__ import annotations

from array import array
import gc
import itertools
from pathlib import Path
import unittest
import inspect

from ue_chain_prep.core.validation_tolerance import MeshCoordinateCapture, evaluate_mesh_tolerance
from ue_chain_prep.ui import draw

from ue_chain_prep.core.weight_islands import CompactPerMeshWeightedInput


class PerformanceContractTests(unittest.TestCase):
    def test_compact_buffers_scale_linearly_for_required_profiles(self) -> None:
        profiles = ((100, 100_000), (300, 500_000), (500, 1_000_000))
        for bone_count, vertex_count in profiles:
            with self.subTest(bones=bone_count, vertices=vertex_count):
                indices = array("I", range(vertex_count))
                coordinates = array("d", itertools.chain.from_iterable((float(index), 0.0, 0.0) for index in range(vertex_count)))
                weights = array("d", itertools.repeat(1.0, vertex_count))
                compact = CompactPerMeshWeightedInput(
                    "Synthetic", indices, coordinates, weights, array("I")
                )
                temporary_bytes = (
                    len(indices) * indices.itemsize
                    + len(coordinates) * coordinates.itemsize
                    + len(weights) * weights.itemsize
                )
                self.assertEqual(temporary_bytes, vertex_count * 36)
                self.assertNotIsInstance(compact.coordinates, list)
                self.assertNotIsInstance(compact.coordinates, tuple)
                sample = tuple(itertools.islice(compact.iter_weighted_vertices(), 3))
                self.assertEqual(len(sample), 3)
                self.assertEqual(sample[0][0], 0)
                del compact, indices, coordinates, weights
                gc.collect()

    def test_runtime_has_no_numpy_dependency(self) -> None:
        root = Path(__file__).resolve().parents[1] / "ue_chain_prep"
        source = "\n".join(path.read_text(encoding="utf-8") for path in root.rglob("*.py"))
        self.assertNotIn("import numpy", source)
        self.assertNotIn("from numpy", source)

    def test_neutral_capture_accepts_flat_compact_buffers(self) -> None:
        before = MeshCoordinateCapture("Mesh", array("f", (0, 0, 0, 1, 0, 0)))
        after = MeshCoordinateCapture("Mesh", array("f", (0, 0, 0, 1, 0, 0)))
        result = evaluate_mesh_tolerance(before, after, mode="AUTO_PRODUCTION")
        self.assertEqual(2, result.vertex_count)
        self.assertEqual("PASS", result.result)

    def test_draw_callback_does_not_construct_gpu_batches_per_frame(self) -> None:
        callback_source = inspect.getsource(draw._draw_callback)
        self.assertNotIn("batch_for_shader", callback_source)


if __name__ == "__main__":
    unittest.main()
