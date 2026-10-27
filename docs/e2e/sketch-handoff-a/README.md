# CASE-SKETCH-001-HANDOFF-A — real sketch → canonical handoff pilot

Status: **blocked at the human review gate**; `EP-R1-SKETCH-001` is **not
complete**. The 0.12.0 executed pilot is preserved under
`history-0.12.0/` and is superseded.

This package now records what is actually true: the designer authorized a
representative pilot on a selected subset, but no object-level geometry or
coordinate review has been recorded. The pipeline therefore stops before
`ConfirmedTraceScene` and produces no canonical model, CAD-IR or DXF.

## What stalled the pipeline

`blocked.json` records `HUMAN_OBJECT_REVIEW_REQUIRED`. The review record in
`handoff.yaml` / `review-record.yaml` has:

- `review_kind: designer_authorized_pilot`
- `object_geometry_review: false`
- `human_confirmed_trace: false`
- every object decision `geometry: not_reviewed`,
  `coordinate: not_reviewed`

The design semantics were confirmed earlier (red = building, brown = main
road, blue = branch/access, green = cluster green, magenta = garage entrance,
underground existing survey buildings removed). Semantics are not geometry.

## Pipeline

```text
CASE-SKETCH-001 selected evidence
  -> handoff inspection + source integrity + road topology
    -> review packet (image-space and local-metric overlays)
      -> [blocked] human review record
        -> ConfirmedTraceScene -> Canonical -> CAD-IR -> DXF -> readback
```

The downstream half is implemented and is exercised by a test double in
`tests/e2e/test_sketch_handoff_a.py::test_human_reviewed_pilot_reaches_dxf_with_scope`.
The test double is never published as evidence.

## Selected subset

| Source | Trace | Canonical | Role |
|---|---|---|---|
| `SK-BND-001` | `SK-BND-001` | `SITE-SKETCH-001` | sketch site boundary |
| `SK-BLD-0007` | `SK-BLD-0007` | `B-SKETCH-0007` | ordinary building |
| `SK-BLD-MRG-0001` | `SK-BLD-MRG-0001` | `B-SKETCH-MRG-0001` | merged multi-unit building |
| `SK-GRN-0001` | `SK-GRN-0001` | `G-001` | cluster green space |
| `SK-RDC-U-0008` | `TRACE-SK-RDC-U-0008` | `SK-RDC-U-0008` | main-road edge |
| `SK-RDC-U-0010` | `TRACE-SK-RDC-U-0010` | `SK-RDC-U-0010` | main-road edge |
| `SK-RDC-U-0017` | `TRACE-SK-RDC-U-0017` | `SK-RDC-U-0017` | branch/access edge |

The site boundary is the **published sketch boundary**, not the private
redline. The redline is the authoritative site reference, but its geometry is
not used or published here. For that reason the boundary maps to
`SITE-SKETCH-001` with **candidate** authority, never to authoritative
`SITE-001`.

## Human review required

`review-packet.html` shows every selected object on the sketch and in local
metric space, with the declared scale range and per-object sensitivity.
`review-request.yaml` lists the questions. `review-confirmation-template.yaml`
is an **unsigned template**; it is not a confirmation and the loader rejects it.

To unblock the pipeline the designer must:

1. inspect every object overlay;
2. fill `geometry` and `coordinate` decisions per object;
3. set `human_confirmed_trace: true` and `object_geometry_review: true`;
4. record `reviewed_at`, `basis`, evidence refs and the packet hash;
5. keep the scope `pilot_subset` (a full-case review requires `confirmed`
   geometry, not `confirmed_for_pilot`).

The Agent cannot sign this record.

## Scope and authority propagation

The v0.1 defect is closed in the code path and tested with the test double:

- trace objects carry `confirmation_scope=pilot_subset`,
  `geometry_quality=confirmed_for_pilot`, `review_kind`;
- canonical objects carry the same fields;
- CAD-IR provenance carries the fields;
- DXF XDATA carries `confirmation_scope`;
- the readback manifest records each entity's scope and the top-level
  `confirmation_scopes`;
- a full-case review rejects `confirmed_for_pilot`;
- a published sketch boundary cannot claim `canonical_site_identity` or
  `SITE-001`.

## Coordinate handoff

- source: `image_space_unscaled`; target: **`LOCAL-XY-ZUP`**;
- transform: `uniform_scale_translation_yflip` — translation, y-flip and a
  single scale; **not** the six-point homography;
- `homography_applied: false`; `shape_correction: none`;
- `axis_orientation: unknown` — the sketch does not establish east or north;
- scale `2.438 px/m`, declared range `2.25–2.89 px/m`; the scale source is the
  private homography reduced to a uniform scale; the matrix is not published;
- origin is the published sketch boundary's bounding-box corner;
- per-object area/perimeter/centroid sensitivity is in
  `coordinate-sensitivity.json`.

## Source integrity

`integrity.json` verifies, for all seven objects:

- the sketch, trace GeoJSON and road-network GeoJSON file hashes;
- that each named source object exists;
- that its geometry hash matches the handoff `source_geometry_sha256`;
- that the handoff geometry equals the source object geometry.

A changed source file or object with a stale hash fails closed. Tests cover
file-hash mismatch, object-geometry mismatch, source-object removal and a
handoff geometry that diverges from its source.

## Road topology

`road-topology.json` records:

- 4 nodes, 3 edges, 1 connected component;
- one T-junction `SK-RDN-0126` with degree 3;
- endpoints `SK-RDN-0067`, `SK-RDN-0125`, `SK-RDN-0209`;
- maximum endpoint offset **3.606 px** against a declared **4.0 px**
  extraction tolerance;
- edge direction normalization: `SK-RDC-U-0010` and `SK-RDC-U-0017` were
  stored `to_node → from_node` in the source network and are normalized to
  `node_a → node_b`;
- each corridor's `edge_refs` and `source_edge_ids` match.

The 3.606 px offset is a real extraction artifact, not a clean T-junction; it
is inside the declared tolerance and visible in the packet for review. A
10 px endpoint mutation is rejected with `ROAD_EDGE_ENDPOINT_MISMATCH`.

## Publication

`publication` declares `pilot_local_metric` with an explicit exclusion list:
DWG, redline, project coordinates and the calibration matrix. The DXF produced
in the test-double run passes a structured privacy scan over TEXT, layer names,
XDATA and raw bytes. The private calibration matrix is not published.

## Reproduce

```bash
python scripts/sketch_intake/build_handoff_a.py
python scripts/e2e/run_sketch_handoff_a.py
python -m pytest -q tests/test_sketch_handoff.py tests/e2e/test_sketch_handoff_a.py
```

`build_handoff_a.py` reads `review.yaml`; it never writes a review decision.
`run_sketch_handoff_a.py` writes the review packet and, when the review is
only an authorization, the blocked evidence.

## Evidence files

- `handoff.yaml`, `review-record.yaml`
- `review-packet.json`, `review-packet.html`
- `review-request.yaml`, `review-confirmation-template.yaml`
- `handoff-summary.json`, `blocked.json`
- `integrity.json`, `road-topology.json`, `coordinate-sensitivity.json`
- `provenance-map.json`
- `history-0.12.0/` — superseded executed pilot; not current evidence

No `pilot.dxf`, `canonical-snapshot.json`, `cad-ir.json` or
`domain-fixture.yaml` exists in this directory: the pipeline did not run.

## Non-claims

- This is a selected pilot subset, not the full CASE-SKETCH-001 site.
- Authorization to run a pilot is not an object-level geometry review.
- `confirmed_for_pilot` is not a full-case or survey-grade confirmation.
- The uniform-scale transform does not correct local sketch distortion.
- The local metric frame is approximate and not survey-grade.
- Road hierarchy, cross-section, width and alignment remain unknown.
- `EP-R1-SKETCH-001` is not complete.
