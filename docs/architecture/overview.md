# Architecture Overview (Provisional)

Status: provisional research architecture, not a frozen technology stack.

Basis: R0 Architecture Synthesis v0.2, Architecture Challenge v0.1 (`provisional_architecture_survives_with_amendments`), Canonical Site IR v0.3, and the R1 Foundation/Runtime/Deployment prototypes.

Source documents:

- `research/archive/r0-v0.19/working/architecture/provisional-architecture-synthesis-v0.2.md`
- `research/archive/r0-v0.19/working/architecture/module-contracts-v0.1.md`
- `research/archive/r0-v0.19/working/architecture/agent-authority-matrix-v0.1.md`
- `research/archive/r0-v0.19/working/architecture/canonical-site-ir-v0.3.yaml`
- `research/archive/r0-v0.19/working/architecture/architecture-challenge-report-v0.1.md`

## 1. Truth model

| Fact domain | Owner | Examples |
|---|---|---|
| Source evidence | Source registry | original raster, control points, imported base CAD |
| Trace evidence | Trace layer | faithful contours, semantic candidates |
| Confirmed design truth | **Canonical Site Model** | confirmed footprint, road centerline, height, profile binding |
| Rule truth | Rule/Profile registry | standard clause, project override, applicability |
| Method-specific results | Derived artifacts | massing, shadow, DXF, IFC |
| External interoperability | Reconcile layer | third-party CAD/IFC round-trip artifacts |

These are different fact domains, not competing owners. The critical prohibition is that a delivery artifact never overwrites canonical design truth.

## 2. Data plane

```text
Source Evidence
  -> Trace Geometry
    -> Intent Candidate
      -> Professional Candidate
        -> Canonical Site Model
          -> Derived 3D / Analysis
            -> DXF / IFC / Renderings
```

Every step records provenance. Professionalization creates a new revision; it never overwrites the trace.

## 3. Control plane

```text
Agent proposal
  -> authority check
    -> deterministic tool execution
      -> rule/profile resolution
        -> validator
          -> human confirm where required
            -> canonical commit
              -> stale propagation / local rebuild
```

Only three commit paths exist:

- **Path A — evidence commit:** Source/Trace revisions, no professional judgment.
- **Path B — deterministic low-risk commit:** confirmed input plus authorized deterministic rule, e.g. confirmed footprint + confirmed height → massing.
- **Path C — design-intent change:** proposal + diff + validator + human confirmation, including road topology changes, regularization of intentional rotation, unknown height assignment and conflicting profile selection.

## 4. Modules M01–M11

| Module | Owns | Must not do |
|---|---|---|
| M01 Source & Calibration | source identity, scale/coordinate/north evidence | guess semantics or real dimensions |
| M02 Trace & Semantic Candidate | faithful trace, semantic candidates | auto-professionalize |
| M03 Geometry & Topology | deterministic geometry/topology operations | decide design intent |
| M04 Road Design | road graph, alignment, cross-section, junction proposals | let an LLM invent road parameters |
| M05 Building & Massing | footprint proposals, height/massing, site topology | redraw designer intent from FAR/BCR |
| M06 Canonical IR | **single confirmed design truth**, revisions, dependency | use a CAD/BIM file as the database |
| M07 Analysis | method-specific analysis results | claim regulatory compliance |
| M08 Rule/Profile | rule sources, applicability, parameters, overrides | fill clauses from model memory |
| M09 Compiler | canonical → DXF/IFC faithful export | "improve" design during export |
| M10 Validator | structured validation with coverage limits | silently modify design |
| M11 Agent | proposals, explanations, tool plans, local repair suggestions | write confirmed truth directly |

## 5. Canonical Site IR v0.3 concepts

The typed IR is defined in `research/archive/r0-v0.19/working/architecture/canonical-site-ir-v0.3.yaml`. Key concepts:

- `object_id` is stable across canonical, 3D, DXF and IFC representations.
- Three independent revision axes: `semantic_revision`, `geometry_revision`, `parameter_revision`.
- Authority states: `evidence_only`, `candidate`, `rule_derived`, `human_confirmed`, `locked`.
- `AtomicChangeSet` with `commit_policy: all_or_nothing`.
- `ProposalSnapshot` marked `preview_only`; previews cannot pollute canonical current.
- Generalized dependency nodes: object revisions, calibration, profile, rule, method/version, context, terrain, sensor grid, delivery profile.
- Rule applicability: `applicable`, `conditionally_applicable`, `not_applicable`, `blocked`.
- Three worlds: `canonical_current`, `proposal_preview`, `external`.
- `ValidationResult.verdict`: `pass`, `pass_with_differences`, `conditional`, `fail`, `unsupported`, `validator_error`.
- External reconcile never writes canonical directly; it emits proposals.

## 6. Authority and locks

- The Agent tool surface exposes no approve/unlock operation.
- Human approval and unlock occur through a separate authenticated control plane.
- Approval grants bind proposal, change-set hash, scene revision, actor and expiry.
- Locks are revision-axis scoped or field-path scoped; bypass requires explicit human unlock.
- Commitment is single-writer per project; stale writers fail closed.

## 7. Deployment shape (R1 candidate)

```text
DGCAD Desktop/Tray Launcher
        | owns lifecycle
        v
Local Sidecar Runtime (canonical authority)
   |- MCP adapter          -> Agent role
   |- Human Review UI      -> approve/unlock role
   |- AutoCAD thin bridge  -> external CAD role
   |- FreeCAD thin bridge  -> external CAD role
   |- CLI                  -> dev/CI role
```

- The Agent does not own the runtime process, project database, human approval or CAD credentials.
- Discovery metadata contains no secrets; credentials use one-time out-of-band pairing.
- SQLite/WAL is a local same-host candidate, not a multi-host authority.
- CAD bridges hold only external representation authority.

## 8. Adapter policy

| Concern | Role | Candidate |
|---|---|---|
| 2D geometry | core dependency | Shapely/GEOS |
| Complex geometry | specialist boundary | CGAL (not yet needed) |
| DXF | adapter | ezdxf |
| IFC | adapter | IfcOpenShell |
| Road centerline/alignment | replaceable algorithm plugin | PyGeoOps, Clothoids |
| Environment analysis | adapter | Ladybug/Honeybee/Radiance |
| CAD authoring / QA | external gate | AutoCAD, LibreCAD, FreeCAD, Bonsai |

Canonical identity, revision, authority and dependency remain in-house. No third-party library owns canonical truth.

## 9. Implemented domain slice 001 (v0.2.0)

`src/dgcad_domain/` is the first implementation that puts real Building/Road objects through the Foundation/Runtime contracts.

```text
ConfirmedTraceScene (fixture, human_confirmed_trace=true)
  -> evidence objects: authority=evidence_only, locked, immutable
  -> design objects: authority=candidate
  -> BuildingCandidate / RoadCandidate
  -> ChangeProposal (required_authority=human_confirm)
  -> Preview (proposal_preview world)
  -> Human approval grant
  -> Canonical commit (canonical_current)
  -> stale propagation (massing / road surface)
  -> rebuild job
  -> structured domain validation
```

Implemented behavior:

- trace/professional footprint separation; trace evidence is never overwritten;
- unknown height remains unknown and blocks massing;
- regularization candidate requires review; intentional rotation is reported, not silently axis-aligned;
- road class, function, access and physical cross-section remain separate;
- unknown road class blocks derived width; explicit user-specified widths remain explicit;
- T-junction node moves are atomic across node, edges and corridors;
- external geometry enters only through a reconcile proposal.

Not implemented within the domain slice: real sketch extraction, professional alignment/junction geometry, standard profiles and road surface geometry.

## 10. Implemented E2E-001 living pipeline (v0.3.0)

`src/dgcad_e2e/` connects the domain slice to delivery using only living packages:

```text
DOMAIN-SLICE-001-r2
  -> StatefulRuntime commits (human approval grants)
  -> massing artifacts + dependency stale
  -> synthetic shadow baseline (dgcad_analysis)
  -> CAD-IR (dgcad_cad)
  -> DXF R2010 + XDATA
  -> readback validator + manifest
  -> domain / CAD-IR / DXF validation
```

Implemented behavior:

- 5 commits (B-001, B-002, B-003, R-001, R-002); canonical revision 6.
- massing for confirmed heights; unknown height blocked with a structured code.
- rebuild jobs queued in dependency-safe order for stale massing and road surface.
- 4 shadow samples: 2 sunlit, 1 confirmed shaded, 1 unknown-height.
- 11 CAD-IR objects / 15 DXF entities; audit 0 errors, 0 fixes; readback `pass`.
- DXF identity/revision/hash/role survive through XDATA.
- No import or invocation of archived R0 scripts.

Still not implemented: third-party CAD round-trip, IFC, real sketch input, real road engineering, standards profile, independent shadow engine and UI. Milestone 3a closes DEV-CAD-003/007/009/010; 3b/3c remain for symbol-table, dependency/ring identity and third-party evidence.

## 11. Implemented E2E-002 mutation/rebuild (v0.4.0)

`src/dgcad_e2e/living_project.py` adds:

- a canonical `PROJECT-CONTEXT-001` object that versions north bearing with a source;
- a deterministic rebuild worker using Runtime claim/complete jobs;
- mutation paths for building height, T-junction node move and north bearing;
- a corridor centerline rebuild that reads only latest canonical edge geometry.

Verified behavior:

- Height change stales massing/shadow/CAD-IR/DXF; `PLAN-B-001` and `MASS-B-003` stay current.
- Node move is one atomic changeset; corridor centerline becomes `[0,11] → [21,12] → [40,11]` from canonical edges.
- North bearing change stales shadow/delivery but not building geometry.
- Rebuild worker recomputes, writes, validates and completes only with a content hash.
- Delivery comparison uses object IDs, revisions, dependency fingerprints, readback verdict and audit result.
- Road surface geometry is explicitly deferred; `SURFACE-R-002` is not registered or claimed as generated.

## 12. Implemented E2E-003 adversarial delivery (v0.5.0)

`tests/e2e/test_e2e_003_adversarial.py` and `contracts/e2e-adversarial-v0.1.yaml` add:

- issue categories: `cad_format_semantics`, `interoperability`, `profile_violation`, `serialization_difference`, `validator_error`;
- a `delivery-comparison.json` artifact combining object IDs, canonical revisions, CAD-IR fingerprint, readback verdict, audit, profile identity, `dxf_sha256` and `readback_manifest_sha256`;
- positive checks for LWPOLYLINE elevation, MultiPolygon 2-part+hole, one layer linetype case and missing XDATA;
- positive checks for CIRCLE/TEXT 3D, text placement, entity style overrides, LWPOLYLINE full semantics and structured validator errors.

Boundaries: same-library `ezdxf` only, modelspace only, no systematic DEV-CAD fix, no third-party CAD evidence, road surface still deferred. CAD-IR fingerprint/dependency-key consistency is tracked as #16 / DEV-CAD-011.

## 13. Implemented E2E-003b semantic/dependency closure (v0.7.0)

- CAD-IR fingerprint excludes the global scene revision; per-object revisions are registered dependencies.
- Symbol-table case semantics cover layers, linetypes, text styles, required blocks/dimstyles/text styles.
- XDATA carries a content-derived `ring_key`; part/ring indices remain build indices.
- Readback manifests carry `canonical_target` and `raw_dxf_semantics` with tolerance `1e-9`.
- Serialization differences, profile violations, CAD semantics, interoperability and validator errors are distinct categories.

Boundaries: same-library, modelspace only, current entity set LWPOLYLINE/CIRCLE/TEXT, no third-party CAD (#6), road surface deferred.

## 14. Implemented E2E-003c third-party evidence (v0.8.0)

- Real AutoCAD 2024 Core Console round-trip in an isolated profile.
- Input and round-trip DXF, environment, comparison, save script and console output are preserved under `docs/e2e/third-party-003c/`.
- Verdict: `semantic_pass_with_serialization_differences`; only DXF-version upgrade and linetype-case normalization differ.
- Matrix status: partial. LibreCAD, FreeCAD and GUI visual/print QA are not executed; #6 remains open.

## 15. CASE-SKETCH-001 sketch intake (v0.9.0)

The first Tier B sketch intake adds an evidence layer before the existing domain slice:

```text
source raster (public)
  -> image-space trace (proposed)
    -> designer-confirmed semantic labels
      -> [future] human-confirmed reference geometry
        -> canonical Building/Road handoff
```

- The sketch and image-space geometry are public; the DWG/DXF, redline/project coordinates, calibration matrix and metric scale are private.
- Semantic label state and geometry state are separate: a designer can confirm that red means building while the extracted footprint remains `proposed`.
- Calibration to a private reference is a reviewed, approximate homography; it is not survey-grade and does not make the sketch project-coordinate truth.
- Road centerlines are skeleton-derived `proposed_rough` candidates. They are not professional alignment, width, cross-section, junction or surface design.
- Road topology is derived from the unified brown+blue mask: 1 component, 309 nodes, 333 edges and 121 proposed junction candidates. Colour is a class attribute; the separate-colour 9-component result and the eight nearest-node connectors are rejected. No width/profile/alignment is derived.
- No sketch object is written to canonical yet; the human-confirmed reference trace and fidelity metrics remain the gate.

## 16. Open architecture questions

- Final road alignment algorithm and Chinese profile source.
- Shapely vs CGAL boundary.
- IFC authoring/round-trip strategy.
- Production environment engine.
- Real project/design-office profile schema.
- DWG production route.
