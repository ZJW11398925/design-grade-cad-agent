# Experiment C — collaborative design and repair

Source focus buildings: 9
Uncorrected candidate: 9 buildings,
failed checks: FOCUS_ROAD_CLEARANCE,
road-clearance conflicts: 1.
Corrected candidate: 7 buildings,
dropped: SK-BLD-0038, SK-BLD-0061,
checks: {"FAR_RANGE": "pass", "PARKING_MIN_ONE_PER_HOUSEHOLD": "pass", "PARKING_ENTRANCES": "pass", "UNIT_COUNT_PRESERVED": "pass", "FOCUS_NS_SPACING": "pass", "FOCUS_BOUNDARY_SETBACK": "pass", "FOCUS_BUILDING_OVERLAP": "pass", "FOCUS_ROAD_CLEARANCE": "pass", "ROAD_CONNECTIVITY": "pass", "ROAD_WIDTHS": "pass", "GREEN_RATIO": "pass", "FULL_SITE_NS_SPACING": "deferred"}.

The repair is not a cosmetic move: the Agent moves the design into a
main-road-bounded free block, re-packs the rows, and drops the buildings that
cannot fit at the declared 20 m spacing, 5 m setback and 3 m road clearance.
The dropped IDs and reasons are recorded in the 4c `design-diff.json`.

Open-source contribution in this candidate:
- Building Regulariser: limited gain on already-regular sketch footprints;
  not the missing building generator.
- OSMnx: consolidated source network 309/333 -> 117/141, but with design
  widths it still leaves no 120x90 m buildable focus rectangle; it is a
  topology preprocessor, not the design hierarchy.
- PyGeoOps: 11 centerlines for 11 road areas, 10 of 11 multi-component;
  useful per-area candidates, not a connected design network.
- Clothoids: a single G1 Hermite fit on MAIN-08 deviates by 356 m Hausdorff;
  a chain/control-point adapter is required.
- The corrected 4c road centerline graph has
  5 components even though the
  corridor union is one polygon. The current `ROAD_CONNECTIVITY` check uses
  the corridor union and is too weak; this is a known defect of the 4c draft.
  The next round should use the OSMnx-consolidated connected network as the
  topology base, then apply the design hierarchy.
- momepy: provides morphology metrics for comparing candidates, not a design
  generator.

The corrected candidate is the 4c standardized design DXF copied here. It is
`rule_derived`, not human-confirmed, and not code-compliant.
