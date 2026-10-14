"""check_substitution_qualification 动作骨架（create_records 配方）。

由 gen_action_skeleton.py 从 model.yaml 生成，重新生成会覆盖本文件，请勿绕过 TODO 标记直接改写；
人工按 TODO(人工插桩) 标记补全业务逻辑后，由 compile_model.py 编译进 engine-bundle/actions.json。
运行依赖（@action、OntologyStore、OntologyEdits、datetime、uuid4）由本体引擎宿主注入——本文件即
引擎 body 源码形态，py_compile 通过即达标，不需要引擎环境独立运行。
"""

@action
def check_substitution_qualification(run_id: str, store: OntologyStore | None = None) -> OntologyEdits:
    """替代资格检查与配额输出（OQ-06 裁决承载）：对每条 SubstitutionPermission 逐一检查七项资格条件—— 替代方向、适用项目、指定批次、有效期、供给可用日期、换算比例、批准用量上限—— 全部通过方可参与替代分配，任一不满足即排除（失效替代关系保留问题记录但不得参与替代计算）， 输出合格替代配额写入 MaterialRequirement 替代满足量。本动作为写操作，会改写替代满足量， 资格误判将直接放大或漏计物理缺口，执行前必须经用户确认卡确认后方可写入。"""

    edits = OntologyEdits()
    store = store or OntologyStore()

    #   1. 查询输入实体（业务计算的输入集合）
    substitution_permission_list = list(store.query_instances("SubstitutionPermission"))
    supply_list = list(store.query_instances("Supply"))
    demand_list = list(store.query_instances("Demand"))
    material_requirement_list = list(store.query_instances("MaterialRequirement"))
    # TODO(人工插桩): 业务计算（人工插桩区）——基于上述输入实体按业务口径计算输出记录集合

    #   2. 主键生成（引擎惯例：前缀-参数-毫秒时间戳-uuid4 前 4 位 hex）
    record_id = f"MaterialRequirement-run_id-{datetime.now().strftime('%Y%m%d%H%M%S%f')[:-3]}-{uuid4().hex[:4]}"
    # TODO(人工插桩): 主键前缀按业务缩写惯例调整（如 Solution -> SOL），多记录场景改为循环生成

    #   3. 组装输出实例并登记（样例：主键赋值 + output_fields 待人工补全）
    new_obj = MaterialRequirement()
    new_obj.req_id = record_id  # 主键字段
    # TODO(人工插桩): 按 output_fields（substitute_satisfied_qty）补全新实例字段赋值
    edits.create("MaterialRequirement", new_obj)
    return edits
