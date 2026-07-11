from __future__ import annotations

import unittest

from ue_chain_prep.core.semantic_names import (
    extract_semantic_stem,
    extract_sequence_index,
    extract_side_marker,
    normalize_bone_name,
    tokenize_bone_name,
)


class SemanticNameTests(unittest.TestCase):
    def test_equivalent_ue_names_share_normal_form_and_semantics(self) -> None:
        names = (
            "hair_f_l_01",
            "hair.f.l.01",
            "Hair-F-L-01",
            "Character:hair_f_l_01",
        )
        self.assertEqual({normalize_bone_name(name) for name in names}, {"hair_f_l_01"})
        self.assertEqual({extract_semantic_stem(name) for name in names}, {"hair_f"})
        self.assertEqual({extract_side_marker(name) for name in names}, {"LEFT"})
        self.assertEqual({extract_sequence_index(name) for name in names}, {1})

    def test_supported_side_markers_are_only_recognized_as_tokens(self) -> None:
        left = ("cape_l_01", "cape.left.01", "cape_L_01", "cape_lf_01")
        right = ("cape_r_01", "cape.right.01", "cape_R_01", "cape_rt_01")
        self.assertTrue(all(extract_side_marker(name) == "LEFT" for name in left))
        self.assertTrue(all(extract_side_marker(name) == "RIGHT" for name in right))
        for name in ("collar_01", "ribbon_01", "lowerarm_01", "hair_01"):
            self.assertIsNone(extract_side_marker(name), name)

    def test_sequence_and_alpha_branch_suffixes_do_not_pollute_stem(self) -> None:
        self.assertEqual(extract_sequence_index("bag_r_03a_01"), 1)
        self.assertEqual(extract_semantic_stem("bag_r_03a_01"), "bag")
        self.assertEqual(extract_semantic_stem("ribbon_hand_L_02"), "ribbon_hand")
        self.assertEqual(extract_sequence_index("hair_12b"), 12)
        self.assertEqual(extract_semantic_stem("hair_12b"), "hair")

    def test_tokenization_strips_namespace_and_empty_delimiters(self) -> None:
        self.assertEqual(
            tokenize_bone_name("Game.Character:  Hair__Ribbon..L--003 "),
            ("hair", "ribbon", "l", "003"),
        )

    def test_names_without_sequence_remain_unsequenced(self) -> None:
        self.assertIsNone(extract_sequence_index("Bip001-Spine"))
        self.assertEqual(extract_semantic_stem("Bip001-Spine"), "bip001_spine")


if __name__ == "__main__":
    unittest.main()
