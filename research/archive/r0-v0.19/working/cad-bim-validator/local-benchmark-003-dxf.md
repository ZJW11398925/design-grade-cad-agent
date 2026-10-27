# LOCAL-CAD-003：DXF 编译、回读与图纸 Profile 校验

**状态：** `local-dxf-roundtrip-probe / all-checks-passed`  
**运行日期：** 2026-10-26  
**运行环境：** Python 3.13.5、ezdxf 1.4.4。  
**产物：** [`samples/sample-design-office-profile-test.dxf`](samples/sample-design-office-profile-test.dxf)、[`local-benchmark-003-dxf.json`](local-benchmark-003-dxf.json)、[`cad-profile-test-v0.1.yaml`](cad-profile-test-v0.1.yaml)。

## 1. 实际运行结果

本轮实际使用 ezdxf 创建、保存、重新读取 DXF，并对重读文件运行 `audit()` 与自定义 Profile Validator。

| 检查 | 结果 | 能证明什么 |
|---|---|---|
| 合成 Profile 首次验证 | 通过 | 所需图层/样式/单位/实体约束与 fixture 一致 |
| DXF 写入后重新读取 | 通过 | 本轮测试范围内的图层属性、单位、布局、块、样式和实体计数一致 |
| `Drawing.audit()` 未修复错误数 | 0 | ezdxf 未报告未修复的 DXF 文档结构错误 |
| 自定义 Profile 对重读文件校验 | 通过 | 图层/线型/线宽策略、单位、布局、块、文字样式、标注样式满足本轮测试合同 |
| 人为植入的错误 | 被发现 | 未定义线型、实体覆盖 BYLAYER 线型/线宽策略被捕获 |
| 无效 Profile 线宽 | 被发现 | `27` 不是有效的标准 DXF lineweight 值，Profile 预检报错 |

本轮 6 项断言全部通过。**这只是合成 DXF profile 的本地测试，不是 AutoCAD/LibreCAD 的第三方 round-trip，也不证明真实设计院标准合规。**

## 2. 一个值得保留的实现细节

本地探针发现：在 ezdxf 1.4.4 中给实体设置 `lineweight=27` 后，读取到的值被规范化为 `30`。因此，单纯检查“写入后实体线宽是否属于有效值集合”不足以发现原始 Profile 中的无效输入；必须在编译前验证 Profile 本身，并比较写入后属性是否仍等于所请求的规范值。

这也说明“库帮忙修正”不等于“输出符合用户要求”。编译器需要同时保存：

- 用户/项目 Profile 中的请求值；
- DXF 实际写入值；
- 转换/规范化行为；
- 差异与错误结果。

## 3. DXF 文件结构与项目规格是两层 Validator

### 文件结构层

- 文件能被读取；
- `Drawing.audit()` 没有未修复错误；
- 引用的图层、线型、样式等表项可解析；
- 实体/块/布局结构没有丢失。

### 项目 Profile 层

- 必需图层是否齐全；
- 图层名、颜色、线型、线宽是否符合指定 Profile；
- 实体是否按项目要求继承 BYLAYER，而不是随意覆盖属性；
- 单位、标注样式、文字样式、块、布局和纸张要求是否满足；
- 对象 ID / 语义类别是否映射到正确图层与实体类型；
- 关键几何与拓扑是否仍与 CAD-IR 一致。

`ezdxf.audit()` 不能替代第二层，也不能替代上游建筑/道路几何 Validator。

## 4. Profile 的重要边界

[`cad-profile-test-v0.1.yaml`](cad-profile-test-v0.1.yaml) 里的层名、颜色、线宽、单位等全部是**人工合成的测试值**，只用来验证校验器能否执行。它不是任何中国国家标准、行业标准、地方标准或设计院内部标准。

正式使用时，Profile 必须绑定：`profile_id`、版本、法域/单位、图纸专业、阶段、来源条款/模板、批准人、例外规则。没有权威来源的值只能标为 project-configured / proposed，不得自动标为 mandatory-by-standard。

## 5. 当前未测试

- 未在 AutoCAD 中打开并保存；
- 未在 LibreCAD 中打开/渲染/保存；
- 未验证不同 DXF 版本的实体兼容性；
- 未验证中文字体在目标 CAD 环境中的替换和打印效果；
- 未验证 CTB/STB、打印样式、视口、布局比例与图框；
- 未将真实设计院模板导入 Profile；
- 未执行 IFC 写入/回读或第三方 BIM 软件 round-trip。

## 6. 来源

- [ezdxf README](https://github.com/mozman/ezdxf/blob/master/README.md)：DXF 读写、版本支持、CLI 和 MIT 许可。
- [Layers](https://ezdxf.readthedocs.io/en/stable/concepts/layers.html)：图层是对象组织与图层属性继承的核心机制。
- [Lineweights](https://ezdxf.readthedocs.io/en/stable/concepts/lineweights.html)：lineweight 以百分之一毫米表示，且只有指定值有效。
- [Common Graphical Attributes](https://ezdxf.readthedocs.io/en/stable/tutorials/common_graphical_attributes.html)：引用未定义的 linetype 可能导致 AutoCAD 无法打开文件，建议显式 audit。
- [Drawing.audit / validate](https://ezdxf.readthedocs.io/en/stable/drawing/drawing.html)：文件完整性审计与未修复错误返回。
