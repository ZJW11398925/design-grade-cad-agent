# Changelog

All notable changes to the formal repository are recorded here. Research snapshots keep their own versions in `research/archive/`.

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
