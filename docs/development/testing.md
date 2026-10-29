# Testing Strategy

Testing is the primary engineering control in this project. Research claims are not promoted by prose; they are promoted by executable evidence with a declared scope.

## 1. Test layers

| Layer | Purpose | Current state |
|---|---|---|
| L0 Contract / conformance | Prove governance invariants: identity, revision, authority, dependency, idempotency, contract↔module sync | **64 tests passing** (Foundation 21, Runtime 22, Deployment 8, Design contract 13) |
| L1 Domain & design topology | Prove building/road domain objects, unknown-state preservation, atomic topology changes, validators, the noded design-road topology, declared road access semantics and main-road alignment/boundary/dead-end resolution | **87 tests passing** (Domain 26, Road topology 3, Design topology 14, Road access 33, Main alignment 11) |
| L2 Integration | Prove the synthetic E2E pipeline, scoped mutation/rebuild, adversarial delivery and semantic/dependency closure | **45 tests (8 E2E-001 + 6 E2E-002 + 20 E2E-003 + 11 E2E-003b), all passing** |
| L2 CAD delivery & evidence | Prove CAD-IR mapping, DXF compile/readback and third-party evidence integrity | **11 tests passing** (CAD delivery 9, Third-party evidence 2) |
| L2 Analysis | Prove solar position, confirmed/unknown blockers, context completeness, dependency fingerprint | **7 tests passing** |
| L2 Sketch & handoff evidence | Prove the sketch case's privacy boundary, designer-confirmed semantics, the scope-aware handoff gate and the blocked pilot | **49 tests passing** (Sketch evidence 11, Sketch handoff gate 32, Sketch handoff A 6) |
| L2 Design synthesis & reuse | Prove the autonomous draft basis/layout/checks/DXF, basis provenance, honest green/parking semantics, declared access relations, access-road generation, the multi-candidate experiment (all-44-road geometry change, basis binding, 11 single-unit objectives/evaluation/visuals), the full-site layout/checks/evidence, the A/B co-design/group experiments and the reuse matrix | **218 tests passing** (Design synthesis 9, Design basis 20, Green/parking semantics 9, Road access generation 13, Parking geometry 6, Candidates 17, Evaluation 27, Visuals 13, Full-site layout 16, Full-site constraints 29, Full-site evidence 13, Co-design access 11, Group-preserving layout 10, Group metrics 11, Co-design evidence 11, Open-source reuse 3) |
| L3 Third-party | Prove semantic round-trip through independent CAD/BIM applications | partial evidence: AutoCAD 2024 Core Console semantic pass with serialization differences; no LibreCAD/FreeCAD/GUI matrix |
| L4 Security / privacy & lifecycle | Prove loopback, roles, pairing, lease, bridge expiry, stale writers and the structured DXF privacy scan | **34 tests passing** (Lifecycle 14, Privacy scan 20) |

Layer totals partition all 515 collected tests with no double counting. (Taxonomy rebuilt in 0.16.0: the previous table counted the 14 lifecycle tests in both L0 and L4 and left 67 tests unmapped.)

A passing lower layer never promotes a higher-layer claim automatically.

## 2. Current suites

| Suite | File | Tests |
|---|---|---|
| Foundation | `tests/test_foundation_contracts.py` | 21 |
| Runtime | `tests/test_runtime_contracts.py` | 22 |
| Deployment | `tests/test_deployment_contracts.py` | 8 |
| Lifecycle | `tests/test_lifecycle_contracts.py` | 14 |
| Domain | `tests/test_domain_contracts.py` | 26 |
| Analysis | `tests/test_analysis_contracts.py` | 7 |
| CAD delivery | `tests/test_cad_delivery_contracts.py` | 9 |
| E2E-001 | `tests/e2e/test_living_pipeline.py` | 8 |
| E2E-002 | `tests/e2e/test_e2e_002_mutations.py` | 6 |
| E2E-003 | `tests/e2e/test_e2e_003_adversarial.py` | 20 |
| E2E-003b | `tests/e2e/test_e2e_003b_semantics.py` | 11 |
| Third-party evidence | `tests/e2e/test_e2e_003c_third_party.py` | 2 |
| Sketch evidence | `tests/test_sketch_evidence.py` | 11 |
| Road topology | `tests/test_road_topology.py` | 3 |
| Sketch handoff gate | `tests/test_sketch_handoff.py` | 32 |
| Sketch handoff A | `tests/e2e/test_sketch_handoff_a.py` | 6 |
| Design synthesis | `tests/test_design_synthesis.py` | 9 |
| Design topology | `tests/test_design_topology.py` | 14 |
| Road access | `tests/test_road_access.py` | 33 |
| Road access generation | `tests/test_road_access_generation.py` | 13 |
| Main alignment | `tests/test_main_alignment.py` | 11 |
| Candidates | `tests/test_candidates.py` | 17 |
| Evaluation | `tests/test_evaluation.py` | 27 |
| Visuals | `tests/test_visuals.py` | 13 |
| Full-site layout | `tests/test_full_site_layout.py` | 16 |
| Full-site constraints | `tests/test_full_site_constraints.py` | 29 |
| Full-site evidence | `tests/test_full_site_evidence.py` | 13 |
| Co-design access | `tests/test_co_design_access.py` | 11 |
| Group-preserving layout | `tests/test_group_preserving_layout.py` | 10 |
| Group metrics | `tests/test_group_metrics.py` | 11 |
| Co-design evidence | `tests/test_co_design_evidence.py` | 11 |
| Design contract | `tests/test_design_contract.py` | 13 |
| Design basis | `tests/test_design_basis.py` | 20 |
| Green/parking semantics | `tests/test_green_parking_semantics.py` | 9 |
| Parking geometry | `tests/test_parking_geometry.py` | 6 |
| Privacy scan | `tests/test_privacy_scan.py` | 20 |
| Open-source reuse | `tests/test_open_source_reuse.py` | 3 |

Run all:

```bash
python -m pytest -q
```

Run one suite:

```bash
python -m pytest tests/test_lifecycle_contracts.py -q
```

Coverage:

```bash
python -m pytest -q --cov --cov-report=term-missing
```

## 3. What the current tests prove

- Stable `object_id` survives revisions; revision axes change independently.
- Preview worlds cannot mutate canonical current state.
- Atomic change sets either commit entirely or not at all; stale proposals are rejected.
- External world cannot write canonical directly.
- Locks enforce axis- or field-level protection and require explicit human unlock.
- Dependency invalidation is transitive but scoped to affected artifacts.
- Validation failures are structured, not exception text.
- Canonical hashing is deterministic and rejects non-finite floats.
- Dependency cycles are rejected; rebuild order is topological.
- Proposal rebase is conservative and resets approval on conflict-free rebase.
- Agent gateway injects actor context; the Agent cannot fabricate human confirmation.
- Runtime job recovery is at-least-once; old workers cannot complete reclaimed jobs.
- Two runtime instances detect lost updates rather than overwriting.
- SQLite CAS distinguishes concurrent modification from hash corruption.
- Artifact store deduplicates and detects tampering.
- Discovery is token-free; pairing is role-bound, single-use and cannot escalate.
- Agent tokens are rejected by the human approval route; human tokens are accepted.
- Loopback HTTP rejects non-loopback bind and DNS-rebinding-style Host/Origin.
- Project lease prevents split-brain; expired takeover increments generation.
- CAD bridge registration requires a bridge role and expires without heartbeat.
- A confirmed trace is canonicalized as immutable evidence and is not overwritten by professional geometry.
- Unknown building height survives commit and blocks massing with a structured code.
- Regularization requires human confirmation; intentional rotation is not silently axis-aligned.
- Unknown road class blocks profile-derived widths; explicit user-specified widths remain explicit.
- A T-junction node move is atomic across node, edges and corridors; a stale member rolls back the whole set.
- Height changes stale massing but not footprint-only artifacts; road geometry changes stale road surfaces.
- External geometry enters only through reconcile proposals.
- The domain flow works through `StatefulRuntime`: propose → preview → human approval → commit → stale artifact → rebuild job.
- A synthetic E2E pipeline runs from confirmed trace to DXF readback without importing archived scripts.
- Massing is produced for confirmed heights and blocked for unknown height; stale artifacts are queued in dependency-safe order.
- Shadow analysis preserves unknown blocker height and binds results to a dependency fingerprint.
- DXF XDATA preserves identity, revision, source/representation hashes and ring roles.
- DXF readback detects vertex mutation, unexpected layers and entity-type substitution without crashing.
- Bulge, constant-width, start/end width, thickness and extrusion are now detected; DEV-CAD-003 is closed.
- Height change stales massing/shadow/CAD-IR/DXF while footprint-only artifacts stay current.
- A T-junction move is one atomic changeset; corridor centerline rebuilds from latest canonical edges.
- North bearing is versioned/sourced and stales analysis/delivery without staling building geometry.
- The rebuild worker recomputes, writes, validates and completes jobs with content hashes.
- Delivery comparison uses object IDs, revisions, dependency fingerprints and readback verdict.
- Unrelated commits do not stale CAD-IR or change its fingerprint; relevant road semantic changes do.
- Symbol-table case semantics are contract-tested for layers, linetypes, text styles, blocks and dimstyles.
- Ring keys are content-derived and stable when a sibling MultiPolygon part shifts indices.
- Readback manifests preserve both canonical targets and raw DXF semantics with tolerance 1e-9.
- Serialization differences are categorized separately from profile violations.
- A real AutoCAD 2024 Core Console round-trip preserves 15 entities/XDATA and passes semantic validation with only DXF-version and linetype-case differences.
- The third-party evidence file records scope as partial: LibreCAD/FreeCAD/GUI QA are not executed.
- LWPOLYLINE elevation, MultiPolygon 2-part+hole, layer/linetype/text style/block/dimstyle case and missing XDATA are handled by the living validator.
- Entity categories distinguish profile violations, CAD semantics, interoperability and serialization differences.
- CIRCLE/TEXT Z, text placement, entity style overrides, LWPOLYLINE full semantics and structured validator errors are now detected by positive tests.
- `delivery-comparison.json` hashes are verified against the actual DXF and manifest files.
- Category mapping is contract-synchronized; unknown future codes are `unclassified`, not silently treated as CAD semantics.
- CASE-SKETCH-001 publishes the sketch and image-space geometry; the project metric scale, calibration matrix, DWG/DXF and redline/project coordinates remain private. The pilot-local approximate scale is published only inside the handoff publication block.
- Designer-confirmed semantic labels are recorded separately from geometry: labels are `confirmed`, while all trace and centerline geometry remains `proposed`.
- Road centerlines are `proposed_rough` and carry an explicit no-width-inference/no-alignment scope.
- Five designer-confirmed merged buildings preserve unit counts, connectors and all 63 original component IDs; all 10 close pairs are resolved.
- Unit counts are inferred from sketch dimensions (16 one-unit, 21 two-unit, 17 three-unit, plus one facility); 52 are inferred and 2 confirmed; six length-vs-area conflicts are flagged; the kindergarten is not forced into a unit type.
- Every building carries a provisional 11-floor state with no floor height, massing or FAR; the unit-type library and human-confirmed geometry remain pending.
- The separate-colour skeleton produced 9 components (superseded). The unified brown+blue mask with a 5 px closing gives **1 component, 309 nodes, 333 edges and 121 junction candidates**; the eight nearest-node connectors are rejected negative evidence.
- Road topology carries no width, cross-section, profile, alignment or surface fields.
- The handoff gate rejects proposed geometry, missing or agent review, project-coordinate claims and broken provenance.
- `designer_authorized_pilot` is not a geometry review: the gate blocks it with `HUMAN_OBJECT_REVIEW_REQUIRED` and publishes a review packet instead of canonical/DXF.
- Source file hashes, source object IDs and source geometry hashes are verified; a stale hash, changed geometry or missing object fails closed.
- Road edges must share their declared nodes within a 4 px extraction tolerance, form one component, and have matching corridor coverage; a 10 px endpoint mutation fails.
- The published sketch boundary maps to `SITE-SKETCH-001` with candidate authority; `SITE-001` is not created.
- When a confirmed handoff exists (test double), scope and geometry quality propagate through trace, canonical, CAD-IR, DXF XDATA and the readback manifest; the audit object is not `human_confirmed` for a test double.
- Structured DXF privacy scanning covers TEXT/MTEXT, layer/linetype/style/block names, XDATA and raw bytes.
- CASE-SKETCH-001-HANDOFF-A is blocked: the committed evidence contains no DXF, canonical snapshot or CAD-IR. The downstream 11-entity / 11/11 path is exercised only by an explicitly marked test double.
- The autonomous design synthesis uses the public sketch evidence without a human review gate; it produces a `rule_derived` draft in `proposal_preview`, never `human_confirmed`.
- The design basis is checked at full-site FAR/parking and focus-block spacing/setback/overlap/road clearance/connectivity; the focus block is the detailed design.
- Design road access is a **declared** service relation (`serves_group_ids` + `access_terminal_xy`): each of the 17 groups is served by its own connector, the terminal centreline distance is in [3.4, 3.5] m, and the separate corridor-edge clearance is recorded next to the 3.0 m corridor setback.
- Declared-access negatives are tested: a terminal not on the serving road's centreline is rejected, an orphan declaration is reported as a relation error, and proximity to another group's endpoint cannot serve a group. Dead ends are asserted as 19 = 17 planned group terminals + 2 site-edge termini with 0 unresolved after the M4c-2 resolution (2 trimmed, 3 bridged, 2 site-edge), not as "all justified".
- Main-road alignment is tested as evidence, not just as a metric: Phase 0 replaces "infeasible" with **`local_search_exhausted`** (the 11.565 m gap only proves the between-buildings passage infeasible; the 66.235 m diversion is a candidate baseline); site-boundary containment is a hard gate (`ROAD_BOUNDARY_CONTAINMENT`, margin 0.6735131264650868; repairs MAIN-08/16/18); the geojson overlap fields are split (`main_before` 38.19068149970835, `main_after` 0.0, `new_access` 0.9943558185246757, `total_after` 0.9943558185246756; after the MAIN-08 repair the remaining main conflict was 34.421783197612406 → 0); dead-end `resolved` is bound to `criterion_met` plus a geometry re-check; source edges/ids are preserved and access remains 17/17 declared.
- The multi-candidate experiment tests four deterministic strategies (A/B1/B2/C) on the same conflict; hard gates are recomputed from geometry (self-reported values ignored), boundary violations/capacity/basis changes fail, the Pareto front keeps only non-dominated candidates, explicit ordered preferences produce different recommendations (default B1, road-first A), every candidate gets a reason, and no single black-box score is produced. M4c-3a additionally asserts: all-44-road geometry change by class/terminal (A BR-G-08 2.826 m / G-08 terminal 2.826 m; B1 BR-G-09 7.352 m; B2 13.645 m; C BR-G-08 76.700 m / G-08 terminal 75.315 m), `parent_basis_id` + canonical fingerprint required and mismatches fail `basis_ok`, `HISTORICAL_BOUNDARY_ARCHIVE` vs current-candidate separation (current B1 boundary-compliant 0.6735, pre-repair archived), 11 single-unit objectives with auxiliary excluded from Pareto/preferences, and no mixed-unit composite.
- Visual tests cover deterministic SVG plan/overlay/comparison rendering, matplotlib-optional PNG degradation, and the candidate DXF CLI dry-run/interface gap (`dxf: pending_interface` when the candidate model does not expose design elements).
- Full-site tests assert 55 buildings / 109 units / 2,398 households with focus G-01 preserved; **completeness requires the exact expected 55-id set** (missing/extra/duplicate ids leave the four `FULL_SITE_*` checks deferred), and negative layouts cannot be turned into pass by widening tolerances. Boundary setback, pairwise building overlap, N-S spacing and road clearance are recomputed; the 20 m rule is the **candidate row-rhythm + design-basis assumption, not a universal/regulatory constraint**; the 147.25 m figure is the maximum from an unbounded search under the current fixed-network/uniform-grid/search family, not a proven global minimum. The full-site DXF is **553 entities** with readback **553/553**, XDATA 11 and privacy pass, including `L-OPEN-SPACE` / `POTENTIAL OPEN SPACE ... NOT LANDSCAPE DESIGN` labels and the `DESIGNED GREEN 15.93% - INCOMPLETE` title. `DESIGNED_GREEN_RATIO` is asserted **deferred** (designed green 15.93% <30%; the 61.06% account is potential open space, auxiliary only). They also assert the honest failures: `ROAD_ACCESS_COVERAGE` 0.0 (17 relation errors) and `DEAD_END_RESOLUTION` 17 unresolved. 3.016362 m / 19.999999999999943 m are model-coordinate internal consistency under approximate sketch registration, not survey-grade engineering clearances.
- Co-design tests assert rebuilt access (17 connectors, 16 branch + 1 access, 362.095 m) is generated from geometry rather than edited declarations, and A/B group metrics are recomputed from layouts: **B is hard-valid 29 = 13 pass + 11 info + 5 deferred + 0 fail** (access 17/17, terminal band 3.499999 m, NS 20.0, clearance 3.0164672267820585 m, dead 0); **A fails only `FULL_SITE_ROAD_CLEARANCE` at served-face 2.8250521190593507 m <3 m**. The test suite asserts hard-first recommendation **B** and **A excluded**, an objective metric table with **no score/ranking**, and honest B residuals (12 group splits, group-centroid max 140.12 m / mean 33.99 m, single-building max 278.46 m). Candidate DXF evidence is asserted as delivered: **A 584 entities/readback 584/584** (`INCOMPLETE`), **B 587/587** (`HARD-VALID`), XDATA 11 and privacy; connector sidewalks are clipped (17 / 115.202 m²) and A/B sidewalk overlap is 0.

## 4. What the current tests do **not** prove

- That MCP wire protocol works (no official SDK executed).
- That AutoCAD or FreeCAD host plug-ins work (no host installed).
- That the runtime is production-safe, crash-safe on power loss, or multi-host.
- That SQLite is integrated into the runtime save/load path (it is a separate spike).
- That real sketch recognition, geometry construction, road design or building regularization works.
- That CASE-SKETCH-001's trace is human-confirmed or accurate: semantic labels are designer-confirmed, but geometry is proposed and no Hausdorff/IoU metrics against a human reference exist yet.
- That building merge/split, 支路/入户路 separation or the canonical Building/Road handoff are resolved.
- That the unified-mask road topology is professionally correct; its 121 junctions are proposed candidates, not designed intersections.
- That the full CASE-SKETCH-001 sketch is human-confirmed, or that the selected pilot subset has been object-level reviewed; no real object is `confirmed_for_pilot` yet.
- That the autonomous design draft is construction-ready, code-compliant, or the designer's unit-type library; full-site checks are a research draft and road corridors are schematic.
- That the schematic main-road alignments are professional alignment, junction or profile design, or that full-site road clearance is a coordinated design; entrance proximity is not a designed driveway. The overlap elimination/boundary containment and the 7 dead-end resolutions are asserted by tests, but only within the recorded schematic scope. The full-site experiment passes clearance/NS-spacing/boundary/overlap/green but **fails** access coverage and dead-end resolution; it is not the canonical design.
- That the candidate recommendation is a professional or final decision, that the candidate set is exhaustive, or that the 11 single-unit objectives form a complete quality model; the current B1 is the boundary-repaired candidate (margin 0.6735), its pre-repair 66.235 m form is historical archive only, and no candidate is human-confirmed or code-compliant.
- That candidate DXF evidence is committed for every candidate; the reproducible path exists, but a candidate without design elements records `dxf: pending_interface` instead of silently pretending an editable DXF exists.
- That the autonomous draft has been adopted or officially issued; it is a proposal the designer may edit or adopt.
- That a DXF produced by the test double is third-party CAD evidence or design-office compliant; readback is same-library ezdxf.
- That the colour-based road class is confirmed; it is inferred from brown/blue pixel majority.
- That road width, cross-section, profile or alignment has been designed; none is derived.
- That the domain slice's simplified regularization (axis-aligned envelope) or road centerline merge is professionally correct.
- That DXF output is compliant with any real project/design-office profile.
- That a third-party CAD application can open/save/read the DXF with semantic equivalence.
- That third-party CAD interoperability is complete: only one AutoCAD 2024 Core Console host was executed; LibreCAD, FreeCAD and GUI visual QA remain.
- That arcs/splines are covered; the current delivery entity set is LWPOLYLINE, CIRCLE and TEXT.
- That a road surface geometry is generated or professionally designed (deferred in E2E-002).
- That paper-space content is validated (explicitly out of scope).
- That same-library ezdxf readback is third-party CAD interoperability (it is not; DEV-CAD-006 remains open).
- That the E2E DXF profile matches any real design-office profile.
- That IFC round-trip preserves identity.
- That shadow analysis matches an independent engine.
- That any Chinese regulatory threshold is satisfied.

Every test file and contract carries this scope boundary. Do not delete or weaken the non-claim statements when adding features.

## 5. Test design rules

1. **Fail closed.** Unknown or unsupported input returns a structured error code, never a default pass.
2. **No silent defaults.** Missing height, scale, north, profile or time must remain `unknown`/`blocked`.
3. **One behavior per test.** Tests are named as contracts, not implementation details.
4. **Adversarial by default.** Every feature needs at least one negative case: stale writer, tampered payload, role escalation, missing prerequisite, malformed entity.
5. **Scope tags.** A test proves only its named scope. Do not rename a scoped test into a global claim.
6. **Fixtures are immutable evidence.** Changing a fixture requires a new revision and a changelog entry.

## 6. Adding a new test layer

When introducing a domain or integration suite:

1. Create a fixture under `fixtures/` with a schema ID and explicit `synthetic_only` / evidence status.
2. Add the test under `tests/<layer>/`.
3. Add the suite to CI.
4. Document what it proves and what it does not prove in this file.
5. If the test depends on an external host (AutoCAD, MCP SDK), mark it `blocked` rather than skipped silently, and record the blocker.

## 7. Regression policy

A defect found by an independent review or user report becomes a named regression test **before** the fix. The test name references the defect ID where one exists (for example `DEV-CAD-001`). Fixes without a failing test are not accepted.
