# Candidate Knowledge Records — BATCH-001

这些是可复用知识的候选记录，不是已审查的正式证据判断。状态均为 `candidate`；不建立架构 `DEC`。

## KNO-ROAD-CLASS-002 — 网络分类不等于工程分类

- **问题：** 能否直接用 OSM `highway=*` 决定中国道路等级与设计参数？
- **候选主张：** 不能。OSM 标签表达道路在整体网络中的角色/重要性，文档明确说明它不必然等于法定分类或物理特征。
- **证据级别：** `official-doc`（仅验证来源的明确表述）。
- **来源：** `HIT-004`；https://wiki.openstreetmap.org/wiki/Key:highway
- **适用范围：** 语义候选和外部底图理解。
- **限制：** 不证明中国工程分类体系的具体条文，也不证明 OSM 属性完整/准确。
- **Benchmark：** `BEN-ROAD-015`, `BEN-ROAD-016`。

## KNO-ROAD-GRAPH-002 — 道路网络、车道与交叉口连接应分层表达

- **问题：** 如何表达道路“相连”与车道“可通行”的差异？
- **候选主张：** SUMO 把 junction/node、edge、lane 和 lane connection 分开表达，可作为数据模型参照；仅有中心线相交不代表所有车道移动都可通行。
- **证据级别：** `official-doc`。
- **来源：** `HIT-005`；https://sumo.dlr.de/docs/Networks/SUMO_Road_Networks.html
- **适用范围：** Road Graph/车道语义设计。
- **限制：** SUMO 的目标是交通仿真，不能直接作为道路设计规范或 CAD 几何内核。
- **Benchmark：** `BEN-ROAD-002`, `BEN-ROAD-012`, `BEN-ROAD-017`。

## KNO-ROAD-PROFILE-002 — 横断面 Profile 与平面道路走廊是不同对象

- **问题：** Street Generator 是否可直接作为完整道路模型？
- **候选主张：** 当前 inspected `StreetConfig` 是按左右顺序排列的横断面组件及宽度，适合研究 typed cross-section + deterministic renderer + validator；它不是完整的中心线/交叉口/纵断面模型。
- **证据级别：** `code-inspected`（Git blob 版本定位明确；未本地运行）。
- **来源：** `HIT-002`, `HIT-003`。
- **适用范围：** Profile 和规则接口设计。
- **限制：** 许可未确认；规则针对德国 RASt；未证明可满足中国设计院要求。
- **Benchmark：** `BEN-ROAD-011`, `BEN-ROAD-012`, `BEN-ROAD-017`。

## KNO-ROAD-RULES-002 — 规则必须带适用条件、版本和来源

- **问题：** 如何避免把一个城市的规则误用于另一种道路？
- **候选主张：** 规则不能只有 `if width < x then fail`；还必须声明适用法域、道路类型、标准版本、适用条件、规则性质、来源条款、严重级别和验证方法。否则 PASS 可能只意味着某个孤立阈值通过。
- **证据级别：** `candidate-synthesis`（由 Street Generator 单一 RASt 规则模块的边界和标准来源问题推导，仍需独立审查）。
- **来源：** `HIT-003`, `HIT-008..011`。
- **适用范围：** RuleSet/Design Profile 架构。
- **限制：** 规则字段设计尚未由完整标准条文验证。
- **Benchmark：** `BEN-ROAD-015`, `BEN-ROAD-018`, `BEN-ROAD-019`。

## KNO-ROAD-DEFAULTS-001 — 默认值不能伪装成规范值

- **问题：** 能否从 OSM/SUMO 的 road type 默认值直接填充设计参数？
- **候选主张：** 不能。SUMO 的 type mapping 用于仿真导入，且官方 OSM import 文档明确警告默认映射值是经验设置、未验证。我们的 Profile 必须标记默认值来源和状态；高影响未知参数不得静默填入。
- **证据级别：** `official-doc` + `candidate-synthesis`。
- **来源：** `HIT-006`；https://sumo.dlr.de/userdoc/Networks/Import/OpenStreetMap.html
- **适用范围：** 缺失值策略、默认值语义。
- **限制：** 该结论并不表示所有默认值都不适用，只说明其不能未经来源/适用性核验就当成工程要求。
- **Benchmark：** `BEN-ROAD-013`, `BEN-ROAD-014`, `BEN-ROAD-018`。

## KNO-ROAD-LICENSE-001 — 可访问源码不等于已获授权复用

- **问题：** 公共 GitHub 仓库是否可以直接纳入产品？
- **候选主张：** 不可以仅凭 public 状态作此推断。Street Generator 的 API metadata 为 `license=null`；在许可证澄清前不复制/集成代码。
- **证据级别：** `official-repository-metadata`。
- **来源：** `HIT-001`。
- **适用范围：** 开源项目筛选与依赖准入。
- **限制：** 需要确认是否有仓库外的独立许可声明；不做法律结论。
- **Benchmark：** `BEN-ROAD-020`。


## KNO-ROAD-STD-002 — 强制性通用规范与配套行业标准必须逐条映射

- **问题：** GB 55011-2021 实施后，能否把 CJJ 37-2012（2016 年版）整部标记为废止？
- **候选主张：** 不能仅凭 GB 55011 的公告这么做。官方公告说现行工程建设标准的相关强制性条文废止、与 GB 55011 不一致的规定以其为准；可访问的二次全文转载列出 CJJ 37 的具体条款 3.4.2、3.4.3、13.3.4。该证据指向“条文级关系映射”，而不是简单的整本标准开/关状态。
- **证据级别：** `official-announcement` + `secondary-text-reproduction`; official attachment verification still missing.
- **来源：** `HIT-008`, `HIT-014`; https://www.mohurd.gov.cn/gongkai/zc/wjk/art/2021/art_17339_761190.html ; https://gf.cabr-fire.com/article-43015.htm
- **适用范围：** 中国城市道路规则库的标准关系与有效性治理。
- **限制：** 二次转载不是原始官方附件；不能仅凭本记录确认 CJJ 37 全部其余条文仍然适用或当前版本状态。
- **Benchmark：** `BEN-ROAD-015`, `BEN-ROAD-019`。

## KNO-ROAD-DEFAULTS-002 — 道路类型默认值可能在跨字段语义上产生冲突

- **问题：** 一个道路标签/类型能否安全地推导方向、允许通行方式和道路设施属性？
- **候选主张：** 不应将单一标签直接扩展为整组隐式属性。SUMO issue #7615 报告了 `highway=path` 与默认 `oneWay` 组合造成的自行车网络约束；issue #7119 讨论默认行人权限与独立人行道边的语义差异。它们提供了应加入负面 Benchmark 的历史案例。
- **证据级别：** `project-issue-report`；问题记录可回读，但不是独立复现。
- **来源：** `HIT-016`, `HIT-017`；https://github.com/eclipse-sumo/sumo/issues/7615 ; https://github.com/eclipse-sumo/sumo/issues/7119
- **适用范围：** 道路类型映射、access/permitted_modes、默认值与覆盖规则。
- **限制：** 两个 issue 均为历史且已关闭；不能推断同样缺陷仍存在于当前版本，也不能将其作为中国道路设计规范证据。
- **Benchmark：** `BEN-ROAD-016`, `BEN-ROAD-018`, `BEN-ROAD-019`。

## KNO-TRACE-001 — 几何编辑历史不能等同于最终几何状态

- **问题：** Agent 的 join/snap/repair 日志能否直接作为最终几何的事实记录？
- **候选主张：** 不可以。SUMO issue #15013 报告 `junctions.join-output` 可能记录后来被撤销的中间 join 操作。因此需要分开保存 proposal、apply/undo 事件、当前几何状态和导出审计结果。
- **证据级别：** `project-issue-report`；项目 issue 可回读，尚未独立复现。
- **来源：** `HIT-018`；https://github.com/eclipse-sumo/sumo/issues/15013
- **适用范围：** `COV-20` provenance/change tracking，及拓扑修复与验证日志。
- **限制：** 该 issue 说明的是输出日志可能包含已撤销操作，不等于最终网络几何错误；不能直接推断其他软件也有同样行为。
- **Benchmark：** `BEN-ROAD-017`, `BEN-ROAD-020`。
