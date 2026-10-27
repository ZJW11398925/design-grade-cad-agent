# Independent Review Checklist — E2E-FIXTURE-001

**Purpose:** review the shared synthetic fixture and its environment/DXF vertical slice before any claim of broader integration. The reviewer should be independent of the authoring thread.

## Artifacts to inspect

1. `site-fixture-v0.1.json`
2. `site-fixture-contract-v0.1.md`
3. `site-fixture-cad-ir-v0.1.json`
4. `local-e2e-fixture-env-001.json` and `run_fixture_benchmark.py`
5. `site-fixture-v0.1.dxf`, `site-fixture-v0.1-dxf-manifest.json`, and `compile_fixture_to_dxf.py`
6. `local-e2e-fixture-slice-001.md`
7. Existing upstream contracts: `working/cad-bim-validator/cad-ir-contract-v0.1.yaml`, `working/building-massing/building-object-schema-v0.1.yaml`, `working/sketch-trace/trace-object-schema-v0.1.yaml`, `working/environment-analysis/analysis-dependency-contract-v0.1.yaml`.

## Required review questions

- **Schema consistency:** does the emitted CAD-IR instance preserve the declared CAD-IR fields and avoid silently inventing final semantics for fields that are still provisional?
- **Identity and provenance:** are stable IDs, geometry revisions, source Trace references, height states and object mapping preserved through fixture → CAD-IR → DXF?
- **Geometry correctness:** are polygon closure, line coordinates, units, sensor locations and geometry hashes checked independently of object counts?
- **Massing honesty:** is the BLDG-01 body clearly identified as a synthetic extrusion/projection check rather than a real 3D kernel/IFC result? Is BLDG-02 correctly blocked from Body generation because its height is unknown?
- **Environment logic:** are solar azimuth convention, local frame/north bearing, unknown/estimated height policy and context completeness represented without a silent default?
- **Dependency invalidation:** does the manifest include the upstream fields that can affect the result? Are height and north mutations actually reflected in the current result state?
- **DXF limits:** is the report explicit that ezdxf re-read is not independent CAD interoperability and that no standards compliance is claimed?
- **Failure cases:** which additional adversarial fixture mutations are needed before this adapter can be trusted beyond this exact synthetic example?
- **Evidence labeling:** are all claims separated into official-source facts, local synthetic tests, external-engine results, and still-blocked items?

## Required reviewer output

Return a short report with:

- `review_status`: `pass_for_next_experiment`, `conditional`, or `fail`;
- findings with severity, artifact/field, reproduction steps and expected/observed result;
- any false-positive or false-negative concern;
- required changes before the next integration experiment;
- explicit statement that this review does not certify real-site accuracy, third-party CAD compatibility, or legal compliance.

## Prohibited inference

- Do not call this a complete Sketch → Professional Site Model → CAD/BIM pipeline.
- Do not promote a synthetic fixture value into a design default.
- Do not treat a passed DXF audit as design correctness.
- Do not treat a dependency hash as proof of simulation accuracy.
- Do not self-approve the project’s A1 or production gate based only on the same authoring thread.
