# 业务事实卡片（fact-cards）—— 极米四场景本体 POC

> 产出步骤：ontology-modeling 七步流水线第 2 步 ｜ 状态：draft（待人审）
> 抽取纪律：单一来源文档（xgimi-poc-doc.md）内部三源交叉：**§4 规则节 ↔ §11 附录预期结果 ↔ §5 黄金案例演示**（intake-log 判定"文档内部多节交叉可作三源"）。
> 状态标签：confirmed（≥2 源交叉）/ candidate（单源）/ pending（待确认）/ conflict（冲突，本次无）。
> provenance 记法：`B_scenarios/xgimi-poc-doc.md#§小节` 或 `A_schema/<表名>.csv#行`。

## 0. 术语表（原样保留，不做同义改写）

| 术语 | 出处 | 说明 |
|---|---|---|
| 策备 | §2.1 场景24、§4.3 | 电子料全量需求梳理→供应商备料/策备审批；输出授权外需求与供应商参考清单 |
| 点检 | §2.1 场景39、§4.2 | 前后版本 BOM/风险 BOM/替代/授权的自动对比与变化识别 |
| 呆滞 | §2.1 场景51/55、§4.4 | 评估期末无法消耗的剩余物料风险 |
| known_at | §11.2 BOM 表列名 | 记录可见时间（以数据版本号 V0-V3 表达） |
| FACT-SIM | §11.1 各分支表 | 事实记录与模拟记录分别保存的情景隔离约定 |
| 风险 BOM | §4.2、§11.8 测试三 | NPI 阶段经批准的预估 BOM（Z10 v0.9/v1.0） |
| 覆盖关系 | §4.3 ① | 订单/MPS/预测之间的需求去重依据（covered_by） |
| 临时许可 | §5.3.1、§11.4 | 工程批准的一次性旧料使用许可（SUB-01） |
| waterfall | §5.4.3 | 数量变化瀑布图：期初+增项−减项=期末核对 |

## 1. 实体候选（26 个）

### 1.1 基础主数据层（4 个）

| # | 实体 | 属性要点 | provenance | 交叉 | 置信/状态 |
|---|---|---|---|---|---|
| E01 | Project 项目 | project_id(P-Z9)、project_code(100-Z9001)、model_name(Z9)、stage(MP/NPI-DVT/停产)、bom_status_desc、purpose_desc | #§11.2 项目表（4 行全列） | §11.2↔§5.2 案例背景 | high/confirmed |
| E02 | Material 物料 | material_id(300-W6A01/H-WIFI-OLD/UNIT-M)、material_name(WiFi5/6/SoC)、base_uom(颗/盒)、unit_cost(16/20 元/颗，演示成本) | #§11.2（BOM 行子项列）、#§11.5（成本参数）、#§11.8 测试六 | §11.2↔§11.5↔§5.2 | high/confirmed |
| E03 | UnitConversion 单位换算 | material_id、from_uom(盒)、to_uom(颗)、ratio(100)、approval_status、evidence_status | #§11.8 测试六（"批准换算1盒＝100颗""移除换算依据后提示缺证"） | §4.1 约定"单位一致"↔测试六 | high/confirmed |
| E04 | Supplier 供应商 | supplier_id(V-WLINK)、supplier_name、purchasing_group(206) | #§11.5 供应商表 | §11.5↔§11.8 测试一（双供应商） | high/confirmed |

### 1.2 BOM 与变更层（2 个）

| # | 实体 | 属性要点 | provenance | 交叉 | 置信/状态 |
|---|---|---|---|---|---|
| E05 | BomLine BOM 行 | line_id(L-Z9-01)、bom_type(standard/risk/maintenance)、version(v3.2)、parent_material_id、child_material_id、project_id、qty_per、base_qty、yield_rate、effective_from/to、known_at、evidence_status | #§11.2 BOM 行表（5 行全列）、#§11.8 测试三/五 | §11.2↔§4.2↔§5.3.1 | high/confirmed |
| E06 | EcnRecord 工程变更记录 | ecn_id(H-ECN-01)、project_id、change_desc、publish_date、effective_date、approval_status、evidence_status、known_at | #§11.1 V1 行、#§11.6（H-ECN-01 引用编号）、#§5.4.6（缺证版保留编号移除批准文件） | §11.1↔§11.6↔§5.4.6 | high/confirmed |

> 说明：附录 BOM 证据表为**行级**（无独立 BOM 头表），故不单设 BomHeader；bom_type/version 上提到行（§4.2"标准 BOM 与风险 BOM 分开比较"）。主案例 ECN 编号未给出 → open_questions OQ-10。

### 1.3 需求与授权层（2 个）

| # | 实体 | 属性要点 | provenance | 交叉 | 置信/状态 |
|---|---|---|---|---|---|
| E07 | Demand 需求 | demand_id+demand_version 复合主键（DEM-Z9-DEC v1/v2"替换不追加"）、project_id、need_date、demand_qty、source_type(MPS/order/forecast/service)、covered_by_demand_id（ORD-Z9-NOV covered_by=DEM-Z9-NOV）、status(confirmed/superseded/reference)、known_at、package_id | #§11.2 需求表（6 行全列含来源及计算口径） | §11.2↔§4.3 ①↔§5.2（覆盖关系叙述） | high/confirmed |
| E08 | MaterialAuthorization 物料授权 | auth_id+auth_version 复合主键（授权 v2 替换 v1）、material_id、project_id、covered_qty(10,000/6,000)、approval_status、effective_from、known_at、package_id | #§11.8 测试四（授权 v1/v2 与待授权计算）、#§2.1 场景24（卫国策备表未授权数量） | 测试四↔§4.3 步骤6"授权不作为物理供给"↔§8 红线 | high/confirmed |

### 1.4 供给层（3 个）

| # | 实体 | 属性要点 | provenance | 交叉 | 置信/状态 |
|---|---|---|---|---|---|
| E09 | Supply 供给记录 | supply_id(PS-1001/SIM-W6-9000/ST-R1)、material_id、supply_type(available_stock/frozen_stock/open_order/simulated_purchase)、qty、available_date、restriction_desc、po_id、scenario_tag(FACT/SIM)、package_id、known_at | #§11.3 供给表（6 行全列+限制列）、#§11.1（9,000 颗模拟供给不得写入 FACT）、#§11.8 测试八（ST-R1） | §11.3↔§11.1↔§4.4 | high/confirmed |
| E10 | PurchaseOrder 采购订单 | po_id(PO-R1/PS-3002 订单)、material_id、order_qty、cumulative_receipt_qty、cancelled_qty、closed_unreceived_qty、confirmed_arrival_date、cancel_deadline(2026-10-15)、cancel_fee_per_unit(1元/颗)、cancel_limit_qty(最多2,000)、postpone_allowed、postpone_deadline(2027-01-15)、postpone_fee(0)、status、package_id、known_at | #§4.3 ③（未收货量公式）、#§11.3 PS-3002 行（取消/延期条件 V0 书面证据）、#§11.8 测试八 | §4.3↔§11.3↔§11.7 方案表 S1/S2 | high/confirmed |
| E11 | StockMovement 库存流水 | movement_id、case_id、material_id、movement_type(receipt/issue/return/scrap/adjust/transfer)、movement_qty（入库为正出库为负）、movement_date、evidence_status、known_at | #§11.6 实际流水（"每条实际记录在对应日期发生后才可用于事实还原"）、#§5.4.3 waterfall 公式 | §11.6↔§4.5 ①↔§5.4.3 | high/confirmed |

### 1.5 替代与供应商条件层（2 个）

| # | 实体 | 属性要点 | provenance | 交叉 | 置信/状态 |
|---|---|---|---|---|---|
| E12 | SubstitutionPermission 替代与转用许可 | permission_id(SUB-01/02)、permission_type(substitution/transfer)、original_material_id、substitute_material_id、applicable_project_id、conversion_ratio(1:1)、batch_limit_qty(6,000)、approved_usage_qty(2,000)、target_supply_id(PS-3002)、effective_from/to(11-01~11-30)、approval_status、known_at、package_id | #§11.4 替代表（SUB-01/02 全列）、#§5.2（临时许可叙述） | §11.4↔§5.2↔§11.8 测试七 | high/confirmed |
| E13 | SupplierSupplyCondition 供应商供货条件 | condition_id、supplier_id、material_id、lead_time_weeks(8 周)、moq(5,000)、order_multiple(1,000)、share_ratio(100%/70%/30%)、approval_status | #§11.5 供应商表、#§11.8 测试一（双供应商 70/30） | §11.5↔§11.8 测试一/测试十 | high/confirmed |

### 1.6 运行底座层（3 个）

| # | 实体 | 属性要点 | provenance | 交叉 | 置信/状态 |
|---|---|---|---|---|---|
| E14 | CalculationRun 计算运行快照 | run_id、package_id、scenario_tag(FACT/SIM)、observed_at(观察时间)、input_version、rule_version、evaluation_period_from/to(2026-11-01~12-31)、run_type(inspection/sourcing/risk_simulation/historical_replay) | #§4.1（"每次运行保存输入版本、观察时间、规则版本和情景编号"）、#§11.1（V2 为策备运行快照） | §4.1↔§11.1↔§7（数据追溯与复算 LIVE） | high/confirmed |
| E15 | DataVersion 数据版本 | version_id(V0-V3)、visible_at(2026-09-28 06:00 等)、change_summary、package_id | #§11.1 版本表（4 行全列） | §11.1↔§4.1 时间明确 | high/confirmed |
| E16 | MaterialRequirement 物料需求汇总 | req_id、run_id、material_id、gross_qty(毛需求)、substitute_satisfied_qty(替代满足)、allocated_supply_qty(已分配供给)、authorized_coverage_qty(授权覆盖)、unit_price、remaining_material_qty(衍生)、physical_gap_qty(衍生)、pending_auth_qty(衍生)、pending_auth_amount(衍生) | #§4.3 ②④（毛需求/替代满足/剩余/缺口公式）、#§11.8 测试四（毛需求 18,000/授权 10,000/待授权 8,000/物理缺口 15,000）、#§5.3.2（Z9 24,000/15,000/9,000） | §4.3↔§11.7↔§11.8 测试四 | high/confirmed |

### 1.7 点检层（2 个）

| # | 实体 | 属性要点 | provenance | 交叉 | 置信/状态 |
|---|---|---|---|---|---|
| E17 | InspectionChange 点检变化记录 | change_id、change_type(material_add/material_remove/usage_change/uom_change/effective_date_change/substitution_change/auth_qty_change)、object_type(bom/risk_bom/substitution/authorization)、detection_run_id、before_line_id、after_line_id、before_value、after_value、judgment_basis、impact_desc、known_at | A_schema/inspection-rules.csv（6 行判断方法全列）、#§4.2 处理步骤/输出 | CSV↔§4.2↔§5.3.1（换料变化四条影响） | high/confirmed |
| E18 | ReviewTask 复核任务 | task_id、change_id、task_desc、status(open/cancelled/adjusted/retained/closed)、resolution_basis | #§4.2 输出（"生成影响明细和复核任务，保留判断依据及处理记录"）、#§5.4.7（"任务只有在收到取消、调整或明确保留的处理依据后才能关闭"） | §4.2↔§5.4.7↔§5.3.1（"12月到货4,000颗旧料需复核采购安排"） | high/confirmed |

### 1.8 策备输出层（2 个）

| # | 实体 | 属性要点 | provenance | 交叉 | 置信/状态 |
|---|---|---|---|---|---|
| E19 | SourcingSuggestion 策备建议 | suggestion_id、run_id、material_id、supplier_id、list_id、allocated_qty(8,400/3,600)、suggested_qty(9,000/4,000 取整后)、rounding_extra_qty(1,000 单列)、expected_arrival_date(2027-01-20/02-03) | #§4.3 ⑤（建议量公式与取整增量单列）、#§11.8 测试一（先份额后取整不二次优化） | §4.3↔§11.8 测试一↔测试十 | high/confirmed |
| E20 | VendorReferenceList 供应商参考清单 | list_id、run_id、supplier_id、status(draft/internal_review/archived)、created_at | #§3 流程③（"生成供内部审核的参考清单…不等同于采购订单"）、#§8（默认不外发） | §3↔§8↔§5.3.2（V2 清单叙述） | high/confirmed |

### 1.9 呆滞模拟层（3 个）

| # | 实体 | 属性要点 | provenance | 交叉 | 置信/状态 |
|---|---|---|---|---|---|
| E21 | PeriodSupplyBalance 分期供需 | balance_id、run_id、material_id、period_label(11月/12月)、beginning_qty、arrival_qty、other_inflow_qty、demand_satisfied_qty、other_outflow_qty、required_qty、unmet_demand_qty(衍生)、ending_qty(衍生) | #§4.4 ①（期初/期末/未满足三公式）、#§11.7 预期结果表（三期间新料/旧料结余） | §4.4↔§11.7↔§5.3.3 | high/confirmed |
| E22 | SlowMovingRisk 呆滞风险 | risk_id、run_id、material_id、risk_source_type(stock/open_order)、ending_remaining_qty、reserved_qty、post_period_consumed_qty、unit_cost、risk_qty(衍生)、risk_amount(衍生) | #§4.4 ②（风险量公式）、④（风险金额=Σ数量×单价）、#§11.7（S0 旧料 4,000×16=64,000、新料 1,200×20=24,000） | §4.4↔§11.7↔§5.3.3 | high/confirmed |
| E23 | SolutionPlan 处理方案 | plan_id、run_id、plan_code(S0/S1/S2)、action_type(none/cancel/postpone/substitute_consume/transfer/reduce)、target_po_id、action_qty(2,000)、action_cost(2,000)、window_risk_amount(56,000)、post_window_commitment_amount(64,000)、shortage_flag、feasible_flag、baseline_risk_qty(8,000)、intervened_risk_qty(2,000)、reducible_qty(衍生)、total_exposure_amount(衍生) | A_schema/scenario-recompute.csv（4 措施对数据调整全列）、#§4.4 ③④、#§11.7 方案表（S0/S1/S2 全列）、#§4.5 ③（可减少风险量公式） | CSV↔§4.4↔§11.7↔§5.4.5（6,000=8,000−2,000） | high/confirmed |

### 1.10 历史层（4 个）

| # | 实体 | 属性要点 | provenance | 交叉 | 置信/状态 |
|---|---|---|---|---|---|
| E24 | HistoricalCase 历史呆滞案例 | case_id、package_id、project_id(P-X8)、material_id、observation_period_from/to(2025-07-01~09-30)、stagnant_qty(8,000)、risk_formed_date(07-15)、decision_observed_date(07-15)、evidence_status(complete/missing)、unattributed_qty(衍生) | #§11.6（观察区间/预期结果"风险首次可识别日 7-15"）、#§5.4.2（三时点表） | §11.6↔§4.5↔§5.4 | high/confirmed |
| E25 | CauseAttribution 原因归因 | attribution_id、case_id、cause_type、attributed_qty、evidence_desc、is_primary | #§4.5 ④（"各主要原因对应数量之和≤案例呆滞总量，无法确认的部分保留为未归因"）、#§5.4.6（三层结论：不应把全部 8,000 归为停采过晚） | §4.5↔§5.4.6↔§8 红线 | high/confirmed |
| E26 | PreventionRule 预防规则 | rule_id、source_case_id、rule_text（"已批准的工程变更导致未来旧料需求减少时，检查关联的未到货订单…"）、trigger_timing（变更已获知且影响能判断时，不等 BOM 生效）、status(draft/review/trial/active)、close_basis | #§5.4.7（规则草案+审核试运行+关闭依据）、#§4.5 输出 | §5.4.7↔§4.5↔§5.5 幕五 | high/confirmed |

> E26 收口：PreventionRule 与 E17 InspectionChange 不合并——前者是"沉淀的检查规则"（有独立状态机 draft→trial→active），后者是"一次点检发现的变化记录"。

## 2. 关系候选（links，方向=持有方 → 目标）

| 关系 | 基数 | 业务含义 | provenance | 状态 |
|---|---|---|---|---|
| BomLine → Material（material=子项主关联）、→ Project | N:1 | 行的子项物料与所属项目；父项引用以 parent_material_id 属性承载（双链取舍见 model.yaml assumptions A7） | #§11.2 BOM 行表 | confirmed |
| EcnRecord → Project | N:1 | 变更所属项目 | #§11.6 | confirmed |
| Demand → Project；covered_by_demand_id 属性（不建 links，目标为复合主键，A7） | N:1 | 需求归属；覆盖关系去重依据 | #§11.2 需求表 covered_by 列 | confirmed |
| MaterialAuthorization → Material、→ Project | N:1 | 授权对象=物料×整机项目（卫国策备表口径） | #§2.1 场景24、测试四 | confirmed |
| Supply → Material、→ PurchaseOrder | N:1 | 订单类供给指向订单条款 | #§11.3（PS-2001/3002 类型=订单） | confirmed |
| SubstitutionPermission → Material（material=原料主关联）、→ Project、→ Supply；替代料引用以属性承载（A7） | N:1 | 原料/新料/适用项目/绑定供给批次 | #§11.4 | confirmed |
| SupplierSupplyCondition → Supplier、→ Material | N:1 | 供应商×物料供货条件 | #§11.5 | confirmed |
| CalculationRun → DataVersion（version_id） | N:1 | 运行使用的输入版本 | #§4.1、#§11.1 | confirmed |
| MaterialRequirement / SourcingSuggestion / VendorReferenceList / PeriodSupplyBalance / SlowMovingRisk / SolutionPlan → CalculationRun | N:1 | 计算产物归属运行（可追溯复算） | #§4.1 结果可追溯 | confirmed |
| SourcingSuggestion → Material、→ Supplier、→ VendorReferenceList | N:1 | 建议归属 | #§4.3 ⑤ | confirmed |
| SolutionPlan → PurchaseOrder（po_id） | N:1 | 措施作用对象 | #§11.7 S1/S2 目标 PS-3002 | confirmed |
| InspectionChange → CalculationRun（run_id）、→ BomLine（line_id=后版本行主关联）；前版本行以 before_line_id 属性承载（A7） | N:1 | 变化由哪次点检运行发现、前后版本行 | #§4.2 步骤2 | confirmed |
| ReviewTask → InspectionChange | N:1 | 任务由变化生成 | #§4.2 步骤4 | confirmed |
| HistoricalCase → Project、→ Material；StockMovement → HistoricalCase、→ Material | N:1 | 案例归属与流水还原 | #§11.6 | confirmed |
| CauseAttribution → HistoricalCase；PreventionRule → HistoricalCase（case_id） | N:1 | 归因/规则挂案例 | #§4.5、#§5.4.7 | confirmed |

## 3. 规则候选

### 3.1 derived_property（13 条，全部文档公式原文）

| # | 规则 | 公式（文档原文） | provenance | 方言内? | 状态 |
|---|---|---|---|---|---|
| R01 | 标准用量 | 标准用量 = BOM 行用量 ÷ BOM 基准数量 | #§4.2、CSV inspection-rules 用量行 | ✅ | confirmed |
| R02 | 订单未收货量 | max(订单数量−累计有效收货量−已取消量−已关闭未收余量, 0) | #§4.3 ③ | ✅ MAX | confirmed |
| R03 | 剩余新料需求 | 剩余新料需求 = 物料毛需求 − 替代满足量 | #§4.3 ④ | ✅ | confirmed |
| R04 | 新料缺口 | max(剩余新料需求 − 已分配新料供给, 0) | #§4.3 ④ | ✅ | confirmed |
| R05 | 待授权数量 | max(毛需求 − 已授权覆盖量, 0)（测试四：18,000−10,000=8,000） | #§11.8 测试四 | ✅ | confirmed |
| R06 | 待授权参考金额 | 待授权数量 × 参考单价（8,000×20=160,000） | #§11.8 测试四、#§2.1 场景24（数量+价格+总金额） | ✅ | confirmed |
| R07 | 分期期末量 | 期初+本期有效到货+其他有效流入−实际满足需求量−其他有效流出 | #§4.4 ① | ✅ | confirmed |
| R08 | 分期未满足需求 | 本期应满足需求 − 实际满足需求量 | #§4.4 ① | ✅ | confirmed |
| R09 | 期末风险量 | max(评估期末剩余量−经确认的保留量−经证实的期后消耗量, 0) | #§4.4 ② | ✅ | confirmed |
| R10 | 风险金额 | 风险数量 × 对应成本单价 | #§4.4 ④ | ✅ | confirmed |
| R11 | 方案合计敞口 | 窗口内风险金额 + 窗口后未消化承诺（S2：24,000+64,000=88,000 不得宣称消除 64,000） | #§11.7 方案表说明 | ✅ | confirmed |
| R12 | 模拟可减少风险量 | max(不干预风险量 − 干预后风险量, 0)（8,000−2,000=6,000） | #§4.5 ③、#§5.4.5 | ✅ | confirmed |
| R13 | 未归因数量 | max(呆滞总量 − Σ各原因归因数量, 0)（防重复归因红线量化） | #§4.5 ④、#§8 | ✅ 单跳反向聚合 SUM | confirmed |

### 3.2 超方言计算（登记 open_questions，禁止发明函数）

| 文档计算 | 超出原因 | 处置 |
|---|---|---|
| 建议量 = 按订购倍数向上取整〔max(分配量, MOQ)〕（§4.3 ⑤） | CEILING 不在白名单 | OQ-01 运行时契约 |
| 多层 BOM 按层展开再汇总（良率逐层计入）（§4.3 ②、测试五 20,615） | 迭代展开 | OQ-02 |
| 需求去重覆盖关系选取/冲减（§4.3 ①） | 条件分支 | OQ-03 |
| 供给分配优先级与稳定排序（先许可旧料后新料、按日期/编码排序）（§4.3 ③④、§11.3） | 排序算法 | OQ-04 |
| 分期滚动结转（期初=上期期末、未满足结转不重复累计）（§4.4 ①） | 跨行引用 | OQ-05 |
| 替代资格多条件检查（方向/项目/批次/有效期/比例/上限）（§4.3 ③、§4.4 ④） | 条件分支 | OQ-06 |
| 方案措施对数据调整后完整重算（scenario-recompute.csv） | 动作域 | OQ-07 |
| 授权生效版本选择（v2 替换 v1）（测试四） | 版本选择 | OQ-08 |
| "各原因之和≤总量"约束校验 | 约束语义（M3 admission 候选） | OQ-09 |

### 3.3 trigger（5 条）

| # | 规则 | 条件→动作 | provenance | 状态 |
|---|---|---|---|---|
| R14 | 呆滞风险触发 | risk_qty > 0 → 生成风险复核（"风险阈值为未覆盖数量大于 0，一次有效评估即可触发"） | #§11.6 预期结果 | confirmed |
| R15 | ECN 预防检查触发 | 工程变更已批准且证据完整 → 检查关联未到货订单（"变更已获知且影响能够判断时触发，不能等 BOM 生效"） | #§5.4.7 | confirmed |
| R16 | 授权变化重核算 | change_type=授权数量变化 → 重新核算待授权需求或策备建议 | A_schema/inspection-rules.csv#授权数量变化行 | confirmed |
| R17 | 替代关系变化复核 | change_type=替代关系变化 → 检查原分配方案有效性（"失效替代关系保留问题记录，不得参与替代计算"） | #§4.2 异常处理、CSV | confirmed |
| R18 | 冻结供给排除 | supply_type=质检冻结 → 不参与供给分配并单列待核查 | #§11.3 PS-1002 行、#§4.3 | confirmed |

## 4. 枚举候选

| 字段 | 枚举值 | provenance |
|---|---|---|
| Project.stage | MP / NPI-DVT / 停产(历史) | #§11.2（量产 MP、NPI-DVT、停产（历史）） |
| BomLine.bom_type | standard / risk / maintenance | #§4.2（标准与风险分开比较）、#§11.8 测试七（维修 BOM） |
| Demand.source_type | MPS / order / forecast / service | #§11.2（已确认 MPS/客户订单/早期预测）、#§11.8 测试七（维修需求） |
| Supply.supply_type | available_stock / frozen_stock / open_order / simulated_purchase | #§11.3（可用库存/质检冻结库存/已确认未收货订单）、#§11.1（模拟供给） |
| scenario_tag | FACT / SIM | #§11.1 |
| InspectionChange.change_type | 7 值 | A_schema/inspection-rules.csv |
| SolutionPlan.action_type | none/cancel/postpone/substitute_consume/transfer/reduce | A_schema/scenario-recompute.csv + S0 不处理 |
| movement_type | receipt/issue/return/scrap/adjust/transfer | #§11.6（领用、退货、报废、其他调整；§4.5 调拨） |
| evidence_status | complete / missing | #§5.4.6（缺证版）、#§11.8 测试六 |

## 5. conflicts

无（brief.yaml known_conflicts 为空；intake-log"未发现跨文档口径冲突"）。唯一口径疑点已入 open_questions（OQ-10 ECN 编号、OQ-11 清单外发审批）。
