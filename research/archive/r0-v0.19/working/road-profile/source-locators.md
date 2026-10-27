# BATCH-001 Source Locators

Accessed: 2026-10-26. These are stable external locators and selected observations, not a claim that complete raw pages were archived. GitHub blob SHAs are upstream version locators returned by GitHub, not locally computed hashes.

## Open-source and code sources

### Street Generator
- Repository: https://github.com/urbanis/street-generator
- GitHub API metadata: https://api.github.com/repos/urbanis/street-generator
- Repository metadata observed: created `2026-03-08`; pushed `2026-07-06`; public; not archived; `license=null`; 0 stars/forks at query time. Do not treat the public repo as cleared for reuse until the license is clarified.
- Model file: https://github.com/urbanis/street-generator/blob/main/src/models/street.ts — blob SHA `e982f8d4f3f99df50bdac101e179c4fecb5a38ba`.
- Rule dispatcher: https://github.com/urbanis/street-generator/blob/main/src/rules/engine.ts — blob SHA `694e97e7f12d8e0eb07069c093039de215497b68`.
- RASt rule implementation: https://github.com/urbanis/street-generator/blob/main/src/rules/de_rast_v01_rules.ts — blob SHA `74817c700e806e8970d371bb02e53e2050b7f156`.
- Rule tests: https://github.com/urbanis/street-generator/blob/main/src/rules/de_rast_v01_rules.test.ts — blob SHA `9b782412f9a46a558142a7961aca1546a7669325`.
- Evidence boundary: source was inspected through GitHub file retrieval; no local build, unit-test execution or independent reproduction was performed.

### Streetmix
- Repository: https://github.com/streetmix/streetmix
- README: https://github.com/streetmix/streetmix/blob/main/README.md — blob SHA `6eed472e74b32e87c8a0b826a5dc6fe2756dee21`.
- LICENSE: https://github.com/streetmix/streetmix/blob/main/LICENSE — blob SHA `0960e51e1546ba2944054b70171b0bf62092b8ed`.
- Current LICENSE states the current codebase and future modifications are AGPL-3.0-or-later. Repository metadata was updated 2026-10-24, reports 749 stars/218 forks and labels license `Other/NOASSERTION` because the file is composite. Treat software-code licensing and content/assets licensing as separate questions.
- README frames the product around conceptual street-section design, collaboration and public engagement. It does not establish engineering-grade plan-view alignment or regulatory compliance.

### OpenStreetMap
- Key:highway: https://wiki.openstreetmap.org/wiki/Key:highway
- Relevant statement: the tag indicates road role/importance in the network; it does not necessarily equal legal national classification or physical characteristics.

### SUMO
- Road network model: https://sumo.dlr.de/docs/Networks/SUMO_Road_Networks.html
- Edge type file: https://sumo.dlr.de/docs/SUMO_edge_type_file.html
- OSM import notes: https://sumo.dlr.de/userdoc/Networks/Import/OpenStreetMap.html
- Relevant model: directed graph; edges, lanes, junctions and lane connections; edge types supply default values for selected properties. This is a traffic-simulation schema, not a road design standard.
- OSM import page says typemaps infer missing values; context matters; values in the supplied maps are ad-hoc/not verified; and junction-cluster joining is heuristic and can wrongly merge some complex junctions: https://sumo.dlr.de/userdoc/Networks/Import/OpenStreetMap.html (lines 106-117, 230-235, 318-323).

## Chinese standards: authority leads

- GB 55011-2021 announcement (MOHURD): https://www.mohurd.gov.cn/gongkai/zc/wjk/art/2021/art_17339_761190.html
  - The announcement states implementation from 2022-01-01, mandatory application of all provisions, and that conflicting provisions in existing engineering standards defer to this code as described there.
  - Attempt to open the full-text attachment failed with `Cache miss` in this run; no clause text was extracted.
- GB 55037-2022 announcement (MOHURD): https://www.mohurd.gov.cn/gongkai/zc/wjk/art/2023/art_17339_770016.html
  - Search result states implementation from 2023-06-01 and mandatory status. Direct page open timed out in this run; clause-level scope not verified.
- GB 55019-2021 announcement (MOHURD): https://www.mohurd.gov.cn/gongkai/zc/wjk/art/2021/art_17339_762461.html
  - Search result states implementation from 2022-04-01 and mandatory status. Direct page open timed out in this run; clause-level scope not verified.
- CJJ 37-2012 / 2016 edition announcement lead: https://www.mohurd.gov.cn/gongkai/zc/wjk/art/2012/art_17339_208843.html
  - Current status/revision metadata still lacks an authoritative status-page confirmation in this batch. A secondary reproduction of the GB 55011-2021 preface/annex lists CJJ 37-2012 (2016 edition) clauses 3.4.2, 3.4.3 and 13.3.4 among the repealed mandatory provisions, and says mandatory clauses in the listed existing standards are governed by GB 55011. This is evidence against treating the entire CJJ 37 document as repealed, but the original MOHURD attachment must be retrieved/checked before using the annex as authoritative. Secondary reproduction: https://gf.cabr-fire.com/article-43015.htm (lines 49, 57-63); another hosted full-text copy: https://www.zlglpt.com/book/book_view.aspx?id=3793 (lines 125-127).
- GB 50180-2018 is a relevant candidate source for residential-area planning, but this batch did not confirm its current status from an authoritative status page.

## Failed or incomplete retrievals

- GB 55011 full-text attachment and its companion mandatory-clause document: cache miss.
- GB 55037 and GB 55019 direct announcement pages: timeout in this session; their search-result snippets were retained as leads only.
- Search-engine total hit counts and pagination completeness were unavailable; related search RUNs remain `truncation=unknown` and cannot pass A1.


## Second-wave source additions (2026-10-26)

- Streetmix current repo metadata: https://api.github.com/repos/streetmix/streetmix; pushed `2026-10-24T07:38:41Z`, `license=Other/NOASSERTION`; README blob `6eed472e74b32e87c8a0b826a5dc6fe2756dee21`; LICENSE blob `0960e51e1546ba2944054b70171b0bf62092b8ed`.
- SUMO OSM import documentation was opened directly: https://sumo.dlr.de/userdoc/Networks/Import/OpenStreetMap.html. It explicitly states that typemaps infer missing values, type maps are context-specific, the included map values are ad-hoc/not verified, and junction-joining heuristics can wrongly join some junctions.
- Search for authoritative current status of CJJ 37 and GB 50180 did not locate an authoritative status page. Local project specifications that cite these standards remain leads only.

## Third-wave issue and license-route additions (RUN-001-09)

### SUMO project issue reports

- Issue #7615, `inconsistent OSM typemap`: https://github.com/eclipse-sumo/sumo/issues/7615
  - Opened 2020-09-29; closed 2020-09-30; updated 2025-09-09. Report states `highway=path` permits pedestrians/bicycles but defaults to one-way in the reported mapping, creating an unrealistic bicycle-network constraint. Treat as a historical project issue report, not proof of a current defect or independent reproduction.
- Issue #7119, `reconsider default permissions on roads for pedestrians`: https://github.com/eclipse-sumo/sumo/issues/7119
  - Opened 2020-06-05; closed 2020-06-07; updated 2025-09-09. Report discusses how default pedestrian permissions and separately mapped sidewalks can require different typemaps. Use as a negative test pattern for access semantics and hidden defaults, not as a current engineering rule.
- Issue #15013, `netedit writes undone join operation to junctions.join-output file`: https://github.com/eclipse-sumo/sumo/issues/15013
  - Opened 2024-06-11; still open at access; updated 2026-10-09. Report states join output may include intermediate operations later undone in NetEdit. This is relevant to provenance/audit-log semantics; it does not prove final network geometry is wrong.

These issue reports provide a project-maintained issue route, not an independent external replication route. GitHub issue searches were limited to topn=8 per query and did not expose total counts; `truncation=unknown` remains.

### Street Generator license route

- Root contents API: https://api.github.com/repos/urbanis/street-generator/contents
- Exact `LICENSE` path: https://api.github.com/repos/urbanis/street-generator/contents/LICENSE — 404 at access time.
- Exact `COPYING` path: https://api.github.com/repos/urbanis/street-generator/contents/COPYING — 404 at access time.
- The returned root listing contained no filename matching license/copying/copyright; the retrieved README had no license statement in its text. Repository metadata still reported `license=null`.

Interpretation: no declared license was found in the standard root locations inspected. This does **not** establish that the author has no separate licensing terms; it does mean reuse permission remains unresolved. Do not copy/integrate until permission is clarified.
