# CAD/BIM Validator Matrix v0.1

**状态：** provisional。验证器不是一个单一函数；每层有不同输入、判据、错误代码和通过状态。

| 层 | 验证对象 | 主要检查 | 候选开源工具/实现 | 单独通过不代表什么 |
|---|---|---|---|---|
| V0 IR / schema | CAD-IR 与 Profile | 必填字段、单位、坐标状态、对象 ID、revision、未知值来源 | JSON Schema/YAML schema + 自研确定性检查 | 不代表几何正确 |
| V1 几何 | canonical geometry | 有效性、自交、退化、面积/边界差、锁定几何 | Shapely/GEOS；必要时 CGAL | 不代表道路/建筑拓扑正确 |
| V2 场地拓扑 | 多对象关系 | Road Graph、共享边、邻接、分离、孔洞、对象合并/拆分 | 自研图/关系 Validator + Shapely | 不代表 CAD 文件可打开 |
| V3 Profile | 设计院/项目图纸规则 | 图层、颜色、线型、线宽、单位、字体、标注、块、布局、纸张/比例 | 自研 Profile Validator；可用 ezdxf 读回属性 | 不代表 DXF 内部结构完整 |
| V4 文件完整性 | 写出的 DXF/IFC | DXF table/reference audit；IFC 可解析、实体/关系完整 | ezdxf `audit()`；IfcOpenShell parse；IfcTester IDS | 不代表符合项目几何/图层规则 |
| V5 同库 round-trip | 生成→同库重读 | IR 到文件再回读，比较单位、实体数、层/样式、placement、representation | ezdxf；IfcOpenShell | 不代表其他软件能同样解释 |
| V6 独立软件 round-trip | 目标文件→独立 CAD/BIM 软件→保存/回读 | 对象/样式/单位/文字/块/几何是否丢失或被改写 | LibreCAD；FreeCAD；Bonsai/Blender | 不代表专业设计或法规合规 |
| V7 视觉/打印 QA | 屏幕与图纸输出 | 图层显示、线宽、字体替换、图框、视口、比例、裁切、遮挡 | LibreCAD/FreeCAD 渲染与 PDF/PNG 对照 | 不代表对象语义和拓扑正确 |
| V8 领域/规范审查 | 项目标准与法规 | 规范版本/法域、条款适用、道路/建筑指标、人工批准项 | 版本化规则库 + 专家审查；IFC 信息规则可用 IDS | 不可由通用文件库单独宣称通过 |

## 状态语义

每层结果独立记录 `not_run / pass / fail / blocked / review_required`。总体交付状态必须显示每层状态和阻断项，不得将 `V4 pass` 自动提升为“设计院标准合格”。

## 重要规则

1. `ezdxf.audit()` 是文件完整性层，不是项目标准层。
2. `IfcTester` IDS 主要验证 IFC 信息交付要求；几何/拓扑/placement consistency 仍需要额外 Validator。
3. 同库写入—读取是序列化回归；只有独立软件打开、保存并再次比较，才算跨软件 round-trip。
4. 视觉 QA 不能替代对象/几何/语义检查；对象检查也不能替代最终打印 QA。
5. 任何 validator 必须输出对象/实体定位、错误代码、证据值、期望值、修复建议和 source/revision，不只给一个 pass/fail。
