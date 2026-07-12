# G01 / G02 Real Asset Regression

Date: 2026-07-12
Runner: `tools/run_g01_g02_real_acceptance.py`

## Input

- Asset: `D:\项目复现\BoneWeaver\test\SK_HuiXing_Lobby_S111.uemodel`
- SHA-256: `0f86151756598e2b8e85419afad08b4fdaf1dbe05bd38c2cc646b5300ee50940`
- Armature: `SK_HuiXing_Lobby_S111_LOD0_Skeleton`
- Bones: 157
- Mesh vertices: 25,610
- UEFormat was copied to an isolated test directory; the original asset was
  opened read-only and never overwritten.

## G02 discovery and hierarchy

- Semantic candidates: 22 (`0 AUTO_INCLUDE`, `12 SUGGEST_INCLUDE`,
  `10 AMBIGUOUS`).
- Hair roots found: `hair_f_l_01`, `hair_f_m_01`, `hair_f_r_01`, `hair_l_01`,
  `hair_r_01`, `hair_up_l_01`, `hair_up_r_01`.
- Main-skeleton AUTO/SUGGEST candidates: 0.
- Finger linear chain: `Bip001-L-Finger0`, `Bip001-L-Finger01`,
  `Bip001-L-Finger02`; parent context `Bip001-L-Hand`.
- Spine linear inspection stops at `Bip001-Spine`; side roots are
  `Bip001-Spine1` and `NekoBotHit`.
- Discovery and inspection did not modify geometry, weights, or selection.

## G01 conversion

- Target: `hair_l_01..hair_l_04`.
- Analyze: FINISHED; Apply: FINISHED; Export: FINISHED.
- Target bones / mutation targets: 4 / 4.
- Existing Tip Helpers: 0; safe ordinary-leaf fallbacks: 1; manual terminal
  overrides: 0; branch resolutions: 0.
- Proposals / mutation records: 4 / 4; non-target changes: 0.
- Per-mesh tolerance (`SK_HuiXing_Lobby_S111_LOD0`):
  `AUTO_PRODUCTION`, soft `9.5367431640625e-07`, hard
  `3.814697265625e-06`, result `PASS`.
- Maximum evaluated-mesh delta: `1.38388392485728e-07`.
- RMS delta: `9.6581166636274e-09`.
- Analyze time: 17.329 s; mesh scan: 17.097 s; Apply: 3.045 s.
- Peak temporary memory: 1,502,932 bytes; `tracemalloc` peak: 2,253,800 bytes.
- Source `.blend` signature unchanged.
- Overall result: **PASS**.

Machine-readable evidence:
`test-output/g01-g02-real-acceptance/real-acceptance.json` and
`conversion-audit.json`.
