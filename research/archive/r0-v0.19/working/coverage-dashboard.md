# R0 Coverage Dashboard：端到端覆盖状态

**状态：** `provisional-draft`。这是主线控制视图，不是 Coverage 已完成声明。  
**更新时间：** 2026-10-27。  
**规则：** “已触达”只表示存在候选来源或校准记录，不等于正式首轮完成、独立验证或本地可用。

## 1. 能力线状态

| 能力线 | COV | 需要证明什么 | 当前候选技术/来源 | 真实状态 | 主要缺口 / 退出条件 |
|---|---|---|---|---|---|
| 输入校准与 Trace | `COV-01..04` | 尺度/坐标、语义提取、忠实向量化、置信度与人工确认 | OpenCV、GDAL、SAM 3/3.1、SamGeo、Potrace；相邻 floorplan 重建项目 | `BATCH-002 ready-for-A1 / unclosed`（官方来源 + 1 个本地合成 Benchmark + 真实 Benchmark 数据合同；A1 未执行） | Tier B/C 真实场地草图真值尚无；SAM3 未本地运行；数据合同已定义但尚无真实实测 |
| 几何清洗与道路拓扑 | `COV-05..07` | snap/node/split、无效几何修复、中心线候选与路线拟合 | Shapely/GEOS、CGAL、OSMnx、PyGeoOps、Clothoids | `calibration-only` | 无本地统一 Benchmark；medial axis 仅为候选算法，不能替代工程 alignment |
| 横断面、交叉口与道路面 | `COV-08..09`、`COV-21..23` | 类别/用途到 Profile、中心线与横断面、分级交叉口/过渡、道路面连续性 | Street Generator、Streetmix、SUMO、OSM；中国标准来源线 | `BATCH-001 unclosed / bounded-paused`（A1 尚未执行；不再阻塞其他独立 Coverage） | 道路 batch 尚未 A1；无可批准的中国数值参数；道路研究不得越过主线控制无限扩张 |
| 建筑与场地约束 | `COV-10..12` | footprint 保真/正规化、建筑类型候选、体量与规划约束 | Building Regulariser / CartAGen、UrbGEN、IfcOpenShell、COMPAS 等 | `BATCH-003 bounded-paused / unclosed`（源码/issue 复核 + LOCAL-BLDG-002 合成 Validator probe；A1 未执行） | 真实 IFC round-trip 受环境阻断；早期搜索截断 unknown；真实草图阈值未校准；不再无限扩张该子题 |
| 统一 2D/3D 与环境分析 | `COV-13..15` | 同一对象身份、坐标/placement、Footprint/Body/Axis、体量、日照/遮挡和形态反馈 | IfcOpenShell、Bonsai、Ladybug Tools、pvlib、Honeybee-Radiance、momepy | `COV-13 在 BATCH-003；COV-14..15 为 BATCH-005 bounded-checkpoint / unclosed` | E2E-FIXTURE-001 v0.3：太阳测试（v0.2+v0.3）44 项通过，DXF validator 12 项回归通过；3/3 传感器、2/2 Body 检查通过；8 个对象 ID、11 个 modelspace 实体、0 audit errors/fixes。v0.2 隔离复核发现的布局/Z/样式/天顶/布尔值/时数语义问题已在合成 Profile 范围内修复；外部 reviewer、独立 CAD/太阳模拟引擎、真实场地与法规阈值仍未验证 |
| CAD/BIM 输出、规则与验证 | `COV-16..19` | DXF 图层/线型/线宽/标注/块、IFC 语义、规则版本、独立回读与差异报告 | ezdxf、LibreCAD/libdxfrw、IfcOpenShell/IfcTester | `BATCH-004 bounded-paused / unclosed`（已有 AutoCAD 2022 core round-trip 首证据；同时发现 MultiPolygon contract、bulge/width false accept、entity-type mismatch exception 与 symbol-name case normalization） | 用户项目适用 Profile 未确认；LibreCAD/FreeCAD/GUI 视觉 QA 未执行；IFC 环境阻断；实现缺陷已转开发验收合同 |
| Agent 变更治理 | `COV-20` | Source→Trace→Intent→Professional→Massing 的 provenance、diff、锁定对象、局部修复 | Typed Intent/CAD-IR、规则引擎、变更 proposal 设计 | `partial synthetic vertical slice` | 共享 fixture 的 IDs/revisions 已经贯通环境结果与 DXF XDATA/manifest；仍无真实 Source/Trace、锁定对象局部修复、独立 CAD/IFC round-trip 或真实场地端到端证据 |

## 2. 端到端依赖与阻断

| 下游目标 | 关键上游 | 当前是否具备 | 不能跳过的检查 |
|---|---|---|---|
| 专业道路面 | Trace、Road Graph、类别/用途、Alignment、CrossSection、Junction | 部分候选，未实测 | 节点拓扑、中心线连续、道路面无缝/无自交、分类证据与参数来源 |
| 建筑 footprint 与体量 | Trace、对象身份、轮廓正规化、层数/高度/标高 | 候选阶段 | Source/Trace 保真、2D/3D 同 ID、footprint 与 Body 的投影一致 |
| 日照/遮挡反馈 | 场地坐标、北向、地点/时间、建筑高度、地形/遮挡体 | 只有工具候选 | 太阳位置输入、阴影几何、简单解析案例交叉验证；不直接推出法定日照结论 |
| 设计院规格 DXF | 专业几何、CAD-IR、图层/线型/标注配置、导出器 | 候选阶段 | 导出后由独立读者回读，检查实体类型、坐标、图层、线型、线宽、标注与块 |
| IFC / BIM | 对象身份、placement、2D/3D representation、语义类型 | 候选阶段 | 2D/3D 表示一致、单位/坐标、对象类型和 placement round-trip |
| 自动修复闭环 | Validator、对象依赖图、变更差异、锁定项 | 概念阶段 | 失败定位→局部修复→差异审计→重跑受影响测试→回归测试 |

## 3. 当前主线判断

- 当前没有任何一条能力线达到 `source-diversified` 或 `locally-saturated` 的正式状态。
- `calibration-only` 项目可用于选择后续来源路线，但不能直接晋升为架构决定。
- `BATCH-001` 是道路分类/Profile 的独立获取批次；其阻断不能被描述成“道路技术本身失败”，也不能成为无限期停止其余主线研究的理由。当前执行转为 `bounded-paused`，保留未关闭事实。
- `BATCH-002` 已进入 `ready-for-A1 / unclosed`：官方来源、许可状态、本地合成误差基准和真实 Benchmark 数据合同已具备；仍缺 Tier B/C 实测，因此不允许将合成误差写成生产精度。
- 全局 Coverage 的下一轮排序应同时考虑：对端到端闭环的依赖度、错误代价、证据不确定性、是否有可运行 Benchmark、是否会改变架构决策。当前尚无经校准的数值评分，不使用伪精确排名。`BATCH-005` 已形成有界检查点；用户本地复核和 AutoCAD core round-trip 已足以暴露验证器语义边界，因此 R0 不再继续实现 hardening。下一步转入 provisional architecture synthesis，同时把真实 paired site-sketch、IFC、独立太阳引擎、真实项目 Profile 与 GUI/视觉 QA 保持为后续独立 Gate。

## 4. 每轮结束必须更新

1. 哪些 COV 从未触达变为已触达，依据是哪一次真实 RUN？
2. 哪些 COV 只是校准，哪些具有可回读原件，哪些已有独立验证？
3. 当前主线中最靠前的阻断点是什么？它阻断哪一项端到端能力？
4. 局部研究是否仍会改变设计选择？若不会，是否应明确延期？
5. 下一动作是否符合 `research-plan.md` 的唯一下一动作和 Skill Gate？


## 5. Architecture Synthesis Phase 2 状态

- M01–M11 已形成 provisional module contracts；但不是 G5 最终架构。
- Canonical Site Model 被提升为当前最强 provisional truth owner；DXF/IFC/analysis 均按 derived representation 处理。
- Agent authority 已显式限制为 proposal/orchestration；confirmed design state 的写入需要 human authority 或已授权 deterministic rule。
- 开源项目已从“候选技术栈”重新归位为 core candidate / adapter / algorithm reference / external gate，减少单项目 lock-in。
- MVP-A 已收敛为简单 site sketch、少量 road/building、massing、fixed-time shadow、DXF、validator、stale/local rebuild；IFC/clothoid/independent environment/real Profile 为 mandatory architecture spikes。
- 下一步 `NEXT-R0-SYN-002` 不新增能力线，专门挑战上述架构假设。


## 6. Architecture Challenge 状态

- Verdict：`provisional_architecture_survives_with_amendments`。
- 通过的核心假设：独立 Canonical IR、Source/Trace evidence separation、Agent proposal-only、Rule/Profile separation、derived/stale model、human-in-the-loop MVP。
- 必须补入 R1 Foundation：Atomic ChangeSet、Proposal Snapshot、Profile/Rule 一等依赖、Conditional Rule Applicability、canonical/preview/external world separation。
- 当前允许：建立 R1 charter candidate 和 mandatory evidence/spike 计划。
- 当前不允许：宣称 G5 最终架构冻结、关闭未执行 A1、开始扩大自动规划/户型/复杂道路/完整法规功能。
