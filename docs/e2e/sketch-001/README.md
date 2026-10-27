# CASE-SKETCH-001 — real designer sketch intake

Status: **proposed geometry; designer-confirmed semantics and building merges**.
Tier: **B — designer sketch on a known base**.
Public scope: **sketch raster and image-space derived geometry only**.

## What this case is

A designer-authored, colour-filled residential site plan. The designer confirmed
that the hand-drawn boundary corresponds to a private site reference, that the
drawing unit is metre, and that the existing survey buildings on the site are to
be removed and are unrelated to the sketch design.

The private site reference (DWG/DXF, redline and project coordinates) is **not**
published. Public files contain image-space pixels only. The sketch is published
with the designer's authorization; no separate licence is asserted for the
drawing, which remains the designer's work.

The current building footprints are **sketch-era placeholders**. The designer
will supply a unit-type library (户型库) to replace them; unit counts and floor
counts are the stable design inputs for now.

## Designer confirmations (2026-10-27)

- The private redline is the site boundary; the sketch is hand-modified with a
  large deviation, and that is accepted.
- Unit: **metre**; the DWG header `$INSUNITS=4` is a metadata defect.
- Existing survey buildings: **remove all**; they are unrelated to the design.
- **Red** = building; **magenta** = underground garage entrance, not a building.
- **Brown** = main road; **blue** = branch road and access road; **green** =
  cluster green space.
- The top edge is intentional; only a road segment is clipped.
- Building merges:
  - **M-001**: 0046, 0047 and 0060 are three units; 0062 and 0063 are the
    connecting parts. They form one 3-unit building.
  - **M-002**: 0030 contains two units; 0053 contains one unit. They form one
    3-unit building.
- **Floors**: 11 floors is the provisional assumption for **all** buildings.
- **Unit-type library**: pending; sketch-era footprints are placeholders.
- Publication: **sketch only**.

## What was extracted

| Class | Count | State |
|---|---|---|
| Buildings (56 standalone + 2 merged) | 58 | semantic label and merge confirmed; geometry proposed |
| Original red components | 63 | preserved for provenance in `building-components.geojson` |
| Merged buildings | 2 | M-001 3 units; M-002 3 units |
| Garage entrance candidates (magenta) | 3 | semantic label confirmed; geometry proposed |
| Cluster green spaces | 12 | semantic label confirmed; geometry proposed |
| Road area candidates | 9 | label confirmed; area not validated |
| Road centerline candidates | 312 | proposed_rough |
| Site boundary | 1 | label confirmed; geometry approximate |

The trace is a deterministic colour segmentation. It does **not** orthogonalise
buildings, smooth roads, or complete occluded boundaries. Building geometry
remains `proposed`; only the semantic labels and merge decisions are confirmed.

### Building merges and the left cluster

A merged building is the union of its confirmed components, **without artificial
bridging**:

- **M-001** (`SK-BLD-MRG-0001`) is a MultiPolygon of five parts: three units
  (0046, 0047, 0060) and two connectors (0062, 0063). Unit count: 3.
- **M-002** (`SK-BLD-MRG-0002`) is a MultiPolygon of two parts: 0030 (2 units)
  and 0053 (1 unit). Unit count: 3.
- The other 56 red components remain one building each. Their unit counts are
  **unknown** and are not inferred.
- Seven of the ten close pairs are resolved into M-001/M-002; the remaining pairs
  `0001/0037`, `0019/0058` and `0027/0059` stay separate pending review.
- All 63 original red components are preserved in `building-components.geojson`
  with `merged_into`, `component_role` and `unit_count`.
- `merge-review-left-cluster.png` shows the pre-merge components;
  `merge-applied-left-cluster.png` shows M-001 after the merge.

Every building records `floor_count: 11`, `floor_state: proposed_initial`, and
`floor_height_m: null`. No height, massing, FAR or unit-mix is derived from the
11-floor assumption.

## Calibration

The sketch was registered to a private site reference with a six-point
homography. Residual: **mean 24.51 px, max 43.42 px**. The designer accepts the
boundary registration, but the sketch is hand-drawn and the result is
**conceptual**, not survey-grade. The reference frame and matrix are private.

## Road centerlines

Skeleton-derived from the brown and blue masks:

- Main road: 1 connected component, 40 nodes, 41 edges, 4 endpoints, 6 junctions, 2 loops, 3860.77 px.
- Branch/access: 8 components, 266 nodes, 271 edges, 125 endpoints, 93 junctions, 13 loops, 10708.66 px.

These are **rough candidates**: no professional alignment, width inference,
cross-section, junction turn geometry, surface or road-engineering validation.
The blue class combines 支路 and 入户路; the colour does not separate them.

Extraction used private intake tooling (colour masks → thinning → pixel graph →
junction clustering → spur pruning → degree-2 chain contraction → simplification).
The method and parameters are recorded here, but the tooling is not part of the
installable package; the public artifact is the evidence, not a benchmark harness.

## Open items

- Provide the unit-type library and replace the sketch-era building footprints.
- Confirm the remaining close pairs `0001/0037`, `0019/0058`, `0027/0059`.
- A human-confirmed trace and fidelity metrics (Hausdorff, IoU, topology) have
  not been produced. No accuracy claim is made.
- 支路 vs 入户路 separation.
- Road topology review.
- Canonical Building/Road handoff from this sketch.

## Non-claims

- One hand-modified concept sketch is not a sketch-recognition benchmark.
- Semantic confirmation and merge decisions do not confirm geometry.
- 11 floors is a provisional design assumption; no floor height, massing, FAR
  or unit-mix is derived.
- Every building footprint is a sketch placeholder pending the unit-type library.
- Unit counts are confirmed only for M-001 and M-002; other buildings remain unknown.
- Calibration is approximate and not survey-grade.
- Road centerlines are not professional road design.
- No claim that building footprints, counts or topology match the design record.
- No OCR; the visible 幼儿园 label was observed visually, not machine-read.

## Files

- `source/sketch.png` — published sketch (designer authorisation: sketch only).
- `trace-raw.geojson` — image-space buildings/garage/green/roads/boundary with labels and review states.
- `building-components.geojson` — all 63 original red components and merge provenance.
- `merge-review-pairs.json` — close pairs and their merge resolutions.
- `merge-review-left-cluster.png` — pre-merge left cluster; `merge-applied-left-cluster.png` — M-001 after merge.
- `road-centerlines-proposed.geojson` — rough image-space centerlines.
- `ambiguities.geojson` — image-space ambiguity regions.
- `trace-overlay.png`, `road-centerlines-overlay.png` — visual review.
- `case-summary.json` — machine-readable public summary.
