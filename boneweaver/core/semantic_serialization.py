"""Strict JSON serialization for immutable semantic discovery plans."""

from __future__ import annotations

import dataclasses
import json
from collections.abc import Mapping
import re

from .semantic_models import (
    DiscoveredChain,
    GeometryProjectionNeed,
    SecondaryBoneCategory,
    SemanticBoneEvidence,
    SemanticDiscoveryClass,
    SemanticDiscoveryPlan,
)


_PLAN_FIELDS = frozenset({
    "kind", "schema_version", "algorithm_version", "armature_object_name",
    "armature_fingerprint", "rule_set_ids", "chains", "bone_evidence",
    "excluded_bones", "ambiguous_bones",
})
_CHAIN_FIELDS = frozenset({
    "discovery_id", "root_bone_name", "bone_names", "category",
    "discovery_class", "discovery_score", "needs_projection_count",
    "already_valid_count", "branch_bone_names", "leaf_bone_names",
    "reason_codes",
})
_EVIDENCE_FIELDS = frozenset({
    "bone_name", "normalized_name", "semantic_stem", "category",
    "semantic_tokens", "side", "sequence_index", "semantic_score",
    "hierarchy_score", "sequence_score", "weight_score",
    "geometry_mismatch_score", "metadata_score", "exclusion_penalty",
    "reason_codes", "geometry_projection_need", "discovery_class",
    "discovery_score",
})
_SEQUENCE_FIELDS = frozenset({
    "rule_set_ids", "chains", "bone_evidence", "excluded_bones",
    "ambiguous_bones", "bone_names", "branch_bone_names", "leaf_bone_names",
    "reason_codes", "semantic_tokens",
})
_EXPECTED_CONSTANTS = {
    "kind": "SEMANTIC_DISCOVERY_PLAN",
    "schema_version": "2.0.0",
    "algorithm_version": "semantic-discovery-v0.2.0",
}
_CATEGORIES = frozenset(item.value for item in SecondaryBoneCategory)
_DISCOVERY_CLASSES = frozenset(item.value for item in SemanticDiscoveryClass)
_GEOMETRY_NEEDS = frozenset(item.value for item in GeometryProjectionNeed)
_SHA256 = re.compile(r"^[0-9a-f]{64}$")


def _require_exact_fields(payload, expected, label):
    if not isinstance(payload, Mapping):
        raise ValueError(f"{label} must be an object")
    actual = frozenset(payload)
    missing = sorted(expected - actual)
    unknown = sorted(actual - expected)
    if missing:
        raise ValueError(f"{label} missing required field: {missing[0]}")
    if unknown:
        raise ValueError(f"{label} has unknown field: {unknown[0]}")


def _tuple_field(payload, field, label):
    value = payload[field]
    if not isinstance(value, (list, tuple)):
        raise ValueError(f"{label}.{field} must be an array")
    return tuple(value)


def _require_enum(value, allowed, label):
    if value not in allowed:
        raise ValueError(f"invalid {label}: {value}")


def _require_score(value, label):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not 0.0 <= float(value) <= 1.0:
        raise ValueError(f"{label} must be a number in [0, 1]")


def semantic_discovery_plan_to_dict(plan: SemanticDiscoveryPlan) -> dict:
    """Return a JSON-native mapping with deterministic field content."""
    if not isinstance(plan, SemanticDiscoveryPlan):
        raise TypeError("plan must be SemanticDiscoveryPlan")

    def json_native(value):
        if dataclasses.is_dataclass(value):
            return {
                field.name: json_native(getattr(value, field.name))
                for field in dataclasses.fields(value)
            }
        if isinstance(value, tuple):
            return [json_native(item) for item in value]
        if isinstance(value, Mapping):
            return {str(key): json_native(item) for key, item in value.items()}
        return value

    return json_native(plan)


def semantic_discovery_plan_to_json(plan: SemanticDiscoveryPlan, *, indent=2) -> str:
    return json.dumps(
        semantic_discovery_plan_to_dict(plan),
        ensure_ascii=False,
        sort_keys=True,
        indent=indent,
    )


def semantic_discovery_plan_from_dict(payload) -> SemanticDiscoveryPlan:
    """Rebuild a plan while rejecting every unknown or missing field."""
    _require_exact_fields(payload, _PLAN_FIELDS, "semantic discovery plan")
    for field, expected in _EXPECTED_CONSTANTS.items():
        if payload[field] != expected:
            raise ValueError(f"unsupported semantic discovery {field}: {payload[field]}")
    chains = []
    for index, item in enumerate(_tuple_field(payload, "chains", "semantic discovery plan")):
        label = f"chains[{index}]"
        _require_exact_fields(item, _CHAIN_FIELDS, label)
        if not isinstance(item["discovery_id"], str) or _SHA256.fullmatch(item["discovery_id"]) is None:
            raise ValueError(f"{label}.discovery_id must be a lowercase sha256")
        _require_enum(item["category"], _CATEGORIES, f"{label}.category")
        _require_enum(item["discovery_class"], _DISCOVERY_CLASSES, f"{label}.discovery_class")
        _require_score(item["discovery_score"], f"{label}.discovery_score")
        values = dict(item)
        for field in _SEQUENCE_FIELDS.intersection(_CHAIN_FIELDS):
            values[field] = _tuple_field(item, field, label)
        chains.append(DiscoveredChain(**values))
    evidence = []
    for index, item in enumerate(_tuple_field(payload, "bone_evidence", "semantic discovery plan")):
        label = f"bone_evidence[{index}]"
        _require_exact_fields(item, _EVIDENCE_FIELDS, label)
        _require_enum(item["category"], _CATEGORIES, f"{label}.category")
        _require_enum(item["discovery_class"], _DISCOVERY_CLASSES, f"{label}.discovery_class")
        _require_enum(item["geometry_projection_need"], _GEOMETRY_NEEDS, f"{label}.geometry_projection_need")
        for field in (
            "semantic_score", "hierarchy_score", "sequence_score", "weight_score",
            "geometry_mismatch_score", "metadata_score", "exclusion_penalty",
            "discovery_score",
        ):
            _require_score(item[field], f"{label}.{field}")
        values = dict(item)
        for field in _SEQUENCE_FIELDS.intersection(_EVIDENCE_FIELDS):
            values[field] = _tuple_field(item, field, label)
        evidence.append(SemanticBoneEvidence(**values))
    return SemanticDiscoveryPlan(
        kind=payload["kind"],
        schema_version=payload["schema_version"],
        algorithm_version=payload["algorithm_version"],
        armature_object_name=payload["armature_object_name"],
        armature_fingerprint=payload["armature_fingerprint"],
        rule_set_ids=_tuple_field(payload, "rule_set_ids", "semantic discovery plan"),
        chains=tuple(chains),
        bone_evidence=tuple(evidence),
        excluded_bones=_tuple_field(payload, "excluded_bones", "semantic discovery plan"),
        ambiguous_bones=_tuple_field(payload, "ambiguous_bones", "semantic discovery plan"),
    )


def semantic_discovery_plan_from_json(text: str) -> SemanticDiscoveryPlan:
    if not isinstance(text, str):
        raise TypeError("text must be a JSON string")
    return semantic_discovery_plan_from_dict(json.loads(text))
