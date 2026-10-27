# EP-R1-ENV-001 — Independent Solar / Shadow Cross-engine Evidence Package

**状态：** `planned-mandatory-spike`  
**服务范围：** R1.5/R1.6；R1-G03 / R1-G08；COV-14..15。

## Decision Question

对于同一 canonical geometry、location、north、date/time 和 context，内部 fixed-time shadow baseline 与独立太阳/阴影引擎是否在声明范围内给出一致、可解释的太阳位置和遮挡判断；并且输入 revision 变化能否可靠使结果 stale？

## 最小 Fixture

- 简单无遮挡 case；
- 单个遮挡建筑 case；
- height/placement mutation case；
- north/time mutation case；
- 一个 near-boundary / grazing shadow case，用于暴露数值敏感性。

## Required Artifacts

- canonical geometry + hashes；
- location/timezone/north/time sample；
- internal method output；
- independent engine output；
- solar vectors / shadow hit results；
- engine/method versions；
- dependency fingerprints；
- discrepancy report。

## Metrics / Checks

- solar altitude/azimuth difference；
- sensor shadow classification agreement；
- boundary/grazing disagreement；
- height/placement/north/time mutation stale behavior；
- missing context / unknown height blocking behavior。

不在本包预先写死“生产精度阈值”；阈值应在独立引擎和真实工程需求的基线分布后确定。

## Gate Conditions

`pass_for_scope`：可以说明 fixed-time direct-shadow baseline 在指定 fixture 上经独立引擎交叉验证，并且差异与 coverage limits 被记录。

## 通过后仍不能宣称

- 日照规范合规；
- 年度 daylight/radiation 精度；
- 复杂材质、反射、天气或热环境模拟已验证。
