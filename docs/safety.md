# Safety Contract

BoneWeaver does not:

- unbind or rebind meshes;
- clear or set mesh parenting;
- apply pose as rest pose;
- recalculate, transfer, or normalize production weights;
- delete or recreate Armature modifiers;
- create a production proxy chain, constraints, drivers, empties, or deform dummy bones.

Only target EditBone `tail`, `roll`, and `use_connect` may change. The selective
Physics Graph workflow targets its frozen scope; the three automatic Quick
Reorient modes target every eligible non-Socket bone in the active Armature. Names,
parents, heads, deform/inheritance flags, mesh topology/coordinates, vertex
groups/weights, transforms, modifiers, actions, NLA, constraints, drivers,
shape keys, and importer metadata are invariants.

The legacy `create_role_collections` setting remains readable for compatibility but is deprecated and behaviorless. Analyze and Apply never create, remove, or assign Armature Bone Collections.

Analyze is read-only. Apply requires an exact current fingerprint, persistent snapshot, context guard, and post validation. Any validation failure restores allowed fields. Restore refuses conflicts rather than overwriting manual edits.

Quick Reorient captures and plans before mutation and writes a persistent
Snapshot. In v0.4.0 all three panel-top actions are explicitly force-complete:
preflight and post-diagnostic findings never become policy blockers. Action,
NLA, Driver, Constraint, Pose, B-Bone, parenting, envelope, modifier, transform,
mesh-digest, and neutral-mesh findings remain visible as advisory evidence. An
actual Blender edit exception still rolls back to avoid a half-written Armature.
In experimental hybrid mode, the UEFormat-compatible proposal is computed first
for every eligible bone. Multi-feature output replaces it only after per-bone
confidence and finite-geometry checks; unrecognized bones and precision-planner
failures therefore degrade to fallback instead of aborting the transaction.
Its Restore compares the complete expected post-state and refuses to overwrite
later manual changes. The separate scoped Physics Graph Apply retains its strict
blocking and post-validation behavior.

Hierarchy Inspect and Semantic Discover are also read-only. Their named Select
operators may change temporary Bone selection only; they do not change
Head/Tail/Roll/Connect or permanent Bone colors. A scope affects Analyze only
after an explicit Use action, and no inspection or discovery action runs Analyze
or Apply automatically.

Every actual target-field change must have a `BoneMutationRecord` linked to a frozen Proposal ID. Any missing record, record without a Proposal, invariant-field change, or non-target Bone change fails post validation and rolls back.

Export fails before Pack or Save unless the Plan is current, Apply is successful, Snapshot and mutation records exist, all digests and neutral validation pass, branch/topology accounting is complete, and no blocker remains. The source `.blend` hash and timestamp are checked before and after copy-save. A successful copy is not reported until a second Blender process reopens and validates it.
