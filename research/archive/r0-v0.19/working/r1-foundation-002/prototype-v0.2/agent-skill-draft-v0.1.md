# DGCAD Agent Skill — Draft v0.1

**Role:** workflow guidance only. This file must never be treated as an authorization mechanism.

## Default workflow

1. Read scene summary and only the objects needed for the user's request.
2. Distinguish current canonical state from preview/external artifacts.
3. Create a proposal rather than mutating canonical state.
4. Preview the proposal when geometry, analysis or delivery effects matter.
5. Run applicable validators and report coverage limits.
6. If human approval or unlock is required, explain the exact blocked scope and request approval through the control plane.
7. After an authorized commit, inspect stale artifacts and request only necessary rebuilds.
8. Export only from an explicit world/revision/profile and retain validation evidence.

## Never do

- claim human identity or unlock permission;
- silently promote candidate semantic/rule values to confirmed/mandatory;
- treat external CAD/IFC as canonical truth;
- infer a successful validation from a tool crash;
- bypass a lock by changing a different representation;
- request global rebuild when dependency evidence supports a local rebuild;
- treat a preview as committed design.

## Reasoning surface

Prefer semantic summaries, revisions, diffs, blockers and validation evidence. Exact geometry remains owned by deterministic geometry services and is referenced by IDs/artifacts unless inspection is necessary.
