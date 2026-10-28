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

**4b.1 exit (met for code/evidence):** scope cannot silently become global confirmation; a sketch boundary cannot become `SITE-001`; a source-geometry mutation with a stale hash fails; a road-topology mismatch fails closed; the synthetic E2E and CAD delivery remain green; 206 tests pass. The real pilot remains blocked until the designer signs the object-level review.

### Milestone 4c — Autonomous Site Design Synthesis (first round partial; M4c-0 complete)

Goal: the Agent converts the sketch's spatial intent into a self-consistent,
standardized schematic design without asking the designer to review sketch
geometry. The designer reviews the product.

First round (`docs/e2e/design-synthesis-001/`):

- [x] Design basis with the required FAR 1.55–1.60, ≥1 parking space/household and ≥20 m north-south spacing, plus explicit assumptions for the unit module, floors, roads, setbacks, green and drawing standard.
- [x] Full-site context: 55 buildings, 109 staircases, 2,398 households, 319,536 m² GFA, FAR 1.565, 2,398 parking spaces and 5 entrances.
- [x] Focus block G-01: 7 standardized buildings / 16 units in rows with 20.0 m north-south spacing, unit division lines, green strips and an access loop.
- [x] Replace the 333-edge skeleton mesh with a design road hierarchy: merged main roads, one branch per group, one focus access loop; widths 12/7/4 m; record the source mesh as evidence.
- [x] Allocate cluster/ strip/ supplementary green; site green ratio 63.0%.
- [x] Check FAR, parking, entrances, unit count, spacing, setback, overlap, road clearance, connectivity, road widths and green ratio; record full-site north-south spacing as deferred.
- [x] Produce an editable 208-entity DXF with layers, building/road labels, dimensions, key plan, title block, legend, north arrow and scale bar; audit 0/0; readback 208/208.
- [x] Mark all design objects `rule_derived` in `proposal_preview`; no `human_confirmed`; title block says Agent-generated and not code-compliant.
- [x] Record the design diff, dropped buildings and the persistent draft manifest.

Next in 4c:

- **First fix the road topology**: use the OSMnx-consolidated connected network as the topology base, replace the corridor-only check with a noded check, then regenerate the candidate.
- Expand the standardized layout from the focus block to all groups; enforce 20 m north-south spacing site-wide.
- Improve the design-intent model: group boundaries, road hierarchy, access logic and green relationships.
- Add design evaluation/search: compare candidate layouts against intent preservation, completeness, consistency, constraint satisfaction and CAD editability.
- Replace the provisional unit module with the designer's unit-type library.
- Move to a real CAD host loop after the draft is stable.

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
  deferred full-site spacing.
- [x] Reuse matrix with versions, licenses, hosts, tested APIs, metrics,
  verdicts and rejected uses: `docs/e2e/open-source-reuse-001/reuse-matrix.yaml`.
- [x] Visual comparison and editable DXF:
  `docs/e2e/open-source-reuse-001/`.
- [x] Found a real 4c defect: the corridor union is 1 polygon, but the noded
  road centerline graph has **5 components**. The corridor-only
  `ROAD_CONNECTIVITY` check is too weak; the 4c candidate is partial.

**M4c-0 answer (partial):** OSMnx is the strongest candidate for a topology
preprocessor; Building Regulariser is a cleanup adapter; PyGeoOps is a
per-area centerline candidate; momepy is an evaluation adapter; Clothoids,
UrbGEN and Street Generator are not direct core dependencies. No open-source
tool produced a complete professional design by itself.

**Next in 4c:** add the optional OSMnx adapter, replace the corridor-only
connectivity check with a noded topology check, and apply a design-aware
hierarchy on the connected consolidated network before regenerating the
candidate.

### Next research main line

1. **Repair the design road topology** — optional OSMnx adapter, noded connectivity check, design-aware hierarchy on the connected network; then expand to all groups.
2. **Expand and evaluate autonomous design** — full-site group layout, design-quality metrics, candidate comparison; do not return to sketch-level human review as the gate.
3. **Measure design quality, not only sketch fidelity** — intent preservation, completeness, internal consistency, verified constraint satisfaction and CAD editability; Hausdorff/IoU remain secondary.
4. **Professional building and road design** — apply the unit-type library, resolve six unit-count conflicts and the kindergarten classification; separate 支路/入户路, then review road class and cross-sections.
5. **Agent ↔ real CAD loop** — hand the draft to the CAD bridge; verify host read/edit/readback/diff/local rebuild; keep LibreCAD, FreeCAD and AutoCAD GUI as independent evidence lanes.

## Milestone 5 — Production hardening (not started)

- Durable store integration (SQLite or chosen alternative) into runtime save/load.
- Windows ACL/DPAPI credential handling and installer trust.
- MCP wire-level conformance with the official SDK.
- Multi-process and crash-recovery testing.
- Performance and large-project benchmarks.

## Ordering rule

Do not start a later milestone merely because an earlier one has code. The exit criteria are the gate. Evidence packages block capability claims independently of code progress.

Host-blocked evidence lanes (for example 3c LibreCAD/FreeCAD/GUI) may run in parallel and do not block Milestone 4. They still block capability claims in their own scope; `#6` remains open.
