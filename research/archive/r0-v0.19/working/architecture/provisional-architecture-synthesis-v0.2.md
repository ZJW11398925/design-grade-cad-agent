# Provisional Architecture Synthesis v0.2

**阶段：** R0 Architecture Synthesis Phase 2  
**状态：** `provisional-architecture-candidate`  
**目的：** 将已有研究从“能力/项目清单”收敛为可以指导 R1/MVP 立项的模块边界、数据真值、权限和开发切面。  
**不代表：** G5 最终架构选型、生产发布或法规合规。

## 1. 一句话架构

> 这是一个以 **Canonical Site Model / typed IR** 为设计真值、以 Source/Trace 为不可变证据、以 Agent 生成 ChangeProposal、以确定性几何/规则/编译/验证模块执行和校核、以 DXF/IFC/分析结果作为可失效派生表示的设计系统。

## 2. 两条平行平面

### Data Plane

```text
Source Evidence
  -> Trace Geometry
  -> Intent Candidate
  -> Professional Candidate
  -> Canonical Site Model
  -> Derived 3D / Analysis
  -> DXF / IFC / Renderings
```

### Control Plane

```text
Agent proposal
  -> authority check
  -> deterministic tool execution
  -> rule/profile resolution
  -> validator
  -> human confirm where required
  -> canonical commit
  -> stale propagation / local rebuild
```

**核心意义：** AI 不再“直接画图”，而是操作一套可审计的设计状态机。

## 3. 11 个模块的职责分界

完整接口见 [module-contracts-v0.1.md](module-contracts-v0.1.md)。

| 模块 | 真正拥有的责任 | 不允许承担的责任 |
|---|---|---|
| M01 Source & Calibration | Source、坐标/比例/北向证据 | 猜语义或真实工程尺寸 |
| M02 Trace & Semantic Candidate | 忠实 Trace 与语义候选 | 自动专业化 |
| M03 Geometry & Topology | 几何与拓扑确定性运算 | 决定设计意图 |
| M04 Road Design | RoadGraph、alignment、cross-section、junction proposal | 靠 LLM 猜道路参数 |
| M05 Building & Massing | footprint proposal、height/massing、site topology | 用指标重画设计者建筑 |
| M06 Canonical IR | **唯一 confirmed design truth + revision/dependency** | 依赖某一 CAD/BIM 格式作为数据库 |
| M07 Analysis | 特定输入/方法下的分析结果 | 宣称法规合规 |
| M08 Rule/Profile | 规则来源、适用性、参数与 override | 用模型记忆补标准 |
| M09 Compiler | canonical → DXF/IFC 忠实编译 | 在导出时“顺手优化”设计 |
| M10 Validator | 结构化验证与 coverage limits | 隐式修改设计 |
| M11 Agent | proposal、解释、工具编排、局部修复建议 | 直接写 confirmed truth |

## 4. Canonical IR 为什么不选 DXF / IFC / FreeCAD 文档本身

当前证据支持将 Canonical Site Model 独立出来：

1. Source/Trace/Intent/Professional 的 lineage 不是传统 CAD 文件的主要职责；
2. RoadGraph、alignment、cross-section、building state、uncertainty、human locks、analysis stale 等生命周期状态需要统一表达；
3. AutoCAD round-trip 已证明交付软件会产生语义等价但序列化不同的结果，说明 delivery representation 不适合作为不加治理的唯一真值；
4. IFC 对开放 BIM 和多 representation 很重要，但道路设计中间态、Trace evidence、Agent proposal 生命周期是否都应由 IFC 直接承载仍未被证明；
5. 只有独立 IR 才能让 DXF、IFC、分析器、未来其他 CAD 后端成为可替换 adapter。

因此：**IFC 是战略级交付/互操作格式候选，不是当前默认 canonical database。**

## 5. 权限模型

完整矩阵见 [agent-authority-matrix-v0.1.md](agent-authority-matrix-v0.1.md)。

架构上只允许三种提交路径：

### Path A：证据型提交
Source/Trace 作为 evidence revision 存档，不做专业判断。

### Path B：确定性低风险提交
已确认输入 + 已授权确定性规则，可以自动生成 derived representation，例如：
- confirmed footprint + confirmed height -> massing；
- confirmed canonical -> DXF；
- canonical revision change -> stale propagation。

### Path C：设计意图改变
Agent/算法只能生成 proposal，经过 diff + validator + human confirmation 才可写 canonical。

包括：
- 改道路连接关系；
- regularize 有意斜向建筑；
- 修改道路等级/用途；
- 设定未知建筑高度；
- 选择存在冲突的规范 Profile。

## 6. Open-source 不再是“技术栈名单”，而是角色插件

完整映射见 [open-source-capability-allocation-v0.1.md](open-source-capability-allocation-v0.1.md)。

推荐的架构思想是：

- **Canonical / revision / authority / dependency：自研。**
- **2D geometry：Shapely/GEOS 优先候选。**
- **复杂几何：保留 CGAL specialist boundary。**
- **RoadGraph / road semantics：自研对象 + OSMnx 思路。**
- **Centerline/alignment：PyGeoOps/Clothoids 作为可替换算法插件。**
- **DXF：ezdxf adapter。**
- **IFC：IfcOpenShell adapter。**
- **Environment：Ladybug/Honeybee/Radiance 等 adapter。**
- **AutoCAD/LibreCAD/FreeCAD/Bonsai：主要作为 external gate / secondary authoring，而不是真值 owner。**

这样可以避免未来某个库升级、许可策略或格式变化导致全系统重构。

## 7. R1/MVP 边界

完整定义见 [mvp-boundary-v0.1.md](mvp-boundary-v0.1.md)。

首版只证明一件事：

> 一张有可靠尺度/边界基准的简单场地草图，是否能经过人工确认的 Trace/Intent，形成少量道路和建筑的 Canonical Professional Site Model，产生简单 3D massing、固定时刻 shadow、DXF，并在修改一个道路节点/建筑高度后正确 stale、局部重建和回归验证。

首版**不做**：自动设计整座社区、完整户型、复杂交通工程、全国规范自动判定、完整施工图、全自动自治 Agent。

## 8. 推荐 R1 开发切片

### R1.0 Foundation
- Canonical IR；
- object/revision/dependency；
- geometry service；
- ChangeProposal / authority check；
- validator result contract。

### R1.1 Human-confirmed Source/Trace
- Source import；
- known scale/boundary；
- manual object confirmation；
- raw/simplified Trace。

### R1.2 Building vertical slice
- footprint candidate；
- preserve/regularize gate；
- confirmed height；
- massing；
- 2D/3D identity。

### R1.3 Road vertical slice
- RoadGraph；
- line/arc centerline；
- simple profile；
- T-junction；
- road surface。

### R1.4 Delivery / validation
- DXF compiler；
- semantic/profile validator；
- third-party CAD round-trip。

### R1.5 Analysis / dependency closure
- fixed-time shadow；
- building height change -> analysis/DXF stale；
- local rebuild/regression。

### R1.6 Architecture spikes
- IFC Footprint/Body/Placement round-trip；
- clothoid plugin boundary；
- real Project Profile subset；
- independent environment engine fixture。

## 9. R0 仍未解决，但不能继续无限扩张的问题

### 必须保留为高优先研究缺口
1. Tier B/C 真实场地草图 → Trace；
2. 道路 engineering alignment + 中国项目 Profile；
3. 真实 building regularization gate 校准；
4. 一份真实设计院/项目 Profile；
5. IFC 最小 round-trip；
6. 独立太阳/阴影引擎 fixture。

### 已经转开发验收，不应继续作为研究主线
- MultiPolygon 字段缺失；
- LWPOLYLINE bulge/width 漏检；
- entity type dispatch exception；
- symbol table name case normalization；
- validator structured failure hardening。

## 10. 当前架构决定强度

见 [provisional-decision-register-v0.1.md](provisional-decision-register-v0.1.md)。其中最强的 provisional decisions 是：

- Source/Trace 不可覆盖；
- Canonical Site IR 独立于 delivery format；
- Agent 不直接写 confirmed state；
- Rule/Profile 独立于 LLM；
- derived representations 全部有 dependency/stale；
- MVP human-in-the-loop。

道路 alignment 细节、Shapely/CGAL 分工、IFC 进入首版 UI 的程度等仍保持可重开。

## 11. Phase 2 结论

R0 现在已经具备一套**足以指导第一版系统拆分的 provisional architecture**。但还不具备“冻结最终技术栈”的证据基础。

下一轮不再继续扩展模块说明，而应对这套架构做 **Architecture Challenge / R0 Exit Review**：用失败场景反推模块边界，检查是否存在循环依赖、真值冲突、无法局部重建或被某个开源库锁死的地方；之后再判断是可以立 R1 charter，还是必须先补某一条高风险证据。
