# BoneWeaver

[中文说明](README_zh.md)

Safety-first Blender tooling for turning Unreal Engine bone hierarchies into
reviewable, physics-ready chains for BoneX and Wiggle.

## Highlights

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

Analyze, hierarchy inspection, and semantic discovery are read-only. Apply may
change only the selected EditBones' `tail`, `roll`, and `use_connect`. It does
not rebind meshes, recalculate weights, apply pose as rest pose, recreate
Armature modifiers, or create production proxy bones.

Apply consumes an exact frozen plan, writes a persistent Snapshot, validates
the result, and rolls back on failure. Restore refuses conflicts instead of
overwriting later manual edits. See [the full safety contract](docs/safety.md).

## Requirements

- Blender 4.2 or newer
- An imported Unreal-style Armature; associated weighted meshes are recommended
- No external Python packages

BoneX, Wiggle, Auto-Rig Pro, and UEFormat are optional workflow integrations,
not bundled dependencies.

## Installation

Download `boneweaver-0.2.0.zip` from the
[v0.2.0 release](https://github.com/dotm5/BoneWeaver/releases/tag/v0.2.0).
In Blender, open **Edit > Preferences > Extensions > Install from Disk**, select
the ZIP, and enable BoneWeaver.

## Quick start

1. Import the UE model and preserve its original weights.
2. Select the secondary-motion bones you want to prepare.
3. Open **3D Viewport > Sidebar > BoneWeaver**.
4. Choose a scope and target profile, then run **Check and Preview**.
5. Review the Physics Graph, terminal evidence, warnings, and blockers.
6. Run **Apply Conversion** only when the frozen plan is current and unblocked.
7. Configure BoneX or Wiggle, then keep the Snapshot until the result is accepted.

## Hierarchy inspection and semantic discovery

Hierarchy inspection shows cached Parent/Root/Descendant overlays without
changing selection. Named Select actions change only temporary bone selection;
**Use for Conversion** explicitly freezes that result as the next Analyze scope.

Semantic discovery scans the Armature for hair, ribbon, skirt, tail, and
accessory candidates. Candidates require confirmation and never flow into Apply
automatically. Ambiguous branches require an explicit continuation choice.

## Validation and recovery

BoneWeaver blocks Apply when Actions, NLA, drivers, constraints, pose state,
connected external children, branch ambiguity, low-confidence terminals, or
mesh/modifier drift make the conversion unsafe. A successful Apply records a
field-level mutation ledger. Export also performs an independent second-process
reopen validation before reporting success.

## Tested release

BoneWeaver v0.2.0 was validated with Blender 5.2.0 LTS RC build
`710df102694f`:

- 208 Blender-hosted automated tests passed with zero failures or errors.
- A real UE asset with 157 bones and 25,610 vertices completed Analyze, Apply,
  export, and independent reopen validation.
- The release ZIP passed an isolated install and repeated registration cycle.
- Archive: `boneweaver-0.2.0.zip`
- Size: `170163` bytes
- SHA-256: `5F4B3F91B2A5BB59D10469F0BDF5263B9B1EDE44BE5055990DA89CF80BC1C48F`

## Known limitations

- v0.2.0 prepares physics chains; it is not a UE animation-basis retargeter.
- Blender 4.2 is the manifest minimum, but this release's local executable
  validation was performed on the Blender 5.2 build above.
- BoneX/Wiggle runtime behavior still requires project-specific manual tuning.
- Existing Actions, NLA, drivers, non-identity pose, related constraints, and
  unsafe branch/terminal evidence intentionally block Apply.

## Documentation

- [User workflow](docs/user-workflow.md)
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
