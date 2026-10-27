# R0 Provisional Architecture Decision Register v0.1

> `PROVISIONAL` 只表示目前最能解释已有证据，不等于最终 G5 决策。

| DEC | 候选决定 | 状态 | 主要理由 | 重新打开条件 |
|---|---|---|---|---|
| `DEC-ARCH-001` | 自研 typed Canonical Site IR 是设计真值；DXF/IFC/CAD 文档为派生表示 | PROVISIONAL-STRONG | 需要同时承载 Source/Trace/provenance/road graph/building/analysis/stale，且 AutoCAD round-trip 已证明交付格式会规范化 | 若证明 IFC/其他开放模型可无损承担全部生命周期且不引入额外耦合 |
| `DEC-ARCH-002` | Source/Trace 不可被 Professional Geometry 覆盖 | PROVISIONAL-STRONG | 这是草图→专业化可解释/可回退的前提 | 仅当产品目标不再需要设计意图追溯 |
| `DEC-ARCH-003` | Agent 只能提交 ChangeProposal，不直接写 confirmed canonical state | PROVISIONAL-STRONG | 多处 evidence/validator/规范不确定性要求显式权限边界 | 若未来确定性 policy 能授权某类低风险自动提交，可局部放宽 |
| `DEC-ARCH-004` | Rule/Profile Engine 独立于 LLM、Geometry Kernel 与 Compiler | PROVISIONAL-STRONG | 避免标准参数靠模型记忆；支持法域/版本/院标/项目 override | 若规则规模极小且产品边界永久固定 |
| `DEC-ARCH-005` | Road truth 以 graph + centerline/alignment + cross-section 为主，而非左右边线 | PROVISIONAL | 有利于连接、profile、junction、3D；尚缺真实道路 Benchmark | 真实复杂 site-road 样例证明该抽象不足 |
| `DEC-ARCH-006` | Building regularization 必须是 gated proposal | PROVISIONAL-STRONG | 开源 failure 已显示斜边、共享边、MultiPolygon 等风险 | 若真实数据证明某一受限对象类可安全自动化 |
| `DEC-ARCH-007` | 2D/3D/analysis/delivery 都是依赖 canonical revision 的 derived artifacts | PROVISIONAL-STRONG | 能统一 stale/rebuild/validation | 若某类对象必须原生 3D 才能定义其 2D 权威表达 |
| `DEC-ARCH-008` | MVP 默认 human-in-the-loop，不追求全自动草图转 CAD | PROVISIONAL-STRONG | 当前最大风险是语义/专业化误判，不是点击次数 | Tier B/C 真实数据和 validator 证明自动提交风险足够低 |
