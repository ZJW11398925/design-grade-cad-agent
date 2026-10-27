# R1 Development Research Charter — Draft v0.1

**状态：** `draft-after-r0-architecture-challenge`  
**性质：** 开发研究章程，不代表正式产品开发已经开始。  
**前提：** R0 provisional architecture challenge verdict = `survives_with_amendments`。

## 1. R1 唯一目标

验证一条最小但真实可工作的闭环：

> 有可靠尺度/边界基准的简单场地草图 → human-confirmed Trace/Intent → Canonical Professional Site Model → 简单 road/building geometry → 3D massing → fixed-time shadow → DXF → independent validation → 修改一个设计参数 → stale/local rebuild/regression。

R1 的成功标准不是“识别模型很强”，而是**真值、身份、权限、依赖和验证闭环能够工作**。

## 2. R1.0 Foundation（最高优先级）

在接入任何强 AI 模型之前，必须建立：

- Canonical Site IR typed model；
- stable `object_id`；
- semantic / geometry / parameter revision；
- immutable Source/Trace references；
- `ChangeProposal` + `AtomicChangeSet`；
- `ProposalSnapshot`；
- authority/lock model；
- generalized dependency graph；
- stale propagation；
- structured `ValidationResult`；
- external reconcile contract。

**禁止捷径：** 不用 DXF handle、IFC GlobalId 或某个库对象地址作为 canonical primary key。

## 3. R1.1 Input / Trace Slice

只支持：
- 一个 raster sketch；
- 至少一个已知尺度或边界；
- manual / assisted object confirmation；
- building / road / green / redline 四类；
- raw trace + simplified trace；
- image-space / local metric 状态区分。

AI segmentation 可以作为 adapter，但不是 R1.1 的阻断项；即使全手工确认，也应先跑通数据模型。

## 4. R1.2 Building Vertical Slice

- 2–3 buildings；
- rectangle / L / U；
- preserve / regularize_candidate / needs_review；
- confirmed height；
- extrusion massing；
- building footprint ↔ body projection validation；
- height change 只 stale massing/analysis/相关 delivery，不错误 stale Source/Trace。

### Mandatory evidence

至少 1 个真实设计草图 building case，用于测试 regularization gate。

## 5. R1.3 Road Vertical Slice

- RoadGraph；
- primary/secondary/service 作为**项目级语义标签**，不冒充法定全国道路等级；
- line / circular arc alignment；
- simple cross-section profile；
- T junction；
- road surface；
- node move 使用 AtomicChangeSet；
- junction + adjacent edges 共同验证后 commit。

### Mandatory evidence

需要 2–3 个 targeted road fixtures，至少包含：T junction、near-parallel roads、手绘 S curve。中国道路工程 Profile 仍是研究 Gate，不在 R1.3 默认填未经核验参数。

## 6. R1.4 DXF / Validation Slice

- single frozen DXF target version；
- minimal Project Profile；
- ezdxf 或等价 compiler adapter；
- independent semantic validator；
- DEV-CAD-001..008 回归；
- third-party CAD round-trip 至少 1 个；
- `pass_with_serialization_differences` 与 semantic failure 分开。

用户本地复核中已经暴露的 MultiPolygon、bulge/width、entity dispatch 和 symbol-name case 作为硬回归，不再重新研究其必要性。

## 7. R1.5 Analysis / Stale Closure

- fixed-time direct shadow；
- location/north/time/height/context 显式输入；
- analysis result 绑定 dependency hash；
- height/placement/profile/method 变化正确 stale；
- proposal preview 可运行 analysis，但结果为 `preview_only`。

### Mandatory spike

使用一个独立太阳/阴影引擎对固定 fixture 做交叉验证；不宣称法规日照合规。

## 8. R1.6 Architecture Spikes

这些 spike 不一定进入首个 UI，但必须证明架构没有堵死未来：

1. **IFC spike**：building Footprint + Body + Placement + identity round-trip；
2. **Clothoid spike**：alignment solver adapter 可替换 line/arc solver 而不改 canonical RoadObject；
3. **Real Project Profile spike**：一份真实院标/项目模板的最小规则子集；
4. **External reconcile spike**：修改外部 DXF/IFC，产生 diff + ChangeProposal，而不是直接覆盖 canonical。

## 9. R1 不做

- 自动生成完整社区方案；
- 户型/室内布局；
- 结构/机电；
- 复杂道路交通工程与完整纵断面；
- 全法规自动合规；
- 完整 DWG production authoring；
- 多人实时协同；
- 施工图自动生成；
- 自主 Agent 无人工确认的大范围设计修改。

## 10. R1 Evidence Gates

| Gate | 最低要求 |
|---|---|
| `R1-G01 Identity` | 同一对象跨 canonical/3D/DXF 可追踪 |
| `R1-G02 Authority` | proposal/confirm/lock 越权测试通过 |
| `R1-G03 Dependency` | building height + road node 两类 change 的 stale/local rebuild 正确 |
| `R1-G04 Geometry` | T junction、building hole/concavity、invalid geometry fail closed |
| `R1-G05 Delivery` | DXF third-party semantic round-trip |
| `R1-G06 Preview` | uncommitted ProposalSnapshot 可预览但不污染 current state |
| `R1-G07 Real Case` | 至少 1 个非纯合成 site sketch 贯通主要链路 |
| `R1-G08 Architecture Spikes` | IFC + external analysis + real Profile 至少完成最小验证 |

只有这些 Gate 基本成立后，才讨论更强自动识别、更复杂道路或生成式规划。

## 11. 与未关闭 R0 研究的关系

R1 draft 不宣称 R0 所有 acquisition/A1 已关闭。以下证据仍可并行补充：
- BATCH-002 Tier B/C paired sketch；
- road alignment/Profile；
- real building regularization threshold；
- IFC/env/Profile spikes。

它们若改变 truth model/module boundary，则回开 architecture decision；若只影响实现参数，则进入 R1 benchmark/config，不重启整个 R0。
