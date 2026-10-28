# 0.12.0 pilot evidence — superseded

These files are the CASE-SKETCH-001-HANDOFF-A evidence produced at commit
`4fe9dc7` (v0.12.0). They are preserved for history, not as current evidence.

What changed in 0.13.0 / Milestone 4b.1:

- The v0.12.0 review record was based on a **designer authorization to run a
  pilot**, not on an object-level geometry or coordinate review. It recorded
  `human_confirmed_trace: true` and `confirmed_for_pilot` for seven objects.
  That overclaimed what had actually happened.
- v0.12.0 mapped the published sketch boundary to canonical `SITE-001` with
  `human_confirmed` authority. The private redline is the authoritative site
  reference; the sketch boundary is not.
- v0.12.0 did not carry the pilot scope into the trace, canonical model,
  CAD-IR or readback manifest.
- v0.12.0 called the transform `LOCAL-ENU-XY-ZUP` even though no east/north
  orientation was established. The transform is a uniform scale, translation
  and y-flip, not the six-point homography.

The current evidence is blocked at the human review gate. See
`../README.md`, `../blocked.json`, `../review-packet.html` and
`../review-confirmation-template.yaml`.

Do not cite the files here as proof of human geometry confirmation.
