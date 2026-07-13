# Native linked selection

Blender's `L` key selects geometry connected through native EditBone
connectivity. A parent/child relationship alone is not enough: the child must
have `use_connect = True`, and the parent Tail must coincide with the child
Head.

BoneWeaver 0.3.0 decomposes the eligible skeleton into deterministic maximal
linear components. For every component:

- each internal parent has exactly one eligible child;
- the parent Tail is placed at that child's unchanged Head;
- the child uses native `use_connect = True`;
- the component root remains disconnected from any external parent;
- a branch point ends the incoming component and starts separate child
  components;
- Socket, control, skipped, and unsafe bones never bridge two components.

This produces native Blender behavior without installing a keymap or replacing
the `L` operator. Hovering a finger, hair, ribbon, spine, or similar unambiguous
segment in Edit Mode selects only its connected component. At a branch,
selecting one side does not pull in sibling branches.

The conversion validator checks component parent identity, Tail/Head
coincidence, every internal child's connect state, every component root's
disconnected state, and branch-child isolation. A mismatch causes automatic
rollback rather than leaving a partially connected hierarchy.
