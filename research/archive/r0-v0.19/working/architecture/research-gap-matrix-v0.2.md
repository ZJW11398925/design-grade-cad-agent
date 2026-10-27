# R0 Research Gap Matrix v0.2

**目的：** 把尚未完成的问题按“阻断架构 / R1 spike / 正式开发 hardening / 未来扩展”重新分类。

| Gap | 类型 | 架构影响 | 当前证据 | 下一步 |
|---|---|---|---|---|
| 真实场地草图 → Trace | R0/R1 高风险证据 | 高 | 合成基线 + 数据合同 | Architecture Challenge 后优先获取 Tier B/C case |
| 道路 engineering alignment + 中国 Profile | R0/R1 高风险证据 | 高 | 算法/标准候选未闭合 | 用 2–3 个真实/半真实道路 fixture 做 targeted study |
| Building regularization gate | R1 calibration | 中高 | 源码/Issue/合成 gate | 用真实草图校准 preserve/candidate/review |
| Canonical IR 存储技术 | R1 implementation spike | 中 | 逻辑 schema 已有 | 在 R1.0 比较 JSON/SQLite/PostGIS/typed models，不在 R0 选库 |
| IFC Footprint/Body/Placement round-trip | R1 mandatory spike | 高 | API/源码证据 | 真实运行一次最小 round-trip |
| DXF validator hardening | Development acceptance | 低架构/高工程 | 用户复核已给明确 failure | 按 DEV-CAD 合同实现，不再 R0 研究 |
| AutoCAD semantic round-trip 扩展 | R1/R2 interoperability | 中 | core engine 首证据 | 后续 GUI/LibreCAD/FreeCAD matrix |
| 独立太阳/阴影引擎 | R1 mandatory spike | 中高 | 合成算法 + 官方研究 | 固定 fixture 对照真实引擎 |
| 真实设计院/项目 Profile | R1 high-value evidence | 高 | 地方标准样例 | 获取一份小型真实 profile/template/CTB/DWT 资产 |
| Shapely/CGAL 最终分工 | R1 implementation decision | 中 | 候选研究 | 只在具体失败 benchmark 触发 CGAL 引入 |
| DWG production delivery | R2/production | 中 | 未冻结 | DXF 闭环稳定后再做 |
| 户型/自动规划生成 | Future | 低 | 未研究 | 明确延期 |

## R0 研究退出原则

某问题同时满足以下条件时，应退出 R0：

1. failure mode 已明确；
2. 修复不会改变模块边界/真值模型/权限模型；
3. 只剩编码、兼容性、CI 或性能工作；
4. 已有明确 development acceptance test。

## R0 Architecture Exit Review 需要回答的 6 个问题

1. Canonical truth 是否存在两个竞争 owner？
2. 任一第三方 adapter 更换时是否会迫使 canonical schema 重构？
3. 一个对象变化能否定位所有 stale downstream，而不全量重建？
4. Agent 是否有任何路径可以绕过 rule/validator/human authority？
5. unsupported/unknown 是否能被 block，而不是静默默认？
6. MVP 是否能在不实现全部未来功能的情况下验证这套架构？
