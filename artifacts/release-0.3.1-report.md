# BoneWeaver v0.3.1 Release Validation

Date: 2026-07-13

## Force-complete regression

- Result: `FINISHED`; runtime state: `RESTORABLE`; Quick blocker count: `0`
- Combined conditions: active Action, NLA track, Driver, non-identity Pose,
  PoseBone Constraint, object Constraint, B-Bone segments, Bone-parented object,
  envelope deformation, duplicate Armature modifiers, and shared Armature data
- Shared data was made single-user automatically.
- Eleven advisory/diagnostic conditions were recorded without preventing the
  four-bone conversion or exact Restore.
- A deliberately failed custom diagnostic also committed successfully when
  `strict_validation=False`; strict direct-call mode still rolled back.

## Automated Blender suite

- Runtime: Blender 5.2.0 LTS Release Candidate, build `710df102694f`
- Result: `BONEWEAVER_TEST_RESULT run=223 failures=0 errors=0 skipped=0`

## Real assets

- Raw `.uemodel`: 157 total, 155 processed, 2 Socket bones, 151 first-run
  mutations, 56 components, 92 connections, zero second-run mutations.
- Existing `x1.blend`: 157 total, 155 processed, 2 Socket bones, 106 first-run
  mutations, 56 components, 92 connections, zero second-run mutations.
- Finger, hair, ribbon, and spine native `L` selection passed on both.
- Exact Restore passed and both source SHA-256 values remained unchanged.

## Package

- Isolated install: `BONEWEAVER_ZIP_INSTALL_OK`
- Repeated unregister/register cycles: passed
- File: `boneweaver-0.3.1.zip`
- Size: `186108` bytes
- SHA-256: `1FDFBA24BD878E07EA3FC194D8D8477F8FD6765B0FD5093154A006BDFD660987`
