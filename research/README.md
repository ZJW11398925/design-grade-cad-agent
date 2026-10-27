# Research Archive

This directory preserves the research evidence behind the current code. It is **historical**, not the living specification. Paths, status labels and claims inside the archive reflect the moment each snapshot was produced.

## Contents

| Path | Description |
|---|---|
| `archive/r0-v0.19/` | Full R0 research workspace: research plan, five acquisition batches (road, sketch/trace, building/massing, CAD/BIM validator, environment analysis), E2E synthetic slice, architecture synthesis, architecture challenge, R1 Foundation/Runtime/Deployment research prototypes, reports and snapshots |
| `archive/r1-deployment-entry-v0.2/` | Original standalone delivery of the R1 deployment lifecycle prototype (Foundation + Runtime + Deployment + Lifecycle, 65 tests) |

## Authority

- The root `src/` and `tests/` are the canonical implementation and executable contracts.
- The root `docs/` describes the current project status.
- The archive is evidence for how decisions were reached; it does not override root docs or tests.
- Do not edit archived documents to match later code. Add a new document or ADR instead.

## Excluded material

The R0 workspace contained `working/reference-skill/v0.2.2-field-test.4/`, a vendored copy of the private `conduct-traceable-research` methodology skill. It is **not** published here. The version used by the research is `v0.2.2-field-test.4`.

## Key entry points

- `archive/r0-v0.19/README.md` — original workspace status.
- `archive/r0-v0.19/research-plan.md` — decision question, scope, coverage, next action.
- `archive/r0-v0.19/working/mainline-roadmap.md` — product chain and gate model.
- `archive/r0-v0.19/working/coverage-dashboard.md` — COV status.
- `archive/r0-v0.19/working/architecture/` — module contracts, authority matrix, Canonical IR, challenge report.
- `archive/r0-v0.19/working/e2e-integration/` — synthetic vertical slice and reviews.
- `archive/r1-deployment-entry-v0.2/README.md` — deployment prototype summary.

## Evidence levels

Research documents distinguish:

- project claims / official documentation;
- source-code inspection;
- local synthetic test;
- independent test;
- real-world evidence.

Do not collapse these levels. A synthetic benchmark is not a production accuracy claim; an independent review is not an A1 acquisition pass; a passing contract test is not a product capability.
