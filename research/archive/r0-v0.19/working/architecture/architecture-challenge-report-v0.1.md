# Architecture Challenge / R0 Exit Review v0.1

**对象：** R0 provisional architecture v0.2  
**方法：** 通过预定义失败场景尝试推翻 truth ownership、module boundary、dependency/stale、authority 与 MVP scope。  
**结论：** `provisional_architecture_survives_with_amendments`。未发现需要推倒重来的根本矛盾，但发现 5 个必须在 R1 Foundation 中显式建模的架构缺口。

## 1. Challenge Matrix

| CH | 失败场景 | 预期危险 | 结果 | 结论 |
|---|---|---|---|---|
| CH-01 | 用户在 AutoCAD 中移动建筑后重新导入 DXF | 外部文件篡改 canonical truth | `survives` | external reconcile 只能生成 ChangeProposal，不直接覆盖 M06 |
| CH-02 | 替换 SAM 为手工 Trace / 其他分割模型 | canonical schema 被模型输出绑定 | `survives` | M02 只输出 TraceObject/candidates；adapter 可替换 |
| CH-03 | 建筑高度 18m→30m | 全场景重建或漏掉旧阴影 | `survives_with_amendment` | 必须让 dependency graph 同时追踪 object revision + derived artifact；footprint 不应 stale，massing/shadow/IFC/相关 label 应 stale |
| CH-04 | T 路口节点移动 | 单对象 revision 无法保持多边/交叉口一致 | `survives_with_amendment` | ChangeProposal 需要 **atomic transaction / change set**，可同时更新 node、edges、junction surface |
| CH-05 | 道路 hierarchy unknown，但 Agent 想生成宽度 | 默认值被伪装为专业设计 | `survives` | Profile resolution 返回 blocked/conditional，Trace/RoadGraph 可继续存在 |
| CH-06 | 红线已 locked，regularization 后建筑越界 | Agent 为满足几何美观移动红线 | `survives` | locks 优先；只能修改 building proposal 或返回 conflict |
| CH-07 | Profile v1→v2，但几何没改 | 输出仍使用旧图层/规范或道路参数 | `survives_with_amendment` | dependency graph 必须把 **profile/rule revision** 作为一等依赖，不只对象 geometry hash |
| CH-08 | Shadow analysis 建议“建筑向北移 2m” | Analysis Engine 反向直接修改设计 | `survives` | M07 只能输出 result; M11 可基于结果生成 proposal，不能 M07→M06 直写 |
| CH-09 | Validator 遇到未知 SPLINE / entity | exception 或默认 pass | `survives` | fail-closed contract 已存在；R1 必须结构化 unsupported/validator_error |
| CH-10 | 在未提交的 road/building proposal 上预览 shadow/DXF | 架构只允许 confirmed canonical 派生，导致无法预览 | `survives_with_amendment` | 需要 **Proposal Snapshot / Preview Artifact**，明确 `preview_only`，不可成为 current derived artifact |
| CH-11 | Rule applicability 取决于尚未确认的道路类型 | Rule Engine 和 semantic confirmation 循环依赖 | `survives_with_amendment` | Rule resolution 必须允许 `applicable / conditionally_applicable / not_applicable / blocked`，不能反向确认道路语义 |
| CH-12 | 外部 IFC 修改高度与 canonical 冲突 | 两个 truth owner | `survives` | IFC 与 DXF 同样进入 reconcile；不存在“last file wins” |

## 2. 五个必须补入架构的 Amendments

### A-01 Atomic ChangeSet

单个 `ChangeProposal` 不足以表达 T junction、共享边、道路节点重连等多对象原子修改。R1 应引入：

```text
ChangeSet
  proposals[]
  transaction_scope[]
  invariant_checks[]
  commit_policy: all_or_nothing
```

只有整组验证通过才写新的 canonical revisions。

### A-02 Preview Snapshot

设计者必须在“确认前”看到专业化/分析/输出效果。因此需要：

```text
ProposalSnapshot
  base_scene_revision
  applied_candidate_changes
  preview_hash
```

Analysis/Compiler/Validator 可消费 preview snapshot，但产生的结果标记 `preview_only`，禁止混入 current production artifacts。

### A-03 Dependency graph 不只依赖对象

依赖节点至少包括：
- object semantic/geometry/parameter revision；
- CalibrationFrame revision；
- Rule/Profile revision；
- method/version；
- context/terrain/time/sensor inputs；
- Delivery Profile revision。

否则“几何没变但规范变了”不会正确 stale。

### A-04 Conditional Rule Applicability

Rule Engine 不能只返回 pass/fail。至少需要：
- `applicable`
- `conditionally_applicable`
- `not_applicable`
- `blocked`

并记录缺失的 semantic/context prerequisites。

### A-05 Canonical vs Preview vs External 三类世界必须分开

系统同时存在：
1. confirmed canonical scene；
2. uncommitted proposal preview；
3. external CAD/BIM round-trip artifact。

三者不能共享“current”状态。所有跨世界变化必须通过 diff/reconcile/proposal。

## 3. Truth Owner Challenge

没有发现需要第二个 design truth owner。

- Source/Trace：证据真值；
- Canonical Site Model：confirmed design truth；
- Profile Registry：规则真值；
- Derived artifacts：方法特定结果；
- External CAD/BIM：互操作证据。

这几个“真值”属于不同事实域，不构成竞争 owner。关键是禁止 delivery artifact 直接覆盖 design truth。

## 4. Adapter Lock-in Challenge

当前架构在以下替换下仍能保持主干：

- SAM → 其他 segmentation / manual trace；
- PyGeoOps → 其他 centerline candidate；
- ezdxf → 其他 DXF writer；
- IfcOpenShell → 其他 IFC adapter；
- Ladybug/Honeybee → 其他 analysis engine；
- AutoCAD → LibreCAD/FreeCAD external gate。

真正可能造成 lock-in 的是：
- geometry model 使用库私有对象直接作为 persistence；
- canonical ID/revision 写进某个 CAD object handle 并把 handle 当主键；
- rules 直接编码在 Agent prompt；
- derived artifact 的生命周期由某个第三方软件文档管理。

R1 Foundation 必须禁止这些实现捷径。

## 5. MVP Scope Challenge

MVP-A 可以在不实现 clothoid、完整 IFC UI、全国法规、复杂日照和自动方案生成的情况下验证核心架构，因为最关键的架构命题是：

- evidence vs design truth；
- stable identity；
- proposal/authority；
- deterministic geometry；
- dependency/stale；
- compiler/validator separation；
- local rebuild。

因此当前 MVP 边界没有被挑战推翻。

## 6. R0 Exit 判断

### 已足以进入 R1 Charter 的部分

- 模块边界；
- canonical truth model；
- Agent authority model；
- derived/stale model；
- MVP-A 目标；
- 开源组件的角色边界。

### 仍不能冻结为最终技术选择的部分

- road alignment 算法/中国 Profile；
- Shapely/CGAL 最终边界；
- IFC 具体 authoring/round-trip 策略；
- production environment engine；
- project/design-office Profile schema；
- DWG production route。

## 7. Challenge Verdict

`provisional_architecture_survives_with_amendments`

建议允许建立 **R1 Charter（开发研究阶段）**，前提是 R1.0 首先实现 A-01..A-05 的基础合同，而不是直接做自动草图识别或复杂道路。

这不等于 G5 正式通过：R0 的 acquisition/A1 仍有未关闭项；此 verdict 只表示当前 provisional architecture 足以指导下一阶段的工程/研究切片，不需要在 R0 继续横向扩展架构。
