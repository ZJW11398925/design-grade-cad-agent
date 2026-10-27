# Changelog

All notable changes to the formal repository are recorded here. Research snapshots keep their own versions in `research/archive/`.

## 0.13.0 — 2026-10-27

### Fixed

- **Withdraw the 0.12.0 human-review claim.** The committed CASE-SKETCH-001-HANDOFF-A review record was a designer **authorization to run a pilot**, not an object-level geometry or coordinate review. It is reclassified as `designer_authorized_pilot`; the pilot blocks with `HUMAN_OBJECT_REVIEW_REQUIRED`.
- **Preserve confirmation scope.** `confirmation_scope`, `geometry_quality` and `review_kind` now propagate through trace objects, canonical objects, CAD-IR provenance, DXF XDATA and the readback manifest. A `full_case` review rejects `confirmed_for_pilot`.
- **Stop the sketch boundary becoming `SITE-001`.** A published sketch boundary maps to `SITE-SKETCH-001` with candidate authority; only an authoritative private site reference may create `SITE-001`.
- **Correct the coordinate claim.** The transform is `uniform_scale_translation_yflip` in `LOCAL-XY-ZUP`, not a homography; `homography_applied: false`, `shape_correction: none`, `axis_orientation: unknown`; per-object area/perimeter/centroid sensitivity recorded.
- **Verify source integrity.** Source file SHA-256, source object ID and canonical source-geometry hash are checked; a stale hash, changed geometry or missing object fails closed.
- **Verify road topology.** Edge endpoints must match declared nodes within a 4.0 px tolerance, the selected graph must be one component with consistent junction degrees and corridor coverage. The selected data's max offset is 3.606 px; two edges were stored in reverse direction and are normalized and recorded.
- **Add a structured DXF privacy scan** over TEXT/MTEXT, layer/linetype/style/block names, XDATA and raw bytes.

### Added

- `contracts/sketch-domain-handoff-v0.2.yaml`; v0.1 is marked superseded.
- Trace/canonical review metadata, boundary authority and site canonical identity.
- `review-packet.html` / `review-packet.json`, `review-request.yaml` and an unsigned `review-confirmation-template.yaml` for the designer.
- `src/dgcad_e2e/sketch_review.py` and `src/dgcad_e2e/privacy.py`.
- Blocked evidence: `blocked.json`, `integrity.json`, `road-topology.json`, `coordinate-sensitivity.json`, `provenance-map.json`.
- `docs/e2e/sketch-handoff-a/history-0.12.0/` preserves the superseded executed pilot.
- `tests/test_sketch_handoff.py` grows to 32 tests; `tests/e2e/test_sketch_handoff_a.py` to 6.

### Verified

- **206 passed**.
- The committed handoff is blocked: no canonical model, CAD-IR or DXF is published; source integrity (3 files, 7 objects) and road topology pass.
- A test-double run still reaches 11 DXF entities, audit 0/0 and 11/11 readback, with `confirmation_scope=pilot_subset` in trace, canonical, CAD-IR, XDATA and the manifest, and `SITE-SKETCH-001` at candidate authority.
- Synthetic E2E-001/002/003/003b and CAD delivery remain green.

### Scope

- The selected real subset still needs a designer object-level review; the test double is not published as human confirmation.
- `EP-R1-SKETCH-001` remains in progress; `R1-G07` remains partial.
- Same-library `ezdxf` readback is not third-party evidence.
- The pilot-local approximate scale is published under the handoff publication block; the private calibration matrix, DWG, redline and project coordinates are not.

## 0.12.0 — 2026-10-28

### Added

- **CASE-SKETCH-001-HANDOFF-A**: a selected real sketch subset passes an explicit human pilot-scope geometry gate, enters the existing Domain Slice, and reaches Canonical → CAD-IR → DXF → readback.
- `contracts/sketch-domain-handoff-v0.1.yaml`.
- `src/dgcad_domain/sketch_handoff.py`: source→trace→canonical mapping, coordinate handoff, human review gate, domain fixture generation.
- `src/dgcad_e2e/sketch_handoff_project.py`: `ConfirmedTraceScene` → `build_initial_scene` → runtime proposal/approval/commit → CAD-IR → DXF readback.
- `fixtures/sketch/CASE-SKETCH-001-HANDOFF-A/`: handoff, human review record, domain fixture and mapping.
- `docs/e2e/sketch-handoff-a/`: handoff summary, canonical snapshot, CAD-IR, DXF, readback manifest, validation and provenance map.
- `scripts/sketch_intake/build_handoff_a.py` and `scripts/e2e/run_sketch_handoff_a.py`.
- `tests/test_sketch_handoff.py` (14) and `tests/e2e/test_sketch_handoff_a.py` (2).

### Verified

- 7 selected real objects: site boundary, ordinary building, merged building, green, two main-road edges, one branch edge and one T-junction.
- DXF: 11 entities, audit 0/0; readback 11/11 pass; CAD-IR `pass_with_scope_limits` with two `UNKNOWN_HEIGHT_ALLOWED` warnings.
- Trace evidence unchanged after all commits; massing blocked for unknown height; road profiles blocked with `ROAD_CLASS_UNCONFIRMED`; no width derived.
- Local metric handoff: 2.438 px/m, declared range 2.25–2.89; `project_coordinates: false`; no DWG/project coordinates published.
- **184 passed**.

### Scope

- Pilot subset only; `confirmed_for_pilot` is not full-case or survey-grade.
- `EP-R1-SKETCH-001` remains in progress; `R1-G07` remains partial.
- Same-library `ezdxf` readback; not third-party CAD evidence.
- Shadow analysis not run; no environmental result.
- Version `0.12.0`.


## 0.11.0 — 2026-10-28

### Fixed

- **Corrected the road-topology process.** The design's road network is one system; the earlier separate brown/blue skeletons cut it at colour boundaries and produced nine artificial components. That result is superseded.
- Unified brown+blue road mask, ≥300 px component filter, **5 px ellipse closing** (4 px leaves five components; 5 px is the smallest tested kernel restoring one component).
- Unified network: **1 connected component**, 309 nodes, 333 edges, 111 endpoints, **121 junction candidates**, 25 cycles; 65 main-road and 268 branch/access edges.
- Colour is a road-class attribute, not a topology separator; junctions are skeleton graph nodes, not inferred connectors.
- The eight nearest-node connectors remain rejected in `road-connectors-rejected.geojson` as negative evidence; they are not used.
- Contract, tests, README and status updated; **168 passed**.
- Version `0.11.0`.

### Scope

- The 121 junctions are proposed candidates and need review.
- No road width, cross-section, profile, alignment or surface.
- Blue still combines 支路 and 入户路; image-space only; DWG/redline/project coordinates remain private.


## 0.10.1 — 2026-10-27

### Changed

- **Withdrew inferred road connectivity.** The eight nearest-node connectors are rejected by designer review and retained in `road-connectors-rejected.geojson` as negative evidence.
- Road topology state is `as_drawn_unresolved`: 306 nodes, 312 edges, 9 components, 129 endpoints, 99 junctions, 15 cycles; gaps 15.62–76.06 px remain open.
- Removed the 320-edge/one-component connected claim; no connected graph is claimed.
- `contracts/sketch-evidence-v0.1.yaml` updates `road_topology` states, required fields and rules.
- `tests/test_road_topology.py` updated; **168 passed**.
- Version `0.10.1`.


## 0.10.0 — 2026-10-27

### Added

- Proposed road network topology from the 312 sketch centerlines:
  - as-drawn: 306 nodes, 312 edges, 9 components, 129 endpoints, 99 junctions, 15 cycles; 41 main-road and 271 branch/access edges;
  - connected with **8 inferred nearest-node connectors**: 320 edges, 1 component, 120 endpoints, 103 junctions, 15 cycles; 41 main-road and 279 branch/access edges.
- `docs/e2e/sketch-001/road-network-proposed.geojson`, `road-nodes-proposed.geojson`, `road-topology-summary.json`, `road-network-overlay.png`.
- `contracts/sketch-evidence-v0.1.yaml` adds `road_topology`.
- `tests/test_road_topology.py`: 3 tests. Total **168 passed**.
- `pyproject.toml` version corrected from `0.9.1` to `0.10.0`.

### Scope

- Every inferred connector is marked `inferred_nearest_endpoint`, `review_state: proposed`, and is **not** a designed road link; gaps span 15.62–76.06 px.
- No road width, cross-section, profile, alignment, junction turn geometry or surface is derived.
- Blue still combines 支路 and 入户路; no subtype separation.
- Image-space topology only; no project coordinates or metric lengths.
- **Superseded in 0.10.1:** inferred connectivity withdrawn; only the as-drawn topology is claimed.
- Version `0.10.0`.


## 0.9.2 — 2026-10-27

### Changed

- Applied the three remaining designer-confirmed merges:
  - `SK-BLD-MRG-0003`: 0001 + 0037 (kindergarten/facility).
  - `SK-BLD-MRG-0004`: 0019 + 0058.
  - `SK-BLD-MRG-0005`: 0027 + 0059.
- Buildings change from 58 to **55** (50 standalone + 5 merged); all **63 original red components** remain preserved, with **13** merged components.
- Inferred **1/2/3-unit** counts for the 52 residential buildings without a confirmed count: **16 one-unit, 21 two-unit, 17 three-unit**. Two are confirmed (M-001/M-002); the kindergarten M-003 is excluded as a facility.
- Six long bars (`0009`, `0010`, `0011`, `0013`, `0015`, `0018`) are 3-unit by length but 2-unit by area; the conflict is recorded for review.
- `contracts/sketch-evidence-v0.1.yaml` adds `unit_inference` and `inferred` unit-count state.
- Sketch suite: **11 tests**; total **165 passed**.

### Scope

- Unit counts are inferred from sketch dimensions, not confirmed, except M-001/M-002.
- No height, massing, FAR or unit-mix is derived; footprints remain sketch placeholders pending the unit-type library.
- No human-confirmed trace, fidelity metrics or canonical handoff yet.
- Version `0.9.2`.


## 0.9.1 — 2026-10-27

### Changed

- Applied the designer's building merges in CASE-SKETCH-001:
  - `SK-BLD-MRG-0001`: 0046 + 0047 + 0060 (3 units) with connectors 0062 + 0063.
  - `SK-BLD-MRG-0002`: 0030 (2 units) + 0053 (1 unit).
- Building count changes from 63 to **58** (56 standalone + 2 merged); all **63 original red components** are preserved in `building-components.geojson`.
- Every building records **11 floors** as `proposed_initial`; no floor height, massing, FAR or unit-mix is derived.
- Every building footprint is marked `sketch_placeholder_pending_unit_type_library`; the unit-type library is pending.
- Public trace, case summary, README, contract and tests updated. Sketch suite: **10 tests**; total **164 passed**.
- Remaining close pairs `0001/0037`, `0019/0058` and `0027/0059` stay separate pending review.

### Scope

- Unit counts are confirmed only for the two merged buildings; other buildings remain unknown.
- No human-confirmed trace, fidelity metrics or canonical handoff yet.
- Version `0.9.1`.

## 0.9.0 — 2026-10-27

### Added

- **CASE-SKETCH-001**: first Tier B designer-sketch intake.
- Public package `docs/e2e/sketch-001/`: sketch raster, image-space trace, rough road centerlines, overlays, ambiguity regions and case summary.
- `contracts/sketch-evidence-v0.1.yaml`.
- `tests/test_sketch_evidence.py`: 8 tests for privacy/leak boundaries, image-space-only geometry, designer-confirmed semantics and rough-centerline scope.
- Designer-confirmed semantics: metre; red buildings; magenta underground garage entrances; brown main roads; blue branch/access roads; green cluster spaces; existing buildings removed; top crop clips only a road segment.
- Proposed trace: 63 building candidates, 3 garage entrances, 12 green spaces, 9 road areas, 1 site boundary; 312 rough centerline candidates (main road 1 component, blue network 8 components).

### Verified

- **162 passed**.
- All trace and centerline geometry is image-space (`SKETCH-IMG-001`) and `review_state: proposed`; semantic labels are separately `confirmed`.
- The public package contains no DWG/DXF path, project coordinates or metric scale.
- Calibration is a reviewed approximate homography: mean 24.51 px, max 43.42 px; not survey-grade.

### Scope

- No human-confirmed trace or fidelity metrics (Hausdorff/IoU/topology).
- No building merge/split decision; 10 close pairs are listed for review.
- 支路 and 入户路 are not separated within the blue class.
- Road centerlines are `proposed_rough`; no alignment, width, cross-section, junction turn geometry or surface.
- No canonical Building/Road handoff from this sketch yet.
- DWG/DXF, redline/project coordinates and metric scale remain private.
- Version `0.9.0`.

## 0.8.0 — 2026-10-27

### Added

- Real third-party CAD evidence: **AutoCAD 2024 Core Console** opened, saved and read back the DGCAD DXF in an isolated profile.
- `contracts/third-party-roundtrip-v0.1.yaml`.
- `scripts/third_party/autocad_core_roundtrip.py` — reproducible host harness.
- `docs/e2e/third-party-003c/` evidence: input/roundtrip DXF, environment, comparison, save script and console output.
- `docs/e2e/third-party-003c.md` executed report.
- `tests/e2e/test_e2e_003c_third_party.py`: 2 evidence-integrity tests.

### Verified

- Verdict: `semantic_pass_with_serialization_differences`.
- Preserved: 15 entities, 15 XDATA records, layers, colors, lineweights, blocks/dimstyles/text styles, units, geometry, audit 0/0.
- Differences: DXF version `AC1024 → AC1032` (R2010 → R2018) and layer linetype case `CONTINUOUS → Continuous`.
- Validator passes with an R2018 semantic-equivalence profile.

### Scope

- Matrix is **partial**: AutoCAD 2024 Core Console executed; LibreCAD, FreeCAD and AutoCAD GUI visual QA are not executed.
- Synthetic fixture only; modelspace only; no real design-office profile.
- `DEV-CAD-006` / #6 remains open for the remaining matrix.
- Test suite: **154 passed**.
- Version `0.8.0`.

## 0.7.0 — 2026-10-27

### Added

- CAD-IR fingerprint decoupling: global scene revision is `built_from_scene_revision` metadata, excluded from the semantic hash (#16).
- Full CAD-IR dependency registration for every exported object's semantic/geometry/parameter revisions.
- Symbol-table case semantics (`symbol_name_policy`): layers, linetypes, text styles, required blocks/dimstyles/text styles, with original spelling preserved (#5).
- Stable `ring_key` in XDATA, content-derived rather than part/ring-index-derived; `RING_KEY_MISMATCH` (#1).
- Readback manifest records `canonical_target` and `raw_dxf_semantics` per entity; numeric tolerance/version documented (#4).
- Serialization-difference vs profile-violation category test (#8).
- `tests/e2e/test_e2e_003b_semantics.py`: 11 tests.
- `docs/e2e/semantic-dependency-003b.md`: executed 3b report.

### Changed

- Test suite: **152 passed**.
- `contracts/e2e-adversarial-v0.1.yaml` and `contracts/cad-ir-v0.1.yaml` updated for symbol tables, ring keys and raw/canonical evidence.
- Roadmap: Milestone 3b complete; 3c (third-party CAD evidence) next.
- Issues #1, #4, #5, #8, #16 closed with evidence; #6 remains for 3c.
- Version `0.7.0`.

### Scope

- Same-library `ezdxf` only; no third-party CAD evidence.
- Modelspace only.
- Arcs/splines are outside the current delivery entity set (LWPOLYLINE/CIRCLE/TEXT).
- No road surface geometry, real sketch input, IFC or standards compliance.

## 0.6.0 — 2026-10-27

### Fixed

- Milestone 3a validator hardening: all 15 strict xfails are now positive checks.
- Structured `VALIDATOR_ERROR`: malformed DXF and validator-internal exceptions return a structured failure, never a pass or uncaught exception.
- Entity-level style overrides: color, linetype, lineweight, true color and transparency are checked against the BYLAYER policy.
- CIRCLE center Z and TEXT insertion Z are checked.
- TEXT rotation, width factor, horizontal and vertical alignment are checked against the delivery profile.
- LWPOLYLINE full semantics: bulge, start/end width, constant width, thickness, extrusion, elevation and closed flag.
- `DeliveryProfile.text_style_policy` and compiler support for explicit TEXT rotation/width/alignment.

### Changed

- `contracts/e2e-adversarial-v0.1.yaml`: all scenarios are now detected or pass; no strict xfail remains in Milestone 3a.
- Issue-category mapping expanded for the new checks; contract-sync test still enforces exact coverage.
- `tests/test_cad_delivery_contracts.py`: bulge and constant-width tests are now positive.
- Test suite: **141 collected / 141 passed / 0 xfailed**.
- Version `0.6.0`.

### Scope

- Closed #3 (LWPOLYLINE validation), #7 (structured validator errors), #17 (entity style overrides) and #18 (CIRCLE/TEXT semantics).
- `DEV-CAD-004` remains open for raw/canonical geometry preservation.
- `DEV-CAD-001/005/006/008/011` remain open for Milestone 3b/3c.
- No third-party CAD round-trip, paper-space validation, IFC, real sketch or road surface geometry.

## 0.5.1 — 2026-10-27

### Fixed

- `delivery-comparison.json`: renamed `manifest_sha256` (which actually stored the DXF hash) to `dxf_sha256`; added `readback_manifest_sha256` computed from the written manifest file.
- DXF readback manifest: renamed its own `sha256` field to `dxf_sha256` to remove ambiguity.
- Issue-category default changed from `cad_format_semantics` to `unclassified`; unknown future codes are now visible instead of silently misclassified.
- Added a contract-sync test ensuring every `DxfIssue` code has an explicit category and unknown codes remain `unclassified`.

### Changed

- `contracts/e2e-mutation-v0.1.yaml`: comparison fields updated to `dxf_sha256` and `readback_manifest_sha256`.
- `contracts/e2e-adversarial-v0.1.yaml`: added `unclassified` category and removed the non-DXF `MASSING_BLOCKED_INVALID_FOOTPRINT` code.
- `contracts/cad-ir-v0.1.yaml`: documented that `ring_index` is global within a CAD object (part order, then ring order); ring identity stability across revisions remains a Milestone 3 decision.
- Status one-line now includes E2E-003; duplicate third-party round-trip row removed.
- Symbol-table scope wording narrowed to one layer linetype reference case; full symbol-table equivalence remains #5.
- Issue #2 narrowed to safe entity dispatch and closed after evidence; structured `validator_error` stays with #7.
- Milestone 3 scope now explicitly includes DEV-CAD-009, 010 and 011.
- Test suite: **141 collected / 126 passed / 15 xfailed**.

### Verified

- `dxf_sha256` matches the actual DXF file; `readback_manifest_sha256` matches the actual manifest file.
- Category contract and implementation are synchronized; unknown codes are `unclassified`.
- E2E-003 remains 7 positive / 13 strict xfail.

## 0.5.0 — 2026-10-27

### Added

- `contracts/e2e-adversarial-v0.1.yaml`: adversarial scenario, category, expected outcome and issue-mapping contract.
- `tests/e2e/test_e2e_003_adversarial.py`: 19 scenarios (6 positive, 13 strict xfail) covering geometry, style, identity, serialization and validator-error gaps.
- `docs/e2e/adversarial-delivery-003.md`: executed E2E-003 audit, results and boundaries.
- `DxfIssue.category` and an issue-category mapping: cad_format_semantics, interoperability, profile_violation, serialization_difference, validator_error.
- `delivery-comparison.json` generated with the DXF: object IDs, canonical revisions, CAD-IR fingerprint, readback verdict, audit counts, manifest hash and profile identity.
- Issues #16 (DEV-CAD-011 dependency fingerprint consistency), #17 (DEV-CAD-009 entity style overrides), #18 (DEV-CAD-010 CIRCLE/TEXT semantics).

### Changed

- `contracts/e2e-mutation-v0.1.yaml`: `manifest_comparison` now explicitly names `delivery-comparison.json` as a composite artifact.
- `pyproject.toml`: version `0.5.0`.
- Test suite: **140 collected / 125 passed / 15 xfailed**.
- Status/testing wording for third-party CAD evidence is unified: one user-run AutoCAD core-engine round-trip; no repeatable third-party matrix.

### Verified

- MultiPolygon with 2 parts + 1 hole round-trips as 3 entities with audit 0/0.
- Symbol-table linetype case is semantically equal.
- Missing XDATA returns a structured issue.
- LWPOLYLINE elevation is detected.
- All remaining known gaps are strict xfails with accurate issue links; no silent acceptance.

## 0.4.0 — 2026-10-27

### Added

- `src/dgcad_e2e/living_project.py`: mutation/rebuild project with canonical project context, deterministic rebuild worker and scoped artifact registry.
- `contracts/e2e-mutation-v0.1.yaml`: mutation, rebuild, manifest-comparison and road-surface-deferral contract.
- `docs/e2e/dependency-mutation-002.md`: executed E2E-002 result.
- 6 E2E-002 tests: height change, T-junction move, north bearing, real rebuild execution, manifest comparison, road-surface deferral.
- `rebuild_road_corridor_proposal`: rebuilds a corridor centerline from latest canonical edge geometry, never from the trace fixture.
- Project context `PROJECT-CONTEXT-001` versions north bearing with an explicit source.
- DXF source hash now includes CAD-IR provenance, so analysis-derived sensor metadata changes when the shadow fingerprint changes.

### Changed

- `pyproject.toml`: version `0.4.0`.
- Test suite: **121 collected / 119 passed / 2 xfailed**.
- Road surface geometry is explicitly deferred: no `SURFACE-R-002` artifact is registered or claimed as generated.

### Verified

- Height change stales massing, shadow, CAD-IR and DXF; footprint-only artifacts stay current.
- Node move is one atomic changeset; corridor centerline is rebuilt from current canonical edges.
- North bearing change stales shadow and delivery but not building footprint geometry.
- Rebuild worker recomputes, writes, validates and completes jobs with content hashes.
- Manifest comparison uses object IDs, revisions, dependency fingerprints and readback verdict.

## 0.3.0 — 2026-10-27

### Added

- `src/dgcad_analysis/`: synthetic solar/shadow baseline with explicit solar position, unknown/estimated/confirmed blocker semantics and dependency fingerprint.
- `src/dgcad_cad/`: minimal CAD-IR, DXF R2010 compiler with `DESIGN_GRADE` XDATA, and independent readback validator + manifest.
- `src/dgcad_e2e/`: living pipeline orchestration from DOMAIN-SLICE-001 through Runtime canonical commits, massing, shadow, CAD-IR, DXF and readback.
- `contracts/cad-ir-v0.1.yaml` and `contracts/e2e-pipeline-v0.1.yaml`.
- `fixtures/e2e/living-pipeline-001.yaml` with 4 analysis sample points and a synthetic DXF profile.
- `fixtures/domain/domain-slice-001-r2.yaml`: fixture revision 2 adds explicit road `trace_refs`; revision 1 is retained.
- `docs/e2e/living-pipeline-001.md`: executed E2E-001 result and scope report.
- Tests: Analysis 7, CAD delivery 9 (2 xfail), E2E 8. Total suite now **115 collected / 113 passed / 2 xfailed**.

### Changed

- `pyproject.toml`: version `0.3.0`; added `ezdxf>=1.4`.
- Domain road corridors now carry `trace_ref` and `trace_refs`; domain scene validation no longer reports `TRACE_REF_MISSING` for roads.
- `contracts/domain-contract-v0.1.yaml`: `road_corridor.required` now explicitly includes `trace_refs`.
- CAD-IR road provenance now records the source road trace reference.

### Known gaps

- `DEV-CAD-003` / issue #3: bulge and constant-width mutations are recorded as strict xfail in E2E-001.
- No third-party CAD round-trip, IFC, real sketch input, standards profile or independent shadow engine.

## 0.2.0 — 2026-10-27

### Added

- `src/dgcad_domain/`: minimal Building/Road domain slice over the Foundation/Runtime contracts.
  - confirmed trace fixture loader with immutable evidence objects;
  - Building intent, footprint preservation and regularization candidate with diff metrics;
  - Road graph, corridor, explicit cross-section and class/profile resolution gate;
  - T-junction atomic multi-object change set;
  - massing and road-surface derived artifacts with dependency keys;
  - structured domain validators;
  - StatefulRuntime integration: propose → preview → human approval → commit → stale → rebuild job.
- `fixtures/domain/domain-slice-001.yaml` with intentional difficulty cases (irregular footprint, 17° rotation, unknown height, unknown road class, T-junction).
- 26 domain contract tests; total suite now **91 tests**.

### Changed

- `pyproject.toml`: version `0.2.0`; added `shapely>=2.0`.
- Status, roadmap, testing and architecture docs now reflect the implemented domain slice.
- Research-to-product map marks the minimal Building/Road schemas as promoted.

### Research promotion and governance

- `docs/research-to-product-map.md`: promotion status for every research artifact.
- `docs/architecture/authority.md`: living authority and lock model.
- `contracts/canonical-site-ir-v0.4.yaml`: promoted Canonical Site IR (no semantic change from v0.3).
- `contracts/evidence-gate-register-v0.2.yaml`: promoted R1 evidence gate register.
- `contracts/domain-contract-v0.1.yaml`: minimal living Building/Road domain contract.
- Branch protection on `main` with the four CI matrix checks and PR requirement.
- GitHub issues `DEV-CAD-001..008` for accepted DXF/validator defects (implementation deferred).

## 0.1.0 — 2026-10-27

### Added

- Formal repository structure: `src/`, `tests/`, `contracts/`, `fixtures/`, `spikes/`, `docs/`, `research/`.
- Canonical source tree consolidating the verified R1 deployment-entry v0.2 prototype:
  - `dgcad_foundation` — identity, revisions, authority, atomic changes, preview, dependency, audit, migration, gateway.
  - `dgcad_runtime` — stateful project runtime, proposals, approvals, jobs, artifacts, idempotency, recovery.
  - `dgcad_deployment` — SQLite/WAL spike, content-addressed artifacts, sidecar lifecycle, discovery/pairing/sessions, local HTTP control plane, CAD bridge registry.
- Contract suite: **65 tests** (Foundation 21, Runtime 22, Deployment 8, Lifecycle 14).
- CI workflow for Ubuntu/Windows × Python 3.11/3.13, including coverage on the primary job.
- Project documentation: architecture overview, status matrix, roadmap, testing strategy, contribution workflow, ADR-0001.
- Apache-2.0 license.
- Research archive: full R0 v0.19 workspace and R1 deployment-entry v0.2 snapshot.

### Notes

- This release is a workspace consolidation, not a capability promotion. All prior non-claims remain in force.
- The vendored research-methodology skill copy is intentionally excluded from the public repository.
- Known DXF/validator defects (`DEV-CAD-001..008`) remain accepted development work.
