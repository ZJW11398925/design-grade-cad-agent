# 开源能力归位矩阵 v0.1

**状态：** `provisional-allocation`  
**目的：** 不再按“项目强不强”评估，而按模块角色决定：直接候选、需要封装、只借鉴、外部 Gate，或暂不进入核心。

## 1. 角色定义

- **Core candidate**：有希望进入确定性核心，但正式开发仍需 benchmark/许可/部署复核。
- **Adapter candidate**：适合作为 I/O、格式、模型调用适配层，不应成为 canonical truth owner。
- **Algorithm/reference**：吸收算法或架构思想，自研接口/实现可能更合适。
- **External gate**：用来独立打开/回读/可视检查，不进入 canonical 核心。
- **Deferred**：对首版闭环价值不足，暂缓。

## 2. 分配矩阵

| 模块 | 候选/来源 | R0 角色 | 首版策略 |
|---|---|---|---|
| M01 Calibration | OpenCV | Core candidate | 图像/几何变换与轮廓基础；封装成无状态工具 |
| M01 Calibration | GDAL | Adapter/Core candidate | 坐标/GCP/栅格 I/O；只有需要 project/georef 时启用 |
| M02 Semantic Candidate | SAM 3/3.1 | Adapter candidate | 只产 mask/candidate，不写 canonical |
| M02 Semantic Candidate | SamGeo | Adapter/reference | 借鉴 geospatial I/O；许可与模型权利分开处理 |
| M02 Trace | Potrace | Algorithm/reference | 用作 trace 对照，不让平滑轮廓成为专业几何 |
| M03 Geometry | Shapely/GEOS | **Core candidate** | Python orchestration 主力；所有写操作走统一 geometry service |
| M03 Robust Geometry | CGAL | Specialist candidate | 仅为复杂 skeleton/offset/鲁棒场景保留插件边界 |
| M04 Road Graph | OSMnx | Algorithm/reference | 借鉴 graph simplify/intersection consolidation，不直接承担设计道路模型 |
| M04 Centerline | PyGeoOps | Adapter candidate | 生成 centerline candidate；必须再经 alignment/validator |
| M04 Alignment | Clothoids | Core/specialist candidate | G1/G2 曲线能力，是否进入 MVP 取决于道路 scope |
| M04 Cross-section | Street Generator | Architecture/reference | 借鉴 typed profile + rules 分离，不直接复用其地域规则 |
| M05 Building | Building Regulariser | Algorithm/reference | 借鉴 principal-direction/regularization；必须加 refusal gate + site topology |
| M05 Massing | UrbGEN | Algorithm/reference | 借鉴 typology/constraint 思路；不作为已有草图的自动重设计器 |
| M06 Canonical IR | COMPAS | Framework/reference | 评估数据结构/几何封装思想；**不把 COMPAS 直接等同 canonical IR** |
| M07 Analysis | Ladybug/Honeybee/Radiance | Adapter/specialist candidate | 生产分析候选；许可/部署与指标适用性需单独评估 |
| M07 Morphology | momepy | Adapter/reference | 形态反馈，不承担物理日照或法规判定 |
| M09 DXF | ezdxf | **Core candidate** | DXF compiler/reader/audit；外加自研 semantic/profile validator |
| M09 IFC | IfcOpenShell | **Core candidate** | IFC 编译/representation；不是 canonical truth owner |
| M10 IFC Information Validation | IfcTester | Adapter candidate | IDS/属性交付验证；几何/topology 仍由其他 validator 负责 |
| M10 External CAD Gate | AutoCAD | External gate | semantic round-trip / GUI QA；不作为 canonical database |
| M10 External CAD Gate | LibreCAD | External gate | 独立 DXF 读者/渲染/转换候选 |
| M10 Secondary Authoring | FreeCAD/Bonsai | External/secondary authoring | 后续人工编辑/QA；首版不把其文档模型当唯一真值 |
| M11 Agent | LLM + typed tools | Orchestrator only | 只操作 ChangeProposal / tool calls，不直接写未验证 geometry |

## 3. 当前最重要的“不要做”

1. 不构建“FreeCAD Agent”然后把整个问题绑在 FreeCAD object model 上。
2. 不把 IFC 当作唯一 canonical model；它是极重要的开放交换/交付表示，但当前规划道路、Trace provenance、Agent proposal 生命周期未必都适合直接塞入 IFC。
3. 不把 Shapely/GEOS 当“专业道路设计器”；它是几何内核，不负责道路工程语义。
4. 不把 SAM 的 mask 可信度当作几何精度。
5. 不把 Ladybug/Honeybee 的分析能力等同中国规划法规合规。
6. 不把 AutoCAD round-trip 的字节/字符串差异当作必然语义失败，也不因“AutoCAD 能打开”就宣称设计正确。

## 4. 首版推荐的依赖最小化方向

为了降低 R1 初期耦合，建议核心进程优先保持：

- 自研 Canonical IR + revision/dependency layer；
- Shapely/GEOS geometry service；
- NetworkX/custom RoadGraph（OSMnx ideas 可移植）；
- ezdxf compiler；
- 轻量 3D massing geometry；
- 可替换的 segmentation / IFC / analysis adapters。

这样即使 SAM、IfcOpenShell、环境引擎或具体 CAD 软件更换，也不会破坏 canonical model。
