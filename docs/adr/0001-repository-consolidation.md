# ADR-0001: Consolidate research snapshots into a formal repository

- Status: accepted
- Date: 2026-10-27
- Deciders: project maintainer

## Context

The project arrived as two archives:

1. `design-grade-cad-agent-r0-starter-v0.19.zip` — a 489-file research workspace containing five acquisition batches, architecture documents, synthetic benchmarks, an E2E slice and five successive Foundation/Runtime/Deployment prototypes.
2. `design-grade-cad-agent-r1-deployment-entry-v0.2.zip` — a clean delivery snapshot of the final deployment lifecycle prototype (65 tests).

Each prototype directory contained near-identical copies of the Foundation and Runtime packages. There was no single canonical source tree, no package metadata, no CI and no public repository.

## Decision

1. Create a formal repository at the workspace root.
2. Make `src/dgcad_foundation`, `src/dgcad_runtime` and `src/dgcad_deployment` the **only canonical source tree**, taken from the latest verified prototype (r1-deployment-entry v0.2).
3. Make `tests/` the canonical executable contract suite (65 tests).
4. Move both original deliverables intact into `research/archive/` as historical evidence. They are read-only in spirit; corrections go into new documents.
5. Do not publish the vendored copy of the private research-methodology skill; record its version only.
6. License the repository under Apache-2.0.
7. Add CI for Ubuntu/Windows and Python 3.11/3.13.

## Consequences

- One source of truth for code; duplicate prototype copies no longer compete.
- Historical provenance is preserved without polluting the build.
- CI can enforce the contract suite from day one.
- The archive may contain stale paths and status labels; readers must prefer root docs and tests.
- A future refactor can rename `dgcad_*` packages under a single `dgcad` namespace, but that is deliberately deferred to avoid changing imports and tests during consolidation.
