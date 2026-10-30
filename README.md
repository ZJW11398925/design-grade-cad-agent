# Design-Grade CAD Agent (DGCAD)

[![CI](https://github.com/ZJW11398925/design-grade-cad-agent/actions/workflows/ci.yml/badge.svg)](https://github.com/ZJW11398925/design-grade-cad-agent/actions/workflows/ci.yml)

**A traceable research-and-development workspace for turning hand-drawn site sketches into professional, verifiable site models and editable CAD/BIM output.**

> **Status: research prototype (v0.27.0).** This is not production CAD software, not a compliance certification, and not a validated AutoCAD/FreeCAD integration. Claims are scoped to the tests and evidence recorded in this repository.

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
| Autonomous design synthesis | **partial draft implemented**, 9 tests | [CASE-SKETCH-001 design synthesis](docs/e2e/design-synthesis-001/README.md): full-site context + focus block G-01; 7 standardized buildings / 16 units in 20 m rows; FAR 1.565 = arithmetic scenario (`FAR_ARITHMETIC_SCENARIO` info; final verification deferred); parking entrance count info (assumed nominal capacity 1,000 vs 2,398 required — capacity/layout deferred); open space dual-measured (candidate 61.64% classified / unbuilt 64.07% geometric union — neither is designed green, designed green 6.54% deferred); **211-entity** editable DXF (content changed in M4c-2; the byte SHA changes per save because of ezdxf GUIDs); `rule_derived` draft, not human-confirmed. M4c-1b made the first design-geometry change: **44 design roads** (25 main + 17 branch + 2 access), road access coverage **1.0 (17/17 groups)**; M4c-1e (0.20.0) bound that evidence to **declared** `serves_group_ids` access relations (17 group-access roads: 16 branch + ACC-G-12; plus BR-FOCUS and the focus loop = 19 connector roads), so each group is served by its own road (G-08 → BR-G-08, G-13 → BR-G-13) instead of the nearest endpoint. Dead ends: 19 remain = 17 planned group terminals + 2 site-edge termini; the 7 previously unresolved dead ends are resolved by 2 trims, 3 bridges and 2 site-edge termini (`DEAD_END_RESOLUTION` pass, 0 unresolved); parking is proximity-only (`PARKING_ENTRANCE_PROXIMITY` info; driveway `PARKING_DRIVEWAY_CONNECTION` deferred). M4c-2 (0.21.0) removed the known main-road/building overlap by recorded alignment (`MAIN_ROAD_BUILDING_OVERLAP` pass; 38.1907 before; MAIN-19 diversion 66.235 m) with site-boundary containment as a Phase-0 hard check (`ROAD_BOUNDARY_CONTAINMENT` pass; margin 0.6735131264650868; 3 repairs MAIN-08/16/18). Phase 0 in 0.22.0 corrected the evidence: alignment semantics are `local_search_exhausted` (the 11.565 m gap only proves the between-buildings passage infeasible; the 66.235 m diversion is a candidate baseline, not a proof of optimality); the geojson overlap fields are split — `main_before` 38.19068149970835, `main_after` 0.0, `new_access` 0.9943558185246757, `total_after` 0.9943558185246756 (after the MAIN-08 boundary repair the remaining main conflict was 34.421783197612406 → 0) — plus `source_segment_map` (25 roads), `main_boundary_repairs` and design-diff alignment/dead-end records; preview/overlay are regenerated. M4c-3 (0.22.0) runs the first **multi-candidate experiment** (A/B1/B2/C on the MAIN-19 conflict; independent hard-gate evaluation; default preference recommends B1, road-first recommends A; no single score); M4c-3a (0.23.0) fixed candidate-evaluation integrity (all-44-road class/terminal evidence, basis binding, 11 single-unit objectives); **M4d** (0.24.1) regenerated the focus evidence under `design-synthesis-v0.9`: **29 checks = 9 pass + 11 info + 9 deferred (+3 DXF = 32)**, with `DESIGNED_GREEN_RATIO` **deferred** (designed green 6.54% <30%; the 61.46% account is `POTENTIAL OPEN SPACE ... NOT LANDSCAPE DESIGN`, auxiliary only) and the four `FULL_SITE_*` checks **deferred** on the focus sheet; tests 571. |
| Multi-candidate design experiment | **first experiment implemented**, 54 tests | [M4c-3/M4c-3a candidates](docs/e2e/design-candidates-001/README.md): four deterministic candidates A (road priority), B1 (building priority, M4c-2 diversion), B2 (alternate fold) and C (coordinated, G-08 branch re-route) for the MAIN-19 conflict. Candidate evidence compares **all 44 roads** by class — A: main 2.320 / branch 2.826 (BR-G-08) / access 0 and G-08 terminal 2.826 m; B1: main 66.235 / branch 7.352 (BR-G-09 follows) / terminal 0; B2: main 71.772 / branch 13.645 / terminal 0; C: main 11.994 / branch 76.700 (BR-G-08) / G-08 terminal 75.315 — every candidate is bound to basis `design-assumption-v0.2` by fingerprint. Hard gates (main-road overlap ≤0.01 m²; total road/building overlap ≤ boundary-safe reference 0.86–0.99 m²) are recomputed from geometry; comparison uses **11 single-unit objectives**, auxiliary metrics never enter Pareto/preferences, no composite score. Default preference recommends **B1**, road-first recommends **A**; Pareto [B1,B2,C,A]; candidate DXF path via `scripts/design/run_candidate_synthesis.py` — B1 is a current, boundary-compliant candidate (margin 0.6735), not the historical pre-repair form |
| Full-site design expansion | **research draft, partial**, 58 tests | [M4d full-site](docs/e2e/design-synthesis-full-site-001/README.md): all **55 buildings / 109 units / 2,398 households** in **18 rows / 8 superblocks (36 row records)** against the frozen 44-road network, focus G-01 preserved; source→design displacement sum **2,328.95 m**, max **147.25 m**, mean **42.34 m**; boundary/overlap/NS/clearance pass (`FULL_SITE_NS_SPACING` min 19.999999999999943 m is the **candidate row-rhythm + basis assumption**, not a universal code rule; over-spacing counts as a rhythm violation); `DESIGNED_GREEN_RATIO` **deferred** (designed green **15.93%** <30%); the 61.06% tiled account is **`POTENTIAL OPEN SPACE ... NOT LANDSCAPE DESIGN`** (layer `L-OPEN-SPACE`, auxiliary only). Fail: access 0.0/17, dead 17. Checks **11 pass + 11 info + 5 deferred + 2 fail**; CAD title embeds `DESIGNED GREEN 15.93% - INCOMPLETE` and `INCOMPLETE: ROAD ACCESS 0/17 - DEAD ENDS 17 UNRESOLVED - DESIGNED GREEN < 30%`. Full-site DXF **553 entities**, readback **553/553**, XDATA 11, privacy pass; the focus sheet remains canonical. 3.016362 m / 19.999999999999943 m are model-coordinate internal consistency under approximate sketch registration, not survey-grade engineering clearances. |
| Building-road co-design A/B | **research draft**, 43 tests | [M4d-2 co-design](docs/e2e/design-co-design-001/README.md): same CASE-SKETCH-001 input/basis and frozen 44-road network. **A** = fixed M4d-1 layout + rebuilt 17-connector access (16 branch + 1 access, 362.095 m, coverage 1.0/relation 0/dead 0); fails **only** `FULL_SITE_ROAD_CLEARANCE` (**2.8250521190593507 m < 3 m**, served-facade corridor conflict, not tolerance-widened). **B** = group-preserving layout (17 groups / 39 rows, 55 buildings) + same rebuilt access: **hard-valid 29 = 13 pass + 11 info + 5 deferred + 0 fail**; access 17/17, terminal band 3.499999 m, boundary/overlap/NS 20.0/clearance **3.0164672267820585 m**, dead ends 0; group splits **12**, group-centroid displacement max **140.12 m**/mean **33.99 m**, single-building max **278.46 m** (honest disclosure). **Hard-first decision: B recommended, A excluded**; objective metric table only, **no single score/ranking**. Candidate DXF delivered: **A 584 entities/readback 584/584, B 587/587**, XDATA 11, privacy pass, audit 0/0; A sheet stamped **INCOMPLETE**, B sheet **HARD-VALID**; `comparison.svg` three panels; connector sidewalks clipped along footprints (17 / 115.202 m²), **A/B sidewalk overlap 0**. Research draft, not professional design/compliance; CAD host unverified. |
| Design-intent audit (M4d-2a) | **descriptive audit, no gate**, 41 tests | [M4d-2a audit](docs/e2e/design-intent-audit-001/README.md): 17 groups are **inferred** (45.0 m + 8.0 m main buffer + Union-Find single linkage; G-01 has 9 inferred members vs 7 in focus, chain max 209.738 m; provenance **not_designer_confirmed**). Group quality: B non-contiguous **12/17**, runs **43**, max row gap 12, displacement mean 47.92 / P90 102.83 / max 278.46; A/baseline 10/17, max 147.25. Corrected source-green table: building-occupied **845.541 / 845.541 / 713.445 m²**, road-occupied **64.113 / 320.949 / 73.815 m²**, retained **10,076.757 (91.72%) / 9,819.92 (89.38%) / 10,199.151 (92.83%)**, preserved/shrunk/cancelled **7/5/0** (no whole cancellation; area ≠ intent). Access layers: **L1 17/17 / L2 0/17 / L3 26/55 / L4 0 driveway** (baseline/A/B L3 15/24/26; no combined coverage). Robustness: 0.1 m independent perturbation leaves **100% samples <3.0 m** (B min 2.8887; common datum unchanged; 3.0 rule not changed; engineering robustness not established). Four-level B status: **geometric pass / intent descriptive / deferred 5 / host not_verified**. No score/ranking/gate; B remains a research baseline, not a professional design. |
| Candidate C (M4d-2b) | **negative result, not promoted**, 15 tests | [M4d-2b candidate C](docs/e2e/design-candidate-c-001/README.md): bounded **generate-and-test** (not joint optimisation) with 20 deterministic group-order variants + full rebuilt access + 29 checks; **5 hard-valid** (default/focus_first_y_asc/y_asc_swap01 same as B; `y_asc_swap12` 41 runs vs 43 but mean 59.02 vs 47.92 m and road 316.08 vs 189.06 m; `y_asc_rotate1` 46 runs/293.42 m max/445.50 m road); 13 fail NS/clearance, 2 layout errors. Bounded local repair **8 proposals / 0 accepted** (7 no feasible, 1 no strict improvement). Decision **`no_improvement_same_as_b`**, `same_as_b = true`, hard-ok 29 = 13/11/5/0, deltas all 0 (fragmented 12, runs 43, displacement max 278.46/mean 47.92, centroid max 140.12, road 189.06); inherited green/access unchanged. **C not promoted and no C DXF**; B remains the only hard-valid baseline, still not a professional design (5 deferred, host not verified, 26/55 frontage, no internal roads/driveway). Negative result: next is M4d-2c (local road re-align/main-road adjustment/stronger optimizer), not relaxing thresholds. |
| Open-source design reuse | **sprint complete; partial answer**, 3 tests | [M4c-0](docs/e2e/open-source-reuse-001/README.md): Building Regulariser, OSMnx, PyGeoOps, Clothoids, momepy tested on CASE-SKETCH-001; OSMnx consolidation 309/333→117/141 with 1 component; Building Regulariser limited; PyGeoOps per-area; Clothoids single fit fails; momepy evaluation only; no new core dependencies |
| Road network topology | **connected_by_unified_road_mask**, 3 tests | 1 connected design network: 309 nodes / 333 edges / 121 junction candidates; colour is a class attribute; no width/profile/alignment |
| R0 research | archived | 5 acquisition batches, synthetic benchmarks, adversarial reviews, architecture challenge |
| Real-world evidence | **partially obtained** | one designer sketch intake (CASE-SKETCH-001); still missing a field-paired case, real design-office profile, IFC round-trip, independent solar engine, AutoCAD/FreeCAD host exchange, MCP wire conformance |

**Verified test baseline: 571 passed (571 collected)** (`python -m pytest -q`).

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
- The autonomous design draft is a schematic proposal, not a construction or permit drawing and not a code-compliance claim. Its unit module is provisional, its road corridors are schematic, its garage layout and driveways are not designed; the full-site experiment checks N-S spacing (min 19.999999999999943 m) but fails access/dead-end checks, so the focus sheet remains canonical. Green, parking, FAR and road-access claims are honest (M4c-1c/1d/1e): open space is dual-measured (`candidate_open_space_ratio` 61.64% classified / `unbuilt_ratio` 64.07% geometric union) and is not designed green (`designed_green_ratio` 6.54%, the ≥30% designed-green target is deferred); parking capacity is the **assumed nominal** 1,000 against the 2,398-space requirement (capacity and layout deferred), entrance proximity is info only and no driveway is designed (`PARKING_ENTRANCE_PROXIMITY` info / `PARKING_DRIVEWAY_CONNECTION` deferred); the `pass` checks are the 9 independently geometry-verified ones (5 focus/topology + declared road-access coverage + site-boundary containment + resolved main-road overlap + dead-end resolution) — FAR is an arithmetic scenario with final verification deferred; all 21 design-basis parameters are unconfirmed assumptions whose authentication is `declarative`, and any `confirmed: true` state requires an `approval_ref`. Road service honesty (M4c-1b/1e): coverage is 1.0 (17/17 groups) through **declared** `serves_group_ids` access relations (17 group-access roads: 16 branch + ACC-G-12; plus BR-FOCUS and the focus loop = 19 connector roads; G-08 → BR-G-08, G-13 → BR-G-13); entrance proximity is 2 of 5 (info only) and no driveway is designed; 19 dead ends remain (17 planned group terminals + 2 site-edge termini) — the 7 previously unresolved dead ends are resolved (`DEAD_END_RESOLUTION` pass, 0 unresolved; 2 trimmed, 3 bridged, 2 site-edge); the main-road/building conflicts (`main_before` 38.19068149970835, including MAIN-19 34.42 + MAIN-08 3.77; after the MAIN-08 boundary repair the remaining main conflict was 34.421783197612406 → 0) are resolved (`MAIN_ROAD_BUILDING_OVERLAP` pass, `main_after` 0.0; `ROAD_ALIGNMENT_EVIDENCE` info), site-boundary containment is a hard check (`ROAD_BOUNDARY_CONTAINMENT` pass; margin 0.6735131264650868; MAIN-08/16/18 repairs) — the claim is zero remaining known overlap and boundary containment, not a 3.0 m clearance for all main roads (unadjusted minimum ≈1.229 m); full-site road clearance is deferred (`FULL_SITE_ROAD_CLEARANCE`).
- The autonomous draft is `rule_derived` in `proposal_preview`, never `human_confirmed`; the designer may adopt or edit it, but the Agent cannot declare it adopted or officially issued.
- The design is **partial**: the focus block is detailed and canonical; the full-site sheet is a research draft whose access coverage/dead-end checks fail (see §8). M4c-0's 5-component road reading was a sub-ULP floating-point noding artefact, corrected in M4c-1a with explicit shared-coordinate junctions; M4c-1b rebaselined the network to 44 design roads, M4c-2 aligned the main road and resolved the dead ends, and Phase 0 (0.22.0) repaired boundary overhangs — the noded graph is **1 component** (58 nodes / 68 segments, cyclomatic 11, 19 dead ends, 36 junctions, `max_endpoint_gap_m` 0.0) and `ROAD_CONNECTIVITY` checks the noded graph. OSMnx remains an optional source-skeleton preprocessor, not a connectivity proof.
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
├── tests/                     Executable contract suites (571 collected)
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
571 passed
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
| Design synthesis | `tests/test_design_synthesis.py` | 9 | basis math (FAR/parking/spacing), full-site input, intent/focus block, row layout, 27 consistency checks, 211-entity DXF, rule-derived draft authority |
| Design topology | `tests/test_design_topology.py` | 14 | noded design-road topology (rebased to the 44-road network in 0.19.0): exact connectivity, explicit shared-vertex junctions, fail-closed negatives (split branch, sub-tolerance gap, snap/round/precision repairs rejected), geometry preservation |
| Road access | `tests/test_road_access.py` | 33 | road access semantics: declared `serves_group_ids` relations (17/17 groups), terminal centreline band [3.4, 3.5] m plus corridor-edge clearance, dead-end classification/resolution, parking proximity vs driveway, re-attachment to the aligned main roads, orphan-declaration and terminal-binding negatives |
| Road access generation | `tests/test_road_access_generation.py` | 13 | access-road generation: one declared service relation per group, G-12 4 m clearance-driven access type, overlap budget for new access roads, no building crossing, terminal placement |
| Main alignment | `tests/test_main_alignment.py` | 11 | main-road alignment, site-boundary containment and dead-end resolution: MAIN-19 diversion with `local_search_exhausted` semantics, MAIN-08/16/18 boundary repairs, overlap field split, boundary margin 0.6735, +45 vertices with ids preserved, 7 dead ends trimmed/bridged/site-edge, access relations unchanged |
| Candidates | `tests/test_candidates.py` | 17 | four deterministic candidate strategies, boundary-safe reference, all-44-road geometry change (`class_max_deviation`, per-road change records, per-group terminal deltas), basis binding and negative cases, historical boundary archive, source_segment_map |
| Evaluation | `tests/test_evaluation.py` | 27 | hard gates recomputed from geometry, basis fingerprint fail-closed, 11 single-unit objectives with no composite score, auxiliary metrics excluded from Pareto/preferences, two preference decisions and per-candidate reasons, determinism |
| Visuals | `tests/test_visuals.py` | 13 | SVG plan/overlay generation, candidate comparison grid, deterministic output, matplotlib-optional PNG degradation, candidate DXF CLI dry-run |
| Parking geometry | `tests/test_parking_geometry.py` | 6 | parking geometry honesty: assumed nominal capacity, entrance capacity semantics, layout deferral |
| Design contract | `tests/test_design_contract.py` | 13 | design-synthesis-v0.9 contract ↔ live module sync (basis provenance + declarative authentication, 29-check taxonomy including `ROAD_BOUNDARY_CONTAINMENT` and `FULL_SITE_*`, declared access relations, main-road alignment/boundary/full-site evidence, topology states, connector states, fail-closed families), v0.8/v0.7/v0.6/v0.5/v0.4/v0.3/v0.2/v0.1 superseded, `design-candidates-v0.2` and evidence-gate register synced |
| Design basis | `tests/test_design_basis.py` | 20 | design-basis provenance and semantics: per-parameter authority states, `confirmed: false` invariants, declarative authentication, arithmetic-vs-spatial check labelling |
| Green/parking semantics | `tests/test_green_parking_semantics.py` | 9 | honest green/parking split: candidate open-space vs unbuilt vs designed-green ratios, assumed nominal capacity vs required spaces, entrance capacities, deferred statuses |
| Privacy scan | `tests/test_privacy_scan.py` | 20 | structured DXF privacy scan: hex-digest false-positive elimination, real token detection in TEXT/MTEXT/names/XDATA, committed-evidence clean runs, fail-closed behaviour |
| Open-source reuse | `tests/test_open_source_reuse.py` | 3 | reuse-matrix coverage/verdicts, experiment evidence and DXF privacy, core-dependency minimality |
| Full-site layout | `tests/test_full_site_layout.py` | 16 | 55-building full-site layout: units/households conserved, focus G-01 preserved, 18 rows / 8 superblocks (36 row records), displacement statistics, boundary/side/no-overlap/spacing checks, determinism |
| Full-site constraints | `tests/test_full_site_constraints.py` | 29 | `FULL_SITE_*` checks against the v0.9 contract: boundary setback, building overlap, N-S spacing, road clearance, designed-green ratio and potential-open-space semantics; completeness requires the exact 55-building id set; negative cases cannot be turned into pass by widening tolerance |
| Full-site evidence | `tests/test_full_site_evidence.py` | 13 | full-site DXF **553** entities with 55 buildings, readback 553/553, XDATA 11, privacy, deterministic rendering, `L-OPEN-SPACE`/`POTENTIAL OPEN SPACE ... NOT LANDSCAPE DESIGN` labels and incomplete title semantics |
| Co-design access | `tests/test_co_design_access.py` | 11 | rebuilt 17-connector access (16 branch + 1 access; 362.095 m), coverage 17/17, relation/dead-end negatives, old focus-era declarations never reused, connector-sidewalk clipping |
| Group-preserving layout | `tests/test_group_preserving_layout.py` | 10 | group-preserving B layout: 17 groups / 39 rows / 55 buildings, group membership preserved, split detection |
| Group metrics | `tests/test_group_metrics.py` | 11 | group centroid/relative-position metrics, split counts, access-truth cross-check, hard-first A/B comparison with no score/ranking |
| Co-design evidence | `tests/test_co_design_evidence.py` | 11 | A/B candidates.json/evaluation.json, per-candidate 29-check consistency, baseline/A/B decision, delivered A/B DXF (584/587, readback, XDATA, privacy) and comparison.svg |
| Intent metrics | `tests/test_intent_metrics.py` | 14 | inferred 17 groups (45 m + 8 m main buffer + Union-Find), group centrality/fragmentation, building displacement P90/max, descriptive not gate |
| Green retention | `tests/test_green_retention.py` | 8 | corrected source-green table: retained 10,076.757/9,819.92/10,199.151 m²; building-occupied 845.541/845.541/713.445 m²; road-occupied 64.113/320.949/73.815 m²; preserved/shrunk/cancelled 7/5/0; no whole cancellation |
| Access semantics | `tests/test_access_semantics.py` | 9 | L1 group access 17/17 (baseline 0/17), L2 internal roads not designed (0/17), L3 frontage 15/24/26 of 55, L4 5 entrances/2 proximity/0 driveway; no combined coverage |
| Intent robustness | `tests/test_intent_robustness.py` | 4 | 0.1 m independent perturbation → 100% samples below 3.0 m (B min 2.8887); common-datum control unchanged; 3.0 threshold not changed |
| Audit evidence | `tests/test_intent_audit_evidence.py` | 6 | `docs/e2e/design-intent-audit-001/` artifacts, four-level status, no-score/no-ranking and historical-evidence preservation |
| Candidate C | `tests/test_candidate_c.py` | 11 | bounded generate-and-test C: 20 deterministic group-order variants, 5 hard-valid, bounded local repair 8 proposals/0 accepted, lexicographic hard-first selection, `same_as_b = true`, no C DXF |
| Candidate C evidence | `tests/test_candidate_c_evidence.py` | 4 | `candidate-c.json` decision/variant table, A/B/C paths, inherited green/access values, no-promotion and negative-result non-claims |
| **Total** | | **571 (all passing)** | |

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
| `contracts/design-synthesis-v0.9.yaml` | Autonomous design draft state, basis provenance authentication, 29-check taxonomy (including site-boundary containment, full-site `FULL_SITE_*` checks and designed-green ratio), declared group-access service relations, main-road alignment/boundary/full-site evidence, dead-end resolution, noded road topology, drawing and authority (v0.8/v0.7/v0.6/v0.5/v0.4/v0.3/v0.2/v0.1 superseded) |
| `contracts/design-candidates-v0.2.yaml` | Multi-candidate declaration with mandatory `parent_basis_id` + canonical `basis_fingerprint`, all-44-road geometry-change evidence, `HISTORICAL_BOUNDARY_ARCHIVE` separated from current candidates, geometry-recomputed hard gates, 11 independent single-unit objectives with auxiliary diagnostics excluded from Pareto/preferences, two explicit preference orders and per-candidate reasons (v0.1 superseded) |
| `contracts/evidence-gate-register-v0.2.yaml` | Living R1 evidence gate register; EP-R1-SKETCH-001 in progress |
| `contracts/mcp-binding-v0.3.yaml` | MCP binding candidate; wire-level status remains unexecuted |

The promotion status of every research artifact is tracked in [docs/research-to-product-map.md](docs/research-to-product-map.md). Archive documents are not living contracts.

## 8. Next milestone

**Milestone 3c is partial; Milestone 4 is in progress.** AutoCAD 2024 Core Console round-trip evidence is captured and `DEV-CAD-001..005/007..011` are closed. LibreCAD/FreeCAD/GUI visual QA remain open under #6. `EP-R1-SKETCH-001` remains in progress with CASE-SKETCH-001. **Milestone 4b.1** made the handoff gate scope-aware: the committed designer record is an authorization, not an object-level geometry review, so the pilot blocks with `HUMAN_OBJECT_REVIEW_REQUIRED`. Source integrity, road topology and coordinate-transform semantics are now enforced; the downstream Canonical → CAD-IR → DXF path is proven with an explicitly marked test double, not published as real evidence.

**Milestone 4c** produced the first autonomous schematic design draft; **M4c-1a** (0.16.0) corrected its road-topology defect with explicit shared-coordinate junctions (noded graph: 1 component) and published `design-roads.geojson`; **M4c-1c** (0.17.0) made the design checks honest — per-parameter design-basis provenance (21 parameters, all unconfirmed) and no unverified quantity presented as a pass; **M4c-1d** (0.18.0) tightened the semantics further — pass reserved for independently geometry-verified checks, FAR split into an arithmetic scenario (info) and a deferred final verification, parking capacity named as assumed nominal, open space dual-measured, and provenance authentication declared as `declarative` (a `confirmed: true` state requires an `approval_ref`); **M4c-1b** (0.19.0) made the first design-geometry change — the network grew to **44 design roads** (25 main + 17 branch + 2 access), all 17 groups are served (`ROAD_ACCESS_COVERAGE` pass, coverage 1.0), G-05/G-12 access gaps are closed, dead ends are all classified (17 justified / 5 unfinished / 2 unclassified; 7 unresolved), the DXF is now **206 entities** (readback 206/206), and the topology is rebaselined to 59 nodes / 65 segments / cyclomatic 7 with `max_endpoint_gap_m` still 0.0. Honest residuals: entrance proximity is 2 of 5 with no designed driveway, and a pre-existing 38.19 m² main-road/building overlap (MAIN-19 34.42 + MAIN-08 3.77) is a deferred machine check for M4c-2. **M4c-1e** (0.20.0) bound road access to declared `serves_group_ids` relations (each of the 17 groups has exactly one declared connector; G-08/G-13 return to BR-G-08/BR-G-13; terminal centreline band [3.4, 3.5] m with corridor-edge clearance recorded separately), made the main-road overlap a deferred machine check (`MAIN_ROAD_BUILDING_OVERLAP`) and added `FULL_SITE_ROAD_CLEARANCE` deferred, split parking proximity from driveway design, and kept design geometry unchanged — 25 checks = 6 pass + 10 info + 9 deferred; DXF content remains 206 entities (its byte SHA differs per save because of ezdxf GUIDs). **M4c-2** (0.21.0) removed the known main-road/building overlap by a recorded MAIN-19 diversion and dead-end/boundary repairs. **Phase 0** (0.22.0) corrected that evidence: the alignment semantics are **`local_search_exhausted`** — the 11.565 m gap only proves the between-buildings passage infeasible, and the 66.235 m diversion is a candidate baseline, not a proof of optimality; site-boundary containment is now a hard check (`ROAD_BOUNDARY_CONTAINMENT` pass, margin 0.6735131264650868, repairs MAIN-08/16/18); the geojson overlap fields are split (`main_before` 38.19068149970835, `main_after` 0.0, `new_access` 0.9943558185246757, `total_after` 0.9943558185246756; after the MAIN-08 boundary repair the remaining main conflict was 34.421783197612406 → 0); `design-diff.json` records alignment/dead-end changes, `source_segment_map` covers 25 roads, dead-end `resolved` is bound to `criterion_met` plus a geometry re-check, and preview/overlay visuals are regenerated by `scripts/design/render_visuals.py`. Geometry: 44 roads (25/17/2), 58 nodes / 68 edges / cyclomatic 11, 19 dead ends, 36 junctions (24 explicit), 3 rings, gap 0.0; main length 2,107.733378663747 m; road area 26,882.20505326313 m²; sidewalk 9,764.76834535878 m²; DXF content 211 entities (audit 0/0, readback 211/211, XDATA 11); then-current 27 checks = 9 pass + 11 info + 7 deferred (+3 DXF = 30); then-current 396 tests. **M4c-3** (0.22.0) ran the first multi-candidate experiment (A/B1/B2/C); **M4c-3a** (0.23.0) completed the evaluation integrity: candidate evidence now compares **all 44 roads by class** (A main 2.320 / branch 2.826 / access 0, G-08 terminal 2.826 m; B1 main 66.235 / branch 7.352 / terminal 0; B2 main 71.772 / branch 13.645 / terminal 0; C main 11.994 / branch 76.700 / G-08 terminal 75.315 m — C is **not** a small local change), every candidate carries `parent_basis_id = design-assumption-v0.2` and canonical fingerprint `2a2d7807…` (missing/mismatch fails `basis_ok`), `HISTORICAL_BOUNDARY_ARCHIVE` separates the MAIN-19 66.235 m diversion and MAIN-08/16/18 repairs from current candidates (current B1 is boundary-compliant, margin 0.6735), the comparison uses **11 single-unit objectives** with auxiliary diagnostics excluded from Pareto/preference and no composite score, the default preference recommends **B1** and road-first recommends **A** with Pareto [B1,B2,C,A], and tests are 414. B1 is only a candidate baseline. The full site, garage geometry, road profiles, daylight and code compliance remain out of scope.

**M4d** (0.24.1) extended the design to the **full site**: all 55 buildings / 109 units / 2,398 households are placed in 18 rows / 8 superblocks (36 row records) against the frozen 44-road network, keeping focus G-01; source→design displacement sum is 2,328.95 m (max 147.25 m, mean 42.34 m). The full-site experiment passes boundary setback, pairwise overlap, N-S spacing (min 19.999999999999943 m) and road clearance (min 3.0163622902759215 m); the 20 m spacing is the **candidate row-rhythm rule + design-basis assumption**, not a regulatory/universal constraint. `DESIGNED_GREEN_RATIO` is **deferred** (designed green **15.93%** <30%); the 61.06% account is `POTENTIAL OPEN SPACE ... NOT LANDSCAPE DESIGN` on layer `L-OPEN-SPACE` (auxiliary only, not designed green), and the title block says `DESIGNED GREEN 15.93% - INCOMPLETE` / `INCOMPLETE: ROAD ACCESS 0/17 - DEAD ENDS 17 UNRESOLVED - DESIGNED GREEN < 30%`. The sheet **fails** `ROAD_ACCESS_COVERAGE` (0.0; 17 relation errors) and `DEAD_END_RESOLUTION` (17 unresolved): with the frozen network and old access declarations, full-site road clearance and group access are **mutually incompatible**. Under the fixed network / uniform row grid / current search family, caps of 25–130 m found no complete layout; an unbounded search produced the 147.25 m candidate, and the **global minimum displacement is not proven**. Regenerating roads makes clearance fail (min 0 m, **17 buildings below 3 m**). The full-site sheet is a **research draft**; the focus design remains canonical. The full-site DXF has **553 entities**, readback 553/553, XDATA 11 and privacy pass. 3.016362 m / 19.999999999999943 m are model-coordinate internal consistency under approximate sketch registration, not survey-grade engineering clearances.

**M4d-2** (0.25.0) tested **building-road co-design** under the same frozen 44-road network: **A** keeps the M4d-1 layout and rebuilds 17 connectors (362.095 m; access 17/17, relation errors 0, dead ends 0), but fails **only** `FULL_SITE_ROAD_CLEARANCE` (served-facade 2.8250521190593507 m < 3 m — a structural conflict between the 3.4–3.5 m terminal band and 7 m branch corridor, reported not widened); **B** uses a group-preserving layout (17 groups / 39 rows) with the same rebuilt access and is **hard-valid 29 = 13 pass + 11 info + 5 deferred + 0 fail** (access 17/17, terminal band 3.499999 m, boundary/overlap/NS 20.0, clearance 3.0164672267820585 m, dead ends 0). B remains incomplete as a design: **12 groups split**, group-centroid displacement max 140.12 m / mean 33.99 m, single-building max 278.46 m. The hard-first rule recommends **B** and excludes **A**; there is **no single score/ranking**. Candidate DXF is delivered: **A 584 entities/readback 584/584** (sheet stamped `INCOMPLETE`), **B 587/587** (`HARD-VALID`), both XDATA 11/privacy/audit 0; `comparison.svg` is a three-panel comparison. Connector sidewalks are clipped along building footprints (17 connectors / 115.202 m²), **A/B sidewalk overlap 0**; the CAD host remains unverified. The focus sheet remains canonical; the co-design sheet is a research draft. Tests are 515.

**M4d-2a** (0.26.0) added the **design-intent audit** without changing the layout algorithm or any threshold: the 17 groups are **inferred** (45.0 m + 8.0 m main-road buffer + Union-Find single linkage; G-01 has 9 inferred members vs 7 focus members, chain max 209.738 m; `provenance = not_designer_confirmed`); group quality is descriptive only (B **12/17** fragmented, **43** runs, max row gap 12, displacement mean 47.92 / P90 102.83 / max 278.46; A/baseline 10/17, max 147.25). The corrected source-green table (12 source objects, 10,986.4 m²) is building-occupied **845.541 / 845.541 / 713.445 m²**, road-occupied **64.113 / 320.949 / 73.815 m²**, retained **10,076.757 (91.72%) / 9,819.92 (89.38%) / 10,199.151 (92.83%)**, preserved/shrunk/cancelled **7/5/0**; no source green is wholly cancelled, and area retention is not intent retention. Access is layered: L1 group access 17/17 (baseline 0/17), L2 internal group roads 0/17 not designed, L3 building frontage **15/24/26 of 55** (geometry only), L4 5 entrances/2 proximity/**0 driveway**; there is no combined coverage claim. Robustness: a 0.1 m **independent** perturbation leaves **100% of samples below the unchanged 3.0 m rule** (B min 2.8887 m) while a common-datum shift leaves the clearance unchanged — so the status is **model-coordinate internal pass with engineering robustness not established**. Four-level B status: **geometric pass / intent descriptive / deferred 5 / host not_verified**; B remains a research baseline, not a professional design.

**M4d-2b** (0.27.0) tested **candidate C** with a bounded generate-and-test search (not a joint optimisation): 20 deterministic group-order variants each got rebuilt access and the full 29 checks; **5 are hard-valid** (default, `focus_first_y_asc`, `y_asc_swap01` are quality-identical to B; `y_asc_swap12` cuts row runs 43→41 but worsens mean displacement 47.92→59.02 m and road 189.06→316.08 m; `y_asc_rotate1` is worse at 46 runs/293.42 m max/445.50 m road); 13 fail NS/clearance and 2 cannot generate a layout. Bounded local repair produced **8 proposals / 0 accepted** (7 no feasible position, 1 no strict improvement). The result is **`no_improvement_same_as_b`** with `same_as_b = true` and hard-ok 29 = 13 pass + 11 info + 5 deferred + 0 fail; C-vs-B deltas are all 0 (fragmented 12, runs 43, displacement max 278.46/mean 47.92, group-centroid max 140.12, road 189.06), and inherited green/access values are unchanged. **C is not promoted and no C DXF is emitted**; B remains the sole hard-valid research baseline, still not a professional design (5 deferred, host not verified, 26/55 frontage, no internal group roads or driveway). This is a negative result; the next step is M4d-2c (local road re-alignment, selected main-road adjustment or a stronger group-aware optimizer), **not** relaxing thresholds.

**Next:** move to **M4d-2c** with a controlled larger design space (local road re-alignment and/or selected main-road adjustment and/or a stronger group-aware optimizer), while keeping the 29 hard checks and the no-score/no-ranking discipline, in parallel with a real CAD host round-trip and R1 evidence closure. Remaining evidence gaps: the designer's object-level review, full-case fidelity metrics, the unit-type library, six unit-count conflicts, road width/profile/alignment, a real CAD host round-trip, and the authority-declaration hardening that must precede autonomous canonical writes.

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

当前仓库整合了 R0 v0.19 研究证据、R1 部署生命周期原型、Domain Slice 001、E2E-001 纵向链路、E2E-002 mutation/rebuild 与 E2E-003 对抗性交付回归：根目录 `src/`、`tests/` 是可执行的正式代码，`research/archive/` 保存历史研究快照。全部测试通过（当前 414，见 §6），无长期 xfail。

项目坚持四条底线：原始 Source/Trace 不可覆盖；Agent 只能提议、不能写入 confirmed 设计真值；DXF/IFC 只是派生表示；未知状态必须显式保留。真实草图、真实设计院 Profile、IFC round-trip、独立日照引擎与真实 AutoCAD/FreeCAD 宿主接入仍是明确的证据缺口，仓库不会把合成测试包装成生产能力。

E2E-001/002/003 已打通：DOMAIN-SLICE-001 → Runtime canonical → massing → 合成 shadow → CAD-IR → DXF → readback manifest，验证了高度/节点/北向的 scoped stale 与真实 rebuild。Milestone 3a 把 15 个 strict xfail 全部转为正向检查；3b 完成指纹/依赖键一致性、符号表大小写、稳定环身份、raw/canonical 回读证据；3c 已用 AutoCAD 2024 Core Console 完成真实第三方 round-trip，判定 semantic_pass_with_serialization_differences。LibreCAD/FreeCAD/GUI QA 仍未执行。此后 Milestone 4 持续推进：4a 引入真实设计师草图取证（CASE-SKETCH-001）与统一路网拓扑（309 节点 / 333 边 / 121 个待复核 junction 候选）；4b.1 让真实草图移交门具备作用域感知，pilot 在设计师对象级几何复核前保持 blocked；4c 产出首个自主标准化设计草案（focus G-01，`rule_derived` 草案，非 human_confirmed），M4c-0 完成开源设计能力复用 sprint；M4c-1a（v0.16.0）已修正 4c 道路图的浮点 noding 缺陷：设计路网携带显式共享坐标 junction，noded 图 1 连通分量（51 节点 / 55 段，max endpoint gap 0.0 m），证据已重生成并发布 design-roads.geojson。M4c-1c（v0.17.0）把证据语义改诚实：检查分 pass / info / deferred（info 与 deferred 都不是 pass），open_space_ratio 63.0% 是开敞空间而非已设计绿地（designed green 6.54%，deferred），停车 recorded capacity 1,000 / 要求 2,398（capacity/layout deferred），21 项 design-basis 参数全部 confirmed:false，Agent 不能自确认。M4c-1d（v0.18.0）进一步收紧：pass 仅保留 5 项独立几何验证检查（v0.18.0 时点：18 项 = 5 项 pass + 8 info + 5 deferred），FAR 拆为算术情景（info）与最终验证（deferred），停车容量命名为 assumed nominal capacity，开敞空间双口径（candidate 63.0% 分类面积和 / unbuilt 65.3% 几何并集），provenance 认证为 declarative——任何 confirmed:true 状态都需要 approval_ref。M4c-1b（v0.19.0）完成首次设计几何变更：路网增至 44 条设计道路（25 主 + 17 支 + 2 入户），17/17 组全部通达（ROAD_ACCESS_COVERAGE pass），G-05/G-12 接入缺口关闭，24 个死端全部分类（17 justified / 5 unfinished / 2 unclassified），DXF 变为 206 实体（readback 206/206），拓扑重基线为 59 节点 / 65 段 / cyclomatic 7（max endpoint gap 仍为 0.0）。诚实残余：5 个车库入口仅 2 个与设计道路邻近（proximity，info），无引道设计（driveway deferred）；既有主路-建筑重叠 38.19 m²（MAIN-19 34.42 + MAIN-08 3.77）为已知未解决冲突，留待 M4c-2。M4c-1e（v0.20.0）把道路接入证据改为**声明式** `serves_group_ids` 关系（17 组各 1 条：16 支 + ACC-G-12；另有 BR-FOCUS 与 focus loop，共 19 条 connector 路），G-08/G-13 回到自有 BR-G-08/BR-G-13，terminal 中心线带 [3.4, 3.5] m 并单列 corridor-edge clearance（7 m 支路 0.0、4 m 入户路 1.5）；死端 24 个全部分类但并非全部 justified（17 justified / 5 unfinished / 2 unclassified，7 unresolved，`DEAD_END_RESOLUTION` deferred）；主路重叠改为机器检查 `MAIN_ROAD_BUILDING_OVERLAP` deferred，全场地道路退距 `FULL_SITE_ROAD_CLEARANCE` deferred；25 项检查 = 6 pass + 10 info + 9 deferred，测试 334，DXF 内容仍 206 实体（字节 SHA 每次保存会变，仅内容未变）。M4c-2（v0.21.0）完成主路对齐与边界修复。Phase 0（v0.22.0）修正证据：对齐语义改为 `local_search_exhausted`（11.565 m 间距只证明建筑间通道不可行；66.235 m diversion 只是候选基线，不是最优证明）；site-boundary 成为硬检查（`ROAD_BOUNDARY_CONTAINMENT` pass，margin 0.6735131264650868，MAIN-08/16/18 三条修复）；geojson 重叠字段拆分（`main_before` 38.19068149970835、`main_after` 0.0、`new_access` 0.9943558185246757、`total_after` 0.9943558185246756；MAIN-08 边界修复后主路剩余冲突 34.421783197612406 → 0）；design-diff 记录主路/死端，`source_segment_map` 25 路，死端 resolved 绑定 criterion_met + 几何复核，preview/overlay 已重生成。几何为 44 路（25/17/2）、58 节点 / 68 段 / cyclomatic 11、19 死端、36 junctions（24 explicit）、3 rings、gap 0；main_len 2,107.733378663747 m；road_area 26,882.20505326313 m²；sidewalk 9,764.76834535878 m²；DXF 211 实体（readback 211/211、XDATA 11）；27 项检查 = 9 pass + 11 info + 7 deferred（+3 DXF = 30），测试 396。M4c-3（v0.22.0）完成首次多候选实验（A/B1/B2/C）：四候选全部 hard pass，默认偏好推荐 B1、road-first 推荐 A，Pareto [B1,B2,C,A]，每个候选都有理由、无单一总分；B1 是候选基线（当前 B1 已完成边界修复、margin 0.6735；pre-repair 66.235 m 仅历史归档），不是预设答案。M4c-3a（v0.23.0）补齐评价完整性：candidate 证据比较全部 44 条路的 main/branch/access 分类位移（A main 2.320 / branch 2.826 / G-08 端点 2.826 m；B1 main 66.235 / branch 7.352；B2 main 71.772 / branch 13.645；C main 11.994 / branch 76.700、G-08 端点 75.315 m——C 不是小改动），每候选绑定 `design-assumption-v0.2` 与指纹 `2a2d7807…`（缺失/不一致 `basis_ok` fail），`HISTORICAL_BOUNDARY_ARCHIVE` 把 MAIN-19 66.235 m diversion 与 MAIN-08/16/18 修复同当前候选分开（当前 B1 边界合规 margin 0.6735），评价改为 11 个单目标、auxiliary 不进 Pareto/偏好、无混合单位/单一总分；默认推荐 B1、road-first 推荐 A、Pareto [B1,B2,C,A]，测试 414。全场地、车库、道路 profile、日照与合规仍未完成；下一步 M4d 全场地扩展 + 宿主往返/R1 并行。M4d（v0.24.1）完成全场地扩展（research draft）：55 栋 / 109 units / 2,398 households，18 rows / 8 superblocks (36 row records)，focus G-01 保留；位移 sum 2,328.95 m / max 147.25 m / mean 42.34 m；全场地检查 29 = 11 pass + 11 info + 5 deferred + 2 fail（`ROAD_ACCESS_COVERAGE` 0.0 / 17 relation errors，`DEAD_END_RESOLUTION` 17 unresolved），而边界/重叠/20 m 行距/3 m 道路退距通过；20 m 是**候选 row-rhythm 规则 + design-basis 假设，不是法规/普适约束**（over-spacing 记为节奏违规）。`DESIGNED_GREEN_RATIO` **deferred**（designed green 15.93% <30%，61.06% 账户是 `POTENTIAL OPEN SPACE ... NOT LANDSCAPE DESIGN`，图层 `L-OPEN-SPACE`，仅 auxiliary）；标题写明 `DESIGNED GREEN 15.93% - INCOMPLETE` 与 `INCOMPLETE: ROAD ACCESS 0/17 - DEAD ENDS 17 UNRESOLVED - DESIGNED GREEN < 30%`。冻结路网 + 旧 access 声明使 clearance 与 access coverage 互斥；**固定路网/统一行列/现有搜索族下 25–130 m cap 均未找到完整布局，无上限搜索得到最大 147.25 m 候选，未证明全局最小可行位移**。全场地 DXF **553/553**、XDATA 11、privacy pass；3.016362 m / 19.999999999999943 m 是近似草图配准下的模型坐标内部一致性，不是测绘级工程退距。focus 证据 29 = 9 pass + 11 info + 9 deferred（`DESIGNED_GREEN_RATIO` deferred，designed green 6.54%；61.46% 账户同样仅 auxiliary；四个 FULL_SITE_* deferred），focus sheet 仍是 canonical；测试 515 at M4d-2。M4d-2（v0.25.0）完成 A/B 建筑-道路协同实验：A 固定 M4d-1 布局 + 重建 17 连接路（16 支 + 1 入户，362.095 m；access 17/17、relation 0、dead 0），仅 `FULL_SITE_ROAD_CLEARANCE` fail（served-face 2.8250521190593507 m <3 m，terminal band 3.4–3.5 m 与 7 m 支路的结构冲突，未放宽）；B 组保持布局（17 组 / 39 rows）+ 同 access，**hard-valid 29 = 13 pass + 11 info + 5 deferred + 0 fail**（access 17/17、band 3.499999、boundary/overlap/NS 20.0、clearance 3.0164672267820585 m、dead 0），但组拆分 12、组质心 max 140.12/mean 33.99 m、单栋 max 278.46 m；hard-first 推荐 **B**、A excluded，无单一总分/排名；candidate DXF 已交付：**A 584/readback 584/584（INCOMPLETE）**、**B 587/587（HARD-VALID）**，XDATA 11/privacy/audit 0，`comparison.svg` 三面板；connector sidewalk 沿 footprint 裁剪（17 条 / 115.202 m²），**A/B sidewalk overlap 0**；CAD 宿主未验证；co-design sheet 是 research draft，focus 仍 canonical。M4d-2a（v0.26.0）设计意图审计（不改算法/阈值）：17 组为推断组（45 m + 8 m 主路 buffer + Union-Find；G-01 9 vs focus 7，链式最大 209.738 m，not_designer_confirmed）；B 非连续 12/17、runs 43、位移 mean 47.92/P90 102.83/max 278.46；修正绿地 table：building-occupied 845.541/845.541/713.445 m²，road 64.113/320.949/73.815 m²，retained 10,076.757(91.72%)/9,819.92(89.38%)/10,199.151(92.83%)，preserved/shrunk/cancelled 7/5/0；access L1 17/17、L2 0/17、L3 15/24/26 of 55、L4 0 driveway；0.1 m 独立扰动 100% <3.0（B min 2.8887，common datum 不变）；四层 B = geometric pass/intent descriptive/deferred 5/host not_verified；无评分/排名/gate；测试 556。M4d-2b（v0.27.0）candidate C 有界 generate-and-test（不是联合优化）：20 个组序变体，5 个 hard-valid（default/focus_first_y_asc/y_asc_swap01 与 B 同质；y_asc_swap12 runs 41 vs 43 但 mean 59.02 vs 47.92、road 316.08 vs 189.06；y_asc_rotate1 runs 46/max 293.42/road 445.50），13 个 NS/clearance fail、2 个 layout error；local repair 8 proposals/0 accepted（7 no feasible，1 no strict improvement）。decision `no_improvement_same_as_b`、same_as_b=true、hard-ok 29=13/11/5/0，C vs B deltas 全 0（fragmented 12、runs 43、位移 max 278.46/mean 47.92、组质心 max 140.12、road 189.06），green/access 继承 B 不变；C 不 promoted、无 C DXF；B 仍是唯一 hard-valid 研究基线，非专业设计（5 deferred、host not verified、26/55 frontage、无内部路/车库引道）。这是 negative result；下一步 M4d-2c（局部道路 re-align/主路调整/更强优化器），不放宽阈值；测试 571。
