# Roadmap

The roadmap is organized so that every milestone has an executable exit criterion. A milestone is not "done" because a demo looks plausible; it is done when the named tests or evidence packages pass within a declared scope.

## Milestone 0 — Formal workspace and CI (complete)

- [x] Consolidate Foundation, Runtime and Deployment into a single `src/` tree.
- [x] Preserve R0 v0.19 and R1 deployment-entry v0.2 under `research/archive/`.
- [x] Establish 65-test contract baseline.
- [x] Add CI matrix (Ubuntu/Windows, Python 3.11/3.13).
- [x] Publish public repository.
- [x] Enable branch protection and require the CI checks on `main`.
- [x] Promote living Canonical Site IR, evidence gates and the minimal domain contract.
- [x] Create `DEV-CAD-001..008` as tracked issues (implementation deferred to Milestone 3).

**Exit:** green CI on the default branch; repository structure documented; promotion map current.

## Milestone 1 — Domain slice entry (`NEXT-R1-MVP-001`) — complete for synthetic scope

Input: human-confirmed Trace/Intent fixture. Output: canonical Building/Road objects, proposal → preview → dependency → validator flow.

- [x] Define `dgcad_domain` package boundary and typed domain objects (Building, RoadCorridor).
- [x] Define a minimal confirmed Trace/Intent fixture and its authority rules (`fixtures/domain/domain-slice-001-r2.yaml`).
- [x] Implement Building adapter: trace footprint → professional candidate → canonical proposal.
- [x] Implement Road adapter: centerline + simple cross-section → canonical proposal.
- [x] Register derived artifacts and stale propagation for both domains.
- [x] Add a domain-level validator contract with structured issues.
- [x] Tests: 26 domain contract tests, including a StatefulRuntime integration test.

**Exit:** one confirmed synthetic site can produce canonical building and road objects through the runtime, with preview isolation and correct staleness. Real sketch input remains blocked by `EP-R1-SKETCH-001`; real road engineering remains blocked by `EP-R1-ROAD-001`.

## Milestone 2a — E2E-001 living pipeline (complete)

- [x] Build the pipeline only from living `src/` packages; archived R0 scripts are reference only.
- [x] Cover: DOMAIN-SLICE-001 → Runtime canonical → massing → shadow → CAD-IR → DXF → readback manifest.
- [x] Run the pipeline in CI on Ubuntu and Windows.
- [x] Freeze expected object IDs (11), entity count (15), audit result (0/0) and dependency fingerprints.
- [x] Add mutation tests for vertex mutation, unexpected layer and entity-type substitution.
- [x] Record bulge/constant-width gaps at E2E-001 time; resolved in Milestone 3a (issue #3 closed).

**Exit:** E2E-001 runs in CI with no external engine and no archive imports. Evidence: `docs/e2e/living-pipeline-001.md`.

## Milestone 2b — E2E-002 dependency and mutation (complete)

- [x] Change `B-001` height and prove massing goes stale while footprint-dependent artifacts stay current.
- [x] Move `RN-003` and prove node/edges/corridors + CAD-IR/DXF handling.
- [x] Change north bearing and prove shadow + dependent delivery artifacts stale.
- [x] Rebuild only affected artifacts; produce a new DXF and manifest.
- [x] Compare old/new manifests by object ID and revision, not just file hash.
- [x] Use the Runtime claim/complete path and a deterministic rebuild executor that recomputes, writes and validates.
- [x] Explicitly defer road surface geometry; do not claim `SURFACE-R-002` is generated.

**Exit:** mutation → scoped stale → rebuild → new delivery artifact is reproducible, with no global regeneration. Evidence: `docs/e2e/dependency-mutation-002.md`.

## Milestone 2c — E2E-003 adversarial delivery regression (complete)

- [x] Port non-zero Z, style override, unexpected layer, entity-type substitution and one layer linetype case into living CI. Full symbol-table equivalence remains Milestone 3.
- [x] Add MultiPolygon 2-part + 1-hole coverage (passes: 3 entities, audit 0/0).
- [x] Add bulge/constant-width/start-end-width/thickness/extrusion mutation cases.
- [x] Keep each known gap linked to a `DEV-CAD` issue (#3, #7, #17, #18).
- [x] Add `delivery-comparison.json` and issue categories.
- [x] Track CAD-IR fingerprint/dependency-key consistency as #16 / DEV-CAD-011.

**Exit (at E2E-003 close):** every adversarial delivery case was either detected or explicitly xfailed with an issue link. All xfails were converted to positive checks in Milestone 3a. Evidence: `docs/e2e/adversarial-delivery-003.md`.

## Milestone 3 — CAD validator hardening (3c partial; parallel evidence lane)

Milestones 3a and 3b are complete. 3c adds the third-party CAD round-trip matrix. Scope explicitly includes `DEV-CAD-001..011`; #2 is closed, #6 remains.

### 3a — Fix existing strict xfails

- [x] `DEV-CAD-003` / #3: LWPOLYLINE bulge, start/end width, constant width, thickness and extrusion.
- [x] `DEV-CAD-007` / #7: structured `validator_error`; validator-internal exceptions never become design failures or passes.
- [x] `DEV-CAD-009` / #17: entity-level color, linetype, lineweight, true color and transparency.
- [x] `DEV-CAD-010` / #18: CIRCLE center Z, TEXT insertion Z, rotation, width and alignment.

**3a exit:** 141/141 tests passing; no permanent xfails. Evidence: `docs/e2e/adversarial-delivery-003.md`.

### 3b — Semantic equivalence and dependency closure

- [x] `DEV-CAD-005` / #5: full symbol-table case semantics (layer, linetype, text style, block, dimstyle) with original spelling retained.
- [x] `DEV-CAD-011` / #16: align CAD-IR fingerprint inputs with registered dependency keys; add an unrelated-object negative test.
- [x] `DEV-CAD-001` / #1: MultiPolygon 2-part+hole contract; content-derived ring keys stable across sibling-part insertion.
- [x] `DEV-CAD-004` / #4: raw DXF semantics and canonical targets both in the readback manifest; tolerance 1e-9 (current entity set: LWPOLYLINE/CIRCLE/TEXT).
- [x] `DEV-CAD-008` / #8: serialization-difference vs profile-violation categories separated and tested.
- [x] Keep the `delivery-comparison.json` hash/file correspondence as a regression check.

**3b exit:** 152/152 tests passing; unrelated commits do not stale CAD-IR, relevant semantic changes do. Evidence: `docs/e2e/semantic-dependency-003b.md`.

### 3c — Third-party CAD evidence (partial)

- [x] AutoCAD 2024 Core Console open/save/readback: 15 entities/XDATA preserved; `semantic_pass_with_serialization_differences`; evidence in `docs/e2e/third-party-003c/`.
- [ ] LibreCAD open/save/readback.
- [ ] FreeCAD Draft open/save/readback.
- [ ] AutoCAD GUI visual/print QA.
- [ ] Real design-office profile (separate evidence package).

**3c status:** partial; `DEV-CAD-006` / #6 remains open. A host without a third-party CAD app must record `blocked`, never a pass.

**Exit:** every strict xfail either becomes a positive test or is explicitly re-scoped with evidence; validator errors are structured and categorised; the third-party matrix covers at least AutoCAD, LibreCAD and FreeCAD with semantic diff evidence; CI remains green.

After Milestone 3, prioritize the real sketch/trace and road evidence packages before broadening to IFC and independent environment engines.

## Milestone 4 — Evidence packages (in progress)

| Package | Capability unlocked |
|---|---|
| `EP-R1-SKETCH-001` | **in progress**: real sketch → trace reliability |
| `EP-R1-ROAD-001` | **in progress**: unified-mask topology; junction review and width/profile/alignment pending |
| `EP-R1-IFC-001` | IFC identity round-trip |
| `EP-R1-ENV-001` | independent shadow engine |
| `EP-R1-PROFILE-001` | real project/design-office profile |
| `CASE-SKETCH-001-HANDOFF-A` | **gate implemented; pilot blocked**: selected real subset passes source/topology checks, then requires an object-level human geometry review. Downstream Canonical → CAD-IR → DXF is proven with a test double only. |
| `EP-R1-DESIGN-001` | **in progress**: autonomous schematic design draft, focus block + full-site metrics; human confirmation not required to generate |

Each package has its own decision question, raw evidence, metrics, failure policy and scope-leakage prohibition. No package is a checklist for production release.

### EP-R1-SKETCH-001 — in progress (0.13.0)

- [x] Intake a designer sketch with a private site reference; publish the sketch and image-space geometry only.
- [x] Record designer-confirmed semantics: metre, red buildings, magenta garage entrances, brown main roads, blue branch/access roads, green cluster spaces, existing buildings removed, top crop road-only.
- [x] Produce an image-space proposed trace (55 buildings after five designer-confirmed merges; 63 original components preserved; 3 garage entrances, 12 green spaces, 9 road areas, 1 boundary) with explicit ambiguities.
- [x] Apply designer building merges: M-001 (0046+0047+0060 plus connectors 0062+0063), M-002 (0030 with 2 units + 0053 with 1 unit), M-003 (0001+0037 kindergarten), M-004 (0019+0058), M-005 (0027+0059). Record 11 floors as `proposed_initial`.
- [x] Infer 1/2/3-unit counts from sketch dimensions: 16 one-unit, 21 two-unit, 17 three-unit, plus one facility; 52 inferred, 2 confirmed.
- [x] Produce rough road centerlines (312 candidates; main road 1 component, blue network 8 components) as `proposed_rough`.
- [ ] Apply the unit-type library and replace sketch-era building footprints.
- [ ] Human-confirmed trace and fidelity metrics (Hausdorff/IoU/topology).
- [ ] Review the six length-vs-area unit-count conflicts (`0009`, `0010`, `0011`, `0013`, `0015`, `0018`) and the kindergarten facility classification.
- [ ] 支路 vs 入户路 separation.
- [x] Handoff gate on a selected real subset (`CASE-SKETCH-001-HANDOFF-A`): source integrity, road topology, authorization-vs-review semantics, review packet and blocked evidence.
- [ ] Object-level human geometry/coordinate review of the selected subset.
- [ ] Full-case Canonical Building/Road handoff; the pilot subset is not the full sketch.

**Exit (not met):** a designer-confirmed semantic trace, a human-confirmed **full-case** geometry reference, fidelity metrics within a declared scope, and a **full-case** canonical handoff. The selected pilot subset is currently blocked at the object-level review gate; R1-G07 remains partial.

### EP-R1-ROAD-001 — in progress (0.11.0)

- [x] Extract rough centerlines; the separate-colour skeleton produced 306 nodes, 312 edges and 9 components — **wrong process**, superseded.
- [x] Union brown+blue into one road mask; 5 px closing (4 px leaves 5 components) -> 1 connected component.
- [x] Unified network: 309 nodes, 333 edges, 111 endpoints, 121 junction candidates, 25 cycles; 65 main and 268 branch/access edges.
- [ ] Review the 121 junction candidates and the 5 px closing kernel.
- [ ] Road width, cross-section, profile and alignment.
- [ ] Separate 支路 from 入户路.
- [ ] Canonical road graph handoff.

**Exit (not met):** a reviewed unified-mask road graph with accepted junctions, explicit width/profile/alignment inputs where required, and a canonical handoff. Until then road topology remains `proposed_unified_mask`.

### Milestone 4b — CASE-SKETCH-001-HANDOFF-A (pilot executed; review claim superseded)

- [x] Add `contracts/sketch-domain-handoff-v0.1.yaml` and `src/dgcad_domain/sketch_handoff.py` (superseded by v0.2 in 4b.1).
- [x] Select a representative real subset: site boundary, one ordinary building, one merged building, one green, two main-road edges, one branch edge, one T-junction.
- [x] Record a designer authorization for a pilot subset; the Agent cannot confirm the handoff.
- [x] Map image-space evidence to a declared local metric frame (2.438 px/m; no project coordinates).
- [x] Run `ConfirmedTraceScene → build_initial_scene → runtime proposal/approval/commit → Canonical → CAD-IR → DXF → readback` with the then-current review record.
- [x] Preserve unknown height/base elevation, unknown road hierarchy/cross-section, no massing and no width.
- [x] Prove provenance from source ID to trace ID to canonical ID to CAD-IR/readback.
- [x] Add fail-closed tests for proposed geometry, missing/agent review, project-coordinate claims, broken provenance, unknown height and unknown road class.

**4b result:** the 0.12.0 executed artifacts are preserved under `docs/e2e/sketch-handoff-a/history-0.12.0/`. Its review record treated a designer authorization as object-level geometry confirmation; that claim is withdrawn.

### Milestone 4b.1 — Scope-Aware Handoff Integrity (code/evidence complete; real review still required)

Task A — boundary and confirmation scope:

- [x] Add `contracts/sketch-domain-handoff-v0.2.yaml`; mark v0.1 superseded.
- [x] Carry `confirmation_scope`, `geometry_quality` and `review_kind` through trace, canonical, CAD-IR provenance, DXF XDATA and the readback manifest.
- [x] A `full_case` review rejects `confirmed_for_pilot`; a pilot review requires it.
- [x] A published sketch boundary maps to `SITE-SKETCH-001` with candidate authority; it cannot become `SITE-001` or claim canonical site identity.
- [x] Keep sketch evidence immutable and separate from professional candidates.

Task B — real review evidence chain:

- [x] Generate `review-packet.html` / `.json` with every selected object on the sketch and in local metric space.
- [x] Generate `review-request.yaml` and an unsigned `review-confirmation-template.yaml`.
- [x] Record semantic, geometry and coordinate decisions separately per object.
- [x] Distinguish `human_object_review`, `designer_authorized_pilot` and `test_double`; the Agent cannot sign.
- [x] Reclassify the 0.12.0 record as `designer_authorized_pilot`; the pipeline blocks with `HUMAN_OBJECT_REVIEW_REQUIRED`.
- [ ] The designer completes the object-level review and signs the record.

Task C — coordinate and source integrity:

- [x] Declare `uniform_scale_translation_yflip`, `homography_applied: false`, `shape_correction: none`, `LOCAL-XY-ZUP`, `axis_orientation: unknown`, scale/origin sources and per-object sensitivity.
- [x] Verify source file SHA-256, source object ID and source geometry hash; a stale hash or changed geometry fails closed.
- [x] Verify road nodes, edge endpoints, corridor coverage, one component and the T-junction degree; record the 3.606 px max offset against the 4.0 px tolerance.
- [x] Add a structured DXF privacy scan over TEXT/MTEXT, layer/linetype/style/block names, XDATA and raw bytes.
- [x] Regenerate the pilot evidence to match the new contract (blocked state + review packet + superseded history).

**4b.1 exit (met for code/evidence):** scope cannot silently become global confirmation; a sketch boundary cannot become `SITE-001`; a source-geometry mutation with a stale hash fails; a road-topology mismatch fails closed; the synthetic E2E and CAD delivery remain green; 206 tests pass (count true at the 4b.1 exit; the suite is 259 after 4c-1a). The real pilot remains blocked until the designer signs the object-level review.

### Milestone 4c — Autonomous Site Design Synthesis (first round partial; M4c-0 complete)

Goal: the Agent converts the sketch's spatial intent into a self-consistent,
standardized schematic design without asking the designer to review sketch
geometry. The designer reviews the product.

First round (`docs/e2e/design-synthesis-001/`):

- [x] Design basis with the required FAR 1.55–1.60, ≥1 parking space/household and ≥20 m north-south spacing, plus explicit assumptions for the unit module, floors, roads, setbacks, green and drawing standard.
- [x] Full-site context: 55 buildings, 109 staircases, 2,398 households, 319,536 m² GFA, FAR 1.565, 2,398 parking spaces and 5 entrances.
- [x] Focus block G-01: 7 standardized buildings / 16 units in rows with 20.0 m north-south spacing, unit division lines, green strips and an access loop.
- [x] Replace the 333-edge skeleton mesh with a design road hierarchy: merged main roads, one branch per group, one focus access loop; widths 12/7/4 m; record the source mesh as evidence.
  (M4c-1b/1e annotation: the current 44-road network serves all 17 groups
  through **declared** `serves_group_ids` relations — 17 group-access roads
  (16 branch + ACC-G-12), each group served by its own road; `BR-FOCUS` and the
  focus loop are network connectors, so 19 connector roads exist in total.)
- [x] Allocate cluster/ strip/ supplementary green; site green ratio 63.0%.
  (M4c-1c/1d annotation: 63.0% is the candidate open-space ratio, not the
  designed-green ratio — designed green is 6.54% in 0.20.0/0.21.0 (6.59% when this
  annotation was written) and deferred; this checklist is a historical statement
  from before M4c-1c.)
- [x] Check FAR, parking, entrances, unit count, spacing, setback, overlap, road clearance, noded connectivity (1 component after 4c-1a; `ROAD_CORRIDOR_COVERAGE` recorded as informational), road widths and green ratio; record full-site north-south spacing as deferred.
  (M4c-1c/1d annotation: same historical caveat — "green ratio" here meant the
  candidate open-space measure; FAR/parking/unit-count are basis arithmetic or
  info checks. The current taxonomy is **26 = 8 pass + 11 info + 7 deferred**,
  M4c-1e.)
- [x] Produce an editable 208-entity DXF with layers, building/road labels, dimensions, key plan, title block, legend, north arrow and scale bar; audit 0/0; readback 208/208.
  (M4c-1b annotation: the DXF is now 206 entities after the road-service geometry change — this line records the pre-4c-1b state.)
- [x] Mark all design objects `rule_derived` in `proposal_preview`; no `human_confirmed`; title block says Agent-generated and not code-compliant.
- [x] Record the design diff, dropped buildings and the persistent draft manifest.

Next in 4c (4c-1a/1c/1d/1b/1e/2/3/3a complete; sequence: M4d full-site expansion + real CAD host/R1 in parallel):

- **First fix the road topology** — **done in 4c-1a** without OSMnx: explicit shared-coordinate junctions + dependency-free noded check + evidence regeneration (the OSMnx base was rejected as a tolerance-created connectivity proof; OSMnx remains an optional preprocessor, see 4c-1a below).
- Expand the standardized layout from the focus block to all groups; enforce 20 m north-south spacing site-wide.
- Improve the design-intent model: group boundaries, road hierarchy, access logic and green relationships.
- Add design evaluation/search: compare candidate layouts against intent preservation, completeness, consistency, constraint satisfaction and CAD editability.
- Replace the provisional unit module with the designer's unit-type library.
- Move to a real CAD host loop after the draft is stable.

### Milestone 4c-1a — Road-Topology Truth Fix (complete, 0.16.0)

- [x] Diagnose the M4c-0 finding: the 5-component noded reading was a sub-ULP floating-point noding artefact (connector endpoints 1.5e-15–2.1e-14 m off the main lines; GEOS exact predicates create no node; all 25 main roads were always in one exact component).
- [x] Add explicit shared-coordinate junctions (no snap, no rounding, no tolerance): noded centerline graph 1 component — 51 nodes / 55 segments, cyclomatic 5, dead ends 21, junctions 27 (16 explicit shared-vertex), closed rings 3, `max_endpoint_gap_m` 0.0.
- [x] Replace the corridor-only `ROAD_CONNECTIVITY` with the noded check: noded connectivity fails closed within a 1e-9 m endpoint tolerance; sub-1e-9 endpoint misalignment surfaces first as component count >1. `ROAD_CORRIDOR_COVERAGE` (corridor union, 1 piece) is published as informational, non-gating.
- [x] Publish `design-roads.geojson` (41 centerlines + 16 explicit junction records) so the topology is checkable from committed evidence.
- [x] Regenerate the evidence in one run: 208-entity DXF, audit 0/0, readback 208/208, 23 declared design layers, all prior metrics unchanged; contract bumped to `design-synthesis-v0.2.yaml` (v0.1 superseded).
- [x] Control plane unchanged: foundation/runtime/deployment/CAD/domain untouched; XDATA arity 11; `ISSUE_CATEGORIES` unchanged.
- [x] Correct the defect narrative across docs (this roadmap, status §16–18, design/reuse READMEs, research-to-product-map); full-site spacing remains deferred at this M4c-1b time point (historical; M4d later checks full-site N-S spacing, min 19.999999999999943 m).

### Milestone 4c-1c — Honest Evidence Semantics (complete, 0.17.0)

- [x] Split check statuses into pass / info / deferred — 16 declared checks: **9 pass**, 3 info (PARKING_REQUIREMENT_ARITHMETIC, ROAD_CORRIDOR_COVERAGE, OPEN_SPACE_RATIO), 4 deferred (PARKING_CAPACITY, PARKING_LAYOUT, DESIGNED_GREEN_RATIO, FULL_SITE_NS_SPACING) at the 0.17.0 time point (historical; superseded by the M4d 29-check taxonomy). `info` is not `pass`; `deferred` is not `pass`.
- [x] Split the green claim: `open_space_ratio` **63.0%** (128,676 m²) is open space, not designed green; `designed_green_ratio` **6.6%** (13,446 m²; supplementary covers 89.6% of open space) — the ≥30% designed-green target is deferred, not achieved. (0.17.0 values; in 0.20.0 they are candidate 63.02% / 128,645.31 m², unbuilt 65.35% / 133,384.46 m², designed green 6.54% / 13,346.69 m².)
- [x] Split the parking claim: entrance count 5 **pass**; recorded capacity **1,000 vs 2,398 required** (PARKING_CAPACITY deferred); parking layout deferred; entrances carry capacities (3 existing × 0, 2 proposed × 500); garage layout `not_designed`.
- [x] Label derived checks: FAR_RANGE / UNIT_COUNT_PRESERVED = `design_basis_arithmetic`; ROAD_WIDTHS = `design_basis_assignment`.
- [x] Publish design-basis provenance: 21 parameters with authority states (5 `declared_requirement`, 2 `designer_stated`, 3 `inferred_from_sketch`, 11 `agent_assumption`), **all `confirmed: false`**; the Agent cannot self-confirm them (`design-assumption-v0.2`).
- [x] Contract `design-synthesis-v0.3.yaml` (v0.2/v0.1 superseded); the gate register's `EP-R1-DESIGN-001` pointer updated to v0.3; tests: `test_design_basis` (14), `test_green_parking_semantics` (7), `test_design_contract` 7→10; suite **283 passed**.
- [x] Merged to `main` as **PR #34** (merge commit `e40f468`, main CI 4/4 green). The merged result remains a research prototype with the non-claims above.

### Milestone 4c-1d — Semantic Residuals (complete, 0.18.0; branch `fix/m4c-1d-semantic-residuals`)

- [x] Narrow `pass` to the 5 independently geometry-verified checks (FOCUS_NS_SPACING, FOCUS_BOUNDARY_SETBACK, FOCUS_BUILDING_OVERLAP, FOCUS_ROAD_CLEARANCE, ROAD_CONNECTIVITY); everything else is info or deferred.
- [x] Split FAR: `FAR_ARITHMETIC_SCENARIO` info (1.5654 under current assumptions) + `FAR_FINAL_VERIFICATION` deferred (value None; needs a confirmed basis and a full-site design).
- [x] Rename/check semantics: `UNIT_COUNT_PRESERVED` → `UNIT_COUNT_BASIS_INVARIANT` (info), `ROAD_WIDTHS` → `ROAD_WIDTH_ASSIGNMENT` (info), `OPEN_SPACE_RATIO` → `CANDIDATE_OPEN_SPACE_RATIO` (info; filters 5.0 m setback / 0.5 m obstacle buffer / 100 m² min polygon, classified-area sum); new `UNBUILT_RATIO` info (65.3%, geometric union). Both open-space ratios use the full published site area as denominator; the filtered/unbuilt areas are measured inside the 5 m setback boundary.
- [x] Parking capacity named `assumed_nominal_capacity_spaces` (1,000 vs 2,398 required, deferred); entrance count is info (per-entrance 500-space assumption, not a capacity result).
- [x] Provenance authentication `declarative` (declared, not certified); `confirmed: true` requires an `approval_ref`.
- [x] Contract `design-synthesis-v0.4.yaml` (v0.3/v0.2/v0.1 superseded); the gate register's `EP-R1-DESIGN-001` pointer updated to v0.4; evidence regenerated with geometry/topology/DXF content unchanged (208 entities, audit 0/0, readback 208/208, design-roads geojson unchanged); tests: `test_design_basis` 14→20, `test_green_parking_semantics` 7→9, `test_design_contract` →11; suite **292 passed**.
- [x] Merged to `main` as **PR #36** (merge commit `0546649`, main CI 4/4 green). The merged result remains a research prototype with the non-claims above.

### Milestone 4c-1b — Road Service Coverage (complete, 0.19.0; branch `feat/m4c-1b-road-access`; first design-geometry change)

- [x] Grow the design network to 44 roads (25 main × 12 m + 17 branch × 7 m + 2 access × 4 m); close the G-05/G-12 access gaps (G-05 via branch BR-G-05; G-12 via access road ACC-G-12 — a 7 m branch cannot satisfy the 3 m focus-building clearance).
- [x] Road access coverage 1.0 — all 17 groups served (`ROAD_ACCESS_COVERAGE` **pass**); connection terminals stop 3.5 m from building footprints (measured 3.499999 m); no route crosses a building; new-access/building overlap 1.34 m² total; the ≤1.0 m² budget applies only to new group-access roads (largest per-building overlap 0.9228 m²).
- [x] Classify every dead end: 24 = 17 justified + 5 unfinished + 2 unclassified (`DEAD_END_JUSTIFICATION` info) — classified, **not all justified**; M4c-1e adds `DEAD_END_RESOLUTION` (deferred, 7 unresolved).
- [x] Entrance proximity honesty (`PARKING_ENTRANCE_CONNECTION` info at the time): 2 of 5 garage entrances near a design road; the 3 existing garage positions are area markers **18.83–25.71 m** from the carriageway; no driveway designed (M4c-1e renames this `PARKING_ENTRANCE_PROXIMITY` info and adds `PARKING_DRIVEWAY_CONNECTION` deferred).
- [x] Record the pre-existing main-road/building overlap (38.19 m² = MAIN-19 34.42 + MAIN-08 3.77, source alignment vs rough background) as a known unresolved conflict deferred to M4c-2; loop∩building = 0; M4c-1e turns it into a deferred machine check (`MAIN_ROAD_BUILDING_OVERLAP`, `known_unresolved`).
- [x] Regenerate evidence: DXF now **206 entities** (was 208), audit 0/0, readback 206/206, XDATA 11, privacy pass; `design-roads.geojson` 44 centerlines + 21 junction records (new sha 59df13d8…); topology rebaselined to 59 nodes / 65 segments, cyclomatic 7, dead ends 24, junctions 32, `max_endpoint_gap_m` 0.0, 1 component; contract `design-synthesis-v0.5.yaml` (v0.4 superseded).
- [x] Tests: `test_road_access` (16), `test_road_access_generation` (10), `test_parking_geometry` (6); `test_design_topology` rebaselined to the new network; suite **324 passed**.
- [x] Merged to `main` as **PR #38** (merge commit `7a3e70a`, main CI 4/4 green). The merged result remains a research prototype with the non-claims above; the MAIN-19/08 overlap and the 5 unfinished / 2 unclassified dead ends stay open for M4c-2. (M4c-2 later resolved all of these.)

### Milestone 4c-1e — Evidence Binding (complete, 0.20.0; branch `fix/m4c-1e-evidence-binding`; no design-geometry change)

- [x] Bind group access to **declared** service relations: `RoadDesign.serves_group_ids` + `access_terminal_xy`; 17 groups / 17 group-access roads (16 branch + ACC-G-12; G-08 → BR-G-08, G-13 → BR-G-13); `BR-FOCUS` and the focus loop are connectors (19 connector roads total). The previous nearest-endpoint attribution (G-08 to BR-G-09 2.895 m, G-13 to BR-G-07 3.188 m) is removed.
- [x] Validate the declared terminal: centreline distance in [3.4, 3.5] m (min 3.497987 m), outside every footprint, route crossing 0.0 m, terminal on the serving road's centreline within 1e-6 m; orphan declarations reported as relation errors (`relation_error_count` 0). `terminal_corridor_edge_clearance_m` is published separately (0.0 m for a 7 m branch end-cap, ~1.5 m for ACC-G-12) — not the 3.0 m corridor setback.
- [x] Checks 21 → **25 = 6 pass + 10 info + 9 deferred**: new `MAIN_ROAD_BUILDING_OVERLAP` (deferred; 38.19068149970834 m², rows MAIN-19/SK-BLD-0006 34.42 + MAIN-08/SK-BLD-0038 3.68 + MAIN-08/SK-BLD-0061 0.09; `known_unresolved`), `FULL_SITE_ROAD_CLEARANCE` (deferred), `DEAD_END_RESOLUTION` (deferred, 7 unresolved), `PARKING_DRIVEWAY_CONNECTION` (deferred); `PARKING_ENTRANCE_CONNECTION` renamed `PARKING_ENTRANCE_PROXIMITY` (info).
- [x] No design geometry changed: 44 roads (25/17/2), endpoints, widths, topology (1 component, 59 nodes / 65 segments, cyclomatic 7, 24 dead ends, 32 junctions / 21 explicit, 3 rings, gap 0.0), overlap values (new 1.3365 / main 38.1907 / total 38.7392) and DXF **content** (206 entities, audit 0/0, readback 206/206, XDATA 11, privacy pass) are identical to 0.19.0. DXF byte SHA changes per save (0.19.0 `34a65926…` → 0.20.0 `fcc42d32…`) — compare content, not bytes; `design-roads.geojson` SHA changes to `d77ce7a8…` because new fields are published (expected).
- [x] Contract `design-synthesis-v0.6.yaml` (v0.5 superseded; gate-register pointer re-pointed); tests 324 → **334** (road access 23, road access generation 13; no test removed).
- [x] PR #40 merged to `main` (merge commit `7f81f0e`, main CI 4/4 green); tests **334 passed**. The merged result keeps the M4c-2 main-road alignment and the 7 unresolved dead ends as open work. (M4c-2 later resolved both.)

### Milestone 4c-2 — Main-Road Alignment and Dead-End Resolution (complete, 0.21.0; Phase-0 corrected in 0.22.0; branch `feat/m4c-2-main-alignment`; real design-geometry change)

- [x] Resolve MAIN-19/SK-BLD-0006 (34.421783197612406 m²) by **diversion**: overlap → 0 m²; max displacement 66.23545861756293 m; +29 vertices; `local_search_exhausted` (Phase-0 wording — the 11.565220076201857 m gap only proves the between-buildings passage infeasible; the 66.235 m diversion is a candidate baseline, not a proof of optimality).
- [x] Resolve MAIN-08/SK-BLD-0038+0061 (3.768898302095937 m²) by **local detour**: overlap → 0 m²; max displacement 4.90654356307025 m; +16 vertices; conflicting gap 4.482068672289278 m.
- [x] Total main-road/building overlap 38.19068149970834 → **0.0 m²**; `MAIN_ROAD_BUILDING_OVERLAP` is now **pass** (remaining ≤ 0.01 m², `resolved`); new `ROAD_ALIGNMENT_EVIDENCE` (info) publishes each adjusted road's source edges, original/adjusted centreline, strategy, displacement, vertex budget and overlap before/after; +45 / −0 vertices; road ids preserved. The claim is **zero remaining overlap for the known conflicts**, not that all 25 main roads meet the 3.0 m corridor clearance — the unadjusted main roads' minimum corridor clearance is about **1.229 m**. Full-site road clearance stays `deferred` (`FULL_SITE_ROAD_CLEARANCE`).
- [x] Resolve the 7 previously unresolved dead ends: MAIN-03 trimmed 9.727353166421203 m; MAIN-05 trimmed 0.24620779365789502 m; MAIN-09 bridged to MAIN-08 13.677655946265997 m; MAIN-20 bridged to MAIN-19 5.233264199174163 m; MAIN-22 bridged to MAIN-08 9.642090864979577 m; MAIN-18 site-edge terminus 4.047925766932525 m from the boundary **within the ≤5 m site-edge band** (the source network is clipped at the published boundary; the endpoint is within the band and no source vertex lies outside it); MAIN-25 extended 5.643487350037444 m **along the shortest direction to the published boundary (not collinear with the terminal segment)**; all `criterion_met`; `DEAD_END_RESOLUTION` is now **pass** (0 unresolved). The 19 remaining dead ends are 17 planned group-access terminals + 2 site-edge termini.
- [x] Geometry/evidence: 44 roads (25/17/2, ids/widths unchanged), topology 1 component / 57 nodes / 66 edges / cyclomatic 10 / 19 dead ends / 35 junctions (24 explicit) / 3 rings / gap 0.0; main length 2,126.392617984018 m; road area 27,369.822509945796 m²; sidewalk 9,889.900380276495 m²; DXF content **211 entities** (was 206; audit 0/0, readback 211/211, XDATA 11, privacy pass); pre-Phase-0 new-access/main/total overlap values are superseded by the Phase-0 correction below; access 17/17 declared unchanged; green candidate 62.07% / unbuilt 64.45% / designed 6.54%; `design-roads.geojson` SHA-256 `a55ebb58…`. (Pre-Phase-0 0.21.0 record; Phase-0 correction below supersedes these values.)
- [x] Checks **26 = 8 pass + 11 info + 7 deferred**; contract `design-synthesis-v0.7.yaml` (v0.6 superseded; gate-register pointer re-pointed); tests 334 → **347** (`test_main_alignment` 9; no test removed). Merged to `main` as **PR #42** (merge commit `bb23377`, main CI 4/4 green).
- [x] Phase-0 correction (0.22.0): the old "infeasible local detour" wording is replaced by `local_search_exhausted`; site-boundary containment hard pass (`ROAD_BOUNDARY_CONTAINMENT`, margin 0.6735131264650868; MAIN-08/16/18 repairs — MAIN-08 341.6908310814502 → 0 m², margin 2.446306837399009; MAIN-16 2.417804558565924 → 0; MAIN-18 8.290901115044374 → 0); overlap fields split (`main_before` 38.19068149970835, `main_after` 0.0, `new_access` 0.9943558185246757, `total_after` 0.9943558185246756); base geometry 58 nodes / 68 edges / cyclomatic 11 / 36 junctions (24 explicit); main length 2,107.733378663747 m; road area 26,882.20505326313 m²; sidewalk 9,764.76834535878 m²; DXF 211 entities with content changed; `design-roads.geojson` SHA-256 `a8c1baf5…`; green candidate 61.64% / unbuilt 64.07% / designed 6.54%; checks **27 = 9 pass + 11 info + 7 deferred** (+3 DXF = 30); contract `design-synthesis-v0.8.yaml`; tests **396**. The pre-Phase-0 numbers above are retained as the 0.21.0 record.

### Milestone 4c-3 — Phase 0 + First Multi-Candidate Experiment (complete, 0.22.0; branch `feat/m4c-3-multi-candidate`; evidence correction + decision experiment)

- [x] Phase 0 (evidence corrections): `local_search_exhausted` alignment semantics; boundary containment hard check and repairs; split overlap fields; `source_segment_map` (25 roads); `design-diff.json` `road_alignment`/`dead_end_resolutions` and changed/why; dead-end `resolved` bound to `criterion_met` plus a geometry re-check (negative tests for forged/unmet records); `main_boundary_repairs` (3); regenerated `design-preview.svg`/`.png` and `design-overlay.svg`.
- [x] Base design after Phase 0: 44 roads (25/17/2), 1 component, **58 nodes / 68 edges / cyclomatic 11 / 19 dead ends / 36 junctions (24 explicit) / 3 rings / gap 0.0**; main length 2,107.733378663747 m; road area 26,882.20505326313 m²; sidewalk 9,764.76834535878 m²; DXF content **211 entities** (audit 0/0, readback 211/211, XDATA 11, privacy pass); new-access overlap 0.9943558185246757 m², main 0.0, total 0.9943558185246756; access 17/17 declared; green candidate 61.64% / unbuilt 64.07% / designed 6.54% (deferred); `design-roads.geojson` SHA-256 `c5fc7262…`.
- [x] First multi-candidate experiment (`docs/e2e/design-candidates-001/`): four deterministic candidates for the MAIN-19/SK-BLD-0006/SK-BLD-0029 conflict, evaluated against the **boundary-safe, dead-end-resolved reference** (source alignment `alignment_mode='none'`; boundary repair and dead-end resolution still apply; main-length baseline 1,984.2812597774587 m; reference total overlap 36.20414480381279 m²). **All four hard-pass**: A road priority (total overlap 0.8595377847886573 m²; building shift 3.1720857962227718 m; road max 2.825827798091072 m; main length 1,981.9609886916392 m); B1 building priority/M4c-2 diversion (overlap 0.9943558185246756 m²; road max 66.23545861756291 m; main 2,107.733378663747 m); B2 alternate fold (overlap 0.9943558185246756 m²; road max 71.7722361902286 m; main 2,115.0219491017956 m); C coordinated (overlap 0.8595377847886573 m²; building 1.5 m + road max 76.69965271965492 m; main 1,995.4961054524852 m). Default preference recommends **B1**, road-first recommends **A**; Pareto [B1,B2,C,A]; every candidate gets a reason and no single black-box score is produced. B1 is only the M4c-2 diversion candidate baseline — not the selected or professional design.
- [x] Contracts: `design-synthesis-v0.8.yaml` (v0.7 superseded) and new `design-candidates-v0.1.yaml` (superseded by v0.2 in 4c-3a); gate-register pointer re-pointed. Tests 347 → **396** (`test_candidates` 11, `test_evaluation` 18, `test_visuals` 10, re-baselined design/topology/access tests). Merged to `main` as **PR #45** (merge commit `569944f`, main CI 4/4 green).

### Milestone 4c-3a — Multi-Candidate Evaluation Integrity (complete, 0.23.0; branch `feat/m4c-3a-evaluation-completeness`; no base-design change)

- [x] Contract `design-candidates-v0.2.yaml` (v0.1 superseded); `design-synthesis-v0.8` unchanged. Every candidate requires `parent_basis_id = design-assumption-v0.2` and canonical `basis_fingerprint = 2a2d7807…`; missing/mismatch fails `basis_ok`. Evidence schema v0.2: `candidates.json` with basis + `geometry_change` (`class_max_deviation_m`, per-road records, `group_terminal_changes`); `evaluation.json` with 11 objectives, auxiliary `not_in_pareto`, and two decisions.
- [x] All-44-road geometry evidence by class and group terminal: **A** main 2.320271085819647 m / branch 2.825827798091072 m (BR-G-08) / access 0; G-08 terminal 2.826209246611442 m; building 3.1720857962227718 m. **B1** main 66.23545861756291 m / branch 7.352131796880056 m (BR-G-09 follows) / access 0; terminal 0. **B2** main 71.7722361902286 m / branch 13.645240022712755 m / access 0; terminal 0. **C** main 11.99363782892846 m / branch 76.69965271965492 m (BR-G-08) / access 0; G-08 terminal 75.3147044566895 m — **C is not a small local change**.
- [x] `HISTORICAL_BOUNDARY_ARCHIVE`: MAIN-19 66.23545861756293 m (M4c-2 diversion, `resolved_by_main_alignment`) and MAIN-08/16/18 source-corridor repairs 341.6908310814502 / 2.417804558565924 / 8.290901115044374 m², kept separate from current candidate verdicts. The current B1 is boundary-repaired and hard-passes (margin 0.6735131264650868); its pre-repair form is archival, never a pass.
- [x] Comparison uses 11 single-unit objectives (building_count_change, building_displaced_count, building_displacement_max_m, main_length_delta_abs_m, main_route_deviation_max_m, branch_access_route_deviation_max_m, access_terminal_max_delta_m, source_preservation_coverage/distance_m/heading_deg, green_designed_ratio_delta); auxiliary metrics never enter Pareto/preference; no composite score. Default recommends **B1**, road-first recommends **A**, Pareto [B1,B2,C,A]; reasons in `evaluation.json`/README.
- [x] Tests 396 → **414** (new candidate geometry-change, evaluation v0.2, basis/negative tests; no deletion). Merged to `main` as **PR #47** (merge commit `29c93bd`, main CI 4/4 green).

### Milestone 4d-1a — Full-Site Delivery Semantics (research draft, 0.24.1; branch `feat/m4d-1a-delivery-semantics`; contract `design-synthesis-v0.9` unchanged)

- [x] Full-site layout: all **55 buildings / 109 units / 2,398 households** in **18 rows / 8 superblocks (36 row records)** against the frozen 44-road network; focus G-01 **7 buildings / 16 units** preserved. Completeness requires the exact expected **55 ids** (no missing/extra/duplicate); otherwise the four `FULL_SITE_*` checks stay deferred. Source→design displacement sum **2,328.95 m**, max **147.25 m**, mean **42.34 m**.
- [x] Full-site checks (`design-synthesis-v0.9`, 29 design + 3 DXF = 32 items): **11 pass + 11 info + 5 deferred + 2 fail**. Pass: `FULL_SITE_BOUNDARY_SETBACK`, `FULL_SITE_BUILDING_OVERLAP`, `FULL_SITE_NS_SPACING` (min **19.999999999999943 m**; the 20 m rule is the **candidate row-rhythm + design-basis assumption**, not a regulatory/universal constraint; over-spacing counts as a rhythm violation), `FULL_SITE_ROAD_CLEARANCE` (min **3.0163622902759215 m**). **`DESIGNED_GREEN_RATIO` deferred** (designed green **15.93%** <30%; the 61.06% account is `POTENTIAL OPEN SPACE ... NOT LANDSCAPE DESIGN` on `L-OPEN-SPACE`, classification `potential_open_space`, auxiliary only). Fail: **`ROAD_ACCESS_COVERAGE` 0.0 (17 relation errors)** and **`DEAD_END_RESOLUTION` 17 unresolved**.
- [x] Focus evidence regenerated under v0.9: **29 checks = 9 pass + 11 info + 9 deferred**, `DESIGNED_GREEN_RATIO` **deferred** (designed green 6.54%; 61.46% account is potential open space, auxiliary only), four `FULL_SITE_*` checks deferred; focus DXF 211/readback 211, topology 58/68/cyc11/19 dead, access 17/17 unchanged, road SHA `c5fc7262…`.
- [x] Full-site DXF **553 entities**, audit 0/0, readback **553/553**, XDATA 11, privacy pass; title `DESIGNED GREEN 15.93% - INCOMPLETE` + `INCOMPLETE: ROAD ACCESS 0/17 - DEAD ENDS 17 UNRESOLVED - DESIGNED GREEN < 30%`; `full-site-preview.svg/png`.
- [x] Feasibility conclusion: under the fixed network / uniform row grid / current search family, caps 25–130 m found no complete layout; an unbounded search produced the **147.25 m candidate**, not a proven global minimum. Regenerating roads makes clearance fail (min 0 m, **17 buildings below 3 m**). The full-site sheet is a **research draft**; the focus sheet remains canonical. 3.016362 m / 19.999999999999943 m are model-coordinate internal consistency under approximate sketch registration, not survey-grade engineering clearances.
- [x] Tests 467 → **472** (full-site layout 16, constraints 29, evidence 13; no deletion). PR/merge pending; next is **M4d-2 access/road co-design** plus real CAD host/R1 in parallel.

### M4c-0 — Open-Source Design Capability Reuse Sprint (complete; partial answer)

Goal: test whether existing open-source geometry, road, morphology and
CAD-agent projects can perform the professional design work we have been
rebuilding, using the same CASE-SKETCH-001 focus block.

- [x] Read the R0 project matrix and capability allocation; audit the current
  core dependencies (PyYAML, Shapely/GEOS, ezdxf only).
- [x] Experiment A: Building Regulariser 0.2.5 on 9 focus footprints. 63→61
  vertices, area −2.0%, mean Hausdorff 1.07 m, ERI 0.972→0.984. Limited gain;
  it is a footprint-cleanup adapter, not a unit/typology generator.
- [x] Experiment B: OSMnx 2.1.1 simplify/consolidate, PyGeoOps 0.6.0
  centerlines, PyClothoids 0.2.0 G1. OSMnx 309/333→257/281→117/141 at 8 m,
  keeping 1 component; PyGeoOps 11 per-area centerlines (10/11
  multi-component); Clothoids single fit failed quality (356 m Hausdorff).
- [x] Experiment C: uncorrected vs corrected collaborative layout. Uncorrected
  had 1 road-clearance conflict (`SK-BLD-0038`); corrected has 7 buildings /
  16 units, 20.0 m N-S, dropped 0038/0061; all current checks pass except
  deferred full-site spacing (historical 4c-0 experiment; superseded by M4d).
  (M4c-1c/1d annotation: this block predates the honest-semantics split — the
  63.0% figure is the candidate open-space ratio, not designed green, and the
  current check semantics are 29 = 9 pass + 11 info + 9 deferred (0.24.1), with
  designed green 6.54% deferred.)
- [x] Reuse matrix with versions, licenses, hosts, tested APIs, metrics,
  verdicts and rejected uses: `docs/e2e/open-source-reuse-001/reuse-matrix.yaml`.
- [x] Visual comparison and editable DXF:
  `docs/e2e/open-source-reuse-001/`.
- [x] Found a real 4c defect: the corridor union is 1 polygon, but the noded
  road centerline graph has **5 components**. The corridor-only
  `ROAD_CONNECTIVITY` check is too weak; the 4c candidate is partial.
  (Diagnosed in 4c-1a: sub-ULP floating-point noding artefact — not a design
  disconnection; fixed with explicit shared-coordinate junctions.)

**M4c-0 answer (partial):** OSMnx is the strongest candidate for a topology
preprocessor; Building Regulariser is a cleanup adapter; PyGeoOps is a
per-area centerline candidate; momepy is an evaluation adapter; Clothoids,
UrbGEN and Street Generator are not direct core dependencies. No open-source
tool produced a complete professional design by itself.

**Next in 4c (superseded by 4c-1a):** the noded topology check landed
dependency-free with explicit shared-coordinate junctions and the candidate was
regenerated; the OSMnx-consolidated base was rejected (tolerance-created
connectivity, source edge ids not preserved). OSMnx remains an optional
source-skeleton preprocessor. **Update (0.20.0):** group access is now bound to
declared `serves_group_ids` relations; the nearest-endpoint attribution used in
the M4c-1b evidence is removed.

### Next research main line

1. ~~Repair the design road topology~~ — **done in 4c-1a/1b/1e** (explicit shared-coordinate junctions, dependency-free noded check, 44-road access network, declared service relations, evidence regenerated).
2. ~~M4c-2 main-road alignment~~ — **done in 0.21.0 and Phase-0 corrected in 0.22.0** (overlap split 38.19068149970835 → 0; boundary-containment hard pass with margin 0.6735131264650868; `FULL_SITE_ROAD_CLEARANCE` remains deferred).
3. ~~First multi-candidate experiment~~ — **done in 0.22.0, evaluation integrity fixed in M4c-3a/0.23.0** (A/B1/B2/C all hard-pass; all-44-road class/terminal evidence; basis binding; 11 single-unit objectives with auxiliary excluded; default B1, road-first A; Pareto [B1,B2,C,A]; no single score).
4. ~~M4d-1 full-site expansion~~ — **full-site research draft in 0.24.1** (55 buildings/109 units/2,398 households, 18 rows / 8 superblocks (36 row records); boundary/overlap/NS spacing/clearance pass; designed green 15.93% deferred; 61.06% potential open space auxiliary; access 0.0/17 errors and dead-end 17 unresolved fail; 25–130 m caps found no complete layout, 147.25 m unbounded candidate not proven global minimum). **M4d-2 open:** recompute access declarations/terminals or clearance-preserving road geometry; run in parallel with a real CAD host round-trip (LibreCAD/FreeCAD/AutoCAD GUI), a real design-office profile, and R1 evidence closure.
5. **Measure design quality, not only sketch fidelity** — intent preservation, completeness, internal consistency, verified constraint satisfaction and CAD editability; Hausdorff/IoU remain secondary.
6. **Professional building and road design** — apply the unit-type library, resolve six unit-count conflicts and the kindergarten classification; separate 支路/入户路, then review road class and cross-sections.
7. **Agent ↔ real CAD loop** — hand the draft to the CAD bridge; verify host read/edit/readback/diff/local rebuild; keep LibreCAD, FreeCAD and AutoCAD GUI as independent evidence lanes.

## Milestone 5 — Production hardening (not started)

- Durable store integration (SQLite or chosen alternative) into runtime save/load.
- Windows ACL/DPAPI credential handling and installer trust.
- MCP wire-level conformance with the official SDK.
- Multi-process and crash-recovery testing.
- Performance and large-project benchmarks.

## Ordering rule

Do not start a later milestone merely because an earlier one has code. The exit criteria are the gate. Evidence packages block capability claims independently of code progress.

Host-blocked evidence lanes (for example 3c LibreCAD/FreeCAD/GUI) may run in parallel and do not block Milestone 4. They still block capability claims in their own scope; `#6` remains open.
