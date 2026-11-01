# BoneWeaver v0.4.1 Release Validation

## Baseline and source boundary

- Release worktree branch: `feature/v0.4.1-animation-compat`
- Baseline and merge-base: `05385581bc6931c650ee24e826c57a701e505ac7`
  (`origin/main`, tagged v0.4.0)
- Build source: `boneweaver`
- The dirty root branch `feature/quick-reorient-linked-chains` remained on
  `349a3b5b1c824fb9a631d69f3c390b2a3648c783`.
- No source was copied from `ue_chain_prep` by global identity replacement.

## Retained automatic modes

- `boneweaver.quick_reorient_auto`
- `boneweaver.quick_reorient_links_only`
- `boneweaver.quick_reorient_hybrid_auto`

Hybrid still computes a UEFormat fallback for every eligible bone, then accepts
only reliable multi-feature proposals per bone.

## Animation and rest-basis validation

- Existing animation-basis checks adapted in memory to the formal package:
  `5/5` passed without creating a test file.
- Parent-local rest-basis delta and cumulative UEFormat `post_quat`: passed.
- Safe Active Action sampling/rebase: passed.
- Quick and scoped Apply Action/metadata Restore: exact.
- Animated Quick Original, Links Only, and Hybrid transaction probe:
  - second execution: `0` mutations in every mode;
  - connected topology preserved in every mode;
  - exact double-snapshot Restore in every mode;
  - maximum sampled pose-matrix error: `2.092068882575404e-07`.
- Pre-mutation blockers passed for active NLA strips, pose-bone Drivers,
  effective pose constraints, shared Actions, unsupported paths, and unsupported
  pose properties. An empty Action used the explicit no-pose-curves Quick
  fallback.

## Blender regression suite

- Blender: 5.2.0 LTS, build `fbe6228777e7`
- Command: `blender --background --factory-startup --python tests/run_blender_tests.py`
- Result: `230` run, `0` failures, `0` errors, `0` skipped.

## Real assets

Each mode was run independently with second-run idempotence, double Restore,
native `L` checks for finger/hair/ribbon/spine, and source hashing.

### `x1.blend`

- SHA-256 before/after:
  `47AA427921B38B88D0CF98DFD102287D07EC5AFA50C8DD107880A82235B598BC`
- Original: PASS, first mutations `106`, second mutations `0`.
- Links Only: PASS, first mutations `106`, second mutations `0`.
- Hybrid: PASS, first mutations `108`, second mutations `0`.
- Hybrid sources: `94` multi-feature, `61` UEFormat fallback.

### `SK_HuiXing_Lobby_S111.uemodel`

- Bone count: `157`
- SHA-256 before/after:
  `0F86151756598E2B8E85419AFAD08B4FDAF1DBE05BD38C2CC646B5300EE50940`
- Original: PASS, first mutations `151`, second mutations `0`.
- Links Only: PASS, first mutations `134`, second mutations `0`.
- Hybrid: PASS, first mutations `151`, second mutations `0`.
- Hybrid sources: `94` multi-feature, `61` UEFormat fallback.

## Package

- Build command:
  `blender --factory-startup --command extension build --source-dir boneweaver --output-dir dist`
- File: `dist/boneweaver-0.4.1.zip`
- Size: `200097` bytes
- SHA-256:
  `7D5160229B8FA33D9C29B36D53BC8A8903B88ACD1F3C72434B5D524D94CEB059`
- Archive contains `core/animation_basis.py` and
  `core/hybrid_reorient.py`; it contains no `ue_chain_prep`, `.pyc`, or
  `__pycache__` entries.
- Isolated `BLENDER_USER_RESOURCES` installation passed and exposed all three
  operator classes; three unregister/register cycles passed.
- The pre-existing root-worktree `dist/boneweaver-0.4.1.zip` was not overwritten
  or used. No v0.4.0 or ue_chain_prep v0.3.0 archive was rebuilt or delivered.
- No remote v0.4.1 tag or GitHub Release is claimed.
