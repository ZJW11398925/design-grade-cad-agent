# R1 Package Boundaries v0.1

## Foundation core

`foundation.model` — typed state objects only.  
`foundation.store` — canonical current state and atomic commit.  
`foundation.authority` — permission/lock decisions.  
`foundation.dependency` — invalidation only.  
`foundation.validation` — later may split from model when validators grow.

## Future adapters — deliberately absent from entry prototype

`adapters.sketch` -> R1.1, gated by EP-R1-SKETCH-001.  
`domain.building` -> R1.2.  
`domain.road` -> R1.3, gated by EP-R1-ROAD-001.  
`adapters.dxf` -> R1.4, real delivery claim gated by EP-R1-PROFILE-001.  
`adapters.ifc` -> R1.6, gated by EP-R1-IFC-001.  
`analysis.shadow` -> R1.5, independent accuracy claim gated by EP-R1-ENV-001.  
`agent.orchestrator` -> only after Foundation authority/proposal contracts are stable.

## Dependency direction

Domain/adapters may depend on Foundation contracts. Foundation must never import Shapely, ezdxf, IfcOpenShell, Ladybug/Honeybee, SAM, or application UI code.

This is the key anti-lock-in boundary.
