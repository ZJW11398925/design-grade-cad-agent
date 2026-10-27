# Human Control Plane Boundary v0.1

The Human Control Plane is a separate trusted surface. It may be a small local web/desktop UI in R1; it is **not** an agent tool collection.

Minimum responsibilities:

1. show proposal diff against the current canonical revision;
2. show preview/validation evidence and stale dependencies;
3. approve or reject a proposal;
4. issue scoped unlock approval when a locked field/path is involved;
5. resolve external CAD reconciliation conflicts;
6. expose who approved, what hash/revision was approved, and expiry;
7. never allow approval to survive a mismatched scene revision or ChangeSet hash.

R1 recommendation: the UI talks to the same local sidecar service as MCP/CLI, but uses a separate authenticated/capability-bearing session type. The agent cannot mint or replay a human approval merely by supplying a request field.
