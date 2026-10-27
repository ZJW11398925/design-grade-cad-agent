# R0 获取情况：BATCH-001 道路语义与 Design Profile

性质：阶段获取说明；非 A1、非正式证据评审、非 Release。  
范围与时点：2026-10-26；本批聚焦道路层级/功能分类、道路类型到 Profile 的映射，以及与路网、横断面和规则引擎的接口。

## 本次任务与实际成果

已完成：
- 第二轮定向检索与来源读取：进一步审查 Streetmix 当前 LICENSE、SUMO OSM 导入默认值/节点合并警告，并查看 GB 55011-2021 前言/附录的二次全文转载。

- 建立精确批次计划 `CPL-ROAD-001-r1`，范围集中于 `COV-21/22`，联动 `COV-23`、`COV-08/09/18/19`。
- 检索并阅读 OSM `highway=*`、SUMO road network/type mapping、Streetmix、Street Generator 的官方文档/仓库。
- 通过 GitHub API 对 Street Generator 的 `StreetConfig` 模型、规则入口、RASt 规则和测试做了源码定位审查，保留 Git blob SHA。
- 获取 GB 55011-2021、GB 55037-2022、GB 55019-2021 等中国强制性通用规范的官方公告来源线索。
- 建立候选 Road Profile schema、候选知识记录与新增 Benchmark。

尚未完成：

- 未完成全部规定来源路线；未系统检索 issue/独立失败报告。
- 未完成 A1；网页搜索引擎总命中数/分页完整性不可得，相关 RUN 的截断状态为 `unknown`。
- 未取得 GB 55011 全文附件（本轮返回 `Cache miss`）；GB 55037/GB 55019 直接打开超时。
- 未核实 CJJ 37-2012（2016 年版）的当前状态、修订/替代关系和强制条文映射。
- 未运行任何项目本地测试或几何 Benchmark。

## 当前有边界的发现

1. OSM 的 `highway=*` 表示网络角色/重要性，不保证等于法定道路等级或物理特征。
2. SUMO 分开表达 edge、lane、junction 和 lane connection；其 type file 可映射默认属性，但属于交通仿真模型。官方文档警告其 OSM 类型映射默认值是经验设置、尚未验证。
3. Street Generator 的 `StreetConfig` 是按横断面左右顺序排列的组件与宽度；规则引擎固定调用德国 RASt 规则模块。其测试覆盖部分边界值、聚合宽度和关系检查，但本轮没有本地执行测试。
4. Street Generator 的 GitHub API 仓库元数据 `license=null`；在许可证澄清前，只作为架构研究对象，不复制/集成代码。
5. Streetmix 适合概念性横断面编辑和共同设计；当前代码 LICENSE 声明 AGPL-3.0-or-later，素材/内容许可应单独核验。
6. 住建部公告确认 GB 55011-2021 的实施日期和强制性属性，但当前批次没有取得完整条文，不能据此生成具体设计参数，也不能推断 CJJ 37 整部废止。

## 依据与读取位置

- [BATCH-001 采集计划](../working/road-profile/collection-plan.md)
- [RUN 日志](../working/road-profile/run-log.jsonl)
- [候选发现命中](../working/road-profile/discovery-hits.jsonl)
- [来源定位](../working/road-profile/source-locators.md)
- [首轮分析](../working/road-profile/road-profile-analysis.md)
- [规范来源图](../working/road-profile/standards-source-map.md)

## 缺失、限制与未知

- 网页搜索未返回总命中数和分页完整性；不能把显示结果数当作全部结果数。新增 RUN-001-06..08，保留所有原始运行记录，不覆盖前次失败。
- 本轮没有保存完整 HTML 原件；对代码使用稳定 Git blob SHA；标准全文未成功取得。
- 本轮没有独立复核者，因此没有声称 A1 已通过。
- `KNO-*` 记录仍是 candidate；没有 `DEC-*` 最终技术决定。

## 可以支持的用途

可支持：继续查证道路分类与 Profile 数据模型；建立标准关系图；为后续 Benchmark 定义字段与失败模式。

不能支持：直接复用 Street Generator 代码；把德国/OSM/SUMO 参数作为中国规范；宣称任何道路设计合规；冻结最终道路算法或生产架构。

## 后续动作与回流

当前计划仍由 [research-plan.md](../research-plan.md) 拥有。下一步是补齐 A1 所需来源覆盖、截断说明和独立复核，优先获取官方标准全文/状态与 Street Generator 许可信息；A1 通过后再做全局整理和选择性深入。
## Third-wave source-route update (RUN-001-09; 2026-10-26)

A direct GitHub route was used to inspect Street Generator's root file listing and exact `LICENSE` / `COPYING` paths, and to retrieve three SUMO issue reports (`#7615`, `#7119`, `#15013`). The issue reports provide concrete test patterns for hidden/default access semantics and distinguishing final topology from edit/audit history. The license check found no standard root license file and no README license statement; this leaves reuse permission unresolved rather than proving the project is unlicensed.

This route is a partial improvement in issue and license coverage, not an A1 pass. GitHub issue search was capped at topn=8 per query and did not expose total counts; original web-search runs still have `truncation=unknown`; official standard full text/status and an independent reproduction route remain unresolved. `BATCH-001` stays `in-progress`; A1 has not been executed.


## BATCH-002 — Sketch Calibration / Trace

- 已触达：OpenCV official geometry/contour docs、GDAL geotransform/GCP docs、Meta SAM 3/3.1 current repository and license、SamGeo README/LICENSE、Potrace official docs/paper，以及少量相邻 floorplan raster→vector 项目。
- 本地运行：`LOCAL-SKETCH-001` synthetic benchmark；保存机器结果与限制。
- 未完成：真实场地草图 benchmark、SAM3 本地 inference、独立人工 truth、A1。
- 搜索总量/分页完整性不可得，相关发现 run 保持 `truncation=unknown`。

## BATCH-002 closeout-for-review checkpoint

BATCH-002 now has a provisional real-benchmark data contract, an explicit case schema, a reproducible synthetic measurement baseline, current official/tool sources, and a limited discovery run for public paired site-plan sketch data. The public-data run found adjacent floor-plan datasets and a GIS/OSM masterplan dataset generator, but did not confirm a source that pairs real site-planning sketches with metric/project control, faithful manual Trace, semantic labels, and professional CAD/site geometry. This is recorded as a discovery gap, not a universal negative finding.

The batch is therefore `ready-for-A1 / unclosed`. There is no independent A1 reviewer in this research thread, so no A1 pass is claimed. Real Tier-B/Tier-C performance remains unknown.

## BATCH-003 — Building Footprint / Massing / 2D↔3D identity

A new exact acquisition batch has started to prevent the research from remaining stuck on roads or visual segmentation. The scope is `COV-10..11` plus `COV-13`, with limited links to planning constraints, downstream daylight/shadow, and change governance.

Initial sources reached:
- Building Regulariser: footprint regularization with principal-direction alignment, optional 45-degree handling, rectangle/circle conversion, simplification, and optional neighbor alignment; MIT code license observed.
- UrbGEN: parameterized massing under BCR/FAR/setback/height/orientation with multiple typology grammars; MIT license observed. It is treated as a design-space/grammar reference, not a planning-code authority.
- IfcOpenShell/Bonsai: official documentation confirms Object Placement and multiple representation contexts such as Plan/Footprint and Model/Body; repository licensing is component-specific/mixed and must be governed at dependency level.
- COMPAS: neutral AEC geometry/data infrastructure candidate, MIT main library.

No local regularization or IFC round-trip benchmark has yet been run in BATCH-003. The new batch remains `in-progress`; A1 has not been executed.

### BATCH-003 local validator baseline

`LOCAL-BLDG-001` was added using Shapely 2.1.2 to test generic 2D footprint vs projected-body consistency. It covers exact projection, placement drift, small rotation drift, and a stale-body case after an authoritative footprint revision. The stale case retained IoU ≈ 0.974 but still had a 0.6 m Hausdorff difference, reinforcing that representation dependency/revision state must be checked alongside overlap metrics. IfcOpenShell, Building Regulariser and COMPAS were not installed in the local runtime, so no claim is made about those implementations passing this benchmark.


## BATCH-003/004 主线回流（2026-10-26）

### BATCH-003 有界暂停

建筑 footprint 规则化第二波已形成规则化拒绝门、场地级拓扑合同和 `LOCAL-BLDG-002`。合成探针的 5 个断言通过，但没有运行 Building Regulariser/CartAGen/IfcOpenShell；早期搜索截断仍 unknown，真实 IFC round-trip 被当前环境阻断，因此 BATCH-003 保持 `bounded-paused / unclosed`，不宣称 A1 通过。详见 [建筑规则化报告](../working/building-massing/local-benchmark-002-regularization.md)。

### BATCH-004 首轮结果

已建立 CAD/BIM Compiler + Validator 采集计划，并完成 `LOCAL-CAD-003`：ezdxf 1.4.4 将合成 Profile 编译为 DXF，写入后重读，结构快照一致，`audit()` 未修复错误数为 0，自定义 Profile Validator 的 6 项断言通过。测试值全部为 synthetic fixture，不代表任何设计院标准。

尚未执行 LibreCAD/AutoCAD/FreeCAD 的独立 round-trip；IfcOpenShell/IfcTester 当前未安装；真实设计院模板与标准来源绑定未完成。`RUN-004-01` 的搜索截断为 unknown，因此 BATCH-004 保持 `in-progress / unclosed`。详见 [LOCAL-CAD-003](../working/cad-bim-validator/local-benchmark-003-dxf.md) 和 [Validator matrix](../working/cad-bim-validator/validator-matrix-v0.1.md)。


### BATCH-004 来源型规范 Profile 进展（2026-10-26）

新增官方标准样例 DB11/T 1948-2021《国土空间详细规划计算机辅助制图标准》。官方状态页将其标为现行，适用于北京市国土空间详细规划；本项目未把它选为默认标准。已将少量条款编码为来源型 Profile，并运行 `LOCAL-CAD-004`：图层名/RGB、米制单位、实体类型和拓扑子集检查通过，重叠面 mutant 被发现，但坐标参考因合成坐标而 blocked，所以完整合规状态保持 false。见 [规范来源映射](../working/cad-bim-validator/standards-profile-source-map-v0.1.md) 与 [LOCAL-CAD-004 报告](../working/cad-bim-validator/local-benchmark-004-db11t1948.md)。


### 主线回流：BATCH-004 bounded pause → BATCH-005 planned（2026-10-26）

BATCH-004 已完成 `LOCAL-CAD-003` 和 `LOCAL-CAD-004` 两个有界探针，但搜索截断 unknown、独立 CAD/BIM 环境缺失、真实设计院 Profile 未确认、IFC 运行阻断仍未解决，故状态调整为 `bounded-paused / unclosed`，不宣称 A1 通过。下一条主线转向 `COV-14..15` 环境分析与规划反馈；只研究可复现的日照/阴影/遮挡计算及其输入/版本依赖，不进入完整能耗/CFD。见 [BATCH-005 采集计划](../working/environment-analysis/collection-plan.md)。
