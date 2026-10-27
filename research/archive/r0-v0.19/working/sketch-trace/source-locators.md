# BATCH-002 Source Locators

## OpenCV

- Homography / perspective transform: https://docs.opencv.org/5.0/main_modules/d_projection.html ; https://docs.opencv.org/5.0/main_modules/geometry_shape.html
- Contours / approximation: https://docs.opencv.org/5.0/py_tutorials/py_imgproc/py_contours/py_contour_features/py_contour_features.html
- License repository file: https://github.com/opencv/opencv/blob/5.x/LICENSE ; fetched SHA `d645695673349e3947e8e5ae42332d0ac3164cd7`.

## GDAL

- Geotransform: https://gdal.org/en/stable/tutorials/geotransforms_tut.html
- Raster data model / GCPs: https://gdal.org/en/stable/user/raster_data_model.html
- Warp using GCPs: https://gdal.org/en/stable/programs/gdalwarp.html

## Meta SAM 3 / 3.1

- Project page: https://ai.meta.com/research/sam3/
- Repository: https://github.com/facebookresearch/sam3
- README fetched SHA: `9aad5341b0d517d6dde1ed5329aec5a4c61d7a0c`.
- LICENSE fetched SHA: `00030caa37d1d1714b2eb0d7f55c50c5805ed4ce`; custom `SAM License`, updated 2025-11-19.
- Edge-quality failure lead: https://github.com/facebookresearch/sam3/issues/501

## SamGeo

- Repository: https://github.com/opengeos/segment-geospatial
- README fetched SHA: `4c09c375a90dea6be4f3ae8ea111aedb7681dbad`.
- LICENSE fetched SHA: `0962b5fe1b6e89ed41b759996df4d4385d885354` (MIT).
- Wrapper license does not supersede license terms of SAM model/code/weights used as a backend.

## Potrace

- Official site: https://potrace.sourceforge.net/
- Library API: https://potrace.sourceforge.net/potracelib.pdf
- Algorithm paper: https://potrace.sourceforge.net/potrace.pdf
- Official materials state GPL licensing for Potrace library/code.

## Adjacent architectural raster→vector projects

- RedrawAI: https://github.com/Yassinevlg/autocad-redraw-ai ; README SHA `7a9347946c2b9cf3e0bacdbfb36a850b72e03f86`; standard root `LICENSE` fetch returned 404 in this run, so reuse permission unresolved.
- Raster2Seq: https://github.com/Cornell-VAILab/Raster2Seq ; README SHA `0d1978b076eaf56a056b262d5e6945e3116e7907`; code LICENSE SHA `d40e4426ec03d3201f1f83dea19d8f7adb98d8c2` (MIT); README states distributed checkpoints use CC BY-NC 4.0.
- floorplan-to-vector: https://github.com/YImingZHANG615/floorplan-to-vector ; README SHA `8de3c7508c1bd5e49ad9162d1479bb4718937b92`; LICENSE SHA `b96a204b1b98116c19ea3f6b51ad7a507fe59f9e` (MIT).

## Benchmark data-gap / controlled urban source leads

- `STASYA00/urban_datasets`: https://github.com/STASYA00/urban_datasets ; README SHA `1f6903d0fe78b461f3832fddc2ae60dcd2bb1c43`; LICENSE SHA `b00666f5f46dae275beef8a07469253732a63f6b` (MIT). It generates top-view/masterplan image datasets from GIS layers and can fetch roads/buildings from OSM; useful for controlled Tier-A geometry/raster pairs, not a real designer-sketch benchmark.
- FP4S Dataverse lead: https://doi.org/10.7910/DVN/MDIRHE ; public metadata describes real floor-plan images with scribble annotations, but it is floorplan-domain rather than site/masterplan and access is restricted/request-based in the surfaced record.
- Architectural plan dataset review lead: CMU thesis on plan-based datasets; useful for dataset landscape only, not a site-sketch paired benchmark.
- `real-benchmark-contract-v0.1.md` records the current three-tier strategy and explicitly treats the missing paired site-sketch dataset as an unresolved discovery gap.
