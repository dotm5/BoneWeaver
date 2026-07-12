# Visual Chain Cleanup

`VISUAL_CHAIN_CLEANUP` is an explicit profile for users who do not need to
preserve the original Unreal animation behavior and want conventional visible
Blender/MMD-style bone chains. It is never selected automatically.

## Fixed behavior

- Every interior tail points to the selected child's head.
- Roll always uses `MINIMAL_TWIST`; the ordinary Roll setting is ignored.
- The first bone in a frozen scope does not connect to an external parent.
- Linear interior bones connect to their parents.
- A manually chosen main continuation may connect through a branch.
- Side-branch roots remain disconnected.
- Branch resolution is always `MANUAL_ONLY`. Longest-path and automatic branch
  scoring are never used by this profile.

An unresolved branch is a Blocker. Use Hierarchy Select & Inspect to choose a
direct child as the main continuation, freeze that scope, and Analyze again.

## Leaf order

Visual cleanup resolves leaf direction in this order:

1. an Existing Tip Helper head;
2. safe parent-chain extrapolation;
3. an explicit manual terminal override.

It does not use weight-cloud, imported-axis, original-axis, or hybrid candidate
selection for leaves. If parent extrapolation is unsafe and no valid scoped
manual override exists, Analyze emits a Blocker.

## Tip Helper usage

`TipHelperUsage` is frozen into the Conversion Plan, snapshot, diagnostic
report, and export manifest.

- `REFERENCE_ONLY` is the default. The helper supplies its head to the parent,
  receives no Proposal, and must remain unchanged.
- `INCLUDE_AS_PHYSICS_TERMINAL` is allowed only with
  `VISUAL_CHAIN_CLEANUP`. A classified helper with no excluded Socket/Control
  child becomes an explicit mutation target and receives its own safe terminal
  tail. The parent still points to the helper head.

If inclusion is selected under another profile, or a helper has an excluded
child, Analyze keeps the helper reference-only and emits a Blocker. It never
silently mutates an unsafe helper.

Snapshot, topology-ledger, export-readiness, and reopen checks distinguish
reference-only helpers from explicitly included helper mutation targets.
