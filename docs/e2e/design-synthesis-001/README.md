# CASE-SKETCH-001 — Autonomous Design Synthesis 001

Status: **partial autonomous design draft**, not human-confirmed, not a
construction or permit drawing, and not a code-compliance claim.
`EP-R1-SKETCH-001` remains in progress. M4c-0 found a road-topology defect in
this candidate; M4c-1a (0.16.0) diagnosed and fixed it — see below. M4c-1c
(0.17.0) made the evidence semantics honest: checks are pass/info/deferred,
designed green is separated from open space, parking capacity is split from
the requirement, and every design-basis parameter carries provenance with
`confirmed: false`. M4c-1d (0.18.0) tightened this further: `pass` is reserved
for the 5 independently geometry-verified checks, FAR is split into an
arithmetic scenario and a deferred final verification, parking capacity is
named as assumed nominal, open space is dual-measured, and the basis
provenance authentication is `declarative` (a `confirmed: true` state requires
an `approval_ref`).

This is the first round of Milestone 4c. The Agent does not ask the designer to
review sketch geometry. It takes the sketch's spatial intent, makes design
decisions, changes the building/road/green organization, checks the declared
constraints, and produces an editable schematic design — a focus-block detail
sheet plus a site key plan (7 of 55 buildings; 10 of 41 design roads drawn).

## Road-topology defect — found by M4c-0, fixed in M4c-1a

The corridor union of the design roads is one polygon, but a noded centerline
graph of the same 41 design roads read **5 connected components** (51 nodes /
50 edges, `cyclomatic: 0`).

M4c-1a diagnosis: that reading was a **sub-ULP floating-point noding
artefact**, not a design disconnection. Connector endpoints taken from
`shapely.ops.nearest_points()` sat 1.5e-15–2.1e-14 m off the main lines, so
GEOS exact predicates created no node; all 25 main roads were always in one
exact component. The 50-edge count is the simple-graph collapse of the closed
access loop, and `cyclomatic: 0` is momepy's connected-graph formula returning
0 on a disconnected graph.

M4c-1a fix: every junction is an **explicit shared-coordinate vertex** (no
snap, no rounding, no tolerance). The noded centerline graph is now
**1 component**: 51 nodes / 55 segments, cyclomatic 5, dead ends 21,
junctions 27 (16 explicit shared-vertex records in `design-roads.geojson`),
`max_endpoint_gap_m` 0.0. `ROAD_CONNECTIVITY` checks the noded graph and
fails closed within a 1e-9 m endpoint tolerance; sub-1e-9 endpoint
misalignment surfaces first as component count >1. `ROAD_CORRIDOR_COVERAGE`
(corridor union, 1 piece) is published as informational. OSMnx consolidation
(117/141 at 8 m) remains an optional source-skeleton preprocessor — not a
connectivity proof and not the design base.

Evidence: `design-roads.geojson` (41 centerlines + 16 explicit junction
records), `design-consistency.json`, and
`docs/e2e/open-source-reuse-001/exp-c/metrics.json` (historical measurement).

## What the Agent changed

The design is not a trace of the sketch. The Agent:

1. replaced the sketch building footprints with a standardized staircase
   module (24 m × 11 m per staircase, two households per floor, 11 floors,
   132 m² gross per household);
2. reorganized the focus group into rows with **20 m north-south spacing**,
   internal green strips and an access loop;
3. replaced the 333-edge skeleton mesh with a simplified road hierarchy:
   merged main-road alignments, one branch per group and a focus access loop;
4. assigned road widths from the declared class: main 12 m, branch 7 m,
   access 4 m, with a 2 m sidewalk band;
5. allocated green space around the blocks and added two garage entrances to
   meet the parking requirement;
6. adjusted the design so the declared **FAR 1.55–1.60** is met: the standard
   module and 11 floors produce **FAR 1.565**.

The full design diff is in `design-diff.json`. The two focus buildings that do
not fit the buildable block are recorded as dropped
(`SK-BLD-0038`, `SK-BLD-0061`), not silently deleted.

## Design basis (provisional)

| Parameter | Value | Status |
|---|---|---|
| Staircase module | 24 × 11 m (2 households/floor) | provisional design assumption; replaces the pending unit-type library |
| Floors / floor height | 11 / 3.0 m → 33.0 m | design assumption |
| Household gross area | 132.0 m² | design assumption |
| FAR | 1.55–1.60 | **required**; achieved 1.565 = arithmetic scenario (`FAR_ARITHMETIC_SCENARIO`, info); final FAR verification **deferred** (needs confirmed basis + full-site design) |
| Parking | ≥1 space/household; 500 spaces/entrance | entrance count `info` — a count check under a 500-spaces-per-entrance assumption, **not** a capacity result; **assumed nominal capacity 1,000** vs 2,398 required (capacity and layout **deferred**); entrances: 3 existing capacity 0 + 2 proposed capacity 500 |
| North-south spacing | ≥20 m | **required**; focus group 20.0 m |
| Side spacing | 13 m | design assumption |
| Boundary setback | 5 m | design assumption |
| Building-road clearance | 3 m | design assumption |
| Road widths | main 12 m, branch 7 m, access 4 m | design assumption |
| Green | ≥30% designed green | **deferred, not achieved**: designed green ratio 6.6% (13,446 m²; supplementary covers 89.6% of open space); open space is dual-measured — `candidate_open_space_ratio` 63.0% (128,676 m²; classified-area sum with filters 5.0 m setback / 0.5 m obstacle buffer / 100 m² min polygon) and `unbuilt_ratio` 65.3% (133,374 m²; geometric union). Both ratios use the full published site area as denominator; the filtered/unbuilt areas are measured inside the 5 m setback boundary. Neither is designed green. |
| Drawing standard | `DGCAD-SCHEMATIC-001` | internal schematic standard |

The basis is `design-basis.yaml` (`design-assumption-v0.2`, 0.2.0): 21
parameters with per-parameter provenance — 5 `declared_requirement`,
2 `designer_stated`, 3 `inferred_from_sketch`, 11 `agent_assumption` —
**all `confirmed: false`**; the Agent cannot self-confirm them. Provenance
authentication is `declarative` (declared, not certified): a `confirmed: true`
state requires an `approval_ref`. Changing the basis and re-running regenerates
the design; the designer does not need to re-review the sketch.

## Full-site context and focus block

The full site contains 55 building candidates, 109 staircase units, one
kindergarten/facility, 333 source road edges, 12 cluster greens and 3 garage
entrances. The full-site metrics use all 109 staircases:

- 2,398 households;
- 319,536 m² total GFA (316,536 residential + 3,000 facility);
- FAR 1.565 (design-basis arithmetic);
- parking requirement 2,398 spaces (basis arithmetic; recorded capacity 1,000, deferred) and 5 garage entrances (3 existing + 2 proposed).

The detailed design is the focus block G-01: **7 buildings / 16 units / 352
households**. The block is selected from the main-road-bounded free space; it
is large enough for the 20 m row spacing and road clearance. The full-site
building layout remains coarse context; **full-site north-south spacing is
recorded as deferred**, to be extended group by group.

## Plan and CAD output

`design-proposal.dxf` (208 entities, audit 0/0, readback 208/208 pass):

- layers: site boundary, building outline, unit line, main/branch/access road,
  sidewalk, green, entrance, dimensions, title, legend, north, scale, key plan;
- 7 standardized buildings with unit division lines, unit counts, households,
  height and dimensions;
- main/branch/access road corridors and centerlines with width labels;
- green strips and cluster green;
- garage entrance marker;
- 20 m north-south dimension, overall plan dimensions, key plan,
  title block, legend, north arrow and scale bar.

The design objects are `rule_derived` in the `proposal_preview` world. DXF
XDATA and the readback manifest carry `confirmation_scope: design_draft`.
No object is `human_confirmed`, and the title block says
"AGENT-GENERATED PROPOSAL - NOT HUMAN-CONFIRMED - NOT CODE-COMPLIANCE".

CAD-IR validation is `pass_with_scope_limits`: the seven building heights are
declared design values in the `proposed` state, so the validator emits seven
`UNKNOWN_HEIGHT_ALLOWED` warnings. This is deliberate: the draft does not
pretend that the height is human-confirmed.

## How to inspect

1. Open `design-preview.png` for a quick raster preview.
2. Open `design-proposal.dxf` in a CAD editor (units: metre, R2010, modelspace).
3. Read `design-summary.json`, `design-consistency.json` and `design-diff.json`
   for the metrics and the changes.
4. If the design direction is useful, edit the DXF directly or ask the Agent
   to revise the basis and regenerate. No sketch review is required.

## Reproduce

```bash
python scripts/design/run_design_synthesis_001.py
python -m pytest -q tests/test_design_synthesis.py
```

The preview PNG is a convenience image, not the deliverable. The committed
tree contains no script that renders it (matplotlib is not a declared
dependency), so treat it as illustrative rather than reproducible output.

## Evidence files

- `design-basis.yaml`, `design-profile.yaml`
- `design-intent.json` — groups, road hierarchy, focus block, principles
- `design-summary.json` — status, metrics, checks, CAD/readback/privacy
- `design-consistency.json` — all declared checks; connectivity is the noded
  centerline graph (`ROAD_CORRIDOR_COVERAGE` is the informational corridor measure)
- `design-diff.json` — what changed, why, what was preserved, what was dropped
- `design-roads.geojson` — the 41 design roads as committed evidence:
  41 centerlines + 16 explicit junction records (id/x/y/road_ids)
- `draft-manifest.json` — persistent autonomous draft, revision 1
- `scene-snapshot.json` — proposal-preview design objects
- `design-proposal.dxf`, `cad-ir.json`, `readback-manifest.json`,
  `validation.json`, `privacy.json`
- `design-preview.png`

## Non-claims

- This is a schematic design proposal, not a construction or permit drawing.
- No Chinese code, fire-access, daylight or accessibility compliance is claimed.
- The unit module is a provisional design assumption, not the designer's unit
  library.
- The published sketch boundary is used; the private redline remains
  authoritative.
- Road corridors are schematic offsets, not professional alignment or junction
  design; the 121-junction review is not continued.
- The underground garage layout is not designed; only the entrance requirement
  is checked.
- The full-site north-south spacing is not yet enforced; the focus block is.
- `EP-R1-SKETCH-001` is not complete.
