# Safety Contract

BoneWeaver does not:

- unbind or rebind meshes;
- clear or set mesh parenting;
- apply pose as rest pose;
- recalculate, transfer, or normalize production weights;
- delete or recreate Armature modifiers;
- create a production proxy chain, constraints, drivers, empties, or deform dummy bones.

Only selected EditBone `tail`, `roll`, and `use_connect` may change. Names, parents, heads, deform/inheritance flags, mesh topology/coordinates, vertex groups/weights, transforms, modifiers, actions, NLA, constraints, drivers, shape keys, and importer metadata are invariants.

The legacy `create_role_collections` setting remains readable for compatibility but is deprecated and behaviorless. Analyze and Apply never create, remove, or assign Armature Bone Collections.

Analyze is read-only. Apply requires an exact current fingerprint, persistent snapshot, context guard, and post validation. Any validation failure restores allowed fields. Restore refuses conflicts rather than overwriting manual edits.

Hierarchy Inspect and Semantic Discover are also read-only. Their named Select
operators may change temporary Bone selection only; they do not change
Head/Tail/Roll/Connect or permanent Bone colors. A scope affects Analyze only
after an explicit Use action, and no inspection or discovery action runs Analyze
or Apply automatically.

Every actual target-field change must have a `BoneMutationRecord` linked to a frozen Proposal ID. Any missing record, record without a Proposal, invariant-field change, or non-target Bone change fails post validation and rolls back.

Export fails before Pack or Save unless the Plan is current, Apply is successful, Snapshot and mutation records exist, all digests and neutral validation pass, branch/topology accounting is complete, and no blocker remains. The source `.blend` hash and timestamp are checked before and after copy-save. A successful copy is not reported until a second Blender process reopens and validates it.
