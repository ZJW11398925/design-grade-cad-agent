# BATCH-005 来源定位

**状态：** 首轮有界来源获取已执行（`RUN-005-01`）；本页不等于 exhaustive search 或 A1。

| Source ID | Official locator | Exact question / evidence captured | Local runtime status |
|---|---|---|---|
| SRC-ENV-001 | https://github.com/ladybug-tools/ladybug ; https://github.com/ladybug-tools/ladybug/blob/master/ladybug/sunpath.py ; https://github.com/ladybug-tools/ladybug/blob/master/tests/sunpath_test.py | Location, timezone, north-angle semantics; official Sydney/New York sun-position tests; repo LICENSE AGPL-3.0 | Not installed; used published Sydney values as sanity reference |
| SRC-ENV-002 | https://pvlib-python.readthedocs.io/en/stable/reference/generated/pvlib.solarposition.spa_python.html ; https://github.com/pvlib/pvlib-python/blob/main/LICENSE ; https://docs.nrel.gov/docs/fy08osti/34302.pdf | NREL SPA API input semantics, timezone-aware timestamps, solar-position reference report; BSD-3-Clause | Install attempted; DNS/network blocked; not run |
| SRC-ENV-003 | https://github.com/ladybug-tools/honeybee-radiance ; https://docs.ladybug.tools/hb-radiance-primer/components/3_recipes/direct_sun_hours | Model + sensor grids + WEA/EPW + timestep + north; raw sensor/time sun visibility and cumulative hours; repo LICENSE AGPL-3.0 | Not installed; not run |
| SRC-ENV-004 | https://docs.ladybug.tools/ladybug-primer/components/3_analyzegeometry/direct_sun_hours | Geometry ray-intersection role, context, grid size, timestep and scaling boundary | Documentation only |
| SRC-ENV-005 | https://docs.momepy.org/ ; https://docs.momepy.org/stable/api/momepy.Streetscape.html | Urban morphology, street network and streetscape indicators; BSD-3-Clause | Not installed; not run |

Searches used official project/API documentation and the NREL SPA report. Search result totals and pagination completeness were not established; do not claim exhaustive discovery. See `source-map-v0.1.md` for per-source evidence and limitations.
