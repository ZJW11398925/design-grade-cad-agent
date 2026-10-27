# CASE-SKETCH-001 — real designer sketch intake

Status: **proposed geometry; designer-confirmed semantics, merges and unit types; unit counts inferred**.
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

Only **1-unit, 2-unit and 3-unit** residential types are designed. Unit counts
for buildings without a designer-confirmed count are inferred from the sketch's
approximate dimensions. The current building footprints are **sketch-era
placeholders**; the designer will supply a unit-type library (户型库) to replace
them.

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
    connecting parts. One 3-unit building.
  - **M-002**: 0030 contains two units; 0053 contains one unit. One 3-unit
    building.
  - **M-003**: 0001 and 0037 are one building; the visible 幼儿园 label makes it
    a kindergarten/facility, so it is not forced into a residential unit type.
  - **M-004**: 0019 and 0058 are one building, inferred as 3 units.
  - **M-005**: 0027 and 0059 are one building, inferred as 3 units.
- **Only 1/2/3-unit residential types**. Unit counts for the remaining
  residential buildings are inferred from sketch dimensions.
- **Floors**: 11 floors is the provisional assumption for **all** buildings.
- **Unit-type library**: pending; sketch-era footprints are placeholders.
- Publication: **sketch only**.

## What was extracted

| Class | Count | State |
|---|---|---|
| Buildings (50 standalone + 5 merged) | 55 | semantic label and merge confirmed; geometry proposed |
| Original red components | 63 | preserved for provenance in `building-components.geojson` |
| Merged buildings | 5 | M-001 3U; M-002 3U; M-003 kindergarten; M-004 3U inferred; M-005 3U inferred |
| Unit distribution (residential) | 16 one-unit, 21 two-unit, 17 three-unit | 2 confirmed, 52 inferred; 1 facility excluded |
| Garage entrance candidates (magenta) | 3 | semantic label confirmed; geometry proposed |
| Cluster green spaces | 12 | semantic label confirmed; geometry proposed |
| Road area candidates | 9 | label confirmed; area not validated |
| Road centerline candidates | 312 | proposed_rough |
| Site boundary | 1 | label confirmed; geometry approximate |

The trace is a deterministic colour segmentation. It does **not** orthogonalise
buildings, smooth roads, or complete occluded boundaries. Building geometry
remains `proposed`; semantic labels, merges and unit types are confirmed or
explicitly inferred.

### Building merges, unit inference and floors

Merged buildings are unions of their confirmed components, **without artificial
bridging**:

- **M-001** (`SK-BLD-MRG-0001`) — 0046 + 0047 + 0060 (3 units) plus connectors
  0062 + 0063; MultiPolygon of five parts; 3 units confirmed.
- **M-002** (`SK-BLD-MRG-0002`) — 0030 (2 units) + 0053 (1 unit);
  MultiPolygon of two parts; 3 units confirmed.
- **M-003** (`SK-BLD-MRG-0003`) — 0001 + 0037; kindergarten/facility;
  `unit_count: null`, `unit_count_state: not_applicable`.
- **M-004** (`SK-BLD-MRG-0004`) — 0019 + 0058; inferred 3 units.
- **M-005** (`SK-BLD-MRG-0005`) — 0027 + 0059; inferred 3 units.
- All ten close pairs are resolved into these five merged buildings.
- All 63 original red components are preserved in `building-components.geojson`
  with `merged_into`, `component_role` and `unit_count`.

Unit-count inference for the 52 residential buildings without a designer count:

- primary rule: **long side** `<75 px` = 1 unit, `75–114 px` = 2 units,
  `>=115 px` = 3 units;
- cross-check: **area** `<2,000 px²` = 1 unit, `2,000–3,199 px²` = 2 units,
  `>=3,200 px²` = 3 units;
- distribution: **16 one-unit, 21 two-unit, 17 three-unit**, plus one facility;
- six long bars (`0009`, `0010`, `0011`, `0013`, `0015`, `0018`) are 3-unit by
  length but 2-unit by area; these conflicts are recorded for designer review.

Every building records `floor_count: 11`, `floor_state: proposed_initial`, and
`floor_height_m: null`. No height, massing, FAR or unit-mix is derived from the
11-floor assumption.

## Calibration

The sketch was registered to a private site reference with a six-point
homography. Residual: **mean 24.51 px, max 43.42 px**. The designer accepts the
boundary registration, but the sketch is hand-drawn and the result is
**conceptual**, not survey-grade. The reference frame and matrix are private.

## Road centerlines and topology (EP-R1-ROAD-001)

**The design's road network is one system.** The earlier process skeletonised
brown and blue masks separately, which cut the design at colour boundaries and
produced nine artificial components. That result is superseded.

Corrected process:

1. union brown (main) and blue (branch/access) into one road mask;
2. filter components below 300 px;
3. apply a **5 px ellipse closing** — 4 px leaves five components; 5 px is the
   smallest tested kernel that restores one connected design network;
4. skeletonise, build the pixel graph, cluster junctions, prune short spurs and
   contract degree-2 chains.

Unified network:

- **1 connected component**, 309 nodes, 333 edges, 111 endpoints,
  **121 junction candidates**, 25 independent cycles;
- road class from brown/blue pixel majority: **65 main-road** and
  **268 branch/access** edges; colour is a class attribute, not a topology
  separator;
- junctions are skeleton graph nodes (red dots in the overlay), not inferred
  connectors; all 121 are `proposed` and need review.

The eight nearest-node connectors from the failed process remain in
`road-connectors-rejected.geojson` as negative evidence; they are not used.

No road width, cross-section, alignment, junction turn geometry, profile or
surface is derived. The blue class still combines 支路 and 入户路. The old
separate-colour centerline file is retained as
`road-centerlines-separate-colour-superseded.geojson`.

## Open items

- Review the six length-vs-area unit-count conflicts: `0009`, `0010`, `0011`,
  `0013`, `0015`, `0018`.
- Confirm the kindergarten M-003 as a facility, not a residential 1/2/3-unit type.
- Provide the unit-type library and replace the sketch-era building footprints.
- A human-confirmed trace and fidelity metrics (Hausdorff, IoU, topology) have
  not been produced. No accuracy claim is made.
- 支路 vs 入户路 separation.
- Review the 121 junction candidates and the 5 px closing kernel; the unified
  mask restores one connected design network.
- Road width, cross-section, profile and alignment are not designed.
- Canonical Building/Road handoff from this sketch.

## Non-claims

- One hand-modified concept sketch is not a sketch-recognition benchmark.
- Semantic confirmation and merge decisions do not confirm geometry.
- Unit counts are inferred from sketch dimensions, not confirmed, except M-001
  and M-002; the kindergarten M-003 is excluded as a facility.
- Six long bars are 3-unit by length but 2-unit by area; the conflict is unresolved.
- 11 floors is a provisional design assumption; no floor height, massing, FAR
  or unit-mix is derived.
- Every building footprint is a sketch placeholder pending the unit-type library.
- Calibration is approximate and not survey-grade.
- Road centerlines are not professional road design.
- No claim that building footprints, counts or topology match the design record.
- Road connectivity comes from the unified brown+blue road mask (5 px closing);
  121 junction candidates are proposed for review. The separate-colour
  9-component result and the 8 nearest-node connectors are rejected.
- No road width, cross-section, profile, alignment or surface is designed.
- No OCR; the visible 幼儿园 label was observed visually, not machine-read.

## Files

- `source/sketch.png` — published sketch (designer authorisation: sketch only).
- `trace-raw.geojson` — image-space buildings/garage/green/roads/boundary with labels, units and review states.
- `building-components.geojson` — all 63 original red components and merge provenance.
- `merge-review-pairs.json` — close pairs; all ten resolved.
- `merge-review-left-cluster.png` — pre-merge left cluster; `merge-applied-left-cluster.png` — M-001 after merge.
- `road-centerlines-separate-colour-superseded.geojson` — superseded separate-colour skeleton.
- `road-network-proposed.geojson`, `road-nodes-proposed.geojson`,
  `road-junctions-proposed.geojson`, `road-topology-summary.json` — unified
  design network (1 component; 121 junction candidates).
- `road-connectors-rejected.geojson` — eight rejected nearest-node connectors
  (negative evidence).
- `road-network-overlay.png` — unified centerlines and junctions;
  `road-centerlines-separate-colour-superseded.png` — superseded overlay.
- `ambiguities.geojson` — image-space ambiguity regions.
- `trace-overlay.png`, `road-network-overlay.png` — visual review.
- `case-summary.json` — machine-readable public summary.
