# examples/ —— 黄金范例（九步流水线全流程实物范本）

> 本目录是 ontology-forge 插件的实物范本区。范例是虚构域，不含任何客户数据；范例里的确认人、日期与追问过程均为示范用途的虚构记录。

## 一、这是什么

一份从资料准备到本体 DSL 的**完整实物**：同一个虚构业务域，九步流水线每一步该产出什么文件、每个文件长什么样、文件之间怎么互相引用，在这里都能看到成品。目前的范例只有一个域：

- [`supplier-recon/`](supplier-recon/README.md)——供应商月度对账与差异处理（本体建模流水线的范本）

它的五份原始资料取自评测用的合成域，逐字节一致；本体的结构与评测黄金答案等价，只做了到现行 DSL 规范的形态升级。

## 二、为什么随包分发

技能文档只能用文字描述"场景章程长什么样""业务事实卡片有哪些列"，现场起草时全凭各自发挥，产物形态容易漂移。范例给出三样文字给不了的东西：

1. **可对照的成品**——每个产物都有实物，起草前先看成品再动笔。
2. **可回查的追溯链**——DSL 里的每句业务陈述都能顺着出处回到资料原文（见域导读第五节）。
3. **可机器验证的标准答案**——范例的 DSL 与探索记录都能被脚本逐项校验，是插件回归的一份基准。

## 三、目录一览

```text
examples/
├── README.md                     # 本文件：范例总导读
└── supplier-recon/               # 范例域
    ├── README.md                 # 域导读：域背景 / 资料包 / 产物与步骤 / 追溯链示例
    ├── modeling-brief/           # 资料包（brief-intake 产出）
    │   ├── brief.yaml            #   资料包清单
    │   ├── intake-log.md         #   摄取日志
    │   ├── exploration.yaml      #   探索记录
    │   ├── A_schema/             #   A 类：建表语句 + 数据字典
    │   ├── B_scenarios/          #   B 类：决策清单 + 口径规则
    │   └── C_interviews/         #   C 类：访谈记录
    ├── charter.md                # 第 1 步：场景章程
    ├── fact-cards.md             # 第 2 步：业务事实卡片
    ├── design-proposal.md        # 第 3-4 步：设计提案（含确认记录）
    ├── business-inquiry.md       # 待确认事项汇总：业务问询单
    ├── model.yaml                # 第 5 步：本体 DSL（现行规范）
    └── topology.md               # 第 8 步：Mermaid 拓扑源（由 model.yaml 生成）
```

## 四、每个产物对应流水线哪一步

| 流水线步骤 | 范例文件 |
|---|---|
| 资料准备（brief-intake，先于九步流水线） | `supplier-recon/modeling-brief/` 下的 `brief.yaml`、`intake-log.md`、五份原始资料 |
| 资料准备中的缺口探索 | `supplier-recon/modeling-brief/exploration.yaml` |
| 第 1 步 场景圈定（确认点①） | `supplier-recon/charter.md` |
| 第 2 步 术语与候选抽取 | `supplier-recon/fact-cards.md` |
| 第 3 步 设计稿合成 | `supplier-recon/design-proposal.md` |
| 第 4 步 设计稿确认（硬关卡） | `supplier-recon/design-proposal.md` 头部的确认记录 |
| 第 5 步 DSL 生成 | `supplier-recon/model.yaml` |
| 第 6 步 硬校验（lint + 语义沙盘） | 对 `model.yaml` 执行 `scripts/lint_model.py` 与 `scripts/semantic_sandbox.py` |
| 第 7 步 CQ 回验 | 对 `model.yaml` 执行 `scripts/check_cq.py` |
| 第 8 步 交付初版候选本体 | `supplier-recon/topology.md`；图片与 `studio-model.yaml` 按需生成 |
| 第 9 步 导入平台后自检 / 资产沉淀回流 | 不入范例（交接包是生成物） |
| 待确认事项的汇总（设计稿之后、DSL 定稿之前） | `supplier-recon/business-inquiry.md` |

## 五、起草前先对照

- **按步骤找文件**：起草哪一步，先读上表里该步骤的范例文件，再读它对应的模板。
- **顺着引用读一遍**：从 `exploration.yaml` 的一个条目出发，看它怎样被 `fact-cards.md` 承接、怎样进入 `design-proposal.md`、最后怎样落进 `model.yaml`——未确认的建议停在哪一层，一目了然。
- **范例不是模板的替代品**：写法规范以技能的模板与指南为准；范例演示的是"照规范写出来是什么样"。两者不一致时以规范为准，并请报告范例的过期之处。
- **本范例的一处已知偏离**：等业务方的 14 条待确认事项没有写进 `model.yaml` 的 open_questions，而是停在 `design-proposal.md` 第 6.2 节与 `business-inquiry.md`。原因与影响见 `design-proposal.md` 第 6.2 节的「升格说明」。

## 六、范例受发布门禁保护

范例的 DSL 必须过 lint、能力问题回验与编译幂等，探索记录必须过门禁——任何一项不过，范例就不能再被当作对照物，等同于插件回归失败。改动范例后在仓库根执行：

```bash
S=plugins/ontology-forge/scripts
E=plugins/ontology-forge/examples/supplier-recon
python $S/check_exploration.py $E/modeling-brief/exploration.yaml    # 结论行须为「探索记录可交接建模」
python $S/lint_model.py $E/model.yaml                               # error 0 处、warning 0 处
python $S/check_cq.py $E/model.yaml                                 # 4 条能力问题全部可解析
python $S/semantic_sandbox.py $E/model.yaml --out-dir <临时目录>     # error 0 处
python $S/render_topology.py $E/model.yaml                          # topology.md 与 DSL 保持同步
python $S/compile_model.py $E/model.yaml --target both -o <临时目录>  # 连续编译两次，产物 sha256 一致
```

## 七、图片与生成物不入库

拓扑的 PNG / SVG、引擎注册 JSON、`studio-model.yaml`、沙盘产物、各类勾选页与交互式页面、交接包，都可以由源文件经脚本确定性重建，所以不入库——入库会出现两份真相并随时间漂移。需要图片时按需渲染：

```bash
python plugins/ontology-forge/scripts/render_topology.py plugins/ontology-forge/examples/supplier-recon/model.yaml --image both
```

本目录位于插件根下；是否进入某个平台的发布包，以该平台的打包清单为准（WorkBuddy 见 `scripts/pack_workbuddy.py` 的 `INCLUDE_ITEMS`）。

## 八、尚未覆盖的部分

- **行为层**：本域资料的触发下游均为平台内置动作（无参数与写入语义，见 model.yaml 的 AS-04 假设），故未造声明式动作——不硬造无据语义。**v0.4 行为层（基数 / 分支触发 / with 参数映射 / 声明式 steps 动作 / 函数型 / 准入挂载 / 多路径不猜）的实物范本见 `evals/ontology-modeling/case14-platform-format/fixture-v04.yaml`**（仓库工程资产，全键覆盖且由回归机器锁定）。带真实动作语义的新域范例长出来后再补第二个域。
- **更多的域**：目前只有一个域的范本，其他业务形态（增量建模、多文档大型资料包）尚无范例。
