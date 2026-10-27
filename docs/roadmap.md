# Roadmap

The roadmap is organized so that every milestone has an executable exit criterion. A milestone is not "done" because a demo looks plausible; it is done when the named tests or evidence packages pass within a declared scope.

## Milestone 0 — Formal workspace and CI (complete)

- [x] Consolidate Foundation, Runtime and Deployment into a single `src/` tree.
- [x] Preserve R0 v0.19 and R1 deployment-entry v0.2 under `research/archive/`.
- [x] Establish 65-test contract baseline.
- [x] Add CI matrix (Ubuntu/Windows, Python 3.11/3.13).
- [x] Publish public repository.
- [x] Enable branch protection and require the CI checks on `main`.
- [x] Promote living Canonical Site IR, evidence gates and the minimal domain contract.
- [x] Create `DEV-CAD-001..008` as tracked issues (implementation deferred to Milestone 3).

**Exit:** green CI on the default branch; repository structure documented; promotion map current.

## Milestone 1 — Domain slice entry (`NEXT-R1-MVP-001`) — complete for synthetic scope

Input: human-confirmed Trace/Intent fixture. Output: canonical Building/Road objects, proposal → preview → dependency → validator flow.

- [x] Define `dgcad_domain` package boundary and typed domain objects (Building, RoadCorridor).
- [x] Define a minimal confirmed Trace/Intent fixture and its authority rules (`fixtures/domain/domain-slice-001-r2.yaml`).
- [x] Implement Building adapter: trace footprint → professional candidate → canonical proposal.
- [x] Implement Road adapter: centerline + simple cross-section → canonical proposal.
- [x] Register derived artifacts and stale propagation for both domains.
- [x] Add a domain-level validator contract with structured issues.
- [x] Tests: 26 domain contract tests, including a StatefulRuntime integration test.

**Exit:** one confirmed synthetic site can produce canonical building and road objects through the runtime, with preview isolation and correct staleness. Real sketch input remains blocked by `EP-R1-SKETCH-001`; real road engineering remains blocked by `EP-R1-ROAD-001`.

## Milestone 2a — E2E-001 living pipeline (complete)

- [x] Build the pipeline only from living `src/` packages; archived R0 scripts are reference only.
- [x] Cover: DOMAIN-SLICE-001 → Runtime canonical → massing → shadow → CAD-IR → DXF → readback manifest.
- [x] Run the pipeline in CI on Ubuntu and Windows.
- [x] Freeze expected object IDs (11), entity count (15), audit result (0/0) and dependency fingerprints.
- [x] Add mutation tests for vertex mutation, unexpected layer and entity-type substitution.
- [x] Record bulge/constant-width gaps as strict xfail referencing `DEV-CAD-003` / issue #3.

**Exit:** E2E-001 runs in CI with no external engine and no archive imports. Evidence: `docs/e2e/living-pipeline-001.md`.

## Milestone 2b — E2E-002 dependency and mutation (complete)

- [x] Change `B-001` height and prove massing goes stale while footprint-dependent artifacts stay current.
- [x] Move `RN-003` and prove node/edges/corridors + CAD-IR/DXF handling.
- [x] Change north bearing and prove shadow + dependent delivery artifacts stale.
- [x] Rebuild only affected artifacts; produce a new DXF and manifest.
- [x] Compare old/new manifests by object ID and revision, not just file hash.
- [x] Use the Runtime claim/complete path and a deterministic rebuild executor that recomputes, writes and validates.
- [x] Explicitly defer road surface geometry; do not claim `SURFACE-R-002` is generated.

**Exit:** mutation → scoped stale → rebuild → new delivery artifact is reproducible, with no global regeneration. Evidence: `docs/e2e/dependency-mutation-002.md`.

## Milestone 2c — E2E-003 adversarial delivery regression (complete)

- [x] Port non-zero Z, style override, unexpected layer, entity-type substitution and one layer linetype case into living CI. Full symbol-table equivalence remains Milestone 3.
- [x] Add MultiPolygon 2-part + 1-hole coverage (passes: 3 entities, audit 0/0).
- [x] Add bulge/constant-width/start-end-width/thickness/extrusion mutation cases.
- [x] Keep each known gap linked to a `DEV-CAD` issue (#3, #7, #17, #18).
- [x] Add `delivery-comparison.json` and issue categories.
- [x] Track CAD-IR fingerprint/dependency-key consistency as #16 / DEV-CAD-011.

**Exit:** every adversarial delivery case is either detected or explicitly xfailed with an issue link; no silent acceptance. Evidence: `docs/e2e/adversarial-delivery-003.md`.

## Milestone 3 — CAD validator hardening (next)

Close the 15 strict xfails and the remaining interoperability gaps. Scope explicitly includes `DEV-CAD-001..011`.

### 3a — Fix existing strict xfails

- [ ] `DEV-CAD-003` / #3: LWPOLYLINE bulge, start/end width, constant width, thickness and extrusion.
- [ ] `DEV-CAD-007` / #7: structured `validator_error`; validator-internal exceptions never become design failures or passes.
- [ ] `DEV-CAD-009` / #17: entity-level color, linetype, lineweight, true color and transparency.
- [ ] `DEV-CAD-010` / #18: CIRCLE center Z, TEXT insertion Z, rotation, width and alignment.

### 3b — Semantic equivalence and dependency closure

- [ ] `DEV-CAD-005` / #5: full symbol-table case semantics (layer, linetype, text style, block, dimstyle) with original spelling retained.
- [ ] `DEV-CAD-011` / #16: align CAD-IR fingerprint inputs with registered dependency keys; add an unrelated-object negative test.
- [ ] `DEV-CAD-001` / #1: MultiPolygon/part/ring contract; confirm archived validator and define ring identity stability across revisions.
- [ ] `DEV-CAD-002` / #2: archived v0.3 safe-dispatch path; decide retirement vs fix.
- [ ] Keep the `delivery-comparison.json` hash/file correspondence as a regression check.

### 3c — Third-party CAD evidence

- [ ] `DEV-CAD-006` / #6: repeatable AutoCAD/LibreCAD/FreeCAD open/save/readback matrix with original and round-trip files, semantic diff report and environment metadata.

**Exit:** every strict xfail either becomes a positive test or is explicitly re-scoped with evidence; validator errors are structured and categorised; third-party round-trip produces `semantic_pass` or `semantic_pass_with_serialization_differences` per policy; CI remains green.

After Milestone 3, prioritize the real sketch/trace and road evidence packages before broadening to IFC and independent environment engines.

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
