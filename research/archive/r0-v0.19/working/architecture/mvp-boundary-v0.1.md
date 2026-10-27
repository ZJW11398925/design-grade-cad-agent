# R1 / MVP 边界收敛 v0.1

**状态：** `provisional-r1-scope`  
**目标：** 定义第一版真正需要证明的闭环，防止“AI CAD”项目在开发开始前重新膨胀。

## 1. MVP 的唯一产品问题

> 给定一张**具有至少一个可靠尺度/项目边界基准**的简单场地草图，系统能否在保留 Source/Trace 的前提下，让设计者确认少量道路、建筑和绿地对象，并将其转成可追溯、可编辑、可验证的 Professional Site Model，生成简单 3D massing 与 DXF；当设计参数变化时，只重建受影响的下游结果，并能解释变化来源？

这比“自动设计一个小区”窄得多，但它能验证整个架构是否成立。

## 2. MVP-A：必须包含

### Input / Trace
- 单张 PNG/JPG/PDF 栅格化页面；
- 一个已知尺寸或已知项目边界；
- Source 原件不可变保存；
- 交互式确认 building / road / green / redline；
- raw Trace 与 simplified Trace 分开。

### Road
- 1 条主要场地道路 + 1 条支路；
- T 路口为必测，X 路口为建议；
- RoadGraph；
- line + circular arc centerline；
- 显式选择的简化 CrossSection Profile；
- centerline → road surface；
- 不要求自动处理复杂环岛、互通、完整竖曲线。

### Building
- 2–3 栋建筑；
- 矩形/L/U 三类简单 footprint；
- preserve / regularize-candidate / needs-review；
- 高度必须人工输入或确认；
- footprint → simple extrusion massing；
- 2D/3D 同 ID、同 placement。

### Canonical / Governance
- stable object ID；
- geometry / semantic / parameter revision；
- lock；
- ChangeProposal；
- diff；
- stale propagation；
- local rebuild。

### Analysis
- 固定日期时间的直接阴影 baseline；
- 输入必须有 north/location/time/height 状态；
- 不宣称法规日照合规。

### Delivery
- DXF R2010（或开发时冻结单一版本）；
- layers / linetypes / lineweights / labels 的最小 Project Profile；
- manifest/XDATA 或等价对象映射；
- 独立 validator；
- 至少一个第三方 CAD round-trip Gate。

## 3. MVP-B：首版前的 mandatory spike，但可不进入首个可用 UI

- IFC：一个 building 对象同时写 Footprint + Body + Placement，并回读检查 identity；
- Clothoid：验证 Road Alignment 插件接口是否能在不改 Canonical IR 的情况下替换 line/arc solver；
- 独立环境引擎：用固定 fixture 对照一个真实太阳/阴影引擎；
- project Profile：接入一份真实项目/院标的小型规则子集。

这些 spike 的目的不是扩功能，而是验证架构没有把未来关键能力堵死。

## 4. 明确推迟到 MVP 之后

- 自动住宅户型与室内空间；
- 结构、机电、景观详图；
- 复杂道路纵断面、超高、完整交叉口交通工程；
- 全国/全城市法规自动判定；
- 自动规划方案生成与多目标优化；
- 完整 DWG 原生编辑；
- 自动生成报审/施工图；
- 多人实时协作；
- 大规模城区 GIS；
- BIM 细部构件。

## 5. MVP 成功不是“图看起来像 CAD”

必须同时通过：

1. **Fidelity**：Source/Trace 可以回看，professionalization 有 diff；
2. **Topology**：T junction、建筑洞/组件、道路连接正确；
3. **Identity**：2D/3D/DXF 中 object ID 可追踪；
4. **Authority**：机器候选与 human confirmed 明确区分；
5. **Staleness**：建筑高度/道路节点变化后旧分析和输出被正确失效；
6. **Local rebuild**：只重建受影响对象/表示；
7. **Interoperability**：第三方 CAD round-trip 通过 semantic policy；
8. **Failure visibility**：错误返回结构化 issue，不静默接受、不未处理崩溃。

## 6. R1 的推荐开发顺序

```text
R1.0 Canonical IR + revision/dependency + geometry service
  ↓
R1.1 Manual Source/Trace import + object confirmation
  ↓
R1.2 Building footprint + massing vertical slice
  ↓
R1.3 RoadGraph + simple centerline/profile/T-junction
  ↓
R1.4 DXF compiler + validator + third-party round-trip
  ↓
R1.5 Shadow baseline + stale/local rebuild
  ↓
R1.6 IFC / clothoid / real Profile architecture spikes
```

理由：先证明“对象、真值、revision、validation”成立，再增加 AI 自动识别。否则模型越强，错误越难治理。

## 7. MVP 退出条件

满足以下条件才允许扩大范围：

- 至少 3 个预定义场地 fixture 全链条通过；
- 至少 1 个 fixture 来自真实设计草图而非纯合成；
- 修改一个道路节点和一个建筑高度后，stale/local rebuild 可复现；
- DXF 经至少 1 个第三方 CAD 往返后语义保持；
- 所有关键对象可以回答“来自哪里、改过什么、谁确认、依赖什么规则”；
- 已知 unsupported case 会被 block/needs-review，而不是伪装成功。
