# DXF Semantic Equivalence Policy v0.1（研究候选）

**状态：** `provisional-research-contract`。用于定义“第三方 CAD 往返后什么算等价”，不是生产实现。

## 1. 为什么需要 semantic equivalence

CAD round-trip 不应以文件字节完全一致为目标。第三方 CAD 可能重排实体、重写 handle、规范化名称大小写或调整序列化形式；与此同时，一些看似很小的字段变化（例如 LWPOLYLINE bulge/width）会改变实际几何。

因此验证应比较**语义规范形（canonical semantic representation）**，而不是只比较原始文本或少量 XY 坐标。

## 2. 三层比较

### A. File / document semantics

- DXF version / units；
- modelspace / paperspace policy；
- layer set；
- block / text style / dimstyle / linetype table semantics；
- required metadata / application IDs。

### B. Object identity and entity semantics

- stable object ID / class / revision；
- allowed entity type；
- layer assignment；
- BYLAYER/BYBLOCK policy；
- color / true color / lineweight / linetype / linetype scale；
- type-specific geometry fields。

### C. Geometric equivalence

- canonical geometric representation；
- topology / ring / hole / component count；
- toleranced metric comparison；
- optional rendered/expanded geometry comparison for arc/bulge/spline-like entities。

## 3. Symbol-table name comparison

Default semantic policy：CAD symbol-table names（layer、linetype、style、block、dimstyle 等）按 case-insensitive key 比较，同时保留原 spelling 作为诊断信息。

原因：Autodesk 文档指出，在检查 symbol table names 相等性时应进行大小写无关比较。`LTYPE` 与 `LAYER` 都是 symbol tables。

Profile 可以额外声明：

```yaml
serialization_name_policy:
  linetype_case: preserve | canonical | exact
```

其中 `exact` 只适用于明确要求文件序列化形式完全一致的项目规范，不作为通用 CAD 语义默认值。

## 4. LWPOLYLINE canonical fields

至少包含：

- entity type = `LWPOLYLINE`；
- closed / plinegen flag；
- ordered XY vertices；
- elevation；
- thickness；
- extrusion；
- per-vertex bulge；
- constant width；
- per-vertex start/end widths；
- layer / linetype / linetype scale / lineweight / color inheritance state。

若 Profile 要求“纯 2D、无宽度边界线”，则不仅要求 XY/Z 正确，还应要求：

- bulge 按对象角色允许或禁止；
- constant width = 0；
- start/end width = 0；
- thickness = 0；
- extrusion 为预期平面法向。

## 5. Entity type dispatch

Validator 必须先根据 `dxftype()` 安全分支，再访问该类型字段。类型不符合 object-role contract 时返回结构化失败，不允许因 `AttributeError` / `KeyError` 中断验证过程。

## 6. MultiPolygon / holes

从 CAD-IR 到 DXF 的每个 part/ring 必须产生显式 provenance：

- source object id；
- part index；
- ring index；
- outer/hole role；
- elevation / plane；
- revision / geometry hash。

若下游格式无法直接保存 hole 语义，应使用可回读 metadata 或明确的 ring role 映射，并由 validator 重建后检查拓扑。

## 7. Round-trip verdict

建议返回：

- `semantic_pass`
- `semantic_pass_with_serialization_differences`
- `conditional`
- `fail`
- `validator_error`

`validator_error` 不能等价于 `fail`：它表示工具无法完成判断，需要修复 Validator 本身。
