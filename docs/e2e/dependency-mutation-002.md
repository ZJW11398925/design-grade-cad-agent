# E2E-002 — Dependency & Mutation Rebuild

Status: implemented (synthetic scope)
Version: 0.4.0
Date: 2026-10-27

## Purpose

Verify that design mutations produce **scoped** staleness, that rebuild jobs actually recompute, write and validate artifacts, and that old/new delivery is compared by identity/revision/dependency — not only by file hash.

## Executed result

Bootstrap (before any mutation) rebuilds 6 artifacts and leaves all current:

```text
MASS-B-001, MASS-B-003, PLAN-B-001, SHADOW-E2E-002, CAD-IR-E2E-002, DXF-E2E-002
```

### 1. B-001 height 18 m → 24 m

| Check | Result |
|---|---|
| Commit path | Runtime propose → preview → human approval → commit |
| Revisions | `B-001.parameter +1`, `B-001.geometry` unchanged |
| Stale | `MASS-B-001`, `SHADOW-E2E-002`, `CAD-IR-E2E-002`, `DXF-E2E-002` |
| Current | `PLAN-B-001`, `MASS-B-003` |
| Rebuilt | exactly the 4 stale artifacts |
| Massing | 24 m, `footprint_area_m2` unchanged, `volume_m3` recomputed |
| Shadow | dependency fingerprint changed |
| CAD-IR | B-001 height 24 m; geometry revision unchanged; parameter revision +1 |
| B-003 | massing 12 m; revisions unchanged |
| DXF | 15 entities; audit 0/0; readback pass |

### 2. T-junction RN-003 move to (21, 12)

| Check | Result |
|---|---|
| Node move | one atomic changeset; node move commit advances scene revision by exactly 1 |
| Edges | RE-001 / RE-002 / RE-003 carry `[21, 12]` |
| Corridor refresh | R-001 and R-002 rebuilt from **latest canonical edge geometry** (deterministic commit), never from the fixture |
| R-001 centerline | `[0,11] → [21,12] → [40,11]`; old `[20,11]` absent |
| R-002 centerline | starts at `[21,12]` |
| Stale | `CAD-IR-E2E-002`, `DXF-E2E-002` only |
| Current | `SHADOW-E2E-002`, `PLAN-B-001`, `MASS-B-001`, `MASS-B-003` |
| Rebuilt | CAD-IR and DXF only |
| DXF | readback pass; CAD-IR R-001 geometry contains the moved node |

### 3. Project north bearing 0° → 90°

| Check | Result |
|---|---|
| Canonical context | `PROJECT-CONTEXT-001.north_bearing_deg = 90.0`, source `human_override` |
| Versioning | context parameter revision increments |
| Stale | `SHADOW-E2E-002`, `CAD-IR-E2E-002`, `DXF-E2E-002` |
| Current | `PLAN-B-001`, `MASS-B-001`, `MASS-B-003` |
| B-001 geometry | geometry revision unchanged |
| Shadow | fingerprint changed; sample statuses changed (SAMPLE-02 shaded → unknown-height, SAMPLE-03 unknown-height → sunlit) |
| Rebuilt | exactly SHADOW, CAD-IR, DXF |
| DXF | readback pass |

### 4. Rebuild execution

- Worker claims jobs through `StatefulRuntime.claim_next_job`.
- Each job recomputes, writes, validates, then completes with a content hash.
- Success requires a content hash; validation failure marks the job failed.
- After rebuild, `stale_artifacts` is empty and all artifact states are `current`.
- The DXF content hash recorded in the job equals the SHA-256 of the written DXF file.

### 5. Delivery comparison

- Object ID set is identical before/after (11 objects).
- Entity count remains 15; audit remains 0 errors / 0 fixes.
- B-001 geometry revision is unchanged; parameter revision changes.
- B-003 revisions are unchanged.
- CAD-IR dependency fingerprint changes.
- Readback verdict remains `pass`.
- The conclusion does not rely on file hash alone.

## Road surface scope

**Road surface geometry is explicitly deferred in E2E-002.**

- No `SURFACE-R-002` artifact is registered in this project.
- No surface JSON/DXF geometry is generated.
- Dependency metadata for a surface is **not** a generated road surface.
- Node-move verification stops at the corridor centerline → CAD-IR → DXF path.

A future surface generator must use a declared input profile (at least R-002's explicit cross-section), record algorithm/version, width source and applicability, and must not present an undocumented `buffer()` result as validated professional road design.

## Known gaps

- Road surface geometry deferred (above).
- No third-party CAD round-trip.
- No IFC.
- No real sketch input.
- No standards or design-office profile.
- Shadow remains a synthetic vertical-prism baseline.

## Reproduce

```bash
python -m pytest tests/e2e/test_e2e_002_mutations.py -q
```

Or:

```python
from dgcad_e2e import LivingProject
project = LivingProject.create(
    "fixtures/e2e/living-pipeline-001.yaml",
    "out/e2e-002",
)
project.bootstrap()
project.mutate_building_height("B-001", 24.0)
project.rebuild_all()
```
