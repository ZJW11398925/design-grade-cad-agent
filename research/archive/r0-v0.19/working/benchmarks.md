# R0 Benchmark 设计（BEN）

> Benchmark 的目标是逼出失败模式，而不是展示漂亮 Demo。数值阈值暂不凭直觉写死；先采集基线分布，再冻结 Gate。

## Sketch / Trace

### BEN-SKETCH-001：无比例手绘总平
输入：建筑块、道路、绿地的简单扫描/手机图。
检查：能否保存 source；能否输出 image-space trace；是否错误宣称真实尺寸。

### BEN-SKETCH-002：有一个已知尺寸
检查：从单一控制尺度建立 metric transform；Trace 与 Source 仍可回溯。

### BEN-SKETCH-003：有红线 CAD + 草图叠加
检查：图像配准、坐标变换、锁定红线不被 Agent 改写。

### BEN-SKETCH-004：线条互相覆盖/标注干扰
检查：语义分割是否把文字、箭头误当道路或建筑边界。

## Road / Topology

### BEN-ROAD-001：T 型路口，端点存在小缝隙
检查：视觉连接是否被转换为同一 topology node；主路是否正确 split。

### BEN-ROAD-002：X 型路口，线段几何相交但数据未 noded
检查：是否产生真实交点节点，edge 是否重建。

### BEN-ROAD-003：手绘 S 型道路
检查：Trace 是否保留；Professional alignment 是否去除手抖而保留整体意图；连续性类别可测。

### BEN-ROAD-004：道路轮廓宽度变化
检查：centerline candidate 是否稳定；短枝是否误保留/误删除。

### BEN-ROAD-005：Y 型不对称交叉口
检查：offset 后是否出现自交、尖角、缝隙；junction polygon 是否有效。

### BEN-ROAD-006：环路 + 多入口
检查：Road Graph 连通性、闭环、重复 node、伪断路。

### BEN-ROAD-007：近距离平行道路
检查：snap/consolidation 是否错误合并本应独立的道路。

### BEN-ROAD-008：中心线存在 Line→Arc→Curve 组合
检查：切向/曲率连续性及导出后的几何保持。

## Building / Massing

### BEN-BLDG-001：略微歪斜的矩形建筑
检查：保真 Trace 与正交化候选是否并存；修改量可解释。

### BEN-BLDG-002：L 型 / U 型 / 院落轮廓
检查：是否错误简化为矩形；typology 能否保留洞/院落。

### BEN-BLDG-003：建筑高度不同
检查：同一 footprint 在 2D/3D 中保持 identity；高度变化不破坏 footprint。

### BEN-BLDG-004：建筑贴近红线/道路
检查：空间冲突能否定位到具体对象和具体边。

## 2D / 3D / Export

### BEN-3D-001：Footprint → Massing
检查：面积、位置、朝向、对象 ID 与 2D 一致。

### BEN-3D-002：太阳遮挡
检查：相同位置/时间输入下结果可复现，并与简单解析案例交叉验证。

### BEN-OUT-001：DXF round-trip
检查：图层、实体数、坐标、线型等关键属性生成后回读是否保持。

### BEN-OUT-002：IFC round-trip
检查：对象类型、placement、Footprint/Body representation、属性是否保持。

## 第一阶段通用验收维度

- Fidelity：与 Source/Trace 的偏差。
- Topology：node/edge、连通、分割与闭环是否正确。
- Geometry validity：自交、无效 polygon、重复/零长度对象。
- Continuity：G0/G1/G2 按对象需求分别评价。
- Semantics：道路/建筑/绿地 identity 是否稳定。
- Provenance：每个专业化对象能否回指原始对象和变更原因。
- Determinism：同输入/同参数是否复现。
- Editability：输出是否为可继续修改的参数/实体，而非只有图片。
- Interoperability：DXF/IFC 等第三方 round-trip。
- Compliance readiness：是否能由独立规则层检查，而非 LLM 文本判断。
