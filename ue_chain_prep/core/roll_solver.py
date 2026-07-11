"""Pure roll reference construction for minimal twist, transport, and radial modes."""

from __future__ import annotations

from mathutils import Vector


def _project(reference, axis):
    axis = Vector(axis).normalized()
    value = Vector(reference) - axis * Vector(reference).dot(axis)
    return value.normalized() if value.length > 1.0e-9 else None


def _fallback(axis, *references):
    for reference in references:
        projected = _project(reference, axis)
        if projected is not None:
            return tuple(projected), True
    axis = Vector(axis).normalized()
    basis = min((Vector((1,0,0)), Vector((0,1,0)), Vector((0,0,1))), key=lambda value: abs(value.dot(axis)))
    return tuple(_project(basis, axis)), True


def minimal_twist_reference(new_y, old_z, old_x, parent_z=None):
    projected = _project(old_z, new_y)
    if projected is not None:
        return tuple(projected), False
    return _fallback(new_y, parent_z or (0,0,0), old_x)


def parallel_transport_reference(new_y, parent_final_z, old_z, transport_weight, old_axis_weight):
    transported = _project(parent_final_z, new_y)
    old = _project(old_z, new_y)
    if transported is None or old is None:
        return _fallback(new_y, parent_final_z, old_z)
    combined = transported * transport_weight + old * old_axis_weight
    if combined.length <= 1.0e-9:
        return _fallback(new_y, parent_final_z, old_z)
    combined.normalize()
    if combined.dot(Vector(parent_final_z)) < 0.0:
        combined.negate()
    return tuple(combined), False


def radial_reference(new_y, head, reference_point):
    radial = Vector(head) - Vector(reference_point)
    projected = _project(radial, new_y)
    if projected is not None:
        return tuple(projected), False
    return _fallback(new_y, (1,0,0), (0,0,1))
