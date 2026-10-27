# BATCH-002 Real Benchmark Contract v0.1

**状态：** `provisional-data-contract`；用于定义真实/半真实样例的最低证据要求，不是精度阈值或正式 Benchmark 通过标准。  
**服务范围：** `COV-01..04`，并为 `COV-05/10/13/20` 提供可信入口。  
**不服务：** 道路工程路线、建筑 typology、日照、CAD 图层/线型/线宽或最终规范合规。

## 1. 为什么需要三层 Benchmark，而不是一个“真实样例集”

入口系统同时要验证几何可测性、设计意图保留和真实世界泛化。单一数据集很难同时提供三种真值，因此 R0 采用分层 Benchmark：

### Tier A — Controlled Paired Raster

从具有明确矢量/坐标真值的场地对象生成 raster，再施加可记录的扫描、拍照、透视、模糊、噪声、标注覆盖等退化。

- 优点：几何真值精确，适合测 calibration / contour / topology error。
- 限制：不是自然的人类设计草图，不能用来证明真实草图泛化能力。

### Tier B — Human Sketch on Known Base

设计者在具有已知红线、比例或底图控制的场地上进行手绘/批注式规划；同时保留已确认的设计意图记录。

- 优点：能测试“手绘表达 → Trace/Intent”之间的真实歧义。
- 限制：仍是受控采集，不能等同于历史项目现场资料。

### Tier C — Field Paired Case

真实设计过程中的草图/批注与后续 CAD/BIM 或人工确认的 Trace/Intent 成对保存。

- 优点：最接近真实工作流。
- 限制：版权、隐私、版本一致性和“最终 CAD 是否等于原草图真实意图”都需要单独核验。

**规则：** Tier A 可以先行建立测量体系；没有 Tier B/C 时，任何真实设计性能结论保持 `unknown`。

## 2. 一个 Benchmark Case 的最低文件合同

每个 case 采用不可变 Source + 独立真值/注释文件，不允许在原图上覆盖修改。

```text
CASE-xxxx/
├─ source/
│  ├─ original.<png|jpg|tif|pdf>
│  └─ source-metadata.json
├─ control/
│  ├─ reference-frame.json
│  ├─ control-points.geojson          # 可空
│  ├─ known-dimensions.json           # 可空
│  └─ locked-references.geojson       # 红线/已知基准，可空
├─ truth/
│  ├─ trace-raw.geojson               # 人工忠实 Trace
│  ├─ semantic-labels.geojson         # 建筑/道路/绿地/边界/unknown 等
│  ├─ ambiguity-regions.geojson       # 有争议区域，可空
│  └─ intent-notes.json               # Tier B/C 才要求
├─ derived/
│  └─ <algorithm outputs...>
└─ review/
   ├─ reviewer-decisions.jsonl
   └─ benchmark-report.json
```

## 3. Source Metadata

至少记录：

- `case_id`
- `tier`: `A_controlled | B_human_known_base | C_field_paired`
- `source_kind`: `scan | phone_photo | screenshot | exported_raster | pdf_page | overlay`
- `source_immutable_sha256`：仅对进入正式 Benchmark 的不可变输入计算，用于防止样例漂移；普通研究文档不因此全面哈希化。
- 图像尺寸 / DPI（若可靠）
- 是否存在透视、镜头畸变、裁剪、拼接
- 来源许可/授权状态
- 是否允许公开 Benchmark；若否，仅保存内部 case ID 与必要元数据

## 4. Reference Frame 状态

必须显式从以下状态中选择，不允许一个 `calibrated=true` 覆盖所有含义：

1. `image_space_unscaled`
2. `local_metric_scaled`
3. `project_aligned`
4. `georeferenced`

并记录：

- transform type：`identity | scale_only | similarity | affine | homography | gcp_warp`
- 控制点来源与 reviewer
- 变换矩阵/参数
- residual mean / median / P95 / max（适用时）
- outlier / rejected control points
- scale evidence
- origin/orientation evidence
- CRS / survey datum（若存在）
- `review_state: proposed | reviewed | confirmed | rejected`

### 禁止行为

- 只有一个确认尺寸时，禁止自动晋升为 `project_aligned` 或 `georeferenced`。
- 仅凭打印比例、截图缩放比例或视觉估计，不得标记为 measured scale。
- 估算值必须单独标 `estimated`，并保留依据。

## 5. 人工 Trace Ground Truth

`trace-raw.geojson` 的目标不是“画得专业”，而是忠实记录 Source 中可见的设计线/区域。

人工 Trace 协议：

- 不主动正交化建筑；
- 不主动圆滑道路；
- 不补全图中不可见/被遮挡的边界；
- 对遮挡、断线、模糊边界使用 ambiguity 标记，而不是猜；
- 红线、控制点、已知尺寸等权威参考单独保存并 `locked=true`；
- 同一对象若存在多种合理 Trace，可保留 alternative revision，而不是强迫单一真值。

## 6. 语义标签合同

最小标签集合暂定：

- `building_candidate`
- `road_candidate`
- `green_candidate`
- `site_boundary_candidate`
- `water_candidate`
- `annotation_text_or_symbol`
- `unknown`

这只是入口语义，不是专业对象分类。比如 `road_candidate` 不包含主干/次干/支路、消防道路等设计等级。

每个 label 同时记录：

- geometry link / object ID
- `label_state: candidate | reviewed | confirmed | disputed`
- reviewer
- evidence region
- confidence（若来自模型，保留模型原值；人工确认不伪造成概率）

## 7. 评价指标：必须分层

### 7.1 Calibration

- control-point reprojection residual
- physical point error（有物理真值时）
- scale relative error
- locked-reference displacement

### 7.2 Semantic Candidate

- per-class precision / recall / F1 或 IoU（仅在有像素/区域真值时）
- missed-object / false-object count
- uncertainty calibration / review burden（后续有足够样本时）

### 7.3 Trace Fidelity

至少联合使用：

- boundary distance（Hausdorff + percentile distance）
- area difference / IoU（适用于 polygon）
- vertex/segment displacement
- component / hole count
- self-intersection / invalid geometry
- endpoint / junction deviation（线网络）
- locked reference identity

**禁止：** 用单一 IoU、面积误差或“看起来一样”作为 Trace 通过标准。

### 7.4 Human Review Cost

真实样例应记录：

- 需要人工确认的对象数；
- 修改对象数；
- 修改类型（semantic / trace / calibration / ambiguity）；
- reviewer time（若采集条件允许）。

R0 暂不冻结最低时间/精度阈值；先获取基线分布再设 Gate。

## 8. 必须覆盖的场景类型

不规定虚假的固定样本数量，但正式入口 Benchmark 至少要出现以下失效类型：

- 正视扫描/导出图；
- 有透视的手机拍照；
- 只有一个已知尺寸；
- 有红线/控制点的项目对齐；
- 线条断裂或交叉；
- 文字/箭头覆盖道路或建筑；
- 曲线/不规则道路边界；
- 不规则建筑/绿地边界；
- 低对比、压缩、模糊；
- 建筑、道路、绿地相互接触或局部重叠；
- 明确存在无法判断的区域。

## 9. 版本与泄漏控制

- Source、truth、derived、review 分目录；算法输出不能写回 truth。
- 每次算法版本/参数改变生成新的 `run_id`。
- 调参时使用的 cases 与最终独立评价 cases 必须标记角色，避免把反复看过的样例当作独立测试。
- 若未来训练/微调模型，训练数据与独立 Benchmark 必须另行治理；R0 当前不把 Benchmark 自动纳入训练集。

## 10. 当前数据缺口

2026-10-26 的初步公开检索触达了大量 floorplan 数据集，以及基于 OSM/QGIS 的 urban/masterplan vector 数据生成项目，但没有在本轮有限检索中确认一个同时具备以下条件的公开数据集：

> **真实建筑/规划场地草图 + 明确尺度/坐标 + 人工忠实 Trace + 语义标签 + 对应专业场地几何/CAD**。

因此当前策略是：

1. 用公开矢量场地数据建立 Tier A，验证测量链；
2. 设计 Tier B 的受控人类草图采集；
3. 当获得合法可用的真实项目过程资料时建立 Tier C；
4. 不用 floorplan 数据集替代 site-plan field truth。

此结论是本轮发现边界，不是“互联网上绝不存在此类数据集”的声明。

## 11. BATCH-002 的 A1 提交条件

数据合同完成后，BATCH-002 仍不能自动关闭。提交 A1 时至少应带：

- 来源路线与访问边界；
- 当前 SAM3/SamGeo/OpenCV/GDAL/Potrace 许可/能力定位；
- `LOCAL-SKETCH-001` 合成测量基线；
- 本真实 Benchmark 合同；
- 公开 paired site-sketch 数据缺口的有限检索记录；
- 清楚标明尚无 Tier B/C 实测结果。

A1 若通过，只授权整理本批入口证据，不等于选择最终视觉模型或证明生产精度。
