# M4d-2b — candidate C bounded co-design search (0.27.0)

**Outcome: `no_improvement_same_as_b`**

This round asked whether a bounded building/local-road co-adjustment could
improve candidate B's spatial-intent quality without breaking the 29 declared
checks. The search deliberately stayed bounded: it did **not** rewrite the
global layout algorithm or release the frozen 44-road main skeleton.

## What was searched

1. **20 deterministic group-order variants** of `layout_group_preserving`,
   each followed by a rebuilt access network (`build_co_design_access`) and the
   full 29-check evaluation. **5 variants are hard-valid**; three are
   quality-identical to B, `y_asc_swap12` trades fewer row runs (41 vs 43) for
   worse mean displacement (59.02 vs 47.92 m) and more road (316.08 vs
   189.06 m), and `y_asc_rotate1` is worse (46 runs, 293.42 m max, 445.50 m
   road). The other 13 fail `FULL_SITE_NS_SPACING`/`FULL_SITE_ROAD_CLEARANCE`;
   2 variants cannot generate a layout (recorded as errors).
2. **Bounded local repair** from B: one-building micro-moves on the
   worst-fragmentation groups, each followed by a rebuilt access network and
   full hard-check evaluation; a move is accepted only on a strict improvement
   of (non-contiguous groups, displacement max, displacement mean).

## Result

| | B | C |
|---|---|---|
| decision | control | **no_improvement_same_as_b** |
| hard checks | 13 pass + 11 info + 5 deferred + 0 fail | same as B |
| non-contiguous groups | 12 / 17 | 12 / 17 |
| row runs | 43 | 43 |
| displacement max / mean | 278.46 / 47.92 m | same as B |
| added road length | 189.06 m | same as B |
| local-repair proposals / accepted | — | 8 / 0 |

Because the selected C variant is the same layout/access as B, the M4d-2a
source-green and access layers are **inherited unchanged**: building-occupied
source green **713.445 m²**, road-occupied **73.815 m²**, retained
**10,199.151 m² (92.83%)**, preserved/shrunk/cancelled **7/5/0**; access L1
**17/17**, L2 **0/17**, L3 **26/55** frontage, L4 **0 driveway**. No candidate-C
DXF is emitted, so none of these values is a new CAD deliverable.

## Four-level C status

| level | C |
|---|---|
| geometric hard checks | **pass** (`hard_ok = true`; 29 = 13 pass + 11 info + 5 deferred + 0 fail) |
| design-intent quality | descriptive; **same as B** (12/17 fragmented, 43 runs, max 278.46 m), no improvement |
| deferred design items | **5** (inherited from B) |
| real CAD host verification | **not_verified** (no C DXF) |

C is **not promoted**. B remains the sole hard-valid research baseline, still
not a professional design (5 deferred, host not verified, 26/55 frontage, no
internal group roads, no garage driveway).

**No candidate C is promoted.** Two hard-valid variants are distinct from B,
but neither improves the declared lexicographic selection key:
`y_asc_swap12` improves 2 row runs but worsens mean displacement by 11.10 m and
adds 127 m of road; `y_asc_rotate1` is worse on all three. The bounded local
repair proposals were all rejected: seven had no feasible position and one was
hard-valid but did not strictly improve the quality key. The evidence records
`same_as_b = true`; C is not promoted and no new DXF is emitted.

## Honest reading

- This is a **negative result**, not a completed joint design: under the
  frozen 44-road skeleton, the current group-preserving layout and the
  current 20 m row/3 m clearance/terminal-band rules, the tested bounded moves
  cannot improve B's 12/17 fragmented groups, 43 row runs or 278.46 m maximum
  displacement.
- The next step is not to relax thresholds. It is to enlarge the design space
  in a controlled way: allow local road re-alignment (not only rebuild the
  same connector pattern), allow selected main-road adjustments, or introduce
  a richer group-aware objective/optimizer in M4d-2c.
- B remains the sole hard-valid research baseline; it is still **not** a
  professional design (5 deferred items, no host verification, 26/55 building
  frontage, no internal group roads, no garage driveway).

## Reproduce

```bash
python -m pytest tests/test_candidate_c.py -q
python scripts/design/build_candidate_c_evidence.py
```

Artifact: `candidate-c.json` (variant table, local-repair log, decision).

Evidence paths: **A/B** in `../design-co-design-001/` (A/B DXF 584/587),
**M4d-2a audit** in `../design-intent-audit-001/`, and **C** here (no C DXF).
Candidate-C suites collect **11 candidate-C + 4 candidate-C-evidence = 15
tests**; project baseline **571 passed** (556 + 15). C is a negative result:
the bounded generate-and-test search did not improve B, and the next step is
M4d-2c (local road re-alignment / selected main-road adjustment / stronger
optimizer), not relaxing thresholds.
