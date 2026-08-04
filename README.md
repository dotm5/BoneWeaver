# BoneWeaver

[中文说明](README_zh.md)

Safety-first Blender tooling for turning Unreal Engine bone hierarchies into
reviewable, physics-ready chains for BoneX and Wiggle.

## Highlights

- Choose one of three panel-top automatic actions: the original
  UEFormat-compatible conversion, link-only rebuilding for already well-oriented
  rigs, or the experimental multi-feature conversion with automatic per-bone
  UEFormat fallback.
- Inspect parent, root, descendant, branch, and semantic secondary-chain scopes
  before changing selection or rest geometry.
- Build an immutable Physics Graph from bone heads and hierarchy, with explicit
  terminal-tip evidence and branch continuation.
- Preview proposed tails, roll, connectivity, warnings, and blockers before
  Apply.
- Use conservative presets for BoneX rotation chains, Wiggle rotation/stretch
  chains, or opt-in visual chain cleanup.
- Export only after transaction, digest, topology, mutation-ledger, and neutral
  evaluated-mesh validation succeeds.

## Safety contract

Analyze, hierarchy inspection, and semantic discovery are read-only. Apply and
the three panel-top automatic actions may change only EditBone `tail`, `roll`, and
`use_connect`. They do
not rebind meshes, recalculate weights, apply pose as rest pose, recreate
Armature modifiers, or create production proxy bones.

Scoped Apply consumes an exact frozen plan and keeps its strict validation
contract. All three automatic actions use force-complete mode: Action, NLA, Driver,
Constraint, Pose, B-Bone, parenting, envelope, modifier, and mesh diagnostics
are advisory and never block conversion. It still writes a persistent Snapshot;
Blender editing exceptions roll back, and Restore refuses to overwrite later
manual edits. See [the full safety contract](docs/safety.md).

## Requirements

- Blender 4.2 or newer
- An imported Unreal-style Armature; associated weighted meshes are recommended
- No external Python packages

BoneX, Wiggle, Auto-Rig Pro, and UEFormat are optional workflow integrations,
not bundled dependencies.

## Installation

Install `dist/boneweaver-0.4.1.zip`. In Blender, open
**Edit > Preferences > Extensions > Install from Disk**, select the ZIP, and
enable BoneWeaver.

## Quick start

1. Import the UE model and preserve its original weights.
2. Select its Armature and open **3D Viewport > Sidebar > BoneWeaver**.
3. Choose one of the three top-level buttons:
   - **Original** applies the v0.3.1 UEFormat-compatible conversion.
   - **Links only** keeps the current orientation and rebuilds native connected
     linear chains.
   - **Experimental hybrid** uses confident multi-feature results per bone and
     automatically falls back to the original UEFormat-compatible result for
     every unresolved bone.
4. The selected action starts immediately, processes the complete eligible
   Armature, validates the result, and stores a persistent Snapshot.
5. In Edit Mode, hover a converted segment and press `L` to select the linked
   native chain. Branch boundaries remain separate by design.
6. Use **Restore Pre-conversion State** if the result is not wanted. Restore
   refuses to overwrite later manual edits.

The existing scoped Physics Graph workflow remains available below the one-click
box for selective BoneX/Wiggle preparation and detailed preview.

## Hierarchy inspection and semantic discovery

Hierarchy inspection shows cached Parent/Root/Descendant overlays without
changing selection. Named Select actions change only temporary bone selection;
**Use for Conversion** explicitly freezes that result as the next Analyze scope.

Semantic discovery scans the Armature for hair, ribbon, skirt, tail, and
accessory candidates. Candidates require confirmation and never flow into Apply
automatically. Ambiguous branches require an explicit continuation choice.

## Validation and recovery

The scoped Physics Graph Apply blocks when Actions, NLA, drivers, constraints, pose state,
connected external children, branch ambiguity, low-confidence terminals, or
mesh/modifier drift make the conversion unsafe. A successful Apply records a
field-level mutation ledger. Export also performs an independent second-process
reopen validation before reporting success.

The three panel-top automatic actions keep their v0.4.0 behavior when animation
compatibility is disabled. With **Protect Existing Animation and UEFormat Basis**
enabled, BoneWeaver rebases one safe Active Action and blocks unsupported active
animation stacks before changing the rest basis.
Hybrid recognition blockers are converted to advisory diagnostics and trigger
per-bone fallback instead of stopping the operation.

## Tested release

BoneWeaver v0.4.1 was validated locally with Blender 5.2.0 LTS build
`fbe6228777e7`:

- 230 Blender-hosted automated tests passed with zero failures or errors.
- Animation probes passed parent-local basis delta, cumulative `post_quat`,
  Active Action rebasing, connected topology, idempotence, and exact
  Action/metadata Restore. Unsupported active animation stacks blocked before
  mutation; an empty Action used the explicit Quick fallback.
- A fixed UEFormat 1.0.0 comparison covered 154 eligible bones: maximum direction
  error `0.033878°`, maximum length error `1.164412e-7`, with unchanged heads,
  parents, and sockets.
- All three modes passed independently on a raw 157-bone `.uemodel` and the
  existing `x1.blend`. Native `L` selection worked on finger, hair, ribbon, and
  spine chains; every second run made zero additional mutations; exact Restore
  passed; both source hashes remained unchanged. Hybrid selected 94 confident
  multi-feature results and automatically fell back on 61 bones.
- The release ZIP passed an isolated install and repeated registration cycle.
- Archive: `boneweaver-0.4.1.zip`
- Size: `200097` bytes
- SHA-256: `7D5160229B8FA33D9C29B36D53BC8A8903B88ACD1F3C72434B5D524D94CEB059`

## Known limitations

- Animation compatibility supports one local, unshared Active Action containing
  only supported pose-bone transform FCurves. Active NLA strips, pose Drivers,
  effective pose constraints, shared Actions, and unsupported paths block.
- Link-only mode performs no orientation inference. To create native connected
  edges without moving child heads, a linear parent's tail is normalized to its
  existing child head when those points differ.
- Hybrid mode is experimental; its confidence gate deliberately prefers the
  UEFormat-compatible fallback whenever the multi-feature result is unresolved.
- Blender 4.2 is the manifest minimum, but this release's local executable
  validation was performed on the Blender 5.2 build above.
- BoneX/Wiggle runtime behavior still requires project-specific manual tuning.
- Existing Actions, NLA, drivers, non-identity pose, related constraints, and
  unsafe branch/terminal evidence intentionally block only the separate scoped
  Physics Graph Apply; they do not block one-click Quick Reorient.

## Documentation

- [User workflow](docs/user-workflow.md)
- [One-click Quick Reorient](docs/quick-reorient.md)
- [Native linked selection](docs/native-linked-selection.md)
- [Architecture](docs/architecture.md)
- [Algorithms](docs/algorithms.md)
- [Hierarchy selection](docs/hierarchy-selection.md)
- [Semantic discovery](docs/semantic-chain-discovery.md)
- [Validation and export contract](docs/export-contract.md)
- [Compatibility](docs/compatibility.md)
- [Changelog](CHANGELOG.md)

## Development

See [CONTRIBUTING.md](CONTRIBUTING.md) for the Blender-hosted verification and
packaging gates. Security issues must follow [SECURITY.md](SECURITY.md).

## License

BoneWeaver is licensed under the GNU General Public License v3.0 or later. See
[LICENSE](LICENSE).
