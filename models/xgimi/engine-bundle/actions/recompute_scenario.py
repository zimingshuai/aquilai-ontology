"""recompute_scenario 动作骨架（create_records 配方）。

由 gen_action_skeleton.py 从 model.yaml 生成，重新生成会覆盖本文件，请勿绕过 TODO 标记直接改写；
人工按 TODO(人工插桩) 标记补全业务逻辑后，由 compile_model.py 编译进 engine-bundle/actions.json。
运行依赖（@action、OntologyStore、OntologyEdits、datetime、uuid4）由本体引擎宿主注入——本文件即
引擎 body 源码形态，py_compile 通过即达标，不需要引擎环境独立运行。
"""

@action
def recompute_scenario(run_id: str, solution_plan_id: str, store: OntologyStore | None = None) -> OntologyEdits:
    """呆滞方案完整重算（OQ-07 裁决承载）：按 scenario-recompute 口径对指定 solution_plan_id 的措施类型 （取消/延期/替代消耗/转用）调整计算数据后，用同一套供需公式完整重算各方案结果—— 禁止用"原风险量减措施数量"代替完整计算；延期至评估期外的供给单独展示后续承诺、不视为消失； 造成不允许缺料的方案不进入推荐结果。重算结果对比写入 SolutionPlan。 本动作为写操作，会覆写方案级风险与敞口字段，直接支撑处置决策， 执行前必须经用户确认卡确认后方可写入。"""

    edits = OntologyEdits()
    store = store or OntologyStore()

    #   1. 查询输入实体（业务计算的输入集合）
    solution_plan_list = list(store.query_instances("SolutionPlan"))
    purchase_order_list = list(store.query_instances("PurchaseOrder"))
    supply_list = list(store.query_instances("Supply"))
    demand_list = list(store.query_instances("Demand"))
    substitution_permission_list = list(store.query_instances("SubstitutionPermission"))
    period_supply_balance_list = list(store.query_instances("PeriodSupplyBalance"))
    # TODO(人工插桩): 业务计算（人工插桩区）——基于上述输入实体按业务口径计算输出记录集合

    #   2. 主键生成（引擎惯例：前缀-参数-毫秒时间戳-uuid4 前 4 位 hex）
    record_id = f"SolutionPlan-run_id-{datetime.now().strftime('%Y%m%d%H%M%S%f')[:-3]}-{uuid4().hex[:4]}"
    # TODO(人工插桩): 主键前缀按业务缩写惯例调整（如 Solution -> SOL），多记录场景改为循环生成

    #   3. 组装输出实例并登记（样例：主键赋值 + output_fields 待人工补全）
    new_obj = SolutionPlan()
    new_obj.plan_id = record_id  # 主键字段
    # TODO(人工插桩): 按 output_fields（window_risk_amount、post_window_commitment_amount、shortage_flag、feasible_flag、action_cost）补全新实例字段赋值
    edits.create("SolutionPlan", new_obj)
    return edits
