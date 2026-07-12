# Contributing to BoneWeaver

Thank you for helping improve BoneWeaver. Keep changes narrow, deterministic,
and consistent with the safety contract in `docs/safety.md`.

## Development requirements

- Blender 4.2 or newer; the current release baseline uses Blender 5.2.
- Python code must run inside Blender without external package dependencies.
- Changes to serialized data require an explicit schema/version review.
- Any new mutation must be represented in the frozen plan and mutation ledger.

## Required verification

Before opening a pull request:

1. Run the complete Blender-hosted suite:

   ```powershell
   & 'C:\Path\To\blender.exe' --background --factory-startup `
     --python tests\run_blender_tests.py
   ```

2. Run `git diff --check`.
3. Build the extension:

   ```powershell
   & 'C:\Path\To\blender.exe' --factory-startup --command extension build `
     --source-dir boneweaver --output-dir dist
   ```

4. Install the resulting ZIP into a fresh `BLENDER_USER_RESOURCES` directory
   and run `tests/test_install_zip.py`.
5. For Apply, export, hierarchy, overlay, or semantic-discovery changes, attach
   relevant real-asset or interactive Blender evidence.

## Pull requests

Explain the user workflow, safety impact, test evidence, schema/version impact,
and release-note impact. Do not include copyrighted test assets or private
`.blend` files in commits.
