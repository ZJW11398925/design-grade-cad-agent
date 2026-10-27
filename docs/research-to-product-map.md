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
| Benchmark Case Schema v0.1 | `deferred` | — | Milestone 2 integration suite |
| Real Benchmark Data Contract v0.1 | `blocked_by_evidence` | — | No Tier B/C paired site-sketch data |

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
| DEV-CAD-001..008 | `deferred` | GitHub issues, Milestone 3 | Issues created; implementation explicitly postponed |
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

Promoted and implemented with 8 E2E tests, 7 analysis tests and 9 CAD delivery tests (2 xfail):

- synthetic shadow baseline with explicit unknown states;
- minimal CAD-IR with identity/revision/provenance;
- DXF R2010 compiler and independent readback validator/manifest;
- living pipeline from DOMAIN-SLICE-001 to DXF readback;
- `DEV-CAD-003` gaps recorded as strict xfail.

Still deferred: third-party CAD round-trip, IFC, real sketch input, standards profile and independent shadow engine.

## E2E-003 implementation (0.5.0)

Promoted and implemented with 19 scenarios (6 positive, 13 strict xfail):

- LWPOLYLINE elevation, MultiPolygon 2-part+hole, symbol-table case and missing XDATA handled;
- CIRCLE/TEXT 3D, TEXT placement, entity style overrides and LWPOLYLINE full semantics remain xfail with issues #17/#18/#3;
- structured `VALIDATOR_ERROR` remains xfail with #7;
- issue categories and `delivery-comparison.json` make classification and comparison explicit;
- same-library ezdxf only; third-party CAD remains out of scope (#6);
- CAD-IR fingerprint/dependency-key consistency tracked as #16 / DEV-CAD-011.

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

- Site Topology Contract → when multi-building shared-boundary/overlap validation starts.
- CAD-IR + semantic equivalence → Milestone 3.
- E2E fixtures → Milestone 2.
- Environment dependency/result schemas → when an analysis slice starts and `EP-R1-ENV-001` has evidence.
