# R0 Research Gap Matrix v0.1

**目的：** 在架构综合后明确“还需要研究什么”，避免把普通实现 bug 当作研究问题继续消耗 R0。

| Gap | 研究价值 | 当前证据 | 下一阶段处理 |
|---|---|---|---|
| 真实场地草图 → Trace | 极高 | 只有合成基线与数据合同 | 获取 Tier B/C paired cases；这是下一轮真实研究核心之一 |
| 道路工程 alignment + 中国 Profile | 极高 | 项目/算法候选，标准关系未闭合 | 需要正式道路 Benchmark 和适用标准研究；不靠视觉平滑替代 |
| Building regularization 阈值 | 高 | 源码、Issue、合成 gate | 用真实设计草图校准 preserve/candidate/review 边界 |
| IFC round-trip | 高 | API/源码研究 | 正式开发前做最小 IFC spike；不是继续文献搜集 |
| DXF validator hardening | 中等研究 / 高工程 | 用户本地复核已暴露明确缺陷 | 转正式开发验收，不再 R0 修代码 |
| AutoCAD semantic round-trip | 高 | 已有 core-engine 首证据 | 后续扩展 GUI/LibreCAD/FreeCAD matrix；按 semantic policy 比较 |
| 真实环境模拟 | 高 | 合成射线 + 官方工具研究 | 使用独立太阳/辐射引擎做固定 fixture 对照 |
| 设计院 Profile | 极高 | 只有地方标准样例 | 未来拿到真实院标/模板/CTB/DWT 后建可追溯 Profile |
| 户型/建筑方案自动生成 | 暂低 | 未研究 | 明确推迟；先证明 site-model 闭环 |
| DWG production delivery | 中高 | 开源生态复杂，未冻结 | 正式开发阶段评估 ODA/AutoCAD/LibreDWG 等边界 |

## 研究阶段退出原则

如果一个问题已经满足：

1. failure mode 已明确；
2. 修复方向不影响整体架构；
3. 只剩代码实现与回归；

则从 R0 研究 backlog 移到 development acceptance contract，不继续以“研究”名义修实现。
