# BATCH-002 — Sketch Calibration, Semantic Candidate & Trace Geometry

**状态：** `ready-for-A1 / unclosed`（首轮来源获取、本地合成 Benchmark 与真实 Benchmark 数据合同已完成；A1 尚未执行；Tier B/C 真实实测仍缺）  
**计划：** `CPL-SKETCH-001-r1`  
**研究时点：** 2026-10-26  
**研究模式：** `technical-algorithm`  
**保证级别：** `high-assurance`

## 1. 本批决策问题

对于建筑/规划总平草图（扫描、手机照片、导出图片或与红线 CAD 叠加的草图），哪些开源方法可以把输入稳定地转化为：

1. 明确坐标状态的 Source Raster；
2. 可复核的比例/透视/控制点变换；
3. 建筑、道路、绿地等语义候选；
4. 不擅自专业化的 Trace Geometry；
5. 带 provenance、confidence、review state 的对象，供后续道路拓扑、建筑 footprint 和 2D/3D 统一对象使用。

## 2. 精确范围

- **主要 Coverage：** `COV-01..04`。
- **关联 Coverage：** `COV-05`（几何清洗入口）、`COV-10`（建筑 footprint 输入）、`COV-13`（坐标与对象身份）、`COV-20`（Source→Trace provenance）。
- **不在本批完成：** 道路工程 alignment、道路 Profile、建筑 typology/户型、3D massing、日照、CAD 图层/线型、IFC 编译和中国规范参数。

## 3. 必需来源路线

| 路线 | 对象 | 本批目标 | 当前状态 |
|---|---|---|---|
| 透视/几何校准 | OpenCV | homography / perspective transform、contour、Douglas–Peucker 的精确定义与边界 | 官方文档已读；本地合成测试已做 |
| 地理/项目坐标 | GDAL | image-space→georeferenced transform、GCP 与 affine geotransform 的表达 | 官方文档已读；未本地运行 GDAL CLI |
| 开放词汇语义候选 | Meta SAM 3/3.1 | text/visual prompt segmentation 的能力、checkpoint/许可和输出边界 | 官方仓库/项目页已读；本地模型未运行 |
| GIS-aware mask→vector | SamGeo | SAM family 的 geospatial I/O、vector export、QGIS/GeoJSON 路线 | README/LICENSE 已读；未本地运行 |
| 通用 bitmap trace | Potrace | 位图→Bezier/line trace 的适用性、失真和许可 | 官方说明/算法论文已读；未本地运行 |
| 建筑图相邻路线 | RedrawAI、Raster2Seq、floorplan-to-vector | 观察“分割→矢量→拓扑→验证”“scale 不猜”“review state”实践 | README/许可部分已检查；仅作为相邻架构参考 |
| 反例/失败路线 | 项目 issue、方法论文、本地合成测试 | 找到边界模糊、过度简化、校准误差、domain shift 等失败模式 | 已部分覆盖；真实场地图 Benchmark 仍缺 |

## 4. 当前已有 RUN

见 `run-log.jsonl`。本批已经执行：官方文档/仓库发现、SAM 3/SamGeo 许可与 README 检查、相邻 floorplan 项目检查，以及 `LOCAL-SKETCH-001` 合成 Benchmark。

## 5. A1 前置缺口

1. 真实 Benchmark 数据合同已定义，但尚无 Tier B/C 场地草图作为固定实测样例；当前本地测试仅为合成几何，不代表真实草图性能。
2. SAM 3/3.1 checkpoint 需要授权访问且本环境未运行；其对建筑/规划草图的真实 zero-shot 准确性未验证。
3. 搜索引擎总命中量/分页完整性不可得；发现搜索 `truncation=unknown`。
4. 相邻 floorplan 项目与场地总平域存在 domain gap，不能直接外推。
5. Potrace/OpenCV 简化的参数阈值尚未由真实样例分布校准，不能冻结 epsilon 或边界容差。
6. 独立人工真值的文件合同与标注规则已定义，但尚未形成实际 Tier B/C truth package。

## 6. 停止条件

本批只推进到“入口技术路线可比较、误差与状态模型可定义、真实 Benchmark 需求明确”。不得因为某个模型能生成 mask 就冻结语义模型，也不得因为 DXF/SVG 能导出就声称得到专业 CAD。

当前已满足“可提交 A1”的工作条件：来源路线可回读、失败边界已记录、合成 Benchmark 可复现、真实 Benchmark 所需真值合同已定义。由于 Tier B/C 真实样例缺失，本批即使通过 A1 也不能宣称真实设计性能；当前保持未关闭，等待独立 A1。
