# Session handoff — 2026-10-27

Purpose: continue DGCAD work in a fresh conversation without re-deriving
context. This file is the single source of continuation state. It is a
development note, not a living contract.

Repository: `D:\agent-cad`

> **2026-10-28 team audit update:** §3 (defect root cause), §4 (next work
> order) and §8 (DXF byte-reproducibility) of this handoff are corrected by
> `docs/development/team-continuation-dossier.md`. Read that dossier before
> acting on this handoff; the rest of this document is still accurate.

## 0. Paste-ready first message for the new conversation

> 先读 `D:\agent-cad\docs\development\session-handoff.md`，再读其中列出的
> `docs/roadmap.md`（Milestone 4c-1a / 4c / M4c-0）、`docs/status.md` §16–18 和
> `docs/e2e/design-synthesis-001/README.md`。4c 道路拓扑缺陷已在 M4c-1a（v0.16.0）
> 修正：显式共享坐标 junction、不依赖容差的 noded 拓扑检查（1 连通分量），证据已重
> 生成并发布 design-roads.geojson。当前最高优先级是 4c-1b：支路接入入口、G-05/G-12
> 覆盖，然后全站点展开与 20 m 间距。不要新增核心依赖，不要声称 human_confirmed /
> 合规 / 已采纳，不要重写 Foundation/Runtime/CAD-IR。

## 1. Repo state (verified 2026-10-28)

- Branch: `milestone-4c-autonomous-design`; M4c-1a is committed, working tree
  clean.
- Latest commit: `9d4ae56 feat(design): M4c-1a noded road-topology truth and explicit junctions`.
- `main`: `4f6698b` (Milestone 4b.1 merged as PR #33).
- Open PR: **#34** “Milestone 4c — autonomous design synthesis + M4c-0
  open-source reuse”; 4/4 CI jobs green (Ubuntu/Windows × Python 3.11/3.13).
- Version: `0.16.0` (`pyproject.toml`).
- Test baseline: **259 passed** (`python -m pytest -q`).
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

### Milestone 4c — first autonomous design draft (on PR #34)

`docs/e2e/design-synthesis-001/`:

- Design basis satisfies the three stated constraints: FAR **1.5654** inside
  1.55–1.60; **2,398 parking spaces** = 1.0/household; **20.0 m** north-south
  spacing in focus group G-01.
- Full-site context: 55 buildings, 109 staircases, 2,398 households,
  319,536 m² GFA, 3,000 m² facility, 5 garage entrances.
- Focus G-01: 7 standardized buildings / 16 units; dropped `SK-BLD-0038` (2U)
  and `SK-BLD-0061` (1U) with recorded reasons.
- 208-entity editable DXF, audit 0/0, readback 208/208, 23 design layers,
  title block "AGENT-GENERATED PROPOSAL - NOT HUMAN-CONFIRMED - NOT
  CODE-COMPLIANCE" (ASCII hyphens, as in the DXF).
- All design objects `rule_derived`, world `proposal_preview`,
  `confirmation_scope: design_draft`, `human_confirmed: false`.
- Consistency: 13 declared checks — 11 pass, `ROAD_CORRIDOR_COVERAGE`
  informational, `FULL_SITE_NS_SPACING` explicitly deferred.
- M4c-1a (0.16.0) corrected the road-topology defect: explicit shared-coordinate
  junctions, noded graph 1 component (51 nodes / 55 segments, cyclomatic 5,
  dead ends 21, junctions 27, `max_endpoint_gap_m` 0.0); `design-roads.geojson`
  (41 centerlines + 16 explicit junction records) published; control plane
  unchanged.

### M4c-0 — open-source reuse sprint (on PR #34)

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
`design-roads.geojson` (41 centerlines + 16 explicit junction records) and
the regenerated `docs/e2e/design-synthesis-001/` package.

The 4c candidate is still **partial** (full-site north-south spacing
deferred). Do not present it as a finished road design.

## 4. Next work order (status after M4c-1a)

1. ~~Add an optional OSMnx adapter~~ — **superseded**: the fix is
   dependency-free (explicit shared-coordinate junctions); OSMnx remains an
   optional source-skeleton preprocessor, never the design base.
2. ~~Replace the corridor-only connectivity check~~ — **done** (noded check,
   fail-closed within a 1e-9 m endpoint tolerance; `ROAD_CORRIDOR_COVERAGE`
   informational; contract `design-synthesis-v0.2.yaml`).
3. ~~Regenerate the 4c candidate~~ — **done** (same FAR / parking / 20 m /
   green / CAD checks pass; 208-entity DXF unchanged; `design-roads.geojson`
   published). Design-aware coverage (branch → entrance access, G-05/G-12) is
   **M4c-1b**, still open.
4. **Expand from focus G-01 to all groups** and enforce 20 m north-south
   spacing site-wide (`FULL_SITE_NS_SPACING`) — open; the spacing policy needs
   agreement (dossier §8).
5. Add design evaluation/search: intent preservation, completeness, internal
   consistency, verified constraint satisfaction, CAD editability; compare
   candidates instead of scoring one — open.
6. Replace the provisional 24×11 m staircase module with the designer’s
   unit-type library — open (designer input).

Acceptance for step 3 (met): the noded graph is 1 component; FAR remains
inside 1.55–1.60; parking ≥1/household; focus spacing ≥20 m; DXF remains
editable with audit 0/0 and full readback; all design objects stay
`rule_derived` `design_draft`.

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
- `contracts/design-synthesis-v0.2.yaml` (v0.1 superseded).

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
  `tests/test_design_contract.py` (7), `tests/test_privacy_scan.py` (20).
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
  and symbol names; skip numeric-only raw tokens.
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

## 9. Open threads needing a decision or external input

- Merge PR #34 now? (Update 2026-10-28: M4c-1a fixed the road topology; the
  earlier "fix topology first" recommendation is satisfied — merge the
  corrected candidate.)
- The designer’s unit-type library is still missing; six source buildings have
  length-vs-area unit-count conflicts: `SK-BLD-0009`, `0010`, `0011`, `0013`,
  `0015`, `0018`. The kindergarten/facility classification is also unresolved.
- Full-site 20 m spacing is deferred; it may require dropping or reshaping more
  buildings than the focus block, and that policy has not been agreed.
- Real CAD host loop (LibreCAD/FreeCAD/AutoCAD) remains deferred; issue #6 open.
- `EP-R1-SKETCH-001` remains in progress; `R1-G07` partial;
  `EP-R1-DESIGN-001` in progress.
