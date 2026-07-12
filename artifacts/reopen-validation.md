# Independent Reopen Validation

Date: 2026-07-12
Converted file: `test-output/g01-g02-real-acceptance/converted.blend`

The export controller launched a second Blender process to reopen the saved
conversion copy and validate the embedded manifest independently.

| Check | Result |
| --- | --- |
| Reopen process | PASS |
| Checked mutation targets | 4 |
| Mutation records / manifest records | 4 / 4 |
| Linear hierarchy edges | 3 |
| Topology ledger conserved | yes |
| Snapshot conflict check | ran |
| Base mesh digest changes | 0 |
| Weight digest changes | 0 |
| Modifier digest changes | 0 |
| Packed images expected / reopened | 1 / 1 |
| Issues | none |

The source `.blend` remained unchanged. Machine-readable evidence is
`test-output/g01-g02-real-acceptance/reopen-validation.json`.
