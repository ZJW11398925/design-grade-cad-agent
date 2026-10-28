# Session handoff — 2026-10-27

Purpose: continue DGCAD work in a fresh conversation without re-deriving
context. This file is the single source of continuation state. It is a
development note, not a living contract.

Repository: `D:\agent-cad`

## 0. Paste-ready first message for the new conversation

> 先读 `D:\agent-cad\docs\development\session-handoff.md`，再读其中列出的
> `docs/roadmap.md`（Milestone 4c / M4c-0）、`docs/status.md` §16–18 和
> `docs/e2e/design-synthesis-001/README.md`。当前最高优先级是修复 4c 的道路拓扑
> 缺陷：新增可选 OSMnx 适配器，用 noded 中心线拓扑检查替换 corridor-union
> 检查，然后在真正连通的网络上重生成候选，并用同一套 FAR/停车/20 m 指标复验。
> 不要新增核心依赖，不要声称 human_confirmed / 合规 / 已采纳，不要重写
> Foundation/Runtime/CAD-IR。

## 1. Repo state (verified 2026-10-27)

- Branch: `milestone-4c-autonomous-design`, clean working tree.
- Latest commit: `f812deb feat(research): add M4c-0 open-source design reuse experiments`.
- `main`: `4f6698b` (Milestone 4b.1 merged as PR #33).
- Open PR: **#34** “Milestone 4c — autonomous design synthesis + M4c-0
  open-source reuse”; 4/4 CI jobs green (Ubuntu/Windows × Python 3.11/3.13).
- Version: `0.15.0` (`pyproject.toml`).
- Test baseline: **217 passed** (`python -m pytest -q`, ~21 s locally).
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
  title block “AGENT-GENERATED PROPOSAL — NOT HUMAN-CONFIRMED — NOT
  CODE-COMPLIANCE”.
- All design objects `rule_derived`, world `proposal_preview`,
  `confirmation_scope: design_draft`, `human_confirmed: false`.
- Consistency: 11 checks pass, `FULL_SITE_NS_SPACING` explicitly deferred.

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

## 3. Current defect (highest priority)

The 4c road design is **not topologically connected**, but the check says it is:

- design corridor union = 1 polygon → `ROAD_CONNECTIVITY` passes with value 1;
- the **noded centerline graph of the same 41 design roads = 5 connected
  components** (51 nodes / 50 edges, cyclomatic 0, meshedness 0).

Evidence: `docs/e2e/open-source-reuse-001/exp-c/metrics.json`
(`corrected_road_topology_defect: true`) and the “Known defect found by M4c-0”
section of `docs/e2e/design-synthesis-001/README.md`.

The 4c candidate is therefore **partial**. Do not present it as a finished
road design.

## 4. Next work order

1. **Add an optional OSMnx adapter** (experiment/research path first):
   `RoadGraph → nx.MultiDiGraph → simplify_graph + consolidate_intersections
   (≤8 m) → noded RoadGraph`, preserving source edge IDs and road classes.
   OSMnx must remain optional; import lazily and record the dependency and
   version in the output. Core `pyproject.toml` stays unchanged.
2. **Replace the corridor-only connectivity check** with a noded centerline
   topology check (component count > 1 fails; record nodes, edges, cyclomatic,
   dead ends, and which source edges were consolidated). Keep
   `contracts/` + `ISSUE_CATEGORIES` in sync — a test enforces category
   completeness.
3. **Regenerate the 4c candidate** on the connected consolidated network with
   design-aware hierarchy (12/7/4 m widths, branch tree, clearance, buildable
   blocks). Re-run the same FAR / parking / 20 m / green / CAD checks; publish
   the new DXF and a before/after topology comparison.
4. Only then **expand from focus G-01 to all groups** and enforce 20 m
   north-south spacing site-wide (`FULL_SITE_NS_SPACING`).
5. Add design evaluation/search: intent preservation, completeness, internal
   consistency, verified constraint satisfaction, CAD editability; compare
   candidates instead of scoring one.
6. Replace the provisional 24×11 m staircase module with the designer’s
   unit-type library.

Acceptance for step 3: the noded graph is 1 component; FAR remains inside
1.55–1.60; parking ≥1/household; focus spacing ≥20 m; DXF remains editable
with audit 0/0 and full readback; all design objects stay `rule_derived`
`design_draft`.

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
- `contracts/design-synthesis-v0.1.yaml`.

CAD delivery:

- `src/dgcad_cad/ir.py`, `dxf.py`, `validator.py`.
- `contracts/cad-ir-v0.1.yaml`, `contracts/domain-contract-v0.1.yaml`.
- `contracts/sketch-domain-handoff-v0.2.yaml` (living), v0.1 superseded.

Experiments / evidence:

- `experiments/m4c0/common.py`, `exp_a_building.py`, `exp_b_roads.py`,
  `exp_c_collaborative.py`, `run_all.py`, `requirements-reuse.txt`.
- `docs/e2e/design-synthesis-001/` (28 files incl. `design-proposal.dxf`,
  `design-preview.png`, `design-summary.json`).
- `docs/e2e/open-source-reuse-001/` (matrix, README, exp-a/b/c artifacts).
- `docs/e2e/sketch-handoff-a/` (blocked pilot evidence).

Tests:

- `tests/test_design_synthesis.py` (8).
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

- **ezdxf output is not byte-reproducible**: `$TDUPDATE`, `$FINGERPRINTGUID`
  and `$VERSIONGUID` are random even with
  `write_fixed_meta_data_for_testing`. The committed hash matches the
  committed file, not a regenerated file. Compare content, not bytes.
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

- Merge PR #34 now, or continue on the branch until the road topology is fixed? 
  (Current recommendation: fix topology first, then merge.)
- The designer’s unit-type library is still missing; six source buildings have
  length-vs-area unit-count conflicts: `SK-BLD-0009`, `0010`, `0011`, `0013`,
  `0015`, `0018`. The kindergarten/facility classification is also unresolved.
- Full-site 20 m spacing is deferred; it may require dropping or reshaping more
  buildings than the focus block, and that policy has not been agreed.
- Real CAD host loop (LibreCAD/FreeCAD/AutoCAD) remains deferred; issue #6 open.
- `EP-R1-SKETCH-001` remains in progress; `R1-G07` partial;
  `EP-R1-DESIGN-001` in progress.
