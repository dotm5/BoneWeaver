"""Rest-basis changes and UEFormat-compatible animation metadata.

The armature edit operations in BONEWEAVER change a bone's local rest frame by
moving its tail and rebuilding its roll.  UEFormat keeps animations compatible
by recording that local basis change as ``post_quat``.  This module centralises
that bookkeeping so the feature-driven planner and Quick Reorient use the
same parent-local calculation.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
import math
import re

from mathutils import Matrix, Quaternion

from ..compatibility import iter_action_fcurves


BASIS_DELTA_PROP = "boneweaver_basis_delta_quat"
BASIS_VERSION_PROP = "boneweaver_basis_version"
BASIS_VERSION = "boneweaver-rest-basis-v1"

_VECTOR_METADATA_KEYS = ("orig_loc", "orig_quat", "post_quat", "reorient_direction")
_TRACKED_METADATA_KEYS = _VECTOR_METADATA_KEYS + (
    "is_socket",
    BASIS_DELTA_PROP,
    BASIS_VERSION_PROP,
)
_EPSILON = 1.0e-7


@dataclass(frozen=True, slots=True)
class BasisChange:
    bone_name: str
    parent_name: str | None
    delta_quat: tuple[float, float, float, float]
    post_quat: tuple[float, float, float, float] | None
    changed: bool


def _normalized_rotation(matrix) -> Matrix:
    """Return a scale-free 3x3 rotation matrix from a Blender bone matrix."""

    source = matrix.to_3x3() if len(matrix) == 4 else matrix.copy()
    columns = []
    for index in range(3):
        column = source.col[index].copy()
        if column.length <= _EPSILON:
            raise ValueError("bone basis contains a zero-length axis")
        columns.append(column.normalized())
    return Matrix(tuple(tuple(columns[column][row] for column in range(3)) for row in range(3)))


def _local_matrix(name, matrices, parents):
    parent_name = parents.get(name)
    matrix = matrices[name]
    if not parent_name:
        return matrix.copy()
    parent = matrices.get(parent_name)
    if parent is None:
        raise KeyError(f"missing parent matrix for {name}: {parent_name}")
    return parent.inverted_safe() @ matrix


def local_basis_delta(name, before, after, parents) -> Quaternion:
    """Return the old-local-to-new-local rotation for one bone.

    The input matrices are armature-space rest matrices.  Computing the delta
    after removing each bone's parent is essential: an armature-space delta
    incorrectly mixes parent rotation with the child's twist.
    """

    old_local = _normalized_rotation(_local_matrix(name, before, parents))
    new_local = _normalized_rotation(_local_matrix(name, after, parents))
    delta = old_local.inverted_safe() @ new_local
    result = delta.to_quaternion()
    result.normalize()
    return result


def capture_rest_matrices(armature) -> dict[str, Matrix]:
    """Capture all armature-space rest matrices without changing Blender mode."""

    return {bone.name: bone.matrix_local.copy() for bone in armature.data.bones}


def _metadata_value(bone, key):
    value = bone.get(key)
    if value is None:
        return None
    if key == "is_socket":
        return bool(value)
    if key == BASIS_VERSION_PROP:
        return str(value)
    if key in _VECTOR_METADATA_KEYS or key == BASIS_DELTA_PROP:
        result = tuple(float(component) for component in value)
        if not all(math.isfinite(component) for component in result):
            raise ValueError(f"non-finite bone metadata: {bone.name}.{key}")
        return result
    return value


def capture_bone_metadata(armature) -> dict[str, dict[str, object]]:
    """Capture the UEFormat and BONEWEAVER basis properties for a rollback snapshot."""

    return {
        bone.name: {
            key: _metadata_value(bone, key)
            for key in _TRACKED_METADATA_KEYS
            if key in bone
        }
        for bone in armature.data.bones
    }


def restore_bone_metadata(armature, state: dict[str, dict[str, object]]) -> None:
    """Restore captured bone properties; safe to call in Object Mode."""

    for bone in armature.data.bones:
        values = state.get(bone.name, {})
        for key in _TRACKED_METADATA_KEYS:
            if key in values:
                bone[key] = values[key]
            elif key in bone:
                del bone[key]


def normalize_bone_metadata(state: dict[str, dict[str, object]]) -> dict[str, dict[str, object]]:
    """Normalize JSON-loaded lists to the tuple shape used by live snapshots."""

    normalized = {}
    for name, values in state.items():
        normalized[name] = {}
        for key, value in values.items():
            if key in _VECTOR_METADATA_KEYS or key == BASIS_DELTA_PROP:
                normalized[name][key] = tuple(float(component) for component in value)
            elif key == "is_socket":
                normalized[name][key] = bool(value)
            else:
                normalized[name][key] = value
    return normalized


def _quat_tuple(quaternion: Quaternion) -> tuple[float, float, float, float]:
    quaternion = quaternion.copy()
    quaternion.normalize()
    return tuple(float(value) for value in quaternion)


def _compose_post_quat(delta: Quaternion, previous: Quaternion) -> Quaternion:
    """Compose using Blender's same ``Quaternion.rotate`` convention as UEFormat."""

    result = delta.copy()
    result.rotate(previous)
    result.normalize()
    return result


def compute_basis_changes(
    armature,
    before: dict[str, Matrix],
    *,
    target_names: tuple[str, ...] | None = None,
) -> tuple[BasisChange, ...]:
    """Compute cumulative local-basis and UEFormat ``post_quat`` changes."""

    after = capture_rest_matrices(armature)
    parents = {
        bone.name: bone.parent.name if bone.parent else None
        for bone in armature.data.bones
    }
    names = tuple(sorted(target_names or after))
    changes = []
    for name in names:
        if name not in before or name not in after:
            continue
        delta = local_basis_delta(name, before, after, parents)
        changed = abs(delta.angle) > _EPSILON
        bone = armature.data.bones[name]
        orig_quat = bone.get("orig_quat")
        post_quat = None
        if orig_quat is not None:
            current_post = bone.get("post_quat")
            previous = (
                Quaternion(current_post)
                if current_post is not None
                else Quaternion(orig_quat).conjugated()
            )
            post_quat = _quat_tuple(_compose_post_quat(delta, previous))
        changes.append(
            BasisChange(
                name,
                parents.get(name),
                _quat_tuple(delta),
                post_quat,
                changed,
            )
        )
    return tuple(changes)


def write_basis_metadata(armature, changes: tuple[BasisChange, ...]) -> None:
    """Persist local basis deltas and cumulative UEFormat metadata."""

    for change in changes:
        if not change.changed:
            continue
        bone = armature.data.bones.get(change.bone_name)
        if bone is None:
            continue
        bone[BASIS_DELTA_PROP] = change.delta_quat
        bone[BASIS_VERSION_PROP] = BASIS_VERSION
        if change.post_quat is not None:
            bone["post_quat"] = change.post_quat


def basis_metadata_is_complete(armature, names=None) -> bool:
    """Whether the requested bones have the source data needed for UEFormat rebase."""

    selected = tuple(names or (bone.name for bone in armature.data.bones))
    return all(
        name in armature.data.bones
        and armature.data.bones[name].get("orig_loc") is not None
        and armature.data.bones[name].get("orig_quat") is not None
        for name in selected
    )


_POSE_PATH_RE = re.compile(
    r'^pose\.bones\["((?:\\["\\/bfnrt]|\\u[0-9A-Fa-f]{4}|[^"\\])*)"\]\.([A-Za-z_][A-Za-z0-9_]*)$'
)
_SUPPORTED_ANIMATION_PROPERTIES = frozenset(
    {"location", "rotation_quaternion", "rotation_euler", "rotation_axis_angle", "scale"}
)
_ROTATION_PROPERTIES = frozenset(
    {"rotation_quaternion", "rotation_euler", "rotation_axis_angle"}
)


def _parse_pose_path(data_path: str):
    match = _POSE_PATH_RE.match(str(data_path))
    if match is None:
        return None
    escaped_name, property_name = match.groups()
    return json.loads(f'"{escaped_name}"'), property_name


def _action_curves(action):
    curves = []
    for curve in iter_action_fcurves(action):
        parsed = _parse_pose_path(curve.data_path)
        if parsed is None:
            continue
        bone_name, property_name = parsed
        curves.append((curve, bone_name, property_name))
    return tuple(curves)


def action_rebase_supported(armature) -> tuple[bool, str | None]:
    """Return whether the armature animation stack is safe to sample/rewrite.

    BoneWeaver only accepts one local, unshared Active Action.  Every FCurve
    must resolve to a supported pose-bone transform channel; silently ignoring
    an object/custom-property path would make the sampled result incomplete.
    """

    animation = armature.animation_data
    action = animation.action if animation else None
    if animation and any(track.strips for track in animation.nla_tracks):
        return False, "BONEWEAVER_REBASE_NLA_UNSUPPORTED"
    if animation and any(_parse_pose_path(driver.data_path) for driver in animation.drivers):
        return False, "BONEWEAVER_REBASE_DRIVER_UNSUPPORTED"
    if any(
        not constraint.mute and constraint.influence != 0.0 and constraint.is_valid
        for pose_bone in armature.pose.bones
        for constraint in pose_bone.constraints
    ):
        return False, "BONEWEAVER_REBASE_CONSTRAINT_UNSUPPORTED"
    if action is None:
        return True, None
    all_curves = tuple(iter_action_fcurves(action))
    if not all_curves:
        return False, "BONEWEAVER_REBASE_NO_POSE_CURVES"
    valid_keyframes = False
    for curve in all_curves:
        parsed = _parse_pose_path(curve.data_path)
        if parsed is None:
            return False, "BONEWEAVER_REBASE_PATH_UNSUPPORTED"
        bone_name, property_name = parsed
        if bone_name not in armature.pose.bones:
            return False, "BONEWEAVER_REBASE_BONE_MISSING"
        if property_name not in _SUPPORTED_ANIMATION_PROPERTIES:
            return False, "BONEWEAVER_REBASE_PROPERTY_UNSUPPORTED"
        valid_keyframes = valid_keyframes or bool(curve.keyframe_points)
    if not valid_keyframes:
        return False, "BONEWEAVER_REBASE_NO_POSE_CURVES"
    if action.users > 1:
        return False, "BONEWEAVER_REBASE_SHARED_ACTION"
    return True, None


def _frame_time(scene) -> float:
    return float(scene.frame_current) + float(getattr(scene, "frame_subframe", 0.0))


def _set_frame(scene, time_value: float) -> None:
    frame = math.floor(float(time_value))
    scene.frame_set(frame, subframe=float(time_value) - frame)


def _depth_order(armature):
    depths = {}
    for bone in armature.data.bones:
        depth = 0
        parent = bone.parent
        seen = set()
        while parent is not None and parent.name not in seen:
            seen.add(parent.name)
            depth += 1
            parent = parent.parent
        depths[bone.name] = depth
    return tuple(sorted((bone.name for bone in armature.data.bones), key=lambda name: (depths[name], name)))


def capture_action_curve_state(action) -> tuple[dict[str, object], ...]:
    """Capture evaluated FCurve data for an in-memory/persistent rollback."""

    state = []
    for curve in iter_action_fcurves(action):
        points = []
        for point in curve.keyframe_points:
            points.append(
                {
                    "co": tuple(float(value) for value in point.co),
                    "handle_left": tuple(float(value) for value in point.handle_left),
                    "handle_right": tuple(float(value) for value in point.handle_right),
                    "interpolation": str(point.interpolation),
                    "handle_left_type": str(point.handle_left_type),
                    "handle_right_type": str(point.handle_right_type),
                    "easing": str(getattr(point, "easing", "AUTO")),
                    "back": float(getattr(point, "back", 0.0)),
                    "amplitude": float(getattr(point, "amplitude", 0.0)),
                    "period": float(getattr(point, "period", 0.0)),
                    "type": str(getattr(point, "type", "KEYFRAME")),
                }
            )
        state.append(
            {
                "data_path": str(curve.data_path),
                "array_index": int(curve.array_index),
                "extrapolation": str(curve.extrapolation),
                "mute": bool(curve.mute),
                "lock": bool(curve.lock),
                "color_mode": str(curve.color_mode),
                "color": tuple(float(value) for value in curve.color),
                "group": curve.group.name if curve.group is not None else None,
                "points": points,
            }
        )
    return tuple(state)


def normalize_action_curve_state(state):
    normalized = []
    for item in state:
        normalized.append(
            {
                "data_path": str(item["data_path"]),
                "array_index": int(item["array_index"]),
                "extrapolation": str(item.get("extrapolation", "CONSTANT")),
                "mute": bool(item.get("mute", False)),
                "lock": bool(item.get("lock", False)),
                "color_mode": str(item.get("color_mode", "AUTO_RAINBOW")),
                "color": tuple(float(value) for value in item.get("color", (0.0, 0.0, 0.0))),
                "group": str(item["group"]) if item.get("group") is not None else None,
                "points": [
                    {
                        "co": tuple(float(value) for value in point["co"]),
                        "handle_left": tuple(float(value) for value in point["handle_left"]),
                        "handle_right": tuple(float(value) for value in point["handle_right"]),
                        "interpolation": str(point["interpolation"]),
                        "handle_left_type": str(point["handle_left_type"]),
                        "handle_right_type": str(point["handle_right_type"]),
                        "easing": str(point.get("easing", "AUTO")),
                        "back": float(point.get("back", 0.0)),
                        "amplitude": float(point.get("amplitude", 0.0)),
                        "period": float(point.get("period", 0.0)),
                        "type": str(point.get("type", "KEYFRAME")),
                    }
                    for point in item["points"]
                ],
            }
        )
    return tuple(normalized)


def _action_curve_owner(action, curve):
    """Return the FCurve collection that owns ``curve`` on legacy or layered Actions."""

    legacy = getattr(action, "fcurves", None)
    if legacy is not None:
        return legacy
    for layer in getattr(action, "layers", ()):
        for strip in getattr(layer, "strips", ()):
            for channelbag in getattr(strip, "channelbags", ()):
                fcurves = getattr(channelbag, "fcurves", None)
                if fcurves is None:
                    continue
                for candidate in fcurves:
                    if candidate == curve:
                        return fcurves
    return None


def restore_action_curve_state(action, state) -> bool:
    state = normalize_action_curve_state(state)
    curves = {
        (str(curve.data_path), int(curve.array_index)): curve
        for curve in iter_action_fcurves(action)
    }
    expected_keys = {
        (str(item["data_path"]), int(item["array_index"]))
        for item in state
    }
    for key, curve in tuple(curves.items()):
        if key not in expected_keys:
            _action_curve_owner(action, curve).remove(curve)
    for item in state:
        curve = curves[(str(item["data_path"]), int(item["array_index"]))]
        while curve.keyframe_points:
            curve.keyframe_points.remove(curve.keyframe_points[-1], fast=True)
        for saved in item["points"]:
            point = curve.keyframe_points.insert(
                saved["co"][0], saved["co"][1], options={"FAST"}
            )
            point.interpolation = saved["interpolation"]
            point.handle_left_type = saved["handle_left_type"]
            point.handle_right_type = saved["handle_right_type"]
            point.easing = saved["easing"]
            point.back = saved["back"]
            point.amplitude = saved["amplitude"]
            point.period = saved["period"]
            point.type = saved["type"]
            point.handle_left = saved["handle_left"]
            point.handle_right = saved["handle_right"]
        curve.extrapolation = item["extrapolation"]
        curve.mute = item["mute"]
        curve.lock = item["lock"]
        curve.color_mode = item["color_mode"]
        curve.color = item["color"]
        current_group = curve.group.name if curve.group is not None else None
        if current_group != item["group"]:
            return False
    for curve in iter_action_fcurves(action):
        curve.update()
    return True


def capture_pose_settings(armature) -> dict[str, dict[str, object]]:
    """Capture pose properties that Action rebasing is allowed to change."""

    return {
        pose_bone.name: {"rotation_mode": str(pose_bone.rotation_mode)}
        for pose_bone in armature.pose.bones
    }


def normalize_pose_settings(state) -> dict[str, dict[str, object]]:
    return {
        str(name): {"rotation_mode": str(values["rotation_mode"])}
        for name, values in state.items()
    }


def restore_pose_settings(armature, state) -> bool:
    for name, values in normalize_pose_settings(state).items():
        armature.pose.bones[name].rotation_mode = values["rotation_mode"]
    return True


def capture_animation_state(armature):
    """Capture the one supported Active Action plus pose settings."""

    animation = armature.animation_data
    action = animation.action if animation else None
    if action is None:
        return None
    return {
        "action_name": str(action.name),
        "action_slot_identifier": str(
            getattr(getattr(animation, "action_slot", None), "identifier", "")
        ),
        "curves": capture_action_curve_state(action),
        "pose_settings": capture_pose_settings(armature),
    }


def normalize_animation_state(state):
    if state is None:
        return None
    return {
        "action_name": str(state["action_name"]),
        "action_slot_identifier": str(state.get("action_slot_identifier", "")),
        "curves": normalize_action_curve_state(state["curves"]),
        "pose_settings": normalize_pose_settings(state["pose_settings"]),
    }


def animation_state_matches(armature, state) -> bool:
    expected = normalize_animation_state(state)
    current = capture_animation_state(armature)
    if current is None or expected is None:
        return current is None and expected is None
    return normalize_animation_state(current) == expected


def restore_animation_state(armature, state) -> bool:
    expected = normalize_animation_state(state)
    if expected is None:
        return capture_animation_state(armature) is None
    animation = armature.animation_data
    action = animation.action if animation else None
    if action is None or action.name != expected["action_name"]:
        return False
    slot_identifier = str(
        getattr(getattr(animation, "action_slot", None), "identifier", "")
    )
    if slot_identifier != expected["action_slot_identifier"]:
        return False
    if not restore_action_curve_state(action, expected["curves"]):
        return False
    return restore_pose_settings(armature, expected["pose_settings"])


def _action_channelbag(action, animation):
    slot = getattr(animation, "action_slot", None)
    slot_handle = getattr(slot, "handle", None)
    for layer in getattr(action, "layers", ()):
        for strip in getattr(layer, "strips", ()):
            for channelbag in getattr(strip, "channelbags", ()):
                if slot_handle is None or getattr(channelbag, "slot_handle", None) == slot_handle:
                    return channelbag
    return None


def _new_action_curve(action, animation, data_path, array_index):
    legacy = getattr(action, "fcurves", None)
    if legacy is not None:
        return legacy.new(data_path=data_path, index=array_index)
    channelbag = _action_channelbag(action, animation)
    if channelbag is None:
        raise RuntimeError("BONEWEAVER_REBASE_ACTION_CHANNELBAG_MISSING")
    return channelbag.fcurves.new(data_path=data_path, index=array_index)


def _affected_descendants(armature, names):
    affected = set(names)
    changed = tuple(names)
    for root_name in changed:
        bone = armature.data.bones.get(root_name)
        if bone is not None:
            affected.update(child.name for child in bone.children_recursive)
    return tuple(sorted(affected))


def capture_action_pose_samples(context, armature):
    """Sample the active Action's final armature-space pose at all curve times."""

    animation = armature.animation_data
    action = animation.action if animation else None
    if action is None:
        return None
    supported, reason = action_rebase_supported(armature)
    if not supported:
        raise RuntimeError(reason)
    curves = _action_curves(action)
    if not curves:
        return None
    sample_times = set()
    for curve, _bone_name, _property_name in curves:
        for point in curve.keyframe_points:
            sample_times.add(round(float(point.co[0]), 6))
            sample_times.add(round(float(point.handle_left[0]), 6))
            sample_times.add(round(float(point.handle_right[0]), 6))
    original_time = _frame_time(context.scene)
    samples = {}
    try:
        for time_value in sorted(sample_times):
            _set_frame(context.scene, time_value)
            context.view_layer.update()
            samples[time_value] = {
                pose_bone.name: pose_bone.matrix.copy()
                for pose_bone in armature.pose.bones
            }
    finally:
        _set_frame(context.scene, original_time)
        context.view_layer.update()
    return {
        "action_name": action.name,
        "action_slot_identifier": str(
            getattr(getattr(animation, "action_slot", None), "identifier", "")
        ),
        "sample_times": tuple(sorted(sample_times)),
        "pose_samples": samples,
        "curve_state": capture_action_curve_state(action),
        "pose_settings": capture_pose_settings(armature),
        "frame": original_time,
    }


def _property_values(pose_bone, property_name):
    if property_name == "location":
        return tuple(float(value) for value in pose_bone.location)
    if property_name == "rotation_quaternion":
        return tuple(float(value) for value in pose_bone.rotation_quaternion)
    if property_name == "rotation_euler":
        return tuple(float(value) for value in pose_bone.rotation_euler)
    if property_name == "rotation_axis_angle":
        return tuple(float(value) for value in pose_bone.rotation_axis_angle)
    if property_name == "scale":
        return tuple(float(value) for value in pose_bone.scale)
    raise ValueError(f"unsupported animation property: {property_name}")


def _matrix_basis_from_target(pose_bone, target):
    bone = pose_bone.bone
    if pose_bone.parent is None:
        return bone.convert_local_to_pose(
            target,
            bone.matrix_local,
            invert=True,
        )
    return bone.convert_local_to_pose(
        target,
        bone.matrix_local,
        parent_matrix=pose_bone.parent.matrix,
        parent_matrix_local=bone.parent.matrix_local,
        invert=True,
    )


def _pose_values_for_time(context, armature, target_matrices, curves):
    for pose_bone in armature.pose.bones:
        pose_bone.matrix_basis.identity()
    context.view_layer.update()
    for name in _depth_order(armature):
        target = target_matrices.get(name)
        if target is not None:
            pose_bone = armature.pose.bones[name]
            pose_bone.matrix_basis = _matrix_basis_from_target(pose_bone, target)
            context.view_layer.update()
    context.view_layer.update()
    return {
        (bone_name, property_name): _property_values(armature.pose.bones[bone_name], property_name)
        for _curve, bone_name, property_name in curves
    }


def _flip(values):
    return tuple(-float(value) for value in values)


def _align_quaternion_samples(sampled, sample_times, curves):
    quaternion_bones = {
        bone_name
        for _curve, bone_name, property_name in curves
        if property_name == "rotation_quaternion"
    }
    for bone_name in quaternion_bones:
        previous = None
        for time_value in sample_times:
            key = (bone_name, "rotation_quaternion")
            values = sampled[time_value].get(key)
            if values is None:
                continue
            if previous is not None and sum(a * b for a, b in zip(previous, values)) < 0.0:
                values = _flip(values)
                sampled[time_value][key] = values
            previous = values


def maximum_pose_sample_error(context, armature, session) -> float:
    """Return the largest armature-space matrix error over captured samples."""

    if not session:
        return 0.0
    original_time = _frame_time(context.scene)
    maximum = 0.0
    try:
        for time_value in session["sample_times"]:
            _set_frame(context.scene, time_value)
            context.view_layer.update()
            for name, expected in session["pose_samples"][time_value].items():
                actual = armature.pose.bones[name].matrix
                maximum = max(
                    maximum,
                    max(
                        abs(float(actual[row][column] - expected[row][column]))
                        for row in range(4)
                        for column in range(4)
                    ),
                )
    finally:
        _set_frame(context.scene, original_time)
        context.view_layer.update()
    return maximum


def rebase_action_from_samples(
    context,
    armature,
    session,
    *,
    affected_names: tuple[str, ...] = (),
) -> tuple[dict[str, object], ...] | None:
    """Rewrite existing Action curves so the evaluated pose survives a rest edit."""

    if not session:
        return None
    animation = armature.animation_data
    action = animation.action if animation else None
    if action is None or action.name != session["action_name"]:
        raise RuntimeError("BONEWEAVER_REBASE_ACTION_CHANGED")
    slot_identifier = str(
        getattr(getattr(animation, "action_slot", None), "identifier", "")
    )
    if slot_identifier != session.get("action_slot_identifier", ""):
        raise RuntimeError("BONEWEAVER_REBASE_ACTION_SLOT_CHANGED")
    original_curves = _action_curves(action)
    requested_names = _affected_descendants(armature, affected_names)
    if not requested_names:
        requested_names = tuple(sorted({bone_name for _curve, bone_name, _property_name in original_curves}))
    for bone_name in requested_names:
        pose_bone = armature.pose.bones.get(bone_name)
        if pose_bone is None:
            continue
        existing_properties = {
            property_name
            for _curve, name, property_name in original_curves
            if name == bone_name
        }
        rotation_properties = existing_properties & _ROTATION_PROPERTIES
        if rotation_properties:
            rotation_property = sorted(rotation_properties)[0]
        else:
            rotation_property = "rotation_quaternion"
            pose_bone.rotation_mode = "QUATERNION"
        properties = {"location", rotation_property, "scale"}
        for property_name in properties:
            if property_name not in _SUPPORTED_ANIMATION_PROPERTIES:
                raise RuntimeError("BONEWEAVER_REBASE_PROPERTY_UNSUPPORTED")
            data_path = pose_bone.path_from_id(property_name)
            values = _property_values(pose_bone, property_name)
            for array_index in range(len(values)):
                if not any(
                    curve.array_index == array_index
                    for curve, name, prop in original_curves
                    if name == bone_name and prop == property_name
                ):
                    _new_action_curve(
                        action,
                        animation,
                        data_path,
                        array_index,
                    )
    requested = frozenset(requested_names)
    curves = tuple(
        item for item in _action_curves(action) if item[1] in requested
    )
    sampled = {}
    animation.action = None
    original_time = _frame_time(context.scene)
    try:
        for time_value in session["sample_times"]:
            _set_frame(context.scene, time_value)
            sampled[time_value] = _pose_values_for_time(
                context,
                armature,
                session["pose_samples"][time_value],
                curves,
            )
        _align_quaternion_samples(sampled, session["sample_times"], curves)
        for curve, bone_name, property_name in curves:
            if not curve.keyframe_points:
                values = _property_values(armature.pose.bones[bone_name], property_name)
                for time_value in session["sample_times"]:
                    point = curve.keyframe_points.insert(
                        time_value,
                        sampled[time_value][(bone_name, property_name)][curve.array_index],
                        options={"FAST"},
                    )
                    point.interpolation = "LINEAR"
                curve.update()
                continue
            for point in curve.keyframe_points:
                value = sampled[round(float(point.co[0]), 6)][(bone_name, property_name)]
                point.co[1] = value[curve.array_index]
                left_time = round(float(point.handle_left[0]), 6)
                right_time = round(float(point.handle_right[0]), 6)
                point.handle_left[1] = sampled[left_time][(bone_name, property_name)][curve.array_index]
                point.handle_right[1] = sampled[right_time][(bone_name, property_name)][curve.array_index]
        for curve in iter_action_fcurves(action):
            curve.update()
    finally:
        animation.action = action
        _set_frame(context.scene, original_time)
        context.view_layer.update()
    maximum_error = maximum_pose_sample_error(context, armature, session)
    if maximum_error > 1.0e-5:
        raise RuntimeError(
            f"BONEWEAVER_REBASE_POSE_MISMATCH:{maximum_error:.17g}"
        )
    return session["curve_state"]
