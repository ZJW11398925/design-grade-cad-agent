"""M4d-2b candidate-C evidence: bounded co-design search outcome.

C is the result of a bounded generate-and-test search over group orders plus a
bounded local repair (building micro-moves with access rebuild and full check
evaluation).  When no hard-valid variant improves candidate B, the honest
outcome is ``no_improvement_same_as_b``; C is not promoted.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from dgcad_design.co_design import build_candidate_c  # noqa: E402

OUT = ROOT / "docs" / "e2e" / "design-candidate-c-001"


def _write(name: str, payload) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    if name.endswith(".md"):
        text = str(payload)
    else:
        text = json.dumps(payload, indent=2, ensure_ascii=False) + "\n"
    (OUT / name).write_text(text, encoding="utf-8", newline="\n")


def main() -> int:
    result = build_candidate_c(
        ROOT / "docs" / "e2e" / "sketch-001",
        ROOT / "fixtures" / "design" / "design-basis-001.yaml",
    )
    model_keys = {
        "building_layout",
        "road_layout",
        "road_access",
        "green_layout",
        "parking_layout",
        "consistency",
        "group_quality",
        "access_meta",
    }
    payload = {key: value for key, value in result.items() if key not in model_keys}
    local = payload.get("local_repair") or {}
    if isinstance(local, dict):
        proposals = local.get("proposals") or []
        log = local.get("log") or []
        local["proposal_count"] = len(proposals)
        local["accepted_count"] = sum(
            1 for entry in log if entry.get("accepted")
        )
        local["rejected_count"] = sum(
            1 for entry in log if entry.get("accepted") is False
        )
    _write("candidate-c.json", payload)

    decision = result.get("decision")
    record = result.get("selected_record") or {}
    comparison = result.get("comparison_vs_b") or {}
    local = result.get("local_repair") or {}
    readme = f"""# M4d-2b — candidate C bounded co-design search

**Outcome: `{decision}`**

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
| decision | control | **{decision}** |
| hard checks | 13 pass + 11 info + 5 deferred + 0 fail | same as B |
| non-contiguous groups | {record.get('groups_non_contiguous')} / 17 | {record.get('groups_non_contiguous')} / 17 |
| row runs | {record.get('total_row_runs')} | {record.get('total_row_runs')} |
| displacement max / mean | {record.get('displacement_max_m'):.2f} / {record.get('displacement_mean_m'):.2f} m | same as B |
| added road length | {record.get('added_road_length_m'):.2f} m | same as B |
| local-repair proposals / accepted | — | {local.get('proposal_count')} / {local.get('accepted_count')} |

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
"""
    _write("README.md", readme)
    print(
        json.dumps(
            {
                "out": str(OUT),
                "decision": decision,
                "same_as_b": result.get("same_as_b"),
                "hard_ok": result.get("hard_ok"),
                "variant_count": result.get("variant_count"),
                "local_proposals": local.get("proposal_count"),
                "local_accepted": local.get("accepted_count"),
                "comparison_vs_b": comparison,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
