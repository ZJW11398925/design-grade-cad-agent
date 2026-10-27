# R0 Architecture Synthesis Phase 2：模块契约 v0.1

**状态：** `provisional-research-contract`  
**目的：** 把 M01–M11 从“职责说明”推进到可以指导 R1/MVP 实现的接口级契约。  
**非目标：** 本文件不冻结编程语言、数据库、具体类名或最终开源技术栈。

## 0. 全局契约原则

1. **Canonical truth ownership**：只有 Source Evidence、人工确认的项目约束、以及 Canonical Site Model 中已确认对象可以成为权威事实。DXF、IFC、分析网格和截图都是派生表示。
2. **No silent overwrite**：任何模块不得原地覆盖 Source/Trace；专业化必须创建新 revision 并保留 diff、理由、工具版本和执行者。
3. **Unknown is valid**：无法可靠判断时允许 `unknown / proposed / needs_review / blocked`，不得用默认值伪装成 confirmed。
4. **Deterministic boundary**：几何构造、规则求值、导出、校验、依赖失效必须由可测试的确定性代码承担。LLM/Agent 只能生成 proposal、解释和工具调用计划。
5. **Stable identity**：对象从 Trace 到 Professional、3D、CAD、IFC、分析结果始终保留 `object_id`；表示变化不能产生隐式新设计对象。
6. **Dependency-driven rebuild**：下游表示记录依赖 revision/hash；上游变化后先标记 stale，再局部重建，而不是全场景重新生成。
7. **Fail closed at validation boundary**：validator 无法解释对象时返回结构化 `validator_error` / `unsupported_entity`，不能抛出未处理异常，也不能默认通过。

## 1. 共同接口对象

### `SourcePacket`
- `source_id`
- `source_type`: raster_sketch | base_cad | gis | control_points | text_note | profile_asset
- `content_ref`
- `immutable_hash`
- `acquired_at`
- `coordinate_claim`
- `provenance`

### `CalibrationFrame`
- `frame_id`
- `state`: image_space | local_metric_scaled | project_coordinate | georeferenced
- `transform_model`
- `control_refs[]`
- `residual_summary`
- `north_state`
- `north_angle_deg`
- `revision`

### `TraceObject`
- `object_id`
- `source_refs[]`
- `trace_geometry_ref`
- `semantic_candidate`
- `confidence`
- `review_state`
- `locks[]`
- `trace_revision`

### `ChangeProposal`
- `proposal_id`
- `target_object_ids[]`
- `operation_type`
- `before_revision[]`
- `candidate_after`
- `reason`
- `evidence_refs[]`
- `rule_refs[]`
- `expected_side_effects[]`
- `required_authority`

### `CanonicalObject`
- `object_id`
- `object_class`
- `semantic_revision`
- `geometry_revision`
- `parameter_revision`
- `authority_state`
- `geometry_ref`
- `parameters`
- `locks[]`
- `provenance`
- `dependency_edges[]`

### `DerivedArtifact`
- `artifact_id`
- `artifact_type`
- `derived_from[]`
- `dependency_hash`
- `method_id`
- `method_version`
- `profile_bindings[]`
- `state`: current | stale | invalid | blocked

### `ValidationResult`
- `validator_id`
- `validator_version`
- `scope`
- `verdict`
- `issues[]`
- `coverage_limits[]`
- `evidence_refs[]`

## 2. M01 Source & Calibration

**权威输入**：`SourcePacket`、人工提供的已知尺寸/控制点/项目坐标/北向。  
**输出**：`CalibrationFrame` + 原始 Source 的不可变引用。  
**拥有真值**：仅拥有“坐标状态与变换证据”，不拥有建筑/道路语义。  
**允许自动执行**：图像旋转、透视候选、控制点拟合、残差计算。  
**必须人工确认**：项目坐标系、真实北向、冲突控制点的取舍。  
**禁止**：单一尺寸推断完整 CRS；从图像观感猜测真实米制宽度。  
**stale 触发**：控制点、尺度、北向、底图 revision 变化。  
**MVP**：必须。

## 3. M02 Trace & Semantic Candidate

**权威输入**：Source + CalibrationFrame。  
**输出**：`TraceObject[]`、mask/line/contour candidates、review queue。  
**拥有真值**：Trace 只拥有“原图中实际画了什么”的证据层真值。  
**允许自动执行**：分割候选、轮廓追踪、文字/箭头过滤候选。  
**必须人工确认**：对象类别、模糊交界、道路中心线/边界含义。  
**禁止**：把模型 mask 直接升级为 Professional Geometry。  
**stale 触发**：Source/Calibration 改变。  
**MVP**：必须，但允许强制 human-in-the-loop。

## 4. M03 Geometry & Topology Kernel

**权威输入**：Trace / proposed professional geometry + tolerance policy。  
**输出**：有效几何、拓扑关系、diff metrics、结构化 failure。  
**拥有真值**：拥有“几何/拓扑计算结果”，不拥有设计意图。  
**允许自动执行**：node/split/snap/polygonize/boolean/validity/diff。  
**必须人工确认**：当修复有多种设计含义时，不得自行选一。  
**禁止**：以 `buffer(0)` 等修复结果自动覆盖设计对象；容差不得写死为无来源常数。  
**stale 触发**：输入几何、容差 policy、kernel version 变化。  
**MVP**：必须。

## 5. M04 Road Design Engine

**权威输入**：Trace/Intent、Road Graph、项目道路 Profile、锁定控制点。  
**输出**：RoadGraph、centerline/alignment、cross-section、junction surfaces、road design proposal。  
**拥有真值**：只有经确认/规则通过的道路对象可以写入 Canonical Site Model。  
**允许自动执行**：centerline candidate、拓扑恢复、profile 候选、line/arc fitting、junction geometry proposal。  
**必须人工确认**：道路层级/服务用途不明确、特殊消防/服务用途、专业化明显偏离 Trace。  
**规则引擎决定**：规范参数、Profile 适用性和冲突优先级。  
**禁止**：让 LLM 直接给出“主路宽度=某值”并写入 confirmed。  
**stale 触发**：RoadGraph、road role、Profile、控制点、alignment revision 变化。  
**MVP**：限制为简单 site road、T/X junction、line/arc；clothoid/复杂环岛可延期。

## 6. M05 Building & Massing Engine

**权威输入**：Trace footprint、项目约束、已确认高度/层数/标高、邻接关系。  
**输出**：professional footprint candidate、massing、冲突报告。  
**拥有真值**：只有人工确认或明确 deterministic rule 可批准的 footprint/参数进入 canonical。  
**允许自动执行**：正交/方向/邻楼对齐候选、typology candidate、extrusion。  
**必须人工确认**：有意斜向、曲线、院落/凹槽、regularization 偏差过大、未知高度。  
**禁止**：为了有 3D 效果而猜高度；用 FAR/BCR 反向重画已有建筑意图。  
**stale 触发**：footprint/height/base elevation/placement/typology 变化。  
**MVP**：2–3 栋简单建筑；高度必须显式 supplied/confirmed。

## 7. M06 Canonical Site Model / IR

**权威输入**：通过权限检查的 ChangeProposal、confirmed project constraints。  
**输出**：唯一 canonical scene + revision graph。  
**拥有真值**：**系统设计真值的唯一写入点。**  
**职责**：stable ID、revision、locks、authority state、dependency graph、provenance、stale propagation。  
**禁止**：让 DXF/IFC/分析结果直接覆盖 canonical；任何 external edit 必须走 reconcile proposal。  
**MVP**：必须；具体存储技术暂不冻结。

## 8. M07 Analysis Engine

**权威输入**：Canonical revisions + location/north/time/context/terrain/method config。  
**输出**：`AnalysisResult` + dependency fingerprint + coverage limits。  
**拥有真值**：只拥有“特定方法、特定输入下的分析结果”，不拥有法规合规结论。  
**允许自动执行**：固定时刻 shadow、日照/形态指标计算。  
**规则引擎决定**：何种指标/阈值可以用于项目合规判断。  
**禁止**：输入缺失时返回 confirmed；把环境计算器输出直接写成“满足规范”。  
**MVP**：固定时间/简单 shadow baseline 必须；生产 daylight/radiation 可延期。

## 9. M08 Rule & Profile Engine

**权威输入**：已核验的法规/标准/设计院/项目 Profile 与明确项目 override。  
**输出**：适用规则集合、参数解析结果、冲突与 override chain。  
**拥有真值**：规则适用性与参数来源。  
**允许自动执行**：scope matching、version resolution、severity/override evaluation。  
**必须人工确认**：项目阶段/法域不明确、院标与地方标准冲突且无明确优先级。  
**禁止**：LLM 记忆补全条文；把 serialization preference 误当强制规范。  
**MVP**：仅支持小型、显式项目 Profile；不宣称全国规范自动合规。

## 10. M09 CAD/BIM Compiler

**权威输入**：Canonical Site Model + Delivery Profile。  
**输出**：DXF/IFC/manifest；只做编译。  
**拥有真值**：不拥有设计真值；只拥有“输出是否忠实映射”的编译责任。  
**禁止**：编译时重新决定道路宽度、建筑高度或对象分类。  
**MVP**：DXF 必须；IFC 作为 mandatory interoperability spike，是否进入首个用户可用版本由 R1 决定。

## 11. M10 Validator Stack

**权威输入**：Canonical、DerivedArtifact、Profile、第三方 round-trip 文件。  
**输出**：结构化 `ValidationResult`。  
**拥有真值**：验证范围内的 pass/fail/conditional；必须显式 coverage limits。  
**层次**：schema → geometry/topology → semantic entity → profile → 2D/3D consistency → round-trip → visual/print QA。  
**禁止**：同库 round-trip 替代第三方兼容 Gate；validator exception 冒充设计失败。  
**MVP**：必须。

## 12. M11 Agent Orchestrator

**权威输入**：用户意图、当前 canonical state、validator/rule/analysis 结果。  
**输出**：`ChangeProposal`、tool plan、解释、review request。  
**拥有真值**：不拥有几何/规范/交付真值。  
**允许自动执行**：读状态、提出候选、调用工具、汇总证据、生成局部修复 proposal。  
**必须人工确认**：所有会改变 confirmed design intent 的动作，除非该动作由已授权 deterministic rule 明确允许。  
**禁止**：绕过 locks、修改 Source、手写规范数值、直接清除 stale、把 validator failure 当作可忽略提示。  
**MVP**：必须，但初版可采用显式“提议→确认→提交”交互，而不是全自动自治。

## 13. 模块之间的最小消息流

```text
M01 -> CalibrationFrame
M02 -> TraceObject[]
M03 -> geometry/topology result
M11 -> ChangeProposal
M08 -> applicable rules/profile resolution
M04/M05 -> professional design candidate
M06 -> confirmed CanonicalObject revisions
M07 -> AnalysisResult (derived)
M09 -> DeliveryArtifact (derived)
M10 -> ValidationResult
M11 -> local repair proposal / human review request
```

**禁止消息流：**
- M09 DXF/IFC → 直接写 M06；
- M07 analysis result → 直接改 M05 geometry；
- M11 natural language → 直接改 M06 without proposal/authority check；
- M10 validator → 自动“修正”对象而不生成可审计 proposal。
