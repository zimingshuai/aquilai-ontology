# 本体拓扑：xgimi（0.3.0-draft.3）

> 由 render_topology.py 从 DSL 自动生成；仅含实体 + links + 规则三要素，不含能力问题（CQ）。
> 图例：🔑 = 主键；关联线 `目标 "1" --> "*" 持有方 : 别名` = 持有方实体的 links 别名持有指向目标的引用；
> 【衍生】= derived_property（目标字段: 表达式）；【触发】= trigger 条件摘要（多条件合取）。

```mermaid
    classDiagram
    class Project {
        +project_id : STRING 🔑
        +project_code : STRING
        +model_name : STRING
        +stage : STRING
        +bom_status_desc : STRING
        +purpose_desc : STRING
    }
    class Material {
        +material_code : STRING 🔑
        +material_name : STRING
        +base_uom : STRING
        +unit_cost : DECIMAL
    }
    class UnitConversion {
        +conversion_id : STRING 🔑
        +material_id : STRING
        +from_uom : STRING
        +to_uom : STRING
        +ratio : DECIMAL
        +approval_status : STRING
        +evidence_status : STRING
    }
    class Supplier {
        +supplier_id : STRING 🔑
        +supplier_name : STRING
        +purchasing_group : STRING
    }
    class BomLine {
        +line_id : STRING 🔑
        +bom_type : STRING
        +version : STRING
        +parent_material_id : STRING
        +material_id : STRING
        +project_id : STRING
        +qty_per : DECIMAL
        +base_qty : DECIMAL
        +yield_rate : DOUBLE
        +effective_from : DATE
        +effective_to : DATE
        +known_at : STRING
        +evidence_status : STRING
        +standard_usage : DECIMAL
    }
    class EcnRecord {
        +ecn_id : STRING 🔑
        +project_id : STRING
        +change_desc : STRING
        +publish_date : DATE
        +effective_date : DATE
        +approval_status : STRING
        +evidence_status : STRING
        +known_at : STRING
    }
    class Demand {
        +demand_id : STRING 🔑
        +demand_version : STRING 🔑
        +project_id : STRING
        +need_date : DATE
        +demand_qty : DECIMAL
        +source_type : STRING
        +covered_by_demand_id : STRING
        +status : STRING
        +known_at : STRING
        +package_id : STRING
    }
    class MaterialAuthorization {
        +auth_id : STRING 🔑
        +auth_version : STRING 🔑
        +material_id : STRING
        +project_id : STRING
        +covered_qty : DECIMAL
        +approval_status : STRING
        +effective_from : DATE
        +known_at : STRING
        +package_id : STRING
    }
    class Supply {
        +supply_id : STRING 🔑
        +material_id : STRING
        +supply_type : STRING
        +qty : DECIMAL
        +available_date : DATE
        +restriction_desc : STRING
        +po_id : STRING
        +scenario_tag : STRING
        +package_id : STRING
        +known_at : STRING
        +exclude_reason : STRING
    }
    class PurchaseOrder {
        +po_id : STRING 🔑
        +material_id : STRING
        +order_qty : DECIMAL
        +cumulative_receipt_qty : DECIMAL
        +cancelled_qty : DECIMAL
        +closed_unreceived_qty : DECIMAL
        +confirmed_arrival_date : DATE
        +cancel_deadline : DATE
        +cancel_fee_per_unit : DECIMAL
        +cancel_limit_qty : DECIMAL
        +postpone_allowed : BOOLEAN
        +postpone_deadline : DATE
        +postpone_fee : DECIMAL
        +status : STRING
        +unreceived_qty : DECIMAL
        +package_id : STRING
        +known_at : STRING
    }
    class StockMovement {
        +movement_id : STRING 🔑
        +case_id : STRING
        +material_id : STRING
        +movement_type : STRING
        +movement_qty : DECIMAL
        +movement_date : DATE
        +evidence_status : STRING
        +known_at : STRING
    }
    class SubstitutionPermission {
        +permission_id : STRING 🔑
        +permission_type : STRING
        +material_id : STRING
        +substitute_material_id : STRING
        +project_id : STRING
        +conversion_ratio : DECIMAL
        +batch_limit_qty : DECIMAL
        +approved_usage_qty : DECIMAL
        +supply_id : STRING
        +effective_from : DATE
        +effective_to : DATE
        +approval_status : STRING
        +known_at : STRING
        +package_id : STRING
    }
    class SupplierSupplyCondition {
        +condition_id : STRING 🔑
        +supplier_id : STRING
        +material_id : STRING
        +lead_time_weeks : INTEGER
        +moq : DECIMAL
        +order_multiple : DECIMAL
        +share_ratio : DECIMAL
        +approval_status : STRING
    }
    class DataVersion {
        +version_id : STRING 🔑
        +visible_at : TIMESTAMP
        +change_summary : STRING
        +package_id : STRING
    }
    class CalculationRun {
        +run_id : STRING 🔑
        +run_type : STRING
        +package_id : STRING
        +scenario_tag : STRING
        +observed_at : TIMESTAMP
        +version_id : STRING
        +rule_version : STRING
        +evaluation_period_from : DATE
        +evaluation_period_to : DATE
    }
    class MaterialRequirement {
        +req_id : STRING 🔑
        +run_id : STRING
        +material_id : STRING
        +gross_qty : DECIMAL
        +substitute_satisfied_qty : DECIMAL
        +allocated_supply_qty : DECIMAL
        +authorized_coverage_qty : DECIMAL
        +unit_price : DECIMAL
        +remaining_material_qty : DECIMAL
        +physical_gap_qty : DECIMAL
        +pending_auth_qty : DECIMAL
        +pending_auth_amount : DECIMAL
    }
    class InspectionChange {
        +change_id : STRING 🔑
        +change_type : STRING
        +object_type : STRING
        +run_id : STRING
        +before_line_id : STRING
        +line_id : STRING
        +before_value : STRING
        +after_value : STRING
        +judgment_basis : STRING
        +impact_desc : STRING
        +known_at : STRING
    }
    class ReviewTask {
        +task_id : STRING 🔑
        +change_id : STRING
        +task_desc : STRING
        +status : STRING
        +resolution_basis : STRING
    }
    class SourcingSuggestion {
        +suggestion_id : STRING 🔑
        +run_id : STRING
        +material_id : STRING
        +supplier_id : STRING
        +list_id : STRING
        +allocated_qty : DECIMAL
        +suggested_qty : DECIMAL
        +rounding_extra_qty : DECIMAL
        +expected_arrival_date : DATE
    }
    class VendorReferenceList {
        +list_id : STRING 🔑
        +run_id : STRING
        +supplier_id : STRING
        +status : STRING
        +created_at : DATE
    }
    class PeriodSupplyBalance {
        +balance_id : STRING 🔑
        +run_id : STRING
        +material_id : STRING
        +period_label : STRING
        +beginning_qty : DECIMAL
        +arrival_qty : DECIMAL
        +other_inflow_qty : DECIMAL
        +required_qty : DECIMAL
        +demand_satisfied_qty : DECIMAL
        +other_outflow_qty : DECIMAL
        +unmet_demand_qty : DECIMAL
        +ending_qty : DECIMAL
    }
    class SlowMovingRisk {
        +risk_id : STRING 🔑
        +run_id : STRING
        +material_id : STRING
        +risk_source_type : STRING
        +ending_remaining_qty : DECIMAL
        +reserved_qty : DECIMAL
        +post_period_consumed_qty : DECIMAL
        +unit_cost : DECIMAL
        +risk_qty : DECIMAL
        +risk_amount : DECIMAL
    }
    class SolutionPlan {
        +plan_id : STRING 🔑
        +run_id : STRING
        +plan_code : STRING
        +action_type : STRING
        +po_id : STRING
        +action_qty : DECIMAL
        +action_cost : DECIMAL
        +window_risk_amount : DECIMAL
        +post_window_commitment_amount : DECIMAL
        +shortage_flag : BOOLEAN
        +feasible_flag : BOOLEAN
        +baseline_risk_qty : DECIMAL
        +intervened_risk_qty : DECIMAL
        +reducible_qty : DECIMAL
        +total_exposure_amount : DECIMAL
    }
    class HistoricalCase {
        +case_id : STRING 🔑
        +package_id : STRING
        +project_id : STRING
        +material_id : STRING
        +observation_period_from : DATE
        +observation_period_to : DATE
        +stagnant_qty : DECIMAL
        +risk_formed_date : DATE
        +decision_observed_date : DATE
        +evidence_status : STRING
        +unattributed_qty : DECIMAL
    }
    class CauseAttribution {
        +attribution_id : STRING 🔑
        +case_id : STRING
        +cause_type : STRING
        +attributed_qty : DECIMAL
        +evidence_desc : STRING
        +is_primary : BOOLEAN
    }
    class PreventionRule {
        +rule_id : STRING 🔑
        +case_id : STRING
        +rule_text : STRING
        +trigger_timing : STRING
        +status : STRING
        +close_basis : STRING
    }
    note for BomLine "【衍生】standard_usage: qty_per / base_qty"
    note for PurchaseOrder "【衍生】unreceived_qty: MAX(order_qty - cumulative_receipt_qty - cancelled_qty - closed_unreceived_qty, 0)"
    note for MaterialRequirement "【衍生】remaining_material_qty: gross_qty - substitute_satisfied_qty<br/>【衍生】physical_gap_qty: MAX(remaining_material_qty - allocated_supply_qty, 0)<br/>【衍生】pending_auth_qty: MAX(gross_qty - authorized_coverage_qty, 0)<br/>【衍生】pending_auth_amount: pending_auth_qty * unit_price"
    note for PeriodSupplyBalance "【衍生】ending_qty: beginning_qty + arrival_qty + other_inflow_qty - demand_satisfied_qty - other_outflow_qty<br/>【衍生】unmet_demand_qty: required_qty - demand_satisfied_qty"
    note for SlowMovingRisk "【衍生】risk_qty: MAX(ending_remaining_qty - reserved_qty - post_period_consumed_qty, 0)<br/>【衍生】risk_amount: risk_qty * unit_cost<br/>【触发】呆滞风险触发复核: risk_qty ＞ 0"
    note for SolutionPlan "【衍生】total_exposure_amount: window_risk_amount + post_window_commitment_amount<br/>【衍生】reducible_qty: MAX(baseline_risk_qty - intervened_risk_qty, 0)"
    note for HistoricalCase "【衍生】unattributed_qty: MAX(stagnant_qty - COALESCE(SUM(cause_attributions.attributed_qty), 0), 0)"
    note for EcnRecord "【触发】工程变更预防检查触发: approval_status == approved 且 evidence_status == complete"
    note for InspectionChange "【触发】授权数量变化重核算: change_type == auth_qty_change<br/>【触发】替代关系变化复核分配方案: change_type == substitution_change"
    note for Supply "【触发】冻结供给排除待核查: supply_type == frozen_stock"
    Material "1" --> "*" UnitConversion : 换算物料
    Material "1" --> "*" BomLine : 子项物料
    Project "1" --> "*" BomLine : 隶属项目
    Project "1" --> "*" EcnRecord : 变更项目
    Project "1" --> "*" Demand : 项目需求
    Material "1" --> "*" MaterialAuthorization : 授权物料
    Project "1" --> "*" MaterialAuthorization : 授权项目
    Material "1" --> "*" Supply : 供给物料
    PurchaseOrder "1" --> "*" Supply : 在途订单
    Material "1" --> "*" PurchaseOrder : 订购物料
    HistoricalCase "1" --> "*" StockMovement : 案例流水
    Material "1" --> "*" StockMovement : 流水物料
    Material "1" --> "*" SubstitutionPermission : 被替代物料
    Project "1" --> "*" SubstitutionPermission : 适用项目
    Supply "1" --> "*" SubstitutionPermission : 许可用供给
    Supplier "1" --> "*" SupplierSupplyCondition : 供货供应商
    Material "1" --> "*" SupplierSupplyCondition : 供货物料
    DataVersion "1" --> "*" CalculationRun : 输入版本
    CalculationRun "1" --> "*" MaterialRequirement : 所属运行
    Material "1" --> "*" MaterialRequirement : 需求物料
    CalculationRun "1" --> "*" InspectionChange : 检测运行
    BomLine "1" --> "*" InspectionChange : 变化行
    InspectionChange "1" --> "*" ReviewTask : 复核变化
    CalculationRun "1" --> "*" SourcingSuggestion : 所属运行
    Material "1" --> "*" SourcingSuggestion : 建议物料
    Supplier "1" --> "*" SourcingSuggestion : 建议供应商
    VendorReferenceList "1" --> "*" SourcingSuggestion : 汇入清单
    CalculationRun "1" --> "*" VendorReferenceList : 所属运行
    Supplier "1" --> "*" VendorReferenceList : 面向供应商
    CalculationRun "1" --> "*" PeriodSupplyBalance : 所属运行
    Material "1" --> "*" PeriodSupplyBalance : 平衡物料
    CalculationRun "1" --> "*" SlowMovingRisk : 所属运行
    Material "1" --> "*" SlowMovingRisk : 风险物料
    CalculationRun "1" --> "*" SolutionPlan : 所属运行
    PurchaseOrder "1" --> "*" SolutionPlan : 目标订单
    Project "1" --> "*" HistoricalCase : 案例项目
    Material "1" --> "*" HistoricalCase : 案例物料
    HistoricalCase "1" --> "*" CauseAttribution : 归因案例
    HistoricalCase "1" --> "*" PreventionRule : 规则来源案例
```
