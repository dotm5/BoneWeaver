# Preview and Issue Visibility Fix Design

## Problem

The 0.1.2 viewport preview is unreadable in Blender 5.2: every two-pixel graph line expands into a large blue or orange strip that covers the rig. The issue list simultaneously renders repeated truncated technical codes, so a user cannot identify the affected bone.

The screenshot and code inspection establish two independent causes:

- `POLYLINE_UNIFORM_COLOR` receives a hard-coded `viewportSize=(1, 1)` instead of the active GPU viewport dimensions.
- `BONEWEAVER_UL_issues` renders only `item.message`; ambiguous terminal issues use the raw error code as their message even though `item.bone_name` is already populated.

The real `x1.blend` armature has an identity world matrix, so local/world coordinate conversion is not the cause of the reported screenshot.

## Design

### Viewport preview

At draw time, read `gpu.state.viewport_get()` and send its width and height to the polyline shader. Clamp each dimension to at least one so minimized or transitional regions remain safe. Keep the frozen line cache and cached GPU batches unchanged; no planning work or batch construction may occur per frame.

### Issue presentation

Add a pure UI presenter that maps the common ambiguous terminal and branch codes to short Chinese explanations. Each list row begins with the affected bone name, followed by the friendly explanation. If an issue has a useful non-code message, preserve it. If it has no bone, show the explanation alone. Technical codes remain in diagnostics and exported reports rather than occupying the primary list label.

The locate button will include the selected bone name in its visible label and continue to use the existing explicit click-to-select-and-focus behavior. Selecting a list row alone will not mutate Blender selection.

### Release identity

Do not rewrite the immutable `v0.1.2` tag. Update add-on and manifest version to `0.1.3`, retain the 0.1.2 archive, and add a 0.1.3 archive and changelog entry.

## Validation

- Regression-test the exact shader uniform call with a fake 1920x1080 viewport.
- Regression-test list rendering for `hair_ribbon_l_06` plus `BONEWEAVER_TERMINAL_CANDIDATE_AMBIGUOUS`.
- Regression-test the bone-specific locate label and 0.1.3 version contracts.
- Run the complete Blender-hosted unittest suite.
- Run the 85-bone `x1.blend` Analyze, Apply, Export, and independent reopen pipeline.
- Build and install the 0.1.3 ZIP in an isolated Blender user directory.
- With Computer Use, install/open the fixed extension in interactive Blender, run the user-facing workflow, inspect the normal-width overlay, load issue details, select an issue, click the bone-specific locate action, and save screenshots.

## Non-goals

- No scoring, terminal-resolution, graph, apply, or export algorithm changes.
- No automatic focus when merely changing the issue-list selection.
- No change to which analyzed graph edges are included in the global preview.

