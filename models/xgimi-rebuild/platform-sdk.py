
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
    project_code: str | None = None
    project_name: str | None = None
    model: str | None = None
    stage: str | None = None
    bom_status_desc: str | None = None
    fields: ClassVar["ProjectFields"]
    bom_lines: ClassVar[list[BomLine]]
    demands: ClassVar[list[Demand]]
    material_authorizations: ClassVar[list[MaterialAuthorization]]
    substitution_permissions: ClassVar[list[SubstitutionPermission]]
    impact_records: ClassVar[list[ImpactRecord]]
    historical_cases: ClassVar[list[HistoricalCase]]

@dataclass
class Material:
    material_code: str | None = None
    material_name: str | None = None
    base_uom: str | None = None
    cost_unit_price: float | None = None
    fields: ClassVar["MaterialFields"]
    supplier_supply_conditions: ClassVar[list[SupplierSupplyCondition]]
    unit_conversions: ClassVar[list[UnitConversion]]
    bom_lines: ClassVar[list[BomLine]]
    bom_lines_2: ClassVar[list[BomLine]]
    material_authorizations: ClassVar[list[MaterialAuthorization]]
    supplys: ClassVar[list[Supply]]
    stock_movements: ClassVar[list[StockMovement]]
    substitution_permissions: ClassVar[list[SubstitutionPermission]]
    substitution_permissions_2: ClassVar[list[SubstitutionPermission]]
    impact_records: ClassVar[list[ImpactRecord]]
    sourcing_suggestions: ClassVar[list[SourcingSuggestion]]
    period_supply_demands: ClassVar[list[PeriodSupplyDemand]]
    slow_moving_risks: ClassVar[list[SlowMovingRisk]]
    historical_cases: ClassVar[list[HistoricalCase]]
    historical_cases_2: ClassVar[list[HistoricalCase]]

@dataclass
class Supplier:
    supplier_code: str | None = None
    supplier_name: str | None = None
    purchase_group: str | None = None
    fields: ClassVar["SupplierFields"]
    supplier_supply_conditions: ClassVar[list[SupplierSupplyCondition]]
    sourcing_suggestions: ClassVar[list[SourcingSuggestion]]
    vendor_reference_lists: ClassVar[list[VendorReferenceList]]

@dataclass
class SupplierSupplyCondition:
    condition_id: str | None = None
    supplier_code: str | None = None
    material_code: str | None = None
    lead_time_days: float | None = None
    moq: float | None = None
    order_multiple: float | None = None
    quota_ratio: float | None = None
    fields: ClassVar["SupplierSupplyConditionFields"]
    supplier: ClassVar[Supplier | None]
    material: ClassVar[Material | None]

@dataclass
class UnitConversion:
    conversion_id: str | None = None
    material_code: str | None = None
    alt_unit: str | None = None
    factor: float | None = None
    approval_status: str | None = None
    fields: ClassVar["UnitConversionFields"]
    material: ClassVar[Material | None]

@dataclass
class BomLine:
    bom_line_id: str | None = None
    bom_type: str | None = None
    bom_version: str | None = None
    parent_material_code: str | None = None
    child_material_code: str | None = None
    project_code: str | None = None
    ecn_id: str | None = None
    line_qty: float | None = None
    base_qty: float | None = None
    yield_rate: float | None = None
    valid_from: date | None = None
    valid_to: date | None = None
    known_at: datetime | None = None
    std_usage_qty: float | None = None
    lower_level_demand_qty: float | None = None
    fields: ClassVar["BomLineFields"]
    material: ClassVar[Material | None]
    material_2: ClassVar[Material | None]
    project: ClassVar[Project | None]
    ecn_record: ClassVar[EcnRecord | None]
    change_records: ClassVar[list[ChangeRecord]]

@dataclass
class EcnRecord:
    ecn_id: str | None = None
    ecn_desc: str | None = None
    publish_time: datetime | None = None
    effective_date: date | None = None
    approve_status: str | None = None
    evidence_status: str | None = None
    fields: ClassVar["EcnRecordFields"]
    bom_lines: ClassVar[list[BomLine]]

@dataclass
class Demand:
    demand_uid: str | None = None
    demand_id: str | None = None
    record_version: str | None = None
    demand_type: str | None = None
    project_code: str | None = None
    required_qty: float | None = None
    required_date: date | None = None
    is_estimate: bool | None = None
    covered_demand_id: str | None = None
    covered_demand_version: str | None = None
    superseded_demand_id: str | None = None
    superseded_demand_version: str | None = None
    supersedes_uid: str | None = None
    covered_by_uid: str | None = None
    fields: ClassVar["DemandFields"]
    project: ClassVar[Project | None]
    demands: ClassVar[list[Demand]]
    demand: ClassVar[Demand | None]
    demands_2: ClassVar[list[Demand]]
    demand_2: ClassVar[Demand | None]
    allocation_records: ClassVar[list[AllocationRecord]]

@dataclass
class MaterialAuthorization:
    auth_id: str | None = None
    project_code: str | None = None
    material_code: str | None = None
    auth_version: str | None = None
    authorized_qty: float | None = None
    approve_date: date | None = None
    status: str | None = None
    gross_demand_qty: float | None = None
    pending_auth_qty: float | None = None
    fields: ClassVar["MaterialAuthorizationFields"]
    project: ClassVar[Project | None]
    material: ClassVar[Material | None]
    change_records: ClassVar[list[ChangeRecord]]

@dataclass
class Supply:
    supply_id: str | None = None
    supply_type: str | None = None
    material_code: str | None = None
    run_id: str | None = None
    qty: float | None = None
    available_date: date | None = None
    branch: str | None = None
    order_qty: float | None = None
    received_qty: float | None = None
    cancelled_qty: float | None = None
    closed_unreceived_qty: float | None = None
    open_order_qty: float | None = None
    cancel_deadline_date: date | None = None
    cancellation_fee: float | None = None
    restriction_note: str | None = None
    fields: ClassVar["SupplyFields"]
    material: ClassVar[Material | None]
    calculation_run: ClassVar[CalculationRun | None]
    stock_movements: ClassVar[list[StockMovement]]
    allocation_records: ClassVar[list[AllocationRecord]]
    solution_plans: ClassVar[list[SolutionPlan]]

@dataclass
class StockMovement:
    movement_id: str | None = None
    movement_type: str | None = None
    material_code: str | None = None
    source_supply_id: str | None = None
    qty: float | None = None
    movement_date: date | None = None
    fields: ClassVar["StockMovementFields"]
    material: ClassVar[Material | None]
    supply: ClassVar[Supply | None]

@dataclass
class SubstitutionPermission:
    permission_id: str | None = None
    permission_type: str | None = None
    replaced_material_code: str | None = None
    replacing_material_code: str | None = None
    project_code: str | None = None
    conversion_ratio: float | None = None
    valid_from: date | None = None
    valid_to: date | None = None
    batch_limit_note: str | None = None
    approval_cap_qty: float | None = None
    approve_status: str | None = None
    fields: ClassVar["SubstitutionPermissionFields"]
    material: ClassVar[Material | None]
    material_2: ClassVar[Material | None]
    project: ClassVar[Project | None]
    change_records: ClassVar[list[ChangeRecord]]
    allocation_records: ClassVar[list[AllocationRecord]]

@dataclass
class CalculationRun:
    run_id: str | None = None
    known_at: datetime | None = None
    data_version: str | None = None
    rule_version: str | None = None
    branch: str | None = None
    scenario_no: str | None = None
    eval_start_date: date | None = None
    eval_end_date: date | None = None
    fields: ClassVar["CalculationRunFields"]
    supplys: ClassVar[list[Supply]]
    change_records: ClassVar[list[ChangeRecord]]
    impact_records: ClassVar[list[ImpactRecord]]
    allocation_records: ClassVar[list[AllocationRecord]]
    sourcing_suggestions: ClassVar[list[SourcingSuggestion]]
    vendor_reference_lists: ClassVar[list[VendorReferenceList]]
    period_supply_demands: ClassVar[list[PeriodSupplyDemand]]
    slow_moving_risks: ClassVar[list[SlowMovingRisk]]
    solution_plans: ClassVar[list[SolutionPlan]]

@dataclass
class ChangeRecord:
    change_id: str | None = None
    change_type: str | None = None
    old_value: str | None = None
    new_value: str | None = None
    check_advice: str | None = None
    run_id: str | None = None
    bom_line_id: str | None = None
    permission_id: str | None = None
    project_code: str | None = None
    material_code: str | None = None
    auth_version: str | None = None
    auth_id: str | None = None
    fields: ClassVar["ChangeRecordFields"]
    calculation_run: ClassVar[CalculationRun | None]
    bom_line: ClassVar[BomLine | None]
    substitution_permission: ClassVar[SubstitutionPermission | None]
    material_authorization: ClassVar[MaterialAuthorization | None]

@dataclass
class ImpactRecord:
    impact_id: str | None = None
    run_id: str | None = None
    project_code: str | None = None
    material_code: str | None = None
    evidence_refs: str | None = None
    review_status: str | None = None
    impact_scope: str | None = None
    fields: ClassVar["ImpactRecordFields"]
    calculation_run: ClassVar[CalculationRun | None]
    project: ClassVar[Project | None]
    material: ClassVar[Material | None]

@dataclass
class AllocationRecord:
    allocation_id: str | None = None
    demand_id: str | None = None
    demand_version: str | None = None
    supply_id: str | None = None
    permission_id: str | None = None
    run_id: str | None = None
    allocated_qty: float | None = None
    priority_seq: float | None = None
    reserved_flag: bool | None = None
    demand_uid: str | None = None
    fields: ClassVar["AllocationRecordFields"]
    demand: ClassVar[Demand | None]
    supply: ClassVar[Supply | None]
    substitution_permission: ClassVar[SubstitutionPermission | None]
    calculation_run: ClassVar[CalculationRun | None]

@dataclass
class SourcingSuggestion:
    suggestion_id: str | None = None
    run_id: str | None = None
    material_code: str | None = None
    supplier_code: str | None = None
    allocated_qty: float | None = None
    suggested_qty: float | None = None
    rounding_extra_qty: float | None = None
    eta_meets_demand: bool | None = None
    list_id: str | None = None
    fields: ClassVar["SourcingSuggestionFields"]
    material: ClassVar[Material | None]
    supplier: ClassVar[Supplier | None]
    vendor_reference_list: ClassVar[VendorReferenceList | None]
    calculation_run: ClassVar[CalculationRun | None]

@dataclass
class VendorReferenceList:
    list_id: str | None = None
    run_id: str | None = None
    supplier_code: str | None = None
    list_status: str | None = None
    review_note: str | None = None
    fields: ClassVar["VendorReferenceListFields"]
    sourcing_suggestions: ClassVar[list[SourcingSuggestion]]
    supplier: ClassVar[Supplier | None]
    calculation_run: ClassVar[CalculationRun | None]

@dataclass
class PeriodSupplyDemand:
    balance_id: str | None = None
    run_id: str | None = None
    material_code: str | None = None
    period: str | None = None
    opening_qty: float | None = None
    arrival_qty: float | None = None
    other_inflow_qty: float | None = None
    required_qty: float | None = None
    fulfilled_qty: float | None = None
    other_outflow_qty: float | None = None
    closing_qty: float | None = None
    unmet_carry_qty: float | None = None
    fields: ClassVar["PeriodSupplyDemandFields"]
    material: ClassVar[Material | None]
    calculation_run: ClassVar[CalculationRun | None]

@dataclass
class SlowMovingRisk:
    risk_id: str | None = None
    run_id: str | None = None
    material_code: str | None = None
    risk_type: str | None = None
    remaining_qty: float | None = None
    reserved_qty: float | None = None
    post_period_consumed_qty: float | None = None
    risk_qty: float | None = None
    risk_amount: float | None = None
    window_later_commit_qty: float | None = None
    window_later_commit_amount: float | None = None
    pending_check_amount: float | None = None
    fields: ClassVar["SlowMovingRiskFields"]
    material: ClassVar[Material | None]
    calculation_run: ClassVar[CalculationRun | None]
    solution_plans: ClassVar[list[SolutionPlan]]

@dataclass
class SolutionPlan:
    plan_id: str | None = None
    run_id: str | None = None
    plan_code: str | None = None
    action_type: str | None = None
    material_code: str | None = None
    adjusted_supply_id: str | None = None
    action_cost: float | None = None
    shortage_flag: bool | None = None
    feasible_reason: str | None = None
    risk_id: str | None = None
    fields: ClassVar["SolutionPlanFields"]
    slow_moving_risk: ClassVar[SlowMovingRisk | None]
    supply: ClassVar[Supply | None]
    calculation_run: ClassVar[CalculationRun | None]

@dataclass
class HistoricalCase:
    case_id: str | None = None
    project_code: str | None = None
    old_material_code: str | None = None
    new_material_code: str | None = None
    observation_start: date | None = None
    observation_end: date | None = None
    future_demand_check_end: date | None = None
    evidence_status: str | None = None
    rebuilt_opening_qty: float | None = None
    received_in_qty: float | None = None
    consumed_out_qty: float | None = None
    rebuilt_closing_qty: float | None = None
    stock_check_diff: float | None = None
    baseline_risk_qty: float | None = None
    intervened_risk_qty: float | None = None
    simulated_reducible_qty: float | None = None
    fields: ClassVar["HistoricalCaseFields"]
    project: ClassVar[Project | None]
    material: ClassVar[Material | None]
    material_2: ClassVar[Material | None]
    historical_milestones: ClassVar[list[HistoricalMilestone]]
    cause_attributions: ClassVar[list[CauseAttribution]]
    prevention_rules: ClassVar[list[PreventionRule]]

@dataclass
class HistoricalMilestone:
    milestone_id: str | None = None
    case_id: str | None = None
    milestone_type: str | None = None
    milestone_date: date | None = None
    known_info: str | None = None
    fields: ClassVar["HistoricalMilestoneFields"]
    historical_case: ClassVar[HistoricalCase | None]

@dataclass
class CauseAttribution:
    attribution_id: str | None = None
    case_id: str | None = None
    cause_type: str | None = None
    attributed_qty: float | None = None
    evidence_ref: str | None = None
    conclusion_level: str | None = None
    fields: ClassVar["CauseAttributionFields"]
    historical_case: ClassVar[HistoricalCase | None]

@dataclass
class PreventionRule:
    rule_id: str | None = None
    source_case_id: str | None = None
    rule_content: str | None = None
    trigger_condition: str | None = None
    rule_status: str | None = None
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
    project_code = FieldRef("PROP_CD202A966D384776")
    project_name = FieldRef("PROP_0321EEACFDA74125")
    model = FieldRef("PROP_1D425B1A39A748B6")
    stage = FieldRef("PROP_FF5DB83CDFCA43C0")
    bom_status_desc = FieldRef("PROP_E457F1FC1C834EB4")

class MaterialFields:
    """物料 的字段引用。"""
    material_code = FieldRef("PROP_88FE9C4D14D74FED")
    material_name = FieldRef("PROP_67C5CB5AAB1D4EAB")
    base_uom = FieldRef("PROP_617749EC13B247A9")
    cost_unit_price = FieldRef("PROP_5C3A0889AE924DA2")

class SupplierFields:
    """供应商 的字段引用。"""
    supplier_code = FieldRef("PROP_3C2E13CD62584EC0")
    supplier_name = FieldRef("PROP_8900F89BF4A1429A")
    purchase_group = FieldRef("PROP_7632531FF5E84D52")

class SupplierSupplyConditionFields:
    """供应商供货条件 的字段引用。"""
    condition_id = FieldRef("PROP_CFC16EA7F89042B0")
    supplier_code = FieldRef("PROP_A6BFDAB28FBA4722")
    material_code = FieldRef("PROP_40A684CFC1D74C3B")
    lead_time_days = FieldRef("PROP_365657F362C54592")
    moq = FieldRef("PROP_9F6A350E5A8544F6")
    order_multiple = FieldRef("PROP_F1DE682E733E4BAF")
    quota_ratio = FieldRef("PROP_6B5B909FE4734B51")

class UnitConversionFields:
    """单位换算 的字段引用。"""
    conversion_id = FieldRef("PROP_4E355B6A15F04528")
    material_code = FieldRef("PROP_35CB48FD1026447B")
    alt_unit = FieldRef("PROP_7F803EF7C8724104")
    factor = FieldRef("PROP_FCE91F03A3F648BA")
    approval_status = FieldRef("PROP_238D1379A57A4DC7")

class BomLineFields:
    """BOM 行 的字段引用。"""
    bom_line_id = FieldRef("PROP_BD841408F465426A")
    bom_type = FieldRef("PROP_8272128E6F3F42CE")
    bom_version = FieldRef("PROP_94DBFA9FFB044B7D")
    parent_material_code = FieldRef("PROP_77011B3C1A5B4B24")
    child_material_code = FieldRef("PROP_AC2B560C1CF948EB")
    project_code = FieldRef("PROP_DEFA562B960B4911")
    ecn_id = FieldRef("PROP_18E7FA8AFAD1409D")
    line_qty = FieldRef("PROP_C70DA6F4E1B949D6")
    base_qty = FieldRef("PROP_987E24B96B7A46E3")
    yield_rate = FieldRef("PROP_CF45314284374A50")
    valid_from = FieldRef("PROP_E22082DCA071402B")
    valid_to = FieldRef("PROP_3A3C5BBF330C4007")
    known_at = FieldRef("PROP_A217E238D2DF468B")
    std_usage_qty = FieldRef("PROP_374CF1C09C0443EE")
    lower_level_demand_qty = FieldRef("PROP_B295C3E8661B4D7A")

class EcnRecordFields:
    """工程变更记录 的字段引用。"""
    ecn_id = FieldRef("PROP_FB027A7A032E4029")
    ecn_desc = FieldRef("PROP_86352CC9D51C4910")
    publish_time = FieldRef("PROP_2E7786A6AC3540A5")
    effective_date = FieldRef("PROP_62F043DD4BEA48BC")
    approve_status = FieldRef("PROP_2038B89445074255")
    evidence_status = FieldRef("PROP_76F8D2B4E6F1446B")

class DemandFields:
    """需求 的字段引用。"""
    demand_uid = FieldRef("PROP_4E34F4379B5E448D")
    demand_id = FieldRef("PROP_03B626D2D66A40F4")
    record_version = FieldRef("PROP_D87DD90E80514EFB")
    demand_type = FieldRef("PROP_ADE7700C928A473F")
    project_code = FieldRef("PROP_87EF44E8831B4EB4")
    required_qty = FieldRef("PROP_A85EAC449DF14874")
    required_date = FieldRef("PROP_BCC588BD8B734046")
    is_estimate = FieldRef("PROP_3A84E39E64434A4B")
    covered_demand_id = FieldRef("PROP_C9F24DF78E0B4BC3")
    covered_demand_version = FieldRef("PROP_E902EAB9CEC84847")
    superseded_demand_id = FieldRef("PROP_2606D471CAEA4B92")
    superseded_demand_version = FieldRef("PROP_DDE19F60C27A4B95")
    supersedes_uid = FieldRef("PROP_7FFBC030EAC5421D")
    covered_by_uid = FieldRef("PROP_E4123982FD084E7D")

class MaterialAuthorizationFields:
    """物料授权 的字段引用。"""
    auth_id = FieldRef("PROP_53225B75269E41E0")
    project_code = FieldRef("PROP_8908BE2F18A94053")
    material_code = FieldRef("PROP_2FE8A78A791C4D75")
    auth_version = FieldRef("PROP_793FD16384F3488C")
    authorized_qty = FieldRef("PROP_714B71D1D6C74A7B")
    approve_date = FieldRef("PROP_C0C384D6370D4954")
    status = FieldRef("PROP_4A40DDEEF3B74DDF")
    gross_demand_qty = FieldRef("PROP_47A88E6F4A1F4B09")
    pending_auth_qty = FieldRef("PROP_3A9BF38B32D042D0")

class SupplyFields:
    """供给 的字段引用。"""
    supply_id = FieldRef("PROP_C0703050AA954F98")
    supply_type = FieldRef("PROP_3167AE20305D471A")
    material_code = FieldRef("PROP_980F98CFF1914EAA")
    run_id = FieldRef("PROP_1043CD926BC442F9")
    qty = FieldRef("PROP_78CA4ADF3A30455D")
    available_date = FieldRef("PROP_A7CD4BD549574CAB")
    branch = FieldRef("PROP_FC741F369A774A89")
    order_qty = FieldRef("PROP_4DD196C036664AFA")
    received_qty = FieldRef("PROP_86F5904FB3F843AA")
    cancelled_qty = FieldRef("PROP_9F548599CB2242C7")
    closed_unreceived_qty = FieldRef("PROP_833DA454CEC34B0E")
    open_order_qty = FieldRef("PROP_BD664BB135984179")
    cancel_deadline_date = FieldRef("PROP_C55804296C964110")
    cancellation_fee = FieldRef("PROP_1BC4681EB0544F15")
    restriction_note = FieldRef("PROP_2EC96DE0E8A7455C")

class StockMovementFields:
    """库存收发流水 的字段引用。"""
    movement_id = FieldRef("PROP_FF45AACBC1A540CD")
    movement_type = FieldRef("PROP_3DDB7F0C8C044E60")
    material_code = FieldRef("PROP_4E9D2BF8F4CE435E")
    source_supply_id = FieldRef("PROP_16862D9F81814425")
    qty = FieldRef("PROP_EAF4CDD83E2E48C4")
    movement_date = FieldRef("PROP_9AF863B89E2C40DF")

class SubstitutionPermissionFields:
    """替代与转用许可 的字段引用。"""
    permission_id = FieldRef("PROP_7B0DB51A503D4277")
    permission_type = FieldRef("PROP_D3232E114E8041B8")
    replaced_material_code = FieldRef("PROP_710585274C0248C8")
    replacing_material_code = FieldRef("PROP_92B19371D7384171")
    project_code = FieldRef("PROP_8FD8B578585744CD")
    conversion_ratio = FieldRef("PROP_A86B132263514A7C")
    valid_from = FieldRef("PROP_221F868B85A941A0")
    valid_to = FieldRef("PROP_F93E7FA0561E45A4")
    batch_limit_note = FieldRef("PROP_86DE3290315743D0")
    approval_cap_qty = FieldRef("PROP_1C9BCCA661054C49")
    approve_status = FieldRef("PROP_73553F9CC1084AAF")

class CalculationRunFields:
    """计算运行 的字段引用。"""
    run_id = FieldRef("PROP_DB001943EC3F4311")
    known_at = FieldRef("PROP_91F9146D0FEF4AF4")
    data_version = FieldRef("PROP_CDD2CF4F5BFF4F76")
    rule_version = FieldRef("PROP_19C89F4C253349EA")
    branch = FieldRef("PROP_CF1AB09F334748F4")
    scenario_no = FieldRef("PROP_61AE196CF1644304")
    eval_start_date = FieldRef("PROP_EE2AC812399747DF")
    eval_end_date = FieldRef("PROP_AF09066314374C32")

class ChangeRecordFields:
    """变化记录 的字段引用。"""
    change_id = FieldRef("PROP_D1E7601F67AC46B4")
    change_type = FieldRef("PROP_2130A9164AF6403B")
    old_value = FieldRef("PROP_2A497E19B8B04335")
    new_value = FieldRef("PROP_36CACB0FDB51495D")
    check_advice = FieldRef("PROP_ECC90C614CE94FB8")
    run_id = FieldRef("PROP_AB9BC248078D42DE")
    bom_line_id = FieldRef("PROP_7AB5DC2609864E18")
    permission_id = FieldRef("PROP_40840B1C07514A06")
    project_code = FieldRef("PROP_82199F6FB5754ACD")
    material_code = FieldRef("PROP_DBFE6ECDD6BF428E")
    auth_version = FieldRef("PROP_14E6AB1A5A044C58")
    auth_id = FieldRef("PROP_C2C1354E8D404313")

class ImpactRecordFields:
    """影响记录 的字段引用。"""
    impact_id = FieldRef("PROP_BB5E6A8418B949B2")
    run_id = FieldRef("PROP_5E11125B517249EE")
    project_code = FieldRef("PROP_E01B7CF02AC442A6")
    material_code = FieldRef("PROP_C3D8DE9E248B4DCD")
    evidence_refs = FieldRef("PROP_92103597C14F4503")
    review_status = FieldRef("PROP_1437F69707E04EFA")
    impact_scope = FieldRef("PROP_69BF8AC0C04C4A20")

class AllocationRecordFields:
    """供需分配记录 的字段引用。"""
    allocation_id = FieldRef("PROP_996DA4B522B14D36")
    demand_id = FieldRef("PROP_555AFE53977A4B90")
    demand_version = FieldRef("PROP_738F7DE17DC84394")
    supply_id = FieldRef("PROP_56FCA9C2C43C4651")
    permission_id = FieldRef("PROP_815C904DACE2473C")
    run_id = FieldRef("PROP_3AB3EBE3080A431E")
    allocated_qty = FieldRef("PROP_25EF5922156B4011")
    priority_seq = FieldRef("PROP_1F79EE2827D54D97")
    reserved_flag = FieldRef("PROP_2CE83C66F50A4BF2")
    demand_uid = FieldRef("PROP_7195F12D4E064D07")

class SourcingSuggestionFields:
    """策备建议 的字段引用。"""
    suggestion_id = FieldRef("PROP_3EE669787FBD4FA3")
    run_id = FieldRef("PROP_BA67101AF70B46C5")
    material_code = FieldRef("PROP_138C14ACA8BC4B2F")
    supplier_code = FieldRef("PROP_2212E85AF08B4BDC")
    allocated_qty = FieldRef("PROP_9416CA91D28647B8")
    suggested_qty = FieldRef("PROP_2F8C15051E2B4005")
    rounding_extra_qty = FieldRef("PROP_9CF8475109214839")
    eta_meets_demand = FieldRef("PROP_BBCB675FF33E4D34")
    list_id = FieldRef("PROP_1D8F3DAAD40F4FE5")

class VendorReferenceListFields:
    """供应商参考清单 的字段引用。"""
    list_id = FieldRef("PROP_42E0743E8FAD49D6")
    run_id = FieldRef("PROP_8190B49FB8CD4E11")
    supplier_code = FieldRef("PROP_555C3416AC7E41F0")
    list_status = FieldRef("PROP_DE2732631D024540")
    review_note = FieldRef("PROP_CAA1B7CBFED4495D")

class PeriodSupplyDemandFields:
    """分期供需 的字段引用。"""
    balance_id = FieldRef("PROP_22427D782A404FAE")
    run_id = FieldRef("PROP_E20E0AB8ED3543B6")
    material_code = FieldRef("PROP_8E9487C6678F4A99")
    period = FieldRef("PROP_47B255CA64D84CE7")
    opening_qty = FieldRef("PROP_412FC6BF5BE8459B")
    arrival_qty = FieldRef("PROP_A2E766515CDC4933")
    other_inflow_qty = FieldRef("PROP_1A490A399EFB4370")
    required_qty = FieldRef("PROP_B938807687604C40")
    fulfilled_qty = FieldRef("PROP_930A6137C5D64F34")
    other_outflow_qty = FieldRef("PROP_9EAF4CD5C1354BCA")
    closing_qty = FieldRef("PROP_68EBC75CCEB94A64")
    unmet_carry_qty = FieldRef("PROP_05A1C6A780754FAD")

class SlowMovingRiskFields:
    """呆滞风险 的字段引用。"""
    risk_id = FieldRef("PROP_87B2E7614AEF41E1")
    run_id = FieldRef("PROP_8473BD43EDF04639")
    material_code = FieldRef("PROP_9CBFF2ACB29340C6")
    risk_type = FieldRef("PROP_7A148D2CAE694589")
    remaining_qty = FieldRef("PROP_3CD99C3433F8441B")
    reserved_qty = FieldRef("PROP_9A8374D6941B44AF")
    post_period_consumed_qty = FieldRef("PROP_F43188996BE34BDD")
    risk_qty = FieldRef("PROP_38374F63E5EE49A6")
    risk_amount = FieldRef("PROP_198FFA2CC9C34497")
    window_later_commit_qty = FieldRef("PROP_0F6C8A4505404BD5")
    window_later_commit_amount = FieldRef("PROP_3B15F27FEC1C402F")
    pending_check_amount = FieldRef("PROP_4A04B40F402041FB")

class SolutionPlanFields:
    """处理方案 的字段引用。"""
    plan_id = FieldRef("PROP_C1C495314DA345E1")
    run_id = FieldRef("PROP_4FF2717103FF482E")
    plan_code = FieldRef("PROP_4706F6A316D94D9F")
    action_type = FieldRef("PROP_523EC58590D746B7")
    material_code = FieldRef("PROP_4059763188724257")
    adjusted_supply_id = FieldRef("PROP_A29B9AF6C3614EE1")
    action_cost = FieldRef("PROP_3176409F442A477D")
    shortage_flag = FieldRef("PROP_49E59F61FFDC4D4A")
    feasible_reason = FieldRef("PROP_FCA8C5006B544EED")
    risk_id = FieldRef("PROP_F0A53AA692A04733")

class HistoricalCaseFields:
    """历史呆滞案例 的字段引用。"""
    case_id = FieldRef("PROP_A4F76BB9FFFF4F99")
    project_code = FieldRef("PROP_C68C7F820FC549AE")
    old_material_code = FieldRef("PROP_EA5527CD9055425B")
    new_material_code = FieldRef("PROP_23EAEB47D0B84E3D")
    observation_start = FieldRef("PROP_317BD8B525BC41D3")
    observation_end = FieldRef("PROP_AF71B12774C442B0")
    future_demand_check_end = FieldRef("PROP_508E8DD6149F43D8")
    evidence_status = FieldRef("PROP_FC47FFCC09A74DCD")
    rebuilt_opening_qty = FieldRef("PROP_E1FBDE61EE914C6F")
    received_in_qty = FieldRef("PROP_6E992FA4DBC041AF")
    consumed_out_qty = FieldRef("PROP_F989ED54758B4E43")
    rebuilt_closing_qty = FieldRef("PROP_D91EAE06407E4115")
    stock_check_diff = FieldRef("PROP_54A0719A256E4015")
    baseline_risk_qty = FieldRef("PROP_435202A4B1D341CA")
    intervened_risk_qty = FieldRef("PROP_068DCD513EBC4F79")
    simulated_reducible_qty = FieldRef("PROP_EA0808FAC6C44479")

class HistoricalMilestoneFields:
    """历史关键时点 的字段引用。"""
    milestone_id = FieldRef("PROP_864EE986099C4988")
    case_id = FieldRef("PROP_056574831E934F46")
    milestone_type = FieldRef("PROP_DF9741F5DC214E03")
    milestone_date = FieldRef("PROP_7976786BF2734CE6")
    known_info = FieldRef("PROP_554649B10F15443D")

class CauseAttributionFields:
    """原因归因 的字段引用。"""
    attribution_id = FieldRef("PROP_84FEAB071ABD46B8")
    case_id = FieldRef("PROP_700FCD9742BE4B39")
    cause_type = FieldRef("PROP_DF5702B7BF5D4B8C")
    attributed_qty = FieldRef("PROP_B27271E6576C4600")
    evidence_ref = FieldRef("PROP_94FB17D064E04B5F")
    conclusion_level = FieldRef("PROP_A0226F46B1AE4101")

class PreventionRuleFields:
    """预防规则 的字段引用。"""
    rule_id = FieldRef("PROP_AA779797F8F54389")
    source_case_id = FieldRef("PROP_EE221C35E9EA47EA")
    rule_content = FieldRef("PROP_918FF673BDE140B0")
    trigger_condition = FieldRef("PROP_8A974DB8D723436B")
    rule_status = FieldRef("PROP_24AE8A729EAD49C3")

Project.fields = ProjectFields()
Material.fields = MaterialFields()
Supplier.fields = SupplierFields()
SupplierSupplyCondition.fields = SupplierSupplyConditionFields()
UnitConversion.fields = UnitConversionFields()
BomLine.fields = BomLineFields()
EcnRecord.fields = EcnRecordFields()
Demand.fields = DemandFields()
MaterialAuthorization.fields = MaterialAuthorizationFields()
Supply.fields = SupplyFields()
StockMovement.fields = StockMovementFields()
SubstitutionPermission.fields = SubstitutionPermissionFields()
CalculationRun.fields = CalculationRunFields()
ChangeRecord.fields = ChangeRecordFields()
ImpactRecord.fields = ImpactRecordFields()
AllocationRecord.fields = AllocationRecordFields()
SourcingSuggestion.fields = SourcingSuggestionFields()
VendorReferenceList.fields = VendorReferenceListFields()
PeriodSupplyDemand.fields = PeriodSupplyDemandFields()
SlowMovingRisk.fields = SlowMovingRiskFields()
SolutionPlan.fields = SolutionPlanFields()
HistoricalCase.fields = HistoricalCaseFields()
HistoricalMilestone.fields = HistoricalMilestoneFields()
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
        "Project", "OBJ_7AE5DFF0DB4E4B9D", Project, "project_code"
    ),
    "Material": _make_definition(
        "Material", "OBJ_B848CE716F4548AE", Material, "material_code"
    ),
    "Supplier": _make_definition(
        "Supplier", "OBJ_E976C2EE936F4A89", Supplier, "supplier_code"
    ),
    "SupplierSupplyCondition": _make_definition(
        "SupplierSupplyCondition", "OBJ_9180FA747C9B4069", SupplierSupplyCondition, "condition_id"
    ),
    "UnitConversion": _make_definition(
        "UnitConversion", "OBJ_C60B73F633514998", UnitConversion, "conversion_id"
    ),
    "BomLine": _make_definition(
        "BomLine", "OBJ_A91C277B2947438A", BomLine, "bom_line_id"
    ),
    "EcnRecord": _make_definition(
        "EcnRecord", "OBJ_47F89A048D824BC1", EcnRecord, "ecn_id"
    ),
    "Demand": _make_definition(
        "Demand", "OBJ_2021F8E6A121412C", Demand, "demand_uid"
    ),
    "MaterialAuthorization": _make_definition(
        "MaterialAuthorization", "OBJ_61F5DB6A0EC44DEF", MaterialAuthorization, "auth_id"
    ),
    "Supply": _make_definition(
        "Supply", "OBJ_A386F2DEEA5E48F0", Supply, "supply_id"
    ),
    "StockMovement": _make_definition(
        "StockMovement", "OBJ_40B7D2403BCE4376", StockMovement, "movement_id"
    ),
    "SubstitutionPermission": _make_definition(
        "SubstitutionPermission", "OBJ_386211E088EA4D45", SubstitutionPermission, "permission_id"
    ),
    "CalculationRun": _make_definition(
        "CalculationRun", "OBJ_DEC6E937741A4921", CalculationRun, "run_id"
    ),
    "ChangeRecord": _make_definition(
        "ChangeRecord", "OBJ_80F7BE36E155403A", ChangeRecord, "change_id"
    ),
    "ImpactRecord": _make_definition(
        "ImpactRecord", "OBJ_D0FCCC3DFDED45F1", ImpactRecord, "impact_id"
    ),
    "AllocationRecord": _make_definition(
        "AllocationRecord", "OBJ_32FEDA11103F4EC3", AllocationRecord, "allocation_id"
    ),
    "SourcingSuggestion": _make_definition(
        "SourcingSuggestion", "OBJ_B228C6F2EB204295", SourcingSuggestion, "suggestion_id"
    ),
    "VendorReferenceList": _make_definition(
        "VendorReferenceList", "OBJ_E45118AA5AAB406A", VendorReferenceList, "list_id"
    ),
    "PeriodSupplyDemand": _make_definition(
        "PeriodSupplyDemand", "OBJ_72576D393A6D421A", PeriodSupplyDemand, "balance_id"
    ),
    "SlowMovingRisk": _make_definition(
        "SlowMovingRisk", "OBJ_11C4974872B142E3", SlowMovingRisk, "risk_id"
    ),
    "SolutionPlan": _make_definition(
        "SolutionPlan", "OBJ_95B4AB5FB801413F", SolutionPlan, "plan_id"
    ),
    "HistoricalCase": _make_definition(
        "HistoricalCase", "OBJ_0637C548D4E341C8", HistoricalCase, "case_id"
    ),
    "HistoricalMilestone": _make_definition(
        "HistoricalMilestone", "OBJ_261831593DDD4E8B", HistoricalMilestone, "milestone_id"
    ),
    "CauseAttribution": _make_definition(
        "CauseAttribution", "OBJ_DABE4EED184944E0", CauseAttribution, "attribution_id"
    ),
    "PreventionRule": _make_definition(
        "PreventionRule", "OBJ_9DA753C0DF404753", PreventionRule, "rule_id"
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
    "rel_dd2d7c64": RelationDefinition(
        code="rel_dd2d7c64",
        source_object="Supplier",
        source_field="PROP_3C2E13CD62584EC0",
        target_object="SupplierSupplyCondition",
        target_field="PROP_A6BFDAB28FBA4722",
        cardinality="1:N",
        source_name="supplier_supply_conditions",
        target_name="supplier",
    ),
    "rel_cbe08085": RelationDefinition(
        code="rel_cbe08085",
        source_object="Material",
        source_field="PROP_88FE9C4D14D74FED",
        target_object="SupplierSupplyCondition",
        target_field="PROP_40A684CFC1D74C3B",
        cardinality="1:N",
        source_name="supplier_supply_conditions",
        target_name="material",
    ),
    "rel_3ca51511": RelationDefinition(
        code="rel_3ca51511",
        source_object="Material",
        source_field="PROP_88FE9C4D14D74FED",
        target_object="UnitConversion",
        target_field="PROP_35CB48FD1026447B",
        cardinality="1:N",
        source_name="unit_conversions",
        target_name="material",
    ),
    "rel_fb63e040": RelationDefinition(
        code="rel_fb63e040",
        source_object="Material",
        source_field="PROP_88FE9C4D14D74FED",
        target_object="BomLine",
        target_field="PROP_77011B3C1A5B4B24",
        cardinality="1:N",
        source_name="bom_lines",
        target_name="material",
    ),
    "rel_49eaaf16": RelationDefinition(
        code="rel_49eaaf16",
        source_object="Material",
        source_field="PROP_88FE9C4D14D74FED",
        target_object="BomLine",
        target_field="PROP_AC2B560C1CF948EB",
        cardinality="1:N",
        source_name="bom_lines_2",
        target_name="material_2",
    ),
    "rel_a2a1ccbb": RelationDefinition(
        code="rel_a2a1ccbb",
        source_object="Project",
        source_field="PROP_CD202A966D384776",
        target_object="BomLine",
        target_field="PROP_DEFA562B960B4911",
        cardinality="1:N",
        source_name="bom_lines",
        target_name="project",
    ),
    "rel_a6d7db64": RelationDefinition(
        code="rel_a6d7db64",
        source_object="EcnRecord",
        source_field="PROP_FB027A7A032E4029",
        target_object="BomLine",
        target_field="PROP_18E7FA8AFAD1409D",
        cardinality="1:N",
        source_name="bom_lines",
        target_name="ecn_record",
    ),
    "rel_1c93fc78": RelationDefinition(
        code="rel_1c93fc78",
        source_object="Project",
        source_field="PROP_CD202A966D384776",
        target_object="Demand",
        target_field="PROP_87EF44E8831B4EB4",
        cardinality="1:N",
        source_name="demands",
        target_name="project",
    ),
    "rel_bf1db796": RelationDefinition(
        code="rel_bf1db796",
        source_object="Demand",
        source_field="PROP_4E34F4379B5E448D",
        target_object="Demand",
        target_field="PROP_E4123982FD084E7D",
        cardinality="1:N",
        source_name="demands",
        target_name="demand",
    ),
    "rel_1988059c": RelationDefinition(
        code="rel_1988059c",
        source_object="Demand",
        source_field="PROP_4E34F4379B5E448D",
        target_object="Demand",
        target_field="PROP_7FFBC030EAC5421D",
        cardinality="1:N",
        source_name="demands_2",
        target_name="demand_2",
    ),
    "rel_f9742ef0": RelationDefinition(
        code="rel_f9742ef0",
        source_object="Project",
        source_field="PROP_CD202A966D384776",
        target_object="MaterialAuthorization",
        target_field="PROP_8908BE2F18A94053",
        cardinality="1:N",
        source_name="material_authorizations",
        target_name="project",
    ),
    "rel_fa88b8f7": RelationDefinition(
        code="rel_fa88b8f7",
        source_object="Material",
        source_field="PROP_88FE9C4D14D74FED",
        target_object="MaterialAuthorization",
        target_field="PROP_2FE8A78A791C4D75",
        cardinality="1:N",
        source_name="material_authorizations",
        target_name="material",
    ),
    "rel_6e112c67": RelationDefinition(
        code="rel_6e112c67",
        source_object="Material",
        source_field="PROP_88FE9C4D14D74FED",
        target_object="Supply",
        target_field="PROP_980F98CFF1914EAA",
        cardinality="1:N",
        source_name="supplys",
        target_name="material",
    ),
    "rel_99cc9782": RelationDefinition(
        code="rel_99cc9782",
        source_object="CalculationRun",
        source_field="PROP_DB001943EC3F4311",
        target_object="Supply",
        target_field="PROP_1043CD926BC442F9",
        cardinality="1:N",
        source_name="supplys",
        target_name="calculation_run",
    ),
    "rel_baed278c": RelationDefinition(
        code="rel_baed278c",
        source_object="Material",
        source_field="PROP_88FE9C4D14D74FED",
        target_object="StockMovement",
        target_field="PROP_4E9D2BF8F4CE435E",
        cardinality="1:N",
        source_name="stock_movements",
        target_name="material",
    ),
    "rel_e452736a": RelationDefinition(
        code="rel_e452736a",
        source_object="Supply",
        source_field="PROP_C0703050AA954F98",
        target_object="StockMovement",
        target_field="PROP_16862D9F81814425",
        cardinality="1:N",
        source_name="stock_movements",
        target_name="supply",
    ),
    "rel_735b4734": RelationDefinition(
        code="rel_735b4734",
        source_object="Material",
        source_field="PROP_88FE9C4D14D74FED",
        target_object="SubstitutionPermission",
        target_field="PROP_710585274C0248C8",
        cardinality="1:N",
        source_name="substitution_permissions",
        target_name="material",
    ),
    "rel_2c91ff9f": RelationDefinition(
        code="rel_2c91ff9f",
        source_object="Material",
        source_field="PROP_88FE9C4D14D74FED",
        target_object="SubstitutionPermission",
        target_field="PROP_92B19371D7384171",
        cardinality="1:N",
        source_name="substitution_permissions_2",
        target_name="material_2",
    ),
    "rel_29131961": RelationDefinition(
        code="rel_29131961",
        source_object="Project",
        source_field="PROP_CD202A966D384776",
        target_object="SubstitutionPermission",
        target_field="PROP_8FD8B578585744CD",
        cardinality="1:N",
        source_name="substitution_permissions",
        target_name="project",
    ),
    "rel_79a327ee": RelationDefinition(
        code="rel_79a327ee",
        source_object="CalculationRun",
        source_field="PROP_DB001943EC3F4311",
        target_object="ChangeRecord",
        target_field="PROP_AB9BC248078D42DE",
        cardinality="1:N",
        source_name="change_records",
        target_name="calculation_run",
    ),
    "rel_8c72cf24": RelationDefinition(
        code="rel_8c72cf24",
        source_object="BomLine",
        source_field="PROP_BD841408F465426A",
        target_object="ChangeRecord",
        target_field="PROP_7AB5DC2609864E18",
        cardinality="1:N",
        source_name="change_records",
        target_name="bom_line",
    ),
    "rel_29c6677e": RelationDefinition(
        code="rel_29c6677e",
        source_object="SubstitutionPermission",
        source_field="PROP_7B0DB51A503D4277",
        target_object="ChangeRecord",
        target_field="PROP_40840B1C07514A06",
        cardinality="1:N",
        source_name="change_records",
        target_name="substitution_permission",
    ),
    "rel_7ae0a816": RelationDefinition(
        code="rel_7ae0a816",
        source_object="MaterialAuthorization",
        source_field="PROP_53225B75269E41E0",
        target_object="ChangeRecord",
        target_field="PROP_C2C1354E8D404313",
        cardinality="1:N",
        source_name="change_records",
        target_name="material_authorization",
    ),
    "rel_d1e5939d": RelationDefinition(
        code="rel_d1e5939d",
        source_object="CalculationRun",
        source_field="PROP_DB001943EC3F4311",
        target_object="ImpactRecord",
        target_field="PROP_5E11125B517249EE",
        cardinality="1:N",
        source_name="impact_records",
        target_name="calculation_run",
    ),
    "rel_debb1826": RelationDefinition(
        code="rel_debb1826",
        source_object="Project",
        source_field="PROP_CD202A966D384776",
        target_object="ImpactRecord",
        target_field="PROP_E01B7CF02AC442A6",
        cardinality="1:N",
        source_name="impact_records",
        target_name="project",
    ),
    "rel_2c69aafa": RelationDefinition(
        code="rel_2c69aafa",
        source_object="Material",
        source_field="PROP_88FE9C4D14D74FED",
        target_object="ImpactRecord",
        target_field="PROP_C3D8DE9E248B4DCD",
        cardinality="1:N",
        source_name="impact_records",
        target_name="material",
    ),
    "rel_da6f0d07": RelationDefinition(
        code="rel_da6f0d07",
        source_object="Demand",
        source_field="PROP_4E34F4379B5E448D",
        target_object="AllocationRecord",
        target_field="PROP_7195F12D4E064D07",
        cardinality="1:N",
        source_name="allocation_records",
        target_name="demand",
    ),
    "rel_bb9581b1": RelationDefinition(
        code="rel_bb9581b1",
        source_object="Supply",
        source_field="PROP_C0703050AA954F98",
        target_object="AllocationRecord",
        target_field="PROP_56FCA9C2C43C4651",
        cardinality="1:N",
        source_name="allocation_records",
        target_name="supply",
    ),
    "rel_a1bcee02": RelationDefinition(
        code="rel_a1bcee02",
        source_object="SubstitutionPermission",
        source_field="PROP_7B0DB51A503D4277",
        target_object="AllocationRecord",
        target_field="PROP_815C904DACE2473C",
        cardinality="1:N",
        source_name="allocation_records",
        target_name="substitution_permission",
    ),
    "rel_45c5529e": RelationDefinition(
        code="rel_45c5529e",
        source_object="CalculationRun",
        source_field="PROP_DB001943EC3F4311",
        target_object="AllocationRecord",
        target_field="PROP_3AB3EBE3080A431E",
        cardinality="1:N",
        source_name="allocation_records",
        target_name="calculation_run",
    ),
    "rel_70386539": RelationDefinition(
        code="rel_70386539",
        source_object="Material",
        source_field="PROP_88FE9C4D14D74FED",
        target_object="SourcingSuggestion",
        target_field="PROP_138C14ACA8BC4B2F",
        cardinality="1:N",
        source_name="sourcing_suggestions",
        target_name="material",
    ),
    "rel_3401e2be": RelationDefinition(
        code="rel_3401e2be",
        source_object="Supplier",
        source_field="PROP_3C2E13CD62584EC0",
        target_object="SourcingSuggestion",
        target_field="PROP_2212E85AF08B4BDC",
        cardinality="1:N",
        source_name="sourcing_suggestions",
        target_name="supplier",
    ),
    "rel_35f2e654": RelationDefinition(
        code="rel_35f2e654",
        source_object="VendorReferenceList",
        source_field="PROP_42E0743E8FAD49D6",
        target_object="SourcingSuggestion",
        target_field="PROP_1D8F3DAAD40F4FE5",
        cardinality="1:N",
        source_name="sourcing_suggestions",
        target_name="vendor_reference_list",
    ),
    "rel_7b7433f2": RelationDefinition(
        code="rel_7b7433f2",
        source_object="CalculationRun",
        source_field="PROP_DB001943EC3F4311",
        target_object="SourcingSuggestion",
        target_field="PROP_BA67101AF70B46C5",
        cardinality="1:N",
        source_name="sourcing_suggestions",
        target_name="calculation_run",
    ),
    "rel_7d04e7ac": RelationDefinition(
        code="rel_7d04e7ac",
        source_object="Supplier",
        source_field="PROP_3C2E13CD62584EC0",
        target_object="VendorReferenceList",
        target_field="PROP_555C3416AC7E41F0",
        cardinality="1:N",
        source_name="vendor_reference_lists",
        target_name="supplier",
    ),
    "rel_1b2d54e4": RelationDefinition(
        code="rel_1b2d54e4",
        source_object="CalculationRun",
        source_field="PROP_DB001943EC3F4311",
        target_object="VendorReferenceList",
        target_field="PROP_8190B49FB8CD4E11",
        cardinality="1:N",
        source_name="vendor_reference_lists",
        target_name="calculation_run",
    ),
    "rel_be27184c": RelationDefinition(
        code="rel_be27184c",
        source_object="Material",
        source_field="PROP_88FE9C4D14D74FED",
        target_object="PeriodSupplyDemand",
        target_field="PROP_8E9487C6678F4A99",
        cardinality="1:N",
        source_name="period_supply_demands",
        target_name="material",
    ),
    "rel_3361aa1a": RelationDefinition(
        code="rel_3361aa1a",
        source_object="CalculationRun",
        source_field="PROP_DB001943EC3F4311",
        target_object="PeriodSupplyDemand",
        target_field="PROP_E20E0AB8ED3543B6",
        cardinality="1:N",
        source_name="period_supply_demands",
        target_name="calculation_run",
    ),
    "rel_54f83795": RelationDefinition(
        code="rel_54f83795",
        source_object="Material",
        source_field="PROP_88FE9C4D14D74FED",
        target_object="SlowMovingRisk",
        target_field="PROP_9CBFF2ACB29340C6",
        cardinality="1:N",
        source_name="slow_moving_risks",
        target_name="material",
    ),
    "rel_819d4e00": RelationDefinition(
        code="rel_819d4e00",
        source_object="CalculationRun",
        source_field="PROP_DB001943EC3F4311",
        target_object="SlowMovingRisk",
        target_field="PROP_8473BD43EDF04639",
        cardinality="1:N",
        source_name="slow_moving_risks",
        target_name="calculation_run",
    ),
    "rel_652d2991": RelationDefinition(
        code="rel_652d2991",
        source_object="SlowMovingRisk",
        source_field="PROP_87B2E7614AEF41E1",
        target_object="SolutionPlan",
        target_field="PROP_F0A53AA692A04733",
        cardinality="1:N",
        source_name="solution_plans",
        target_name="slow_moving_risk",
    ),
    "rel_858fca76": RelationDefinition(
        code="rel_858fca76",
        source_object="Supply",
        source_field="PROP_C0703050AA954F98",
        target_object="SolutionPlan",
        target_field="PROP_A29B9AF6C3614EE1",
        cardinality="1:N",
        source_name="solution_plans",
        target_name="supply",
    ),
    "rel_e3cf2a48": RelationDefinition(
        code="rel_e3cf2a48",
        source_object="CalculationRun",
        source_field="PROP_DB001943EC3F4311",
        target_object="SolutionPlan",
        target_field="PROP_4FF2717103FF482E",
        cardinality="1:N",
        source_name="solution_plans",
        target_name="calculation_run",
    ),
    "rel_7a92993b": RelationDefinition(
        code="rel_7a92993b",
        source_object="Project",
        source_field="PROP_CD202A966D384776",
        target_object="HistoricalCase",
        target_field="PROP_C68C7F820FC549AE",
        cardinality="1:N",
        source_name="historical_cases",
        target_name="project",
    ),
    "rel_e49e5481": RelationDefinition(
        code="rel_e49e5481",
        source_object="Material",
        source_field="PROP_88FE9C4D14D74FED",
        target_object="HistoricalCase",
        target_field="PROP_EA5527CD9055425B",
        cardinality="1:N",
        source_name="historical_cases",
        target_name="material",
    ),
    "rel_df1ac2f7": RelationDefinition(
        code="rel_df1ac2f7",
        source_object="Material",
        source_field="PROP_88FE9C4D14D74FED",
        target_object="HistoricalCase",
        target_field="PROP_23EAEB47D0B84E3D",
        cardinality="1:N",
        source_name="historical_cases_2",
        target_name="material_2",
    ),
    "rel_e24cebd5": RelationDefinition(
        code="rel_e24cebd5",
        source_object="HistoricalCase",
        source_field="PROP_A4F76BB9FFFF4F99",
        target_object="HistoricalMilestone",
        target_field="PROP_056574831E934F46",
        cardinality="1:N",
        source_name="historical_milestones",
        target_name="historical_case",
    ),
    "rel_0f255887": RelationDefinition(
        code="rel_0f255887",
        source_object="HistoricalCase",
        source_field="PROP_A4F76BB9FFFF4F99",
        target_object="CauseAttribution",
        target_field="PROP_700FCD9742BE4B39",
        cardinality="1:N",
        source_name="cause_attributions",
        target_name="historical_case",
    ),
    "rel_90554ae2": RelationDefinition(
        code="rel_90554ae2",
        source_object="HistoricalCase",
        source_field="PROP_A4F76BB9FFFF4F99",
        target_object="PreventionRule",
        target_field="PROP_EE221C35E9EA47EA",
        cardinality="1:N",
        source_name="prevention_rules",
        target_name="historical_case",
    ),
}

LINK_REL_DD2D7C64 = "rel_dd2d7c64"
LINK_REL_CBE08085 = "rel_cbe08085"
LINK_REL_3CA51511 = "rel_3ca51511"
LINK_REL_FB63E040 = "rel_fb63e040"
LINK_REL_49EAAF16 = "rel_49eaaf16"
LINK_REL_A2A1CCBB = "rel_a2a1ccbb"
LINK_REL_A6D7DB64 = "rel_a6d7db64"
LINK_REL_1C93FC78 = "rel_1c93fc78"
LINK_REL_BF1DB796 = "rel_bf1db796"
LINK_REL_1988059C = "rel_1988059c"
LINK_REL_F9742EF0 = "rel_f9742ef0"
LINK_REL_FA88B8F7 = "rel_fa88b8f7"
LINK_REL_6E112C67 = "rel_6e112c67"
LINK_REL_99CC9782 = "rel_99cc9782"
LINK_REL_BAED278C = "rel_baed278c"
LINK_REL_E452736A = "rel_e452736a"
LINK_REL_735B4734 = "rel_735b4734"
LINK_REL_2C91FF9F = "rel_2c91ff9f"
LINK_REL_29131961 = "rel_29131961"
LINK_REL_79A327EE = "rel_79a327ee"
LINK_REL_8C72CF24 = "rel_8c72cf24"
LINK_REL_29C6677E = "rel_29c6677e"
LINK_REL_7AE0A816 = "rel_7ae0a816"
LINK_REL_D1E5939D = "rel_d1e5939d"
LINK_REL_DEBB1826 = "rel_debb1826"
LINK_REL_2C69AAFA = "rel_2c69aafa"
LINK_REL_DA6F0D07 = "rel_da6f0d07"
LINK_REL_BB9581B1 = "rel_bb9581b1"
LINK_REL_A1BCEE02 = "rel_a1bcee02"
LINK_REL_45C5529E = "rel_45c5529e"
LINK_REL_70386539 = "rel_70386539"
LINK_REL_3401E2BE = "rel_3401e2be"
LINK_REL_35F2E654 = "rel_35f2e654"
LINK_REL_7B7433F2 = "rel_7b7433f2"
LINK_REL_7D04E7AC = "rel_7d04e7ac"
LINK_REL_1B2D54E4 = "rel_1b2d54e4"
LINK_REL_BE27184C = "rel_be27184c"
LINK_REL_3361AA1A = "rel_3361aa1a"
LINK_REL_54F83795 = "rel_54f83795"
LINK_REL_819D4E00 = "rel_819d4e00"
LINK_REL_652D2991 = "rel_652d2991"
LINK_REL_858FCA76 = "rel_858fca76"
LINK_REL_E3CF2A48 = "rel_e3cf2a48"
LINK_REL_7A92993B = "rel_7a92993b"
LINK_REL_E49E5481 = "rel_e49e5481"
LINK_REL_DF1AC2F7 = "rel_df1ac2f7"
LINK_REL_E24CEBD5 = "rel_e24cebd5"
LINK_REL_0F255887 = "rel_0f255887"
LINK_REL_90554AE2 = "rel_90554ae2"

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
    Supplier: _EditEntityEndpoint[Supplier]
    SupplierSupplyCondition: _EditEntityEndpoint[SupplierSupplyCondition]
    UnitConversion: _EditEntityEndpoint[UnitConversion]
    BomLine: _EditEntityEndpoint[BomLine]
    EcnRecord: _EditEntityEndpoint[EcnRecord]
    Demand: _EditEntityEndpoint[Demand]
    MaterialAuthorization: _EditEntityEndpoint[MaterialAuthorization]
    Supply: _EditEntityEndpoint[Supply]
    StockMovement: _EditEntityEndpoint[StockMovement]
    SubstitutionPermission: _EditEntityEndpoint[SubstitutionPermission]
    CalculationRun: _EditEntityEndpoint[CalculationRun]
    ChangeRecord: _EditEntityEndpoint[ChangeRecord]
    ImpactRecord: _EditEntityEndpoint[ImpactRecord]
    AllocationRecord: _EditEntityEndpoint[AllocationRecord]
    SourcingSuggestion: _EditEntityEndpoint[SourcingSuggestion]
    VendorReferenceList: _EditEntityEndpoint[VendorReferenceList]
    PeriodSupplyDemand: _EditEntityEndpoint[PeriodSupplyDemand]
    SlowMovingRisk: _EditEntityEndpoint[SlowMovingRisk]
    SolutionPlan: _EditEntityEndpoint[SolutionPlan]
    HistoricalCase: _EditEntityEndpoint[HistoricalCase]
    HistoricalMilestone: _EditEntityEndpoint[HistoricalMilestone]
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
DEFAULT_WORKSPACE_ID = "01a1441a-18fc-7000-b946-ceb3beed70d0"


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
    "Supplier",
    "SupplierFields",
    "SupplierSupplyCondition",
    "SupplierSupplyConditionFields",
    "UnitConversion",
    "UnitConversionFields",
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
    "StockMovement",
    "StockMovementFields",
    "SubstitutionPermission",
    "SubstitutionPermissionFields",
    "CalculationRun",
    "CalculationRunFields",
    "ChangeRecord",
    "ChangeRecordFields",
    "ImpactRecord",
    "ImpactRecordFields",
    "AllocationRecord",
    "AllocationRecordFields",
    "SourcingSuggestion",
    "SourcingSuggestionFields",
    "VendorReferenceList",
    "VendorReferenceListFields",
    "PeriodSupplyDemand",
    "PeriodSupplyDemandFields",
    "SlowMovingRisk",
    "SlowMovingRiskFields",
    "SolutionPlan",
    "SolutionPlanFields",
    "HistoricalCase",
    "HistoricalCaseFields",
    "HistoricalMilestone",
    "HistoricalMilestoneFields",
    "CauseAttribution",
    "CauseAttributionFields",
    "PreventionRule",
    "PreventionRuleFields",
    "LINK_REL_DD2D7C64",
    "LINK_REL_CBE08085",
    "LINK_REL_3CA51511",
    "LINK_REL_FB63E040",
    "LINK_REL_49EAAF16",
    "LINK_REL_A2A1CCBB",
    "LINK_REL_A6D7DB64",
    "LINK_REL_1C93FC78",
    "LINK_REL_BF1DB796",
    "LINK_REL_1988059C",
    "LINK_REL_F9742EF0",
    "LINK_REL_FA88B8F7",
    "LINK_REL_6E112C67",
    "LINK_REL_99CC9782",
    "LINK_REL_BAED278C",
    "LINK_REL_E452736A",
    "LINK_REL_735B4734",
    "LINK_REL_2C91FF9F",
    "LINK_REL_29131961",
    "LINK_REL_79A327EE",
    "LINK_REL_8C72CF24",
    "LINK_REL_29C6677E",
    "LINK_REL_7AE0A816",
    "LINK_REL_D1E5939D",
    "LINK_REL_DEBB1826",
    "LINK_REL_2C69AAFA",
    "LINK_REL_DA6F0D07",
    "LINK_REL_BB9581B1",
    "LINK_REL_A1BCEE02",
    "LINK_REL_45C5529E",
    "LINK_REL_70386539",
    "LINK_REL_3401E2BE",
    "LINK_REL_35F2E654",
    "LINK_REL_7B7433F2",
    "LINK_REL_7D04E7AC",
    "LINK_REL_1B2D54E4",
    "LINK_REL_BE27184C",
    "LINK_REL_3361AA1A",
    "LINK_REL_54F83795",
    "LINK_REL_819D4E00",
    "LINK_REL_652D2991",
    "LINK_REL_858FCA76",
    "LINK_REL_E3CF2A48",
    "LINK_REL_7A92993B",
    "LINK_REL_E49E5481",
    "LINK_REL_DF1AC2F7",
    "LINK_REL_E24CEBD5",
    "LINK_REL_0F255887",
    "LINK_REL_90554AE2",
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
