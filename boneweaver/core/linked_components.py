"""Pure maximal-linear-component decomposition for native linked selection."""

from __future__ import annotations

from .canonical import sha256
from .quick_reorient_models import LinkedChainComponent, QuickBoneState


def decompose_linear_components(
    bone_states: tuple[QuickBoneState, ...],
    eligible_names: frozenset[str],
    eligible_edges: frozenset[tuple[str, str]] | None = None,
) -> tuple[LinkedChainComponent, ...]:
    """Return deterministic paths whose interior edges have one eligible child."""
    by_name = {state.bone_name: state for state in bone_states}
    children = {
        name: tuple(
            child
            for child in by_name[name].child_names
            if child in eligible_names
            and (eligible_edges is None or (name, child) in eligible_edges)
        )
        for name in eligible_names
    }
    roots = []
    for name in sorted(eligible_names):
        parent = by_name[name].parent_name
        if (
            parent not in eligible_names
            or (eligible_edges is not None and (parent, name) not in eligible_edges)
            or len(children[parent]) != 1
        ):
            roots.append(name)

    components = []
    visited: set[str] = set()
    for root in roots:
        path = []
        current = root
        while current in eligible_names and current not in visited:
            path.append(current)
            visited.add(current)
            next_names = children[current]
            if len(next_names) != 1:
                break
            current = next_names[0]
        if not path:
            continue
        parent = by_name[root].parent_name
        parent_branch = (
            parent if parent in eligible_names and len(children[parent]) > 1 else None
        )
        component_id = sha256(("boneweaver.linked_component", tuple(path)))
        components.append(
            LinkedChainComponent(
                component_id=component_id,
                bone_names=tuple(path),
                root_bone_name=root,
                leaf_bone_name=path[-1],
                parent_branch_name=parent_branch,
                contains_weightless_leaf=not by_name[path[-1]].use_deform,
            )
        )

    for name in sorted(eligible_names - visited):
        component_id = sha256(("boneweaver.linked_component", (name,)))
        components.append(
            LinkedChainComponent(
                component_id, (name,), name, name, None, not by_name[name].use_deform
            )
        )
    return tuple(
        sorted(components, key=lambda item: (item.root_bone_name, item.component_id))
    )


def component_lookup(
    components: tuple[LinkedChainComponent, ...],
) -> dict[str, str]:
    return {
        bone_name: component.component_id
        for component in components
        for bone_name in component.bone_names
    }
