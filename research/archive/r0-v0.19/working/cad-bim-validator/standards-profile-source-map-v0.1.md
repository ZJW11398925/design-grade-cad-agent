# Standards Profile Source Map v0.1 — DB11/T 1948-2021 excerpt

**目的：** 用一份可追溯的真实规范文本检验输出 Profile 的数据模型与 Validator，不代表为本项目选定北京标准。  
**当前状态：** official-source-backed excerpt / partial rule extraction / not a full compliance package。

## 1. 官方来源与适用范围

- 标准：DB11/T 1948—2021《国土空间详细规划计算机辅助制图标准》
- 官方全文 PDF：<https://ghzrzyw.beijing.gov.cn/biaozhunguanli/bz/cxgh/202207/P020220711347172743065.pdf>
- 官方标准状态页：<https://std.samr.gov.cn/db/search/stdDBDetailed?id=D7B84EB1F2C445E9E05397BE0A0A6D15>
- 官方发布通知：<https://scjgj.beijing.gov.cn/zwxx/gs/dfbzgg/202112/t20211231_2579609.html>
- 状态核对日期：2026-10-26；官方平台标记“现行”。实施日期 2022-07-01；替代 DB11/T 997-2013。
- 适用范围：北京市域内国土空间详细规划编制和管理涉及的计算机辅助制图。不能自动外推到其他省市、建筑施工图或任意设计院企业模板。
- 官方标准页面还列有《符号库》和“三册通用字体库”资源，但本轮点击资源返回内部错误；资源存在性有官方页面证据，实际下载/许可/内容尚未检查。

## 2. 已读取的可机器化规则

| 规则 | 原文定位 | 可转成的 Validator | 注意事项 |
|---|---|---|---|
| 适用范围 | 1.0.2 | Profile applicability check | 非北京详细规划不得默认应用 |
| 真彩色 | 2.1.5 | 检查 layer/entity true color 与 RGB | 不能只用 ACI color 代替真彩色 |
| 坐标基准 | 2.2.1 | CRS/coordinate-frame metadata check | DXF `$INSUNITS` 只表示单位，不足以证明坐标系正确 |
| 长度/面积单位精度 | 2.2.3 | display/measurement precision profile | 不应未经授权就把 canonical geometry 坐标四舍五入 |
| 几何拓扑 | 2.4.1 | 自交、相邻面重叠检查 | 这是几何 Validator，不是单纯 DXF audit |
| 实体类型/闭合 | 2.4.2 | line entity type + closed area boundary check | 需对 polyline/arc 的实际几何做验证 |
| CAD 图层命名 | 3.1.3 | 命名规则解析与图层映射 | 允许分类代码/中文说明部分省略；不要写成僵硬的固定五段非空 regex |
| 道路图层示例 | 附录 D，表 D.2 | exact layer name + RGB | 已定道路中线为 RGB(0,0,0)；已定道路红线为 RGB(255,0,0)；新定道路红线为 RGB(0,0,255) |
| 线宽选择 | 附录 D 表格备注 | discretionary rule / review | 部分要素线宽明确允许按图面效果自定，不能擅自补成标准固定值 |

## 3. 对 CAD-IR / Profile 架构的影响

1. Profile 不能只是“图层名→颜色→线宽”字典；它还需要适用范围、坐标基准、长度/面积精度、几何拓扑规则、实体类型、图层命名语法和图例/符号资源引用。
2. 每条规则都要带来源条款/表号、页面、适用条件、规范性质（强制/推荐/裁量/项目自定义）、机器检查方式和例外流程。
3. “标准未规定”与“本轮尚未知”必须是两个状态。对于显式允许按图面效果确定的线宽，应记录 `explicitly_discretionary`，而不是标成缺失或用通用值补齐。
4. 对象语义需要映射到目标 CAD layer key。例如 road centerline、existing road redline、proposed road redline 不是仅靠颜色猜出来的；它们应来自 canonical intent/object class 和 profile mapping。
5. Profile 需要保存 coordinate reference metadata sidecar 或合适的 CAD/BIM 元数据；DXF 的单位头变量不能证明其地理坐标基准。
6. 规范版本/辖区与设计院内部模板需要分层：标准定义基础要求，项目/设计院 Profile 可以补充层名、图框、字体、线宽和输出交付细节，但不能无记录地覆盖标准要求。

## 4. 本轮没有做什么

- 没有把 DB11/T 1948-2021 认定为用户项目的适用标准。
- 没有提取全部 80 页、所有图层、图例、符号和字体资源。
- 没有对其全部图层命名规则做完整 parser/validator。
- 没有声明国家/行业/地方标准或设计院合规已经通过。
- 没有把该标准规定的真彩色、坐标基准或图层命名直接写入所有项目的全局默认值。

## 5. 可复核来源

- 官方全文 PDF：<https://ghzrzyw.beijing.gov.cn/biaozhunguanli/bz/cxgh/202207/P020220711347172743065.pdf>
- 官方现行状态页：<https://std.samr.gov.cn/db/search/stdDBDetailed?id=D7B84EB1F2C445E9E05397BE0A0A6D15>
- 官方发布通知：<https://scjgj.beijing.gov.cn/zwxx/gs/dfbzgg/202112/t20211231_2579609.html>
