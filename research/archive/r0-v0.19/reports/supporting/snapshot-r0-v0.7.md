# R0 v0.7 工作区快照说明

**快照日期：** 2026-10-26  
**性质：** 研究工作区快照；不是生产发布，不代表技术选型或标准合规结论。

## 本次推进

1. **BATCH-003 有界暂停：** 建筑 footprint regularization 研究形成规则化拒绝门、场地级拓扑合同和 `LOCAL-BLDG-002` 合成 Validator probe。重点结果：单体 IoU 很高仍可能破坏共享边或合并对象；真实 IFC round-trip 未运行。
2. **BATCH-004 有界暂停：** `LOCAL-CAD-003` 在 ezdxf 1.4.4 下完成合成 DXF 写入/重读、audit 和 Profile Validator，6 项断言通过。
3. **来源型规范样例：** 对 DB11/T 1948-2021 进行少量官方条款提取，建立 `db11t1948-profile-extract-v0.1.yaml`，并运行 `LOCAL-CAD-004`。可测子项通过，重叠面 mutant 被发现，但坐标基准因使用合成本地坐标而 blocked，完整合规状态明确为 false。
4. **Skill 检查：** 只读布局检查对 5 个显式必需文档通过；该检查未评估实际 RUN 覆盖、研究完成或发布授权。
5. **主线回流：** 下一条计划线是 BATCH-005 环境分析与规划反馈（COV-14..15），范围先限于太阳位置、日照/阴影/遮挡的输入依赖与结果 revision，不扩张到完整能耗/CFD。

## 当前批次状态

- BATCH-001：`bounded-paused / unclosed`
- BATCH-002：`ready-for-A1 / unclosed`，需独立 A1；当前线程不自行批准
- BATCH-003：`bounded-paused / unclosed`
- BATCH-004：`bounded-paused / unclosed`
- BATCH-005：`planned / not-started`

## 重要限制

- 早期广搜/部分 Web 搜索的截断状态为 `unknown`，不能宣称获取完整或 A1 通过。
- 当前环境没有 LibreCAD/AutoCAD/FreeCAD/IfcOpenShell，第三方 CAD/BIM round-trip 与真实 IFC 写入/重读未执行。
- DB11/T 1948-2021 仅是北京市国土空间详细规划的来源样例，不是用户项目的默认标准。
- 用户项目的真实设计院 Profile、适用地域/专业/阶段和批准模板仍未确认。
- 未创建正式 governed package；`research_complete=false`、`release_authorized=false`。
