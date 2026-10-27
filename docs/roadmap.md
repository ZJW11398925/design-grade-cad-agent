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

## Milestone 3 — CAD validator hardening (3c partial; Milestone 4 next)

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

Each package has its own decision question, raw evidence, metrics, failure policy and scope-leakage prohibition. No package is a checklist for production release.

### EP-R1-SKETCH-001 — in progress (0.9.0)

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
- [ ] Canonical Building/Road handoff from this sketch.

**Exit (not met):** a designer-confirmed semantic trace, a human-confirmed geometry reference, fidelity metrics within a declared scope, and a canonical handoff. Until then R1-G07 remains partial.

### EP-R1-ROAD-001 — in progress (0.11.0)

- [x] Extract rough centerlines; the separate-colour skeleton produced 306 nodes, 312 edges and 9 components — **wrong process**, superseded.
- [x] Union brown+blue into one road mask; 5 px closing (4 px leaves 5 components) -> 1 connected component.
- [x] Unified network: 309 nodes, 333 edges, 111 endpoints, 121 junction candidates, 25 cycles; 65 main and 268 branch/access edges.
- [ ] Review the 121 junction candidates and the 5 px closing kernel.
- [ ] Road width, cross-section, profile and alignment.
- [ ] Separate 支路 from 入户路.
- [ ] Canonical road graph handoff.

**Exit (not met):** a reviewed unified-mask road graph with accepted junctions, explicit width/profile/alignment inputs where required, and a canonical handoff. Until then road topology remains `proposed_unified_mask`.

## Milestone 5 — Production hardening (not started)

- Durable store integration (SQLite or chosen alternative) into runtime save/load.
- Windows ACL/DPAPI credential handling and installer trust.
- MCP wire-level conformance with the official SDK.
- Multi-process and crash-recovery testing.
- Performance and large-project benchmarks.

## Ordering rule

Do not start a later milestone merely because an earlier one has code. The exit criteria are the gate. Evidence packages block capability claims independently of code progress.
