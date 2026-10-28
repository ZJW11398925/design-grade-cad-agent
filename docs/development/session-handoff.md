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
> `docs/status.md` §2/§16–18、`docs/roadmap.md` 的 M4c-1b/4c-1e 与 Next 块、以及
> `docs/e2e/design-synthesis-001/README.md`。当前版本 0.20.0（M4c-1e 证据绑定：道路接入
> 改为声明式 `serves_group_ids`，25 项检查 = 6 pass + 10 info + 9 deferred，测试 334）。
> 下一步顺序：M4c-2 主路对齐（MAIN-19/08 38.19 m² 重叠）→ 多候选设计评价 → 全站点展开
> 与 20 m 间距。不要新增核心依赖，不要声称 human_confirmed / 合规 / 已采纳，不要重写
> Foundation/Runtime/CAD-IR。

## 1. Repo state (verified 2026-10-28)

- `main` is the integration branch: **PR #34 merged as merge commit `e40f468`**
  (Milestone 4c — autonomous design synthesis + M4c-0 reuse + M4c-1a/1c fixes),
  **PR #36 merged as merge commit `0546649`** (M4c-1d semantic residuals),
  **PR #38 merged as merge commit `7a3e70a`** (M4c-1b design-aware road access),
  **PR #39 merged as merge commit `3e50399`** (docs: record PR #38 merge) and
  **PR #40 merged as merge commit `7f81f0e`** (M4c-1e declared access evidence);
  main CI is 4/4 green on all.
- The old topic branches `milestone-4c-autonomous-design`,
  `fix/m4c-1d-semantic-residuals`, `feat/m4c-1b-road-access` and
  `fix/m4c-1e-evidence-binding` contain the same history (M4c-1a `9d4ae56` +
  `1209955`, M4c-1c `e02337b`, M4c-1d `2f396b2`, M4c-1b `2750bc5`). **Start new
  work from `main`** — e.g. `feat/m4c-2-main-alignment` or
  `feat/m4c-multi-candidate`.
- Version: `0.20.0` (`pyproject.toml`).
- Contract: `design-synthesis-v0.6.yaml` (v0.5/v0.4/v0.3/v0.2/v0.1 superseded;
  gate-register pointer → v0.6).
- Test baseline: **334 passed** (`python -m pytest -q`).
- Milestone order: M4c-1d honest-semantics residuals (**complete**) →
  M4c-1b road service coverage (**complete** — first design-geometry change:
  44 roads, coverage 1.0, DXF 206 entities) → M4c-1e evidence binding
  (**complete** — declared `serves_group_ids` access relations, 25 checks =
  6 pass + 10 info + 9 deferred, no design-geometry change) → **next: M4c-2
  main-road alignment** (MAIN-19/08 38.19 m² overlap) → multi-candidate design
  evaluation → full-site expansion with basis confirmation.
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
- **206-entity** editable DXF (was 208 before M4c-1b), audit 0/0, readback
  206/206, 23 design layers,
  title block "AGENT-GENERATED PROPOSAL - NOT HUMAN-CONFIRMED - NOT
  CODE-COMPLIANCE" (ASCII hyphens, as in the DXF).
- All design objects `rule_derived`, world `proposal_preview`,
  `confirmation_scope: design_draft`, `human_confirmed: false`.
- Consistency: **25 declared checks** (M4c-1e) — **6 pass** (FOCUS_NS_SPACING,
  FOCUS_BOUNDARY_SETBACK, FOCUS_BUILDING_OVERLAP, FOCUS_ROAD_CLEARANCE,
  ROAD_CONNECTIVITY, ROAD_ACCESS_COVERAGE); **10 info** (FAR_ARITHMETIC_SCENARIO,
  PARKING_REQUIREMENT_ARITHMETIC, PARKING_ENTRANCE_COUNT,
  PARKING_ENTRANCE_PROXIMITY, UNIT_COUNT_BASIS_INVARIANT,
  ROAD_CORRIDOR_COVERAGE, DEAD_END_JUSTIFICATION, ROAD_WIDTH_ASSIGNMENT,
  CANDIDATE_OPEN_SPACE_RATIO, UNBUILT_RATIO); **9 deferred** (PARKING_CAPACITY,
  PARKING_DRIVEWAY_CONNECTION, PARKING_LAYOUT, MAIN_ROAD_BUILDING_OVERLAP,
  FULL_SITE_ROAD_CLEARANCE, DEAD_END_RESOLUTION, DESIGNED_GREEN_RATIO,
  FULL_SITE_NS_SPACING, FAR_FINAL_VERIFICATION — value None).
  `info`/`deferred` are not `pass`.
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
- M4c-1a (0.16.0) corrected the road-topology defect: explicit shared-coordinate
  junctions, noded graph 1 component (51 nodes / 55 segments, cyclomatic 5,
  dead ends 21, junctions 27, `max_endpoint_gap_m` 0.0); `design-roads.geojson`
  (41 centerlines + 16 explicit junction records) published; control plane
  unchanged.

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

The 4c candidate is still **partial** (full-site north-south spacing
deferred). Do not present it as a finished road design.

## 4. Next work order (status after M4c-1e; order: M4c-2 main-road alignment → multi-candidate evaluation → full-site expansion)

1. ~~Add an optional OSMnx adapter~~ — **superseded**: the fix is
   dependency-free (explicit shared-coordinate junctions); OSMnx remains an
   optional source-skeleton preprocessor, never the design base.
2. ~~Replace the corridor-only connectivity check~~ — **done** (noded check,
   fail-closed within a 1e-9 m endpoint tolerance; `ROAD_CORRIDOR_COVERAGE`
   informational; contract `design-synthesis-v0.6.yaml`).
3. ~~Regenerate the 4c candidate~~ — **done** (M4c-1b/M4c-1e; 44 roads, coverage
   1.0, declared `serves_group_ids` evidence, 206-entity DXF content with
   audit 0/0 and full readback).
4. **M4c-2 main-road alignment** — resolve the pre-existing 38.19 m²
   MAIN-19/08 road/building overlap; it is currently a deferred machine check
   (`MAIN_ROAD_BUILDING_OVERLAP`, `known_unresolved`), not a pass.
5. **Expand from focus G-01 to all groups** and enforce 20 m north-south
   spacing site-wide (`FULL_SITE_NS_SPACING`), plus full-site road clearance
   (`FULL_SITE_ROAD_CLEARANCE`) — open; the spacing policy needs agreement.
6. Add design evaluation/search: intent preservation, completeness, internal
   consistency, verified constraint satisfaction, CAD editability; compare
   candidates instead of scoring one — open.
7. Replace the provisional 24×11 m staircase module with the designer’s
   unit-type library — open (designer input).
8. Resolve the 7 unresolved dead ends (5 unfinished main stubs + 2
   unclassified) and design driveways/garage access — open.

Acceptance for step 3 (met): the noded graph is 1 component; FAR remains
inside 1.55–1.60; parking ≥1/household; focus spacing ≥20 m; DXF remains
editable with audit 0/0 and full readback; all design objects stay
`rule_derived` `design_draft`. M4c-1e acceptance (met): every group is served
by its declared access road, the terminal centreline distance is in
[3.4, 3.5] m with a separate corridor-edge clearance, and relation errors are
zero — with no design-geometry change.

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
- `contracts/design-synthesis-v0.6.yaml` (v0.5/v0.4/v0.3/v0.2/v0.1 superseded).

CAD delivery:

- `src/dgcad_cad/ir.py`, `dxf.py`, `validator.py`.
- `contracts/cad-ir-v0.1.yaml`, `contracts/domain-contract-v0.1.yaml`.
- `contracts/sketch-domain-handoff-v0.2.yaml` (living), v0.1 superseded.

Experiments / evidence:

- `experiments/m4c0/common.py`, `exp_a_building.py`, `exp_b_roads.py`,
  `exp_c_collaborative.py`, `run_all.py`, `requirements-reuse.txt`.
- `docs/e2e/design-synthesis-001/` (16 files incl. `design-proposal.dxf`,
  `design-roads.geojson`, `design-preview.png`, `design-summary.json`).
- `docs/e2e/open-source-reuse-001/` (matrix, README, exp-a/b/c artifacts).
- `docs/e2e/sketch-handoff-a/` (blocked pilot evidence).

Tests:

- `tests/test_design_synthesis.py` (9), `tests/test_design_topology.py` (14),
  `tests/test_design_contract.py` (11), `tests/test_design_basis.py` (20),
  `tests/test_green_parking_semantics.py` (9), `tests/test_privacy_scan.py` (20),
  `tests/test_road_access.py` (23), `tests/test_road_access_generation.py` (13),
  `tests/test_parking_geometry.py` (6).
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
- **DXF content vs bytes (M4c-1e)**: design geometry was unchanged in 0.20.0, but
  the committed DXF byte SHA changed (0.19.0 `34a65926…`, 0.20.0 `fcc42d32…`)
  because ezdxf regenerates `$TDUPDATE`/GUIDs on save. Documentation must say
  "content unchanged", never "SHA unchanged". `design-roads.geojson` SHA changes
  (59df13d8… → d77ce7a8…) because new fields are added — expected.

## 9. Open threads needing a decision or external input

- The designer’s unit-type library is still missing; six source buildings have
  length-vs-area unit-count conflicts: `SK-BLD-0009`, `0010`, `0011`, `0013`,
  `0015`, `0018`. The kindergarten/facility classification is also unresolved.
- Full-site 20 m spacing is deferred; it may require dropping or reshaping more
  buildings than the focus block, and that policy has not been agreed.
- Pre-existing 38.19 m² main-road/building overlap (MAIN-19 34.42 + MAIN-08
  3.77) is a deferred machine check (`MAIN_ROAD_BUILDING_OVERLAP`,
  `known_unresolved`) deferred to M4c-2; full-site road clearance is also
  deferred (`FULL_SITE_ROAD_CLEARANCE`). Entrance proximity is 2 of 5 but no
  driveway is designed (`PARKING_DRIVEWAY_CONNECTION` deferred), and 7 dead ends
  remain unresolved (5 unfinished main stubs + 2 unclassified,
  `DEAD_END_RESOLUTION` deferred).
- Real CAD host loop (LibreCAD/FreeCAD/AutoCAD) remains deferred; issue #6 open.
- `EP-R1-SKETCH-001` remains in progress; `R1-G07` partial;
  `EP-R1-DESIGN-001` in progress.
