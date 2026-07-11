# Architecture

UE Chain Prep separates stable source truth, immutable reasoning, and Blender mutation:

```text
Armature Bone Head + Parent Hierarchy + Rest Axes + Weight Evidence
  -> immutable PhysicsNode / PhysicsEdge / PhysicsChain
  -> terminal candidates and optional Virtual Tip nodes
  -> immutable BoneProposal
  -> snapshot-backed EditBone transaction
  -> post validation or rollback
```

`Analyze` reads Blender RNA and freezes ordinary Python dataclasses. `_PLAN_STORE` holds no Blender RNA references. `Apply` accepts one exact `plan_id`, recomputes source and settings fingerprints, creates `UECP_SNAPSHOT::<sha256>`, modifies only allowed EditBone fields, then validates. UI lists and viewport caches are views, never transaction inputs.

The interaction layer is controller-owned: `WorkflowController` owns workflow transitions, `PreviewController` owns the draw handler/cache/runtime flag, `SessionController` owns Plan loss and lifecycle cleanup, and `SelectionController` owns selection identity and issue location. Operators are thin adapters. The main panel renders a pure `PanelViewState`; technical state and raw codes stay in opt-in diagnostics.

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

The Plan contains statistics and digests, never Blender RNA references or raw point clouds. Export is a separate backend contract; the ordinary panel workflow and button layout are unchanged.
