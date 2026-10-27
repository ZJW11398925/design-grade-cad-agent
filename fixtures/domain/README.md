# Domain Slice Fixtures

`domain-slice-001.yaml` is the first **human-confirmed, synthetic** trace fixture for the Building/Road domain slice.

- `synthetic_only: true`
- `human_confirmed_trace: true`
- coordinate frame: `LOCAL-ENU-XY-ZUP`, units: metre
- no georeference and no real-world evidence claim

## Intentional difficulty cases

| Object | Case |
|---|---|
| `B-001` | axis-aligned rectangle, height confirmed at 18 m |
| `B-002` | slightly irregular footprint, height **unknown** |
| `B-003` | intentionally rotated 17°, height confirmed at 12 m |
| `R-001` | main corridor with **unknown road class** and no profile |
| `R-002` | secondary corridor with a confirmed class and explicit user-specified 6 m cross-section |
| `RN-003` | T-junction shared by three edges |

These cases exist to prove that unknown values survive from trace to canonical state and are not silently defaulted.

## Immutability

Do not edit this fixture in place once it is used as evidence. Add a new revision (`domain-slice-002.yaml`) and keep this file for regression comparison.
