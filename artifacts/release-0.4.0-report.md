# BoneWeaver v0.4.0 Release Validation

Date: 2026-07-26

## Three automatic modes

- Original: whole-Armature UEFormat-compatible reorientation and native
  linear-chain rebuilding.
- Links only: whole-Armature native linear-chain rebuilding without direction
  inference.
- Experimental hybrid: confident multi-feature result per bone, with a
  precomputed UEFormat-compatible fallback retained for every unresolved bone.
- All three operators are immediate actions with no confirmation dialog.
- Runtime blocker count remains zero in all three force-complete paths.
- Injected non-finite single-bone output and a complete precision-planner
  exception both completed by automatic fallback.

## Automated Blender suite

- Runtime: Blender 5.2.0 LTS, build `fbe6228777e7`
- Result: `BONEWEAVER_SUITE_COUNTS 230 0 0 0`

## Existing x1.blend

- Source SHA-256 before and after:
  `47AA427921B38B88D0CF98DFD102287D07EC5AFA50C8DD107880A82235B598BC`
- Total bones: 157; processed: 155; Socket bones: 2; components: 56;
  native connections: 92.
- Original: 106 first-run mutations; zero second-run mutations.
- Links only: 106 first-run mutations; zero second-run mutations.
- Hybrid: 108 first-run mutations; 94 multi-feature bones; 61 automatic
  UEFormat fallbacks; zero second-run mutations.
- Finger, hair, ribbon, and spine native `L` selection passed in every mode.
- Exact Restore passed in every mode.

## Raw UEFormat import

- Source: `SK_HuiXing_Lobby_S111.uemodel`
- Source SHA-256 before and after:
  `0F86151756598E2B8E85419AFAD08B4FDAF1DBE05BD38C2CC646B5300EE50940`
- Factory-startup import used the isolated UEFormat 1.0.0 package.
- Total bones: 157; processed: 155; Socket bones: 2; components: 56;
  native connections: 92.
- Original: 151 first-run mutations; zero second-run mutations.
- Links only: 134 first-run mutations; zero second-run mutations.
- Hybrid: 151 first-run mutations; 94 multi-feature bones; 61 automatic
  UEFormat fallbacks; zero second-run mutations.
- Finger, hair, ribbon, and spine native `L` selection passed in every mode.
- Exact Restore passed in every mode.

## Original versus experimental hybrid

- A direct final-state comparison was run on both real-asset paths after applying
  each plan independently and restoring the source state between runs.
- Hybrid routed 94 bones through confident multi-feature proposals and retained
  61 per-bone fallbacks. All 61 fallback results exactly matched Original.
- Both modes produced the same hierarchy, heads, parents, and 92 native
  connections. Only three of 155 eligible bones ended in a different geometric
  state:
  - `ik_hand_root`: direction changed by `22.395577` degrees; length was
    unchanged. Roll differed by `22.395584` degrees on `x1.blend` and
    `67.579975` degrees after raw import.
  - `Bip001-R-ForeTwist`: length changed from approximately `0.04` to `0.08`;
    direction changed by `0.387922` degrees on `x1.blend` and `0.509101`
    degrees after raw import.
  - `bag_r_03`: length changed from approximately `0.058266` to `0.066396`;
    direction remained effectively unchanged.
- The precision planner reported 87 blocker-class diagnostics on each asset.
  Hybrid converted them to advisory evidence, completed with zero blockers, and
  used fallback wherever recognition was not accepted.
- Observed background-run time was `1.272 s` Original versus `2.258 s` Hybrid
  on `x1.blend`, and `1.244 s` versus `2.168 s` after raw import.
- These measurements establish automation and fallback equivalence, not general
  superiority of the experimental output. Hybrid remains explicitly
  experimental; Original remains the stable default and Links only remains the
  safest choice for already well-oriented rigs.

## Package

- Isolated install: `BONEWEAVER_ZIP_INSTALL_OK`
- Installed package exposed all three top-level operator classes.
- Repeated unregister/register cycles: passed
- File: `boneweaver-0.4.0.zip`
- Size: `190353` bytes
- SHA-256: `A68C65050DAFE9DC91A53C0F9DA91C4610EBC343F153D0F21DC540C0A1E4E709`
