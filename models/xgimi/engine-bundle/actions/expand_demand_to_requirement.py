"""expand_demand_to_requirement 动作骨架（create_records 配方）。

由 gen_action_skeleton.py 从 model.yaml 生成，重新生成会覆盖本文件，请勿绕过 TODO 标记直接改写；
人工按 TODO(人工插桩) 标记补全业务逻辑后，由 compile_model.py 编译进 engine-bundle/actions.json。
运行依赖（@action、OntologyStore、OntologyEdits、datetime、uuid4）由本体引擎宿主注入——本文件即
引擎 body 源码形态，py_compile 通过即达标，不需要引擎环境独立运行。
"""

@action
def expand_demand_to_requirement(run_id: str, demand_version: str, store: OntologyStore | None = None) -> OntologyEdits:
    """策备需求展开（OQ-02+03 裁决承载）：读取运行 run_id 在 demand_version 数据版本下的 Demand/BomLine/UnitConversion 输入，先按覆盖关系去重（有 covered_by 依据的按确认口径选取冲减， 如 MPS 已含订单并替代早期预测，三者不相加；无覆盖依据不得仅凭来源优先级舍弃）， 再逐层展开「下层需求 = 上层需求 × 标准用量 ÷ 有效良率」（良率仅计入明确适用层级、无损耗层级取 1， 标准用量须先经 UnitConversion 单位换算对齐），将物料毛需求汇总写入 MaterialRequirement。 本动作为写操作，会新增/覆写 MaterialRequirement 记录，存在覆盖既有计算结果的风险， 执行前必须经用户确认卡确认后方可写入。"""

    edits = OntologyEdits()
    store = store or OntologyStore()

    #   1. 查询输入实体（业务计算的输入集合）
    demand_list = list(store.query_instances("Demand"))
    bom_line_list = list(store.query_instances("BomLine"))
    unit_conversion_list = list(store.query_instances("UnitConversion"))
    data_version_list = list(store.query_instances("DataVersion"))
    # TODO(人工插桩): 业务计算（人工插桩区）——基于上述输入实体按业务口径计算输出记录集合

    #   2. 主键生成（引擎惯例：前缀-参数-毫秒时间戳-uuid4 前 4 位 hex）
    record_id = f"MaterialRequirement-run_id-{datetime.now().strftime('%Y%m%d%H%M%S%f')[:-3]}-{uuid4().hex[:4]}"
    # TODO(人工插桩): 主键前缀按业务缩写惯例调整（如 Solution -> SOL），多记录场景改为循环生成

    #   3. 组装输出实例并登记（样例：主键赋值 + output_fields 待人工补全）
    new_obj = MaterialRequirement()
    new_obj.req_id = record_id  # 主键字段
    # TODO(人工插桩): 按 output_fields（run_id、material_id、gross_qty）补全新实例字段赋值
    edits.create("MaterialRequirement", new_obj)
    return edits
