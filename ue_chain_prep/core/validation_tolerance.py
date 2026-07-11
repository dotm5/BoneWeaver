"""Per-mesh neutral-geometry tolerance calculation.

The default decision is made in evaluated mesh object-local coordinates. World
coordinates are carried only so diagnostics can explain transform-amplified
deltas without changing the safety decision.
"""

from __future__ import annotations

import math
import struct
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class AutoToleranceDefaults:
    auto_relative_factor: float = 2.5e-7
    baseline_noise_multiplier: float = 4.0
    float32_ulp_multiplier: int = 8
    hard_limit_multiplier: float = 4.0
    absolute_floor: float = 1.0e-7
    minimum_scale_floor: float = 1.0e-6
    strict_relative_factor: float = 1.0e-7
    soft_rms_ratio: float = 0.25
    outlier_ratio_allowance: float = 1.0e-6
    minimum_outlier_allowance: int = 4


AUTO_TOLERANCE_DEFAULTS = AutoToleranceDefaults()


@dataclass(frozen=True, slots=True)
class MeshCoordinateCapture:
    mesh_name: str
    local_coordinates: object
    world_coordinates: object = ()


@dataclass(frozen=True, slots=True)
class MeshValidationResult:
    mesh_name: str
    coordinate_space: str
    mesh_scale: float
    tolerance_mode: str
    soft_limit: float
    hard_limit: float
    baseline_max_delta: float
    baseline_rms_delta: float
    float32_ulp_budget: float
    max_delta: float
    mean_delta: float
    rms_delta: float
    soft_outlier_count: int
    soft_outlier_ratio: float
    hard_outlier_count: int
    result: str
    recommended_relative_factor: float
    recommended_absolute_limit: float
    world_max_delta: float
    vertex_count: int


def float32_ulp(value: float) -> float:
    """Return spacing from the float32 representation toward positive infinity."""
    number = float(value)
    if not math.isfinite(number):
        return math.inf
    packed = struct.pack("<f", number)
    rounded = struct.unpack("<f", packed)[0]
    bits = struct.unpack("<I", packed)[0]
    if rounded == 0.0:
        return struct.unpack("<f", struct.pack("<I", 1))[0]
    adjacent_bits = bits + 1 if rounded > 0.0 else bits - 1
    adjacent = struct.unpack("<f", struct.pack("<I", adjacent_bits))[0]
    return abs(float(adjacent) - float(rounded))


def _distance(first, second) -> float:
    return math.sqrt(sum((float(first[index]) - float(second[index])) ** 2 for index in range(3)))


def _is_flat_coordinates(coordinates) -> bool:
    return bool(coordinates) and isinstance(coordinates[0], (int, float))


def _iter_points(coordinates):
    if _is_flat_coordinates(coordinates):
        if len(coordinates) % 3:
            raise ValueError("flat coordinate buffer length must be divisible by three")
        for index in range(0, len(coordinates), 3):
            yield (coordinates[index], coordinates[index + 1], coordinates[index + 2])
    else:
        yield from coordinates


def _point_count(coordinates) -> int:
    return len(coordinates) // 3 if _is_flat_coordinates(coordinates) else len(coordinates)


def _bbox_diagonal(coordinates, minimum_scale_floor: float) -> float:
    if not coordinates:
        return float(minimum_scale_floor)
    minima = [math.inf, math.inf, math.inf]
    maxima = [-math.inf, -math.inf, -math.inf]
    for point in _iter_points(coordinates):
        for index in range(3):
            value = float(point[index])
            minima[index] = min(minima[index], value)
            maxima[index] = max(maxima[index], value)
    return max(_distance(minima, maxima), float(minimum_scale_floor))


def coordinate_delta_metrics(before, after, *, soft_limit=math.inf, hard_limit=math.inf):
    if _point_count(before) != _point_count(after):
        return math.inf, math.inf, math.inf, 0, 0
    maximum = total = squared = 0.0
    soft_count = hard_count = count = 0
    for first, second in zip(_iter_points(before), _iter_points(after)):
        delta = _distance(first, second)
        maximum = max(maximum, delta)
        total += delta
        squared += delta * delta
        soft_count += delta > soft_limit
        hard_count += delta > hard_limit
        count += 1
    if not count:
        return 0.0, 0.0, 0.0, 0, 0
    return maximum, total / count, math.sqrt(squared / count), soft_count, hard_count


def evaluate_mesh_tolerance(
    before: MeshCoordinateCapture,
    after: MeshCoordinateCapture,
    *,
    mode: str,
    custom_relative_factor: float = 1.0e-7,
    baseline_max_delta: float = 0.0,
    baseline_rms_delta: float = 0.0,
    defaults: AutoToleranceDefaults = AUTO_TOLERANCE_DEFAULTS,
) -> MeshValidationResult:
    """Compare one mesh and return a complete, deterministic tolerance report."""
    mode_value = getattr(mode, "value", mode)
    mesh_scale = _bbox_diagonal(before.local_coordinates, defaults.minimum_scale_floor)
    magnitude = max((abs(float(value)) for point in _iter_points(before.local_coordinates) for value in point), default=0.0)
    ulp_budget = float32_ulp(magnitude) * defaults.float32_ulp_multiplier
    if mode_value == "STRICT_TEST":
        soft_limit = max(defaults.absolute_floor, mesh_scale * defaults.strict_relative_factor)
    elif mode_value == "CUSTOM":
        soft_limit = max(defaults.absolute_floor, mesh_scale * float(custom_relative_factor))
    elif mode_value == "AUTO_PRODUCTION":
        soft_limit = max(
            defaults.absolute_floor,
            mesh_scale * defaults.auto_relative_factor,
            float(baseline_max_delta) * defaults.baseline_noise_multiplier,
            ulp_budget,
        )
    else:
        raise ValueError(f"unsupported validation tolerance mode: {mode_value}")
    hard_limit = soft_limit * defaults.hard_limit_multiplier
    maximum, mean, rms, soft_count, hard_count = coordinate_delta_metrics(
        before.local_coordinates, after.local_coordinates, soft_limit=soft_limit, hard_limit=hard_limit,
    )
    world_maximum, _, _, _, _ = coordinate_delta_metrics(before.world_coordinates, after.world_coordinates)
    vertex_count = _point_count(before.local_coordinates)
    soft_ratio = soft_count / vertex_count if vertex_count else 0.0
    allowed_outliers = max(
        defaults.minimum_outlier_allowance,
        math.ceil(vertex_count * defaults.outlier_ratio_allowance),
    )
    if maximum <= soft_limit:
        result = "PASS"
    elif (
        maximum <= hard_limit
        and rms <= soft_limit * defaults.soft_rms_ratio
        and soft_count <= allowed_outliers
    ):
        result = "PASS_WITH_NUMERIC_NOISE_WARNING"
    else:
        result = "FAIL_AND_ROLLBACK"
    recommended_limit = maximum * 1.25
    return MeshValidationResult(
        mesh_name=before.mesh_name,
        coordinate_space="EVALUATED_MESH_OBJECT_LOCAL",
        mesh_scale=mesh_scale,
        tolerance_mode=str(mode_value),
        soft_limit=soft_limit,
        hard_limit=hard_limit,
        baseline_max_delta=float(baseline_max_delta),
        baseline_rms_delta=float(baseline_rms_delta),
        float32_ulp_budget=ulp_budget,
        max_delta=maximum,
        mean_delta=mean,
        rms_delta=rms,
        soft_outlier_count=soft_count,
        soft_outlier_ratio=soft_ratio,
        hard_outlier_count=hard_count,
        result=result,
        recommended_relative_factor=recommended_limit / mesh_scale,
        recommended_absolute_limit=recommended_limit,
        world_max_delta=world_maximum,
        vertex_count=vertex_count,
    )
