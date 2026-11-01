"""Conservative, name-only bone roles for animation cleanup.

These labels describe name evidence, not whether a bone can safely be removed.
Hierarchy, animation, weights, and explicit metadata still need separate checks.
"""

import re

ROOT = "ROOT"
IK = "IK"
SOCKET = "SOCKET"
WEAPON_ATTACHMENT = "WEAPON_ATTACHMENT"
CONTROL = "CONTROL"
VIRTUAL = "VIRTUAL"
PRIMARY_JOINT = "PRIMARY_JOINT"
SECONDARY = "SECONDARY"
DIRECTION_HELPER = "DIRECTION_HELPER"
UNKNOWN = "UNKNOWN"

_PROTECTED = frozenset({ROOT, IK, SOCKET, WEAPON_ATTACHMENT, CONTROL, VIRTUAL,
                        PRIMARY_JOINT})
_SECONDARY = frozenset({
    "hair", "skirt", "cloth", "clothing", "cape", "coat", "dress", "tail",
    "breast", "bust", "jiggle", "physics", "phys", "spring", "ribbon",
    "ponytail", "pigtail", "masscenter", "twist", "sr", "st",
})
_PRIMARY = frozenset({
    "pelvis", "hips", "hip", "spine", "chest", "neck", "head", "clavicle",
    "collar", "shoulder", "upperarm", "lowerarm", "forearm", "arm", "elbow",
    "hand", "wrist", "thigh", "upleg", "upperleg", "calf", "shin", "leg",
    "knee", "foot", "ankle", "ball", "toe", "thumb", "index", "middle",
    "ring", "pinky", "little", "finger",
})


def _tokens(name):
    # Namespace prefixes do not contribute meaning to the bone itself.
    name = name.rsplit(":", 1)[-1]
    name = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1 \2", name)
    name = re.sub(r"([a-z])([A-Z])", r"\1 \2", name)
    return tuple(re.findall(r"[a-z]+|\d+", name.lower()))


def _has_pair(tokens, first, second):
    return any(a == first and b == second for a, b in zip(tokens, tokens[1:]))


def secondary_chain_name(name):
    """Whether the name contains an explicit secondary/physics-chain marker."""
    tokens = _tokens(name)
    return bool(_SECONDARY.intersection(tokens) or _has_pair(tokens, "mass", "center"))


def direction_helper_name(name, parent_name=""):
    """Recognize explicitly named terminal direction markers, never effectors.

    The optional parent is accepted for callers with hierarchy context; names alone
    are deliberately sufficient here and an arbitrary child is never inferred to
    be a direction helper from its parent.
    """
    tokens = _tokens(name)
    if not tokens or "effector" in tokens:
        return False
    if tokens[-1].isdigit():
        tokens = tokens[:-1]
    return bool(tokens and tokens[-1] in {"end", "tip", "nub"})


def bone_role(name, *, is_socket=False):
    """Return a strong role label based only on the supplied name and metadata."""
    tokens = _tokens(name)
    words = set(tokens)
    if is_socket:
        return SOCKET
    if not tokens:
        return UNKNOWN
    # Explicit rig and attachment markers take precedence over anatomical names.
    if "ik" in words:
        return IK
    if "socket" in words:
        return SOCKET
    if words.intersection({"weapon", "weap", "prop", "attachment", "attach", "gun", "handgun",
                           "rifle", "pistol", "muzzle", "magazine", "sight", "scope", "holster"}):
        return WEAPON_ATTACHMENT
    # Case is a separate terminal marker, never a substring such as "showcase".
    stem = tokens[:-1] if tokens[-1].isdigit() else tokens
    if stem and stem[-1] == "case":
        return WEAPON_ATTACHMENT
    if _has_pair(tokens, "camera", "position") or (
        _has_pair(tokens, "neko", "bot") and "hit" in words
    ):
        return CONTROL
    if words.intersection({"control", "controller", "ctrl", "effector", "pole", "camera", "aim", "target", "marker", "hitbox", "collision"}):
        return CONTROL
    if "vb" in words or "virtual" in words:
        return VIRTUAL
    if secondary_chain_name(name):
        return SECONDARY
    if direction_helper_name(name):
        return DIRECTION_HELPER
    # Root is a standalone name or a common prefixed root, not e.g. hair_root.
    if "root" in words and all(t in {"root", "bip", "armature"} or t.isdigit()
                               for t in tokens):
        return ROOT
    if words.intersection(_PRIMARY):
        return PRIMARY_JOINT
    return UNKNOWN


def protected_role(role):
    """Whether a strong role requires protection from name-only cleanup.

    An unprotected role is not evidence that deletion is safe; callers must
    still check hierarchy, weights, animation, and external references.
    """
    return role in _PROTECTED
