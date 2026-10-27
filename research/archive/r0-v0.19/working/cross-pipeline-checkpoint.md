# Cross-pipeline Checkpoint：从道路分支回到端到端主线

**日期：** 2026-10-26  
**性质：** 校准运行与跨能力检查；不是正式 acquisition A1、不是独立 Benchmark、不是技术选型。  
**目标：** 检查道路研究之外的关键能力是否有可用开源构件，并明确它们不能替代哪些端到端检查。

## 1. 本轮实际读取的官方资料

### PyGeoOps：polygon centerline / medial axis

来源：
- https://pygeoops.readthedocs.io/en/stable/api/pygeoops.centerline.html
- https://github.com/pygeoops/pygeoops

官方 API 将 `centerline()` 描述为多边形的近似中心线/medial axis，并提供 densify、短分支清理和简化等参数。文档说明，较大的 `densify_distance` 可能使窄部位出现缺口。该能力适合生成**候选中心线**，但不证明结果具备工程路线所需的控制点、曲率/切向连续、交叉口处理或规范适用性。

### IfcOpenShell：对象表示上下文

来源：
- https://docs.ifcopenshell.org/ifcopenshell-python/geometry_creation.html
- https://docs.ifcopenshell.org/autoapi/ifcopenshell/api/geometry/add_axis_representation/index.html

官方文档区分 Model/Plan context，并列出 `Body`、`Box`、`Axis`、`Profile`、`Footprint` 等不同用途的表示。`add_axis_representation` 当前文档描述的是简单起终点直线轴。由此可以确认 IFC 提供多表示与对象 placement 的语义机制，但不能据此假设所有曲线道路 alignment 都能由该简单 API 表达，也不能自动保证各表示几何一致。

### ezdxf：文件级审计

来源：
- https://ezdxf.readthedocs.io/en/stable/drawing/drawing.html

`Drawing.audit()` 检查 DXF 文档完整性并修复可修复的问题；不可修复问题会进入 auditor errors。`validate()` 会返回是否存在未修复错误。该能力可成为 DXF 编译后的**文件结构检查**，但它不替代本项目自定义的图层、线型、线宽、标注样式、对象语义、几何拓扑或设计规范检查。

### Ladybug Tools：日照与阴影分析

来源：
- https://www.ladybug.tools/ladybug.html
- https://www.ladybug.tools/ladybug/docs/ladybug.sunpath.html

官方资料支持 sunpath、shadow studies、solar access 和 sunlight-hours 等早期设计分析。太阳位置与分析依赖地点、时间/时区、北向以及相应天气/分析输入。该工具可作为环境分析候选，但结果正确性仍依赖输入校准和几何正确；分析能力本身不等于中国规划日照规范的合规判断。

## 2. 共同结论（仅为候选知识）

这些工具分别覆盖不同层，进一步支持“不要寻找一个包办所有工作的 CAD Agent 仓库”的研究策略：

- PyGeoOps 可生成几何候选，不替代拓扑/工程路线校核。
- IfcOpenShell 能表达多种 2D/3D 表示，不替代对象一致性与几何 round-trip 验证。
- ezdxf 能审计 DXF 文件完整性，不替代设计规格/语义/规范验证。
- Ladybug Tools 能执行环境分析，不替代场地输入校准和法规判断。

因此端到端系统至少需要可组合的“候选生成器 + 统一对象/参数模型 + 确定性 Validator + 第三方回读 + 可追溯局部修复”闭环。

## 3. 运行边界

- 本轮属于校准，不是 BATCH-001 的新 RUN，不改变其 A1 状态。
- 搜索工具没有提供完整总命中量/分页信息；本轮不声明候选生态穷尽。
- 本轮只阅读官方文档/官方项目资料，没有本地安装、运行、性能测试或独立复现。
- 没有冻结技术栈、CAD-IR 或 IFC 作为唯一中间表示的决定。

## 4. 回到主线后的影响

本轮结果回流到 `coverage-dashboard.md` 和 `project-matrix.md`。后续必须用同一代表性场地样例贯穿输入校准、Trace、几何/拓扑、建筑体量、分析、DXF/IFC 导出与回读；不能分别展示多个互不相干的工具 Demo 并把它们相加当成完整系统。
