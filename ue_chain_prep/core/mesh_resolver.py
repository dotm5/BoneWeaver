"""Resolve associated meshes from Armature modifiers, not object parenting."""

from __future__ import annotations

import bpy

from .models import MeshBindingRef, ValidationIssue


def _blocker(code: str, message: str, objects: tuple[str, ...]) -> ValidationIssue:
    return ValidationIssue("BLOCKER", code, code.lower(), message, object_names=objects)


def find_associated_meshes(armature_obj):
    bindings = []
    issues = []
    for obj in sorted(bpy.data.objects, key=lambda item: item.name):
        if obj.type != "MESH":
            continue
        modifiers = [
            modifier
            for modifier in obj.modifiers
            if modifier.type == "ARMATURE" and modifier.object == armature_obj
        ]
        if len(modifiers) > 1:
            issues.append(
                _blocker(
                    "UECP_AMBIGUOUS_ARMATURE_MODIFIER",
                    "Mesh has multiple modifiers targeting the same Armature",
                    (obj.name,),
                )
            )
        elif len(modifiers) == 1:
            bindings.append(MeshBindingRef(obj.name, modifiers[0].name))
    return tuple(bindings), tuple(issues)
