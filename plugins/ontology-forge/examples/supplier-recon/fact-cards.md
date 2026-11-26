# supplier-recon 业务事实卡片（fact-cards）

> 产出步骤：ontology-modeling 九步流水线第 2 步 ｜ 状态：已随设计稿确认（虚构域示范记录：2026-11-25 17:31:20，示范确认人——确认点②通过时一并确认）
> 抽取纪律：同一术语至少两源交叉（A 类字典或建表语句 + B 类口径规则或 C 类访谈）；单源高置信候选的状态最高为「候选」；口径出入写入第 6 节。承接自探索记录且已确认的条目不受「单源最高为候选」限制——确认来自资料明示，出处写条目编号即可追溯
> 状态标签：已确认 / 候选 / 待确认 / 冲突（本资料包三类来源齐备，候选均达到两源以上交叉，故候选行全部为「已确认」；「待确认」只出现在第 7 节的未确认 AI 建议上）
> 出处记法：`<资料路径>#<位置>` 的路径相对资料包目录；`X-NNN` 是探索记录 `modeling-brief/exploration.yaml` 的条目编号
> 探索记录承接：已承接，见第 7 节——未确认的 AI 建议不写成已确认候选；已否决的条目不进卡片
>
> 范例性质：虚构域示范记录（随插件分发的黄金范例）。章节与列对照 `skills/ontology-modeling/references/fact-cards-template.md`。

## 0. 术语表

原样保留业务术语，不做同义改写；「对齐判定」是新术语登记的唯一载体，是否登记进 `seeds/glossary.md` 由人审统一裁定。本域从零新建，术语与命名全部取自资料原文。

| 术语 | 出处 | 含义 | 对齐判定 |
|---|---|---|---|
| 供应商编码 | `A_schema/data_dictionary.md#supplier.supplier_code` | SRM 系统供应商唯一编码 | 新术语 |
| 对账单 | `C_interviews/interview_finance.md#Q：对账单和供应商的关系是怎么挂的？` | 每张对账单按「供应商 + 月份」生成，一个供应商每月一张；对账单上直接记着供应商编码 | 新术语 |
| 对账期间 | `A_schema/data_dictionary.md#reconciliation_statement.recon_period` | 对账月份，格式 yyyy-MM | 新术语 |
| 发票金额 | `A_schema/data_dictionary.md#reconciliation_statement.invoice_amount` | 供应商本期开具发票总额（元） | 新术语 |
| 已对账金额 | `A_schema/data_dictionary.md#reconciliation_statement.reconciled_amount` | 双方核对一致确认的金额（元） | 新术语 |
| 对账差异金额 | `B_scenarios/rules.md#对账差异金额` | 发票金额 − 已对账金额（元） | 新术语 |
| 多对账 | `B_scenarios/rules.md#对账差异金额` | 差异金额为负值的情况（少见），保留负值不取绝对值 | 新术语 |
| 对账差异率 | `B_scenarios/rules.md#对账差异率` | 差异金额 ÷ 发票金额（比率，非百分数） | 新术语 |
| 供应商交货总额 | `B_scenarios/rules.md#供应商交货总额` | 该供应商所有合同下全部交货记录的交货金额合计（元，含税） | 新术语 |
| 需复核 / 人工复核 | `B_scenarios/rules.md#复核触发`；`B_scenarios/decisions.md#决策 1` | 差异金额超 2000 元且差异率超 5% 的对账单被标记为「需复核」，由财务对账专员人工复核 | 新术语 |
| 冻结 | `A_schema/data_dictionary.md#supplier.frozen_flag` | 合同纠纷或质检问题时冻结，停止对账与付款；由采购侧在 SRM 系统操作 | 新术语 |
| 结算方式 | `A_schema/data_dictionary.md#supplier.settlement_type` | 与供应商约定的付款周期 | 新术语 |
| 合同状态 | `A_schema/data_dictionary.md#purchase_contract.status` | 生效 = 正常履约；终止 = 到期或提前终止；作废 = 签署后取消 | 新术语 |
| 对账状态 | `A_schema/data_dictionary.md#reconciliation_statement.status` | open = 对账中；confirmed = 双方确认；disputed = 存在争议 | 新术语 |
| mark_recon_review | `B_scenarios/rules.md#复核触发` | 把对账单标记为「需复核」的系统动作，由平台内置处理 | 新术语 |
| block_recon_for_frozen_supplier / mark_supplier_frozen | `B_scenarios/rules.md#冻结拦截` | 前者是「冻结拦截」这条口径规则的代号，后者是它触发的系统动作名（由平台内置处理）；两者不是一回事 | 新术语 |

## 1. 实体候选

### 1.1 主数据

| # | 实体（英文） | 展示名 | 一句话职责 | 属性要点 | 出处 | 交叉 | 置信 / 状态 |
|---|---|---|---|---|---|---|---|
| E01 | Supplier | 供应商 | SRM 系统管理的供应商主数据，含结算方式与冻结状态 | supplier_code（主键）/ supplier_name / settlement_type（枚举 3 值）/ frozen_flag（BOOLEAN，1 = 冻结、0 = 正常）/ create_time / update_time / total_delivery_amount（衍生，DECIMAL，元） | X-003、X-005、X-009；`A_schema/data_dictionary.md#supplier`；`A_schema/supplier_ddl.sql#supplier` | A + C | 高 / 已确认 |

### 1.2 交易与对账单据

| # | 实体（英文） | 展示名 | 一句话职责 | 属性要点 | 出处 | 交叉 | 置信 / 状态 |
|---|---|---|---|---|---|---|---|
| E02 | PurchaseContract | 采购合同 | 与供应商签署的采购合同，记录金额与履约状态 | contract_nr（主键）/ contract_amount（DECIMAL，元，含税）/ sign_date（DATE）/ status（枚举 3 值）/ supplier_code（引用供应商，非空） | X-003、X-006、X-009、X-010；`A_schema/data_dictionary.md#purchase_contract` | A + C | 高 / 已确认 |
| E03 | DeliveryRecord | 交货记录 | WMS 记录的每次交货明细，挂在采购合同下 | delivery_nr（主键）/ contract_nr（引用合同，非空）/ delivery_qty（DOUBLE，件）/ delivery_amount（DECIMAL，元，含税）/ delivery_date（DATE） | X-003、X-006、X-009、X-010；`A_schema/data_dictionary.md#delivery_record` | A + B + C | 高 / 已确认 |
| E04 | ReconciliationStatement | 对账单 | FIM 财务系统按供应商按月生成的对账单，记录发票与对账金额 | recon_nr（主键）/ supplier_code（引用供应商，非空）/ recon_period（STRING，yyyy-MM）/ invoice_amount（DECIMAL，元）/ reconciled_amount（DECIMAL，元）/ status（枚举 3 值）/ create_time / recon_diff_amount（衍生，DECIMAL，元）/ recon_diff_rate（衍生，DECIMAL，比率） | X-003、X-006、X-009、X-010；`A_schema/data_dictionary.md#reconciliation_statement` | A + B + C | 高 / 已确认 |

说明：三个衍生字段的类型资料未给，取值系推断（见 `design-proposal.md` 的假设 AS-01；探索记录 X-013 为待确认的建议）。发票金额、已对账金额的含税口径资料未写明（探索记录 X-014，待确认），故上表不标注含税。

## 2. 关系候选（links）

方向为「持有方 → 目标」。语义名取自数据字典的业务术语列，并经访谈佐证。

| # | 方向（持有方 → 目标） | 语义名 | 基数 | 业务含义 | 出处 | 状态 |
|---|---|---|---|---|---|---|
| R01 | PurchaseContract → Supplier | 签约供应商 | n:1 | 每份采购合同签约于一个供应商；一个供应商可以有多份合同 | X-010、X-016；`A_schema/data_dictionary.md#purchase_contract.supplier_code`（外键→supplier）；`C_interviews/interview_finance.md#Q：合同和交货的关系？` | 已确认 |
| R02 | DeliveryRecord → PurchaseContract | 关联合同 | n:1 | 每条交货记录挂在一份采购合同下；一份合同可以有多条交货记录 | X-010、X-016；`A_schema/data_dictionary.md#delivery_record.contract_nr`（外键→purchase_contract）；`C_interviews/interview_finance.md#Q：合同和交货的关系？` | 已确认 |
| R03 | ReconciliationStatement → Supplier | 对账供应商 | n:1 | 每张对账单对应一个供应商，按供应商加月份生成；一个供应商每月一张 | X-010、X-016；`A_schema/data_dictionary.md#reconciliation_statement.supplier_code`（外键→supplier）；`C_interviews/interview_finance.md#Q：对账单和供应商的关系是怎么挂的？` | 已确认 |

三条关系的引用字段在建表语句里均不允许为空（X-010），没有可空引用。「一个供应商每月一张」是否为硬约束资料未明确（X-035，待确认），上表只把它作为访谈明示的基数约定记录。

## 3. 规则候选

每条候选都做方言可表达性判定：✅ 可表达进 3.1；❌ 需条件逻辑等方言外能力进 3.2。

### 3.1 衍生计算（方言可表达 ✅）

| # | 规则 | 公式 | 出处 | 方言可表达 | 状态 |
|---|---|---|---|---|---|
| RU01 | 对账差异金额 | `recon_diff_amount: invoice_amount - COALESCE(reconciled_amount, 0)` | X-004、X-008；`B_scenarios/rules.md#对账差异金额` | ✅ 四则运算 + COALESCE 空值兜底 | 已确认 |
| RU02 | 对账差异率 | `recon_diff_rate: COALESCE(recon_diff_amount / invoice_amount, 9999)` | X-026；`B_scenarios/rules.md#对账差异率` | ✅ 除法兜底按引擎惯例写法；发票金额为 0 时兜底是否生效待引擎验证 → OQ-01（X-030，待确认） | 已确认（口径） |
| RU03 | 供应商交货总额 | `total_delivery_amount: SUM(purchase_contracts.delivery_records.delivery_amount)` | X-016、X-027；`B_scenarios/rules.md#供应商交货总额` | ✅ 两级反向合计的候选语法；引擎是否支持待验证 → OQ-02（X-031，待确认） | 已确认（口径） |

三个计算结果的取整方式与保留位数资料未说明（X-029，待确认），公式不体现取整。

### 3.2 表达式写不出的计算（方言可表达 ❌ → 函数或运行时契约候选）

无。口径规则一节的五条规则中，三条计算口径均可用表达式方言写出（RU01-RU03），另两条是触发规则（见 3.3）。
RU02、RU03 写得出但引擎行为未验证，已各登记一条待确认问题（OQ-01、OQ-02），不属"写不出"。

另记：三项 KPI（月度复核单量、争议单处理时长、冻结供应商占比）不是口径规则——资料只给了指标名、没有给计算口径（`B_scenarios/rules.md` 一节未列），不建规则；其中「月度复核单量」依赖的"需复核"承载字段与「争议单处理时长」依赖的状态变更时间，分别是探索记录的待确认条目 X-015、X-011。

### 3.3 触发联动（trigger）

失败语义必填——联动失败时原操作结果是否成立。

| # | 规则 | 条件 → 动作 | 下游目标对象 | 失败语义 | 出处 | 状态 |
|---|---|---|---|---|---|---|
| RU04 | 对账差异复核触发 | 差异金额 > 2000 且差异率 > 0.05（合取）→ mark_recon_review，把对账单标记为「需复核」 | 对账单自身 | 不适用：只改自身，没有跨对象联动（联动矩阵 L-003） | X-022；`B_scenarios/rules.md#复核触发`；`B_scenarios/decisions.md#决策 1`；`C_interviews/interview_finance.md#Q：对账差异怎么算、什么情况要人看？` | 已确认 |
| RU05 | 供应商冻结提醒 | 冻结标记 = 真 → mark_supplier_frozen，触发供应商冻结提醒 | 对账单（其所有对账单不再自动推进） | **资料未规定**：提醒失败时冻结是否仍成立未说明（X-024，待确认）；AI 建议冻结照常成立、对账单照常拦截，提醒失败转人工跟进——未确认，不作为事实 | X-023；`B_scenarios/rules.md#冻结拦截`；`B_scenarios/decisions.md#决策 2`；`C_interviews/interview_finance.md#Q：冻结是什么意思？` | 已确认（联动本体）；失败语义待确认 |

## 4. 异常语义 → 规则映射表（强制）

逐节扫描五份资料的异常 / 红线 / 限制语义，逐条落到规则编号或"不建规则的理由"。本表与 `design-proposal.md` 第四节的覆盖核对是同一份清单。

| 异常处理 / 红线 / 附录限制语义（出处） | 对应规则编号 | 或"不建规则的理由" |
|---|---|---|
| 负值 = 多对账（少见，保留负值不取绝对值）（`B_scenarios/rules.md#对账差异金额`） | RU01 | — |
| 无已对账金额时按 0 处理（COALESCE 兜底）（`B_scenarios/rules.md#对账差异金额`） | RU01 | — |
| 发票金额为 0 或缺失时差异率记为 9999，视为异常大、保证触发复核规则（`B_scenarios/rules.md#对账差异率`） | RU02 | —（引擎能否在分母为 0 时让兜底生效待验证 → OQ-01） |
| 两个都超线才必须人工复核，只超一个不用（`C_interviews/interview_finance.md#Q：对账差异怎么算、什么情况要人看？`） | RU04 | — |
| 复核线用严格大于（差异金额 > 2000、差异率 > 0.05），恰好等于阈值不触发（`B_scenarios/rules.md#复核触发`） | RU04 | — |
| 冻结中的供应商，其所有对账单不应继续推进、不自动确认（`B_scenarios/decisions.md#决策 2`） | RU05 | 「不自动推进」如何拦截资料未定义，不另建拦截规则 |
| 冻结期间不能自动确认对账单，系统要给个提醒（`C_interviews/interview_finance.md#Q：冻结是什么意思？`） | RU05 | 提醒失败时的处置资料未规定 → X-024（待确认） |
| 冻结 = 停止对账与付款（`A_schema/data_dictionary.md#supplier.frozen_flag`） | RU05 | 「停止对账」由 RU05 承接；「停止付款」不在本域范围（X-002），不建规则 |
| 三系统各自建表，外键未建约束，业务含义见数据字典（`A_schema/supplier_ddl.sql#三系统各自建表，主键均为业务编码`） | — | 数据现状说明，不是业务规则；引用关系按数据字典建（R01-R03） |
| 合同状态：终止 = 到期或提前终止；作废 = 签署后取消（`A_schema/data_dictionary.md#purchase_contract.status`） | — | 合同终止或作废后交货记录与对账单如何处理资料未说明 → X-025（待确认）；状态变化条件未给 → X-018（待确认） |
| 对账状态 disputed = 存在争议（`A_schema/data_dictionary.md#reconciliation_statement.status`）；KPI 争议单处理时长（`B_scenarios/decisions.md#决策 1`） | — | 争议如何产生、如何处置资料未描述 → X-017（待确认）；状态变更时间资料未给 → X-011（待确认） |
| 一个供应商每月一张（`C_interviews/interview_finance.md#Q：对账单和供应商的关系是怎么挂的？`）；对账单的建表语句只有对账单号唯一（`A_schema/supplier_ddl.sql#reconciliation_statement`） | — | 口头约定与表结构不一致，是否作为硬约束未明确 → X-035（待确认） |
| 冻结标记缺省为 0（`A_schema/supplier_ddl.sql#supplier.frozen_flag`） | — | 缺省值属字段定义；含义写在字段说明里（0 = 正常），不建规则 |
| 三项 KPI：月度复核单量、争议单处理时长、冻结供应商占比（`B_scenarios/decisions.md#决策 1`、`B_scenarios/decisions.md#决策 2`） | — | 资料只给指标名、未给计算口径，口径规则一节未列 → 不建规则 |

## 5. 枚举候选

| 字段 | 枚举值（含含义） | 出处 | 状态 |
|---|---|---|---|
| EN-01 Supplier.settlement_type 结算方式 | 月结30天 / 月结60天 / 货到付款（与供应商约定的付款周期；资料未对各取值另行解释） | X-007；`A_schema/data_dictionary.md#supplier.settlement_type`；`A_schema/supplier_ddl.sql#supplier.settlement_type` | 已确认 |
| EN-02 PurchaseContract.status 合同状态 | 生效（正常履约）/ 终止（到期或提前终止）/ 作废（签署后取消） | X-007；`A_schema/data_dictionary.md#purchase_contract.status`；`A_schema/supplier_ddl.sql#purchase_contract.status`；`C_interviews/interview_finance.md#Q：状态都有哪些？` | 已确认 |
| EN-03 ReconciliationStatement.status 对账状态 | open（对账中）/ confirmed（双方确认）/ disputed（存在争议） | X-007；`A_schema/data_dictionary.md#reconciliation_statement.status`；`A_schema/supplier_ddl.sql#reconciliation_statement.status`；`C_interviews/interview_finance.md#Q：状态都有哪些？` | 已确认 |

对账状态的含义在三处资料里措辞略异（数据字典「双方确认 / 存在争议」、建表语句「已确认 / 有争议」、访谈「双方确认 / 有争议」），同义而非冲突，以数据字典为准。

## 6. conflicts

逐术语交叉比对五份资料（阈值 2000 元与 5% / 0.05、差异算法、复核条件、状态清单、关系挂法），**没有发现同一术语有两种定义的口径冲突**。

交叉比对时发现一处措辞出入，如实记录如下。两处对「交货金额合计」的定义一致，出入只在标题里的一个词，因此没有登记为冲突，而是作为范围待确认条目 X-028 挂在探索记录提示清单：

| 主题 | 一方定义 + 来源 | 另一方定义 + 来源 | 状态 |
|---|---|---|---|
| 供应商交货金额合计的统计范围 | 供应商交货总额 = 该供应商所有合同下**全部**交货记录的交货金额合计（未限定期间）——`B_scenarios/rules.md#供应商交货总额` | 决策 3 标题：「某供应商**本期**实际交付了多少金额？」——`B_scenarios/decisions.md#决策 3`；同一决策的「依据信息」一栏写的是「该供应商所有合同下的交货记录金额合计」，与左侧一致 | 未登记为冲突（定义一致）；「本期」是否要按对账期间过滤待业务方确认 → X-028 |

另有三处"写法不同但语义一致"、经核对不构成冲突的地方，在此留痕以免重复排查：冻结标记的类型（数据字典 BOOLEAN、建表语句 TINYINT(1)）→ 设计稿假设 AS-02；差异率的表示（决策清单写 5%、口径规则写 0.05 并注明"比率，非百分数"）→ 同一阈值；`block_recon_for_frozen_supplier` 与 `mark_supplier_frozen`（前者是规则代号、后者是动作名）→ 见术语表。

## 7. 探索记录承接表

承接自 `modeling-brief/exploration.yaml`（`check_exploration.py` 判定可交接建模：必问项 6 条全部已确认）。下表登记已确认条目（直接作为已确认候选）与未确认的 AI 建议条目（以待确认状态出现，不生成候选）。按纪律，已否决的条目不进卡片、不在本表登记。

| 探索条目编号 | 陈述摘要 | 候选编号 | 承接后的状态 |
|---|---|---|---|
| X-001 | 本域范围与三项决策 | —（范围，不生成候选） | 已确认：写入 `charter.md` 的 Charter 表 |
| X-002 | 范围外：不含发票明细管理与付款执行 | — | 已确认（AI 建议经确认）：写入 `charter.md` 的范围排除 |
| X-003 | 四类对象及其唯一编号 | E01-E04 | 已确认：实体候选 |
| X-004 | 术语「对账差异金额」：发票金额 − 已对账金额，负值保留 | RU01、术语表 | 已确认：规则候选 |
| X-005 | 术语「冻结」：停止对账与付款，采购侧在 SRM 操作 | E01（frozen_flag）、术语表 | 已确认：属性含义与术语 |
| X-006 | 含税口径与计量单位（合同总金额、交货金额含税、元；交货数量件） | E01-E04 的属性要点 | 已确认：字段量纲 |
| X-007 | 三个枚举的取值全集 | EN-01、EN-02、EN-03 | 已确认：枚举候选 |
| X-008 | 空值含义（已对账金额为空按 0；冻结标记缺省 0） | RU01、E01（frozen_flag） | 已确认 |
| X-009 | 字段类型（含冻结标记 BOOLEAN 与 TINYINT(1)） | E01-E04 的属性要点 | 已确认；类型差异登记为设计稿假设 AS-02 |
| X-010 | 三个引用字段不允许为空 | R01、R02、R03 | 已确认：基数 n:1、无可空引用 |
| X-016 | 三条关系与基数 | R01、R02、R03 | 已确认：关系候选 |
| X-020 | 差异超线的对账单由财务对账专员人工复核 | —（动作，不建对象） | 已确认：写入 `charter.md` 边界声明；写入方式未明见 X-021 |
| X-022 | 复核触发：差异金额 > 2000 且差异率 > 0.05，只超一个不触发 | RU04 | 已确认：触发规则候选 |
| X-023 | 供应商冻结后其所有对账单不再自动推进，并触发提醒 | RU05 | 已确认（联动本体）；失败语义未明见 X-024 |
| X-026 | 对账差异率口径（比率、除零记 9999） | RU02 | 已确认：规则候选 |
| X-027 | 供应商交货总额口径（全部交货记录合计，两级查找） | RU03、R01、R02 | 已确认：规则候选 |
| X-032 | 数据来自 SRM、WMS、FIM 三个系统，外键未建约束 | E01-E04（来源系统） | 已确认 |
| X-033 | 资料提出的四条能力问题 | cq-001 至 cq-004 | 已确认：写入 `charter.md` 与 `design-proposal.md` |
| X-011 | 建议对账单增加「状态变更时间」 | 无 | 待确认：AI 建议，未确认——不写进候选，见 `design-proposal.md` 6.2 |
| X-012 | 建议供应商增加「对账联系人」 | 无 | 待确认：AI 建议，未确认——不写进候选，见 `design-proposal.md` 6.2 |
| X-013 | 三个计算字段的数据类型建议 | 无 | 待确认：AI 建议，未确认——DSL 侧仅登记为假设 AS-01 |
| X-014 | 发票金额、已对账金额的含税口径 | 无 | 待确认：AI 建议，未确认——不写进候选，见 `design-proposal.md` 6.2 |
| X-015 | 「需复核」标记的承载信息项 | 无 | 待确认：AI 建议，未确认——不增设字段，见 `design-proposal.md` 6.2 |
| X-017 | 对账单状态如何流转 | 无 | 待确认：AI 建议，未确认——不建规则，见 `design-proposal.md` 6.2 |
| X-018 | 合同状态的变化条件 | 无 | 待确认：AI 建议，未确认——不建规则，见 `design-proposal.md` 6.2 |
| X-021 | 人工复核结论的落库方式 | 无 | 待确认：AI 建议，未确认——不建动作，见 `design-proposal.md` 6.2 |
| X-024 | 冻结提醒失败时冻结是否仍成立 | 无 | 待确认：AI 建议，未确认——失败语义不写成事实，见 RU05 |
| X-025 | 合同终止或作废后交货记录与对账单的处理 | 无 | 待确认：AI 建议，未确认——不建规则，见 `design-proposal.md` 6.2 |
| X-028 | 交货金额合计的「本期」与全量 | 无 | 待确认：AI 建议，未确认——RU03 按口径规则原文建全量合计，见第 6 节 |
| X-029 | 取整方式与保留位数 | 无 | 待确认：AI 建议，未确认——公式不体现取整，见 `design-proposal.md` 6.2 |
| X-030 | 差异率除零兜底的引擎验证 | 无 | 待确认：等引擎——已对应 DSL 待确认问题 OQ-01 |
| X-031 | 两级合计的引擎验证 | 无 | 待确认：等引擎——已对应 DSL 待确认问题 OQ-02 |
| X-034 | 变化响应型能力问题的补充建议 | 无 | 待确认：AI 建议，未确认——不计入能力问题，见 `charter.md` 第四节说明 |
| X-035 | 「供应商加对账期间」是否为唯一限制 | 无 | 待确认：AI 建议，未确认——不加唯一限制，见第 4 节 |
