# CASE-SKETCH-001 — real designer sketch intake

Status: **proposed, not human-confirmed**.
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

## Designer confirmations (2026-10-27)

- The private redline is the site boundary; the sketch is hand-modified with a
  large deviation, and that is accepted.
- Unit: **metre**; the DWG header `$INSUNITS=4` is a metadata defect.
- Existing survey buildings: **remove all**; they are unrelated to the design.
- **Red** = building; **magenta** = underground garage entrance, not a building.
- **Brown** = main road; **blue** = branch road and access road; **green** =
  cluster green space.
- The top edge is intentional; only a road segment is clipped.
- Publication: **sketch only**.

## What was extracted

| Class | Count | State |
|---|---|---|
| Building candidates (red components) | 63 | semantic label confirmed; geometry proposed |
| Garage entrance candidates (magenta) | 3 | semantic label confirmed; geometry proposed |
| Cluster green spaces | 12 | semantic label confirmed; geometry proposed |
| Road area candidates | 9 | label confirmed; area not validated |
| Road centerline candidates | 312 | proposed_rough |
| Site boundary | 1 | label confirmed; geometry approximate |

The trace is a deterministic colour segmentation. It does **not** orthogonalise
buildings, smooth roads, or complete occluded boundaries. Buildings are red
connected components; no merge or split has been applied.

### Merge/split and the left cluster

A red connected component is treated as one building. If two adjacent components
are actually one building with an attached wing, they should be merged; if one
component contains two buildings separated by a gap, it should be split. The
current default is **separate**. The 10 close pairs (≤4 px) are listed in
`merge-review-pairs.json`; see `merge-review-left-cluster.png` for the left
cluster IDs 0040–0049. To merge, name the two trace IDs; to split, name the
component and the cut. No merge or split has been applied yet.

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

- Building merge/split decisions (default: separate).
- A human-confirmed trace and fidelity metrics (Hausdorff, IoU, topology) have
  not been produced. No accuracy claim is made.
- 支路 vs 入户路 separation.
- Road topology review.

## Non-claims

- One hand-modified concept sketch is not a sketch-recognition benchmark.
- Semantic confirmation does not confirm geometry.
- Calibration is approximate and not survey-grade.
- Road centerlines are not professional road design.
- No claim that building footprints, counts or topology match the design record.
- No OCR; the visible 幼儿园 label was observed visually, not machine-read.

## Files

- `source/sketch.png` — published sketch (designer authorisation: sketch only).
- `trace-raw.geojson` — image-space trace with labels and review states.
- `road-centerlines-proposed.geojson` — rough image-space centerlines.
- `ambiguities.geojson` — image-space ambiguity regions.
- `trace-overlay.png`, `road-centerlines-overlay.png` — visual review.
- `merge-review-left-cluster.png` — merge/split review crop.
- `merge-review-pairs.json` — the 10 close pairs, default separate.
- `case-summary.json` — machine-readable public summary.
