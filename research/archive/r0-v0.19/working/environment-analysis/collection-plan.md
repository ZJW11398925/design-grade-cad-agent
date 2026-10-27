# BATCH-005 采集计划：环境分析与规划反馈

**状态：** `bounded-checkpoint / unclosed`。已执行首轮官方来源获取与 `LOCAL-ENV-001` 合成基线；不等于 A1、生产模拟验证或法规合规。

## 1. 唯一决策问题

在建筑 Footprint/3D Massing 进入同一对象模型后，如何用可追溯的开源分析工具计算日照、阴影、遮挡与空间环境指标，并把结果反馈到规划方案中，而不是只输出漂亮的 3D 预览？

## 2. Coverage 与依赖

- 主要 Coverage：`COV-14` 日照/阴影/遮挡计算，`COV-15` 环境指标反馈与方案比较。
- 上游依赖：`COV-10..13` 建筑 footprint、height/floors provenance、Body/Placement、场地几何；`COV-16..19` 负责版本化输出与 Validator。
- 结果必须能追溯到具体的 geometry revision、height source、coordinate frame、north orientation、site location、date/time/timezone 与 simulation settings。

## 3. 本批范围

### 纳入

- 太阳位置/太阳路径与场地坐标基准；
- 建筑高度、地形/地面高程、北向与周边遮挡体对阴影的影响；
- 指定日期/时刻的阴影几何、累计日照时长/日照窗口、建筑或开放空间的遮挡率；
- 几何/高度 revision 变化如何使旧分析结果 stale；
- 不同方案间可复现、可解释的指标比较；
- 开源项目的许可、输入要求、输出指标、适用边界和独立 Benchmark。

### 不纳入

- 在没有适用地域/标准来源时直接判定法律意义上的日照合规；
- 完整建筑能耗、HVAC、CFD、微气候/风环境作为本批主任务；
- 将未知高度、未知坐标系或未知北向自动补成 confirmed；
- 把图像渲染的视觉阴影当作可量化的日照模拟结果。

## 4. 首轮候选路线（待精确获取，不是选型）

- Ladybug Tools / Ladybug：太阳位置、日照与环境分析工作流；
- Honeybee-Radiance / Radiance：基于几何和天空/光照条件的光照分析；
- Honeybee-Energy / EnergyPlus：若后续需要能耗模拟，作为独立扩展，不与几何阴影混为一谈；
- momepy：城市形态与空间指标，不能替代物理太阳/光照模拟；
- 轻量太阳几何/射线投射实现：作为可复现基准，不预设其可替代专业模拟。

## 5. 必须建立的 Benchmark

- `BEN-ENV-001` 未知建筑高度：分析结果必须 blocked/estimated，不能伪装成 confirmed。
- `BEN-ENV-002` 北向/坐标系错误：检测到输入基准变化，不能静默复用旧结果。
- `BEN-ENV-003` 建筑 Footprint/Height revision 改变：旧阴影结果标记 stale 并重算。
- `BEN-ENV-004` 邻近建筑高度差：验证遮挡体的高程/高度来源影响结果。
- `BEN-ENV-005` 指定日期/时间/时区：同一方案可重复生成相同太阳位置/阴影结果。
- `BEN-ENV-006` 绿地/公共空间日照：明确指标是直射日照时长、时段覆盖还是遮挡比例，不能混成一个“日照评分”。
- `BEN-ENV-007` 2D 几何与 3D Body 不同步：禁止使用 stale Body 做日照分析。
- `BEN-ENV-008` 周边建筑/地形缺失：输出覆盖范围与缺失环境对象提示。

## 6. 当前检查点与残余风险

已完成：Ladybug/PVlib/NREL SPA/Honeybee-Radiance/momepy 的有界官方来源核验；自研低依赖太阳位置与竖直棱柱射线基线；17 个断言函数直接调用通过；发布值与 Ladybug Sydney 示例在 0.5° 容差内通过；未知高度、缺失上下文、北向变化和 revision stale 均有合成测试。

未完成：pvlib/Ladybug/Honeybee-Radiance 的本地运行；跨季节/纬度误差分布；独立 3D 引擎对照；真实场地数据；地形/复杂 3D；适用法规条款。当前 pytest CLI 在此沙箱中未能干净终止，需在干净运行环境复核。

## 7. 退出条件

- 至少一条可执行的太阳/阴影路线和一条独立参考/验证路线；
- 明确输入坐标、北向、时间、天气/天空模型、建筑高度/地形等参数要求；
- 指标定义可复现且不混淆物理模拟、几何计算与法规判定；
- 几何 revision 与环境分析 stale/rebuild 依赖可验证；
- 真实标准阈值仅在来源、地域、版本、适用范围均核验后才可纳入。
