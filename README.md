# UE Chain Prep

UE Chain Prep is a Blender 4.2+ extension that interprets imported Unreal-style bone heads and parent hierarchy as an immutable physics graph, then projects unambiguous graph edges onto the original deform bones for BoneX/Wiggle-style continuous chains.

## Safety model

The `REST_ONLY_STRICT` MVP changes only selected bones' `tail`, `roll`, and `use_connect`. It does not unparent meshes, rebuild Armature modifiers, recalculate weights, apply pose as rest pose, or create a production proxy rig. Analyze is read-only. Apply consumes an exact frozen plan, writes a persistent snapshot, validates digests and neutral evaluated geometry, and rolls back on failure.

## Install

Install `dist/ue_chain_prep-0.1.0.zip` through Blender Preferences → Extensions → Install from Disk. The extension has no external Python dependencies.

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

Version 0.1.0 is a physics-preparation tool, not a UE animation-basis retargeter. Active Actions, NLA, drivers, non-identity pose, related constraints, ambiguous branches, connected external children, and low-confidence terminal solutions block Apply.

See [architecture](docs/architecture.md), [algorithms](docs/algorithms.md), [safety](docs/safety.md), and the [manual BoneX/Wiggle checklist](docs/manual-test-bonex-wiggle.md).
