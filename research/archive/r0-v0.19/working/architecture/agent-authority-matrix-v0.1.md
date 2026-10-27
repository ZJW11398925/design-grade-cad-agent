# Agent / Human / Rule / Validator 权限矩阵 v0.1

**状态：** `provisional-governance-contract`  
**目标：** 明确“谁可以提出、谁可以计算、谁可以确认、谁可以写入 canonical”，防止 Agent 在不确定场景中越权。

## 1. 权限代码

- `R`：可读取。
- `P`：可提出 proposal，但不能提交为 confirmed。
- `E`：可执行确定性计算/变换，但结果仍受权限状态约束。
- `C`：可确认并授权写入 canonical。
- `V`：可验证/否决，但不直接改设计。
- `LOCK`：明确禁止自动修改。

## 2. 核心矩阵

| 动作 | Agent | Deterministic Engine | Rule/Profile Engine | Validator | 设计者/授权审核者 |
|---|---|---|---|---|---|
| 读取 Source/Trace/Canonical | R | R | R | R | R |
| 修改原始 Source | LOCK | LOCK | LOCK | LOCK | 仅通过新 Source revision |
| 创建 segmentation/trace candidate | P | E | - | V | C/修订 |
| 确认对象语义（road/building/green） | P | - | 可给约束 | V | C |
| 建立 snap/node/validity 结果 | P | E | - | V | C（若改变设计含义） |
| 道路等级/服务功能分类 | P | 可算候选 | 可约束 | V | C（证据不足时） |
| 选择道路 Profile | P | - | E/resolve | V | C（项目上下文不明确时） |
| 生成 centerline/alignment candidate | P | E | 参数约束 | V | C |
| 修改锁定道路控制点 | LOCK | LOCK | LOCK | - | C（先解锁） |
| 建筑 regularization | P | E | 可约束 | V | C |
| 设定未知建筑高度 | P | - | 可限定 | V | C |
| 根据已确认高度挤出 massing | P | E | - | V | 自动可提交 derived representation |
| 设置法定/院标参数 | LOCK | - | E（仅已核验 Profile） | V | C/项目 override |
| 更新 Canonical confirmed geometry | P | - | - | V | C，或已授权 deterministic rule |
| 生成 DXF/IFC | P | E | Profile 输入 | V | 不需要逐实体确认 |
| 接受第三方 round-trip 差异 | P | - | policy 输入 | V | C（超出 policy 时） |
| 清除 stale 状态 | LOCK | 只有依赖重建后自动 | - | V | 不直接手工清除 |
| 生成局部修复 | P | E candidate | rule constraint | V | C（若改变 design intent） |
| 宣称“规范合规/可报审” | LOCK | - | 只能提供规则结果 | V within scope | C + 完整 Gate，R0 不允许 |
| 生产发布 | LOCK | - | - | V | C（未来正式 Gate） |

## 3. Authority State

建议 CanonicalObject 新增：

- `evidence_only`：Source/Trace 等证据对象；不可被 professionalization 覆盖。
- `candidate`：机器/Agent 候选。
- `rule_derived`：由确定性、已授权规则生成，可追溯到规则版本。
- `human_confirmed`：设计者明确确认。
- `locked`：后续自动变换不得修改。
- `stale`：上游依赖变化，当前表示不能继续作为 current 使用。
- `blocked`：缺关键输入/规则，禁止继续推导 confirmed 结果。

## 4. 高风险动作必须升级人工确认

以下任一条件出现，Agent 只能 proposal：

1. Professional Geometry 与 Trace 的偏差超过已校准 Gate；
2. 会改变道路连接关系或建筑对象数；
3. 会移动/修改锁定红线、控制点、项目坐标；
4. 道路用途或建筑高度为 unknown；
5. Profile 适用范围存在冲突或标准版本不明确；
6. Validator 返回 conditional / validator_error；
7. round-trip 差异不在 semantic equivalence policy 中；
8. 局部修复会连锁改变超过一个邻接设计对象。

## 5. 初版 MVP 的交互模式

MVP 默认采用：

```text
Agent 识别/解释
  -> 生成 proposal
  -> deterministic preview + diff
  -> Validator
  -> 用户确认
  -> 写 Canonical revision
  -> 局部 rebuild downstream
```

不采用“Agent 直接改 CAD 文件再让用户检查”的工作方式。
