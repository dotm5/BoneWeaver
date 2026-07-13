# BoneWeaver v0.3.0 Release Validation

Date: 2026-07-13

## Automated Blender suite

- Runtime: Blender 5.2.0 LTS Release Candidate, build `710df102694f`
- Result: `BONEWEAVER_TEST_RESULT run=220 failures=0 errors=0 skipped=0`

## Fixed UEFormat parity

- UEFormat: 1.0.0, GPL-3.0-or-later
- Audited commit: `8da96d65f669ca688dbf7c0141f800605a6c16e6`
- Fixture: `SK_HuiXing_Lobby_S111.uemodel`
- Comparable bones: 154; Socket bones: 2
- Maximum direction error: `0.033878443821242374°`
- Maximum length error: `1.1644113720454818e-7`
- Maximum Head error: `0`; maximum Socket error: `0`; parent differences: none
- Native linked-chain reconstruction was disabled only for this Stage-A numeric
  comparison and validated separately below.

## Real one-click acceptance

Raw `.uemodel`:

- Source SHA-256:
  `0F86151756598E2B8E85419AFAD08B4FDAF1DBE05BD38C2CC646B5300EE50940`
- Armature: 157 total bones, 155 processed, 2 Socket bones
- First run: 151 bone mutations, 56 native components, 92 connected edges
- Second run: zero additional mutations
- Native `L` selection: finger, hair, ribbon, and spine checks passed
- Exact Restore passed; source SHA-256 remained unchanged

Existing `x1.blend`:

- Source SHA-256:
  `8DFAD9ABADE8D6CA4DF08A18FB7FDA68E9FF260E297A34AD17BC3EDAC927BFB6`
- Armature: 157 total bones, 155 processed, 2 Socket bones
- Source adapter: `UEFORMAT_ALREADY_REORIENTED`
- First run: 106 bone mutations, 56 native components, 92 connected edges
- Second run: zero additional mutations
- Native `L` selection and exact Restore passed; source hash remained unchanged

Both assets reported seven pre-existing zero-length-bone warnings; those bones
were skipped and did not block the safe transaction.

## Packaged extension

- Isolated install: `BONEWEAVER_ZIP_INSTALL_OK`
- Repeated unregister/register cycles: passed
- File: `boneweaver-0.3.0.zip`
- Size: `185592` bytes
- SHA-256: `4FA71A1F71640047D10F03E023DB03EB89126D6DEF8353BBCB93D9989E2B23C2`
