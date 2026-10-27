# BATCH-003 Source Locators

## Building Regulariser

- Repository: https://github.com/DPIRD-DMA/Building-Regulariser
- README SHA: `b680776f77f10aaeadd352db7bd27a2aff879afa`
- LICENSE SHA: `a4904a19518e805dd627e87624ba52d378869ea7` (MIT)
- Core regularization source: `buildingregulariser/regularization.py`, SHA observed in directory listing: `eb72b83cc36fc2da43d0678f82fe6558db481b9f`.
- Related independent implementation/docs lead: CartAGen feature edge reconstruction regularizer.

## UrbGEN

- Repository: https://github.com/trongtintr/UrbGEN
- README SHA: `be56b3be1e0b5cab60846697779bb5afc4f4d856`
- LICENSE SHA: `14b1ed66de72155da60041fd09001a7a3659b7aa` (MIT)
- Role in this research: massing grammar / constraint-driven design-space reference, not authoritative planning rule source.

## IfcOpenShell / Bonsai

- Repository: https://github.com/IfcOpenShell/IfcOpenShell
- README fetched at current v0.9.0 default/tag context, SHA `e21f8f9a3d871608af3a64361bd3eebc52bddb88`.
- Official geometry creation: https://docs.ifcopenshell.org/ifcopenshell-python/geometry_creation.html
- API geometry index: https://docs.ifcopenshell.org/autoapi/ifcopenshell/api/geometry/index.html
- GPLv3 text SHA: `810fce6e9bf2aa10265b85614db5ac65941ecf81`
- LGPLv3 text SHA: `0a041280bd00a9d068f503b8ee7ce35214bd24a1`
- Repository README labels ifcopenshell-python as LGPL-3.0-or-later; mixed-license components require component-level review.
- Bonsai docs: https://docs.bonsaibim.org/

## COMPAS

- Docs: https://compas.dev/compas/latest/
- Repository: https://github.com/compas-dev/compas
- README SHA: `a5d60f1b268b43c205a37fc9a815bf87c9950df6`
- LICENSE SHA: `359c0d7c80fb92853820c6bb9cc533577782e931` (MIT)

## BATCH-003 second-wave: regularization failure boundaries and IFC representation lifecycle

### Building Regulariser source/tests

- `buildingregulariser/regularization.py` — SHA `eb72b83cc36fc2da43d0678f82fe6558db481b9f`; [source](https://github.com/DPIRD-DMA/Building-Regulariser/blob/main/buildingregulariser/regularization.py). Inspected orientation histogram, edge snapping and edge reconnection logic.
- `tests/test_end_to_end.py` — SHA `6ffdf48ff1110875a540ed9eace46ec4286e5767`; [test](https://github.com/DPIRD-DMA/Building-Regulariser/blob/main/tests/test_end_to_end.py). Current test checks valid/non-null geometry, row count, input/output intersection, IoU >= 0.4 and perimeter within ±60%; this is not a design-grade topology acceptance contract.
- `tests/test_multipolygon.py` — SHA `fb0f2ed2216b4837d1526d178fd9faf6f36e9a3a`; [test](https://github.com/DPIRD-DMA/Building-Regulariser/blob/main/tests/test_multipolygon.py).
- `CHANGELOG.md` — SHA `788c2255db7dfa17083c47f4e5e1fcb9f610f149`; [changelog](https://github.com/DPIRD-DMA/Building-Regulariser/blob/main/CHANGELOG.md). Version 0.2.4 documents invalid-input / Issue #5 handling; 0.2.5 documents MultiPolygon regression tests and widened type handling.
- `pyproject.toml` — SHA `ea02153933e1fd89e959e3484616a77a51fc6f11`; [metadata](https://github.com/DPIRD-DMA/Building-Regulariser/blob/main/pyproject.toml). Package metadata states MIT and Python >=3.9; current classifiers include Python 3.13.

### Targeted issues (status must not be overgeneralized)

- [Issue #8](https://github.com/DPIRD-DMA/Building-Regulariser/issues/8), created 2025-10-02, closed 2025-10-16. Maintainer reply says each polygon is processed independently and has no concept of intersecting polygons; a topology-aware solution would require a significant rewrite. Current changelog 0.2.5 does not list this as fixed. Treat as unresolved capability risk unless a later implementation/retest proves otherwise.
- [Issue #5](https://github.com/DPIRD-DMA/Building-Regulariser/issues/5), created 2025-07-21, closed 2025-07-24. Maintainer reply points to invalid input geometries and says `make_valid` was added; changelog 0.2.4 explicitly records the fix. Treat as historical defect with a fix trail, not a claim of current failure.
- [Issue #4](https://github.com/DPIRD-DMA/Building-Regulariser/issues/4), created 2025-07-04, closed 2025-07-22. User reports problematic diagonal/rotated geometry; maintainer suggests parameter tuning and notes a foolproof solution for irregular shapes may be out of scope. No specific fix is identified in the current changelog.

### CartAGen / FER

- [FER API](https://cartagen.readthedocs.io/en/latest/reference/cartagen.regularize_building_fer.html): documented defaults `length=6.0 m`, `area=6.0 m²`; small polygons under area threshold can be filtered; assumes roughly rectilinear architecture.
- [CartAGen User Manual](https://cartagen.readthedocs.io/en/latest/manual.html): identifies aerial/satellite segmentation as the context for building regularization; states recursive regression can be destructive and always returns 45-degree angles, while FER is designed to keep overall shape better. Manual states EUPL 1.2. Search result and opened page disagree on documentation version label, so exact version is not frozen.

### IfcOpenShell representation lifecycle

- `add_footprint_representation.py` — SHA `9d5fe9f20bc4408559e2561a47ee32a3a101debb`; creates `GeometricCurveSet` representation.
- `add_profile_representation.py` — SHA `754b7ded031df2e488bb9c356dbb174351881484`; supports profile extrusion along +Z and arbitrary profiles with inner curves.
- `assign_representation.py` — SHA `a1e03ece8b7806fe6b6ae3f9c1ec3492a8af9539`; appends representation to product representations.
- `unassign_representation.py` — SHA `c631c8421aafb78e996258fb218001b3f0c8e535`; removes a representation from the product/type association.
- `remove_representation.py` — SHA `fa96768679e2b40c12ac99faca30e01aed89b997`; removes an unreferenced representation and associated geometry elements.
- `context/add_context.py` — SHA `c1afea62ab0895e29706dc1fcbb52456810127c0`; explains Model/Plan contexts and Body/Footprint/Axis identifiers.
- [Official geometry creation docs](https://docs.ifcopenshell.org/ifcopenshell-python/geometry_creation.html).
- Local environment: Python 3.13.5, Shapely 2.1.2, IfcOpenShell absent; `pip index versions ifcopenshell` failed due DNS/network resolution, so real IFC execution is blocked in this runtime.
