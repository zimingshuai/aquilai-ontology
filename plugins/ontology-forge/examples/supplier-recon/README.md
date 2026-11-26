# supplier-recon 黄金范例——供应商月度对账与差异处理

> 范例性质：虚构域示范（随插件分发的黄金范例）。五份原始资料是评测用的合成资料，不含任何客户数据；
>   范例里的确认人、日期、追问轮次均为示范用途的虚构记录，不对应任何真实确认。
> 本目录是本体建模九步流水线的实物范本：起草任何一步的产物前，先对照这里的同步骤文件。

## 一、域背景

财务共享中心每月按供应商对账。每张对账单记着供应商当期的发票金额与已对账金额，两者之差是对账差异金额；差异金额超过 2000 元且差异率超过 5% 的对账单自动转财务对账专员人工复核，只超一个的不用；供应商因合同纠纷或质检问题被冻结时，其所有对账单不再自动确认。查某供应商的交货要顺着「采购合同 → 交货记录」两级找。本体覆盖四类对象——供应商、采购合同、交货记录、对账单——三条计算口径与两条触发规则，数据分别来自 SRM、WMS、FIM 三个系统。以上每句都能在 `modeling-brief/` 的五份资料里找到原文。

## 二、资料包构成

| 路径 | 类别 | 内容 |
|---|---|---|
| `modeling-brief/brief.yaml` | 资料包清单 | 域、场景名、业务负责人、来源系统、资料清单（逐份路径 / 类别 / 备注）、约束摘录、已知冲突、探索记录路径 |
| `modeling-brief/intake-log.md` | 摄取日志 | 每份资料的来源标识 → 归位路径 → 判型依据；源摘要；资料完备度评分；缺口报告；冲突预检 |
| `modeling-brief/exploration.yaml` | 探索记录 | 对资料包的缺口探索：8 个维度、35 条结论（四态齐全）、7 行联动矩阵 |
| `modeling-brief/A_schema/supplier_ddl.sql` | A 类 结构化 schema | 四张表的建表语句 |
| `modeling-brief/A_schema/data_dictionary.md` | A 类 结构化 schema | 四表 26 个字段的数据字典 |
| `modeling-brief/B_scenarios/decisions.md` | B 类 业务场景 | 三项决策与四条能力问题 |
| `modeling-brief/B_scenarios/rules.md` | B 类 业务场景 | 三条计算口径与两条触发规则 |
| `modeling-brief/C_interviews/interview_finance.md` | C 类 访谈 | 财务共享中心访谈，5 组问答 |

五份原始资料与评测合成域 `evals/ontology-modeling/goldstandard/modeling-brief/` 逐字节一致，内容未改。

## 三、产物清单与对应的流水线步骤

| 产物 | 流水线步骤 | 对照的模板 / 校验脚本 | 一句话说明 |
|---|---|---|---|
| `modeling-brief/brief.yaml`、`intake-log.md` | 资料准备（brief-intake，先于九步流水线） | `skills/brief-intake/SKILL.md`、`references/intake-rules.md` | 资料包清单与摄取日志 |
| `modeling-brief/exploration.yaml` | 资料准备（缺口探索） | `references/exploration-guide.md`；`scripts/check_exploration.py` | 探索记录；门禁判定「可交接建模」：必问项 6 条全部已确认，提示清单 16 条 |
| `charter.md` | 第 1 步 场景圈定（确认点①） | `references/charter-template.md` | 场景章程：六项要素、必问收口清单、设计红线、四条能力问题 |
| `fact-cards.md` | 第 2 步 术语与候选抽取 | `references/fact-cards-template.md` | 业务事实卡片：4 个实体、3 条关系、5 条规则、3 组枚举、异常语义映射、探索记录承接 |
| `design-proposal.md` | 第 3 步 设计稿合成；第 4 步 设计稿确认（硬关卡） | `references/design-proposal-template.md` | 设计提案：确认记录在文件头；第 6.2 节逐条承接探索记录提示清单 |
| `business-inquiry.md` | 待确认事项汇总（设计稿之后、DSL 定稿之前） | `references/business-inquiry-template.md` | 业务问询单：14 条等业务方的待确认事项 |
| `model.yaml` | 第 5 步 DSL 生成 | `references/dsl-spec.md`、`references/modeling-guide.md` | 本体 DSL `0.1.0-draft.2`：4 个实体 / 26 个属性 / 3 条引用关系 / 5 条规则 / 4 条能力问题 / 2 条待确认问题 |
| （对 `model.yaml` 执行） | 第 6 步 硬校验 | `scripts/lint_model.py`、`scripts/semantic_sandbox.py` | 沙盘产物按需落临时目录，不入库 |
| （对 `model.yaml` 执行） | 第 7 步 CQ 回验 | `scripts/check_cq.py` | 四条能力问题全部可解析 |
| `topology.md` | 第 8 步 交付初版候选本体 | `scripts/render_topology.py` | Mermaid 拓扑源，由 `model.yaml` 生成；图片与 `studio-model.yaml` 按需生成，不入库 |
| （不在范例内） | 第 9 步 导入平台后自检 / 资产沉淀回流 | `scripts/gen_handoff.py` 等 | 交接包是生成物，不入范例 |

## 四、怎么用它对照

1. **按步骤对照**：起草哪一步，就先读上表里该步骤的范例文件，再读它对照的模板。
2. **先感受终态**：读 `exploration.yaml` 与 `charter.md`，看"必问项全部收口、提示清单挂着待确认"的可交接终态长什么样——必问项来自资料明示，落盘即已确认；资料没说清的事一律挂着，不带进建模。
3. **对照 DSL 时看形态**：`model.yaml` 相对旧形态的升级点有八处——文件头治理注释三行、links 的显式形态（语义名 + 业务定义）、属性 `source` 锚点、枚举双写、衍生字段以「衍生：」重述并标 `derived: true`、规则级 `source`、待确认问题的七态 schema、`assumptions`。
4. **留意未决点的去向**：等引擎的 2 条在 `model.yaml` 的 open_questions；等业务方的 14 条在 `design-proposal.md` 第 6.2 节与 `business-inquiry.md`，没有写进 DSL——本范例因此与流程条款有一处偏离，说明见 `design-proposal.md` 第 6.2 节的「升格说明」。
5. **改了就重跑**：任何对 `model.yaml` 或 `exploration.yaml` 的改动，都要重跑上一级目录 `examples/README.md` 第六节列出的验收命令。

## 五、追溯链示例

### 5.1 一条已确认的业务陈述：对账差异金额

| 环节 | 位置 | 内容 |
|---|---|---|
| 资料 | `modeling-brief/B_scenarios/rules.md`「对账差异金额」一节 | 口径：发票金额 − 已对账金额；负值 = 多对账，保留负值不取绝对值；无已对账金额时按 0 处理 |
| 探索记录 | `exploration.yaml` 的 X-004（D2 业务对象、属性与关系）、X-008 | X-004：术语「对账差异金额」属必问清单第 5 条，资料明示，落盘即已确认；X-008：空值含义（已对账金额为空按 0） |
| 事实卡片 | `fact-cards.md` 术语表、3.1 节 RU01、第 7 节承接表 | 术语「对账差异金额」「多对账」；公式 `invoice_amount - COALESCE(reconciled_amount, 0)`；承接表登记 X-004 → RU01 |
| 设计稿 | `design-proposal.md` 第四节 RU01 与异常覆盖核对 | 口径的自然语言表述；「负值保留」「空值按 0」两条异常语义各落到 RU01 |
| DSL | `model.yaml` 的规则「对账差异金额」与属性 `ReconciliationStatement.recon_diff_amount` | 规则 `logic` 与 `source`；属性标 `derived: true`，description 以「衍生：」重述口径 |
| 编译产物 | `compile_model.py` 的 `rules.json`、`objects.json`（按需生成） | `logic` 与 description 进入引擎产物；`derived`、`source` 按剥离清单不进产物——所以口径必须在 description 里重述 |
| 拓扑 | `topology.md` | 对账单类的 note：「【衍生】recon_diff_amount: …」 |

### 5.2 一条没说清的事：取整方式

| 环节 | 位置 | 内容 |
|---|---|---|
| 资料 | `modeling-brief/B_scenarios/rules.md` 三节口径 | 只给算法，没有给保留位数与取整方式 |
| 探索记录 | `exploration.yaml` 的 X-029（D6 计算口径与校验） | AI 建议「金额保留两位小数、差异率保留四位小数」；追问两轮仍无明确答复，状态 pending |
| 事实卡片 | `fact-cards.md` 3.1 节表下说明、第 7 节承接表 | 公式不体现取整；承接表登记 X-029 为「待确认：AI 建议，未确认」 |
| 设计稿 | `design-proposal.md` 第 6.2 节 | 逐条列出并标『AI 建议，未确认』 |
| 问询单 | `business-inquiry.md` Q12 | 六要素齐全，业务方可直接回「按建议」 |
| DSL | `model.yaml` | **不出现**——未确认的建议不写成事实 |

两条链路合起来说明同一件事：进了 DSL 的每句业务陈述都能顺着编号回到资料原文；资料没说清的，停在设计稿与问询单，等确认后再补。

## 六、出处锚点记法

范例里所有出处都写成 `<资料路径>#<位置>`，路径相对 `modeling-brief/` 目录：

| 资料 | 锚点写法 | 示例 |
|---|---|---|
| `data_dictionary.md` | 表名.字段名，定位到字典的一行 | `A_schema/data_dictionary.md#supplier.frozen_flag` |
| `supplier_ddl.sql` | 表名.字段名——先找到 `CREATE TABLE` 段，再找以字段名开头的行；引用整张表时只写表名；引用头注释时用其原文片段 | `A_schema/supplier_ddl.sql#supplier.frozen_flag` |
| `rules.md` | 章节标题的主干 | `B_scenarios/rules.md#对账差异率` |
| `decisions.md` | 章节标题的前缀 | `B_scenarios/decisions.md#决策 1` |
| `interview_finance.md` | 问句原文 | `C_interviews/interview_finance.md#Q：冻结是什么意思？` |
| `brief.yaml` | 键名 | `brief.yaml#notes` |

探索记录的 `source` 字段在此基础上加类型前缀：资料写 `资料：<路径>#<位置>`，AI 建议写 `AI 建议 <日期>`（AI 建议没有资料出处，这是有意的区分）。

## 七、尚未覆盖的部分

- **行为层待补**：动作 / 状态机 / 函数的范例待 DSL 升级后补充；当前范例覆盖对象层与规则层。对账单与合同的状态流转、人工复核的写入方式、联动失败语义在本域资料里都没有说明，它们以"待确认"的形态留在探索记录、设计稿与问询单里。
- **生成物不入范例**：骨架 DSL、交互式拓扑、CQ 勾选页、探索勾选页、沙盘产物、引擎注册 JSON、`studio-model.yaml`、拓扑图片、交接包，都由源文件或脚本按需生成。
- **未示范的形态**：不适用维度（本域 8 个维度都有资料涉及）；D 类参考资料与云端拉取的原始层（本域没有这两类资料）；必问项以否决收口（本域必问项全部由资料明示）。
