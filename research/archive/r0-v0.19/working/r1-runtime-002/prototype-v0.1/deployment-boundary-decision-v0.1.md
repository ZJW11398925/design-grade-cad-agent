# Deployment Boundary Decision v0.1

Status: **research candidate**, not production architecture approval.

## Decision

Prefer **Local Sidecar Runtime + thin CAD bridges + Human Control Plane + MCP/CLI adapters** for R1.

The runtime, not AutoCAD/FreeCAD and not the agent host, owns canonical project truth. CAD integrations should be thin in-process bridges because native APIs need access to the host drawing/application, while the durable project state and permission model remain out-of-process.

## Compared modes

| Mode | Canonical isolation | Native CAD access | Agent portability | Failure blast radius | R1 fit |
|---|---|---|---|---|---|
| Embedded CAD plug-in owns system | weak | strongest | weak | CAD crash can own state | reject as primary |
| Local sidecar only | strong | indirect | strong | bounded | strong |
| Remote service only | strong | difficult for local CAD | strong | network-dependent | defer |
| Hybrid sidecar + thin bridges + optional remote workers | strong | strong | strong | bounded by bridge/runtime | **recommended** |

## Why AutoCAD is a bridge, not the runtime

AutoCAD ObjectARX/.NET plug-ins execute in the AutoCAD environment and have direct access to drawing/database objects. This is useful for native read/write, view synchronization and command integration, but it also couples lifecycle and version compatibility to AutoCAD. The bridge should therefore translate between AutoCAD objects and DGCAD external/canonical contracts rather than own canonical truth.

## Why FreeCAD is also a bridge

FreeCAD exposes extensive Python scripting and custom workbench capabilities. This makes a Python workbench or macro a practical bridge for model synchronization and visual review, but it should remain another adapter to the same runtime instead of creating a second project truth.

## MCP transport choice

For an already-running local sidecar, prefer loopback **Streamable HTTP**. `stdio` remains useful when an MCP host itself launches and owns the server subprocess. Do not build a new SSE transport.

Wire-level MCP execution is **blocked in the current container** because the official Python SDK is not installed and pip installation failed due DNS/network resolution. This document therefore freezes the binding boundary from official documentation but does not claim MCP conformance testing.
