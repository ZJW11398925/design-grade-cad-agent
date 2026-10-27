# BATCH-004 候选知识记录

## KNO-CAD-001 — DXF 文件审计与项目 Profile 验证必须分层

- **候选主张：** `ezdxf.Drawing.audit()` 可检查/修复 DXF 文档结构问题，但项目自己的图层命名、颜色、线型/线宽策略、单位、标注、块、布局和实体映射仍需确定性 Profile Validator。
- **依据：** ezdxf 官方 README、layers/lineweights/common graphical attributes/drawing audit 文档；`LOCAL-CAD-003` 实际生成/重读 DXF 并验证合成 Profile。
- **本地结果：** 6 个断言通过；同库重读结构快照一致，audit 未修复错误数为 0；人为植入的未定义线型和 BYLAYER 属性覆盖被自定义 Validator 捕获。
- **限制：** 合成 Profile 不是任何真实标准；未在 AutoCAD/LibreCAD 独立打开/保存。

## KNO-CAD-002 — 线宽值要在 Profile 输入端预检，不能只检查输出值

- **候选主张：** DXF lineweight 用百分之一毫米表达，且只允许指定值集合；ezdxf 1.4.4 的本地探针中，把 lineweight 27 赋给实体后，读取值被规范化为 30。因此，编译器必须先验证用户配置，再比较写出后的属性，不应只验证最终值“看起来有效”。
- **依据：** ezdxf 官方 Lineweights 文档；本地 `LOCAL-CAD-003` 的赋值探针。
- **限制：** 27→30 是 ezdxf 1.4.4 的观察，不外推到所有版本或其他 DXF 库。真实 Profile 值需来自项目/设计院标准。

## KNO-CAD-003 — DXF round-trip 至少需要同库与独立应用两层

- **候选主张：** 同库写入—读取可验证序列化与结构保持；独立应用打开/保存/回读才能验证跨软件互操作。两者必须分别报告。
- **依据：** ezdxf README 支持多 DXF 版本读写；LibreCAD 官方 README 提供独立 CAD/CLI 转换路线；LibreCAD 文档也指出不同构建的 DWG 能力不同。
- **限制：** 当前环境没有 LibreCAD/AutoCAD/FreeCAD，第三方 round-trip 未执行；当前结果只覆盖 ezdxf 1.4.4 同库 DXF R2010 路线。

## KNO-CAD-004 — IFC IDS 检查信息交付，不等同几何或规划合规

- **候选主张：** IfcTester 可验证 IFC 对 IDS 信息交付规格的满足情况，并生成多种报告；几何有效性、2D Footprint/3D Body 一致、placement、单位、道路/建筑拓扑与规划约束仍需其他 Validator。
- **依据：** IfcTester 官方文档；IfcOpenShell 官方 README 的工具/组件职责表。
- **限制：** 当前环境未安装 IfcOpenShell，未本地运行 IDS 或 IFC round-trip。

## KNO-CAD-005 — CAD-IR 应与 DXF/IFC 导出器分离

- **候选主张：** 道路、建筑、绿地和注释应在工具无关的 canonical IR 中保持对象 ID、几何 revision、单位/坐标状态、来源、锁定项和依赖；DXF 与 IFC 分别从 IR 编译，不能把一个输出文件反过来当成唯一真值。
- **依据：** BATCH-002 的 Trace provenance、BATCH-003 的 representation revision/stale 发现，以及当前 `LOCAL-CAD-003` 显示文件层通过不等于项目 Profile 通过。
- **限制：** 当前 CAD-IR 仅为 provisional schema，尚无真实端到端样例验证其完整性。

## KNO-CAD-006 — 交付状态必须分层显示

- **候选主张：** 至少独立报告 IR、几何、拓扑、Profile、文件完整性、同库 round-trip、第三方 round-trip、视觉/打印 QA、领域/规范审查状态；总体状态不得由任意一个 `pass` 自动推导。
- **依据：** `validator-matrix-v0.1.md` 与本地 DXF profile probe；IfcTester IDS 与 ezdxf audit 的官方职责范围。
- **限制：** 验证层定义尚待独立 A1 和真实设计院模板校准。


## KNO-CAD-007 — 规划制图 Profile 必须同时建模适用范围、几何拓扑和图层映射

- **候选主张：** 真实规划制图标准不仅规定图层名/颜色，也可能规定坐标基准、单位精度、几何实体类型、闭合与相邻面拓扑、GIS-CAD 要素映射。Profile 必须能把这些不同类型规则关联到来源条款，并逐层执行。
- **依据：** 官方 DB11/T 1948-2021 第 2.2、2.4、3.1 节与附录 B/D；`LOCAL-CAD-004` 实际将一小部分图层/RGB/拓扑规则编码并运行。
- **限制：** 该标准只适用于北京市国土空间详细规划，不能默认应用到用户项目；本轮只提取少量规则，不是完整合规包。

## KNO-CAD-008 — 标准中的“允许自定”必须与缺失值区分

- **候选主张：** 若标准明确允许按图面效果决定线宽/图案，Profile 应记录 `explicitly_discretionary` 并要求项目选择或人工审查；不能把它误判为漏数据，也不能由 Agent 随意填一个固定值并宣称标准要求。
- **依据：** DB11/T 1948-2021 附录 D 表格备注；`db11t1948-profile-extract-v0.1.yaml` 中 `DB11-1948-LINEWEIGHT-DISCRETION`。
- **限制：** 仅对本次读取的规则与图层成立；完整标准中其他要素可能有不同要求。

## KNO-CAD-009 — 坐标单位不等于坐标参考系

- **候选主张：** DXF `$INSUNITS=6` 只能表示米制单位，不能证明图纸已使用标准要求的地方平面/高程坐标系或与国家空间参考系建立联系。Profile compliance 应将 `units` 和 `coordinate_reference` 分开检查。
- **依据：** DB11/T 1948-2021 第 2.2.1 与 2.2.3；`LOCAL-CAD-004` 的真实来源型规则验证：图层/颜色/拓扑检查通过，但坐标参考仍 blocked。
- **限制：** 本地样例使用合成坐标，不是真实北京地理数据。
