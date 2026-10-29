# Full-site experimental evidence (M4d-1, 0.24.0)

This directory is a **research draft** for the full-site expansion under
`design-synthesis-v0.9` (v0.8 superseded; 29 design checks + 3 DXF = 32 items).
It is not a complete design and not a claim that the full-site design is
finished.

## What was generated

- `full-site-layout`: all **55 buildings** packed into a regularized full-site
  layout (18 rows / 8 superblocks (36 row records)) against the **frozen 44-road design
  network**, keeping the focus group G-01 (7 buildings / 16 units) and
  preserving **109 units / 2,398 households**.
- Geometry (measured by `src/dgcad_design/consistency.py`, no widened
  tolerances):
  - all footprints inside the published site boundary minus the declared setback;
  - pairwise building overlap ≤ 0.01 m²;
  - adjacent full-site rows: min **19.999999999999943 m** (required 20 m ±0.01);
  - building to road corridor edge: min **3.0163622902759215 m** (required 3 m);
  - designed green: **15.93%** of the site (<0.30, **deferred**; the 61.06% open-space tiling — 124,633.20046173329 m², 10 parcels — is auxiliary only, not designed green);
  - boundary containment / main-road overlap / topology / access-road geometry
    of the frozen network: pass (as in the focus design).
- Displacement: source → design sum **2,328.95 m**, max **147.25 m**, mean
  42.34 m (all 55 buildings; the full-site regularization is a real layout
  change).
- DXF: **547 entities** (all 55 buildings drawn), readback **547/547**,
  XDATA 11 fields, privacy pass; `full-site-preview.svg` and `.png`.
- Checks (`full-site-consistency.json`): **29 design checks = 11 pass + 11 info
  + 5 deferred + 2 fail**; `DESIGNED_GREEN_RATIO` is one of the deferred checks.

## The two honest failures

| check | status | measured |
|---|---|---|
| `ROAD_ACCESS_COVERAGE` | **fail** | 0.0 — 17 relation errors / 0 of 17 groups served |
| `DEAD_END_RESOLUTION` | **fail** | 17 unresolved |

Cause: the declared group-access relations and access terminals were generated
for the **focus layout**. Relocating the other 48 buildings leaves every
declared access relation outside the terminal band, so group access must be
recomputed (or the roads/access network co-designed) before this can become a
complete design. Regenerating the road network from the full-site layout does
**not** solve it: it breaks `FULL_SITE_ROAD_CLEARANCE` (min 0 m, 17 buildings below 3 m).

This is the known M4d integration gap, reported rather than hidden. The focus
design (`docs/e2e/design-synthesis-001/`) remains the canonical design draft;
this sheet demonstrates the full-site geometry engine, checks and DXF path.

## Reproduce

```bash
python -m pytest tests/test_full_site_layout.py tests/test_full_site_constraints.py tests/test_full_site_evidence.py -q
python scripts/design/render_full_site.py --layout full-site --output-dir docs/e2e/design-synthesis-full-site-001
python scripts/design/build_full_site_evidence.py
```

## Files

- `full-site-summary.json` — sheet summary (55 buildings, 109 units, 2,398
  households, layout source, road access gap, clearance/spacing/green).
- `full-site-consistency.json` — the 29-check report (2 fail, as above).
- `full-site-proposal.dxf` — editable full-site DXF (547 entities).
- `full-site-readback-manifest.json`, `full-site-validation.json`,
  `full-site-privacy.json`, `full-site-cad-ir.json`, `full-site-scene-snapshot.json`.
- `full-site-preview.svg` / `.png` — full-site plan preview.
- `full-site-visuals.json` — preview generation metadata.

## Non-claims

- This is not a construction/permit drawing, not human-confirmed, and not a
  code/fire-access/daylight/accessibility compliance result.
- The full-site layout is a **geometric feasibility draft**; it is not yet a
  coordinated design with recomputed group access, road hierarchy and detailed
  junctions.
- The full-site green account is a tiled designed-green account outside
  buildings/roads, not a landscape design.
- M4d-2 (road/access co-design) is required before this can become the
  canonical design.
