# Design-Grade CAD Agent：R0 Sketch → Professional Site Model

工作空间版本：**R0 v0.19**（研究工作区快照，不是生产发布）

## 当前结论

本主题已于 2026-10-26 正式启动。当前处于 **R0/R1 覆盖校准 + 多批次首轮获取阶段**，尚未形成正式技术选型、规范合规结论或生产架构决定。

已经冻结的工作假设：

1. 原始草图不能被“专业化结果”覆盖；系统必须同时保存 Source / Trace / Intent / Professional Geometry / 3D Massing 的可追溯关系。
2. 建筑与规划场景不能把 3D 推迟到末端；当 2D 拓扑和 footprint 基本可信后，应尽早生成轻量 3D massing，用于高度、遮挡、日照等反馈。
3. 道路应优先建模为 **拓扑图 + 中心线 + 横断面/边界派生**，而不是直接让 Agent 画两条道路边线。
4. LLM 不直接拥有最终几何真值；几何、规范、导出和校核应由可测试的确定性模块承担。
5. 道路分类必须先于设计 Profile 解析，但不能被压缩为“宽度=等级”的单标签判断；网络层级、服务功能、通行权限、特殊用途和物理横断面需要分开建模。

以上为当前研究假设，不等于已验证架构决定。

## 当前状态（2026-10-27）

`BATCH-001` 道路语义/Profile：`bounded-paused / unclosed`，A1 未执行；不再让道路局部阻断整个项目。

`BATCH-002` 草图校准/语义候选/Trace：`ready-for-A1 / unclosed`。已完成官方来源与许可核查、`LOCAL-SKETCH-001` 合成误差基准、真实 Benchmark 数据合同和公开 paired site-sketch 数据缺口的有限检索；尚无 Tier B/C 真实场地草图实测。

`BATCH-003` 建筑 Footprint / Massing / 2D↔3D identity：`bounded-paused / unclosed`。已完成源码/issue 复核、规则化拒绝门和 `LOCAL-BLDG-002` 合成 Validator probe；真实 IFC round-trip 受当前环境 DNS/安装限制，A1 未执行。

`BATCH-004` CAD/BIM Compiler + Validator：`bounded-paused / unclosed`。在既有 ezdxf 合成测试之外，用户已完成一轮 AutoCAD 2022 core engine 打开/保存/回读：主要对象、单位和实体数量保持，但暴露出线型名大小写规范化差异；同时本地复核发现 MultiPolygon 字段契约、LWPOLYLINE bulge/width 漏检及 entity-type mismatch 异常。研究阶段不继续修实现，这些问题已转入开发验收合同。仍未接入真实设计院 Profile。

新增来源型规范样例：DB11/T 1948-2021（仅限北京详细规划）已抽取少量条款并运行 `LOCAL-CAD-004`。可测子项通过，重叠面 mutant 被发现，但坐标基准未建立，因此完整合规状态仍为 false。

`BATCH-005` 环境分析与规划反馈：`bounded-checkpoint / unclosed`。v0.3 内部回归仍保留，但用户本地复核结论维持 `conditional`。AutoCAD core round-trip 已提供首个第三方 CAD 互操作证据，同时揭示 validator 的真实语义缺口。该分支现冻结为研究证据，不再在 R0 继续 hardening；独立太阳模拟引擎、真实草图、IFC 和真实项目 Profile 仍未完成。

BATCH-001 主要入口：
- [BATCH-001 采集计划](working/road-profile/collection-plan.md)
- [首轮道路语义/Profile 分析](working/road-profile/road-profile-analysis.md)
- [候选 Profile schema](working/road-profile/road-profile-schema-v0.1.yaml)
- [中国规范来源图](working/road-profile/standards-source-map.md)
- [候选知识记录](working/road-profile/knowledge-candidates.md)
- [获取情况报告](reports/acquisition-summary.md)

BATCH-002 入口/Trace：
- [采集计划](working/sketch-trace/collection-plan.md)
- [第一轮分析](working/sketch-trace/sketch-trace-analysis.md)
- [候选对象 schema](working/sketch-trace/trace-object-schema-v0.1.yaml)
- [本地合成 Benchmark](working/sketch-trace/local-benchmark-001.md)
- [真实 Benchmark 数据合同](working/sketch-trace/real-benchmark-contract-v0.1.md)
- [Benchmark Case schema](working/sketch-trace/benchmark-case-schema-v0.1.yaml)
- [候选知识记录](working/sketch-trace/knowledge-candidates.md)

BATCH-003 建筑/3D：
- [采集计划](working/building-massing/collection-plan.md)
- [首轮分析](working/building-massing/building-massing-analysis.md)
- [候选 BuildingObject schema](working/building-massing/building-object-schema-v0.1.yaml)
- [2D↔3D 本地合成一致性 Benchmark](working/building-massing/local-benchmark-001-identity.md)
- [候选知识记录](working/building-massing/knowledge-candidates.md)
- [规则化 Gate](working/building-massing/regularization-gate-v0.1.md)
- [场地级拓扑合同](working/building-massing/site-topology-contract-v0.1.yaml)
- [LOCAL-BLDG-002 结果](working/building-massing/local-benchmark-002-regularization.md)
- [IFC round-trip 测试合同](working/building-massing/ifc-roundtrip-contract-v0.1.md)

- [CAD/BIM Compiler + Validator 采集计划](working/cad-bim-validator/collection-plan.md)
- [CAD-IR provisional contract](working/cad-bim-validator/cad-ir-contract-v0.1.yaml)
- [Validator 分层矩阵](working/cad-bim-validator/validator-matrix-v0.1.md)
- [LOCAL-CAD-003 DXF round-trip 结果](working/cad-bim-validator/local-benchmark-003-dxf.md)
- [Profile rule contract](working/cad-bim-validator/profile-rule-contract-v0.1.yaml)
- [DB11/T 1948-2021 来源映射](working/cad-bim-validator/standards-profile-source-map-v0.1.md)
- [DB11/T 1948-2021 来源型 Profile 摘录](working/cad-bim-validator/db11t1948-profile-extract-v0.1.yaml)
- [LOCAL-CAD-004 来源型 Profile 结果](working/cad-bim-validator/local-benchmark-004-db11t1948.md)
- [BATCH-005 环境分析采集计划](working/environment-analysis/collection-plan.md)
- [BATCH-005 来源定位（首轮已获取）](working/environment-analysis/source-locators.md)
- [BATCH-005 候选知识记录](working/environment-analysis/knowledge-candidates.md)
- [BATCH-005 官方来源图](working/environment-analysis/source-map-v0.1.md)
- [BATCH-005 Benchmark 合同](working/environment-analysis/benchmark-contract-v0.1.md)
- [BATCH-005 依赖合同](working/environment-analysis/analysis-dependency-contract-v0.1.yaml)
- [BATCH-005 结果 Schema](working/environment-analysis/environment-analysis-result-schema-v0.1.yaml)
- [LOCAL-ENV-001 运行报告](working/environment-analysis/local-benchmark-001-solar-shadow.md)
- [跨流水线差距审计](working/cross-pipeline-gap-audit-v0.1.md)
- [共享 E2E v0.2 垂直切片报告](working/e2e-integration/local-e2e-fixture-slice-002.md)
- [E2E v0.2 对抗性审查报告（历史）](working/e2e-integration/adversarial-review-report-v0.2.md)
- [v0.2 隔离复核报告与新增缺陷](working/e2e-integration/reviews/independent-review-report-v0.3.md)
- [v0.3 修复与回归报告](working/e2e-integration/local-e2e-fixture-slice-003.md)
- [v0.3 机器可读测试结果](working/e2e-integration/reviews/hardening-results-v0.3.json)
- [v0.3 合成 DXF Profile](working/e2e-integration/synthetic-dxf-profile-v0.3.json)
- [v0.3 DXF 验证器回归测试](working/e2e-integration/test_dxf_validator_v0_3.py)
- [v0.2 外部复核清单](working/e2e-integration/independent-review-checklist-v0.2.md)
- [对抗性测试结果](working/e2e-integration/adversarial-review-results-v0.2.json)
- [E2E fixture → CAD-IR → DXF](working/e2e-integration/README.md)
- [共享场景 JSON（v0.2 / r2）](working/e2e-integration/site-fixture-v0.2.json)
- [CAD-IR 实例 JSON（v0.2）](working/e2e-integration/site-fixture-cad-ir-v0.2.json)
- [DXF 回读清单 JSON（v0.2）](working/e2e-integration/site-fixture-v0.2-dxf-manifest.json)
- [v0.1 独立复核清单（历史版）](working/e2e-integration/independent-review-checklist-v0.1.md)
- [v0.1 独立复核清单/哈希（历史版）](working/e2e-integration/independent-review-manifest-v0.1.json)
- [v0.2 独立复核清单/哈希](working/e2e-integration/independent-review-manifest-v0.2.json)
- [环境结果 JSON（v0.2）](working/e2e-integration/local-e2e-fixture-env-002.json)
- [DXF 回读清单 JSON（v0.2）](working/e2e-integration/site-fixture-v0.2-dxf-manifest.json)

- [用户本地复核记录（v0.3）](working/e2e-integration/reviews/user-local-review-v0.3-2026-10-27.md)
- [DXF semantic equivalence policy v0.1](working/cad-bim-validator/dxf-semantic-equivalence-policy-v0.1.md)
- [正式开发阶段验收合同 v0.1](working/cad-bim-validator/development-acceptance-contract-v0.1.md)
- [R0 v0.11 工作区快照说明](reports/supporting/snapshot-r0-v0.11.md)
- [R0 v0.10 工作区快照说明](reports/supporting/snapshot-r0-v0.10.md)
- [R0 v0.9 工作区快照说明](reports/supporting/snapshot-r0-v0.9.md)
- [R0 v0.8 工作区快照说明](reports/supporting/snapshot-r0-v0.8.md)
- [R0 v0.7 工作区快照说明](reports/supporting/snapshot-r0-v0.7.md)

## R1 Stateful Runtime checkpoint（v0.17）

`NEXT-R1-RUNTIME-001` 已达到有界研究 checkpoint：

- Foundation contract：21/21 passing；
- Runtime contract：22/22 passing；
- clean ZIP extraction 后合计 43/43 passing；
- Agent/CLI/MCP 统一进入同一个 stateful Runtime；
- human approve/unlock 通过独立 Control Plane 写入服务端 Approval Grant，Agent tool surface 不暴露伪造权限字段；
- Project/Proposal/Approval/Job/Artifact/Idempotency/Audit registry 已形成可运行研究原型；
- interrupted job 采用 at-least-once 恢复语义，并用 worker+attempt 阻止旧 worker 完成已重新领取的任务；
- 双 runtime stale writer 使用 persisted-state hash compare-and-swap fail-closed，不静默覆盖。

主要入口：

- [Runtime review](working/r1-runtime-001/runtime-001-review-v0.1.md)
- [Stateful Runtime architecture](working/r1-runtime-001/stateful-runtime-architecture-v0.1.md)
- [Recovery / idempotency policy](working/r1-runtime-001/recovery-idempotency-policy-v0.1.md)
- [Runtime contract register](working/r1-runtime-001/runtime-contract-register-v0.1.yaml)
- [Executable prototype](working/r1-runtime-001/prototype-v0.1/README.md)
- [R0 v0.17 snapshot](reports/supporting/snapshot-r0-v0.17.md)

该 checkpoint 不代表生产 Runtime 完成。当前唯一下一动作转为 `NEXT-R1-RUNTIME-002`：研究本地 sidecar / CAD bridge / remote service 的部署边界、事务存储、单写者生命周期、actual MCP server 与 Human Control Plane handshake。

## R1 Deployment Boundary checkpoint（v0.18）

`NEXT-R1-RUNTIME-002` 已达到有界研究 checkpoint：

- 推荐 R1 形态收敛为 **Local Sidecar Runtime + thin CAD bridges + separate Human Control Plane + MCP/CLI adapters**；
- SQLite/WAL + content-addressed artifact store 研究 spike 已执行；Foundation + Runtime + Deployment 合计 51/51 tests passing，clean ZIP extraction 后仍为 51/51；
- 两个 SQLite connection 的 stale-writer CAS、payload/hash corruption、artifact dedup/tamper/reopen、CLI/shared-service parity 已验证；
- AutoCAD 推荐使用薄 Managed .NET in-process bridge；FreeCAD 推荐使用薄 Python workbench/macro bridge。两者都不拥有 canonical project truth；
- MCP v2 官方文档已复核：stdio 适用于 host-launched local subprocess，Streamable HTTP 适合独立部署的 sidecar；SSE 不作为新实现目标；
- 当前环境没有官方 MCP Python SDK，pip 安装因 DNS/network resolution 失败，因此 **wire-level MCP conformance 未执行**，不得声称 actual MCP 已跑通；
- SQLite 只被提升为 R1 本地 sidecar 的首选候选，不适用于多机共享 WAL/网络文件系统权威数据库。

主要入口：

- [Deployment boundary review](working/r1-runtime-002/runtime-002-review-v0.1.md)
- [Deployment boundary decision](working/r1-runtime-002/deployment-boundary-decision-v0.1.md)
- [Deployment mode matrix](working/r1-runtime-002/deployment-mode-matrix-v0.1.yaml)
- [SQLite + artifact spike](working/r1-runtime-002/sqlite-artifact-spike-v0.1.md)
- [Human Control Plane boundary](working/r1-runtime-002/human-control-plane-boundary-v0.1.md)
- [MCP binding candidate](working/r1-runtime-002/contracts/mcp-binding-v0.2.yaml)
- [CAD bridge contract](working/r1-runtime-002/contracts/cad-bridge-contract-v0.1.yaml)
- [Executable deployment prototype](working/r1-runtime-002/prototype-v0.1/README.md)

该 checkpoint 不代表生产部署完成。新的唯一下一动作是 `NEXT-R1-DEPLOY-003`：定义真实 local service lifecycle、loopback authentication/capabilities、project open/close/session semantics、Human Review handshake，并完成第一个 CAD bridge message exchange。官方 MCP SDK 可用后补做真实 wire-level binding。

## R0 架构综合（provisional）

Phase 2 已把“模块说明”推进为可用于 R1/MVP 立项讨论的接口、权限与边界：

- [Provisional Architecture Synthesis v0.2](working/architecture/provisional-architecture-synthesis-v0.2.md)：总体数据面/控制面、模块分界、R1 切片。
- [Module Contracts v0.1](working/architecture/module-contracts-v0.1.md)：M01–M11 的输入、输出、真值 owner、stale 条件与 MVP 责任。
- [Agent Authority Matrix v0.1](working/architecture/agent-authority-matrix-v0.1.md)：Agent / deterministic engine / rules / validator / human 的权限边界。
- [Canonical Site IR v0.2](working/architecture/canonical-site-ir-v0.2.yaml)：authority state、ChangeProposal、derived representation 和 external reconcile 合同。
- [Architecture Challenge Report v0.1](working/architecture/architecture-challenge-report-v0.1.md)：用 12 个失败场景挑战 truth owner、adapter lock-in、stale、权限与 MVP scope。
- [Architecture Amendments v0.1](working/architecture/architecture-amendments-v0.1.md)：挑战后必须进入 R1 Foundation 的 5 项修正。
- [Canonical Site IR v0.3](working/architecture/canonical-site-ir-v0.3.yaml)：加入 AtomicChangeSet、ProposalSnapshot、广义 dependency graph、conditional rule applicability 与三世界隔离。
- [R1 Development Research Charter Draft v0.1](working/architecture/r1-development-research-charter-draft-v0.1.md)：在不开始正式开发的前提下定义下一阶段研究/实现切片。
- [Open-source Capability Allocation v0.1](working/architecture/open-source-capability-allocation-v0.1.md)：把开源项目归位为 core candidate / adapter / reference / external gate。
- [R1 / MVP Boundary v0.1](working/architecture/mvp-boundary-v0.1.md)：第一版必须证明什么、明确延期什么。
- [Provisional Decision Register v0.1](working/architecture/provisional-decision-register-v0.1.md)：可重开的架构决定候选及重验条件。
- [Research Gap Matrix v0.2](working/architecture/research-gap-matrix-v0.2.md)：区分 R0/R1 高风险证据、mandatory spike、development hardening 与未来扩展。

以上仍是 provisional research artifacts，不是 G3/G5 通过、最终技术栈或生产架构冻结。


### R1 Charter Review / Evidence Planning

- [R1 Charter Review v0.1](working/architecture/r1-charter-review-v0.1.md)：复核 R1.0–R1.6 的进入条件、Gate 与证据关系。
- [R1 Development Research Charter Candidate v0.2](working/architecture/r1-development-research-charter-candidate-v0.2.md)：Foundation 先行 + Evidence Gate 分层解锁后的候选章程。
- [R1 Evidence Gate Register v0.1](working/architecture/r1-evidence-gate-register-v0.1.yaml)：机器可读 Gate/Package 状态与 claim blockers。
- [R1 Evidence Packages](working/architecture/evidence-packages/README.md)：SKETCH / ROAD / IFC / ENV / PROFILE 五个最小证据包。

## 当前权威项

- [当前计划](research-plan.md)：决策问题、边界、覆盖、许可和唯一下一动作。
- [能力树](working/capability-map.md)：本项目真正需要解决的能力，而不是仓库收藏列表。
- [Benchmark 设计](working/benchmarks.md)：用固定测试题比较项目和算法。
- [第一批项目研究矩阵](working/project-matrix.md)：首轮需要深入的开源项目及其研究问题。
- [知识与决定记录规范](working/recording-model.md)：CAP / KNO / BEN / DEC 的讨论接口。
- [道路分类与设计 Profile](working/road-classification-and-design-profile.md)：新增的道路层级/功能/用途/标准映射研究线。
- [工作变更记录](working/changelog.md)：记录本轮范围与文件更新。
- [调研 Skill 完整副本](working/reference-skill/v0.2.2-field-test.4/SKILL.md)：随工作空间保留用户提供的 `conduct-traceable-research` 版本及其 references/assets/scripts，便于后续按原合同执行。
- [校准获取说明](reports/acquisition-summary.md)：本轮已查什么、没查什么、哪些结论不能下。

## 下一步依据

`NEXT-R0-SYN-002` 已完成：Architecture Challenge verdict 为 **`provisional_architecture_survives_with_amendments`**。挑战没有发现需要推倒重来的根本真值冲突，但要求补入 Atomic ChangeSet、Proposal Snapshot、Profile/Rule 一等依赖、conditional rule applicability 和 canonical/preview/external 三世界隔离。

`NEXT-R1-CHARTER-001` 已完成。R1 scope 保持收敛，五个 Evidence Packages 与 Gate register 已建立；当前进入 `NEXT-R1-ENTRY-001`，只做 R1.0 Foundation 的 repo/package skeleton、typed contract tests 与 synthetic fixtures 规划。未关闭的 R0 acquisition/A1 继续保留；如果后续真实证据改变 truth/module/authority/dependency model，再回开 architecture decision。

## R1.0 Foundation Entry checkpoint — v0.15

R1 entry planning has produced a research-only executable Foundation skeleton. The current expanded contract suite is 12/12 passing after correcting preview-confirmation ordering, transitive dependency invalidation and scoped lock behavior. This is an entry candidate, not a formal R1 Gate pass and not product code.

See `working/r1-entry/foundation-entry-review-v0.1.md` and the standalone prototype package `design-grade-cad-agent-r1-foundation-entry-v0.1`.

## R1 Foundation v0.2 / Agent Integration checkpoint

- [Foundation v0.2 Review](working/r1-foundation-002/foundation-002-review-v0.1.md)
- [Foundation Entry Prototype v0.2](working/r1-foundation-002/prototype-v0.2/README.md) — 21 contract tests, research-only.
- [Agent Integration Architecture v0.1](working/architecture/agent-integration-architecture-v0.1.md)
- [Agent Integration Options v0.1](working/architecture/agent-integration-options-v0.1.md)
- [Agent Authority Boundary v0.1](working/architecture/agent-authority-boundary-v0.1.md)
- [Agent Tool Contract v0.1](working/architecture/agent-tool-contract-v0.1.yaml)

The preferred final Agent form is a narrow MCP gateway over a separate stateful DGCAD runtime, not direct library import and not a prompt-only skill. The internal Foundation stays protocol-agnostic.


## R1 Deployment Lifecycle checkpoint（v0.19）

`NEXT-R1-DEPLOY-003` 已达到有界研究 checkpoint：

- Local Sidecar 启动所有权收敛为 **DGCAD Desktop/Tray Launcher**；Agent/MCP adapter 与 CAD plug-in 默认发现已有 Runtime，而不是各自拥有 canonical runtime；
- Foundation + Runtime + Deployment + Lifecycle 合计 **65/65 tests passing**，clean ZIP extraction 后仍为 65/65；
- 新增 token-free discovery、role-bound one-time pairing、short-lived bearer session、Agent/Human Review/CAD Bridge 三类独立 principal；
- localhost control-plane prototype 仅绑定 loopback，并对 `Host` 与 `Origin` 进行校验；Agent token 无法调用 Human approve/unlock，Human Review token 可以；
- SQLite runtime lease 防止同一项目出现两个 live writer，expired takeover 使用 generation 递增，旧实例随后 heartbeat fail-closed；
- CAD bridge 采用注册/heartbeat/expiry 语义，只有 external CAD representation 权限，不拥有 canonical commit/approval；
- 独立 child-process probe 已执行：lease → loopback bind → token-free discovery → 私有 pairing handoff → agent session → graceful stop/discovery cleanup；
- 当前 generic bridge lifecycle 已执行，但 **实际 AutoCAD/FreeCAD host plug-in message exchange 未执行**，不得宣称 CAD host 已接通；
- 官方 MCP SDK 当前环境仍不可用，因此 actual MCP Streamable HTTP / OAuth wire conformance 仍为 blocker。

主要入口：

- [Deployment lifecycle review](working/r1-deployment-003/deployment-003-review-v0.1.md)
- [Startup / connection lifecycle](working/r1-deployment-003/startup-connection-lifecycle-v0.1.md)
- [Local sidecar threat model](working/r1-deployment-003/local-sidecar-threat-model-v0.1.md)
- [Sidecar lifecycle contract](working/r1-deployment-003/contracts/sidecar-lifecycle-contract-v0.1.yaml)
- [Local auth/capability contract](working/r1-deployment-003/contracts/local-auth-capability-contract-v0.1.yaml)
- [CAD bridge lifecycle contract](working/r1-deployment-003/contracts/cad-bridge-lifecycle-contract-v0.2.yaml)
- [MCP binding candidate v0.3](working/r1-deployment-003/contracts/mcp-binding-v0.3.yaml)
- [Executable lifecycle prototype](working/r1-deployment-003/prototype-v0.2/README.md)

该 checkpoint 不是生产安全批准。由于当前环境没有 Windows/AutoCAD/FreeCAD host，继续在 Linux 容器中模拟 CAD host 的边际价值已经下降。下一主线动作应回到 MVP domain slice：先建立 **confirmed Trace/Intent → Canonical Site Model → simple Building/Road domain adapter**，而 AutoCAD bridge 的真实 host spike 留作 Windows/AutoCAD 环境 Gate。
