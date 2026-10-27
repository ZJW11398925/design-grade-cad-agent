# EP-R1-SKETCH-001 — Real Site Sketch / Trace Evidence Package

**状态：** `planned`  
**服务范围：** R1.1，R1-G04 / R1-G07；COV-01..04、COV-20。

## Decision Question

在存在可靠尺度/边界基准的情况下，系统能否把真实或接近真实设计工作流的场地草图转换成可追溯 TraceObject，并让道路/建筑/绿地/红线的设计语义通过人工确认进入后续 canonical，而不把识别误差伪装成专业几何？

## 最小 Evidence Set

至少包含：

- 一个完整的非纯合成场地草图 case，带可靠尺度或项目边界；
- 一个包含明显手绘噪声/不规则线/遮挡或批注的 companion case；
- building、road、green、redline 四类中至少覆盖项目实际存在的类别；
- 人工复核的 trace geometry 与 semantic intent 记录；
- 原始 Source、控制基准、review decisions 与所有中间候选。

可以采用真实项目资料（脱敏后）、设计者重画 case、或在真实底图上的人工草图；不得只用程序生成的干净矢量图冒充 real case。

## Required Artifacts

- immutable source files + SHA-256；
- CalibrationFrame 输入与残差记录；
- raw trace、simplified trace、semantic candidates；
- human-reviewed trace/intent reference；
- per-object object_id / trace_revision / confidence / review state；
- failure annotations：missing segment、false object、wrong class、merged/split object、boundary drift；
- reproducible run manifest。

## Metrics（先记录分布，不预设统一阈值）

- boundary distance / Hausdorff；
- overlap / IoU（仅作补充，不单独决定 fidelity）；
- object count / split-merge errors；
- topology preservation；
- semantic confusion；
- calibration residual；
- human correction workload；
- unknown / needs-review rate。

## Gate Conditions

`pass_for_scope` 需要同时证明：

1. Source 与 Trace 可追溯且未被 professionalization 覆盖；
2. 尺度/坐标状态被正确区分，没有从不足证据虚构 CRS；
3. 关键对象可进入 human review，错误不会静默升级为 confirmed intent；
4. 评估报告同时呈现边界偏差、对象级错误和拓扑错误，而不是只报 IoU；
5. case 可以进入后续 Building/Road vertical slice。

## 失败时的处置

- segmentation 弱：允许退化到 manual-assisted trace，不阻断 Canonical architecture；
- calibration 不足：保持 image-space / local-scaled，不升级 project-coordinate；
- semantic 模糊：保持 unknown / proposed，进入 review queue。

## 通过后仍不能宣称

- 所有规划草图都可自动识别；
- 无需人工确认；
- Trace 已经是 professional CAD geometry；
- 具有全国通用的真实尺度/地理定位能力。
