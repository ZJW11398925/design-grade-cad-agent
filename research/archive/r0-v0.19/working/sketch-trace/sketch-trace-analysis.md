# Sketch → Trace 入口线：第一轮分析

**状态：** `candidate-analysis`；不是最终架构决定。  
**BATCH：** `BATCH-002`。

## 1. 当前最重要的结论

入口不能只有一个“vectorized_geometry”。至少需要分开保存：

```text
Source Raster
  ↓
Calibration / Reference Frame
  ↓
Semantic Candidates (mask / label / confidence)
  ↓
Raw Trace Geometry
  ↓
Controlled Simplified Trace
  ↓
[后续批次] Intent / Professional Geometry
```

语义 mask、忠实 Trace、专业几何是三种不同对象。SAM/Potrace/OpenCV 都不能单独把它们合并为“工程真值”。

## 2. 坐标状态必须显式建模

建议至少区分：

- `image_space_unscaled`：只有像素坐标；不能输出真实面积/距离。
- `local_metric_scaled`：已由确认尺寸得到米制比例，但原点/方向/CRS 仍未确定。
- `project_aligned`：通过红线/控制点与项目局部坐标对齐。
- `georeferenced`：已进入明确 CRS / survey reference。

变换本身记录 `transform_type`、控制点、残差、异常点、来源与人工确认状态。

### 变换选择

- 四对平面对应点可建立 projective homography；适合纸面/屏幕平面照片的透视校正。
- affine / geotransform 用于图像像素到平面坐标的线性映射。
- 多个 GCP 可用于地理/项目坐标配准，并应保留残差与异常点信息。
- 单个已知长度只提供比例证据；不自动提供全局原点、朝向或 CRS。
- lens distortion 与 projective distortion 不是同一问题；必要时应在 homography 前做相机畸变校正。

## 3. 语义候选：SAM 3 是候选生成器，不是几何权威

Meta SAM 3/3.1 已支持文本与视觉 prompt 的开放词汇分割，因此从“building / road / green area”等语义产生候选 mask 的能力比 SAM 2 更强。但本批只把它视为 **candidate generator**：

- 模型官方基准不等于建筑/规划草图域的准确性；
- 项目 issue 已出现“区域能识别但边缘不够 sharp、影响 downstream line fitting”的实例；
- checkpoint 有访问门槛；
- 当前项目采用 Meta 自定义 SAM License，不能继续沿用旧矩阵中“Apache 2.0”的 SAM 1/2 许可判断。

SamGeo 本身 MIT，并提供 SAM family 的 GeoTIFF/GeoJSON/GeoPackage 等 I/O 和 mask→vector 便利接口，但 wrapper 的 MIT 许可不覆盖其调用的模型/权重许可。

## 4. Vector trace：不能把“平滑”误当“忠实”

Potrace 的目标是把 bitmap 转为平滑、可缩放的 Bezier/line outline。其算法论文明确指出：trace 不可能从 bitmap 恢复输入中不存在的信息，且算法会在多个可能轮廓中寻找更合理/美观的近似。

因此在本项目中：

- Potrace 适合做 `trace_candidate` 或视觉参考，不适合直接承担专业建筑/道路几何；
- OpenCV `findContours` + `approxPolyDP` 更适合受控地保留 raw contour 与不同简化级别；
- Trace 阶段必须保留 `raw_trace`，任何简化都应产生新 revision，不能覆盖原轮廓。

## 5. LOCAL-SKETCH-001 合成 Benchmark

环境：OpenCV 4.13.0；合成数据，仅用于校准测量方法。

### 5.1 四控制点 homography 对点击误差敏感

| 控制点噪声 σ(px) | 平均重投影误差(px) | 平均 P95(px) |
|---:|---:|---:|
| 0.5 | 0.5915 | 0.9776 |
| 1.0 | 1.1202 | 1.8421 |
| 2.0 | 2.3001 | 3.7804 |
| 4.0 | 4.6587 | 7.6491 |
| 8.0 | 8.8404 | 14.5589 |

含义：控制点不是“有/无”布尔量。必须保存 residual / uncertainty，后续专业几何与尺寸校核应知道其坐标基础质量。

### 5.2 单一已知长度可以给比例，但不是完整地理定位

30 m 基准、600 px 长度的合成测试中，即使端点点击存在 4 px Gaussian 噪声，P95 相对比例误差约 1.872%。这说明“局部比例”可以有可用性，但它仍不决定项目坐标原点、方向或 CRS。

### 5.3 轮廓简化：面积误差可能掩盖边界损失

| epsilon / perimeter | 顶点数 | Hausdorff(px) | 面积误差 |
|---:|---:|---:|---:|
| 0.001 | 47 | 1.8518 | 0.0439% |
| 0.005 | 11 | 8.0353 | 0.5244% |
| 0.010 | 8 | 11.6859 | 0.0954% |
| 0.020 | 7 | 32.4266 | 3.9632% |
| 0.050 | 4 | 54.9898 | 17.6278% |

`epsilon=0.01*perimeter` 的面积误差仍小于 0.1%，但最大边界偏差已经超过 11 px。因此 Trace Validator 至少需要组合：

- boundary/Hausdorff deviation；
- area difference；
- topology/holes/components；
-关键控制点偏差；
- 简化前后 vertex/segment 变化。

不能只用 IoU 或面积误差判断“忠实”。

## 6. 相邻 floorplan 项目带来的架构启发

这些项目不是总平解决方案，只用于观察成熟问题拆分：

- **RedrawAI**：明确采用 segmentation → vectorization → graph reconstruction → cleanup → DXF → validation；README 还明确“scale 必须有来源或人工确认，绝不猜”。
- **Raster2Seq**：证明可以直接学习“labeled polygon sequence”，但训练域是 floorplan，checkpoint 非商业许可与代码许可需要分开处理。
- **floorplan-to-vector**：要求 reviewed semantic mask 或人工基线，未校准时保持 pixel-based / NTS；把估算值和测量值状态分开。这与本项目的“未知显式化”原则高度一致。

这些只支持架构思想，不证明它们能处理总平草图中的道路、绿地或建筑体量。

## 7. provisional 输入对象模型

建议 R0 先使用以下对象，而不是直接生成 CAD 实体：

- `SourceRaster`
- `ReferenceFrame`
- `ControlPoint`
- `SemanticCandidate`
- `TraceObject`
- `TraceRevision`
- `ReviewDecision`

`TraceObject.semantic_role` 可以是 `candidate`；只有设计者确认或后续规则足够强时才进入 `confirmed`。红线、测量控制点等外部权威对象可标记 `locked=true`。

## 8. 下一步与主线关系

BATCH-002 只负责把“模糊图像”变成**可信、可追溯的入口对象**。下一阶段仍需单独研究：

- `COV-05..09`：道路/几何专业化；
- `COV-10..12`：建筑 footprint 与 massing；
- `COV-13`：2D/3D identity；
- `COV-16..19`：CAD/BIM 编译与独立验证。

因此本批不会因 SAM/矢量化工具继续横向扩张到视觉模型排行榜。
