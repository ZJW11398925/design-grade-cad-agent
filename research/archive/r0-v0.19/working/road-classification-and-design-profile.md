# 道路分类、设计 Profile 与几何生成：研究工作说明

状态：`provisional-draft`。这是能力/数据模型假设，不是道路设计规范，也不是最终架构决定。

## 1. 为什么它是独立问题

道路不是一条线加一个宽度。道路的层级与功能会影响设计速度、设计车辆、横断面构成、出入口控制、交叉口组织、转弯空间、坡度要求、步行/骑行设施，以及后续需要执行的规范校核。如果 Agent 在类别尚未确定时就生成道路边界，后面再改等级可能导致中心线、道路宽度、节点几何、建筑退让和日照/景观关系全部返工。

因此顺序应是：

`识别道路对象 → 建立 Road Graph → 分类候选 → 确认/解析 Design Profile → 设计中心线与节点 → 生成横断面/道路面 → 验证 → CAD/IFC 输出`

## 2. 不要把道路类型压成一个枚举

同一条道路可能同时具有“场地内部主要通行道路”“住宅出入口服务”“消防车辆通行”等属性。这些不是互斥选项。至少需要拆成以下维度：

1. **分类体系 / 适用语境**：城市道路体系、地块内部道路体系、园区道路体系、消防通道体系等。不同体系之间不直接等价。
2. **路网层级 `network_hierarchy`**：例如城市快速路/主干路/次干路/支路，或项目自定义的场地主要路/组团路/局部通路。必须注明所采用的 classification scheme。
3. **主要服务功能 `primary_function`**：通过交通、集散、地块/建筑出入、停车场连接、装卸服务、消防/应急、步行空间等。
4. **允许通行方式与权限 `permitted_modes/access`**：机动车、消防/服务车辆、公交、骑行、步行、共享空间，以及限制条件。
5. **特殊用途 `special_designations`**：消防通行、急救/维护、货运装卸、无障碍通行等。它们可能叠加在普通道路类别上。
6. **物理横断面 `physical_cross_section`**：车道数、车道宽度、中央分隔、停车带、人行道、非机动车道、绿化带、路缘、排水等。
7. **设计 Profile `design_profile_id`**：将分类/用途/项目条件映射到一组经来源支持的参数和校核规则。
8. **证据与状态**：分类依据、置信度、冲突、`proposed / confirmed / unknown / needs_review` 状态和确认者。

OSM 的 `highway=*` 分类可用于学习“道路在路网中的功能与重要性”如何被标注，但其文档明确说明这并不必然等同于各国法定道路等级或物理特征。它只能提供网络语义参考，不能直接当作中国道路工程参数表。来源：[OpenStreetMap Wiki — Key:highway](https://wiki.openstreetmap.org/wiki/Key:highway)。

## 3. 道路分类应如何识别

### 3.1 证据优先级（暂定）

- 已确认的设计任务书、设计者明确标注、经确认的既有图纸/项目规则；
- 有出处且适用于该地点/版本的权威底图或 GIS 属性；
- 道路网络拓扑与场地功能上下文；
- 经尺度校准后的宽度、车道线、路缘、隔离带等视觉特征；
- 单纯线宽、颜色或手绘粗细（弱证据）。

这不是对所有事实的绝对真值排序：例如设计者标注可以表达“意图”，但不能覆盖强制规范。系统应分别记录“设计者意图”和“规范校核结果”。

### 3.2 可用的识别线索

- **网络角色**：是否连接地块出入口、外围道路、多个组团；是否为局部尽端路或环路；在 Road Graph 中的连接位置。
- **服务对象**：服务多少建筑/入口/停车区/装卸点；是否承担穿行还是主要到达功能。
- **场地上下文**：居住、商业、工业、公共设施、园区或混合用途；是否存在需要专用通行的设施。
- **显式语义**：文字标注、图例、道路名称、已有 GIS/CAD 属性、设计说明。
- **几何线索**：校准后的宽度、分隔、车道数、路缘、转弯几何。它们可以支持候选判断，但不能单独证明法定等级。
- **约束需求**：消防、服务车辆、无障碍、步行/骑行连续性等需求是否已在任务书或适用标准中明确。

### 3.3 输出不是“猜一个答案”

每条道路/道路走廊应输出候选类别、支持证据、反证/冲突、置信度、缺失信息和是否需要人工确认。若高影响属性未知，允许 `unknown`，并暂停依赖该属性的专业化动作。禁止把模型推断自动升级为 `confirmed`。

## 4. 从类别映射到 Design Profile

Profile 不是只包含一个宽度。它可以包含：

- 适用地域/法域、标准/版本、生效时点、项目阶段、专业范围；
- 设计速度（若适用）、设计车辆、车道数、车道/车行道宽度；
- 中央分隔、停车带、人行道、骑行设施、绿化/分隔带、路缘等横断面组件；
- 平曲线/转弯半径、交叉口组织、视距、纵坡/横坡等设计约束（按适用规范及阶段启用）；
- 适用/不适用条件、必填参数、规则来源、验证方法、严重级别；
- 参数是规范硬约束、项目约束、设计建议还是待确认假设。

任何数字参数都必须来自适用标准、经确认的项目标准或明确的设计输入。R0 不在代码里硬编码“内部路一律 6m”或“消防路一律某个宽度”。

中国城市道路标准是单独的来源路线。住建部曾发布 CJJ 37-2012《城市道路工程设计规范》的公告：[住建部公告](https://www.mohurd.gov.cn/gongkai/zc/wjk/art/2012/art_17339_208843.html)。本次初步检索未完成该标准当前状态、修订/替代关系和全部相关条文的正式核验；在核验前不得将它直接作为当前可执行 Profile。地块内部道路、消防通行及地方标准也需分别查明适用依据。

## 5. 分级如何影响几何生成

- **Road corridor** 表示一条连续的设计走廊/道路身份；它可由多个 segment 组成。
- **Road segment / edge** 应在设计 Profile 或几何控制条件发生变化处分段。分段不应破坏道路走廊身份。
- **Junction node** 应保存相交道路的类别、优先关系（如果有依据）、交角、控制方式、设计车辆及需要的转弯空间。
- **中心线** 先满足控制点、连通、避让与适用的几何约束，再拟合 Line/Arc/Clothoid 等元素；不能因为分类相同就强迫所有道路使用同一曲线规则。
- **横断面** 由 Profile 组件组合产生，沿路线的变化应形成可检查的过渡段。
- **交叉口** 根据相交道路类别、交角、交通组织、设计车辆、场地限制和适用标准选模板；不得对所有节点使用相同 buffer/fillet。
- **道路面** 从中心线、横断面和节点几何共同生成，并检查有效 Polygon、缝隙、重叠、自交和路缘连续性。

## 6. 候选数据模型（仅示意）

```yaml
road_corridor_id: R-COR-001
classification_scheme: project_site_road_v1
network_hierarchy:
  value: site_primary
  status: proposed
primary_function: access_and_internal_distribution
permitted_modes: [motor_vehicle, pedestrian]
special_designations: [fire_access_candidate]
physical_cross_section:
  lanes: null
  carriageway_width_m: null
  sidewalks: unknown
  cycle_facility: unknown
design_profile_id: null
classification_evidence:
  - source_type: sketch_annotation
    locator: null
    supports: site_primary
  - source_type: graph_context
    supports: internal_distribution
confidence: medium
review_state: needs_review
unresolved_questions:
  - confirm whether fire access is a mandatory requirement
```

这里的 `site_primary`、`fire_access_candidate` 等只是示例值，不是国家标准分类或合规结论。

## 7. 新增 Benchmark 与验收问题

- `BEN-ROAD-009`：同一场地中主通行道路、组团支路、局部/服务道路的分轴分类。
- `BEN-ROAD-010`：几何相同但用途不同（消防路线 vs 步行路径），验证语义不能只靠外形。
- `BEN-ROAD-011`：连续道路的 Profile/横断面变化与过渡段。
- `BEN-ROAD-012`：主次道路相交时按类别和节点上下文生成不同交叉口。
- `BEN-ROAD-013`：类别不明时输出候选、证据与人工确认请求，不静默猜测。
- `BEN-ROAD-014`：特殊用途与几何条件冲突时报告不满足/信息不足。
- `BEN-ROAD-015`：标准版本、地域或项目规则冲突时阻断不受支持的参数应用。

评价指标包括：分类准确性（仅对有可靠 ground truth 的案例）、unknown/needs-review 的适当使用率、证据可追溯性、错误自动确认率、Profile 参数来源完整性、过渡段几何连续性、交叉口可行性及规范冲突检出率。不能只用分类 accuracy 评价。

## 8. 初步研究结论（仍是候选）

`KNO-ROAD-CLASS-001`（candidate）：道路类别需要被建模为“分类体系 + 路网层级 + 服务功能 + 通行权限/方式 + 特殊用途 + 物理横断面 + 设计 Profile”的组合，而不是一个单标签。分类与几何/尺寸之间需要通过带来源、版本和适用范围的 Profile 显式连接。该结论的架构动机由 OSM 分类说明支持；中国工程参数与标准映射仍待规范来源核验和 Benchmark 验证。

## 9. 本研究线下一步

1. 核验 CJJ 37-2012 及相关强制性通用规范、消防/居住区/无障碍等来源的现行状态、适用范围与交叉引用；先建立标准关系图，不直接抄参数。
2. 对比 OSM 分类模型、Street Generator 的 typed configuration/rules engine，以及可用的道路网络/横断面开源实现。
3. 定义第一版 Road Profile schema 与规则优先级，但暂不填入未经核验的默认数值。
4. 为 BEN-ROAD-009..015 制作可重复的小型几何/语义样例，并确定哪些属性由用户确认、哪些可以低风险推断。
