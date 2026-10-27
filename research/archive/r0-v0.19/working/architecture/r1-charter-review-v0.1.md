# R1 Charter Review v0.1

**状态：** `reviewed-provisional-charter`  
**性质：** R1 开发研究章程复核；不等于正式产品发布计划。  
**基线：** R0 provisional architecture + A-01..A-05 amendments + Canonical Site IR v0.3。

## 1. 复核结论

R1 scope **维持**，但采用“Foundation 先行 + Evidence Gate 分层解锁”的进入方式。

R1 不以“自动化程度”作为首要成功标准，而以以下闭环是否成立作为核心：

> Source/Trace evidence → human-confirmed Intent → Canonical Site Model → deterministic professional geometry → derived 3D/analysis/delivery → independent validation → ChangeSet → stale/local rebuild → regression。

五个外部/真实证据包不会阻止 R1.0 Foundation 开始，但会阻止对应能力被提升为 `validated_for_scope` 或写入产品承诺。

## 2. R1 各阶段进入条件

| 阶段 | 可以立即开始 | 在证据不足时允许做到 | 证据 Gate 通过前禁止宣称 |
|---|---|---|---|
| R1.0 Foundation | 是 | typed IR、ID/revision、ChangeSet、Preview、dependency、validator contract | production-ready architecture |
| R1.1 Input/Trace | 是 | manual-assisted trace、候选分割、review queue | real-sketch automatic trace reliability |
| R1.2 Building | 是 | preserve/regularize candidate、confirmed-height extrusion | automatic professionalization works on real design sketches |
| R1.3 Road | 是（仅项目语义 + 简单几何） | RoadGraph、line/arc、T junction、explicit project profile | China engineering road compliance / general alignment quality |
| R1.4 DXF/Validation | 是 | frozen DXF profile、compiler、semantic validator | broad AutoCAD/LibreCAD/FreeCAD interoperability |
| R1.5 Analysis | 是 | fixed-time direct-shadow baseline、dependency/stale | production daylight/radiation or regulation compliance |
| R1.6 Spikes | 是，按证据包推进 | IFC、external analysis、real Profile、external reconcile | production BIM / regulation automation |

## 3. Evidence Package 原则

每个 Evidence Package 必须：

1. 保留**原始输入**与不可变 hash，而不是只保存截图或最终指标；
2. 明确 ground truth / human judgment 的来源与不确定性；
3. 同时保存成功例与失败/边界例；
4. 使用预先声明的 metrics，但不在没有基线分布前虚构统一数值阈值；
5. 失败必须区分：模型失败、几何失败、规则适用性失败、validator failure、evidence insufficiency；
6. 产生可复跑的 manifest、方法版本、环境版本和结果；
7. Gate verdict 必须是 `pass_for_scope / conditional / fail / insufficient_evidence` 之一；
8. 通过只授权对应 scope，不向相邻能力外推。

## 4. 五个最小 Evidence Packages

- `EP-R1-SKETCH-001`：真实/半真实场地草图 → Calibration/Trace/Intent。
- `EP-R1-ROAD-001`：道路拓扑、简单 alignment、Profile 适用性。
- `EP-R1-IFC-001`：Building Footprint/Body/Placement/identity round-trip。
- `EP-R1-ENV-001`：独立太阳/阴影引擎交叉验证。
- `EP-R1-PROFILE-001`：真实设计院/项目交付 Profile 的最小规则子集。

它们的详细合同见 `evidence-packages/`。

## 5. Gate 与 Evidence Package 的映射

| R1 Gate | 主要证据 | Gate 意义 |
|---|---|---|
| R1-G01 Identity | Foundation tests + EP-R1-IFC-001 + DXF | 对象跨 canonical/derived/external 可追踪 |
| R1-G02 Authority | Foundation adversarial tests | Agent/engine 不能绕过 confirm/lock |
| R1-G03 Dependency | building/road mutation fixtures + EP-R1-ENV-001 | stale/local rebuild 正确 |
| R1-G04 Geometry | road fixtures + building concavity/hole fixtures | 几何/拓扑 fail closed |
| R1-G05 Delivery | DXF third-party round-trip + EP-R1-PROFILE-001 | 输出语义与 Profile 可验证 |
| R1-G06 Preview | ProposalSnapshot tests | preview 不污染 canonical current |
| R1-G07 Real Case | EP-R1-SKETCH-001 | 至少一个非纯合成输入贯通主要链路 |
| R1-G08 Architecture Spikes | EP-R1-IFC-001 + EP-R1-ENV-001 + EP-R1-PROFILE-001 | 架构没有堵死 BIM/分析/真实交付规则 |

## 6. 当前已拥有的证据与仍缺的证据

### 已拥有

- Source/Trace/Professional 分层原则与合成 trace 误差基线；
- Building regularization 的源码/Issue failure evidence；
- RoadGraph / Profile / junction 的候选架构研究；
- DXF compiler/validator 合成回归与一次用户侧 AutoCAD core-engine round-trip；
- fixed-time shadow 合成基线与 dependency/stale probe；
- Canonical/Preview/External world 隔离和 ChangeSet architecture challenge。

### 仍缺

- 真实设计者场地草图与人工 trace/intent 真值；
- 足够接近真实设计的 road fixtures 与已核验项目道路 Profile；
- 实际 IfcOpenShell（或等价 IFC stack）写出/回读运行证据；
- 独立太阳/阴影引擎对同一 fixture 的结果对照；
- 真实项目/设计院的图层、线型、线宽、文字/标注、打印或交付规则资产。

## 7. R1 Scope Freeze

在上述 Evidence Packages 完成前，R1 不扩展到：

- 自动完整社区方案生成；
- 户型、结构、机电；
- 全国法规自动合规；
- 复杂交通工程、完整纵断面；
- 全自动 Agent 大范围修改；
- DWG 原生生产 authoring；
- 施工图自动生成。

新增功能只有在它直接服务 R1-G01..G08 或 Evidence Package 时才可进入 R1 backlog。

## 8. Charter Verdict

`r1_charter_scope_approved_for_development_research`

含义：允许进入 R1.0 Foundation 和受限 vertical slices；**不**代表任何能力已经生产可用，也不关闭 R0 未完成的 A1/acquisition 事实。

### 下一动作

`NEXT-R1-ENTRY-001`：建立 R1.0 Foundation 的最小 repo/package skeleton 与测试清单，但只实现 IR/revision/authority/dependency/preview/validation contracts，不接入强 AI、不实现复杂道路或 UI。
