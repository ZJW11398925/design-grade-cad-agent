# R1 Evidence Packages

本目录保存 R1 开发研究阶段的最小证据合同。它们不是功能需求清单，也不是“做完即可生产发布”的 checklist。

## Package Index

| Package | 研究对象 | 主要 Gate | 当前状态 |
|---|---|---|---|
| [EP-R1-SKETCH-001](EP-R1-SKETCH-001.md) | 真实/半真实场地草图、校准、Trace、Intent | G04 / G07 | planned |
| [EP-R1-ROAD-001](EP-R1-ROAD-001.md) | RoadGraph、简单 alignment、junction、Profile | G03 / G04 | planned |
| [EP-R1-IFC-001](EP-R1-IFC-001.md) | Footprint/Body/Placement/identity round-trip | G01 / G08 | planned mandatory spike |
| [EP-R1-ENV-001](EP-R1-ENV-001.md) | 独立太阳/阴影引擎交叉验证 | G03 / G08 | planned mandatory spike |
| [EP-R1-PROFILE-001](EP-R1-PROFILE-001.md) | 真实项目/设计院交付 Profile | G05 / G08 | planned high-value evidence |

统一机器可读登记见 [r1-evidence-gate-register-v0.1.yaml](../r1-evidence-gate-register-v0.1.yaml)。

## 统一 Verdict

- `pass_for_scope`：仅批准本包声明的能力范围。
- `conditional`：存在已知限制，但部分证据足以继续受限实验。
- `fail`：已知目标未达到。
- `insufficient_evidence`：不能判断，不等于 fail，也绝不能当 pass。

## Scope Leakage 禁止

例如：

- SKETCH package 通过 ≠ professional geometry 自动正确；
- ROAD package 通过 ≠ 中国道路规范合规；
- IFC package 通过 ≠ 完整 BIM authoring；
- ENV package 通过 ≠ 日照法规合规；
- PROFILE package 通过 ≠ 所有设计院交付标准均支持。
