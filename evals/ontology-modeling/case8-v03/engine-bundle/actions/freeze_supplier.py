"""freeze_supplier 动作骨架（modify_instance 配方）。

由 gen_action_skeleton.py 从 gold-actions.yaml 生成，重新生成会覆盖本文件，请勿绕过 TODO 标记直接改写；
人工按 TODO(人工插桩) 标记补全业务逻辑后，由 compile_model.py 编译进 engine-bundle/actions.json。
运行依赖（@action、OntologyStore、OntologyEdits、datetime、uuid4）由本体引擎宿主注入——本文件即
引擎 body 源码形态，py_compile 通过即达标，不需要引擎环境独立运行。
"""

@action
def freeze_supplier(supplier_code: str, store: OntologyStore | None = None) -> OntologyEdits:
    """冻结供应商：把指定供应商置为冻结状态（停止对账与付款）。写操作——直接修改供应商主数据 frozen_flag，执行前必须经用户在确认卡中明确确认，不得仅凭指令性措辞直接执行。"""

    edits = OntologyEdits()
    store = store or OntologyStore()

    #   1. 主键定位：按 lookup 定位目标实例（@param -> 函数参数注入）
    obj = next((o for o in store.query_instances("Supplier") if getattr(o, "supplier_code") == supplier_code), None)
    if obj is None:
        raise ValueError(f"未找到 supplier_code={supplier_code}的供应商实例，无法执行 freeze_supplier")

    #   2. status_guard 前置校验（本配方未配置 status_guard）
    # TODO(人工插桩): 如需额外前置校验（状态/权限/数量边界等），在此补充，不满足时 raise ValueError(中文消息)

    #   3. 实例重建：复制原实例字段并排除 property 属性（衍生属性由引擎按规则重算，不参与 setattr）
    new_obj = type(obj)()
    for field_name in vars(obj):
        if not isinstance(getattr(type(obj), field_name, None), property):
            setattr(new_obj, field_name, getattr(obj, field_name))

    #   4. set_fields 赋值（@param 注入参数 / 常量）
    new_obj.frozen_flag = True  # set_fields（常量）

    edits.modify("Supplier", new_obj)
    # TODO(人工插桩): edits.modify 调用签名以目标引擎 ontology/actions.py 为准，必要时按引擎实际调整
    return edits
