# Export Contract

Conversion export is distinct from diagnostic-report export. `assert_export_ready` requires a current Plan, successful RESTORABLE Apply, persistent applied Snapshot, non-empty actual mutations, zero non-target/digest changes, passing per-mesh neutral validation, complete topology accounting, resolved branches, and no blockers.

Failure occurs before Pack and Save. Success packs resources, writes `UECP_EXPORT_MANIFEST`, saves a copy, verifies the source SHA-256 and timestamp, writes `conversion-audit.json`, then launches a second Blender process. The second process checks rest geometry, mutation ledger, branch main/side state, linear continuity, mesh and modifier digests, packed-image count, and snapshot conflict-readiness. It writes `reopen-validation.json`.

A failed reopen leaves the copy and diagnostics for investigation but the export operation returns failure and must not be reported as successful.
