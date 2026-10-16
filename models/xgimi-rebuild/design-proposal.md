# xgimi-rebuild 本体设计提案（design-proposal）

> 版本：1-draft ｜ 呈审人：FDE（agent，ontology-modeling v0.3.6 流水线）｜ 待确认人：____
> 确认记录：____（确认人/日期/修改意见摘要——每次返改追加一行）
>
> 本提案由 models/xgimi-rebuild/modeling-brief/ 从零合成（charter.md + fact-cards.md 为支撑证据）；命名对照 seeds/glossary.md 建议名。
> **确认点②硬关卡：本文件与骨架拓扑经 FDE 逐表确认前，不生成完整 model.yaml、不跑 lint/CQ/编译。**

## 一、场景回顾

以 BOM 为极米业务世界模型主轴，让每一次 BOM 变化被确定性捕获、沿需求与供给链穿透传播、转化为受控的策备与去库存决策，并让历史教训沉淀为可自动触发的预防规则——一套本体对象支撑四个 POC 场景：点检变化识别（39）、电子料需求与策备计算（24）、呆滞模拟与方案比较（51）、历史呆滞还原（55）；POC 全程只读，不写回 SAP/PDM/SRM。

CQ 清单（12 条，全文见 charter.md §二）：cq-001 点检变化与影响 ｜ cq-002 毛需求展开溯源 ｜ cq-003 供给分配与缺口 ｜ cq-004 授权外需求 ｜ cq-005 供应商建议量与取整 ｜ cq-006 期末呆滞风险 ｜ cq-007 处理方案对比 ｜ cq-008 历史呆滞形成还原 ｜ cq-009 历史干预模拟 ｜ cq-010 原因归因分布 ｜ cq-011 计算运行追溯复算 ｜ cq-012 工程变更触发预防规则。

## 二、实体设计（共 25 个）

> 主键建议 STRING 业务编码或复合自然键（生成式编码的输出类实体用复合键，见假设 A-06）；字段类型为推断（OQ-01）。

| # | 实体（英文） | 展示名 | 主键 | 关键字段（≤5，含类型） | 一句话职责 | 来源 |
|---|---|---|---|---|---|---|
| E01 | Project | 项目 | project_code | project_name STRING / model STRING（机型）/ stage STRING（量产/NPI-DVT/停产）/ bom_status_desc STRING | 机型/产品线，需求和 BOM 的挂载主体 | §4.1、§11.2 |
| E02 | Material | 物料 | material_code | material_name STRING / base_uom STRING（基本单位）/ cost_unit_price DOUBLE（演示成本 元/颗） | 最小跟踪单位，汇总与库存跟踪的锚点 | §4.1、§11.2/11.5 |
| E03 | BomLine | BOM 行 | bom_line_id | bom_type STRING（标准/风险/维修）/ bom_version STRING / line_qty DOUBLE（行用量）/ yield_rate DOUBLE（良率）；备注：base_qty、valid_from/to、known_at 阶段⑤补全 | 机型结构清单行：层级用量、损耗与生效期，点检与展开的载体 | §4.1、§11.2、inspection-rules.csv |
| E04 | EcnRecord | 工程变更记录 | ecn_id | ecn_desc STRING / publish_time TIMESTAMP / effective_date DATE / evidence_status STRING（完整/缺失） | 换料等工程变更的发布与批准记录，BOM 版本变化的驱动源 | §11.1、§11.7、§5.4 |
| E05 | Demand | 需求 | demand_id + record_version（复合） | demand_type STRING（MPS/客户订单/预测/维修）/ required_qty INTEGER / required_date DATE / is_estimate BOOLEAN（估算不入确定需求） | 各项目需要数量与日期，覆盖与替换关系明确 | §4.1、§11.2 |
| E06 | MaterialAuthorization | 物料授权 | project_code + material_code + auth_version（复合） | authorized_qty INTEGER（覆盖台数/颗数）/ approve_date DATE / status STRING | 整机料号采购授权（策备表域），授权≠物理供给 | §2.1、§4.3⑥、测试四 |
| E07 | Supply | 供给 | supply_id | supply_type STRING（可用库存/质检冻结/已确认未收货订单）/ qty INTEGER / available_date DATE / branch STRING（FACT/SIM）；备注：取消截止日/取消费/延期条件字段阶段⑤落 | 可用库存、冻结与在途订单的统一供给记录 | §4.1、§11.3 |
| E08 | StockMovement | 库存收发流水 | movement_id | movement_type STRING（收货/其他入库/消耗/其他出库，分类互斥）/ qty INTEGER / movement_date DATE / source_supply_id STRING（可空） | 出入库事实流水，waterfall 核对与收货转库存的依据 | §4.5①、§11.7、测试八 |
| E09 | Supplier | 供应商 | supplier_code | supplier_name STRING / purchase_group STRING | 具备供货资格的供应商主体 | §11.5 |
| E10 | SupplierSupplyCondition | 供应商供货条件 | supplier_code + material_code（复合） | lead_time_days INTEGER / moq INTEGER（最小起订量）/ order_multiple INTEGER（订购倍数）/ quota_ratio DOUBLE（份额%） | 交期、起订量、倍数与配额约定 | §4.1、§11.5 |
| E11 | SubstitutionPermission | 替代与转用许可 | permission_id | permission_type STRING（临时许可替代/售后转用）/ conversion_ratio DOUBLE（1:1 等）/ valid_from DATE / valid_to DATE；备注：批次限定与批准上限字段阶段⑤落 | 物料可替换及批准条件，替代计算的准入门槛 | §4.1、§11.4 |
| E12 | UnitConversion | 单位换算 | material_code + alt_unit（复合） | alt_unit STRING / factor DOUBLE（1 盒=100 颗）/ approval_status STRING | 已确认的单位换算关系，原始值保留计算用换算 | §4.1 约定、测试六 |
| E13 | CalculationRun | 计算运行 | run_id | known_at TIMESTAMP（观察时点）/ data_version STRING（V0—V3）/ branch STRING（FACT/SIM）/ scenario_no STRING；备注：rule_version、评估期间起止阶段⑤落 | 一次计算的运行身份：输入版本/观察时点/规则版本/情景，追溯与复算的锚 | §4.1、§11.1 |
| E14 | ChangeRecord | 变化记录 | change_id | change_type STRING（物料增删/用量/单位/生效日期/替代关系/授权数量）/ old_value STRING / new_value STRING / check_advice STRING（后续检查） | 点检对比产出的单条变化（六类判断） | §4.2、inspection-rules.csv |
| E15 | ImpactRecord | 影响记录 | impact_id | evidence_refs STRING（多条依据）/ review_status STRING（待复核/已收处理依据/关闭）/ impact_scope STRING | 变化波及对象的合并明细与复核任务载体 | §4.2、§5.3.1 |
| E16 | AllocationRecord | 供需分配记录 | allocation_id | allocated_qty INTEGER / priority_seq INTEGER（稳定排序）/ reserved_flag BOOLEAN | 一批供给对一个需求（含替代路径）的分配明细，保证可展开复算 | §4.3③④、§11.3 |
| E17 | SourcingSuggestion | 策备建议 | run_id + material_code + supplier_code（复合） | allocated_qty INTEGER / suggested_qty INTEGER（取整后建议量）/ rounding_extra_qty INTEGER（取整额外量）/ eta_meets_demand BOOLEAN（交期满足） | 对剩余缺口的采购建议量（MOQ/倍数取整、交期检查） | §4.3⑤、§11.5/11.6 |
| E18 | VendorReferenceList | 供应商参考清单 | run_id + supplier_code（复合） | list_status STRING（草稿/内部审核，默认不外发）/ review_note STRING | 按供应商整理的建议参考清单（≠采购订单） | §3.2③、§5.3.3 |
| E19 | PeriodSupplyDemand | 分期供需 | run_id + material_code + period（复合） | opening_qty INTEGER（期初）/ arrival_qty INTEGER（有效到货）/ fulfilled_qty INTEGER（满足需求）/ closing_qty INTEGER（期末）/ unmet_carry_qty INTEGER（未满足结转） | 按评估期逐期推演的供需行，呆滞与逾期口径的载体 | §4.4①、§11.6 |
| E20 | SlowMovingRisk | 呆滞风险 | run_id + material_code（复合） | risk_type STRING（库存风险/未到货订单风险）/ remaining_qty INTEGER（期末剩余）/ reserved_qty INTEGER（经确认保留）/ risk_qty INTEGER（衍生）；备注：risk_amount、窗口后承诺、冻结待核查金额阶段⑤落 | 评估期末无法消耗的剩余风险，区分库存与在途 | §4.4②、§11.6 |
| E21 | SolutionPlan | 处理方案 | run_id + plan_code（复合，S0/S1/S2…） | action_type STRING（不处理/取消或减量/延期/替代消耗/跨项目转用）/ action_cost DOUBLE（行动成本）/ shortage_flag BOOLEAN（是否缺料）/ feasible_reason STRING | 对呆滞风险的处置方案，调整数据后同套公式重算对比 | §4.4③④、scenario-recompute.csv |
| E22 | HistoricalCase | 历史呆滞案例 | case_id | observation_start DATE / observation_end DATE / evidence_status STRING（完整/缺证）/ stock_check_diff INTEGER（核对差异）；备注：还原期末库存、模拟可减少量为衍生字段 | 独立历史分析案例：还原、归因与可干预结论的宿主 | §4.5、§11.7 |
| E23 | HistoricalMilestone | 历史关键时点 | case_id + milestone_type（复合） | milestone_date DATE / milestone_type STRING（风险形成/取消窗口截止/观察决策点/结果核实）/ known_info STRING（当时已知） | 案例时间线锚点，回答"何时已经知道什么" | §4.5③、§11.7 |
| E24 | CauseAttribution | 原因归因 | case_id + cause_type（复合） | attributed_qty INTEGER / evidence_ref STRING / conclusion_level STRING（可确认事实/待核实/不可下结论） | 呆滞原因结论行：归因数量受总量上限约束，余量保留未归因 | §4.5④、§5.4 |
| E25 | PreventionRule | 预防规则 | rule_id | rule_content STRING / trigger_condition STRING（变更已获知且影响可判断时）/ rule_status STRING（草案/审核/试运行/启用） | 历史教训沉淀的检查规则，审核试运行后才启用 | §4.5 输出、§5.4 |

## 三、关系设计（共 49 条）

> 语义名即 DSL links 的 name 与拓扑连线标签（v0.3.4 纪律）；基数以持有方（"从"）视角标注；"（可空）"= 变体分支只填其一。

| # | 从 → 到 | 关系语义名 | 基数 | 业务含义（一句话） | 来源 |
|---|---|---|---|---|---|
| R01 | BOM 行 → 物料 | 父项物料 | n:1 | 该行描述父项物料的一个组件构成 | §11.2 父项列 |
| R02 | BOM 行 → 物料 | 子项物料 | n:1 | 该行挂载被使用的子项物料 | §11.2 子项列 |
| R03 | BOM 行 → 项目 | 隶属项目 | n:1 | BOM 行归属机型项目 | §4.1 |
| R04 | BOM 行 → 工程变更记录 | 产生于变更 | n:1 | 行的增改（如换料新旧行）由哪次 ECN 驱动 | §11.1/§11.2 |
| R05 | 需求 → 项目 | 归属项目 | n:1 | 需求按项目归口汇总 | §11.2 |
| R06 | 需求 → 需求 | 被需求覆盖 | n:1 | 订单/预测被上位 MPS 需求覆盖，避免重复计算 | §4.3①、§11.2 covered_by |
| R07 | 需求 → 需求 | 替换历史版本 | n:1 | 新版本需求替换旧版本，不追加计数 | §11.2 v2 替换 v1 |
| R08 | 物料授权 → 项目 | 授权项目 | n:1 | 授权按整机项目归口 | §2.1、测试四 |
| R09 | 物料授权 → 物料 | 授权物料 | n:1 | 授权覆盖的具体物料 | 同上 |
| R10 | 供给 → 物料 | 供给物料 | n:1 | 每条供给对应一颗物料 | §11.3 |
| R11 | 供给 → 计算运行 | 所属运行 | n:1 | 供给归属 FACT/SIM 分支与运行（模拟供给不写入 FACT） | §11.1 |
| R12 | 库存收发流水 → 物料 | 收发物料 | n:1 | 流水按物料核对 | §11.7 |
| R13 | 库存收发流水 → 供给 | 来源供给（可空） | n:1 | 收货流水把未收货订单量转入库存，防止重复计入 | §4.3③、测试八 |
| R14 | 供应商供货条件 → 供应商 | 供货供应商 | n:1 | 条件归属供应商 | §11.5 |
| R15 | 供应商供货条件 → 物料 | 适用物料 | n:1 | 条件按物料生效 | §11.5 |
| R16 | 替代与转用许可 → 物料 | 被替代物料 | n:1 | 需求侧被补偿的物料（如 WiFi6 需求） | §11.4 SUB-01 |
| R17 | 替代与转用许可 → 物料 | 替代物料 | n:1 | 供给侧用于替代的物料（如 WiFi5 指定批次） | §11.4 |
| R18 | 替代与转用许可 → 项目 | 适用项目 | n:1 | 许可只对指定项目生效（仅 Z9） | §11.4 |
| R19 | 单位换算 → 物料 | 换算物料 | n:1 | 换算关系挂靠物料 | 测试六 |
| R20 | 变化记录 → 计算运行 | 所属运行 | n:1 | 点检对比也在某次运行身份下留存 | §4.1 |
| R21 | 变化记录 → BOM 行 | 涉及BOM行（可空） | n:1 | 增删/用量/单位/生效日期四类变化指向的 BOM 行 | inspection-rules.csv |
| R22 | 变化记录 → 替代与转用许可 | 涉及替代关系（可空） | n:1 | 替代关系变化指向的许可记录 | inspection-rules.csv |
| R23 | 变化记录 → 物料授权 | 涉及授权（可空） | n:1 | 授权数量变化指向的授权记录 | inspection-rules.csv |
| R24 | 影响记录 → 计算运行 | 所属运行 | n:1 | 影响明细归属运行 | §4.2 |
| R25 | 影响记录 → 项目 | 受影响项目（可空） | n:1 | 变化波及的项目 | §4.2③ |
| R26 | 影响记录 → 物料 | 受影响物料 | n:1 | 变化波及的物料 | §4.2③ |
| R27 | 供需分配记录 → 需求 | 分配需求 | n:1 | 本次分配满足的需求 | §4.3④ |
| R28 | 供需分配记录 → 供给 | 分配供给 | n:1 | 被占用的供给批次 | §4.3④ |
| R29 | 供需分配记录 → 替代与转用许可 | 依据替代许可（可空） | n:1 | 替代路径分配的批准依据 | §4.3④ |
| R30 | 供需分配记录 → 计算运行 | 所属运行 | n:1 | 分配结果可追溯到运行 | §4.1 |
| R31 | 策备建议 → 物料 | 建议物料 | n:1 | 建议针对的物料 | §4.3⑤ |
| R32 | 策备建议 → 供应商 | 建议供应商 | n:1 | 建议面向的供应商 | §4.3⑤ |
| R33 | 策备建议 → 供应商参考清单 | 列入参考清单 | n:1 | 建议按供应商归入参考清单 | §3.2③ |
| R34 | 策备建议 → 计算运行 | 所属运行 | n:1 | 建议归属运行（V2 快照） | §11.1 |
| R35 | 供应商参考清单 → 供应商 | 面向供应商 | n:1 | 清单按供应商整理 | §3.2③ |
| R36 | 供应商参考清单 → 计算运行 | 所属运行 | n:1 | 清单归属运行 | §11.1 |
| R37 | 分期供需 → 物料 | 供需物料 | n:1 | 分期推演按物料 | §4.4① |
| R38 | 分期供需 → 计算运行 | 所属运行 | n:1 | 分期数据随方案运行独立成套 | §4.4③ |
| R39 | 呆滞风险 → 物料 | 风险物料 | n:1 | 风险按物料计量 | §4.4② |
| R40 | 呆滞风险 → 计算运行 | 所属运行 | n:1 | 风险归属运行 | §4.4 |
| R41 | 处理方案 → 呆滞风险 | 处置风险 | n:1 | 方案针对同一风险的处置 | §4.4③ |
| R42 | 处理方案 → 供给 | 调整供给（可空） | n:1 | 取消/延期所调整的供给批次 | §11.6 |
| R43 | 处理方案 → 计算运行 | 所属运行 | n:1 | 方案重算在独立运行分支 | §4.4④ |
| R44 | 历史呆滞案例 → 项目 | 历史项目 | n:1 | 案例归属独立历史项目（P-X8） | §11.7 |
| R45 | 历史呆滞案例 → 物料 | 案例旧料 | n:1 | 案例中被替代/呆滞的旧料 | §11.7 |
| R46 | 历史呆滞案例 → 物料 | 案例新料 | n:1 | 案例中切换后的新料 | §11.7 |
| R47 | 历史关键时点 → 历史呆滞案例 | 归属案例 | n:1 | 时点挂在案例时间线上 | §11.7 |
| R48 | 原因归因 → 历史呆滞案例 | 归属案例 | n:1 | 归因行归属案例 | §4.5④ |
| R49 | 预防规则 → 历史呆滞案例 | 源自案例（可空） | n:1 | 规则草案的证据来源案例 | §5.4 |

## 四、规则设计（共 14 条）

| # | 类型 | 名称 | 口径（自然语言/公式） | 挂载实体 | 来源 |
|---|---|---|---|---|---|
| RU-01 | 衍生 | 标准用量 | 标准用量 = BOM 行用量 ÷ BOM 基准数量 | BomLine | §4.2、inspection-rules.csv |
| RU-02 | 衍生 | 下层物料需求 | 下层物料需求 = 上层需求 × 标准用量 ÷ 有效良率；多层逐层展开后同物料汇总；良率仅计明确适用层级（无损耗取 1），同一损耗不得经良率与损耗系数重复计；替代料不作为额外必需组件重复展开（挂载实体待引擎验证多跳聚合 → OQ-03） | AllocationRecord（候选） | §4.3②、测试五 |
| RU-03 | 衍生 | 订单未收货量 | max（订单数量 − 累计有效收货量 − 已取消量 − 已关闭未收余量, 0）；收货转库存后不再按原未收数量重复计 | Supply | §4.3③、测试八 |
| RU-04 | 衍生 | 分期期末量 | 本期期末量 = 期初量 + 本期有效到货 + 其他有效流入 − 实际满足需求量 − 其他有效流出；本期期初量 = 上期期末量；初始库存只计一次 | PeriodSupplyDemand | §4.4① |
| RU-05 | 衍生 | 分期未满足需求 | 本期未满足需求 = 本期应满足需求 − 实际满足需求量；未满足保留为逾期需求，结转不重复累计 | PeriodSupplyDemand | §4.4① |
| RU-06 | 衍生 | 期末风险量 | 风险量 = max（评估期末剩余量 − 经确认的保留量 − 经证实的期后消耗量, 0）；保留与期后消耗不得重复覆盖同一用途，不得凭"以后可能会用"扣减 | SlowMovingRisk | §4.4② |
| RU-07 | 衍生 | 风险金额 | 风险金额 = Σ（风险数量 × 对应成本单价）；预计损失另行结合回收价值/处置方式计算，不与风险金额混同；窗口外承诺单独展示（延期≠消除） | SlowMovingRisk | §4.4④、§11.6 |
| RU-08 | 衍生 | 建议量取整 | 建议量 = 按订购倍数向上取整〔max（分配量, 最小起订量）〕；取整额外数量单独展示并纳入后续风险评估；交期晚于需要日期不得视为解决当期缺料（取整函数超方言白名单 → OQ-02） | SourcingSuggestion | §4.3⑤、测试一/十 |
| RU-09 | 衍生 | 待授权数量 | 待授权数量 = 项目物料毛需求 − 已授权覆盖数量；参考金额 = 待授权数量 × 单价；授权不增减物理供给 | MaterialAuthorization | §4.3⑥、测试四 |
| RU-10 | 衍生 | 还原期末库存 | 期末库存 = 期初库存 + 有效收货及其他入库 − 实际消耗及其他出库；出入库分类互斥、调拨处置不重复计；与记录不一致先列差异不判呆滞；不可取消采购承诺单独核算不混入物理库存 | HistoricalCase | §4.5① |
| RU-11 | 衍生 | 模拟可减少风险量 | max（不干预风险量 − 干预后风险量, 0)；同评估期间同口径，只用当时已知信息；证据不足不输出确定值 | HistoricalCase | §4.5③ |
| RU-12 | 触发 | 呆滞风险触发 | 未覆盖数量 > 0（阈值预先确定，一次有效评估即触发）；风险可先出现在未到货订单上，不等入库 | SlowMovingRisk | §4.4②、§11.7 |
| RU-13 | 触发 | 换料未到货检查（预防规则） | 已批准的工程变更导致未来旧料需求减少时 → 检查关联的未到货订单，计算无法被需求覆盖的数量，提示可取消数量、办理时间及截止日期；变更已获知且影响能够判断时触发，不等 BOM 正式生效 | EcnRecord | §4.5 末段、§5.4 |
| RU-14 | 约束 | 分配与归因双约束 | ①同一方案内一批供给的累计分配量（跨项目与替代路径合并）≤ 该批可用数量；②各主要原因归因数量之和 ≤ 案例呆滞总量，无法确认部分保留为未归因（DSL 形态：trigger 校验候选，阶段⑤定） | AllocationRecord / CauseAttribution | §4.3③、§4.5④ |

## 五、CQ 覆盖预映射

| CQ | 回答它需要的实体/关系/规则（引用上面表格编号） |
|---|---|
| cq-001 点检变化与影响 | E14、E15、R20—R26、RU-01 |
| cq-002 毛需求展开溯源 | E05、E03、R03、R05—R07、RU-01、RU-02 |
| cq-003 供给分配与缺口 | E07、E16、R10、R11、R27—R30、RU-03 |
| cq-004 授权外需求 | E06、R08、R09、RU-09 |
| cq-005 供应商建议量与取整 | E17、E10、E18、R31—R36、RU-08 |
| cq-006 期末呆滞风险 | E19、E20、R37—R40、RU-04、RU-05、RU-06、RU-07 |
| cq-007 处理方案对比 | E21、E07、R41—R43、RU-04（方案重算）、RU-14① |
| cq-008 历史呆滞形成还原 | E22、E23、E08、R12、R13、R44—R47、RU-10 |
| cq-009 历史干预模拟 | E22、R11（SIM 分支语义）、RU-11 |
| cq-010 原因归因分布 | E24、R48、RU-14② |
| cq-011 计算运行追溯复算 | E13、R11、R20、R24、R30、R34、R36、R38、R40、R43 |
| cq-012 工程变更触发预防规则 | E25、E04、R04、R49、RU-13 |

## 六、待确认事项（open_questions）与口径冲突（conflicts）

### open_questions（人审前须清零或标记接受）

| 编号 | 问题 | 缺在哪份材料（missing_from） | 建议 |
|---|---|---|---|
| OQ-01 | 全部字段类型与主键编码规则无正式 DDL，现按演示数据推断 | 客户 SAP/PDM 建表语句或字段字典（intake-log 缺口报告已声明） | 阶段⑤全量记 assumptions；向客户索取 |
| OQ-02 | "按订购倍数向上取整"超出表达式方言白名单（SUM/COALESCE/MAX） | dsl-spec §3.1 引擎方言能力 | 引擎侧裁决扩展 CEILING/ROUND，或建议量落为输入侧预处理字段 |
| OQ-03 | RU-02 多层 BOM 逐级展开属多跳反向聚合，v0.3.4 候选语法待引擎沙箱验证 | 引擎多跳聚合能力（dsl-spec 已注明） | 首个使用场景标注 open_question 进沙箱；不支持则逐级衍生 |
| OQ-04 | 影响记录与变化记录为多依据 n:m（合并为一条影响、保留多条依据），单外键 links 无法表达 | dsl-spec links 能力（无 n:m） | POC 以 evidence_refs 字段承载依据清单；n:m 桥表是否引入由 FDE+引擎侧裁决 |
| OQ-05 | 前后版本对比的数据形态：V0 旧记录不修改、V1 存变更版本（known_at 双记录并存），查询侧如何配对比较 | 文档未给版本配对查询口径 | 以同 bom 路径 + known_at 最近两版本配对（假设 A-04），FDE 确认 |
| OQ-06 | StockMovement 流水类型枚举全集（文档仅给收货/入库/消耗/出库大类） | 正式数据字典 | 先按四类枚举落，阶段⑤可扩 |
| OQ-07 | 物料授权的源系统（卫国策备表）字段结构未给，仅测试四预期值可反推 | 附录无授权字段级表 | 按测试四反推三字段（覆盖数量/批准日期/版本），FDE 与客户确认 |
| OQ-08 | 预防规则"验证四项"明细在未归位嵌入表（sheet TMAn4S） | 正文/附录未内联该表内容 | 向资料包补录，或按 §5.4 演示验证描述推断后 FDE 确认 |
| OQ-09 | 冻结库存"单列待核查"（1,000 颗/20,000 元）建模位置：现按 Supply 供给类型=质检冻结 + SlowMovingRisk 待核查金额字段承载 | —（设计选择） | FDE 确认是否需独立标记实体 |
| OQ-10 | 良率与损耗系数并存关系："同一损耗不能同时通过良率和损耗系数重复计算"暗示两字段，字段级表未见损耗系数列 | 附录 BOM 行表 | BomLine 先只落 yield_rate；损耗系数字段是否增设由 FDE 裁决 |
| OQ-11 | business_owner 为推断值（聂江锋，CIO） | 文档署名缺失（intake-log） | 用户确认后回写 brief.yaml |

### conflicts

本包三源交叉（§4 规则 ↔ §11 附录 ↔ §5 黄金案例）关键数字全部对齐（需求 30,000 / 旧料补偿 6,000 / 新料缺口 9,000 / 风险金额 88,000 / 历史 8,000→6,000），brief.yaml known_conflicts 为空——**无待裁决冲突**。

### assumptions（生成假设，供人审抽查）

- A-01 字段类型全部按演示数据推断（INTEGER 数量 / DOUBLE 金额比例 / DATE 日期 / TIMESTAMP 时点）。
- A-02 不建 DataVersion 实体：V0—V3 数据版本由各记录 known_at 字段 + CalculationRun.data_version 承载。
- A-03 PeriodSupplyDemand 期间粒度=月（演示附录 11.6 按月推演），粒度本身为字段不做硬编码。
- A-04 点检前后版本对比=同路径 known_at 最近两版本配对（V0 旧记录不可变）。
- A-05 可用库存/质检冻结/未收货订单统一 Supply 实体 + supply_type 字段（文档统一编号统一表）。
- A-06 输出类实体（策备建议/参考清单/分期供需/风险/方案）用复合自然键（run+业务维度），不用运行时生成编码。
- A-07 历史案例旧料/新料各建一条 links（案例结构为新旧料对比）；多料案例扩展性由 FDE 确认是否改桥表。

## 七、骨架拓扑

见 `models/xgimi-rebuild/topology-skeleton.png` / `.svg`（由 model.skeleton.yaml 经 render_topology.py --image both 产出；图上实体=主键+名称字段，连线标签=第三节关系语义名，供 FDE 对照第二/三节核完整性）。
