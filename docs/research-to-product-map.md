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
- No human-confirmed trace or fidelity metrics; all 10 close pairs are resolved; six unit-count conflicts and the kindergarten facility remain for review; 支路/入户路 unseparated; no canonical handoff.
- Contract: `contracts/sketch-evidence-v0.1.yaml`; tests: `tests/test_sketch_evidence.py` (8).

## EP-R1-ROAD-001 topology start (0.10.0)

- 312 rough centerlines: 41 main-road and 271 branch/access edges.
- As-drawn graph: 306 nodes, 312 edges, 9 components, 129 endpoints, 99 junctions, 15 cycles.
- Connected with eight inferred nearest-node connectors: 320 edges, 1 component; every connector is marked `inferred_nearest_endpoint`, `proposed`, and is not a designed road link.
- No road width, cross-section, profile, alignment, junction turn geometry or surface; 支路/入户路 remain combined.
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

- Sketch evidence → human-confirmed trace and fidelity metrics when the designer supplies or approves the geometry reference.
- Road width/profile/alignment → after review of the eight inferred connectors and 支路/入户路 separation.
- Site Topology Contract → when multi-building shared-boundary/overlap validation starts.
- Environment dependency/result schemas → when an analysis slice starts and `EP-R1-ENV-001` has evidence.
- CAD-IR + semantic equivalence → completed in Milestones 3a/3b; third-party matrix remains partial (#6).
