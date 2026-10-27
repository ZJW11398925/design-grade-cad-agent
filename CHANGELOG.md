# Changelog

All notable changes to the formal repository are recorded here. Research snapshots keep their own versions in `research/archive/`.

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
