# BoneWeaver Repository and Release Design

Date: 2026-07-12
Status: Approved for implementation

## Objective

Prepare the project for its first public GitHub repository and release while
finishing the already validated G01/G02 work. The public and internal identity
will be unified under **BoneWeaver** because no compatible public release or
user migration path is required.

## Naming contract

The rename is atomic. No `ue_chain_prep` or `UECP` compatibility package,
operator alias, RNA alias, schema alias, or migration shim will be retained.

| Surface | New identity |
| --- | --- |
| GitHub repository | `BoneWeaver` |
| Blender display name | `BoneWeaver` |
| Extension ID and source directory | `boneweaver` |
| Python package | `boneweaver` |
| Operator namespace | `boneweaver.*` |
| RNA property prefix | `boneweaver_*` |
| Python class prefix | `BONEWEAVER_*` |
| Diagnostic/error prefix | `BONEWEAVER_*` |
| Schema URI prefix | `boneweaver://` |
| Serialized kind prefix | `boneweaver.*` |
| Algorithm version prefix | `boneweaver-` |
| Sidebar category | `BoneWeaver` |
| Distribution archive | `boneweaver-0.2.0.zip` |

The product version remains `0.2.0`, schema remains `4.0.0`, and the release
tag is `v0.2.0`. The identity break is intentional and requires no backwards
compatibility because the extension has not been distributed.

## GitHub presentation

Repository description:

> A safety-first Blender extension for inspecting, validating, and converting
> Unreal Engine bone hierarchies into physics-ready chains for BoneX and Wiggle.

Recommended topics: `blender`, `blender-addon`, `unreal-engine`, `rigging`,
`bones`, `animation`, `physics`, `bonex`, and `wiggle`.

The primary README will be English and link to the complete Chinese README.
Both READMEs will contain the same release facts: product purpose, safety model,
feature overview, installation, quick start, supported Blender versions,
validation evidence, limitations, documentation map, license, and contribution
entry points. Development-only wording will be removed.

The repository will add:

- a GPL-3.0-or-later `LICENSE` matching the Blender extension manifest;
- `CONTRIBUTING.md` with the Blender-hosted test and package commands;
- `SECURITY.md` directing reporters to GitHub's private security-advisory flow
  rather than publishing vulnerability details in an issue;
- GitHub issue templates for bug reports and feature requests;
- a pull-request template with test and safety-contract checks;
- `docs/releases/v0.2.0.md` as the canonical release notes source.

## Release content

Release title: **BoneWeaver v0.2.0 — Initial Public Preview**.

The release notes will lead with the user-visible hierarchy inspection,
three-role overlay, confirmed semantic discovery, safety-first Analyze/Apply
contract, and independent export/reopen validation. They will list Blender
4.2+ support, the tested Blender 5.2 build, the archive name and SHA-256, known
limitations, and installation steps.

The release will contain only `dist/boneweaver-0.2.0.zip`. Obsolete
`ue_chain_prep` archives will not remain in the release-ready tree.

## Git and worktree integration

The root worktree on `feature/semantic-chain-discoverv-v0.1.1` contains
uncommitted user work and will not be modified, reset, staged, or merged.

The release workflow is:

1. commit the validated G01/G02 implementation on
   `feature/g01-g02-completion`;
2. commit the atomic BoneWeaver rename and GitHub/release metadata separately;
3. verify the complete Blender test suite and rebuild/install the renamed ZIP;
4. merge the feature branch into the clean dedicated `main` worktree with a
   non-fast-forward merge;
5. rerun the complete suite and package checks on merged `main`;
6. create the annotated local tag `v0.2.0` only after merged verification;
7. leave push and GitHub Release publication pending until a remote URL exists.

Already merged auxiliary worktrees may be removed after the merge. The dirty
root worktree remains intact. The G01/G02 worktree may be removed only after the
merge, tag, and final evidence checks succeed.

## Verification gates

Completion requires all of the following on the renamed code and again on
merged `main` where applicable:

- no remaining `ue_chain_prep`, `UECP`, or `uecp` identity references outside
  historical release notes that explicitly describe the rename;
- Blender-hosted unit/integration suite passes with zero failures;
- all JSON schemas and rule files parse;
- extension build produces `boneweaver-0.2.0.zip`;
- isolated install and three unregister/register cycles pass;
- real UE asset Analyze, Apply, export, and independent reopen validation pass;
- `git diff --check` passes;
- the generated archive size and SHA-256 match README/release notes;
- final `main` status is clean before tagging.

## Non-goals

- No GitHub repository creation, push, or release publication is attempted
  without a configured remote.
- No compatibility shim for the old internal identity is added.
- No unrelated algorithm or UI behavior is changed during the rename.
- No dirty user work in the root worktree is absorbed into this release.
