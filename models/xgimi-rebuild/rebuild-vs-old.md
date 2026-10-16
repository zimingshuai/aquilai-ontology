# xgimi-rebuild vs xgimi（旧版）对照分析

> 编制：ontology-modeling v0.3.6 流水线第 5-8 步执行代理 ｜ 日期：2026-10-16
> 对照对象：`models/xgimi-rebuild/model.yaml`（0.1.0-draft.1，本流水线产物，语义依据=已确认设计稿）vs `models/xgimi/model.yaml`（0.3.0-draft.3，2026-10-14 版，含 2026-10-14 用户 12 条 OQ 裁决落档）。
> 性质：**纯对照分析**——旧版仅作参照，未回流影响 rebuild 产物；两版语义差异源自各自的 Charter/设计稿与裁决路径，下文分歧点仅供人审回溯讨论，不构成对任一版的改动。

## 一、规模总览

| 维度 | rebuild（本版） | 旧版 | 差异说明 |
|---|---|---|---|
| 实体 | 25 | 26 | 同名 20，各自独有见下节 |
| links | 49（全部显式 fk + 中文语义名） | 39（部分引用降级为属性，见旧版假设 A7） | v0.3.4 显式 fk 能力引入后复合引用可进 links |
| 规则 | 13（11 derived + 2 trigger），RU-14 落 OQ-12 | 19（13 derived + 5 trigger + 1 admission） | 汇总实体与动作域的有无导致规则数差 |
| 动作 | 0（POC 只读，无 actions 段） | 6（OQ-02~09 裁决"C 方案动作域承载"） | 版本定位差异：旧版已进入动作域，rebuild 严守只读边界 |
| CQ | 12 | 12 | 措辞不同（rebuild 按 charter 重写，更细） |
| OQ | 12（11 原样 + OQ-12 新增） | 12（9 resolved + 3 pending-business） | 旧版多数已裁决；rebuild 待本轮人审 |
| lint_model | 0 error / 0 warning | —（未重跑，非本次验收范围） | — |

## 二、实体集合差异

### 同名实体（20 个）

Project、Material、Supplier、SupplierSupplyCondition、UnitConversion、BomLine、EcnRecord、Demand、MaterialAuthorization、Supply、StockMovement、SubstitutionPermission、CalculationRun、SourcingSuggestion、VendorReferenceList、SlowMovingRisk、SolutionPlan、HistoricalCase、CauseAttribution、PreventionRule

同名实体中**主键不同**（旧版代理 ID → rebuild 业务复合自然键，假设 A-06）：

| 实体 | 旧版主键 | rebuild 主键 |
|---|---|---|
| Project | project_id | project_code |
| Supplier | supplier_id | supplier_code |
| SupplierSupplyCondition | condition_id | supplier_code + material_code |
| UnitConversion | conversion_id | material_code + alt_unit |
| Demand | demand_id + demand_version | demand_id + record_version（字段名差异） |
| MaterialAuthorization | auth_id + auth_version | project_code + material_code + auth_version（业务维度直接作键） |
| SourcingSuggestion | suggestion_id | run_id + material_code + supplier_code |
| VendorReferenceList | list_id | run_id + supplier_code |
| PeriodSupplyDemand/Balance（异名对应） | balance_id | run_id + material_code + period |
| SlowMovingRisk | risk_id | run_id + material_code |
| SolutionPlan | plan_id | run_id + plan_code |
| CauseAttribution | attribution_id | case_id + cause_type |
| HistoricalCase / ChangeRecord(InspectionChange) / PreventionRule 等 | 单 ID | 同为单业务编码（形态一致） |

### rebuild 独有（5 个）

| 实体 | 职责 | 对旧版的替代关系 |
|---|---|---|
| ChangeRecord | 点检单条变化（六类） | 概念对应旧版 InspectionChange（异名） |
| ImpactRecord | 变化影响合并明细 + 复核状态内嵌 | 替代旧版 InspectionChange.impact_desc 字段 + ReviewTask 实体 |
| AllocationRecord | 一批供给对一个需求（含替代路径）的分配明细 | 替代旧版 MaterialRequirement 的汇总承载（行级可展开复算） |
| PeriodSupplyDemand | 分期供需行 | 概念对应旧版 PeriodSupplyBalance（异名） |
| HistoricalMilestone | 案例时间线锚点（何时已知什么） | 替代旧版 HistoricalCase 上的 risk_formed_date / decision_observed_date 散落字段 |

### 旧版独有（6 个）

| 实体 | 职责 | rebuild 的处理 |
|---|---|---|
| PurchaseOrder | 订单承诺与取消/延期条款（订单侧 14 字段） | 并入 Supply（supply_type=已确认未收货订单 + order/received/cancelled/closed 字段 + 取消截止日/取消费/延期说明，假设 A-05：文档统一编号统一表） |
| DataVersion | 数据版本 V0-V3 实体 | 不建（假设 A-02：版本由各记录 known_at + CalculationRun.data_version 承载） |
| MaterialRequirement | 物料粒度汇总（毛需求/替代满足/已分配/授权覆盖/缺口/待授权） | 拆解：分配明细→AllocationRecord；待授权→MaterialAuthorization.pending_auth_qty（RU-09）；毛需求→BomLine.lower_level_demand_qty（RU-02 单层）+ gross_demand_qty 输入位 |
| InspectionChange | 点检变化记录 | 概念保留，更名 ChangeRecord（语义聚焦"单条变化"，与影响记录解耦） |
| ReviewTask | 复核任务实体 | 不建（charter §三判定：任务状态归入 ImpactRecord.review_status 字段，无独立生命周期身份） |
| PeriodSupplyBalance | 分期供需 | 概念保留，更名 PeriodSupplyDemand（语义聚焦"供需推演"而非"余额"） |

## 三、关系（links）差异

1. **数量与表达力**：rebuild 49 条全部显式 fk + 中文语义名（lint13 0 warning）；旧版 39 条且受 v0.2.2 单字段外键约定约束，把复合主键目标与同目标第二引用降级为属性（旧版假设 A7：BomLine.parent_material_id、SubstitutionPermission.substitute_material_id、Demand.covered_by_demand_id 均不进 links）——dsl-spec v0.3 显式 fk 能力正是由此实证引入，rebuild 恢复了这些关系（父项/子项双链、被需求覆盖、替换历史版本等）。
2. **新增关系结构**：rebuild 的 ChangeRecord→BomLine/替代/授权 三向可空指向、ImpactRecord→项目/物料、AllocationRecord→需求/供给/许可、HistoricalCase→旧料/新料双链（旧版案例物料单链）；旧版的 Supply→PurchaseOrder（在途订单）、CalculationRun→DataVersion（输入版本）、SolutionPlan→PurchaseOrder（目标订单）随实体取消而消失（语义并入 Supply 自身字段）。

## 四、规则差异（逐条映射）

### derived（rebuild 11 vs 旧版 13）

| rebuild | 旧版对应 | 差异 |
|---|---|---|
| RU-01 标准用量（BomLine） | 标准用量（BomLine） | 同式（std_usage_qty vs standard_usage 字段名差异） |
| RU-02 下层物料需求（BomLine，单层展开） | 无 DSL 规则（OQ-02 裁决 C 方案：动作 expand_demand_to_requirement 承载多层展开） | **形态分歧**：rebuild 以单层表达式进 DSL（多层的递归留 OQ-03 引擎验证）；旧版整体外移动作域 |
| RU-03 订单未收货量（Supply） | 订单未收货量（PurchaseOrder） | 同式，挂载实体随 PurchaseOrder 并入 Supply 迁移 |
| RU-04 分期期末量（PeriodSupplyDemand） | 本期期末量（PeriodSupplyBalance） | 同式 |
| RU-05 分期未满足需求（PeriodSupplyDemand） | 本期未满足需求（PeriodSupplyBalance） | 同式 |
| RU-06 期末风险量（SlowMovingRisk） | 期末风险量（SlowMovingRisk） | 同式 |
| RU-07 风险金额（risk_qty × material.cost_unit_price） | 呆滞风险金额（risk_qty × unit_cost 本实体冗余字段） | rebuild 消除单价冗余（最小属性原则：单价唯一落 Material） |
| RU-08 建议量取整（rounding_extra_qty = suggested_qty − allocated_qty） | 无对应 derived（旧版 OQ-01 裁决 A 方案：CEILING 待引擎扩展后由 derived 承载，现仅运行时契约） | rebuild 把可衍生的"取整额外量"落 DSL，取整本身两侧同为待引擎/输入侧 |
| RU-09 待授权数量（MaterialAuthorization） | 待授权数量 + 待授权参考金额（MaterialRequirement 两条） | 挂载实体迁移；参考金额 rebuild 由查询侧计算不单列（旧版有 pending_auth_amount derived） |
| RU-10 还原期末库存（HistoricalCase） | 无对应（旧版 HistoricalCase 无还原公式规则，还原语义散在描述） | rebuild 显式落公式 |
| RU-11 模拟可减少风险量（HistoricalCase） | 模拟可减少风险量（SolutionPlan） | **挂载迁移**：旧版把不干预/干预风险量放 SolutionPlan（方案对比域），rebuild 放 HistoricalCase（场景 55 历史干预模拟独立成域） |
| —（无对应） | 剩余新料需求 / 新料缺口 / 方案合计敞口 / 未归因数量（4 条） | 见"值得回溯讨论"第 4/5 点 |

### trigger（rebuild 2 vs 旧版 5）

| rebuild | 旧版对应 | 差异 |
|---|---|---|
| RU-12 呆滞风险触发（risk_qty > 0） | 呆滞风险触发复核（同条件） | 同式；downstream 占位名两侧不同（notify_slow_moving_risk vs create_risk_review_task） |
| RU-13 换料未到货检查（approve_status==已批准 单条件） | 工程变更预防检查触发（approval_status==approved **AND evidence_status==complete** 双条件） | **口径差异**：旧版把"影响能够判断"映射为证据齐全条件；rebuild 仅落批准条件 |
| — | 授权数量变化重核算（InspectionChange→recompute_pending_authorization） | rebuild 无对应触发 |
| — | 替代关系变化复核分配方案（→review_allocation_validity） | rebuild 无对应触发（失效替代"保留问题记录不参与计算"仅在描述中） |
| — | 冻结供给排除待核查（supply_type==frozen_stock→exclude_from_allocation_and_flag） | rebuild 无对应触发（冻结单列语义由 supply_type 枚举 + OQ-09 字段承载） |

### admission（rebuild 0 vs 旧版 1）

旧版「归因不得超案例总量」admission 挂在 record_cause_attribution 动作上（OQ-09 裁决"立即落地"），并以 HistoricalCase.unattributed_qty derived 量化余量。rebuild 的 RU-14（分配≤可用 + 归因之和≤总量）落 OQ-12 动作域候选——因为 rebuild 无 actions 段（POC 只读），admission 无处可挂；建占位动作违反"不发明语义"。

## 五、结构决策差异摘要（六项）

1. **ChangeRecord vs InspectionChange+ReviewTask**：旧版把"变化识别"与"复核任务"拆两实体（ReviewTask 有独立状态机 open/cancelled/adjusted/retained/closed）；rebuild 按 charter §三"流程步骤不建实体"判定，复核状态内嵌 ImpactRecord.review_status（待复核/已收处理依据/关闭）。取舍本质：任务是否具备独立身份+生命周期——两版判定相反，rebuild 版少一个实体但任务处理记录粒度较粗（处理依据落 review_note/evidence_refs 文字）。
2. **PurchaseOrder 独立 vs 并入 Supply**：旧版订单侧 14 字段独立成实体（含状态机 confirmed/closed/cancelled）；rebuild 忠实"文档统一编号统一表"（A-05）并入 Supply，代价是 Supply 字段变宽、订单状态机未显式建模。
3. **DataVersion 建与不建**：旧版独立实体承载版本→可见时间映射（visible_at TIMESTAMP）；rebuild 以 known_at 字段 + CalculationRun.data_version 承载（A-02），版本表 change_summary 摘要语义丢失（不入本体）。
4. **MaterialRequirement（汇总快照）vs AllocationRecord（行级明细）**：旧版在物料粒度汇总（5 条 derived 直接支撑 CQ）；rebuild 行级分配明细（"保证可展开复算"，设计稿 E16），汇总口径可由行级聚合。取舍：旧版查询直接、复算需信任汇总过程；rebuild 复算可展开、但物料粒度汇总无 DSL 衍生承载。
5. **历史时间线：散落字段 vs HistoricalMilestone 实体**：旧版在 HistoricalCase 上放 risk_formed_date/decision_observed_date 两个字段（单案例两时点）；rebuild 建时点实体（四类时点可变数量，"其他案例不必相同"），known_info 显式承载"当时已知什么"（cq-008/cq-009 的直接支撑）。
6. **主键策略**：旧版几乎全代理 ID（project_id/supplier_id/…，A6/A7 为 studio-model 单字段外键约定所做的适配）；rebuild 全业务复合自然键（A-06）。副作用见"值得回溯讨论"第 6 点。

## 六、值得回溯讨论的分歧点（供人审裁决，按影响排序）

1. **RU-13 触发条件宽度**：旧版双条件（批准 AND 证据齐全），rebuild 单条件（批准）。缺证 ECN（如历史 H-ECN-01 缺证版本）在 rebuild 形态下会触发检查但依据不全——建议 FDE 裁决是否补 evidence_status==完整 条件（rebuild 的 EcnRecord.evidence_status 字段已具备，加条件零成本）。
2. **三条 trigger 的取舍**：授权数量变化重算、替代关系变化复核、冻结供给排除待核查在旧版均有触发规则（§4.2 点检异常处理 + §11.3 PS-1002 语义），rebuild 设计稿 14 条规则未纳入。若 POC 需要演示"点检→自动响应"闭环，rebuild 需补规则或由人审确认裁剪依据。
3. **RU-14 形态与动作域路线**：旧版已走通"admission + 真实动作（record_cause_attribution）"先例且用户裁决过（2026-10-14 OQ-09）；rebuild 因只读边界整体落 OQ-12。两版路线需要在平台落地前统一：若 rebuild 后续接入引擎，须补动作域（至少归因写入与分配写入两个动作）才能承载两条红线约束。
4. **汇总口径的 DSL 承载缺口**：旧版 MaterialRequirement 有 剩余新料需求/新料缺口/待授权参考金额/方案合计敞口 4 条 derived；rebuild 对应语义分散为输入字段与查询侧计算（gross_demand_qty、窗口承诺字段、feasible_reason），物料粒度缺口（cq-003 的"缺口还剩多少"）无衍生公式直接回答。可讨论：是否在 AllocationRecord/SlowMovingRisk 上补缺口衍生，或接受"行级明细+查询聚合"路线。
5. **known_at 类型**：旧版 STRING 版本号（A3 + OQ-12 记录"V0 之前"无法日期化，转业务方补充）；rebuild 定 TIMESTAMP 时点（A-01 类型推断口径）。若客户数据确有"V0 之前"取值，TIMESTAMP 将无法承载——建议人审时与旧版 OQ-12 的业务方答复对齐后定类型。
6. **复合自然键与 studio-model 单字段连线的边界**：rebuild 复合主键实体导致编译时 6 条连线跳过（目标为复合主键，模板 sourcePropertyCode 无法单值表达）+ lint_studio_model 17 处"主键连主键"error（复合主键成员同时是外键）。旧版代理 ID + A7 属性降级正是为绕开此边界的适配。需平台侧确认：模板/平台是否支持复合键连线，否则 rebuild 导入平台前需 Studio 侧手工配置 6 条关系或重新评估代理键。
7. **CQ 措辞与覆盖深度**：两版 12 条 CQ 主题对应但措辞不同（rebuild 版含更多验证型细节如"授权增加会不会误增物理供给""证据不足能否忍住不给结论"）；旧版 cq-008 关注订单取消条款（PurchaseOrder 字段直答），rebuild 对应问题改由 Supply.restriction_note/cancel_deadline_date 承载。人审可对照确认 rebuild 版 CQ 覆盖不弱于旧版。

## 七、结论

两版差异主因不是资料变化，而是**三条路线选择**：①rebuild 严守 POC 只读（无动作域→admission/多层展开/汇总计算全部外移或留 OQ），旧版已扩展到动作域；②rebuild 行级明细复算优先（AllocationRecord）vs 旧版汇总快照优先（MaterialRequirement）；③rebuild 业务复合自然键 vs 旧版代理 ID（对 studio-model/平台导入边界的不同取舍）。同名 20 实体的核心口径（标准用量、订单未收货量、分期推演、风险量、风险金额公式）两版一致，未发现语义矛盾；分歧集中在上述 7 点，建议人审时逐条裁决后决定是否回流。
