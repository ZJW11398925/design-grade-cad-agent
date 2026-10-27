# Project Status

Updated: 2026-10-27
Version: `0.10.1` (Milestone 4a sketch intake and as-drawn road topology; Milestone 3c partial third-party evidence)
Research basis: R0 v0.19 + R1 deployment-entry v0.2

## 1. One-line status

The project has a working **governance/runtime contract layer**, a **synthetic Building/Road domain slice**, **living E2E-001/002/003/003b pipelines** from confirmed trace to DXF readback with scoped mutation/rebuild, adversarial delivery checks, semantic/dependency closure, **one real AutoCAD 2024 Core Console round-trip**, a first **Tier B designer-sketch intake** with designer-confirmed semantics and a proposed image-space trace, and an **as-drawn road topology** whose nearest-node connectors were rejected. It does **not** yet have a human-confirmed sketch trace with fidelity metrics, real road engineering, general third-party CAD interoperability, IFC, or real-world validated behavior.

## 2. Test baseline

```text
python -m pytest -q
168 passed
```

168 tests collected, all passing. No long-lived strict xfails.

| Suite | Tests | Status |
|---|---|---|
| Foundation | 21 | passing |
| Runtime | 22 | passing |
| Deployment | 8 | passing |
| Lifecycle | 14 | passing |
| Domain | 26 | passing |
| Analysis | 7 | passing |
| CAD delivery | 9 | passing |
| E2E-001 | 8 | passing |
| E2E-002 | 6 | passing |
| E2E-003 | 20 | passing |
| E2E-003b | 11 | passing |
| Third-party evidence | 2 | passing |
| Sketch evidence | 11 | passing |
| Road topology | 3 | passing |

## 3. Capability status

| Capability | Status | Notes |
|---|---|---|
| Canonical identity / revision / authority | implemented | three revision axes; proposal-only Agent writes |
| Atomic multi-object changes | implemented | all-or-nothing commit with stale rejection |
| Preview isolation | implemented | preview world cannot mutate canonical current |
| Dependency and stale propagation | implemented | object/profile/method dependency keys; transitive invalidation |
| Audit log | implemented | append-only JSONL in research prototype |
| Stateful runtime | implemented | proposals, approvals, jobs, artifacts, idempotency |
| Human Control Plane | implemented (prototype) | approve/unlock only; separate principal |
| Local sidecar lifecycle | implemented (prototype) | discovery, pairing, sessions, lease, bridge registry |
| SQLite/WAL persistence | spike | not wired into `StatefulRuntime` save/load |
| MCP wire protocol | **blocked** | official SDK unavailable |
| AutoCAD/FreeCAD runtime bridge | **blocked** | no host message exchange; the AutoCAD Core Console file round-trip is separate (3c) |
| Building/Road domain adapters | **implemented (synthetic)** | confirmed trace → canonical building/road; unknown states preserved |
| Real professional road geometry | **not validated** | only centerline + explicit cross-section; no alignment/clothoid/surface |
| E2E-001 living pipeline | **implemented (synthetic)** | Domain → massing → shadow → CAD-IR → DXF → readback, living packages only |
| E2E-002 mutation/rebuild | **implemented (synthetic)** | scoped stale + deterministic rebuild worker; height, node, north bearing verified |
| E2E-003 adversarial delivery | **implemented (same-library)** | 20/20 positive checks; no permanent xfails; categories and issue mapping |
| E2E-003b semantic/dependency | **implemented (same-library)** | fingerprint consistency, symbol tables, ring keys, raw/canonical manifest |
| Road surface geometry | **deferred** | no `SURFACE-R-002` artifact is generated or claimed |
| DXF delivery | **minimal synthetic** | R2010, 15 entities, audit 0/0; known DEV-CAD gaps deferred |
| Symbol-table case semantics | **implemented** | layer/linetype/text style/block/dimstyle case-insensitive; `exact` policy available |
| CAD-IR dependency consistency | **implemented** | global scene revision is metadata; per-object revisions registered |
| Ring identity | **implemented** | content-derived `ring_key` stable across part insertion |
| Raw/canonical readback | **implemented** | manifest carries `canonical_target` + `raw_dxf_semantics`; tolerance 1e-9 |
| Third-party CAD round-trip | **partial evidence only** | AutoCAD 2024 Core Console: semantic pass with serialization differences; LibreCAD/FreeCAD/GUI not run; issue #6 |
| Real sketch → trace | **partial (designer sketch)** | CASE-SKETCH-001: 55 buildings (5 designer-confirmed merges), unit counts 16/21/17 plus 1 facility, 11 floors provisional, image-space geometry proposed; no fidelity metrics or unit-type library yet |
| Road centerline extraction | **proposed_rough** | skeleton-derived from colour masks; no professional alignment, width or junction design |
| Road network topology | **as_drawn_unresolved** | 9 as-drawn components; 8 nearest-node connectors rejected; no connected-graph claim; no width, profile or alignment |
| Real design-office profile | **not validated** | synthetic and DB11 subset only |
| IFC round-trip | **blocked** | IfcOpenShell unavailable |
| Independent solar engine | **not validated** | synthetic NOAA baseline only |


## 4. Living contracts

| Contract | Scope |
|---|---|
| `contracts/canonical-site-ir-v0.4.yaml` | Canonical identity, revisions, authority, dependency, worlds |
| `contracts/domain-contract-v0.1.yaml` | Confirmed trace → Building/Road domain slice |
| `contracts/cad-ir-v0.1.yaml` | Minimal CAD-IR for the E2E delivery slice |
| `contracts/e2e-pipeline-v0.1.yaml` | E2E-001 stages, invariants and known gaps |
| `contracts/e2e-mutation-v0.1.yaml` | E2E-002 mutation, rebuild and manifest comparison |
| `contracts/e2e-adversarial-v0.1.yaml` | E2E-003 adversarial scenarios, categories and issue mapping |
| `contracts/sketch-evidence-v0.1.yaml` | Sketch-to-trace evidence, review states and publication boundary |
| `contracts/evidence-gate-register-v0.2.yaml` | R1-G01..G08 and evidence packages |
| `contracts/runtime-state-contract-v0.1.yaml` | Runtime state envelope and registries |
| `contracts/sidecar-lifecycle-contract-v0.1.yaml` | Sidecar lifecycle |
| `contracts/local-auth-capability-contract-v0.1.yaml` | Roles and capabilities |
| `contracts/mcp-binding-v0.3.yaml` | MCP binding candidate (unexecuted) |

Promotion status of all research artifacts: [research-to-product-map.md](research-to-product-map.md).

## 5. Evidence gates

| Gate | Requirement | Status |
|---|---|---|
| R1-G01 Identity | stable identity across canonical/3D/DXF/IFC | partial (no IFC execution) |
| R1-G02 Authority | no bypass path | pass for prototype scope |
| R1-G03 Dependency | correct stale/local rebuild | pass for contract scope |
| R1-G04 Geometry | representative failure cases fail closed | partial (real geometry, entity range and project validation not exercised) |
| R1-G05 Delivery | third-party semantic round-trip + real profile | partial (AutoCAD Core Console executed; real profile subset missing) |
| R1-G06 Preview | no canonical pollution | pass for prototype scope |
| R1-G07 Real Case | one non-synthetic site sketch | partial (one designer sketch ingested; not human-confirmed; not through canonical) |
| R1-G08 Spikes | IFC + independent ENV + real profile | not started |

## 6. Known defects carried forward

These were reproduced after the v0.3 synthetic hardening and are accepted as **development acceptance items**, not research tasks. The living validator now covers the resolved items; only `DEV-CAD-006` remains open.

Resolved in the living validator (0.6.0):

- `DEV-CAD-002` safe entity dispatch and `ENTITY_TYPE_MISMATCH` — issue #2 closed.
- `DEV-CAD-003` LWPOLYLINE bulge, width, thickness and extrusion — issue #3 closed.
- `DEV-CAD-007` structured `validator_error` — issue #7 closed.
- `DEV-CAD-009` entity-level style overrides — issue #17 closed.
- `DEV-CAD-010` CIRCLE/TEXT 3D and text placement — issue #18 closed.

Resolved in 0.7.0 (Milestone 3b):

- `DEV-CAD-001` / #1: MultiPolygon 2-part+hole passes; content-derived ring keys are stable across sibling-part insertion.
- `DEV-CAD-004` / #4: raw DXF semantics and canonical targets are both in the readback manifest; tolerance `1e-9`. Arcs/splines are outside the current delivery entity set.
- `DEV-CAD-005` / #5: layer/linetype/text style/block/dimstyle case semantics implemented; original spelling retained.
- `DEV-CAD-008` / #8: serialization-difference vs profile-violation categories tested and separated.
- `DEV-CAD-011` / #16: global scene revision is metadata; per-object revisions drive CAD-IR dependencies.

Still open:

- `DEV-CAD-006` / #6: repeatable third-party CAD round-trip matrix (Milestone 3c).

See `research/archive/r0-v0.19/working/cad-bim-validator/development-acceptance-contract-v0.1.md`.

## 7. Domain slice 001

Implemented in `src/dgcad_domain/` and tested by `tests/test_domain_contracts.py`.

What it proves:

- A confirmed trace is canonicalized as immutable `evidence_only` objects and is not overwritten by professional proposals.
- Buildings preserve trace/professional footprint separation and explicit height state/source.
- Unknown height survives proposal, preview and commit; massing is blocked with `MASSING_BLOCKED_UNKNOWN_HEIGHT`.
- Regularization is a candidate requiring human confirmation; intentional rotation is not silently axis-aligned.
- Road class, function, access and cross-section are separate facts; unknown class blocks derived widths.
- A T-junction node move is an atomic multi-object change set; a stale member rejects the whole set.
- Height changes stale massing but not footprint-dependent artifacts; road geometry changes stale road surfaces.
- External geometry cannot write canonically; it enters through a reconcile proposal.
- The same flow works through `StatefulRuntime`: agent proposal → preview → human approval → commit → stale artifact → rebuild job.

What it does **not** prove:

- That a real sketch can be converted into the confirmed trace.
- That professional road alignment, junction turn geometry or a real cross-section profile is correct.
- That any Chinese standard or design-office profile is satisfied.
- That DXF/IFC output is valid or interoperable.
- That the synthetic fixture represents real design practice.

## 8. E2E-001 living pipeline

Implemented in `src/dgcad_analysis/`, `src/dgcad_cad/`, `src/dgcad_e2e/` and `tests/e2e/`.

What it proves:

- DOMAIN-SLICE-001 → Runtime canonical → massing → shadow → CAD-IR → DXF → readback works in one chain using only living packages.
- Five domain proposals commit through human approval grants; scene revision reaches 6.
- Massing is produced for confirmed heights and blocked for the unknown-height building.
- Rebuild scheduling queues the three stale artifacts in dependency-safe order.
- Unknown height and unknown road class remain explicit through analysis, CAD-IR and DXF metadata.
- DXF XDATA preserves object ID, class, geometry revision, source/representation hashes, entity role and ring role.
- Readback detects vertex mutation, unexpected layers and entity-type substitution without crashing.
- The pipeline does not import or call archived R0 scripts.

What it does **not** prove:

- Real sketch → trace or real professional geometry.
- Third-party CAD compatibility or a design-office DXF profile.
- IFC/BIM interoperability.
- Standards or daylight compliance.
- That the synthetic shadow baseline matches an independent engine.

`DEV-CAD-003` (bulge/constant width) was resolved in Milestone 3a; issue #3 is closed.

## 9. E2E-002 mutation and rebuild

Implemented in `src/dgcad_e2e/living_project.py` and `tests/e2e/test_e2e_002_mutations.py`.

What it proves:

- A height change bumps only the parameter revision, stales massing/shadow/CAD-IR/DXF, and leaves footprint-only artifacts current.
- A T-junction move is one atomic changeset; corridor centerlines are rebuilt from latest canonical edge geometry, never from the fixture.
- North bearing is versioned and sourced in `PROJECT-CONTEXT-001`; changing it stales shadow and delivery but not building footprint geometry.
- The rebuild worker claims jobs, recomputes, writes, validates and completes only with a content hash.
- Old/new delivery is compared by object IDs, canonical revisions, dependency fingerprints, readback verdict and audit result.
- Road surface geometry is explicitly deferred; no `SURFACE-R-002` artifact is registered.

What it does **not** prove:

- Professional road surface construction.
- Real sketch input or real road engineering.
- Third-party CAD compatibility, IFC or standards compliance.
- Independent shadow-engine accuracy.

## 10. E2E-003 adversarial delivery regression

Implemented in `tests/e2e/test_e2e_003_adversarial.py` and `contracts/e2e-adversarial-v0.1.yaml`.

Positive coverage:

- LWPOLYLINE non-zero elevation → `NONZERO_Z`.
- MultiPolygon 2 parts + 1 hole → 3 entities, audit 0/0, readback pass; `ring_index` is global within the object (part order, then ring order).
- One layer linetype case (`Continuous`) → semantic pass; full symbol-table equivalence was completed in 3b (#5 closed).
- Missing XDATA → `MISSING_XDATA`, category `interoperability`.
- `delivery-comparison.json` contains object IDs, canonical revisions, CAD-IR fingerprint, readback verdict, audit, profile identity, `dxf_sha256` and `readback_manifest_sha256`; both hashes are verified against the actual files.
- Issue categories distinguish `profile_violation` from `cad_format_semantics`; unknown codes default to `unclassified`, and a contract-sync test enforces the mapping.

Hardened in Milestone 3a (previously strict xfails):

- CIRCLE/TEXT Z, TEXT rotation/width/alignment → `CIRCLE_NONZERO_Z`, `TEXT_NONZERO_Z`, `TEXT_ROTATION_MISMATCH`, `TEXT_WIDTH_MISMATCH`, `TEXT_ALIGNMENT_MISMATCH`.
- Entity color/linetype/lineweight/true-color/transparency overrides → `ENTITY_*_OVERRIDE`.
- LWPOLYLINE start/end width, thickness, extrusion → `VERTEX_WIDTH_MISMATCH`, `THICKNESS_MISMATCH`, `EXTRUSION_MISMATCH`; bulge/constant width also detected.
- Structured `VALIDATOR_ERROR` for malformed DXF or validator-internal exceptions.

Existing coverage reused: vertex mutation, unexpected layer, entity-type substitution, bulge and constant width.

Boundaries:

- Same-library `ezdxf` compile/readback only; not third-party CAD evidence.
- Modelspace only; paper space out of scope.
- Milestone 3a hardened the living validator; 3b closed symbol-table, dependency and ring identity; 3c provides one-host third-party evidence.
- Road surface geometry remains deferred.
- CAD-IR fingerprint/dependency-key consistency was closed in 3b (#16 / DEV-CAD-011).

## 11. E2E-003b semantic and dependency closure

Implemented in `src/dgcad_cad/` and `tests/e2e/test_e2e_003b_semantics.py`.

What it proves:

- An unrelated node-property change advances the scene revision but does not stale CAD-IR/DXF or change the CAD-IR fingerprint.
- A road hierarchy change stales CAD-IR/DXF and changes the fingerprint, because per-object semantic revisions are registered.
- Layer, linetype, text style, block and dimstyle names compare case-insensitively; `exact` policy remains available.
- A missing required block/dimstyle/text style is a structured profile violation.
- MultiPolygon ring keys are content-derived and stable when a sibling part shifts indices.
- The readback manifest carries both canonical targets and raw DXF semantics, with tolerance `1e-9`.
- Serialization differences (`AUDIT_FIX`) are distinct from profile violations.

Boundaries:

- Same-library `ezdxf` only; no third-party CAD evidence (#6).
- Modelspace only.
- Arcs/splines are outside the current delivery entity set.
- No road surface geometry, real sketch, IFC or standards compliance.

## 12. E2E-003c third-party CAD evidence

Executed with **AutoCAD 2024 Core Console** in an isolated profile.

What was verified:

- 15 input entities and 15 XDATA records survive the round-trip.
- Layers, colors, lineweights, blocks, dimstyles, text styles, units and geometry are preserved.
- Audit errors/fixes remain 0/0.
- The living validator passes with an R2018 semantic-equivalence profile.
- Recorded serialization differences: `AC1024 → AC1032` (R2010 → R2018) and `CONTINUOUS → Continuous` on six layers.
- Verdict: `semantic_pass_with_serialization_differences`.

Not verified:

- LibreCAD and FreeCAD round-trips.
- AutoCAD GUI visual/print QA.
- A real design-office profile.
- General CAD compatibility beyond this synthetic fixture and host version.

Evidence: `docs/e2e/third-party-003c.md` and `docs/e2e/third-party-003c/`. Issue #6 remains open for the remaining matrix.

## 13. CASE-SKETCH-001 intake (Milestone 4a, proposed)

Implemented as a private-reference, public-sketch evidence package in `docs/e2e/sketch-001/` and `contracts/sketch-evidence-v0.1.yaml`.

What is confirmed:

- The private redline is the site boundary; the sketch is hand-modified with a large deviation.
- Unit is metre; the DWG header `$INSUNITS=4` is a metadata defect.
- Existing survey buildings are to be removed and are unrelated to the sketch design.
- Red = building; magenta = underground garage entrance; brown = main road; blue = branch/access road; green = cluster green space.
- The top edge is intentional; only a road segment is clipped.
- Publication is sketch-only; DWG/DXF, redline/project coordinates and metric scale remain private.

What is proposed:

- 55 buildings (50 standalone + 5 designer-confirmed merges), 63 original red components preserved for provenance, 3 garage entrances, 12 cluster green spaces, 9 road areas and 1 site boundary in image space.
- M-001: 0046 + 0047 + 0060 (3 units) with connectors 0062 + 0063. M-002: 0030 (2 units) + 0053 (1 unit). M-003: 0001 + 0037 (kindergarten/facility). M-004: 0019 + 0058 (3 units inferred). M-005: 0027 + 0059 (3 units inferred). Merged geometry is a union of components without artificial bridging.
- Unit counts: 16 one-unit, 21 two-unit, 17 three-unit; 52 inferred from sketch dimensions and 2 confirmed (M-001/M-002). The kindergarten M-003 is excluded as a facility. Six long bars conflict between length and area and are flagged.
- All buildings record 11 floors as `proposed_initial`; no floor height, massing, FAR or unit-mix is derived.
- Building footprints are sketch placeholders pending the unit-type library; unit counts are inferred, not confirmed, except M-001/M-002.
- 312 rough centerline candidates: main road 1 component / 40 nodes / 41 edges / 4 endpoints / 6 junctions / 2 loops; blue network 8 components / 266 nodes / 271 edges / 125 endpoints / 93 junctions / 13 loops.
- Semantic labels, merge decisions and 11-floor assumption are confirmed; all geometry and centerline topology remain proposed.
- Calibration to the private reference is a reviewed approximate homography (mean 24.51 px, max 43.42 px); not survey-grade.

What is not done:

- No human-confirmed trace or fidelity metrics (Hausdorff/IoU/topology).
- No unit-type library replacement; sketch-era building footprints remain placeholders.
- All 10 close pairs are resolved into five merged buildings; six unit-count conflicts and the kindergarten facility remain for review.
- No 支路/入户路 separation.
- No canonical Building/Road handoff from this sketch yet.
- Road centerlines are not professional alignment or junction design.

Evidence: `docs/e2e/sketch-001/README.md`, `docs/e2e/sketch-001/case-summary.json`, `contracts/sketch-evidence-v0.1.yaml`, `tests/test_sketch_evidence.py`.

## 14. Road network topology (EP-R1-ROAD-001 start)

- As-drawn: 306 nodes, 312 edges, 9 components, 129 endpoints, 99 junctions, 15 cycles; 41 main-road edges and 271 branch/access edges.
- Eight nearest-node connectors were attempted and **rejected by designer review**: a straight nearest-node line is not evidence of a road connection and can create false topology.
- No connected graph is claimed; the nine as-drawn components remain separate; component gaps 15.62–76.06 px remain open.
- Rejected connectors are retained in `road-connectors-rejected.geojson` as negative evidence (`review_state: rejected`).
- No width, cross-section, profile, alignment, junction turn geometry or surface is derived. The blue class still combines 支路 and 入户路.
- Evidence: `docs/e2e/sketch-001/road-network-proposed.geojson` (as-drawn), `road-nodes-proposed.geojson`, `road-connectors-rejected.geojson`, `road-topology-summary.json`, `road-network-overlay.png`; `tests/test_road_topology.py` (3 tests).

## 15. Current non-claims

- `research_complete = false`
- `release_authorized = false`
- No production security approval.
- No production database decision.
- No Chinese road/building daylight compliance conclusion.
- No claim that MCP wire protocol, FreeCAD or IFC have been executed; AutoCAD 2024 Core Console was executed as a file round-trip, not a runtime bridge or GUI/print QA.
- CASE-SKETCH-001 semantic labels, five building merges, the 1/2/3-unit type set and the 11-floor assumption are designer-confirmed; geometry and road centerlines are proposed, and no fidelity metrics exist.
- 11 floors is provisional; no floor height, massing, FAR or unit-mix is derived. Building footprints are placeholders pending the unit-type library; unit counts are inferred except M-001/M-002, the kindergarten M-003 is excluded as a facility, and six length-vs-area conflicts remain for review.
- CASE-SKETCH-001 publishes the sketch and image-space geometry only; the DWG/DXF, redline/project coordinates and metric scale are private.
- Road connectivity is unresolved: nine as-drawn components; eight nearest-node connectors were rejected.
- No road width, cross-section, profile, alignment or surface is designed.
