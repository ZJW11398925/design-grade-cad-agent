# R0 能力树（CAP）

> 本文件回答“系统必须会什么”，不回答“哪个项目最强”。状态均为 provisional。

## A. 草图到语义

- `CAP-SKETCH-01` 图像校准：旋转、透视、畸变、比例/控制点。
- `CAP-SKETCH-02` 语义分割：建筑、道路、绿地、红线等。
- `CAP-SKETCH-03` 忠实轮廓追踪：生成 Trace Geometry。
- `CAP-SKETCH-04` 置信度与人工确认：不确定区域可交互修订。

## B. 几何清洗与拓扑

- `CAP-GEO-01` 去除重复点/尖刺/微小噪声。
- `CAP-GEO-02` snap / node / split / polygonize。
- `CAP-GEO-03` 自交、无效 polygon、洞、重叠修复。
- `CAP-GEO-04` 受控简化：保留关键点和共同边界。
- `CAP-GEO-05` Source→Trace→Professional 几何 diff。

## C. 道路

- `CAP-ROAD-01` 从草图恢复 Road Graph。
- `CAP-ROAD-02` 从道路轮廓得到 centerline candidate。
- `CAP-ROAD-03` 从手绘单线得到关键控制点与 candidate alignment。
- `CAP-ROAD-04` 工程路线拟合：line / arc / clothoid 等。
- `CAP-ROAD-05` 交叉口节点合并、边重连、T/X/Y/环岛识别。
- `CAP-ROAD-06` 横断面参数模型。
- `CAP-ROAD-07` centerline + cross-section → road surface。
- `CAP-ROAD-08` 交叉口道路面生成与无缝 Boolean。
- `CAP-ROAD-09` 纵断面/高程接口（R0 可延后，但数据模型需预留 Z）。

## D. 建筑与场地

- `CAP-BLDG-01` footprint 正规化并保留设计意图。
- `CAP-BLDG-02` typology 识别/建议，而不是直接猜户型。
- `CAP-BLDG-03` 高度、层数、层高、进深等 massing 参数。
- `CAP-BLDG-04` FAR/BCR/退界/高度等约束驱动候选体量。
- `CAP-BLDG-05` 建筑与道路/红线/绿地的空间冲突检测。

## E. 3D与BIM

- `CAP-3D-01` footprint → extrusion massing。
- `CAP-3D-02` 统一 Object Placement / 坐标系。
- `CAP-3D-03` 同一对象保存 Axis / Footprint / 3D Body 等多 representation。
- `CAP-3D-04` IFC/BIM 语义对象与类型。

## F. 分析

- `CAP-ANL-01` 太阳位置/太阳向量。
- `CAP-ANL-02` 阴影与太阳时数。
- `CAP-ANL-03` 道路/建筑形态指标。
- `CAP-ANL-04` 规划约束校核接口。

## G. CAD/BIM交付

- `CAP-OUT-01` DXF/DWG 友好实体与 CAD 图层体系。
- `CAP-OUT-02` linetype / lineweight / text / dimstyle / blocks / layouts。
- `CAP-OUT-03` IFC 输出与回读。
- `CAP-OUT-04` PDF/PNG 渲染用于视觉 QA。
- `CAP-OUT-05` round-trip：生成→第三方打开→回读→结构比较。

## H. Agent治理

- `CAP-AGT-01` Typed Intent / CAD-IR。
- `CAP-AGT-02` 规则引擎覆盖 LLM 自由决定。
- `CAP-AGT-03` 变更 proposal + diff + reason。
- `CAP-AGT-04` Validator 失败→局部修复，而不是全图重画。
- `CAP-AGT-05` 人工锁定对象/控制点，Agent 不得擅改。
