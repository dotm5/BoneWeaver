"""Immutable public models for semantic chain discovery."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from types import MappingProxyType
from typing import Mapping


class StableSemanticEnum(str, Enum):
    """String enum with serialized values that form part of the public contract."""


class SemanticDiscoveryClass(StableSemanticEnum):
    AUTO_INCLUDE = "AUTO_INCLUDE"
    SUGGEST_INCLUDE = "SUGGEST_INCLUDE"
    AMBIGUOUS = "AMBIGUOUS"
    EXCLUDE = "EXCLUDE"


class SecondaryBoneCategory(StableSemanticEnum):
    HAIR = "HAIR"
    RIBBON = "RIBBON"
    SKIRT = "SKIRT"
    CLOAK = "CLOAK"
    CAPE = "CAPE"
    TAIL = "TAIL"
    EARRING = "EARRING"
    ACCESSORY = "ACCESSORY"
    BAG_OR_STRAP = "BAG_OR_STRAP"
    BELT = "BELT"
    CLOTH = "CLOTH"
    CHEST_SECONDARY = "CHEST_SECONDARY"
    PHYSICS_EXPLICIT = "PHYSICS_EXPLICIT"
    UNKNOWN_SECONDARY = "UNKNOWN_SECONDARY"
    MAIN_SKELETON = "MAIN_SKELETON"
    SOCKET = "SOCKET"
    IK_CONTROL = "IK_CONTROL"
    TWIST_DEFORM = "TWIST_DEFORM"
    FACIAL = "FACIAL"


class GeometryProjectionNeed(StableSemanticEnum):
    REQUIRED = "REQUIRED"
    RECOMMENDED = "RECOMMENDED"
    NOT_REQUIRED = "NOT_REQUIRED"
    UNRESOLVED = "UNRESOLVED"


@dataclass(frozen=True, slots=True)
class SemanticBoneEvidence:
    bone_name: str
    normalized_name: str
    semantic_stem: str
    category: str
    semantic_tokens: tuple[str, ...]
    side: str | None
    sequence_index: int | None
    semantic_score: float
    hierarchy_score: float
    sequence_score: float
    weight_score: float
    geometry_mismatch_score: float
    metadata_score: float
    exclusion_penalty: float
    reason_codes: tuple[str, ...]
    geometry_projection_need: str = GeometryProjectionNeed.UNRESOLVED.value


@dataclass(frozen=True, slots=True)
class DiscoveredChain:
    discovery_id: str
    root_bone_name: str
    bone_names: tuple[str, ...]
    category: str
    discovery_class: str
    discovery_score: float
    needs_projection_count: int
    already_valid_count: int
    branch_bone_names: tuple[str, ...]
    leaf_bone_names: tuple[str, ...]
    reason_codes: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class SemanticDiscoveryPlan:
    kind: str
    schema_version: str
    algorithm_version: str
    armature_object_name: str
    armature_fingerprint: str
    rule_set_ids: tuple[str, ...]
    chains: tuple[DiscoveredChain, ...]
    bone_evidence: tuple[SemanticBoneEvidence, ...]
    excluded_bones: tuple[str, ...]
    ambiguous_bones: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class SemanticCategoryRule:
    tokens: tuple[str, ...]
    maximum_class: str


@dataclass(frozen=True, slots=True)
class SemanticRuleSet:
    schema_version: str
    rule_set_id: str
    rule_set_version: str
    display_name: str
    include_tokens: Mapping[str, tuple[str, ...]]
    exclude_tokens: Mapping[str, tuple[str, ...]]
    category_rules: Mapping[str, SemanticCategoryRule]
    sequence_patterns: tuple[str, ...]
    main_skeleton_patterns: tuple[str, ...]
    metadata_rules: Mapping[str, str]


@dataclass(frozen=True, slots=True)
class MergedSemanticRules:
    rule_set_ids: tuple[str, ...]
    strong_include_tokens: frozenset[str]
    medium_include_tokens: frozenset[str]
    generic_include_tokens: frozenset[str]
    main_skeleton_tokens: frozenset[str]
    socket_tokens: frozenset[str]
    ik_control_tokens: frozenset[str]
    twist_deform_tokens: frozenset[str]
    facial_tokens: frozenset[str]
    category_rules: Mapping[str, SemanticCategoryRule]
    sequence_patterns: tuple[str, ...]
    main_skeleton_patterns: tuple[str, ...]
    metadata_rules: Mapping[str, str]


def immutable_mapping(values: Mapping):
    return MappingProxyType(dict(values))
