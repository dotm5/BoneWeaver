# Export Contract

Conversion export is distinct from diagnostic-report export. `assert_export_ready` requires a current Plan, successful RESTORABLE Apply, persistent applied Snapshot, non-empty actual mutations, zero non-target/digest changes, passing per-mesh neutral validation, complete topology accounting, resolved branches, and no blockers. Schema 4 additionally requires Snapshot classifications and counts to match the frozen Plan: selected bones equal mutation targets plus reference-only Tip Helpers plus explicitly skipped bones, and no reference-only Tip Helper may appear in the mutation ledger.

Failure occurs before Pack and Save. Success packs resources, writes `UECP_EXPORT_MANIFEST`, saves a copy, verifies the source SHA-256 and timestamp, writes `conversion-audit.json`, then launches a second Blender process. The manifest explicitly lists `selected_bones`, `mutation_targets`, `reference_only_tip_helpers`, full Tip Helper audit records, PhysicsNode semantic flags, and the topology ledger. The second process checks rest geometry, mutation ledger, branch main/side state, linear continuity, Tip Helper classification and unchanged geometry, ledger conservation, mesh and modifier digests, packed-image count, and snapshot conflict-readiness. It writes `reopen-validation.json`.

Immediately before Pack/Save, the gate recomputes the settings fingerprint and
checks the complete armature rest-state snapshot (including non-target Roll),
the applicable neutral pose scope, Armature and Mesh object transforms, Mesh to
Armature relationships, and current weight/base-mesh/modifier digests. The
independent reopen process repeats the tolerant whole-armature and transform
checks; it does not rely only on the historical post-Apply result.

A failed reopen leaves the copy and diagnostics for investigation but the export operation returns failure and must not be reported as successful.

For `VISUAL_CHAIN_CLEANUP`, the Plan, Snapshot, diagnostic report, and export
manifest also freeze `tip_helper_usage`. Reference-only helpers remain subject
to unchanged-geometry checks. A safely and explicitly included helper instead
appears in `mutation_targets`; its parent/head identity remains fixed while its
post tail, Roll, and Connect state are validated through `expected_post_bones`,
the mutation ledger, and independent reopen checks.
