# CAD/BIM Validator：正式开发阶段验收合同 v0.1

**用途：** 把 R0 技术研究中已经发现的问题冻结为后续开发的验收要求。  
**状态：** `research-to-development-handoff`。本文件不要求在 R0 继续实现。

## DEV-CAD-001 MultiPolygon contract

必须：
- Polygon / MultiPolygon / part / ring 字段契约一致；
- hole/outer 明确；
- `elevation_z` 等 plane 字段具有明确必需/默认/继承规则；
- 合法 MultiPolygon 不得造成未处理 `KeyError`。

验收：含两个 part + 至少一个 hole 的 fixture 必须生成结构化 manifest 和 validation result。

## DEV-CAD-002 Safe entity dispatch

必须：
- 先检查实体类型，再读取类型专属字段；
- 实体类型替换返回 `ENTITY_TYPE_MISMATCH`，不得抛出未处理 `AttributeError`。

## DEV-CAD-003 LWPOLYLINE full-semantic geometry

必须验证：
- XY vertices；
- bulge；
- constant width；
- start/end width；
- elevation；
- thickness；
- extrusion；
- closed flag。

验收：仅修改 bulge 或 width、保持 XY 与 XDATA 不变时必须失败。

## DEV-CAD-004 Geometric canonicalization

对 line/polyline/arc/spline 等可同时保留：
- raw DXF semantic fields；
- canonical geometry / sampled representation（带明确 tolerance）。

不能只依赖其中一侧。

## DEV-CAD-005 Symbol-table name normalization

默认 case-insensitive 比较 layer/linetype/style/block/dimstyle 等符号表名称；保留原始 spelling 供诊断。

验收：AutoCAD 将 `CONTINUOUS` 规范化为 `Continuous` 时，若线型定义与引用语义未变化，应得到 `semantic_pass_with_serialization_differences`，而不是几何/规范失败。

## DEV-CAD-006 Third-party round-trip matrix

至少分别记录：
- AutoCAD core / GUI（若可用）；
- LibreCAD；
- FreeCAD Draft 或其他候选；
- 原 DXF 与 round-trip DXF。

比较对象必须使用 semantic equivalence policy；不得用同库 ezdxf read/write 代替第三方 Gate。

## DEV-CAD-007 Structured validator failures

每个验证项返回机器可读：
- code；
- severity；
- object id；
- expected；
- actual；
- evidence locator；
- fixability；
- validator version。

Validator 自身异常必须单独标 `validator_error`。

## DEV-CAD-008 Profile / CAD semantics separation

区分：
- CAD 格式固有语义；
- 通用互操作规则；
- 国家/地方/设计院 Profile；
- serialization preference。

不得把 AutoCAD 的序列化规范化误判为设计规范失败，也不得反过来用“CAD 能打开”替代设计院标准校核。

## 延后到正式开发的事项

R0 不继续实现上述修复。只有当正式开发启动时，才把这些项转为测试代码、CI Gate 与第三方软件测试矩阵。
