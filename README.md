# UE Chain Prep

UE Chain Prep is a Blender 4.2+ extension that interprets imported Unreal-style bone heads and parent hierarchy as an immutable physics graph, then projects unambiguous graph edges onto the original deform bones for BoneX/Wiggle-style continuous chains.

## Safety model

The `REST_ONLY_STRICT` MVP changes only selected bones' `tail`, `roll`, and `use_connect`. It does not unparent meshes, rebuild Armature modifiers, recalculate weights, apply pose as rest pose, or create a production proxy rig. Analyze is read-only. Apply consumes an exact frozen plan, writes a persistent snapshot, validates digests and neutral evaluated geometry, and rolls back on failure.

## Install

Install `dist/ue_chain_prep-0.2.0.zip` through Blender Preferences → Extensions → Install from Disk. The extension has no external Python dependencies.

## Recommended workflow

1. Import the UE model and original weights.
2. Before ARP, BoneX, or Wiggle creates control relationships, select a secondary-motion chain.
3. Open View3D → Sidebar → UE Chain Prep.
4. Choose scope, physics profile, terminal inference, and roll mode.
5. Analyze and review blockers, terminal candidates, confidence, and graph projection.
6. Apply only a current blocker-free plan.
7. Validate, configure the third-party physics tool, and keep the snapshot until the result is accepted.

The default roll mode is Minimal Twist. Parallel Transport is opt-in. Virtual tips and long-segment samples exist only in the immutable plan, preview, and diagnostics; they never become deform bones.

## Important limitation

Version 0.2.0 is a physics-preparation tool, not a UE animation-basis retargeter. Active Actions, NLA, drivers, non-identity pose, related constraints, ambiguous branches, connected external children, and low-confidence terminal solutions block Apply.

## BoneX 1.2.6 on Blender 5.2

BoneX 1.2.6 may try to initialize `Object["bonex_data"]` while its Soft Connection panel is drawing, which Blender 5.2 rejects. This is a BoneX UI-context bug and reproduces without UE Chain Prep. A version-guarded, reversible local hotfix is documented in [BoneX 1.2.6 draw-context hotfix](docs/bonex-1.2.6-draw-context-hotfix.md). Restart Blender after applying or restoring it.

See [architecture](docs/architecture.md), [algorithms](docs/algorithms.md), [safety](docs/safety.md), and the [manual BoneX/Wiggle checklist](docs/manual-test-bonex-wiggle.md).

## Backend hardening

The production default now uses per-mesh evaluated object-local neutral validation, safe parent-chain leaf fallback, clustered terminal evidence, scored branch continuation, topology-aware weight islands, scoped idempotent overrides, mutation/topology ledgers, a hard conversion-export gate, and independent reopen validation. See [validation tolerance](docs/validation-tolerance.md), [branch resolution](docs/branch-resolution.md), and [export contract](docs/export-contract.md).

## Hierarchy and semantic selection (unreleased)

The current development branch adds five hierarchy inspection modes, cached
Parent/Root/Descendant overlays, explicit branch continuation, and confirmed
semantic secondary-chain discovery. Inspection and discovery are read-only;
selection changes only through their named Select actions, and a frozen scope is
used only after an explicit Use action. The `VISUAL_CHAIN_CLEANUP` profile is
also opt-in and never replaces the production default automatically. See
[hierarchy selection](docs/hierarchy-selection.md), [semantic discovery](docs/semantic-chain-discovery.md),
and [visual cleanup](docs/visual-chain-cleanup.md).
