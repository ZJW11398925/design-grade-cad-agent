# Project Status

Updated: 2026-10-28
Version: `0.16.0` (M4c-1a road-topology truth fix — explicit shared-coordinate junctions, dependency-free noded topology check, evidence regeneration; M4c-0 open-source design reuse sprint; Milestone 4c autonomous design synthesis draft; Milestone 4b.1 scope-aware handoff integrity; Milestone 4a sketch/road evidence; Milestone 3c partial third-party evidence)
Research basis: R0 v0.19 + R1 deployment-entry v0.2

## 1. One-line status

The project has a working **governance/runtime contract layer**, a **synthetic Building/Road domain slice**, **living E2E-001/002/003/003b pipelines** from confirmed trace to DXF readback with scoped mutation/rebuild, adversarial delivery checks, semantic/dependency closure, **one real AutoCAD 2024 Core Console round-trip**, a first **Tier B designer-sketch intake** with designer-confirmed semantics and a proposed image-space trace, a **unified-mask road topology** with 121 junction candidates, and a **real-sketch handoff gate that now blocks correctly** until an object-level human geometry review exists, and the first **autonomous standardized design draft** from the real sketch (focus block G-01, FAR 1.565, 1 parking space/household, 20 m north-south rows, editable DXF). The handoff → Canonical → CAD-IR → DXF path is implemented and tested with a test double, not published as real evidence; the autonomous draft is a `rule_derived` proposal, not human-confirmed. It does **not** yet have a human-confirmed sketch trace with fidelity metrics, real road engineering, general third-party CAD interoperability, IFC, or real-world validated behavior.

## 2. Test baseline

```text
python -m pytest -q
259 passed
```

259 tests collected, all passing. No long-lived strict xfails.

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
| Sketch handoff gate | 32 | passing |
| Sketch handoff A | 6 | passing |
| Design synthesis | 9 | passing |
| Design topology | 14 | passing |
| Design contract | 7 | passing |
| Privacy scan | 20 | passing |
| Open-source reuse | 3 | passing |

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
| Real sketch → canonical handoff | **gate implemented; pilot blocked** | CASE-SKETCH-001-HANDOFF-A: 7 selected objects pass source-integrity and topology checks but stop at `HUMAN_OBJECT_REVIEW_REQUIRED`; the downstream ConfirmedTraceScene → Canonical → CAD-IR → DXF path is proven only with an explicitly marked test double. Scope, geometry quality and boundary authority propagate when confirmed. |
| Autonomous design synthesis | **partial draft implemented** | CASE-SKETCH-001 design draft: full-site context (55 buildings/109 staircases/333 road edges) + focus block G-01 (7 standardized buildings/16 units); FAR 1.565; 2,398 households; 2,398 parking spaces and 5 entrances; 20 m north-south rows; 208-entity DXF with title block/key plan/dimensions; `rule_derived` proposal, not human-confirmed. M4c-0's 5-component road reading was diagnosed in M4c-1a as a sub-ULP floating-point noding artefact and fixed: explicit shared-coordinate junctions, noded graph **1 component** (51 nodes / 55 segments, cyclomatic 5, `max_endpoint_gap_m` 0.0), corridor union 1 piece; `design-roads.geojson` published. |
| Open-source design reuse | **sprint complete; partial answer** | Building Regulariser, OSMnx, PyGeoOps, Clothoids, momepy tested on CASE-SKETCH-001; OSMnx consolidation 309/333→117/141 with 1 component; Building Regulariser limited; PyGeoOps per-area; Clothoids single fit fails; momepy evaluation only; UrbGEN/Street Generator host/reference only |
| Road centerline extraction | **proposed_rough** | skeleton-derived from colour masks; no professional alignment, width or junction design |
| Road network topology | **connected_by_unified_road_mask** | 1 component: 309 nodes, 333 edges, 121 junction candidates; colour is a class attribute; no width, profile or alignment |
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
| `contracts/sketch-domain-handoff-v0.2.yaml` | Scope-aware real-sketch handoff, boundary authority, source integrity and road topology |
| `contracts/design-synthesis-v0.2.yaml` | Autonomous design draft state, basis, constraints, noded road topology, drawing and authority (v0.1 superseded) |
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
| R1-G07 Real Case | one non-synthetic site sketch | partial (the selected real subset blocks at the human geometry gate; the autonomous design draft is a `rule_derived` proposal, not human-confirmed) |
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
- Publication is sketch-only; the project metric scale, DWG/DXF and redline/project coordinates remain private. The pilot-local approximate scale is published only inside the handoff publication block.

What is proposed:

- 55 buildings (50 standalone + 5 designer-confirmed merges), 63 original red components preserved for provenance, 3 garage entrances, 12 cluster green spaces, 9 road areas and 1 site boundary in image space.
- M-001: 0046 + 0047 + 0060 (3 units) with connectors 0062 + 0063. M-002: 0030 (2 units) + 0053 (1 unit). M-003: 0001 + 0037 (kindergarten/facility). M-004: 0019 + 0058 (3 units inferred). M-005: 0027 + 0059 (3 units inferred). Merged geometry is a union of components without artificial bridging.
- Unit counts: 16 one-unit, 21 two-unit, 17 three-unit; 52 inferred from sketch dimensions and 2 confirmed (M-001/M-002). The kindergarten M-003 is excluded as a facility. Six long bars conflict between length and area and are flagged.
- All buildings record 11 floors as `proposed_initial`; no floor height, massing, FAR or unit-mix is derived.
- Building footprints are sketch placeholders pending the unit-type library; unit counts are inferred, not confirmed, except M-001/M-002.
- Road centerlines: the separate-colour 312-centerline result is superseded; the unified brown+blue network in section 14 has 333 edges and 121 junction candidates.
- Semantic labels, merge decisions and 11-floor assumption are confirmed; all geometry and centerline topology remain proposed.
- Calibration to the private reference is a reviewed approximate homography (mean 24.51 px, max 43.42 px); not survey-grade.

What is not done:

- No human-confirmed trace or fidelity metrics (Hausdorff/IoU/topology).
- No unit-type library replacement; sketch-era building footprints remain placeholders.
- All 10 close pairs are resolved into five merged buildings; six unit-count conflicts and the kindergarten facility remain for review.
- No 支路/入户路 separation.
- No full-case canonical Building/Road handoff; the selected pilot subset is blocked at the object-level human geometry review (`CASE-SKETCH-001-HANDOFF-A`).
- Road centerlines are not professional alignment or junction design.

Evidence: `docs/e2e/sketch-001/README.md`, `docs/e2e/sketch-001/case-summary.json`, `contracts/sketch-evidence-v0.1.yaml`, `tests/test_sketch_evidence.py`.

## 14. Road network topology (EP-R1-ROAD-001)

**The design's road network is one system.** The earlier separate-colour skeleton was the wrong process: it cut the network at brown/blue boundaries and produced nine artificial components.

- Corrected mask: brown OR blue, ≥300 px components, 5 px ellipse closing. 4 px leaves five components; 5 px is the smallest tested kernel that restores one component.
- Unified graph: 309 nodes, 333 edges, 1 component, 111 endpoints, 121 junction candidates, 25 cycles; 65 main-road and 268 branch/access edges.
- Colour is a road-class attribute, not a topology separator; junctions are skeleton graph nodes, not inferred connectors. All 121 junction candidates are `proposed` and need review.
- The eight nearest-node connectors are rejected and retained in `road-connectors-rejected.geojson` as negative evidence; they are not used.
- No width, cross-section, profile, alignment, junction turn geometry or surface is derived. The blue class still combines 支路 and 入户路.
- Handoff topology check on the selected T-junction: 4 nodes, 3 edges, 1 component, degree-3 node `SK-RDN-0126`; maximum edge-endpoint offset **3.606 px** against a declared **4.0 px** extraction tolerance. `SK-RDC-U-0010` and `SK-RDC-U-0017` are stored `to_node → from_node` in the source network and are normalized to `node_a → node_b`; this is recorded in the handoff, not hidden.
- Evidence: `road-network-proposed.geojson` (unified), `road-nodes-proposed.geojson`, `road-junctions-proposed.geojson`, `road-topology-summary.json`, `road-network-overlay.png`; the separate-colour centerlines are superseded; `tests/test_road_topology.py` (3 tests).

## 15. CASE-SKETCH-001-HANDOFF-A (Milestone 4b.1)

- Explicit handoff contract: `contracts/sketch-domain-handoff-v0.2.yaml`; v0.1 is superseded. Model/validation: `src/dgcad_domain/sketch_handoff.py`.
- The committed review record is `designer_authorized_pilot`: it authorizes the pilot and records all object geometry/coordinate decisions as `not_reviewed`. It does **not** claim a geometry review. The loader blocks it with `HUMAN_OBJECT_REVIEW_REQUIRED`.
- The v0.12.0 executed pilot is preserved under `docs/e2e/sketch-handoff-a/history-0.12.0/`; it is superseded and not current evidence.
- Selected real subset: site boundary, one ordinary building, one merged building, one green, two main-road edges, one branch edge, one T-junction.
- Boundary authority: the private redline is authoritative; the pilot uses the published sketch boundary and maps it to `SITE-SKETCH-001` with **candidate** authority. It cannot become `SITE-001` or claim canonical site identity.
- Review packet: `review-packet.html`, `review-packet.json`, `review-request.yaml` and an unsigned `review-confirmation-template.yaml`; 7 objects, image-space and local-metric panels, declared scale range, per-object sensitivity, T-junction topology and source hashes.
- Source integrity: 3 source files and 7 objects verified by SHA-256 and canonical geometry hash. File-hash mismatch, source-object mismatch, missing object and handoff-geometry divergence fail closed.
- Coordinate handoff: `image_space_unscaled` → `LOCAL-XY-ZUP`, `local_metric_scaled`, `uniform_scale_translation_yflip`, `homography_applied: false`, `shape_correction: none`, `axis_orientation: unknown`, scale 2.438 px/m (range 2.25–2.89), `project_coordinates: false`; area/perimeter/centroid sensitivity recorded per object.
- Road topology: 4 nodes, 3 edges, 1 component; degree-3 `SK-RDN-0126`; endpoints `SK-RDN-0067/0125/0209`; max endpoint offset 3.606 px against a declared 4.0 px tolerance; two source edges are direction-normalized and recorded.
- Downstream path (test double only): trace, canonical, CAD-IR, DXF XDATA and readback manifest all carry `confirmation_scope: pilot_subset` and `geometry_quality: confirmed_for_pilot`. The test-double run reaches 11 entities, audit 0/0 and readback pass; massing and road profiles remain blocked; no width is derived.
- Scope, quality and boundary authority propagate through `build_initial_scene()`; a full-case review rejects `confirmed_for_pilot`; a test double is rejected unless the caller explicitly allows it.
- Structured DXF privacy scan covers TEXT/MTEXT, layer/linetype/style/block names, XDATA and raw bytes.
- Evidence: `docs/e2e/sketch-handoff-a/`; tests: `tests/test_sketch_handoff.py` (32) and `tests/e2e/test_sketch_handoff_a.py` (6).
- `EP-R1-SKETCH-001` remains in progress; `R1-G07` remains partial until an object-level human geometry review exists.

## 16. CASE-SKETCH-001 autonomous design synthesis (Milestone 4c)

- Contract: `contracts/design-synthesis-v0.2.yaml` (v0.1 superseded); design package: `src/dgcad_design/`; evidence: `docs/e2e/design-synthesis-001/`.
- Full-site context: 55 building candidates, 109 staircase units, one kindergarten/facility, 333 source road edges, 12 cluster greens and 3 garage entrances.
- Design basis: 24×11 m staircase module (2 households/floor), 11 floors, 3.0 m floor height, 132 m² gross per household; FAR 1.55–1.60; ≥1 parking space/household; 20 m north-south spacing; 5 m boundary setback; 3 m building-road clearance; 12/7/4 m main/branch/access roads; ≥30% green.
- Full-site metrics: 2,398 households; 319,536 m² GFA (316,536 residential + 3,000 facility); **FAR 1.565**; 2,398 parking spaces; 5 garage entrances.
- Focus block G-01: 7 buildings / 16 units / 352 households, placed in rows with 20.0 m north-south spacing, unit division lines, green strips and an access loop; 2 buildings (2U + 1U) are recorded as dropped because they do not fit the buildable block.
- Road design: the 333-edge skeleton mesh is treated as **source evidence**, not the design network. The design uses merged main roads, one branch per group and a focus access loop; widths are 12/7/4 m. The 121-junction review is not continued as an optimization target.
- Road topology (corrected in M4c-1a): the design roads carry **explicit shared-coordinate junctions**; the noded centerline graph is **1 component** (51 nodes / 55 segments, cyclomatic 5, dead ends 21, junctions 27, explicit junctions 16, closed rings 3, `max_endpoint_gap_m` 0.0). Noded connectivity fails closed within a 1e-9 m endpoint tolerance; sub-1e-9 endpoint misalignment surfaces first as component count >1. `ROAD_CORRIDOR_COVERAGE` (corridor union, 1 piece) is published as informational, not a gate. Committed evidence: `design-roads.geojson` (41 centerlines + 16 explicit junction records).
- Green: cluster greens are clipped to the free space; green strips are inserted between rows; supplementary green is allocated from the residual open space. Site green ratio 63.0%.
- CAD: `design-proposal.dxf`, 208 entities, audit 0/0, readback 208/208 pass; CAD-IR `pass_with_scope_limits` with seven `UNKNOWN_HEIGHT_ALLOWED` warnings for the declared design heights; layers for site/building/unit/main/branch/access/sidewalk/green/dimension/title/legend/north/scale/key plan; title block states Agent-generated, not human-confirmed, not code-compliant.
- Authority: all design objects are `rule_derived` in `proposal_preview`; DXF XDATA and the readback manifest carry `confirmation_scope: design_draft`; no object is `human_confirmed`. Control plane unchanged in M4c-1a (foundation/runtime/deployment/CAD/domain untouched; XDATA arity 11; `ISSUE_CATEGORIES` unchanged).
- Checks: 13 declared — FAR, parking, entrance count, unit count, focus 20 m spacing, boundary setback, overlap, road clearance, noded road connectivity, road widths and green ratio pass; `ROAD_CORRIDOR_COVERAGE` is informational (non-gating); full-site north-south spacing is **deferred** until each group is designed.
- Tests: `tests/test_design_synthesis.py` (9); full suite **259 passed**.
- The autonomous draft is not construction-ready, not code-compliant, not the designer's unit library, and not an adopted or officially issued design.
- M4c-0's road finding ("corridor union 1 polygon, noded graph 5 components") was diagnosed in M4c-1a as a sub-ULP floating-point noding artefact — not a design disconnection; the fix and corrected narrative are recorded in §17 and the team dossier. The 4c candidate remains partial (full-site spacing deferred).

## 17. M4c-0 open-source design reuse sprint

- Evidence: `docs/e2e/open-source-reuse-001/`; matrix: `reuse-matrix.yaml`; experiments A/B/C with metrics, overlays, GeoJSON and an editable DXF.
- **Building Regulariser 0.2.5 (MIT)**: 9 focus footprints, 63→61 vertices, area −2.0%, mean Hausdorff 1.07 m, max 4.87 m, IoU 0.959, ERI 0.972→0.984. Limited gain; a cleanup adapter, not a unit/typology generator.
- **OSMnx 2.1.1 (MIT)**: source 309 nodes/333 edges → simplify 257/281 → consolidate 8 m 117/141, **1 component**, total length 6,090 m (−10.7%). With design widths the consolidated network still leaves no 120×90 m buildable focus rectangle; it is a topology preprocessor, not the design hierarchy.
- **PyGeoOps 0.6.0 (BSD-3)**: 11 centerlines for 11 road areas, 78% coverage, 10/11 multi-component; per-area candidates, not a connected network.
- **PyClothoids 0.2.0 (MIT)**: single G1 fit on MAIN-08 shortened the road by 78 m and deviated by 356 m Hausdorff; not a usable alignment generator.
- **momepy 1.0.0 (BSD-3)**: building morphology and network-ratio metrics; candidate evaluation only, not a compliance verdict.
- **UrbGEN (MIT)** is a Rhino/Grasshopper `.gha` plugin; **Street Generator/rue-lib (MIT)** is not on PyPI and uses foreign 20/15/10 m widths; both are reference-only. Clothoids, IfcOpenShell and Ladybug are deferred.
- The 4c candidate's road **corridor union is 1 polygon but its noded centerline graph read 5 components** (51 nodes/50 edges, `cyclomatic: 0`). M4c-1a later diagnosed this as a **sub-ULP floating-point noding artefact** — connector endpoints sat 1.5e-15–2.1e-14 m off the main lines (GEOS exact predicates create no node), the 50-edge count is the simple-graph collapse of the closed access loop, and `cyclomatic: 0` is momepy's connected-graph formula returning 0 on a disconnected graph (true multigraph cycle rank 5). Fixed in M4c-1a with explicit shared-coordinate junctions: the noded graph is **1 component**, and `ROAD_CONNECTIVITY` now checks the noded graph.
- Next (superseded by M4c-1a): the "optional OSMnx adapter + rebuild on the consolidated network" plan was **not** taken — the fix is dependency-free and the design network was never rebuilt on OSMnx; OSMnx remains an optional source-skeleton preprocessor, not a connectivity proof. Building Regulariser only for noisy input cleanup; momepy for evaluation.
- No new core dependencies were added; the experiment dependencies are optional only.

## 18. Current non-claims



- `research_complete = false`
- `release_authorized = false`
- No production security approval.
- No production database decision.
- No Chinese road/building daylight compliance conclusion.
- No claim that MCP wire protocol, FreeCAD or IFC have been executed; AutoCAD 2024 Core Console was executed as a file round-trip, not a runtime bridge or GUI/print QA.
- CASE-SKETCH-001 semantic labels, five building merges, the 1/2/3-unit type set and the 11-floor assumption are designer-confirmed; geometry and road centerlines are proposed, and no fidelity metrics exist.
- 11 floors is provisional; no floor height, massing, FAR or unit-mix is derived. Building footprints are placeholders pending the unit-type library; unit counts are inferred except M-001/M-002, the kindergarten M-003 is excluded as a facility, and six length-vs-area conflicts remain for review.
- CASE-SKETCH-001 publishes the sketch and image-space geometry; the project metric scale, calibration matrix, DWG/DXF and redline/project coordinates remain private. The pilot-local approximate scale is published only inside the handoff publication block, with its source and range recorded.
- Road connectivity is derived from the unified brown+blue mask: one component, 121 proposed junction candidates. The separate-colour 9-component result and the eight nearest-node connectors are rejected.
- CASE-SKETCH-001-HANDOFF-A is a pilot subset. The committed review record is an authorization, not an object-level geometry review; the pipeline is blocked at `HUMAN_OBJECT_REVIEW_REQUIRED`, and `EP-R1-SKETCH-001` is not complete.
- No DXF or canonical model is published for the current blocked handoff. The test-double DXF is local metric only; no project coordinates/DWG are published. Same-library `ezdxf` readback is not third-party evidence.
- The pilot transform is uniform scale, translation and y-flip, not the six-point homography; it does not correct local sketch distortion.
- No road width, cross-section, profile, alignment or surface is designed.
- The 4c design candidate is partial (full-site north-south spacing deferred). Its earlier 5-component noded reading was a sub-ULP floating-point noding artefact, corrected in M4c-1a with explicit shared-coordinate junctions (noded graph 1 component; corridor union 1 piece). The open-source M4c-0 sprint did not produce a complete professional design; OSMnx remains an optional source-skeleton preprocessor, not a connectivity proof.
- The open-source libraries tested in M4c-0 are optional experiment dependencies, not production/core dependencies; no code-compliance or construction-readiness claim is made.
- The reuse experiments assigned EPSG:3857 only for library compatibility; the coordinates are the local metric sketch frame, not a real projection.
- The autonomous design draft is a schematic proposal, not a construction or permit drawing and not a code-compliance claim; its unit module is provisional, its road corridors are schematic, its garage layout is not designed, and full-site north-south spacing is deferred.
- The autonomous draft is never `human_confirmed`; it is a `rule_derived` proposal the designer may adopt or edit.
