# E2E-001 — Living Pipeline Port

Status: implemented (synthetic scope)
Version: 0.3.0
Date: 2026-10-27

## Purpose

First end-to-end path built **only** from living `src/` packages. The R0 archived pipeline is reference evidence, not an execution dependency.

```text
fixtures/domain/domain-slice-001-r2.yaml
  -> ConfirmedTraceScene                    (dgcad_domain)
  -> SceneState with evidence/candidates    (dgcad_domain)
  -> StatefulRuntime commits                (dgcad_runtime)
  -> massing DerivedArtifact + stale        (dgcad_domain / foundation dependency graph)
  -> synthetic shadow baseline              (dgcad_analysis)
  -> CAD-IR                                 (dgcad_cad)
  -> DXF R2010                              (dgcad_cad)
  -> readback manifest + validation         (dgcad_cad)
  -> domain / CAD-IR / DXF validation
```

## Executed result

| Item | Result |
|---|---|
| Canonical commits | B-001, B-002, B-003, R-001, R-002 committed through Runtime with human approval grants |
| Canonical scene revision | 6 (initial 1 + 5 commits) |
| Massing artifacts | `MASS-B-001`, `MASS-B-003` |
| Massing blocked | `B-002` → `MASSING_BLOCKED_UNKNOWN_HEIGHT` |
| Rebuild order | `MASS-B-001`, `MASS-B-003`, `SURFACE-R-002` (3 queued jobs) |
| Shadow samples | 2 sunlit, 1 confirmed shaded (B-001), 1 unknown-height (B-002) |
| Shadow status | `bounded_or_unknown` |
| CAD-IR objects | 11 (7 canonical + 4 analysis samples) |
| CAD-IR validation | `pass_with_scope_limits` (`UNKNOWN_HEIGHT_ALLOWED`) |
| DXF entities | 15 modelspace entities |
| DXF audit | 0 errors, 0 fixes |
| DXF readback | `pass` |
| Domain validation | `blocked` with exactly `UNKNOWN_HEIGHT_BLOCKS_MASSING` and `ROAD_CLASS_UNCONFIRMED` |
| Evidence files | `cad-ir.json`, `shadow-result.json`, `readback-manifest.json`, `cad-ir-validation.json`, `domain-validation.json`, `pipeline-summary.json`, `living-pipeline-001.dxf` |

The domain verdict is intentionally **blocked**: the fixture contains a building with unknown height and a road with unknown class. The pipeline still produces a delivery artifact, while both unknowns remain explicit and visible.

## What this proves

- The living Domain/Runtime contracts survive contact with Building and Road objects in one chain.
- Human approval, canonical commit, dependency invalidation and rebuild scheduling work end to end.
- Unknown height and unknown road class survive into analysis, CAD-IR and DXF metadata rather than being defaulted.
- DXF output carries object identity, revisions, source/representation hashes, entity roles and `confirmation_scope` through XDATA. Synthetic objects carry `confirmation_scope: synthetic`; the 0.13.0 field is the 11th XDATA value.
- The readback validator detects vertex mutation, unexpected layers and entity-type substitution without crashing.
- The pipeline contains no import or invocation of archived research scripts.

## Known gaps (deliberately not fixed here)

- `DEV-CAD-003` / issue #3: at E2E-001 time bulge and constant-width mutations were not detected (two strict xfails). Resolved in Milestone 3a / 0.6.0; this report records the earlier state.
- `DEV-CAD-001`, `002`, `004`–`008` remain Milestone 3 work.
- No third-party CAD round-trip.
- No real sketch → trace.
- No IFC.
- No standards or design-office profile compliance.
- Shadow is a synthetic vertical-prism baseline, not an independent simulation engine.

## Reproduce

```bash
python -m pytest tests/e2e/test_living_pipeline.py -q
python -m pytest tests/test_cad_delivery_contracts.py -q
```

Or run the pipeline directly:

```python
from dgcad_e2e import run_living_pipeline
result = run_living_pipeline(
    "fixtures/e2e/living-pipeline-001.yaml",
    "out/e2e-001",
)
```
