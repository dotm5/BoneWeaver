"""Immutable, deterministic parent/child hierarchy queries.

The index is deliberately independent from Blender RNA.  Callers snapshot the
bone names and parent names once, then every inspection and overlay query uses
this structure instead of walking ``children_recursive`` during drawing.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from types import MappingProxyType


class HierarchyIndexError(ValueError):
    """Raised when a hierarchy snapshot cannot describe a valid forest."""


@dataclass(frozen=True, slots=True)
class HierarchyBoneSnapshot:
    """Minimal Blender-free input required to build a hierarchy index."""

    name: str
    parent_name: str | None


def _name_sort_key(name: str) -> tuple[str, str]:
    return name.casefold(), name


def _readonly_mapping(values: Mapping):
    return MappingProxyType(dict(values))


@dataclass(frozen=True, slots=True)
class ArmatureHierarchyIndex:
    """Stable adjacency, depth and order information for one armature.

    ``bone_order`` is a depth-first pre-order that preserves the source
    armature's stable root and sibling order.  It is independent from mutable
    Blender selection state and can be built in O(Bones + Edges).
    """

    parent_by_child: Mapping[str, str | None]
    children_by_parent: Mapping[str, tuple[str, ...]]
    depth_by_bone: Mapping[str, int]
    bone_order: tuple[str, ...]

    def __post_init__(self) -> None:
        parent_by_child = dict(self.parent_by_child)
        children_by_parent = {
            name: tuple(children)
            for name, children in self.children_by_parent.items()
        }
        depth_by_bone = dict(self.depth_by_bone)
        bone_order = tuple(self.bone_order)
        names = set(parent_by_child)
        if set(children_by_parent) != names:
            raise HierarchyIndexError("children_by_parent must contain every bone exactly once")
        if set(depth_by_bone) != names:
            raise HierarchyIndexError("depth_by_bone must contain every bone exactly once")
        if len(bone_order) != len(names) or set(bone_order) != names:
            raise HierarchyIndexError("bone_order must contain every bone exactly once")
        for child_name, parent_name in parent_by_child.items():
            if parent_name is not None and parent_name not in names:
                raise HierarchyIndexError(
                    f"bone {child_name!r} references missing parent {parent_name!r}"
                )
        listed_children: list[str] = []
        for parent_name, child_names in children_by_parent.items():
            for child_name in child_names:
                if child_name not in names:
                    raise HierarchyIndexError(
                        f"bone {parent_name!r} lists unknown child {child_name!r}"
                    )
                if parent_by_child[child_name] != parent_name:
                    raise HierarchyIndexError(
                        f"bone {child_name!r} has inconsistent parent adjacency"
                    )
                listed_children.append(child_name)
        expected_children = {
            name for name, parent_name in parent_by_child.items() if parent_name is not None
        }
        if len(listed_children) != len(set(listed_children)) or set(listed_children) != expected_children:
            raise HierarchyIndexError("child adjacency must list every non-root bone exactly once")
        order_position = {name: position for position, name in enumerate(bone_order)}
        for name, parent_name in parent_by_child.items():
            depth = depth_by_bone[name]
            if parent_name is None:
                if depth != 0:
                    raise HierarchyIndexError(f"root bone {name!r} must have depth zero")
                continue
            if depth != depth_by_bone[parent_name] + 1:
                raise HierarchyIndexError(f"bone {name!r} has inconsistent depth")
            if order_position[parent_name] >= order_position[name]:
                raise HierarchyIndexError(f"parent {parent_name!r} must precede child {name!r}")
        object.__setattr__(self, "parent_by_child", _readonly_mapping(parent_by_child))
        object.__setattr__(self, "children_by_parent", _readonly_mapping(children_by_parent))
        object.__setattr__(self, "depth_by_bone", _readonly_mapping(depth_by_bone))
        object.__setattr__(self, "bone_order", bone_order)

    @classmethod
    def from_bones(cls, bones: Iterable[HierarchyBoneSnapshot]) -> ArmatureHierarchyIndex:
        """Build an index from immutable name/parent snapshots."""
        parent_by_child: dict[str, str | None] = {}
        source_order: list[str] = []
        for bone in bones:
            name = str(bone.name)
            parent_name = None if bone.parent_name is None else str(bone.parent_name)
            if not name:
                raise HierarchyIndexError("bone name must not be empty")
            if name in parent_by_child:
                raise HierarchyIndexError(f"duplicate bone name {name!r}")
            if parent_name == name:
                raise HierarchyIndexError(f"bone {name!r} cannot parent itself")
            parent_by_child[name] = parent_name
            source_order.append(name)

        names = set(parent_by_child)
        missing = sorted(
            {
                parent_name
                for parent_name in parent_by_child.values()
                if parent_name is not None and parent_name not in names
            },
            key=_name_sort_key,
        )
        if missing:
            raise HierarchyIndexError(f"missing parent bones: {', '.join(missing)}")

        mutable_children = {name: [] for name in source_order}
        for child_name, parent_name in parent_by_child.items():
            if parent_name is not None:
                mutable_children[parent_name].append(child_name)
        children_by_parent = {
            name: tuple(children)
            for name, children in mutable_children.items()
        }

        roots = tuple(
            name for name in source_order if parent_by_child[name] is None
        )
        if names and not roots:
            raise HierarchyIndexError("hierarchy contains no root; a parent cycle is present")

        depth_by_bone: dict[str, int] = {}
        bone_order: list[str] = []
        stack = [(root_name, 0) for root_name in reversed(roots)]
        while stack:
            name, depth = stack.pop()
            if name in depth_by_bone:
                raise HierarchyIndexError(f"hierarchy contains a cycle at bone {name!r}")
            depth_by_bone[name] = depth
            bone_order.append(name)
            for child_name in reversed(children_by_parent[name]):
                stack.append((child_name, depth + 1))

        if len(bone_order) != len(names):
            unresolved = sorted(names - set(bone_order), key=_name_sort_key)
            raise HierarchyIndexError(
                f"hierarchy contains a disconnected parent cycle: {', '.join(unresolved)}"
            )
        return cls(parent_by_child, children_by_parent, depth_by_bone, tuple(bone_order))

    @classmethod
    def from_bone_states(cls, bone_states: Iterable[object]) -> ArmatureHierarchyIndex:
        """Adapt objects exposing ``name`` and ``parent_name`` without retaining them."""
        return cls.from_bones(
            HierarchyBoneSnapshot(
                name=str(getattr(state, "name")),
                parent_name=getattr(state, "parent_name"),
            )
            for state in bone_states
        )

    def __contains__(self, bone_name: str) -> bool:
        return bone_name in self.parent_by_child

    def parent_of(self, bone_name: str) -> str | None:
        """Return the direct parent or raise ``KeyError`` for an unknown bone."""
        return self.parent_by_child[bone_name]

    def children_of(self, bone_name: str) -> tuple[str, ...]:
        """Return direct children in canonical order."""
        return self.children_by_parent[bone_name]

    def depth_of(self, bone_name: str) -> int:
        return self.depth_by_bone[bone_name]

    def roots(self) -> tuple[str, ...]:
        return tuple(name for name in self.bone_order if self.parent_by_child[name] is None)

    def ancestors_of(self, bone_name: str, *, include_self: bool = False) -> tuple[str, ...]:
        """Return ancestors nearest-parent first, optionally prefixed by the bone."""
        if bone_name not in self:
            raise KeyError(bone_name)
        ancestors = [bone_name] if include_self else []
        current = self.parent_by_child[bone_name]
        while current is not None:
            ancestors.append(current)
            current = self.parent_by_child[current]
        return tuple(ancestors)

    def descendants_of(self, bone_name: str, *, include_self: bool = False) -> tuple[str, ...]:
        """Return descendants in the index's deterministic depth-first order."""
        if bone_name not in self:
            raise KeyError(bone_name)
        descendants: set[str] = {bone_name} if include_self else set()
        stack = list(reversed(self.children_by_parent[bone_name]))
        while stack:
            current = stack.pop()
            descendants.add(current)
            stack.extend(reversed(self.children_by_parent[current]))
        return tuple(name for name in self.bone_order if name in descendants)

    def order_names(self, bone_names: Iterable[str]) -> tuple[str, ...]:
        """Deduplicate known names and return them in canonical hierarchy order."""
        requested = set(bone_names)
        return tuple(name for name in self.bone_order if name in requested)

    def branch_bones(self, bone_names: Iterable[str] | None = None) -> tuple[str, ...]:
        """Return bones with more than one child, optionally limited to a scope."""
        scope = set(self.bone_order if bone_names is None else bone_names)
        return tuple(
            name
            for name in self.bone_order
            if name in scope and len(self.children_by_parent[name]) > 1
        )
