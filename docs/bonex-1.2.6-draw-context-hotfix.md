# BoneX 1.2.6 / Blender 5.2 Draw-Context Hotfix

## Problem

BoneX 1.2.6 calls `get_armature_soft_connections()` from its Soft Connection panel `draw()` method. On a newly imported Armature, that getter creates `Object["bonex_data"]` and `soft_connections`. Blender 5.2 rejects ID data writes while drawing UI and reports:

```text
AttributeError: Writing to ID classes in this context is not allowed
```

The failure reproduces with a factory-startup Armature and BoneX alone, without loading BoneWeaver. The same write succeeds outside draw context, so the imported object is not read-only and BONEWEAVER mode/transaction restoration is not the cause.

## Fix design

The supported local hotfix makes the getter read-only:

- Missing `bonex_data` or `soft_connections` returns an empty list.
- BoneX operator/setter code remains responsible for creating persistent data.
- BONEWEAVER runtime does not import, monkey-patch, or initialize BoneX state.
- `tools/patch_bonex_1_2_6.py` refuses versions other than the audited `id=bonex`, `version=1.2.6` source shape.
- Apply creates `utils.py.boneweaver-bonex-1.2.6.bak`; restore refuses to overwrite a source that diverged after patching.

## Commands

```powershell
python tools/patch_bonex_1_2_6.py --check
python tools/patch_bonex_1_2_6.py --apply
python tools/patch_bonex_1_2_6.py --restore
```

Restart Blender after apply or restore because an already-running Blender process retains the previously imported Python module.

## Verified evidence

- Original installed `utils.py` SHA-256: `F293E8BE0FB5EF13965EC669852A9BB8DFE5B14A30A40123E55B7E0B38AF6A1C`.
- Patched installed `utils.py` SHA-256: `8D8A40E6EE52BB1026D026693D77E3C8BF14EA8C616673E29D06B195968887CF`.
- Original real-window probe: `FAIL AttributeError: Writing to ID classes in this context is not allowed`.
- Patched isolated-copy probe: `PASS bonex_data=None`.
- Patched installed-copy probe: `PASS bonex_data=None`.
- Setter/readback probe: one soft connection persisted and read successfully outside draw.
- Automated suite: 61 tests, 0 failures, 0 errors, 0 skipped.

This verifies the UI initialization fault and its local hotfix. BoneX physics generation, playback and bake remain separate interactive manual validation.
