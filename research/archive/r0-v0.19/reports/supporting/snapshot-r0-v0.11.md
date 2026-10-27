# R0 v0.11 snapshot — 本地复核吸收与研究阶段冻结

日期：2026-10-27

## 本快照解决什么

吸收用户对 E2E-FIXTURE-001 v0.3 的本地复核结果，并把发现的兼容性/验证器缺陷转换为正式开发阶段的验收合同；停止在 R0 继续逐项修实现。

## 关键新证据

- 35/35 包文件大小与 SHA-256 匹配；原 56 tests 通过。
- 合法 MultiPolygon 触发 `elevation_z` KeyError。
- LWPOLYLINE bulge 变化被误接受。
- LWPOLYLINE constant width 变化被误接受。
- 保留 XDATA 的 entity-type replacement 触发未处理 AttributeError。
- AutoCAD 2022 core engine round-trip 保留主要对象/单位/实体，但将业务图层线型名称 `CONTINUOUS` 规范化为 `Continuous`；原 validator 因大小写精确比较误判失败。

## 研究结论

- v0.3 维持 `conditional`，不得升级为 pass。
- bulge/width 属于 DXF 实体语义，必须进入 canonical geometry/semantic comparison。
- CAD symbol-table name 默认应 case-insensitive semantic compare；序列化 spelling 作为单独 diagnostic/policy。
- Validator 必须 fail-closed + structured-report，不得用未处理异常代替失败结果。
- 进一步修复推迟到正式开发阶段。

## 主线下一步

进入 `NEXT-R0-SYN-001`：R0 provisional architecture synthesis。目标是整合现有五条能力线，形成最小可行模块边界、IR/接口、证据等级、开发阶段验收合同与仍需真实数据验证的研究缺口，不继续对单一 Validator 做实现 hardening。
