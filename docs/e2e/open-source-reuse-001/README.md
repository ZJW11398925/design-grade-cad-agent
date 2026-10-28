# M4c-0 — open-source design capability reuse sprint

Status: **research sprint complete; the 4c candidate is partial** (full-site
north-south spacing deferred). The road-topology finding below was later
diagnosed in M4c-1a as a floating-point noding artefact and fixed — this
sprint does not add new core dependencies and does not claim a finished design.

The sprint tested whether existing open-source geometry, road, morphology and
CAD-agent projects can replace work we have been doing ourselves. It used the
same CASE-SKETCH-001 focus block G-01 for all three experiments.

## Short answer

**Partially.** The open-source tools were useful for input cleanup, topology
reduction and evaluation, but none of them generated the professional design
we need. The most important finding is negative:

- Building Regulariser improved already-regular sketch footprints only
  marginally (2% area change, ERI +0.012) and does not generate unit/typology
  or massing. It is a cleanup adapter, not a building generator.
- OSMnx is the strongest candidate: `consolidate_intersections` cut the source
  309-node / 333-edge mesh to **117 nodes / 141 edges while keeping one
  connected component** at 8 m tolerance. But with design widths it still
  leaves no 120 × 90 m buildable focus rectangle; it is a topology
  preprocessor, not a road design hierarchy.
- PyGeoOps produced 11 centerlines for 11 road areas with 78% coverage, but
  **10 of 11 are multi-component**; per-area centerlines do not form a
  connected network.
- A single Clothoids G1 fit on MAIN-08 deviated by **356 m** and shortened the
  road by 78 m; direct clothoid fitting is not a usable alignment generator.
- momepy provides useful morphology/network metrics for candidate comparison,
  but is not a generator and not a compliance verdict.
- UrbGEN is MIT but a Rhino/Grasshopper `.gha` plugin, so it cannot run in this
  environment; it remains a design-knowledge reference.

The 4c design candidate also exposed a real defect: its **corridor union is one
polygon, but its noded centerline graph read 5 components** (51 nodes / 50
edges, `cyclomatic: 0`). The current `ROAD_CONNECTIVITY` check used the corridor
union and was too weak. (M4c-1a diagnosis: the 5-component reading was a
sub-ULP floating-point noding artefact — the 50-edge count is the simple-graph
collapse and `cyclomatic: 0` is momepy's connected-graph artefact. Fixed with
explicit shared-coordinate junctions; the noded graph is now 1 component
without OSMnx, which remains an optional source-skeleton preprocessor, not a
connectivity proof or the design base.)

## Experiments

| Experiment | What was tested | Result |
|---|---|---|
| A — building | Building Regulariser 0.2.5 on 9 focus footprints | 63→61 vertices, area −2.0%, mean Hausdorff 1.07 m, max 4.87 m, IoU 0.959, ERI 0.972→0.984; 10.3 s. Limited gain; no unit/typology generation. |
| B — roads | OSMnx 2.1.1 simplify + consolidate; PyGeoOps 0.6.0 centerlines; PyClothoids 0.2.0 G1 | OSMnx simplify 309/333→257/281; consolidate 8 m→117/141, 1 component, length 6,090 m (−10.7%). PyGeoOps 11/11 centerlines, 78% coverage, 10/11 multi-component. Clothoid fit failed quality (356 m Hausdorff). |
| C — collaboration | Uncorrected vs corrected building/road/green layout; momepy 1.0 evaluation | Uncorrected: 9 buildings, 1 road-clearance conflict (`SK-BLD-0038`), `FOCUS_ROAD_CLEARANCE` fail. Corrected: 7 buildings / 16 units, 20.0 m N-S, dropped `SK-BLD-0038` (2U) and `SK-BLD-0061` (1U), all current checks pass except deferred full-site spacing. Noded road topology then read 5 components (M4c-1a later diagnosed this as a float-noding artefact and fixed it). |

## Visual comparison

- Building regularization: [exp-a/overlay.png](exp-a/overlay.png)
- OSMnx simplification: [exp-b/overlay-osmnx.png](exp-b/overlay-osmnx.png)
- PyGeoOps centerlines: [exp-b/overlay-centerlines.png](exp-b/overlay-centerlines.png)
- Collaborative conflict/repair: [exp-c/comparison.png](exp-c/comparison.png)
- Editable DXF candidate: [exp-c/candidate-corrected.dxf](exp-c/candidate-corrected.dxf)
- 4c full drawing: [../design-synthesis-001/design-preview.png](../design-synthesis-001/design-preview.png)

## Reuse matrix

The full matrix, with versions, licenses, hosts, tested interfaces, metrics,
verdicts and rejected uses, is in [reuse-matrix.yaml](reuse-matrix.yaml).

Summary:

- **Adopt optional:** OSMnx (topology preprocessor), Building Regulariser
  (footprint cleanup only), PyGeoOps (per-area centerline candidate), momepy
  (candidate evaluation).
- **Reference only:** UrbGEN (Rhino/Grasshopper), Street Generator/rue-lib
  (not on PyPI, GDAL, foreign widths).
- **Defer:** Clothoids (needs a chain/control-point policy), IfcOpenShell and
  Ladybug Tools (3D/IFC/environment stage).
- **Research only:** SolidCraft, vcad, text-to-cad, CADAM (no tested code,
  host/license review pending).
- **Reject:** broad 90-project integration; using foreign design defaults as
  Chinese standards; treating the source skeleton as the final road design.

## Next round

1. Add an optional OSMnx adapter: local `RoadGraph` → `nx.MultiDiGraph` →
   `simplify_graph` + `consolidate_intersections(tolerance ≤ 8 m)` → noded
   `RoadGraph`, preserving source edge IDs and classes.
2. Replace the corridor-only `ROAD_CONNECTIVITY` check with a noded centerline
   topology check; regenerate the 4c candidate.
3. Apply the design hierarchy on the connected consolidated network: retain a
   connected branch tree, assign 12/7/4 m widths, and search for buildable
   blocks.
4. Use Building Regulariser only on noisy inputs; keep the 24×11 staircase
   module as the building design step.
5. Use momepy for candidate comparison, not for code compliance.
6. Do not add Clothoids, UrbGEN or Street Generator to core until host,
   control-point and Chinese-profile adapters exist.

## Evidence

- `reuse-matrix.yaml`
- `exp-a/metrics.json`, `exp-a/source.geojson`, `exp-a/regularized.geojson`,
  `exp-a/overlay.png`
- `exp-b/metrics.json`, `exp-b/source-network.geojson`,
  `exp-b/osmnx-simplified.geojson`, `exp-b/osmnx-consolidated-8m.geojson`,
  `exp-b/pygeoops-centerlines.geojson`, `exp-b/clothoid.json`,
  `exp-b/overlay-osmnx.png`, `exp-b/overlay-centerlines.png`
- `exp-c/metrics.json`, `exp-c/comparison.png`, `exp-c/design-notes.md`,
  `exp-c/candidate-corrected.dxf`

## Reproduce

```bash
python -m pip install buildingregulariser pygeoops pyclothoids momepy osmnx
python experiments/m4c0/exp_a_building.py
python experiments/m4c0/exp_b_roads.py
python experiments/m4c0/exp_c_collaborative.py
```

Optional dependencies are for the experiment only; they are not in
`pyproject.toml` core dependencies.

## Non-claims

- The open-source tools do not by themselves produce a professional Chinese
  residential design.
- The 4c candidate is a partial candidate: its noded road topology is
  disconnected; the corridor-union check masked it.
- No code compliance, construction readiness or design-office approval is
  claimed.
- EPSG:3857 was assigned only for GeoPandas/OSMnx compatibility; the
  coordinates are the local metric sketch frame, not a real projection.
