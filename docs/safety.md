# Safety Contract

UE Chain Prep does not:

- unbind or rebind meshes;
- clear or set mesh parenting;
- apply pose as rest pose;
- recalculate, transfer, or normalize production weights;
- delete or recreate Armature modifiers;
- create a production proxy chain, constraints, drivers, empties, or deform dummy bones.

Only selected EditBone `tail`, `roll`, and `use_connect` may change. Names, parents, heads, deform/inheritance flags, mesh topology/coordinates, vertex groups/weights, transforms, modifiers, actions, NLA, constraints, drivers, shape keys, and importer metadata are invariants.

Analyze is read-only. Apply requires an exact current fingerprint, persistent snapshot, context guard, and post validation. Any validation failure restores allowed fields. Restore refuses conflicts rather than overwriting manual edits.
