# BATCH-005 候选知识记录

**状态：** `bounded-checkpoint / unclosed`；以下是来源支持的候选知识，不是最终技术选型。

## KNO-ENV-001 — 输入是物理结果的一部分

太阳位置至少依赖地点经纬度、时间及时间基准/时区；场地阴影还依赖项目坐标系、北向定义、建筑 footprint/height/base elevation、周边遮挡体及其覆盖范围。任何未知项都必须作为状态暴露，而不是默认为 0、默认正北或随意猜一个高度。

证据：Ladybug `Sunpath` API 与官方测试；pvlib `spa_python` API；本地 `LOCAL-ENV-001` 的 naive datetime / north rotation / unknown-height tests。

## KNO-ENV-002 — 指标必须拆开命名

- **太阳位置**：方位角、太阳高度角或向量。
- **几何阴影/直射日照可见性**：给定时刻与给定几何的射线可见性。
- **采样直射日照时数**：由明确时间采样与步长汇总，必须说明采样间隔。
- **气候数据驱动的日照/辐射**：依赖 EPW/WEA 等气象输入与模型设置。
- **室内 daylight metrics**：如 DA/cDA/UDI，依赖传感器网格、占用时间表、照度阈值及模拟方法。
- **法规合规判断**：另需适用地域、标准版本、测点/计算规则、阈值和完整输入；以上任何工具的分析输出都不能自动替代这一层。

证据：Honeybee-Radiance Direct Sun Hours、Annual Daylight、Cumulative Radiation 官方 recipe 文档；Ladybug direct sun hours 文档；momepy 形态分析文档。

## KNO-ENV-003 — 低依赖几何基线有价值，但不是生产模拟

本地 Shapely 射线/竖直棱柱探针在合成场景中可以识别遮挡、未知高度和缺失环境上下文，并能通过依赖指纹将高度 revision 变化转成 stale 状态。它只适用于明确定义的平面坐标、竖直棱柱、给定时刻的几何可见性，不能代表复杂 3D、气候驱动 daylight、反射、地形或法规计算。

证据：`LOCAL-ENV-001`；17 个断言函数通过。pytest CLI 在当前沙箱未能正常结束，因此测试运行器仍需在干净环境复核。

## KNO-ENV-004 — 工具角色应分层

- **pvlib / NREL SPA**：高精度太阳位置候选；pvlib BSD-3-Clause，当前沙箱未能安装运行。
- **Ladybug Core**：太阳路径、天气文件与早期设计分析候选；当前仓库 LICENSE 为 AGPL-3.0，部署/分发方式需做许可证审查。
- **Honeybee-Radiance / Radiance**：更可扩展的传感器网格直射日照与 daylight/radiation 分析候选；仓库 LICENSE 为 AGPL-3.0，当前沙箱未运行。
- **momepy**：建筑/街道形态、密度、街景剖面和路网连通性指标候选；BSD-3-Clause；不能替代物理太阳/阴影模拟。

这只是角色映射，不是最终技术栈。总搜索量/分页完整性未知。

## KNO-ENV-005 — 结果必须与依赖 revision 绑定

本地依赖指纹试验表明，canonical JSON 对高度 revision 的改变能产生不同 SHA-256，并识别旧结果 stale。实际系统仍须把 footprint、body、height、placement、terrain、north、location/time、sensor grid、context coverage、weather/sky 与方法版本纳入 dependency manifest，并针对每类指标做依赖最小化/过期规则；哈希相同只证明输入声明相同，不证明模拟物理正确。

证据：`analysis-dependency-contract-v0.1.yaml` 与 `LOCAL-ENV-001`。

## 尚未回答

1. 本地太阳位置近似与 pvlib SPA / Ladybug 的跨季节、跨纬度误差分布如何？
2. 自研射线基线与 Honeybee-Radiance/Radiance 在同一 3D 场景/时间网格下的差异如何？
3. 地形起伏、不同 base elevation、凹多边形、孔洞、斜屋面、复杂 3D mesh 与遮阳构件应采用什么几何表达/精度策略？
4. 用户项目实际使用的坐标系、北向来源、地形与周边建筑数据覆盖如何确定？
5. 是否需要在后续批次接入具体中国日照规范，适用标准和测量/计算条款是什么？本批不做法规判定。
