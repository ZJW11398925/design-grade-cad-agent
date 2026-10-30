# M4d-2 — A/B building-road co-design experiment

Both candidates start from the same CASE-SKETCH-001 input, basis and frozen
44-road network; they differ in **how the buildings are placed**, and both use
the same rebuilt group-access generator (`build_co_design_access`). The old
focus-era access declarations are never reused.

| candidate | building layout | access | hard result |
|---|---|---|---|
| **M4D1-BASELINE** | M4d-1 full-site layout | old focus-era declarations | access 0/17, 17 unresolved |
| **A** | fixed M4d-1 full-site layout | rebuilt connectors (17, 362.09 m) | see below |
| **B** | group-preserving layout (17 groups; 39 rows) | rebuilt connectors | see below |

## M4d-2a audit qualification

The `HARD-VALID` stamp means **hard-valid on the 29 declared checks only**.
The M4d-2a intent audit (`../design-intent-audit-001/`) shows that B still has
**12/17 inferred groups fragmented**, **43 row runs**, **278.46 m** maximum
building displacement, **713.445 m²** of source-green area occupied by
buildings (baseline/A **845.541 m²**; road-occupied **64.113/320.949/73.815 m²**;
retained **10,076.757/9,819.92/10,199.151 m²**, preserved/shrunk/cancelled
**7/5/0**), **26/55** buildings with geometric road frontage (L3 baseline/A/B
**15/24/26 of 55**), no internal group roads (L2 0/17), no garage driveway
(L4 0), and **5 deferred** design items; the 3.016 m clearance is not robust to
a 0.1 m relative coordinate perturbation (**100% of samples <3.0 m**, B min
2.8887 m). Four-level B status: **geometric pass / intent descriptive /
deferred 5 / host not_verified**. B is a research baseline, not a professional
design. The project baseline is **556 passed** (515 + 41 audit tests).

## Measured results

| metric | baseline | A | B |
|---|---|---|---|
| buildings / units / households | 55 / 109 / 2,398 | 55 / 109 / 2,398 | 55 / 109 / 2,398 |
| hard check failures | 2 (access, dead ends) | 1 (FULL_SITE_ROAD_CLEARANCE) | 0 |
| hard-valid? | no | no | **yes** |
| checks (29 design) | — | 12 pass + 11 info + 5 deferred + 1 fail | **13 pass + 11 info + 5 deferred + 0 fail** |
| access coverage | 0.0 | 1.0 | 1.0 |
| access relation errors | 17 | 0 | 0 |
| dead ends unresolved | 17 | 0 | 0 |
| terminal band min / max (m) | 6.516 / 114.438 | 3.499999 / 3.499999 | 3.499999 / 3.499999 |
| building displacement mean / max (m) | 42.34 / 147.25 | 42.34 / 147.25 | 47.92 / 278.46 |
| group centroid displacement mean / max (m) | 37.00 / 110.73 | 37.00 / 110.73 | 33.99 / 140.12 |
| added road length (m) | 0 | 410.79 (17 connectors 362.095 m) | 189.06 |
| group split count | 10 | 10 | 12 |
| DXF entities / readback | — | **584 / 584** | **587 / 587** |

## Decision

**Recommendation: B**

Reasons:
- A: excluded: hard gate failure
- B: hard gates pass

Hard-first rule: a candidate failing any hard check (`FULL_SITE_BOUNDARY_SETBACK`,
`FULL_SITE_BUILDING_OVERLAP`, `FULL_SITE_ROAD_CLEARANCE`, `FULL_SITE_NS_SPACING`,
`ROAD_ACCESS_COVERAGE`, `DEAD_END_RESOLUTION`) is not a complete design. The
access rebuilds reach 17/17 coverage, but the **served-facade corridor** cannot
keep 3.0 m under the declared 3.4–3.5 m terminal band and 7 m branch width
(structurally 2.825 m; reported, not hidden). This is a real design-rule
conflict that M4d-2 exposes: the terminal band and the 3 m corridor rule need
coordination (e.g. terminal at corridor edge, narrower access, or a revised
access standard) rather than silently widening a tolerance.

## What this proves / does not prove

- Proves: both candidate paths can be generated from the same source, with all
  55 buildings / 109 units / 2,398 households preserved, 17 groups represented,
  and rebuilt access geometry (no `serves_group_ids`-only edits); the comparison
  is hard-first and reports failures honestly.
- Does not prove: a complete hard-valid full-site design exists under the
  current basis/constraints. No CAD deliverable is presented as a finished
  design. Candidate DXF **is** provided as evidence (`A/`, `B/`: editable DXF,
  readback manifest, validation, privacy scan, scene snapshot and preview;
  A **584 entities** / B **587 entities**, readback **584/584** and **587/587**,
  XDATA 11, privacy pass, audit 0/0; `comparison.svg` is the three-panel
  comparison). The A sheet is stamped `INCOMPLETE` for the clearance failure
  (`INCOMPLETE: FULL_SITE_ROAD_CLEARANCE FAIL (MIN 2.825 m < 3.0 m) - ROAD ACCESS
  17/17 - DESIGNED GREEN < 30%`); the B sheet is stamped `HARD-VALID CANDIDATE:
  0 HARD FAILS - ROAD ACCESS 17/17 - DEAD ENDS 0 UNRESOLVED - DESIGNED GREEN <
  30% (5 DEFERRED)`. Both sheets keep the potential-open-space / designed-green
  distinction. The new connector sidewalks are clipped along building
  footprints (17 connectors / 115.202 m² clipped); **A/B sidewalk overlap = 0**,
  and `access_meta.candidate` is generated, not hard-coded.
- Honest B residuals remain: **12 group splits**, group-centroid displacement
  max **140.12 m** / mean **33.99 m**, single-building max **278.46 m**.

## Reproduce

```bash
python -m pytest tests/test_co_design_access.py tests/test_group_preserving_layout.py tests/test_group_metrics.py tests/test_co_design_evidence.py -q
python scripts/design/build_co_design_evidence.py
```

The co-design suites collect **11 access + 10 group-layout + 11 group-metric +
11 evidence = 43 tests**; the M4d-2a audit adds **14 intent-metrics + 8
green-retention + 9 access-semantics + 4 robustness + 6 audit-evidence = 41
tests**, for a project baseline of **556 passed** (515 + 41).
