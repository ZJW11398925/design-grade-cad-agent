# Changelog

## 2026-10-26 — R0.2: Road classification and design profiles

- Added `CAP-ROAD-10..13` for road hierarchy/function classification, profile resolution, class-aware junction/transition geometry, and classification provenance.
- Added `COV-21..23` to the research plan.
- Added `BEN-ROAD-009..015` for class ambiguity, special-use conflict, profile transitions, and standard-version conflicts.
- Added `working/road-classification-and-design-profile.md` with a multi-axis data model, inference/evidence policy, profile resolution, and next research actions.
- Recorded calibration search `RUN-CAL-004`; this is not a formal acquisition or standards compliance finding.
- No final technology selection or engineering parameter values were frozen.


## 2026-10-26 — BATCH-001: Road Semantics & Design Profile

- 将原先过宽的首批范围修订为精确的道路语义/Profile 批次；理由是道路分类是中心线、横断面、交叉口和规则引擎的上游依赖。
- 新增 `working/road-profile/` 下的采集计划、运行日志、发现命中、来源定位、候选分析、Profile schema、标准来源图与 KNO 候选。
- 对 Street Generator 做了部分源码定位审查；记录 `license=null`，暂停任何代码复用推断。
- 将 OSM 与 SUMO 限定为网络语义/图模型参照；将 Streetmix 限定为概念横断面/共同设计参照。
- 新增 `BEN-ROAD-016..020`；新增 `CAP-ROAD-14..15`。
- GB 55011 全文附件本轮 cache-miss；GB 55037/55019 直接打开超时；未完成标准条文核验。
- A1 未执行；搜索总量/分页完整性未知；未建立最终 `DEC-*`。
- 根目录 `CHANGELOG.md` 与 `working/changelog.md` 内容重复，合并保留在本文件后移除根目录副本，以符合主题目录角色约束。


## 2026-10-26 — BATCH-001 second-wave source review

- 新增 `RUN-001-06..08`：Streetmix current LICENSE/metadata、CJJ 37/GB 55011 关系定向检索、SUMO OSM import 和 GB 55011 二次全文转载阅读。
- SUMO 证据更新：type-map 默认值依赖国家/城市上下文，官方文档标记随附值为 ad-hoc/not verified；交叉口合并为启发式且可能误合并。
- CJJ 37 关系更新：二次全文转载列出 CJJ 37（2016版）第 3.4.2、3.4.3、13.3.4 条在废止的相关强制性条文清单中。原始住建部附件仍访问失败，故保留为 secondary evidence，不做正式标准状态结论。
- Streetmix 代码 LICENSE 确认为 AGPL-3.0-or-later；repo API 的 `Other/NOASSERTION` 是复合许可元数据，不代表许可证缺失。
- BATCH-001 仍 `in-progress`；A1 未执行，搜索结果截断状态仍未知，未冻结任何 DEC。


## 2026-10-26 — Mainline closure checkpoint

- 新增 `working/mainline-roadmap.md`，明确产品技术链与 Skill 调研流程两条闭环、G0–G8 阶段门及防止局部研究无限扩张的规则。
- 新增 `working/coverage-dashboard.md`，将 COV-01..23 按端到端能力线汇总，显式标记校准、阻断和未测试状态。
- 新增 `working/cross-pipeline-checkpoint.md`；对 PyGeoOps centerline、IfcOpenShell Axis/Footprint/Body 表示、ezdxf 文件级 audit、Ladybug Tools 日照/阴影功能进行了官方资料校准。
- 将本轮查询记为 `BATCH-CAL-003 / RUN-CAL-005`；它是校准，不冒充 BATCH-001 的新 RUN 或 A1 通过。
- 更新 `research-plan.md` 的唯一下一动作到 `NEXT-001-R2`：对道路 batch 做有界阻断处置；如果不同来源路线仍无法解决 A1 阻断，则保留未关闭状态并回到全局 Coverage 排序，不原样重复失败路径或继续扩张道路研究。
- 未创建 `DEC-*`，未冻结 CAD-IR/IFC 的最终角色，未声明任何中国规范合规或本地算法可用性。

## 2026-10-26 — BATCH-001 bounded blocker route update

- 新增 `RUN-001-09 / AUD-001-09`：通过 GitHub 直接 API 检查 Street Generator 根目录、`LICENSE`/`COPYING` 路径，并检索/读取 SUMO issue #7615、#7119、#15013。
- 新增 `HIT-016..018`：记录 OSM typemap 默认方向/通行权限问题，以及 join 操作日志可能保留已撤销中间态的项目 issue 证据；明确它们不是独立复现，也不证明当前版本仍存在同样缺陷。
- 补充 Street Generator 许可路线：未找到标准根目录许可文件，许可仍未解决；不能把“未发现许可”写成法律上的确定无许可结论。
- A1 仍未执行：搜索结果截断未知、官方标准全文/状态路线未完成、issue 搜索总量未知且无独立复现路线。未生成 DEC 或合规结论。
- 保持主线约束：该批仅做有界阻断处置，若不同来源路线仍不能解决阻断，则回到全局 Coverage 排序，不继续扩张道路子题。


## 2026-10-26 — BATCH-002: Sketch Calibration & Trace entry line

- 按主线防漂移规则暂停继续扩张 BATCH-001；道路批次保持未关闭/A1 未执行。
- 启动 `BATCH-002`，范围限定 `COV-01..04 + COV-20 entry`：输入校准、语义候选、忠实 Trace、人工确认/provenance。
- 更新当前视觉候选：SAM 3/3.1 已取代旧矩阵中的 SAM2-only 视图；当前仓库使用 custom SAM License，checkpoint 需授权访问。SamGeo 为 MIT wrapper，但不覆盖 SAM 后端许可。
- 新增 OpenCV/GDAL/Potrace、RedrawAI、Raster2Seq、floorplan-to-vector 的入口/相邻路线记录。
- 执行 `LOCAL-SKETCH-001`：量化 homography 控制点误差、单一已知尺寸比例误差、Douglas–Peucker 简化的 Hausdorff/面积变化。合成结果不作为真实生产精度。
- 新增 `CAP-SKETCH-05..07`、`BEN-SKETCH-005..010`、`trace-object-schema-v0.1.yaml` 和 BATCH-002 运行/来源/知识记录。
- 修正 capability-map 中此前 changelog 声称存在但文件遗漏的 `CAP-ROAD-10..15`。
- 当前唯一下一动作改为 `NEXT-002-R1`：定义真实入口 Benchmark 数据合同并完成 BATCH-002 首轮来源闭合，然后回到 Coverage Dashboard。

## 2026-10-26 — BATCH-002 ready-for-A1 + BATCH-003 start

- 完成 `working/sketch-trace/real-benchmark-contract-v0.1.md` 与 `benchmark-case-schema-v0.1.yaml`，将入口真实 Benchmark 分为 Tier A controlled paired raster、Tier B human sketch on known base、Tier C field paired case。
- 新增 `RUN-002-05`：有限检索 paired site-plan sketch Benchmark；触达 floorplan 数据集与 GIS/masterplan 生成项目，但本轮没有确认同时具备真实场地草图、尺度/坐标、人工忠实 Trace、语义标签和专业 CAD 真值的公开数据集。此项仅记为 discovery gap，不宣称互联网上不存在。
- BATCH-002 状态调整为 `ready-for-A1 / unclosed`；A1 必须独立复核，当前线程不自行批准；Tier B/C 真实实测仍缺。
- 按总体主线启动 `BATCH-003`，范围限定 `COV-10..11 + COV-13`，关联 `COV-12/14/20`：Building Trace → Professional Footprint → Massing → 2D/3D identity。
- BATCH-003 首轮触达 Building Regulariser、CartAGen/FER、UrbGEN、IfcOpenShell/Bonsai、COMPAS；新增 building object provisional schema 与失败 Benchmark。
- 新增 `CAP-BLDG-06..08`、`CAP-3D-05..06`、`BEN-BLDG-005..013`、`BEN-3D-003`。
- 未进入户型、立面、结构/机电；未冻结建筑 regularization 阈值、高度默认值、typology 或 IFC 最终集成方式。


## 2026-10-26 — BATCH-003 second-wave: regularization refusal and representation lifecycle

- 新增 `RUN-003-04..08`：Building Regulariser 源码/测试/changelog、针对性 issue 复核、CartAGen FER 与 IfcOpenShell 官方文档、LOCAL-BLDG-002、IfcOpenShell 安装阻断。
- 修正 Issue #5 的证据状态：v0.2.4 changelog 已记录 invalid-input 修复，v0.2.5 增加 MultiPolygon 回归测试；不再把历史问题说成当前必现。
- 记录 Issue #8 的 topology 风险：维护者说明 polygon 独立处理、不理解共享边/相交关系；当前 changelog 未列修复。
- 新增 `regularization-gate-v0.1.md`、`site-topology-contract-v0.1.yaml`、`local-benchmark-002-regularization.*`、`ifc-roundtrip-contract-v0.1.md`。合成 Validator 的 5 个断言通过；不代表规则化算法或 IFC round-trip 已通过。
- BATCH-003 调整为 `bounded-paused / unclosed`，原因是 RUN-003-01 搜索截断仍 unknown、IFC 运行环境被 DNS 阻断、真实设计草图阈值未校准。未批准 A1，未做最终技术选型。
- 回到全局 Coverage，下一条主线转向 `COV-16..19` CAD/BIM Compiler + Validator，避免继续无限扩张建筑规则化子题。


## 2026-10-26 — BATCH-004 start: CAD/BIM Compiler + Validator

- 新增 `working/cad-bim-validator/`：精确采集计划、来源定位、候选知识、CAD-IR provisional contract、分层 Validator matrix。
- 读取 ezdxf / LibreCAD / libdxfrw / IfcOpenShell / IfcTester 官方仓库与文档，区分 DXF 写入/文件审计、独立 CAD 读者、DWG 边界和 IFC IDS 信息验证职责。
- 新增 `LOCAL-CAD-003`：在 Python 3.13.5 / ezdxf 1.4.4 下创建、写入、重读合成 DXF，执行 `audit()` 与自定义 Profile Validator，6 项断言通过；生成可回读的测试 DXF。
- 观察到 ezdxf 1.4.4 对无效 lineweight 27 的赋值会规范化为 30；因此 Profile 必须在编译前预检，并比较请求值与写出值。
- 明确合成 Profile 不是任何真实设计院标准；没有 LibreCAD/AutoCAD/FreeCAD/IfcOpenShell 的独立或 IFC round-trip 结果。
- BATCH-004 状态为 `in-progress / unclosed`；RUN-004-01 搜索截断 unknown，A1 未执行。主线下一动作更新为 `NEXT-004-R1`。


## 2026-10-26 — BATCH-004 source-backed standards profile probe

- 从北京市规划和自然资源委员会官方 PDF 与国家标准信息平台定位 DB11/T 1948-2021；确认它是现行的北京地方标准，适用范围为北京市国土空间详细规划，不是通用全国标准。
- 新增 `profile-rule-contract-v0.1.yaml`、`db11t1948-profile-extract-v0.1.yaml`、`standards-profile-source-map-v0.1.md`。提取真彩色、坐标基准、单位/精度、拓扑、实体类型、CAD 图层命名与部分道路/用地层示例。
- 新增 `LOCAL-CAD-004`：来源型图层名/RGB/单位/实体类型/闭合面/拓扑子集检查通过；人为重叠的面要素被检测；坐标参考因合成本地坐标而 blocked，总体 `full_profile_compliance=false`。
- 明确标准中的“按图面效果自定”不能被 Agent 擅自改成强制线宽；Profile 需要区分 mandatory/recommended/discretionary/project-configured。
- 官方符号库/字体库资源点击返回内部错误，未宣称其下载或许可核验成功。


## 2026-10-26 — BATCH-004 bounded checkpoint; BATCH-005 planned

- BATCH-004 完成两个本地 DXF/Profile 探针：`LOCAL-CAD-003`（合成 Profile）与 `LOCAL-CAD-004`（DB11/T 1948-2021 官方来源摘录）。后者的可测子项通过，但坐标基准仍 blocked；不宣称完整标准合规。
- 由于搜索截断 unknown、第三方 CAD/BIM 软件未安装、真实 IFC round-trip 受环境阻断、用户项目 Profile 未确认，BATCH-004 调整为 `bounded-paused / unclosed`。不冻结技术选型，不关闭后续验证任务。
- 全局 Coverage 回流后，下一主线转向 `BATCH-005` 环境分析与规划反馈（`COV-14..15`），研究太阳位置、阴影/遮挡、日照指标及 geometry revision 依赖，避免在输出工具局部阻断上无限深挖。
- 新增 `working/environment-analysis/collection-plan.md` 与 `BEN-ENV-001..008`，当前只冻结研究范围，尚未开始正式来源获取。


## 2026-10-26 — Skill layout check and workspace snapshot

- 按提供的 Research Skill 执行只读 `check_research_layout.py`：初次调用因把 IFC contract 写成错误的相对路径而失败（RUN-004-09）；纠正为真实路径后 `layout_valid=true`（RUN-004-10），显式检查 4 个 Benchmark/contract 文档。
- 该检查仅覆盖声明的文件与 entry/plan 链接，`expected_runs_checked=0`、`actual_action_coverage=supplied-expectations-only`、`research_complete=false`、`release_authorized=false`。它不证明实际动作全覆盖、领域事实正确或研究完成。
- 完成 YAML/JSON/JSONL 解析、运行 ID 唯一性和三个本地 Benchmark 脚本语法检查；未创建正式 governed package，也未选择摘要绑定型 acquisition overlay。


## 2026-10-26 — BATCH-005 bounded checkpoint: solar/shadow probe

- 对 Ladybug Core/Sunpath、pvlib NREL SPA、NREL SPA 报告、Honeybee-Radiance Direct Sun Hours 与 momepy 进行首轮官方来源核验；记录项目角色、许可与本地运行边界。搜索总量/分页完整性未知，不宣称生态穷尽。
- 新增 `solar_shadow.py`、`test_solar_shadow.py`、`run_local_benchmark.py` 与 `LOCAL-ENV-001` 机器可读/人读报告。低精度 NOAA 太阳位置与 Ladybug 公开 Sydney 示例在 0.5° 容差内相符；17 个断言函数直接调用通过。
- 本地合成测试覆盖已知/未知高度遮挡、缺失上下文、北向旋转、时区输入检查、依赖 fingerprint 与 height revision stale。样例不是真实场地或法规合规测试。
- 更新环境分析依赖合同、结果 schema、Benchmark 合同、来源图与候选知识；增加 `CAP-ENV-04..05` 和 `BEN-ENV-009..010`。
- pvlib/Ladybug/Honeybee-Radiance/momepy 未本地运行，安装受 DNS/网络阻断；pytest CLI 未在当前沙箱干净终止，虽直接调用测试函数全部通过。BATCH-005 定为 `bounded-checkpoint / unclosed`，不批准 A1，不做最终技术选型。
- 当前下一动作改为 `NEXT-005-R2`：建立跨流水线差距审计表，明确真实证据、合成证据与 blocked/unknown，不把局部 Demo 相加当作端到端系统。


## 2026-10-26 — Cross-pipeline shared fixture vertical slice

- 新增 `working/cross-pipeline-gap-audit-v0.1.md`，明确各批次证据等级与最大集成缺口：当前主要风险是缺少共享 canonical site fixture/object-revision lineage，而不是缺少某个名气更大的工具。
- 新增 `E2E-FIXTURE-001`，包含 site boundary、road centerline、green space、两个 building footprints（一个合成已知高度、一个高度 unknown）、coordinate frame/north/time 与 3 个 sensor points。所有值均明确标记为 synthetic。
- 新增 `LOCAL-E2E-ENV-001`：3/3 传感器状态符合预期；2/2 合成 Footprint/Body identity 状态检查通过；高度 revision、geometry content 变化但 revision 未更新、北向变化都会使结果 stale。
- 新增 fixture→provisional CAD-IR adapter 与 `LOCAL-E2E-CAD-001`：8 个对象 ID 编译到 11 个 DXF 实体，ezdxf audit 0 errors/fixes，XDATA/manifest 回读保留类别、geometry revision、hash、layer 与测试坐标。仅为同库回读。
- 新增独立复核清单/manifest；`COV-20` 更新为 `partial synthetic vertical slice`，不代表真实 Source→Trace→Professional Geometry 的完整端到端能力。
- 当前唯一下一动作改为 `NEXT-E2E-002`：独立复核共享 fixture 与运行证据；真实 paired site-sketch 与第三方 CAD round-trip 保持独立残余 Gate。


## 2026-10-27 — E2E-FIXTURE-001 v0.2 adversarial review and regression hardening

- 保留 v0.1 原件及其历史 review packet，新增 `site-fixture-v0.2.json`（`fixture_revision: r2`）和版本化 mapper/environment/DXF 脚本，避免静默修改旧 fixture。
- 内部对抗性复核发现：旧 Body projection 检查为 footprint 与自身比较；环境 fingerprint 漏掉高度/状态/标高/Body geometry 内容；DXF 导出会静默丢失 polygon interior ring；DXF 验证未覆盖单位、图层属性、标签、坐标变异与意外实体。
- R2 新增真实存储的合成 prism mesh 与 top/bottom projection、标高、closed-shell 检查；环境 fingerprint 纳入 height value/state、base elevation、body representation/content hash、footprint content hash、timestamp、方法版本、sensor-grid content、terrain content 与 context coverage。
- 新增 `dxf_validator.py` 独立代码路径：检查 DXF 版本、INSUNITS、图层颜色/线型/线宽、精确实体数量、实体类型、身份/版本、source/representation hash、轮廓坐标/闭合、Point marker/label 以及额外实体。
- Polygon/MultiPolygon exterior/interior rings 现在分别导出并写入 `outer`/`hole` 与 part/ring 元数据；明确这仍是轮廓线而非填充 DXF Region。
- `run_adversarial_review.py` 变异测试通过：高度数值/状态、标高、Body 顶/底顶点、时间、方法版本、sensor grid、terrain 与 context coverage 变化均改变 fingerprint；图层线宽、单位、标签、polyline 坐标和未标记额外实体均被 validator 拒绝；hole 变异保留 outer/hole 两类轮廓。
- 环境测试 `pytest -q test_solar_shadow.py`：17 passed；E2E v0.2 3/3 sensor states、2/2 stored body checks、11/11 base DXF entity mapping checks 通过，0 audit errors/fixes。
- 新增 `local-e2e-fixture-slice-002.md`、`adversarial-review-report-v0.2.md`、`independent-review-checklist-v0.2.md`。审查状态为 `conditional / external_review_pending`，没有批准 A1/生产 Gate；第三方 CAD 应用、独立太阳模拟、真实草图、IFC 与法规合规仍未验证。
- 使用随项目保留的 `conduct-traceable-research` `check_research_layout.py` 对 v0.9 active entry/plan 和 4 个 E2E 必需文件复核：`layout_valid=true`、无链接问题；但 `expected_runs_checked=0`、`actual_action_coverage=supplied-expectations-only`、`research_complete=false`、`release_authorized=false`。该结果只验证声明的目录与链接，不构成技术审查或外部 A1。


## 2026-10-27 — R0 v0.10 / E2E-FIXTURE-001 v0.3

- 对 v0.2 review packet 执行 33/33 文件哈希校验、复跑既有命令，并做隔离的额外变异审查；结论 conditional，明确不冒充外部独立签字。
- 新增 `reviews/independent-review-report-v0.3.md` 和机器可读结果，记录布局空间、2D Z、样式策略、层集合、太阳天顶、布尔数值输入和时数区间语义问题。
- 保留 v0.2 历史源文件；新增版本化 `dxf_validator_v0_3.py`、`solar_shadow_v0_3.py`、合成 DXF Profile 和回归测试。
- v0.3 太阳测试（v0.2+v0.3）44 项通过；DXF validator 回归 12 项通过；E2E fixture 3/3 传感器、2/2 Body 检查通过；DXF 8 个对象 ID、11 个 modelspace 实体、0 audit errors/fixes。
- 主线唯一下一动作更新为 `NEXT-E2E-005`：将 v0.3 包交给未参与编写的独立审查者，并争取第三方 CAD 应用往返测试。所有生产/A1 Gate 仍未获批。

## 2026-10-27 — R0 v0.11: user local review absorbed, implementation hardening deferred

- Recorded user-run local review of E2E-FIXTURE-001 v0.3, including AutoCAD 2022 core round-trip.
- Kept verdict `conditional`; did not promote to pass/A1/production.
- Added research-level DXF semantic equivalence policy: symbol-table names default case-insensitive, while LWPOLYLINE bulge/width/elevation/thickness/extrusion remain semantic geometry fields.
- Added formal-development acceptance contract for MultiPolygon schema, safe entity dispatch, full LWPOLYLINE semantics, structured validator errors, and third-party round-trip matrix.
- Added BEN-OUT-008..012 as development-stage regression cases.
- Changed the unique next action from validator hardening to `NEXT-R0-SYN-001` provisional architecture synthesis.


## 2026-10-27 — R0 v0.12: Architecture Synthesis Phase 2

- 将 M01–M11 从职责说明推进为 `module-contracts-v0.1.md`：明确 authoritative inputs、outputs、truth ownership、human gate、stale trigger 与 MVP responsibility。
- 新增 `agent-authority-matrix-v0.1.md`：Agent 仅生成 proposal/orchestrate；规则、几何、验证与 human confirmation 分离；锁定对象与 confirmed truth 不允许 Agent 直接覆盖。
- 新增 `canonical-site-ir-v0.2.yaml`：加入 authority/lifecycle state、ChangeProposal、representation dependency、external reconcile，不再让外部 CAD/BIM 文件直接覆盖 canonical。
- 新增 `open-source-capability-allocation-v0.1.md`：把 Shapely/ezdxf/IfcOpenShell 等归位为 core/adapter/reference/external gate，而不是“最终技术栈名单”。
- 新增 `mvp-boundary-v0.1.md`：MVP-A 收敛到简单 site sketch → human confirmed objects → road/building professional geometry → massing → fixed-time shadow → DXF → validator → stale/local rebuild；复杂规划生成、户型、完整法规、DWG production 延后。
- 新增 `provisional-decision-register-v0.1.md` 与 `research-gap-matrix-v0.2.md`，区分强 provisional decision、可重开条件、R1 mandatory spike 与 development hardening。
- `NEXT-R0-SYN-001` 完成 Phase 2；唯一下一动作改为 `NEXT-R0-SYN-002` Architecture Challenge / R0 Exit Review。研究仍为 conditional/provisional，不批准 G3/G5/A1/production。


## 2026-10-27 — R0 v0.13: Architecture Challenge and R1 charter draft

- 执行 `NEXT-R0-SYN-002`，用 12 个失败场景挑战 competing truth、adapter lock-in、stale propagation、authority bypass、unsupported/fail-closed 与 MVP scope。
- Verdict：`provisional_architecture_survives_with_amendments`；未发现需要推倒重来的根本冲突。
- 识别 5 个 R1 Foundation 必须修正：Atomic ChangeSet、Proposal Snapshot、广义依赖图、conditional rule applicability、canonical/preview/external 三世界隔离。
- 新增 `canonical-site-ir-v0.3.yaml`、`architecture-challenge-report-v0.1.md`、`architecture-amendments-v0.1.md`。
- 新增 `r1-development-research-charter-draft-v0.1.md`；强调当前仍是技术研究/开发前准备，不代表正式产品开发开始。
- 唯一下一动作转为 `NEXT-R1-CHARTER-001`：复核 R1 scope/Evidence Gates 并定义最小 evidence packages。


## 2026-10-27 — R0 v0.14: R1 Charter Review and Evidence Packages

- 完成 `NEXT-R1-CHARTER-001`。复核结论：R1 scope 维持，采用 Foundation 先行 + Evidence Gate 分层解锁，不要求在 R1.0 前伪造所有 R0 batch closed。
- 新增 `r1-charter-review-v0.1.md` 与 `r1-development-research-charter-candidate-v0.2.md`；明确 R1.0–R1.6 的进入条件、禁止宣称和 Scope Freeze Rule。
- 新增五个最小 Evidence Packages：`EP-R1-SKETCH-001`、`EP-R1-ROAD-001`、`EP-R1-IFC-001`、`EP-R1-ENV-001`、`EP-R1-PROFILE-001`。每包均定义 decision question、原始证据、metrics、失败处置、Gate conditions 与禁止外推范围。
- 新增 `r1-evidence-gate-register-v0.1.yaml`，把 R1-G01..G08 与 evidence packages / claim blockers 机器可读化。
- 未人为写入统一性能阈值；Trace、alignment、environment 等数值阈值须来自 baseline 分布或 authoritative source。
- 新唯一下一动作：`NEXT-R1-ENTRY-001`，只规划 R1.0 Foundation repo/package skeleton、typed contracts、contract tests 和 synthetic fixtures；尚不开始复杂功能实现。

### v0.15 — R1.0 Foundation Entry
- Added executable research-only Foundation skeleton and typed fixtures.
- Initial 8 contracts passed; architecture challenge exposed preview-confirmation ordering, transitive stale propagation and over-broad lock semantics.
- Amended contracts; expanded suite now 12/12 passing.
- Added Foundation contract register, entry review and first-week entry plan.
- No geometry/AI/CAD/BIM/domain feature implementation added.

## 2026-10-27 — R0 v0.16 / Foundation v0.2 + Agent integration boundary

- 完成 `NEXT-R1-FOUNDATION-002` 的第二轮 research prototype：Foundation contract suite 扩展至 21/21 passing。
- 新增 deterministic canonical serialization/hash、non-finite value rejection、dependency cycle detection、topological rebuild planning、audit JSONL round-trip、conservative proposal rebase、same-field conflict fail-closed、field-path lock、schema migration registry。
- 新增 protocol-neutral `AgentGateway`，明确 `ActorContext` 由宿主注入；Agent 不能通过参数声明 human/unlock 权限，也没有 raw canonical mutation API。
- 架构候选收敛为 `Agent -> thin MCP adapter -> stateful DGCAD Runtime -> Foundation Core -> domain/adapters`；CLI 保留为测试/运维适配器，Human Review UI 使用独立 authenticated control-plane 路径。
- MCP 仅作为第一 Agent protocol adapter，不进入 Foundation truth/authority/dependency 语义；A2A 延后到 DGCAD 真正成为独立 specialist Agent 的 R2+ 场景。
- 新增 `agent-integration-architecture-v0.1.md`、`agent-integration-options-v0.1.md`、`agent-authority-boundary-v0.1.md`、`agent-tool-contract-v0.1.yaml`、MCP binding draft 和 thin Agent Skill draft。
- 新唯一下一动作改为 `NEXT-R1-RUNTIME-001`：研究最小 stateful runtime contract，包括 durable project store、idempotency/retry、proposal lifecycle、job/artifact registry、restart-safe rebuild scheduling，以及 CLI/MCP parity spike；仍不开始道路/建筑/AI domain adapters。


## 2026-10-27 — R0 v0.17 / Stateful Runtime Entry v0.1

- 完成 `NEXT-R1-RUNTIME-001` research checkpoint。
- 新增 self-contained Runtime prototype；clean ZIP extraction 43/43 tests passing（21 Foundation + 22 Runtime）。
- 新增 stateful project envelope、proposal/approval/job/artifact/idempotency registries、restart recovery、job claim generation、CAS stale-writer rejection、CLI/MCP semantic parity。
- 新增服务端 Human Control Plane approval model；Agent 不可传 `is_human` / `confirmed` / `can_unlock`。
- 新增 multi-object AtomicChangeSet runtime registration 与 mixed unlock+confirm regression。
- 记录 Runtime 非生产边界：single JSON state 仅为 contract carrier；无 distributed lock/auth/actual MCP/CAD bridge。
- 下一动作：`NEXT-R1-RUNTIME-002` deployment-boundary research。


## 2026-10-27 — R0 v0.18

- Added `working/r1-runtime-002/` deployment-boundary research.
- Executed SQLite/WAL + content-addressed artifact spike and clean-package tests (51/51).
- Selected local-sidecar hybrid as R1 deployment candidate; AutoCAD/FreeCAD remain thin bridges.
- Recorded MCP SDK environment blocker; no wire-level MCP conformance claim.
- Next action: `NEXT-R1-DEPLOY-003`.
