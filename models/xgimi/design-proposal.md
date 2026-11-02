# xgimi 本体设计提案（design-proposal）——回溯建档版

> 版本：0.2.0-draft.2 · 呈审人：FDE（agent）作 · 待确认人：极米业务方（历史确认见 charter 与 OQ 裁决）
> 确认记录：回溯建档（2026-11-02）——本文由定稿 DSL model.yaml 机械提取生成，对应确认点②材料的事后补档；
> 历史确认与裁决痕迹见 model.yaml 内 OQ resolution（2026-10-14 用户 12 条裁决）与 diff-vs-trial-summary.md（复验对差异）。
> 后续增量建模时，本文件作为「现行设计基线」供 diff 对照，不再回溯重生成。

## 一、场景回顾

业务目标：极米（XGIMI）整机项目供需与呆滞风险的本体化——BOM 变化点检、供需策备、呆滞模拟、历史案例回放四场景。
CQ 清单：共 12 条（cq-001..cq-012），见 model.yaml competency_questions 段与 cq-checklist.html。

## 二、实体设计（共 26 个）

| # | 实体 | 展示名 | 主键 | 关键字段（≤5） | 一句话职责 | 来源 |
|---|---|---|---|---|---|---|
| 1 | Project | 项目 | project_id | project_id(STR) / stage(STR) | 机型/产品线，需求和 BOM 的挂载主体（如 P-Z9/Z9、P-Z10 仅风险 | B_scenarios/xgimi-poc-doc.md#§11.2 |
| 2 | Material | 物料 | material_code | material_code(STR) | 最小跟踪单位（WiFi 模组、SoC 等），用于汇总与库存跟踪 | B_scenarios/xgimi-poc-doc.md#§11.2+§11.5 |
| 3 | UnitConversion | 单位换算 | conversion_id | conversion_id(STR) / approval_status(STR) / evidence_status(STR) | 已批准的计量单位换算关系（如 1盒=100颗） | B_scenarios/xgimi-poc-doc.md#§4.1+§11.8 测试六 |
| 4 | Supplier | 供应商 | supplier_id | supplier_id(STR) | 物料供应商（参考清单的整理维度 | B_scenarios/xgimi-poc-doc.md#§11.5 |
| 5 | BomLine | BOM行 | line_id | line_id(STR) / bom_type(STR) / evidence_status(STR) / standard_usage(DEC) | 机型结构清单行（标准/风险/维修 BOM），含版本、层级用量、损耗与生效日期 | B_scenarios/xgimi-poc-doc.md#§11.2+§4.2 |
| 6 | EcnRecord | 工程变更记录 | ecn_id | ecn_id(STR) / approval_status(STR) / evidence_status(STR) | 工程变更（ECN）记录（如 Z9 换料 ECN：WiFi5 退出、WiFi6 引 | B_scenarios/xgimi-poc-doc.md#§11.1+§11.6+§5.4.6 |
| 7 | Demand | 需求 | demand_id,demand_version | demand_id(STR) / demand_version(STR) / source_type(STR) / status(STR) | 各项目需要数量与日期（订单/MPS/预测/售后维修），覆盖关系明确 | B_scenarios/xgimi-poc-doc.md#§11.2+§4.3 ① |
| 8 | MaterialAuthorization | 物料授权 | auth_id,auth_version | auth_id(STR) / auth_version(STR) / approval_status(STR) | 整机料号维度的供应商备料授权（对应卫国策备表口径） | B_scenarios/xgimi-poc-doc.md#§4.3 步骤6+§11.8 测试四+§8 红线 |
| 9 | Supply | 供给记录 | supply_id | supply_id(STR) / supply_type(STR) / scenario_tag(STR) | 物理供给条目（可用库存/质检冻结库存/已确认未收货订单/模拟采购） | B_scenarios/xgimi-poc-doc.md#§11.3+§11.1 |
| 10 | PurchaseOrder | 采购订单 | po_id | po_id(STR) / status(STR) / unreceived_qty(DEC) | 采购订单承诺与取消/延期条款（未到货供给的订单侧） | B_scenarios/xgimi-poc-doc.md#§4.3 ③+§11.3 |
| 11 | StockMovement | 库存流水 | movement_id | movement_id(STR) / movement_type(STR) / evidence_status(STR) | 库存出入库流水（收货/领用/退货/报废/调整/调拨），分类互斥、调拨和处置不得重 | B_scenarios/xgimi-poc-doc.md#§11.6+§5.4.3 |
| 12 | SubstitutionPermission | 替代与转用许可 | permission_id | permission_id(STR) / permission_type(STR) / approval_status(STR) | 物料间可替换规则及批准条件（替代/转用通道） | B_scenarios/xgimi-poc-doc.md#§11.4+§5.2 |
| 13 | SupplierSupplyCondition | 供应商供货条件 | condition_id | condition_id(STR) / approval_status(STR) | 供应商×物料的供货资格与订购条件（交期/最小起订量/订购倍数/分配份额） | B_scenarios/xgimi-poc-doc.md#§11.5+§11.8 测试一 |
| 14 | DataVersion | 数据版本 | version_id | version_id(STR) | 数据包版本（V0-V3）：可见时间与新增/修改内容 | B_scenarios/xgimi-poc-doc.md#§11.1 |
| 15 | CalculationRun | 计算运行快照 | run_id | run_id(STR) / run_type(STR) / scenario_tag(STR) | 每次计算运行的快照（观察时间/输入版本/规则版本/情景编号/评估期间） | B_scenarios/xgimi-poc-doc.md#§4.1+§11.1 |
| 16 | MaterialRequirement | 物料需求汇总 | req_id | req_id(STR) / remaining_material_qty(DEC) / physical_gap_qty(DEC) / pending_auth_qty(DEC) / pending_auth_amount(DEC) | 策备计算在物料粒度的汇总结果：毛需求、替代满足、已分配供给、授权覆盖与物理缺口分 | B_scenarios/xgimi-poc-doc.md#§4.3+§11.8 测试四 |
| 17 | InspectionChange | 点检变化记录 | change_id | change_id(STR) / change_type(STR) / object_type(STR) | 点检自动对比识别的前后版本变化（六类变化） | B_scenarios/xgimi-poc-doc.md#§4.2+A_schema/inspection-rules.csv |
| 18 | ReviewTask | 复核任务 | task_id | task_id(STR) / status(STR) | 点检变化生成的复核任务 | B_scenarios/xgimi-poc-doc.md#§4.2+§5.4.7 |
| 19 | SourcingSuggestion | 策备建议 | suggestion_id | suggestion_id(STR) | 对剩余缺口的策备建议（按供应商条件形成初步分配再检查订购条件） | B_scenarios/xgimi-poc-doc.md#§4.3 ⑤+§11.8 测试一 |
| 20 | VendorReferenceList | 供应商参考清单 | list_id | list_id(STR) / status(STR) | 按供应商整理的策备参考清单，供内部审核 | B_scenarios/xgimi-poc-doc.md#§3 流程③+§8 |
| 21 | PeriodSupplyBalance | 分期供需 | balance_id | balance_id(STR) / unmet_demand_qty(DEC) / ending_qty(DEC) | 按期间（11 月/12 月）分列的供需平衡：第一期期初取观察时间可用库存，后续期 | B_scenarios/xgimi-poc-doc.md#§4.4 ①+§11.7 |
| 22 | SlowMovingRisk | 呆滞风险 | risk_id | risk_id(STR) / risk_source_type(STR) / risk_qty(DEC) / risk_amount(DEC) | 评估期末可能无法消耗的物料风险，区分现有库存与未到货订单风险分别说明 | B_scenarios/xgimi-poc-doc.md#§4.4+§11.7 |
| 23 | SolutionPlan | 处理方案 | plan_id | plan_id(STR) / action_type(STR) / reducible_qty(DEC) / total_exposure_amount(DEC) | 呆滞处理方案（取消/延期/替代消耗/转用）及其重算结果对比 | B_scenarios/xgimi-poc-doc.md#§4.4+§4.5 ③+§11.7+A_schema/scenario-recompute.csv |
| 24 | HistoricalCase | 历史呆滞案例 | case_id | case_id(STR) / evidence_status(STR) / unattributed_qty(DEC) | 独立数据包的历史呆滞案例还原（P-X8） | B_scenarios/xgimi-poc-doc.md#§11.6+§4.5+§5.4 |
| 25 | CauseAttribution | 原因归因 | attribution_id | attribution_id(STR) | 历史案例的呆滞原因归因记录 | B_scenarios/xgimi-poc-doc.md#§4.5 ④+§5.4.6 |
| 26 | PreventionRule | 预防规则 | rule_id | rule_id(STR) / status(STR) | 从历史案例沉淀的检查规则草案（如工程变更导致旧料需求减少时检查关联未到货订单） | B_scenarios/xgimi-poc-doc.md#§5.4.7+§4.5 输出 |

## 三、关系设计（共 39 条）——说清「是什么关系」

| # | 从 → 到 | 关系语义名 | 基数 | 业务含义 |
|---|---|---|---|---|
| 1 | UnitConversion → Material | 换算物料 | n:1 | 单位换算关系生效的物料，计算前据此把盒/颗等源单位对齐到基本单位（1盒=100颗） |
| 2 | BomLine → Material | 子项物料 | n:1 | BOM 行需求展开的计算主体物料，各层毛需求按此逐层汇总到物料粒度 |
| 3 | BomLine → Project | 隶属项目 | n:1 | BOM 行归属的机型项目（行表未单列项目、由项目持有的 BOM 版本状态推断，A2），点检比较与需求 |
| 4 | EcnRecord → Project | 变更项目 | n:1 | 工程变更记录归属的整机项目，变更生效后在该项目上驱动 BOM 前后版本比较与旧料关联未到货订单的预防 |
| 5 | Demand → Project | 项目需求 | n:1 | 各来源需求（MPS/客户订单/预测/售后维修）以项目为挂载主体，覆盖去重与需求展开均在项目口径内进行 |
| 6 | MaterialAuthorization → Material | 授权物料 | n:1 | 供应商备料授权的物料对象（整机料号维度、卫国策备表口径），运行按生效版本（v2 覆盖替换 v1）汇总 |
| 7 | MaterialAuthorization → Project | 授权项目 | n:1 | 授权覆盖的整机项目，与授权物料共同构成「物料×项目」授权粒度，覆盖量仅在该项目口径内冲减待授权数量 |
| 8 | Supply → Material | 供给物料 | n:1 | 物理供给条目（可用库存/冻结库存/在途订单/模拟采购）的物料归属，供给分配与呆滞评估按该物料聚合，模 |
| 9 | Supply → PurchaseOrder | 在途订单 | n:1 | 仅订单类供给（open_order）指向的采购订单，取其到货日与取消/延期条款参与分配 |
| 10 | PurchaseOrder → Material | 订购物料 | n:1 | 订单订购的物料，未收货量核算与呆滞「未到货订单风险」均按该物料口径归集 |
| 11 | StockMovement → HistoricalCase | 案例流水 | n:1 | 流水归属的历史呆滞案例，waterfall 还原按案例聚合全部出入库记录，核对呆滞数量的期初+增减项 |
| 12 | StockMovement → Material | 流水物料 | n:1 | 出入库流水的物料，六类流水互斥记录、入库为正出库为负，为案例数量还原提供逐笔增减依据 |
| 13 | SubstitutionPermission → Material | 被替代物料 | n:1 | 许可中被替代/转出的原物料（原料侧，如 WiFi5 旧料），替代料引用以 substitute_ma |
| 14 | SubstitutionPermission → Project | 适用项目 | n:1 | 许可限定的适用项目（如 SUB-01 仅 Z9），替代分配仅在该项目需求上合法，不代表新旧物料可任意 |
| 15 | SubstitutionPermission → Supply | 许可用供给 | n:1 | 许可绑定的具体供给批次（指定库存批次或特定在途订单），替代/转用可用量受该供给数量与批次/批准用量上 |
| 16 | SupplierSupplyCondition → Supplier | 供货供应商 | n:1 | 供货条件的供应商一方，与物料共同构成「供应商×物料」资格粒度，份额分配与 MOQ/订购倍数取整按该供 |
| 17 | SupplierSupplyCondition → Material | 供货物料 | n:1 | 供货条件的物料一方，策备建议先按该物料下各供应商份额初步分配，再各自向上取整且不进行二次优化 |
| 18 | CalculationRun → DataVersion | 输入版本 | n:1 | 本次运行作为输入的数据版本快照（V0-V3），复算与历史决策判断只使用该版本可见时间点已知的信息 |
| 19 | MaterialRequirement → CalculationRun | 所属运行 | n:1 | 策备汇总归属的计算运行，毛需求/替代满足/授权覆盖按「运行×物料」一条记录列示，支撑结果可追溯可复算 |
| 20 | MaterialRequirement → Material | 需求物料 | n:1 | 供需与授权各项数量（毛需求/替代满足/已分配供给/物理缺口/待授权）汇总的物料粒度，授权覆盖与物理供 |
| 21 | InspectionChange → CalculationRun | 检测运行 | n:1 | 识别出该变化的点检运行（run_type=inspection），变化记录可回溯该次运行所比较的前后 |
| 22 | InspectionChange → BomLine | 变化行 | n:1 | 变化后的 BOM 行（删除类变化无后版本行时为空），变化前行以 before_line_id 属性承 |
| 23 | ReviewTask → InspectionChange | 复核变化 | n:1 | 复核任务来源的点检变化记录，同一变化不重复生成任务，任务关闭须附取消/调整或明确保留的处理依据、不能 |
| 24 | SourcingSuggestion → CalculationRun | 所属运行 | n:1 | 策备建议归属的策备运行（run_type=sourcing），建议针对该运行输入版本下的剩余物理缺口 |
| 25 | SourcingSuggestion → Material | 建议物料 | n:1 | 建议针对的缺口物料，每条建议为「物料×供应商」粒度的分配与取整结果，取整增量单列并纳入后续风险评估 |
| 26 | SourcingSuggestion → Supplier | 建议供应商 | n:1 | 建议初步分配的供应商，先按其供货份额与资格形成分配量再按 MOQ/订购倍数向上取整，到货晚于需求日期 |
| 27 | SourcingSuggestion → VendorReferenceList | 汇入清单 | n:1 | 建议汇入的供应商参考清单，同供应商的物料建议归并一张清单供内部审核，清单不等同于采购订单 |
| 28 | VendorReferenceList → CalculationRun | 所属运行 | n:1 | 参考清单归属的策备运行，清单内物料、建议量与预计到货安排由该运行的策备建议汇总生成 |
| 29 | VendorReferenceList → Supplier | 面向供应商 | n:1 | 清单面向的供应商，按供应商维度整理建议内容 |
| 30 | PeriodSupplyBalance → CalculationRun | 所属运行 | n:1 | 分期供需归属的呆滞模拟运行（run_type=risk_simulation），逐期滚动结转（期初= |
| 31 | PeriodSupplyBalance → Material | 平衡物料 | n:1 | 分期平衡的物料，新料/旧料分开列示、按「物料×期间」逐期滚动，未满足需求保留为逾期结转且不重复累计 |
| 32 | SlowMovingRisk → CalculationRun | 所属运行 | n:1 | 呆滞风险归属的呆滞模拟运行，风险量以该运行评估期末剩余量为基础，风险量大于 0 时一次有效评估即触发 |
| 33 | SlowMovingRisk → Material | 风险物料 | n:1 | 呆滞风险的物料对象，现有库存与未到货订单两类风险来源按物料分开说明，风险金额按演示成本单价计、不等于 |
| 34 | SolutionPlan → CalculationRun | 所属运行 | n:1 | 处理方案归属的呆滞模拟运行，各方案（S0/S1/S2）在该运行数据上完整重算对比，禁止以原风险量减措 |
| 35 | SolutionPlan → PurchaseOrder | 目标订单 | n:1 | 取消/延期类措施作用的采购订单，可取消量与延期条件以该订单运行前已有的书面条款为限、不得事后补设，不 |
| 36 | HistoricalCase → Project | 案例项目 | n:1 | 案例还原的机型项目（如停产 P-X8），历史案例属独立数据包，不与当前项目需求混算 |
| 37 | HistoricalCase → Material | 案例物料 | n:1 | 案例呆滞的物料（如旧料 H-WIFI-OLD），呆滞总量与各原因归因数量之和均以该物料口径核对 |
| 38 | CauseAttribution → HistoricalCase | 归因案例 | n:1 | 归因记录归属的历史案例，各原因归因数量之和不得超过案例呆滞总量（写入经 admission 写前拦截 |
| 39 | PreventionRule → HistoricalCase | 规则来源案例 | n:1 | 预防规则沉淀来源的历史案例，规则保留该案例的证据链，触发不等 BOM 正式生效，经审核并试运行后启用 |

## 四、规则设计（共 19 条）

| # | 类型 | 名称 | 口径（摘要） | 挂载实体 | 来源 |
|---|---|---|---|---|---|
| 1 | derived_property | 标准用量 | 标准用量 = BOM 行用量 ÷ BOM 基准数量；用量比较须在单位和基准数量一 | BomLine | — |
| 2 | derived_property | 订单未收货量 | 订单未收货量 = max(订单数量 − 累计有效收货量 − 已取消量 − 已关闭 | PurchaseOrder | — |
| 3 | derived_property | 剩余新料需求 | 剩余新料需求 = 物料毛需求 − 替代满足量（主案例 Z9：20,000−6,0 | MaterialRequirement | — |
| 4 | derived_property | 新料缺口 | 新料缺口 = max(剩余新料需求 − 已分配新料供给, 0)（24,000−1 | MaterialRequirement | — |
| 5 | derived_property | 待授权数量 | 待授权数量 = max(毛需求 − 已授权覆盖量, 0)（测试四：18,000− | MaterialRequirement | — |
| 6 | derived_property | 待授权参考金额 | 待授权参考金额 = 待授权数量 × 参考单价（8,000×20=160,000  | MaterialRequirement | — |
| 7 | derived_property | 本期期末量 | 本期期末量 = 期初量 + 本期有效到货 + 其他有效流入 − 实际满足需求量  | PeriodSupplyBalance | — |
| 8 | derived_property | 本期未满足需求 | 本期未满足需求 = 本期应满足需求 − 实际满足需求量；保留为逾期需求，后续结转 | PeriodSupplyBalance | — |
| 9 | derived_property | 期末风险量 | 风险量 = max(评估期末剩余量 − 经确认的保留量 − 经证实的期后消耗量, | SlowMovingRisk | — |
| 10 | derived_property | 呆滞风险金额 | 风险金额 = Σ(风险数量 × 对应成本单价)；不等于减值损失或实际收益，敞口≠ | SlowMovingRisk | — |
| 11 | derived_property | 方案合计敞口 | 合计敞口 = 窗口内风险金额 + 窗口后未消化承诺（S2：24,000+64,0 | SolutionPlan | — |
| 12 | derived_property | 模拟可减少风险量 | 模拟可减少风险量 = max(不干预风险量 − 干预后风险量, 0)（8,000 | SolutionPlan | — |
| 13 | derived_property | 未归因数量 | 未归因数量 = max(呆滞总量 − Σ各原因归因数量, 0)；各主要原因对应数 | HistoricalCase | — |
| 14 | trigger | 呆滞风险触发复核 | 风险阈值为未覆盖数量大于 0，一次有效评估即可触发；风险首次可识别日即形成（§1 | SlowMovingRisk | — |
| 15 | trigger | 工程变更预防检查触发 | 已批准的工程变更导致未来旧料需求减少时，检查关联的未到货订单，计算无法被需求覆盖 | EcnRecord | — |
| 16 | trigger | 授权数量变化重核算 | 同一授权对象及口径下比较前后数量，识别授权数量变化后重新核算相关待授权需求或策备 | InspectionChange | — |
| 17 | trigger | 替代关系变化复核分配方案 | 比较方向、范围、比例、有效期及批准状态，检查原分配方案是否仍然有效；失效替代关系 | InspectionChange | — |
| 18 | trigger | 冻结供给排除待核查 | 质检冻结库存未获放行不参与供给分配，单列待核查数量（1,000 颗/20,000 | Supply | — |
| 19 | admission | 归因不得超案例总量 | 写前拦截——新归因数量不得超出案例未归因量（未归因 = max(呆滞总量 − Σ | record_cause_attribution | — |

## 五、CQ 映射（共 12 条）

| id | 问题 | covered_by |
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

## 六、open_questions 确认（共 12 条，已裁决 9 条）

| id | 主题 | 状态 | 裁决摘要 |
|---|---|---|---|
| OQ-01 | 策备建议量向上取整（方言边界） | resolved-pending-engine | A 方案——引擎方言扩展 CEILING 取整函数；扩展落地后由 derived |
| OQ-02 | 多级 BOM 迭代展开（方言边界） | resolved | C 方案——动作域承载，见 actions.expand_demand_to_r |
| OQ-03 | 需求去重与覆盖关系选取（方言边界） | resolved | C 方案——动作域承载，见 actions.expand_demand_to_r |
| OQ-04 | 供给分配优先级与稳定排序（方言边界） | resolved | C 方案——动作域承载，见 actions.allocate_supply |
| OQ-05 | 分期滚动结转（方言边界） | resolved | C 方案——动作域承载，见 actions.compute_period_bal |
| OQ-06 | 替代资格多条件检查（方言边界） | resolved | C 方案——动作域承载，见 actions.check_substitution |
| OQ-07 | 方案措施数据调整与完整重算（方言边界/动作域） | resolved | C 方案——动作域承载，见 actions.recompute_scenario |
| OQ-08 | 授权生效版本选择（方言边界） | resolved | B 方案——预计算，数据侧维护"当前有效授权"视图/字段 |
| OQ-09 | 防重复归因上限约束（admission 候选） | resolved | 立即落地 admission 拦截——见 admission 规则「归因不得超案 |
| OQ-10 | 主案例 ECN 编号缺失 | pending-business | 转业务方补充 |
| OQ-11 | 参考清单外发审批流程未定义 | pending-business | 转业务方补充 |
| OQ-12 | known_at"V0 之前"的精确时点 | pending-business | 转业务方补充 |

> 待业务方回复的 3 条 pending-business（OQ-10/11/12）以业务问询单形式另行呈送；定稿前须清零或显式接受。
