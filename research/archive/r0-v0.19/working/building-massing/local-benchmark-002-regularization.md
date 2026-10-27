# LOCAL-BLDG-002：Regularization refusal / topology validator probe

**运行状态：** `synthetic-validator-probe / checks-pass`  
**运行日期：** 2026-10-26  
**脚本：** [`scripts/local_benchmark_002_regularization.py`](scripts/local_benchmark_002_regularization.py)  
**机器结果：** [`local-benchmark-002-regularization.json`](local-benchmark-002-regularization.json)  
**运行环境：** Shapely 2.1.2。没有执行 Building Regulariser、CartAGen 或 IfcOpenShell。

## 1. 这次实验到底验证了什么

实验用人工构造的几何候选验证：我们设计的 Validator 是否能识别几类已知危险变化。它不验证 Building Regulariser 或 CartAGen 的算法准确率，也不代表真实项目精度。

5 个 fixture assertions 全部通过，证明当前指标组合能捕捉这些**被植入的**失败；生产阈值仍未校准。

## 2. 几何指标结果

| 案例 | 候选变化 | IoU | 边界 Hausdorff | 相对面积误差 | 额外不变量 | 当前判断 |
|---|---|---:|---:|---:|---|---|
| `BEN-BLDG-001A` | 手抖矩形 → 轴对齐包络 | 0.9932 | 0.060 m | 0.68% | 无拓扑变化 | 可作为候选对照；是否接受仍需设计意图和校准容差 |
| `BEN-BLDG-005A` | 有意旋转矩形 → 全局轴对齐包络 | 0.5886 | 5.592 m | 69.90% | 方向意图丢失 | 拒绝自动应用 |
| `BEN-BLDG-006A` | U 形 → 外接矩形 | 0.6500 | 3.000 m | 53.85% | 凹槽丢失 | 拒绝自动应用 |
| `BEN-BLDG-006B` | 有院落孔洞 → 实心矩形 | 0.7000 | 3.000 m | 42.86% | 孔洞数 1 → 0 | 若孔洞已确认则硬拒绝 |
| `BEN-BLDG-007A` | 曲线建筑 → 最小旋转外接矩形 | 0.3985 | 6.973 m | 150.93% | 曲率形态丢失 | 保留 Trace / 人工复核 |
| `BEN-BLDG-015A` | 两个独立对象 → 一个合并对象 | 0.9800 | 4.000 m | 2.04% | 对象数 2 → 1；组件数 2 → 1 | 即使 IoU 很高也硬拒绝未授权合并 |

距离单位是本实验人为设定的米；它们不是推荐容差。

## 3. 场地级拓扑比单体 IoU 更关键

`BEN-BLDG-014A` 用两个原本共享 8 m 边界的建筑做对照：

- 两栋建筑单体 IoU 均为 `0.995`；
- 单体 Hausdorff 仅 `0.05 m`；
- 单体相对面积误差仅 `0.5%`；
- 但原先 `touches=true`，候选变成 `touches=false`；
- 共享边长 `8 m → 0 m`，出现 `0.1 m` 间隙，间隙面积 `0.8 m²`。

这意味着一个只逐个比较建筑轮廓的 Validator 会把结果看成“非常接近”，但场地模型已经产生新的缝隙。正式系统必须计算对象关系图和共享边，而不能只看单体几何指标。

## 4. 与开源项目自身测试的对照

Building Regulariser 当前公开 `tests/test_end_to_end.py` 检查几何有效性、空值、输入输出行数、相交性、IoU 与周长范围。该测试使用的 IoU 下限为 `0.4`，周长容许偏差为 `±60%`。这可以作为通用运行/粗粒度质量检查，但不足以直接当作设计院图纸的专业化验收标准；它也没有在该测试中检查跨建筑共享边/邻接图是否保持。

这个判断不是说项目宣称自己的默认测试等同生产验收，而是说明：**我们的验收合同必须比通用库的 smoke test 更严格，并覆盖不同层级的失败。**

## 5. 当前可冻结的结论

1. IoU 必须与边界距离、面积差、孔洞/组件数、对象 ID、邻接图一起报告。
2. 对象数/ID、已确认孔洞、锁定边界和受保护的邻接关系属于硬不变量；未经授权改变即拒绝。
3. 规则化只生成派生候选，不覆盖 Trace。
4. 没有设计意图证据、坐标尺度或项目容差时，输出应是 `preserve_trace` 或 `needs_review`，不是“自动修好”。
5. 本轮只验证了指标设计对合成反例的检出能力；真实库运行和真实草图校准仍是缺口。

## 6. 可回读来源

- [Building Regulariser end-to-end test](https://github.com/DPIRD-DMA/Building-Regulariser/blob/main/tests/test_end_to_end.py)
- [Building Regulariser changelog](https://github.com/DPIRD-DMA/Building-Regulariser/blob/main/CHANGELOG.md)
- [Issue #8 — Connected buildings become disconnected](https://github.com/DPIRD-DMA/Building-Regulariser/issues/8)
- [Issue #5 — simplify may create MultiPolygon](https://github.com/DPIRD-DMA/Building-Regulariser/issues/5)
- [Issue #4 — Bad regularization results on diagonal edges](https://github.com/DPIRD-DMA/Building-Regulariser/issues/4)
- [CartAGen FER API](https://cartagen.readthedocs.io/en/latest/reference/cartagen.regularize_building_fer.html)
- [IfcOpenShell Geometry Creation](https://docs.ifcopenshell.org/ifcopenshell-python/geometry_creation.html)
