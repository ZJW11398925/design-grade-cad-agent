# LOCAL-SKETCH-001 — Synthetic calibration & trace fidelity

**用途：** 校准测量方法，不证明真实建筑/规划草图性能。

原始机器结果见 `local-benchmark-001.json`。

## 结论摘要

1. 四点 homography 的输出误差随控制点点击误差明显传播，因此 `ReferenceFrame` 必须保存 residual / uncertainty，而不能只有 `calibrated=true`。
2. 两点确认尺寸可以建立比例，但不自动建立全局原点、方向或 CRS。
3. Douglas–Peucker 简化可能在面积变化很小的情况下产生明显局部边界偏移，因此 Trace Fidelity 不可只看 area/IoU。
4. 本测试没有语义模型、文字干扰、笔画粘连、扫描阴影、纸张弯曲和真实控制点误差；这些必须进入真实 Benchmark。
