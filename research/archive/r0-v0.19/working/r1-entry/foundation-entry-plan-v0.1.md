# R1.0 Foundation Entry Plan v0.1

**Purpose:** turn the R0 architecture into the smallest executable contract layer without starting domain feature development.

## Entry objective

R1.0 succeeds only if the system can represent and enforce design-state governance before it knows how to draw roads or buildings.

The first executable chain is:

`CanonicalObject -> ChangeProposal -> AtomicChangeSet -> ProposalSnapshot -> authority check -> commit -> revision bump -> dependency invalidation -> structured validation`.

## Package boundary

The Foundation package owns:

- stable IDs and revision stamps;
- canonical current state;
- proposal and atomic transaction semantics;
- preview-world isolation;
- authority and lock decisions;
- generalized dependency invalidation;
- structured validator result schema;
- external-direct-write prohibition.

It explicitly does not own geometry operations, road/building semantics, CAD/BIM serialization, analysis physics, UI, or AI inference.

## First-week implementation order

Day 1: typed IR subset + IDs/revisions/worlds.  
Day 2: ChangeProposal, AtomicChangeSet, stale-precondition checks.  
Day 3: ProposalSnapshot + canonical/preview isolation + lock/authority.  
Day 4: dependency graph + local stale propagation + ValidationResult.  
Day 5: adversarial contract tests, fixture versioning, R1-G01/G02/G03/G06 entry review.

## Stop conditions

Do not add SAM, road centerline fitting, IFC, DXF, shadow engines, or UI when any Foundation invariant is still ambiguous. Domain examples may appear only as typed fixture labels, not real feature implementation.
