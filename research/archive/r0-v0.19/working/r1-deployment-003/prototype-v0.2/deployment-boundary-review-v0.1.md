# Deployment Boundary Review v0.1

## Verdict

`local_sidecar_hybrid_recommended_for_r1_research`

This is a research checkpoint, not production deployment approval.

## What was actually executed

- Existing Foundation + Stateful Runtime suite was preserved.
- Added an executable SQLite/WAL + content-addressed artifact spike.
- Added compare-and-swap tests across two SQLite connections.
- Added artifact tamper/dedup/reopen tests.
- Added a real command-line argument adapter that invokes the exact same `DeploymentService` as the protocol-neutral agent surface.
- Re-ran the combined suite.

## Test result

51/51 local tests pass in the working directory.

## MCP limitation

Official MCP Python SDK v2 documentation was checked. The current environment has no `mcp` module, and pip installation failed because DNS/network resolution was unavailable. Therefore this round freezes the MCP binding and transport choice but does **not** claim wire-level MCP interoperability.

## Deployment decision

For R1, prefer:

`Agent Host -> MCP Adapter -> Local Sidecar Runtime -> Core/Workers`

plus:

`Human Review UI -> Local Sidecar Runtime`

and thin CAD-local bridges:

`AutoCAD .NET bridge <-> Local Sidecar`

`FreeCAD Python workbench bridge <-> Local Sidecar`

Remote workers may be introduced later for expensive analyses; they do not own canonical state.

## Why not embed the whole runtime in AutoCAD

Native AutoCAD APIs are valuable because they run in-process and see the drawing database directly. That same property couples lifecycle, crash domain and version compatibility to AutoCAD. R1 should use this strength for a bridge, not make AutoCAD the project database or authority owner.

## Why SQLite is only a candidate

The spike demonstrates same-host transactional semantics that match the local-sidecar model. SQLite documentation also makes the same-host limitation of WAL explicit. No claim is made for multi-host collaboration, network filesystem sharing, large-project performance or final schema design.

## Next question

`NEXT-R1-DEPLOY-003`: define and spike the actual local service boundary: one process lifecycle, loopback authentication/capabilities, project open/close semantics, Human Review handshake, and the first real CAD bridge message exchange. Wire-level MCP should be executed once the official SDK is available.
