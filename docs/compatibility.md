# Compatibility

| Target | Status |
|---|---|
| Blender 5.2.0 LTS RC `710df102694f` | v0.3.1 validated with 223 automated tests, combined former-blocker force-complete coverage, fixed UEFormat parity, raw `.uemodel` and existing `.blend` one-click/native-`L` acceptance, exact Restore, and isolated ZIP installation |
| Blender 4.2 | Manifest minimum; executable unavailable locally, external validation pending |
| Blender 5.1 | Executable unavailable locally, external validation pending |
| UEFormat 1.0.0 | Factory-startup import verified; Quick Reorient compared against fixed commit `8da96d65f669ca688dbf7c0141f800605a6c16e6` across 154 eligible bones |
| BoneX 1.2.6 | Blender 5.2 draw-context fault reproduced and reversible local hotfix verified; physics behavior remains manual |
| Wiggle 2 RTX 2.2.5 | Installed locally; manual physics behavior must be recorded separately |
| Auto-Rig Pro 3.78.22 | Installed locally; post-conversion rig workflow remains manual |

Compatibility code uses feature detection for Action APIs and Blender 5.2's `PoseBone.select` migration rather than relying only on version comparisons.

BONEWEAVER runtime does not mutate BoneX state. The separately invoked support tool and rollback procedure are documented in [BoneX 1.2.6 draw-context hotfix](bonex-1.2.6-draw-context-hotfix.md).

Schema 3.1 added optional branch, tolerance, mutation, topology, and export records. Schema 4.0 makes PhysicsNode semantic flags, Existing Tip Helper classifications, mutation-target/reference-only counts, and their export/reopen audit records required for newly generated artifacts. It also requires the stable Weight Island policy and Tip Helper usage in Settings. This is a Schema Major change; the corresponding algorithm version is `boneweaver-physics-graph-v4-tip-helper-branch-island-visual-cleanup`, so older Plans become stale.

v0.2.0 is the first public BoneWeaver release and intentionally uses a clean
runtime identity. Plans and snapshots created under pre-release package names are
not discovered automatically. Schema-4 BoneWeaver snapshots remain restorable;
new export and independent-reopen guarantees apply to newly generated Schema-4
artifacts.

The v0.2.0 evidence is recorded in `artifacts/release-0.2.0-report.md` and the
canonical release notes. Blender 4.2 and 5.1 still require external executable
coverage because those runtimes are not available in the local validation setup.

v0.3.0 adds a separate Quick Reorient Plan/Snapshot Schema 1.0.0 and algorithm
identity. Its idempotence marker makes an unchanged converted Armature a safe
zero-mutation second run. It does not rewrite UEFormat `post_quat` animation
metadata. Release evidence is recorded in
`artifacts/release-0.3.0-report.md` and `docs/releases/v0.3.0.md`.

v0.3.1 keeps the same geometry algorithm and Schema while changing the public
one-click execution policy to force-complete. Existing 0.3.0 idempotence markers
remain valid, so upgrading does not reorient an unchanged converted Armature a
second time. Evidence is recorded in `artifacts/release-0.3.1-report.md` and
`docs/releases/v0.3.1.md`.
