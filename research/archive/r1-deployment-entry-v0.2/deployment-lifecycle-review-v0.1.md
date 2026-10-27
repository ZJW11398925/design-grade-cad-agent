# NEXT-R1-DEPLOY-003 — Deployment Lifecycle Review v0.1

## Verdict

`bounded_checkpoint / lifecycle_candidate_ready`

The Local Sidecar recommendation survives the lifecycle/security challenge with amendments. The research prototype now exercises the startup/discovery/auth/lease/bridge-control boundary rather than only in-process Runtime semantics.

This is **not** production security approval, an AutoCAD integration pass, or MCP wire-level conformance.

## Executed evidence

- Full suite: **65/65 tests passed**.
- Loopback-only endpoint discovery is token-free and private on the POSIX test environment.
- Agent, Human Review and CAD Bridge sessions have disjoint server-side roles/capabilities.
- Pairing grants are role-bound, one-time and short-lived; the exchange request cannot select or escalate its role.
- Bearer sessions expire and can be revoked.
- Local HTTP control plane rejects non-loopback bind configuration and DNS-rebinding-style Host / cross-Origin requests.
- Agent bearer session is rejected by `/human/approve`; Human Review session can approve and the Agent may subsequently request commit through the ordinary agent surface.
- CAD bridge registration rejects Agent session and accepts only a bridge-scoped session.
- SQLite project lease prevents two live sidecars from becoming writers of the same project and uses generation increments on expired takeover.
- Bridge heartbeat is actor-bound and expires fail-closed.
- A separate child-process probe demonstrated: lease → bind → token-free discovery → private pairing handoff → pairing exchange → authenticated Agent session → graceful stop → discovery removal.

## Child-process probe result

See `spikes/sidecar-process-probe-result.json`.

The probe used an actual child Python process and localhost TCP socket. It did **not** use MCP. The pairing handoff file was mode `0600` on this POSIX host; Windows ACL/DPAPI behavior remains an explicit gap.

## Architecture decisions strengthened

1. The interactive runtime owner should be a DGCAD Desktop/Tray Launcher, not the Agent and not the CAD plug-in.
2. Runtime discovery is public-to-the-local-user metadata only; credentials use out-of-band one-time pairing.
3. Agent, Human Review and CAD Bridge are separate security principals even when all are local.
4. Human approval/unlock remains outside the agent tool surface and outside the Agent session capability set.
5. CAD bridge is a heartbeat-based external adapter; host disappearance cannot leave an implicit permanent bridge authority.
6. Project mutation remains single-writer. The local lease is a guard for R1, not a distributed multi-host solution.

## Important unresolved gaps

- No official MCP SDK is installed in this environment, so no Streamable HTTP MCP wire exchange, OAuth resource-server behavior, MCP session lifecycle or tool/resource registration has been executed.
- No AutoCAD/Windows host exists here. The actual .NET bridge load/initialize/document-event/shutdown flow is source-backed only, not locally executed.
- No FreeCAD host exists here.
- The current session authority is in-memory. Production credentials, OS key protection, rotation, Windows ACL/DPAPI and installer trust remain open.
- The HTTP control-plane spike is not intended to replace a real MCP SDK or production web framework.
- Lease expiry under suspend/resume, system clock discontinuity and abrupt kill need a monotonic/DB-time production design.

## Next gate

`NEXT-R1-DEPLOY-004` should no longer add another abstract lifecycle layer. It should perform the first host-specific bridge implementation spike on a Windows/AutoCAD-capable environment **or**, if that environment is unavailable, freeze the AutoCAD bridge command/event/wire contract and return to the domain MVP slice (Trace → building/road → preview → DXF) without pretending the host integration has been validated.
