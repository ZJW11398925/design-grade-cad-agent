# R1.0 Foundation Contract Test Matrix v0.1

| Contract | Failure that must be caught | Gate |
|---|---|---|
| Stable ID | parameter update creates a new object identity | G01 |
| Exact revision precondition | stale proposal commits over newer state | G01/G03 |
| Atomic ChangeSet | first object commits while second fails | G02/G03 |
| Human confirmation | design-intent change auto-commits | G02 |
| Lock/unlock | locked redline changes without explicit unlock | G02 |
| Preview isolation | preview changes canonical current | G06 |
| External isolation | CAD/IFC import overwrites canonical directly | G01/G02 |
| Local stale | one parameter change marks unrelated artifacts stale | G03 |
| Structured validation | validator crashes or returns opaque exception-only result | G04/G05 support |
| Fixture versioning | a test fixture has no schema/version identity | all |

No numeric geometry threshold is introduced at Foundation level.
