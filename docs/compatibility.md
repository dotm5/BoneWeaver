# Compatibility

| Target | Status |
|---|---|
| Blender 5.2.0 LTS RC `710df102694f` | 0.1.3 baseline was validated; Schema-4/G02 development changes require a fresh automated, transaction, real-asset, viewport and ZIP run |
| Blender 4.2 | Manifest minimum; executable unavailable locally, external validation pending |
| Blender 5.1 | Executable unavailable locally, external validation pending |
| UEFormat 1.0.0 | Factory-startup isolated-copy import verified |
| BoneX 1.2.6 | Blender 5.2 draw-context fault reproduced and reversible local hotfix verified; physics behavior remains manual |
| Wiggle 2 RTX 2.2.5 | Installed locally; manual physics behavior must be recorded separately |
| Auto-Rig Pro 3.78.22 | Installed locally; post-conversion rig workflow remains manual |

Compatibility code uses feature detection for Action APIs and Blender 5.2's `PoseBone.select` migration rather than relying only on version comparisons.

UECP runtime does not mutate BoneX state. The separately invoked support tool and rollback procedure are documented in [BoneX 1.2.6 draw-context hotfix](bonex-1.2.6-draw-context-hotfix.md).

Schema 3.1 added optional branch, tolerance, mutation, topology, and export records. Schema 4.0 makes PhysicsNode semantic flags, Existing Tip Helper classifications, mutation-target/reference-only counts, and their export/reopen audit records required for newly generated artifacts. It also requires the stable Weight Island policy and Tip Helper usage in Settings. This is a Schema Major change; the corresponding algorithm version is `uecp-physics-graph-v4-tip-helper-branch-island-visual-cleanup`, so older Plans become stale.

Old snapshots remain restorable. Restore and snapshot discovery continue to read the original pre-state and expected-post fields without rejecting a Snapshot solely because it predates Schema 4. New export and independent-reopen guarantees apply only to newly generated Schema 4 artifacts; legacy Snapshots do not fabricate Tip Helper classifications or ledger counts.

Compatibility results recorded before the Schema-4/G02 changes are historical
baselines, not proof for the current development tree. Fresh results must be
recorded after testing is authorized.
