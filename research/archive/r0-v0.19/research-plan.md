# Design-Grade CAD Agent：R0 当前计划

## 目标与边界

### decision_question

对于建筑与规划设计场景，哪些开源算法、几何内核、AEC/BIM/CAD 技术与规则执行方法，能够组成一条可追溯的 **Sketch → Professional Site Model → CAD/BIM** 转换链，使设计者仅提供建筑、道路、绿地等大体草图时，系统能够：

- 忠实保存原始设计意图；
- 将不严谨草图转化为拓扑正确、几何连续、可参数化的专业场地模型；
- 尽早生成具有建筑高度/厚度/层数等信息的 3D massing；
- 支持日照、遮挡及后续规划指标分析；
- 最终输出可编辑、可校核、可继续深化的 CAD / IFC；
- 为未来接入中国国标、行业标准、地方规定与设计院企业标准预留确定性规则层。

### mode

`technical-algorithm`

### assurance_level

`high-assurance`

### strategy

`breadth-depth-iterative`

### 时点与地域

- 技术生态时点：2026-10-26。
- 第一阶段优先研究国际开源生态；规范层以中国建筑/规划/道路设计场景为主要目标，但 R0 不宣称完成具体法规/标准合规。

### 本轮明确不回答

- 不直接解决住宅户型自动生成、室内平面深化、结构/机电专业深化。
- 不承诺自动生成可直接报审或施工的完整设计院成套图纸。
- 不把任何单一开源项目视为最终技术栈。
- 不在缺少真实控制尺寸/坐标时声称草图实现“物理世界一比一”。
- 不把 medial axis、spline、buffer 等单一算法直接等同于专业道路设计。

## 规范采用与权威

采用用户提供的 `conduct-traceable-research` v0.2.2-field-test.4 工作方法，并采用 `ctr-topic-layout-v0.1` 的主题级组织原则。

当前为候选研究阶段，不创建正式 governed package，不生成摘要绑定型 acquisition workspace，不计算无必要哈希。

## 当前工作与许可

本轮允许：

- 开放网络检索官方文档、官方仓库、论文与工程说明；
- 建立 Coverage、Benchmark、项目矩阵和候选知识记录；
- 保存普通查询日志和来源定位；
- 形成有限的“架构假设”，但必须标为 provisional。

本轮禁止：

- 将校准搜索直接写成最终技术选型；
- 将 README/项目自述直接写成“本地已验证能力”；
- 在未做 Benchmark 的情况下宣称某算法能稳定处理设计草图；
- 将某国/某城市道路规则直接外推为中国设计规范。

## Coverage（provisional-draft）

- `COV-01` 草图来源校准：比例、坐标、控制点、图像畸变与可追溯性。
- `COV-02` 草图语义提取：建筑/道路/绿地/红线/水体等区域和线对象。
- `COV-03` Trace Geometry：忠实向量化，不主动专业化。
- `COV-04` 几何清洗：去噪、简化、闭合、自交修复、snap、node。
- `COV-05` 道路拓扑恢复：node/edge、T/X/Y/环岛、断裂与伪连接处理。
- `COV-06` 道路中心线候选：轮廓→medial axis/centerline；单线草图→关键控制点。
- `COV-07` 工程路线拟合：直线/圆曲线/缓和曲线、G0/G1/G2 连续及约束拟合。
- `COV-08` 道路横断面与道路面：道路宽度、车行/人行/绿带等 profile 派生。
- `COV-09` 交叉口几何：offset、trim、fillet/turning geometry、polygon union。
- `COV-10` 建筑 footprint 正规化：正交/朝向/边界对齐/不规则轮廓保留策略。
- `COV-11` 建筑 typology/massing：板式、点式、L/U/院落等及高度/层数/进深参数。
- `COV-12` 规划条件与生成：FAR、BCR、退界、高度等约束进入候选方案。
- `COV-13` 2D↔3D 统一语义：Axis / Footprint / Body / Object Placement。
- `COV-14` 日照与遮挡：太阳几何、阴影、太阳时数及后续中国规范校核接口。
- `COV-15` 城市形态/路网评价：连通性、密度、形态指标和设计反馈。
- `COV-16` CAD 输出：DXF 图层、线型、线宽、块、标注、Model/Paper space。
- `COV-17` BIM 输出：IFC schema、类型、placement、2D/3D representation。
- `COV-18` 规范规则引擎：国家/行业/地方/设计院 profile 与优先级。
- `COV-19` Validator：几何、拓扑、语义、规范、跨格式 round-trip。
- `COV-20` Agent 交互与变更追踪：Source→Trace→Intent→Professional→Massing 的 provenance / diff / confidence。
- `COV-21` 道路层级与功能分类：区分城市路网等级、场地内部层级、服务功能、通行方式/权限及消防/服务等专用用途；明确分类方案的适用范围。
- `COV-22` 道路设计 Profile 与标准映射：类别/用途如何解析为设计速度、设计车辆、车道/横断面、转弯、坡度、交叉口等参数；记录标准版本、地域、项目阶段和来源。
- `COV-23` 分级道路的几何生成与过渡：按道路类别、用途和节点上下文生成中心线、横断面、交叉口、转弯空间及类别变化过渡，并验证无缝连接和规则冲突。

Coverage 当前仅为 `provisional-draft`，需要通过首轮来源和 Benchmark 校准后才能上卷。

## 来源与查询安排

### 第一轮来源角色

1. 官方 API / 技术文档：验证“能做什么”和精确接口。
2. 官方 GitHub：验证许可、维护状态、测试、架构与实现边界。
3. 原始论文/方法论文：理解几何算法和失败边界。
4. 独立 Benchmark / issue / failure report：后续验证项目自述之外的工程边界。
5. 中国官方标准/住建部/国家标准数据库：在规范分支单独开展，不与算法来源混池。

### 第一批候选技术族

- Sketch / Trace：OpenCV、GDAL、SAM 3/3.1、SamGeo、Potrace；RedrawAI / Raster2Seq / floorplan-to-vector 仅作相邻架构参考。
- 2D geometry/topology：Shapely/GEOS、CGAL。
- Road topology/centerline：OSMnx、PyGeoOps、Clothoids。
- Street profile/rules：Street Generator。
- Architecture/BIM：IfcOpenShell/Bonsai、FreeCAD BIM、COMPAS。
- Massing：UrbGEN。
- Analysis：Ladybug Tools、momepy。
- CAD export：ezdxf。

## 本轮交付与必需记录

已创建：

- `working/capability-map.md`
- `working/benchmarks.md`
- `working/project-matrix.md`
- `working/recording-model.md`
- `working/calibration/query-log.jsonl`（校准运行留痕；尚未启动正式 acquisition workspace）
- `reports/acquisition-summary.md`

最初联网检索属于 `BATCH-CAL-001` 校准获取；随后已分别建立 `BATCH-001`、`BATCH-002`、`BATCH-003`、`BATCH-004` 的正式 collection workspace，并建立 `BATCH-005` 的 collection workspace，当前为 bounded-checkpoint；已获取批次均保留 RUN/source locator 与候选知识记录。校准 RUN 继续保留为历史，不冒充正式 batch 证据。

## 接收与后续选择

批次治理约束：

- 每个 exact batch 必须服务明确 COV 与直接下游能力，并写出本批不回答的问题；
- Benchmark 必须覆盖失败模式，而不只是“正常案例”；
- 每个项目/算法都有明确研究问题，不因知名度而纳入；
- 项目自述、本地合成测试、真实样例、独立失败报告的证据等级必须分开；
- 一个 batch 进入 `ready-for-A1` 后，不得由同一研究线程自行宣称 A1 通过；可以在不做全局整理的前提下启动另一条独立 Coverage 获取线。

## 当前唯一下一动作（2026-10-27 更新）

`NEXT-R1-CHARTER-001` 已完成：R1 scope 维持，采用 **Foundation 先行 + Evidence Gate 分层解锁**。已建立五个最小证据包：`EP-R1-SKETCH-001`、`EP-R1-ROAD-001`、`EP-R1-IFC-001`、`EP-R1-ENV-001`、`EP-R1-PROFILE-001`，并形成 `r1-evidence-gate-register-v0.1.yaml` 与 R1 Charter Candidate v0.2。

新的唯一下一动作是 `NEXT-R1-ENTRY-001`：**R1.0 Foundation Entry Planning**。下一轮仍属于开发研究准备，只定义 repo/package skeleton、typed contracts、contract tests 与第一批 synthetic fixtures；不接入强 AI、不实现复杂道路、不扩 UI。

R1.0 允许在 R0 batch 尚未全部 closed 的情况下开始，因为 Foundation 主要验证 stable identity、revision、authority、AtomicChangeSet、ProposalSnapshot、dependency/stale 和 structured validation。五个 Evidence Packages 将分别阻止对应能力被提升为 `validated_for_scope`，但不要求在 Foundation 之前全部完成。

**R0 状态仍不是全局 closed。** R1 charter candidate 允许进入受限开发研究规划，不等于 G3/G5/A1/production/design-office compliance 获批。

## NEXT-R1-FOUNDATION-002

Before domain adapters begin, resolve the remaining Foundation-only research questions: deterministic canonical serialization/hash, dependency cycle detection, concurrent stale proposal/rebase semantics, schema migration/versioning and audit-event persistence. Do not start road/building/AI feature implementation merely because the current 12 contract tests pass.

## NEXT-R1-FOUNDATION-002 checkpoint — Agent integration boundary

Foundation v0.2 now adds deterministic canonical serialization/hash, dependency-cycle rejection, topological rebuild planning, audit JSONL, conservative rebase, field-path locks, explicit migration and a protocol-neutral AgentGateway. The expanded research suite is 21/21 passing.

The Agent integration candidate is no longer “Agent imports Foundation”. The preferred boundary is:

> Agent → thin MCP adapter → stateful DGCAD Runtime/Control Plane → protocol-agnostic Foundation Core → domain/adapters.

Human confirmation/unlock/profile promotion use a separate authenticated control-plane path. A thin Agent Skill may guide sequencing but cannot enforce authority. A2A is deferred until/unless DGCAD becomes an autonomous specialist Agent.

New unique next action: `NEXT-R1-RUNTIME-001` — research the minimal stateful runtime contract: durable project store, idempotency/retry, proposal lifecycle, job/artifact registry, restart-safe rebuild scheduling and a CLI/MCP parity spike. Do not begin road/building/AI adapters merely because Foundation v0.2 tests pass.


## 2026-10-27 — R0 v0.17 / NEXT-R1-RUNTIME-001 Stateful Runtime checkpoint

- 在 Foundation v0.2 之上建立独立 `dgcad_runtime` research prototype，保持 domain geometry/AI/CAD adapters 继续 out-of-scope。
- 新增 Project state persistence、Proposal / Approval / Job / Artifact / Idempotency registry，并用单一 hash-envelope + atomic replace 验证 restart/retry 语义；该存储仅用于研究合同，不是生产数据库决定。
- Human approval/unlock 从 Agent tool schema 中移除；Human Control Plane 在服务端建立绑定 proposal/change-set hash/scene revision/actor/expiry 的 Approval Grant。Agent 只能 `request_commit(proposal_id)`。
- CLI 与 MCP research shim 共享同一 AgentToolSurface；相同 idempotency key 跨 adapter 返回相同 Proposal，并共享相同 authority behavior。当前不宣称 wire-level MCP conformance。
- Runtime contract suite 经对抗性扩展后为 22/22 passing；连同 21 个 Foundation contracts，clean ZIP extraction 后 43/43 passing。
- 对抗性修复包括：transient empty job claim 不持久缓存、worker claim generation、restart 后旧 claim 失效、optimistic concurrent-writer CAS、保存前磁盘 payload integrity 重算、多对象 AtomicChangeSet、mixed unlock+confirm whole-set semantics。
- Runtime worker delivery 目前明确为 at-least-once；exactly-once 不宣称。
- 唯一下一动作改为 `NEXT-R1-RUNTIME-002`：部署边界研究（local sidecar / embedded CAD bridge / remote service）、local transactional store candidate、project single-writer lifecycle、actual MCP + CLI binding、Human Control Plane handshake 与 CAD bridge boundary。
- `research_complete=false`、`release_authorized=false` 保持不变。


## 2026-10-27 — R0 v0.18 / NEXT-R1-RUNTIME-002 Deployment Boundary checkpoint

- 四种部署模式已比较：embedded CAD plugin / local sidecar / remote service / hybrid。R1 推荐方向为 **hybrid local sidecar**：Runtime 独立持有 canonical truth，CAD 应用内只运行薄 bridge。
- 新增 SQLite/WAL + content-addressed artifact store research spike；验证 same-host transactional state、CAS stale-writer rejection、artifact dedup/tamper/reopen 与 CLI/shared-service parity。
- 合并 Foundation/Runtime 后 clean ZIP 复跑为 51/51 passing。
- MCP v2 官方文档支持 stdio 与 Streamable HTTP；当前更适合 already-running local sidecar 的候选为 loopback Streamable HTTP，stdio 保留给 host-launched subprocess。SSE 不用于新实现。
- 当前环境 `mcp` Python SDK 缺失，pip 安装受 DNS/network 阻塞，因此 actual MCP wire-level execution 仍是显式缺口。
- AutoCAD 2026 官方资料确认 ObjectARX/.NET 为宿主进程内扩展接口；因此 AutoCAD 侧优先薄 Managed .NET bridge，不让插件拥有持久 canonical state。FreeCAD Python/workbench 采用同样 adapter 原则。
- SQLite WAL 的 same-host 限制与 local-sidecar 模型一致，但不用于网络文件系统/多机共享权威状态。
- 新的唯一下一动作：`NEXT-R1-DEPLOY-003` — local service lifecycle + loopback auth/capability + project/session semantics + Human Review handshake + first real CAD bridge message exchange；MCP SDK 可用时补 wire-level conformance spike。
- `research_complete=false`、`release_authorized=false` 保持不变。


## 2026-10-27 — R0 v0.19 / NEXT-R1-DEPLOY-003 Deployment Lifecycle checkpoint

- 推荐 interactive owner 冻结为 DGCAD Desktop/Tray Launcher；Agent、Human Review、CAD bridge 均作为独立 client principal。
- 新增 sidecar discovery / pairing / session / lease / bridge lifecycle research prototype；全套 clean ZIP 复跑 65/65 passing。
- discovery 不携带凭证；pairing server-side role-bound、single-use；Agent pairing exchange 无 role selector，不能升级为 human_review。
- local HTTP prototype bind loopback only，Host/Origin validation 与当前 MCP SDK localhost DNS-rebinding guidance 对齐；但 prototype 自身不是 MCP。
- Human approve/unlock 通过独立 Human Review session；Agent token 实测被 Human endpoint 拒绝。
- project runtime lease 防 split-brain；expired takeover generation++；旧 runtime heartbeat 被拒绝。
- generic CAD bridge register/heartbeat/expiry 已执行；actual AutoCAD .NET / FreeCAD host exchange 因宿主不可用未执行。
- child-process probe 已验证真实 OS process + TCP loopback boundary，不仅是单进程类测试。
- MCP Python SDK 仍不可用，actual MCP transport/OAuth conformance 继续显式 blocked。

新的唯一主线动作：`NEXT-R1-MVP-001` — **Domain Slice Entry**。停止继续抽象部署层；从已经人工确认/可追溯的 Trace/Intent 输入开始，定义最小 Building/Road domain adapter，将 confirmed objects 写入 Canonical Site Model，并跑通 Proposal/Preview/Dependency/Validator。真实 AutoCAD bridge 作为 Windows/AutoCAD 环境的独立 Gate，不阻塞 domain MVP。

`research_complete=false`、`release_authorized=false` 保持不变。
