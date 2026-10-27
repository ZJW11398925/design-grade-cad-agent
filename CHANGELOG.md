# Changelog

All notable changes to the formal repository are recorded here. Research snapshots keep their own versions in `research/archive/`.

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
