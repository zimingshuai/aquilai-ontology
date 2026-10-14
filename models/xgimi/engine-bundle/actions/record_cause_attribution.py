"""record_cause_attribution 动作骨架（create_records 配方）。

由 gen_action_skeleton.py 从 model.yaml 生成，重新生成会覆盖本文件，请勿绕过 TODO 标记直接改写；
人工按 TODO(人工插桩) 标记补全业务逻辑后，由 compile_model.py 编译进 engine-bundle/actions.json。
运行依赖（@action、OntologyStore、OntologyEdits、datetime、uuid4）由本体引擎宿主注入——本文件即
引擎 body 源码形态，py_compile 通过即达标，不需要引擎环境独立运行。
"""

@action
def record_cause_attribution(historical_case_id: str, cause_type: str, attribution_qty: float, store: OntologyStore | None = None) -> OntologyEdits:
    """历史呆滞原因归因记录写入（OQ-09 裁决承载）：向指定历史案例追加一条原因归因记录（原因类型 + 归因数量）。 写入受 admission 规则「归因不得超案例总量」前置拦截——归因数量不得超过案例未归因量 （未归因 = max(呆滞总量 − Σ归因, 0)），守住"各主要原因数量之和 ≤ 案例呆滞总量"红线； 相关证据可同时保留，不自动定责个人/部门。本动作为写操作，直接改写案例归因账目， 执行前必须经用户确认卡确认后方可写入。"""

    edits = OntologyEdits()
    store = store or OntologyStore()

    #   1. 查询输入实体（业务计算的输入集合）
    historical_case_list = list(store.query_instances("HistoricalCase"))
    cause_attribution_list = list(store.query_instances("CauseAttribution"))
    # TODO(人工插桩): 业务计算（人工插桩区）——基于上述输入实体按业务口径计算输出记录集合

    #   2. 主键生成（引擎惯例：前缀-参数-毫秒时间戳-uuid4 前 4 位 hex）
    record_id = f"CauseAttribution-historical_case_id-{datetime.now().strftime('%Y%m%d%H%M%S%f')[:-3]}-{uuid4().hex[:4]}"
    # TODO(人工插桩): 主键前缀按业务缩写惯例调整（如 Solution -> SOL），多记录场景改为循环生成

    #   3. 组装输出实例并登记（样例：主键赋值 + output_fields 待人工补全）
    new_obj = CauseAttribution()
    new_obj.attribution_id = record_id  # 主键字段
    # TODO(人工插桩): 按 output_fields（case_id、cause_type、attributed_qty）补全新实例字段赋值
    edits.create("CauseAttribution", new_obj)
    return edits
