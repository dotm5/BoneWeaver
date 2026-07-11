"""Weighted head-centered point-cloud statistics for terminal evidence."""

from __future__ import annotations

import math
from dataclasses import dataclass

from .eigen3 import jacobi_eigen_symmetric_3x3
from .models import WeightCloudStats


@dataclass(frozen=True, slots=True)
class WeightEvidenceCollection:
    points_by_bone: dict[str, tuple[tuple[tuple[float, float, float], float], ...]]
    vertex_count: int
    membership_count: int
    peak_point_count: int


def collect_weight_evidence(
    armature_obj,
    mesh_objects,
    target_bone_names,
    *,
    minimum_weight,
    weight_exponent,
    use_vertex_area_weight,
    exclusivity_mode,
):
    """Collect all target memberships in one pass per mesh vertex."""
    targets = set(target_bone_names)
    collected = {name: [] for name in sorted(targets)}
    vertex_count = 0
    membership_count = 0
    for mesh_obj in mesh_objects:
        mesh = mesh_obj.data
        transform = armature_obj.matrix_world.inverted_safe() @ mesh_obj.matrix_world
        positions = tuple(transform @ vertex.co for vertex in mesh.vertices)
        areas = [0.0] * len(mesh.vertices)
        if use_vertex_area_weight and mesh.polygons:
            mesh.calc_loop_triangles()
            for triangle in mesh.loop_triangles:
                first, second, third = (positions[index] for index in triangle.vertices)
                area = (second - first).cross(third - first).length * 0.5
                for index in triangle.vertices:
                    areas[index] += area / 3.0
        else:
            areas = [1.0] * len(mesh.vertices)
        group_names = {group.index: group.name for group in mesh_obj.vertex_groups}
        target_indices = {index: name for index, name in group_names.items() if name in targets}
        for vertex in mesh.vertices:
            vertex_count += 1
            memberships = []
            for membership in vertex.groups:
                membership_count += 1
                name = target_indices.get(membership.group)
                if name is not None:
                    memberships.append((name, float(membership.weight)))
            denominator = sum(weight for _, weight in memberships)
            for name, raw_weight in memberships:
                adjusted = max(raw_weight - minimum_weight, 0.0) ** weight_exponent
                if adjusted <= 0.0:
                    continue
                exclusivity = raw_weight / max(denominator, 1.0e-12) if exclusivity_mode in {"CHAIN_NORMALIZED", "SELECTED_SET_NORMALIZED"} else 1.0
                statistical_weight = areas[vertex.index] * adjusted * exclusivity
                if statistical_weight > 0.0:
                    collected[name].append((tuple(float(value) for value in positions[vertex.index]), statistical_weight))
    frozen = {name: tuple(points) for name, points in collected.items()}
    return WeightEvidenceCollection(frozen, vertex_count, membership_count, max((len(points) for points in frozen.values()), default=0))


def _normalize(vector):
    length = math.sqrt(sum(value * value for value in vector))
    return tuple(value / length for value in vector) if length > 1.0e-12 else None


def weighted_percentile(samples, percentile):
    values = sorted((float(value), float(weight)) for value, weight in samples if weight > 0.0)
    if not values:
        raise ValueError("weighted percentile needs positive samples")
    target = max(0.0, min(1.0, float(percentile))) * sum(weight for _, weight in values)
    cumulative = 0.0
    for value, weight in values:
        cumulative += weight
        if cumulative >= target:
            return value
    return values[-1][0]


def analyze_weight_cloud(bone_name, head, weighted_points, mesh_names=()):
    points = tuple((tuple(float(v) for v in point), float(weight)) for point, weight in weighted_points if weight > 0.0)
    total = sum(weight for _, weight in points)
    if len(points) < 3 or total <= 1.0e-12:
        return WeightCloudStats(bone_name, tuple(mesh_names), len(points), float(len(points)), total, None, None, None, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, None, "INSUFFICIENT", 0.0, ("UECP_INSUFFICIENT_WEIGHT_CLOUD",))
    centroid = tuple(sum(point[i] * weight for point, weight in points) / total for i in range(3))
    offsets = [(tuple(point[i] - head[i] for i in range(3)), weight) for point, weight in points]
    covariance = tuple(tuple(sum(weight * offset[row] * offset[column] for offset, weight in offsets) / total for column in range(3)) for row in range(3))
    values, vectors = jacobi_eigen_symmetric_3x3(covariance)
    values = tuple(max(0.0, value) for value in values)
    scale = max(values[0], 1.0e-12)
    linearity = (values[0] - values[1]) / scale
    planarity = (values[1] - values[2]) / scale
    sphericity = values[2] / scale
    cloud_class = "LINEAR" if linearity >= 0.45 else ("PLANAR" if planarity >= 0.25 else "ISOTROPIC")
    centroid_direction = _normalize(tuple(centroid[i] - head[i] for i in range(3)))
    principal = vectors[0]
    if centroid_direction and sum(principal[i] * centroid_direction[i] for i in range(3)) < 0.0:
        principal = tuple(-value for value in principal)
    projections = [(sum(offset[i] * principal[i] for i in range(3)), weight) for offset, weight in offsets]
    positive_weight = sum(weight for projection, weight in projections if projection > 0.0)
    positive = tuple((projection, weight) for projection, weight in projections if projection > 0.0)
    length = weighted_percentile(positive, 0.9) if positive else None
    agreement = sum(principal[i] * centroid_direction[i] for i in range(3)) if centroid_direction else 0.0
    reliability = {"LINEAR": 1.0, "PLANAR": 0.7, "ISOTROPIC": 0.35}[cloud_class]
    confidence = min(1.0, reliability * min(1.0, len(points) / 8.0) * (0.5 + 0.5 * positive_weight / total))
    return WeightCloudStats(bone_name, tuple(mesh_names), len(points), float(len(points)), total, centroid, principal, values, linearity, planarity, sphericity, positive_weight / total, math.dist(centroid, head) / max(length or 1.0, 1.0e-12), agreement, length, cloud_class, confidence, ())
