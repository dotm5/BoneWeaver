# BoneWeaver v0.2.0 Release Validation

Date: 2026-07-12

## Automated Blender suite

- Runtime: Blender 5.2.0 LTS Release Candidate, build `710df102694f`
- Result: `BONEWEAVER_TEST_RESULT run=208 failures=0 errors=0 skipped=0`

## Real UE asset acceptance

- Source: `SK_HuiXing_Lobby_S111.uemodel`
- Source SHA-256: `0F86151756598E2B8E85419AFAD08B4FDAF1DBE05BD38C2CC646B5300EE50940`
- Armature: 157 bones
- Mesh: 25,610 vertices
- Result: `BONEWEAVER_G01_G02_REAL_RESULT PASS`
- Analyze, Apply, export, source-integrity, packed-image, and independent reopen
  validation passed.
- Reopen checked 4 mutation targets and 3 linear edges with no issues; weight,
  base-mesh, and modifier digests remained unchanged.

## Packaged extension

- Isolated install: `BONEWEAVER_ZIP_INSTALL_OK`
- Repeated unregister/register cycles: passed
- File: `boneweaver-0.2.0.zip`
- Size: `170163` bytes
- SHA-256: `5F4B3F91B2A5BB59D10469F0BDF5263B9B1EDE44BE5055990DA89CF80BC1C48F`

## Interactive evidence

The G01/G02 acceptance baseline includes real-window viewport validation for
finger hierarchy selection (one selected bone to three) and explicit branch
continuation. The automated real-asset run independently confirmed that
inspection and semantic discovery left selection and geometry unchanged until a
named selection/use action.
