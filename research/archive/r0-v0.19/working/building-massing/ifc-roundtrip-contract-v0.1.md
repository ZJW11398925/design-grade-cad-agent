# IFC Footprint / Body Round-trip Contract v0.1

**状态：** test contract / not executed。  
**目标：** 检验同一 Building Object 的 2D Footprint、3D Body、Object Placement、单位和版本关系能否在 IFC 序列化后保持一致。  
**重要限制：** 当前运行环境没有 IfcOpenShell，且外部包索引不可访问；因此本轮只完成源码/官方文档核验与测试合同，不宣称 IFC 文件已真实生成或 round-trip 通过。

## 1. 源码事实与设计含义

- IfcOpenShell 官方文档说明：几何相对于 Object Placement 定位；一个产品可具有多个 Representation，并由 Representation Context 区分用途。
- 官方上下文 API 将 `Model/Body/MODEL_VIEW`、`Plan/Footprint/PLAN_VIEW`、`Axis/GRAPH_VIEW` 等作为不同上下文/用途。
- `add_footprint_representation` 创建 `GeometricCurveSet` 类型的 Footprint representation。
- `add_profile_representation` 可把 2D profile 沿 +Z 挤出形成 Body；任意 profile 可以含 inner curves。
- `assign_representation` 的实现会把 representation 追加到产品的 representations 集合，而不是按项目自定义 revision 自动替换旧项。
- `unassign_representation` 与 `remove_representation` 是不同操作：前者从产品/类型关联解除，后者清理不再使用的 representation 及其相关元素。

因此，IFC 能表达多表示，但不能代替项目自己的 revision/dependency contract；更新时必须明确替换策略，不能反复 assign 后留下旧表示。

## 2. 最小可复现对象

使用 IFC4 的最小测试文件，建立：

1. `IfcProject` 与显式长度单位；
2. `Model` 和 `Plan` 根 context；
3. `Model/Body/MODEL_VIEW` 与 `Plan/Footprint/PLAN_VIEW` subcontext；
4. 一个稳定 `GlobalId` 的 `IfcBuildingElementProxy`（或明确的适用建筑实体）；
5. Footprint：带已知外环/内环的闭合 2D 曲线；
6. Body：由同一 profile 按显式 height extrusion 得到；
7. Object Placement：至少包含非零 XY 平移和非零旋转，以避免只测原点/轴对齐的假阳性；
8. 属性集保存 `SourceTraceRef`、`TraceRevision`、`ProfessionalFootprintRevision`、`MassingParameterSource` 和 `BodyRevision`。这些是项目级 provenance 属性，不替代 IFC 的 GlobalId/placement/representation。

## 3. 写入—重读断言

写出 IFC 后关闭文件，再由 IfcOpenShell 重新打开并断言：

- `GlobalId`、IFC class、项目单位和对象 placement 存在且保持；
- Footprint 与 Body representation context 的 `ContextType / ContextIdentifier / TargetView` 正确；
- 两种表示均可被独立定位；无重复的旧 Footprint/Body 表示；
- Footprint 外环、内环、面积、边界和世界坐标位置与源几何在声明容差内一致；
- Body 的 XY 投影与 Footprint 一致；Z min/max、extrusion depth 与确认的 massing 参数一致；
- 单位换算明确（API 使用 SI 参数时，写入项目单位的转换不能造成 1000 倍尺度错误）；
- provenance 属性、revision 与稳定对象身份保持。

所有数值容差由几何/单位和序列化方法校准，不在本合同里预设一个适用于所有模型的常数。

## 4. 变更与失效传播测试

### IFC-RT-01：修改 Footprint

将 `ProfessionalFootprintRevision` 从 R1 改为 R2。预期：旧 Body 标记 `stale/rebuild-required`；不得因为旧 Body 的 IoU 仍很高就宣称一致。重建后 `BodyRevision` 与 footprint dependency revision 匹配。

### IFC-RT-02：表示替换

从 R1 Body 更新为 R2 Body。验证旧表示从对象关联中解除，且不再被当前对象引用；新文件中不能出现两个都被当作 current 的 Body。按 API 的 `unassign_representation` / `remove_representation` 生命周期操作，验证不误删共享的命名 profile 或被其他对象引用的元素。

### IFC-RT-03：Placement drift

仅改变 placement 平移或旋转。Validator 必须检查世界坐标下的 Footprint 和 Body 投影，而不是只比较各自的局部坐标。

### IFC-RT-04：单位漂移

分别使用 metre / millimetre 项目单位做写入—重读。检查面积平方单位、长度单位和 placement 的换算；发现 1000 倍/1000000 倍偏差时硬失败。

### IFC-RT-05：孔洞与凹槽

测试 U/L/院落 footprint。确保 profile 内环和 Body 的挤出结果保留对应空洞/凹槽；如果 IFC 表示能力或 exporter 不支持该输入，必须显式失败或标记需审阅，不能静默填实。

### IFC-RT-06：第三方互操作

同一 IFC 由 Bonsai/BlenderBIM 或另一独立 IFC 读者打开/保存后再检查。仅由 IfcOpenShell 写入再由 IfcOpenShell 读取属于库内序列化测试，不足以证明跨软件互操作。

## 5. 通过条件与失败处理

- 任一关键对象身份、单位、placement、内环、representation context 或 revision 断言失败：`fail`。
- geometry metrics 通过但 revision/dependency 不匹配：仍 `fail`。
- 只有 IFC 文件结构合法但未完成几何/placement/provenance 检查：仅 `serialization_smoke_pass`，不得升级为 round-trip pass。
- 真实 IFC 测试未执行时，状态必须是 `blocked_not_run`，不能用合成 Shapely 投影实验替代。

## 6. 依据与定位

- [IfcOpenShell Geometry Creation](https://docs.ifcopenshell.org/ifcopenshell-python/geometry_creation.html)
- [add_footprint_representation.py](https://github.com/IfcOpenShell/IfcOpenShell/blob/v0.9.0/src/ifcopenshell-python/ifcopenshell/api/geometry/add_footprint_representation.py)
- [add_profile_representation.py](https://github.com/IfcOpenShell/IfcOpenShell/blob/v0.9.0/src/ifcopenshell-python/ifcopenshell/api/geometry/add_profile_representation.py)
- [assign_representation.py](https://github.com/IfcOpenShell/IfcOpenShell/blob/v0.9.0/src/ifcopenshell-python/ifcopenshell/api/geometry/assign_representation.py)
- [unassign_representation.py](https://github.com/IfcOpenShell/IfcOpenShell/blob/v0.9.0/src/ifcopenshell-python/ifcopenshell/api/geometry/unassign_representation.py)
- [remove_representation.py](https://github.com/IfcOpenShell/IfcOpenShell/blob/v0.9.0/src/ifcopenshell-python/ifcopenshell/api/geometry/remove_representation.py)
