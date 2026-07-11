"""Swing-only segment alignment helpers."""

from __future__ import annotations

from mathutils import Vector


def swing_rotation(old_segment, new_segment):
    old = Vector(old_segment).normalized()
    new = Vector(new_segment).normalized()
    return old.rotation_difference(new)
