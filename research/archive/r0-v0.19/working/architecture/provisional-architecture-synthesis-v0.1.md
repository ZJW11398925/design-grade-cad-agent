# Provisional Architecture Synthesis v0.1

**阶段：** R0 technical research synthesis  
**状态：** `provisional`，不是最终技术选型。  
**目标：** 把 BATCH-001..005 的研究结果合成一条最小可行 Sketch → Professional Site Model → CAD/BIM 闭环，并明确每层真值、模块责任和验证边界。

## 1. 最重要的架构结论：系统不是“AI 画 CAD”，而是多层真值转换系统

推荐保留七层对象状态：

1. **Source Evidence**：原始草图、红线底图、已知尺寸、坐标点、设计文字说明。不可被后续算法覆盖。
2. **Trace Geometry**：对 Source 的忠实向量化，只表达“原图画了什么”，不表达“专业上应该是什么”。
3. **Intent Model**：道路/建筑/绿地/边界等语义、关系、候选类别和不确定性。
4. **Professional Site Model**：经过拓扑、几何和规则处理后的专业模型，是后续 CAD/BIM/分析的 canonical design state。
5. **Derived 3D / Analysis Representations**：Massing、道路面、阴影分析模型等。它们依赖 Professional Site Model，可 stale，不反向覆盖上游。
6. **Delivery Representations**：DXF、IFC、PDF/PNG 等格式化交付物。
7. **Validation / Review Evidence**：验证结果、第三方 round-trip、人工确认和变更记录。

核心规则：**下游表示永远不能静默成为上游设计真值。** 例如 AutoCAD round-trip 的 DXF 不能反向改写 canonical site model，除非经过显式 import/reconcile 操作。

## 2. 最小模块边界

### M01 Source & Calibration

责任：
- 保存原图/底图/控制点；
- 建立 image-space / local metric / project coordinate transform；
- 输出 transform quality、residual 和 confidence。

候选实现：OpenCV、GDAL 等。

禁止：没有足够控制信息时伪称 georeferenced / 1:1。

### M02 Trace & Semantic Candidate

责任：
- 候选 mask / line / contour；
- Trace Geometry；
- semantic candidate + confidence；
- 人工确认和锁定。

候选实现：SAM family / SamGeo / deterministic vectorization + custom reconstruction。

禁止：把 segmentation mask 直接当工程边界。

### M03 Geometry & Topology Kernel

责任：
- polygon validity、snap、node、split、union、offset；
- shared-boundary / component / hole topology；
- geometry difference metrics。

候选实现：Shapely/GEOS 为高层核心候选；CGAL 用于需要更强鲁棒性的专门几何。

### M04 Road Design Engine

责任：
- Road Graph；
- road role / hierarchy / use candidates；
- centerline / engineering alignment；
- cross-section profile；
- junction / transition geometry。

候选实现来源：OSMnx 的 graph 思想、PyGeoOps 的 centerline candidate、Clothoids 的连续曲线、Street Generator 的 typed profile/rules 架构。

原则：道路边界由 centerline + profile + junction 派生，而不是 Agent 直接画左右边线。

### M05 Building & Massing Engine

责任：
- Trace footprint → professional footprint candidate；
- regularization proposal + refusal gate；
- typology candidate；
- height/floors/elevation state；
- footprint → 3D massing；
- group/shared-boundary consistency。

原则：regularization 是 proposal，不是默认真值；FAR/BCR 等是 constraints，不替代设计意图。

### M06 Canonical Site Model / IR

这是系统最关键的数据边界。道路、建筑、绿地等最终都必须在同一 canonical scene 中拥有：
- stable object ID；
- semantic role；
- authoritative geometry revision；
- source/trace provenance；
- locks；
- uncertainty state；
- dependency links；
- stale propagation。

CAD/BIM/环境分析都消费这一层，不直接消费 LLM 文本。

### M07 Analysis Engine

责任：
- 根据 canonical revision 创建分析输入；
- 记录 location / north / time / terrain / context / method version；
- 返回结果 + dependency fingerprint + coverage limits；
- 上游变化时自动 stale。

候选：Ladybug/Honeybee/Radiance 等作为专门引擎候选；R0 合成射线算法只作为基线，不作为生产模拟器。

### M08 Rule & Profile Engine

必须区分四种规则：

1. CAD format semantics；
2. 通用互操作 policy；
3. 国家/地方/行业/设计院/项目 design profile；
4. serialization / presentation preference。

Rule Engine 不应把所有规则混成一份 YAML。每条规则必须有 scope、source、version、severity、override policy、validation method。

### M09 CAD/BIM Compiler

责任：
- canonical model → DXF；
- canonical model → IFC；
- 不负责决定“设计是否专业”；只负责忠实编译已确认的 canonical design state。

当前候选：ezdxf、IfcOpenShell。

### M10 Validator Stack

分层：
- file validity；
- schema/contract；
- entity semantics；
- geometry/topology；
- Profile compliance；
- 2D/3D consistency；
- round-trip equivalence；
- rendered/visual QA。

Validator 自身错误必须是 `validator_error`，不能冒充设计失败。

### M11 Agent Orchestrator

Agent 只做：
- 解释设计输入；
- 生成候选与变更 proposal；
- 选择工具；
- 汇总冲突与证据；
- 请求确认；
- 根据 validator failure 发起局部修复。

Agent 不直接拥有：
- 标准参数真值；
- CAD layer/linetype 最终值；
- geometry validity 的最终判断；
- 规范合规最终判定。

## 3. Canonical truth hierarchy

建议权威顺序：

```text
confirmed project constraints / locked references
        ↓
confirmed Professional Site Model
        ↓
derived representations (3D / analysis / CAD / IFC)
        ↓
renderings / screenshots / reports
```

Trace 与 Source 不在“专业权威”层级中，但它们是不可删除的**证据真值**。Professional Geometry 可以偏离 Trace，但必须留下 diff + reason + reviewer/agent action。

## 4. Revision / dependency model

每个 canonical object 至少维护：

```text
object_id
semantic_revision
geometry_revision
parameter_revision
source_refs
trace_ref
locks
state: unknown | proposed | confirmed | rejected | stale | blocked
```

派生对象记录：

```text
derived_from[]
dependency_hash
method_id + method_version
profile_id + profile_version
```

任何 dependency 改变时，下游自动 `stale`，而不是继续沿用旧结果。

## 5. 当前技术候选的角色，而不是“最终技术栈”

| 能力 | 当前优先候选角色 | 研究判断 |
|---|---|---|
| 2D geometry/topology | Shapely/GEOS | 很适合 Python orchestration，但复杂/高鲁棒几何需保留 CGAL 路线 |
| Road graph | custom graph + OSMnx ideas | OSMnx 更适合学习网络语义/节点合并，不直接作为设计道路引擎 |
| Centerline candidate | PyGeoOps | 只做候选，不是工程 alignment |
| Alignment | Clothoids / custom constraints | 需要结合道路等级/Profile，尚未冻结 |
| Building regularization | custom gate + Building Regulariser ideas | 不能直接全自动；公开 failure 已证明需场地级 topology check |
| 2D/3D/BIM | IfcOpenShell | 语义/representation 能力强，真实 round-trip 尚待执行 |
| CAD | ezdxf | 编译和结构检查价值高；第三方 round-trip 已暴露 semantic-equivalence 需求 |
| Environmental | Ladybug/Honeybee/Radiance candidates | 真实独立模拟尚未完成，许可/部署也需正式开发评估 |
| Human inspection | LibreCAD / AutoCAD / others | 应作为 independent application gate，而不是 canonical model authority |

## 6. 最小闭环 MVP（未来正式开发目标，不在 R0 实现）

第一版不需要“自动设计整座社区”，只需要：

1. 输入一张带已知尺度/红线的简单场地草图；
2. 保存 Source + Trace；
3. 人工确认道路/建筑/绿地对象；
4. 对一个 T 路口和 2–3 栋建筑生成 Professional Geometry；
5. 生成建筑简单 massing；
6. 运行一个固定时刻阴影检查；
7. 编译 DXF + IFC；
8. Validator 检查；
9. 故意修改一个道路节点/建筑高度，验证 stale → local rebuild → regression。

如果这个闭环不能可靠工作，就不应该继续扩展户型、复杂道路、自动规划生成。

## 7. 当前仍不可冻结的架构点

- canonical IR 的具体语言/存储格式；
- Shapely/CGAL 的最终边界；
- Road alignment 的实际规范算法；
- IFC 是否作为 canonical model 本身，还是只作为 delivery representation；
- 真实设计院 Profile schema；
- 环境分析生产引擎与许可/部署策略；
- DWG 最终交付链路。

这些必须通过后续真实 Benchmark 或正式开发 spike 决定。
