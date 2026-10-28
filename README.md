# Design-Grade CAD Agent (DGCAD)

[![CI](https://github.com/ZJW11398925/design-grade-cad-agent/actions/workflows/ci.yml/badge.svg)](https://github.com/ZJW11398925/design-grade-cad-agent/actions/workflows/ci.yml)

**A traceable research-and-development workspace for turning hand-drawn site sketches into professional, verifiable site models and editable CAD/BIM output.**

> **Status: research prototype (v0.20.0).** This is not production CAD software, not a compliance certification, and not a validated AutoCAD/FreeCAD integration. Claims are scoped to the tests and evidence recorded in this repository.

---

## 1. The problem

A designer supplies a rough site sketch with buildings, roads, green space and boundaries. The system must:

1. preserve the original sketch and a faithful trace as immutable evidence;
2. extract semantic intent and resolve it into topology-correct professional geometry;
3. produce an early lightweight 3D massing with explicit height/floor provenance;
4. support shadow, obstruction and planning-rule feedback;
5. export editable, independently verifiable DXF/IFC;
6. keep every object traceable from source to delivery, including revisions, authority, locks and staleness;
7. reserve a deterministic rule layer for national, industry, local and design-office standards.

The hard part is not drawing. It is **truth ownership, identity, authority, dependency and verification**.

## 2. Architecture in one screen

```text
DATA PLANE
  Source evidence
    -> Trace geometry
      -> Intent candidate
        -> Professional candidate
          -> Canonical Site Model        (single confirmed design truth)
            -> Derived 3D / analysis
              -> DXF / IFC / renderings  (derived, invalidatable)

CONTROL PLANE
  Agent proposal
    -> authority check
      -> deterministic tool execution
        -> rule / profile resolution
          -> validator
            -> human confirmation where required
              -> canonical commit
                -> stale propagation / local rebuild
```

Core invariants:

- **Source and Trace are never overwritten** by professionalization.
- **The Agent never writes confirmed design state.** It proposes; deterministic engines compute; humans confirm.
- **DXF/IFC are adapters, not the database.** External edits re-enter only through reconcile proposals.
- **Unknown is a valid state.** Missing scale, height, road class or rule applicability is surfaced, never silently defaulted.
- **Every derived artifact carries a dependency fingerprint** and becomes stale when its inputs change.
- **Validation is layered and scoped.** A file that opens is not a design that complies.

The provisional architecture defines 11 modules (M01 Source & Calibration through M11 Agent), a typed Canonical Site IR, a three-world model (`canonical_current` / `proposal_preview` / `external`), and an authority matrix separating Agent, deterministic engine, rule engine, validator and human reviewer. See [docs/architecture/overview.md](docs/architecture/overview.md).

## 3. Current evidence base

| Area | State | Evidence |
|---|---|---|
| Foundation contracts | implemented, 21 tests | stable identity, three revision axes, authority/locks, AtomicChangeSet, ProposalSnapshot, dependency/stale, canonical hash, audit, migration, AgentGateway |
| Stateful runtime | implemented, 22 tests | proposals, approvals, jobs, artifacts, idempotency, restart recovery, stale-writer CAS |
| Deployment boundary | implemented, 8 tests | SQLite/WAL spike, content-addressed artifact store, CLI/service parity |
| Local sidecar lifecycle | implemented, 14 tests | token-free discovery, role-bound pairing, sessions, loopback HTTP, project lease, CAD bridge registry, child-process probe |
| Domain slice 001 | implemented, 26 tests | confirmed trace → Building/Road canonical objects; proposal/preview/commit; T-junction atomic change set; stale massing/surface; structured validators |
| E2E-001 living pipeline | implemented, 8 tests + 9 CAD tests | Domain → massing → shadow → CAD-IR → DXF → readback, using living packages only; bulge/width and full LWPOLYLINE checks now positive |
| E2E-002 mutation/rebuild | implemented, 6 tests | height change, T-junction move, north bearing, real rebuild worker, manifest comparison; road surface deferred |
| E2E-003 adversarial delivery | implemented, 20 tests (all pass) | geometry, style, identity, serialization and validator-error checks; same-library only |
| E2E-003b semantic/dependency | implemented, 11 tests | fingerprint consistency, symbol-table case, stable ring keys, raw/canonical manifest |
| E2E-003c third-party CAD | **partial**, 2 evidence tests | AutoCAD 2024 Core Console round-trip: 15 entities/XDATA preserved, R2010→R2018 + linetype case; LibreCAD/FreeCAD/GUI not run |
| EP-R1-SKETCH-001 intake | **in progress**, 11 evidence tests | [CASE-SKETCH-001](docs/e2e/sketch-001/README.md): designer sketch, 55 buildings (5 designer-confirmed merges), unit counts 16/21/17 + 1 facility, 11 floors provisional, public image-space trace and rough centerlines; private DWG/redline; no fidelity metrics or unit-type library yet |
| Real sketch → canonical handoff | **gate implemented; pilot blocked**, 6 E2E tests | [CASE-SKETCH-001-HANDOFF-A](docs/e2e/sketch-handoff-a/README.md): 7 selected objects pass source-integrity and road-topology checks but stop at `HUMAN_OBJECT_REVIEW_REQUIRED`; the downstream Canonical → CAD-IR → DXF path (11/11) is proven only with an explicitly marked test double; scope, geometry quality and boundary authority propagate when confirmed |
| Autonomous design synthesis | **partial draft implemented**, 9 tests | [CASE-SKETCH-001 design synthesis](docs/e2e/design-synthesis-001/README.md): full-site context + focus block G-01; 7 standardized buildings / 16 units in 20 m rows; FAR 1.565 = arithmetic scenario (`FAR_ARITHMETIC_SCENARIO` info; final verification deferred); parking entrance count info (assumed nominal capacity 1,000 vs 2,398 required — capacity/layout deferred); open space dual-measured (candidate 63.02% classified / unbuilt 65.35% geometric union — neither is designed green, designed green 6.54% deferred); **206-entity** editable DXF (content unchanged since 0.19.0; the byte SHA changes per save because of ezdxf GUIDs); `rule_derived` draft, not human-confirmed. M4c-1b made the first design-geometry change: **44 design roads** (25 main + 17 branch + 2 access), road access coverage **1.0 (17/17 groups)**; M4c-1e (0.20.0) bound that evidence to **declared** `serves_group_ids` access relations (17 group-access roads: 16 branch + ACC-G-12; plus BR-FOCUS and the focus loop = 19 connector roads), so each group is served by its own road (G-08 → BR-G-08, G-13 → BR-G-13) instead of the nearest endpoint. Dead ends are all classified, not all justified: 17 justified / 5 unfinished / 2 unclassified (7 unresolved, `DEAD_END_RESOLUTION` deferred); parking is proximity-only (`PARKING_ENTRANCE_PROXIMITY` info; driveway `PARKING_DRIVEWAY_CONNECTION` deferred); the pre-existing 38.19 m² main-road/building overlap (MAIN-19 34.42 + MAIN-08 3.77) is a machine-checked deferred conflict (`MAIN_ROAD_BUILDING_OVERLAP`, `known_unresolved`), and full-site road clearance remains deferred (`FULL_SITE_ROAD_CLEARANCE`). |
| Open-source design reuse | **sprint complete; partial answer**, 3 tests | [M4c-0](docs/e2e/open-source-reuse-001/README.md): Building Regulariser, OSMnx, PyGeoOps, Clothoids, momepy tested on CASE-SKETCH-001; OSMnx consolidation 309/333→117/141 with 1 component; Building Regulariser limited; PyGeoOps per-area; Clothoids single fit fails; momepy evaluation only; no new core dependencies |
| Road network topology | **connected_by_unified_road_mask**, 3 tests | 1 connected design network: 309 nodes / 333 edges / 121 junction candidates; colour is a class attribute; no width/profile/alignment |
| R0 research | archived | 5 acquisition batches, synthetic benchmarks, adversarial reviews, architecture challenge |
| Real-world evidence | **partially obtained** | one designer sketch intake (CASE-SKETCH-001); still missing a field-paired case, real design-office profile, IFC round-trip, independent solar engine, AutoCAD/FreeCAD host exchange, MCP wire conformance |

**Verified test baseline: 334 passed (334 collected)** (`python -m pytest -q`).

### Explicit non-claims

- No MCP wire-level conformance: the official MCP Python SDK was unavailable in the research environment.
- No real AutoCAD or FreeCAD host message exchange: only a generic loopback bridge lifecycle was executed.
- No production database decision: SQLite/WAL is a local-sidecar candidate only.
- No production security approval: session authority is in-memory; Windows ACL/DPAPI, installer trust and same-user malware resistance are out of scope.
- No Chinese road/building daylight compliance claim: standard clauses were not fully obtained and no numeric design defaults were frozen.
- E2E-001/002/003 remain same-library ezdxf. E2E-003c adds one real AutoCAD 2024 Core Console round-trip, but the LibreCAD/FreeCAD/GUI matrix is still incomplete (#6).
- Third-party evidence is **partial**: AutoCAD 2024 Core Console executed with `semantic_pass_with_serialization_differences`; LibreCAD, FreeCAD and AutoCAD GUI visual QA are not executed. `DEV-CAD-006` / #6 remains open. Arcs/splines are outside the current delivery entity set.
- Road surface geometry is deferred in E2E-002: no `SURFACE-R-002` artifact is registered or presented as generated road surface.
- CASE-SKETCH-001 is one hand-modified designer sketch: semantic labels, five building merges, the 1/2/3-unit type set and the 11-floor assumption are designer-confirmed; building geometry, inferred unit counts, heights and road centerlines are proposed/inferred/unknown, and no fidelity metrics exist against a human-confirmed trace.
- Unit counts: 16 one-unit, 21 two-unit, 17 three-unit; 52 are inferred and 2 confirmed. The kindergarten M-003 is a facility and excluded. Six long bars conflict between length and area and are flagged for review.
- The unit-type library is pending, so all building footprints are sketch-era placeholders. 11 floors is provisional; no floor height, massing, FAR or unit-mix is derived.
- The sketch case publishes the sketch and image-space geometry; the project metric scale, calibration matrix, DWG/DXF and redline/project coordinates remain private. The pilot-local approximate scale is published only inside the handoff publication block.
- Road connectivity is derived from the unified brown+blue mask (5 px closing): 1 component, 309 nodes, 333 edges and 121 junction candidates. The separate-colour 9-component result and the eight nearest-node connectors are rejected; no width/profile/alignment is derived.
- CASE-SKETCH-001-HANDOFF-A is a selected pilot subset. The committed record is a designer authorization, not an object-level geometry review; the pipeline blocks with `HUMAN_OBJECT_REVIEW_REQUIRED`. No pilot DXF/canonical model is currently published, and `EP-R1-SKETCH-001` remains in progress.
- The test-double DXF is local metric only; no DWG/redline/project coordinates are published, and unknown building height and road hierarchy remain unknown. The pilot transform is uniform scale + y-flip, not the six-point homography.
- The autonomous design draft is a schematic proposal, not a construction or permit drawing and not a code-compliance claim. Its unit module is provisional, its road corridors are schematic, its garage layout and driveways are not designed, and its full-site north-south spacing is deferred; only the focus block is checked at 20 m. Green, parking, FAR and road-access claims are honest (M4c-1c/1d/1e): open space is dual-measured (`candidate_open_space_ratio` 63.02% classified / `unbuilt_ratio` 65.35% geometric union) and is not designed green (`designed_green_ratio` 6.54%, the ≥30% designed-green target is deferred); parking capacity is the **assumed nominal** 1,000 against the 2,398-space requirement (capacity and layout deferred), entrance proximity is info only and no driveway is designed (`PARKING_ENTRANCE_PROXIMITY` info / `PARKING_DRIVEWAY_CONNECTION` deferred); the `pass` checks are the 6 independently geometry-verified ones (the 5 focus/topology checks + declared road-access coverage) — FAR is an arithmetic scenario with final verification deferred; all 21 design-basis parameters are unconfirmed assumptions whose authentication is `declarative`, and any `confirmed: true` state requires an `approval_ref`. Road service honesty (M4c-1b/1e): coverage is 1.0 (17/17 groups) through **declared** `serves_group_ids` access relations (17 group-access roads: 16 branch + ACC-G-12; plus BR-FOCUS and the focus loop = 19 connector roads; G-08 → BR-G-08, G-13 → BR-G-13); entrance proximity is 2 of 5 (info only) and no driveway is designed; 24 dead ends are all classified but **not all justified** — 17 justified / 5 unfinished / 2 unclassified (7 unresolved, `DEAD_END_RESOLUTION` deferred); the pre-existing 38.19 m² main-road/building overlap (MAIN-19 34.42 + MAIN-08 3.77) is a deferred machine check (`MAIN_ROAD_BUILDING_OVERLAP`, `known_unresolved`), and full-site road clearance is deferred (`FULL_SITE_ROAD_CLEARANCE`).
- The autonomous draft is `rule_derived` in `proposal_preview`, never `human_confirmed`; the designer may adopt or edit it, but the Agent cannot declare it adopted or officially issued.
- The 4c design candidate is **partial** (full-site north-south spacing deferred; only the focus block is detailed). M4c-0's 5-component road reading was a sub-ULP floating-point noding artefact, corrected in M4c-1a with explicit shared-coordinate junctions; M4c-1b rebaselined the network to 44 design roads — the noded graph is **1 component** (59 nodes / 65 segments, cyclomatic 7, `max_endpoint_gap_m` 0.0) and `ROAD_CONNECTIVITY` checks the noded graph. OSMnx remains an optional source-skeleton preprocessor, not a connectivity proof.
- M4c-0 tested open-source libraries as optional experiment dependencies; no OSMnx/GeoPandas/momepy/Building Regulariser dependency was added to `pyproject.toml`, and no open-source algorithm or foreign design default is claimed as Chinese code compliance.

## 4. Repository layout

```text
.
├── src/
│   ├── dgcad_foundation/      Canonical IR, authority, dependency, audit, gateway
│   ├── dgcad_runtime/         Stateful runtime, proposals, jobs, idempotency, human control plane
│   ├── dgcad_deployment/      SQLite/artifact spike, lifecycle, discovery, pairing, local HTTP
│   ├── dgcad_domain/          Confirmed trace → Building/Road adapters and validators
│   ├── dgcad_analysis/        Synthetic solar/shadow baseline with dependency fingerprint
│   ├── dgcad_cad/             CAD-IR, DXF compiler, readback validator
│   └── dgcad_e2e/             Living end-to-end pipeline orchestration
├── experiments/m4c0/         Open-source reuse experiments A/B/C (optional deps)
├── tests/                     Executable contract suites (334 collected)
├── contracts/                 Machine-readable IR, domain, E2E, lifecycle/auth/MCP/CAD bridge contracts
├── fixtures/                  Typed synthetic fixtures (scene, authority, dependency, domain, E2E)
├── spikes/                    Executed process probe and MCP install-attempt evidence
├── docs/
│   ├── architecture/          Provisional architecture and module boundaries
│   ├── development/           Testing strategy and contribution workflow
│   ├── adr/                   Architecture decision records
│   ├── status.md              Current gate/status matrix
│   └── roadmap.md             Milestones and next actions
├── research/
│   ├── README.md              Provenance and scope of the research archive
│   └── archive/
│       ├── r0-v0.19/          Full R0 research workspace
│       └── r1-deployment-entry-v0.2/  Original R1 deployment snapshot
├── scripts/                   Local test runners
├── pyproject.toml
├── LICENSE                    Apache-2.0
└── README.md
```

The root `src/` and `tests/` are the **living code**. `research/archive/` is historical evidence and may contain outdated paths and status labels.

## 5. Quick start

```bash
git clone https://github.com/ZJW11398925/design-grade-cad-agent.git
cd design-grade-cad-agent

python -m venv .venv
# Windows:
.venv\Scripts\activate
# Linux/macOS:
source .venv/bin/activate

python -m pip install -e ".[dev]"
python -m pytest -q
```

Expected:

```text
334 passed
```

With coverage:

```bash
python -m pytest -q --cov --cov-report=term-missing
```

## 6. Test suites

| Suite | File | Tests | Contract scope |
|---|---|---|---|
| Foundation | `tests/test_foundation_contracts.py` | 21 | identity, revisions, authority, atomic changes, preview isolation, dependency, locks, audit, migration |
| Runtime | `tests/test_runtime_contracts.py` | 22 | proposal lifecycle, approval binding, jobs, idempotency, recovery, stale writer, CLI/MCP parity |
| Deployment | `tests/test_deployment_contracts.py` | 8 | SQLite WAL/CAS, artifact dedup/tamper, service parity, MCP-unverified marking |
| Lifecycle | `tests/test_lifecycle_contracts.py` | 14 | discovery, pairing, roles, sessions, loopback security, lease, bridge expiry |
| Domain | `tests/test_domain_contracts.py` | 26 | confirmed trace, building footprint/height, road class/profile, T-junction, stale, runtime integration |
| Analysis | `tests/test_analysis_contracts.py` | 7 | solar position, confirmed/unknown blockers, context completeness, dependency fingerprint |
| CAD delivery | `tests/test_cad_delivery_contracts.py` | 9 | CAD-IR mapping, DXF compile/readback, mutation detection, bulge/width/LWPOLYLINE semantics |
| E2E-001 | `tests/e2e/test_living_pipeline.py` | 8 | full living pipeline, evidence files, declared unknowns, living-package-only check |
| E2E-002 | `tests/e2e/test_e2e_002_mutations.py` | 6 | height change, node move, north bearing, rebuild worker, manifest comparison, road-surface deferral |
| E2E-003 | `tests/e2e/test_e2e_003_adversarial.py` | 20 | geometry, style, identity, serialization, validator-error checks |
| E2E-003b | `tests/e2e/test_e2e_003b_semantics.py` | 11 | fingerprint consistency, symbol-table case, ring keys, raw/canonical manifest |
| Third-party evidence | `tests/e2e/test_e2e_003c_third_party.py` | 2 | AutoCAD 2024 Core Console round-trip evidence and scope integrity |
| Sketch evidence | `tests/test_sketch_evidence.py` | 11 | image-space trace, sketch-only privacy, designer semantics, five building merges, unit inference/conflicts, 11-floor provisional state, rough centerlines, leak checks |
| Road topology | `tests/test_road_topology.py` | 3 | unified-mask connectivity, 121 junction candidates, rejected nearest-node connectors, node/contract checks |
| Sketch handoff gate | `tests/test_sketch_handoff.py` | 32 | authorization vs geometry review, scope/authority propagation, source integrity, road topology, coordinate metadata and sensitivity, DXF privacy |
| Sketch handoff A | `tests/e2e/test_sketch_handoff_a.py` | 6 | blocked evidence + review packet; test-double Canonical → CAD-IR → DXF (11/11) with scope in trace/canonical/CAD-IR/XDATA/manifest; privacy and scope-mismatch detection |
| Design synthesis | `tests/test_design_synthesis.py` | 9 | basis math (FAR/parking/spacing), full-site input, intent/focus block, row layout, consistency checks, 206-entity DXF, rule-derived draft authority |
| Design topology | `tests/test_design_topology.py` | 14 | noded design-road topology (rebased to the 44-road network in 0.19.0): exact connectivity, explicit shared-vertex junctions, fail-closed negatives (split branch, sub-tolerance gap, snap/round/precision repairs rejected), geometry preservation |
| Road access | `tests/test_road_access.py` | 23 | road access semantics: declared `serves_group_ids` relations (17/17 groups), terminal centreline band [3.4, 3.5] m plus corridor-edge clearance, dead-end classification vs resolution, parking proximity vs driveway, orphan-declaration and terminal-binding negatives |
| Road access generation | `tests/test_road_access_generation.py` | 13 | access-road generation: one declared service relation per group, G-12 4 m clearance-driven access type, overlap budget for new access roads, no building crossing, terminal placement |
| Parking geometry | `tests/test_parking_geometry.py` | 6 | parking geometry honesty: assumed nominal capacity, entrance capacity semantics, layout deferral |
| Design contract | `tests/test_design_contract.py` | 11 | design-synthesis-v0.6 contract ↔ live module sync (basis provenance + declarative authentication, 25-check taxonomy, declared access relations, topology states, connector states, fail-closed families), v0.5/v0.4/v0.3/v0.2/v0.1 superseded, evidence-gate register repointed |
| Design basis | `tests/test_design_basis.py` | 20 | design-basis provenance and semantics: per-parameter authority states, `confirmed: false` invariants, declarative authentication, arithmetic-vs-spatial check labelling |
| Green/parking semantics | `tests/test_green_parking_semantics.py` | 9 | honest green/parking split: candidate open-space vs unbuilt vs designed-green ratios, assumed nominal capacity vs required spaces, entrance capacities, deferred statuses |
| Privacy scan | `tests/test_privacy_scan.py` | 20 | structured DXF privacy scan: hex-digest false-positive elimination, real token detection in TEXT/MTEXT/names/XDATA, committed-evidence clean runs, fail-closed behaviour |
| Open-source reuse | `tests/test_open_source_reuse.py` | 3 | reuse-matrix coverage/verdicts, experiment evidence and DXF privacy, core-dependency minimality |
| **Total** | | **334 (all passing)** | |

Read [docs/development/testing.md](docs/development/testing.md) for what these tests prove, what they do **not** prove, and how new test layers are added.

## 7. Contracts

| File | Purpose |
|---|---|
| `contracts/runtime-state-contract-v0.1.yaml` | Durable runtime state envelope and registry semantics |
| `contracts/runtime-agent-surface-v0.1.yaml` | Agent tool surface; no approval/unlock tool |
| `contracts/deployment-boundary-contract-v0.2.yaml` | Sidecar / bridge / control-plane boundary |
| `contracts/sidecar-lifecycle-contract-v0.1.yaml` | Discovery, pairing, session and lease lifecycle |
| `contracts/local-auth-capability-contract-v0.1.yaml` | Role/capability model for Agent, Human Review, CAD Bridge |
| `contracts/cad-bridge-contract-v0.1.yaml` | External CAD representation authority |
| `contracts/cad-bridge-lifecycle-contract-v0.2.yaml` | Bridge registration, heartbeat, expiry; host execution blockers |
| `contracts/canonical-site-ir-v0.4.yaml` | Living Canonical Site IR promoted from R0 v0.3 |
| `contracts/domain-contract-v0.1.yaml` | Living Building/Road domain contract for domain slice 001 |
| `contracts/cad-ir-v0.1.yaml` | Minimal living CAD-IR for the E2E delivery slice |
| `contracts/e2e-pipeline-v0.1.yaml` | Living E2E-001 stage and invariant contract |
| `contracts/e2e-mutation-v0.1.yaml` | E2E-002 mutation, rebuild and manifest-comparison contract |
| `contracts/e2e-adversarial-v0.1.yaml` | E2E-003 adversarial scenario, category and issue-mapping contract |
| `contracts/third-party-roundtrip-v0.1.yaml` | Third-party CAD evidence and verdict contract |
| `contracts/sketch-evidence-v0.1.yaml` | Sketch-to-trace evidence, review states and publication boundary |
| `contracts/sketch-domain-handoff-v0.2.yaml` | Scope-aware real-sketch handoff, boundary authority, source integrity and road topology (v0.1 superseded) |
| `contracts/design-synthesis-v0.6.yaml` | Autonomous design draft state, basis provenance authentication, 25-check taxonomy, declared group-access service relations, noded road topology, deferred conflict checks, drawing and authority (v0.5/v0.4/v0.3/v0.2/v0.1 superseded) |
| `contracts/evidence-gate-register-v0.2.yaml` | Living R1 evidence gate register; EP-R1-SKETCH-001 in progress |
| `contracts/mcp-binding-v0.3.yaml` | MCP binding candidate; wire-level status remains unexecuted |

The promotion status of every research artifact is tracked in [docs/research-to-product-map.md](docs/research-to-product-map.md). Archive documents are not living contracts.

## 8. Next milestone

**Milestone 3c is partial; Milestone 4 is in progress.** AutoCAD 2024 Core Console round-trip evidence is captured and `DEV-CAD-001..005/007..011` are closed. LibreCAD/FreeCAD/GUI visual QA remain open under #6. `EP-R1-SKETCH-001` remains in progress with CASE-SKETCH-001. **Milestone 4b.1** made the handoff gate scope-aware: the committed designer record is an authorization, not an object-level geometry review, so the pilot blocks with `HUMAN_OBJECT_REVIEW_REQUIRED`. Source integrity, road topology and coordinate-transform semantics are now enforced; the downstream Canonical → CAD-IR → DXF path is proven with an explicitly marked test double, not published as real evidence.

**Milestone 4c** produced the first autonomous schematic design draft; **M4c-1a** (0.16.0) corrected its road-topology defect with explicit shared-coordinate junctions (noded graph: 1 component) and published `design-roads.geojson`; **M4c-1c** (0.17.0) made the design checks honest — per-parameter design-basis provenance (21 parameters, all unconfirmed) and no unverified quantity presented as a pass; **M4c-1d** (0.18.0) tightened the semantics further — pass reserved for independently geometry-verified checks, FAR split into an arithmetic scenario (info) and a deferred final verification, parking capacity named as assumed nominal, open space dual-measured, and provenance authentication declared as `declarative` (a `confirmed: true` state requires an `approval_ref`); **M4c-1b** (0.19.0) made the first design-geometry change — the network grew to **44 design roads** (25 main + 17 branch + 2 access), all 17 groups are served (`ROAD_ACCESS_COVERAGE` pass, coverage 1.0), G-05/G-12 access gaps are closed, dead ends are all classified (17 justified / 5 unfinished / 2 unclassified; 7 unresolved), the DXF is now **206 entities** (readback 206/206), and the topology is rebaselined to 59 nodes / 65 segments / cyclomatic 7 with `max_endpoint_gap_m` still 0.0. Honest residuals: entrance proximity is 2 of 5 with no designed driveway, and a pre-existing 38.19 m² main-road/building overlap (MAIN-19 34.42 + MAIN-08 3.77) is a deferred machine check for M4c-2. **M4c-1e** (0.20.0) bound road access to declared `serves_group_ids` relations (each of the 17 groups has exactly one declared connector; G-08/G-13 return to BR-G-08/BR-G-13; terminal centreline band [3.4, 3.5] m with corridor-edge clearance recorded separately), made the main-road overlap a deferred machine check (`MAIN_ROAD_BUILDING_OVERLAP`) and added `FULL_SITE_ROAD_CLEARANCE` deferred, split parking proximity from driveway design, and kept design geometry unchanged — 25 checks = 6 pass + 10 info + 9 deferred; DXF content remains 206 entities (its byte SHA differs per save because of ezdxf GUIDs).

**Next:** multi-candidate generation with independent design-quality evaluation; then full-site expansion with basis confirmation (and the MAIN-19/08 main-road alignment plus full-site road clearance in M4c-2). Remaining evidence gaps: the designer's object-level review, full-case fidelity metrics, the unit-type library, six unit-count conflicts, the 121-junction review and the 5 px closing kernel, road width/profile/alignment, 支路/入户路 separation, a real CAD host round-trip for the 206-entity DXF, and the authority-declaration hardening that must precede autonomous canonical writes.

See [docs/roadmap.md](docs/roadmap.md) for the milestone plan and exit criteria.

## 9. Research provenance

This repository consolidates two research deliverables:

- **R0 v0.19** — research workspace covering `COV-01..23`, five acquisition batches, local synthetic benchmarks, E2E synthetic vertical slice and the provisional architecture.
- **R1 deployment-entry v0.2** — the executable Foundation + Runtime + Deployment + Lifecycle prototype (65 tests).

The vendored copy of the private research-methodology skill is intentionally **not** published; only its version is recorded in [research/README.md](research/README.md).

## 10. Contributing

Tests come first. Any contract change requires the contract YAML, the executable test and `CHANGELOG.md` to change together. Research claims stay in `research/`; code claims stay in tests.

- [CONTRIBUTING.md](CONTRIBUTING.md)
- [SECURITY.md](SECURITY.md)
- [docs/development/workflow.md](docs/development/workflow.md)

## 11. License

Apache-2.0. See [LICENSE](LICENSE).

---

## 中文简介

**Design-Grade CAD Agent（DGCAD）** 是一个以研究为先导的开源工作区，目标是建立一条可追溯的 **草图 → 专业场地模型 → CAD/BIM** 转换链。

当前仓库整合了 R0 v0.19 研究证据、R1 部署生命周期原型、Domain Slice 001、E2E-001 纵向链路、E2E-002 mutation/rebuild 与 E2E-003 对抗性交付回归：根目录 `src/`、`tests/` 是可执行的正式代码，`research/archive/` 保存历史研究快照。全部测试通过（当前 334，见 §6），无长期 xfail。

项目坚持四条底线：原始 Source/Trace 不可覆盖；Agent 只能提议、不能写入 confirmed 设计真值；DXF/IFC 只是派生表示；未知状态必须显式保留。真实草图、真实设计院 Profile、IFC round-trip、独立日照引擎与真实 AutoCAD/FreeCAD 宿主接入仍是明确的证据缺口，仓库不会把合成测试包装成生产能力。

E2E-001/002/003 已打通：DOMAIN-SLICE-001 → Runtime canonical → massing → 合成 shadow → CAD-IR → DXF → readback manifest，验证了高度/节点/北向的 scoped stale 与真实 rebuild。Milestone 3a 把 15 个 strict xfail 全部转为正向检查；3b 完成指纹/依赖键一致性、符号表大小写、稳定环身份、raw/canonical 回读证据；3c 已用 AutoCAD 2024 Core Console 完成真实第三方 round-trip，判定 semantic_pass_with_serialization_differences。LibreCAD/FreeCAD/GUI QA 仍未执行。此后 Milestone 4 持续推进：4a 引入真实设计师草图取证（CASE-SKETCH-001）与统一路网拓扑（309 节点 / 333 边 / 121 个待复核 junction 候选）；4b.1 让真实草图移交门具备作用域感知，pilot 在设计师对象级几何复核前保持 blocked；4c 产出首个自主标准化设计草案（focus G-01，`rule_derived` 草案，非 human_confirmed），M4c-0 完成开源设计能力复用 sprint；M4c-1a（v0.16.0）已修正 4c 道路图的浮点 noding 缺陷：设计路网携带显式共享坐标 junction，noded 图 1 连通分量（51 节点 / 55 段，max endpoint gap 0.0 m），证据已重生成并发布 design-roads.geojson。M4c-1c（v0.17.0）把证据语义改诚实：检查分 pass / info / deferred（info 与 deferred 都不是 pass），open_space_ratio 63.0% 是开敞空间而非已设计绿地（designed green 6.54%，deferred），停车 recorded capacity 1,000 / 要求 2,398（capacity/layout deferred），21 项 design-basis 参数全部 confirmed:false，Agent 不能自确认。M4c-1d（v0.18.0）进一步收紧：pass 仅保留 5 项独立几何验证检查（v0.18.0 时点：18 项 = 5 项 pass + 8 info + 5 deferred），FAR 拆为算术情景（info）与最终验证（deferred），停车容量命名为 assumed nominal capacity，开敞空间双口径（candidate 63.0% 分类面积和 / unbuilt 65.3% 几何并集），provenance 认证为 declarative——任何 confirmed:true 状态都需要 approval_ref。M4c-1b（v0.19.0）完成首次设计几何变更：路网增至 44 条设计道路（25 主 + 17 支 + 2 入户），17/17 组全部通达（ROAD_ACCESS_COVERAGE pass），G-05/G-12 接入缺口关闭，24 个死端全部分类（17 justified / 5 unfinished / 2 unclassified），DXF 变为 206 实体（readback 206/206），拓扑重基线为 59 节点 / 65 段 / cyclomatic 7（max endpoint gap 仍为 0.0）。诚实残余：5 个车库入口仅 2 个与设计道路邻近（proximity，info），无引道设计（driveway deferred）；既有主路-建筑重叠 38.19 m²（MAIN-19 34.42 + MAIN-08 3.77）为已知未解决冲突，留待 M4c-2。M4c-1e（v0.20.0）把道路接入证据改为**声明式** `serves_group_ids` 关系（17 组各 1 条：16 支 + ACC-G-12；另有 BR-FOCUS 与 focus loop，共 19 条 connector 路），G-08/G-13 回到自有 BR-G-08/BR-G-13，terminal 中心线带 [3.4, 3.5] m 并单列 corridor-edge clearance（7 m 支路 0.0、4 m 入户路 1.5）；死端 24 个全部分类但并非全部 justified（17 justified / 5 unfinished / 2 unclassified，7 unresolved，`DEAD_END_RESOLUTION` deferred）；主路重叠改为机器检查 `MAIN_ROAD_BUILDING_OVERLAP` deferred，全场地道路退距 `FULL_SITE_ROAD_CLEARANCE` deferred；25 项检查 = 6 pass + 10 info + 9 deferred，测试 334，DXF 内容仍 206 实体（字节 SHA 每次保存会变，仅内容未变）。
