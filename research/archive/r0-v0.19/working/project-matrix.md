# 第一批开源项目研究矩阵（校准版）

> 这是 `BATCH-CAL-001` 的候选矩阵，不代表技术选型。

| 项目 | 主要 CAP | 第一轮真正要研究的问题 | 目前角色判断 | 证据状态 |
|---|---|---|---|---|
| OpenCV | SKETCH-01/03, GEO-04 | contour / approxPolyDP 对草图轮廓能保留多少意图？噪声与文字怎样处理？ | 基础图像/轮廓工具 | 官方文档已校准 |
| SAM 2 | SKETCH-02/04 | promptable segmentation 能否帮助建筑/道路/绿地交互分割？错误边界如何暴露置信度？ | 语义候选生成，不做最终几何 | 官方仓库已校准 |
| Shapely / GEOS | GEO-01..04, ROAD-07/08 | node/snap/offset/polygonize/boolean 对 road graph 与道路面是否足够稳健？ | 2D 几何主候选 | 官方文档已校准 |
| CGAL | GEO-03, ROAD-02/07/08 | straight skeleton/offset 的鲁棒性与许可是否适合生产？哪些功能可作为 Shapely 的补强？ | 高鲁棒几何候选，许可需单独评估 | 官方文档/许可已校准 |
| OSMnx | ROAD-01/05 | simplify_graph / consolidate_intersections 的 node/edge 修复思想怎样迁移到草图 Road Graph？ | 拓扑算法参照 | 官方文档已校准 |
| PyGeoOps | ROAD-02 | polygon centerline / medial axis 在道路轮廓、窄区、分叉情况下的失败模式？ | centerline candidate | 官方仓库已校准 |
| Clothoids | ROAD-04 | G1/G2 clothoid fitting 是否适合从控制点生成工程路线？如何与道路规范参数连接？ | alignment 候选核心 | 官方仓库已校准 |
| Street Generator | ROAD-06, AGT-01/02 | typed StreetConfig + rules engine + renderer 分离方式能否迁移到道路横断面？ | 架构参考/横断面参考 | 官方仓库已校准 |
| IfcOpenShell | 3D-02/03/04, OUT-03 | Axis/Footprint/Body/Placement 能否成为 2D↔3D identity 的稳定载体？ | BIM/语义主候选 | 官方文档已校准 |
| Bonsai | 3D-04, OUT-03/04 | 作为 IFC 可视化/人工修订/QA 环境的价值；哪些能力不应放在 Agent 核心？ | 交互与 QA 候选 | 官方站点已校准 |
| FreeCAD BIM | BLDG/3D, OUT | 参数化建筑实体与 2D Draft→3D BIM 工作流是否适合二级编辑后端？ | 二级 authoring 后端候选 | 官方文档已校准 |
| COMPAS | GEO/3D/AGT | 是否适合作为脱离具体 CAD 的 AEC 数据结构/算法层？与自研 IR 的边界？ | AEC 计算框架候选 | 官方仓库已校准 |
| UrbGEN | BLDG-02..04 | typology + FAR/BCR/height/setback 的生成逻辑怎样抽象成规划候选器？ | massing 知识来源/算法参考 | 官方仓库已校准 |
| Ladybug Tools | ANL-01/02 | sun vectors / shadow / solar access 如何接入轻量 massing，并怎样与中国日照规范隔离？ | 环境分析候选 | 官方资料已校准 |
| momepy | ANL-03 | 哪些建筑/街道形态指标适合做设计反馈而非最终规范判断？ | 城市形态评价候选 | 官方文档已校准 |
| ezdxf | OUT-01/02/05 | 如何把专业模型确定性地编译为 DXF，并建立 round-trip validator？ | CAD 输出层主候选 | 官方文档/许可已校准 |

## 当前优先级

### P0：必须深入

Shapely/GEOS、OSMnx、PyGeoOps、Clothoids、IfcOpenShell、ezdxf。

### P1：必须比较/补强

OpenCV、SAM 2、CGAL、COMPAS、Ladybug。

### P2：架构与领域知识参考

Street Generator、UrbGEN、momepy、FreeCAD BIM、Bonsai。

优先级只表示 R0 调研顺序，不表示最终采用概率。
