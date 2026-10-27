# External Review Checklist — E2E-FIXTURE-001 Adapter/Profile v0.3

**Status:** `awaiting_external_review`. Do not mark complete from the authoring thread alone.

## Required preflight

1. Verify `review-manifest.json` hashes in the packet.
2. Run the documented v0.3 commands in a fresh extraction; record Python, Shapely, ezdxf and pytest versions.
3. Inspect the previous v0.2 conditional review and ensure the new fixes address its findings without mutating historical v0.2 artifacts.

## Review questions

- Does the validator reject paper-space entities under the declared `modelspace_only` policy?
- Does it reject nonzero polyline elevation, circle center Z, text insertion/alignment Z and non-world-XY extrusion?
- Does the executable Profile actually match the CAD-IR `profile_ref`, version, DXF version and units?
- Are unexpected layers rejected while `0` and `Defpoints` are explicitly allowed?
- Are entity-level color, linetype, lineweight, true-color and transparency overrides rejected under the stated BYLAYER policy?
- Are text style, rotation, width factor, alignment and height checked and included in the representation contract?
- Does solar zenith behave correctly for complete and incomplete context, including a sensor on/in a blocker?
- Are booleans rejected for metric inputs and coordinates?
- Do both `timestamp_starts_interval` and `timestamp_is_instant` modes return the intended interval count and coverage bounds? Are end points handled as documented?
- Are the mutation tests testing the validator rather than repeating the compiler's assumptions?
- Does the result clearly separate synthetic Profile compliance from design-office/national-standard compliance?

## Required independent environment check

If available, open `site-fixture-v0.3.dxf` in LibreCAD, FreeCAD Draft or AutoCAD, save a copy and read it back with a separate toolchain. Compare units, layer table, entity counts/types, XY/Z, text placement, and polygon ring geometry. Record application/version and any transformations or dropped metadata. Do not claim compatibility if this step is unavailable.

## Required response

Return `review_status`: `pass_for_next_experiment`, `conditional`, or `fail`; findings with severity and reproduction; false-positive/false-negative concerns; reproducibility; third-party CAD test outcome; and explicit non-claims.

## Prohibited inferences

Do not claim real sketch-to-CAD accuracy, professional road/building design quality, IFC correctness, third-party compatibility without a completed round-trip, design-office standard compliance, or legal/regulatory compliance. Do not approve A1 or production release from this packet alone.
