# CASE-SKETCH-001-HANDOFF-A — real sketch → canonical handoff pilot

Status: **pilot subset only**; `EP-R1-SKETCH-001` is **not complete**.

This is the first end-to-end proof that selected real CASE-SKETCH-001 evidence
can pass an explicit human geometry gate, enter the existing Domain Slice,
produce canonical objects, and reach a readback DXF through CAD-IR.

## Pipeline

```text
CASE-SKETCH-001 selected evidence
  -> human-reviewed handoff (pilot subset)
    -> ConfirmedTraceScene
      -> build_initial_scene()
        -> runtime proposal / preview / human approval / commit
          -> Canonical Site Model
            -> CAD-IR -> pilot.dxf -> ezdxf readback
```

## Selected subset

| Source | Trace | Canonical | Role |
|---|---|---|---|
| `SK-BND-001` | `SK-BND-001` | `SITE-001` | site boundary |
| `SK-BLD-0007` | `SK-BLD-0007` | `B-SKETCH-0007` | ordinary building |
| `SK-BLD-MRG-0001` | `SK-BLD-MRG-0001` | `B-SKETCH-MRG-0001` | merged multi-unit building |
| `SK-GRN-0001` | `SK-GRN-0001` | `G-001` | cluster green space |
| `SK-RDC-U-0008` | `TRACE-SK-RDC-U-0008` | `SK-RDC-U-0008` | main-road edge |
| `SK-RDC-U-0010` | `TRACE-SK-RDC-U-0010` | `SK-RDC-U-0010` | main-road edge |
| `SK-RDC-U-0017` | `TRACE-SK-RDC-U-0017` | `SK-RDC-U-0017` | branch/access edge |

The selected road edges form a real T-junction (`SK-RDN-0126`) with two main
edges and one branch edge. The main corridor `R-SK-MAIN-001` references both main
edges; `R-SK-BRANCH-001` references the branch edge.

The site-boundary geometry is the published sketch boundary (`SK-BND-001`). The
private redline remains the authoritative site reference, but its geometry is
neither used nor published in this pilot; the local metric scale is approximate.

## Human geometry gate

`review-record.yaml` is an **input**, not an agent output:

- reviewer role: `designer`;
- scope: `pilot_subset`;
- `human_confirmed_trace: true`;
- every selected object has `semantic: confirmed`, `geometry:
  confirmed_for_pilot`, `coordinate: local_metric_approximate`;
- basis: designer instruction 2026-10-28 to run a representative pilot;
- limitations: **not a full-case geometry review and not survey-grade**.

The handoff loader rejects proposed geometry, missing decisions, agent review
roles, broken provenance, duplicate mappings and project-coordinate claims.

## Coordinate handoff

- source: `image_space_unscaled`; target: `LOCAL-ENU-XY-ZUP`;
- state: `local_metric_scaled` (approximate, not survey-grade);
- scale: `2.438 px/m`; declared range `2.25–2.89 px/m`;
- origin: arbitrary local sketch origin `[45, 1536] px`; y axis flipped;
- `project_coordinates: false`; private calibration reference is not published.

No DWG, redline or project coordinate is included in this evidence package.

## Result

- Canonical scene: site boundary `SITE-001`, two building candidates, one green
  space `G-001`, two road corridors, three road edges and four road nodes.
- Building heights and base elevations remain `unknown`; both massing attempts
  are blocked with `MASSING_BLOCKED_UNKNOWN_HEIGHT`.
- Road hierarchy and cross-section remain `unknown`; both profiles are blocked
  with `ROAD_CLASS_UNCONFIRMED`; no width is derived.
- Trace evidence is unchanged after all proposals and commits
  (`trace_immutable` is true for all seven trace objects).
- CAD-IR: `pass_with_scope_limits`; the only issues are
  `UNKNOWN_HEIGHT_ALLOWED` warnings for the two buildings.
- DXF: **11 entities**, audit **0 errors / 0 fixes**; readback **11/11 pass**.
  Breakdown: site boundary 1, ordinary building 1, merged building 5,
  green 1, main corridor 2 parts, branch corridor 1.
- Road edges are exported through their corridor centerlines; edge IDs remain
  in CAD-IR provenance and `provenance-map.json`, not as separate DXF entities.
- Shadow/environment analysis is **not run** (`shadow-not-run.json`); no
  environmental result is claimed.

## Provenance

`provenance-map.json` records:

- source ID → trace ID → canonical ID for all seven selected objects;
- canonical object presence and CAD-IR object presence;
- readback entity counts;
- corridor → edge refs → source edge IDs;
- road-node provenance (graph-only; exported through corridor edges);
- the `HANDOFF-CASE-SKETCH-001-HANDOFF-A` canonical audit object.

## Reproduce

```bash
python scripts/sketch_intake/build_handoff_a.py
python scripts/e2e/run_sketch_handoff_a.py
python -m pytest -q tests/test_sketch_handoff.py tests/e2e/test_sketch_handoff_a.py
```

## Evidence files

- `handoff.yaml`, `review-record.yaml`, `domain-fixture.yaml`
- `handoff-summary.json`
- `canonical-snapshot.json`
- `cad-ir.json`
- `pilot.dxf`
- `readback-manifest.json`
- `validation.json`
- `provenance-map.json`
- `shadow-not-run.json`

## Non-claims

- This is a selected pilot subset, not the full CASE-SKETCH-001 site.
- `confirmed_for_pilot` is not a full-case or survey-grade geometry confirmation.
- 11 floors is provisional; no building height, base elevation, massing, FAR or
  unit-mix is derived.
- Road hierarchy, cross-section, alignment, width and surface are not designed.
- Same-library `ezdxf` readback is not third-party CAD evidence.
- A successful DXF readback is not a design-office compliance conclusion.
- `EP-R1-SKETCH-001` remains in progress; `R1-G07` remains partial.
