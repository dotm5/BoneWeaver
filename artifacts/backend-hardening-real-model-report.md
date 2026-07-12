# BoneWeaver Backend Hardening Real Model Report

## Asset

- Source: `C:\Users\70560\Documents\Blender项目\x1.blend`
- Source SHA-256 before/after: `998b92001e76a169e6e17d55f08e1cd606eda8034d7eb95f7acc57fc66464da1`
- Source timestamp before/after: unchanged
- Blender: 5.2.0 LTS RC `710df102694f`
- Algorithm: `boneweaver-physics-graph-v2-backend-hardening`
- Schema: 3.1.0
- Target rule: `bag_`, `chest_`, `cloak_`, `earring_`, `hair_`, `part_`, `ribbon_`
- Target bones: 85

## Result

- Analyze blockers: 0
- Warnings: 82 (`BONEWEAVER_DISCONNECTED_WEIGHT_ISLANDS`: 59; `BONEWEAVER_TERMINAL_SAFE_FALLBACK_USED`: 23)
- Auto confident terminals: 0
- Auto safe fallback terminals: 23
- Manual terminals: 0
- Unresolved terminals: 0
- Proposals: 85
- Mutation records: 85
- Non-target Bone changes: 0
- Weight/Base Mesh/Modifier digest changes: 0/0/0

## Branch Resolution

| Branch | Selected Main Child | Score | Margin | Side Roots | Result |
|---|---|---:|---:|---|---|
| `bag_r_03` | `bag_r_04` | 1.000000 | 0.847871 | `bag_r_03a_01` | HIGH |
| `ribbon_leg_l_b_03` | `ribbon_leg_l_b_04` | 0.999479 | 0.412047 | `ribbon_leg_l_b_03a_01`, `ribbon_leg_l_b_03b_01` | HIGH |

The bag side candidate scored 0.152129. Ribbon side candidates scored 0.587432 and 0.172830. Full candidate fields are preserved in `test-output/backend-hardening-real-model/real-run.json`.

## Neutral Validation

| Mesh | Space | Scale | Soft | Hard | Max | RMS | Soft/Hard Outliers | Result |
|---|---|---:|---:|---:|---:|---:|---:|---|
| `SK_HuiXing_Lobby_S111_LOD0` | evaluated object-local | 2.081384 | 9.536743e-7 | 3.814697e-6 | 4.768381e-7 | 7.418687e-8 | 0 / 0 | PASS |

No-op baseline max/RMS were both zero. Float32 ULP budget was `9.536743e-7`. Recommended relative factor for the observed maximum was `2.863707e-7`; it was diagnostic only and no retry occurred.

## Topology Ledger

- Selected hierarchy edges: 65
- Linear edges: 60
- Branch edges: 5
- Branch nodes: 2
- Resolved/unresolved branches: 2/0
- Virtual tips: 23
- External child edges: 0
- Skipped by design: 0
- Proposal/mutation counts: 85/85

## Output

- Converted copy: `test-output/backend-hardening-real-model/x1-boneweaver-converted.blend`
- Manifest: `test-output/backend-hardening-real-model/conversion-audit.json`
- Reopen report: `test-output/backend-hardening-real-model/reopen-validation.json`
- Full run data: `test-output/backend-hardening-real-model/real-run.json`
