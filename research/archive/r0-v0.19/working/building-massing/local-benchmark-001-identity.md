# LOCAL-BLDG-001 — 2D Footprint ↔ projected Body consistency

**性质：** synthetic validator baseline；不验证 IfcOpenShell、Building Regulariser 或真实建筑设计性能。  
**环境：** Shapely 2.1.2。  

使用一个带真实凹槽的 U 形建筑 footprint，比较“3D Body 的 XY 投影”在完全一致、placement 漂移、轻微旋转漂移以及 footprint 已修改但 Body 未重建四种状态下的几何差异。

| Case | IoU | Hausdorff (m) | centroid shift (m) | symmetric diff (m²) |
|---|---:|---:|---:|---:|
| `exact_projection` | 1.000000 | 0.000000 | 0.000000 | 0.000000 |
| `placement_drift_0p25m_minus0p10m` | 0.921922 | 0.269258 | 0.269258 | 13.000000 |
| `rotation_drift_1p5deg` | 0.955644 | 0.233836 | 0.000000 | 7.257922 |
| `stale_body_after_footprint_revision` | 0.973750 | 0.600000 | 0.147359 | 4.200000 |

## 解释

- 完全一致投影应得到 0 边界误差。
- placement/rotation 轻微漂移时 IoU 仍可能很高，因此 2D↔3D Validator 不能只看 IoU；还要检查 placement、Hausdorff、centroid/orientation 和对象 identity。
- Footprint 改动后，即使旧 Body 与新 footprint 大面积重叠，也必须通过 dependency graph 将 Body 标为 `stale/rebuild-required`；几何相似不能替代依赖状态。
- 本测试没有运行 IfcOpenShell，只验证我们将来用于 IFC round-trip 的一致性测量方法。
