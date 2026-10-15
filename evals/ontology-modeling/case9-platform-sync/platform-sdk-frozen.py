
from __future__ import annotations

import inspect
import json
import logging
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, fields as dataclass_fields
from datetime import date, datetime
from functools import wraps
import os
from typing import (
    Any,
    ClassVar,
    Generic,
    Literal,
    Protocol,
    TypeVar,
    cast,
    get_args,
    get_origin,
    get_type_hints,
)


# ---------------------------------------------------------------------------
# 实体模型（由 metadata-service 按当前工作区生成）
# ---------------------------------------------------------------------------

@dataclass
class Project:
    project_id: str | None = None
    project_code: str | None = None
    model_name: str | None = None
    stage: str | None = None
    bom_status_desc: str | None = None
    purpose_desc: str | None = None
    fields: ClassVar["ProjectFields"]
    bom_lines: ClassVar[list[BomLine]]
    ecn_records: ClassVar[list[EcnRecord]]
    demands: ClassVar[list[Demand]]
    material_authorizations: ClassVar[list[MaterialAuthorization]]
    substitution_permissions: ClassVar[list[SubstitutionPermission]]
    historical_cases: ClassVar[list[HistoricalCase]]

@dataclass
class Material:
    material_code: str | None = None
    material_name: str | None = None
    base_uom: str | None = None
    unit_cost: float | None = None
    fields: ClassVar["MaterialFields"]
    unit_conversions: ClassVar[list[UnitConversion]]
    bom_lines: ClassVar[list[BomLine]]
    material_authorizations: ClassVar[list[MaterialAuthorization]]
    supplys: ClassVar[list[Supply]]
    purchase_orders: ClassVar[list[PurchaseOrder]]
    stock_movements: ClassVar[list[StockMovement]]
    substitution_permissions: ClassVar[list[SubstitutionPermission]]
    supplier_supply_conditions: ClassVar[list[SupplierSupplyCondition]]
    material_requirements: ClassVar[list[MaterialRequirement]]
    sourcing_suggestions: ClassVar[list[SourcingSuggestion]]
    period_supply_balances: ClassVar[list[PeriodSupplyBalance]]
    slow_moving_risks: ClassVar[list[SlowMovingRisk]]
    historical_cases: ClassVar[list[HistoricalCase]]

@dataclass
class UnitConversion:
    conversion_id: str | None = None
    material_id: str | None = None
    from_uom: str | None = None
    to_uom: str | None = None
    ratio: float | None = None
    approval_status: str | None = None
    evidence_status: str | None = None
    fields: ClassVar["UnitConversionFields"]
    material: ClassVar[Material | None]

@dataclass
class Supplier:
    supplier_id: str | None = None
    supplier_name: str | None = None
    purchasing_group: str | None = None
    fields: ClassVar["SupplierFields"]
    supplier_supply_conditions: ClassVar[list[SupplierSupplyCondition]]
    sourcing_suggestions: ClassVar[list[SourcingSuggestion]]
    vendor_reference_lists: ClassVar[list[VendorReferenceList]]

@dataclass
class BomLine:
    line_id: str | None = None
    bom_type: str | None = None
    version: str | None = None
    parent_material_id: str | None = None
    material_id: str | None = None
    project_id: str | None = None
    qty_per: float | None = None
    base_qty: float | None = None
    yield_rate: float | None = None
    effective_from: date | None = None
    effective_to: date | None = None
    known_at: str | None = None
    evidence_status: str | None = None
    standard_usage: float | None = None
    fields: ClassVar["BomLineFields"]
    material: ClassVar[Material | None]
    project: ClassVar[Project | None]
    inspection_changes: ClassVar[list[InspectionChange]]

@dataclass
class EcnRecord:
    ecn_id: str | None = None
    project_id: str | None = None
    change_desc: str | None = None
    publish_date: date | None = None
    effective_date: date | None = None
    approval_status: str | None = None
    evidence_status: str | None = None
    known_at: str | None = None
    fields: ClassVar["EcnRecordFields"]
    project: ClassVar[Project | None]

@dataclass
class Demand:
    demand_id: str | None = None
    demand_version: str | None = None
    project_id: str | None = None
    need_date: date | None = None
    demand_qty: float | None = None
    source_type: str | None = None
    covered_by_demand_id: str | None = None
    status: str | None = None
    known_at: str | None = None
    package_id: str | None = None
    fields: ClassVar["DemandFields"]
    project: ClassVar[Project | None]

@dataclass
class MaterialAuthorization:
    auth_id: str | None = None
    auth_version: str | None = None
    material_id: str | None = None
    project_id: str | None = None
    covered_qty: float | None = None
    approval_status: str | None = None
    effective_from: date | None = None
    known_at: str | None = None
    package_id: str | None = None
    fields: ClassVar["MaterialAuthorizationFields"]
    material: ClassVar[Material | None]
    project: ClassVar[Project | None]

@dataclass
class Supply:
    supply_id: str | None = None
    material_id: str | None = None
    supply_type: str | None = None
    qty: float | None = None
    available_date: date | None = None
    restriction_desc: str | None = None
    po_id: str | None = None
    scenario_tag: str | None = None
    package_id: str | None = None
    known_at: str | None = None
    exclude_reason: str | None = None
    fields: ClassVar["SupplyFields"]
    material: ClassVar[Material | None]
    purchase_order: ClassVar[PurchaseOrder | None]
    substitution_permissions: ClassVar[list[SubstitutionPermission]]

@dataclass
class PurchaseOrder:
    po_id: str | None = None
    material_id: str | None = None
    order_qty: float | None = None
    cumulative_receipt_qty: float | None = None
    cancelled_qty: float | None = None
    closed_unreceived_qty: float | None = None
    confirmed_arrival_date: date | None = None
    cancel_deadline: date | None = None
    cancel_fee_per_unit: float | None = None
    cancel_limit_qty: float | None = None
    postpone_allowed: bool | None = None
    postpone_deadline: date | None = None
    postpone_fee: float | None = None
    status: str | None = None
    package_id: str | None = None
    known_at: str | None = None
    unreceived_qty: float | None = None
    fields: ClassVar["PurchaseOrderFields"]
    supplys: ClassVar[list[Supply]]
    material: ClassVar[Material | None]
    solution_plans: ClassVar[list[SolutionPlan]]

@dataclass
class StockMovement:
    movement_id: str | None = None
    case_id: str | None = None
    material_id: str | None = None
    movement_type: str | None = None
    movement_qty: float | None = None
    movement_date: date | None = None
    evidence_status: str | None = None
    known_at: str | None = None
    fields: ClassVar["StockMovementFields"]
    historical_case: ClassVar[HistoricalCase | None]
    material: ClassVar[Material | None]

@dataclass
class SubstitutionPermission:
    permission_id: str | None = None
    permission_type: str | None = None
    material_id: str | None = None
    substitute_material_id: str | None = None
    project_id: str | None = None
    conversion_ratio: float | None = None
    batch_limit_qty: float | None = None
    approved_usage_qty: float | None = None
    supply_id: str | None = None
    effective_from: date | None = None
    effective_to: date | None = None
    approval_status: str | None = None
    known_at: str | None = None
    package_id: str | None = None
    fields: ClassVar["SubstitutionPermissionFields"]
    material: ClassVar[Material | None]
    project: ClassVar[Project | None]
    supply: ClassVar[Supply | None]

@dataclass
class SupplierSupplyCondition:
    condition_id: str | None = None
    supplier_id: str | None = None
    material_id: str | None = None
    lead_time_weeks: float | None = None
    moq: float | None = None
    order_multiple: float | None = None
    share_ratio: float | None = None
    approval_status: str | None = None
    fields: ClassVar["SupplierSupplyConditionFields"]
    supplier: ClassVar[Supplier | None]
    material: ClassVar[Material | None]

@dataclass
class DataVersion:
    version_id: str | None = None
    visible_at: datetime | None = None
    change_summary: str | None = None
    package_id: str | None = None
    fields: ClassVar["DataVersionFields"]
    calculation_runs: ClassVar[list[CalculationRun]]

@dataclass
class CalculationRun:
    run_id: str | None = None
    run_type: str | None = None
    package_id: str | None = None
    scenario_tag: str | None = None
    observed_at: datetime | None = None
    version_id: str | None = None
    rule_version: str | None = None
    evaluation_period_from: date | None = None
    evaluation_period_to: date | None = None
    fields: ClassVar["CalculationRunFields"]
    data_version: ClassVar[DataVersion | None]
    material_requirements: ClassVar[list[MaterialRequirement]]
    inspection_changes: ClassVar[list[InspectionChange]]
    sourcing_suggestions: ClassVar[list[SourcingSuggestion]]
    vendor_reference_lists: ClassVar[list[VendorReferenceList]]
    period_supply_balances: ClassVar[list[PeriodSupplyBalance]]
    slow_moving_risks: ClassVar[list[SlowMovingRisk]]
    solution_plans: ClassVar[list[SolutionPlan]]

@dataclass
class MaterialRequirement:
    req_id: str | None = None
    run_id: str | None = None
    material_id: str | None = None
    gross_qty: float | None = None
    substitute_satisfied_qty: float | None = None
    allocated_supply_qty: float | None = None
    authorized_coverage_qty: float | None = None
    unit_price: float | None = None
    pending_auth_amount: float | None = None
    pending_auth_qty: float | None = None
    remaining_material_qty: float | None = None
    physical_gap_qty: float | None = None
    fields: ClassVar["MaterialRequirementFields"]
    calculation_run: ClassVar[CalculationRun | None]
    material: ClassVar[Material | None]

@dataclass
class InspectionChange:
    change_id: str | None = None
    change_type: str | None = None
    object_type: str | None = None
    run_id: str | None = None
    before_line_id: str | None = None
    line_id: str | None = None
    before_value: str | None = None
    after_value: str | None = None
    judgment_basis: str | None = None
    impact_desc: str | None = None
    known_at: str | None = None
    fields: ClassVar["InspectionChangeFields"]
    calculation_run: ClassVar[CalculationRun | None]
    bom_line: ClassVar[BomLine | None]
    review_tasks: ClassVar[list[ReviewTask]]

@dataclass
class ReviewTask:
    task_id: str | None = None
    change_id: str | None = None
    task_desc: str | None = None
    status: str | None = None
    resolution_basis: str | None = None
    fields: ClassVar["ReviewTaskFields"]
    inspection_change: ClassVar[InspectionChange | None]

@dataclass
class SourcingSuggestion:
    suggestion_id: str | None = None
    run_id: str | None = None
    material_id: str | None = None
    supplier_id: str | None = None
    list_id: str | None = None
    allocated_qty: float | None = None
    suggested_qty: float | None = None
    rounding_extra_qty: float | None = None
    expected_arrival_date: date | None = None
    fields: ClassVar["SourcingSuggestionFields"]
    calculation_run: ClassVar[CalculationRun | None]
    material: ClassVar[Material | None]
    supplier: ClassVar[Supplier | None]
    vendor_reference_list: ClassVar[VendorReferenceList | None]

@dataclass
class VendorReferenceList:
    list_id: str | None = None
    run_id: str | None = None
    supplier_id: str | None = None
    status: str | None = None
    created_at: date | None = None
    fields: ClassVar["VendorReferenceListFields"]
    sourcing_suggestions: ClassVar[list[SourcingSuggestion]]
    calculation_run: ClassVar[CalculationRun | None]
    supplier: ClassVar[Supplier | None]

@dataclass
class PeriodSupplyBalance:
    balance_id: str | None = None
    run_id: str | None = None
    material_id: str | None = None
    period_label: str | None = None
    beginning_qty: float | None = None
    arrival_qty: float | None = None
    other_inflow_qty: float | None = None
    required_qty: float | None = None
    demand_satisfied_qty: float | None = None
    other_outflow_qty: float | None = None
    ending_qty: float | None = None
    unmet_demand_qty: float | None = None
    fields: ClassVar["PeriodSupplyBalanceFields"]
    calculation_run: ClassVar[CalculationRun | None]
    material: ClassVar[Material | None]

@dataclass
class SlowMovingRisk:
    risk_id: str | None = None
    run_id: str | None = None
    material_id: str | None = None
    risk_source_type: str | None = None
    ending_remaining_qty: float | None = None
    reserved_qty: float | None = None
    post_period_consumed_qty: float | None = None
    unit_cost: float | None = None
    risk_amount: float | None = None
    risk_qty: float | None = None
    fields: ClassVar["SlowMovingRiskFields"]
    calculation_run: ClassVar[CalculationRun | None]
    material: ClassVar[Material | None]

@dataclass
class SolutionPlan:
    plan_id: str | None = None
    run_id: str | None = None
    plan_code: str | None = None
    action_type: str | None = None
    po_id: str | None = None
    action_qty: float | None = None
    action_cost: float | None = None
    window_risk_amount: float | None = None
    post_window_commitment_amount: float | None = None
    shortage_flag: bool | None = None
    feasible_flag: bool | None = None
    baseline_risk_qty: float | None = None
    intervened_risk_qty: float | None = None
    reducible_qty: float | None = None
    total_exposure_amount: float | None = None
    fields: ClassVar["SolutionPlanFields"]
    calculation_run: ClassVar[CalculationRun | None]
    purchase_order: ClassVar[PurchaseOrder | None]

@dataclass
class HistoricalCase:
    case_id: str | None = None
    package_id: str | None = None
    project_id: str | None = None
    material_id: str | None = None
    observation_period_from: date | None = None
    observation_period_to: date | None = None
    stagnant_qty: float | None = None
    risk_formed_date: date | None = None
    decision_observed_date: date | None = None
    evidence_status: str | None = None
    unattributed_qty: float | None = None
    fields: ClassVar["HistoricalCaseFields"]
    stock_movements: ClassVar[list[StockMovement]]
    project: ClassVar[Project | None]
    material: ClassVar[Material | None]
    cause_attributions: ClassVar[list[CauseAttribution]]
    prevention_rules: ClassVar[list[PreventionRule]]

@dataclass
class CauseAttribution:
    attribution_id: str | None = None
    case_id: str | None = None
    cause_type: str | None = None
    attributed_qty: float | None = None
    evidence_desc: str | None = None
    is_primary: bool | None = None
    fields: ClassVar["CauseAttributionFields"]
    historical_case: ClassVar[HistoricalCase | None]

@dataclass
class PreventionRule:
    rule_id: str | None = None
    case_id: str | None = None
    rule_text: str | None = None
    trigger_timing: str | None = None
    status: str | None = None
    close_basis: str | None = None
    fields: ClassVar["PreventionRuleFields"]
    historical_case: ClassVar[HistoricalCase | None]

# ---------------------------------------------------------------------------
# 基础返回类型
# ---------------------------------------------------------------------------


T = TypeVar("T")


@dataclass(frozen=True)
class Page(Generic[T]):
    """实体 load 接口返回的一页数据。"""

    data: list[T]
    next_page_token: str | None = None
    total_count: int | None = None


# ---------------------------------------------------------------------------
# 字段和关系元数据
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class FieldRef:
    """字段引用，用于 where、select 和排序。"""

    field_name: str

    def __repr__(self) -> str:
        return f"FieldRef({self.field_name!r})"

    def eq(self, value: Any) -> WhereExpression:
        return _Comparison("eq", self, value)

    def neq(self, value: Any) -> WhereExpression:
        return _Comparison("neq", self, value)

    def lt(self, value: Any) -> WhereExpression:
        return _Comparison("lt", self, value)

    def lte(self, value: Any) -> WhereExpression:
        return _Comparison("lte", self, value)

    def gt(self, value: Any) -> WhereExpression:
        return _Comparison("gt", self, value)

    def gte(self, value: Any) -> WhereExpression:
        return _Comparison("gte", self, value)

    def between(self, minimum: Any, maximum: Any) -> WhereExpression:
        return _Comparison("between", self, {"min": minimum, "max": maximum})

    def in_(self, values: Sequence[Any]) -> WhereExpression:
        if isinstance(values, (str, bytes)):
            raise TypeError("in_ expects a sequence of values, not a string")
        return _Comparison("in", self, list(values))

    def is_null(self) -> WhereExpression:
        return _NullCheck("isNull", self)

    def is_not_null(self) -> WhereExpression:
        return _NullCheck("isNotNull", self)

    def contains_any_term(self, value: str) -> WhereExpression:
        return _Comparison("containsAnyTerm", self, value)

    def contains_all_terms(self, value: str) -> WhereExpression:
        return _Comparison("containsAllTerms", self, value)

    def contains_all_terms_in_order(self, value: str) -> WhereExpression:
        return _Comparison("containsAllTermsInOrder", self, value)

    def asc(self) -> SortField:
        return SortField(self, "asc")

    def desc(self) -> SortField:
        return SortField(self, "desc")


class ProjectFields:
    """项目 的字段引用。"""
    project_id = FieldRef("PROP_13D08F49EA6A4CBF")
    project_code = FieldRef("PROP_C6C049E3E8284BB1")
    model_name = FieldRef("PROP_73073C2A8F1D4ACE")
    stage = FieldRef("PROP_0C8964488CE941F2")
    bom_status_desc = FieldRef("PROP_703A5B394AE3475E")
    purpose_desc = FieldRef("PROP_922AFDF595B54349")

class MaterialFields:
    """物料 的字段引用。"""
    material_code = FieldRef("PROP_4E0AA28654DB45A0")
    material_name = FieldRef("PROP_F0FA0A85510846B2")
    base_uom = FieldRef("PROP_CE3E763B36664310")
    unit_cost = FieldRef("PROP_8C56932EA5C041D9")

class UnitConversionFields:
    """单位换算 的字段引用。"""
    conversion_id = FieldRef("PROP_5D0800DE500242A8")
    material_id = FieldRef("PROP_ABFDBFF5DA4F4A1B")
    from_uom = FieldRef("PROP_454F644015774C75")
    to_uom = FieldRef("PROP_13EA4CA1A8574D9A")
    ratio = FieldRef("PROP_478C7F9AA06E4E5B")
    approval_status = FieldRef("PROP_E93CF9362DEA4075")
    evidence_status = FieldRef("PROP_54400272E663429B")

class SupplierFields:
    """供应商 的字段引用。"""
    supplier_id = FieldRef("PROP_EFE1AE77A0934EC2")
    supplier_name = FieldRef("PROP_512E3F07558348B7")
    purchasing_group = FieldRef("PROP_D961DD9A752E4E4A")

class BomLineFields:
    """BOM行 的字段引用。"""
    line_id = FieldRef("PROP_0A7AC95321F74944")
    bom_type = FieldRef("PROP_7AE324002F314105")
    version = FieldRef("PROP_66E2AB260C6647F7")
    parent_material_id = FieldRef("PROP_5796B96314CE4505")
    material_id = FieldRef("PROP_64D06C14ED334EA8")
    project_id = FieldRef("PROP_65CC8A17D36041C8")
    qty_per = FieldRef("PROP_90C1C425A2154241")
    base_qty = FieldRef("PROP_01524AB51E1E49A5")
    yield_rate = FieldRef("PROP_7B347FEA2D3C4371")
    effective_from = FieldRef("PROP_0263F37A2D2F43CA")
    effective_to = FieldRef("PROP_D08F438A579B4FAD")
    known_at = FieldRef("PROP_9B39890D04E44242")
    evidence_status = FieldRef("PROP_1F15D1C1C6E14EE1")
    standard_usage = FieldRef("PROP_6EFB69D7AF8A4E22")

class EcnRecordFields:
    """工程变更记录 的字段引用。"""
    ecn_id = FieldRef("PROP_282811E4B69947BB")
    project_id = FieldRef("PROP_E5DD7B096F0C48E6")
    change_desc = FieldRef("PROP_7F7FCA97D00D48D8")
    publish_date = FieldRef("PROP_4ED1FD51FB3B435C")
    effective_date = FieldRef("PROP_1304485EC0484A93")
    approval_status = FieldRef("PROP_4B633A0C830142C8")
    evidence_status = FieldRef("PROP_25DAE6E9AED84F35")
    known_at = FieldRef("PROP_B710B5BFD5624189")

class DemandFields:
    """需求 的字段引用。"""
    demand_id = FieldRef("PROP_3857ECE3E970496F")
    demand_version = FieldRef("PROP_8F0B130AE38C494A")
    project_id = FieldRef("PROP_D93CF875DDFC417B")
    need_date = FieldRef("PROP_D50385476A5C41F4")
    demand_qty = FieldRef("PROP_F756BF6487CB4A98")
    source_type = FieldRef("PROP_A742F63B2F6F459E")
    covered_by_demand_id = FieldRef("PROP_E63057E60D84486A")
    status = FieldRef("PROP_DA907E18216348AE")
    known_at = FieldRef("PROP_35DD57AA5A824C2A")
    package_id = FieldRef("PROP_55661E3E2D874053")

class MaterialAuthorizationFields:
    """物料授权 的字段引用。"""
    auth_id = FieldRef("PROP_CF33288A8C484B8E")
    auth_version = FieldRef("PROP_3BC1C48694634B45")
    material_id = FieldRef("PROP_9BA3863716A340A5")
    project_id = FieldRef("PROP_6812C68F40DE4A56")
    covered_qty = FieldRef("PROP_D33EC06EBA3E426C")
    approval_status = FieldRef("PROP_DC627F23914B4800")
    effective_from = FieldRef("PROP_C1B0C3250B744DBC")
    known_at = FieldRef("PROP_27A290E3164E485C")
    package_id = FieldRef("PROP_283B9391D7824ED4")

class SupplyFields:
    """供给记录 的字段引用。"""
    supply_id = FieldRef("PROP_96EE65869BF647CC")
    material_id = FieldRef("PROP_B2131DBD56C948A1")
    supply_type = FieldRef("PROP_264D5E27083140FE")
    qty = FieldRef("PROP_BF994DB902204245")
    available_date = FieldRef("PROP_99EF8F4C7BB04090")
    restriction_desc = FieldRef("PROP_09C3BD854FFA44BB")
    po_id = FieldRef("PROP_CCCCB48ED0FA4C40")
    scenario_tag = FieldRef("PROP_A3081785FACE4B29")
    package_id = FieldRef("PROP_6AB22A32F50C4438")
    known_at = FieldRef("PROP_09E88FCC30424766")
    exclude_reason = FieldRef("PROP_2469AFE9D3194B60")

class PurchaseOrderFields:
    """采购订单 的字段引用。"""
    po_id = FieldRef("PROP_81018F10C07348E5")
    material_id = FieldRef("PROP_B4B6EF80FCCE4594")
    order_qty = FieldRef("PROP_EFA8A9B2CC5A4FCE")
    cumulative_receipt_qty = FieldRef("PROP_50D24EFFACBF4C17")
    cancelled_qty = FieldRef("PROP_639037B1F7994115")
    closed_unreceived_qty = FieldRef("PROP_DD83CBB35D494DFF")
    confirmed_arrival_date = FieldRef("PROP_F8B40828293C4C9A")
    cancel_deadline = FieldRef("PROP_BAA2E4B432064F28")
    cancel_fee_per_unit = FieldRef("PROP_2881FAC2E26141BC")
    cancel_limit_qty = FieldRef("PROP_695F75A6B8744B7E")
    postpone_allowed = FieldRef("PROP_ACF4309CCFF14639")
    postpone_deadline = FieldRef("PROP_DBED6F8076F34493")
    postpone_fee = FieldRef("PROP_06DC78B04D18484C")
    status = FieldRef("PROP_A69F28EAFB134E1D")
    package_id = FieldRef("PROP_61D8021155FE414F")
    known_at = FieldRef("PROP_C354C8E1BE7F4806")
    unreceived_qty = FieldRef("PROP_DACEE76425384741")

class StockMovementFields:
    """库存流水 的字段引用。"""
    movement_id = FieldRef("PROP_F99E093E724045A8")
    case_id = FieldRef("PROP_DB8876C0014245B3")
    material_id = FieldRef("PROP_DF38E3FC5DB14EB9")
    movement_type = FieldRef("PROP_B224C37626784717")
    movement_qty = FieldRef("PROP_27212269C2D14444")
    movement_date = FieldRef("PROP_1418ABA79C854862")
    evidence_status = FieldRef("PROP_0093D758DF074FA3")
    known_at = FieldRef("PROP_4FCDFCD9E40540B3")

class SubstitutionPermissionFields:
    """替代与转用许可 的字段引用。"""
    permission_id = FieldRef("PROP_7439ED0778E24368")
    permission_type = FieldRef("PROP_D0181AD774FD47A0")
    material_id = FieldRef("PROP_D475F8CB2F2740FC")
    substitute_material_id = FieldRef("PROP_A9B609BBA2E148AD")
    project_id = FieldRef("PROP_22E3DB661E8A4285")
    conversion_ratio = FieldRef("PROP_BFA803B5E8D24C79")
    batch_limit_qty = FieldRef("PROP_BB0922B2E1BA47C5")
    approved_usage_qty = FieldRef("PROP_0C93F57137EF41FD")
    supply_id = FieldRef("PROP_2F764B70945245DA")
    effective_from = FieldRef("PROP_E012BE0124AD4F1F")
    effective_to = FieldRef("PROP_AFE8727CFB4145D2")
    approval_status = FieldRef("PROP_1FAE445724AE454D")
    known_at = FieldRef("PROP_A76BF7BDD04045B1")
    package_id = FieldRef("PROP_F23501ED79FE4D59")

class SupplierSupplyConditionFields:
    """供应商供货条件 的字段引用。"""
    condition_id = FieldRef("PROP_8592DD5B4E82411F")
    supplier_id = FieldRef("PROP_2386A6C1857F4C54")
    material_id = FieldRef("PROP_7FFF6E9E0BEC4324")
    lead_time_weeks = FieldRef("PROP_891651CFBBB548FC")
    moq = FieldRef("PROP_253040441F724F53")
    order_multiple = FieldRef("PROP_65551D083D904ECB")
    share_ratio = FieldRef("PROP_7790005CE30449C1")
    approval_status = FieldRef("PROP_64BBAA0162C24084")

class DataVersionFields:
    """数据版本 的字段引用。"""
    version_id = FieldRef("PROP_BB209579A74B4213")
    visible_at = FieldRef("PROP_45D38045058E4A1D")
    change_summary = FieldRef("PROP_12E1A6C513424D7C")
    package_id = FieldRef("PROP_8857C3F4B43F4805")

class CalculationRunFields:
    """计算运行快照 的字段引用。"""
    run_id = FieldRef("PROP_EFAF194DC8164B32")
    run_type = FieldRef("PROP_9FB10B17BC6C45DD")
    package_id = FieldRef("PROP_0E38EC9E681F4399")
    scenario_tag = FieldRef("PROP_005590F4FD884654")
    observed_at = FieldRef("PROP_B44213BDEBB54238")
    version_id = FieldRef("PROP_3C8F235ED1F946F6")
    rule_version = FieldRef("PROP_E55723030FF74523")
    evaluation_period_from = FieldRef("PROP_AB47A0F4869C4803")
    evaluation_period_to = FieldRef("PROP_74263D0ABB3F4FCC")

class MaterialRequirementFields:
    """物料需求汇总 的字段引用。"""
    req_id = FieldRef("PROP_E38C36872C304ECC")
    run_id = FieldRef("PROP_F3F035E716D64A58")
    material_id = FieldRef("PROP_665E241FD46643EA")
    gross_qty = FieldRef("PROP_44D82FAF9A2B4C14")
    substitute_satisfied_qty = FieldRef("PROP_CBAB62E7C5E34D18")
    allocated_supply_qty = FieldRef("PROP_01FFDBBA2F8B4656")
    authorized_coverage_qty = FieldRef("PROP_8FEC19A4C9C14880")
    unit_price = FieldRef("PROP_FD1A001E0BB44761")
    pending_auth_amount = FieldRef("PROP_E9C39602F8494431")
    pending_auth_qty = FieldRef("PROP_8C763E8F4FF74D36")
    remaining_material_qty = FieldRef("PROP_DC7BEF75439143CB")
    physical_gap_qty = FieldRef("PROP_A571DDB5466C49CB")

class InspectionChangeFields:
    """点检变化记录 的字段引用。"""
    change_id = FieldRef("PROP_1152CF9D4BA64097")
    change_type = FieldRef("PROP_49BB1342D1DA4D41")
    object_type = FieldRef("PROP_05FD66E4F50641E7")
    run_id = FieldRef("PROP_6BD5FB80EF234949")
    before_line_id = FieldRef("PROP_42D065BE88354A39")
    line_id = FieldRef("PROP_B8F59EB445144D96")
    before_value = FieldRef("PROP_1980CF2B55B74700")
    after_value = FieldRef("PROP_09AC6388AF1E4A80")
    judgment_basis = FieldRef("PROP_30F24CD542694504")
    impact_desc = FieldRef("PROP_32DCF55A5DE3400E")
    known_at = FieldRef("PROP_B8788B90EDA344A8")

class ReviewTaskFields:
    """复核任务 的字段引用。"""
    task_id = FieldRef("PROP_9FA7EAE068F94B36")
    change_id = FieldRef("PROP_DAD3D9B956F5485C")
    task_desc = FieldRef("PROP_FD4D8DAD9AD246AE")
    status = FieldRef("PROP_24CB9318D55A4E77")
    resolution_basis = FieldRef("PROP_46C0ECBA9C294757")

class SourcingSuggestionFields:
    """策备建议 的字段引用。"""
    suggestion_id = FieldRef("PROP_E2A22291D8574287")
    run_id = FieldRef("PROP_305E69F0D3544D61")
    material_id = FieldRef("PROP_90ABF1B2A1BF4323")
    supplier_id = FieldRef("PROP_A207537F1E284DE5")
    list_id = FieldRef("PROP_1C7D675D23AD4667")
    allocated_qty = FieldRef("PROP_CD5444ACCD994192")
    suggested_qty = FieldRef("PROP_E3A32F72470142EA")
    rounding_extra_qty = FieldRef("PROP_C5BFBBF365A8425B")
    expected_arrival_date = FieldRef("PROP_CE72A95462FB4068")

class VendorReferenceListFields:
    """供应商参考清单 的字段引用。"""
    list_id = FieldRef("PROP_BD89D4B6198D4725")
    run_id = FieldRef("PROP_7F2453DB16CC482D")
    supplier_id = FieldRef("PROP_6368F1F8E72F42B3")
    status = FieldRef("PROP_1C4C3C31C4B5449A")
    created_at = FieldRef("PROP_100B05590C5A496C")

class PeriodSupplyBalanceFields:
    """分期供需 的字段引用。"""
    balance_id = FieldRef("PROP_D51296C639814B1A")
    run_id = FieldRef("PROP_C283B97D90F443B0")
    material_id = FieldRef("PROP_8602B8BB6CC24505")
    period_label = FieldRef("PROP_6D80824A2B054524")
    beginning_qty = FieldRef("PROP_FF16056604B046E9")
    arrival_qty = FieldRef("PROP_FDDA20CAF6064CDF")
    other_inflow_qty = FieldRef("PROP_A11AE465AD784F3E")
    required_qty = FieldRef("PROP_334B49E36B3646BA")
    demand_satisfied_qty = FieldRef("PROP_CC434E5A290E4C5F")
    other_outflow_qty = FieldRef("PROP_AD32917D4D8C40FC")
    ending_qty = FieldRef("PROP_9849088EE3EA40D9")
    unmet_demand_qty = FieldRef("PROP_ED2224DCB96F41CC")

class SlowMovingRiskFields:
    """呆滞风险 的字段引用。"""
    risk_id = FieldRef("PROP_CC10307DC4944E61")
    run_id = FieldRef("PROP_9FBF30298ACA4462")
    material_id = FieldRef("PROP_5FB348BD43674668")
    risk_source_type = FieldRef("PROP_A03AB7F22B2E470F")
    ending_remaining_qty = FieldRef("PROP_78CA7D658511413C")
    reserved_qty = FieldRef("PROP_AC773BA2F84A425B")
    post_period_consumed_qty = FieldRef("PROP_48F3621DDD394A93")
    unit_cost = FieldRef("PROP_97FEBA21DBF24965")
    risk_amount = FieldRef("PROP_DA1D97363BEC4DEC")
    risk_qty = FieldRef("PROP_DAF99EEC6DDF49FF")

class SolutionPlanFields:
    """处理方案 的字段引用。"""
    plan_id = FieldRef("PROP_2BB6F36BE07D4C36")
    run_id = FieldRef("PROP_EF23DBC3A4264CD5")
    plan_code = FieldRef("PROP_72379326F14F4530")
    action_type = FieldRef("PROP_4DCA6A6F665D43B0")
    po_id = FieldRef("PROP_4FDC275F673E487A")
    action_qty = FieldRef("PROP_636D098C2DCD48C7")
    action_cost = FieldRef("PROP_65F53AA5D8B746C4")
    window_risk_amount = FieldRef("PROP_D2DEFB7933E941AE")
    post_window_commitment_amount = FieldRef("PROP_FCB219E5B0394D03")
    shortage_flag = FieldRef("PROP_013BBFA05C93467A")
    feasible_flag = FieldRef("PROP_27F9A20961ED4616")
    baseline_risk_qty = FieldRef("PROP_42DABDE986C24A52")
    intervened_risk_qty = FieldRef("PROP_44CFE61EA68F48DC")
    reducible_qty = FieldRef("PROP_EB636D5225A441BB")
    total_exposure_amount = FieldRef("PROP_2198EA33307F4024")

class HistoricalCaseFields:
    """历史呆滞案例 的字段引用。"""
    case_id = FieldRef("PROP_7967ECFC3DCE4FB0")
    package_id = FieldRef("PROP_042E36A3D9624028")
    project_id = FieldRef("PROP_2655D290CF4549E3")
    material_id = FieldRef("PROP_9CC2E5AB5D9C402F")
    observation_period_from = FieldRef("PROP_076FB29BCF2D4239")
    observation_period_to = FieldRef("PROP_A0BA57FAE3AC4480")
    stagnant_qty = FieldRef("PROP_5255E60F44394B23")
    risk_formed_date = FieldRef("PROP_A8690816DFA84D0F")
    decision_observed_date = FieldRef("PROP_0124E60641374434")
    evidence_status = FieldRef("PROP_67352CB6BBEF4249")
    unattributed_qty = FieldRef("PROP_84AEED0A7F3E4CB0")

class CauseAttributionFields:
    """原因归因 的字段引用。"""
    attribution_id = FieldRef("PROP_A20AC877089D42A8")
    case_id = FieldRef("PROP_0F4A27C63CBF43F6")
    cause_type = FieldRef("PROP_B57F9A248CDC4E2D")
    attributed_qty = FieldRef("PROP_929A97673FEE44C5")
    evidence_desc = FieldRef("PROP_4A3E4D4BA846466E")
    is_primary = FieldRef("PROP_7805925C3BB24164")

class PreventionRuleFields:
    """预防规则 的字段引用。"""
    rule_id = FieldRef("PROP_3DE66BAAE3AA4E0F")
    case_id = FieldRef("PROP_1484C134C5D648E1")
    rule_text = FieldRef("PROP_77B03E7ABBFE40F9")
    trigger_timing = FieldRef("PROP_EFB586612B5C48CA")
    status = FieldRef("PROP_2399351610084AE7")
    close_basis = FieldRef("PROP_ECEFE0DE7B6B4949")

Project.fields = ProjectFields()
Material.fields = MaterialFields()
UnitConversion.fields = UnitConversionFields()
Supplier.fields = SupplierFields()
BomLine.fields = BomLineFields()
EcnRecord.fields = EcnRecordFields()
Demand.fields = DemandFields()
MaterialAuthorization.fields = MaterialAuthorizationFields()
Supply.fields = SupplyFields()
PurchaseOrder.fields = PurchaseOrderFields()
StockMovement.fields = StockMovementFields()
SubstitutionPermission.fields = SubstitutionPermissionFields()
SupplierSupplyCondition.fields = SupplierSupplyConditionFields()
DataVersion.fields = DataVersionFields()
CalculationRun.fields = CalculationRunFields()
MaterialRequirement.fields = MaterialRequirementFields()
InspectionChange.fields = InspectionChangeFields()
ReviewTask.fields = ReviewTaskFields()
SourcingSuggestion.fields = SourcingSuggestionFields()
VendorReferenceList.fields = VendorReferenceListFields()
PeriodSupplyBalance.fields = PeriodSupplyBalanceFields()
SlowMovingRisk.fields = SlowMovingRiskFields()
SolutionPlan.fields = SolutionPlanFields()
HistoricalCase.fields = HistoricalCaseFields()
CauseAttribution.fields = CauseAttributionFields()
PreventionRule.fields = PreventionRuleFields()

@dataclass(frozen=True)
class _ObjectDefinition:
    """一个实体的对象类型 code、Python 模型和主键等生成元数据。"""

    entity_name: str
    object_code: str
    model_type: type[Any]
    primary_key_field: str
    fields_by_name: Mapping[str, FieldRef]


def _make_definition(
    entity_name: str,
    object_code: str,
    model_type: type[Any],
    primary_key_field: str,
) -> _ObjectDefinition:
    """从 dataclass 和公开的 ``fields`` 字段引用生成实体定义。"""

    names = {field.name for field in dataclass_fields(model_type)}
    fields_by_name = {
        name: cast(FieldRef, getattr(model_type.fields, name))
        for name in names
    }
    return _ObjectDefinition(
        entity_name=entity_name,
        object_code=object_code,
        model_type=model_type,
        primary_key_field=primary_key_field,
        fields_by_name=fields_by_name,
    )



OBJECT_DEFINITIONS: dict[str, _ObjectDefinition] = {
    "Project": _make_definition(
        "Project", "OBJ_4822EC27478B4BAE", Project, "project_id"
    ),
    "Material": _make_definition(
        "Material", "OBJ_D91FF14456814417", Material, "material_code"
    ),
    "UnitConversion": _make_definition(
        "UnitConversion", "OBJ_67C51920EAA148F0", UnitConversion, "conversion_id"
    ),
    "Supplier": _make_definition(
        "Supplier", "OBJ_48052765529C47D6", Supplier, "supplier_id"
    ),
    "BomLine": _make_definition(
        "BomLine", "OBJ_E461AAED451342E3", BomLine, "line_id"
    ),
    "EcnRecord": _make_definition(
        "EcnRecord", "OBJ_8E63675B29A44327", EcnRecord, "ecn_id"
    ),
    "Demand": _make_definition(
        "Demand", "OBJ_1202002A7A114138", Demand, "demand_id"
    ),
    "MaterialAuthorization": _make_definition(
        "MaterialAuthorization", "OBJ_F3EF06BE4B344F3F", MaterialAuthorization, "auth_id"
    ),
    "Supply": _make_definition(
        "Supply", "OBJ_D8D4FCE5780948A1", Supply, "supply_id"
    ),
    "PurchaseOrder": _make_definition(
        "PurchaseOrder", "OBJ_5CF38E887F774893", PurchaseOrder, "po_id"
    ),
    "StockMovement": _make_definition(
        "StockMovement", "OBJ_424687970CF0433B", StockMovement, "movement_id"
    ),
    "SubstitutionPermission": _make_definition(
        "SubstitutionPermission", "OBJ_1DDAD533A18042D7", SubstitutionPermission, "permission_id"
    ),
    "SupplierSupplyCondition": _make_definition(
        "SupplierSupplyCondition", "OBJ_98E46094292B4EE5", SupplierSupplyCondition, "condition_id"
    ),
    "DataVersion": _make_definition(
        "DataVersion", "OBJ_D3B0008D87B94F5D", DataVersion, "version_id"
    ),
    "CalculationRun": _make_definition(
        "CalculationRun", "OBJ_895556E51C504FBD", CalculationRun, "run_id"
    ),
    "MaterialRequirement": _make_definition(
        "MaterialRequirement", "OBJ_5663B8C01F3440C0", MaterialRequirement, "req_id"
    ),
    "InspectionChange": _make_definition(
        "InspectionChange", "OBJ_003FB220F9774B02", InspectionChange, "change_id"
    ),
    "ReviewTask": _make_definition(
        "ReviewTask", "OBJ_BA8F972519E14FF5", ReviewTask, "task_id"
    ),
    "SourcingSuggestion": _make_definition(
        "SourcingSuggestion", "OBJ_FBAA5C12D8364C86", SourcingSuggestion, "suggestion_id"
    ),
    "VendorReferenceList": _make_definition(
        "VendorReferenceList", "OBJ_1F5C4D1D89404A24", VendorReferenceList, "list_id"
    ),
    "PeriodSupplyBalance": _make_definition(
        "PeriodSupplyBalance", "OBJ_D753BE2257EE41CD", PeriodSupplyBalance, "balance_id"
    ),
    "SlowMovingRisk": _make_definition(
        "SlowMovingRisk", "OBJ_7FBB5F19B27C4736", SlowMovingRisk, "risk_id"
    ),
    "SolutionPlan": _make_definition(
        "SolutionPlan", "OBJ_865F49108279435C", SolutionPlan, "plan_id"
    ),
    "HistoricalCase": _make_definition(
        "HistoricalCase", "OBJ_3A010E889D2E4395", HistoricalCase, "case_id"
    ),
    "CauseAttribution": _make_definition(
        "CauseAttribution", "OBJ_6B3B61DB4E3046D3", CauseAttribution, "attribution_id"
    ),
    "PreventionRule": _make_definition(
        "PreventionRule", "OBJ_45DD9D839D2444A1", PreventionRule, "rule_id"
    ),
}

OBJECT_DEFINITIONS_BY_CODE: dict[str, _ObjectDefinition] = {
    definition.object_code: definition
    for definition in OBJECT_DEFINITIONS.values()
}

@dataclass(frozen=True)
class RelationDefinition:
    """一个对象关系及其正反向访问名称。"""

    code: str
    source_object: str
    source_field: str
    target_object: str
    target_field: str
    cardinality: Cardinality
    source_name: str
    target_name: str

    def returns_many(self, side: Literal["source", "target"]) -> bool:
        """判断从关系一端访问另一端时是否返回列表。"""

        return (
            self.cardinality == "N:N"
            or (self.cardinality == "1:N" and side == "source")
            or (self.cardinality == "N:1" and side == "target")
        )


Cardinality = Literal["1:1", "1:N", "N:1", "N:N"]

RELATION_DEFINITIONS: dict[str, RelationDefinition] = {
    "rel_8ba0301e": RelationDefinition(
        code="rel_8ba0301e",
        source_object="Material",
        source_field="PROP_4E0AA28654DB45A0",
        target_object="UnitConversion",
        target_field="PROP_ABFDBFF5DA4F4A1B",
        cardinality="1:N",
        source_name="unit_conversions",
        target_name="material",
    ),
    "rel_04711ef7": RelationDefinition(
        code="rel_04711ef7",
        source_object="Material",
        source_field="PROP_4E0AA28654DB45A0",
        target_object="BomLine",
        target_field="PROP_64D06C14ED334EA8",
        cardinality="1:N",
        source_name="bom_lines",
        target_name="material",
    ),
    "rel_336fff57": RelationDefinition(
        code="rel_336fff57",
        source_object="Project",
        source_field="PROP_13D08F49EA6A4CBF",
        target_object="BomLine",
        target_field="PROP_65CC8A17D36041C8",
        cardinality="1:N",
        source_name="bom_lines",
        target_name="project",
    ),
    "rel_1b9e39f9": RelationDefinition(
        code="rel_1b9e39f9",
        source_object="Project",
        source_field="PROP_13D08F49EA6A4CBF",
        target_object="EcnRecord",
        target_field="PROP_E5DD7B096F0C48E6",
        cardinality="1:N",
        source_name="ecn_records",
        target_name="project",
    ),
    "rel_e5935086": RelationDefinition(
        code="rel_e5935086",
        source_object="Project",
        source_field="PROP_13D08F49EA6A4CBF",
        target_object="Demand",
        target_field="PROP_D93CF875DDFC417B",
        cardinality="1:N",
        source_name="demands",
        target_name="project",
    ),
    "rel_c9e4445e": RelationDefinition(
        code="rel_c9e4445e",
        source_object="Material",
        source_field="PROP_4E0AA28654DB45A0",
        target_object="MaterialAuthorization",
        target_field="PROP_9BA3863716A340A5",
        cardinality="1:N",
        source_name="material_authorizations",
        target_name="material",
    ),
    "rel_a7afb4d2": RelationDefinition(
        code="rel_a7afb4d2",
        source_object="Project",
        source_field="PROP_13D08F49EA6A4CBF",
        target_object="MaterialAuthorization",
        target_field="PROP_6812C68F40DE4A56",
        cardinality="1:N",
        source_name="material_authorizations",
        target_name="project",
    ),
    "rel_66f6753b": RelationDefinition(
        code="rel_66f6753b",
        source_object="Material",
        source_field="PROP_4E0AA28654DB45A0",
        target_object="Supply",
        target_field="PROP_B2131DBD56C948A1",
        cardinality="1:N",
        source_name="supplys",
        target_name="material",
    ),
    "rel_2c63fa8f": RelationDefinition(
        code="rel_2c63fa8f",
        source_object="PurchaseOrder",
        source_field="PROP_81018F10C07348E5",
        target_object="Supply",
        target_field="PROP_CCCCB48ED0FA4C40",
        cardinality="1:N",
        source_name="supplys",
        target_name="purchase_order",
    ),
    "rel_643985e8": RelationDefinition(
        code="rel_643985e8",
        source_object="Material",
        source_field="PROP_4E0AA28654DB45A0",
        target_object="PurchaseOrder",
        target_field="PROP_B4B6EF80FCCE4594",
        cardinality="1:N",
        source_name="purchase_orders",
        target_name="material",
    ),
    "rel_e1e213ce": RelationDefinition(
        code="rel_e1e213ce",
        source_object="HistoricalCase",
        source_field="PROP_7967ECFC3DCE4FB0",
        target_object="StockMovement",
        target_field="PROP_DB8876C0014245B3",
        cardinality="1:N",
        source_name="stock_movements",
        target_name="historical_case",
    ),
    "rel_cc00f36e": RelationDefinition(
        code="rel_cc00f36e",
        source_object="Material",
        source_field="PROP_4E0AA28654DB45A0",
        target_object="StockMovement",
        target_field="PROP_DF38E3FC5DB14EB9",
        cardinality="1:N",
        source_name="stock_movements",
        target_name="material",
    ),
    "rel_0f491122": RelationDefinition(
        code="rel_0f491122",
        source_object="Material",
        source_field="PROP_4E0AA28654DB45A0",
        target_object="SubstitutionPermission",
        target_field="PROP_D475F8CB2F2740FC",
        cardinality="1:N",
        source_name="substitution_permissions",
        target_name="material",
    ),
    "rel_3cddf3f1": RelationDefinition(
        code="rel_3cddf3f1",
        source_object="Project",
        source_field="PROP_13D08F49EA6A4CBF",
        target_object="SubstitutionPermission",
        target_field="PROP_22E3DB661E8A4285",
        cardinality="1:N",
        source_name="substitution_permissions",
        target_name="project",
    ),
    "rel_5e1dc2d0": RelationDefinition(
        code="rel_5e1dc2d0",
        source_object="Supply",
        source_field="PROP_96EE65869BF647CC",
        target_object="SubstitutionPermission",
        target_field="PROP_2F764B70945245DA",
        cardinality="1:N",
        source_name="substitution_permissions",
        target_name="supply",
    ),
    "rel_bad3c217": RelationDefinition(
        code="rel_bad3c217",
        source_object="Supplier",
        source_field="PROP_EFE1AE77A0934EC2",
        target_object="SupplierSupplyCondition",
        target_field="PROP_2386A6C1857F4C54",
        cardinality="1:N",
        source_name="supplier_supply_conditions",
        target_name="supplier",
    ),
    "rel_2f9f9c78": RelationDefinition(
        code="rel_2f9f9c78",
        source_object="Material",
        source_field="PROP_4E0AA28654DB45A0",
        target_object="SupplierSupplyCondition",
        target_field="PROP_7FFF6E9E0BEC4324",
        cardinality="1:N",
        source_name="supplier_supply_conditions",
        target_name="material",
    ),
    "rel_783ee3df": RelationDefinition(
        code="rel_783ee3df",
        source_object="DataVersion",
        source_field="PROP_BB209579A74B4213",
        target_object="CalculationRun",
        target_field="PROP_3C8F235ED1F946F6",
        cardinality="1:N",
        source_name="calculation_runs",
        target_name="data_version",
    ),
    "rel_13993c79": RelationDefinition(
        code="rel_13993c79",
        source_object="CalculationRun",
        source_field="PROP_EFAF194DC8164B32",
        target_object="MaterialRequirement",
        target_field="PROP_F3F035E716D64A58",
        cardinality="1:N",
        source_name="material_requirements",
        target_name="calculation_run",
    ),
    "rel_f797c76f": RelationDefinition(
        code="rel_f797c76f",
        source_object="Material",
        source_field="PROP_4E0AA28654DB45A0",
        target_object="MaterialRequirement",
        target_field="PROP_665E241FD46643EA",
        cardinality="1:N",
        source_name="material_requirements",
        target_name="material",
    ),
    "rel_d4e5bdd9": RelationDefinition(
        code="rel_d4e5bdd9",
        source_object="CalculationRun",
        source_field="PROP_EFAF194DC8164B32",
        target_object="InspectionChange",
        target_field="PROP_6BD5FB80EF234949",
        cardinality="1:N",
        source_name="inspection_changes",
        target_name="calculation_run",
    ),
    "rel_4f36cf0d": RelationDefinition(
        code="rel_4f36cf0d",
        source_object="BomLine",
        source_field="PROP_0A7AC95321F74944",
        target_object="InspectionChange",
        target_field="PROP_B8F59EB445144D96",
        cardinality="1:N",
        source_name="inspection_changes",
        target_name="bom_line",
    ),
    "rel_d8ceb2d7": RelationDefinition(
        code="rel_d8ceb2d7",
        source_object="InspectionChange",
        source_field="PROP_1152CF9D4BA64097",
        target_object="ReviewTask",
        target_field="PROP_DAD3D9B956F5485C",
        cardinality="1:N",
        source_name="review_tasks",
        target_name="inspection_change",
    ),
    "rel_7b7433f2": RelationDefinition(
        code="rel_7b7433f2",
        source_object="CalculationRun",
        source_field="PROP_EFAF194DC8164B32",
        target_object="SourcingSuggestion",
        target_field="PROP_305E69F0D3544D61",
        cardinality="1:N",
        source_name="sourcing_suggestions",
        target_name="calculation_run",
    ),
    "rel_c9bd6ea6": RelationDefinition(
        code="rel_c9bd6ea6",
        source_object="Material",
        source_field="PROP_4E0AA28654DB45A0",
        target_object="SourcingSuggestion",
        target_field="PROP_90ABF1B2A1BF4323",
        cardinality="1:N",
        source_name="sourcing_suggestions",
        target_name="material",
    ),
    "rel_fce2d407": RelationDefinition(
        code="rel_fce2d407",
        source_object="Supplier",
        source_field="PROP_EFE1AE77A0934EC2",
        target_object="SourcingSuggestion",
        target_field="PROP_A207537F1E284DE5",
        cardinality="1:N",
        source_name="sourcing_suggestions",
        target_name="supplier",
    ),
    "rel_35f2e654": RelationDefinition(
        code="rel_35f2e654",
        source_object="VendorReferenceList",
        source_field="PROP_BD89D4B6198D4725",
        target_object="SourcingSuggestion",
        target_field="PROP_1C7D675D23AD4667",
        cardinality="1:N",
        source_name="sourcing_suggestions",
        target_name="vendor_reference_list",
    ),
    "rel_1b2d54e4": RelationDefinition(
        code="rel_1b2d54e4",
        source_object="CalculationRun",
        source_field="PROP_EFAF194DC8164B32",
        target_object="VendorReferenceList",
        target_field="PROP_7F2453DB16CC482D",
        cardinality="1:N",
        source_name="vendor_reference_lists",
        target_name="calculation_run",
    ),
    "rel_78c8eda5": RelationDefinition(
        code="rel_78c8eda5",
        source_object="Supplier",
        source_field="PROP_EFE1AE77A0934EC2",
        target_object="VendorReferenceList",
        target_field="PROP_6368F1F8E72F42B3",
        cardinality="1:N",
        source_name="vendor_reference_lists",
        target_name="supplier",
    ),
    "rel_22e3127a": RelationDefinition(
        code="rel_22e3127a",
        source_object="CalculationRun",
        source_field="PROP_EFAF194DC8164B32",
        target_object="PeriodSupplyBalance",
        target_field="PROP_C283B97D90F443B0",
        cardinality="1:N",
        source_name="period_supply_balances",
        target_name="calculation_run",
    ),
    "rel_035efff8": RelationDefinition(
        code="rel_035efff8",
        source_object="Material",
        source_field="PROP_4E0AA28654DB45A0",
        target_object="PeriodSupplyBalance",
        target_field="PROP_8602B8BB6CC24505",
        cardinality="1:N",
        source_name="period_supply_balances",
        target_name="material",
    ),
    "rel_819d4e00": RelationDefinition(
        code="rel_819d4e00",
        source_object="CalculationRun",
        source_field="PROP_EFAF194DC8164B32",
        target_object="SlowMovingRisk",
        target_field="PROP_9FBF30298ACA4462",
        cardinality="1:N",
        source_name="slow_moving_risks",
        target_name="calculation_run",
    ),
    "rel_26ba6628": RelationDefinition(
        code="rel_26ba6628",
        source_object="Material",
        source_field="PROP_4E0AA28654DB45A0",
        target_object="SlowMovingRisk",
        target_field="PROP_5FB348BD43674668",
        cardinality="1:N",
        source_name="slow_moving_risks",
        target_name="material",
    ),
    "rel_e3cf2a48": RelationDefinition(
        code="rel_e3cf2a48",
        source_object="CalculationRun",
        source_field="PROP_EFAF194DC8164B32",
        target_object="SolutionPlan",
        target_field="PROP_EF23DBC3A4264CD5",
        cardinality="1:N",
        source_name="solution_plans",
        target_name="calculation_run",
    ),
    "rel_48f28f78": RelationDefinition(
        code="rel_48f28f78",
        source_object="PurchaseOrder",
        source_field="PROP_81018F10C07348E5",
        target_object="SolutionPlan",
        target_field="PROP_4FDC275F673E487A",
        cardinality="1:N",
        source_name="solution_plans",
        target_name="purchase_order",
    ),
    "rel_c78e07d7": RelationDefinition(
        code="rel_c78e07d7",
        source_object="Project",
        source_field="PROP_13D08F49EA6A4CBF",
        target_object="HistoricalCase",
        target_field="PROP_2655D290CF4549E3",
        cardinality="1:N",
        source_name="historical_cases",
        target_name="project",
    ),
    "rel_57c56235": RelationDefinition(
        code="rel_57c56235",
        source_object="Material",
        source_field="PROP_4E0AA28654DB45A0",
        target_object="HistoricalCase",
        target_field="PROP_9CC2E5AB5D9C402F",
        cardinality="1:N",
        source_name="historical_cases",
        target_name="material",
    ),
    "rel_0f255887": RelationDefinition(
        code="rel_0f255887",
        source_object="HistoricalCase",
        source_field="PROP_7967ECFC3DCE4FB0",
        target_object="CauseAttribution",
        target_field="PROP_0F4A27C63CBF43F6",
        cardinality="1:N",
        source_name="cause_attributions",
        target_name="historical_case",
    ),
    "rel_de692b23": RelationDefinition(
        code="rel_de692b23",
        source_object="HistoricalCase",
        source_field="PROP_7967ECFC3DCE4FB0",
        target_object="PreventionRule",
        target_field="PROP_1484C134C5D648E1",
        cardinality="1:N",
        source_name="prevention_rules",
        target_name="historical_case",
    ),
}

LINK_REL_8BA0301E = "rel_8ba0301e"
LINK_REL_04711EF7 = "rel_04711ef7"
LINK_REL_336FFF57 = "rel_336fff57"
LINK_REL_1B9E39F9 = "rel_1b9e39f9"
LINK_REL_E5935086 = "rel_e5935086"
LINK_REL_C9E4445E = "rel_c9e4445e"
LINK_REL_A7AFB4D2 = "rel_a7afb4d2"
LINK_REL_66F6753B = "rel_66f6753b"
LINK_REL_2C63FA8F = "rel_2c63fa8f"
LINK_REL_643985E8 = "rel_643985e8"
LINK_REL_E1E213CE = "rel_e1e213ce"
LINK_REL_CC00F36E = "rel_cc00f36e"
LINK_REL_0F491122 = "rel_0f491122"
LINK_REL_3CDDF3F1 = "rel_3cddf3f1"
LINK_REL_5E1DC2D0 = "rel_5e1dc2d0"
LINK_REL_BAD3C217 = "rel_bad3c217"
LINK_REL_2F9F9C78 = "rel_2f9f9c78"
LINK_REL_783EE3DF = "rel_783ee3df"
LINK_REL_13993C79 = "rel_13993c79"
LINK_REL_F797C76F = "rel_f797c76f"
LINK_REL_D4E5BDD9 = "rel_d4e5bdd9"
LINK_REL_4F36CF0D = "rel_4f36cf0d"
LINK_REL_D8CEB2D7 = "rel_d8ceb2d7"
LINK_REL_7B7433F2 = "rel_7b7433f2"
LINK_REL_C9BD6EA6 = "rel_c9bd6ea6"
LINK_REL_FCE2D407 = "rel_fce2d407"
LINK_REL_35F2E654 = "rel_35f2e654"
LINK_REL_1B2D54E4 = "rel_1b2d54e4"
LINK_REL_78C8EDA5 = "rel_78c8eda5"
LINK_REL_22E3127A = "rel_22e3127a"
LINK_REL_035EFFF8 = "rel_035efff8"
LINK_REL_819D4E00 = "rel_819d4e00"
LINK_REL_26BA6628 = "rel_26ba6628"
LINK_REL_E3CF2A48 = "rel_e3cf2a48"
LINK_REL_48F28F78 = "rel_48f28f78"
LINK_REL_C78E07D7 = "rel_c78e07d7"
LINK_REL_57C56235 = "rel_57c56235"
LINK_REL_0F255887 = "rel_0f255887"
LINK_REL_DE692B23 = "rel_de692b23"

class _RelationAccessor:
    """在实体实例上按点号访问关联对象。"""

    def __init__(
        self,
        relation: RelationDefinition,
        side: Literal["source", "target"],
    ) -> None:
        self._relation = relation
        self._side = side

    def __get__(self, instance: Any, owner: type[Any] | None = None) -> Any:
        if instance is None:
            return self
        client = getattr(instance, "_dataservice_client", None)
        if client is None:
            raise RuntimeError(
                "related objects are available only on objects loaded by WorkspaceClient"
            )

        owner_object = (
            self._relation.source_object
            if self._side == "source"
            else self._relation.target_object
        )
        owner_definition = OBJECT_DEFINITIONS[owner_object]
        primary_key = getattr(instance, owner_definition.primary_key_field, None)
        if primary_key is None:
            return [] if self._relation.returns_many(self._side) else None

        related = (
            EntityEndpoint(client, owner_definition)
            .static([str(primary_key)])
            .search_around(self._relation.code)
            .load()
            .data
        )
        if self._relation.returns_many(self._side):
            return related
        if len(related) > 1:
            raise DataServiceError(
                f"relation {self._relation.code} expected one related object"
            )
        return related[0] if related else None


for _relation in RELATION_DEFINITIONS.values():
    _source_definition = OBJECT_DEFINITIONS[_relation.source_object]
    _target_definition = OBJECT_DEFINITIONS[_relation.target_object]
    setattr(
        _source_definition.model_type,
        _relation.source_name,
        _RelationAccessor(_relation, "source"),
    )
    setattr(
        _target_definition.model_type,
        _relation.target_name,
        _RelationAccessor(_relation, "target"),
    )


# ---------------------------------------------------------------------------
# ObjectSet 和 where 表达式（新增的标准查询能力）
# ---------------------------------------------------------------------------


class WhereExpression:
    """标准 ObjectSet ``where`` 表达式的基类。"""

    def to_dict(self) -> dict[str, Any]:
        raise NotImplementedError

    def __and__(self, other: WhereExpression) -> WhereExpression:
        return _Logical("and", [self, other])

    def __or__(self, other: WhereExpression) -> WhereExpression:
        return _Logical("or", [self, other])

    def __invert__(self) -> WhereExpression:
        return _Not(self)

    def and_(self, *others: WhereExpression) -> WhereExpression:
        """用显式方法连接条件，避免依赖 Python 的 ``&`` 运算符。"""

        return and_(self, *others)

    def or_(self, *others: WhereExpression) -> WhereExpression:
        """用显式方法连接条件，避免依赖 Python 的 ``|`` 运算符。"""

        return or_(self, *others)

    def not_(self) -> WhereExpression:
        """返回当前条件的逻辑否定。"""

        return _Not(self)

    def __bool__(self) -> bool:
        raise TypeError("ObjectSet where expressions cannot be used as booleans")


@dataclass(frozen=True)
class _Comparison(WhereExpression):
    operator: str
    field: FieldRef
    value: Any

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": self.operator,
            "field": self.field.field_name,
            "value": self.value,
        }


@dataclass(frozen=True)
class _NullCheck(WhereExpression):
    operator: str
    field: FieldRef

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": self.operator,
            "field": self.field.field_name,
        }


@dataclass(frozen=True)
class _Logical(WhereExpression):
    operator: str
    children: Sequence[WhereExpression]

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": self.operator,
            "children": [child.to_dict() for child in self.children],
        }


@dataclass(frozen=True)
class _Not(WhereExpression):
    child: WhereExpression

    def to_dict(self) -> dict[str, Any]:
        return {"type": "not", "child": self.child.to_dict()}


@dataclass(frozen=True)
class SortField:
    field: FieldRef
    direction: Literal["asc", "desc"] = "asc"

    def to_dict(self) -> dict[str, str]:
        return {
            "field": self.field.field_name,
            "direction": self.direction,
        }


def _as_where(value: WhereExpression | Mapping[str, Any]) -> dict[str, Any]:
    """将类型化条件或原始 JSON 条件统一转换为请求字典。"""

    if isinstance(value, WhereExpression):
        return value.to_dict()
    if isinstance(value, Mapping):
        return dict(value)
    raise TypeError("where must be a WhereExpression or an ObjectSet where object")


def and_(*expressions: WhereExpression) -> WhereExpression:
    """显式构造 ``and`` 条件；名称末尾的下划线是 Python 关键字约束。"""

    if not expressions:
        raise ValueError("and_ requires at least one expression")
    if not all(isinstance(expression, WhereExpression) for expression in expressions):
        raise TypeError("and_ arguments must be WhereExpression instances")
    return _Logical("and", list(expressions))


def or_(*expressions: WhereExpression) -> WhereExpression:
    """显式构造 ``or`` 条件；名称末尾的下划线是 Python 关键字约束。"""

    if not expressions:
        raise ValueError("or_ requires at least one expression")
    if not all(isinstance(expression, WhereExpression) for expression in expressions):
        raise TypeError("or_ arguments must be WhereExpression instances")
    return _Logical("or", list(expressions))


def not_(expression: WhereExpression) -> WhereExpression:
    """显式构造 ``not`` 条件。"""

    if not isinstance(expression, WhereExpression):
        raise TypeError("not_ argument must be a WhereExpression instance")
    return _Not(expression)


def _field_for(
    definition: _ObjectDefinition | None, value: FieldRef | str
) -> FieldRef:
    """解析字段引用；关系跳转结果尚未加载时允许原始字段名。"""

    if isinstance(value, FieldRef):
        if definition is None:
            return value
        if value in definition.fields_by_name.values():
            return value
        field_name = value.field_name
    else:
        field_name = value

    if not isinstance(field_name, str):
        raise TypeError("field must be a FieldRef or string")
    if definition is None:
        return FieldRef(field_name)
    if field_name in definition.fields_by_name:
        return definition.fields_by_name[field_name]
    raise ValueError(f"unknown field for {definition.entity_name}: {field_name!r}")


def _select_fields(
    definition: _ObjectDefinition | None,
    select: Sequence[FieldRef | str] | None,
) -> list[str] | None:
    """校验并序列化 ``select``；字段名按 DataService 原样发送。"""

    if select is None:
        return None
    if isinstance(select, (str, bytes)):
        raise TypeError("select must be a sequence of fields")
    values = [_field_for(definition, item).field_name for item in select]
    if not values:
        raise ValueError("select must contain at least one field")
    return values


def _parse_direction(value: Any) -> Literal["asc", "desc"]:
    """校验并返回标准化后的排序方向。"""

    direction = str(value).lower()
    if direction not in {"asc", "desc"}:
        raise ValueError("order_by direction must be asc or desc")
    return cast(Literal["asc", "desc"], direction)


def _serialize_order_by(
    definition: _ObjectDefinition | None,
    order_by: str | SortField | FieldRef | Mapping[str, Any] | Sequence[Any] | None,
) -> dict[str, Any] | None:
    """将多种便捷排序写法统一转换成 ObjectSet ``orderBy`` JSON。"""

    if order_by is None:
        return None
    if isinstance(order_by, SortField):
        fields = [order_by]
    elif isinstance(order_by, FieldRef):
        fields = [SortField(order_by)]
    elif isinstance(order_by, str):
        fields = [SortField(_field_for(definition, order_by))]
    elif isinstance(order_by, Mapping):
        if order_by.get("type") == "relevance":
            return {"type": "relevance"}
        if "fields" in order_by:
            raw_fields = order_by["fields"]
            if not isinstance(raw_fields, Sequence) or isinstance(raw_fields, (str, bytes)):
                raise ValueError("order_by.fields must be a sequence")
            fields = list(raw_fields)
        elif "field" in order_by:
            field = order_by["field"]
            fields = [
                SortField(
                    _field_for(definition, cast(FieldRef | str, field)),
                    _parse_direction(order_by.get("direction", "asc")),
                )
            ]
        else:
            fields = [
                SortField(_field_for(definition, field), _parse_direction(direction))
                for field, direction in order_by.items()
            ]
    else:
        if isinstance(order_by, (str, bytes)):
            raise TypeError("order_by must be a SortField or sequence")
        fields = list(cast(Sequence[Any], order_by))

    result: list[dict[str, str]] = []
    for item in fields:
        if isinstance(item, FieldRef):
            item = SortField(item)
        if isinstance(item, Mapping):
            field_value = item.get("field")
            item = SortField(
                _field_for(definition, cast(FieldRef | str, field_value)),
                _parse_direction(item.get("direction", "asc")),
            )
        if not isinstance(item, SortField):
            raise TypeError("each order_by value must be a SortField")
        result.append(item.to_dict())
    if not result:
        raise ValueError("order_by must contain at least one field")
    return {"type": "fields", "fields": result}

# ---------------------------------------------------------------------------
# 响应模型解码
# ---------------------------------------------------------------------------


def _decode_model(
    definition: _ObjectDefinition,
    payload: Mapping[str, Any],
    client: Any | None = None,
) -> Any:
    """将 DataService 对象响应解码为对应的实体 dataclass。"""

    properties = payload.get("properties")
    if not isinstance(properties, Mapping):
        raise DataServiceError("DataService returned invalid properties")

    type_hints = get_type_hints(definition.model_type)
    values: dict[str, Any] = {}
    for field in dataclass_fields(definition.model_type):
        property_ref = definition.fields_by_name[field.name].field_name
        if property_ref not in properties:
            continue
        value = properties[property_ref]
        annotation = type_hints.get(field.name)
        possible_types = set(get_args(annotation)) if annotation else set()
        if annotation is datetime or datetime in possible_types:
            if isinstance(value, str):
                value = datetime.fromisoformat(value.replace("Z", "+00:00"))
        elif annotation is date or date in possible_types:
            if isinstance(value, str):
                value = date.fromisoformat(value)
        elif annotation is float or float in possible_types:
            if isinstance(value, str):
                try:
                    value = float(value)
                except ValueError as error:
                    raise DataServiceError(
                        f"DataService returned invalid numeric property: {property_ref!r}"
                    ) from error
        elif annotation is int or int in possible_types:
            if isinstance(value, str):
                try:
                    value = int(value)
                except ValueError as error:
                    raise DataServiceError(
                        f"DataService returned invalid integer property: {property_ref!r}"
                    ) from error
        values[field.name] = value

    primary_key = definition.primary_key_field
    if primary_key not in values and payload.get("id") is not None:
        values[primary_key] = payload["id"]
    model = definition.model_type(**values)
    if client is not None:
        object.__setattr__(model, "_dataservice_client", client)
    return model


class ObjectSet(Generic[T]):
    """由标准 load 接口执行的不可变 ObjectSet 构造器。"""

    def __init__(
        self,
        client: _HttpClient,
        definition: _ObjectDefinition | None,
        node: Mapping[str, Any],
    ) -> None:
        # 每个查询变换都创建新的 ObjectSet，因此调用方可以安全复用原查询。
        self._client = client
        self._definition = definition
        self._node = dict(node)

    @property
    def object_type(self) -> str | None:
        """返回当前 ObjectSet 的对象类型 code（关系跳转结果可能未知）。"""

        if self._definition is None:
            return None
        return self._definition.object_code

    def where(self, expression: WhereExpression | Mapping[str, Any]) -> ObjectSet[T]:
        """在当前 ObjectSet 上追加一个 filter 节点。"""

        return ObjectSet(
            self._client,
            self._definition,
            {
                "type": "filter",
                "objectSet": self._node,
                "where": _as_where(expression),
            },
        )

    def search_around(self, link_code: str) -> ObjectSet[Any]:
        """按 ``metadata_dev.link_types.code`` 沿关系查询另一端对象。"""

        if not isinstance(link_code, str) or not link_code:
            raise TypeError("search_around expects a non-empty link code string")
        # 关系方向、目标实体和关联字段由 DataService 元数据解析，SDK 只发送 code。
        return ObjectSet(
            self._client,
            None,
            {
                "type": "searchAround",
                "objectSet": self._node,
                "link": link_code,
            },
        )

    def union(self, *others: ObjectSet[T]) -> ObjectSet[T]:
        """构造多个同类型 ObjectSet 的并集。"""

        object_sets = (self, *others)
        self._require_same_type(object_sets, "union")
        return ObjectSet(
            self._client,
            self._definition,
            {"type": "union", "objectSets": [item._node for item in object_sets]},
        )

    def intersect(self, *others: ObjectSet[T]) -> ObjectSet[T]:
        """构造多个同类型 ObjectSet 的交集。"""

        object_sets = (self, *others)
        self._require_same_type(object_sets, "intersect")
        return ObjectSet(
            self._client,
            self._definition,
            {"type": "intersect", "objectSets": [item._node for item in object_sets]},
        )

    def subtract(self, other: ObjectSet[T]) -> ObjectSet[T]:
        """从当前 ObjectSet 中排除另一个同类型 ObjectSet。"""

        self._require_same_type((self, other), "subtract")
        return ObjectSet(
            self._client,
            self._definition,
            {"type": "subtract", "left": self._node, "right": other._node},
        )

    @staticmethod
    def _require_same_type(
        object_sets: Sequence[ObjectSet[Any]],
        operation: str,
    ) -> None:
        for item in object_sets:
            if not isinstance(item, ObjectSet):
                raise TypeError(f"{operation} operands must be ObjectSet instances")
        if any(item.object_type != object_sets[0].object_type for item in object_sets[1:]):
            raise ValueError(f"{operation} requires ObjectSets of the same type")

    def load(
        self,
        *,
        select: Sequence[FieldRef | str] | None = None,
        order_by: str | SortField | FieldRef | Mapping[str, Any] | Sequence[Any] | None = None,
        page_size: int = 20,
        page_token: str | None = None,
        snapshot: bool = False,
        include_total_count: bool = False,
        branch: str | None = None,
    ) -> Page[T]:
        """执行 ObjectSet 查询并返回当前页、下一页 token 和可选总数。"""

        if not 1 <= page_size <= 100:
            raise ValueError("page_size must be between 1 and 100")
        body: dict[str, Any] = {
            "objectSet": self._node,
            "pageSize": page_size,
            "snapshot": snapshot,
            "includeTotalCount": include_total_count,
        }
        if select is not None:
            body["select"] = _select_fields(self._definition, select)
        if order_by is not None:
            body["orderBy"] = _serialize_order_by(self._definition, order_by)
        if page_token is not None:
            body["pageToken"] = page_token
        if branch is not None:
            body["branch"] = branch

        response = self._client.request(
            "POST",
            f"/v1/api/ontology/data/projects/"
            f"{quote(self._client.workspace_id, safe='')}/objectSets/loadObjects",
            body,
            operation=(
                f"{self._definition.entity_name}.load"
                if self._definition is not None
                else "ObjectSet.searchAround.load"
            ),
        )
        rows = response.get("records")
        if not isinstance(rows, list):
            raise DataServiceError("DataService returned invalid data.records")
        raw_total_count = response.get("totalCount")
        if raw_total_count is None:
            total_count = None
        elif isinstance(raw_total_count, str):
            try:
                total_count = int(raw_total_count)
            except ValueError as error:
                raise DataServiceError("DataService returned invalid totalCount") from error
        else:
            raise DataServiceError("DataService returned invalid totalCount")
        next_page_token = response.get("nextPageToken")
        if next_page_token is not None and not isinstance(next_page_token, str):
            raise DataServiceError("DataService returned invalid nextPageToken")
        decoded_rows: list[Any] = []
        for row in rows:
            definition = self._definition
            if definition is None:
                object_code = row.get("objectType")
                definition = OBJECT_DEFINITIONS_BY_CODE.get(object_code)
                if definition is None:
                    raise DataServiceError(
                        f"DataService returned unknown objectType: {object_code!r}"
                    )
            decoded_rows.append(_decode_model(definition, row, self._client))
        return Page(
            data=decoded_rows,
            next_page_token=next_page_token,
            total_count=cast(int | None, total_count),
        )


def _encode_change_value(value: Any) -> Any:
    """把 changes 里的日期时间值递归转成 ISO 字符串，保证结果可直接 ``json.dumps``。"""

    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, Mapping):
        return {key: _encode_change_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_encode_change_value(item) for item in value]
    return value


@dataclass(frozen=True)
class OntologyEdit:
    """一条符合 DataService edits 入参契约的对象编辑项。"""

    object_type: str
    primary_key: str
    changes: Mapping[str, Any]
    operation: Literal["CREATE", "UPDATE", "DELETE"] = "UPDATE"

    def to_dict(self) -> dict[str, Any]:
        """返回可直接提交给 DataService 的编辑项。

        changes 中的日期和日期时间值会转成 ISO 8601 字符串，因此返回值
        可以直接传给 ``json.dumps``。
        """

        return {
            "operation": self.operation,
            "objectType": self.object_type,
            "primaryKey": self.primary_key,
            "changes": {
                key: _encode_change_value(value)
                for key, value in self.changes.items()
            },
        }


class EditableObject(Generic[T]):
    """Ontology edits 容器中的可编辑对象视图。

    该对象不复制完整实体，只记录调用方赋值过的字段；赋值不会立即发 HTTP，
    由所属的 :class:`OntologyEdits` 容器统一通过 ``get_edits`` 返回。
    """

    def __init__(
        self,
        endpoint: EntityEndpoint[T],
        primary_key: str,
        source: T | None = None,
        operation: Literal["CREATE", "UPDATE", "DELETE"] = "UPDATE",
    ) -> None:
        self._endpoint = endpoint
        self._primary_key = primary_key
        self._source = source
        self._operation = operation
        self._changes: dict[str, Any] = {}

    def __setattr__(self, name: str, value: Any) -> None:
        """把实体字段赋值转换为待应用变更。"""

        if name.startswith("_"):
            object.__setattr__(self, name, value)
            return
        definition = self._endpoint._definition
        if self._operation == "DELETE":
            raise ValueError("a deleted object cannot be updated")
        if name == definition.primary_key_field:
            raise ValueError("an existing object's primary key cannot be updated")
        if name not in definition.fields_by_name:
            raise AttributeError(name)
        self._changes[name] = value

    def __getattr__(self, name: str) -> Any:
        """优先返回本次编辑后的值；有原对象时回退读取原值。"""

        if name in self._changes:
            return self._changes[name]
        if self._source is not None and name in self._endpoint._definition.fields_by_name:
            return getattr(self._source, name)
        raise AttributeError(name)

    @property
    def primary_key(self) -> str:
        """返回本次编辑对应的对象主键。"""

        return self._primary_key

    @property
    def has_changes(self) -> bool:
        """表示当前视图是否产生了一条 create/update/delete 意图。"""

        return self._operation != "UPDATE" or bool(self._changes)

    def _to_edit(self) -> OntologyEdit:
        """生成当前可编辑视图对应的待应用记录。"""

        definition = self._endpoint._definition
        changes = {
            definition.fields_by_name[name].field_name: value
            for name, value in self._changes.items()
        }
        return OntologyEdit(
            object_type=definition.object_code,
            primary_key=self._primary_key,
            changes=changes,
            operation=self._operation,
        )

    def _mark_deleted(self) -> None:
        self._operation = "DELETE"
        self._changes.clear()


class EntityEndpoint(Generic[T]):
    """实体查询接口；对象更新通过 ``client.edits()`` 进入。"""

    def __init__(self, client: _HttpClient, definition: _ObjectDefinition) -> None:
        self._client = client
        self._definition = definition

    def _base_object_set(self) -> ObjectSet[T]:
        """创建当前实体的 base ObjectSet 节点。"""

        return ObjectSet(
            self._client,
            self._definition,
            {"type": "base", "objectType": self._definition.object_code},
        )

    def where(self, expression: WhereExpression | Mapping[str, Any]) -> ObjectSet[T]:
        """从当前实体入口开始构造一个过滤查询。"""

        return self._base_object_set().where(expression)

    def static(self, objects: Sequence[str]) -> ObjectSet[T]:
        """构造由主键组成的 static ObjectSet。"""

        if isinstance(objects, (str, bytes)):
            raise TypeError("static expects a sequence of object IDs")
        return ObjectSet(
            self._client,
            self._definition,
            {
                "type": "static",
                "objectType": self._definition.object_code,
                "objects": list(objects),
            },
        )

    def detail(
        self,
        primary_key: str,
        *,
        select: Sequence[FieldRef | str] | None = None,
        branch: str | None = None,
    ) -> T:
        """按主键读取一个对象详情。"""

        fields = _select_fields(self._definition, select)
        path = (
            f"/v1/api/ontology/data/projects/{quote(self._client.workspace_id, safe='')}/objects/"
            f"{quote(self._definition.object_code, safe='')}/{quote(primary_key, safe='')}"
        )
        query: list[tuple[str, str]] = []
        if fields:
            query.extend(("select", value) for value in fields)
        if branch is not None:
            query.append(("branch", branch))
        if query:
            path = f"{path}?{urlencode(query)}"
        response = self._client.request(
            "GET",
            path,
            operation=f"{self._definition.entity_name}.detail",
        )
        return _decode_model(self._definition, response, self._client)

    def load(
        self,
        *,
        where: WhereExpression | Mapping[str, Any] | None = None,
        select: Sequence[FieldRef | str] | None = None,
        order_by: str | SortField | FieldRef | Mapping[str, Any] | Sequence[Any] | None = None,
        page_size: int = 20,
        page_token: str | None = None,
        snapshot: bool = False,
        include_total_count: bool = False,
        branch: str | None = None,
    ) -> Page[T]:
        """执行当前实体的 base/filter 查询。"""

        query = self._base_object_set()
        if where is not None:
            query = query.where(where)
        return query.load(
            select=select,
            order_by=order_by,
            page_size=page_size,
            page_token=page_token,
            snapshot=snapshot,
            include_total_count=include_total_count,
            branch=branch,
        )


class _EditEntityEndpoint(Generic[T]):
    """Ontology edits 容器中的实体编辑入口。"""

    def __init__(self, edits: OntologyEdits, endpoint: EntityEndpoint[T]) -> None:
        self._edits = edits
        self._endpoint = endpoint

    def edit(self, object_or_primary_key: T | str) -> EditableObject[T]:
        """按实体实例或主键创建可编辑对象视图。"""

        return self._edits._register(self._endpoint, object_or_primary_key, "UPDATE")

    def create(self, primary_key: str, **properties: Any) -> EditableObject[T]:
        """登记一个 CREATE 意图；属性只写入 edits 容器，不发 HTTP。"""

        editable = self._edits._register(self._endpoint, primary_key, "CREATE")
        for name, value in properties.items():
            setattr(editable, name, value)
        return editable

    def delete(self, object_or_primary_key: T | str | EditableObject[T]) -> None:
        """登记一个 DELETE 意图；删除只在 Action Runtime 真正发生。"""

        self._edits._delete(self._endpoint, object_or_primary_key)


class OntologyEdits:
    """收集多个对象修改的 edits 容器。

    ``get_edits`` 只返回待应用意图，不发 HTTP；真正写回由 Action Runtime 负责。
    """

    def __init__(self, client: _HttpClient) -> None:
        self._client = client
        self._endpoints: dict[str, EntityEndpoint[Any]] = {
            definition.entity_name: EntityEndpoint(client, definition)
            for definition in OBJECT_DEFINITIONS.values()
        }
        self._editable_objects: dict[tuple[str, str], EditableObject[Any]] = {}
        # 为编辑器提供 ``edits.objects.<Entity>.edit(...)`` 的补全信息。
        self.objects: _EditObjectsRuntime = _EditObjectsRuntime(self)

    def _register(
        self,
        endpoint: EntityEndpoint[T],
        object_or_primary_key: T | str,
        operation: Literal["CREATE", "UPDATE", "DELETE"] = "UPDATE",
    ) -> EditableObject[T]:
        """登记对象意图，并合并同一对象的重复编辑入口。"""

        definition = endpoint._definition
        primary_key, source = self._resolve_primary_key(endpoint, object_or_primary_key)

        identity = (definition.entity_name, primary_key)
        existing = self._editable_objects.get(identity)
        if existing is not None:
            if operation == "CREATE" and existing._operation != "CREATE":
                raise ValueError("cannot create an existing edited object")
            if operation == "UPDATE" and existing._operation == "DELETE":
                raise ValueError("cannot edit a deleted object")
            return cast(EditableObject[T], existing)
        editable = EditableObject(endpoint, primary_key, source, operation)
        self._editable_objects[identity] = editable
        return editable

    @staticmethod
    def _resolve_primary_key(
        endpoint: EntityEndpoint[T],
        object_or_primary_key: Any,
    ) -> tuple[str, Any]:
        definition = endpoint._definition
        if isinstance(object_or_primary_key, str):
            return object_or_primary_key, None
        if isinstance(object_or_primary_key, EditableObject):
            if object_or_primary_key._endpoint is not endpoint:
                raise ValueError("the editable object belongs to another edits container")
            return object_or_primary_key.primary_key, object_or_primary_key._source
        if isinstance(object_or_primary_key, definition.model_type):
            raw_primary_key = getattr(object_or_primary_key, definition.primary_key_field)
            if raw_primary_key is None:
                raise ValueError("an editable object must have a primary key")
            return str(raw_primary_key), object_or_primary_key
        raise TypeError("expected an entity instance or primary key")

    def _delete(
        self,
        endpoint: EntityEndpoint[T],
        object_or_primary_key: T | str | EditableObject[T],
    ) -> None:
        """登记删除，并按对象主键折叠同一容器中的前序意图。"""

        primary_key, source = self._resolve_primary_key(endpoint, object_or_primary_key)
        identity = (endpoint._definition.entity_name, primary_key)
        existing = self._editable_objects.get(identity)
        if existing is not None and existing._operation == "CREATE":
            del self._editable_objects[identity]
            return
        if existing is not None:
            existing._mark_deleted()
            return
        self._editable_objects[identity] = EditableObject(
            endpoint,
            primary_key,
            source,
            "DELETE",
        )

    def get_edits(self) -> list[OntologyEdit]:
        """返回待应用的编辑项，不发起 HTTP 请求。"""

        return [
            editable._to_edit()
            for editable in self._editable_objects.values()
            if editable.has_changes
        ]


class _EditObjectsRuntime:
    """将 edits 容器绑定成 edits.objects.<Entity> 编辑入口。"""

    Project: _EditEntityEndpoint[Project]
    Material: _EditEntityEndpoint[Material]
    UnitConversion: _EditEntityEndpoint[UnitConversion]
    Supplier: _EditEntityEndpoint[Supplier]
    BomLine: _EditEntityEndpoint[BomLine]
    EcnRecord: _EditEntityEndpoint[EcnRecord]
    Demand: _EditEntityEndpoint[Demand]
    MaterialAuthorization: _EditEntityEndpoint[MaterialAuthorization]
    Supply: _EditEntityEndpoint[Supply]
    PurchaseOrder: _EditEntityEndpoint[PurchaseOrder]
    StockMovement: _EditEntityEndpoint[StockMovement]
    SubstitutionPermission: _EditEntityEndpoint[SubstitutionPermission]
    SupplierSupplyCondition: _EditEntityEndpoint[SupplierSupplyCondition]
    DataVersion: _EditEntityEndpoint[DataVersion]
    CalculationRun: _EditEntityEndpoint[CalculationRun]
    MaterialRequirement: _EditEntityEndpoint[MaterialRequirement]
    InspectionChange: _EditEntityEndpoint[InspectionChange]
    ReviewTask: _EditEntityEndpoint[ReviewTask]
    SourcingSuggestion: _EditEntityEndpoint[SourcingSuggestion]
    VendorReferenceList: _EditEntityEndpoint[VendorReferenceList]
    PeriodSupplyBalance: _EditEntityEndpoint[PeriodSupplyBalance]
    SlowMovingRisk: _EditEntityEndpoint[SlowMovingRisk]
    SolutionPlan: _EditEntityEndpoint[SolutionPlan]
    HistoricalCase: _EditEntityEndpoint[HistoricalCase]
    CauseAttribution: _EditEntityEndpoint[CauseAttribution]
    PreventionRule: _EditEntityEndpoint[PreventionRule]

    def __init__(self, edits: OntologyEdits) -> None:
        for entity_name, endpoint in edits._endpoints.items():
            setattr(self, entity_name, _EditEntityEndpoint(edits, endpoint))


_FUNCTION_BASIC_TYPES = (str, int, float, bool, date, datetime)


def _function_param_kind(annotation: Any) -> str | None:
    """把参数标注归类为 object/basic/dict；不合法返回 None。"""

    if annotation in _FUNCTION_BASIC_TYPES:
        return "basic"
    if annotation is dict or get_origin(annotation) is dict:
        return "dict"
    for definition in OBJECT_DEFINITIONS.values():
        if annotation is definition.model_type:
            return "object"
    return None


_function_default_client: _HttpClient | None = None


def _function_client() -> _HttpClient:
    """惰性创建 function 修饰器加载实体使用的默认客户端。"""

    global _function_default_client
    if _function_default_client is None:
        _function_default_client = WorkspaceClient()._http
    return _function_default_client


def function(
    *, edits: Sequence[type[Any]]
) -> Callable[[Callable[..., list[OntologyEdit]]], Callable[..., list[dict[str, Any]]]]:
    """声明函数的下游编辑类型，符合 Palantir Python Ontology edits 写法。

    被修饰函数按 Palantir 写法构造并返回 ``list[OntologyEdit]``；
    修饰后的函数由 SDK 负责序列化，返回可直接 ``json.dumps`` 的
    编辑字典列表，调用方不需要感知 ``OntologyEdit``。
    """

    def decorate(
        func: Callable[..., list[OntologyEdit]],
    ) -> Callable[..., list[dict[str, Any]]]:
        wrapped = _decorate_function(func)
        setattr(wrapped, "__ontology_edits__", tuple(edits))
        return cast("Callable[..., list[dict[str, Any]]]", wrapped)

    return decorate


def _decorate_function(
    func: Callable[..., list[OntologyEdit]],
) -> Callable[..., list[dict[str, Any]]]:
    """把实体参数改写为按主键加载，并序列化 OntologyEdit 返回值。

    Python 不写类型标注就无法推导，因此参数和返回值都必须显式标注：
    参数类型只能是生成的实体类型、基础数据类型（str/int/float/bool/date/datetime）
    或 dict；返回值类型必须是 ``list[OntologyEdit]``。

    标注为实体类型的参数，包装后接受该实体的主键 id；调用时由 SDK 先从
    DataService 加载对象，再把加载好的实体传给原函数。对象不存在（40402）时
    记录日志并返回空 edits，不调用原函数；其它 DataService 错误继续抛出。
    已经传入实体实例的参数会原样透传。基础类型和 dict 参数不做转换。

    原函数的返回值先校验为 ``list[OntologyEdit]``，再由 wrapper 统一转换
    成可 ``json.dumps`` 的字典列表；这相当于 Palantir 平台 Function Runtime
    做的 edits 序列化，调用方拿到结果即可直接提交。
    """

    signature = inspect.signature(func)
    hints = get_type_hints(func)
    entity_params: dict[str, _ObjectDefinition] = {}
    for param in signature.parameters.values():
        if param.kind in (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD):
            raise TypeError(
                f"@function: {func.__name__!r} must not use *args or **kwargs; "
                "list each parameter with a type annotation"
            )
        if param.annotation is inspect.Parameter.empty:
            raise TypeError(
                f"@function: parameter {param.name!r} of {func.__name__!r} "
                "requires a type annotation"
            )
        annotation = hints.get(param.name)
        kind = _function_param_kind(annotation)
        if kind is None:
            raise TypeError(
                f"@function: parameter {param.name!r} of {func.__name__!r} must be "
                "a workspace entity type, a basic type (str/int/float/bool/date/datetime), "
                f"or dict, got {annotation!r}"
            )
        if kind == "object":
            for definition in OBJECT_DEFINITIONS.values():
                if annotation is definition.model_type:
                    entity_params[param.name] = definition
                    break
    if signature.return_annotation is inspect.Signature.empty or "return" not in hints:
        raise TypeError(f"@function: {func.__name__!r} requires a return type annotation")
    return_type = hints["return"]
    if get_origin(return_type) is not list or get_args(return_type) != (OntologyEdit,):
        raise TypeError(
            f"@function: {func.__name__!r} must return list[OntologyEdit], "
            f"got {return_type!r}"
        )

    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> list[dict[str, Any]]:
        bound = signature.bind(*args, **kwargs)
        client: _HttpClient | None = None
        for name, value in list(bound.arguments.items()):
            definition = entity_params.get(name)
            if definition is None or isinstance(value, definition.model_type):
                continue
            if value is None:
                raise TypeError(
                    f"@function: parameter {name!r} of {func.__name__!r} "
                    "expects an id or entity instance, got None"
                )
            if client is None:
                client = _function_client()
            try:
                loaded: Any = EntityEndpoint(client, definition).detail(str(value))
            except DataServiceError as error:
                if error.code != 40402:
                    raise
                client._log_json(
                    "function_skipped",
                    level=logging.WARNING,
                    function=func.__name__,
                    entity=definition.entity_name,
                    primary_key=str(value),
                    reason="DataService returned OBJECT_NOT_FOUND; function skipped successfully with no edits",
                )
                return []
            if loaded is None:
                raise DataServiceError(
                    f"@function: {definition.entity_name} {value!r} not found"
                )
            bound.arguments[name] = loaded
        result = func(*bound.args, **bound.kwargs)
        if not isinstance(result, list) or any(not isinstance(item, OntologyEdit) for item in result):
            raise TypeError(f"@function: {func.__name__!r} must return list[OntologyEdit]")
        return [item.to_dict() for item in result]

    return wrapper


class Objects(Protocol):
    """由当前工作区生成的实体入口；运行时属性按对象定义动态绑定。"""

    pass


class _ObjectsRuntime:
    """将生成的实体定义绑定成 ``client.objects.<Entity>`` 属性。"""

    def __init__(self, client: _HttpClient) -> None:
        for definition in OBJECT_DEFINITIONS.values():
            setattr(self, definition.entity_name, EntityEndpoint(client, definition))


class WorkspaceClient:
    """Workspace DataService 客户端。

    生成 SDK 时已经把当前工作区的 ``workspace_id``、DataService 地址和
    Demo token 固化在 SDK 中，调用方通常只需要执行 ``WorkspaceClient()``。
    部署到其他环境时，可以通过构造参数或 ``DATASERVICE_URL``、
    ``DATASERVICE_TOKEN``、``DATASERVICE_WORKSPACE_ID`` 环境变量覆盖默认配置。

    HTTP 请求和响应通过 ``workspace_sdk.http`` logger 以 JSON Lines 记录。
    SDK 不配置全局 handler；调用方可以自行决定是否输出、输出到控制台，
    或写入日志文件。
    """

    def __init__(
        self,
        *,
        base_url: str | None = None,
        token: str | None = None,
        workspace_id: str | None = None,
        timeout: float = 30.0,
        logger: logging.Logger | None = None,
    ) -> None:
        configured_workspace_id = (
            workspace_id
            or os.getenv("DATASERVICE_WORKSPACE_ID")
            or DEFAULT_WORKSPACE_ID
        )
        if not configured_workspace_id:
            raise ValueError(
                "workspace_id is required; pass it to WorkspaceClient or set DATASERVICE_WORKSPACE_ID"
            )
        http = _HttpClient(
            base_url=base_url or os.getenv("DATASERVICE_URL") or DEFAULT_DATASERVICE_URL,
            token=token or os.getenv("DATASERVICE_TOKEN") or DEFAULT_TOKEN,
            workspace_id=configured_workspace_id,
            timeout=timeout,
            logger=logger,
        )
        self._http = http
        self.objects: Objects = cast(Objects, _ObjectsRuntime(http))

    def edits(self) -> OntologyEdits:
        """创建一个新的 edits 容器。"""

        return OntologyEdits(self._http)

    @property
    def base_url(self) -> str:
        return self._http.base_url

    @property
    def workspace_id(self) -> str:
        return self._http.workspace_id


# ---------------------------------------------------------------------------
# HTTP 传输（放在文件末尾，便于把 SDK 领域 API 与网络细节分开）
# ---------------------------------------------------------------------------


from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen


DEFAULT_DATASERVICE_URL = "https://aquilair.idcs.elitescloud.com/data-service"
DEFAULT_TOKEN = "runtime-token"
DEFAULT_WORKSPACE_ID = "01a13d97-dbdb-7000-b2e7-cfd274604b12"


class DataServiceError(RuntimeError):
    """DataService 请求失败或返回了不符合协议的响应。"""

    def __init__(
        self,
        message: str,
        *,
        code: int | None = None,
        http_status: int | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.http_status = http_status


class _HttpClient:
    """DataService HTTP 传输层；成功请求也通过标准 logging 输出 JSON。"""

    def __init__(
        self,
        *,
        base_url: str,
        token: str,
        workspace_id: str,
        timeout: float,
        logger: logging.Logger | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.token = token
        self.workspace_id = workspace_id
        self.timeout = timeout
        self.logger = logger or logging.getLogger("workspace_sdk.http")

    def _log_json(self, event: str, *, level: int = logging.DEBUG, **values: Any) -> None:
        """把一条 HTTP 事件编码成 JSON，交给调用方配置的 logger。"""

        record = {"event": event, **values}
        self.logger.log(
            level,
            json.dumps(record, ensure_ascii=False, default=str),
        )

    def request(
        self,
        method: str,
        path: str,
        body: Mapping[str, Any] | None = None,
        *,
        operation: str = "",
    ) -> dict[str, Any]:
        """发送 JSON 请求，并返回 JSON object。"""

        request_url = f"{self.base_url}{path}"
        request_body = {} if body is None else dict(body)
        self._log_json(
            "http_request",
            operation=operation,
            method=method,
            url=request_url,
            body=request_body,
        )
        payload = json.dumps(request_body, ensure_ascii=False).encode("utf-8")
        request = Request(
            request_url,
            data=payload if method != "GET" else None,
            method=method,
            headers={
                "Accept": "application/json",
                "Authorization": f"Bearer {self.token}",
                "Content-Type": "application/json",
            },
        )
        try:
            with urlopen(request, timeout=self.timeout) as response:
                raw = response.read().decode("utf-8")
                response_body = json.loads(raw) if raw else {}
                self._log_json(
                    "http_response",
                    operation=operation,
                    status_code=response.status,
                    url=request_url,
                    body=response_body,
                )
        except HTTPError as error:
            raw = error.read().decode("utf-8", errors="replace")
            try:
                error_body: Any = json.loads(raw) if raw else {}
            except json.JSONDecodeError:
                error_body = {"raw": raw}
            self._log_json(
                "http_response",
                level=logging.ERROR,
                operation=operation,
                status_code=error.code,
                url=request_url,
                body=error_body,
            )
            raw_business_code = (
                error_body.get("code") if isinstance(error_body, dict) else None
            )
            try:
                business_code = int(raw_business_code)
            except (TypeError, ValueError):
                business_code = None
            raise DataServiceError(
                f"DataService returned HTTP {error.code}: {error_body}",
                code=business_code,
                http_status=error.code,
            ) from error
        except URLError as error:
            self._log_json(
                "http_error",
                level=logging.ERROR,
                operation=operation,
                method=method,
                url=request_url,
                error=str(error.reason),
            )
            raise DataServiceError(f"DataService request failed: {error.reason}") from error

        if not isinstance(response_body, dict):
            raise DataServiceError("DataService response must be a JSON object")
        if "code" not in response_body or "message" not in response_body:
            raise DataServiceError(
                "DataService response must contain code and message"
            )
        if "data" not in response_body:
            raise DataServiceError(
                "DataService response must contain data"
            )
        data = response_body["data"]
        if not isinstance(data, dict):
            raise DataServiceError("DataService response data must be a JSON object")
        return data


__all__ = [
    "Project",
    "ProjectFields",
    "Material",
    "MaterialFields",
    "UnitConversion",
    "UnitConversionFields",
    "Supplier",
    "SupplierFields",
    "BomLine",
    "BomLineFields",
    "EcnRecord",
    "EcnRecordFields",
    "Demand",
    "DemandFields",
    "MaterialAuthorization",
    "MaterialAuthorizationFields",
    "Supply",
    "SupplyFields",
    "PurchaseOrder",
    "PurchaseOrderFields",
    "StockMovement",
    "StockMovementFields",
    "SubstitutionPermission",
    "SubstitutionPermissionFields",
    "SupplierSupplyCondition",
    "SupplierSupplyConditionFields",
    "DataVersion",
    "DataVersionFields",
    "CalculationRun",
    "CalculationRunFields",
    "MaterialRequirement",
    "MaterialRequirementFields",
    "InspectionChange",
    "InspectionChangeFields",
    "ReviewTask",
    "ReviewTaskFields",
    "SourcingSuggestion",
    "SourcingSuggestionFields",
    "VendorReferenceList",
    "VendorReferenceListFields",
    "PeriodSupplyBalance",
    "PeriodSupplyBalanceFields",
    "SlowMovingRisk",
    "SlowMovingRiskFields",
    "SolutionPlan",
    "SolutionPlanFields",
    "HistoricalCase",
    "HistoricalCaseFields",
    "CauseAttribution",
    "CauseAttributionFields",
    "PreventionRule",
    "PreventionRuleFields",
    "LINK_REL_8BA0301E",
    "LINK_REL_04711EF7",
    "LINK_REL_336FFF57",
    "LINK_REL_1B9E39F9",
    "LINK_REL_E5935086",
    "LINK_REL_C9E4445E",
    "LINK_REL_A7AFB4D2",
    "LINK_REL_66F6753B",
    "LINK_REL_2C63FA8F",
    "LINK_REL_643985E8",
    "LINK_REL_E1E213CE",
    "LINK_REL_CC00F36E",
    "LINK_REL_0F491122",
    "LINK_REL_3CDDF3F1",
    "LINK_REL_5E1DC2D0",
    "LINK_REL_BAD3C217",
    "LINK_REL_2F9F9C78",
    "LINK_REL_783EE3DF",
    "LINK_REL_13993C79",
    "LINK_REL_F797C76F",
    "LINK_REL_D4E5BDD9",
    "LINK_REL_4F36CF0D",
    "LINK_REL_D8CEB2D7",
    "LINK_REL_7B7433F2",
    "LINK_REL_C9BD6EA6",
    "LINK_REL_FCE2D407",
    "LINK_REL_35F2E654",
    "LINK_REL_1B2D54E4",
    "LINK_REL_78C8EDA5",
    "LINK_REL_22E3127A",
    "LINK_REL_035EFFF8",
    "LINK_REL_819D4E00",
    "LINK_REL_26BA6628",
    "LINK_REL_E3CF2A48",
    "LINK_REL_48F28F78",
    "LINK_REL_C78E07D7",
    "LINK_REL_57C56235",
    "LINK_REL_0F255887",
    "LINK_REL_DE692B23",
    "DataServiceError",
    "Page",
    "FieldRef",
    "SortField",
    "EditableObject",
    "OntologyEdit",
    "OntologyEdits",
    "EntityEndpoint",
    "ObjectSet",
    "Objects",
    "RelationDefinition",
    "RELATION_DEFINITIONS",
    "WhereExpression",
    "and_",
    "or_",
    "not_",
    "function",
    "WorkspaceClient",
]
