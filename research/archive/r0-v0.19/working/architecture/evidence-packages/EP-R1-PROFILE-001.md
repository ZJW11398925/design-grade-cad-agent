# EP-R1-PROFILE-001 — Real Project / Design-office Profile Evidence Package

**状态：** `planned-high-value-evidence`  
**服务范围：** R1.4/R1.6；R1-G05 / R1-G08；COV-16、COV-18、COV-19。

## Decision Question

系统的 Profile/Rule Engine 能否表达一份真实项目或设计院交付规则的最小可用子集，并将 mandatory、recommended、project override、serialization preference 和 unknown/unsupported 明确分开？

## 可接受的 Evidence Source

优先级从高到低：

1. 用户/团队实际项目的 DWT/DWG/DXF 模板、CTB/STB、图层/文字/标注标准或书面交付要求；
2. 设计院或项目提供的正式 CAD 制图标准；
3. 有明确适用范围与版本的地方/行业标准作为补充；
4. 仅公开教程或个人习惯不能作为 authoritative Profile。

资产可脱敏，但必须保留规则来源类别、版本/日期和适用范围。

## 最小规则子集

至少覆盖可从真实资产中确定的若干类：

- layer naming / layer attributes；
- linetype / lineweight policy；
- text / dimension style；
- unit / coordinate / elevation policy；
- entity-type policy；
- layout/modelspace policy（若适用）；
- serialization equivalence policy（如 symbol table name case）。

不要求一次覆盖全部规则；缺失项应显式 unsupported/unknown。

## Required Artifacts

- source assets + hash；
- provenance / applicability metadata；
- extracted machine-readable Profile；
- source-to-rule mapping；
- override chain examples；
- compliant fixture + deliberate mutants；
- validator outputs；
- third-party round-trip evidence where available。

## Gate Conditions

`pass_for_scope` 需要证明：

1. Profile 规则可以追溯到真实资产/文档；
2. Rule Engine 不依赖 LLM 记忆补全；
3. mandatory 与 preference 可区分；
4. AutoCAD 等外部工具的语义等价序列化差异不会被误判为 design failure；
5. 真实违规 mutant 能被结构化拒绝；
6. 不支持的规则会显式报告 coverage limit。

## 通过后仍不能宣称

- 已支持所有设计院；
- 已达到全国统一 CAD 交付规范；
- 可以自动报审；
- DWG native production workflow 已解决。
