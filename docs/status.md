# Project Status

Updated: 2026-10-27
Version: `0.4.0` (domain slice + E2E-001/002)
Research basis: R0 v0.19 + R1 deployment-entry v0.2

## 1. One-line status

The project has a working **governance/runtime contract layer**, a **synthetic Building/Road domain slice**, and **living E2E-001/002 pipelines** from confirmed trace to DXF readback with scoped mutation/rebuild. It does **not** yet have real sketch input, real road engineering, third-party CAD interoperability, IFC, or real-world validated behavior.

## 2. Test baseline

```text
python -m pytest -q
119 passed, 2 xfailed
```

121 tests collected: 119 passing, 2 expected xfails (`DEV-CAD-003`).

| Suite | Tests | Status |
|---|---|---|
| Foundation | 21 | passing |
| Runtime | 22 | passing |
| Deployment | 8 | passing |
| Lifecycle | 14 | passing |
| Domain | 26 | passing |
| Analysis | 7 | passing |
| CAD delivery | 9 | 7 passing, 2 xfail |
| E2E-001 | 8 | passing |
| E2E-002 | 6 | passing |

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
| Real AutoCAD / FreeCAD bridge | **blocked** | no host environment |
| Building/Road domain adapters | **implemented (synthetic)** | confirmed trace → canonical building/road; unknown states preserved |
| Real professional road geometry | **not validated** | only centerline + explicit cross-section; no alignment/clothoid/surface |
| E2E-001 living pipeline | **implemented (synthetic)** | Domain → massing → shadow → CAD-IR → DXF → readback, living packages only |
| E2E-002 mutation/rebuild | **implemented (synthetic)** | scoped stale + deterministic rebuild worker; height, node, north bearing verified |
| Road surface geometry | **deferred** | no `SURFACE-R-002` artifact is generated or claimed |
| DXF delivery | **minimal synthetic** | R2010, 15 entities, audit 0/0; known DEV-CAD gaps deferred |
| Third-party CAD round-trip | **not validated** | issue #6 |
| Real sketch → trace | **not validated** | no Tier B/C data |
| Real design-office profile | **not validated** | synthetic and DB11 subset only |
| IFC round-trip | **blocked** | IfcOpenShell unavailable |
| Independent solar engine | **not validated** | synthetic NOAA baseline only |
| Third-party CAD round-trip | **partial** | one AutoCAD 2022 core-engine user review; defects deferred to development |

## 4. Living contracts

| Contract | Scope |
|---|---|
| `contracts/canonical-site-ir-v0.4.yaml` | Canonical identity, revisions, authority, dependency, worlds |
| `contracts/domain-contract-v0.1.yaml` | Confirmed trace → Building/Road domain slice |
| `contracts/cad-ir-v0.1.yaml` | Minimal CAD-IR for the E2E delivery slice |
| `contracts/e2e-pipeline-v0.1.yaml` | E2E-001 stages, invariants and known gaps |
| `contracts/e2e-mutation-v0.1.yaml` | E2E-002 mutation, rebuild and manifest comparison |
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
| R1-G04 Geometry | representative failure cases fail closed | partial (DXF defects deferred) |
| R1-G05 Delivery | third-party semantic round-trip + real profile | not started |
| R1-G06 Preview | no canonical pollution | pass for prototype scope |
| R1-G07 Real Case | one non-synthetic site sketch | not started |
| R1-G08 Spikes | IFC + independent ENV + real profile | not started |

## 6. Known defects carried forward

These were reproduced after the v0.3 synthetic hardening and are accepted as **development acceptance items**, not research tasks:

- `DEV-CAD-001` MultiPolygon expected-entity contract raises `KeyError`.
- `DEV-CAD-002` entity-type mismatch raises unhandled `AttributeError`.
- `DEV-CAD-003` LWPOLYLINE bulge / constant width mutations are falsely accepted.
- `DEV-CAD-004` raw DXF semantics and canonical geometry are not both validated.
- `DEV-CAD-005` symbol-table name comparison is case-sensitive; AutoCAD normalizes `CONTINUOUS` to `Continuous`.
- `DEV-CAD-006` third-party round-trip matrix not implemented.
- `DEV-CAD-007` some validator failures are not structured issues.
- `DEV-CAD-008` CAD serialization differences vs project profile rules are not fully separated.

E2E-001 records `DEV-CAD-003` bulge/constant-width as strict xfail with issue #3. The old archived validator and the full DEV-CAD matrix remain Milestone 3 work.

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

Known gap: `DEV-CAD-003` (bulge/constant width) is recorded as two strict xfails referencing issue #3.

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

## 10. Current non-claims

- `research_complete = false`
- `release_authorized = false`
- No production security approval.
- No production database decision.
- No Chinese road/building daylight compliance conclusion.
- No claim that MCP, AutoCAD, FreeCAD or IFC have been executed.
