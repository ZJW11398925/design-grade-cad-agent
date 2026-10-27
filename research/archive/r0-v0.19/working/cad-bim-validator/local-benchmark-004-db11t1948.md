# LOCAL-CAD-004：DB11/T 1948-2021 来源型 Profile 子集探针

**状态：** `testable_checks_pass / full_profile_compliance=false`  
**运行日期：** 2026-10-26  
**环境：** Python 3.13.5、ezdxf 1.4.4、Shapely 2.1.2。  
**样例：** [`samples/sample-db11t1948-excerpt.dxf`](samples/sample-db11t1948-excerpt.dxf)；[manifest](samples/sample-db11t1948-excerpt.manifest.json)；[机器结果](local-benchmark-004-db11t1948.json)。

## 1. 为什么选这份标准

DB11/T 1948—2021 是北京市地方标准，适用于北京市域内国土空间详细规划的计算机辅助制图。官方状态页在 2026-10-26 核对时标为现行，实施日期为 2022-07-01，并替代 DB11/T 997-2013。它不是全国通用标准，也没有被选为用户项目的默认标准。

本次只用它作为一个**真实来源型 Profile 的工程样例**，测试标准条款能否转成机器规则，并保留适用范围与阻断项。

## 2. 实际编码的来源型规则

| 来源规则 | 编码结果 | 测试结果 |
|---|---|---|
| 2.1.5 图形颜色采用真彩色 | 使用 RGB true color，而非只写 ACI | 通过 |
| 2.2.3 长度单位米、面积平方米，精确到小数点后两位 | DXF `$INSUNITS=6`；显示精度单独保存，不对几何坐标自动取整 | 单位检查通过；显示精度由 Profile 记录，未输出标注样例 |
| 2.4.1 不得自交，相邻面状图形不得重叠 | Shapely 检查闭合多边形有效性与相邻多边形交叠面积 | 正常样例通过；人为植入重叠的 mutant 被检测 |
| 2.4.2 线状要素为多段线/弧线，面状要素由连续线段/弧段闭合 | 道路线使用 LWPOLYLINE，面要素使用闭合 LWPOLYLINE | 通过 |
| 3.1.3 CAD 图层命名 | 使用标准原文中的具体层名，规则元数据记录命名结构与可省略段 | 具体层名通过；通用命名 parser 尚未实现 |
| 附录 D 表 D.2 道路层名与颜色 | 已定道路中线 RGB(0,0,0)，已定道路红线 RGB(255,0,0)，新定道路红线 RGB(0,0,255) | 通过 |
| 附录 B 表 B.1 两类城镇住宅用地颜色 | 使用原文给出的 RGB 值和图层名 | 通过 |

**线宽没有被擅自固定。** 该标准的相关表格备注中存在按图面效果确定线宽的情形，所以本轮没有给这些样例层补造一个“标准线宽”。

## 3. 结果必须如实解释

- ezdxf 同库写入/重读后 `audit()` 未修复错误数为 0；
- 来源型图层名称与 RGB 属性检查通过；
- 面要素闭合和相邻面不重叠检查通过；
- 人为把第二个面要素左移 0.5 m，制造重叠后，Validator 检测到 `ADJACENT_AREA_OVERLAP`；
- 但该样例坐标是人为构造的本地米制坐标，**并没有北京地方平面/高程坐标系及其与国家空间参考系的连接证据**，因此 2.2.1 被标为 `blocked`，总体 `full_profile_compliance=false`。

这正是期望的行为：一份 DXF 可以在已测试的图层、颜色、实体类型和拓扑子集中通过，但仍因坐标基准证据缺失而不能被宣称完全合规。

## 4. 对 Agent 的直接启示

1. Profile 要求必须有 `source_document + clause/table + applicability + requirement_kind + validation_method`，不能只保存属性值。
2. 标准里的“未规定”“明确允许自定”和“本轮未知”必须区分。
3. 单位正确不代表坐标系正确；DXF `$INSUNITS` 不足以证明地理参考合规。
4. DXF audit 不能检查相邻面重叠、道路拓扑或设计意图；需要自研几何 Validator。
5. 标准适用范围本身就是 Validator 的输入。将北京详细规划标准套到其他地区或建筑施工图，必须先被拒绝或要求确认。

## 5. 当前边界

- 仅提取少量规则，不是 DB11/T 1948-2021 全量 Profile；
- 官方符号库和字体库链接存在，但本轮资源下载请求返回内部错误，未审查其内容与许可；
- 未在 LibreCAD/AutoCAD 中打开/保存该样例；
- 未覆盖图框、打印比例、全部图层表、完整符号库、GIS-CAD 映射、真实地理坐标或设计院内部模板；
- 不能据此宣称完整标准符合性。

## 6. 官方来源

- [官方标准全文 PDF](https://ghzrzyw.beijing.gov.cn/biaozhunguanli/bz/cxgh/202207/P020220711347172743065.pdf)
- [全国标准信息公共服务平台：现行状态与替代关系](https://std.samr.gov.cn/db/search/stdDBDetailed?id=D7B84EB1F2C445E9E05397BE0A0AD18E)
- [北京市地方标准发布通知](https://scjgj.beijing.gov.cn/zwxx/gs/dfbzgg/202112/t20211231_2579609.html)
