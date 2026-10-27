# R1.0 Foundation Entry Review v0.1

**Verdict:** `entry_ready_candidate_with_open_foundation_questions`

## What was executed

A research-only Python skeleton was created with no geometry engine, AI, CAD/BIM adapter, UI or domain design logic. It implements only the minimum state-governance contracts needed to challenge the R0 architecture.

Initial contract run: 8/8 passed. Architecture challenge then found three missing/incorrect contracts:

1. Preview was incorrectly requiring human confirmation before a proposal could be visualized.
2. Dependency invalidation was only direct and did not propagate across derived chains such as Building parameter -> Massing -> Shadow.
3. Locks were over-broad; a geometry lock also blocked unrelated parameter-only changes.

The prototype was amended and the expanded suite passed 12/12.

## What this means

The exercise supports the current R0 decision to keep canonical state, preview state, dependency state and authority in a small self-owned Foundation layer instead of delegating them to DXF/IFC/FreeCAD/LLM state.

It does **not** validate any domain algorithm. R1-G01/G02/G03/G06 are not formally passed; this is only an entry candidate showing that the contracts can be expressed and tested.

## Open Foundation questions before a real repository freeze

- persistent event/revision storage model;
- schema migration policy;
- concurrent proposal/rebase semantics;
- dependency cycle detection;
- artifact rebuild scheduling;
- field-path locks finer than revision-axis locks;
- deterministic canonical hashing and serialization;
- audit/event log retention;
- process boundary for Agent vs deterministic Foundation API.

These are Foundation concerns; they should be resolved before domain code becomes large, but they do not require road/building/AI implementation to investigate.
