# Existing Tip Helper Classification

BoneWeaver may classify a selected, zero-weight terminal bone as
`EXISTING_TIP_HELPER`. The default `REFERENCE_ONLY` usage preserves that bone as
part of the immutable Physics Graph while excluding it from Blender mutation:

```text
semantic_role = EXISTING_TIP_HELPER
reference_only = true
mutation_target = false
requires_own_tail = false
```

Its deform parent normally receives a Proposal whose tail is the helper head and
whose terminal source is `EXISTING_TIP_HELPER_HEAD`. A scoped manual terminal
override may supersede that parent tail; this does not change the helper's
reference-only classification and never creates a helper Proposal. A connected
helper may only keep the helper-head tail: an override that would move its
connected head is rejected with
`BONEWEAVER_MANUAL_OVERRIDE_CONNECTED_TIP_HELPER`, because Apply may not mutate a
reference-only helper indirectly.

## Conservative eligibility

Automatic classification requires zero effective weight, one deform parent for
which the candidate is the unique direct child, non-zero and plausible
Parent-to-Helper length, acceptable upstream direction, and no dependency issue.
The candidate must have no child except an explicitly excluded Socket/Control
child. `end`, `tip`, `terminal`, `dummy`, `nub`, and `末端` are weak positive
evidence only.

IK, FK, control, pole, target, effector, socket, attachment, weapon, muzzle,
camera, twist, roll, and corrective evidence prevents classification. Socket
metadata, constraints, drivers, and bone-parented object dependencies are
stronger than names.

## Audit and export contract

Schema 4 records every classification in the Conversion Plan, diagnostic report,
Snapshot, and export manifest. Snapshot and manifest records freeze helper head,
tail, roll, connection state, parent, and the parent Proposal source. The
topology ledger conserves selected bones as mutation targets, reference-only Tip
Helpers, and explicitly skipped bones.

Independent reopen validation requires the manifest and Snapshot classifications
to agree, checks the four PhysicsNode semantic flags, verifies unchanged helper
geometry, rejects any helper MutationRecord, and checks ledger conservation.
Parent-to-helper continuity is required only when the recorded parent terminal
source remains `EXISTING_TIP_HELPER_HEAD`; a `MANUAL_OVERRIDE` is validated
against its own frozen expected post-state.

## Explicit visual-cleanup inclusion

`INCLUDE_AS_PHYSICS_TERMINAL` is restricted to the explicit
`VISUAL_CHAIN_CLEANUP` profile. A classified Helper is eligible only when it has
no excluded child. Eligible Helpers freeze these Graph flags instead:

```text
semantic_role = EXISTING_TIP_HELPER
reference_only = false
mutation_target = true
requires_own_tail = true
```

The Helper then receives its own Proposal using safe parent extrapolation (or a
manual terminal only when extrapolation cannot be proven safe). Its original
geometry remains in the audit record, while Snapshot expected-post state,
mutation records, export readiness, and reopen validation audit the explicit
mutation. Unsafe Helpers remain reference-only and produce a Blocker.
