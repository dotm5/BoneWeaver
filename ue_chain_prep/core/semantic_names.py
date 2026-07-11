"""Deterministic parsing of common UE/importer bone-name conventions."""

from __future__ import annotations

import re
import unicodedata


_DELIMITERS = re.compile(r"[^0-9a-z]+")
_SEQUENCE_TOKEN = re.compile(r"^(?P<index>[0-9]+)(?:[a-z])?$")
_SIDES = {
    "l": "LEFT",
    "left": "LEFT",
    "lf": "LEFT",
    "r": "RIGHT",
    "right": "RIGHT",
    "rt": "RIGHT",
}


def normalize_bone_name(name: str) -> str:
    """Return a namespace-free, case-folded, underscore-delimited name."""
    if not isinstance(name, str):
        raise TypeError("bone name must be a string")
    local_name = name.rsplit(":", 1)[-1]
    folded = unicodedata.normalize("NFKC", local_name).casefold().strip()
    return _DELIMITERS.sub("_", folded).strip("_")


def tokenize_bone_name(name: str) -> tuple[str, ...]:
    """Tokenize a normalized name without returning empty delimiter runs."""
    normalized = normalize_bone_name(name)
    return tuple(token for token in normalized.split("_") if token)


def extract_side_marker(name: str) -> str | None:
    """Extract a side marker only when it occupies a complete token."""
    sides = {_SIDES[token] for token in tokenize_bone_name(name) if token in _SIDES}
    return next(iter(sides)) if len(sides) == 1 else None


def extract_sequence_index(name: str) -> int | None:
    """Return the rightmost explicit numeric or numeric-alpha sequence token."""
    for token in reversed(tokenize_bone_name(name)):
        match = _SEQUENCE_TOKEN.fullmatch(token)
        if match:
            return int(match.group("index"))
    return None


def extract_semantic_stem(name: str) -> str:
    """Remove recognized side and sequence suffix tokens from a semantic name."""
    semantic_tokens = tuple(
        token
        for token in tokenize_bone_name(name)
        if token not in _SIDES and _SEQUENCE_TOKEN.fullmatch(token) is None
    )
    return "_".join(semantic_tokens)
