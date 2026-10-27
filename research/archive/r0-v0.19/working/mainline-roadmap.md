# R0 主线路线图与闭环控制

**状态：** `working-control`；用于防止研究分支漂移，不是正式架构决定。  
**时点：** 2026-10-27。  
**权威入口：** 根目录 `README.md` 与 `research-plan.md`；本文件是其主线视图，不覆盖项目计划。

## 1. 项目真正要完成什么

把设计者提供的建筑、道路、绿地等场地规划草图，转化为一份**保留原始意图、几何与拓扑正确、参数可追溯、具备 2D/3D 一致语义、可检查并可继续编辑的 CAD/BIM 场地模型**。

这不是“把某个局部画得更专业”，也不是收集尽可能多的 CAD 仓库。每项研究必须回答：它支撑端到端链条的哪一个能力、依赖什么上游事实、怎样被下游验证、失败时如何回退。

## 2. 产品技术主线

```text
设计输入 / 原始草图
  ↓
输入校准与控制基准（比例、坐标、方向、红线、已知尺寸）
  ↓
Source → Trace（忠实复刻，不擅自修正）
  ↓
语义与设计意图（道路、建筑、绿地、边界、特殊用途、待确认项）
  ↓
拓扑恢复与几何清洗（节点、边、闭合、共享边界、自交、容差）
  ↓
专业几何生成（道路中心线/交叉口/横断面/道路面；建筑 footprint/组团边界）
  ↓
统一对象身份与 2D/3D 场地模型（坐标、标高、层数、高度、厚度、地形）
  ↓
分析与约束（空间冲突、日照、遮挡、规划条件、适用规范）
  ↓
CAD / BIM 编译（DXF 图层/线型/线宽/标注/块；IFC 语义与表示）
  ↓
独立回读与验证（几何、拓扑、语义、格式、图层、3D 一致性）
  ↓
按差异局部修复 → 重跑受影响验证 → 生成新版本
```

### 不可破坏的原则

1. **双轨保真：** Source 与 Trace 永不被 Professional Geometry 覆盖；每次专业化都记录变更、理由和回退关系。
2. **先忠实、再专业化：** 首轮不强行把所有歪斜轮廓“修正规矩”；先保存原始几何，再生成带约束、可比较的专业化候选。
3. **确定性核心：** LLM/Agent 负责提议和解释；几何构造、规则执行、导出与验证由可测试模块承担。
4. **2D/3D 不分家：** footprint、对象身份、坐标/placement、高度/厚度必须保持关联；在 2D 拓扑可信后尽早生成轻量 massing，而不是等到最后才考虑高度与遮挡。
5. **未知必须显式：** 未校准尺寸、未确认道路用途、未验证标准、冲突约束均可保持 unknown / proposed / needs-review；不得静默填默认值或伪称合规。
6. **输出也要验证：** DXF 文件结构可读不等于设计正确；IFC 中存在 Axis/Footprint/Body 表示也不自动保证它们一致。必须回读并比较。

## 3. 与调研 Skill 主流程的闭环对应

本项目采用 `conduct-traceable-research` v0.2.2-field-test.4 的状态化调研方法。研究流程与产品技术流程相互关联，但不混为一条状态线。

| 调研阶段 | 研究动作 | 阶段出口 | 不允许的越级 |
|---|---|---|---|
| R0 章程 | 定义决策问题、范围、保证级别、边界与唯一下一动作 | 项目入口和计划一致 | 不因某个仓库好用就改写总目标 |
| R1 Coverage | 把端到端能力拆成 COV，并标注依赖与停止条件 | Coverage 保持 provisional 或经校准升级 | 不能从现有关键词倒推“已经完整” |
| R2–R3 获取 | 按精确 batch 执行高召回来源路线，保存 RUN/RAW/薄命中 | 真实获取边界可解释 | 不能把搜索摘要当作独立验证，也不能边搜边宣布覆盖完成 |
| R3.5 A1 | 独立复核一个精确 batch 的路线、截断、原件与动作边界 | 仅授权关闭该 batch 和相应整理动作 | A1 不等于技术结论或全项目完成 |
| R4 整理 | 在获准范围内去重、补全术语与 Coverage、决定下一轮广搜/深搜 | 有依据的全局缺口与优先级 | 不从一个局部 batch 直接冻结整体技术栈 |
| R5–R7 深化 | 对关键候选做源码/论文/失败案例/独立证据审查 | KNO / EVR / 有边界判断 | 不以项目自述或单一成功案例作为能力证明 |
| 架构综合 | 比较可组合的技术路线，记录 DEC 候选、代价和替代方案 | 可追溯的 provisional 架构 | 证据不足时不宣称最终选型 |
| Benchmark / 原型 | 用同一批代表性输入贯穿端到端链条 | 可重复测试、错误定位和回归 | 不用漂亮 Demo 替代失败测试 |
| 独立验证与交付 | DXF/IFC 回读、属性/几何差异、3D 与分析校验 | 受限但可验证的交付包 | 不把结构验证通过说成设计院/规范合规已通过 |

## 4. 全项目阶段门

| Gate | 目的 | 当前状态 | 通过条件（概要） |
|---|---|---|---|
| G0 项目章程 | 目标与范围固定 | `provisional-baseline` | 主线、排除项、时点和权限明确 |
| G1 覆盖校准 | 确保端到端能力不漏项 | `provisional-draft` | 各 COV 有问题、来源路线、依赖、停止条件和残余损失 |
| G2 首轮获取 | 让所有必要来源路线有可解释的执行边界 | `in-progress` | 精确 batch 分别完成 A1；失败/截断如实保留 |
| G3 全局整理 | 归并来源与覆盖缺口 | `not-started` | 必需的首轮 batch 处理完毕，按 Skill 授权整理 |
| G4 选择性证据深化 | 核实关键能力、反例、许可和适用边界 | `not-started` | 关键主张有原始来源、失败路线和适用性评价 |
| G5 架构候选决策 | 选择最小可行的组合，而非单项目神化 | `provisional-architecture-survives-with-amendments` | 备选、证据、风险、许可和重验条件齐全 |
| G6 端到端原型 | 验证真实闭环 | `not-started` | 同一场地样例可从输入走到 CAD/BIM 输出 |
| G7 独立 Benchmark | 证明错误能被发现、定位、修复和回归 | `not-started` | 预定义测试、独立回读、失败案例和回归结果可复现 |
| G8 交付与责任边界 | 明确实际可用范围 | `not-started` | 图纸规范、格式、版本、残余风险和人工审核点清晰 |

**关键限制：** Gate 是分层的。G2 通过不代表 G3–G8 通过；一个算法 Benchmark 通过不代表适用规范、CAD 图层和 BIM 语义自动通过。

## 5. Coverage 主线视图

Coverage 详细状态见 [coverage-dashboard.md](coverage-dashboard.md)。本项目把 COV 分成六条相互依赖的能力线：

1. **输入与 Trace：** `COV-01..04`。
2. **几何、路网与道路专业化：** `COV-05..09`、`COV-21..23`。
3. **建筑与场地约束：** `COV-10..12`。
4. **2D/3D 身份、分析与规划反馈：** `COV-13..15`。
5. **CAD/BIM 编译、规范与 Validator：** `COV-16..19`。
6. **Agent 变更治理与人工控制：** `COV-20`。

道路线是重要依赖，但不是唯一主线。道路 Profile 研究必须与建筑 footprint、统一对象身份、DXF/IFC 输出和 Validator 的依赖一起评估。

## 6. 防止局部研究无限扩张的规则

每个研究 batch 开始前必须写清：

- 唯一 decision question；
- 它服务的 COV 与直接下游能力；
- 本轮不回答的相邻问题；
- 必需来源角色与反例路线；
- 什么证据会改变设计选择；
- 结束时必须回到主线更新什么。

每个 batch 结束或受阻后，必须回到本文件和 Coverage Dashboard，回答：

1. 这批结果改变了哪个端到端能力的判断？
2. 哪些下游能力因此解锁或仍被阻断？
3. 是否出现更高风险、更靠近完整闭环的缺口？
4. 当前局部问题继续投入是否会改变架构/Benchmark？
5. 下一动作是继续、换来源路线、明确延期，还是转向下一个覆盖缺口？

同一失败访问路径不能原样反复重试；再次尝试必须改变来源角色/访问路径，并记录为什么预期能获得新证据。若外部访问限制持续存在，保留 `blocked/unknown` 与残余风险，不为了“完成感”重复检索或伪造 A1 通过。

## 7. 当前状态与下一动作

- 项目主线：已明确，但 Coverage 仍是 `provisional-draft`。
- 开源生态矩阵：90 个条目是生态目录，不是 90 个都已审查或可复用；24 个高关注项目也不等于最终候选。
- `BATCH-001` 道路语义/Profile：A1 尚未执行，当前按主线规则进入 `bounded-paused`；保留阻断，不继续把道路扩张成主线。
- `BATCH-002` 草图校准/语义候选/Trace：`ready-for-A1 / unclosed`；官方来源、许可路线、`LOCAL-SKETCH-001` 与真实 Benchmark 数据合同已具备。Tier B/C 真实场地草图真值仍缺。
- `BATCH-003` 建筑 Footprint / Massing / 2D↔3D identity：`bounded-paused / unclosed`，服务 `COV-10..11`、`COV-13`，关联 `COV-12/14/20`。规则化 Gate 与合成 Validator probe 已记录；真实 IFC 与真实草图阈值仍阻断。
- `BATCH-004` CAD/BIM Compiler + Validator：`bounded-paused / unclosed`，服务 `COV-16..19`。本地 DXF Profile 写入/回读已跑通；DB11/T 1948-2021 来源型 Profile 子集通过，但它只适用于北京详细规划，且坐标基准仍 blocked。第三方 round-trip、用户项目真实 Profile 和 IFC 运行仍未验证。
- `BATCH-005` 环境分析与规划反馈：`bounded-checkpoint / unclosed`，服务 `COV-14..15`。官方来源首轮获取及 `LOCAL-ENV-001` 已记录；外部模拟引擎未运行，不能宣称生产模拟验证。
- 本轮跨主线校准：新增检查 PyGeoOps centerline、IfcOpenShell representation、ezdxf audit 和 Ladybug solar/shadow 的官方资料；它们分别支撑局部能力，均未证明端到端闭环。
- 已有 BATCH-002 的入口合成误差基线与 BATCH-003 的 2D↔3D synthetic consistency baseline，但没有真实端到端原型、真实建筑 regularization Benchmark 或最终架构 DEC；没有任何中国道路/建筑参数被批准为可执行默认值。

### 唯一下一动作：`NEXT-R1-CHARTER-001`（R1 Charter Review / Evidence Planning）

Architecture Challenge 已完成，当前 provisional architecture 在 12 个失败场景下没有出现需要推倒重来的 truth-owner 或 module-boundary 矛盾，但发现 5 项 R1 Foundation 必须修正。

下一步只起草/复核 R1 技术研究章程与最小 evidence packages，不直接开始正式产品开发；未关闭的 R0 batch/A1 状态继续保留。

## 8. R1 Charter Review 回流（v0.14）

`NEXT-R1-CHARTER-001` 已完成。R1 不再等待所有现实证据一次性齐备，而采用两层推进：

1. **R1.0 Foundation** 可以先验证 stable identity、revision、authority、AtomicChangeSet、ProposalSnapshot、dependency/stale、structured validation；
2. **能力提升** 必须由对应 Evidence Package 解锁，不能从 synthetic Foundation test 外推真实能力。

五个 Evidence Packages：

- `EP-R1-SKETCH-001`：真实/半真实 site sketch；
- `EP-R1-ROAD-001`：road topology/alignment/profile；
- `EP-R1-IFC-001`：IFC identity round-trip；
- `EP-R1-ENV-001`：independent shadow engine；
- `EP-R1-PROFILE-001`：real project/design-office delivery profile。

### 当前唯一下一动作

`NEXT-R1-ENTRY-001`：只定义 R1.0 Foundation repo/package skeleton、typed contract tests 和 synthetic fixtures。仍不进入强 AI、复杂道路、生成式规划或大规模 UI。

## 2026-10-27 — Deployment boundary checkpoint

`NEXT-R1-RUNTIME-002` converged the R1 deployment candidate to:

`Agent Host -> MCP/CLI adapter -> Local Sidecar Runtime -> Foundation/Workers`

with a separate `Human Review UI -> Runtime` control plane and thin `AutoCAD .NET` / `FreeCAD Python` bridges. SQLite/WAL + content-addressed artifacts are the current local persistence candidate. This is a research checkpoint; actual wire-level MCP and CAD bridge execution remain gated.

Next: `NEXT-R1-DEPLOY-003` — service lifecycle/auth/session/control-plane handshake + first CAD bridge message exchange.
