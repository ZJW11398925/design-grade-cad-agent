# Architecture Amendments after Challenge v0.1

**Applies to:** Provisional Architecture Synthesis v0.2  
**Status:** required for R1 Foundation.

## Required amendments

1. **Atomic ChangeSet**：多对象拓扑修改必须 all-or-nothing commit。
2. **Proposal Snapshot / Preview Artifact**：未提交方案允许运行 analysis/compiler/validator，但结果只能 `preview_only`。
3. **Generalized Dependency Graph**：对象 revision、Calibration、Profile/Rule、method、context、delivery profile 都是一等依赖。
4. **Conditional Rule Applicability**：规则解析支持 applicable / conditional / not-applicable / blocked。
5. **World separation**：canonical / preview / external artifact 三类状态不得混用。

## R1 implementation prohibition

- 不用 CAD handle 作为 canonical object ID；
- 不持久化第三方 geometry object 作为唯一 canonical geometry；
- 不把规范参数写死在 prompt；
- 不允许 preview artifact 冒充 current；
- 不允许 external file 的“last saved”状态直接覆盖 canonical。
