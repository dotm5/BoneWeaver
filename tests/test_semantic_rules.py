from __future__ import annotations

import dataclasses
import json
from pathlib import Path
import unittest

from boneweaver.core.semantic_models import (
    DiscoveredChain,
    GeometryProjectionNeed,
    SecondaryBoneCategory,
    SemanticBoneEvidence,
    SemanticDiscoveryClass,
    SemanticDiscoveryPlan,
)
from boneweaver.core.semantic_rule_loader import (
    load_default_rule_set,
    merge_rule_sets,
    parse_rule_set,
)


def _layer(rule_set_id: str, **overrides):
    payload = {
        "schema_version": "1.0.0",
        "rule_set_id": rule_set_id,
        "rule_set_version": "1.0.0",
        "display_name": rule_set_id,
        "include_tokens": {"strong": [], "medium": [], "generic": []},
        "exclude_tokens": {
            "main_skeleton": [], "socket": [], "ik_control": [],
            "twist_deform": [], "facial": [],
        },
        "category_rules": {},
        "sequence_patterns": [r"^[0-9]+[a-z]?$"],
        "main_skeleton_patterns": [],
        "metadata_rules": {"is_socket": "SOCKET"},
    }
    payload.update(overrides)
    return parse_rule_set(payload)


class SemanticRuleTests(unittest.TestCase):
    def test_enum_values_are_stable(self) -> None:
        self.assertEqual(
            {item.value for item in SemanticDiscoveryClass},
            {"AUTO_INCLUDE", "SUGGEST_INCLUDE", "AMBIGUOUS", "EXCLUDE"},
        )
        self.assertEqual(
            {item.value for item in GeometryProjectionNeed},
            {"REQUIRED", "RECOMMENDED", "NOT_REQUIRED", "UNRESOLVED"},
        )
        self.assertEqual(
            {item.value for item in SecondaryBoneCategory},
            {
                "HAIR", "RIBBON", "SKIRT", "CLOAK", "CAPE", "TAIL",
                "EARRING", "STRAP", "ACCESSORY", "BAG", "BAG_OR_STRAP",
                "BELT", "SCARF", "TASSEL", "CLOTH",
                "CHEST_SECONDARY", "PHYSICS_EXPLICIT", "UNKNOWN_SECONDARY",
                "MAIN_SKELETON", "SOCKET", "IK_CONTROL", "TWIST_DEFORM", "FACIAL",
            },
        )

    def test_discovery_models_are_frozen_slotted_and_rna_free(self) -> None:
        evidence = SemanticBoneEvidence(
            "hair_l_01", "hair_l_01", "hair", "HAIR", ("hair",), "LEFT", 1,
            1.0, 1.0, 1.0, 0.5, 1.0, 0.0, 0.0,
            ("BONEWEAVER_SEMANTIC_STRONG_INCLUDE_TOKEN",), "REQUIRED",
        )
        chain = DiscoveredChain(
            "chain-id", "hair_l_01", ("hair_l_01",), "HAIR", "AUTO_INCLUDE",
            0.9, 1, 0, (), ("hair_l_01",), ("BONEWEAVER_SEMANTIC_STRONG_INCLUDE_TOKEN",),
        )
        plan = SemanticDiscoveryPlan(
            "SEMANTIC_DISCOVERY_PLAN", "2.0.0", "semantic-discovery-v0.2.0",
            "Rig", "fingerprint", ("default-ue-secondary@0.2.0",),
            (chain,), (evidence,), (), (),
        )
        with self.assertRaises(dataclasses.FrozenInstanceError):
            plan.kind = "changed"
        self.assertFalse(hasattr(plan, "__dict__"))
        self.assertNotIn("bpy", repr(dataclasses.asdict(plan)))

    def test_default_rules_are_external_versioned_and_complete(self) -> None:
        rules = load_default_rule_set()
        self.assertEqual(rules.schema_version, "1.0.0")
        self.assertEqual(rules.rule_set_id, "default-ue-secondary")
        self.assertEqual(rules.rule_set_version, "0.2.0")
        self.assertIn("hair", rules.include_tokens["strong"])
        self.assertIn("part", rules.include_tokens["medium"])
        self.assertIn("socket", rules.exclude_tokens["socket"])
        self.assertEqual(rules.metadata_rules["is_socket"], "SOCKET")

        root = Path(__file__).resolve().parents[1] / "boneweaver"
        schema = json.loads((root / "schemas" / "semantic-rule-set.schema.json").read_text("utf-8"))
        discovery_schema = json.loads((root / "schemas" / "semantic-discovery-plan.schema.json").read_text("utf-8"))
        self.assertFalse(schema["additionalProperties"])
        self.assertFalse(discovery_schema["additionalProperties"])

    def test_later_rule_layers_override_earlier_token_decisions_and_categories(self) -> None:
        default = _layer(
            "default",
            include_tokens={"strong": ["hair"], "medium": [], "generic": []},
            exclude_tokens={
                "main_skeleton": ["body"], "socket": [], "ik_control": [],
                "twist_deform": [], "facial": [],
            },
            category_rules={"HAIR": {"tokens": ["hair"], "maximum_class": "AUTO_INCLUDE"}},
        )
        importer = _layer(
            "importer",
            include_tokens={"strong": ["body"], "medium": [], "generic": []},
        )
        game = _layer(
            "game",
            category_rules={"HAIR": {"tokens": ["hair", "mane"], "maximum_class": "SUGGEST_INCLUDE"}},
        )
        user = _layer(
            "user",
            exclude_tokens={
                "main_skeleton": ["hair"], "socket": [], "ik_control": [],
                "twist_deform": [], "facial": [],
            },
        )
        merged = merge_rule_sets((default, importer, game, user))
        self.assertIn("body", merged.strong_include_tokens)
        self.assertNotIn("body", merged.main_skeleton_tokens)
        self.assertIn("hair", merged.main_skeleton_tokens)
        self.assertNotIn("hair", merged.strong_include_tokens)
        self.assertEqual(merged.category_rules["HAIR"].maximum_class, "SUGGEST_INCLUDE")
        self.assertEqual(merged.rule_set_ids, ("default@1.0.0", "importer@1.0.0", "game@1.0.0", "user@1.0.0"))

    def test_missing_required_rule_field_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "metadata_rules"):
            parse_rule_set({
                "schema_version": "1.0.0", "rule_set_id": "bad",
                "rule_set_version": "1.0.0", "display_name": "bad",
                "include_tokens": {}, "exclude_tokens": {}, "category_rules": {},
                "sequence_patterns": [], "main_skeleton_patterns": [],
            })


if __name__ == "__main__":
    unittest.main()
