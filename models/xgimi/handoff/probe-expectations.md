> 域交接包（handoff）——技能工厂（aquilair-skill-forge）立项素材。
> 红线：本文件是技能**制造时**的输入素材，不是技能**运行时**依赖；
> 动作/规则/字段等易变结构一律以平台 MCP 实时元数据为准，本包内容不沉淀为快照。

# MCP 实测预期清单（比对用，不沉淀）

> 用途：技能工厂第②步实测的预期输入——带着本清单去验证 19 工具，实测从盲摸变验证；
> **本件比对后即弃**：与实时元数据的差异以平台为准并记入 facts 坑典，本清单不进技能资产
> （历史实证：actions 三周内 15→22，快照必漂）。

- 实体（26 个）：Project、Material、UnitConversion、Supplier、BomLine、EcnRecord、Demand、MaterialAuthorization、Supply、PurchaseOrder、StockMovement、SubstitutionPermission、SupplierSupplyCondition、DataVersion、CalculationRun、MaterialRequirement、InspectionChange、ReviewTask、SourcingSuggestion、VendorReferenceList、PeriodSupplyBalance、SlowMovingRisk、SolutionPlan、HistoricalCase、CauseAttribution、PreventionRule
- 动作（6 个）：expand_demand_to_requirement、allocate_supply、compute_period_balance、check_substitution_qualification、recompute_scenario、record_cause_attribution
- 规则（19 条）：标准用量、订单未收货量、剩余新料需求、新料缺口、待授权数量、待授权参考金额、本期期末量、本期未满足需求、期末风险量、呆滞风险金额、方案合计敞口、模拟可减少风险量、未归因数量、呆滞风险触发复核、工程变更预防检查触发、授权数量变化重核算、替代关系变化复核分配方案、冻结供给排除待核查、归因不得超案例总量
