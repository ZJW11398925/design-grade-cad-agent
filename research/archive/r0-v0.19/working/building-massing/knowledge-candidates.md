# Candidate Knowledge Records — BATCH-003

> 全部为 candidate；未经 A1、独立 Benchmark 或最终架构决策。

## KNO-BLDG-REG-001 — Regularization 必须是可回退的派生 revision

- **候选主张：** 建筑轮廓正交化、主方向对齐、圆形/矩形识别和邻楼方向对齐都会改变原几何，必须输出 `professional_revision` + diff，而不是覆盖 Trace。
- **依据：** Building Regulariser 当前公开功能/参数；BATCH-002 的 Trace 不覆盖原则。
- **限制：** 尚未对设计草图运行该库。
- **Benchmark：** `BEN-BLDG-001..002`, 待新增 BATCH-003 失败案例。

## KNO-BLDG-REG-002 — 遥感 footprint regularization 的默认阈值不能直接迁移到设计草图

- **候选主张：** pixel-size related simplify tolerance、45°/circle/neighbor alignment 等默认策略来自另一任务域；设计草图需要意图证据和人工回退。
- **依据：** Building Regulariser 文档；相关 footprint regularization 文献/CartAGen 文档线索。
- **限制：** 尚未建立真实草图阈值分布。

## KNO-BLDG-MASS-001 — FAR/BCR 等规划指标约束形态，但不唯一决定形态

- **候选主张：** 同一 FAR/BCR/height envelope 可产生多个 typology/massing；已有草图意图时不应被生成器覆盖。
- **依据：** UrbGEN 当前 README 的设计逻辑与多 typology 生成。
- **限制：** UrbGEN 不是中国规划规则源；本批不核验具体数值规范。
- **Benchmark：** 规划约束与草图意图冲突案例。

## KNO-BLDG-IFC-001 — 同一建筑对象可拥有 2D Footprint 与 3D Body，但一致性需独立验证

- **候选主张：** IFC representation contexts 可表达 Plan/Footprint、Model/Body、Axis 等，但存在这些 representation 不等于它们自动同步。
- **依据：** IfcOpenShell 官方 geometry creation / API 文档。
- **限制：** 尚未本地 round-trip。
- **Benchmark：** `BEN-3D-001` + 新增 projection consistency test。

## KNO-BLDG-PARAM-001 — 高度/层数/typology 必须带来源状态

- **候选主张：** early massing 可以存在 unknown/proposed 参数；不能为了生成 3D 而把估计层数伪装为确认值。
- **依据：** 本项目 uncertainty/provenance 原则；UrbGEN 将 height/floor parameters 作为显式输入。
- **限制：** 后续需与实际设计流程/规划约束结合。

## KNO-BLDG-LICENSE-001 — IfcOpenShell 必须做组件级许可证治理

- **候选主张：** 仓库同时包含 GPL/LGPL 许可文本，README 对不同工具列出不同许可；实际依赖准入不能只看根目录某一个 COPYING。
- **依据：** 当前仓库 README、COPYING、COPYING.LESSER。
- **限制：** 不构成法律意见；最终分发方案需单独复核。

## KNO-BLDG-IDENTITY-001 — 几何相似不能替代 representation dependency state

- **候选主张：** Footprint 改动后，Body 即使仍高度重叠，也必须被 dependency graph 标记为 stale；2D/3D 一致性 Validator 需要同时检查 revision/placement/identity 与几何差异。
- **依据：** `LOCAL-BLDG-001` synthetic validator baseline。
- **限制：** 未运行 IFC；数值阈值未冻结。
- **Benchmark：** `BEN-BLDG-010..011`, `BEN-3D-003`。

## KNO-BLDG-REG-003 — 单体 IoU/几何有效性不能证明场地级拓扑保持

- **候选主张：** 单体 footprint regularization 即使保持极高 IoU，也可能破坏相邻建筑共享边、邻接关系或对象身份；Validator 必须同时检查单体几何和场地级关系图。
- **依据：** Building Regulariser Issue #8 的公开描述与维护者回复（当前实现逐个处理 polygon，不理解相交/共享边关系；维护者当时说明需要较大重写）；`LOCAL-BLDG-002` 中两个单体 IoU 均为 0.995、但共享边 8 m 消失的合成反例。
- **限制：** Issue 是公开用户报告，不是当前版本独立复现；合成案例仅验证 Validator 指标，不证明库在该精确案例上的当前输出。
- **下游影响：** `COV-10`、`COV-04/05`、`COV-20`；新增场地级 topology contract。

## KNO-BLDG-REG-004 — Building Regulariser 的已报告 MultiPolygon 输入问题有后续修复记录

- **候选主张：** Issue #5 报告的 `simplify` / invalid geometry 导致 MultiPolygon 处理异常，在后续 changelog 中有明确修复记录：0.2.4 标注改进无效输入处理并处理 Issue #5，0.2.5 增加 MultiPolygon 回归测试并拓宽 `regularize_single_polygon` 类型签名。
- **依据：** 当前仓库 `CHANGELOG.md`、`tests/test_multipolygon.py` 与 Issue #5 维护者回复。
- **限制：** 不应继续把旧 Issue 描述为当前必现缺陷；仍需对目标版本运行自己的回归测试。当前本地环境未安装该库。

## KNO-BLDG-REG-005 — CartAGen FER 是可比较的形态保留路线，但默认参数和任务域不能直接迁移

- **候选主张：** CartAGen 文档将 FER 描述为估计主方向、迭代调整近似平行/垂直边，并结合 Douglas–Peucker、最小旋转矩形和局部重建；文档称其相对保持整体形状，但假设建筑大致为直角形态。当前文档给出的默认 `length=6.0 m`、`area=6.0 m²`，面积过滤可能使小于阈值的多边形被丢弃。
- **依据：** CartAGen 官方 API 文档与用户手册；文档将建筑正则化定位在航空/卫星影像分割生成的 footprint，且明确指出 recursive regression 可能很具破坏性。
- **限制：** 官方文档页面的版本标识在搜索结果与打开页面间不完全一致，本轮不锁定精确版本号；没有在本地运行 FER。EUPL 1.2 许可事实来自官方用户手册，不构成法律意见。
- **下游影响：** `COV-10`；作为对照算法，不作为最终方案。

## KNO-BLDG-IFC-002 — IFC Representation 更新必须有显式替换生命周期

- **候选主张：** IfcOpenShell 的 `assign_representation` 会把新 representation 加入产品表示集合；若应用只反复 assign 而不明确解除旧表示，旧 Footprint/Body 可能仍然挂在对象上。因此 Agent 必须管理当前 revision 与 representation 生命周期，更新时执行明确的 unassign/remove/replace 流程并回读验证。
- **依据：** IfcOpenShell v0.9.0 的 `assign_representation.py`、`unassign_representation.py`、`remove_representation.py`；官方 Geometry Creation 文档关于 Object Placement 与多个 Representation Context 的说明。
- **限制：** 源码检查已完成，但当前环境没有 IfcOpenShell，未执行 IFC 文件写入/重读；不能宣称 round-trip 通过。

## KNO-BLDG-VALIDATOR-001 — 不建立未经校准的单一几何总分

- **候选主张：** Validator 应输出偏差向量（IoU、Hausdorff、对称差面积、相对面积变化、边界距离分位数、component/hole、对象 ID 与关系图），而不是把 IoU 单独当作通过条件。
- **依据：** `LOCAL-BLDG-002` 的合成反例：对象合并仍可有 0.98 IoU；相邻建筑共享边断裂时单体 IoU 仍为 0.995；删除院落可通过几何有效性检查但 hole count 从 1 变 0。
- **限制：** 数值阈值未冻结；真实阈值必须由设计者配对标注、坐标精度和项目容差校准。
