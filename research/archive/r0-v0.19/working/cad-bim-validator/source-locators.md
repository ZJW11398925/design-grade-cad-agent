# BATCH-004 来源定位

## ezdxf

- Repository: https://github.com/mozman/ezdxf
- README: SHA `bddd26af7d9224d3bbb2b3cb7fe03089e7298055` — https://github.com/mozman/ezdxf/blob/master/README.md
- LICENSE: SHA `33a77673a9100f1f8553745ac6c924a6b8e58410` — https://github.com/mozman/ezdxf/blob/master/LICENSE
- README facts: MIT; Python package for DXF create/read/modify/write; read/write/new support for R12, R2000, R2004, R2007, R2010, R2013, R2018; CLI includes `audit`, `info`, `browse`, `draw`; optional ODA converter interface is separate.
- Official docs:
  - Layers: https://ezdxf.readthedocs.io/en/stable/concepts/layers.html
  - Lineweights: https://ezdxf.readthedocs.io/en/stable/concepts/lineweights.html
  - Common graphical attributes: https://ezdxf.readthedocs.io/en/stable/tutorials/common_graphical_attributes.html
  - Drawing audit/validate: https://ezdxf.readthedocs.io/en/stable/drawing/drawing.html
- Version caveat: local benchmark used ezdxf 1.4.4; current stable web docs showed 1.4.5. Do not merge local behavior and online docs into a single version claim.

## LibreCAD

- Repository: https://github.com/LibreCAD/LibreCAD
- README: SHA `93594a3b7aa29e09a587ab4691ba023795dfd64c` — https://github.com/LibreCAD/LibreCAD/blob/master/README.md
- LICENSE: SHA `e3cb9f298dbcf63ee7174e5cd74a08e755f6cf42` — https://github.com/LibreCAD/LibreCAD/blob/master/LICENSE
- README facts: open-source 2D CAD; GPLv2; CLI converters for DXF→PDF/PNG/SVG and DXF/DWG conversions, with DWG support conditional on a `DWGSUPPORT` build; Windows invocation has process wait/exit-code caveats.
- Official CLI docs: https://docs.librecad.org/en/latest/guides/cmdline.html
- Local environment: `librecad`/`LibreCAD` executable not installed; independent open/save/render test not run.

## libdxfrw

- Repository: https://github.com/LibreCAD/libdxfrw
- README: SHA `608ddc705be5d043e3a59ddb0f942c51fe505138` — https://github.com/LibreCAD/libdxfrw/blob/master/README.md
- README facts: C++17 DXF/DWG reader/writer, GPL-2.0-or-later; DWG read/write support is labelled experimental; it explicitly says local/self-roundtrip is not an independent semantic oracle and some 3D/raw-carrier paths remain experimental.
- Use: possible lower-level conversion/reference component, not a general DWG correctness guarantee.

## IfcOpenShell / IfcTester

- IfcOpenShell README: SHA `e21f8f9a3d871608af3a64361bd3eebc52bddb88` — https://github.com/IfcOpenShell/IfcOpenShell/blob/v0.9.0/README.md
- README states open-source LGPL library, with parsing support for IFC2x3 TC1, IFC4 Add2 TC1, IFC4x1, IFC4x2 and IFC4x3 Add2; the repository includes IFC conversion, Bonsai and IDS tools with component-specific licenses.
- IfcTester official docs: https://docs.ifcopenshell.org/ifctester.html
- IfcTester supports authoring/reading IDS, validating IFC against IDS, and report generation (console/HTML/JSON/SQLite/ODS/BCF). This is information-delivery validation, not a substitute for custom geometry/topology/placement validation.
- Local environment: `ifcopenshell` not installed; pip index lookup failed due DNS/network resolution in this runtime. No IFC execution claim.

## Local run artifacts

- Profile fixture: `working/cad-bim-validator/cad-profile-test-v0.1.yaml`
- Script: `working/cad-bim-validator/scripts/local_benchmark_003_dxf_roundtrip.py`
- Result: `working/cad-bim-validator/local-benchmark-003-dxf.json`
- Human report: `working/cad-bim-validator/local-benchmark-003-dxf.md`
- Sample DXF: `working/cad-bim-validator/samples/sample-design-office-profile-test.dxf`

All local Profile values are synthetic fixture values and must not be cited as actual design-institute requirements.


## Source-backed planning CAD standard exemplar (not the user's selected standard)

- Standard: **DB11/T 1948—2021《国土空间详细规划计算机辅助制图标准》**.
- Official full text PDF: https://ghzrzyw.beijing.gov.cn/biaozhunguanli/bz/cxgh/202207/P020220711347172743065.pdf
- Official current-status page: https://std.samr.gov.cn/db/search/stdDBDetailed?id=D7B84EB1F2C445E9E05397BE0A0AD18E
- Official release notice: https://scjgj.beijing.gov.cn/zwxx/gs/dfbzgg/202112/t20211231_2579609.html
- Official scope/status: Beijing detailed spatial planning CAD drafting/management; status listed as current; effective 2022-07-01; supersedes DB11/T 997-2013. This is a Beijing local standard, not a national universal profile.
- Official full text was read via the Beijing Municipal Commission of Planning and Natural Resources PDF. Relevant clauses: 1.0.2 (scope), 2.1.5 (true color), 2.2.1 (coordinate reference), 2.2.3 (units/precision), 2.4.1 (topology), 2.4.2 (line/area geometry), 3.1.3 (CAD layer naming), Appendix D Table D.2 (road centerline/redline layers), Appendix B Table B.1 (land-use layers).
- Official page lists a symbol library and three general font libraries, but the direct resource click returned an internal error in this run; actual downloads, contents and licenses remain unchecked.
- Extracted subset: `db11t1948-profile-extract-v0.1.yaml`; source map: `standards-profile-source-map-v0.1.md`; local probe: `local-benchmark-004-db11t1948.*`.
