# BATCH-003 — Building Footprint Professionalization, Massing & 2D↔3D Identity

**当前状态：** `bounded-paused / unclosed`（第二波源码/issue 复核与合成 Validator probe 已完成；A1 未执行；真实 IFC 执行受环境阻断）  
**计划：** `CPL-BLDG-001-r1`  
**研究时点：** 2026-10-26  
**模式：** `technical-algorithm`  
**保证级别：** `high-assurance`

## 1. 本批决策问题

对于已经由 BATCH-002 产生、且仍保留 Source/Trace provenance 的建筑候选轮廓，怎样形成：

1. 不覆盖原 Trace 的 Professional Footprint 候选；
2. 能区分“应正交/对齐”和“真实不规则设计”的 regularization 机制；
3. 高度、层数、层高、进深、typology 等参数状态明确的早期 3D massing；
4. 同一建筑对象在 2D Footprint、3D Body 与对象 placement 之间保持 identity；
5. 可供后续日照/遮挡、规划约束、CAD/IFC 输出和局部修复使用的稳定对象模型。

## 2. 精确范围

- **主要 Coverage：** `COV-10`、`COV-11`、`COV-13`。
- **关联 Coverage：** `COV-12`（规划条件）、`COV-14`（日照/遮挡下游）、`COV-20`（变更/provenance）。
- **明确排除：** 户型自动生成、室内房间布局、立面/幕墙深化、结构/机电、法定日照结论、CAD 图层/线宽、最终 IFC 交付规则。

## 3. 首轮来源路线

| 路线 | 候选 | 研究问题 | 当前状态 |
|---|---|---|---|
| Footprint regularization | Building Regulariser、CartAGen/FER、相关论文 | 如何正交化/主方向化，又如何避免吞掉真实斜边、凹槽、院落与多方向建筑 | README/文档已触达；源码/失败样例尚未完成 |
| Parametric massing | UrbGEN | typology、BCR/FAR、setback、height 如何驱动体量；哪些参数是设计输入而非可猜默认值 | README/LICENSE 已读 |
| 2D/3D identity | IfcOpenShell / Bonsai | Object Placement、Footprint/Body/Axis context 如何表达同一对象；表示之间是否需要独立一致性验证 | 官方文档/仓库已读 |
| Geometry/data infrastructure | COMPAS | 是否适合作为独立 CAD 软件之外的几何/数据结构与序列化层 | 官方文档/README/LICENSE 已读 |
| 失败/反例 | regularization 过拟合、typology 强制套模板、2D/3D drift、高度猜测 | 用失败模式定义 Benchmark 与回退条件 | 初步建立，需独立样例/本地测试 |

## 4. 本批首先要证明的边界

### 4.1 Regularization 不是“建筑都修成直角”

建筑专业化必须支持至少三种结果：

- `preserve_trace`：保留原始不规则轮廓；
- `regularized_candidate`：提出正交/主方向/邻楼对齐候选；
- `needs_review`：无法判断是否应规则化时不自动决定。

任何 regularization 输出都必须保留对 Trace 的差异、面积/边界/拓扑变化和可回退关系。

### 4.2 Typology 是解释/生成候选，不是真值标签

I/L/U/Courtyard/塔式/板式等可以用于 massing grammar 或方案探索，但不能仅凭粗草图强行套入某个语法。`typology_state` 至少区分 `unknown | proposed | confirmed`。

### 4.3 高度与层数不能凭空生成

高度来源必须区分：

- designer confirmed；
- planning envelope；
- existing survey/GIS/BIM；
- inferred/estimated；
- unknown。

`estimated` 必须保留依据，不能冒充 confirmed。

### 4.4 IFC 多表示不等于自动一致

同一 IFC object 可以有 Footprint / Body / Axis 等 representation context；本项目仍需独立检查：

- 2D footprint 与 3D body 的 XY 投影；
- object placement；
- 单位/坐标；
- object ID / provenance；
- 修改一侧后另一侧是否需要重建。

## 5. A1 前置缺口

1. 尚未本地运行 Building Regulariser / CartAGen 等 regularization 路线。
2. 尚无设计草图中的“不规则是真实意图还是手抖”的人工 truth 标注。
3. UrbGEN 是方案生成工具，其 BCR/FAR/height 输入来源与中国项目规范尚未建立映射。
4. 已完成 `LOCAL-BLDG-001` 通用 2D↔3D projection 一致性测量基线；但本环境未安装 IfcOpenShell，尚未做真实 IFC Footprint→Body→round-trip。
5. 已确认 IfcOpenShell 仓库存在 GPL/LGPL 不同许可文本且 README 对组件分别标注许可；仍需在最终依赖方案明确到实际组件/分发方式。

## 6. 停止条件

本批推进到：

- regularization 的适用/拒绝/回退机制可定义；
- massing 参数来源状态可定义；
- 2D/3D identity 模型与一致性 Benchmark 可定义；
- 至少一个本地小型 footprint→massing/representation Benchmark 可复现，或明确记录环境阻断；
- 达到可提交独立 A1 的证据边界。

达到后必须返回 Coverage Dashboard，不自动进入户型生成或环境模拟深挖。


## 7. BATCH-003 bounded checkpoint（2026-10-26）

### 已新增证据

- 检查 Building Regulariser 源码、端到端测试、MultiPolygon 回归测试、当前 changelog 与 package metadata。
- 发现其端到端测试使用 IoU 下限 0.4、周长容许偏差 ±60%，但未在该测试中校验建筑组共享边/邻接图；这只能视作库内宽松几何 smoke test，不是设计院级验收门。
- Issue #8 的维护者回复明确说明当前处理是逐 polygon 独立执行、不理解相交建筑；当前 changelog 未列出其修复。Issue #5 有 v0.2.4 修复和 v0.2.5 MultiPolygon 测试记录，不再把它当作当前必现缺陷。
- CartAGen FER 提供另一条候选路线，但官方文档给出 6 m 最短边与 6 m² 面积过滤默认值，并假设近似正交建筑；这些默认值不能直接迁移到草图设计。
- 新增 `regularization-gate-v0.1.md`、`site-topology-contract-v0.1.yaml`、`local-benchmark-002-regularization.*`、`ifc-roundtrip-contract-v0.1.md`。

### LOCAL-BLDG-002 结果

5 个合成 Validator 检查通过。重要反例：相连建筑单体 IoU 均 0.995，但共享边 8 m 消失并产生 0.1 m 缝隙；两个独立对象被合并后全局 IoU 仍为 0.98。该实验只验证指标覆盖，不是规则化库实测。

### 未关闭原因

1. `RUN-003-01` 的广搜截断状态仍为 `unknown`，且 `RUN-003-05/06` 的搜索结果总量/分页边界不可得。按 Skill，不能自行宣称 A1 通过。
2. 本地无 IfcOpenShell；PyPI 访问因 DNS/网络解析失败，真实 IFC write/read 与第三方 round-trip 未执行。
3. 尚无 Tier B/C 真实设计草图，不能校准专业化的几何阈值。

因此本批暂停的是当前这条重复深挖动作，不是宣布建筑能力失败或关闭 BATCH-003。后续可在可安装 IfcOpenShell 的运行环境中执行 `ifc-roundtrip-contract-v0.1.md`，并由独立 A1 reviewer 复核精确批次。主线转回 Coverage Dashboard，优先处理更接近最终交付的 CAD/BIM Compiler + Validator（`COV-16..19`）。
