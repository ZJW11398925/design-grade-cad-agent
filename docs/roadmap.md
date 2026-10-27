# Roadmap

The roadmap is organized so that every milestone has an executable exit criterion. A milestone is not "done" because a demo looks plausible; it is done when the named tests or evidence packages pass within a declared scope.

## Milestone 0 — Formal workspace and CI (current)

- [x] Consolidate Foundation, Runtime and Deployment into a single `src/` tree.
- [x] Preserve R0 v0.19 and R1 deployment-entry v0.2 under `research/archive/`.
- [x] Establish 65-test contract baseline.
- [x] Add CI matrix (Ubuntu/Windows, Python 3.11/3.13).
- [x] Publish public repository.
- [ ] Enable branch protection and require the CI check on `main`.

**Exit:** green CI on the default branch; repository structure documented.

## Milestone 1 — Domain slice entry (`NEXT-R1-MVP-001`)

Input: human-confirmed Trace/Intent fixture. Output: canonical Building/Road objects, proposal → preview → dependency → validator flow.

- [ ] Define `dgcad_domain` package boundary and typed domain objects (Building, RoadCorridor).
- [ ] Define a minimal confirmed Trace/Intent fixture and its authority rules.
- [ ] Implement Building adapter: trace footprint → professional candidate → canonical proposal.
- [ ] Implement Road adapter: centerline + simple cross-section → canonical proposal.
- [ ] Register derived artifacts and stale propagation for both domains.
- [ ] Add a domain-level validator contract with structured issues.
- [ ] Tests: at least 20 new domain contract tests.

**Exit:** one confirmed synthetic site can produce canonical building and road objects through the runtime, with preview isolation and correct staleness.

## Milestone 2 — E2E integration suite

- [ ] Port the R0 synthetic E2E pipeline into `tests/e2e/` as pytest fixtures.
- [ ] Cover: fixture → solar/shadow → CAD-IR → DXF → readback manifest.
- [ ] Run the pipeline in CI on Ubuntu and Windows.
- [ ] Freeze expected object IDs, entity counts, hashes and audit results.
- [ ] Add mutation tests for: height revision, north bearing, non-zero Z, style override, unexpected layer, entity-type substitution.

**Exit:** E2E suite runs in CI with no external engine; known DXF defects either fixed or explicitly xfailed with issue links.

## Milestone 3 — CAD validator hardening

Implement `DEV-CAD-001..008` and add third-party round-trip gates.

- [ ] MultiPolygon/part/ring contract.
- [ ] Safe entity dispatch and `ENTITY_TYPE_MISMATCH`.
- [ ] Full LWPOLYLINE semantics (bulge, width, elevation, thickness, extrusion).
- [ ] Symbol-table case-insensitive equivalence with preserved spelling.
- [ ] Structured validator issue schema on every failure path.
- [ ] AutoCAD/LibreCAD/FreeCAD round-trip matrix (manual or CI-hosted).

**Exit:** real third-party round-trip produces `semantic_pass` or `semantic_pass_with_serialization_differences` per policy.

## Milestone 4 — Evidence packages

| Package | Capability unlocked |
|---|---|
| `EP-R1-SKETCH-001` | real sketch → trace reliability |
| `EP-R1-ROAD-001` | road topology/alignment/profile |
| `EP-R1-IFC-001` | IFC identity round-trip |
| `EP-R1-ENV-001` | independent shadow engine |
| `EP-R1-PROFILE-001` | real project/design-office profile |

Each package has its own decision question, raw evidence, metrics, failure policy and scope-leakage prohibition. No package is a checklist for production release.

## Milestone 5 — Production hardening (not started)

- Durable store integration (SQLite or chosen alternative) into runtime save/load.
- Windows ACL/DPAPI credential handling and installer trust.
- MCP wire-level conformance with the official SDK.
- Multi-process and crash-recovery testing.
- Performance and large-project benchmarks.

## Ordering rule

Do not start a later milestone merely because an earlier one has code. The exit criteria are the gate. Evidence packages block capability claims independently of code progress.
