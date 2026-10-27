# R0 v0.8 工作区快照说明

**日期：** 2026-10-26  
**状态：** 研究/合成验证工作区，不是生产发布，不代表完整端到端系统。

## 本版本新增

1. `BATCH-005` 环境分析首轮官方来源定位：Ladybug Core/Sunpath、pvlib SPA/NREL 报告、Honeybee-Radiance Direct Sun Hours、momepy；记录角色、许可、来源和未运行限制。
2. `LOCAL-ENV-001`：17 个断言函数直接调用通过；太阳位置与 Ladybug 公开 Sydney 示例在 0.5° 容差内相符；未知/估计高度、缺失北向、缺失上下文、不规则时间采样、height/north/content-hash stale 均有合成检查。
3. 跨流水线差距审计：明确多个局部合成证明不能相加成为完整产品证明，主要缺口是共享对象/版本/坐标/来源 lineage 与真实输入。
4. `E2E-FIXTURE-001`：共享 synthetic site fixture，含 site boundary、road centerline、green space、两个 building footprints（一个合成已知高度、一个高度 unknown）、传感器网格、坐标框架/北向/时间。
5. `LOCAL-E2E-ENV-001`：3/3 传感器预期状态通过，2/2 synthetic Footprint/Body identity 状态通过；height revision、geometry content hash（即使 revision 未更新）和 north 变化都标记旧结果 stale。
6. Fixture → provisional CAD-IR → DXF：8 个对象 ID、11 个 DXF 实体；同库回读 0 个 ezdxf audit errors/fixes；对象类别、geometry revision、content hash、layer 与测试坐标/闭合性通过；环境依赖指纹也能检测 geometry content 改变但 revision ID 未更新的情况。
7. 独立复核清单与 SHA-256 review manifest 已准备，但尚未由独立 reviewer 执行。

## 本版本不宣称

- 不宣称真实 raster-to-Trace、道路生成、建筑规则化已贯通。
- 不宣称生成或验证了 IFC；合成 Footprint/Body 检查不是实际 IFC/几何内核 round-trip。
- 不宣称第三方 CAD 应用兼容；DXF 仅由 ezdxf 同库回读。
- 不宣称太阳/阴影生产模拟精度、真实场地准确性或法规合规。
- 不批准任何 A1 或生产 Gate；BATCH-001/003/004 仍为 bounded-paused/unclosed，BATCH-002 仍需真实 paired site-sketch 和独立 A1，BATCH-005 仍为 bounded-checkpoint/unclosed。

## 当前唯一下一动作

`NEXT-E2E-002`：使用 `working/e2e-integration/independent-review-checklist-v0.1.md` 独立复核共享 fixture、CAD-IR、环境结果、DXF 与映射清单。真实 paired site-sketch 和第三方 CAD round-trip 是分开的后续 Gate。
