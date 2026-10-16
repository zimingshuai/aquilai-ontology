# 本体拓扑：xgimi-rebuild（0.2.0-draft.2）

> 由 render_topology.py 从 DSL 自动生成；仅含实体 + links + 规则三要素，不含能力问题（CQ）。
> 图例：🔑 = 主键；关联线 `目标 "1" --> "*" 持有方 : 别名` = 持有方实体的 links 别名持有指向目标的引用；
> 【衍生】= derived_property（目标字段: 表达式）；【触发】= trigger 条件摘要（多条件合取）。

```mermaid
    classDiagram
    class Project {
        +project_code : STRING 🔑
        +project_name : STRING
        +model : STRING
        +stage : STRING
        +bom_status_desc : STRING
    }
    class Material {
        +material_code : STRING 🔑
        +material_name : STRING
        +base_uom : STRING
        +cost_unit_price : DOUBLE
    }
    class Supplier {
        +supplier_code : STRING 🔑
        +supplier_name : STRING
        +purchase_group : STRING
    }
    class SupplierSupplyCondition {
        +condition_id : STRING 🔑
        +supplier_code : STRING
        +material_code : STRING
        +lead_time_days : INTEGER
        +moq : INTEGER
        +order_multiple : INTEGER
        +quota_ratio : DOUBLE
    }
    class UnitConversion {
        +conversion_id : STRING 🔑
        +material_code : STRING
        +alt_unit : STRING
        +factor : DOUBLE
        +approval_status : STRING
    }
    class BomLine {
        +bom_line_id : STRING 🔑
        +bom_type : STRING
        +bom_version : STRING
        +parent_material_code : STRING
        +child_material_code : STRING
        +project_code : STRING
        +ecn_id : STRING
        +line_qty : DOUBLE
        +base_qty : DOUBLE
        +yield_rate : DOUBLE
        +valid_from : DATE
        +valid_to : DATE
        +known_at : TIMESTAMP
        +std_usage_qty : DOUBLE
        +lower_level_demand_qty : DOUBLE
    }
    class EcnRecord {
        +ecn_id : STRING 🔑
        +ecn_desc : STRING
        +publish_time : TIMESTAMP
        +effective_date : DATE
        +approve_status : STRING
        +evidence_status : STRING
    }
    class Demand {
        +demand_uid : STRING 🔑
        +demand_id : STRING
        +record_version : STRING
        +demand_type : STRING
        +project_code : STRING
        +required_qty : INTEGER
        +required_date : DATE
        +is_estimate : BOOLEAN
        +covered_demand_id : STRING
        +covered_demand_version : STRING
        +superseded_demand_id : STRING
        +superseded_demand_version : STRING
        +supersedes_uid : STRING
        +covered_by_uid : STRING
    }
    class MaterialAuthorization {
        +auth_id : STRING 🔑
        +project_code : STRING
        +material_code : STRING
        +auth_version : STRING
        +authorized_qty : INTEGER
        +approve_date : DATE
        +status : STRING
        +gross_demand_qty : INTEGER
        +pending_auth_qty : INTEGER
    }
    class Supply {
        +supply_id : STRING 🔑
        +supply_type : STRING
        +material_code : STRING
        +run_id : STRING
        +qty : INTEGER
        +available_date : DATE
        +branch : STRING
        +order_qty : INTEGER
        +received_qty : INTEGER
        +cancelled_qty : INTEGER
        +closed_unreceived_qty : INTEGER
        +open_order_qty : INTEGER
        +cancel_deadline_date : DATE
        +cancellation_fee : DOUBLE
        +restriction_note : STRING
    }
    class StockMovement {
        +movement_id : STRING 🔑
        +movement_type : STRING
        +material_code : STRING
        +source_supply_id : STRING
        +qty : INTEGER
        +movement_date : DATE
    }
    class SubstitutionPermission {
        +permission_id : STRING 🔑
        +permission_type : STRING
        +replaced_material_code : STRING
        +replacing_material_code : STRING
        +project_code : STRING
        +conversion_ratio : DOUBLE
        +valid_from : DATE
        +valid_to : DATE
        +batch_limit_note : STRING
        +approval_cap_qty : INTEGER
        +approve_status : STRING
    }
    class CalculationRun {
        +run_id : STRING 🔑
        +known_at : TIMESTAMP
        +data_version : STRING
        +rule_version : STRING
        +branch : STRING
        +scenario_no : STRING
        +eval_start_date : DATE
        +eval_end_date : DATE
    }
    class ChangeRecord {
        +change_id : STRING 🔑
        +change_type : STRING
        +old_value : STRING
        +new_value : STRING
        +check_advice : STRING
        +run_id : STRING
        +bom_line_id : STRING
        +permission_id : STRING
        +project_code : STRING
        +material_code : STRING
        +auth_version : STRING
        +auth_id : STRING
    }
    class ImpactRecord {
        +impact_id : STRING 🔑
        +run_id : STRING
        +project_code : STRING
        +material_code : STRING
        +evidence_refs : STRING
        +review_status : STRING
        +impact_scope : STRING
    }
    class AllocationRecord {
        +allocation_id : STRING 🔑
        +demand_id : STRING
        +demand_version : STRING
        +supply_id : STRING
        +permission_id : STRING
        +run_id : STRING
        +allocated_qty : INTEGER
        +priority_seq : INTEGER
        +reserved_flag : BOOLEAN
        +demand_uid : STRING
    }
    class SourcingSuggestion {
        +suggestion_id : STRING 🔑
        +run_id : STRING
        +material_code : STRING
        +supplier_code : STRING
        +allocated_qty : INTEGER
        +suggested_qty : INTEGER
        +rounding_extra_qty : INTEGER
        +eta_meets_demand : BOOLEAN
        +list_id : STRING
    }
    class VendorReferenceList {
        +list_id : STRING 🔑
        +run_id : STRING
        +supplier_code : STRING
        +list_status : STRING
        +review_note : STRING
    }
    class PeriodSupplyDemand {
        +balance_id : STRING 🔑
        +run_id : STRING
        +material_code : STRING
        +period : STRING
        +opening_qty : INTEGER
        +arrival_qty : INTEGER
        +other_inflow_qty : INTEGER
        +required_qty : INTEGER
        +fulfilled_qty : INTEGER
        +other_outflow_qty : INTEGER
        +closing_qty : INTEGER
        +unmet_carry_qty : INTEGER
    }
    class SlowMovingRisk {
        +risk_id : STRING 🔑
        +run_id : STRING
        +material_code : STRING
        +risk_type : STRING
        +remaining_qty : INTEGER
        +reserved_qty : INTEGER
        +post_period_consumed_qty : INTEGER
        +risk_qty : INTEGER
        +risk_amount : DOUBLE
        +window_later_commit_qty : INTEGER
        +window_later_commit_amount : DOUBLE
        +pending_check_amount : DOUBLE
    }
    class SolutionPlan {
        +plan_id : STRING 🔑
        +run_id : STRING
        +plan_code : STRING
        +action_type : STRING
        +material_code : STRING
        +adjusted_supply_id : STRING
        +action_cost : DOUBLE
        +shortage_flag : BOOLEAN
        +feasible_reason : STRING
        +risk_id : STRING
    }
    class HistoricalCase {
        +case_id : STRING 🔑
        +project_code : STRING
        +old_material_code : STRING
        +new_material_code : STRING
        +observation_start : DATE
        +observation_end : DATE
        +future_demand_check_end : DATE
        +evidence_status : STRING
        +rebuilt_opening_qty : INTEGER
        +received_in_qty : INTEGER
        +consumed_out_qty : INTEGER
        +rebuilt_closing_qty : INTEGER
        +stock_check_diff : INTEGER
        +baseline_risk_qty : INTEGER
        +intervened_risk_qty : INTEGER
        +simulated_reducible_qty : INTEGER
    }
    class HistoricalMilestone {
        +milestone_id : STRING 🔑
        +case_id : STRING
        +milestone_type : STRING
        +milestone_date : DATE
        +known_info : STRING
    }
    class CauseAttribution {
        +attribution_id : STRING 🔑
        +case_id : STRING
        +cause_type : STRING
        +attributed_qty : INTEGER
        +evidence_ref : STRING
        +conclusion_level : STRING
    }
    class PreventionRule {
        +rule_id : STRING 🔑
        +source_case_id : STRING
        +rule_content : STRING
        +trigger_condition : STRING
        +rule_status : STRING
    }
    note for BomLine "【衍生】std_usage_qty: line_qty / base_qty<br/>【衍生】lower_level_demand_qty: SUM(project.demands.required_qty) * std_usage_qty / COALESCE(yield_rate, 1)"
    note for Supply "【衍生】open_order_qty: MAX(order_qty - received_qty - cancelled_qty - closed_unreceived_qty, 0)"
    note for PeriodSupplyDemand "【衍生】closing_qty: opening_qty + arrival_qty + other_inflow_qty - fulfilled_qty - other_outflow_qty<br/>【衍生】unmet_carry_qty: required_qty - fulfilled_qty"
    note for SlowMovingRisk "【衍生】risk_qty: MAX(remaining_qty - reserved_qty - post_period_consumed_qty, 0)<br/>【衍生】risk_amount: risk_qty * material.cost_unit_price<br/>【触发】呆滞风险触发: risk_qty ＞ 0"
    note for SourcingSuggestion "【衍生】rounding_extra_qty: suggested_qty - allocated_qty"
    note for MaterialAuthorization "【衍生】pending_auth_qty: gross_demand_qty - authorized_qty"
    note for HistoricalCase "【衍生】rebuilt_closing_qty: rebuilt_opening_qty + received_in_qty - consumed_out_qty<br/>【衍生】simulated_reducible_qty: MAX(baseline_risk_qty - intervened_risk_qty, 0)"
    note for EcnRecord "【触发】换料未到货检查: approve_status == 已批准"
    Supplier "1" --> "*" SupplierSupplyCondition : 供货供应商
    Material "1" --> "*" SupplierSupplyCondition : 适用物料
    Material "1" --> "*" UnitConversion : 换算物料
    Material "1" --> "*" BomLine : 父项物料
    Material "1" --> "*" BomLine : 子项物料
    Project "1" --> "*" BomLine : 隶属项目
    EcnRecord "1" --> "*" BomLine : 产生于变更
    Project "1" --> "*" Demand : 归属项目
    Demand "1" --> "*" Demand : 被需求覆盖
    Demand "1" --> "*" Demand : 替换历史版本
    Project "1" --> "*" MaterialAuthorization : 授权项目
    Material "1" --> "*" MaterialAuthorization : 授权物料
    Material "1" --> "*" Supply : 供给物料
    CalculationRun "1" --> "*" Supply : 所属运行
    Material "1" --> "*" StockMovement : 收发物料
    Supply "1" --> "*" StockMovement : 来源供给
    Material "1" --> "*" SubstitutionPermission : 被替代物料
    Material "1" --> "*" SubstitutionPermission : 替代物料
    Project "1" --> "*" SubstitutionPermission : 适用项目
    CalculationRun "1" --> "*" ChangeRecord : 所属运行
    BomLine "1" --> "*" ChangeRecord : 涉及BOM行
    SubstitutionPermission "1" --> "*" ChangeRecord : 涉及替代关系
    MaterialAuthorization "1" --> "*" ChangeRecord : 涉及授权
    CalculationRun "1" --> "*" ImpactRecord : 所属运行
    Project "1" --> "*" ImpactRecord : 受影响项目
    Material "1" --> "*" ImpactRecord : 受影响物料
    Demand "1" --> "*" AllocationRecord : 分配需求
    Supply "1" --> "*" AllocationRecord : 分配供给
    SubstitutionPermission "1" --> "*" AllocationRecord : 依据替代许可
    CalculationRun "1" --> "*" AllocationRecord : 所属运行
    Material "1" --> "*" SourcingSuggestion : 建议物料
    Supplier "1" --> "*" SourcingSuggestion : 建议供应商
    VendorReferenceList "1" --> "*" SourcingSuggestion : 列入参考清单
    CalculationRun "1" --> "*" SourcingSuggestion : 所属运行
    Supplier "1" --> "*" VendorReferenceList : 面向供应商
    CalculationRun "1" --> "*" VendorReferenceList : 所属运行
    Material "1" --> "*" PeriodSupplyDemand : 供需物料
    CalculationRun "1" --> "*" PeriodSupplyDemand : 所属运行
    Material "1" --> "*" SlowMovingRisk : 风险物料
    CalculationRun "1" --> "*" SlowMovingRisk : 所属运行
    SlowMovingRisk "1" --> "*" SolutionPlan : 处置风险
    Supply "1" --> "*" SolutionPlan : 调整供给
    CalculationRun "1" --> "*" SolutionPlan : 所属运行
    Project "1" --> "*" HistoricalCase : 历史项目
    Material "1" --> "*" HistoricalCase : 案例旧料
    Material "1" --> "*" HistoricalCase : 案例新料
    HistoricalCase "1" --> "*" HistoricalMilestone : 归属案例
    HistoricalCase "1" --> "*" CauseAttribution : 归属案例
    HistoricalCase "1" --> "*" PreventionRule : 源自案例
```
