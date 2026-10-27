# Building Trace → Professional Footprint → Massing：首轮分析

**状态：** `candidate-analysis`；不是最终架构决定。  
**BATCH：** `BATCH-003`。

## 1. 当前主线判断

建筑这一段不能被建模成：

```text
rough polygon → orthogonalize() → extrude(height=guessed) → done
```

更合理的是：

```text
TraceObject
  ↓
Footprint Intent Assessment
  ├─ preserve
  ├─ regularize candidate
  └─ needs review
  ↓
Professional Footprint Revision
  ↓
Massing Parameters (height/floors/floor height/typology/provenance)
  ↓
Same Building Object
  ├─ Plan / Footprint representation
  └─ Model / Body representation
  ↓
Independent 2D↔3D consistency checks
```

## 2. Building Regulariser：值得研究的是“候选正规化”，不是直接采用默认结果

Building Regulariser 当前公开说明包含：主方向对齐、可选 45°、近矩形/近圆形转换、简化和邻楼方向对齐；同时暴露 `simplify_tolerance`、`neighbor_max_rotation`、circle IoU threshold 等参数。

对本项目的直接启发：

- 正规化天然包含“改变几何”的行为，因此必须作为 derivative revision，而不是覆盖 Trace；
- `neighbor_alignment` 可能有规划设计价值，但也可能把有意的旋转建筑误拉齐；
- “near rectangle → perfect rectangle”“near circle → perfect circle”在遥感制图中可能合理，在设计草图中却可能改掉真实设计意图；
- README 建议 simplification tolerance 与 raster pixel size 相关，这更说明参数不能跨域直接固定为设计草图默认值。

因此第一版 Agent 不应问“要不要正交化所有建筑”，而应先判断**规则化意图是否有证据**。

## 3. UrbGEN：说明规划指标不足以唯一决定建筑形态

UrbGEN 以 site boundary、setback、BCR、FAR、height、orientation 等约束生成多种 3D massing，并提供 I/L/T/H/C/U/Plus/Courtyard 等 footprint grammar。

它本身就强调：相同 BCR/FAR 可以对应非常不同的形态。这一点对我们的系统极重要：

> 规划指标是约束，不是建筑形状的唯一解。

因此当草图已经表达了一个粗略建筑位置/形态时，Agent 应优先保留该设计意图，在约束下专业化；不能因为存在 FAR/BCR 就重新生成一套完全不同的建筑布局。

Typology 更适合作为：

- 对已有轮廓的解释候选；
- 缺少具体形态时的方案生成 grammar；
- 用户要求探索替代方案时的可控变量。

而不是自动真值标签。

## 4. IfcOpenShell：非常接近我们需要的 2D/3D identity 模型

官方文档明确区分 Object Placement 与 Representation，并允许同一对象存在：

- `Plan / Footprint / PLAN_VIEW`
- `Model / Body / MODEL_VIEW`
- `Axis / GRAPH_VIEW`
- Annotation 等其他 representation context。

任意 2D profile 还可以挤出为 3D representation；profile 可包含直线、圆弧和内孔。

这支持一个关键架构方向：

```text
BuildingObject B-017
  identity/provenance
  placement
  trace_ref
  professional_footprint
  massing_parameters
  representations:
    footprint_2d
    body_3d
```

而不是维护一个 DXF polygon 和一个完全独立的 3D mesh。

但 IFC 允许多表示并不自动保证它们一致。因此本项目必须有独立 Validator，例如比较 `Body` 的 XY 投影与 `Footprint` 的边界差异。

## 5. COMPAS 的潜在角色

COMPAS 的定位是 AEC 计算研究的通用 Python 基础设施，包含 geometry、datastructures、tolerance、serialization，并可在 Rhino/Grasshopper/Blender 等环境使用。

它更像潜在的**中立几何/数据基础设施**，而不是建筑 massing 生成器或 IFC 编译器。是否进入最终技术栈要看后续 CAD-IR / dependency graph 是否真的受益，当前不做选型。

## 6. 许可初步事实

- Building Regulariser：MIT；README/当前 LICENSE 已读取。
- UrbGEN：MIT；当前 README/LICENSE 已读取。
- COMPAS 主库：MIT。
- IfcOpenShell 仓库是 mixed-license 工程。当前 README 对 `ifcopenshell-python` 标为 LGPL-3.0-or-later，仓库同时存在 GPLv3 和 LGPLv3 license 文本；实际集成必须按具体组件和分发方式治理，不能写成“整个 IfcOpenShell = 某一个许可证”。

以上仅是许可文本事实，不是法律意见。

## 7. provisional 建筑对象状态

```text
BuildingObject
  id
  source_trace_ref
  footprint:
    trace_geometry
    professional_revision
    regularization_method
    diff_metrics
    review_state
  semantic:
    typology
    typology_state
  massing:
    elevation
    height
    floors
    floor_height
    parameter_sources
    confidence/review_state
  placement
  representations:
    plan_footprint
    model_body
  locked_constraints
  provenance
```

这里的 `height/floors/typology` 都不是必填真值；可以保持 unknown。

## 8. 本批必须设计的失败 Benchmark

- 轻微手抖矩形：应产生可比较 regularized candidate，但 Trace 不丢。
- 有意旋转建筑：邻楼对齐不能把它强制转正。
- L/U/院落建筑：不能被近矩形规则吞掉洞/凹槽。
- 曲线/圆弧建筑：正交化必须拒绝或局部处理。
- 两个很近但独立的建筑：不能因为几何清洗发生 merge。
- 只有 footprint、无高度：可以形成 2D Professional Footprint，但 3D 高度保持 unknown/proposed。
- 已确认高度：Footprint→Body 后 XY 投影必须一致。
- 修改 footprint：Body 必须被标记 stale/rebuild-required，而不是悄悄保留旧体量。
- 规划约束与草图意图冲突：产生 conflict，不自动重做整个方案。

## 9. 与总体闭环的关系

BATCH-003 不是“建筑生成项目”。它只负责把入口 Trace 推进到**可分析的专业 footprint + 早期 massing + 同一对象 2D/3D 表达**。

它一旦达到 `ready-for-A1`，下一步应回到全局 Coverage，优先考虑：

- `COV-16..19` CAD/BIM 编译与 Validator；
- `COV-14` 日照/遮挡的独立分析线；
- 道路 BATCH-001 的未闭合项是否出现新解法。

不能自动转入户型、立面或生成式建筑设计。

## 10. LOCAL-BLDG-001：2D↔3D 一致性测量基线

本地环境只具备 Shapely 2.1.2；IfcOpenShell、Building Regulariser、COMPAS 未安装。因此本轮没有伪装成真实项目测试，只验证未来 Validator 的几何测量逻辑。

使用带凹槽的 U 形 footprint，对 Body 的 XY 投影构造四种合成状态：

| Case | IoU | Hausdorff (m) | centroid shift (m) | symmetric diff (m²) |
|---|---:|---:|---:|---:|
| exact | 1.0000 | 0.0000 | 0.0000 | 0.0000 |
| placement drift | 0.9219 | 0.2693 | 0.2693 | 13.0000 |
| 1.5° rotation drift | 0.9556 | 0.2338 | 0.0000 | 7.2579 |
| footprint revised, body stale | 0.9738 | 0.6000 | 0.1474 | 4.2000 |

最重要的结果不是数值阈值，而是：即使旧 Body 与新 footprint 的 IoU 仍约 0.974，它也已经是**逻辑过期的 representation**。因此 2D↔3D 一致性必须同时依赖：

- geometry comparison；
- Object Placement；
- authoritative revision ID；
- dependency/stale state；
- object identity。

这支持 `CAP-3D-05/06`，但不证明 IfcOpenShell round-trip 已通过。


## 11. 第二波源码与失败报告复核（2026-10-26）

### Building Regulariser 的公开测试边界

当前 `tests/test_end_to_end.py` 检查 geometry validity、null、row count、input/output intersection、IoU >= 0.4 和周长 ±60% 范围。它可以用于粗粒度回归/运行检查，但不足以支撑严格的设计意图保真或场地级拓扑验收。当前仓库 `CHANGELOG.md` 对 Issue #5 记录了修复路径；不应继续把该历史问题描述成当前必现。

### 未解决的场地级风险

Issue #8 的维护者回复说明每个 polygon 独立处理，算法不理解共享边/相交关系；当时维护者认为 topology-aware 实现需要较大重写，当前 changelog 未列出修复。这与我们的设计目标直接冲突：单体规则化后即使轮廓合理，建筑组仍可能产生缝隙。该公开 Issue 不是当前版本独立复现，但必须进入回归测试。

### CartAGen FER 对照路线

官方文档称 FER 通过主方向估计、近似平行/垂直边调整、Douglas–Peucker、最小旋转矩形与局部重建保持整体形状；但仍假设大致正交的建筑，并给出 `length=6m`、`area=6m²` 默认值（小面积对象可被过滤）。它比简单外接矩形更值得作为候选对照，但同样不能把遥感/制图默认值直接搬进规划草图。文档版本标识存在不一致，尚未冻结精确版本。

## 12. LOCAL-BLDG-002：候选指标覆盖检查

新增脚本 `scripts/local_benchmark_002_regularization.py`，以 Shapely 2.1.2 构造七个几何/状态反例；五个指标/不变量断言全部通过。

最有解释力的两个结果：

- 两个共享边的建筑单体 IoU 均为 0.995、Hausdorff 仅 0.05 m，但 8 m 共享边消失并产生 0.1 m 缝隙。
- 两个独立建筑合并后，全局 IoU 仍有 0.98，但对象数 2→1、组件数 2→1。

因此 Validator 必须分层检查：几何偏差向量、单体拓扑、场地关系图、对象身份/版本。数值阈值尚未冻结；这些结果只验证人工构造反例能被当前指标检测，不是算法性能结论。

## 13. IFC representation 生命周期与未执行项

IfcOpenShell 源码核验确认：Footprint API 创建 `GeometricCurveSet`；Profile API 可把含内环的 profile 挤出为 Body；`assign_representation` 会追加 representation，`unassign_representation` 与 `remove_representation` 分别承担解除关联和清理职责。因此更新流程需要显式替换策略，不能只反复 assign。

当前运行环境没有 IfcOpenShell，且包索引因 DNS/网络不可用，真实 IFC write/read 未执行。`ifc-roundtrip-contract-v0.1.md` 定义了之后需要运行的检查，但不能把合同写成测试通过。

## 14. 本批边界决定

BATCH-003 进入 `bounded-paused / unclosed`：当前源码/公开失败报告/合成 Validator 研究已达到有用的局部边界，但 A1 仍受早期搜索截断未知阻断，真实 IFC round-trip 受运行环境阻断，真实设计草图阈值也缺数据。为避免局部研究无限扩张，主线返回 Coverage Dashboard，下一条精确研究线转向 `COV-16..19` CAD/BIM Compiler + Validator。
