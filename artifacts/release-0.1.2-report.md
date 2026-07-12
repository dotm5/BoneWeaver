# BoneWeaver 0.1.2 Release Verification

Date: 2026-07-12 (Asia/Shanghai)

## Release identity

- Add-on version: `0.1.2`
- Schema version: `3.1.0`
- Algorithm version: `boneweaver-physics-graph-v3-interaction-hardening`
- Blender: 5.2.0 LTS Release Candidate, hash `710df102694f`

## Automated verification

- Full Blender-hosted unittest suite: 168 run, 0 failures, 0 errors, 0 skipped.
- Focused version-contract RED phase: contract and manifest tests each failed because production metadata was still `0.1.0`.
- Focused version-contract GREEN phase: 8 tests passed after updating production metadata to `0.1.2`.

## Real model verification

The read-only source `C:\Users\70560\Documents\Blender项目\x1.blend` completed Analyze, Apply, conversion export, and independent reopen validation with 85 target bones, 0 blockers, 85 proposals, and 85 mutation records. The exported manifest recorded add-on version `0.1.2`; reopen validation reported success. Source SHA-256 and timestamp were unchanged.

- Source SHA-256: `998B92001E76A169E6E17D55F08E1CD606EDA8034D7EB95F7ACC57FC66464DA1`

## Package verification

- Archive: `dist/boneweaver-0.1.2.zip`
- Size: 97,807 bytes
- SHA-256: `968FE9885E11D6C5E47CCF89E48D916D513DF733CFF6E365E82D501BF7B326AA`
- Isolated Blender extension install: passed.
- Three register/unregister cycles after installation: passed with no leaked `Scene.boneweaver_settings` RNA property.
