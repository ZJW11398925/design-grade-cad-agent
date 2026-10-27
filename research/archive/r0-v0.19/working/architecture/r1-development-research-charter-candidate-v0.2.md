# R1 Development Research Charter — Candidate v0.2

**状态：** `candidate-after-charter-review`  
**性质：** 开发研究章程；允许建立最小 Foundation 和受限 vertical slices，但不代表正式产品能力已获批准。  
**基线：** R0 provisional architecture challenge = `survives_with_amendments`；Canonical Site IR v0.3。

## 1. R1 唯一目标

验证一条最小但真实可工作的设计闭环：

> 有可靠尺度/边界基准的简单场地草图 → human-confirmed Trace/Intent → Canonical Professional Site Model → 简单 road/building geometry → 3D massing → fixed-time shadow → DXF → independent validation → 修改一个设计参数 → stale/local rebuild/regression。

R1 成功不以“AI 自动化程度”衡量，而以**真值、身份、权限、依赖、派生表示和验证闭环是否可靠**衡量。

## 2. R1.0 Foundation — 必须最先完成

R1.0 只实现以下合同：

- Canonical Site IR typed model；
- stable object_id；
- semantic / geometry / parameter revisions；
- immutable Source/Trace references；
- ChangeProposal + AtomicChangeSet；
- ProposalSnapshot；
- authority/lock model；
- generalized dependency graph；
- stale propagation；
- structured ValidationResult；
- canonical / preview / external world separation；
- external reconcile contract。

**禁止：** 在 Foundation 尚未通过 R1-G01/G02/G03/G06 基础测试前接入复杂 AI、复杂道路、生成式规划或 UI 大工程。

## 3. R1.1 Input / Trace Slice

支持：一个 raster sketch、至少一个可靠尺度或边界、building/road/green/redline、manual-assisted confirmation、raw/simplified trace、image-space/local-metric 状态区分。

AI segmentation 是 adapter，不是架构依赖。即使先采用人工 trace，也必须先验证数据模型和 review workflow。

对应真实证据：`EP-R1-SKETCH-001`。

## 4. R1.2 Building Vertical Slice

- 2–3 buildings；
- rectangle / L / U 或同等简单但可表现凹槽的 footprint；
- preserve / regularize_candidate / needs_review；
- confirmed height；
- extrusion massing；
- footprint ↔ Body projection validation；
- height/placement change 只 stale 受影响 derived artifacts。

真实 regularization Gate 的提升依赖 `EP-R1-SKETCH-001` 中的建筑 case；IFC 身份链依赖 `EP-R1-IFC-001`。

## 5. R1.3 Road Vertical Slice

- RoadGraph；
- project-level primary/secondary/service labels；
- line / circular arc；
- simple cross-section；
- T junction；
- road surface；
- node move 通过 AtomicChangeSet；
- classification/profile unknown 可 block，不静默默认。

对应证据：`EP-R1-ROAD-001`。在该包未获得足够证据前，不宣称中国工程道路设计合规。

## 6. R1.4 DXF / Validation Slice

- frozen DXF target version；
- minimal Project Profile；
- compiler adapter；
- independent semantic validator；
- 已知 DXF hardening regressions；
- third-party CAD round-trip；
- semantic failure 与 serialization difference 分离。

真实交付规则能力依赖 `EP-R1-PROFILE-001`。

## 7. R1.5 Analysis / Stale Closure

- fixed-time direct shadow；
- location/north/time/height/context 显式输入；
- AnalysisResult 绑定 dependency hash；
- proposal preview 可运行分析但必须 `preview_only`；
- height/placement/north/time/method/profile 变化正确 stale。

独立引擎验证依赖 `EP-R1-ENV-001`。

## 8. R1.6 Mandatory Architecture Spikes

1. IFC Footprint + Body + Placement + identity round-trip — `EP-R1-IFC-001`；
2. independent solar/shadow cross-engine — `EP-R1-ENV-001`；
3. real Project/Design-office Profile — `EP-R1-PROFILE-001`；
4. clothoid adapter replaceability；
5. external CAD/BIM reconcile → diff + proposal。

前三项属于 R1-G08 的明确 Evidence Packages；后二项以 targeted spike + benchmark 形式保留。

## 9. Evidence Gates

| Gate | 要求 | 主要证据 |
|---|---|---|
| R1-G01 Identity | canonical/3D/DXF/IFC 具有稳定身份与映射 | Foundation + IFC/DXF |
| R1-G02 Authority | proposal/confirm/lock 无越权路径 | Foundation adversarial tests |
| R1-G03 Dependency | building/road/context/rule 变化正确 stale/local rebuild | Foundation + road + ENV |
| R1-G04 Geometry | 代表性拓扑/几何错误 fail closed | sketch/road/building fixtures |
| R1-G05 Delivery | third-party semantic round-trip + real Profile subset | DXF + PROFILE |
| R1-G06 Preview | ProposalSnapshot 不污染 current | Foundation tests |
| R1-G07 Real Case | 非纯合成 site sketch 贯通主链路 | SKETCH |
| R1-G08 Spikes | IFC + independent ENV + real Profile 有边界的运行证据 | IFC/ENV/PROFILE |

Gate verdict 与 package 状态见 `r1-evidence-gate-register-v0.1.yaml`。

## 10. R1 不做

- 自动生成完整社区方案；
- 户型/室内；
- 结构/机电；
- 复杂道路交通工程和完整纵断面；
- 全国法规自动合规；
- 原生 DWG production authoring；
- 多人实时协作；
- 施工图自动生成；
- 无人工确认的大范围自主设计修改。

## 11. 与 R0 未关闭研究的关系

R1 可以开始 Foundation，不要求先伪造 R0 全部 closed。未关闭的 R0 batch 继续作为证据缺口存在：

- BATCH-002 → EP-R1-SKETCH-001；
- BATCH-001 / road line → EP-R1-ROAD-001；
- BATCH-003 IFC / building → EP-R1-IFC-001；
- BATCH-005 external analysis → EP-R1-ENV-001；
- BATCH-004 real delivery profile → EP-R1-PROFILE-001。

如果新证据改变 canonical truth、module boundary、authority model 或 dependency model，则重开 architecture decision；若只影响阈值/算法/兼容性，则进入 R1 config/benchmark，不推倒 R0。

## 12. Scope Freeze Rule

任何新增功能进入 R1 backlog 前，必须回答：

1. 它服务 R1-G01..G08 中哪一个 Gate？
2. 它是否是 Evidence Package 必需步骤？
3. 如果删除它，最小闭环是否仍可验证？

若三个问题均不能给出明确答案，则默认延期到 R2+。

## 13. Charter Verdict

`r1_charter_candidate_ready_for_entry_planning`

下一动作：`NEXT-R1-ENTRY-001` — 只定义 R1.0 Foundation repo/package skeleton、contract tests 和第一批 typed fixtures；尚不启动复杂功能实现。
