# E2E-FIXTURE-001 Contract v0.1

**Status:** provisional synthetic integration fixture; not a real design, survey, code profile or engineering default.

## Required envelope

- `fixture_id`, `fixture_revision`, and explicit `synthetic_only: true`.
- A coordinate frame with `x=east, y=north, z=up`, units, north-bearing convention and coordinate state. A local metric frame is not the same as a georeferenced CRS.
- Site location and offset-aware timestamp solely for the solar-position test; the location is a synthetic reference location and must not be treated as the project's real geographic location.
- Stable `object_id`, `object_class`, `geometry_revision`, geometry, `provenance`, `evidence_state`, `review_state`, and `locked` flag for each object.
- Building height/base elevation fields with explicit `confirmed`, `estimated`, or `unknown` state; a numeric value is forbidden when height state is `unknown`.
- A small sensor grid with stable IDs and known local coordinates.
- Declared context coverage and explicit expected outputs for each sensor.

## Required invariants

1. Every derived object points back to one or more source/trace IDs, even when the source trace is a synthetic fixture stub.
2. Changing footprint, body, height, placement, terrain, north, time or method revision invalidates dependent environment results.
3. Unknown/estimated inputs remain visible; the fixture must not coerce them to confirmed.
4. Every output names the exact input revision and metric definition.
6. Geometry content hashes detect geometry changes even if an upstream producer incorrectly reuses the previous revision ID.
5. A successful environment slice is not evidence of road design quality, CAD interoperability, legal compliance or real-sketch performance.

## Expected vertical-slice results

For `E2E-FIXTURE-001` at the declared test time:

- `SENSOR-GREEN-01`: shaded by known-height synthetic building `BLDG-01`.
- `SENSOR-GREEN-02`: unknown because the ray meets `BLDG-02`, whose height is unknown.
- `SENSOR-GREEN-03`: sunlit within the explicitly declared synthetic context.
- Change `BLDG-01.height_revision`: old environment result must be stale.
- Change project +Y true-north bearing: sensor classifications or the dependency fingerprint must change; the old result cannot remain current.

The expected states are analytic test expectations for the fixture only.
