# supplier-recon 本体设计提案（design-proposal）

> 版本：0.1.0-draft.2 ｜ 呈审人：FDE（agent）｜ 待确认人：示范确认人（虚构域示范记录）
> 确认记录（**虚构域示范记录**——确认人、日期与审阅意见均为示范用途，不对应任何真实确认；真实项目每返改一次在此追加一行）：
> ｜ 2026-11-25 17:30:20 ｜ 示范审阅人 ｜ 第 1 轮意见：两条指向供应商的连线在图上标签相同，分不清哪条是「合同签约」、哪条是「对账」，要求说清各是什么关系 → 回改：关系语义名分别定为「签约供应商」「对账供应商」（取数据字典的业务术语）
> ｜ 2026-11-25 17:31:20 ｜ 示范确认人 ｜ 第 2 轮：对象层、规则与联动层分两批逐表呈审，确认通过，无进一步修改意见 → 进入第 5 步 DSL 起草
>
> 范例性质：虚构域示范记录（随插件分发的黄金范例）。章节对照 `skills/ontology-modeling/references/design-proposal-template.md`。
> 编号规则：实体 E01..E04 / 关系 R01..R03 / 规则 RU01..RU05；能力问题沿用 `charter.md` 的 cq-NNN；`X-NNN` 是探索记录的条目编号。
> 出处记法：`<资料路径>#<位置>` 的路径相对资料包目录。

## 一、场景回顾

财务共享中心每月按供应商对账，算清每张对账单的差异；差异金额超过 2000 元且差异率超过 5% 的对账单自动转人工复核；供应商被冻结时其所有对账单不再自动确认。本体的范围是四类对象——供应商、采购合同、交货记录、对账单——与三条计算口径、两条触发规则；发票明细管理与付款执行不在范围内。场景章程已在确认点①定稿，能力问题四条：

- cq-001 哪些对账单的差异金额超阈值且差异率超阈值（需要复核）？
- cq-002 哪些供应商处于冻结状态？
- cq-003 某供应商本期发票金额、已对账金额、差异金额分别是多少？
- cq-004 某供应商名下所有交货记录的金额合计是多少？

## 二、实体设计（共 4 个）

| # | 实体（英文） | 展示名 | 主键 | 关键字段（含类型） | 一句话职责 | 来源 |
|---|---|---|---|---|---|---|
| E01 | Supplier | 供应商 | supplier_code（STRING） | 供应商名称 STRING / 结算方式 STRING（3 值）/ 冻结标记 BOOLEAN / 供应商交货总额 DECIMAL（衍生，元） | SRM 系统管理的供应商主数据，含结算方式与冻结状态 | `A_schema/data_dictionary.md#supplier`；X-003 |
| E02 | PurchaseContract | 采购合同 | contract_nr（STRING） | 合同总金额 DECIMAL（元，含税）/ 签约日期 DATE / 合同状态 STRING（3 值）/ 签约供应商 supplier_code STRING | 与供应商签署的采购合同，记录金额与履约状态 | `A_schema/data_dictionary.md#purchase_contract`；X-003 |
| E03 | DeliveryRecord | 交货记录 | delivery_nr（STRING） | 交货数量 DOUBLE（件）/ 交货金额 DECIMAL（元，含税）/ 交货日期 DATE / 关联合同 contract_nr STRING | WMS 记录的每次交货明细，挂在采购合同下 | `A_schema/data_dictionary.md#delivery_record`；X-003 |
| E04 | ReconciliationStatement | 对账单 | recon_nr（STRING） | 对账期间 STRING（yyyy-MM）/ 发票金额 DECIMAL（元）/ 已对账金额 DECIMAL（元）/ 对账状态 STRING（3 值）/ 对账差异金额 DECIMAL（衍生，元） | FIM 财务系统按供应商按月生成的对账单，记录发票与对账金额 | `A_schema/data_dictionary.md#reconciliation_statement`；X-003 |

阶段⑤补全字段（关键字段栏装不下的）：E01 创建时间 TIMESTAMP、更新时间 TIMESTAMP；E04 创建时间 TIMESTAMP、对账供应商 supplier_code STRING、对账差异率 DECIMAL（衍生，比率）。

## 三、关系设计（共 3 条）——说清"是什么关系"

| # | 从 → 到 | 关系语义名 | 基数 | 业务含义（一句话） | 来源 |
|---|---|---|---|---|---|
| R01 | 采购合同 → 供应商 | 签约供应商 | n:1 | 每份采购合同签约于一个供应商；一个供应商可以有多份合同 | `A_schema/data_dictionary.md#purchase_contract.supplier_code`（外键→supplier）；X-016 |
| R02 | 交货记录 → 采购合同 | 关联合同 | n:1 | 每条交货记录挂在一份采购合同下；一份合同可以有多条交货记录 | `A_schema/data_dictionary.md#delivery_record.contract_nr`（外键→purchase_contract）；`C_interviews/interview_finance.md#Q：合同和交货的关系？`；X-016 |
| R03 | 对账单 → 供应商 | 对账供应商 | n:1 | 每张对账单对应一个供应商，按供应商加月份生成；一个供应商每月一张 | `A_schema/data_dictionary.md#reconciliation_statement.supplier_code`（外键→supplier）；`C_interviews/interview_finance.md#Q：对账单和供应商的关系是怎么挂的？`；X-016 |

三条关系的引用字段在建表语句里均不允许为空，故基数都是 n:1、没有可空引用（X-010）。关系语义名取自数据字典的业务术语列；两条指向供应商的关系分别命名为「签约供应商」「对账供应商」，拓扑连线标签与平台关系名随之可区分。

## 四、规则设计（共 5 条）

| # | 类型 | 名称 | 口径（自然语言 / 公式） | 挂载实体 | 来源 |
|---|---|---|---|---|---|
| RU01 | 衍生 | 对账差异金额 | 发票金额 − 已对账金额；已对账金额为空按 0；负值表示多对账，保留负值、不取绝对值 | E04 对账单 | `B_scenarios/rules.md#对账差异金额`；X-004、X-008 |
| RU02 | 衍生 | 对账差异率 | 对账差异金额 ÷ 发票金额，比率（非百分数）；发票金额为 0 或缺失时记 9999 | E04 对账单 | `B_scenarios/rules.md#对账差异率`；X-026 |
| RU03 | 衍生 | 供应商交货总额 | 该供应商所有合同下全部交货记录的交货金额合计（元，含税） | E01 供应商 | `B_scenarios/rules.md#供应商交货总额`；X-027 |
| RU04 | 触发 | 对账差异复核触发 | 差异金额 > 2000 且差异率 > 0.05（同时满足，只超一个不触发）→ 把对账单标记为「需复核」（系统动作 mark_recon_review） | E04 对账单 | `B_scenarios/rules.md#复核触发`；`B_scenarios/decisions.md#决策 1`；X-022 |
| RU05 | 触发 | 供应商冻结提醒 | 冻结标记为真 → 触发供应商冻结提醒（系统动作 mark_supplier_frozen），其所有对账单不再自动推进 | E01 供应商（影响 E04 对账单） | `B_scenarios/rules.md#冻结拦截`；`B_scenarios/decisions.md#决策 2`；X-023 |

**异常处理段覆盖核对**（逐条列出五份资料里的异常 / 红线 / 限制语义 → 对应规则编号或"不建规则的理由"；与 `fact-cards.md` 第 4 节同一份清单）：

| 异常处理 / 红线 / 限制语义（出处） | 对应规则 | 或"不建规则的理由" |
|---|---|---|
| 负值 = 多对账，保留负值不取绝对值（`B_scenarios/rules.md#对账差异金额`） | RU01 | — |
| 无已对账金额时按 0 处理（`B_scenarios/rules.md#对账差异金额`） | RU01 | — |
| 发票金额为 0 或缺失时差异率记 9999（`B_scenarios/rules.md#对账差异率`） | RU02 | 引擎能否在分母为 0 时让兜底生效待验证 → OQ-01 |
| 两个都超线才复核，只超一个不用（`C_interviews/interview_finance.md#Q：对账差异怎么算、什么情况要人看？`）；阈值用严格大于（`B_scenarios/rules.md#复核触发`），恰好等于 2000 或 0.05 不触发 | RU04 | — |
| 冻结中的供应商，其所有对账单不应继续推进（`B_scenarios/decisions.md#决策 2`）；系统要给个提醒（`C_interviews/interview_finance.md#Q：冻结是什么意思？`） | RU05 | 「不自动推进」如何拦截资料未定义，不另建拦截规则 |
| 冻结 = 停止对账与付款（`A_schema/data_dictionary.md#supplier.frozen_flag`） | RU05 | 「停止付款」不在本域范围（X-002），不建规则 |
| 三系统各自建表、外键未建约束（`A_schema/supplier_ddl.sql#三系统各自建表，主键均为业务编码`） | — | 数据现状说明，不是业务规则；引用关系按数据字典建（R01-R03） |
| 合同状态：终止 = 到期或提前终止；作废 = 签署后取消（`A_schema/data_dictionary.md#purchase_contract.status`） | — | 合同终止或作废后交货记录与对账单如何处理资料未说明 → 待确认 X-025 |
| 对账状态 disputed = 存在争议；KPI「争议单处理时长」 | — | 争议如何产生、如何处置资料未描述 → 待确认 X-017；状态变更时间资料未给 → 待确认 X-011 |
| 一个供应商每月一张（`C_interviews/interview_finance.md#Q：对账单和供应商的关系是怎么挂的？`），建表语句无「供应商加对账期间」唯一限制（`A_schema/supplier_ddl.sql#reconciliation_statement`） | — | 只是访谈中的口头约定，是否作为硬约束未明确 → 待确认 X-035 |
| 冻结标记缺省为 0（`A_schema/supplier_ddl.sql#supplier.frozen_flag`） | — | 缺省值属字段定义；含义写在字段说明里（0 = 正常），不建规则 |
| 三项 KPI：月度复核单量、争议单处理时长、冻结供应商占比（`B_scenarios/decisions.md#决策 1`、`B_scenarios/decisions.md#决策 2`） | — | 资料只给指标名、未给计算口径，且口径规则一节未列 → 不建规则 |

## 五、CQ 覆盖预映射

| CQ | 回答它需要的实体 / 关系 / 规则 |
|---|---|
| cq-001 | E04 + RU01 + RU02（差异金额、差异率两个字段）+ RU04（复核线的判定） |
| cq-002 | E01（冻结标记字段）+ RU05 |
| cq-003 | E04 + R03（按供应商定位对账单，「本期」即对账期间字段）+ RU01 |
| cq-004 | E01 + RU03 + R01 + R02（顺着合同到交货两级合计） |

四条均由资料提出的原始问题构成，无 AI 建议成分；变化响应型问题的补充建议见下节 X-034（未确认，不计入覆盖）。

## 六、待确认事项（open_questions）、口径冲突（conflicts）与生成假设（assumptions）

### 6.1 open_questions（进入 DSL 的待确认问题，共 2 条，均等引擎侧验证）

| 编号 | 主题 | 问题 | 缺在哪份材料 | 建议 | 对应探索条目 |
|---|---|---|---|---|---|
| OQ-01 | 差异率除零兜底语义 | 口径要求发票金额为 0 时差异率记 9999；表达式按引擎惯例写成「差异金额 ÷ 发票金额，除不出结果时取 9999」，发票金额为 0 时这个兜底会不会生效，取决于引擎的除法语义 | `B_scenarios/rules.md#对账差异率`（只给口径，未给实现层） | 在引擎沙箱用一张发票金额为 0 的对账单实测；兜底不生效时由建模侧另写兜底方案 | X-030 |
| OQ-02 | 两级合计的方言支持性 | 供应商交货总额要从供应商出发、经采购合同再到交货记录做合计，是两级查找；这种两级合计能否被引擎正确执行 | `B_scenarios/rules.md#供应商交货总额`（只给口径，未给实现路径） | 在引擎沙箱实测；引擎不支持时改为逐级计算——先在每份合同上算出交货合计，再加到供应商上 | X-031 |

两条验证通过前，DSL 保持 draft 状态，不注册引擎。

### 6.2 探索记录提示清单承接（共 16 条，均标『AI 建议，未确认』）

来源：`modeling-brief/exploration.yaml` 的提示清单（`check_exploration.py` 输出的非必问未确认条目）。这些条目**没有写成已确认候选**，下表逐条承接；等业务方的 14 条已汇总成 `business-inquiry.md`，等引擎的 2 条已对应 6.1 的 OQ。

| 编号 | 待确认事项 | AI 建议（未确认） | 备选 | 缺在哪份材料 | 去向 |
|---|---|---|---|---|---|
| X-011 | 对账单要不要记最近一次状态变化的时间 | 增加「状态变更时间」，由系统在状态变化时自动记录 | 不增加；或分别记录进入争议、争议结束两个时间 | 五份资料均无此字段；动机是 `B_scenarios/decisions.md#决策 1` 的 KPI「争议单处理时长」 | 等业务方 |
| X-012 | 供应商要不要记对账联系人 | 增加「对账联系人」 | 不增加；或增加联系人与联系方式两项 | 五份资料均无此字段 | 等业务方 |
| X-013 | 三个计算字段按什么类型存 | 对账差异金额、供应商交货总额按金额型，对账差异率按数值型 | 三个都按金额型 | `B_scenarios/rules.md` 三节口径均未给类型 | 等业务方（DSL 侧先按惯例登记为假设 AS-01，批复后转正） |
| X-014 | 发票金额、已对账金额是含税还是不含税 | 按含税金额登记，与交货金额、合同总金额口径一致 | 按不含税登记；或含税与不含税都登记 | `A_schema/data_dictionary.md#reconciliation_statement.invoice_amount` 与 `A_schema/data_dictionary.md#reconciliation_statement.reconciled_amount` 未写明 | 等业务方 |
| X-015 | 「需复核」标记记在对账单的哪个信息项上 | 对账单增加「需复核标记」（是 / 否），差异超线时由系统置为「是」 | 不加信息项，标记由系统动作自行处理 | `B_scenarios/rules.md#复核触发` 只说由系统动作标记；`A_schema/data_dictionary.md#reconciliation_statement` 无此字段 | 等业务方与平台侧 |
| X-017 | 对账单三种状态如何流转 | 复核线以内且双方核对一致 → 「双方确认」；任一方提异议 → 「有争议」；「双方确认」为终态 | 争议解决后可直接转「双方确认」；或全部人工操作 | `A_schema/data_dictionary.md#reconciliation_statement.status` 只给取值，无流程件 | 等业务方 |
| X-018 | 合同三种状态在什么条件下变化 | 到期或协商提前结束 → 「终止」；签署后取消 → 「作废」；二者为终态 | 「终止」可恢复为「生效」；或只保留「生效」 | `A_schema/data_dictionary.md#purchase_contract.status` 只给含义 | 等业务方 |
| X-021 | 人工复核的结论如何落库 | 落为对账单的状态变化与已对账金额的调整；默认沙箱试跑并弹确认卡 | 只写复核意见不改对账单；或直接改生产数据不弹确认卡 | `B_scenarios/decisions.md#决策 1` 只写决策人与规则 | 等业务方 |
| X-024 | 冻结提醒失败时冻结是否仍然成立 | 冻结照常成立、对账单照常拦截；提醒失败记录并转人工跟进 | 提醒失败则冻结作废；或自动重试若干次 | `B_scenarios/rules.md#冻结拦截` 只要求给提醒 | 等业务方 |
| X-025 | 合同终止或作废后，交货记录与对账单怎么处理 | 都不自动改动，合同终止或作废只作为提示信息 | 自动剔除其下交货金额；或自动冻结相关对账单 | `A_schema/data_dictionary.md#purchase_contract.status` 只给含义 | 等业务方 |
| X-028 | 交货金额合计算全部历史还是只算本期 | 保留全量合计的现有口径；确需按月核对时再补一个本期口径 | 只建本期口径；或只建全量口径 | `B_scenarios/decisions.md#决策 3` 标题带「本期」，`B_scenarios/rules.md#供应商交货总额` 未限定期间 | 等业务方 |
| X-029 | 金额与差异率保留几位小数、怎么取整 | 金额保留两位小数、差异率保留四位小数，四舍五入 | 差异率只保留两位；或不取整 | `B_scenarios/rules.md` 三节口径均未给 | 等业务方 |
| X-034 | 要不要补充三个「发生变化以后系统怎么做」类的问题 | 补充：供应商被冻结时对账单会怎样；差异越过复核线时系统做什么；合同终止或作废时交货合计与对账要不要跟着变 | 只保留已有四条；或挑部分采纳 | `B_scenarios/decisions.md#能力问题` 四条均为现状查询 | 等业务方 |
| X-035 | 同一供应商同月会不会有多张对账单 | 「一个供应商每月一张」当作业务约定，不加唯一限制；同月多单时逐张计算差异再加总 | 增加「供应商加对账期间」唯一限制；或以最新一张为准 | `C_interviews/interview_finance.md#Q：对账单和供应商的关系是怎么挂的？` 是口头约定，`A_schema/supplier_ddl.sql#reconciliation_statement` 无唯一约束 | 等业务方 |
| X-030 | 发票金额为 0 时引擎算出的差异率是不是 9999 | 在引擎沙箱实测；兜底不生效时另写兜底方案 | 等引擎确认后再定表达式 | 引擎方言能力边界 | 已对应 OQ-01 |
| X-031 | 从供应商出发的两级合计引擎能不能算对 | 在引擎沙箱实测；不支持时改为逐级计算 | 直接改为逐级计算 | 引擎方言能力边界 | 已对应 OQ-02 |

**升格说明（本范例与流程条款的一处偏离，须知悉）**：按 `ontology-modeling` 第 3 步的条款，提示清单里的条目应同时升格为 DSL 的 open_questions（等业务方的标 `pending-business`）。本范例的 DSL `open_questions` 与评测黄金答案保持等价（只有两条等引擎类），所以上表等业务方的 14 条停留在本节与 `business-inquiry.md`，**未写入 `model.yaml` 的 open_questions**。真实项目请按条款升格；本范例的 DSL 在这 14 条清零之前同样不得定稿。

### 6.3 conflicts（口径冲突）

逐术语交叉比对五份资料（阈值、差异算法、复核条件、状态清单、关系挂法），**没有发现同一术语有两种定义的口径冲突**；DSL 的 `conflicts` 记为显式空集合。

交叉比对时发现一处措辞出入，如实记录：`B_scenarios/rules.md#供应商交货总额` 定义交货总额为「所有合同下**全部**交货记录的交货金额合计」，未限定期间；`B_scenarios/decisions.md#决策 3` 的标题问的是「某供应商**本期**实际交付了多少金额」，而同一决策的「依据信息」一栏写的也是「所有合同下的交货记录金额合计」。两处对「交货金额合计」的定义一致，出入只在标题里的「本期」是否意味着要按对账期间过滤，故未登记为冲突，作为范围待确认条目 X-028 列入 6.2。

### 6.4 assumptions（生成假设，可抽查的推断记录，与 `model.yaml` 的 assumptions 同一清单）

| 编号 | 假设 | 推断依据 |
|---|---|---|
| AS-01 | 三个衍生字段的类型系推断：对账差异金额、供应商交货总额按 DECIMAL，对账差异率按 DECIMAL | `B_scenarios/rules.md` 三节口径只给算法、未给类型；两个金额分别对齐发票金额与交货金额的 DECIMAL（`A_schema/data_dictionary.md#reconciliation_statement.invoice_amount`、`A_schema/data_dictionary.md#delivery_record.delivery_amount`） |
| AS-02 | 冻结标记按数据字典建模为 BOOLEAN | 数据字典为 BOOLEAN，建表语句为 TINYINT(1)（1 = 冻结、0 = 正常），两者语义一致（`A_schema/data_dictionary.md#supplier.frozen_flag`、`A_schema/supplier_ddl.sql#supplier.frozen_flag`） |
| AS-03 | 三条引用关系的引用字段与目标主键同名，按数据字典的外键指向显式声明 | `A_schema/data_dictionary.md#purchase_contract.supplier_code` 等三处外键指向 |
| AS-04 | 两条触发规则的下游动作 mark_recon_review、mark_supplier_frozen 取自口径规则原文，不在 actions 段声明 | `B_scenarios/rules.md#复核触发`、`B_scenarios/rules.md#冻结拦截` 写明「由平台内置处理」，资料未给参数与写入语义 |
| AS-05 | 三个引用字段均按不允许为空处理，不登记可空引用 | `A_schema/supplier_ddl.sql#purchase_contract.supplier_code`、`A_schema/supplier_ddl.sql#delivery_record.contract_nr`、`A_schema/supplier_ddl.sql#reconciliation_statement.supplier_code` 三处均为 NOT NULL |

## 七、骨架拓扑

真实流程在本步用骨架 DSL（实体 + 引用关系 + 主键与名称字段）经 `python scripts/render_topology.py <model.skeleton.yaml> --interactive` 产出交互式 HTML 呈审，确认后再补全为完整 DSL。
本范例不单独入库骨架 DSL 与图片：`topology.md` 是由完整 DSL 渲染的 Mermaid 拓扑源（实体、连线与关系语义名标签与本节第二、三节逐项对应），需要图片时按需渲染、不入库：

```bash
python plugins/ontology-forge/scripts/render_topology.py plugins/ontology-forge/examples/supplier-recon/model.yaml --image both
```
