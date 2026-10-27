# Source Locators — Deployment Boundary Research

Checked: 2026-10-27.

## MCP

- Official Python SDK v2: https://py.sdk.modelcontextprotocol.io/
- Running servers / transports: https://py.sdk.modelcontextprotocol.io/run/
- Client transports: https://py.sdk.modelcontextprotocol.io/client/transports/

Observed boundary relevant to DGCAD:
- v2 is documented as current stable.
- `stdio` is intended for local host-launched subprocess servers.
- `streamable-http` is the deployable HTTP transport; default local bind in examples is loopback.
- SSE is superseded and should not be selected for a new implementation.

Current environment limitation: official `mcp` Python package is absent. A pip installation attempt failed because DNS/network resolution was unavailable, so wire-level MCP conformance was not executed.

## AutoCAD

- AutoCAD 2026 Managed .NET API overview: https://help.autodesk.com/cloudhelp/2026/ENU/OARX-DevGuide-Managed/files/GUID-390A47DB-77AF-433A-994C-2AFBBE9996AE.htm
- AutoCAD 2026 ObjectARX applications: https://help.autodesk.com/view/ACD/2026/ENU/?caas=caas%2Fdocumentation%2FCIV3D%2F2014%2FENU%2FfilesACD%2FGUID-3FF72BD0-9863-4739-8A45-B14AF1B67B06-htm.html
- Managed .NET compatibility: https://help.autodesk.com/cloudhelp/2026/ENU/AutoCAD-Customization/files/GUID-A6C680F2-DE2E-418A-A182-E4884073338A.htm
- NETLOAD terminology: https://help.autodesk.com/cloudhelp/2026/CHS/OARX-DevGuide-Managed/files/GUID-0733B384-E920-4007-B364-80EC9A0FC620.htm

Observed boundary relevant to DGCAD:
- ObjectARX runs in AutoCAD's address space and has direct access to native data structures.
- Managed .NET exposes drawing/application objects and is a practical Windows integration surface.
- AutoCAD release/.NET compatibility changes across versions, so an embedded plug-in should remain a thin adapter rather than own the durable canonical project model.

## FreeCAD

- FreeCAD feature overview: https://www.freecad.org/features.php
- FreeCAD source documentation: https://freecad.github.io/SourceDoc/
- FreeCAD manual / Python scripting: https://www.freecad.org/manual/a-freecad-manual.pdf

Observed boundary relevant to DGCAD:
- FreeCAD exposes broad Python scripting, macros and custom workbench capabilities.
- This makes an in-process Python workbench/bridge feasible for native document interaction while keeping canonical state in the sidecar runtime.

## SQLite

- Transactions: https://www.sqlite.org/lang_transaction.html
- WAL: https://www.sqlite.org/wal.html
- Isolation: https://www.sqlite.org/isolation.html
- Network caveats: https://sqlite.org/useovernet.html

Observed boundary relevant to DGCAD:
- SQLite serializes writers; WAL allows readers and a writer to coexist on the same host.
- WAL relies on same-host shared memory and is not appropriate as a shared database on a network filesystem.
- This aligns with the proposed **local sidecar / single-project writer** boundary, not a multi-host shared-authority design.

## NEXT-R1-DEPLOY-003 sources (2026-10-27)

### MCP local transport/security

- Official MCP Python SDK deploy/security guidance: https://py.sdk.modelcontextprotocol.io/run/deploy/
  - Local Streamable HTTP defaults to localhost Host/Origin allowlisting and DNS-rebinding protection.
- Official MCP Python SDK authorization guidance: https://py.sdk.modelcontextprotocol.io/run/authorization/
  - HTTP MCP server acts as a bearer-token resource server; token issuance belongs to an authorization server.
- Official MCP C# SDK transport guidance: https://csharp.sdk.modelcontextprotocol.io/v2/concepts/transports/transports.html
  - Recommends restricting local HTTP accepted hosts to loopback values.

Current environment limitation remains unchanged: the official MCP Python package is not installed and pip acquisition is blocked by current network/DNS, so these are source-backed contracts, not wire-level execution evidence.

### AutoCAD plug-in lifecycle

- Autodesk ObjectARX application loading: https://help.autodesk.com/cloudhelp/2024/ENU/AutoCAD-Customization/files/GUID-409E18E6-7164-41CB-A188-97E79E42BC5A.htm
- Autodesk managed .NET application initialization / `IExtensionApplication`: https://help.autodesk.com/cloudhelp/2026/ESP/OARX-DevGuide-Managed/files/GUID-FA3B4125-F7BD-4E89-969F-9DCC90AC6977.htm
- Autodesk in-process vs out-of-process .NET guidance: https://help.autodesk.com/cloudhelp/2024/ENU/OARX-DevGuide-Managed/files/GUID-C8C65D7A-EC3A-42D8-BF02-4B13C2EA1A4B.htm
- Autodesk ObjectARX application messages (`kInitAppMsg`, `kUnloadAppMsg`, `kLoadDwgMsg`): https://help.autodesk.com/cloudhelp/2022/ENU/OARX-DevGuide/files/GUID-22B47871-3716-4DED-9275-F60D150D9BD3.htm

These sources support the thin in-process AutoCAD bridge lifecycle. No AutoCAD host execution occurred in this container.
