# R1.0 First-Week Entry Plan v0.1

This is a development-research plan, not a production sprint commitment.

## Day 1 — Schema and state identity

Freeze the minimum typed CanonicalObject/Scene/Revision/World contracts. Add canonical serialization and deterministic hashing spike. No geometry libraries.

## Day 2 — Proposal and transaction semantics

Implement stale-precondition checks, AtomicChangeSet and structured failure. Add conflict fixtures for stale proposals and multi-object rollback.

## Day 3 — Authority and preview

Implement scoped locks, human-confirm/human-unlock states, ProposalSnapshot and canonical/preview isolation. Add adversarial tests for preview leakage and external direct writes.

## Day 4 — Dependency and validation

Implement DAG/cycle detection spike, local + transitive stale propagation and structured ValidationResult. Define rebuild-required vs mark-stale vs block policies.

## Day 5 — Entry review

Re-run all contract tests from a clean checkout/package. Decide whether to freeze R1.0 repository boundaries. Only after this review may R1.1 manual Source/Trace adapter work begin.

## Explicitly deferred

SAM/segmentation, road centerline, building regularization, DXF/IFC, shadow engines, UI, autonomous Agent behavior.
