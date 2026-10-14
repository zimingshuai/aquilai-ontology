"""DSL v0.2.2 动作骨架生成器：按 actions 段 recipe 配方生成引擎 body 骨架（dsl-spec §4）。

主要 Input：DSL YAML 模型路径（位置参数）+ -o/--bundle-dir 输出目录（默认 <模型目录>/engine-bundle）。
主要 Output：<bundle>/actions/<name>.py 骨架文件（每 action 一份），严格按 §4 统一模式生成：
@action 装饰器、签名（parameters 类型标注 + 隐式 store: OntologyStore | None = None）、
docstring=description 原文、edits/store 初始化开头、query_instances+next 主键定位、
中文 ValueError 前置校验、排除 property 属性的实例重建、edits.modify/create、主键生成模式，
全部人工插桩点统一 TODO(人工插桩) 标记。生成后逐文件内置 compile() 语法自查（非法即退出 1，
不落残件）。骨架运行依赖（@action/OntologyStore/OntologyEdits/datetime/uuid4）由本体引擎宿主
注入——文件即引擎 body 源码形态，py_compile 通过即达标，不需要引擎环境独立运行。
"""

# 标准库导入
import argparse
import re
import sys
from pathlib import Path
from typing import Any

# 第三方依赖导入
import yaml

# ===========一、常量（dsl-spec §4 配方与类型标注约定）==========
# KNOWN_RECIPES：三种骨架配方（自 mfg 引擎 8 个真实 action 实测归纳）。
KNOWN_RECIPES = {"modify_instance", "state_transition", "create_records"}
# PARAM_TYPES：parameters 值允许的引擎类型标注（str/float；可选加 ? 后缀 -> None 默认值）。
PARAM_TYPES = {"str": "str", "float": "float"}
# PARAM_REF_PREFIX：recipe_config 中参数注入引用前缀（如 "@param:supplier_code"）。
PARAM_REF_PREFIX = "@param:"
# STATUS_FIELD：state_transition 配方约定状态字段名（dsl-spec §4 配方未显式声明，按引擎惯例）。
STATUS_FIELD = "status"
# HEADER_TEMPLATE：骨架文件头 docstring 模板（溯源 + 运行环境说明 + 禁改提示）。
HEADER_TEMPLATE = '''"""{name} 动作骨架（{recipe} 配方）。

由 gen_action_skeleton.py 从 {model_name} 生成，重新生成会覆盖本文件，请勿绕过 TODO 标记直接改写；
人工按 TODO(人工插桩) 标记补全业务逻辑后，由 compile_model.py 编译进 engine-bundle/actions.json。
运行依赖（@action、OntologyStore、OntologyEdits、datetime、uuid4）由本体引擎宿主注入——本文件即
引擎 body 源码形态，py_compile 通过即达标，不需要引擎环境独立运行。
"""
'''


def _fail(location: str, detail: str) -> None:
    """非法 DSL 显性退出：打印中文错误位置与详情后以非零码终止。

    Args:
        location: 出问题的 DSL 位置（如动作名、配置键）。
        detail: 非法内容描述（未知配方、缺必填键等）。
    Raises:
        SystemExit: 总是触发，退出码 1。
    """
    print(f"错误：{location} 不符合 DSL 规范——{detail}", file=sys.stderr)
    raise SystemExit(1)


# ===========二、值渲染与签名（骨架片段工具）==========
def _value_expr(value: Any) -> str:
    """把 lookup/set_fields 的值渲染为骨架 Python 表达式。

    Args:
        value: DSL 配方配置值（"@param:参数名" 字符串或任意 YAML 常量）。
    Returns:
        @param:名 -> 参数名裸标识符（函数参数注入）；其余 -> repr 常量字面量。
    """
    if isinstance(value, str) and value.startswith(PARAM_REF_PREFIX):
        ref = value[len(PARAM_REF_PREFIX):]
        if not ref.isidentifier():
            _fail("recipe_config 参数引用", f"{value!r} 的 {PARAM_REF_PREFIX}后缀不是合法标识符")
        return ref
    return repr(value)


def _is_param_ref(value: Any) -> bool:
    """判定配置值是否为 @param 参数注入引用。Args: value 配置值。Returns: 是返回 True。"""
    return isinstance(value, str) and value.startswith(PARAM_REF_PREFIX)


def _signature(action: dict[str, Any]) -> str:
    """渲染函数签名参数串：parameters 类型标注 + 隐式 store 参数。

    Args:
        action: DSL 动作 dict（parameters 键为参数名 -> 类型标注字符串）。
    Returns:
        形如 "supplier_code: str, store: OntologyStore | None = None" 的签名串。
    """
    parts: list[str] = []
    for pname, ptype in (action.get("parameters") or {}).items():
        base = str(ptype).removesuffix("?")
        if base not in PARAM_TYPES:
            _fail(f"动作 {action.get('name')} 参数 {pname}", f"类型标注 {ptype!r} 非法（仅 str/float 可选加 ?）")
        if str(ptype).endswith("?"):
            parts.append(f"{pname}: {PARAM_TYPES[base]} | None = None")
        else:
            parts.append(f"{pname}: {PARAM_TYPES[base]}")
    parts.append("store: OntologyStore | None = None")
    return ", ".join(parts)


def _docstring_block(description: str) -> str:
    """把 description 原文渲染为函数 docstring（多行时逐行保持 4 空格缩进）。

    Args:
        description: 动作中文描述原文。
    Returns:
        缩进合法的 docstring 文本块。
    """
    lines = str(description).strip().splitlines()
    if len(lines) == 1:
        return f'    """{lines[0]}"""'
    body = "\n".join("    " + line for line in lines)
    return f'    """{lines[0]}\n{body}\n    """'


def _pk_desc(lookup: dict[str, Any]) -> str:
    """渲染主键定位描述中文（骨架 raise 消息内嵌 f-string 表达式用）。

    Args:
        lookup: 主键字段 -> 值（@param 引用或常量）映射。
    Returns:
        形如 "supplier_code={supplier_code} 且 contract_nr={contract_nr}" 的描述串。
    """
    return " 且 ".join(f"{k}={{{_value_expr(v)}}}" for k, v in lookup.items())


def _entity_meta(entities: dict[str, Any], entity: str) -> tuple[str, list[str]]:
    """取目标实体的中文展示名与主键字段列表。

    Args:
        entities: DSL entities 段。
        entity: 目标实体名。
    Returns:
        (展示名, 主键字段列表)；实体不存在时显性退出，无主键返回空列表。
    """
    ent = entities.get(entity)
    if not isinstance(ent, dict):
        _fail(f"recipe_config.target_entity {entity!r}", "目标实体未在 DSL entities 中声明")
    props = ent.get("properties") or {}
    pk_fields = [f for f, spec in props.items() if isinstance(spec, dict) and spec.get("primary")]
    return str(ent.get("display_name") or entity), pk_fields


def _locate_block(entity: str, display: str, lookup: dict[str, Any], action_name: str) -> list[str]:
    """渲染主键定位 + 存在性校验块（modify/state 两配方共用）。

    Args:
        entity: 目标实体名。
        display: 目标实体中文展示名（raise 消息用）。
        lookup: 主键字段 -> 值映射。
        action_name: 动作名（raise 消息用）。
    Returns:
        骨架代码行列表（已含 4 空格函数体缩进）。
    """
    cond = " and ".join(f'getattr(o, "{k}") == {_value_expr(v)}' for k, v in lookup.items())
    return [
        f'    obj = next((o for o in store.query_instances("{entity}") if {cond}), None)',
        "    if obj is None:",
        f'        raise ValueError(f"未找到 {_pk_desc(lookup)}的{display}实例，无法执行 {action_name}")',
    ]


def _rebuild_lines(old: str, new: str, indent: str = "    ") -> list[str]:
    """渲染实例重建块：复制原实例字段并排除 property 属性（dsl-spec §4 统一模式）。

    Args:
        old: 原实例变量名（obj / item）。
        new: 新实例变量名（new_obj / new_item）。
        indent: 块首缩进（级联场景传 8 空格）。
    Returns:
        骨架代码行列表。
    """
    return [
        f"{indent}{new} = type({old})()",
        f"{indent}for field_name in vars({old}):",
        f"{indent}    if not isinstance(getattr(type({old}), field_name, None), property):",
        f"{indent}        setattr({new}, field_name, getattr({old}, field_name))",
    ]


# ===========三、三种配方渲染（dsl-spec §4 recipe 分支）==========
def _render_modify(action: dict[str, Any], cfg: dict[str, Any], entities: dict[str, Any]) -> str:
    """渲染 modify_instance 配方骨架：定位 -> status_guard -> 重建 -> set_fields -> edits.modify。

    Args:
        action: DSL 动作 dict。
        cfg: recipe_config（target_entity/lookup/set_fields/status_guard）。
        entities: DSL entities 段。
    Returns:
        函数体源码（不含 def 行与 docstring）。
    """
    name = action["name"]
    display, _pks = _entity_meta(entities, cfg.get("target_entity"))
    lookup = cfg.get("lookup") or {}
    lines = [
        "    edits = OntologyEdits()",
        "    store = store or OntologyStore()",
        "",
        "    #   1. 主键定位：按 lookup 定位目标实例（@param -> 函数参数注入）",
        *_locate_block(str(cfg.get("target_entity")), display, lookup, name),
        "",
    ]
    guard = cfg.get("status_guard")
    if isinstance(guard, dict) and guard.get("field"):
        field, expect = guard["field"], guard.get("expect")
        lines += [
            "    #   2. status_guard 前置校验（状态不满足即拒绝，防非法写入）",
            f'    current = getattr(obj, "{field}")',
            f"    if current != {expect!r}:",
            f"        raise ValueError(f\"{display}实例（{_pk_desc(lookup)}）当前{field}={{current!r}}，"
            f"须为{expect!r}才能执行 {name}\")",
        ]
    else:
        lines += [
            "    #   2. status_guard 前置校验（本配方未配置 status_guard）",
            "    # TODO(人工插桩): 如需额外前置校验（状态/权限/数量边界等），在此补充，不满足时 raise ValueError(中文消息)",
        ]
    lines += [
        "",
        "    #   3. 实例重建：复制原实例字段并排除 property 属性（衍生属性由引擎按规则重算，不参与 setattr）",
        *_rebuild_lines("obj", "new_obj"),
        "",
        "    #   4. set_fields 赋值（@param 注入参数 / 常量）",
    ]
    for field, value in (cfg.get("set_fields") or {}).items():
        src = "参数注入" if _is_param_ref(value) else "常量"
        lines.append(f"    new_obj.{field} = {_value_expr(value)}  # set_fields（{src}）")
    lines += [
        "",
        f'    edits.modify("{cfg.get("target_entity")}", new_obj)',
        "    # TODO(人工插桩): edits.modify 调用签名以目标引擎 ontology/actions.py 为准，必要时按引擎实际调整",
        "    return edits",
    ]
    return "\n".join(lines)


def _render_state(action: dict[str, Any], cfg: dict[str, Any], entities: dict[str, Any]) -> str:
    """渲染 state_transition 配方骨架：定位 -> from_status 校验 -> to_status 变更 -> cascade 级联。

    Args:
        action: DSL 动作 dict。
        cfg: recipe_config（target_entity/lookup/from_status/to_status/cascade）。
        entities: DSL entities 段。
    Returns:
        函数体源码（不含 def 行与 docstring）。
    """
    name = action["name"]
    entity = str(cfg.get("target_entity"))
    display, _pks = _entity_meta(entities, entity)
    lookup = cfg.get("lookup") or {}
    from_status, to_status = cfg.get("from_status"), cfg.get("to_status")
    lines = [
        "    edits = OntologyEdits()",
        "    store = store or OntologyStore()",
        "",
        "    #   1. 主键定位：按 lookup 定位目标实例（@param -> 函数参数注入）",
        *_locate_block(entity, display, lookup, name),
        "",
        "    #   2. from_status 状态校验（状态机前置条件，非预期状态即拒绝）",
        f'    current = getattr(obj, "{STATUS_FIELD}")',
        f"    if current != {from_status!r}:",
        f"        raise ValueError(f\"{display}实例（{_pk_desc(lookup)}）当前{STATUS_FIELD}={{current!r}}，"
        f"须为{from_status!r}才能执行 {name}\")",
        "",
        f"    #   3. 实例重建（排除 property 属性）+ to_status 目标状态变更",
        *_rebuild_lines("obj", "new_obj"),
        f"    new_obj.{STATUS_FIELD} = {to_status!r}  # to_status（状态字段按约定为 {STATUS_FIELD}，异名时人工调整）",
    ]
    for cas in cfg.get("cascade") or []:
        child, via = cas.get("entity"), cas.get("via")
        c_display, _cpks = _entity_meta(entities, child)
        lines += [
            "",
            f"    #   cascade 级联：{c_display}按 via 外键关联且状态匹配的子实例同步迁移",
            f'    for item in store.query_instances("{child}"):',
            f'        if getattr(item, "{via}", None) == getattr(obj, "{via}") and '
            f'getattr(item, "{STATUS_FIELD}", None) == {cas.get("from")!r}:',
            *_rebuild_lines("item", "new_item", indent="            "),
            f"            new_item.{STATUS_FIELD} = {cas.get('to')!r}",
            f'            edits.modify("{child}", new_item)',
        ]
    lines += [
        "",
        f'    edits.modify("{entity}", new_obj)',
        "    return edits",
    ]
    return "\n".join(lines)


def _render_create(action: dict[str, Any], cfg: dict[str, Any], entities: dict[str, Any]) -> str:
    """渲染 create_records 配方骨架：查询输入 -> TODO 业务计算区 -> 主键生成 -> edits.create 样例。

    Args:
        action: DSL 动作 dict。
        cfg: recipe_config（target_entity/input_entities/output_fields）。
        entities: DSL entities 段。
    Returns:
        函数体源码（不含 def 行与 docstring）。
    """
    name = action["name"]
    entity = str(cfg.get("target_entity"))
    _display, pk_fields = _entity_meta(entities, entity)
    params = list((action.get("parameters") or {}).keys())
    first_param = params[0] if params else name
    snake = re.sub(r"(?<!^)(?=[A-Z])", "_", entity).lower()
    lines = [
        "    edits = OntologyEdits()",
        "    store = store or OntologyStore()",
        "",
        "    #   1. 查询输入实体（业务计算的输入集合）",
    ]
    for input_entity in cfg.get("input_entities") or []:
        in_snake = re.sub(r"(?<!^)(?=[A-Z])", "_", str(input_entity)).lower()
        lines.append(f'    {in_snake}_list = list(store.query_instances("{input_entity}"))')
    lines += [
        "    # TODO(人工插桩): 业务计算（人工插桩区）——基于上述输入实体按业务口径计算输出记录集合",
        "",
        "    #   2. 主键生成（引擎惯例：前缀-参数-毫秒时间戳-uuid4 前 4 位 hex）",
        f'    record_id = f"{entity}-{first_param}-'
        "{datetime.now().strftime('%Y%m%d%H%M%S%f')[:-3]}-{uuid4().hex[:4]}\"",
        "    # TODO(人工插桩): 主键前缀按业务缩写惯例调整（如 Solution -> SOL），多记录场景改为循环生成",
        "",
        f"    #   3. 组装输出实例并登记（样例：主键赋值 + output_fields 待人工补全）",
        f"    new_obj = {entity}()",
    ]
    if pk_fields:
        lines.append(f"    new_obj.{pk_fields[0]} = record_id  # 主键字段")
    else:
        lines.append(f"    # TODO(人工插桩): 实体 {entity} 未声明 primary 字段，人工确定主键生成字段并赋值")
    output_fields = "、".join(str(f) for f in cfg.get("output_fields") or []) or "（未配置 output_fields）"
    lines += [
        f"    # TODO(人工插桩): 按 output_fields（{output_fields}）补全新实例字段赋值",
        f'    edits.create("{entity}", new_obj)',
        "    return edits",
    ]
    return "\n".join(lines)


# ===========四、组装与命令行入口==========
def render_skeleton(action: dict[str, Any], entities: dict[str, Any], model_name: str) -> str:
    """组装单动作骨架全文：文件头 docstring + @action 函数定义 + 按 recipe 渲染的函数体。

    Args:
        action: DSL actions 段单个动作 dict（校验已由调用方完成）。
        entities: DSL entities 段。
        model_name: 源模型文件名（骨架头部溯源展示）。
    Returns:
        骨架文件全文（语法合法的 Python 源码）。
    """
    renderer = {
        "modify_instance": _render_modify,
        "state_transition": _render_state,
        "create_records": _render_create,
    }[action["recipe"]]
    header = HEADER_TEMPLATE.format(name=action["name"], recipe=action["recipe"], model_name=model_name)
    func_head = (
        "@action\n"
        f"def {action['name']}({_signature(action)}) -> OntologyEdits:\n"
        f"{_docstring_block(action['description'])}\n"
        "\n"
    )
    return header + "\n" + func_head + renderer(action, action.get("recipe_config") or {}, entities) + "\n"


def main() -> int:
    """命令行入口：读 DSL -> 校验 actions 段 -> 逐动作渲染骨架并语法自查 -> 落盘 actions 目录。"""
    parser = argparse.ArgumentParser(description="按 DSL actions 段生成引擎 body 骨架（dsl-spec §4）")
    parser.add_argument("model", help="DSL YAML 模型路径")
    parser.add_argument("-o", "--bundle-dir", default=None,
                        help="输出目录（默认 <模型目录>/engine-bundle，骨架写入其 actions/ 子目录）")
    args = parser.parse_args()
    model_path = Path(args.model)
    # bundle_dir：产物目录，缺省为模型同目录下的 engine-bundle（与 compile_model.py 口径一致）。
    bundle_dir = Path(args.bundle_dir) if args.bundle_dir else model_path.parent / "engine-bundle"
    model = yaml.safe_load(model_path.read_text(encoding="utf-8"))
    actions = model.get("actions") or []
    if not actions:
        print(f"提示：{model_path.name} 无 actions 段，未生成骨架")
        return 0
    entities = model.get("entities") or {}
    out_dir = bundle_dir / "actions"
    out_dir.mkdir(parents=True, exist_ok=True)
    #   1. 逐动作校验 -> 渲染 -> 语法自查（compile 内置，非法即终止不落残件）-> 落盘
    for idx, action in enumerate(actions):
        where = f"actions[{idx}]"
        if not isinstance(action, dict):
            _fail(where, "不是映射结构")
        name = action.get("name")
        if not isinstance(name, str) or not name.isidentifier():
            _fail(where, f"name={name!r} 缺失或不是合法 Python 函数名")
        for key in ("description", "recipe", "recipe_config"):
            if not action.get(key):
                _fail(f"动作 {name}", f"缺少必填键 {key}")
        if action["recipe"] not in KNOWN_RECIPES:
            _fail(f"动作 {name}", f"recipe={action['recipe']!r} 不在三种配方 {sorted(KNOWN_RECIPES)} 内")
        text = render_skeleton(action, entities, model_path.name)
        out_path = out_dir / f"{name}.py"
        try:
            compile(text, str(out_path), "exec")  # 语法自查：与 python -m py_compile 同口径
        except SyntaxError as exc:
            _fail(f"动作 {name} 骨架", f"生成的骨架语法非法（生成器内部错误，请反馈）——{exc}")
        out_path.write_text(text, encoding="utf-8")
        #   2. body_ref 一致性：声明路径须指向骨架实际输出（compile_model 按 body_ref 回读 body）
        body_ref = action.get("body_ref")
        if not body_ref:
            print(f"警告：动作 {name} 未声明 body_ref，请在 DSL 中补声明以供 compile_model 回读 body")
        else:
            declared = Path(body_ref)
            if not declared.is_absolute():
                declared = model_path.parent / declared
            if declared.resolve() != out_path.resolve():
                _fail(f"动作 {name} body_ref", f"声明路径 {body_ref!r} 与骨架实际输出 {out_path} 不一致，请对齐")
    print(f"====骨架生成完成====: {len(actions)} 个动作 -> {out_dir}")
    return 0


if __name__ == "__main__":
    # CLI 脚本本体即调试入口：python gen_action_skeleton.py <model.yaml> 跑真实模型。
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    sys.exit(main())
