# E2E-FIXTURE-001 v0.3 用户本地复核记录（2026-10-27）

**证据类型：** 用户在独立本地环境执行的初步技术复核。  
**状态：** `conditional`。  
**用途：** 作为研究阶段的外部执行证据和开发阶段验收输入；不构成第三方独立签字、生产批准或真实设计质量证明。

## 1. 环境与范围

用户报告的执行环境：Python 3.12.3、Shapely 2.2.0、ezdxf 1.4.5、pytest 9.1.1，并使用 AutoCAD 2022 核心引擎完成一次打开、另存与回读。未做 GUI 人工视觉检查。

原复核包保持未修改。用户在其本地工作目录保存了复现脚本、探测结果及 AutoCAD round-trip 文件；这些本地路径不属于本研究工作区的可复核附件，因此本文件只记录用户报告的结果，不把不可访问路径伪装成已取得原件。

## 2. 可确认的复核结果

- 复核包清单中 35/35 文件的字节数与 SHA-256 匹配。
- 原测试 56 项全部通过。
- MultiPolygon：含两个 part 与一个 hole 的有效输入在生成 DXF 后，验证器出现 `KeyError: 'elevation_z'`，未能返回结构化验证清单。
- Bulge 变异：修改 LWPOLYLINE bulge、保持 XY 顶点与 XDATA 不变，验证器仍接受。
- Constant width 变异：将 polyline constant width 从 0 改为 2，验证器仍接受。
- 实体类型替换：保留原 XDATA、把 polyline 替换为 circle 后，验证器出现 `AttributeError`，未返回结构化失败。
- AutoCAD 2022 core round-trip：单位、图层名称、11 个实体类型/数量及现有对象检查保持；五个业务图层的线型名称从 `CONTINUOUS` 变为 `Continuous`，现有 validator 因大小写精确比较导致整体失败。

## 3. 研究层判断

### 3.1 几何验证仍存在 false accept

Bulge 与 polyline width 都是实体几何/显示语义的一部分。只比较 XY 顶点和 XDATA 不能证明 LWPOLYLINE 几何保持。后续正式开发必须把 LWPOLYLINE 的完整语义字段纳入 canonical representation，包括：

- vertices / closed flag；
- bulge；
- constant width；
- start/end width；
- elevation；
- thickness；
- extrusion direction；
- entity type。

必要时还应增加“实体字段比较 + 几何展开后比较”双重验证，避免只靠一种表示。

### 3.2 验证器必须 fail-closed，而不是 exception-closed

输入字段缺失或实体类型不匹配时，不应抛出未处理异常并中断整个验证。应返回结构化错误，例如：

- `SCHEMA_FIELD_MISSING`
- `ENTITY_TYPE_MISMATCH`
- `UNSUPPORTED_ENTITY`
- `GEOMETRY_SEMANTIC_MISMATCH`

异常可作为内部诊断，但不能代替验证结果。

### 3.3 MultiPolygon 是契约问题，不只是一个 bug

如果 CAD-IR 允许 `Polygon | MultiPolygon`，那么 part、ring、hole 必须共享一致的必需字段与继承规则。`elevation_z` 不能在单 Polygon 路径存在、到 MultiPolygon 分支就缺失。正式开发前应冻结 shape contract，明确：

- object-level 字段；
- part-level 字段；
- ring-level 字段；
- 默认值与继承；
- hole/outer role；
- 空/无效 component 的处理策略。

### 3.4 AutoCAD 线型大小写差异属于语义规范化问题

Autodesk AutoLISP 文档明确提醒：比较 symbol table names 时应忽略大小写；`LTYPE` 属于 symbol table。因而 `CONTINUOUS` 与 `Continuous` 在 CAD 语义比较中不应仅因大小写不同被判失败。

建议正式开发采用两层比较：

1. **semantic name**：对 CAD symbol-table name 使用 case-insensitive canonical key；
2. **presentation/original spelling**：保留实际序列化字符串，用于 round-trip diagnostics，但默认不作为 semantic failure。

如果未来某个设计院 Profile 明确要求文件中的文字拼写/大小写必须完全一致，则可以将其作为额外的 serialization policy，而不是混入通用 CAD 语义层。

## 4. 官方 DXF 语义依据

Autodesk DXF Reference：LWPOLYLINE 的 group code `42` 为 bulge，`43` 为 constant width，`38` 为 elevation，`39` 为 thickness，`40/41` 为 vertex start/end width，`210/220/230` 为 extrusion direction。因此这些字段均不能被“XY 顶点相同”所替代。

来源：
- https://help.autodesk.com/cloudhelp/2024/ENU/AutoCAD-DXF/files/GUID-748FC305-F3F2-4F74-825A-61F04D757A50.htm
- https://help.autodesk.com/view/ACD/2027/ENU/?caas=caas%2Fdocumentation%2FACD%2F2014%2FENU%2Ffiles%2FGUID-A77594CA-D8AF-4550-8EAA-3D3EED0248AC-htm.html

## 5. 阶段决定

本轮不继续在研究阶段修复实现。将上述发现转入 `development-acceptance-contract-v0.1.md`，作为后续正式开发的硬验收项。

当前 E2E v0.3 状态维持：`conditional`。不得升级为 `pass_for_next_experiment`、A1、生产可用或设计院合规。
