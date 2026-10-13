# 生成说明（generation-notes）· supplier-recon 本体盲测生成

> 生成日期：2026-10-13 ｜ 生成对象：`generated/model.yaml`
> 盲测纪律声明：本次生成**只读取了** `dsl/README.md`（DSL 规范）与
> `goldstandard/modeling-brief/` 资料包（brief.yaml、A_schema/data_dictionary.md、
> A_schema/supplier_ddl.sql、B_scenarios/rules.md、B_scenarios/decisions.md、
> C_interviews/interview_finance.md，共 6 份，全部通读）。
> 未读取 `goldstandard/gold/` 及其他任何目录；所有设计决策仅来自上述材料。

---

## 一、输入材料与用途总览

| 材料 | 在生成中的用途 |
|---|---|
| `brief.yaml` | 本体标识（domain: supplier-recon）、owner（王财务）、target_engine=new（base_version=null）、场景背景（按月对账、差异超阈值自动复核） |
| `A_schema/data_dictionary.md` | 实体/字段/类型/枚举/主外键/量纲的唯一权威来源（4 张表 26 个字段） |
| `A_schema/supplier_ddl.sql` | 与数据字典交叉验证物理类型；确认主键、FK 未建约束（业务含义见字典） |
| `B_scenarios/rules.md` | 5 条口径规则的业务口径原文（3 derived + 2 trigger） |
| `B_scenarios/decisions.md` | 3 项业务决策 + 4 条能力问题（CQ 的直接来源） |
| `C_interviews/interview_finance.md` | 口径佐证与实体关系佐证（合同→交货两级、按供应商+月生成对账单、9999 约定、「只超一个不用」） |

三份口径来源交叉核对结果：**rules.md / decisions.md / interview 三方在阈值（2000 元、5%/0.05）、
复合条件（两条件同时满足）、差异算法（发票−已对账）上完全一致，无矛盾**。
唯一发现的口径出入是 cf-001（全量 vs 本期，见第五节）。

---

## 二、实体设计决策（粒度与 provenance）

### 为什么是 4 个实体、与表一一对应

| 实体 | 表 | provenance（实体名依据） | 为什么建成实体而不是属性/子表 |
|---|---|---|---|
| `Supplier` | `supplier` | data_dictionary.md `supplier` 表 + DDL `CREATE TABLE supplier` | 有独立主键（supplier_code）、独立源系统（SRM）、被两类单据引用（合同、对账单）——是被引用的主体，必须是实体 |
| `PurchaseContract` | `purchase_contract` | data_dictionary.md `purchase_contract` 表 | 有独立主键（contract_nr）、独立业务生命周期（status: 生效/终止/作废）；是 supplier 与 delivery 的中间层级，访谈明确「顺着 合同→交货 两级找」，拍扁会丢失该层级语义 |
| `DeliveryRecord` | `delivery_record` | data_dictionary.md `delivery_record` 表 | 有独立主键（delivery_nr）、独立源系统（WMS）；每次交货一条，天然是实体 |
| `ReconciliationStatement` | `reconciliation_statement` | data_dictionary.md `reconciliation_statement` 表 | 有独立主键（recon_nr）、独立源系统（FIM）；月度对账主单据，规则与 CQ 的核心载体 |

**不拆不并的理由**：资料包的表结构即业务颗粒度（三系统各自建表、主键均为业务编码），无任何
材料提示需要合并（如把交货并入合同）或拆分（如把对账差异拆独立单据）。差异金额/差异率是
**金额级的衍生口径**而非独立单据（无独立单号、无独立主键），故建为对账单的衍生属性而非实体。

### 命名依据

- 实体名 PascalCase、表名保留字典原文：`Supplier/supplier` 等，4 组全部来自 data_dictionary.md 的 table 列，无发明。
- 字段名 snake_case：逐字来自 data_dictionary.md 的 field 列（26 个字段零改名）。
- 3 个衍生字段名（`recon_diff_amount`、`recon_diff_rate`、`total_delivery_amount`）直接采用 rules.md 各口径标题的括号英文名——这是资料包明示的命名，非生成方发明。

---

## 三、属性与类型决策

1. **类型映射**：全部按 data_dictionary.md 的 data_type 列直译（STRING/INTEGER/DOUBLE/DECIMAL/
   BOOLEAN/DATE/TIMESTAMP 七种之内，无需变换）。DECIMAL(18,2) → DECIMAL（DSL 不含精度槽位）。
2. **`frozen_flag` BOOLEAN vs TINYINT(1)**（as-001）：数据字典标 BOOLEAN，DDL 物理类型
   TINYINT(1)（1=冻结/0=正常，SQL 布尔惯用法）。语义一致、非口径冲突，按字典的 BOOLEAN 建模。
3. **枚举值三组**逐字抄录字典 enum 列：`settlement_type`（月结30天/月结60天/货到付款）、
   `purchase_contract.status`（生效/终止/作废）、`reconciliation_statement.status`
   （open/confirmed/disputed），未增删改任何枚举值。
4. **量纲 uom**：金额类=元、交货数量=件、差异率=比率——均来自字典 definition 列的括号标注。
5. **外键字段保留为属性 + links 声明引用**（as-006）：字典将 supplier_code/contract_nr 列为
   表字段，故属性保留；同时按 DSL §2 在持有方写 links（`supplier: Supplier`、
   `purchase_contract: PurchaseContract`），被引用方不写反向集合（引擎推导），反向引用仅在
   规则表达式用复数表名（`delivery_records`）。
6. **links 别名全部用默认名**（=目标表名 snake_case，as-005）：资料包无短别名诉求。
7. **衍生字段类型系推断**（as-002）：金额→DECIMAL（对齐同域金额字段）、差异率→DECIMAL；
   资料包只给口径未给类型，此推断已列入 assumptions 供人审推翻。
8. **未发明的字段**：没有为「需复核」增加 review_flag 之类字段——资料包把复核定义为系统动作
   打标，schema 中无承载字段，落点不明已列 oq-005。

---

## 四、规则设计决策（5 条）

| # | 规则名（DSL name） | 资料包代号 | 表达式 | 口径出处 | 关键取舍 |
|---|---|---|---|---|---|
| 1 | 对账差异金额 | `recon_diff_amount` | `invoice_amount - COALESCE(reconciled_amount, 0)` | rules.md §对账差异金额 | 「无已对账金额按 0（COALESCE 兜底）」原文即 COALESCE 语义，与方言白名单完全对上；负值保留（不取绝对值）写进 description |
| 2 | 对账差异率 | `recon_diff_rate` | `recon_diff_amount / invoice_amount` | rules.md §对账差异率 | **9999 兜底无法表达**：方言无条件分支函数，表达式只承载基础除法，兜底口径完整记入 description 并列 oq-001，绝不脑补 IF/CASE（lint 白名单会挂） |
| 3 | 供应商交货总额 | `total_delivery_amount` | `SUM(delivery_records.delivery_amount)` | rules.md §供应商交货总额 | 目标字段挂 `Supplier`（口径主语是"该供应商"）；两跳反向聚合（supplier→合同→交货）方言无先例，列 oq-002；与决策3"本期"口径的出入记 cf-001 不擅自裁决 |
| 4 | 复核触发 | `mark_recon_review` | `ALL: diff_amount > 2000, diff_rate > 0.05` → downstream `mark_recon_review` | rules.md §复核触发 + decisions.md 决策1 + 访谈 | 运算符用 `>`（rules.md 原文即 `>`，中文"超过"=严格大于，三份材料一致）；两条件 ALL 合取（访谈"只超一个不用"）；downstream 为平台内置隐式 action（as-004），不入 actions 槽位 |
| 5 | 冻结拦截 | `block_recon_for_frozen_supplier` | `ALL: frozen_flag == true` → downstream `mark_supplier_frozen` | rules.md §冻结拦截 + decisions.md 决策2 + 访谈 | upstream=[Supplier]（条件字段在 supplier 上）；注意规则代号 `block_recon_for_frozen_supplier` 与动作名 `mark_supplier_frozen` 是两个东西（资料包原文即如此）；「对账单不再自动推进」机制未定义，列 oq-003 |

**规则名采用中文**（DSL §3 要求 name 为中文人审用），资料包括号里的英文代号保留在
description 与本表中，保证 provenance 可回溯。

**为什么复核/冻结建 trigger 而不是 derived_property**：资料包对这两条的表述是「标记为需复核」
「触发提醒、不再自动推进」——是条件→系统动作语义（rules.md 标题即「复核触发」「冻结拦截」），
且 downstream 动作名均为平台内置处理，正对 DSL §3.2 trigger 的形态。

---

## 五、conflicts（生成过程新发现，非 brief.yaml 已知项）

brief.yaml 声明 `known_conflicts: []`，但交叉阅读时发现一处口径出入，如实记入
model.yaml `conflicts`（cf-001），**未擅自裁决**：

- **cf-001 交货总额的期间口径**：rules.md 说 total_delivery_amount 是「所有合同下**全部**交货
  记录合计」（全量）；decisions.md 决策3 却问「某供应商**本期**实际交付了多少金额」并与
  **本期**发票金额交叉核对（隐含按期间过滤）。两者算出来的数不同。
  处理：按 rules.md 明示口径建全量合计（它给出了精确定义），「本期交付金额」是否需要独立
  衍生口径提请人审。

---

## 六、open_questions 清单（缺失信息 → 问题）

以下均为资料包**没讲清、生成方拒绝脑补**的信息（6 条）：

| id | 缺失信息 | 为什么不能脑补 |
|---|---|---|
| oq-001 | 差异率 9999 兜底的实现层 | 方言白名单（四则/点路径/SUM/COALESCE/MAX）写不出「为 0 或缺失时记 9999」；rules.md 只给口径未说在哪层实现；擅自用 COALESCE 拼会得到 diff/9999 的错误语义 |
| oq-002 | 两跳反向聚合 `SUM(delivery_records.delivery_amount)` 从 supplier 出发是否可解析 | DSL §2 示例只有单跳复数引用；rules.md 只说口径未给实现路径；若引擎不支持需改为逐级衍生，结构不同，不能替引擎拍板 |
| oq-003 | 冻结拦截「对账单不再自动推进」的具体机制 | 资料包只说给提醒、不能自动确认，未定义任何动作名/状态迁移；若建 admission 需先有 action（一期 DSL 不含） |
| oq-004 | 争议单（disputed）如何产生与处置 | 字典只有枚举值定义；decisions.md KPI 提「争议单处理时长」但无流程描述，无从建模 |
| oq-005 | mark_recon_review 打标的承载字段 | A_schema 对账单表没有复核标记字段；动作落库方式资料包未说，加字段即发明 schema |
| oq-006 | 「供应商+月份」唯一性是约定还是硬约束 | 访谈口头说"一个供应商每月一张"，DDL 无唯一键；同月多单时差异口径（按单/按期间汇总）未说 |

---

## 七、CQ 映射（能力问题 → DSL 元素）

4 条 CQ 逐条来自 decisions.md §能力问题（原文照录），covered_by 映射如下：

| CQ | 来源 | covered_by | 备注 |
|---|---|---|---|
| cq-001 需复核对账单 | 能力问题1 / 决策1 | `recon_diff_amount` + `recon_diff_rate`（衍生字段） | 阈值判定由「复核触发」trigger 承载 |
| cq-002 冻结供应商 | 能力问题2 / 决策2 | `Supplier.frozen_flag` | — |
| cq-003 某供应商本期三金额 | 能力问题3 | `recon_period` + `invoice_amount` + `reconciled_amount` + `recon_diff_amount` | 「本期」= recon_period（yyyy-MM；按供应商每月一张，访谈）；「某供应商」经对账单自带 supplier_code 过滤 |
| cq-004 某供应商交货合计 | 能力问题4 / 决策3 | `Supplier.total_delivery_amount`（衍生字段） | 全量口径，与"本期"出入见 cf-001 |

decisions.md 的 KPI（月度复核单量、争议单处理时长、冻结供应商占比）属度量层，需要
聚合查询能力而非新 DSL 元素，未据此发明实体/字段；其中争议单 KPI 的前置流程缺口已列 oq-004。

---

## 八、治理与版本假设

- `ontology: supplier-recon` ← brief.yaml `domain`
- `base_version: null` ← brief.yaml `target_engine: new`（从零建库）
- `owner: 王财务` ← brief.yaml `business_owner`；实体级 governance 缺省继承本体级
- `version: 0.1.0-draft.1`、`maturity: experimental` ← DSL §1 规则 + 新本体未人审
- `actions: []` ← DSL §4 一期不含；两个内置动作以隐式 action 形式被 trigger 引用（as-004）

---

## 九、lint 自查结果（对照 DSL §7 最小集）

1. **schema 合法**：实体名 PascalCase（4/4）、字段 snake_case（29/29 含衍生）、类型全部在
   7 种枚举内、必填键（display_name/table_name/description/properties、属性 display_name/type）齐备 — 通过
2. **主键**：每实体恰 1 个 primary 且均为 STRING（supplier_code / contract_nr / delivery_nr / recon_nr）— 通过
3. **links 闭合**：`supplier→Supplier`、`purchase_contract→PurchaseContract` 目标实体均存在；
   别名在实体内唯一 — 通过
4. **derived 静态检查**：三个目标字段均存在于 upstream 实体属性；表达式前缀仅
   `delivery_records`（复数引用 = 引用方表名+s）；函数仅 SUM/COALESCE（白名单内）— 通过
   （`delivery_records` 两跳可解析性属引擎行为，已列 oq-002，静态语法层面合法）
5. **trigger**：field 为同实体可解析字段（含衍生字段）；operator ∈ {>, ==}；无 in — 通过
6. **受控词表**：M0 暂缓 — 不适用

## 十、遗留提醒（给人审）

人审需重点裁决：oq-001（9999 兜底落点）、oq-002（两跳聚合实现）、oq-003（冻结拦截机制）、
cf-001（交货总额期间口径）；并复核 as-002（三个衍生字段的推断类型）。
