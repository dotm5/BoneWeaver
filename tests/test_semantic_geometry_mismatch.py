from __future__ import annotations

from dataclasses import dataclass
import unittest

from ue_chain_prep.core.semantic_discovery import (
    assess_geometry_projection,
    detect_uniform_imported_display_length,
)
from ue_chain_prep.core.semantic_models import GeometryProjectionNeed


@dataclass(frozen=True)
class StubBone:
    name: str
    parent_name: str | None
    child_names: tuple[str, ...]
    head: tuple[float, float, float]
    tail: tuple[float, float, float]


def _assessment(tail, child_head=(0.0, 1.0, 0.0)):
    parent = StubBone("hair_l_01", None, ("hair_l_02",), (0.0, 0.0, 0.0), tail)
    child = StubBone("hair_l_02", "hair_l_01", (), child_head, (0.0, 1.2, 0.0))
    return assess_geometry_projection(parent, {parent.name: parent, child.name: child})


class SemanticGeometryMismatchTests(unittest.TestCase):
    def test_tail_at_child_head_is_not_required(self) -> None:
        result = _assessment((0.0, 1.0, 0.0))
        self.assertEqual(result.need, GeometryProjectionNeed.NOT_REQUIRED.value)
        self.assertEqual(result.reason_codes, ("UECP_SEMANTIC_ALREADY_CONTINUOUS",))

    def test_fixed_short_tail_is_required_with_uniform_import_signal(self) -> None:
        bones = []
        heads = (0.0, 1.0, 2.7, 5.1, 8.4, 12.8)
        for index, y in enumerate(heads):
            bones.append(StubBone(
                f"hair_{index}", f"hair_{index - 1}" if index else None,
                (f"hair_{index + 1}",) if index + 1 < len(heads) else (),
                (0.0, y, 0.0), (0.0, y + 0.1, 0.0),
            ))
        uniform = detect_uniform_imported_display_length(tuple(bones))
        self.assertTrue(uniform.detected)
        result = assess_geometry_projection(bones[2], {bone.name: bone for bone in bones}, uniform)
        self.assertEqual(result.need, GeometryProjectionNeed.REQUIRED.value)
        self.assertIn("UECP_SEMANTIC_UNIFORM_DISPLAY_LENGTH", result.reason_codes)
        self.assertIn("UECP_SEMANTIC_TAIL_CHILD_MISMATCH", result.reason_codes)

    def test_reversed_direction_is_required(self) -> None:
        result = _assessment((0.0, -0.5, 0.0))
        self.assertEqual(result.need, GeometryProjectionNeed.REQUIRED.value)
        self.assertGreater(result.direction_angle_degrees, 170.0)

    def test_correct_direction_but_short_length_is_required(self) -> None:
        result = _assessment((0.0, 0.3, 0.0))
        self.assertEqual(result.need, GeometryProjectionNeed.REQUIRED.value)
        self.assertAlmostEqual(result.length_ratio, 0.3)

    def test_small_tail_error_is_recommended(self) -> None:
        result = _assessment((0.03, 0.98, 0.0))
        self.assertEqual(result.need, GeometryProjectionNeed.RECOMMENDED.value)
        self.assertLess(result.direction_angle_degrees, 3.0)

    def test_leaf_is_unresolved_for_terminal_solver(self) -> None:
        leaf = StubBone("hair_l_03", "hair_l_02", (), (0.0, 2.0, 0.0), (0.0, 2.1, 0.0))
        result = assess_geometry_projection(leaf, {leaf.name: leaf})
        self.assertEqual(result.need, GeometryProjectionNeed.UNRESOLVED.value)
        self.assertEqual(result.reason_codes, ())

    def test_branch_is_unresolved_for_branch_resolver(self) -> None:
        branch = StubBone("hair_l_01", None, ("a", "b"), (0.0, 0.0, 0.0), (0.0, 0.1, 0.0))
        a = StubBone("a", branch.name, (), (0.0, 1.0, 0.0), (0.0, 1.1, 0.0))
        b = StubBone("b", branch.name, (), (1.0, 0.0, 0.0), (1.1, 0.0, 0.0))
        result = assess_geometry_projection(branch, {bone.name: bone for bone in (branch, a, b)})
        self.assertEqual(result.need, GeometryProjectionNeed.UNRESOLVED.value)
        self.assertEqual(result.reason_codes, ("UECP_SEMANTIC_BRANCH_DETECTED",))

    def test_uniform_lengths_without_variable_hierarchy_distances_are_not_import_signal(self) -> None:
        bones = tuple(
            StubBone(
                f"b{index}", f"b{index - 1}" if index else None,
                (f"b{index + 1}",) if index < 5 else (),
                (0.0, float(index), 0.0), (0.0, float(index) + 0.9, 0.0),
            )
            for index in range(6)
        )
        self.assertFalse(detect_uniform_imported_display_length(bones).detected)


if __name__ == "__main__":
    unittest.main()
