# Architecture

BoneWeaver separates stable source truth, immutable reasoning, and Blender mutation:

```text
Armature Bone Head + Parent Hierarchy + Rest Axes + Weight Evidence
  -> immutable PhysicsNode / PhysicsEdge / PhysicsChain
  -> terminal candidates and optional Virtual Tip nodes
  -> immutable BoneProposal
  -> snapshot-backed EditBone transaction
  -> post validation or rollback
```

`Analyze` reads Blender RNA and freezes ordinary Python dataclasses. `_PLAN_STORE` holds no Blender RNA references. `Apply` accepts one exact `plan_id`, recomputes source and settings fingerprints, creates `BONEWEAVER_SNAPSHOT::<sha256>`, modifies only allowed EditBone fields, then validates. UI lists and viewport caches are views, never transaction inputs.

The one-click Quick Reorient path is independent of the selective Physics Graph
Plan but follows the same immutable-plan and snapshot-backed transaction model:

```text
Complete Armature EditBone capture + importer metadata
  -> immutable QuickReorientPlan
  -> UEFormat-compatible direction proposals
  -> maximal linear LinkedChainComponents
  -> snapshot-backed tail / roll / use_connect transaction
  -> mesh, invariant, native-component validation
  -> commit or automatic rollback
```

`QuickReorientController` owns this full workflow and all related runtime-state
writes. Its operators are thin adapters and the panel renders a pure
`QuickReorientView`. `_QUICK_PLAN_STORE` contains immutable values only. The
persistent `BONEWEAVER_QUICK_SNAPSHOT::<sha256>` Text datablock is the sole
cross-session recovery record.

The interaction layer is controller-owned: `WorkflowController` owns workflow transitions, `PreviewController` owns the draw handler/cache/runtime flag, `SessionController` owns Plan loss and lifecycle cleanup, and `SelectionController` owns selection identity and issue location. Operators are thin adapters. The main panel renders pure view models; technical state and raw codes stay in opt-in diagnostics.

Hierarchy inspection and semantic discovery are separate pre-Analyze pipelines:

```text
Armature hierarchy snapshot
  -> immutable HierarchyIndex
  -> deterministic HierarchyInspectionPlan
  -> cached viewport Overlay roles
  -> explicit Select
  -> explicit frozen hierarchy Analyze Scope

Full Armature BoneState snapshot + optional reusable weight summaries
  -> layered semantic rules (default, Source Adapter, game, user)
  -> immutable SemanticDiscoveryPlan
  -> explicit chain confirmation and Select
  -> explicit frozen semantic Analyze Scope
```

Neither pipeline runs Analyze or Apply. Hierarchy and semantic frozen scopes are
mutually exclusive and bind the source file plus Armature object/data identity.
The runtime store contains only immutable values and identifiers, never Blender
RNA. Load, undo, redo, relevant depsgraph changes, successful Apply, reset, and
unregister invalidate the transient plans and draw caches.

Branches remain graph facts. `Branch Continuation Resolver` scores every direct child without deleting graph edges, then projects one sufficiently distinct main continuation onto the Blender branch tail. Side children retain their parent and head and are projected as disconnected `BRANCH_SIDE_ROOT` proposals. Ambiguous symmetric branches remain blockers.

Backend hardening adds these operation-scoped layers:

```text
MeshScanCache
  -> streaming weight/base/modifier digests
  -> compact per-mesh weight inputs
  -> topology components and compatible clouds

Frozen Plan
  -> proposal IDs
  -> branch resolutions
  -> topology projection ledger

Apply Transaction
  -> field-level mutation records
  -> per-mesh neutral validation
  -> persistent snapshot

Export Gate
  -> conversion manifest
  -> copy save
  -> independent Blender reopen validation
```

The Plan contains statistics and digests, never Blender RNA references or raw
point clouds. Export is a separate backend contract. G01 hardening does not add
normal-workflow actions; the opt-in G02 hierarchy and semantic panels are
separate pre-Analyze tools.
