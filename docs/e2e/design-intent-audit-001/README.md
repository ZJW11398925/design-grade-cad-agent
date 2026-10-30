# M4d-2a — Spatial intent integrity and candidate quality audit (0.26.0)

**Scope:** this round does **not** rewrite the layout algorithm. It adds
independent, descriptive measurements to the M4d-2 A/B experiment so that
"hard-valid on the 29 declared checks" is not mistaken for a successful
professional design. Every number below is recomputed from geometry; no metric
is a gate, a score or a ranking, and no threshold was changed.

## Four-level candidate status

| level | baseline (M4d-1) | A | B |
|---|---|---|---|
| geometric hard checks | **fail** (`ROAD_ACCESS_COVERAGE`, `DEAD_END_RESOLUTION`) | **fail** (`FULL_SITE_ROAD_CLEARANCE` 2.825 m) | **pass** (29 = 13 pass + 11 info + 5 deferred + 0 fail) |
| design-intent quality | descriptive only; 10/17 groups fragmented | descriptive only; 10/17 fragmented | descriptive only; **12/17 fragmented** |
| deferred design items | **5** | **5** | **5** (parking capacity, garage driveway, garage layout, designed green, final FAR) |
| real CAD host verification | not verified | not verified | not verified (ezdxf internal readback only) |

**B is the only candidate that passes the current 29 declared checks. It is
not a complete professional design and is retained as a research baseline.**

## 1. The 17 groups are inferred, not designer-confirmed

- Method: building centroid distance **45.0 m** (`basis.group_distance_m`),
  main-road **8.0 m** buffer, transitive **Union-Find single-linkage** merging.
- The chain is real: the longest inferred group (G-01) has source-member
  pairwise distance **209.738 m**, far beyond 45 m.
- `groups_preserved = 17` only means member IDs are complete. `groups_split`
  (non-adjacent design rows) is a different, spatial measure: baseline **10**,
  A **10**, B **12**.
- G-01 has **9 inferred members**; the focus layout preserves **7**
  (`SK-BLD-0038` / `SK-BLD-0061` are not in the focus set).

## 2. Group quality (descriptive, no gate)

| metric | baseline | A | B |
|---|---|---|---|
| groups with non-contiguous rows | 10/17 | 10/17 | **12/17** |
| total row runs | 29 | 29 | **43** |
| max row gap | 5 | 5 | **12** |
| mean group pairwise distance | 88.01 m | 88.01 m | 83.59 m |
| max group span | 271.84 m | 271.84 m | **294.50 m** |
| relative-position distance change mean / P90 / max | 34.31 / 85.91 / 191.84 m | same | 35.14 / 67.80 / **258.77 m** |
| nearest-neighbour preservation | 0.60 | 0.60 | 0.66 |
| building displacement mean / P90 / max | 42.34 / 108.35 / 147.25 m | same | **47.92** / 102.83 / **278.46 m** |
| group centroid displacement mean / max | 37.00 / 110.73 m | same | 33.99 / **140.12 m** |

A and baseline share the M4d-1 building layout (A only rebuilds access).
B's mean group distance, nearest-neighbour preservation and group-centroid mean
are slightly better; its **fragmentation and displacement tail are worse**.
This is a trade-off, not a uniform improvement.

## 3. Source-green retention (12 source objects, 10,986.4 m²)

| metric | baseline | A | B |
|---|---|---|---|
| retained open-space area | 10,076.757 m² (91.72 %) | 9,819.92 m² (89.38 %) | 10,199.151 m² (92.83 %) |
| building-occupied source green | **845.541 m² (7.70 %)** | **845.541 m² (7.70 %)** | **713.445 m² (6.49 %)** |
| road-occupied source green | 64.113 m² | **320.949 m²** | **73.815 m²** |
| preserved / shrunk / cancelled | 7 / 5 / 0 | 7 / 5 / 0 | 7 / 5 / 0 |
| new designed green | 20,864.1 m² | 20,206.0 m² | 19,457.6 m² |

No source green is wholly cancelled. Baseline and A share the M4d-1 building
layout, so both occupy **845.541 m²** of source green; B reduces that to
**713.445 m²**. A's rebuilt access raises road-occupied source green from
**64.113 m²** to **320.949 m²**. The building layout's buildable area does not
subtract source greens. Area retention (~90 %) is **not** spatial or intent
retention (`area_retention_is_not_intent_retention = true`); continuity,
access and landscape usability are not assessed here.
An earlier draft of this table used wrong values; the table above is recomputed
from `green-retention.json` and supersedes it.

## 4. Access semantics: 17/17 is group-level only

| layer | baseline | A | B |
|---|---|---|---|
| **L1** group external access | 0/17, 17 errors, 17 unresolved dead ends | **17/17**, 0 errors, 0 unresolved | **17/17**, 0 errors, 0 unresolved |
| **L2** internal group roads | not designed | not designed | not designed |
| **L3** building frontage (geometry only) | 15/55 front a road, median 12.14 m, max 58.26 m | **24/55**, median 6.00 m, max 58.18 m | **26/55**, median 6.00 m, max 53.28 m |
| **L4** garage driveway | 5 entrances, 2 proximity, **0 driveway** | same | same |

`ROAD_ACCESS_COVERAGE = 17/17` must not be read as "55 buildings are fully
connected": only **26/55** B buildings front a road in the geometric sense,
internal group roads are not designed, and no garage driveway is designed.

## 5. Clearance robustness: 1.6 cm is not a robust margin

The B minimum corridor clearance is **3.0164672267820585 m**, only 0.016 m
above the 3.0 m rule. The source sketch registration residual is mean
**24.51 px**, max **43.42 px** (about a 10 m order at 2.438 px/m). Perturbing
the generated geometry deterministically:

| relative perturbation | B min clearance | fraction of samples < 3 m |
|---|---|---|
| 0 m | 3.0165 m | 0 % |
| 0.1 m independent | 2.8887 m | **100 %** |
| 1.0 m independent | 1.7037 m | **100 %** |
| 2.0 m independent | 0.3246 m | **100 %** |
| any magnitude, common datum | 3.0165 m | 0 % (control) |

Any decimetre-level **relative** coordinate error already violates the 3.0 m
rule in every sample. The 3.0 m rule is unchanged; the correct status is
**model-coordinate internal pass, engineering robustness not established**.

## 6. What this changes (and what it does not)

- It does **not** promote B to a final design. B remains a hard-valid research
  baseline with 12/17 fragmented groups, 278.46 m maximum building displacement,
  713.445 m² source green occupied, 26/55 frontage, no internal roads, no garage
  driveway and no real-host verification.
- It gives M4d-2b a measurement basis: group fragmentation, relative-position
  change, displacement distribution, source-green occupation and access layers.
- Recommended next step: **M4d-2b candidate C** — a bounded building/local-road
  co-adjustment loop, with these metrics as descriptive comparison, hard-first
  evaluation, no single score, and explicit reporting of what each candidate
  sacrifices.

## Reproduce

```bash
python scripts/design/audit_intent_robustness.py
python scripts/design/build_intent_audit_evidence.py
python -m pytest tests/test_intent_metrics.py tests/test_green_retention.py tests/test_access_semantics.py tests/test_intent_robustness.py -q
```

Artifacts: `audit.json`, `inferred-groups.json`, `group-quality.json`,
`green-retention.json`, `access-semantics.json`, `robustness.json`.

The audit suites collect **14 intent-metrics + 8 green-retention + 9
access-semantics + 4 robustness + 6 audit-evidence = 41 tests**; the project
baseline is **556 passed**. No metric is a gate, score or ranking, and
historical M4d-1/1a/2 evidence is preserved.
