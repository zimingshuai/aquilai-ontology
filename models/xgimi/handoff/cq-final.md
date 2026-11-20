> 域交接包（handoff）——技能工厂（aquilair-skill-forge）立项素材。
> 红线：本文件是技能**制造时**的输入素材，不是技能**运行时**依赖；
> 动作/规则/字段等易变结构一律以平台 MCP 实时元数据为准，本包内容不沉淀为快照。

# CQ 终版（验收用例种子）

> 用途：技能工厂第⑥步验收的评估用例生成输入——每条 CQ 即一个业务问题验收点；
> 呈审三态勾选结果（真业务/要改/删）见模型目录 cq-checklist.html，人工批复为权威。

| CQ | 业务问题 | 本体覆盖（covered_by） |
|---|---|---|
| cq-001 | BOM、风险 BOM、替代关系或授权发生前后版本变化时，系统识别出哪些变化、波及哪些需求与供给、生成哪些复核任务？ | InspectionChange, ReviewTask |
| cq-002 | 某物料在评估期内的毛需求、替代满足量、已分配供给和物理缺口分别是多少？ | MaterialRequirement.gross_qty, MaterialRequirement.substitute_satisfied_qty, MaterialRequirement.allocated_supply_qty, MaterialRequirement.physical_gap_qty |
| cq-003 | 某物料的待授权数量与参考金额是多少？新增授权后物理缺口是否应随之改变？ | MaterialRequirement.pending_auth_qty, MaterialRequirement.pending_auth_amount, MaterialRequirement.physical_gap_qty, MaterialAuthorization.covered_qty |
| cq-004 | 按供应商整理的参考清单列了哪些物料、建议量、取整增量和预计到货安排？ | SourcingSuggestion.allocated_qty, SourcingSuggestion.suggested_qty, SourcingSuggestion.rounding_extra_qty, SourcingSuggestion.expected_arrival_date, VendorReferenceList |
| cq-005 | 某物料逐期的期初、到货、满足消耗、期末结余与未满足需求是多少？ | PeriodSupplyBalance.beginning_qty, PeriodSupplyBalance.arrival_qty, PeriodSupplyBalance.demand_satisfied_qty, PeriodSupplyBalance.ending_qty, PeriodSupplyBalance.unmet_demand_qty |
| cq-006 | 评估期末哪些物料存在呆滞风险量与风险金额，分别来自现有库存还是未到货订单？ | SlowMovingRisk.risk_qty, SlowMovingRisk.risk_amount, SlowMovingRisk.risk_source_type |
| cq-007 | 取消、延期、替代消耗、转用各方案的窗口内风险、窗口后未消化承诺、行动成本与合计敞口各是多少，是否造成缺料？ | SolutionPlan.window_risk_amount, SolutionPlan.post_window_commitment_amount, SolutionPlan.action_cost, SolutionPlan.total_exposure_amount, SolutionPlan.shortage_flag |
| cq-008 | 某张未到货订单的未收货量、可取消数量上限、取消截止日与延期条件是什么？ | PurchaseOrder.unreceived_qty, PurchaseOrder.cancel_limit_qty, PurchaseOrder.cancel_deadline, PurchaseOrder.postpone_allowed |
| cq-009 | 某历史呆滞案例的呆滞总量、风险形成时点、决策观察时点与证据完整性如何？ | HistoricalCase.stagnant_qty, HistoricalCase.risk_formed_date, HistoricalCase.decision_observed_date, HistoricalCase.evidence_status |
| cq-010 | 历史案例归因中各原因分配了多少数量，未归因部分还剩多少，是否守住"各原因之和≤总量"？ | HistoricalCase.stagnant_qty, HistoricalCase.unattributed_qty, CauseAttribution.attributed_qty |
| cq-011 | 从历史案例沉淀了哪些预防规则，各自触发时机与启用状态是什么？ | PreventionRule.rule_text, PreventionRule.trigger_timing, PreventionRule.status |
| cq-012 | 每次计算运行采用的输入数据版本、观察时间、规则版本与情景（FACT/SIM）是什么？ | CalculationRun.observed_at, CalculationRun.version_id, CalculationRun.rule_version, CalculationRun.scenario_tag, DataVersion |

共 12 条。
