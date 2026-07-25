# One-click Quick Reorient

BoneWeaver 0.4.0 provides three whole-Armature actions at the top of the Sidebar.
All three are immediate, force-complete operations with persistent Snapshot
recovery.

## Three automatic modes

1. **原版：全自动转换并重建 L 键骨链** preserves the v0.3.1 clean-room
   UEFormat-compatible direction conversion and native-chain rebuilding.
2. **仅重建连接：保留现有朝向** is for rigs whose orientation is already good.
   It performs no direction recognition. Linear parents are connected to their
   existing child heads and branch boundaries remain separate.
3. **实验性：多特征识别 + UEFormat 回退** starts with a complete
   UEFormat-compatible fallback plan, runs the existing weight-cloud, hierarchy,
   branch, terminal-candidate, and roll evidence pipeline, and overlays only
   confident per-bone results.

For the hybrid mode, missing proposals, invalid vectors, zero-length results,
ambiguous branches, unresolved or low-confidence terminals, safe-parent
fallbacks, or a precision-planner exception all retain the corresponding
UEFormat fallback. They are advisory evidence, never a workflow blocker.

## Workflow

1. Select the imported Armature in Object or Pose Mode.
2. Open **3D Viewport > Sidebar > BoneWeaver**.
3. Click the desired automatic mode. It starts immediately; there is no
   confirmation dialog and no policy blocker.
4. Review the processed-bone, connected-edge, component, and source-adapter
   summary in the panel.
5. Enter Armature Edit Mode, hover a converted linear segment, and press `L`.

Each action performs source capture, immutable planning, advisory diagnostics,
mutation, post-diagnostics, and Snapshot persistence in one operator call. It
does not require the user to run Analyze and Apply separately.

Action, NLA, Driver, bone/object Constraint, non-identity Pose, B-Bone segments,
Bone parenting, envelope deformation, duplicate Armature modifiers, transform
diagnostics, and mesh-evaluation diagnostics never block this path. Shared
Armature data is made single-user automatically; linked data is localized when
Blender permits it. The panel reports how many conditions were handled after
the conversion has completed.

## Source adapters and confidence overlay

The read-only adapter recognizes UEFormat original-transform metadata,
UEFormat-already-reoriented Armatures, and generic joint hierarchies. Socket
bones are detected from importer metadata, conservative name evidence, and Bone
Collections. Control/IK/pole/helper names and zero-length bones are excluded
from direction solving. Skipped bones retain their original state.

The original mode and the hybrid fallback use a clean-room implementation of
UEFormat-compatible dominant-axis and average-child reorientation. The hybrid
overlay accepts direct-child evidence, confident terminal candidates, and
high-confidence branch continuation; it keeps the fallback for every other bone.
The panel reports the exact multi-feature and fallback bone counts.

Mode-specific normalization markers prevent link-only from suppressing a later
original or hybrid run. Repeating the same mode on an unchanged result produces
zero additional geometry mutations.

## Transaction and recovery

Before mutation, BoneWeaver writes a persistent
`BONEWEAVER_QUICK_SNAPSHOT::<sha256>` Text datablock containing every bone's
Head, Tail, Roll, parent, connect state, deform state, source metadata, and mesh
digests. Post-diagnostics inspect target values, invariant fields, connected
component geometry, native connectivity, mesh digests, and neutral evaluated
mesh tolerance. Findings are stored as advisory Snapshot evidence and do not
roll back a completed one-click conversion. An actual Blender edit exception
still triggers automatic rollback so the file is not left half-mutated.

**恢复全自动转换前状态** restores the exact pre-operation bone and metadata
state. It refuses the restore if the Armature, mesh digests, metadata, or any
expected post-operation bone field has changed since conversion.

## Scope and limitations

- The action intentionally targets the complete eligible Armature, not the
  current bone selection.
- It modifies only EditBone `tail`, `roll`, and `use_connect`. Link-only does
  not infer new directions, but may move a linear parent's Tail to its existing
  child Head because Blender requires coincident joints for `use_connect`.
- It does not alter heads, parents, names, weights, meshes, Armature modifiers,
  Actions, NLA, constraints, drivers, or UEFormat animation metadata.
- It reorients rest-bone display geometry; it is not animation Basis
  retargeting.
- Branch boundaries remain disconnected because Blender native linked
  selection cannot represent multiple connected children safely.

See [Native linked selection](native-linked-selection.md) for the component
rules and [Safety Contract](safety.md) for the complete mutation boundary.
