"""Automatic interior-joint orientation and evidence-based terminal cleanup.

This is deliberately separate from the legacy UEFormat-parity modes. The
original Armature datablock is retained as a persistent, exact topology backup.
No mesh, vertex group or weight is removed or rewritten.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
import datetime as dt
import json
import re

import bpy
from mathutils import Matrix, Vector

from ..compatibility import iter_action_fcurves
from .animation_basis import (
    action_rebase_supported, capture_animation_state, restore_animation_state,
)
from .bone_roles import bone_role, direction_helper_name, secondary_chain_name
from .armature_reader import resolve_active_armature
from .canonical import sha256
from .context_guard import ContextStateGuard
from .validation_tolerance import evaluate_mesh_tolerance
from .quick_reorient import build_quick_reorient_plan, dominant_axis
from .quick_source_adapter import capture_quick_source, is_socket_bone
from .quick_transaction import (
    apply_quick_plan, _mesh_digests, _neutral_baseline, _capture_neutral, _capture_delta,
)

VERSION = "boneweaver-auto-cleanup-v2"
PREFIX = "BONEWEAVER_AUTO_SNAPSHOT::"
_EPS = 1e-7


def _numbered_continuation(parent, leaf):
    first, last = re.match(r"^(.*?)(\d+)$", parent), re.match(r"^(.*?)(\d+)$", leaf)
    return bool(first and last and first[1].casefold() == last[1].casefold()
                and int(last[2]) == int(first[2]) + 1)


@dataclass(frozen=True)
class CleanupPlan:
    quick_plan: object
    delete_names: tuple[str, ...]
    decisions: tuple[tuple[str, str], ...]
    evidence_fingerprint: str
    mode: str = "AUTO"


def _plain(value):
    if hasattr(value, "items"):
        return {str(k): _plain(v) for k, v in value.items()}
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if isinstance(value, bpy.types.ID):
        return (value.bl_rna.identifier, value.name_full)
    try:
        return [_plain(v) for v in value]
    except TypeError:
        return str(value)


def _data_signature(data):
    """Include custom properties/collections in restore conflict detection."""
    return sha256((
        [(b.name, b.parent.name if b.parent else None,
          tuple(b.head_local), tuple(b.tail_local),
          tuple(v for row in b.matrix_local for v in row), b.use_connect,
          b.use_deform, sorted(c.name for c in b.collections), _plain(b), _rna_settings(b),
          _rna_settings(b.color), _rna_settings(b.color.custom),
          tuple(getattr(getattr(b, key, None), "name", None) for key in
                ("bbone_custom_handle_start", "bbone_custom_handle_end")))
         for b in sorted(data.bones, key=lambda x: x.name)],
        _plain(data), _rna_settings(data, exclude={"name", "name_full", "use_fake_user"}),
        [(c.name, c.parent.name if c.parent else None, _rna_settings(c), _plain(c)) for c in data.collections_all],
    ))


def _rna_settings(owner, exclude=()):
    result = {}
    for prop in owner.bl_rna.properties:
        key = prop.identifier
        if prop.is_readonly or key in exclude or key.startswith("select") or key in {"rna_type"}:
            continue
        if prop.type in {"BOOLEAN", "INT", "FLOAT", "STRING", "ENUM"}:
            value = getattr(owner, key)
            result[key] = sorted(value) if isinstance(value, set) else _plain(value)
    return result


def _pose_state(armature):
    state = {}
    for b in armature.pose.bones:
        values = _rna_settings(b, exclude={"name", "matrix", "matrix_basis", "matrix_channel", "head", "tail"})
        values["_custom_shape"] = b.custom_shape.name if b.custom_shape else None
        values["_custom_shape_transform"] = b.custom_shape_transform.name if b.custom_shape_transform else None
        state[b.name] = values
    return state


def _restore_pose(armature, state):
    for name, values in state.items():
        bone = armature.pose.bones.get(name)
        if bone:
            bone.rotation_mode = values["rotation_mode"]
            for key, value in values.items():
                if not key.startswith("_"):
                    setattr(bone, key, value)
            bone.custom_shape = bpy.data.objects.get(values.get("_custom_shape") or "")
            bone.custom_shape_transform = armature.pose.bones.get(values.get("_custom_shape_transform") or "")


def _references(armature):
    """Conservative live-file references, including inactive Actions and LODs."""
    names = set(armature.data.bones.keys())
    refs = set()
    # Bone paths in every Action protect even an unassigned reusable clip.
    paths = {name: 'pose.bones["' + bpy.utils.escape_identifier(name) + '"]' for name in names}
    for action in bpy.data.actions:
        for curve in iter_action_fcurves(action):
            refs.update(name for name, path in paths.items() if path in curve.data_path)
    ids = list(bpy.data.objects) + list(bpy.data.armatures) + list(bpy.data.meshes) + list(bpy.data.shape_keys)
    for owner in ids:
        animation = getattr(owner, "animation_data", None)
        for curve in getattr(animation, "drivers", ()):
            if owner in (armature, armature.data):
                refs.update(name for name, path in paths.items() if path in curve.data_path)
            for variable in curve.driver.variables:
                for target in variable.targets:
                    if target.id in (armature, armature.data):
                        if getattr(target, "bone_target", ""):
                            refs.add(target.bone_target)
                        refs.update(name for name, path in paths.items() if path in target.data_path)
    for obj in bpy.data.objects:
        for modifier in obj.modifiers:
            if getattr(modifier, "object", None) == armature and getattr(modifier, "subtarget", ""):
                refs.add(modifier.subtarget)
        if obj.parent == armature and obj.parent_type == "BONE":
            refs.add(obj.parent_bone)
        owners = [obj] + (list(obj.pose.bones) if obj.type == "ARMATURE" else [])
        for owner in owners:
            for constraint in owner.constraints:
                if obj == armature and isinstance(owner, bpy.types.PoseBone):
                    refs.add(owner.name)
                for target_key, bone_key in (("target", "subtarget"), ("pole_target", "pole_subtarget")):
                    if getattr(constraint, target_key, None) == armature:
                        refs.add(getattr(constraint, bone_key, ""))
                for target in getattr(constraint, "targets", ()):
                    if getattr(target, "target", None) == armature:
                        refs.add(getattr(target, "subtarget", ""))
        if obj == armature:
            for bone in obj.pose.bones:
                if len(bone.keys()):
                    refs.add(bone.name)
                if bone.custom_shape_transform and bone.custom_shape_transform != bone:
                    refs.add(bone.custom_shape_transform.name)
                for key in ("bbone_custom_handle_start", "bbone_custom_handle_end"):
                    for owner in (bone, bone.bone):
                        handle = getattr(owner, key, None)
                        if handle:
                            refs.add(handle.name)
    return refs


def _weight_evidence(armature):
    weighted, meshes = set(), []
    for obj in bpy.data.objects:
        if obj.type != "MESH":
            continue
        # Also protect detached/disabled parented LODs, not only visible meshes.
        modifiers = [m for m in obj.modifiers if m.type == "ARMATURE" and m.object == armature]
        if not modifiers and obj.parent != armature:
            continue
        meshes.append(obj)
        groups = {g.index: g.name for g in obj.vertex_groups}
        for vertex in obj.data.vertices:
            for membership in vertex.groups:
                if membership.weight > 0.0:  # No lossy tiny-weight threshold.
                    weighted.add(groups.get(membership.group, ""))
        if any(m.use_bone_envelopes for m in modifiers):
            weighted.update(b.name for b in armature.data.bones if b.use_deform)
    return weighted, meshes


def _evidence_fingerprint(armature):
    weighted, meshes = _weight_evidence(armature)
    from .fingerprint import modifier_digest
    from .mesh_scan_cache import mesh_digest_pair
    return sha256((_data_signature(armature.data), sorted(weighted),
                   sorted((o.name, *mesh_digest_pair(o), modifier_digest(o)) for o in meshes),
                   sorted(_references(armature)), capture_animation_state(armature),
                   _pose_state(armature), tuple(v for row in armature.matrix_world for v in row)))


def build_cleanup_plan(context, mode="AUTO"):
    if mode not in {"AUTO", "REORIENT", "CONNECT", "CLEANUP"}:
        raise ValueError("未知整理模式：" + str(mode))
    armature = resolve_active_armature(context)
    if armature is None:
        raise ValueError("未找到骨架")
    if armature.library or armature.data.library:
        raise ValueError("请先将链接骨架本地化")
    if armature.animation_data and armature.animation_data.action:
        raise ValueError("自动整理用于蒙皮/动画前：请先在副本中解除活动 Action，再整理骨架")
    paths = ['pose.bones["' + bpy.utils.escape_identifier(b.name) + '"]' for b in armature.data.bones]
    if any(any(path in c.data_path for path in paths) for a in bpy.data.actions for c in iter_action_fcurves(a)):
        raise ValueError("文件中存在引用此骨架名称的动画，请使用不含旧动画的模型副本整理")
    # Always retain animation/Basis safeguards in the new automatic path.
    supported, reason = action_rebase_supported(armature)
    if not supported:
        raise ValueError("动画需先处理：" + str(reason))
    states, metadata = capture_quick_source(context, armature)
    by_name = {s.bone_name: s for s in states}
    weighted, meshes = _weight_evidence(armature)
    referenced = _references(armature)
    roles = {n: bone_role(n, is_socket=is_socket_bone(n, metadata[n])) for n in by_name}
    hard = {n for n, role in roles.items() if role in
            {"ROOT", "IK", "SOCKET", "WEAPON_ATTACHMENT", "CONTROL", "VIRTUAL"}}
    # A control/attachment subtree retains its coordinate frame, even where
    # children have generic names. Structural ancestors remain, but may orient.
    for state in states:
        parent = by_name.get(state.parent_name)
        while parent:
            if parent.bone_name in hard and roles[parent.bone_name] != "ROOT":
                hard.add(state.bone_name)
                break
            parent = by_name.get(parent.parent_name)
    retained = set(weighted) | referenced | hard
    for name in tuple(retained):
        state = by_name.get(name)
        while state and state.parent_name:
            retained.add(state.parent_name)
            state = by_name.get(state.parent_name)
    candidates, decisions = set(), []
    def depth(name):
        value, state = 0, by_name[name]
        while state.parent_name:
            value += 1
            state = by_name[state.parent_name]
        return value
    for state in sorted(states, key=lambda s: (-depth(s.bone_name), s.bone_name)):
        name, parent = state.bone_name, by_name.get(state.parent_name)
        imported = metadata[name].orig_loc is not None and metadata[name].orig_quat is not None
        explicit = bool(armature.data.bones[name].get("boneweaver_direction_helper", False))
        helper = (explicit or direction_helper_name(name) or secondary_chain_name(name)
                  or (parent and _numbered_continuation(parent.bone_name, name)))
        # Imported unknown leaves retain the earlier UE landmark inference only
        # on a sole-child, weighted segment; anatomical names need stronger evidence.
        imported_tip = (imported and roles[name] == "UNKNOWN" and parent
                        and parent.bone_name in weighted and len(parent.child_names) == 1
                        and not state.child_names)
        anchor = parent
        while anchor and anchor.bone_name not in weighted:
            anchor = by_name.get(anchor.parent_name)
        if parent is None:
            reason = "KEEP_ROOT"
        elif name in weighted:
            reason = "KEEP_WEIGHTED"
        elif name in referenced:
            reason = "KEEP_REFERENCED"
        elif name in hard:
            reason = "KEEP_" + roles[name]
        elif name in retained:
            reason = "KEEP_REQUIRED_ANCESTOR"
        elif not meshes or not anchor:
            reason = "KEEP_NO_WEIGHTED_ANCHOR"
        elif any(n not in candidates for n in state.child_names):
            reason = "KEEP_SURVIVING_CHILD"
        elif helper or imported_tip:
            reason = "DELETE_ZERO_HELPER_SUBTREE"
            candidates.add(name)
        else:
            reason = "KEEP_UNCERTAIN_ZERO"
        decisions.append((name, reason))
    delete_names = sorted(candidates, key=lambda n: (-depth(n), n)) if mode in {"AUTO", "CLEANUP"} else []

    settings = context.scene.boneweaver_settings
    old_rebase = settings.animation_basis_rebase
    try:
        settings.animation_basis_rebase = True
        quick = build_quick_reorient_plan(context, connect_linear_chains=False)
    finally:
        settings.animation_basis_rebase = old_rebase
    proposals = []
    for proposal in quick.proposals:
        state = by_name[proposal.bone_name]
        children = [by_name[n] for n in state.child_names
                    if n not in hard]
        # Prefer surviving continuation over zero corrective side branches.
        surviving = [c for c in children if c.bone_name not in candidates]
        if surviving:
            children = surviving
        keep = (mode not in {"AUTO", "REORIENT"} or state.parent_name is None
                or not state.child_names or state.bone_name in hard or not children)
        tail = Vector(state.tail)
        source = "KEEP_ROOT_OR_TERMINAL"
        if not keep:
            offsets = [Vector(c.head) - Vector(state.head) for c in children]
            offsets = [o for o in offsets if o.length > _EPS]
            if len(offsets) == 1:
                tail = Vector(state.head) + offsets[0]
                source = "DIRECT_CHILD_HEAD"
            elif offsets:
                average = sum(offsets, Vector()) / len(offsets)
                if average.length > _EPS:
                    rotation = Matrix([state.matrix[i:i+4] for i in range(0, 16, 4)]).to_3x3()
                    # Current local frame, never mix original offsets with edited axes.
                    axis = Vector(dominant_axis(rotation.inverted_safe() @ average))
                    tail = Vector(state.head) + (rotation @ axis).normalized() * (sum(o.length for o in offsets) / len(offsets))
                    source = "UEFORMAT_BRANCH_AXIS_CURRENT_FRAME"
                else:
                    keep = True
                    source = "KEEP_CANCELLED_BRANCH"
            else:
                keep = True
                source = "KEEP_COINCIDENT_CHILDREN"
        # Existing connected children constrain their parent's tail. Do not move heads.
        connected = [by_name[n] for n in state.child_names if by_name[n].use_connect]
        if connected and any((tail - Vector(c.head)).length > _EPS for c in connected):
            keep, tail, source = True, Vector(state.tail), "KEEP_CONNECTED_CHILD_BOUNDARY"
        proposals.append(replace(proposal, skipped=keep, skip_reason=source if keep else None,
            source=source, target_tail=tuple(tail), target_length=(tail-Vector(state.head)).length,
            target_use_connect=state.use_connect, component_id=None, branch_boundary=False))
    quick = replace(quick, proposals=tuple(proposals), linked_components=(), connect_linear_chains=False,
                    already_normalized=False, animation_basis_rebase=True)
    targets = {p.bone_name: Vector(p.target_tail) for p in proposals}
    if mode in {"AUTO", "CONNECT"}:
        connected_proposals = []
        for p in proposals:
            state = by_name[p.bone_name]
            parent = by_name.get(state.parent_name)
            siblings = [n for n in parent.child_names if n not in candidates and n not in hard] if parent else []
            connect = (parent and state.bone_name not in hard and parent.bone_name not in hard
                       and state.bone_name not in delete_names and siblings == [state.bone_name]
                       and (targets[parent.bone_name] - Vector(state.head)).length <= _EPS)
            changed = bool(connect) and not state.use_connect
            connected_proposals.append(replace(p, target_use_connect=state.use_connect or bool(connect),
                skipped=p.skipped and not changed, skip_reason=None if changed else p.skip_reason))
        proposals = connected_proposals
    quick = replace(quick, proposals=tuple(proposals),
                    plan_id=sha256((VERSION, mode, quick.source_fingerprint, proposals, delete_names)))
    return CleanupPlan(quick, tuple(delete_names), tuple(sorted(decisions)),
                       _evidence_fingerprint(armature), mode)


def _activate(context, armature):
    if context.object and context.object.mode != "OBJECT":
        bpy.ops.object.mode_set(mode="OBJECT")
    bpy.ops.object.select_all(action="DESELECT")
    armature.select_set(True)
    context.view_layer.objects.active = armature


def _write(text, payload):
    text.clear()
    text.write(json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2))


def _snapshot_fingerprint(armature):
    return sha256((_data_signature(armature.data), _mesh_digests(armature),
                   capture_animation_state(armature), _pose_state(armature),
                   sorted(_references(armature)), tuple(v for row in armature.matrix_world for v in row)))


def _static_pose_rebaser(armature):
    """Keep skin deformation matrices, not old local pose channels, invariant."""
    if armature.animation_data and armature.animation_data.action:
        return None  # The existing sampled Action rebasing owns this path.
    deformation = {b.name: b.matrix.copy() @ b.bone.matrix_local.inverted_safe()
                   for b in armature.pose.bones}
    def rebase(context, rig):
        target = {b.name: deformation[b.name] @ b.bone.matrix_local for b in rig.pose.bones}
        for bone in rig.pose.bones:
            args = {}
            if bone.parent:
                args = {"parent_matrix": target[bone.parent.name],
                        "parent_matrix_local": bone.parent.bone.matrix_local}
            bone.matrix_basis = bone.bone.convert_local_to_pose(
                target[bone.name], bone.bone.matrix_local, invert=True, **args)
        context.view_layer.update()
    return rebase


def apply_cleanup_plan(context, plan, *, validator=None):
    armature = bpy.data.objects[plan.quick_plan.armature_object_name]
    if _evidence_fingerprint(armature) != plan.evidence_fingerprint:
        raise ValueError("骨架、权重或引用已变化，请重新运行")
    previous_name = latest_cleanup_snapshot(armature)
    if previous_name:
        previous = json.loads(bpy.data.texts[previous_name].as_string())
        if (previous.get("kind") == VERSION and previous.get("mode") == plan.mode
                and previous.get("post_fingerprint") == _snapshot_fingerprint(armature)):
            return previous_name, {"status": "NOOP", "reoriented": 0, "connected": 0, "deleted": 0}
    blockers = [i for i in plan.quick_plan.issues if i.severity == "BLOCKER"]
    if blockers:
        raise ValueError(blockers[0].code)
    states = {s.bone_name: s for s in plan.quick_plan.bone_states}
    if not plan.delete_names and all(
        p.skipped or ((Vector(p.target_tail) - Vector(states[p.bone_name].tail)).length <= _EPS
                      and p.target_use_connect == states[p.bone_name].use_connect)
        for p in plan.quick_plan.proposals
    ):
        return latest_cleanup_snapshot(armature), {"status": "NOOP", "reoriented": 0, "connected": 0, "deleted": 0}
    original = armature.data
    pre_fake_user = original.use_fake_user
    animation = capture_animation_state(armature)
    pose = _pose_state(armature)
    mesh_before = _mesh_digests(armature)
    neutral = _neutral_baseline(armature)
    changed_orientation = [p for p in plan.quick_plan.proposals if not p.skipped
                           and (Vector(p.target_tail)-Vector(states[p.bone_name].tail)).length > _EPS]
    changed_connections = [p for p in plan.quick_plan.proposals
                           if p.target_use_connect != states[p.bone_name].use_connect]
    static_rebase = _static_pose_rebaser(armature) if changed_orientation else None
    payload = {"kind": VERSION, "mode": plan.mode, "status": "CREATED", "created_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "object_name": armature.name, "backup_data": original.name, "backup_fake_user": pre_fake_user,
        "backup_signature": _data_signature(original), "pre_animation": animation, "pre_pose": pose,
        "delete_names": list(plan.delete_names), "decisions": list(plan.decisions),
        "plan_id": plan.quick_plan.plan_id, "mutations": []}
    text = bpy.data.texts.new(PREFIX + plan.quick_plan.plan_id[:20])
    _write(text, payload)
    working = original.copy()
    working.name = original.name + "_Prepared"
    working.use_fake_user = False
    original.use_fake_user = True
    quick_text = None
    with ContextStateGuard(context):
        try:
            _activate(context, armature)
            armature.data = working
            _restore_pose(armature, pose)
            if static_rebase is not None:
                # Measure float32 matrix round-trip noise with UNCHANGED rest
                # axes. This calibrates the same numerical operations, never
                # the proposed reorientation or its deformation error.
                static_rebase(context, armature)
                calibration = _capture_neutral(armature)
                for mesh_name, (capture, noise_max, noise_rms) in tuple(neutral.items()):
                    round_max, round_rms = _capture_delta(capture, calibration[mesh_name])
                    neutral[mesh_name] = (capture, max(noise_max, round_max), max(noise_rms, round_rms))
                _restore_pose(armature, pose)
                context.view_layer.update()
            quick = replace(plan.quick_plan, armature_data_name=working.name)
            result = apply_quick_plan(context, quick, strict_validation=True,
                                      after_reorient=static_rebase, neutral_baseline=neutral)
            quick_text = bpy.data.texts.get(result.snapshot_text_name)
            if not result.success:
                raise RuntimeError(result.error or "重定向验证失败")
            # The leaf head is consumed by parent orientation BEFORE deletion.
            bpy.ops.object.mode_set(mode="EDIT")
            for name in plan.delete_names:
                bone = working.edit_bones[name]
                if bone.children or bone.parent is None:
                    raise RuntimeError("辅助子树存在未计划删除的子骨或根骨")
                working.edit_bones.remove(bone)
            bpy.ops.object.mode_set(mode="OBJECT")
            context.view_layer.update()
            if set(working.bones.keys()) != set(original.bones.keys()) - set(plan.delete_names):
                raise RuntimeError("骨骼集合验证失败")
            if _mesh_digests(armature) != mesh_before:
                raise RuntimeError("网格或权重发生意外变化")
            after = _capture_neutral(armature)
            mesh_checks = []
            for name, (before, noise_max, noise_rms) in neutral.items():
                check = evaluate_mesh_tolerance(before, after[name], mode="AUTO_PRODUCTION",
                    baseline_max_delta=noise_max, baseline_rms_delta=noise_rms)
                mesh_checks.append({"mesh": name, "max_delta": check.max_delta,
                                    "hard_limit": check.hard_limit, "result": check.result,
                                    "roundtrip_max": noise_max, "roundtrip_rms": noise_rms})
                if check.result == "FAIL_AND_ROLLBACK":
                    raise RuntimeError("清理导致网格形变：" + name)
            if validator is not None and not validator(context, plan):
                raise RuntimeError("清理验证未通过")
            payload["mutations"] = [
                {"bone": p.bone_name, "operation": "REORIENT", "tail": p.target_tail}
                for p in changed_orientation
            ] + [{"bone": p.bone_name, "operation": "CONNECT"} for p in changed_connections] + [{"bone": name, "operation": "DELETE_DIRECTION_HELPER"} for name in plan.delete_names]
            working["boneweaver_auto_snapshot"] = text.name
            payload.update(status="APPLIED", post_data=working.name,
                           post_fingerprint=_snapshot_fingerprint(armature),
                           reoriented=len(changed_orientation), connected=len(changed_connections), deleted=len(plan.delete_names),
                           mesh_checks=mesh_checks)
            _write(text, payload)
        except Exception as error:
            _activate(context, armature)
            armature.data = original
            original.use_fake_user = pre_fake_user
            if not restore_animation_state(armature, animation):
                raise RuntimeError("动画恢复失败") from error
            _restore_pose(armature, pose)
            context.view_layer.update()
            payload.update(status="ROLLED_BACK", error=str(error))
            _write(text, payload)
            if working.users == 0:
                bpy.data.armatures.remove(working)
            raise
        finally:
            if quick_text:
                bpy.data.texts.remove(quick_text)
    return text.name, payload


def latest_cleanup_snapshot(armature):
    if armature is None:
        return ""
    # The main panel redraw must not parse large pose snapshots every frame.
    direct = armature.data.get("boneweaver_auto_snapshot", "")
    if direct and direct.startswith(PREFIX) and direct in bpy.data.texts:
        return direct
    choices = []
    for text in bpy.data.texts:
        if not text.name.startswith(PREFIX):
            continue
        try:
            p = json.loads(text.as_string())
        except (ValueError, TypeError):
            continue
        if p.get("status") == "APPLIED" and p.get("object_name") == armature.name and p.get("post_data") == armature.data.name:
            choices.append((p.get("created_at", ""), text.name))
    return max(choices)[1] if choices else ""


def restore_cleanup_snapshot(context, text_name):
    text = bpy.data.texts.get(text_name)
    if text is None or not text.name.startswith(PREFIX):
        return False
    payload = json.loads(text.as_string())
    armature = bpy.data.objects.get(payload.get("object_name", ""))
    backup = bpy.data.armatures.get(payload.get("backup_data", ""))
    if (payload.get("status") != "APPLIED" or armature is None or backup is None
            or armature != resolve_active_armature(context)
            or armature.data.name != payload["post_data"]
            or _data_signature(backup) != payload["backup_signature"]
            or _snapshot_fingerprint(armature) != payload["post_fingerprint"]):
        return False
    current = armature.data
    with ContextStateGuard(context):
        _activate(context, armature)
        armature.data = backup
        if not restore_animation_state(armature, payload["pre_animation"]):
            armature.data = current
            return False
        _restore_pose(armature, payload["pre_pose"])
        backup.use_fake_user = payload["backup_fake_user"]
        context.view_layer.update()
    payload["status"] = "RESTORED"
    _write(text, payload)
    if current.users == 0:
        bpy.data.armatures.remove(current)
    return True
