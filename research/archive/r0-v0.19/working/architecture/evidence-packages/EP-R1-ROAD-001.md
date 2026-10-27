# EP-R1-ROAD-001 — Road Topology / Alignment / Profile Evidence Package

**状态：** `planned`  
**服务范围：** R1.3，R1-G03 / G04；COV-05..09、COV-21..23。

## Decision Question

系统能否在保留设计者道路意图的同时，建立正确 RoadGraph，生成简单工程化 centerline/alignment 与 junction candidate，并把道路语义、物理横断面和规则/Profile 适用性分开管理？

## 最小 Evidence Set

至少覆盖以下 targeted fixtures：

- T junction；
- near-parallel / close-but-not-connected roads；
- hand-drawn S curve 或明显曲线道路；
- 一个道路语义/特殊用途存在不确定性的 case；
- 一份明确来源的项目级 road profile 子集，若没有则明确标记 profile-blocked。

fixtures 可以半真实，但几何必须能代表真实场地设计失败模式；不能只用理想正交线网。

## Required Artifacts

- raw trace / control points；
- RoadGraph nodes/edges 与 topology truth；
- candidate centerline/alignment；
- line/arc primitives 及 continuity summary；
- junction inputs/outputs；
- classification evidence、unknown/proposed/confirmed state；
- Profile source/version/applicability；
- AtomicChangeSet for node move / junction repair；
- before/after diff and validator results。

## Metrics / Checks

- node/edge correctness；
- false intersection / missing intersection；
- connected component changes；
- centerline deviation from confirmed intent；
- geometry validity；
- G0/G1 continuity（按适用范围）；
- cross-section continuity；
- junction gap/overlap/self-intersection；
- rule applicability state；
- change-set atomicity。

## Gate Conditions

`pass_for_scope` 需要证明：

1. RoadGraph 与 visible geometry 分离，拓扑错误可被 validator 捕获；
2. near-parallel 道路不会因为 snap/merge 启发式被错误连通；
3. T junction 修改通过 AtomicChangeSet 一次性提交或整体拒绝；
4. road class/function/access/special-use 与 physical profile 分离；
5. 未核验的中国工程参数不会静默成为 confirmed default；
6. line/arc solver 可以替换，而无需重构 canonical RoadObject。

## 失败时的处置

- alignment 不可靠：保留 trace/control points，标记 needs_review；
- road class 不确定：保持 candidate/unknown；
- Profile 缺失：允许 geometry research 继续，但 compliance/profile validation blocked。

## 通过后仍不能宣称

- 已满足中国城市道路完整工程规范；
- 已覆盖 clothoid、纵断面、复杂环岛或交通组织；
- 能自动决定消防/服务道路所有法定参数。
