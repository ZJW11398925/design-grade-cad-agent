# Changelog

All notable changes to the formal repository are recorded here. Research snapshots keep their own versions in `research/archive/`.

## 0.24.0 — 2026-10-29

### Added

- **M4d-1 — full-site layout engine, full-site checks, and an experimental
  full-site sheet.** A new `layout_full_site` packs **all 55 buildings** into a
  regularized full-site layout against the frozen 44-road design network
  (**18 rows / 8 superblocks / 36 row records**, row ordinals contiguous
  1..18, adjacent-row pitch 31.0 m), preserving **109 units / 2,398
  households** and the focus group G-01 (7 buildings / 16 units). Measured
  geometry: all footprints inside the declared boundary-setback; pairwise
  overlap ≤ 0.01 m²; adjacent 20 m rows (min **19.999999999999943 m**, 44
  adjacent pairs, 0 under/over); 3 m building-road clearance (min
  **3.0163622902759215 m**); source→design displacement sum **2,328.95 m**,
  max **147.25 m**, mean **42.34 m**.
- **New full-site checks** in contract `design-synthesis-v0.9` (**32 entries =
  29 design + 3 DXF**; v0.8 superseded): `FULL_SITE_BOUNDARY_SETBACK`,
  `FULL_SITE_BUILDING_OVERLAP`, `FULL_SITE_ROAD_CLEARANCE`,
  `FULL_SITE_NS_SPACING` and a computable `DESIGNED_GREEN_RATIO`. Full-site
  checks are **deferred** while the default pipeline still uses the focus
  layout (no full-site `row_index`), never silently passing; the default focus
  design now reports **29 checks = 9 pass + 11 info + 9 deferred**.
- **Full-site experimental sheet** `docs/e2e/design-synthesis-full-site-001/`:
  `full-site-layout`, DXF **547 entities** (all 55 buildings), readback
  **547/547**, XDATA 11, privacy pass, preview SVG/PNG and a 29-check report
  (**11 pass + 11 info + 5 deferred + 2 fail**).
- **Honest integration gap:** the frozen access network was declared for the
  focus layout, so the full-site layout fails `ROAD_ACCESS_COVERAGE`
  (0.0; 17 relation errors) and `DEAD_END_RESOLUTION` (17 unresolved).
  Regenerating the road network from the full-site layout does not fix it — it
  breaks `FULL_SITE_ROAD_CLEARANCE` (min 0 m; 17 buildings below 3 m). M4d-2
  must co-design road geometry and declared access before the full-site sheet
  can become canonical. The focus design remains the canonical draft; the
  full-site sheet is a **research draft**, not a complete or professional
  design.
- **Designed-green honesty:** the new full-site green account
  (0.6105795566533792; 124,633.20 m²; 10 parcels of open space outside
  buildings/roads/sidewalks) is published as an **auxiliary open-space
  tiling**, not as designed green. Designed green (cluster strips /
  supplementary) is 0.0654 on the focus sheet and 0.1593 on the full-site
  sheet, both below the declared 0.30 target, so `DESIGNED_GREEN_RATIO` stays
  **deferred** and reports both accounts separately.

### Verified

- Full test suite: **467 passed** (414 → 467: 16 full-site layout tests, 25
  full-site constraint tests, 12 full-site evidence tests; no test removed).
- Independent verification by `site-verifier` (55-building conservation,
  geometry, clearance/spacing, access-gap honesty, green-account honesty,
  DXF/readback/privacy) and contract checks; CI 4/4.

## 0.23.0 — 2026-10-29

### Fixed

- **M4c-3a — evaluation integrity for the multi-candidate experiment.** This is
  a bounded semantic fix (no architecture/CAD-IR change) for the five review
  findings on M4c-3. Version 0.23.0; contract
  `design-candidates-v0.2.yaml` (v0.1 superseded); `design-synthesis-v0.8`
  unchanged.

  - **Unified geometry-change evidence (P1-a).** The candidate change record
    now compares **all 44 roads** (main, branch and access) against the
    boundary-safe source reference: per road `kind`
    (trim/extend/length_change/reroute/replace), length delta, max vertex
    displacement, symmetric Hausdorff distance, removed/added length; per class
    max deviation; and per-group terminal before/after/delta. This exposes the
    effects the previous main-road-only record missed:
    - **A** moves SK-BLD-0006 3.172 m, which re-routes **BR-G-08 by 2.826 m**
      (G-08 terminal shifts 2.826 m);
    - **B1/B2** keep all buildings and divert MAIN-19 (66.235 / 71.772 m); the
      attached **BR-G-09 follows by 7.352 / 13.645 m** (G-08 stays 0);
    - **C** moves SK-BLD-0006 only 1.50 m but re-routes **BR-G-08 by
      76.700 m** and shifts the **G-08 terminal by 75.315 m** — C is not a
      small local change; its candidate description now says so explicitly.
    The evaluator independently recomputes the same per-class quantities from
    geometry (candidate self-reports are not trusted).
  - **Historical boundary archive (P1-b).** The previous
    `KNOWN_BOUNDARY_VIOLATIONS` wrongly attached 66.235 m (a MAIN-19 diversion)
    to MAIN-08. It is replaced by `HISTORICAL_BOUNDARY_ARCHIVE`:
    MAIN-19 / M4c-2 main-road diversion (66.23545861756293 m,
    resolved by the final alignment) and the M4c-3 source-corridor boundary
    repairs MAIN-08/16/18 (outside areas 341.6908310814502 / 2.417804558565924 /
    8.290901115044374 m²). Tests associate the numbers with the actual
    geometry, not just the fields. The current B1 candidate is the
    boundary-repaired version (margin 0.6735131264650868 m) and is judged only
    on its own geometry; the pre-repair form is archival.
  - **Basis binding (P1-c).** Every candidate now carries
    `parent_basis_id = design-assumption-v0.2` and a canonical
    `basis_fingerprint = sha256(json.dumps(basis.to_dict(), sort_keys=True,
    separators=(",",":")))` (2a2d7807…). `basis_ok` **fails** when either is
    missing or mismatched — a candidate without basis identity is never a hard
    pass — and both fields are published in `candidates.json` and each
    candidate summary.
  - **Explicit single-unit objectives (P2).** The mixed-unit composites
    (building count + metres; main length + deviation) are removed. The Pareto
    front and preference comparison now use eleven independent objectives:
    `building_count_change`, `building_displaced_count`,
    `building_displacement_max_m`, `main_length_delta_abs_m`,
    `main_route_deviation_max_m`, `branch_access_route_deviation_max_m`,
    `access_terminal_max_delta_m`, `source_preservation_coverage`,
    `source_preservation_distance_m`, `source_preservation_heading_deg`,
    `green_designed_ratio_delta`. Auxiliary diagnostics (green open-space /
    unbuilt deltas, GFA/FAR invariants, added vertices, group-integrity detail)
    are reported but **never enter the Pareto front or the preference
    comparison**; the candidate README table has one column per objective.
    The default preference order is building-count → displaced-count →
    building-displacement → access-terminal → main-route-deviation →
    main-length-delta → source coverage → designed-green (rationale in
    `DEFAULT_PRIORITY_RATIONALE`); the road-first order starts from route
    deviation/length and leaves building displacement late.
  - **Re-run decisions.** Evidence regenerated
    (`docs/e2e/design-candidates-001/`, schema v0.2): all four candidates still
    pass the hard gates; the default preference recommends **B1** and the
    road-first preference recommends **A**; the Pareto front remains
    **[B1, B2, C, A]**. C remains non-dominated on the explicit objectives, but
    its BR-G-08 / G-08 numbers (76.700 / 75.315 m) are now visible in the table
    and candidate description rather than hidden behind a 1.5 m building shift.

### Verified

- New targeted tests cover: wrong historical road association (MAIN-19 vs
  MAIN-08), change-record vs evaluator consistency (BR-G-08), large access
  terminal movement, missing/mismatched basis fingerprint, and objective
  single-sourcing/auxiliary exclusion.
- Full test suite: **414 passed** (`python -m pytest -q`; 396 → 414: new
  candidate geometry-change tests, evaluation/contract v0.2 tests, basis-binding
  and negative tests; no test removed).
- Independent reviews: `arch-core` (candidate contract/evaluation), `adversary`
  (adversarial verification of the five fixes), `docs` checks; CI 4/4.

## 0.22.0 — 2026-10-29

### Changed

- **M4c-3 — first multi-candidate design-decision experiment.** This release
  fixes the M4c-2 evidence issues, adds site-boundary containment as a hard
  check, and runs the first controlled design experiment: four candidate
  solutions to the MAIN-19 conflict, independently evaluated with hard gates,
  soft objectives and a Pareto/preference decision (no opaque score). Tests
  347 → **396**.

  - **Phase 0 corrections (from review):**
    - `local_detour_infeasible` is replaced by the honest
      `local_search_exhausted` wording: the recorded 11.565 m gap < 12 m
      corridor only proves that the **between-buildings passage** is
      infeasible; the limited local search family found no end-point-preserving
      local solution. The M4c-2 66.235 m diversion remains a candidate
      baseline, not a proof of optimality.
    - **Boundary containment is now a hard check** (`ROAD_BOUNDARY_CONTAINMENT`,
      27 design checks = 9 pass + 11 info + 7 deferred; contract
      `design-synthesis-v0.8.yaml`, v0.7 superseded): main-road corridor edge
      (centreline ± width/2) must lie inside the published site boundary
      (tolerance ≤ 0.01 m). The base design was repaired accordingly:
      MAIN-08/16/18 corridor overhangs fixed (MAIN-08 341.69 m² → 0, margin
      2.446 m), MAIN-19 diversion retained and boundary-compliant.
    - `design-roads.geojson` overlap fields are split and labelled:
      `main_before` (38.1907 m² known conflict), `main_after` (0.0),
      `new_access` and `total_after` (0.9944 m² — access-road overlap after
      the boundary repairs), plus the split `alignment_records_before`
      (34.4218 m²) / `boundary_replaced_before` (3.7689 m²) fields,
      with a cross-consistency test. `source_segment_map` (design road →
      source main-edge segments, coverage/distance/heading) and
      `main_boundary_repairs` are published.
    - `design-diff.json` now records the main-road alignment and dead-end
      resolutions in `road_alignment` / `dead_end_resolutions`, and lists them
      in `changed` / `why`.
    - Dead-end `resolved` is bound to `criterion_met is True` **and** a
      geometry re-check (trimmed→no longer degree-1; bridged→shared-vertex
      junction and no building crossing; site-edge→inside the ≤5 m band and no
      source vertex outside), with negative tests for forged/unmet records.
    - Visuals are regenerated from the current geometry:
      `design-preview.svg`/`.png` (55 buildings, 44 roads, 27 greens, legend,
      north arrow, scale bar) and `design-overlay.svg` (MAIN-08/MAIN-19
      before/after + displacement), replacing the stale M4c-1 PNG.
  - **First candidate experiment (MAIN-19 / SK-BLD-0006 / SK-BLD-0029):**
    four deterministic candidates from the same source, basis and evidence,
    with soft metrics measured against the **raw source-aligned design**
    (`alignment_mode="none"`), not against the already-aligned M4c-2 base:
    - **A road priority** — original main alignment, SK-BLD-0006 shifted
      3.172 m; road max displacement 2.83 m; main length 1,981.96 m.
    - **B1 building priority (M4c-2 diversion)** — buildings fixed, MAIN-19
      diversion 66.235 m; main length 2,107.73 m.
    - **B2 building priority (alternate)** — buildings fixed, a different
      diversion fold, 71.772 m main displacement; main length 2,115.02 m.
    - **C coordinated** — SK-BLD-0006 shifted 1.50 m plus a medium local road
      adjustment (11.99 m retract-and-bridge on MAIN-15); main length
      1,995.50 m.
    All four pass the hard gates (overlap ≤ 0.01 m², one noded component,
    corridor inside the site boundary, access 17/17 declared, 55 buildings /
    109 units, 2,398 households) and all four are non-dominated on the soft
    objectives. **Decision:** under the default building-preservation-first
    preferences the recommendation is **B1**; under road-first preferences it
    is **A** — the explicit trade-off is published instead of a single score.
    The M4c-2 66.235 m diversion is recorded as a **known boundary-violating
    baseline** prior to its boundary-compliant repair; it is a candidate, not
    the predetermined answer.
  - **Independent evaluation** (`evaluation.py`, contract
    `design-candidates-v0.1.yaml`): hard gates are re-computed from geometry
    (candidate self-reports are ignored); soft objectives cover source-trend
    preservation (via `source_segment_map`), road change, building change,
    group integrity, green change and space utilization. `compare()` applies
    explicit ordered preferences and reports the Pareto front plus a reason for
    every candidate; no single black-box score is produced.
  - Evidence: `docs/e2e/design-candidates-001/` (candidates, per-candidate
    summary/plan, evaluation.json, comparison.svg, README with recommendation
    and rejected alternatives); base design evidence regenerated (DXF content
    changes, 211 entities, audit 0/0, readback 211/211, XDATA 11, privacy pass;
    `design-roads.geojson` SHA-256 changes; main length 2,107.733 m; road area
    26,882.21 m²; sidewalk 9,764.77 m²; open space candidate 61.64 % / unbuilt
    64.07 % / designed green 6.54 % deferred).

### Verified

- **396 passed** (`python -m pytest -q`; 347 → 396: boundary repairs,
  candidates, independent evaluation, candidate contract, visuals, phase-0
  negative tests and geometry re-baselines; no test removed).
- Independent reviews: `arch-core` candidate-contract/evaluation consistency;
  `adversary` adversarial verification of candidate independence, hard-gate
  recomputation and decision honesty; `cad-pipeline` visuals/evidence chain.

## 0.21.0 — 2026-10-28

### Changed

- **M4c-2 — main-road alignment and dead-end resolution.** Real design-geometry
  change: the known main-road/building conflicts are removed by recorded
  alignments, and the 7 unresolved dead ends are resolved. Tests 334 →
  **347**.

  - **MAIN-19 / SK-BLD-0006 (34.42 m²)**: a local detour is provably
    infeasible (the gap between SK-BLD-0006 and SK-BLD-0029 is 11.565 m, less
    than the 12 m corridor), so the road is diverted around the combined
    clearance envelope: 0.0 m² overlap after, **66.235 m** maximum displacement,
    `alignment_strategy: diversion`, `local_detour_infeasible: true`, with the
    gap proof recorded.
  - **MAIN-08 / SK-BLD-0038 + SK-BLD-0061 (3.77 m²)**: cleared by a local
    detour (4.907 m displacement, +16 vertices), 0.0 m² after.
  - `MAIN_ROAD_BUILDING_OVERLAP` is now a **pass** (38.1907 m² before → **0.0**
    after, `resolved`); the new `ROAD_ALIGNMENT_EVIDENCE` (info) publishes each
    adjusted road's source edges, original/adjusted centreline, strategy,
    maximum displacement, vertex budget and overlap before/after. `+45 / −0`
    vertices; road ids preserved; `FULL_SITE_ROAD_CLEARANCE` stays deferred.
  - **7 dead ends resolved** (recorded per node with strategy and displacement):
    MAIN-03/MAIN-05 trimmed back to junctions; MAIN-09/MAIN-20/MAIN-22 bridged
    to another main road with explicit shared-vertex junctions;
    MAIN-18/MAIN-25 justified as site-edge termini (MAIN-25 extended 5.643 m to
    the published site boundary). `DEAD_END_RESOLUTION` is now a **pass**
    (0 unresolved). The 19 remaining dead ends are the 17 planned group-access
    terminals plus the 2 justified site-edge termini.
  - **Topology**: 1 component; 57 nodes / 66 edges / cyclomatic 10;
    19 dead ends; 35 junctions (24 explicit); 3 closed rings; max endpoint gap
    0.0; main length 2126.393 m; road area 27,369.82 m²; sidewalk 9,889.90 m²;
    44 roads (25 main / 17 branch / 2 access) with unchanged ids and widths.
  - **Access preserved**: the 17 declared group-access relations, `G-08 →
    BR-G-08`, `G-13 → BR-G-13`, the [3.4, 3.5] m terminal band and
    `relation_errors: 0` are unchanged; terminals are frozen and re-attached to
    the adjusted mains with shared vertices. New-access overlap drops to
    **0.5485 m²** (was 1.3365); total road/building overlap = 0.5485 m².
  - **Checks: 26 design checks = 8 pass + 11 info + 7 deferred** (plus 3 DXF
    checks in the contract). Contract `design-synthesis-v0.7.yaml` (v0.6
    superseded; gate-register pointer re-pointed).
  - **Geometry/evidence change**: DXF content changes (206 → **211 entities**,
    audit 0/0, readback 211/211, XDATA 11, privacy pass; byte hash varies per
    save); `design-roads.geojson` publishes `main_alignment_records` and
    `dead_end_resolution_records`; open-space metrics shift to candidate
    62.07 % (126,691 m²), unbuilt 64.45 % (131,560 m²), designed green 6.54 %
    (13,347 m², deferred).

### Verified

- **347 passed** (`python -m pytest -q`; 334 → 347: main-alignment tests,
  contract v0.7 and re-baselined topology/green/synthesis assertions for the
  intended geometry change; no test removed).
- Independent reviews: `arch-core` contract/implementation PASS;
  `cad-pipeline` evidence-chain/content PASS; `adversary` adversarial PASS
  (main overlap recomputed to 0, 7/7 resolutions, access unchanged).

## 0.20.0 — 2026-10-28

### Changed

- **M4c-1e — road-access evidence is now bound to declared service
  relations.** No design geometry changes: the road inventory, endpoints,
  widths, topology and the 206-entity DXF are identical to 0.19.0; the change
  is to what the evidence can prove, and to the machine-readable state of
  known conflicts. Tests 324 → **334**.

  - **Explicit service relations.** Each access road now declares
    `serves_group_ids` and `access_terminal_xy`; `ROAD_ACCESS_COVERAGE` uses
    that declaration instead of "nearest qualifying endpoint". Each of the 17
    groups is served by exactly its own connector (G-08 → BR-G-08,
    G-13 → BR-G-13); the previous evidence assigned G-08 to BR-G-09 (2.895 m)
    and G-13 to BR-G-07 (3.188 m), which are other groups' roads.
  - **Terminal band and binding.** A served terminal must be within the
    **[3.4, 3.5] m** centreline band, outside every footprint, with route
    crossing ≤ 0.1 m, and must actually lie on the serving road's centreline or
    an endpoint (≤ 1e-6 m) — a declared terminal 100 m off its road is rejected.
    Orphan declarations (`serves_group_ids` naming a non-existent group) are
    reported as relation errors.
  - **Two clearances, not one.** The terminal band is a centreline-to-facade
    distance; the 3.0 m `building_road_clearance_m` in `FOCUS_ROAD_CLEARANCE`
    remains a corridor-edge quantity. Each group now records
    `terminal_corridor_edge_clearance_m` separately (0.0 m for a 7 m branch
    end-cap, 1.5 m for the 4 m ACC-G-12 lane), so "3 m clearance" is no longer
    stated with two different meanings.
  - **Known main-road conflict is now a check, not a footnote.**
    `MAIN_ROAD_BUILDING_OVERLAP` is `deferred` and lists the conflicts per road
    and building (MAIN-19/SK-BLD-0006 34.42 m², MAIN-08/SK-BLD-0038 3.68 m²,
    MAIN-08/SK-BLD-0061 0.09 m²; total 38.1907 m², `known_unresolved`);
    `FULL_SITE_ROAD_CLEARANCE` is `deferred`. The 1.0 m² per-route budget applies
    only to new group-access roads and does not cover the main-road overlap.
  - **Parking proximity vs driveway.** `PARKING_ENTRANCE_CONNECTION` is renamed
    `PARKING_ENTRANCE_PROXIMITY` (`info`; point-to-centreline proximity only)
    and `PARKING_DRIVEWAY_CONNECTION` is added as `deferred`; all entrances
    report `driveway_designed: false`.
  - **Dead ends classified ≠ resolved.** `DEAD_END_JUSTIFICATION` (`info`) now
    states "all classified, not all justified"; a new `DEAD_END_RESOLUTION`
    (`deferred`, 7 unresolved) lists the 5 unfinished main stubs and 2
    unclassified tips.
  - **Checks: 25 design checks = 6 pass + 10 info + 9 deferred** (plus 3 DXF in
    the contract). Contract `design-synthesis-v0.6.yaml` (v0.5 superseded;
    gate-register pointer re-pointed).
  - Docs: the self-contradictory "every dead end is justified" wording is
    removed; the "19 connector roads / G-08/G-09 share BR-G-09" statement is
    corrected to 17 declared group-access connectors (16 branch + ACC-G-12)
    plus BR-FOCUS and the focus loop; the continuation dossier is marked as a
    historical 0.15-era audit snapshot and the handoff is the single current
    state source.

### Verified

- **334 passed** (`python -m pytest -q`; 324 → 334: declared-relation, terminal
  binding, orphan-declaration and negative tests; no test removed).
- Evidence regenerated: DXF unchanged (206 entities, audit 0/0, readback
  206/206, XDATA 11, privacy pass); `design-roads.geojson` SHA-256 changes only
  because it now publishes `serves_group_ids`, `access_terminal_xy` and the
  main-road overlap records; road geometry, topology and overlap values are
  bit-identical to 0.19.0.

## 0.19.0 — 2026-10-28

### Changed

- **M4c-1b — design-aware road access coverage.** This is the first M4c
  release that changes design **geometry**: the design road network now
  connects every building group to the network, replaces the
  bounding-box/ focus-box heuristic, and publishes a per-group access relation
  and per-dead-end justification. 292 → **324 passed**. Main-road alignment,
  DXF layers/drawing standard, XDATA schema (11), readback and privacy
  mechanisms are unchanged.

  - **Every group is served.** 44 roads = 25 main (12 m) + 17 branch (7 m) +
    2 access (4 m). G-05 (3 buildings / 7 units) and G-12 (2 buildings /
    4 units), previously skipped because their bounding boxes intersected the
    focus box, now have access roads (`BR-G-05`, `ACC-G-12`). `G-01` is served
    by `BR-G-01`; the focus access loop is `ACC-FOCUS-01`.
  - **Access is a geometric relation.** Each access road terminates
    **3.499999 m** from its group's building footprint (clearance 3.0 m + 0.5 m
    schematic tolerance), never inside a footprint, with a route that crosses
    footprints by 0.0 m, and is joined to the network by an explicit
    shared-vertex junction. `ROAD_ACCESS_COVERAGE` = 1.0 (17/17 groups) is a
    `pass`; it is not a connected-component count.
  - **G-12 is a 4 m access lane** because a 7 m branch corridor could not keep
    the 3.0 m focus-building clearance from SK-BLD-0035; the loop was expanded
    to include the G-05/G-12 buildings, so loop corridor ∩ buildings = 0 m².
  - **Known, reported road-building overlap.** New access roads overlap
    building footprints by **1.3365 m²** (budget ≤ 1.0 m² per new road, max
    per-building 0.9228 m²). The pre-existing **main-road overlap is
    38.1907 m²** (MAIN-19 34.42 + MAIN-08 3.77, source alignment vs coarse
    full-site context); total 38.7392 m². This is published as a known
    unresolved conflict, not silently accepted; main alignment is M4c-2 scope.
  - **Parking entrance geometry repaired (R18).** Designer-marked garage
    entrances are Polygons in the source; `ParkingEntrance.point` is now
    always a `Point` (representative point) with the polygon kept in a separate
    `footprint` field, so serialisation no longer crashes.
    `PARKING_ENTRANCE_CONNECTION` (info) reports 2/5 connected: the two proposed
    entrances sit on the main road, while the three existing garage-face markers
    are 18.83–25.71 m from a centreline and **have no designed driveway** —
    reported, not assumed away.
  - **Access connectors vs groups.** The 17 groups are served by 19 connector
    roads (G-08/G-09 share `BR-G-09`), not necessarily one branch per group.
  - **Dead ends classified.** 24 noded dead ends = **17 justified group
    terminals** + **5 unfinished main-road stubs** + 2 unclassified; the
    unfinished and unclassified ids are published in
    `DEAD_END_JUSTIFICATION` (info) and in `design-roads.geojson`.
  - **Checks: 21 design checks = 6 pass + 10 info + 5 deferred** (plus 3 DXF
    checks in the contract). New: `ROAD_ACCESS_COVERAGE` (pass/fail),
    `PARKING_ENTRANCE_CONNECTION` (info), `DEAD_END_JUSTIFICATION` (info).
    Contract `design-synthesis-v0.5.yaml` (v0.4 superseded; gate-register
    pointer re-pointed).
  - **Evidence changed accordingly**: DXF 208 → **206 entities** (junction
    repair merges some road polylines), road count 41 → **44**, design-roads
    SHA-256 changes, noded graph 59 nodes / 65 edges / cyclomatic 7 / 24 dead
    ends / 32 junctions / 21 explicit junctions / 3 closed rings / gap 0.0 /
    1 component; readback 206/206, audit 0/0, XDATA 11, privacy pass.
    Open-space areas shift slightly with the new corridors: candidate
    63.02 % (128,645 m²), unbuilt 65.35 % (133,384 m²), designed green
    6.54 % (13,347 m², deferred).

### Not claimed

- No parking layout, aisle geometry or parking spaces are designed; entrance
  points are markers, not driveways.
- The main-road building overlap (38.19 m²), the vertical alignment, road
  profiles, junction turning radii and road service beyond "terminal within
  3.5 m of a group" are not designed.
- The draft is still focus-only for detailed building design (7 of 55
  buildings); full-site spacing remains deferred.

## 0.18.0 — 2026-10-28

### Changed

- **M4c-1d — tightened pass semantics and metric definitions.** No design
  geometry, CAD content or road topology changes; the checks are restructured so
  that `pass` means what it says. The check set grows from 16 to **18**:
  **5 pass / 8 info / 5 deferred**.

  - **`pass` is now reserved for checks that verify generated geometry against
    a declared constraint**: `FOCUS_NS_SPACING`, `FOCUS_BOUNDARY_SETBACK`,
    `FOCUS_BUILDING_OVERLAP`, `FOCUS_ROAD_CLEARANCE`, `ROAD_CONNECTIVITY`.
    Basis-derived checks report `info` when self-consistent and `fail` on
    inconsistency; they never report `pass`.
  - **FAR split**: `FAR_RANGE` → `FAR_ARITHMETIC_SCENARIO` (`info`; 1.5654 under
    the current all-unconfirmed assumptions) plus a new
    `FAR_FINAL_VERIFICATION` (`deferred`; can only be answered after the basis is
    confirmed and the full-site design exists).
  - **Parking naming**: `PARKING_CAPACITY` now records
    `assumed_nominal_capacity_spaces` (1,000 = 2 proposed entrances × the
    declared 500 spaces/entrance assumption), explicitly **not verified
    capacity**; the entrance-count check is `info` under that assumption;
    `PARKING_LAYOUT` remains deferred.
  - **Unit count / road widths**: `UNIT_COUNT_PRESERVED` →
    `UNIT_COUNT_BASIS_INVARIANT` (`info`), `ROAD_WIDTHS` →
    `ROAD_WIDTH_ASSIGNMENT` (`info`); both keep their `derived_from` labels.
  - **Open space split into two measured accounts**: `CANDIDATE_OPEN_SPACE_RATIO`
    (`info`; 63.04 %, filtered: 5 m boundary setback, 0.5 m obstacle buffer,
    supplementary polygons ≥ 100 m², area = sum of recorded classifications) and
    a new `UNBUILT_RATIO` (`info`; **65.34 %**, geometric polygon-union area of
    the site minus buildings/roads/sidewalks, no extra filters). The 30 %
    designed-green target stays `deferred` (`DESIGNED_GREEN_RATIO` 6.59 %).
  - **Design-basis provenance**: `confirmed: true` now requires a non-empty
    `approval_ref`; provenance is explicitly declared
    `provenance_authentication: declarative` in the contract and in
    `design-summary.json`. This binds confirmation to an approval reference but
    does **not** authenticate the author — real authentication remains part of
    the authority-hardening task that must close before any autonomous canonical
    write. The 21 basis parameters remain `confirmed: false`.
  - **Contract** `design-synthesis-v0.4.yaml` (v0.3 superseded; gate register
    re-pointed) updates the verification list (18 design checks + 3 DXF checks)
    and rules (pass reserved for geometry verifications; basis-derived checks are
    info; deferred is not pass; candidate/unbuilt definitions; provenance is
    declarative).
  - DXF title block now states `UNBUILT … | CAND OPEN SPACE … | DESIGNED GREEN …
    (DEFERRED)` instead of reporting open space as "GREEN".

- Evidence regenerated in one run: **18 checks = 5 pass + 8 info + 5 deferred**;
  DXF still 208 entities, audit 0/0, readback 208/208, XDATA 11, privacy pass;
  road topology and `design-roads.geojson` SHA-256 unchanged.
- Docs: early 4c/M4c-0 checklists are annotated (not rewritten) with the
  M4c-1c/1d definitions; the completed "merge PR #34" thread is removed from the
  handoff; the mainline order is recorded as M4c-1d → M4c-1b → multi-candidate
  evaluation → full-site expansion.

### Verified

- **292 passed** (`python -m pytest -q`): new basis approval-ref tests (20
  basis tests), green/parking dual-account tests (9), contract tests expanded to
  11 including the v0.4 evidence binding; no test was removed (283 → 292).

## 0.17.0 — 2026-10-28

### Changed

- **M4c-1c — honest design-check semantics.** No design geometry, CAD output or
  road topology changes: this release changes what the checks are allowed to
  claim. The previous 13-check set marked several basis-derived or unverified
  quantities as `pass`; the new 16-check set uses explicit `pass` / `info` /
  `deferred` semantics (a deferred check is never a pass).

  - **Green** — `GREEN_RATIO` (which passed at 63.0 %) is replaced by
    `OPEN_SPACE_RATIO` (`info`; 63.04 % of the site is free of buildings and
    roads) and `DESIGNED_GREEN_RATIO` (`deferred`; classified cluster/strip
    green is only 6.59 % / 13,446 m² of the site — 89.55 % of the reported
    "green" was residual space, so the declared 30 % target is **not** met under
    this definition yet).
  - **Parking** — `PARKING_MIN_ONE_PER_HOUSEHOLD` and `PARKING_ENTRANCES` are
    replaced by `PARKING_REQUIREMENT_ARITHMETIC` (`info`; requirement is
    households × declared ratio), `PARKING_ENTRANCE_COUNT` (`pass`; 5 entrances,
    count only), `PARKING_CAPACITY` (`deferred`; recorded entrance capacity is
    1,000 spaces versus 2,398 required) and `PARKING_LAYOUT` (`deferred`; garage
    layout is not designed).
  - **FAR / unit count / road widths** — now explicitly labelled
    `derived_from: design_basis_arithmetic` / `design_basis_assignment`; they are
    basis arithmetic or declared-assignment results, not spatial design results.
    `UNIT_COUNT_PRESERVED` now states that the 55 buildings / 109 units still
    include the 2 buildings (3 units) dropped from the detailed focus layout.
  - **Design basis provenance** — `design-basis-001.yaml` is now
    `design-assumption-v0.2` with a machine-readable `parameter_sources` block
    covering all 21 design parameters (`source`, `authority`, `confirmed`):
    5 `declared_requirement`, 2 `designer_stated`, 3 `inferred_from_sketch`,
    11 `agent_assumption`; every parameter is `confirmed: false`. Validation
    rejects a missing/incomplete provenance block and **rejects
    `agent_assumption` marked as confirmed** — the Agent cannot self-confirm.
  - **Contract** — `contracts/design-synthesis-v0.3.yaml` (v0.2 marked
    superseded; evidence-gate register re-pointed) adds
    `basis.parameter_sources`, `basis.parameter_authorities`, the honest
    verification list and rules ("deferred is not pass", "open-space ratio is
    not designed green", "entrance count is not parking capacity",
    "FAR/GFA are basis arithmetic"). A contract test binds the YAML to the live
    module.

- Evidence regenerated in one run: **16 checks = 9 pass + 3 info + 4 deferred**;
  DXF still 208 entities, audit 0/0, readback 208/208, XDATA arity 11, privacy
  pass; road topology unchanged (41 roads, 1 component, 51 nodes / 55 edges,
  max endpoint gap 0.0 m, `design-roads.geojson` SHA-256 unchanged).

### Verified

- **283 passed** (`python -m pytest -q`), including new
  `tests/test_green_parking_semantics.py` (7), `tests/test_design_basis.py` (14)
  and an expanded `tests/test_design_contract.py` (10).

### Docs

- README / status / design-synthesis README / roadmap / testing guide updated to
  the honest metrics: the misleading "green ratio achieved 63.0 %" is removed;
  parking capacity and garage layout are shown as deferred; FAR is described as
  design-basis arithmetic. The continuation dossier and handoff keep the
  corrected narrative.

## 0.16.0 — 2026-10-28

### Added

- **M4c-1a — noded road-topology truth and explicit design junctions**
  (`src/dgcad_design/topology.py`, `src/dgcad_design/roads.py`): exact-coordinate
  MultiGraph topology (no rounding, buffering, tolerance or snapping),
  fail-closed violation codes, and explicit shared-vertex junctions replacing the
  `nearest_points`-as-junction connectors. `RoadLayout` now exposes
  `corridor_union_pieces`, `noded_topology` and `explicit_junctions`;
  `RoadDesign` carries `start_junction_id` / `end_junction_id`.
- `design-roads.geojson` in `docs/e2e/design-synthesis-001/` (41 centre lines
  with class, width, junction ids and a recorded SHA-256), so the design road
  topology can be recomputed from committed evidence. Before this, only the 10
  focus-area centre lines reached the DXF and the defect was not checkable from
  the evidence package.
- `contracts/design-synthesis-v0.2.yaml` with a `road_design.topology` block
  (required fields, connector states, fail-closed conditions and rules);
  `design-synthesis-v0.1.yaml` marked superseded;
  `contracts/evidence-gate-register-v0.2.yaml` re-pointed.
- Tests: `tests/test_design_topology.py` (14), `tests/test_privacy_scan.py` (20),
  and an evidence test that recomputes the noded topology from
  `design-roads.geojson` (`tests/test_design_synthesis.py`).

### Fixed

- **The 4c "5-component road network" defect is a floating-point noding
  artefact, not a design disconnection.** Four connector endpoints were
  1.5e-15 … 2.1e-14 m off the main alignment, so exact GEOS noding never merged
  them, while the corridor-union check still passed (it merges centreline gaps up
  to 8.98 m). Explicit shared-vertex junctions reduce the noded graph to **one
  component with 0.0 m geometry displacement**; the documented claim that the main
  roads were not connected to each other was wrong (all 25 main roads were always
  in one exact component).
- `ROAD_CONNECTIVITY` now reads the **noded centreline component count** and fails
  closed on component > 1, endpoint gap > 1e-9 m, crossing-without-shared-vertex
  and undeclared closed rings. The corridor-union piece count became the
  non-gating `ROAD_CORRIDOR_COVERAGE` (`info`).
- DXF privacy scan no longer reports spurious numeric-token matches inside
  64-hex digests/GUIDs (the ~6.3 % per-run false-positive source); real numeric
  privacy findings are still detected.
- **Hash-pinned evidence is byte-stable across platforms**: `design-roads.geojson`
  is written with explicit LF newlines and `*.geojson` is marked `-text` in
  `.gitattributes`, so the recorded `design_roads.sha256` matches the committed
  blob on Linux and Windows. (CI caught the CRLF-normalisation mismatch before
  merge; the first CI run of M4c-1a failed on all four jobs and was fixed in the
  follow-up commit without changing any evidence value.)

### Verified

- 41 design roads: **1 noded component**, 51 nodes / 55 edges / cyclomatic 5,
  21 dead ends, 27 junctions, 16 explicit junctions, 3 design-level closed rings,
  max endpoint gap **0.0 m**.
- Design metrics unchanged: FAR 1.5654107291796402, 2,398 households, 2,398
  parking spaces, 5 entrances, focus G-01 7 buildings / 16 units / 352 households
  at 20.0 m north-south spacing, green ratio 0.6303863597090935.
- `design-proposal.dxf`: 208 entities, audit 0/0, readback 208/208, XDATA arity
  11, 7 `UNKNOWN_HEIGHT_ALLOWED` warnings, privacy pass. All design objects stay
  `rule_derived` / `proposal_preview` / `design_draft`; no `human_confirmed`
  object and no compliance claim.
- **259 passed** (`python -m pytest -q`).

### Docs

- The 4c defect narrative is corrected in `docs/e2e/design-synthesis-001/README.md`,
  `docs/status.md` §16–18, `docs/roadmap.md`, `docs/e2e/open-source-reuse-001/`
  and `docs/research-to-product-map.md`; stale counts (206 / 214 / 65 / 154 /
  210 entities / 22 layers / 28 files) are corrected and the contract references
  point at `design-synthesis-v0.2`.
- `docs/development/session-handoff.md` carries the updated HEAD and file counts.

### Scope

- OSMnx is **not** required for this fix and remains an optional source-skeleton
  preprocessor; design connectivity is now proven by exact shared vertices, not
  by tolerance snapping.
- DXF byte reproducibility (`write_fixed_meta_data_for_testing`) remains a
  separate evidence-migration decision.
- No road width/profile/alignment, junction design, full-site layout or
  code-compliance claim is added.

## 0.15.0 — 2026-10-27

### Added

- **M4c-0 — open-source design capability reuse sprint**: `docs/e2e/open-source-reuse-001/` and `experiments/m4c0/`.
- Reuse matrix with tested versions, licenses, hosts, APIs, metrics, verdicts and rejected uses: `reuse-matrix.yaml`.
- Experiment A: Building Regulariser 0.2.5 on 9 focus footprints.
- Experiment B: OSMnx 2.1.1 simplify/consolidate, PyGeoOps 0.6.0 centerlines, PyClothoids 0.2.0 G1 fit.
- Experiment C: uncorrected vs corrected collaborative layout, momepy 1.0 evaluation, comparison image and editable DXF.
- `tests/test_open_source_reuse.py` (3 tests).

### Verified

- **217 passed**.
- Building Regulariser: 63→61 vertices, area −2.0%, mean Hausdorff 1.07 m, max 4.87 m, IoU 0.959, ERI 0.972→0.984; limited gain, no unit/typology generation.
- OSMnx: 309/333 → 257/281 (simplify) → 117/141 (consolidate 8 m), 1 component, length 6,090 m (−10.7%); with design widths it still leaves no 120×90 m buildable focus rectangle.
- PyGeoOps: 11 centerlines for 11 road areas, 78% coverage, 10/11 multi-component.
- PyClothoids: single G1 fit on MAIN-08 shortened the road by 78 m and deviated by 356 m Hausdorff; not a usable alignment.
- momepy: building morphology and network-ratio metrics for candidate evaluation only.
- **Found a 4c defect**: the design corridor union is one polygon, but the noded road centerline graph has 5 components (51 nodes / 50 edges, cyclomatic 0). The corridor-only `ROAD_CONNECTIVITY` check is too weak; the 4c candidate is partial.
- Uncorrected layout had 1 road-clearance conflict (`SK-BLD-0038`); the corrected layout has 7 buildings / 16 units, 20.0 m N-S and dropped 0038/0061; all current checks pass except deferred full-site spacing.
- No new core dependencies: `pyproject.toml` still lists only PyYAML, Shapely/GEOS and ezdxf.

### Scope

- Open-source tools were tested as optional experiment dependencies, not production/core dependencies.
- No open-source algorithm or foreign design default is claimed as Chinese code compliance.
- UrbGEN is a Rhino/Grasshopper plugin (host-blocked); Street Generator/rue-lib is not on PyPI and uses foreign widths; Clothoids, IfcOpenShell and Ladybug are deferred.
- The 4c candidate remains a partial schematic proposal; the road topology must be rebuilt on the connected OSMnx-consolidated base.

## 0.14.0 — 2026-10-27

### Added

- **Milestone 4c — first autonomous standardized design draft** from the real CASE-SKETCH-001 sketch: `docs/e2e/design-synthesis-001/`.
- `contracts/design-synthesis-v0.1.yaml`: autonomous draft state, design basis, constraints, drawing standard and authority rules.
- `src/dgcad_design/`: design basis, full-site input, intent model, building standardization/row layout, road hierarchy, green allocation, parking, consistency checks, drawing and CAD export.
- `fixtures/design/design-basis-001.yaml` and `design-profile-001.yaml`.
- `scripts/design/run_design_synthesis_001.py`.
- `tests/test_design_synthesis.py` (8 tests).
- `docs/e2e/design-synthesis-001/README.md`, `design-proposal.dxf`, `design-preview.png`, `design-basis.yaml`, `design-intent.json`, `design-summary.json`, `design-consistency.json`, `design-diff.json`, `draft-manifest.json`, `scene-snapshot.json`, `cad-ir.json`, `readback-manifest.json`, `validation.json`, `privacy.json`.

### Verified

- **214 passed**.
- Full-site context: 55 buildings, 109 staircase units, 2,398 households, 319,536 m² GFA, **FAR 1.565** (required 1.55–1.60), 2,398 parking spaces (≥1/household) and 5 garage entrances.
- Focus block G-01: 7 buildings / 16 units in rows with **20.0 m north-south spacing**, unit division lines, green strips and an access loop; 2 buildings recorded as dropped.
- Road hierarchy: merged main roads, one branch per group and a focus access loop; widths 12/7/4 m; the 333-edge skeleton mesh is retained as evidence and is not the design network.
- Green ratio 63.0%; all declared hard checks pass except full-site north-south spacing, which is recorded as deferred.
- DXF: 208 entities, audit 0/0, readback 208/208 pass; CAD-IR `pass_with_scope_limits` with seven `UNKNOWN_HEIGHT_ALLOWED` warnings for the declared design heights; 23 design layers including main/branch/access roads, unit lines, dimensions, title, legend, north, scale and key plan.
- Authority: every design object is `rule_derived` in `proposal_preview`; XDATA and the readback manifest carry `confirmation_scope: design_draft`; no `human_confirmed` claim.
- The design is generated without a human review gate; the designer reviews the product, not the sketch.

### Scope

- Schematic design proposal, not construction or permit drawing; no code-compliance claim.
- The unit module is provisional; the designer's unit-type library is still pending.
- Road corridors are schematic; the 121-junction review is not continued.
- The garage layout is not designed; only the entrance requirement is checked.
- The full-site north-south spacing is deferred until each group is designed.
- `EP-R1-SKETCH-001` remains in progress.

## 0.13.0 — 2026-10-27

### Fixed

- **Withdraw the 0.12.0 human-review claim.** The committed CASE-SKETCH-001-HANDOFF-A review record was a designer **authorization to run a pilot**, not an object-level geometry or coordinate review. It is reclassified as `designer_authorized_pilot`; the pilot blocks with `HUMAN_OBJECT_REVIEW_REQUIRED`.
- **Preserve confirmation scope.** `confirmation_scope`, `geometry_quality` and `review_kind` now propagate through trace objects, canonical objects, CAD-IR provenance, DXF XDATA and the readback manifest. A `full_case` review rejects `confirmed_for_pilot`.
- **Stop the sketch boundary becoming `SITE-001`.** A published sketch boundary maps to `SITE-SKETCH-001` with candidate authority; only an authoritative private site reference may create `SITE-001`.
- **Correct the coordinate claim.** The transform is `uniform_scale_translation_yflip` in `LOCAL-XY-ZUP`, not a homography; `homography_applied: false`, `shape_correction: none`, `axis_orientation: unknown`; per-object area/perimeter/centroid sensitivity recorded.
- **Verify source integrity.** Source file SHA-256, source object ID and canonical source-geometry hash are checked; a stale hash, changed geometry or missing object fails closed.
- **Verify road topology.** Edge endpoints must match declared nodes within a 4.0 px tolerance, the selected graph must be one component with consistent junction degrees and corridor coverage. The selected data's max offset is 3.606 px; two edges were stored in reverse direction and are normalized and recorded.
- **Add a structured DXF privacy scan** over TEXT/MTEXT, layer/linetype/style/block names, XDATA and raw bytes.

### Added

- `contracts/sketch-domain-handoff-v0.2.yaml`; v0.1 is marked superseded.
- Trace/canonical review metadata, boundary authority and site canonical identity.
- `review-packet.html` / `review-packet.json`, `review-request.yaml` and an unsigned `review-confirmation-template.yaml` for the designer.
- `src/dgcad_e2e/sketch_review.py` and `src/dgcad_e2e/privacy.py`.
- Blocked evidence: `blocked.json`, `integrity.json`, `road-topology.json`, `coordinate-sensitivity.json`, `provenance-map.json`.
- `docs/e2e/sketch-handoff-a/history-0.12.0/` preserves the superseded executed pilot.
- `tests/test_sketch_handoff.py` grows to 32 tests; `tests/e2e/test_sketch_handoff_a.py` to 6.

### Verified

- **206 passed**.
- The committed handoff is blocked: no canonical model, CAD-IR or DXF is published; source integrity (3 files, 7 objects) and road topology pass.
- A test-double run still reaches 11 DXF entities, audit 0/0 and 11/11 readback, with `confirmation_scope=pilot_subset` in trace, canonical, CAD-IR, XDATA and the manifest, and `SITE-SKETCH-001` at candidate authority.
- Synthetic E2E-001/002/003/003b and CAD delivery remain green.

### Scope

- The selected real subset still needs a designer object-level review; the test double is not published as human confirmation.
- `EP-R1-SKETCH-001` remains in progress; `R1-G07` remains partial.
- Same-library `ezdxf` readback is not third-party evidence.
- The pilot-local approximate scale is published under the handoff publication block; the private calibration matrix, DWG, redline and project coordinates are not.

## 0.12.0 — 2026-10-28

### Added

- **CASE-SKETCH-001-HANDOFF-A**: a selected real sketch subset passes an explicit human pilot-scope geometry gate, enters the existing Domain Slice, and reaches Canonical → CAD-IR → DXF → readback.
- `contracts/sketch-domain-handoff-v0.1.yaml`.
- `src/dgcad_domain/sketch_handoff.py`: source→trace→canonical mapping, coordinate handoff, human review gate, domain fixture generation.
- `src/dgcad_e2e/sketch_handoff_project.py`: `ConfirmedTraceScene` → `build_initial_scene` → runtime proposal/approval/commit → CAD-IR → DXF readback.
- `fixtures/sketch/CASE-SKETCH-001-HANDOFF-A/`: handoff, human review record, domain fixture and mapping.
- `docs/e2e/sketch-handoff-a/`: handoff summary, canonical snapshot, CAD-IR, DXF, readback manifest, validation and provenance map.
- `scripts/sketch_intake/build_handoff_a.py` and `scripts/e2e/run_sketch_handoff_a.py`.
- `tests/test_sketch_handoff.py` (14) and `tests/e2e/test_sketch_handoff_a.py` (2).

### Verified

- 7 selected real objects: site boundary, ordinary building, merged building, green, two main-road edges, one branch edge and one T-junction.
- DXF: 11 entities, audit 0/0; readback 11/11 pass; CAD-IR `pass_with_scope_limits` with two `UNKNOWN_HEIGHT_ALLOWED` warnings.
- Trace evidence unchanged after all commits; massing blocked for unknown height; road profiles blocked with `ROAD_CLASS_UNCONFIRMED`; no width derived.
- Local metric handoff: 2.438 px/m, declared range 2.25–2.89; `project_coordinates: false`; no DWG/project coordinates published.
- **184 passed**.

### Scope

- Pilot subset only; `confirmed_for_pilot` is not full-case or survey-grade.
- `EP-R1-SKETCH-001` remains in progress; `R1-G07` remains partial.
- Same-library `ezdxf` readback; not third-party CAD evidence.
- Shadow analysis not run; no environmental result.
- Version `0.12.0`.


## 0.11.0 — 2026-10-28

### Fixed

- **Corrected the road-topology process.** The design's road network is one system; the earlier separate brown/blue skeletons cut it at colour boundaries and produced nine artificial components. That result is superseded.
- Unified brown+blue road mask, ≥300 px component filter, **5 px ellipse closing** (4 px leaves five components; 5 px is the smallest tested kernel restoring one component).
- Unified network: **1 connected component**, 309 nodes, 333 edges, 111 endpoints, **121 junction candidates**, 25 cycles; 65 main-road and 268 branch/access edges.
- Colour is a road-class attribute, not a topology separator; junctions are skeleton graph nodes, not inferred connectors.
- The eight nearest-node connectors remain rejected in `road-connectors-rejected.geojson` as negative evidence; they are not used.
- Contract, tests, README and status updated; **168 passed**.
- Version `0.11.0`.

### Scope

- The 121 junctions are proposed candidates and need review.
- No road width, cross-section, profile, alignment or surface.
- Blue still combines 支路 and 入户路; image-space only; DWG/redline/project coordinates remain private.


## 0.10.1 — 2026-10-27

### Changed

- **Withdrew inferred road connectivity.** The eight nearest-node connectors are rejected by designer review and retained in `road-connectors-rejected.geojson` as negative evidence.
- Road topology state is `as_drawn_unresolved`: 306 nodes, 312 edges, 9 components, 129 endpoints, 99 junctions, 15 cycles; gaps 15.62–76.06 px remain open.
- Removed the 320-edge/one-component connected claim; no connected graph is claimed.
- `contracts/sketch-evidence-v0.1.yaml` updates `road_topology` states, required fields and rules.
- `tests/test_road_topology.py` updated; **168 passed**.
- Version `0.10.1`.


## 0.10.0 — 2026-10-27

### Added

- Proposed road network topology from the 312 sketch centerlines:
  - as-drawn: 306 nodes, 312 edges, 9 components, 129 endpoints, 99 junctions, 15 cycles; 41 main-road and 271 branch/access edges;
  - connected with **8 inferred nearest-node connectors**: 320 edges, 1 component, 120 endpoints, 103 junctions, 15 cycles; 41 main-road and 279 branch/access edges.
- `docs/e2e/sketch-001/road-network-proposed.geojson`, `road-nodes-proposed.geojson`, `road-topology-summary.json`, `road-network-overlay.png`.
- `contracts/sketch-evidence-v0.1.yaml` adds `road_topology`.
- `tests/test_road_topology.py`: 3 tests. Total **168 passed**.
- `pyproject.toml` version corrected from `0.9.1` to `0.10.0`.

### Scope

- Every inferred connector is marked `inferred_nearest_endpoint`, `review_state: proposed`, and is **not** a designed road link; gaps span 15.62–76.06 px.
- No road width, cross-section, profile, alignment, junction turn geometry or surface is derived.
- Blue still combines 支路 and 入户路; no subtype separation.
- Image-space topology only; no project coordinates or metric lengths.
- **Superseded in 0.10.1:** inferred connectivity withdrawn; only the as-drawn topology is claimed.
- Version `0.10.0`.


## 0.9.2 — 2026-10-27

### Changed

- Applied the three remaining designer-confirmed merges:
  - `SK-BLD-MRG-0003`: 0001 + 0037 (kindergarten/facility).
  - `SK-BLD-MRG-0004`: 0019 + 0058.
  - `SK-BLD-MRG-0005`: 0027 + 0059.
- Buildings change from 58 to **55** (50 standalone + 5 merged); all **63 original red components** remain preserved, with **13** merged components.
- Inferred **1/2/3-unit** counts for the 52 residential buildings without a confirmed count: **16 one-unit, 21 two-unit, 17 three-unit**. Two are confirmed (M-001/M-002); the kindergarten M-003 is excluded as a facility.
- Six long bars (`0009`, `0010`, `0011`, `0013`, `0015`, `0018`) are 3-unit by length but 2-unit by area; the conflict is recorded for review.
- `contracts/sketch-evidence-v0.1.yaml` adds `unit_inference` and `inferred` unit-count state.
- Sketch suite: **11 tests**; total **165 passed**.

### Scope

- Unit counts are inferred from sketch dimensions, not confirmed, except M-001/M-002.
- No height, massing, FAR or unit-mix is derived; footprints remain sketch placeholders pending the unit-type library.
- No human-confirmed trace, fidelity metrics or canonical handoff yet.
- Version `0.9.2`.


## 0.9.1 — 2026-10-27

### Changed

- Applied the designer's building merges in CASE-SKETCH-001:
  - `SK-BLD-MRG-0001`: 0046 + 0047 + 0060 (3 units) with connectors 0062 + 0063.
  - `SK-BLD-MRG-0002`: 0030 (2 units) + 0053 (1 unit).
- Building count changes from 63 to **58** (56 standalone + 2 merged); all **63 original red components** are preserved in `building-components.geojson`.
- Every building records **11 floors** as `proposed_initial`; no floor height, massing, FAR or unit-mix is derived.
- Every building footprint is marked `sketch_placeholder_pending_unit_type_library`; the unit-type library is pending.
- Public trace, case summary, README, contract and tests updated. Sketch suite: **10 tests**; total **164 passed**.
- Remaining close pairs `0001/0037`, `0019/0058` and `0027/0059` stay separate pending review.

### Scope

- Unit counts are confirmed only for the two merged buildings; other buildings remain unknown.
- No human-confirmed trace, fidelity metrics or canonical handoff yet.
- Version `0.9.1`.

## 0.9.0 — 2026-10-27

### Added

- **CASE-SKETCH-001**: first Tier B designer-sketch intake.
- Public package `docs/e2e/sketch-001/`: sketch raster, image-space trace, rough road centerlines, overlays, ambiguity regions and case summary.
- `contracts/sketch-evidence-v0.1.yaml`.
- `tests/test_sketch_evidence.py`: 8 tests for privacy/leak boundaries, image-space-only geometry, designer-confirmed semantics and rough-centerline scope.
- Designer-confirmed semantics: metre; red buildings; magenta underground garage entrances; brown main roads; blue branch/access roads; green cluster spaces; existing buildings removed; top crop clips only a road segment.
- Proposed trace: 63 building candidates, 3 garage entrances, 12 green spaces, 9 road areas, 1 site boundary; 312 rough centerline candidates (main road 1 component, blue network 8 components).

### Verified

- **162 passed**.
- All trace and centerline geometry is image-space (`SKETCH-IMG-001`) and `review_state: proposed`; semantic labels are separately `confirmed`.
- The public package contains no DWG/DXF path, project coordinates or metric scale.
- Calibration is a reviewed approximate homography: mean 24.51 px, max 43.42 px; not survey-grade.

### Scope

- No human-confirmed trace or fidelity metrics (Hausdorff/IoU/topology).
- No building merge/split decision; 10 close pairs are listed for review.
- 支路 and 入户路 are not separated within the blue class.
- Road centerlines are `proposed_rough`; no alignment, width, cross-section, junction turn geometry or surface.
- No canonical Building/Road handoff from this sketch yet.
- DWG/DXF, redline/project coordinates and metric scale remain private.
- Version `0.9.0`.

## 0.8.0 — 2026-10-27

### Added

- Real third-party CAD evidence: **AutoCAD 2024 Core Console** opened, saved and read back the DGCAD DXF in an isolated profile.
- `contracts/third-party-roundtrip-v0.1.yaml`.
- `scripts/third_party/autocad_core_roundtrip.py` — reproducible host harness.
- `docs/e2e/third-party-003c/` evidence: input/roundtrip DXF, environment, comparison, save script and console output.
- `docs/e2e/third-party-003c.md` executed report.
- `tests/e2e/test_e2e_003c_third_party.py`: 2 evidence-integrity tests.

### Verified

- Verdict: `semantic_pass_with_serialization_differences`.
- Preserved: 15 entities, 15 XDATA records, layers, colors, lineweights, blocks/dimstyles/text styles, units, geometry, audit 0/0.
- Differences: DXF version `AC1024 → AC1032` (R2010 → R2018) and layer linetype case `CONTINUOUS → Continuous`.
- Validator passes with an R2018 semantic-equivalence profile.

### Scope

- Matrix is **partial**: AutoCAD 2024 Core Console executed; LibreCAD, FreeCAD and AutoCAD GUI visual QA are not executed.
- Synthetic fixture only; modelspace only; no real design-office profile.
- `DEV-CAD-006` / #6 remains open for the remaining matrix.
- Test suite: **154 passed**.
- Version `0.8.0`.

## 0.7.0 — 2026-10-27

### Added

- CAD-IR fingerprint decoupling: global scene revision is `built_from_scene_revision` metadata, excluded from the semantic hash (#16).
- Full CAD-IR dependency registration for every exported object's semantic/geometry/parameter revisions.
- Symbol-table case semantics (`symbol_name_policy`): layers, linetypes, text styles, required blocks/dimstyles/text styles, with original spelling preserved (#5).
- Stable `ring_key` in XDATA, content-derived rather than part/ring-index-derived; `RING_KEY_MISMATCH` (#1).
- Readback manifest records `canonical_target` and `raw_dxf_semantics` per entity; numeric tolerance/version documented (#4).
- Serialization-difference vs profile-violation category test (#8).
- `tests/e2e/test_e2e_003b_semantics.py`: 11 tests.
- `docs/e2e/semantic-dependency-003b.md`: executed 3b report.

### Changed

- Test suite: **152 passed**.
- `contracts/e2e-adversarial-v0.1.yaml` and `contracts/cad-ir-v0.1.yaml` updated for symbol tables, ring keys and raw/canonical evidence.
- Roadmap: Milestone 3b complete; 3c (third-party CAD evidence) next.
- Issues #1, #4, #5, #8, #16 closed with evidence; #6 remains for 3c.
- Version `0.7.0`.

### Scope

- Same-library `ezdxf` only; no third-party CAD evidence.
- Modelspace only.
- Arcs/splines are outside the current delivery entity set (LWPOLYLINE/CIRCLE/TEXT).
- No road surface geometry, real sketch input, IFC or standards compliance.

## 0.6.0 — 2026-10-27

### Fixed

- Milestone 3a validator hardening: all 15 strict xfails are now positive checks.
- Structured `VALIDATOR_ERROR`: malformed DXF and validator-internal exceptions return a structured failure, never a pass or uncaught exception.
- Entity-level style overrides: color, linetype, lineweight, true color and transparency are checked against the BYLAYER policy.
- CIRCLE center Z and TEXT insertion Z are checked.
- TEXT rotation, width factor, horizontal and vertical alignment are checked against the delivery profile.
- LWPOLYLINE full semantics: bulge, start/end width, constant width, thickness, extrusion, elevation and closed flag.
- `DeliveryProfile.text_style_policy` and compiler support for explicit TEXT rotation/width/alignment.

### Changed

- `contracts/e2e-adversarial-v0.1.yaml`: all scenarios are now detected or pass; no strict xfail remains in Milestone 3a.
- Issue-category mapping expanded for the new checks; contract-sync test still enforces exact coverage.
- `tests/test_cad_delivery_contracts.py`: bulge and constant-width tests are now positive.
- Test suite: **141 collected / 141 passed / 0 xfailed**.
- Version `0.6.0`.

### Scope

- Closed #3 (LWPOLYLINE validation), #7 (structured validator errors), #17 (entity style overrides) and #18 (CIRCLE/TEXT semantics).
- `DEV-CAD-004` remains open for raw/canonical geometry preservation.
- `DEV-CAD-001/005/006/008/011` remain open for Milestone 3b/3c.
- No third-party CAD round-trip, paper-space validation, IFC, real sketch or road surface geometry.

## 0.5.1 — 2026-10-27

### Fixed

- `delivery-comparison.json`: renamed `manifest_sha256` (which actually stored the DXF hash) to `dxf_sha256`; added `readback_manifest_sha256` computed from the written manifest file.
- DXF readback manifest: renamed its own `sha256` field to `dxf_sha256` to remove ambiguity.
- Issue-category default changed from `cad_format_semantics` to `unclassified`; unknown future codes are now visible instead of silently misclassified.
- Added a contract-sync test ensuring every `DxfIssue` code has an explicit category and unknown codes remain `unclassified`.

### Changed

- `contracts/e2e-mutation-v0.1.yaml`: comparison fields updated to `dxf_sha256` and `readback_manifest_sha256`.
- `contracts/e2e-adversarial-v0.1.yaml`: added `unclassified` category and removed the non-DXF `MASSING_BLOCKED_INVALID_FOOTPRINT` code.
- `contracts/cad-ir-v0.1.yaml`: documented that `ring_index` is global within a CAD object (part order, then ring order); ring identity stability across revisions remains a Milestone 3 decision.
- Status one-line now includes E2E-003; duplicate third-party round-trip row removed.
- Symbol-table scope wording narrowed to one layer linetype reference case; full symbol-table equivalence remains #5.
- Issue #2 narrowed to safe entity dispatch and closed after evidence; structured `validator_error` stays with #7.
- Milestone 3 scope now explicitly includes DEV-CAD-009, 010 and 011.
- Test suite: **141 collected / 126 passed / 15 xfailed**.

### Verified

- `dxf_sha256` matches the actual DXF file; `readback_manifest_sha256` matches the actual manifest file.
- Category contract and implementation are synchronized; unknown codes are `unclassified`.
- E2E-003 remains 7 positive / 13 strict xfail.

## 0.5.0 — 2026-10-27

### Added

- `contracts/e2e-adversarial-v0.1.yaml`: adversarial scenario, category, expected outcome and issue-mapping contract.
- `tests/e2e/test_e2e_003_adversarial.py`: 19 scenarios (6 positive, 13 strict xfail) covering geometry, style, identity, serialization and validator-error gaps.
- `docs/e2e/adversarial-delivery-003.md`: executed E2E-003 audit, results and boundaries.
- `DxfIssue.category` and an issue-category mapping: cad_format_semantics, interoperability, profile_violation, serialization_difference, validator_error.
- `delivery-comparison.json` generated with the DXF: object IDs, canonical revisions, CAD-IR fingerprint, readback verdict, audit counts, manifest hash and profile identity.
- Issues #16 (DEV-CAD-011 dependency fingerprint consistency), #17 (DEV-CAD-009 entity style overrides), #18 (DEV-CAD-010 CIRCLE/TEXT semantics).

### Changed

- `contracts/e2e-mutation-v0.1.yaml`: `manifest_comparison` now explicitly names `delivery-comparison.json` as a composite artifact.
- `pyproject.toml`: version `0.5.0`.
- Test suite: **140 collected / 125 passed / 15 xfailed**.
- Status/testing wording for third-party CAD evidence is unified: one user-run AutoCAD core-engine round-trip; no repeatable third-party matrix.

### Verified

- MultiPolygon with 2 parts + 1 hole round-trips as 3 entities with audit 0/0.
- Symbol-table linetype case is semantically equal.
- Missing XDATA returns a structured issue.
- LWPOLYLINE elevation is detected.
- All remaining known gaps are strict xfails with accurate issue links; no silent acceptance.

## 0.4.0 — 2026-10-27

### Added

- `src/dgcad_e2e/living_project.py`: mutation/rebuild project with canonical project context, deterministic rebuild worker and scoped artifact registry.
- `contracts/e2e-mutation-v0.1.yaml`: mutation, rebuild, manifest-comparison and road-surface-deferral contract.
- `docs/e2e/dependency-mutation-002.md`: executed E2E-002 result.
- 6 E2E-002 tests: height change, T-junction move, north bearing, real rebuild execution, manifest comparison, road-surface deferral.
- `rebuild_road_corridor_proposal`: rebuilds a corridor centerline from latest canonical edge geometry, never from the trace fixture.
- Project context `PROJECT-CONTEXT-001` versions north bearing with an explicit source.
- DXF source hash now includes CAD-IR provenance, so analysis-derived sensor metadata changes when the shadow fingerprint changes.

### Changed

- `pyproject.toml`: version `0.4.0`.
- Test suite: **121 collected / 119 passed / 2 xfailed**.
- Road surface geometry is explicitly deferred: no `SURFACE-R-002` artifact is registered or claimed as generated.

### Verified

- Height change stales massing, shadow, CAD-IR and DXF; footprint-only artifacts stay current.
- Node move is one atomic changeset; corridor centerline is rebuilt from current canonical edges.
- North bearing change stales shadow and delivery but not building footprint geometry.
- Rebuild worker recomputes, writes, validates and completes jobs with content hashes.
- Manifest comparison uses object IDs, revisions, dependency fingerprints and readback verdict.

## 0.3.0 — 2026-10-27

### Added

- `src/dgcad_analysis/`: synthetic solar/shadow baseline with explicit solar position, unknown/estimated/confirmed blocker semantics and dependency fingerprint.
- `src/dgcad_cad/`: minimal CAD-IR, DXF R2010 compiler with `DESIGN_GRADE` XDATA, and independent readback validator + manifest.
- `src/dgcad_e2e/`: living pipeline orchestration from DOMAIN-SLICE-001 through Runtime canonical commits, massing, shadow, CAD-IR, DXF and readback.
- `contracts/cad-ir-v0.1.yaml` and `contracts/e2e-pipeline-v0.1.yaml`.
- `fixtures/e2e/living-pipeline-001.yaml` with 4 analysis sample points and a synthetic DXF profile.
- `fixtures/domain/domain-slice-001-r2.yaml`: fixture revision 2 adds explicit road `trace_refs`; revision 1 is retained.
- `docs/e2e/living-pipeline-001.md`: executed E2E-001 result and scope report.
- Tests: Analysis 7, CAD delivery 9 (2 xfail), E2E 8. Total suite now **115 collected / 113 passed / 2 xfailed**.

### Changed

- `pyproject.toml`: version `0.3.0`; added `ezdxf>=1.4`.
- Domain road corridors now carry `trace_ref` and `trace_refs`; domain scene validation no longer reports `TRACE_REF_MISSING` for roads.
- `contracts/domain-contract-v0.1.yaml`: `road_corridor.required` now explicitly includes `trace_refs`.
- CAD-IR road provenance now records the source road trace reference.

### Known gaps

- `DEV-CAD-003` / issue #3: bulge and constant-width mutations are recorded as strict xfail in E2E-001.
- No third-party CAD round-trip, IFC, real sketch input, standards profile or independent shadow engine.

## 0.2.0 — 2026-10-27

### Added

- `src/dgcad_domain/`: minimal Building/Road domain slice over the Foundation/Runtime contracts.
  - confirmed trace fixture loader with immutable evidence objects;
  - Building intent, footprint preservation and regularization candidate with diff metrics;
  - Road graph, corridor, explicit cross-section and class/profile resolution gate;
  - T-junction atomic multi-object change set;
  - massing and road-surface derived artifacts with dependency keys;
  - structured domain validators;
  - StatefulRuntime integration: propose → preview → human approval → commit → stale → rebuild job.
- `fixtures/domain/domain-slice-001.yaml` with intentional difficulty cases (irregular footprint, 17° rotation, unknown height, unknown road class, T-junction).
- 26 domain contract tests; total suite now **91 tests**.

### Changed

- `pyproject.toml`: version `0.2.0`; added `shapely>=2.0`.
- Status, roadmap, testing and architecture docs now reflect the implemented domain slice.
- Research-to-product map marks the minimal Building/Road schemas as promoted.

### Research promotion and governance

- `docs/research-to-product-map.md`: promotion status for every research artifact.
- `docs/architecture/authority.md`: living authority and lock model.
- `contracts/canonical-site-ir-v0.4.yaml`: promoted Canonical Site IR (no semantic change from v0.3).
- `contracts/evidence-gate-register-v0.2.yaml`: promoted R1 evidence gate register.
- `contracts/domain-contract-v0.1.yaml`: minimal living Building/Road domain contract.
- Branch protection on `main` with the four CI matrix checks and PR requirement.
- GitHub issues `DEV-CAD-001..008` for accepted DXF/validator defects (implementation deferred).

## 0.1.0 — 2026-10-27

### Added

- Formal repository structure: `src/`, `tests/`, `contracts/`, `fixtures/`, `spikes/`, `docs/`, `research/`.
- Canonical source tree consolidating the verified R1 deployment-entry v0.2 prototype:
  - `dgcad_foundation` — identity, revisions, authority, atomic changes, preview, dependency, audit, migration, gateway.
  - `dgcad_runtime` — stateful project runtime, proposals, approvals, jobs, artifacts, idempotency, recovery.
  - `dgcad_deployment` — SQLite/WAL spike, content-addressed artifacts, sidecar lifecycle, discovery/pairing/sessions, local HTTP control plane, CAD bridge registry.
- Contract suite: **65 tests** (Foundation 21, Runtime 22, Deployment 8, Lifecycle 14).
- CI workflow for Ubuntu/Windows × Python 3.11/3.13, including coverage on the primary job.
- Project documentation: architecture overview, status matrix, roadmap, testing strategy, contribution workflow, ADR-0001.
- Apache-2.0 license.
- Research archive: full R0 v0.19 workspace and R1 deployment-entry v0.2 snapshot.

### Notes

- This release is a workspace consolidation, not a capability promotion. All prior non-claims remain in force.
- The vendored research-methodology skill copy is intentionally excluded from the public repository.
- Known DXF/validator defects (`DEV-CAD-001..008`) remain accepted development work.
