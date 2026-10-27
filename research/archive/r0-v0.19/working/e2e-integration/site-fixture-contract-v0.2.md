# E2E-FIXTURE-001 Contract v0.2

**Status:** provisional synthetic integration fixture; not a real design, survey, code profile or engineering default. v0.2 is a new immutable fixture revision (`fixture_revision: r2`); v0.1 is retained unchanged as historical evidence.

## Required envelope

- `fixture_id`, `fixture_revision`, and explicit `synthetic_only: true`.
- Coordinate frame with axis convention, units, north-bearing convention and coordinate state. A local metric frame is not the same as a georeferenced CRS.
- Site location and offset-aware timestamp solely for the solar-position test; the location is synthetic and must not be treated as the project's real geographic location.
- Stable object IDs, geometry revisions, provenance, evidence/review state and lock flags.
- Building height/base-elevation values and evidence states. A numeric height is forbidden when height state is `unknown`.
- For a current synthetic 3D body, an explicit stored mesh, coordinate frame, units, vertices and faces. A body cannot be declared current merely because a reference string exists.
- Stable sensor IDs, coordinates and explicit expected outcomes.

## Required invariants

1. Derived objects retain source/Trace lineage; synthetic fixture stubs are not represented as real source traces.
2. Changes to footprint, body, height value/state, base elevation, placement, terrain, north, time or method inputs invalidate dependent results even if an upstream revision ID is incorrectly reused.
3. Unknown/estimated inputs remain visible; no silent promotion to confirmed.
4. Body/footprint consistency is checked from stored body mesh coordinates, not by comparing the footprint object with itself.
5. Every result names the exact dependency manifest/fingerprint, metric definition and method version.
6. DXF source geometry hash and exported representation hash are distinct. Polygon/MultiPolygon rings carry part/ring roles; a DXF outline loop is not claimed to be a filled region.
7. A successful synthetic slice is not evidence of road design quality, real-sketch performance, third-party CAD interoperability, IFC correctness, or legal compliance.

## Expected environment outcomes

At the fixture's declared timestamp and synthetic location:

- `SENSOR-GREEN-01`: shaded by the known-height synthetic building `BLDG-01`.
- `SENSOR-GREEN-02`: unknown because the sunward ray intersects `BLDG-02`, whose height is unknown.
- `SENSOR-GREEN-03`: sunlit within the declared synthetic context.
- Mutations to height revision/value/state, base elevation, body/footprint content or north bearing change the dependency fingerprint; invalid body mesh mutations fail the body/footprint check.

These are analytic expectations for this fixture only. They are not regulatory sunlight-hours criteria.
