"""Build and own one frozen hierarchy overlay cache per inspection."""

from __future__ import annotations

from dataclasses import dataclass

import bpy
from mathutils import Vector

from ..contracts import ADDON_ID
from ..core.runtime_store import get_hierarchy_inspection
from ..ui import hierarchy_overlay as overlay_draw


ROLE_COLORS = {
    "PARENT_CONTEXT": (1.0, 0.78, 0.08, 1.0),
    "ACTIVE_ROOT": (1.0, 0.18, 0.06, 1.0),
    "SELECTED_DESCENDANT": (0.0, 0.78, 1.0, 1.0),
    "MAIN_CONTINUATION": (0.0, 0.68, 0.52, 1.0),
    "BRANCH_NODE": (0.72, 0.18, 0.92, 1.0),
    "SIDE_BRANCH": (0.48, 0.52, 0.58, 0.85),
    "TIP_HELPER": (0.88, 0.38, 0.08, 1.0),
    "EXCLUDED_HELPER": (0.48, 0.03, 0.03, 1.0),
}


@dataclass(frozen=True, slots=True)
class HierarchyOverlaySegment:
    start: tuple[float, float, float]
    end: tuple[float, float, float]
    color: tuple[float, float, float, float]
    width: float
    role: str


@dataclass(frozen=True, slots=True)
class HierarchyOverlayLabel:
    position: tuple[float, float, float]
    text: str
    color: tuple[float, float, float, float]
    role: str


@dataclass(frozen=True, slots=True)
class HierarchyOverlayCache:
    inspection_id: str
    armature_object_name: str
    segments: tuple[HierarchyOverlaySegment, ...]
    labels: tuple[HierarchyOverlayLabel, ...]


def _vec3(value) -> tuple[float, float, float]:
    return tuple(float(component) for component in value)


def _dashed_segments(start, end, *, color, role, width, dash_count=8):
    direction = end - start
    return tuple(
        HierarchyOverlaySegment(
            _vec3(start + direction * (index / dash_count)),
            _vec3(start + direction * ((index + 1) / dash_count)),
            color,
            width,
            role,
        )
        for index in range(0, dash_count, 2)
    )


class HierarchyOverlayController:
    @staticmethod
    def _colors(context) -> dict[str, tuple[float, float, float, float]]:
        addon = context.preferences.addons.get(ADDON_ID)
        preferences = getattr(addon, "preferences", None) if addon else None
        if preferences is None:
            return dict(ROLE_COLORS)
        return {
            "PARENT_CONTEXT": tuple(preferences.hierarchy_parent_color),
            "ACTIVE_ROOT": tuple(preferences.hierarchy_active_color),
            "SELECTED_DESCENDANT": tuple(preferences.hierarchy_descendant_color),
            "MAIN_CONTINUATION": tuple(preferences.hierarchy_main_continuation_color),
            "BRANCH_NODE": tuple(preferences.hierarchy_branch_color),
            "SIDE_BRANCH": tuple(preferences.hierarchy_side_branch_color),
            "TIP_HELPER": tuple(preferences.hierarchy_tip_helper_color),
            "EXCLUDED_HELPER": tuple(preferences.hierarchy_excluded_helper_color),
        }

    @staticmethod
    def _options(context) -> overlay_draw.HierarchyOverlayOptions:
        runtime = getattr(context.window_manager, "boneweaver_runtime", None)
        return overlay_draw.HierarchyOverlayOptions(
            show_names=bool(runtime and runtime.hierarchy_show_names),
            show_parent=bool(runtime and runtime.hierarchy_show_parent),
            show_side_branches=bool(runtime and runtime.hierarchy_show_side_branches),
            show_tip_helpers=bool(runtime and runtime.hierarchy_show_tip_helpers),
        )

    @staticmethod
    def _role_by_name(session) -> dict[str, str]:
        plan = session.plan
        roles = {name: "SELECTED_DESCENDANT" for name in plan.selected_bone_names}
        selected = set(plan.selected_bone_names)
        side_roots = set(plan.side_branch_root_names)
        for branch_name in plan.branch_bone_names:
            for child_name in session.index.children_of(branch_name):
                if child_name in selected and child_name not in side_roots:
                    roles[child_name] = "MAIN_CONTINUATION"
        for name in plan.side_branch_root_names:
            roles[name] = "SIDE_BRANCH"
        for name in plan.branch_bone_names:
            roles[name] = "BRANCH_NODE"
        for name in plan.tip_helper_names:
            roles[name] = "TIP_HELPER"
        if (
            plan.parent_context_name
            and plan.parent_context_name not in plan.selected_bone_names
        ):
            roles[plan.parent_context_name] = "PARENT_CONTEXT"
        roles[plan.active_bone_name] = "ACTIVE_ROOT"
        # Render only excluded helpers encountered by this local inspection.
        # The snapshot may contain semantic exclusions from the full Armature;
        # drawing all of them makes a single-chain inspection unreadable.
        for name in plan.excluded_helper_names:
            roles[name] = "EXCLUDED_HELPER"
        return roles

    @classmethod
    def build_cache(cls, context) -> HierarchyOverlayCache:
        """Snapshot bone display geometry once; no RNA is retained by the cache."""
        session = get_hierarchy_inspection()
        if session is None:
            raise RuntimeError("BONEWEAVER_HIERARCHY_INSPECTION_MISSING")
        armature = context.scene.objects.get(session.plan.armature_object_name)
        if armature is None or armature.type != "ARMATURE":
            raise RuntimeError("BONEWEAVER_HIERARCHY_ARMATURE_CHANGED")
        roles = cls._role_by_name(session)
        semantic_categories = dict(session.snapshot.semantic_categories)
        colors = cls._colors(context)
        segments = []
        labels = []
        matrix_world = armature.matrix_world.copy()
        for name in session.index.order_names(roles):
            bone = armature.data.bones.get(name)
            if bone is None:
                raise RuntimeError("BONEWEAVER_HIERARCHY_ARMATURE_CHANGED")
            role = roles[name]
            color = colors[role]
            start = matrix_world @ Vector(bone.head_local)
            end = matrix_world @ Vector(bone.tail_local)
            width = 4.0 if role == "ACTIVE_ROOT" else 3.0 if role in {
                "BRANCH_NODE", "TIP_HELPER", "EXCLUDED_HELPER",
            } else 2.0
            if role == "SIDE_BRANCH":
                segments.extend(_dashed_segments(
                    start, end, color=color, role=role, width=width,
                ))
            else:
                segments.append(HierarchyOverlaySegment(
                    _vec3(start), _vec3(end), color, width, role,
                ))
            prefix = "母骨 · " if role == "PARENT_CONTEXT" else "活动 · " if role == "ACTIVE_ROOT" else ""
            category = semantic_categories.get(name)
            semantic_suffix = f" · {category}" if category else ""
            labels.append(HierarchyOverlayLabel(
                _vec3(start), f"{prefix}{name}{semantic_suffix}", color, role,
            ))
        return HierarchyOverlayCache(
            inspection_id=session.plan.inspection_id,
            armature_object_name=armature.name,
            segments=tuple(segments),
            labels=tuple(labels),
        )

    @classmethod
    def enable(cls, context) -> None:
        cache = cls.build_cache(context)
        runtime = getattr(context.window_manager, "boneweaver_runtime", None)
        try:
            overlay_draw.enable(cache, cls._options(context))
        except Exception:
            if runtime is not None:
                runtime.hierarchy_overlay_enabled = False
            cls.tag_redraw(context)
            raise
        if runtime is not None:
            runtime.hierarchy_overlay_enabled = True
        cls.tag_redraw(context)

    @classmethod
    def refresh(cls, context) -> bool:
        if overlay_draw.is_enabled():
            try:
                cls.enable(context)
            except Exception:
                cls.disable(context)
                return False
            return True
        return False

    @classmethod
    def sync_options(cls, context) -> None:
        overlay_draw.set_options(cls._options(context))
        cls.tag_redraw(context)

    @staticmethod
    def disable(context=None) -> None:
        overlay_draw.disable()
        if context is not None:
            runtime = getattr(context.window_manager, "boneweaver_runtime", None)
            if runtime is not None:
                runtime.hierarchy_overlay_enabled = False
            HierarchyOverlayController.tag_redraw(context)

    @staticmethod
    def is_enabled() -> bool:
        return overlay_draw.is_enabled()

    @staticmethod
    def tag_redraw(context) -> None:
        screen = getattr(context, "screen", None)
        for area in getattr(screen, "areas", ()) if screen else ():
            if area.type == "VIEW_3D":
                area.tag_redraw()
