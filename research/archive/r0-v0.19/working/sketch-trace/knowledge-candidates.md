# Candidate Knowledge Records — BATCH-002

> 均为 `candidate`，不是正式 DEC 或经过 A1 的综合结论。

## KNO-SKETCH-CAL-001 — 坐标状态不是二元“已标定/未标定”

- **候选主张：** 输入至少应区分 image-space、local metric、project-aligned、georeferenced；比例、方向、原点、CRS 是不同信息。
- **依据：** OpenCV homography；GDAL geotransform/GCP 数据模型；`LOCAL-SKETCH-001`。
- **限制：** 尚未在真实场地底图与 survey control 上测试。
- **Benchmark：** `BEN-SKETCH-001..003`, `BEN-SKETCH-005..006`。

## KNO-SKETCH-TRACE-001 — Raw Trace 不能被简化结果覆盖

- **候选主张：** `approxPolyDP`/Bezier trace 应生成新 revision；必须保留 raw contour，因为面积/IoU 很小的变化也可能对应较大的局部边界偏移。
- **依据：** OpenCV 官方 epsilon 定义；`LOCAL-SKETCH-001` 轮廓简化结果。
- **限制：** 合成轮廓，不代表真实草图的容差分布。
- **Benchmark：** `BEN-SKETCH-008`。

## KNO-SKETCH-METRIC-001 — Trace fidelity 不能只用面积或 IoU

- **候选主张：** 至少组合 boundary/Hausdorff、area、topology、关键控制点和 component/hole 变化。
- **依据：** `LOCAL-SKETCH-001` 中 epsilon=0.01 时面积误差约 0.0954%，但 Hausdorff 已约 11.69 px。
- **限制：** 阈值尚未冻结。
- **Benchmark：** `BEN-SKETCH-008`。

## KNO-SKETCH-SEM-001 — Foundation segmentation 只产生语义候选

- **候选主张：** SAM 3/3.1 可通过 text/visual prompt 生成开放词汇 mask，但输出不能直接晋升为建筑/道路工程边界。
- **依据：** Meta 官方 README/项目页；SAM3 issue #501 提供“能识别区域但边缘不够 sharp”的项目问题实例。
- **限制：** issue 不是建筑总平独立复现；本批未运行 checkpoint。
- **Benchmark：** `BEN-SKETCH-004`, `BEN-SKETCH-007`。

## KNO-SKETCH-VEC-001 — 通用 bitmap tracing 不等于专业几何恢复

- **候选主张：** Potrace 的 smooth outline 适合 trace candidate，但它不恢复语义、尺度、拓扑或专业设计意图。
- **依据：** Potrace 官方说明和算法论文。
- **限制：** 尚未与 OpenCV trace 在真实样例上对比。
- **Benchmark：** `BEN-SKETCH-008`。

## KNO-SKETCH-PIPE-001 — 分割与几何重建需要独立阶段

- **候选主张：** RedrawAI、floorplan-to-vector 等相邻项目都把 semantic input 与 geometry reconstruction/validation 分开，这一模式值得用于场地总平入口。
- **依据：** 对应 README；不是本项目本地验证。
- **限制：** floorplan domain 与 site-plan domain 不同。
- **Benchmark：** `BEN-SKETCH-004`, `BEN-BLDG-001`, `BEN-ROAD-001`。

## KNO-SKETCH-LICENSE-001 — SAM 3 许可必须与 SamGeo wrapper 分开治理

- **候选主张：** SamGeo 为 MIT，但 SAM 3 使用自定义 SAM License；不能因为 wrapper 是 MIT 就将 backend 权重/模型标为 MIT/Apache。
- **依据：** 两个仓库的当前 LICENSE 文件。
- **限制：** 仅记录许可文本事实，不替代法律意见。
- **Benchmark：** `BEN-SKETCH-010`。
