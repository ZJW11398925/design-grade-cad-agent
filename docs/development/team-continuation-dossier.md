# Team Continuation Dossier — DGCAD (2026-10-28)

Status: **development note, not a living contract.** It complements — and in three
places corrects — `docs/development/session-handoff.md`, which should be read first
for the narrative context. Every claim below was reproduced in this session by the
Lead or by at least one peer team member from committed artifacts, code, tests or
commands; each section names its evidence. Nothing in the repository was modified
while producing this dossier (working tree clean; `_incoming/` untouched).

Team: Lead + 5 peer specialists (`arch-core`, `design-topology`, `cad-pipeline`,
`docs-audit`, `red-team`), two model families (deepseek-flash / glm-5.3-flash),
cross-review in one round plus an adversarial audit of this dossier. Raw peer
deliverables are session artifacts under `scratch/team/<member>/` (gitignored);
this dossier is the durable summary.

---

## 0. 中文摘要（给项目负责人）

**基线（已实测）**：分支 `milestone-4c-autonomous-design` @ `83d71eb`，
v0.15.0（无 git tag），工作区干净；`python -m pytest -q` = **217 passed**（约 20–22 s）；
PR **#34 OPEN，4/4 CI 绿**（3.11/3.13 × Ubuntu/Windows）；核心依赖仍只有
PyYAML / Shapely / ezdxf。

**最重要的更正 —— 4c「道路拓扑缺陷」不是设计断连，而是浮点 noding 缺陷。**
41 条设计道路（25 主 + 15 支 + 1 环路）在**精确算术**下 noded 图是 51 节点 / 51 边 /
5 分量；但 4 个游离分量的连接端点距离主路网仅 **1.5e-15 ~ 2.1e-14 m**
（`shapely.ops.nearest_points()` 的投影不是精确落线点，GEOS 精确谓词因此不 noding）。
只要声明 1e-9 m 的容差，图就是 **1 个连通分量**。走廊union 检查之所以 pass，是因为
12 m / 7 m 缓冲在 **8.978 m** 中心线间隙下仍会合并——它测的是铺装覆盖，不是拓扑。
文档中「主路彼此不连通」的因果叙述是**错的**：25 条主路全部在同一个精确分量里。
因此**不要**按 handoff §4 用 OSMnx 重建设计路网（OSMnx 数字可精确复现 117/141 与
1 分量，但它是源骨架预处理器，靠 8 m 容差制造连通，且 −10.7% 长度、只保留
141/333 源边 id，用它做「连通性证明」属于口径错误）。

**修复方案（已原型验证，M4c-1a）**：显式共享坐标 junction + 不依赖容差的
`topology.py` noded 检查。原型结果：41/41 道路保留、**1 分量**、**0.0 m Hausdorff 位移**、
道路面积变化 +2.9e-11 m²、**208 实体不变**、12 项一致性检查状态全部不变。
拓扑修复单独提交，设计层改造（支路接到入口、G-05/G-12 覆盖）另做 M4c-1b。

**本次审计还发现的高价值问题**（详见 §5 风险登记册）：
1. **权威绕过（HIGH）**：Agent 会话可自报 `required_authority="deterministic_auto"`，
   在无审批、无规则注册表的情况下修改 `human_confirmed` 对象（两名成员独立复现）。
   这是与「Agent 永不写入 confirmed 真值」核心不变量的直接冲突，应在任何自主提交功能前修。
2. **契约大多只是散文**：22 个契约 YAML 只有 3 个被测试直接解析；已出现漂移
   （`e2e-pipeline` 仍称 DEV-CAD xfail；`runtime-agent-surface` 多了一个不存在的
   `object_view` 工具）。
3. **单写者未强制**：`StatefulRuntime` 没接 lease，只有「过期写入检测」；
   overview 的「single-writer per project」表述过强。
4. **FAR/停车/户数是 basis 闭式算术**（109×2×11、ceil(2398/500)），不是空间设计结果；
   「满足 FAR/停车」不能当成几何验证。
5. **4c 只有 focus G-01 落图**（7/55 建筑、10/41 道路），发布 DXF 里看不到 41 条路的拓扑。
6. **第三方 CAD 证据从未跑过 208 实体 DXF**（只跑过 15 实体的合成文件）；
   handoff 的 review-packet 哈希只做格式检查、未与文件比对。
7. **文档 stale 清单 12+ 条**（status 头部 206、CONTRIBUTING「65 passed」、
   research-to-product-map 的 210 entities/22 layers、handoff「28 files」、
   中文简介 154 等），M4c-1a 应一并修正；PR #34 合并前尤其要改掉 defect 叙述。
8. **DXF 字节可复现（handoff §8 的说法是错的）**：设置
   `ezdxf.options.write_fixed_meta_data_for_testing = True` 后两次保存字节一致；
   但启用它会改变所有已提交 DXF 哈希（含第三方 round-trip 记录的 input sha256），
   必须作为一次独立的 evidence-migration + 真实 host 复跑，不要塞进 M4c-1a。

**建议的下一步顺序**：先做 **M4c-1a**（拓扑真相 + 精确 junction 修复 + 文档更正，
小、可证、指标中性）→ 再决定是否合并 PR #34 → **M4c-1b**（设计感知的支路/入口覆盖）
→ 全站点展开与 20 m 间距 → 设计评估/搜索 → 设计院户型号库。
**决策点**：PR #34 现在合并还是修完拓扑再合并（建议修完再合并）；权威绕过问题单独排期。

---

## 1. Verified baseline (2026-10-28)

| Item | Value | Evidence |
|---|---|---|
| Repository | `D:\agent-cad`, branch `milestone-4c-autonomous-design`, HEAD `83d71eb`, clean tree | `git status --short`; Lead + peers |
| Version | `0.15.0`; **no git tag exists** | `pyproject.toml:7`, `CHANGELOG.md:5`, `git tag --list` |
| Tests | **217 passed / 217 collected**, ~20.1–21.6 s | Lead and three peers independently |
| PR | **#34 OPEN**, 4/4 CI checks SUCCESS (py3.11/3.13 × ubuntu/windows, 2026-10-28T03:42–43Z) | `gh pr view 34` (docs-audit) |
| Python | 3.13.2 local; CI covers 3.11 + 3.13 | `ci.yml:18-20` |
| Core deps | PyYAML 6.0.3 / shapely 2.1.2 / ezdxf 1.4.5 — satisfy `pyproject.toml:26` | measured |
| Optional research deps | osmnx 2.1.1, buildingregulariser, pygeoops, pyclothoids, momepy, networkx 3.6.1, geopandas — installed locally, **not** core | `experiments/m4c0/requirements-reuse.txt` |
| Test hygiene | 0 skip / 0 xfail markers in `tests/` | docs-audit grep |
| CI scope | `pytest -q` + `compileall src`; coverage summary only on ubuntu/py3.13 | `ci.yml` |

Suite composition (217, per-file): foundation 21, runtime 22, deployment 8,
lifecycle 14, domain 26, analysis 7, CAD delivery 9, E2E-001 8, E2E-002 6,
E2E-003 20, E2E-003b 11, E2E-003c 2, sketch evidence 11, road topology 3,
sketch handoff 32, handoff-A 6, design synthesis 8, reuse 3.

**Pin discipline.** All figures above were measured at HEAD `83d71eb` with this
dossier and the `session-handoff.md` pointer **uncommitted** (work tree therefore
no longer "clean" until they are committed or removed). If this work is committed,
one follow-up must repin every `83d71eb` reference in this dossier and in
`session-handoff.md` §1, and re-run `pytest -q` to confirm 217. Suggested commit:
`docs: add verified team continuation dossier and correct handoff pointers`.

---

## 2. What the project actually is (verified)

**Purpose.** A research-first workspace that turns a hand-drawn site sketch into a
traceable, semantically resolved site model and derived CAD output. The hard part
is not drawing: it is truth ownership, identity, authority, dependency and
verification (`README.md:11-24`).

**Two planes** (`README.md:25-57`):

- Data: source evidence → trace → intent → professional candidate → canonical
  site model → derived 3D/analysis → DXF/IFC (derived, invalidatable).
- Control: agent proposal → authority check → deterministic execution → rule
  resolution → validator → human confirmation → canonical commit → stale
  propagation.

**What is really implemented** (arch-core, 44-row fact table):

- Foundation: authority enforcement, 3 revision axes, three-world model, CAS,
  locks, atomic change sets, transitive stale propagation, append-semantics audit,
  migration registry (library only), canonical hashing (`src/dgcad_foundation/*`).
- Runtime: proposals/approval grants/jobs/idempotency/restart recovery,
  stale-writer fail-closed, agent tool surface of **8 tools with no approve or
  unlock** (`src/dgcad_runtime/*`; `tests/test_runtime_contracts.py:108-118`).
- Deployment: SQLite/WAL tested but **not wired** into the runtime (JSON envelope
  is the live store), loopback HTTP, in-memory sessions/pairings, MCP adapter is a
  shim with **zero wire execution**, Windows ACL protection absent
  (`chmod 0600` → `0o666` on this host) (`src/dgcad_deployment/*`).
- Domain/CAD: confirmed-trace adapters, CAD-IR, DXF compiler, readback validator,
  privacy scan, handoff gate with scope/authority/provenance propagation.
- Design: autonomous draft generator (`src/dgcad_design/*`) for CASE-SKETCH-001 —
  schematic only, rule_derived, proposal_preview.
- Analysis: synthetic solar/shadow baseline, not an independent engine.

**Documentary-only parts**: the 11 modules M01–M11 exist only in
`docs/architecture/overview.md:61-75` and `docs/research-to-product-map.md:31`
(zero grep hits in `*.py`). M08 rule/profile engine has **no code** — only
`fixtures/design/design-basis-001.yaml` arithmetic. `contracts/` holds 22 YAML
files but only **3 are parsed by tests** (sketch-evidence v0.1,
deployment-boundary v0.1, e2e-adversarial v0.1), so most contracts cannot fail CI.

**Authority**: matrix, locks, preview isolation and "Agent has no approve/unlock"
are real and test-backed. But see risk R1 (agent-declared `deterministic_auto`
bypass) — the unqualified claim "the Agent can never write confirmed state" is
**not** true today.

---

## 3. The 4c road-topology defect: corrected diagnosis

This is the highest-priority technical fact for continuation and the single most
important correction to the existing docs. Three independent reproductions agree
(Lead; design-topology; red-team's re-verification).

### 3.1 What was claimed

`docs/e2e/design-synthesis-001/README.md:13-31`, `docs/status.md:360,371`,
`docs/roadmap.md:240-242`, `session-handoff.md:92-105` (line numbers after the
2026-10-28 banner edit): the design corridor union
is one polygon, but the noded centerline graph of the same 41 design roads has
5 components (51 nodes / 50 edges, cyclomatic 0); therefore the design is "not
topologically connected", the corridor check is too weak, and the candidate is
partial. Handoff §4 orders: rebuild on the OSMnx-consolidated network.

### 3.2 What is actually true

- Design roads: **41 = 25 main + 15 branch + 1 access loop**, zero
  `MAIN-CONNECTOR` (the 25 main lines are already mutually exact, total length
  1970.998998 m = source main-edge total). `build_road_layout`
  (`src/dgcad_design/roads.py:186-389`).
- Exact-coordinate graph (multigraph, no rounding): **51 nodes / 51 edges /
  5 components**, cyclomatic `E−V+C = 5`, degree histogram `{1:25, 2:3, 3:21, 4:2}`,
  25 dead ends, 23 nodes of degree ≥3.
- Components: C0 = 36 roads (all 25 `MAIN-*` + 11 branches), C1 = `BR-FOCUS` +
  `ACC-FOCUS-01`, C2 = `BR-G-02`, C3 = `BR-G-04`, C4 = `BR-G-08`.
- The four detached components are **sub-ULP floating-point artefacts**: their
  attachment endpoints are 1.54e-15, 2.06e-14, 9.29e-15 and 1.32e-14 m from the
  main network, with exact `intersects == False`. Cause: connector endpoints are
  taken directly from `shapely.ops.nearest_points()` output
  (`roads.py:241-244,284-287`), which is a projected point, not a guaranteed
  exact-on-line coordinate; GEOS noding uses exact predicates, so a 1e-15 m
  residual creates no node. The 11 other branches node correctly, but by three
  different accidents: 5 land on exact main vertices; 3 are exactly collinear;
  and 3 (`BR-G-06/10/17`) are attached only because the branch segment **crosses**
  the main line near its endpoint and GEOS nodes at that crossing (line-level
  intersection, no shared vertex). The attached/detached split is reproduced by
  line-level `intersects`, not by point-on-line `intersects` (the latter is False
  even for those three). That float accident is exactly why M4c-1a must require
  explicit shared-vertex junctions: a T-junction that works only because of a
  crossing is not a declared junction.
- red-team re-derived every number in this section with its own scripts and an
  independently written repair prototype: 41-road split, 1970.998998 m main total,
  51/51/5, component composition, the four gaps, the 50-edge and cyclomatic
  explanations, the 1e-9 tolerance experiment, OSMnx numbers, and the repair
  result (1 component, 51 nodes / 55 edges, cyclic 5, displacement 5.7e-14 m).
- **Under a declared 1e-9 m precision model the graph collapses to 1 component**
  (`shapely.union_all(centrelines, grid_size=1e-9)` → 55 noded pieces, 1
  component). This is a **diagnostic experiment, not a fix**: endpoint-key
  rounding does not close a mid-segment attachment, and a per-geometry
  `set_precision(1e-9)` still leaves 4 components (red-team check). It shows the
  four gaps are grid-scale artefacts and that no design-intent disconnection
  exists beyond ~1e-14 m; it does not justify "connected for any engineering
  purpose", and M4c-1a must not use grid snapping as a repair (§4.4).
- exp-c's `51/50/5` is consistent but explained: `nx.Graph.add_edge` collapses
  the access loop's two parallel arcs (50 vs 51 editable), and the reported
  `cyclomatic: 0` is `momepy.cyclomatic`'s `e−v+1` connected-graph formula
  returning 0 on a disconnected graph — true cycle rank is 5 (multigraph) / 4
  (simple graph). Do not quote "cyclomatic 0 / meshedness 0" as evidence.
- The corridor-union check passes because buffers merge. Measured sweep: moving
  `BR-G-02` away from the main line, `ROAD_CONNECTIVITY` still "passes" at an
  **8.978 m** centerline gap and fails only at 9.976 m (≈ 6 m + 3.5 m half-widths
  with round caps). It measures paved coverage, not topology.
- The documented causal claim is wrong: **all 25 main roads are in one exact
  component**; `_main_connectors` emitted zero connectors.
  `_main_connectors` is nonetheless a latent defect of the same class: it treats
  a gap < 0.5 m as connected and appends no connector (`roads.py:173-183`).

### 3.3 Independent design-coverage findings (orthogonal to the float defect)

- Only the focus-group roads are drawn: CAD-IR/DXF contain **10 of 41**
  centerlines (`src/dgcad_design/drawing.py:241-245` filters to the plan box).
- 15 of 17 groups receive a branch; **G-05 (3 buildings / 7 units) and G-12
  (2 buildings / 4 units) are skipped entirely** because their bbox intersects
  the focus box (`roads.py:279-280`).
- **Entrance reach is weak**: there are 5 design parking entrances (3 designer
  polygon markers + 2 proposed point markers). The 2 proposed ones coincide
  (≤1e-9 m) with branch main-side endpoints only as a `nearest_points` side
  effect, not by design; the 3 existing markers sit 8.0–30.2 m from the nearest
  branch endpoint (centroids 12.8–25.7 m from any centerline). No branch is
  designed to terminate at an entrance. (An earlier version of this dossier said
  "0 of 17 entrances"; red-team's review showed 17 is the group count, not the
  entrance count — corrected here. This is exactly the class of error the peer
  review exists to catch.)
- These are design-quality gaps for **M4c-1b**, separate from the topology-truth
  fix (M4c-1a).

### 3.4 OSMnx branch: reproducible, but not a connectivity proof

- Reproduced exactly from committed source: 309/333 → simplify 257/281 →
  consolidate 8 m **117/141, 1 weak component**, total length 6090.17 m vs
  6821.84 m (**−10.72%**); tolerance sweep matches committed values.
- It is a **source-skeleton preprocessor** with tolerance-based node merging:
  edge keys reset, only 141 of 333 source ids survive, geometry changes; it can
  create junctions that do not exist, and exp-c already showed design widths on
  it leave **no 120×90 m buildable focus rectangle**.
- Correct use: optional, lazily imported adapter (`import osmnx` inside the
  function, provenance record, `ImportError` hint), never a core dependency and
  never the proof that the *design* network is connected.

---

## 4. M4c-1 work order (recommended, staged)

### 4.1 M4c-1a — topology truth + exact junctions (metric-neutral, do first)

Goal: make the design road graph exactly noded with explicit junctions, replace
the corridor-only connectivity check with a real noded-topology check, publish a
verifiable 41-road artifact, regenerate evidence once, and correct the narrative
docs. No design intent change; no new dependency; no tolerance in the check.

| # | Change | File(s) |
|---|---|---|
| 1 | New dependency-free noded-topology module: `noded_road_topology(roads)` → segment/node/edge/component counts, cyclomatic `E−V+C`, degree histogram, dead ends, real junctions, `max_endpoint_gap_m` (endpoint-on-line **exact** predicate — pin it), **design-level** closed-ring inventory (design data has 3 rings: `MAIN-10` 14.52 m, `MAIN-12` 99.30 m and the access loop; only `MAIN-12` survives noding as a closed piece), crossing-without-shared-vertex violations, per-component `road_ids`; fail-closed violation codes | **new** `src/dgcad_design/topology.py` |
| 2 | Junction model: every junction is an **explicit shared coordinate** (insert the projection as a vertex of both lineworks and reuse the same float tuple); delete the `nearest_points`-as-junction pattern; delete or redesign `_main_connectors` (never assume "<0.5 m = connected"); **treat a crossing that nodes only by float accident as a defect**; classify dead ends (planned cul-de-sac) | `src/dgcad_design/roads.py` |
| 3 | `ROAD_CONNECTIVITY` keeps its id but `value` = **noded** component count; add non-gating `ROAD_CORRIDOR_COVERAGE` publishing `corridor_union_pieces`; rename `RoadLayout.component_count` → `corridor_union_pieces` and add `noded_topology`; fix `junction_count` (real degree≥3) and `dead_end_count`; add coverage metrics (`road_access_coverage`) | `src/dgcad_design/consistency.py`, `roads.py` |
| 4 | Contract: add `road_design.topology` block (states / required / connector rules / "no snap-round-buffer may create connectivity" / "corridor coverage ≠ connectivity" / "topology is not road design"); bump schema to `dgcad.design-synthesis.v0.2` because published metric keys change meaning; sync `evidence-gate-register-v0.2.yaml:34-35` and `status.md:91-92` references | `contracts/design-synthesis-v0.1.yaml` → `-v0.2.yaml` |
| 5 | Publish the design road network as committed evidence so the defect is checkable from the repo: 41 rows with `edge_id, class, width_m, centerline, source_edge_ids, junction_ids` (e.g. `design-roads.geojson`), written by the runner | `src/dgcad_design/project.py:396-478`, `scripts/design/run_design_synthesis_001.py`, `docs/e2e/design-synthesis-001/` |
| 6 | Tests: update `tests/test_design_synthesis.py:139` (`road_noded_component_count == 1` **and** `corridor_union_pieces == 1`), `:149`, `:228`; add a **contract completeness test** (new contract must be parsed by a test, mirroring `tests/test_road_topology.py:108-142`); add negative tests (a split branch fails; a 1e-12 m gap fails; a snap/round/tolerance "fix" is rejected; a crossing that nodes without a shared vertex fails; the closed-ring inventory matches the design-level rings); add an evidence test that recomputes the graph from `design-roads.geojson`; add a test that `import dgcad_design` succeeds with osmnx unavailable | `tests/test_design_synthesis.py`, new test file |
| 6a | **Pre-step (before regenerating evidence): harden the privacy scan** — exclude 64-hex hash fields from numeric-token matching while keeping digit detection on TEXT/layer/block/style names; add a deterministic regression test. Otherwise the M4c-1a acceptance gate ("privacy pass") can flake ~6.3% per run against its own regeneration (R8) | `src/dgcad_e2e/privacy.py`, new test |
| 7 | Regenerate `docs/e2e/design-synthesis-001/` **in one run** (all hash-bearing files: DXF, preview PNG, cad-ir, validation, readback-manifest, draft-manifest, scene-snapshot, summary/consistency/diff); commit regenerated bytes; do **not** enable fixed-metadata in this change | runner output |
| 8 | Correct docs: design-synthesis README defect section (reproduced numbers, real cause), `status.md` §16–18, `roadmap.md` M4c/M4c-0 "next", `research-to-product-map.md:207`, `README.md` §3 row + 中文简介, `reuse-matrix.yaml:186-191`, `CHANGELOG.md` new entry describing the correction, `session-handoff.md` §3/§4 (or a pointer to this dossier). Ownership in the docs pass: docs-audit owns wording/test-count ripple/README §7/README:11; cad-pipeline owns CAD-number facts; design-topology owns the defect narrative text | docs |
| 9 | Annotate (do not rewrite) the R1 M4c-0 evidence: exp-c metrics are historical; add a note that `50 edges` = simple-graph collapse and `cyclomatic 0` = momepy artefact | `docs/e2e/open-source-reuse-001/README.md`, `exp-c/metrics.json` note |

**Acceptance (hard, fail-closed):**

- noded centerline graph = **1 component**; `max_endpoint_gap_m == 0.0` (no snap,
  no rounding, no tolerance may create connectivity);
- all previous metrics unchanged within tolerance: FAR 1.56541, households 2,398,
  parking 2,398, entrances 5, focus 7/16/352 @ 20.0 m, green 0.63039;
- DXF entity count = **recomputed expectation for the drawing set** (208 for a
  topology-only repair with the current drawing set; any added junction marker
  changes it), audit 0/0, readback full, XDATA arity **11**,
  privacy pass (watch the numeric-token false-positive trap: scan structured
  TEXT/MTEXT/XDATA/symbol names, not raw numbers);
- all design objects stay `rule_derived` / `proposal_preview` / `design_draft`;
  no `human_confirmed`, no compliance claim;
- `python -m pytest -q` green including new negative tests; contract + tests +
  CHANGELOG change together (repo rule).

**Prototype evidence (design-topology, scratch only; independently re-derived by
red-team with its own chained-vertex-insertion script):** 1 component, 51 nodes /
55 edges, cyclomatic 5, dead ends 21, deg≥3 nodes 27, explicit junctions 16,
max Hausdorff displacement **0.0 m** (red-team run: 5.7e-14 m), road area
+2.9e-11 m², sidewalk −7.3e-12 m²,
all 12 consistency checks keep their R1 status, drawing still 203 elements →
208 DXF entities.

### 4.2 M4c-1b — design-aware coverage (needs design judgement)

- Branch terminations move from group bbox boundary to a declared access
  point/entrance; G-05 and G-12 must get access or their omission must be
  recorded with a reason in `design-diff.json`.
- Publish `road_access_coverage` (groups with branch / all groups; entrances
  reached) as a non-gating design metric until a basis threshold exists.
- This will change road area / clearance / possibly rows, so it needs a
  second evidence regeneration and design sign-off (it is not a pure fix).

### 4.3 After that (unchanged from roadmap, re-sequenced)

1. Expand the standardized layout from focus G-01 to all groups; enforce full-site
   20 m north-south spacing (`FULL_SITE_NS_SPACING`).
2. Design evaluation/search: intent preservation, completeness, internal
   consistency, verified constraint satisfaction, CAD editability; compare
   candidates instead of scoring one.
3. Replace the provisional 24×11 m staircase module with the designer's
   unit-type library; resolve the six length-vs-area conflicts and the
   kindergarten classification (human input).
4. Road width/profile/alignment and 支路/入户路 separation (needs standard text).
5. Agent ↔ real CAD host loop (LibreCAD/FreeCAD/AutoCAD GUI remain open, #6).

### 4.4 Explicit non-goals for M4c-1a

- Do **not** rebuild the design hierarchy on the OSMnx-consolidated network.
- Do **not** add core dependencies or make osmnx importable from core modules.
- Do **not** enable DXF fixed-metadata (byte reproducibility) in the same change;
  that is a separate evidence migration (§5 R9).
- Do **not** "make the check pass" by rounding node keys, buffering,
  `set_precision`, grid snapping or editing test expectations. Red-team verified
  that endpoint-key rounding to 9–15 dp still leaves 5 components and
  per-geometry `set_precision(1e-9)` leaves 4 / 56 pieces — only explicit shared
  vertices produce stable connectivity. The check must be able to fail.
- Do **not** claim human confirmation, code compliance, adoption or official
  issue; do not publish private DWG/redline coordinates.

---

## 5. Risk register (cross-cutting findings, severity-ranked)

| ID | Finding | Evidence | Risk / why it matters | Recommended action | Scope |
|---|---|---|---|---|---|
| **R1** | **Authority bypass**: an agent-only session can mutate a `human_confirmed` object with no approval by declaring `required_authority="deterministic_auto"`; no rule/profile registry exists to validate the declaration (M08 has no code) | arch-core probe + design-topology independent probe: height 18.0→99.0 committed, object stays `human_confirmed`; `runtime.py:117-119,328-335`; `human_confirm` and locked paths correctly blocked | Direct violation of the core invariant "the Agent never writes confirmed design state"; docs `authority.md` §3/§6 and `status.md` R1-G02 say otherwise | Server-side derivation of required authority + rule-registry binding + fail-closed test; schedule before any autonomous-commit feature. Not part of M4c-1a | **HIGH** |
| **R2** | Defect narrative wrong → next session would chase an OSMnx rebuild | §3 above; docs cited there | Wasted milestone, wrong evidence claims, possible tolerance-faked connectivity | Correct docs in M4c-1a; do not rebuild on OSMnx | **HIGH** |
| **R3** | Contracts are mostly prose: 22 YAMLs, only 3 parsed by tests; already drifted (`e2e-pipeline` xfail claims; `runtime-agent-surface` lists `object_view`, absent from surface) | arch-core; docs-audit; `surface.py:16-37` | Contract changes cannot fail CI; silent divergence | Parse every living contract in a test (start with the ones this work touches); add completeness test | **HIGH** |
| **R4** | "Single-writer per project" not enforced: `StatefulRuntime` uses `AtomicProjectFile` only; the lease is wired into the sidecar host, not the runtime | arch-core; `overview.md:98` vs `runtime.py:29`, `lifecycle.py:202-282,358-382` | Concurrent-process corruption risk mis-documented; CAS is optimistic detect-and-fail | Correct docs; wire lease or declare multi-process out of scope; add a test if wiring | MEDIUM |
| **R5** | FAR / parking / households are closed-form basis arithmetic (109×2×11; ceil(2398/500)), not spatial design results | cad-pipeline; `src/dgcad_design/basis.py` | "Meets FAR/parking" over-reads as a geometric validation | Add spatial checks or label as basis arithmetic in docs/summary | MEDIUM |
| **R6** | Only focus G-01 is drawn (7/55 buildings, 10/41 roads); the 4c DXF cannot show the design road topology; full-site spacing deferred | cad-pipeline (`drawing.py:241-245`), status §16 | Reviewers over-trust the DXF as a site plan | Label scope in README/title block; commit `design-roads.geojson`; expand in M4c-1b/M4c-2 | MEDIUM |
| **R7** | Third-party CAD evidence never ran on the 208-entity DXF: accoreconsole round-trip is a 15-entity synthetic fixture (AC1024→AC1032, 6 linetype normalisations, XDATA identical); LibreCAD/FreeCAD/GUI not run; handoff review-packet hash is format-checked only | cad-pipeline; `docs/e2e/third-party-003c/`, `sketch-domain-handoff-v0.2.yaml:163,173` | Over-claiming host portability; contract/code divergence | Keep non-claim; add a real-host lane for the actual DXF when a host is available; fix or document packet-hash check | MEDIUM |
| **R8** | Privacy scan can spuriously fail: numeric tokens are substring-matched against 539 uniform hex hashes (`ring_key`/`canonical_hash` = sha256 of canonical JSON); cad-pipeline estimates ~6.3% per run and ~26% over 5 regenerations. Fix is cheap: exclude 64-hex hash fields from numeric-token matching, keep digit detection on TEXT/layer/block/style names, add a deterministic regression test | cad-pipeline §E6 + `src/dgcad_e2e/privacy.py`, `serialization.py:32-33`, `dxf.py:75-91` | Evidence regeneration may randomly "fail" | Fix **before** iterating M4c-1 regeneration, not during it | MEDIUM |
| **R9** | DXF **is** byte-reproducible with `ezdxf.options.write_fixed_meta_data_for_testing=True` (two saves identical; `compile_to_dxf` twice identical); the project never sets it (`dxf.py:337` bare `saveas`), so committed bytes are random and handoff §8 is wrong | design-topology + cad-pipeline independent | Enabling it changes every committed DXF hash and invalidates `third-party-003c/comparison.json`'s recorded input hash (`tests/e2e/test_e2e_003c_third_party.py:72-79`) | Separate evidence-migration commit: enable option, re-run the AutoCAD host, then a regeneration-equality test can assert bytes; until then compare content/XDATA | MEDIUM |
| **R10** | Metric labels wrong: `junction_count` = new-connector road count; `dead_end_count` = rounded road-endpoint occurrences; `road_components` = corridor polygons | arch-core (rows 37, 40), design-topology §6.a | Metrics mislead reviewers | Rename/redefine in M4c-1a | MEDIUM |
| **R11** | Stale/incorrect documentation, 12+ items (status headline 206 vs 217; CONTRIBUTING "65 passed"; research-to-product-map 210 entities/210 readback/22 layers; handoff "28 files"; Chinese intro "154"; status §16 "214"; handoff §1 stale commit; no git tag) | docs-audit §8 | Actively misleads contributors and the next session | Fix in M4c-1a docs pass; tag v0.15.0 | MEDIUM |
| **R12** | `e2e-pipeline-v0.1.yaml` still claims DEV-CAD gaps are xfail; 0 xfail exist; only #6 remains. Two more contracts carry closed DEV-CAD items as open: `cad-ir-v0.1.yaml:162-170`, `e2e-adversarial-v0.1.yaml:255`. Superseded contract versions are unmarked (deployment v0.1, handoff v0.1, mcp v0.2); README §7 omits two living contracts | docs-audit + review round | Contract drift and confusion | Refresh contracts; mark superseded; add README rows | MEDIUM |
| **R13** | Test layer taxonomy incomplete: L0/L4 double-count lifecycle; 67 of 217 tests belong to no declared layer | docs-audit §5 | "Which tests protect what" is not reliably answerable | Rebuild `testing.md` layer table | LOW |
| **R14** | Documentary-only architecture: M01–M11 exist only in docs; M08 rule engine has no code; `AgentGateway` is a dead façade; MCP is a shim with no wire evidence | arch-core | Architecture diagrams over-promise | Mark documentary; decide M08 before rule claims | LOW |
| **R15** | Road evidence gaps: 121 junction review, 5 px closing kernel, road width/profile/alignment, 支路/入户路 separation remain open; 6 unit-count conflicts + kindergarten classification need the designer | roadmap, status §13–14, handoff §9 | EP-R1-ROAD-001 / SKETCH-001 blocked | Keep as open evidence packages; human input required | LOW |
| **R16** | Six dev-side pitfalls are real: ezdxf GUIDs regenerated on load; privacy-scan false positives; blocked handoff must not write domain-fixture; invalid sketch polygons need `make_valid`; road graph from `unary_union` not per-road endpoints; noding requires exact coordinates or explicit tolerance (new) | handoff §8 + this session | Re-discovering them costs a session | Keep handoff §8; add the noding lesson | LOW |
| **R17** | Wording caveat flagged by red-team: "five designer-confirmed merges" may overstate the designer text, which spells out only two merge patterns explicitly; the rest come from a resolution state (M-004/M-005 unit counts are already marked inferred) | red-team claim audit (not independently re-verified by the Lead); `docs/e2e/sketch-001/README.md:35-43,54-56,82,157-159` | Read as a stronger confirmation than it is | Qualify the wording at the next sketch-evidence refresh; keep the merge record's provenance visible | LOW |
| **R18** | Latent crash: `ParkingEntrance.point` can hold a **Polygon** for the 3 designer entrance markers (`input.py:194` maps Point geometry only), so `parking.py:28` / entrance `to_dict()` can raise `AttributeError`. red-team hit it; design-topology confirmed. It did not trip cad-pipeline's scratch regeneration | red-team + design-topology | Any entrance/summary serialization path can crash during evidence regeneration | Reproduce first in M4c-1a, then normalize entrance geometry to Point or extend the type; add a test | LOW |

---

## 6. Documentation corrections required (start of M4c-1a)

Beyond §3's defect narrative, the following are verified wrong/stale (docs-audit,
with cad-pipeline additions). Fix together with M4c-1a, not before (except the
defect narrative, which should not survive a PR merge):

1. `research-to-product-map.md:207` — 210 entities → 208; readback 210/210 → 208/208;
   22 layers → 23 design layers (25 table layers minus `0`/`Defpoints`, 20 used).
2. `CONTRIBUTING.md:33` — "Expected: 65 passed" → 217.
3. `docs/status.md:15,18` — 206 → 217 (the §2 table is correct).
4. `session-handoff.md:181` (was `:176` before the banner edit) — "28 files" → 15
   in `docs/e2e/design-synthesis-001/`.
5. `docs/status.md:358` — "214 passed" → 217 (or annotate per era).
6. `docs/status.md:343` — `test_sketch_handoff.py (31)` → 32.
7. `README.md:252,256` — Chinese intro 154 → 217 and extend through 4a/4b.1/4c.
8. `docs/status.md:349` vs `:351` — reconcile "5 entrances" as 3 existing + 2 proposed.
9. `contracts/e2e-pipeline-v0.1.yaml:50,62-64` — refresh DEV-CAD gap statement
   (only #6 open; zero xfail).
10. `README.md` §7 — add rows for `design-synthesis-v0.2` and
    `sketch-domain-handoff-v0.2`; mark superseded contract versions.
11. `docs/development/testing.md` §1 — rebuild layer taxonomy (L0/L4 double count;
    67 unmapped tests).
12. `session-handoff.md:27` (was `:22` before the banner edit) — latest commit
    `f812deb` → `83d71eb` at next refresh.
13. `docs/e2e/design-synthesis-001/README.md:13-31`; `docs/status.md:360,371`;
    `docs/roadmap.md:240-242`; `research-to-product-map.md:196`;
    `reuse-matrix.yaml:186,187-191` (`next_round` also carries the OSMnx-rebuild
    path); `CHANGELOG.md:24` — replace the "not topologically connected / rebuild
    on OSMnx" narrative with the reproduced diagnosis (§3). `README.md:94` holds
    DXF facts, not the defect narrative — leave it to the number-sync pass. For
    CHANGELOG, add a new version entry describing the correction and annotate the
    historical entry rather than rewriting it (same principle as item 15).
14. `session-handoff.md` §8 — "DXF is not byte-reproducible even with
    `write_fixed_meta_data_for_testing`" is wrong (see R9); keep the
    "compare content not bytes" advice until the evidence migration.
15. Annotate (don't rewrite) historical exit records: `roadmap.md:188` "206
    tests pass" was true at the 4b.1 exit; CHANGELOG historical counts are fine.
16. Optional release hygiene: create `git tag v0.15.0`; CHANGELOG entry dates are
    non-monotonic (0.11/0.12 dated 2026-10-28, 0.13–0.15 dated 2026-10-27) — worth
    one consistency note.
17. Doc blast radius: at least 8 locations carry the 4c numbers and must be
    updated as one set when the candidate is regenerated — `docs/status.md:349-360`,
    `session-handoff.md:58-70`, `docs/roadmap.md:199-206`,
    `docs/research-to-product-map.md:199-208` (still stale at 210/210/22),
    `README.md:75,252-256`, `docs/e2e/design-synthesis-001/README.md:46-94`,
    `CHANGELOG.md:49-56`; the "23 layers" figure alone appears in 4 places. This is
    how commit `83d71eb` fixed `roadmap.md:204` (210→208) but missed the product
    map. Build an explicit sync checklist in the M4c-1a PR description.
18. Optional: include the peer briefs (currently gitignored under `scratch/team/`)
    in a versioned docs folder if the project wants the audit trail; otherwise
    this dossier is the durable record.
19. `contracts/sketch-domain-handoff-v0.2.yaml:163` (declared 1e-6 endpoint
    tolerance vs 4.0 px implementation) and `:173` (review-packet hash "must
    match" vs format-check only) — contract-vs-code divergences found by
    cad-pipeline; fix or explicitly document.
20. `README.md:11` overstates the spatial scope ("traceable ... site model"); the
    design README's PNG-renderer sentence is unproducible as written (the PNG is
    not regenerated by the runner). Assign wording to the docs-audit owner in the
    M4c-1a docs pass — cad-pipeline's suggested wording: "focus G-01 detail sheet
    + site key plan; 7 of 55 buildings, 10 of 41 design roads".

---

## 7. Team protocol used (reusable)

**Roster and model assignment** (only the two requested base models):

| Member | Model | Domain authority | W1 deliverable | Cross-review |
|---|---|---|---|---|
| `arch-core` | deepseek-flash (high) | Foundation / Runtime / Deployment / authority | 44-row fact table, red lines | reviewed by red-team |
| `design-topology` | deepseek-flash (max) | 4c design domain, road topology, M4c-1 fix design | reproduction + root cause + fix | reviewed by red-team |
| `cad-pipeline` | deepseek-flash (high) | CAD-IR → DXF → readback, handoff, evidence guardrails | "what is not proven" + guardrails | reviews docs-audit |
| `docs-audit` | glm-5.3-flash (high) | cross-doc consistency, CI/env baseline | stale-claim list + authoritative numbers | reviews cad-pipeline |
| `red-team` | glm-5.3-flash (max) | adversarial claim verification | 15-claim verdict table | reviews arch-core + design-topology |

**Claim audit result.** red-team re-derived 15 load-bearing numeric claims from
artifacts in an isolated pass: all 15 were CONFIRMED (0 wrong, 0 unverifiable).
The only wrong statement found in the audited set was a *derived* sub-claim in
`session-handoff.md` §8 (DXF byte reproducibility), independently confirmed wrong
by design-topology and cad-pipeline. The numeric chain
(basis → metrics → consistency → DXF → manifests) is internally reproducible; the
systemic weakness is documentation drift, not fabricated numbers. Two caveats
worth carrying: the "cyclomatic 0" figure understates the defect (true cycle rank
5 on the multigraph / 4 on a simple graph), and "five designer-confirmed merges"
has a provenance nuance (risk R17).

**Working rules that made the result usable:**

1. **No master-slave**: each member is authoritative in its domain; the Lead
   coordinates process and integrates, but does not overrule a domain conclusion
   without artifact evidence. Peers message each other directly for missing facts
   (one round-trip each); disagreements are settled by file/command evidence,
   never by rank.
2. **Shared task board**: one unowned task per deliverable with explicit write
   scope; members claim with the current revision and complete when the artifact
   exists; review tasks depend on the reviewed task.
3. **Write scopes are disjoint**: every member wrote only under
   `scratch/team/<name>/` (gitignored); the repo stayed read-only for everyone but
   the Lead. This is what made 5 parallel investigators safe.
4. **Evidence standard**: every claim carries `file:line`, a command output, or an
   artifact value; verdicts are `VERIFIED / DOCUMENTED-UNVERIFIED / WRONG /
   UNKNOWN`, and "unknown" is a legitimate answer. No fact may be inferred from
   another document's restatement of it.
5. **Independent reproduction first, cross-review second**: reviewers re-derive
   the numbers they check (not just read the brief), and must produce at least
   three weaknesses/questions. The cross-review caught real things (the DXF
   reproducibility error, the design-topology contract-parse gap, and the
   `momepy` metric artefact).
6. **Forbidden operations**: running the evidence-rewriting scripts
   (`scripts/design/run_design_synthesis_001.py`, `experiments/m4c0/run_all.py`)
   in the repo; touching tracked files; editing another member's brief.

**Cross-review ring result (all five completed, no REJECT):**

| Author | Reviewer (model family) | Verdict | Corrections folded |
|---|---|---|---|
| arch-core | design-topology (deepseek same family) | ACCEPT-WITH-CORRECTIONS | contract must be test-parsed; gate-register refs; exp-c must consume `topology.py`; 4 docs must be corrected |
| design-topology | red-team (glm → deepseek) | ACCEPT-WITH-CORRECTIONS | line-level predicate; 5 (not 17) entrances; v0.2 unconditional; 3 design rings; recomputed-entity-count wording |
| cad-pipeline | docs-audit (glm → deepseek) | ACCEPT-WITH-CORRECTIONS | E1 scope; verdict source; line ranges; write-ownership; doc blast radius |
| docs-audit | cad-pipeline (deepseek → glm) | ACCEPT-WITH-CORRECTIONS | 121-junction source; layer count qualifier; spacing is policy not code; 5 omissions |
| red-team | arch-core (deepseek → glm) | ACCEPT-WITH-CORRECTIONS | momepy formula wording; 23/25/20 layer arithmetic; wrong script citation; tally-vs-subclaim |
| **the dossier** | red-team + docs-audit | **ACCEPT-WITH-CORRECTIONS** (both) | C1 privacy pre-step; C2 tolerance mechanism; C3 index; C4 line drift; C5 parking crash; doc-list fixes |

Every reviewer re-derived numbers with its own scripts; two independent repair
prototypes (design-topology and red-team) reached the same exact-junction result.
The dossier below already folds every correction that was accepted.

**How to re-run this team shape next time** (one paragraph of guidance, not code):
spawn 4–5 specialists with disjoint domains and explicit read lists, give each a
self-contained task with a write scope, require file:line evidence + a brief, then
assign a cross-family review ring (each member reviews exactly one peer) and one
adversarial verifier that re-derives the load-bearing numbers; the Lead writes the
integration artifact and submits it to the adversary for audit before use.

---

## 8. Open decisions for the human

1. **PR #34**: merge now, or land M4c-1a first and merge the corrected candidate?
   *Recommendation: M4c-1a first* — it is small, metric-neutral, and removes a
   wrong claim from the PR that reviewers would otherwise read.
2. **M4c-1a scope sign-off**: topology-only + exact junctions + docs/evidence
   regeneration (as §4.1). *Recommendation: yes, as a separate reviewable commit.*
3. **M4c-1b policy**: branch terminations to entrances + G-05/G-12 access changes
   road geometry and needs design judgement — approve or defer?
4. **Authority bypass (R1)**: schedule as a dedicated hardening milestone before
   any "autonomous commit" feature. *Recommendation: yes; do not wait for M5.*
5. **DXF byte-reproducibility (R9)**: enable + re-run the AutoCAD host as a
   separate evidence migration? *Recommendation: yes, but after M4c-1a.*
6. **Human-input items** (designer): unit-type library, six unit-count conflicts,
   kindergarten classification, object-level review signature, full-site 20 m
   spacing policy.
7. **Keep or discard the session audit artifacts?** The peer briefs live in
   `scratch/team/` (gitignored). If they should be kept as evidence, copy them to
   a versioned docs folder in the same PR as M4c-1a; otherwise this dossier is
   the durable record.
8. **Commit plan for this dossier**: commit the dossier + the `session-handoff.md`
   pointer as one docs-only commit
   (`docs: add verified team continuation dossier and correct handoff pointers`),
   then repin the `83d71eb` references (§1 pin discipline) and re-run `pytest -q`.
   If you prefer not to touch PR #34 yet, leave both files uncommitted — the
   dossier is still readable in the work tree.

---

## 9. Evidence index

**Committed evidence used (read-only):**

- `docs/development/session-handoff.md` — continuation state (corrected by §3/§6 here).
- `docs/e2e/design-synthesis-001/` — 15 files: `design-summary.json`,
  `design-consistency.json`, `design-diff.json`, `design-intent.json`,
  `design-proposal.dxf`, `readback-manifest.json`, `validation.json`,
  `privacy.json`, `draft-manifest.json`, `scene-snapshot.json`, `cad-ir.json`,
  `design-preview.png`, `design-basis.yaml`, `design-profile.yaml`, `README.md`.
- `docs/e2e/open-source-reuse-001/` — `exp-b`, `exp-c`, `reuse-matrix.yaml`.
- `docs/e2e/third-party-003c/` — accoreconsole round-trip (15-entity fixture).
- `docs/e2e/sketch-001/`, `docs/e2e/sketch-handoff-a/` — sketch/handoff evidence.
- `contracts/` (22 YAML), `src/dgcad_*`, `tests/` (217), `.github/workflows/ci.yml`.

**Session evidence (gitignored, still on disk):**

- `scratch/lead/lead-findings.md`, `repro_topology*.py`, `diagnose_gap.py` —
  Lead's independent reproduction (51/51/5, gaps, 1e-9 → 1 component).
- `scratch/team/arch-core/` — `brief.md`, `independent-claim-checks.md`, probes.
- `scratch/team/design-topology/` — `brief.md`, scripts `01`–`08`, `out/`
  (reproduction, root cause, repair prototype, OSMnx, DXF repro).
- `scratch/team/cad-pipeline/` — `brief.md`, `review-docs-audit.md`,
  `erratum-dxf-reproducibility.md`, verify scripts + regen experiment.
- `scratch/team/docs-audit/` — `brief.md`, verify scripts.
- `scratch/team/red-team/` — `claim-verdicts.md` (15/15 confirmed),
  `review-design-topology.md` (ACCEPT-WITH-CORRECTIONS; 4 corrections),
  `review-dossier.md` (ACCEPT-WITH-CORRECTIONS; C1–C5) + 14 verification scripts.

**Reproduction commands:**

```bash
cd D:\agent-cad
python -m pytest -q                                   # 217 passed
python scratch/team/design-topology/01_repro_topology.py   # 51/51/5
python scratch/team/design-topology/06_repair_prototype.py # 1 component, 0.0 m
python scratch/lead/diagnose_gap.py                        # exact gaps + tolerance test
git status --short                                          # clean
```

---

*Prepared by the DGCAD peer team on 2026-10-28. This is a development note: it
does not change any contract, authority rule or capability claim. Claims about the
codebase are bounded by the tests and evidence cited above; non-claims in
`README.md` §3 and `docs/status.md` §18 continue to apply.*
