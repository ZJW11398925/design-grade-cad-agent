# BATCH-001 — Road Semantics & Design Profile

**状态：** `in-progress`（首轮正式获取已执行；A1 尚未执行；不得视为批次关闭）  
**计划：** `CPL-ROAD-001-r1`  
**研究时点：** 2026-10-26  
**研究模式：** `technical-algorithm`  
**保证级别：** `high-assurance`

## 1. 本批决策问题

如何将草图/底图中的道路对象区分为不同的路网角色、服务功能、通行权限和特殊用途，并把这些语义可靠地解析成带地域、标准版本、适用条件和证据来源的设计 Profile，供后续中心线、横断面、交叉口、道路面与 CAD/BIM 生成使用？

## 2. 精确范围

- **主要 Coverage：** `COV-21` 道路层级与功能分类；`COV-22` 道路设计 Profile 与标准映射。
- **关联 Coverage：** `COV-23` 分级道路的几何生成与过渡；`COV-08` 横断面/道路面；`COV-09` 交叉口；`COV-18` 规范规则引擎；`COV-19` Validator。
- **不在本批内完成：** 草图分割算法全面比较、完整道路中心线拟合 Benchmark、全部中国标准条文抽取、生产代码实现、任何道路设计参数的最终定值。

## 3. 来源路线与研究对象

| 路线 | 对象 | 目标 | 本批状态 |
|---|---|---|---|
| 类型化横断面与规则引擎 | Street Generator | 审查类型模型、规则执行边界、测试结构、许可状态 | 已做仓库元数据和部分源码审查 |
| 概念性横断面与人机协作 | Streetmix | 界定概念设计/公众参与价值，核验代码许可 | README 与 LICENSE 已读；几何能力未源码审计 |
| 路网分类词汇 | OpenStreetMap `highway=*` | 区分网络角色分类与法定等级/物理特征 | 官方 Wiki 已读 |
| 道路图/车道模型 | SUMO | 审查 edge/lane/junction/connection 与类型默认值映射 | 官方文档已读 |
| 中国规范权威来源 | 住建部公告及相关标准入口 | 建立标准关系图，确认适用范围/版本/生效状态 | 公告线索已获取；全文附件访问失败，条文未抽取 |
| 反例/独立验证 | issue、失败报告、独立案例 | 寻找错误默认值、分类映射失败、规则缺口 | 尚未覆盖，阻断 A1 |

## 4. 已执行 RUN

精确运行记录见同目录 `run-log.jsonl`；候选发现命中见 `discovery-hits.jsonl`；稳定定位见 `source-locators.md`。本轮没有下载并保存完整网页快照；对仓库代码使用 GitHub 文件路径和返回的 blob SHA 作为稳定版本定位，不复制无明确许可的完整代码。

## 5. A1 前置条件与阻断项

以下事项未解决前，不得将本批标为 `acquisition-batch-reviewed`，也不得声称首轮来源路线完整：

1. 网页搜索结果没有返回引擎总命中量/分页完整性；相关 RUN 的 `truncation=unknown`。
2. 住建部 GB 55011-2021 附件下载返回缓存访问失败；GB 55037-2022 与 GB 55019-2021 页面在本轮打开时超时。当前只有公告层信息，没有条文级抽取。
3. CJJ 37-2012（2016 年版）的当前状态、修订/替代关系及与 GB 55011-2021 的条文关系仍未核实；不得推断整个 CJJ 37 已被废止。
4. 尚未系统获取项目 issue、独立失败报告和独立复现材料。
5. Street Generator 的 GitHub API 仓库元数据 `license=null`；在许可澄清前只可作为架构研究对象，不作为可直接复制/集成的开源依赖。

## 6. 暂定停止条件

只有当必需来源路线均有实际执行记录、所有命中有稳定定位、截断状态可解释、失败和缺失路线已记录，并且独立复核者逐项检查后，才请求 A1。A1 仅可授权本批关闭与整理，不代表道路 Profile 已合规，也不授权把其他国家的参数移植到中国场景。

## 7. Third-wave route update (RUN-001-09)

- **Issue route partially executed:** GitHub issue records `eclipse-sumo/sumo#7615`, `#7119`, and `#15013` were read. They expose concrete negative-test patterns around inconsistent OSM typemap defaults, implicit pedestrian permissions, and audit logs retaining undone join operations. These are project-maintained issue reports, not independent external replications; the search is capped and total counts are unavailable.
- **Street Generator license route checked:** root contents contain no license/copying-like filename; exact `LICENSE` and `COPYING` API paths return 404; README has no license statement; metadata remains `license=null`. Permission to reuse remains unresolved.
- **Still blocking A1:** search-result truncation is unknown; official standard full-text/status routes remain incomplete; issue search completeness is unknown; no independent reproduction route has been established. This update reduces one gap but does not close the batch.
- **Scope stop:** do not expand this batch into exhaustive Chinese road parameter extraction. Only use genuinely different source routes to address A1 criteria; if blockers remain, preserve the batch as unclosed and return to global Coverage prioritization.
