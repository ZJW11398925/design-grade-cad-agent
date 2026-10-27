#!/usr/bin/env python3
"""Run or block CASE-SKETCH-001-HANDOFF-A and refresh its evidence directory.

The committed review record is an authorization, not an object-level geometry
review. This script therefore records a blocked evidence package and a review
packet until a signed human_object_review exists.
"""
from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from dgcad_domain import (  # noqa: E402
    SketchHandoff,
    SketchHandoffNotConfirmed,
)
from dgcad_e2e import (  # noqa: E402
    SketchHandoffProject,
    build_review_packet,
    write_blocked_evidence,
)

FIXTURE = ROOT / "fixtures" / "sketch" / "CASE-SKETCH-001-HANDOFF-A"
OUT = ROOT / "docs" / "e2e" / "sketch-handoff-a"
SKETCH = "docs/e2e/sketch-001/source/sketch.png"
SKETCH_HREF = "../sketch-001/source/sketch.png"
IMAGE_SIZE = (1023, 1537)

EVIDENCE_FILES = (
    "handoff.yaml",
    "review-record.yaml",
    "review-packet.json",
    "review-packet.html",
    "review-request.yaml",
    "review-confirmation-template.yaml",
    "handoff-summary.json",
    "blocked.json",
    "canonical-snapshot.json",
    "cad-ir.json",
    "pilot.dxf",
    "readback-manifest.json",
    "validation.json",
    "provenance-map.json",
    "integrity.json",
    "road-topology.json",
    "coordinate-sensitivity.json",
    "privacy.json",
    "shadow-not-run.json",
    "domain-fixture.yaml",
)


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    for name in EVIDENCE_FILES:
        (OUT / name).unlink(missing_ok=True)
    shutil.rmtree(OUT / "runtime", ignore_errors=True)

    handoff = SketchHandoff.load(
        FIXTURE / "handoff.yaml",
        FIXTURE / "review.yaml",
        require_confirmation=False,
        verify_sources=True,
        root=ROOT,
    )
    packet = build_review_packet(
        handoff,
        OUT,
        sketch_path=SKETCH,
        sketch_href=SKETCH_HREF,
        image_size=IMAGE_SIZE,
    )

    if handoff.review.review_kind == "designer_authorized_pilot":
        summary = write_blocked_evidence(
            handoff,
            OUT,
            handoff_path=FIXTURE / "handoff.yaml",
            review_path=FIXTURE / "review.yaml",
            code="HUMAN_OBJECT_REVIEW_REQUIRED",
            message=(
                "the designer authorized a pilot but no object-level "
                "geometry review is recorded"
            ),
            packet=packet,
            root=ROOT,
        )
    elif handoff.review.review_kind == "test_double":
        summary = write_blocked_evidence(
            handoff,
            OUT,
            handoff_path=FIXTURE / "handoff.yaml",
            review_path=FIXTURE / "review.yaml",
            code="TEST_DOUBLE_NOT_EVIDENCE",
            message="a test double is never published as real evidence",
            packet=packet,
            root=ROOT,
        )
    else:
        if handoff.review.review_packet_sha256 != packet["packet_sha256"]:
            raise SystemExit(
                "review_packet_sha256 does not match the generated packet"
            )
        project = SketchHandoffProject.create(
            FIXTURE / "handoff.yaml",
            FIXTURE / "review.yaml",
            OUT,
            root=ROOT,
        )
        summary = project.run_pilot()
        if not summary["privacy"]["ok"]:
            raise SystemExit("DXF privacy scan failed")
        if not summary["integrity"]["ok"]:
            raise SystemExit("source integrity check failed")

    shutil.rmtree(OUT / "runtime", ignore_errors=True)
    print(
        json.dumps(
            {
                "handoff_id": summary["handoff_id"],
                "status": summary["status"],
                "review_kind": summary["review_kind"],
                "object_geometry_review": summary["object_geometry_review"],
                "human_confirmation_claimed": summary[
                    "human_confirmation_claimed"
                ],
                "site_boundary_authority": summary[
                    "site_boundary_authority"
                ],
                "site_canonical_id": summary["site_canonical_id"],
                "review_packet_sha256": packet["packet_sha256"],
                "dxf": summary.get("dxf"),
                "blocked": summary.get("blocked"),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
