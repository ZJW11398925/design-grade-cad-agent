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

- The sketch and image-space geometry are public; the project metric scale, DWG/DXF, redline/project coordinates and calibration matrix are private. The pilot-local approximate scale is published only inside the handoff publication block.
- Semantic label state and geometry state are separate: a designer can confirm that red means building while the extracted footprint remains `proposed`.
- Calibration to the private reference is a reviewed, approximate six-point homography; the pilot handoff uses only a uniform scale derived from it and does not correct local distortion.
- Road centerlines are skeleton-derived `proposed_rough` candidates. They are not professional alignment, width, cross-section, junction or surface design.
- Road topology is derived from the unified brown+blue mask: 1 component, 309 nodes, 333 edges and 121 proposed junction candidates. Colour is a class attribute; the separate-colour 9-component result and the eight nearest-node connectors are rejected. No width/profile/alignment is derived.
- A selected pilot subset passes source-integrity and road-topology checks but is blocked at the object-level human geometry review; full-case confirmation and fidelity metrics remain open.

## 16. CASE-SKETCH-001-HANDOFF-A (v0.13.0)

- `contracts/sketch-domain-handoff-v0.2.yaml` maps selected source evidence → trace → canonical, with an explicit `review_kind`, confirmation scope, geometry quality, boundary authority, source integrity and road-topology checks.
- `designer_authorized_pilot` is not a geometry review. The committed record authorizes the pilot but marks every object `not_reviewed`; the pipeline blocks with `HUMAN_OBJECT_REVIEW_REQUIRED` and publishes a review packet + unsigned template.
- Pilot subset: site boundary, one ordinary building, one merged building, one green, two main-road edges, one branch edge and one T-junction. The sketch boundary maps to `SITE-SKETCH-001` with candidate authority; the private redline remains authoritative and unused.
- The downstream path `ConfirmedTraceScene` → `build_initial_scene` → runtime proposal/approval/commit → Canonical → CAD-IR → DXF → readback is implemented and tested with an explicitly marked test double. Scope and geometry quality propagate through trace, canonical, CAD-IR provenance, DXF XDATA and the readback manifest.
- The coordinate transform is `uniform_scale_translation_yflip` in `LOCAL-XY-ZUP`: no homography, no shape correction, unknown axis orientation, per-object scale-range sensitivity.
- Source file/object/geometry hashes are verified; a stale hash or changed geometry fails closed. Road topology checks nodes, edge endpoints, corridor coverage, one component and the T-junction degree; the selected data's max endpoint offset is 3.606 px against a declared 4.0 px tolerance.
- Unknown building height/base elevation and road hierarchy/cross-section remain unknown; massing and road profiles are blocked; no width is derived.
- `EP-R1-SKETCH-001` remains in progress.

## 18. Autonomous design synthesis (v0.14.0)

- `src/dgcad_design/` separates design basis, full-site input, intent model, building standardization, road hierarchy, green allocation, parking, consistency checks, drawing and CAD export.
- The Agent generates a **schematic design draft** in `proposal_preview` with `rule_derived` authority. It may revise the draft without human approval; it may not claim `human_confirmed`, code compliance, adoption or official issue.
- The design basis is explicit and replaceable: staircase module, floors, floor height, road widths, setbacks, FAR range, parking ratio, north-south spacing and green target.
- The first round uses the full site as coarse context (55 buildings, 109 staircases, 2,398 households, FAR 1.565, 2,398 parking spaces, 5 entrances) and deep-designs focus block G-01 (7 buildings / 16 units) with 20 m rows, green strips and an access loop.
- The 333-edge source skeleton is evidence, not the design road network. The design merges main roads and serves all 17 groups through 19 connector roads (17 branch + 2 access; G-08/G-09 share BR-G-09 — not one branch per group); the 121-junction review is not continued.
- The CAD layer now supports `polyline` and `text` representations in addition to polygon rings, centerlines and point markers; the design profile standardizes 22 layers, labels, dimensions, key plan, title block, legend, north arrow and scale bar.
- Consistency checks cover FAR, parking, entrances, unit counts, focus spacing/setback/overlap/road clearance, connectivity, road widths and green ratio. Full-site north-south spacing is recorded as deferred, not pass.
- `EP-R1-DESIGN-001` is in progress; the draft is not construction-ready or code-compliant.

## 19. Open-source reuse (M4c-0)

- The sprint tested Building Regulariser, OSMnx, PyGeoOps, PyClothoids and momepy on the same CASE-SKETCH-001 focus block; evidence is in `docs/e2e/open-source-reuse-001/`.
- OSMnx `consolidate_intersections` is the strongest candidate for a topology preprocessor: 309/333 → 117/141 at 8 m, one component. It does not select the design hierarchy or widths.
- Building Regulariser is a limited footprint-cleanup adapter; PyGeoOps produces per-area centerlines; a single clothoid fit fails quality; momepy is an evaluation adapter.
- The 4c design candidate exposed a road-topology defect: the corridor union is one polygon, but the noded centerline graph read 5 components. M4c-1a (0.16.0) diagnosed this as a sub-ULP floating-point noding artefact — not a design disconnection — and fixed it with explicit shared-coordinate junctions: the noded graph is 1 component (M4c-1a: 51 nodes / 55 segments; after the M4c-1b access network: 59 nodes / 65 segments, 24 dead ends; after Phase 0 in 0.22.0: **58 nodes / 68 segments, cyclomatic 11, 19 dead ends, 36 junctions, `max_endpoint_gap_m` 0.0**), the dependency-free noded check replaced the corridor-only check, and OSMnx remains an optional source-skeleton preprocessor, not a connectivity proof.
- M4c-2 (0.21.0) removed the known main-road/building overlap by a recorded MAIN-19 diversion (66.235 m; 38.19068149970834 → 0 m², `MAIN_ROAD_BUILDING_OVERLAP` pass, `ROAD_ALIGNMENT_EVIDENCE` info) and resolved the 7 unresolved dead ends (`DEAD_END_RESOLUTION` pass, 0 unresolved; MAIN-18/MAIN-25 are site-edge termini within the ≤5 m boundary band — the source network is clipped at the published boundary, and MAIN-25 is extended along the shortest direction to the boundary, not collinear with its terminal segment). Phase 0 (0.22.0) corrected the semantics to `local_search_exhausted`, added the site-boundary hard check (`ROAD_BOUNDARY_CONTAINMENT` pass, margin 0.6735131264650868; MAIN-08/16/18 repairs), split the overlap fields (`main_before` 38.19068149970835 / `main_after` 0.0 / `new_access` 0.9943558185246757 / `total_after` 0.9943558185246756) and published `source_segment_map`/design-diff alignment+dead-end records. The 44-road network, declared access relations and road ids are unchanged. The alignment claim is zero remaining known overlap and boundary containment, not a 3.0 m clearance for all main roads (unadjusted minimum ≈1.229 m); full-site road clearance remains deferred.
- M4c-3 (0.22.0) added the first multi-candidate experiment (A/B1/B2/C); M4c-3a (0.23.0) completed its evaluation integrity under `design-candidates-v0.2` (v0.1 superseded): candidates carry `parent_basis_id` + canonical fingerprint (missing/mismatch fails `basis_ok`); `geometry_change` compares all 44 roads by main/branch/access class and per-group terminal (A BR-G-08 2.826 / G-08 terminal 2.826; B1 BR-G-09 7.352; B2 13.645; C BR-G-08 76.700 / G-08 terminal 75.315 — C is not a small change); `HISTORICAL_BOUNDARY_ARCHIVE` separates the MAIN-19 66.235 m diversion and MAIN-08/16/18 repairs from current candidates (current B1 boundary-compliant, margin 0.6735; pre-repair archival); comparison uses 11 single-unit objectives with auxiliary metrics excluded from Pareto/preference and no single score; the default preference recommends B1, road-first recommends A, Pareto [B1,B2,C,A]. Code compliance remains out of scope.
- M4d (0.24.1) extended the draft to the full site under `design-synthesis-v0.9` (v0.8 superseded): 55 buildings / 109 units / 2,398 households in 18 rows / 8 superblocks (36 row records) against the frozen 44-road network, focus G-01 preserved; completeness requires exact expected 55 ids; displacement sum 2,328.95 m (max 147.25 m, mean 42.34 m). Full-site checks 29 = 11 pass + 11 info + 5 deferred + 2 fail: boundary setback, building overlap, N-S spacing (19.999999999999943 m; 20 m is candidate row-rhythm + basis assumption, not universal) and road clearance (3.0163622902759215 m) pass; `DESIGNED_GREEN_RATIO` is **deferred** (designed green 15.93% <30%; the 61.06% account is `POTENTIAL OPEN SPACE ... NOT LANDSCAPE DESIGN` on `L-OPEN-SPACE`, auxiliary only), and `ROAD_ACCESS_COVERAGE` fails 0.0 (17 relation errors) while `DEAD_END_RESOLUTION` fails 17 unresolved. Under the fixed network / uniform row grid / current search family, 25–130 m caps found no complete layout; the unbounded search produced the 147.25 m candidate, not a proven global minimum. Full-site DXF 553/553 with incomplete-title semantics; the focus sheet remains canonical and M4d-2 must recompute access/roads. 3.016362/19.999999 are model-coordinate internal consistency, not survey-grade.
- No new core dependency is promoted; the experiment dependencies are optional only.

## 20. Open architecture questions

- Final road alignment algorithm and Chinese profile source.
- Shapely vs CGAL boundary.
- IFC authoring/round-trip strategy.
- Production environment engine.
- Real project/design-office profile schema.
- DWG production route.
