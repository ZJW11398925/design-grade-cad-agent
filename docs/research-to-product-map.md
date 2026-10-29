# Research → Product Promotion Map

Status: **living control document**
Version: 1.0
Updated: 2026-10-27

## Purpose

The research archive contains many candidate schemas, contracts and conclusions produced under different evidence levels. A document existing in `research/archive/` does **not** mean the current code must obey it.

This map is the single index of which research artifacts have been promoted into living contracts, which remain research evidence, and which are deliberately deferred or blocked. Every promotion changes the target path and adds a test or contract reference. Nothing is promoted merely because it is well written.

## Status vocabulary

| Status | Meaning |
|---|---|
| `promoted` | Now a living contract/docs artifact and binding on current code/tests |
| `research_only` | Preserved as evidence; not binding on current code |
| `deferred` | Intentionally postponed to a named milestone |
| `blocked_by_evidence` | Cannot be promoted until a named evidence gap closes |
| `superseded` | Replaced by a later artifact; historical only |

## Promotion decisions

### Architecture and governance

| Research artifact | Status | Living target | Notes |
|---|---|---|---|
| Canonical Site IR v0.3 | **promoted** | `contracts/canonical-site-ir-v0.4.yaml` | Promotion metadata only; no semantic change from v0.3 |
| Agent Authority Matrix v0.1 | **promoted** | `docs/architecture/authority.md` | Narrative living authority model |
| Module Contracts M01–M11 v0.1 | **promoted** | `docs/architecture/overview.md` | Already summarized; archive remains source evidence |
| Architecture Challenge Report v0.1 | **promoted** | `docs/architecture/overview.md` + ADR-0001 | The 5 amendments are now baseline requirements |
| R1 Evidence Gate Register v0.1 | **promoted** | `contracts/evidence-gate-register-v0.2.yaml` | Packages remain `planned`; gates are binding on claims |
| Provisional Decision Register v0.1 | `research_only` | — | Decisions already reflected in living architecture docs |
| Research Gap Matrix v0.2 | `research_only` | — | Operational planning input; not a contract |
| R1 Development Research Charter Candidate v0.2 | **promoted** | `docs/roadmap.md` | Milestone structure and scope-freeze rule |
| MVP Boundary v0.1 | **promoted** | `docs/roadmap.md` | Narrowed further for domain slice 001 |

### Domain schemas

| Research artifact | Status | Living target | Notes |
|---|---|---|---|
| Trace Object Schema v0.1 | **promoted (minimal)** | `contracts/domain-contract-v0.1.yaml` + `src/dgcad_domain/trace.py` | Confirmed-trace fields and immutability implemented; multi-revision trace and ambiguity regions deferred |
| Road Profile Schema v0.1 | **promoted (minimal)** | `contracts/domain-contract-v0.1.yaml` + `src/dgcad_domain/road.py` | Multi-axis classification state and "unknown class blocks derived width" implemented; numeric standard profiles deferred |
| Road Classification and Design Profile research line | **promoted (minimal)** | `contracts/domain-contract-v0.1.yaml` + `src/dgcad_domain/road.py` | Separation of network role / function / access / special use / physical cross-section implemented; no Chinese numeric defaults |
| Building Object Schema v0.1 | **promoted (minimal)** | `contracts/domain-contract-v0.1.yaml` + `src/dgcad_domain/building.py` | Trace/professional footprint split, height state/source and revision axes implemented; typology grammar deferred |
| Regularization Gate v0.1 | **promoted (minimal)** | `contracts/domain-contract-v0.1.yaml` + `src/dgcad_domain/building.py` | States and "candidate requires review" implemented; real tolerances remain uncalibrated |
| Site Topology Contract v0.1 | `deferred` | — | Needed for multi-building shared-edge/overlap slices; not required by domain slice 001 |
| Environment Analysis Dependency Contract v0.1 | `deferred` | — | Requires an analysis slice and independent engine evidence |
| Environment Result Schema v0.1 | `deferred` | — | Same |
| CAD-IR Contract v0.1 | **promoted (minimal)** | `contracts/cad-ir-v0.1.yaml` + `src/dgcad_cad/ir.py` | Minimal E2E delivery subset; full CAD-IR semantics and Profile enforcement deferred |
| DXF Semantic Equivalence Policy v0.1 | **promoted** | `docs/status.md` (known defects) + Milestone 3 | Policy accepted; implementation deferred |
| IFC Round-trip Contract v0.1 | `blocked_by_evidence` | — | IfcOpenShell execution and a real host are unavailable |
| Benchmark Case Schema v0.1 | **partially promoted** | `contracts/sketch-evidence-v0.1.yaml` + `docs/e2e/sketch-001/` | Case/trace/review states implemented; a full benchmark suite is not built |
| Real Benchmark Data Contract v0.1 | **partially promoted** | `docs/e2e/sketch-001/README.md` | One Tier B designer sketch with designer-confirmed semantics; no human-confirmed reference trace or fidelity metrics |

### Standards and profiles

| Research artifact | Status | Living target | Notes |
|---|---|---|---|
| DB11/T 1948-2021 subset | `research_only` | — | Beijing local standard excerpt; **not** a project default and not a national profile |
| Profile Rule Contract v0.1 | **partially promoted** | `contracts/domain-contract-v0.1.yaml` | `normative_status` / `value_state` / failure policy concepts retained; full rule engine deferred |
| Chinese road standard source map | `research_only` | — | Unverified standard status and missing full text |
| Synthetic DXF Profile v0.3 | `research_only` | — | Synthetic fixture; not a design-office profile |

### Benchmarks, E2E and evidence

| Research artifact | Status | Living target | Notes |
|---|---|---|---|
| LOCAL-SKETCH-001 | `research_only` | — | Synthetic method calibration, not real accuracy |
| LOCAL-BLDG-001/002 | `research_only` | — | Synthetic identity/refusal probes |
| LOCAL-CAD-003/004 | `research_only` | — | Synthetic and DB11 subset probes |
| LOCAL-ENV-001 | `research_only` | — | NOAA baseline; independent engine missing |
| E2E-FIXTURE-001 v0.1–v0.3 | `research_only` | — | Superseded as the active pipeline by E2E-001; retained as historical evidence |
| E2E-001 living pipeline | **promoted** | `contracts/e2e-pipeline-v0.1.yaml` + `src/dgcad_e2e/` + `tests/e2e/` | Domain → massing → shadow → CAD-IR → DXF → readback, using living packages only |
| E2E-002 mutation/rebuild | **promoted** | `contracts/e2e-mutation-v0.1.yaml` + `src/dgcad_e2e/living_project.py` + `tests/e2e/` | Scoped stale, deterministic rebuild worker, manifest comparison; road surface deferred |
| E2E-003 adversarial delivery | **promoted** | `contracts/e2e-adversarial-v0.1.yaml` + `tests/e2e/test_e2e_003_adversarial.py` | Adversarial scenarios, categories and issue mapping; same-library only |
| E2E-003b semantic/dependency | **promoted** | `src/dgcad_cad/` + `tests/e2e/test_e2e_003b_semantics.py` | Fingerprint consistency, symbol tables, ring keys, raw/canonical manifest; same-library only |
| E2E-003c third-party CAD | **partially promoted** | `contracts/third-party-roundtrip-v0.1.yaml` + `scripts/third_party/autocad_core_roundtrip.py` | AutoCAD 2024 Core Console evidence captured; LibreCAD/FreeCAD/GUI matrix still open (#6) |
| CASE-SKETCH-001-HANDOFF-A | **promoted (gate; pilot blocked)** | `contracts/sketch-domain-handoff-v0.2.yaml` + `src/dgcad_domain/sketch_handoff.py` + `docs/e2e/sketch-handoff-a/` | Source integrity, road topology, review packet and scope/authority propagation promoted; the real pilot blocks at `HUMAN_OBJECT_REVIEW_REQUIRED` until an object-level review exists |
| CASE-SKETCH-001-AUTONOMOUS-DESIGN-001 | **promoted (partial draft)** | `contracts/design-synthesis-v0.9.yaml` + `src/dgcad_design/` + `docs/e2e/design-synthesis-001/` | Full-site metrics + focus-block standardized design; `rule_derived` draft, no human review gate; full-site checks deferred on the focus sheet; road topology corrected in 4c-1a; honest semantics in 4c-1c/1d; road service coverage in 4c-1b (44 roads, coverage 1.0, first design-geometry change); M4c-1e (0.20.0) bound access to declared `serves_group_ids` relations; M4c-2/Phase-0 (0.21.0–0.22.0) resolved the main-road/building overlap by a recorded MAIN-19 diversion, added site-boundary containment as a hard check with MAIN-08/16/18 repairs, split the overlap fields (`main_before` 38.19068149970835 / `main_after` 0.0 / `new_access` 0.9943558185246757 / `total_after` 0.9943558185246756), made alignment semantics `local_search_exhausted`, published `source_segment_map`/design-diff alignment+dead-end records, and re-baselined geometry to 58/68/cyclomatic 11; M4d (0.24.0) regenerated focus evidence under v0.9 — 29 checks = 9 pass + 11 info + 9 deferred (+3 DXF = 32), `DESIGNED_GREEN_RATIO` deferred (designed green 6.54%; the 61.46% open-space tiling is auxiliary only), four `FULL_SITE_*` deferred; DXF 211 entities, 467 tests; v0.8/v0.7/v0.6/v0.5/v0.4/v0.3/v0.2/v0.1 superseded |
| CASE-SKETCH-001-FULL-SITE-001 | **promoted (research draft)** | `src/dgcad_design/buildings.py`/`consistency.py`/`green.py`/`drawing.py` + `docs/e2e/design-synthesis-full-site-001/` | 55 buildings / 109 units / 2,398 households in 18 rows / 8 superblocks (36 row records) against the frozen 44-road network, focus G-01 preserved; displacement sum 2,328.95 m / max 147.25 m / mean 42.34 m; full-site checks 29 = 11 pass + 11 info + 5 deferred + 2 fail — boundary/overlap/NS spacing (19.999999999999943 m)/road clearance (3.0163622902759215 m) pass; `DESIGNED_GREEN_RATIO` deferred (designed green 15.93% <30%; open-space tiling 0.6105795566533792 / 124,633.20 m² / 10 parcels auxiliary only); `ROAD_ACCESS_COVERAGE` fail 0.0 (17 relation errors) and `DEAD_END_RESOLUTION` fail 17 unresolved; frozen network + old access declarations make clearance/access mutually incompatible; full-site DXF 547/547/XDATA 11/privacy; research draft, not canonical |
| CASE-SKETCH-001-MULTI-CANDIDATE-001 | **promoted (first experiment; integrity-fixed)** | `contracts/design-candidates-v0.2.yaml` + `src/dgcad_design/candidates.py`/`evaluation.py`/`visuals.py` + `docs/e2e/design-candidates-001/` | Four deterministic candidates A/B1/B2/C for the MAIN-19 conflict; all-44-road geometry change by main/branch/access class and group terminal (A BR-G-08 2.826 / G-08 terminal 2.826; B1 BR-G-09 7.352; B2 13.645; C BR-G-08 76.700 / G-08 terminal 75.315 — C is not a small change); `parent_basis_id` + fingerprint binding (`basis_ok` fail otherwise); `HISTORICAL_BOUNDARY_ARCHIVE` separated from current candidates (current B1 boundary-compliant 0.6735; pre-repair 66.235 archived); hard gates recomputed from geometry; 11 single-unit objectives with auxiliary excluded from Pareto/preference; default recommends B1, road-first A; Pareto [B1,B2,C,A] with reasons and no single score; v0.1 superseded |
| CASE-SKETCH-001-OPEN-SOURCE-REUSE-001 | **promoted (research evidence)** | `experiments/m4c0/` + `docs/e2e/open-source-reuse-001/` | Building Regulariser, OSMnx, PyGeoOps, Clothoids, momepy tested; OSMnx useful as an optional source-skeleton preprocessor, not a connectivity proof (see 4c-1a); no new core dependencies |
| DEV-CAD-001..008 | **partially promoted** | Issues #1/#4/#5/#6/#8 + closed #2/#3/#7 | Milestone 3a fixed 002/003/007; 009/010 added and fixed; 001/004/005/006/008/011 remain for 3b/3c |
| R0 acquisition batches (BATCH-001..005) | `research_only` | — | Unclosed evidence; gate claims remain blocked |

### Code prototypes

| Prototype | Status | Living target | Notes |
|---|---|---|---|
| Foundation v0.1/v0.2 | **promoted** | `src/dgcad_foundation/` + `tests/test_foundation_contracts.py` | 21 contract tests |
| Stateful Runtime v0.1 | **promoted** | `src/dgcad_runtime/` + `tests/test_runtime_contracts.py` | 22 contract tests |
| Deployment Boundary v0.1 | **promoted** | `src/dgcad_deployment/` + `tests/test_deployment_contracts.py` | 8 contract tests |
| Deployment Lifecycle v0.2 | **promoted** | `src/dgcad_deployment/` + `tests/test_lifecycle_contracts.py` | 14 contract tests |
| Duplicate prototype copies inside R0 archive | `superseded` | — | Historical only; canonical code is root `src/` |

## Promotion rules

1. A research artifact is promoted only when current code or current governance depends on it.
2. A promoted artifact gets a living path under `contracts/` or `docs/` and a version distinct from its archive version.
3. Promotion must not silently change semantics. If semantics change, the change is recorded in the living artifact and in `CHANGELOG.md`.
4. Deferred artifacts keep their archive path and are not duplicated into the root tree.
5. A promoted claim is still scope-limited. Promotion is not a capability promotion.
6. If new evidence invalidates a promoted decision, add a new version and mark the old one `superseded`; never edit archived evidence.

## Domain slice 001 implementation (0.2.0)

Promoted and implemented with 26 tests:

- confirmed trace fixture and immutability;
- Building intent, footprint preservation/regularization candidate, height state/source;
- Road graph, corridor, explicit cross-section, profile resolution gate;
- T-junction atomic change set;
- massing and road-surface derived artifacts with dependency keys;
- structured domain validators;
- StatefulRuntime integration (propose → preview → human approval → commit → stale → rebuild job).

Still deferred: real sketch input, real alignment/junction geometry, standard profiles and UI.

## E2E-001 implementation (0.3.0)

Promoted and implemented with 8 E2E tests, 7 analysis tests and 9 CAD delivery tests:

- synthetic shadow baseline with explicit unknown states;
- minimal CAD-IR with identity/revision/provenance;
- DXF R2010 compiler and independent readback validator/manifest;
- living pipeline from DOMAIN-SLICE-001 to DXF readback;
- `DEV-CAD-003` LWPOLYLINE gaps are now detected (Milestone 3a).

Still deferred: third-party CAD round-trip, IFC, real sketch input, standards profile and independent shadow engine.

## E2E-003 implementation (0.5.0)

Promoted and implemented with 20 scenarios, all positive:

- LWPOLYLINE elevation, MultiPolygon 2-part+hole, one layer linetype case and missing XDATA handled;
- CIRCLE/TEXT 3D, TEXT placement, entity style overrides and LWPOLYLINE full semantics are now detected (issues #17/#18/#3 closed);
- structured `VALIDATOR_ERROR` is implemented (#7 closed);
- issue categories and `delivery-comparison.json` make classification and comparison explicit, with DXF/manifest hashes verified against files;
- same-library ezdxf only; third-party CAD remains out of scope (#6);
- 3b/3c remain: full symbol table (#5), fingerprint/dependency consistency (#16), ring identity (#1), raw/canonical geometry (#4), profile semantics (#8);
- CAD-IR fingerprint/dependency-key consistency is fixed (3b); global scene revision is metadata.

## E2E-003b implementation (0.7.0)

Implemented with 11 tests:

- unrelated commits do not stale CAD-IR or change its fingerprint; relevant road semantic changes do;
- symbol-table case semantics for layers, linetypes, text styles, blocks and dimstyles;
- content-derived `ring_key` stable across sibling-part insertion;
- readback manifest carries canonical targets and raw DXF semantics with tolerance 1e-9;
- serialization differences separated from profile violations.

Still open: LibreCAD/FreeCAD/GUI third-party matrix (#6), arcs/splines outside the current entity set, real sketch/road/IFC/standards evidence.

## E2E-003c third-party evidence (0.8.0)

- AutoCAD 2024 Core Console opened, saved and read back the synthetic DXF in an isolated profile.
- 15 entities and 15 XDATA records preserved; layers, styles, units, geometry and audit 0/0 preserved.
- Verdict `semantic_pass_with_serialization_differences`: R2010→R2018 and `CONTINUOUS`→`Continuous` only.
- LibreCAD, FreeCAD and GUI visual/print QA were not executed; #6 remains open.

## CASE-SKETCH-001 intake (0.9.0)

- First Tier B designer-sketch intake; the sketch is published, while the DWG/DXF, redline/project coordinates and metric scale remain private.
- Designer-confirmed semantics: metre; red buildings; magenta underground garage entrances; brown main roads; blue branch/access roads; green cluster spaces; existing survey buildings removed; top crop clips only a road segment.
- Image-space proposed trace: 55 buildings (50 standalone + 5 designer-confirmed merges), 63 original red components preserved for provenance (13 merged), 3 garage entrances, 12 green spaces, 9 road areas and 1 site boundary.
- Designer building merges: M-001 = 0046+0047+0060 (3 units) plus connectors 0062+0063; M-002 = 0030 (2 units) + 0053 (1 unit); M-003 = 0001+0037 (kindergarten/facility); M-004 = 0019+0058; M-005 = 0027+0059. All buildings record 11 floors as provisional; the unit-type library is pending.
- Unit counts: 16 one-unit, 21 two-unit, 17 three-unit; 52 inferred from sketch dimensions, 2 confirmed, 1 facility excluded; six length-vs-area conflicts are flagged.
- 312 rough road centerlines (`proposed_rough`): main road 1 component, blue network 8 components.
- No full-case human-confirmed trace or fidelity metrics; all 10 close pairs are resolved; six unit-count conflicts and the kindergarten facility remain for review; 支路/入户路 unseparated; the selected pilot subset is blocked at the object-level review gate.
- Contract: `contracts/sketch-evidence-v0.1.yaml`; tests: `tests/test_sketch_evidence.py` (11).

## CASE-SKETCH-001-HANDOFF-A (0.13.0)

- Handoff contract and model: `contracts/sketch-domain-handoff-v0.2.yaml` + `src/dgcad_domain/sketch_handoff.py`; v0.1 is superseded.
- Selected real subset: site boundary, one ordinary building, one merged building, one green, two main-road edges, one branch edge, one T-junction.
- Review status: the committed record is `designer_authorized_pilot`, not an object-level geometry review. The gate blocks with `HUMAN_OBJECT_REVIEW_REQUIRED`; a review packet and unsigned template are published instead of canonical/DXF.
- Boundary authority: the published sketch boundary maps to `SITE-SKETCH-001` with candidate authority; the private redline remains authoritative but is not used or published.
- Coordinate handoff: image-space → `LOCAL-XY-ZUP`, `uniform_scale_translation_yflip`, not a homography; local metric 2.438 px/m (range 2.25–2.89), no project coordinates; per-object sensitivity recorded.
- Source integrity: 3 files and 7 objects verified by SHA-256 and canonical geometry hashes; stale hashes and changed geometry fail closed.
- Road topology: 4 nodes, 3 edges, 1 component, one degree-3 T-junction; maximum endpoint offset 3.606 px against a 4.0 px declared tolerance; two edges direction-normalized.
- Downstream path (test double only): `ConfirmedTraceScene` → `build_initial_scene` → runtime proposal/approval/commit → Canonical → CAD-IR → DXF → readback; 11 entities, audit 0/0, readback 11/11; scope in trace/canonical/CAD-IR/XDATA/manifest.
- Unknown height/base, road hierarchy/cross-section and massing/width remain explicit; no third-party evidence.
- Tests: `tests/test_sketch_handoff.py` (32) and `tests/e2e/test_sketch_handoff_a.py` (6).


## CASE-SKETCH-001 open-source reuse sprint (0.15.0)

- Evidence: `docs/e2e/open-source-reuse-001/`; code: `experiments/m4c0/`; matrix: `reuse-matrix.yaml`.
- Building Regulariser 0.2.5 (MIT): 9 focus footprints, 63→61 vertices, area −2%, mean Hausdorff 1.07 m, ERI +0.012; cleanup adapter only.
- OSMnx 2.1.1 (MIT): 309/333→257/281 simplify→117/141 consolidate at 8 m, 1 component, length −10.7%; topology preprocessor, not a design hierarchy.
- PyGeoOps 0.6.0 (BSD-3): 11/11 road-area centerlines, 78% coverage, 10/11 multi-component.
- PyClothoids 0.2.0 (MIT): single G1 fit on MAIN-08 failed quality (356 m Hausdorff, −78 m length).
- momepy 1.0.0 (BSD-3): morphology/network metrics for candidate comparison only.
- UrbGEN (MIT, Rhino/Grasshopper) and Street Generator/rue-lib (MIT, not on PyPI, foreign widths) are reference-only; Clothoids/IfcOpenShell/Ladybug deferred.
- **Found a 4c defect**: the corridor union is one polygon, but the noded road centerline graph has 5 components; the `ROAD_CONNECTIVITY` check based on corridor union is too weak. (4c-1a diagnosis: sub-ULP floating-point noding artefact, not a design disconnection; fixed with explicit shared-coordinate junctions — noded graph 1 component.)
- No new core dependencies; the experiment deps are optional.

## CASE-SKETCH-001 autonomous design synthesis (0.14.0)

> Historical 0.14.0 snapshot (contract v0.2, 208 entities, 8 tests). Current
> state: 0.24.0 / contract v0.9 / 29 checks / 467 tests — see the promotion
> registry rows above and `docs/status.md` §16. This section is not rewritten;
> it records what was promoted at 0.14.0.

- Contract and package: `contracts/design-synthesis-v0.2.yaml` (v0.1 superseded), `src/dgcad_design/`, `docs/e2e/design-synthesis-001/`.
- Full-site context: 55 buildings, 109 staircases, 2,398 households, 319,536 m² GFA, FAR 1.565, 2,398 parking spaces, 5 entrances.
- Focus block G-01: 7 standardized buildings / 16 units in 20 m rows, unit division lines, green strips and an access loop; 2 buildings recorded as dropped.
- Design changes: standardized staircase modules, row layout, green strips, simplified main/branch/access road hierarchy, two added garage entrances.
- Authority: `rule_derived` in `proposal_preview`; no `human_confirmed`; draft revision persisted; designer may edit or adopt.
- Verification at 0.14.0: FAR, parking, entrance count, unit count, focus spacing/setback/overlap/road clearance, connectivity, road widths and green ratio pass; full-site spacing deferred (historical; M4d later checks full-site N-S spacing).
- CAD: 208 entities, audit 0/0, readback 208/208, 23 declared design layers (25 table layers minus `0`/`Defpoints`; 20 used by modelspace entities), title block/key plan/dimensions; same-library ezdxf only.
- Tests: `tests/test_design_synthesis.py` (8).

## EP-R1-ROAD-001 unified-mask topology (0.11.0)

- The separate-colour skeleton produced 9 artificial components; that result is superseded.
- Unified brown+blue mask with a 5 px closing restores 1 connected component: 309 nodes, 333 edges, 111 endpoints, 121 junction candidates, 25 cycles; 65 main-road and 268 branch/access edges.
- Colour is a road-class attribute, not a topology separator; junctions are skeleton graph nodes, not inferred connectors.
- The eight nearest-node connectors are rejected and retained as negative evidence.
- No width, cross-section, profile, alignment, junction turn geometry or surface; 支路/入户路 remain combined.
- Contract: `contracts/sketch-evidence-v0.1.yaml` (`road_topology`); tests: `tests/test_road_topology.py` (3).

## E2E-002 implementation (0.4.0)

Promoted and implemented with 6 E2E tests:

- scoped staleness for height, T-junction node and north-bearing mutations;
- canonical project context with versioned/sourced north bearing;
- deterministic corridor centerline rebuild from latest canonical edges;
- Runtime claim/recompute/write/validate/complete rebuild worker;
- manifest comparison by object IDs, revisions, dependency fingerprint and readback verdict;
- road surface geometry explicitly deferred (no `SURFACE-R-002` artifact).

## Current living contracts

```text
contracts/
├── canonical-site-ir-v0.4.yaml
├── domain-contract-v0.1.yaml
├── cad-ir-v0.1.yaml
├── e2e-pipeline-v0.1.yaml
├── e2e-mutation-v0.1.yaml
├── e2e-adversarial-v0.1.yaml
├── third-party-roundtrip-v0.1.yaml
├── sketch-evidence-v0.1.yaml
├── sketch-domain-handoff-v0.2.yaml
├── design-synthesis-v0.9.yaml
├── design-candidates-v0.2.yaml
├── evidence-gate-register-v0.2.yaml
├── runtime-state-contract-v0.1.yaml
├── runtime-agent-surface-v0.1.yaml
├── deployment-boundary-contract-v0.2.yaml
├── sidecar-lifecycle-contract-v0.1.yaml
├── local-auth-capability-contract-v0.1.yaml
├── cad-bridge-contract-v0.1.yaml
├── cad-bridge-lifecycle-contract-v0.2.yaml
└── mcp-binding-v0.3.yaml
```

## Next promotion review

Re-run this map before each milestone exit. The next expected promotions are:

- ~~OSMnx topology adapter → noded connectivity check~~ — done in 4c-1a without OSMnx (explicit shared-coordinate junctions, dependency-free noded check); next: design-aware hierarchy and full-site expansion.
- Autonomous design draft → full-site group layout, design-quality evaluation and candidate comparison.
- Sketch evidence → human-confirmed trace and fidelity metrics when the designer completes the object-level review packet and supplies or approves the geometry reference.
- Handoff → a real `human_object_review` record; then the selected subset may enter Canonical/DXF without a test double.
- Road connectivity from actual geometry → after review of the 121 junction candidates; then width/profile/alignment and 支路/入户路 separation.
- Site Topology Contract → when multi-building shared-boundary/overlap validation starts.
- Environment dependency/result schemas → when an analysis slice starts and `EP-R1-ENV-001` has evidence.
- CAD-IR + semantic equivalence → completed in Milestones 3a/3b; third-party matrix remains partial (#6).
