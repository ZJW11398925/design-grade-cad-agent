# BATCH-005 Source Map v0.1

**Acquisition date:** 2026-10-26  
**State:** first bounded official-source pass; no tool selected as final architecture.  
**Evidence convention:** public docs/source facts are not local runtime verification.

## SRC-ENV-001 — Ladybug core / Sunpath

- Official repository: https://github.com/ladybug-tools/ladybug
- API/documentation entry: https://www.ladybug.tools/ladybug/docs/
- Retrieved source files: `README.md` blob SHA `d74e9d8fe9d0b171b4f801085d6cda2ec5cbeff1`; `ladybug/sunpath.py` blob SHA `2962d6f9c3ef948213218f61fa5cc7349a18e0c9`.
- Repository LICENSE: AGPL-3.0 (blob SHA `0ad25db4bd1d86c452db3f9602ccdbe172438f52`). Verify the exact installed release and dependency/license inventory before product use.
- Verified source facts: the README shows `Location(latitude, longitude, time_zone)` → `Sunpath.from_location()` → `calculate_sun()` and publishes a Sydney example (15 Nov, 11:00: altitude 72.26°, azimuth 32.37°). The source defines latitude/longitude/time-zone/north-angle separately and documents that north angle is relative to the positive Y axis.
- Official tests include NOAA-comparison examples for New York and Sydney, including Sydney 72.26° / 32.37°.
- Role: solar-position and weather-file reference/candidate; not itself proof of 3D site occlusion or regulatory compliance.
- Source evidence: https://github.com/ladybug-tools/ladybug/blob/master/README.md ; https://github.com/ladybug-tools/ladybug/blob/master/ladybug/sunpath.py ; https://github.com/ladybug-tools/ladybug/blob/master/tests/sunpath_test.py

## SRC-ENV-002 — pvlib-python solar position

- Official repository: https://github.com/pvlib/pvlib-python
- API: https://pvlib-python.readthedocs.io/en/stable/reference/generated/pvlib.solarposition.spa_python.html
- License: BSD-3-Clause, confirmed in repository LICENSE (https://github.com/pvlib/pvlib-python/blob/main/LICENSE).
- Verified source facts: `spa_python` implements the NREL Solar Position Algorithm (SPA), requires a localized timestamp or assumes UTC, and takes latitude/longitude plus optional altitude, pressure, temperature and delta-T. The documentation cites Reda & Andreas, *Solar Position Algorithm for Solar Radiation Applications*, Solar Energy 76(5), 577–589 (2004), DOI 10.1016/j.solener.2003.12.003, and its 2007 corrigendum.
- Independent reference report: NREL/TP-560-34302, https://docs.nrel.gov/docs/fy08osti/34302.pdf.
- Role: higher-assurance solar-position reference candidate. **Not locally installed or run**: package installation was attempted but blocked by DNS/network unavailability in the sandbox.

## SRC-ENV-003 — Honeybee-Radiance direct sun hours

- Official repository: https://github.com/ladybug-tools/honeybee-radiance
- Direct Sun Hours recipe: https://docs.ladybug.tools/hb-radiance-primer/components/3_recipes/direct_sun_hours
- Repository README describes it as a Radiance extension for daylight/radiation simulation and documents a pytest test suite. The repository LICENSE is AGPL-3.0 (verify exact release/dependency notices before distribution).
- Verified recipe inputs: a Honeybee model with sensor grids, WEA/EPW weather input, timestep and north orientation; output includes raw sensor-by-time sun visibility results and cumulative hours.
- Role: physically richer, scalable analysis candidate after the local geometry baseline. No local Radiance/Honeybee runtime was available; no simulation is claimed.

## SRC-ENV-004 — Ladybug direct sun hours (geometry ray test)

- Official docs: https://docs.ladybug.tools/ladybug-primer/components/3_analyzegeometry/direct_sun_hours
- Verified facts: direct-sun results are derived from sun vectors and ray intersections against test geometry/context; the documentation warns that the CAD environment's ray intersections do not scale as well for complex geometry or many test points, and recommends Honeybee-Radiance for complex studies. Grid size and timestep affect meaning/resolution.
- Role: close analogue for the small deterministic ray/prism probe in this workspace, not proof of production scalability.

## SRC-ENV-005 — momepy urban morphology

- Official docs: https://docs.momepy.org/
- Official repository: https://github.com/pysal/momepy
- License: BSD-3-Clause in repository LICENSE.
- Verified scope: quantitative urban morphology, building/street-network shape, density, diversity, spatial relationships and connectivity. `Streetscape` includes measures such as building height, height-to-width ratio, sky-view-related cross-section measures and building coverage ratio when suitable data are provided.
- Role: candidate for COV-15 morphology and street-context indicators. It is **not** a physical solar-position engine or substitute for ray-based shadow/daylight simulation.

## Acquisition limits

- The web/source inspection is a bounded first pass, not an exhaustive ecosystem survey; total search result counts and pagination completeness were not established.
- No Honeybee-Radiance/Radiance, Ladybug, pvlib or momepy package was run in this sandbox. Only the custom, deliberately limited Shapely-based probe was run locally.
- AGPL-3.0 on Ladybug/Honeybee repositories is a material integration consideration. This record is not legal advice and does not decide whether/how the projects may be combined or distributed.
