# CASE-SKETCH-001 — Autonomous Design Synthesis 001

Status: **partial autonomous design draft**, not human-confirmed, not a
construction or permit drawing, and not a code-compliance claim.
`EP-R1-SKETCH-001` remains in progress. M4c-0 found a road-topology defect in
this candidate; M4c-1a (0.16.0) diagnosed and fixed it — see below. M4c-1c
(0.17.0) made the evidence semantics honest: checks are pass/info/deferred,
designed green is separated from open space, parking capacity is split from
the requirement, and every design-basis parameter carries provenance with
`confirmed: false`. M4c-1d (0.18.0) tightened this further: `pass` is reserved
for the independently geometry-verified checks, FAR is split into an
arithmetic scenario and a deferred final verification, parking capacity is
named as assumed nominal, open space is dual-measured, and the basis
provenance authentication is `declarative` (a `confirmed: true` state requires
an `approval_ref`). M4c-1b (0.19.0) made the first design-geometry change:
the network grew to **44 design roads** and all 17 groups are served — see
below. M4c-1e (0.20.0) bound road access to **declared** service relations
(`serves_group_ids` + `access_terminal_xy`), made the main-road overlap and
full-site road clearance machine-checked deferred items, split parking
proximity from driveway design, and changed no design geometry (25 checks =
6 pass + 10 info + 9 deferred; DXF content unchanged). M4c-2 (0.21.0) made the
real alignment change: M4c-2's MAIN-19 diversion and MAIN-08 local detour
removed the 38.1907 m² main-road/building overlap, the 7 unresolved dead ends
were resolved, and the DXF content became 211 entities. Phase 0 (0.22.0) then
corrected the evidence: alignment semantics are **`local_search_exhausted`** (the
66.235 m diversion is a candidate baseline, not a proof of optimality),
site-boundary containment is a hard check (`ROAD_BOUNDARY_CONTAINMENT` pass;
margin 0.6735131264650868; MAIN-08/16/18 repairs — the remaining MAIN-08 conflict
is resolved by the boundary repair), the geojson overlap fields are split
(`main_before` 38.19068149970835 → `main_after` 0.0; `new_access`
0.9943558185246757; `total_after` 0.9943558185246756), and `source_segment_map`,
design-diff alignment/dead-end records, `criterion_met`-verified dead-end
resolutions and regenerated preview/overlay are published. The base draft now
has **27 checks = 9 pass + 11 info + 7 deferred (+3 DXF = 30)**, **58 nodes /
68 edges / cyclomatic 11**, DXF **211 entities** and **396 tests**. M4c-3
(0.22.0) adds the first **multi-candidate experiment** (A/B1/B2/C), documented in
`docs/e2e/design-candidates-001/`: all four pass the hard gates; the default
preference recommends **B1**, road-first recommends **A**, and no single score is
produced. B1 is only the M4c-2 diversion candidate baseline.

This is the first round of Milestone 4c. The Agent does not ask the designer to
review sketch geometry. It takes the sketch's spatial intent, makes design
decisions, changes the building/road/green organization, checks the declared
constraints, and produces an editable schematic design — a focus-block detail
sheet plus a site key plan (7 of 55 buildings; only the design-road
centerlines inside the plan box are drawn).

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

Evidence (as measured at M4c-0 time): `docs/e2e/open-source-reuse-001/exp-c/metrics.json`; the current `design-roads.geojson` (44 centerlines + 24 junction records) supersedes the 41/16 counts.

## Road service coverage — added in M4c-1b, bound to declared relations in M4c-1e

M4c-1b (0.19.0) made the first design-geometry change: the network grew from
41 to **44 design roads** (25 main × 12 m + 17 branch × 7 m + 2 access × 4 m)
and every group is served. M4c-1e (0.20.0) changed no geometry but bound the
evidence to explicit service relations:

- Road access coverage **1.0 — 17/17 groups** (`ROAD_ACCESS_COVERAGE` pass).
  Each group has exactly one **declared** access road (`serves_group_ids` +
  `access_terminal_xy`): 17 group-access roads = 16 branch + `ACC-G-12`
  (G-08 → BR-G-08, G-13 → BR-G-13, G-12 → ACC-G-12); `BR-FOCUS` and the focus
  access loop are network connectors, so there are 19 connector roads
  (17 branch + 2 access) in total. The previous nearest-endpoint attribution
  (G-08 to BR-G-09, G-13 to BR-G-07) is removed.
- The declared terminal **centreline** distance is in the [3.4, 3.5] m band
  (min 3.497987 m), outside every footprint, with 0.0 m route crossing and zero
  relation errors/orphans. The separate `terminal_corridor_edge_clearance_m`
  is published per group (0.0 m for a 7 m branch end-cap, ~1.5 m for the 4 m
  `ACC-G-12` lane) — this is not the 3.0 m corridor setback.
- New-access/building overlap is **0.9943558185246757 m²** (total_after
  0.9943558185246756; an earlier pre-Phase-0 value is superseded); the ≤1.0 m² budget
  applies only to new group-access roads.
- Dead ends: the 7 previously unresolved items are **resolved** (2 trimmed,
  3 bridged, 2 site-edge termini; `DEAD_END_RESOLUTION` pass, 0 unresolved,
  each bound to `criterion_met` plus a geometry re-check). The 19 remaining
  dead ends are 17 planned group terminals + 2 site-edge termini
  (`DEAD_END_JUSTIFICATION` info, 17/19).
- Parking is **proximity only** (`PARKING_ENTRANCE_PROXIMITY` info): 2 of 5
  garage entrances are near a design road, the 3 existing garage positions are
  area markers **18.83–25.71 m** from the carriageway; no driveway is designed
  (`PARKING_DRIVEWAY_CONNECTION` deferred).
- The **main-road/building overlap is resolved**:
  `main_before` 38.19068149970835 → `main_after` **0.0 m²**
  (`MAIN_ROAD_BUILDING_OVERLAP` pass; details in the alignment section below).
  Full-site road clearance remains deferred (`FULL_SITE_ROAD_CLEARANCE`); the
  access loop crosses no building.
- Topology after Phase 0: **1 component, 58 nodes / 68 segments, cyclomatic 11,
  19 dead ends, 36 junctions (24 explicit), closed rings 3,
  `max_endpoint_gap_m` 0.0**. Evidence: `design-roads.geojson` (44 centerlines
  + 24 junction records) publishes `serves_group_ids`/`access_terminal_xy`,
  split overlap fields, `main_boundary_repairs`, `source_segment_map` (25 roads),
  main-alignment and dead-end-resolution records; its SHA-256 is `a8c1baf5…`.

## Main-road alignment and Phase 0 — added in M4c-2, corrected in 0.22.0

M4c-2 (0.21.0) removed the known conflict. Phase 0 (0.22.0) corrected the
evidence and added boundary containment; road ids, source edges and widths are
still preserved:

- **MAIN-19 / SK-BLD-0006**: **diversion**; overlap 34.421783197612406 → 0 m²;
  max displacement **66.23545861756293 m**; +29 vertices. Phase 0 semantics are
  **`local_search_exhausted`**, not "infeasible": the 11.565220076201857 m gap
  between SK-BLD-0006 and SK-BLD-0029 only proves the **between-buildings
  passage** infeasible; the limited local search family found no
  end-point-preserving local solution, and the 66.235 m diversion is a
  **candidate baseline, not a proof of optimality**.
- **Site-boundary containment** is a hard check (`ROAD_BOUNDARY_CONTAINMENT`
  pass; margin **0.6735131264650868**; tolerance 0.01 m). Three source overhangs
  were repaired and recorded: **MAIN-08** outside 341.6908310814502 → 0 m²
  (margin 2.446306837399009; max vertex displacement 44.1586496117478;
  14 → 108 vertices), **MAIN-16** 2.417804558565924 → 0 m² (margin
  0.7176286428079739) and **MAIN-18** 8.290901115044374 → 0 m² (margin
  0.6735131264650868).
- Overlap fields are split and labelled: `main_before` **38.19068149970835**
  (the original known conflict: MAIN-19 34.42 + MAIN-08 3.77), `main_after`
  **0.0**, `new_access` **0.9943558185246757**, `total_after`
  **0.9943558185246756**. After the MAIN-08 boundary repair the remaining main
  conflict was 34.421783197612406 → 0; `MAIN_ROAD_BUILDING_OVERLAP` pass
  (remaining ≤ 0.01 m²), `ROAD_ALIGNMENT_EVIDENCE` info (1 record: MAIN-19,
  source edges/original-adjust centreline/displacement/vertex budget).
  `source_segment_map` covers 25 roads. Main length **2,107.733378663747 m**;
  road area 26,882.20505326313 m²; sidewalk 9,764.76834535878 m²; 44 roads
  (25 main / 17 branch / 2 access); access stays 17/17 declared.
  `main_before` includes the original MAIN-08 **3.768898302095937 m²** overlap
  whose alignment record was replaced by the boundary repair, so
  **Σ `alignment_records.overlap_before` = 34.421783197612406 m²**; the
  3.768898302095937 m² difference is published as
  `road_building_overlap_m2_boundary_replaced_before` in the final evidence
  (cross-checked: `main_before` = alignment-records before + boundary-replaced
  before). The overlay's "before" layer uses the alignment records'
  original/adjusted centrelines, not a full pre-M4c-2 history.
- **7 dead ends resolved**: MAIN-03 trimmed 9.727353166421203 m; MAIN-05
  trimmed 0.24620779365789502 m; MAIN-09 bridged to MAIN-08
  13.677655946265997 m; MAIN-20 bridged to MAIN-19 5.233264199174163 m;
  MAIN-22 bridged to MAIN-08 9.642090864979577 m; **MAIN-18** site-edge
  terminus lies 4.047925766932525 m from the boundary **within the ≤5 m
  site-edge band** (no extension; the source network is clipped at the published
  boundary, so no source vertex lies outside); **MAIN-25** extended
  5.643487350037444 m **along the shortest direction to the published boundary
  (not collinear with the terminal segment)**; each resolution is bound to
  `criterion_met` plus a geometry re-check.
- Scope of the alignment claim: the adjustment eliminates the **known** overlaps
  and keeps the main corridors inside the site boundary. It does **not** claim
  that all 25 main roads satisfy the 3.0 m corridor clearance — the unadjusted
  main roads' minimum corridor clearance is about **1.229 m**, and full-site road
  clearance (`FULL_SITE_ROAD_CLEARANCE`) remains deferred.

## Multi-candidate experiment — added in M4c-3

`docs/e2e/design-candidates-001/` holds the first controlled multi-candidate
decision experiment for the MAIN-19 / SK-BLD-0006 / SK-BLD-0029 conflict. Change
metrics are measured against the **raw source-aligned design**
(`alignment_mode='none'`; main-length baseline 1,984.2812597774587 m; reference
total overlap 36.20414480381279 m²), not against the already-aligned base.

| id | strategy | hard | total overlap | road max disp | main length | building shift |
|---|---|---|---|---|---|---|
| A | road_priority | pass | 0.8595377847886573 m² | 2.825827798091072 m | 1,981.9609886916392 m | SK-BLD-0006 3.1720857962227718 m |
| B1 | building_priority_diversion | pass | 0.9943558185246756 m² | 66.23545861756291 m | 2,107.733378663747 m | 0 |
| B2 | building_priority_alternate | pass | 0.9943558185246756 m² | 71.7722361902286 m | 2,115.0219491017956 m | 0 |
| C | coordinated | pass | 0.8595377847886573 m² | 76.69965271965492 m | 1,995.4961054524852 m | SK-BLD-0006 1.5 m |

All four pass the hard gates (**main-road overlap ≤ 0.01 m²; total
road/building overlap ≤ the boundary-safe reference 0.86–0.99 m²**; 1 noded
component; corridor inside the boundary with margin 0.6735131264650868; access
17/17 declared; capacity and basis unchanged). The **default preference**
(building change → road change → source preservation → green change) recommends
**B1**; the **road-first preference** recommends **A**. The default Pareto front
is [B1,B2,C,A], every candidate has a reason, and **no single opaque score** is
produced. B1 is only the M4c-2 diversion as a candidate baseline — not the
selected or professional design, the candidate set is not exhaustive, and no
candidate is human-confirmed or code-compliant.

## What the Agent changed

The design is not a trace of the sketch. The Agent:

1. replaced the sketch building footprints with a standardized staircase
   module (24 m × 11 m per staircase, two households per floor, 11 floors,
   132 m² gross per household);
2. reorganized the focus group into rows with **20 m north-south spacing**,
   internal green strips and an access loop;
3. replaced the 333-edge skeleton mesh with a simplified road hierarchy:
   merged main-road alignments, group branch connectors and a focus access loop;
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
| Parking | ≥1 space/household; 500 spaces/entrance | entrance count `info` — a count check under a 500-spaces-per-entrance assumption, **not** a capacity result; **assumed nominal capacity 1,000** vs 2,398 required (capacity and layout **deferred**); entrances: 3 existing capacity 0 + 2 proposed capacity 500. M4c-1e split the claim: `PARKING_ENTRANCE_PROXIMITY` (info; 2 of 5 near a design road) is not a connection; `PARKING_DRIVEWAY_CONNECTION` is **deferred** because no driveway/apron is designed (`driveway_designed: false` for all entrances) |
| North-south spacing | ≥20 m | **required**; focus group 20.0 m |
| Side spacing | 13 m | design assumption |
| Boundary setback | 5 m | design assumption |
| Building-road clearance | 3 m | design assumption |
| Road widths | main 12 m, branch 7 m, access 4 m | design assumption |
| Green | ≥30% designed green | **deferred, not achieved**: designed green ratio 6.54% (13,346.693042679242 m²; supplementary covers 89.6% of candidate open space); open space is dual-measured (re-measured after the Phase-0 geometry change) — `candidate_open_space_ratio` 61.6391% (125,819.46553768215 m²; classified-area sum with filters 5.0 m setback / 0.5 m obstacle buffer / 100 m² min polygon) and `unbuilt_ratio` 64.0735% (130,788.70473514873 m²; geometric union). Both ratios use the full published site area as denominator; the filtered/unbuilt areas are measured inside the 5 m setback boundary. Neither is designed green. |
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
- parking requirement 2,398 spaces (basis arithmetic; recorded capacity 1,000, deferred), 5 garage entrances (3 existing + 2 proposed), entrance proximity 2/5 and no driveway design (`PARKING_DRIVEWAY_CONNECTION` deferred).

The detailed design is the focus block G-01: **7 buildings / 16 units / 352
households**. The block is selected from the main-road-bounded free space; it
is large enough for the 20 m row spacing and road clearance. The full-site
building layout remains coarse context; **full-site north-south spacing is
recorded as deferred**, to be extended group by group.

## Plan and CAD output

`design-proposal.dxf` (**211 entities** in the Phase-0 base; was 206 in 0.20.0 and 208 before M4c-1b; audit 0/0, readback 211/211 pass). Phase 0 changed the content (boundary repairs/alignment; still 211 entities); the file byte SHA-256 also changes per save because ezdxf regenerates `$TDUPDATE`/GUIDs (0.19.0 `34a65926…`, 0.20.0 `fcc42d32…`, 0.21.0 `0f76c006…`, 0.22.0 `65fde1ca…`) — compare content, not bytes:

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
python scripts/design/render_visuals.py --output-dir docs/e2e/design-synthesis-001
python scripts/design/build_candidate_experiment.py
python -m pytest -q tests/test_design_synthesis.py tests/test_main_alignment.py
```

Visuals are generated from the current evidence by
`scripts/design/render_visuals.py`: `design-preview.svg` and
`design-overlay.svg` are always written; `design-preview.svg`/`.png` are the same
scene and the PNG is refreshed only when matplotlib is importable (the project
adds no dependency). Candidate evidence is regenerated by
`build_candidate_experiment.py`; one candidate can be turned into an editable
DXF with `run_candidate_synthesis.py --candidate-id <id>` when the model exposes
design elements (otherwise the summary records `dxf: pending_interface`).

## Evidence files

- `design-basis.yaml`, `design-profile.yaml`
- `design-intent.json` — groups, road hierarchy, focus block, principles
- `design-summary.json` — status, metrics, checks, CAD/readback/privacy
- `design-consistency.json` — all 27 declared checks (9 pass / 11 info / 7
  deferred, M4c-3) plus 3 DXF checks = 30; connectivity is the noded centerline
  graph (`ROAD_CORRIDOR_COVERAGE` is the informational corridor measure); group
  access is the declared `serves_group_ids` relation; site-boundary containment
  (`ROAD_BOUNDARY_CONTAINMENT`) and the split main-overlap evidence are included
- `design-diff.json` — what changed, why, what was preserved, what was dropped;
  includes `road_alignment` and `dead_end_resolutions` and lists them in
  `changed`/`why`
- `design-roads.geojson` — the 44 design roads as committed evidence:
  44 centerlines + 24 explicit junction records (id/x/y/road_ids) + per-road
  `serves_group_ids`/`access_terminal_xy`, `group_access` (17 declared
  relations), split overlap fields (`main_before` 38.19068149970835,
  `main_after` 0.0, `new_access` 0.9943558185246757, `total_after`
  0.9943558185246756), `main_boundary_repairs` (3), `source_segment_map`
  (25 roads), `main_alignment_records` (1: MAIN-19) and
  `dead_end_resolution_records` (7 resolutions bound to `criterion_met` and a
  geometry re-check); SHA-256 `a8c1baf5…`
- `draft-manifest.json` — persistent autonomous draft, revision 1
- `scene-snapshot.json` — proposal-preview design objects
- `design-proposal.dxf`, `cad-ir.json`, `readback-manifest.json`,
  `validation.json`, `privacy.json`
- `design-preview.svg`, `design-preview.png`, `design-overlay.svg` (generated by
  `scripts/design/render_visuals.py`)
- The multi-candidate evidence lives in `../design-candidates-001/`
  (`candidates.json`, `evaluation.json`, `comparison.svg`, per-candidate
  `candidate-summary.json`/`plan.svg`/`design-consistency.json`/`design-roads.geojson`).

## Non-claims

- This is a schematic design proposal, not a construction or permit drawing.
- No Chinese code, fire-access, daylight or accessibility compliance is claimed.
- The unit module is a provisional design assumption, not the designer's unit
  library.
- The published sketch boundary is used; the private redline remains
  authoritative.
- Road corridors are schematic offsets. The M4c-2 MAIN-19 diversion and the
  Phase-0 MAIN-08/16/18 boundary repairs are schematic centreline adjustments
  made to clear footprints and stay inside the published boundary; they are not
  professional alignment, junction, profile or horizontal/vertical design, and
  the 121-junction review is not continued. `local_search_exhausted` only
  reports the limit of the limited local search family, not a proof of
  optimality.
- The alignment claim is zero remaining known overlap and boundary containment,
  not that all 25 main roads meet the 3.0 m corridor clearance (unadjusted
  minimum ≈1.229 m).
- The underground garage layout and driveways are not designed; entrance
  proximity is not a connection (`PARKING_ENTRANCE_PROXIMITY` info,
  `PARKING_DRIVEWAY_CONNECTION` deferred).
- Dead ends are all classified: the 7 previously unresolved items are resolved
  (`DEAD_END_RESOLUTION` pass, 0 unresolved); 19 remain = 17 planned group
  terminals + 2 site-edge termini.
- The main-road/building overlap is **resolved** (`MAIN_ROAD_BUILDING_OVERLAP`
  pass; `main_before` 38.19068149970835 → `main_after` 0.0 m²); full-site road
  clearance is still deferred (`FULL_SITE_ROAD_CLEARANCE`).
- The multi-candidate experiment is a decision aid: B1 is only the M4c-2
  diversion as a candidate baseline, the candidate set is not exhaustive, no
  candidate is human-confirmed or code-compliant, and the soft objectives are
  not a complete quality model.
- The full-site north-south spacing is not yet enforced; the focus block is.
- `EP-R1-SKETCH-001` is not complete.
