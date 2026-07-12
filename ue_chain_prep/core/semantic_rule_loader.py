"""Strict loading and deterministic precedence merging for semantic rule sets."""

from __future__ import annotations

import json
from pathlib import Path
import re
from types import MappingProxyType

from .semantic_models import (
    MergedSemanticRules,
    SecondaryBoneCategory,
    SemanticCategoryRule,
    SemanticDiscoveryClass,
    SemanticRuleSet,
)


SEMANTIC_RULE_SCHEMA_VERSION = "1.0.0"
_REQUIRED = {
    "schema_version", "rule_set_id", "rule_set_version", "display_name",
    "include_tokens", "exclude_tokens", "category_rules", "sequence_patterns",
    "main_skeleton_patterns", "metadata_rules",
}
_INCLUDE_KINDS = ("strong", "medium", "generic")
_EXCLUDE_KINDS = ("main_skeleton", "socket", "ik_control", "twist_deform", "facial")


def _string_tuple(value, field: str) -> tuple[str, ...]:
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ValueError(f"{field} must be an array of strings")
    return tuple(dict.fromkeys(item.casefold() for item in value))


def parse_rule_set(payload: dict) -> SemanticRuleSet:
    if not isinstance(payload, dict):
        raise ValueError("semantic rule set must be an object")
    missing = sorted(_REQUIRED - set(payload))
    if missing:
        raise ValueError(f"missing required field: {missing[0]}")
    unknown = sorted(set(payload) - _REQUIRED)
    if unknown:
        raise ValueError(f"unknown semantic rule field: {unknown[0]}")
    if payload["schema_version"] != SEMANTIC_RULE_SCHEMA_VERSION:
        raise ValueError(f"unsupported semantic rule schema: {payload['schema_version']}")
    for field in ("rule_set_id", "rule_set_version", "display_name"):
        if not isinstance(payload[field], str) or not payload[field]:
            raise ValueError(f"{field} must be a non-empty string")

    include = payload["include_tokens"]
    exclude = payload["exclude_tokens"]
    if not isinstance(include, dict) or set(include) != set(_INCLUDE_KINDS):
        raise ValueError("include_tokens must contain strong, medium, and generic")
    if not isinstance(exclude, dict) or set(exclude) != set(_EXCLUDE_KINDS):
        raise ValueError("exclude_tokens must contain all exclusion categories")
    parsed_include = MappingProxyType({kind: _string_tuple(include[kind], f"include_tokens.{kind}") for kind in _INCLUDE_KINDS})
    parsed_exclude = MappingProxyType({kind: _string_tuple(exclude[kind], f"exclude_tokens.{kind}") for kind in _EXCLUDE_KINDS})

    category_payload = payload["category_rules"]
    if not isinstance(category_payload, dict):
        raise ValueError("category_rules must be an object")
    valid_categories = {item.value for item in SecondaryBoneCategory}
    valid_classes = {item.value for item in SemanticDiscoveryClass}
    categories = {}
    for category, rule in category_payload.items():
        if category not in valid_categories or not isinstance(rule, dict):
            raise ValueError(f"invalid category rule: {category}")
        if set(rule) != {"tokens", "maximum_class"} or rule["maximum_class"] not in valid_classes:
            raise ValueError(f"invalid category rule body: {category}")
        categories[category] = SemanticCategoryRule(
            _string_tuple(rule["tokens"], f"category_rules.{category}.tokens"),
            rule["maximum_class"],
        )
    sequences = _string_tuple(payload["sequence_patterns"], "sequence_patterns")
    skeleton_patterns = _string_tuple(payload["main_skeleton_patterns"], "main_skeleton_patterns")
    for pattern in sequences + skeleton_patterns:
        try:
            re.compile(pattern)
        except re.error as error:
            raise ValueError(f"invalid regex {pattern!r}: {error}") from error
    metadata = payload["metadata_rules"]
    if not isinstance(metadata, dict) or not all(isinstance(key, str) and isinstance(value, str) for key, value in metadata.items()):
        raise ValueError("metadata_rules must map strings to strings")
    normalized_metadata = {
        key.casefold(): value.upper() for key, value in metadata.items()
    }
    invalid_metadata_categories = sorted(set(normalized_metadata.values()) - valid_categories)
    if invalid_metadata_categories:
        raise ValueError(f"invalid metadata category: {invalid_metadata_categories[0]}")
    return SemanticRuleSet(
        payload["schema_version"], payload["rule_set_id"], payload["rule_set_version"],
        payload["display_name"], parsed_include, parsed_exclude,
        MappingProxyType(categories), sequences, skeleton_patterns,
        MappingProxyType(normalized_metadata),
    )


def load_rule_set(path: str | Path) -> SemanticRuleSet:
    return parse_rule_set(json.loads(Path(path).read_text(encoding="utf-8")))


def load_default_rule_set() -> SemanticRuleSet:
    return load_rule_set(Path(__file__).resolve().parents[1] / "rules" / "default-ue-secondary.json")


def merge_rule_sets(rule_sets: tuple[SemanticRuleSet, ...] | list[SemanticRuleSet]) -> MergedSemanticRules:
    includes = {kind: set() for kind in _INCLUDE_KINDS}
    excludes = {kind: set() for kind in _EXCLUDE_KINDS}
    categories = {}
    sequences: list[str] = []
    skeleton_patterns: list[str] = []
    metadata = {}
    identities = []
    for rules in rule_sets:
        identities.append(f"{rules.rule_set_id}@{rules.rule_set_version}")
        for kind in _INCLUDE_KINDS:
            for token in rules.include_tokens[kind]:
                for values in includes.values():
                    values.discard(token)
                for values in excludes.values():
                    values.discard(token)
                includes[kind].add(token)
        for kind in _EXCLUDE_KINDS:
            for token in rules.exclude_tokens[kind]:
                for values in includes.values():
                    values.discard(token)
                for values in excludes.values():
                    values.discard(token)
                excludes[kind].add(token)
        categories.update(rules.category_rules)
        sequences.extend(pattern for pattern in rules.sequence_patterns if pattern not in sequences)
        skeleton_patterns.extend(pattern for pattern in rules.main_skeleton_patterns if pattern not in skeleton_patterns)
        metadata.update(rules.metadata_rules)
    return MergedSemanticRules(
        tuple(identities), frozenset(includes["strong"]), frozenset(includes["medium"]),
        frozenset(includes["generic"]), frozenset(excludes["main_skeleton"]),
        frozenset(excludes["socket"]), frozenset(excludes["ik_control"]),
        frozenset(excludes["twist_deform"]), frozenset(excludes["facial"]),
        MappingProxyType(dict(categories)), tuple(sequences), tuple(skeleton_patterns),
        MappingProxyType(dict(metadata)),
    )
