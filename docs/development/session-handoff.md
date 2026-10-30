# Session handoff — 2026-10-27

Purpose: continue DGCAD work in a fresh conversation without re-deriving
context. This file is the single source of continuation state. It is a
development note, not a living contract.

Repository: `D:\agent-cad`

> **State-source policy (2026-10-28):** §1 of this file is the single current
> continuation state. `docs/development/team-continuation-dossier.md` is a
> **historical 0.15-era audit snapshot** (HEAD `83d71eb`, 217 tests at the time)
> kept as background only; do not derive current numbers, status or next steps
> from it.

## 0. Paste-ready first message for the new conversation

> 先读 `D:\agent-cad\docs\development\session-handoff.md`（§1 是唯一当前状态），再读
> `docs/status.md` §2/§16–18、`docs/roadmap.md` 的 M4c-2/4c-3 与 Next 块、以及
> `docs/e2e/design-synthesis-001/README.md` / `docs/e2e/design-candidates-001/README.md`。
> 当前版本 0.26.0（M4d-2a 设计意图审计，不改算法/阈值：17 组为推断组——45 m +
> 8 m 主路 buffer + Union-Find，G-01 9 成员 vs focus 7，链式最大 209.738 m，
> provenance `not_designer_confirmed`；B 非连续 12/17、runs 43、位移 mean 47.92/
> P90 102.83/max 278.46；修正绿地 table：building-occupied 845.541/845.541/
> 713.445 m²，road-occupied 64.113/320.949/73.815 m²，retained 10,076.757(91.72%)/
> 9,819.92(89.38%)/10,199.151(92.83%)，preserved/shrunk/cancelled 7/5/0；access
> L1 17/17、L2 0/17、L3 15/24/26 of 55、L4 0 driveway；0.1 m 独立扰动 100% <3.0
> （B min 2.8887，common datum 不变）；四层 B = geometric pass/intent descriptive/
> deferred 5/host not_verified；tests **556**）。M4d-2 A/B 历史：A fail only clearance
> 2.825<3；B hard-valid；A/B DXF 584/587；M4d-1a/full-site DXF 553/553。下一步
> M4d-2b candidate C + CAD 宿主/R1 并行。不要新增核心依赖，不要声称
> human_confirmed / 合规 / 已采纳，不要重写 Foundation/Runtime/CAD-IR。

## 1. Repo state (verified 2026-10-28)

- `main` is the integration branch: **PR #34 merged as merge commit `e40f468`**
  (Milestone 4c — autonomous design synthesis + M4c-0 reuse + M4c-1a/1c fixes),
  **PR #36 merged as merge commit `0546649`** (M4c-1d semantic residuals),
  **PR #38 merged as merge commit `7a3e70a`** (M4c-1b design-aware road access),
  **PR #39 merged as merge commit `3e50399`** (docs: record PR #38 merge),
  **PR #40 merged as merge commit `7f81f0e`** (M4c-1e declared access evidence),
  **PR #41 merged as merge commit `03b5367`** (docs: record PR #40 merge),
  **PR #42 merged as merge commit `bb23377`** (M4c-2 main-road alignment and
  dead-end resolution), **PR #43 merged as merge commit `238483c`** (docs:
  record PR #42 merge), **PR #44 merged as merge commit `78e46d5`** (docs:
  correct final M4c-2 design-roads geojson SHA-256), **PR #45 merged as merge
  commit `569944f`** (M4c-3 multi-candidate design decision experiment +
  Phase-0 evidence corrections), **PR #46 merged as merge commit `c59b93b`**
  (docs: record PR #45 merge and refresh continuation state), **PR #47
  merged as merge commit `29c93bd`** (M4c-3a evaluation integrity and
  geometry-change evidence), **PR #48 merged as merge commit `a2ec899`**
  (docs: record PR #47 merge) and **PR #49 merged as merge commit `95239d7`**
  (M4d-1 full-site design expansion) and **PR #51 merged as merge commit
  `b5c45ae`** (M4d-1a full-site delivery semantics and completeness),
  **PR #52 merged as merge commit `19955d6`** (docs: record PR #51 merge) and
  **PR #53 merged as merge commit `81b7dc9`** (M4d-2 A/B building-road
  co-design experiment, 0.25.0); main CI is 4/4 green on all.
- The old topic branches `milestone-4c-autonomous-design`,
  `fix/m4c-1d-semantic-residuals`, `feat/m4c-1b-road-access`,
  `fix/m4c-1e-evidence-binding`, `feat/m4c-2-main-alignment`,
  `feat/m4c-3-multi-candidate` and `feat/m4c-3a-evaluation-completeness`
  contain the same history (M4c-1a `9d4ae56` + `1209955`, M4c-1c `e02337b`,
  M4c-1d `2f396b2`, M4c-1b `2750bc5`). **Start new work from `main`** — e.g.
  `feat/m4d-full-site` or `feat/real-cad-host-evidence`.
- Version: `0.26.0` (`pyproject.toml`).
- Contract: `design-synthesis-v0.9.yaml` (v0.8/v0.7/v0.6/v0.5/v0.4/v0.3/v0.2/v0.1
  superseded; gate-register pointer → v0.9) and
  `design-candidates-v0.2.yaml` (v0.1 superseded; multi-candidate
  evaluation/comparison with basis binding and 11 single-unit objectives).
- Test baseline: **556 passed** (`python -m pytest -q`).
- Milestone order: M4c-1d honest-semantics residuals (**complete**) →
  M4c-1b road service coverage (**complete** — first design-geometry change:
  44 roads, coverage 1.0, DXF 206 entities) → M4c-1e evidence binding
  (**complete** — declared `serves_group_ids` access relations, 25 checks =
  6 pass + 10 info + 9 deferred) → M4c-2 main-road alignment and dead-end
  resolution (**complete** — 26 checks = 8 pass + 11 info + 7 deferred, DXF
  211 entities) → M4c-3 Phase 0 + first multi-candidate experiment
  (**complete** — 27 checks = 9 pass + 11 info + 7 deferred (+3 DXF = 30),
  boundary-containment hard gate, overlap fields split, candidates A/B1/B2/C,
  default B1 / road-first A, 396 tests) → M4c-3a evaluation integrity
  (**complete in 0.23.0** — candidate evidence compares all 44 roads by
  class/terminal, basis fingerprint binding, `HISTORICAL_BOUNDARY_ARCHIVE`,
  11 single-unit objectives with auxiliary excluded, contract v0.2, 414 tests)
  → M4d full-site expansion (**complete research draft in 0.24.1, delivery
  semantics corrected** — 55 buildings / 109 units / 2,398 households, 18
  rows / 36 row records / 8 superblocks, focus preserved; full-site 29 checks
  = 11 pass + 11 info + 5 deferred + 2 fail (access 0.0, dead-end 17 unresolved;
  designed green 15.93% deferred; 61.06% is `POTENTIAL OPEN SPACE ... NOT
  LANDSCAPE DESIGN`, auxiliary); focus sheet 29 = 9 pass + 11 info + 9 deferred
  (designed green 6.54%); full-site DXF 553/553; contract v0.9; 472 tests) →
  M4d-2 A/B co-design (**research draft in 0.25.0** — A fails only
  `FULL_SITE_ROAD_CLEARANCE` at served-face 2.825 m; B hard-valid, 12 group
  splits; A/B DXF 584/587 delivered) → M4d-2a design-intent audit (**0.26.0,
  descriptive only**: 17 inferred groups, B 12/17 fragmented, corrected green
  table 845.541/713.445 m², access L1 17/17 vs L3 26/55 vs L4 0 driveway,
  0.1 m perturbation 100% <3 m; 556 tests) → **next: M4d-2b candidate C +
  served-facade/terminal-band resolution**, in parallel with real CAD host
  round-trip (LibreCAD/FreeCAD/AutoCAD GUI) and R1 evidence closure**.
- Local environment: Windows, Python 3.13. Core dependencies remain only
  **PyYAML 6.0.3 / Shapely 2.1.2 / ezdxf 1.4.5**.
- Optional research-only installs (NOT in `pyproject.toml`): osmnx 2.1.1,
  buildingregulariser 0.2.5, pygeoops 0.6.0, pyclothoids 0.2.0, momepy 1.0.0.

## 2. What is complete

### Milestone 4b.1 — Scope-Aware Handoff Integrity (merged, PR #33)

Closed the five review findings:

- confirmation scope/quality/review kind propagate trace → canonical → CAD-IR
  provenance → DXF XDATA → readback manifest;
- published sketch boundary maps to candidate `SITE-SKETCH-001`
  (`canonical_site_identity: false`), never `SITE-001`;
- authorization-only review (`designer_authorized_pilot`) blocks with
  `HUMAN_OBJECT_REVIEW_REQUIRED`; test doubles rejected unless explicitly
  allowed and never published;
- coordinate handoff is honestly `LOCAL-XY-ZUP` +
  `uniform_scale_translation_yflip`, `homography_applied: false`,
  `shape_correction: none`, `axis_orientation: unknown`;
- source file/object/geometry SHA-256 verification, road topology validation
  and structured DXF privacy scan fail closed.

Evidence: `docs/e2e/sketch-handoff-a/` (status `blocked`, correct).

### Milestone 4c — first autonomous design draft (merged in PR #34)

`docs/e2e/design-synthesis-001/`:

- Design basis (`design-assumption-v0.2`, 21 parameters, all `confirmed: false`,
  provenance authentication `declarative`): FAR **1.5654** = arithmetic scenario
  inside 1.55–1.60 (final verification deferred); parking requirement **2,398** =
  1.0/household (assumed nominal capacity 1,000, capacity/layout deferred);
  **20.0 m** north-south spacing in focus group G-01.
- Full-site context: 55 buildings, 109 staircases, 2,398 households,
  319,536 m² GFA, 3,000 m² facility, 5 garage entrances.
- Focus G-01: 7 standardized buildings / 16 units; dropped `SK-BLD-0038` (2U)
  and `SK-BLD-0061` (1U) with recorded reasons.
- **211-entity** editable DXF (Phase-0 base; content changed in 0.22.0, unchanged in 0.23.0), audit
  0/0, readback 211/211, 23 design layers,
  title block "AGENT-GENERATED PROPOSAL - NOT HUMAN-CONFIRMED - NOT
  CODE-COMPLIANCE" (ASCII hyphens, as in the DXF).
- All design objects `rule_derived`, world `proposal_preview`,
  `confirmation_scope: design_draft`, `human_confirmed: false`.
- Consistency: **29 declared checks** under `design-synthesis-v0.9` — **9 pass**
  (FOCUS_NS_SPACING, FOCUS_BOUNDARY_SETBACK, FOCUS_BUILDING_OVERLAP,
  FOCUS_ROAD_CLEARANCE, ROAD_CONNECTIVITY, ROAD_ACCESS_COVERAGE,
  ROAD_BOUNDARY_CONTAINMENT, MAIN_ROAD_BUILDING_OVERLAP, DEAD_END_RESOLUTION);
  **11 info** (FAR_ARITHMETIC_SCENARIO,
  PARKING_REQUIREMENT_ARITHMETIC, PARKING_ENTRANCE_COUNT,
  PARKING_ENTRANCE_PROXIMITY, UNIT_COUNT_BASIS_INVARIANT, ROAD_CORRIDOR_COVERAGE,
  ROAD_ALIGNMENT_EVIDENCE, DEAD_END_JUSTIFICATION, ROAD_WIDTH_ASSIGNMENT,
  CANDIDATE_OPEN_SPACE_RATIO, UNBUILT_RATIO); **9 deferred** (PARKING_CAPACITY,
  PARKING_DRIVEWAY_CONNECTION, PARKING_LAYOUT, FULL_SITE_BOUNDARY_SETBACK,
  FULL_SITE_BUILDING_OVERLAP, FULL_SITE_ROAD_CLEARANCE, FULL_SITE_NS_SPACING,
  DESIGNED_GREEN_RATIO, FAR_FINAL_VERIFICATION). `info`/`deferred` are not
  `pass`; designed green is 6.54% (<30%, deferred), and the 61.46% open-space
  tiling is auxiliary only, not designed green. Plus 3 DXF checks = 32 items.
- M4c-1c (0.17.0) honest semantics: open space is not designed green
  (`designed_green_ratio` 6.6% at 0.17.0; now 6.54%, deferred); parking capacity recorded 1,000 vs
  2,398 required; basis provenance published (21 parameters,
  `confirmed: false`).
- M4c-1d (0.18.0) semantic residuals: `pass` narrowed to the 5
  geometry-verified checks; FAR split into `FAR_ARITHMETIC_SCENARIO` (info) and
  `FAR_FINAL_VERIFICATION` (deferred); parking capacity named
  `assumed_nominal_capacity_spaces`; open space dual-measured
  (`candidate_open_space_ratio` 63.0% classified / `unbuilt_ratio` 65.3%
  geometric union — both ratios use the full published site area as
  denominator; the filtered/unbuilt areas are measured inside the 5 m setback
  boundary); provenance authentication `declarative`; contract v0.4.
- M4c-1b (0.19.0) road service coverage — the first design-geometry change:
  44 design roads (25 main + 17 branch + 2 access), all 17 groups served
  (coverage 1.0), G-05/G-12 access gaps closed, 24 dead ends all classified but
  **not all justified** (17 justified / 5 unfinished / 2 unclassified),
  terminals 3.5 m from footprints, no building crossings; DXF 206 entities
  (readback 206/206); topology rebaselined (59 nodes / 65 segments, cyclomatic 7,
  junctions 32); `design-roads.geojson` regenerated (44 centerlines + 21 junction
  records, sha 59df13d8…). Honest residuals: entrance proximity only (2/5);
  pre-existing 38.19 m² MAIN-19/08 road/building overlap deferred to M4c-2;
  contract v0.5.
- M4c-1e (0.20.0) evidence binding — no design-geometry change: road inventory,
  endpoints, widths, topology (1 component, 59/65, cyclomatic 7, 24 dead ends,
  32 junctions / 21 explicit, 3 rings, gap 0.0), overlap values and DXF content
  are identical to 0.19.0. Access is now a **declared** relation
  (`serves_group_ids` + `access_terminal_xy`) instead of nearest-endpoint
  attribution: 17 group-access roads (16 branch + ACC-G-12; G-08 → BR-G-08,
  G-13 → BR-G-13), terminal centreline band [3.4, 3.5] m (min 3.497987 m) with
  a separate `terminal_corridor_edge_clearance_m` (0.0 m for a 7 m branch
  end-cap, ~1.5 m for ACC-G-12), relation errors/orphans rejected. 25 checks =
  6 pass + 10 info + 9 deferred; new `MAIN_ROAD_BUILDING_OVERLAP` (deferred,
  38.19068149970834 m²: MAIN-19/SK-BLD-0006 34.42, MAIN-08/SK-BLD-0038 3.68,
  MAIN-08/SK-BLD-0061 0.09), `FULL_SITE_ROAD_CLEARANCE` (deferred),
  `DEAD_END_RESOLUTION` (deferred, 7 unresolved), `PARKING_DRIVEWAY_CONNECTION`
  (deferred); `PARKING_ENTRANCE_CONNECTION` renamed
  `PARKING_ENTRANCE_PROXIMITY` (info). `design-roads.geojson` sha changes to
  d77ce7a8… because of the new fields (expected); DXF byte sha changes per save
  (content unchanged). Tests 334. Contract v0.6.
- M4c-2 (0.21.0) main-road alignment and dead-end resolution — a real
  design-geometry change: MAIN-19 was **diverted** (overlap 34.421783197612406
  → 0 m²; max displacement 66.23545861756293 m; the earlier "infeasible
  local detour" wording is corrected in Phase 0 — the SK-BLD-0006/0029 gap of
  11.565220076201857 m only proves the between-buildings passage infeasible, so
  the diversion is a candidate baseline)
  and MAIN-08 was **locally detoured** (3.768898302095937 → 0 m²; max
  displacement 4.90654356307025 m), so total main-road overlap
  38.19068149970834 → 0 (`MAIN_ROAD_BUILDING_OVERLAP` pass; new
  `ROAD_ALIGNMENT_EVIDENCE` info with source edges, original/adjusted
  centreline, strategy, displacement and vertex budget; +45 / −0 vertices; road
  ids preserved). The claim is zero remaining overlap for the known conflicts,
  not that all 25 main roads meet the 3.0 m corridor clearance (the unadjusted
  main roads' minimum corridor clearance is about 1.229 m; full-site clearance
  remains deferred). The 7 unresolved dead ends were resolved: MAIN-03 trimmed
  9.727353166421203 m, MAIN-05 trimmed 0.24620779365789502 m; MAIN-09 bridged to
  MAIN-08 13.677655946265997 m, MAIN-20 bridged to MAIN-19 5.233264199174163 m,
  MAIN-22 bridged to MAIN-08 9.642090864979577 m; MAIN-18 is a site-edge
  terminus 4.047925766932525 m from the boundary **within the ≤5 m site-edge
  band** (the source network is clipped at the published boundary; the endpoint
  is within the band and no source vertex lies outside it), MAIN-25
  extended 5.643487350037444 m **along the shortest direction to the published
  boundary (not collinear with the terminal segment)** (`DEAD_END_RESOLUTION`
  pass; 0 unresolved). 19 dead ends
  remain = 17 planned group terminals + 2 site-edge termini. Geometry: 44 roads
  (25/17/2, ids/widths unchanged), 57 nodes / 66 edges / cyclomatic 10,
  35 junctions (24 explicit), 3 rings, gap 0.0; main length
  2,126.392617984018 m; road area 27,369.822509945796 m²; sidewalk
  9,889.900380276495 m²; DXF content 206 → **211 entities** (readback 211/211,
  XDATA 11); pre-Phase-0 new-access/main/total overlap values are superseded by
  Phase 0; access stays 17/17 declared (terminals frozen and
  re-attached with shared vertices); green candidate 62.07% / unbuilt 64.45% /
  designed 6.54% (designed unchanged); `design-roads.geojson` SHA-256
  `a55ebb58…`. Tests 347. Contract v0.7. (Pre-Phase-0 values; Phase 0 corrected
  the semantics, boundary check and overlap fields — see the M4c-3 bullet below.)
- M4c-3 (0.22.0) Phase 0 + first multi-candidate experiment — the base design
  was corrected, not re-concepted: alignment semantics are now
  **`local_search_exhausted`** (the 11.565220076201857 m gap only proves the
  between-buildings passage infeasible; the 66.235 m diversion is a candidate
  baseline, not a proof of optimality); `ROAD_BOUNDARY_CONTAINMENT` is a hard
  check (margin 0.6735131264650868) with three repairs — MAIN-08
  341.6908310814502 → 0 m² / margin 2.446306837399009, MAIN-16
  2.417804558565924 → 0, MAIN-18 8.290901115044374 → 0; the geojson overlap
  fields are split `main_before` 38.19068149970835 / `main_after` 0.0 /
  `new_access` 0.9943558185246757 / `total_after` 0.9943558185246756 (after
  the MAIN-08 repair the remaining main conflict was 34.421783197612406 → 0);
  `source_segment_map` covers 25 roads; design-diff records
  `road_alignment`/`dead_end_resolutions` and `changed`/`why`; dead-end
  `resolved` is bound to `criterion_met` plus a geometry re-check; preview/overlay
  are regenerated by `scripts/design/render_visuals.py`. Base geometry: 44 roads
  (25/17/2), **58 nodes / 68 edges / cyclomatic 11 / 19 dead ends / 36 junctions
  (24 explicit) / 3 rings / gap 0.0**; main length 2,107.733378663747 m; road
  area 26,882.20505326313 m²; sidewalk 9,764.76834535878 m²; DXF **211 entities**
  (readback 211/211, XDATA 11, byte sha current f88c29e1…); green candidate 61.64%
  (125,819.46553768215 m²) / unbuilt 64.07% (130,788.70473514873 m²) / designed
  6.54%; `design-roads.geojson` SHA-256 `c5fc7262…`; 27 checks = 9 pass + 11 info
  + 7 deferred (+3 DXF = 30); tests 396 at M4c-3; contract v0.8. **Candidate
  experiment** (`docs/e2e/design-candidates-001/`): four deterministic candidates
  for the MAIN-19/SK-BLD-0006/SK-BLD-0029 conflict, all hard-pass.
- M4c-3a (0.23.0) evaluation integrity — no base-design change, candidate
  evidence/contract fixed. Every candidate now carries
  `parent_basis_id = design-assumption-v0.2` and canonical
  `basis_fingerprint = 2a2d7807d218f21b0d5f8546c4ea766f631788f7d48d01d9831d93513344227e`;
  missing/mismatch fails `basis_ok`. `geometry_change` compares **all 44 roads**
  by class and per-group terminal: A main 2.320271085819647 m / branch
  2.825827798091072 m (BR-G-08) / access 0, G-08 terminal 2.826209246611442 m;
  B1 main 66.23545861756291 m / branch 7.352131796880056 m (BR-G-09 follows) /
  terminal 0; B2 main 71.7722361902286 m / branch 13.645240022712755 m /
  terminal 0; C main 11.99363782892846 m / branch 76.69965271965492 m (BR-G-08) /
  G-08 terminal 75.3147044566895 m — **C is not a small local change**.
  `HISTORICAL_BOUNDARY_ARCHIVE` separates MAIN-19 66.23545861756293 m
  (`resolved_by_main_alignment`) and MAIN-08/16/18 repairs
  (341.6908310814502 / 2.417804558565924 / 8.290901115044374 m²) from current
  candidates; the current B1 is boundary-repaired (margin 0.6735131264650868)
  and hard-passes, while its pre-repair form is archival and never a pass.
  Comparison uses 11 single-unit objectives (`building_count_change`,
  `building_displaced_count`, `building_displacement_max_m`,
  `main_length_delta_abs_m`, `main_route_deviation_max_m`,
  `branch_access_route_deviation_max_m`, `access_terminal_max_delta_m`,
  `source_preservation_coverage`, `source_preservation_distance_m`,
  `source_preservation_heading_deg`, `green_designed_ratio_delta`); auxiliary
  metrics never enter Pareto/preference; no composite score. Default preference
  recommends **B1**, road-first recommends **A**, Pareto [B1,B2,C,A]. Contract
  `design-candidates-v0.2.yaml` (v0.1 superseded); tests **414**; evidence
  schema v0.2 (candidates.json with basis/geometry_change, evaluation.json with
  11 objectives/auxiliary/two decisions, per-candidate 6 files).
- M4d (0.24.1; full-site draft) — a **research draft**, not the canonical
  design: all 55 buildings / 109 units / 2,398 households in **18 rows / 36
  row records / 8 superblocks** against the frozen 44-road network, focus G-01
  preserved; completeness requires the exact expected **55 ids** (missing/
  extra/duplicate → four `FULL_SITE_*` deferred); source→design displacement sum
  **2,328.95 m** (max **147.25 m**, mean **42.34 m**). Full-site checks
  **29 = 11 pass + 11 info + 5 deferred + 2 fail**:
  `FULL_SITE_BOUNDARY_SETBACK`, `FULL_SITE_BUILDING_OVERLAP`,
  `FULL_SITE_NS_SPACING` (min 19.999999999999943 m; 20 m is the candidate
  row-rhythm + basis assumption, not a universal rule) and
  `FULL_SITE_ROAD_CLEARANCE` (min 3.0163622902759215 m) pass;
  `DESIGNED_GREEN_RATIO` is **deferred** (designed green 15.93% <30%; the
  61.06% account is `POTENTIAL OPEN SPACE ... NOT LANDSCAPE DESIGN` on
  `L-OPEN-SPACE`, classification `potential_open_space`, auxiliary only);
  **`ROAD_ACCESS_COVERAGE` fail 0.0** (17 relation errors) and
  **`DEAD_END_RESOLUTION` fail 17 unresolved**. Under the fixed network /
  uniform row grid / current search family, caps 25–130 m found no complete
  layout; unbounded search produced the 147.25 m candidate; the global minimum
  is **not proven**. Regenerating roads fails clearance (min 0 m, 17 buildings
  below 3 m). Contract `design-synthesis-v0.9.yaml` (v0.8 superseded; 29 design
  + 3 DXF = 32 items). Focus evidence 29 = 9 pass + 11 info + 9 deferred
  (designed green 6.54% <30%, deferred; the 61.46% table is auxiliary only;
  four `FULL_SITE_*` deferred). Full-site DXF **553 entities**, readback
  553/553, XDATA 11, privacy pass; CAD title `DESIGNED GREEN 15.93% -
  INCOMPLETE` + `INCOMPLETE: ROAD ACCESS 0/17 - DEAD ENDS 17 UNRESOLVED -
  DESIGNED GREEN < 30%`. 3.016362/19.999999 are model-coordinate internal
  consistency, not survey-grade. Tests **472 at M4d**.
- M4d-2a (0.26.0) design-intent audit — **descriptive only, no algorithm/gate change**: 17 groups are inferred (45 m + 8 m main buffer + Union-Find; G-01 9 inferred vs 7 focus; chain max 209.738 m; `not_designer_confirmed`); B non-contiguous **12/17**, runs 43, displacement mean 47.92/P90 102.83/max 278.46 (A/baseline 10/17, max 147.25). Corrected green table: building-occupied **845.541/845.541/713.445 m²**, road-occupied **64.113/320.949/73.815 m²**, retained **10,076.757 (91.72%)/9,819.92 (89.38%)/10,199.151 (92.83%)**, preserved/shrunk/cancelled **7/5/0**; area ≠ intent. Access L1 **17/17**, L2 **0/17**, L3 **15/24/26 of 55**, L4 5 entrances/2 proximity/**0 driveway**; no combined coverage. 0.1 m independent perturbation → **100% <3.0** (B min 2.8887; common datum unchanged); four-level B = geometric pass/intent descriptive/deferred 5/host not_verified; tests **556**.
- M4d-2 (0.25.0) A/B building-road co-design — a **research draft**: A (fixed
  M4d-1 layout + rebuilt 17 connectors, 16 branch + 1 access, 362.0944726221448 m)
  gets access 17/17, 0 relation errors and 0 unresolved dead ends but fails only
  `FULL_SITE_ROAD_CLEARANCE` at served-face **2.8250521190593507 m <3 m**
  (structural terminal-band/branch-width conflict, not tolerance-widened;
  check status 12 pass + 11 info + 5 deferred + 1 fail). B (group-preserving
  layout, 17 groups / 39 rows) is **hard-valid 29 = 13 pass + 11 info + 5
  deferred + 0 fail** (access 17/17, band 3.499999 m, boundary/overlap, NS 20.0,
  clearance **3.0164672267820585 m**, dead 0); honest residuals are **12 group
  splits**, group-centroid max **140.12 m**/mean **33.99 m**, single-building
  max **278.46 m**. Hard-first recommends **B**, excludes **A**, no score/ranking.
  Candidate DXF delivered: A **584 entities/readback 584/584** (`INCOMPLETE`),
  B **587/587** (`HARD-VALID`), XDATA 11/privacy/audit 0; connector sidewalks
  clipped 17/115.202 m² and A/B sidewalk overlap 0; `comparison.svg` three
  panels. Tests **515**.
- M4c-1a (0.16.0) corrected the road-topology defect: explicit shared-coordinate
  junctions, noded graph 1 component (51 nodes / 55 segments, cyclomatic 5,
  dead ends 21, junctions 27, `max_endpoint_gap_m` 0.0); `design-roads.geojson`
  (41 centerlines + 16 explicit junction records) published; control plane
  unchanged. (Historical; rebaselined by M4c-1b and M4c-2.)

### M4c-0 — open-source reuse sprint (merged in PR #34)

`docs/e2e/open-source-reuse-001/` + `experiments/m4c0/`:

- Building Regulariser 0.2.5: 63→61 vertices, area −2.0%, mean Hausdorff
  1.07 m, ERI 0.972→0.984. Cleanup adapter only.
- OSMnx 2.1.1: 309/333 → 257/281 → 117/141 nodes/edges at 8 m consolidation,
  1 component, length −10.7%. Strongest topology candidate.
- PyGeoOps 0.6.0: 11/11 per-area centerlines (78.4% coverage), 10/11
  multi-component.
- PyClothoids: single G1 fit failed quality (356 m Hausdorff, −78 m length).
- momepy: evaluation metrics only. UrbGEN: Rhino/Grasshopper host-blocked.
  Street Generator/rue-lib: not on PyPI, foreign widths.
- Verdicts and rejected uses: `docs/e2e/open-source-reuse-001/reuse-matrix.yaml`.

## 3. Road-topology defect — FIXED in M4c-1a (0.16.0)

The M4c-0 finding ("corridor union 1 polygon, noded graph 5 components",
51 nodes / 50 edges, `cyclomatic: 0`) was real as measured but wrong as a
diagnosis: it was a **sub-ULP floating-point noding artefact** — connector
endpoints sat 1.5e-15–2.1e-14 m off the main lines (GEOS exact predicates
create no node), all 25 main roads were always in one exact component, the
50-edge count is the simple-graph collapse of the closed access loop, and
`cyclomatic: 0` is momepy's connected-graph formula returning 0 on a
disconnected graph.

M4c-1a fix: explicit shared-coordinate junctions (no snap, no rounding, no
tolerance); the noded graph is **1 component** (51 nodes / 55 segments,
cyclomatic 5, dead ends 21, junctions 27, `max_endpoint_gap_m` 0.0);
`ROAD_CONNECTIVITY` now checks the noded graph and fails closed within a
1e-9 m endpoint tolerance (sub-1e-9 misalignment surfaces first as component
count >1); `ROAD_CORRIDOR_COVERAGE` is informational. Evidence:
`design-roads.geojson` (41 centerlines + 16 explicit junction records at the
M4c-1a time point; the current file is 44 centerlines + 21 junction records
after M4c-1b/M4c-1e) and the regenerated
`docs/e2e/design-synthesis-001/` package.

The 4c candidate is still **partial**; the M4d full-site sheet checks N-S spacing
but fails access coverage and dead-end resolution, so it is a research draft.
Do not present either as a finished road design.

## 4. Next work order (status after M4d; order: M4d-2 access/road co-design + real CAD host/R1 in parallel)

1. ~~Add an optional OSMnx adapter~~ — **superseded**: the fix is
   dependency-free (explicit shared-coordinate junctions); OSMnx remains an
   optional source-skeleton preprocessor, never the design base.
2. ~~Replace the corridor-only connectivity check~~ — **done** (noded check,
   fail-closed within a 1e-9 m endpoint tolerance; `ROAD_CORRIDOR_COVERAGE`
   informational; contract `design-synthesis-v0.9.yaml`).
3. ~~Regenerate the 4c candidate~~ — **done** (M4c-1b/1e/2 and Phase 0 in
   0.22.0; 44 roads, coverage 1.0, declared `serves_group_ids` evidence,
   boundary-containment hard check, 211-entity DXF with audit 0/0 and full
   readback).
4. ~~M4c-2 main-road alignment~~ — **done in 0.21.0 and corrected by Phase 0 in
   0.22.0**: the `MAIN_ROAD_BUILDING_OVERLAP` pass now uses the split fields
   (`main_before` 38.19068149970835 → `main_after` 0.0; `new_access`
   0.9943558185246757; `total_after` 0.9943558185246756), and
   `ROAD_BOUNDARY_CONTAINMENT` is a hard pass (margin 0.6735131264650868;
   MAIN-08/16/18 repairs). The alignment semantics are
   `local_search_exhausted`, not a proof of optimality.
5. ~~Multi-candidate design evaluation~~ — **first experiment done in 0.22.0
   and evaluation integrity fixed in M4c-3a/0.23.0**: A/B1/B2/C all hard-pass;
   all-44-road geometry by class/terminal; basis fingerprint binding;
   `HISTORICAL_BOUNDARY_ARCHIVE` separated from current candidates; 11
   single-unit objectives with auxiliary excluded; default preference recommends
   B1, road-first recommends A; Pareto [B1,B2,C,A]; reasons for every candidate,
   no single score. The current B1 is the boundary-repaired candidate
   (margin 0.6735); its pre-repair form is archival only.
6. ~~M4d — full-site layout~~ — **full-site research draft in 0.24.1**: 55
   buildings / 109 units / 2,398 households, 18 rows / 36 row records / 8
   superblocks against the frozen 44-road network; boundary/overlap/NS
   spacing/road clearance pass, but `DESIGNED_GREEN_RATIO` is **deferred**
   (designed green 15.93% <30%; the 61.06% account is `POTENTIAL OPEN SPACE ...
   NOT LANDSCAPE DESIGN`, auxiliary), and
   **`ROAD_ACCESS_COVERAGE` fail 0.0 (17 relation errors)** and
   **`DEAD_END_RESOLUTION` fail 17 unresolved**. Under the fixed network /
   uniform row grid / current search family, caps 25–130 m found no complete
   layout; the unbounded search produced the 147.25 m candidate, not a proven
   global minimum. **M4d-2 open:** recompute access declarations/terminals or
   generate clearance-preserving road geometry (and then re-check dead ends).
7. ~~M4d-2 A/B co-design~~ — **research draft in 0.25.0**: A fails only
   `FULL_SITE_ROAD_CLEARANCE` (served-face 2.825 m); B hard-valid (29 = 13/11/5/0,
   access 17/17, dead 0) with 12 group splits and honest displacement residuals;
   hard-first recommends B, A excluded; A/B DXF 584/587 delivered. **M4d-2a
   design-intent audit (0.26.0, descriptive only):** inferred 17 groups; B 12/17
   fragmented, 43 runs, max displacement 278.46; corrected green table 845.541/
   845.541/713.445 m² building-occupied and 7/5/0 preserved/shrunk/cancelled;
   access L1 17/17, L2 0/17, L3 15/24/26, L4 0 driveway; 0.1 m perturbation 100%
   <3 m; four-level B geometric pass/intent descriptive/deferred 5/host
   not_verified. **Open:** resolve served-facade/terminal-band conflict and run
   M4d-2b candidate C.
8. **Real CAD host/external evidence** — LibreCAD/FreeCAD/AutoCAD GUI, a real
   design-office profile and IFC remain open; the committed DXF evidence is
   same-library ezdxf readback only.
9. Replace the provisional 24×11 m staircase module with the designer’s
   unit-type library — open (designer input).
10. Design driveways/garage access (`PARKING_DRIVEWAY_CONNECTION` deferred) and
    review the 19 remaining dead ends (17 planned group terminals + 2 site-edge
    termini) in the full-site design — open.

Acceptance for step 3 (met): the noded graph is 1 component; FAR remains
inside 1.55–1.60; parking ≥1/household; focus spacing ≥20 m; DXF remains
editable with audit 0/0 and full readback; all design objects stay
`rule_derived` `design_draft`. M4c-1e acceptance (met): every group is served
by its declared access road, the terminal centreline distance is in
[3.4, 3.5] m with a separate corridor-edge clearance, and relation errors are
zero — with no design-geometry change. M4c-2 acceptance (met): 26 checks =
8 pass + 11 info + 7 deferred; main-road overlap 0.0 m² after a recorded
alignment (+45 vertices, ids preserved); 7/7 dead ends resolved; access remains
17/17 declared; DXF content 211 entities with audit 0/0 and readback 211/211;
`FULL_SITE_ROAD_CLEARANCE` remains deferred. M4c-3 acceptance (met): Phase 0
boundary containment is a hard pass (margin 0.6735131264650868; MAIN-08/16/18
repairs), the overlap fields are split (`main_before` 38.19068149970835 /
`main_after` 0 / `new_access` 0.9943558185246757 / `total_after`
0.9943558185246756), 27 checks = 9 pass + 11 info + 7 deferred (+3 DXF = 30),
the four candidates A/B1/B2/C all hard-pass, the default/road-first
recommendations are B1/A with Pareto [B1,B2,C,A], and tests are 396 passed at
the M4c-3 time point;
B1 is only a candidate baseline. M4c-3a acceptance (met): every candidate
publishes `parent_basis_id` + canonical fingerprint (missing/mismatch fails
`basis_ok`), all 44 roads are compared by class and group terminal (A BR-G-08
2.826 / G-08 terminal 2.826; B1 BR-G-09 7.352; B2 13.645; C BR-G-08 76.700 /
G-08 terminal 75.315), `HISTORICAL_BOUNDARY_ARCHIVE` is separate from current
candidate verdicts (current B1 boundary-compliant 0.6735; pre-repair archival),
11 single-unit objectives exclude auxiliary metrics from Pareto/preferences,
contract `design-candidates-v0.2` is live (v0.1 superseded), and tests are
**414 passed at M4c-3a**. M4d acceptance (research draft): all 55 buildings / 109 units /
2,398 households conserved and focus G-01 preserved; 18 rows / 36 row records / 8
superblocks; boundary setback, building overlap, NS spacing 19.999999999999943 m
and road clearance 3.0163622902759215 m pass; designed green is **15.93% (<30%,
deferred; the 61.06% open-space tiling is auxiliary only)**; the two honest fails
are `ROAD_ACCESS_COVERAGE` 0.0 (17 relation errors) and `DEAD_END_RESOLUTION` 17
unresolved; full-site DXF 553/553, XDATA 11, privacy pass; contract v0.9 and
**472 tests at M4d**. M4d-2 acceptance (research draft): A excluded solely for
`FULL_SITE_ROAD_CLEARANCE` at served-face 2.825 m; B hard-valid 29 = 13/11/5/0
with access 17/17, dead 0, clearance 3.0164672267820585 m; A/B DXF 584/587,
readback 584/584 and 587/587, XDATA 11, privacy, audit 0; sidewalk overlap 0;
tests **515**.

## 5. Non-negotiable constraints

- Publish the sketch only. DWG/DXF, redline/project coordinates, calibration
  matrix and project metric scale stay private; raw assets in gitignored
  `_incoming/`.
- Never bypass the `human_confirmed_trace` gate for **source geometry**.
- The autonomous design draft needs no human gate, but must never claim
  `human_confirmed`, code compliance, adoption or official issue.
- No fabricated evidence. Blocked runs are recorded as `blocked`.
- Unknown height / road class stays unknown; never derive road width from an
  unconfirmed class.
- Same-library ezdxf readback is not third-party evidence.
- Archived research is historical evidence, not a living contract.
- Foreign design defaults are not Chinese standards.
- **Every new core design capability must first check the R0 open-source
  research, test the candidate, then decide wrap / self-build / abandon.**
- Do not add optional libraries to core dependencies just because R0 graded
  them S; do not replace design quality with test or documentation counts.
- Report local file paths, not only links.

## 6. Local file map

Design synthesis:

- `src/dgcad_design/basis.py` — design basis + math checks.
- `src/dgcad_design/input.py` — sketch → local metric design input.
- `src/dgcad_design/intent.py` — grouping, main-road barrier, focus group.
- `src/dgcad_design/buildings.py` — standard module, focus rect, row layout.
- `src/dgcad_design/roads.py` — main/branch/access hierarchy, corridors.
- `src/dgcad_design/green.py`, `parking.py`, `consistency.py`.
- `src/dgcad_design/scene.py`, `drawing.py`, `project.py`.
- `scripts/design/run_design_synthesis_001.py`.
- `fixtures/design/design-basis-001.yaml`, `design-profile-001.yaml`.
- `contracts/design-synthesis-v0.9.yaml` (v0.8/v0.7/v0.6/v0.5/v0.4/v0.3/v0.2/v0.1
  superseded) and `contracts/design-candidates-v0.2.yaml` (v0.1 superseded).
- `src/dgcad_design/candidates.py`, `evaluation.py`, `visuals.py`.
- `scripts/design/build_candidate_experiment.py`,
  `scripts/design/run_candidate_synthesis.py`,
  `scripts/design/render_visuals.py`.

CAD delivery:

- `src/dgcad_cad/ir.py`, `dxf.py`, `validator.py`.
- `contracts/cad-ir-v0.1.yaml`, `contracts/domain-contract-v0.1.yaml`.
- `contracts/sketch-domain-handoff-v0.2.yaml` (living), v0.1 superseded.

Experiments / evidence:

- `experiments/m4c0/common.py`, `exp_a_building.py`, `exp_b_roads.py`,
  `exp_c_collaborative.py`, `run_all.py`, `requirements-reuse.txt`.
- `docs/e2e/design-synthesis-001/` (evidence incl. `design-proposal.dxf`,
  `design-roads.geojson`, `design-preview.svg/.png`, `design-overlay.svg`,
  `design-summary.json`).
- `docs/e2e/design-candidates-001/` (`candidates.json`, `evaluation.json`,
  `comparison.svg`, `candidates.json`, per-candidate
  `candidate-summary.json`/`plan.svg`/`design-consistency.json`/`design-roads.geojson`).
- `docs/e2e/open-source-reuse-001/` (matrix, README, exp-a/b/c artifacts).
- `docs/e2e/sketch-handoff-a/` (blocked pilot evidence).

Tests:

- `tests/test_design_synthesis.py` (9), `tests/test_design_topology.py` (14),
  `tests/test_design_contract.py` (13), `tests/test_design_basis.py` (20),
  `tests/test_green_parking_semantics.py` (9), `tests/test_privacy_scan.py` (20),
  `tests/test_road_access.py` (33), `tests/test_road_access_generation.py` (13),
  `tests/test_parking_geometry.py` (6).
- `tests/test_main_alignment.py` (11), `tests/test_candidates.py` (17),
  `tests/test_evaluation.py` (27), `tests/test_visuals.py` (13).
- `tests/test_full_site_layout.py` (16), `tests/test_full_site_constraints.py`
  (29), `tests/test_full_site_evidence.py` (13).
- `tests/test_co_design_access.py` (11), `tests/test_group_preserving_layout.py`
  (10), `tests/test_group_metrics.py` (11), `tests/test_co_design_evidence.py`
  (11), `tests/test_intent_metrics.py` (14), `tests/test_green_retention.py` (8),
  `tests/test_access_semantics.py` (9), `tests/test_intent_robustness.py` (4),
  `tests/test_intent_audit_evidence.py` (6).
- `tests/test_open_source_reuse.py` (3).
- `tests/test_sketch_handoff.py` (32), `tests/e2e/test_sketch_handoff_a.py` (6).

Status docs:

- `docs/status.md` §16 (4c), §17 (M4c-0), §18 (non-claims).
- `docs/roadmap.md` Milestone 4c / M4c-0 / “Next research main line”.
- `docs/architecture/overview.md` §19.
- `docs/research-to-product-map.md`.

## 7. Commands

```bash
cd /d/agent-cad
python -m pytest -q
python scripts/design/run_design_synthesis_001.py
python experiments/m4c0/run_all.py
```

Design run rewrites `docs/e2e/design-synthesis-001/`; experiments rewrite
`docs/e2e/open-source-reuse-001/`. Both are deterministic except the DXF byte
hash (see pitfalls).

## 8. Pitfalls learned (do not rediscover)

- **ezdxf byte reproducibility (corrected 2026-10-28)**: output **is**
  byte-identical with the global `ezdxf.options.write_fixed_meta_data_for_testing = True`
  (zero GUID + J2000 date); without it `$TDUPDATE`/`$FINGERPRINTGUID`/
  `$VERSIONGUID` are random. The project never sets the option, so committed
  hashes match the committed files only. Compare content, not bytes — and hash
  **file bytes**, never loaded header metadata (ezdxf regenerates random GUIDs
  in memory on load). Enabling the option would invalidate every committed DXF
  hash including the third-party round-trip input — a separate evidence
  migration, not part of a feature change.
- **Privacy scan false positives**: numeric tokens in raw bytes (e.g. a float
  containing `95119`) are not private data. Scan structured TEXT/MTEXT, XDATA
  and symbol names; skip numeric-only raw tokens. (M4c-1a hardened the scanner
  so 64-hex digests/GUIDs no longer trigger numeric-token false positives.)
- **Hash-pinned evidence artifacts must be byte-stable across platforms**: a
  `.geojson`/JSON evidence file whose sha256 is recorded inside another
  committed file must be written with explicit LF newlines
  (`write_text(..., newline="\n")`) and marked `-text` in `.gitattributes`.
  Otherwise git normalises CRLF→LF and the recorded hash matches the local
  Windows bytes but fails on a clean Linux CI checkout (caught by CI in M4c-1a,
  fixed in `1209955`). Verify the *committed blob* hash
  (`git show :path | sha256`), not just the working-tree file.
- **Blocked handoff runs must not write `domain-fixture.yaml`** (the old stale
  file was deleted; a test forbids it).
- **Invalid sketch polygons**: use `shapely.validation.make_valid` and accept
  Polygon or MultiPolygon (`_valid_polygon` in `input.py`).
- **Road graph construction**: build the topology graph from `unary_union` of
  noded linework, not from per-road endpoints (the latter gave 15 spurious
  components).
- **Noding needs exact shared coordinates**: `nearest_points()` returns a
  projection, not an on-line point; 1e-15 m residuals defeat GEOS exact
  predicates and split the graph. Junctions must be explicit shared vertices
  (M4c-1a `topology.py`); never infer connectivity from a snap tolerance.
- **Focus layout**: search the largest free rectangle inside the focus bbox
  minus main-road corridor + 3 m clearance; drop non-fitting buildings and
  record why. `main_barrier = 8 m` keeps buildings across a main road in
  separate groups.
- **Handoff validation order matters**: kind-specific review checks run before
  scope/quality checks, so `designer_authorized_pilot` reports
  `HUMAN_OBJECT_REVIEW_REQUIRED`, not `PILOT_SCOPE_MISMATCH`.
- **Do not create a second Canonical model**: extend the existing trace /
  adapter / CAD-IR path.
- **XDATA arity**: 11 fields now (11th = `confirmation_scope`); changing it
  requires updating validator, contract and tests together.
- **Test doubles**: never published; only allowed in explicit test runs.
- **DXF content vs bytes (M4c-1e/2/3/3a/M4d)**: design geometry was unchanged in 0.20.0,
  changed in 0.21.0 (206 → **211 entities**) and changed again in Phase 0/0.22.0
  (boundary repairs/alignment; still 211). The committed DXF byte SHA changed
  in each release (0.19.0 `34a65926…`, 0.20.0 `fcc42d32…`, 0.21.0 `0f76c006…`,
  0.22.0 `65fde1ca…`, 0.23.0 `f88c29e1…`, current 0.24.1 `1cb17865…`) because
  ezdxf regenerates `$TDUPDATE`/GUIDs on save — documentation must say "content
  changed/unchanged" as appropriate and never infer content change from SHA
  alone. Base focus evidence content is unchanged in M4c-3a/M4d; its files were
  regenerated, so only the byte SHA moved. `design-roads.geojson` SHA is
  `c5fc7262…`. The full-site DXF is separate: **553 entities**, SHA-256
  `d86ba8d2…`, readback 553/553.
- **Visuals are generated, not hand-made**: `scripts/design/render_visuals.py`
  regenerates `design-preview.svg`/`.png` and `design-overlay.svg` from the
  current evidence; SVG is always written, PNG only when matplotlib is
  importable (the project adds no dependency). The overlay's before layer uses
  the alignment records' original/adjusted geometry, not a pre-M4c-2 full
  history; visuals are re-rendered after the final evidence. Candidate visuals
  come from `build_candidate_experiment.py`/`render_visuals.py`.

## 9. Open threads needing a decision or external input

- The designer’s unit-type library is still missing; six source buildings have
  length-vs-area unit-count conflicts: `SK-BLD-0009`, `0010`, `0011`, `0013`,
  `0015`, `0018`. The kindergarten/facility classification is also unresolved.
- Full-site 20 m spacing is deferred; it may require dropping or reshaping more
  buildings than the focus block, and that policy has not been agreed.
- The main-road/building overlap is **resolved** (`MAIN_ROAD_BUILDING_OVERLAP` pass:
  `main_before` 38.19068149970835 → `main_after` 0.0 m²; after the MAIN-08
  boundary repair the remaining main conflict was 34.421783197612406 → 0;
  Phase 0 also added the `ROAD_BOUNDARY_CONTAINMENT` hard check with margin
  0.6735131264650868 and MAIN-08/16/18 repairs). On the focus sheet the four
  `FULL_SITE_*` checks remain deferred; the full-site experiment separately
  passes boundary/overlap/NS spacing/clearance/green but fails access and
  dead-end resolution. Entrance proximity is 2 of 5 but
  no driveway is designed (`PARKING_DRIVEWAY_CONNECTION` deferred); the 7
  previously unresolved dead ends are resolved on the focus sheet
  (`DEAD_END_RESOLUTION` pass, 0 unresolved), leaving 19 = 17 planned group
  terminals + 2 site-edge termini.
- The first multi-candidate experiment (A/B1/B2/C) is complete, and M4c-3a fixed
  evaluation integrity: default recommendation B1, road-first recommendation A,
  Pareto [B1,B2,C,A], no single score; 11 single-unit objectives with auxiliary
  excluded, all-44-road class/terminal evidence, basis fingerprint binding, and
  `HISTORICAL_BOUNDARY_ARCHIVE` separated from current candidates. The current
  B1 is the boundary-repaired candidate (margin 0.6735); its pre-repair 66.235 m
  form is archival and never a hard pass. B1 is only a candidate baseline; the
  candidate set is not exhaustive and no candidate is a professional or
  human-confirmed design.
- M4d full-site expansion is complete as a **research draft** (0.24.1): 55
  buildings / 109 units / 2,398 households in 18 rows / 36 row records / 8
  superblocks; boundary/overlap/NS-spacing/road-clearance pass, designed green
  15.93% deferred (the 61.06% account is `POTENTIAL OPEN SPACE ... NOT
  LANDSCAPE DESIGN`, auxiliary), but `ROAD_ACCESS_COVERAGE` 0.0 (17 relation
  errors) and `DEAD_END_RESOLUTION` 17 unresolved fail. The frozen network + old
  access declarations make clearance and access coverage mutually incompatible.
  Full-site DXF 553/553, XDATA 11, privacy pass; tests 472 at M4d. **M4d-2
  A/B co-design (0.25.0, research draft):** A fails only
  `FULL_SITE_ROAD_CLEARANCE` at served-face 2.825 m; B is hard-valid
  (29 = 13/11/5/0; access 17/17, dead 0; 12 group splits; group-centroid max
  140.12 m / mean 33.99 m; single max 278.46 m); hard-first recommends B and
  excludes A; A/B DXF **584/587** delivered (`INCOMPLETE` / `HARD-VALID`),
  XDATA 11/privacy/audit 0; connector sidewalk 17/115.202 m² and sidewalk
  overlap 0; tests 515 at M4d-2. **M4d-2a design-intent audit (0.26.0,
  descriptive only):** 17 groups inferred (G-01 9 vs 7, chain 209.738 m;
  `not_designer_confirmed`); B 12/17 fragmented, 43 runs, displacement max
  278.46; corrected green table building-occupied 845.541/845.541/713.445 m²,
  retained 10,076.757/9,819.92/10,199.151 m², preserved/shrunk/cancelled 7/5/0;
  access L1 17/17, L2 0/17, L3 15/24/26, L4 0 driveway; 0.1 m independent
  perturbation 100% <3.0 (B min 2.8887); four-level B geometric pass/intent
  descriptive/deferred 5/host not_verified; tests **556**. **Next:** M4d-2b
  candidate C + resolve served-facade/terminal-band conflict, plus a real CAD
  host (LibreCAD/FreeCAD/AutoCAD GUI), a real design-office profile, IFC and R1
  closure; the committed DXF evidence is same-library ezdxf readback.
- `EP-R1-SKETCH-001` remains in progress; `R1-G07` partial;
  `EP-R1-DESIGN-001` in progress.
