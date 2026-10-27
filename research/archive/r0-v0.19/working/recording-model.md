# 讨论与研究记录模型

目标：避免未来讨论变成“我记得某个项目好像能做这个”。所有重要内容使用稳定 ID。

## CAP — Capability

系统必须具备的能力。CAP 不绑定具体实现。

示例：

`CAP-ROAD-05`：交叉口节点合并、边重连、T/X/Y/环岛识别。

## KNO — Knowledge

从来源、代码或 Benchmark 得到的可复用知识。

建议字段：

- `id`
- `question`
- `claim`
- `evidence_level`: project-claim / official-doc / code-inspected / local-test / independent-test
- `source_refs`
- `applies_to`
- `limits`
- `benchmark_refs`
- `status`: candidate / reviewed / superseded

示例：

`KNO-ROAD-001`：OSMnx 的 intersection consolidation 能把邻近节点聚合为一个交叉口，并可重建/重连 edge geometry；它可作为 Road Graph 修复算法参照，但不是直接用于草图道路专业设计的完整方案。

## BEN — Benchmark

固定输入、期望性质、评价方法和失败模式。项目之间使用相同 BEN 才可比较。

## DEC — Decision

只有达到足够证据等级后才建立架构决定。

建议字段：

- `id`
- `decision`
- `scope`
- `alternatives`
- `evidence_refs`（KNO/BEN）
- `reasoning_summary`
- `tradeoffs`
- `revalidation_triggers`
- `status`: proposed / accepted / superseded

## SRC / RUN / RAW

底层证据仍按 `conduct-traceable-research` 保存：

- RUN：我们实际搜了什么/读了什么。
- RAW：搜索返回、下载材料或稳定定位。
- SRC：进入深化的规范来源身份。
- SCL/FND/EVR/AJG：只有真正进入证据深化后再形成。

## 讨论原则

以后可以直接说：

- “复查 CAP-ROAD-04”；
- “KNO-GEO-006 是否足以支持 DEC-ROAD-002？”；
- “用 BEN-ROAD-005 比较 Shapely 与 CGAL 的表现”。

这样聊天中的观点不会自动升级为项目事实。
