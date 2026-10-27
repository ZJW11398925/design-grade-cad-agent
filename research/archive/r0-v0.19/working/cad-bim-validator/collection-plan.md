# BATCH-004 采集计划：CAD/BIM Compiler + Validator

**当前状态：** `bounded-paused / unclosed`。已完成第一轮官方来源定位、两个本地 DXF/Profile probes 与一个来源型标准摘录；A1 未执行，真实设计院 Profile 与独立 CAD/BIM round-trip 仍缺。

## 1. 唯一决策问题

能否用现有开源项目组合成一条可测试的输出闭环，把同一 canonical site model 分别编译为 DXF/IFC，并通过互相独立的几何、拓扑、项目 Profile、文件完整性、跨软件 round-trip 与视觉/打印检查？各工具的责任边界是什么？

## 2. Coverage 与下游

- 主要：`COV-16` DXF 输出、`COV-17` IFC 输出、`COV-18` 版本化规范/项目 Profile、`COV-19` Validator。
- 直接依赖：`COV-04` 几何/拓扑、`COV-10..13` 建筑 footprint/massing/placement、`COV-20` provenance/revision/lock。
- 本批不把任何标准自动选为用户项目的目标 Profile；但已引入 DB11/T 1948-2021 作为一个真实、官方来源的规划制图标准样例，验证 Profile 能否表达适用范围、条款、真彩色、坐标、单位精度、拓扑与图层映射。

## 3. 本批必须区分的验证层

1. IR/schema 完整性；
2. canonical geometry/topology；
3. 设计院/项目 Profile 校验；
4. DXF/IFC 文件结构完整性；
5. 同库写入—重读 round-trip；
6. 独立 CAD/BIM 软件打开/保存/回读；
7. 渲染/打印视觉 QA；
8. 领域/规范人工审查。

每层状态独立记录，不能用其中一层的通过覆盖其余层。

## 4. 首轮候选与角色

- `ezdxf`：DXF writer/reader、图层/样式结构和 audit；MIT；适合作为 DXF 编译器与自定义 Profile Validator 的数据访问基础。
- `LibreCAD`：独立 2D CAD reader/renderer/converter；GPLv2；适合做第三方打开/渲染/转换对照。DWG 支持取决于构建选项，不能默认所有发行版都具备。
- `libdxfrw`：DXF/DWG 读写库，GPL-2.0-or-later；官方 README 把 DWG 读写标为 experimental，并强调独立语义 oracle 仍需补充；暂不当作 DWG 可靠性保证。
- `IfcOpenShell`：IFC 创建/读写、几何与工具生态；LGPL 系列；当前环境没有安装，实际 round-trip 未运行。
- `IfcTester`：IDS 信息交付要求验证；不能替代几何、拓扑、placement 或日照/规划 Validator。
- `FreeCAD` / `Bonsai`：潜在独立 authoring/readback 环境；当前环境未安装，后续需 pin 版本和平台做实际兼容测试。

## 5. 本轮允许与禁止

允许：官方 README/API/source/license 检查；本地合成 DXF profile 编译/回读；自定义 Validator 错误注入；定义 CAD-IR 与 Validator matrix。

禁止：把合成 Profile 当作真实设计院规范；把 `ezdxf.audit()` 通过当作图纸专业合格；把 IfcTester IDS 通过当作几何/规划合规；在没有第三方软件 round-trip 时宣称跨软件兼容；把 DWG 支持描述成所有开源发行版都保证。

## 6. 当前实际结果

`LOCAL-CAD-003` 在 ezdxf 1.4.4 / Python 3.13.5 下通过 6 个断言：合成 Profile 合法、写入后重读属性一致、`audit()` 无未修复错误、未定义线型/实体属性覆盖可被自定义 Validator 捕获、无效 lineweight Profile 被拒绝。测试文件在 `samples/sample-design-office-profile-test.dxf`。

该 Profile 明确标注 `synthetic_fixture_only`，不包含任何真实国家/行业/地方/设计院标准值。另有 `LOCAL-CAD-004` 用 DB11/T 1948-2021 的少量官方条款与图层/RGB 做来源型 Profile 子集测试；可测子项通过，坐标基准因合成坐标而 blocked，不能宣称完整合规。

## 7. 来源型 Profile 样例与边界

- DB11/T 1948-2021 在官方状态页标为现行，适用范围是北京市国土空间详细规划。它只用于工程验证，不是用户项目默认标准。
- 已读取官方 PDF 的少量条款：真彩色、坐标基准、单位/精度、几何拓扑、线/面实体类型、CAD 图层命名和道路/用地图层示例。
- 该标准部分图层线宽允许按图面效果确定，因此 Profile 必须能表示明确裁量，而不是强制填一个默认值。
- 官方符号库/字体库链接可见，但本轮下载返回内部错误；资源内容/许可仍未知。

## 8. A1 阻断与来源边界

- `RUN-004-01` 搜索结果总量/分页完整性不可得，`truncation=unknown`；本批不声明来源路线完整。
- 本轮没有真实设计院模板；Profile 仅为合成测试值。
- 当前环境没有 LibreCAD、FreeCAD、IfcOpenShell，因此未执行独立应用 round-trip 和真实 IFC write/read。
- 用户提供的 Skill bundle 内未发现 `source-intelligence/README.md`；按 Skill 要求仅检查当前提供的 Skill 副本，不扫描无关用户目录。此处记为 unavailable，不代表用户设备上没有该库。

## 9. 退出条件

- 至少一个真实设计院/项目 Profile 能以来源、版本、适用范围和批准记录绑定；
- DXF 生成→重读→独立软件打开/渲染→回读差异可复现；
- IFC 信息要求验证与几何/placement/revision 验证明确分层；
- 失败能定位到具体对象、属性、层/representation 和来源 revision；
- A1 由独立 reviewer 复核真实获取边界和动作权限。

在上述条件未满足前，BATCH-004 保持 `in-progress / unclosed`，不冻结技术选型。


## 10. BATCH-004 bounded checkpoint（2026-10-26）

本轮已完成：

- `LOCAL-CAD-003`：ezdxf 同库 DXF 写入/重读、audit 与合成 Profile Validator，6 项断言通过。
- `LOCAL-CAD-004`：DB11/T 1948-2021 的少量官方条款与图层/RGB 子集被编码并测试；可测子项通过，故意重叠的面要素被检测，坐标参考因合成坐标而 blocked。
- 形成 CAD-IR、Profile rule contract 与 Validator matrix。

暂停原因：

1. `RUN-004-01` 与 `RUN-004-06` 搜索总量/分页状态 unknown，不能宣称来源路线完整。
2. 当前环境没有 LibreCAD/AutoCAD/FreeCAD/IfcOpenShell，无法执行独立软件 round-trip 或真实 IFC write/read。
3. 用户项目适用的国家/地方/设计院 Profile 尚未确定；DB11/T 1948-2021 仅是北京详细规划的来源样例。
4. 官方符号/字体库下载未成功。

因此本批在完成有价值的局部验证后有界暂停，不关闭、不冻结技术选型；主线转到 `COV-14..15` 环境分析与规划反馈，避免在输出工具局部阻断上继续消耗主线。
