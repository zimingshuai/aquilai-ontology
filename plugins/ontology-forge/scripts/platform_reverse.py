"""平台 studio-model 新导入格式逆向为 DSL v0.4（内部模块，由 export_dsl.py 调用）。

主要 Input：平台 studio-model YAML dict（format: studio-model，含 object_types/link_types/
           rule_types/action_types 四段——2026-11 平台新导入格式，见官方升级说明）。
主要 Output：DSL v0.4 模型 dict（语义等价；平台不承载的信息按注记显性化，不虚构）。
逆向原则（有损处一律注记进 assumptions，不静默丢弃）：
  - table_name 平台不承载 → snake_case(实体名) 推导；
  - links 别名平台不承载 → snake_case(目标实体名) 重造（同目标多条加 _2 序号）；
  - 反向引用名 → snake_case(持有方实体名)+s（与 DSL 复数引用惯例一致）；
  - admission 的 lookup 平台不承载 → 注记（实例定位由动作运行时 instances 提供）；
  - 空步骤动作无法区分函数型/recipe → 按 function 型占位并注记需人工确认；
  - 动作 parameters 从步骤/with 的 $ 引用推导（平台由步骤推导，不显式承载）。
"""

# 标准库导入
import re
import sys
from typing import Any

# ===========一、类型与操作符逆映射表==========
# PLATFORM_TYPE_TO_DSL：平台属性类型 -> DSL 类型（integer 精确保留，不压 double）。
PLATFORM_TYPE_TO_DSL = {"string": "STRING", "integer": "INTEGER", "double": "DOUBLE",
                        "boolean": "BOOLEAN", "date": "DATE", "datetime": "TIMESTAMP"}
# OP_PLATFORM_TO_DSL：平台条件操作符 -> DSL operator（编译正向映射的逆）。
OP_PLATFORM_TO_DSL = {"eq": "==", "ne": "!=", "gt": ">", "gte": ">=", "lt": "<", "lte": "<=", "in": "in"}
# OP_DSL_TO_PLATFORM：DSL operator -> 平台操作符（正向映射，条件还原后用于幂等对照）。
OP_DSL_TO_PLATFORM = {v: k for k, v in OP_PLATFORM_TO_DSL.items()}


def _snake(name: str) -> str:
    """PascalCase 实体名转 snake_case（别名/表名/引用名重造用）。

    Args:
        name: 实体名（如 WorkOrder）。
    Returns:
        snake_case 名（如 work_order）。
    """
    return re.sub(r"(?<!^)(?=[A-Z])", "_", name).lower()


def _camel(name: str) -> str:
    """snake_case 转 PascalCase（实体名由 code 直接承载，此函数供路径段重组兜底）。

    Args:
        name: snake_case 名。
    Returns:
        PascalCase 名。
    """
    return "".join(part.capitalize() for part in name.split("_"))


# ===========二、实体与关系逆向==========
def _reverse_objects(sm: dict[str, Any]) -> tuple[dict[str, Any], dict[str, str], dict[str, list[tuple[str, str]]]]:
    """object_types/link_types 逆向为 DSL entities，并建 links 别名索引与邻接表。

    Args:
        sm: 平台 studio-model dict。
    Returns:
        (entities, alias_index, adj)——alias_index: {(持有实体, 目标实体): [别名...]}（同目标多条序号递增）；
        adj: {实体: [(别名或复数引用名, 对端实体, 是否正向), ...]}（表达式点路径还原用：
        正向=持有 links（别名前进），反向=被指向（复数引用名前进））。
    """
    entities: dict[str, Any] = {}
    for obj in sm.get("object_types") or []:
        code = obj.get("code") or ""
        props: dict[str, Any] = {}
        for attr in obj.get("attrs") or []:
            prop: dict[str, Any] = {
                "display_name": attr.get("name", ""),
                "description": attr.get("description", "") or "",
                "type": PLATFORM_TYPE_TO_DSL.get(attr.get("type"), "STRING"),
            }
            if attr.get("isKey"):
                prop["primary"] = True
            if attr.get("isDerived"):
                prop["derived"] = True
            props[attr.get("code") or ""] = prop
        entities[code] = {
            "display_name": obj.get("name", ""),
            "table_name": _snake(code),
            "description": obj.get("description", "") or "",
            "properties": props,
        }
    # links 逆向：平台 link_types 的 source=DSL 目标实体、target=DSL 持有方；
    # 基数翻转（平台 source→target 卡 1:n ≡ DSL 持有方→目标 n:1）。
    alias_index: dict[tuple[str, str], list[str]] = {}
    adj: dict[str, list[tuple[str, str, bool]]] = {code: [] for code in entities}
    for link in sm.get("link_types") or []:
        target, holder = link.get("source") or "", link.get("target") or ""
        if target not in entities or holder not in entities:
            continue
        base = _snake(target)
        aliases = alias_index.setdefault((holder, target), [])
        alias = base if not aliases else f"{base}_{len(aliases) + 1}"
        aliases.append(alias)
        fk = link.get("targetPropertyCode") or ""
        card = "1:1" if str(link.get("cardinality")) == "1:1" else "n:1"
        explicit = {"target": target, "name": link.get("name", "") or "",
                    "description": link.get("description", "") or "", "cardinality": card}
        if fk:
            explicit["fk"] = [fk]
        entities[holder].setdefault("links", {})[alias] = explicit
        adj[holder].append((alias, target, True))
        adj[target].append((_snake(holder) + "s", holder, False))
    return entities, alias_index, adj


# ===========三、表达式与条件还原==========
def _alias_path(upstream: str, segs: list[dict[str, Any]], adj: dict[str, list[tuple[str, str, bool]]],
                where: str) -> str:
    """把 relationPath 段列表还原为 DSL 点路径前缀（沿邻接表逐段匹配方向与端点）。

    Args:
        upstream: 规则输出实体（路径起点）。
        segs: expressionSources 别名的 relationPath 段列表。
        adj: 邻接表。
        where: 报错定位串。
    Returns:
        点路径前缀（如 "equipment" / "work_orders"；无段时空串）。
    Raises:
        SystemExit: 段端点与邻接表不匹配（无法还原）时退出码 1——不猜。
    """
    current, parts = upstream, []
    for seg in segs:
        src, dst = seg.get("sourceEntityCode") or "", seg.get("targetEntityCode") or ""
        # 段匹配：遍历方向 current→dst；邻接对端 == 段目标即命中（正向反向的名字已在建表时算好
        # ——正向=links 别名，反向=snake(持有方)+s 复数引用名），src 由 current 的推进隐式保证。
        for name, other, _forward in adj.get(current, []):
            if dst == other:
                parts.append(name)
                current = other
                break
        else:
            print(f"错误：规则「{where}」关系路径段 {src}->{dst} 无法从 {current} 还原为 DSL 点路径"
                  "（邻接表无匹配边）——不猜", file=sys.stderr)
            raise SystemExit(1)
    return ".".join(parts)


def _ref_to_dsl(platform_ref: str) -> tuple[str, str]:
    """平台 @Entity.attr 引用拆为 (实体名, 属性名)。

    Args:
        platform_ref: 形如 "@WorkOrder.status" 的引用串。
    Returns:
        (实体名, 属性名)；非该形态时 ("", "")。
    """
    if isinstance(platform_ref, str) and platform_ref.startswith("@") and "." in platform_ref:
        entity, _, attr = platform_ref[1:].partition(".")
        return entity, attr
    return "", ""


def _value_to_dsl(value: Any) -> Any:
    """平台条件 right / 赋值里的 $ 参数引用还原为 DSL 引擎方言的 {param: 名} 字典形态。

    Args:
        value: 平台侧值（常量 / "$参数名" / @引用）。
    Returns:
        DSL 侧值（"$x" -> {param: x}；其余原样——@引用与常量两方言一致）。
    """
    if isinstance(value, str) and value.startswith("$"):
        return {"param": value[1:]}
    return value


def _action_ref(code: Any, action_name_by_code: dict[str, str]) -> Any:
    """动作引用还原（模块级，规则逆向与 with 参数推导共用）。

    Args:
        code: 平台动作 code（action_ 哈希或 action_<动作名>）。
        action_name_by_code: 平台 action_types 的 code -> name 索引。
    Returns:
        动作名——声明动作查名；查不到的是隐式动作（未在 DSL 声明），剥 code 的 action_
        前缀还原动作名（编译器对隐式动作按 action_<动作名> 推导 code——往返对称）。
    """
    return action_name_by_code.get(code) or str(code).removeprefix("action_")


def _expr_to_dsl(expression: str, sources: dict[str, Any], upstream: str,
                 adj: dict[str, list[tuple[str, str, bool]]], where: str) -> str:
    """把平台占位符表达式还原为 DSL 点路径表达式。

    Args:
        expression: 平台表达式（含 ${别名.属性}）。
        sources: expressionSources（别名 -> {entityCode, relationPath}）。
        upstream: 规则输出实体。
        adj: 邻接表。
        where: 报错定位串。
    Returns:
        DSL 表达式（${x.attr} -> 点路径.属性；无别名的字面量原样保留）。
    """
    import re as _re
    def _sub(match: "_re.Match[str]") -> str:
        alias, _, attr = match.group(1).partition(".")
        src = sources.get(alias) or {}
        prefix = _alias_path(upstream, src.get("relationPath") or [], adj, where)
        return f"{prefix}.{attr}" if prefix else attr
    return _re.sub(r"\$\{([A-Za-z_][\w.]*)\}", _sub, expression or "")


def _conditions_to_dsl(conds: list[dict[str, Any]], upstream: str,
                        adj: dict[str, list[tuple[str, str, bool]]], where: str) -> list[dict[str, Any]]:
    """平台 when.all 条件列表还原为 DSL 条件列表（@引用 -> 点路径 field；$参数 -> check: param）。

    Args:
        conds: 平台条件项（left/operator/right）。
        upstream: trigger upstream 实体（@引用路径还原起点）。
        adj: 邻接表。
        where: 报错定位串。
    Returns:
        DSL 条件项列表（instance 形态统一；平台 $ 参数条件还原为 check: param）。
    """
    items: list[dict[str, Any]] = []
    for cond in conds or []:
        left, op, right = cond.get("left"), OP_PLATFORM_TO_DSL.get(cond.get("operator")), cond.get("right")
        entity, attr = _ref_to_dsl(left)
        if entity:
            # 属性引用：实体为 upstream 自身时 field 直写属性名；跨实体时还原点路径
            #（用别名路径——from upstream 到 entity 的首段邻接匹配，多段场景平台条件无先例，取首段）。
            field = attr if entity == upstream else f"{_snake(entity)}.{attr}"
            items.append({"field": field, "operator": op, "value": _value_to_dsl(right)})
        elif isinstance(left, str) and left.startswith("$"):
            items.append({"check": "param", "param": left[1:], "operator": op, "value": _value_to_dsl(right)})
    return items


# ===========四、规则与动作逆向==========
def _reverse_rules(sm: dict[str, Any], entities: dict[str, Any],
                    adj: dict[str, list[tuple[str, str, bool]]]) -> tuple[list[dict[str, Any]], dict[str, str]]:
    """rule_types 逆向为 DSL 规则列表（calculation→derived、trigger→branches/旧形态、validation→admission）。

    Args:
        sm: 平台 studio-model dict。
        entities: 已逆向的 DSL 实体（目标字段声明核对用）。
        adj: 邻接表。
    Returns:
        (rules, validation_by_code)——validation_by_code: {validation 规则 code: 规则名}（动作挂载还原用）。
    """
    rules: list[dict[str, Any]] = []
    validation_by_code: dict[str, str] = {}
    # mounted: {动作名: [validation code]}——从 action_types.validation_rules 收集（admission upstream 的权威）。
    mounted: dict[str, list[str]] = {}
    for action in sm.get("action_types") or []:
        for code in action.get("validation_rules") or []:
            mounted.setdefault(action.get("name") or "", []).append(code)
    name_by_code = {r.get("code"): r.get("name") or "" for r in sm.get("rule_types") or []}
    # action_name_by_code：动作 code（action_ 哈希）-> 动作名——trigger/admission 的 downstream/run 引用还原用。
    action_name_by_code = {a.get("code"): a.get("name") or "" for a in sm.get("action_types") or []}


    for rule in sm.get("rule_types") or []:
        name, rtype = rule.get("name") or "", rule.get("ruleType")
        if rtype == "calculation":
            upstream = rule.get("outputEntityCode") or ""
            cfg = rule.get("ruleConfig") or {}
            logic = f"{rule.get('outputPropertyCode')}: {_expr_to_dsl(cfg.get('expression') or '', cfg.get('expressionSources') or {}, upstream, adj, name)}"
            rules.append({"rule_type": "derived_property", "name": name, "upstream": [upstream],
                          "logic": logic, "description": rule.get("description", "") or ""})
        elif rtype == "trigger":
            # upstream 推导：取 cases 条件里首个 @ 引用实体（触发依附的观察对象）；无引用时置空由 lint 拦
            upstream = ""
            for case in rule.get("cases") or []:
                for cond in (case.get("when") or {}).get("all") or []:
                    entity, _ = _ref_to_dsl(cond.get("left"))
                    if entity:
                        upstream = entity
                        break
                if upstream:
                    break
            branches, single_condition, single_run = [], None, None
            for case in rule.get("cases") or []:
                run = case.get("run") or []
                branch: dict[str, Any] = {}
                conds = _conditions_to_dsl((case.get("when") or {}).get("all") or [], upstream, adj, name)
                if conds:
                    branch["condition"] = {"ALL": conds}
                if run:
                    branch["downstream"] = _action_ref(run[0].get("action"), action_name_by_code)
                    if run[0].get("with"):
                        branch["with"] = run[0]["with"]
                branches.append(branch)
            for run_item in rule.get("otherwise") or []:
                branches.append({"downstream": _action_ref(run_item.get("action"), action_name_by_code),
                                 **({"with": run_item["with"]} if run_item.get("with") else {})})
            if len(branches) == 1 and "condition" in branches[0]:
                single_condition, single_run = branches[0]["condition"], branches[0].get("downstream")
            out: dict[str, Any] = {"rule_type": "trigger", "name": name, "upstream": [upstream],
                                   "description": rule.get("description", "") or ""}
            if single_condition is not None:
                out["logic"], out["downstream"] = single_condition, single_run
            else:
                out["branches"] = branches
            rules.append(out)
        elif rtype == "validation":
            validation_by_code[rule.get("code") or ""] = name
            host = next((act for act, codes in mounted.items()
                         if rule.get("code") in codes), "")
            conds_all = (rule.get("when") or {}).get("all") or []
            logic_items = []
            for cond in conds_all:
                entity, attr = _ref_to_dsl(cond.get("left"))
                if entity:
                    logic_items.append({"check": "instance", "entity": entity, "field": attr,
                                        "operator": OP_PLATFORM_TO_DSL.get(cond.get("operator")),
                                        "value": _value_to_dsl(cond.get("right"))})
                elif isinstance(cond.get("left"), str) and cond["left"].startswith("$"):
                    logic_items.append({"check": "param", "param": cond["left"][1:],
                                        "operator": OP_PLATFORM_TO_DSL.get(cond.get("operator")),
                                        "value": _value_to_dsl(cond.get("right"))})
            rules.append({"rule_type": "admission", "name": name, "upstream": [host],
                          "logic": {"ALL": logic_items},
                          "downstream": rule.get("failureMessage") or f"Action 准入拦截: {host}",
                          "description": rule.get("description", "") or ""})
    return rules, validation_by_code


def _reverse_actions(sm: dict[str, Any], mounted: dict[str, list[str]],
                      validation_name_by_code: dict[str, str],
                      with_params: dict[str, set[str]]) -> list[dict[str, Any]]:
    """action_types 逆向为 DSL 动作（声明式 steps 逆转；空步骤按函数型占位并注记）。

    Args:
        sm: 平台 studio-model dict。
        mounted: {动作名: [validation code]}。
        validation_name_by_code: {validation code: 规则名}。
        with_params: {动作名: {with 引用的参数名}}（trigger 的 run.with 键——平台不显式承载
            parameters，从引用处推导，与步骤 $ 引用合并）。
    Returns:
        DSL 动作列表。
    """
    actions: list[dict[str, Any]] = []
    for action in sm.get("action_types") or []:
        name = action.get("name") or ""
        params: dict[str, str] = {}
        steps_out: list[dict[str, Any]] = []
        for step in action.get("steps") or []:
            if step.get("type") == "data":
                assignments = {}
                for field, value in (step.get("assignments") or {}).items():
                    if isinstance(value, str) and value.startswith("$"):
                        assignments[field] = f"@param:{value}"
                        params[value[1:]] = "string"
                    else:
                        assignments[field] = value
                steps_out.append({"type": "data", "entity": step.get("entity") or "",
                                  "operation": step.get("operation") or "update",
                                  "assignments": assignments})
            elif step.get("type") == "notification":
                note = {"type": "notification", "channel": step.get("channel") or "",
                        "recipients": step.get("recipients"), "content": step.get("content")}
                # 通知字段值以 $ 开头 = 参数引用 -> 逆转为 @param: 形态（与 data 赋值同规则）
                for key in ("recipients", "content"):
                    if isinstance(note[key], str) and note[key].startswith("$"):
                        params[note[key][1:]] = "string"
                        note[key] = f"@param:{note[key]}"
                steps_out.append(note)
        entry: dict[str, Any] = {"name": name, "description": action.get("description", "") or ""}
        for extra in with_params.get(name, ()):  # with 引用的参数并入（类型统一 string 占位，注记已列）
            params.setdefault(extra, "string")
        if params:
            entry["parameters"] = {f"${p}": t for p, t in params.items()}
        if steps_out:
            entry["steps"] = steps_out
        else:
            entry["function"] = {"name": name,
                                 "description": "逆向占位：平台 yaml 不区分函数型/recipe（步骤不随 yaml 往返），需人工确认"}
        mounts = [validation_name_by_code.get(c) for c in mounted.get(name, [])
                  if validation_name_by_code.get(c)]
        if mounts:
            entry["validation_rules"] = mounts
        actions.append(entry)
    return actions


# ===========五、组装入口==========
def reverse_platform_model(sm: dict[str, Any], ontology: str, version: str) -> dict[str, Any]:
    """平台 studio-model 新格式逆向为 DSL v0.4 模型。

    Args:
        sm: 平台 studio-model dict（format: studio-model）。
        ontology: 本体标识。
        version: 语义化版本号。
    Returns:
        DSL 模型 dict（含 assumptions 逆向注记——平台不承载的信息显性列出）。
    """
    entities, alias_index, adj = _reverse_objects(sm)
    rules, validation_by_code = _reverse_rules(sm, entities, adj)
    mounted = {a.get("name") or "": a.get("validation_rules") or [] for a in sm.get("action_types") or []}
    # action_name_by_code：动作 code -> 名（with 参数推导按动作名归集）。
    action_name_by_code = {a.get("code"): a.get("name") or "" for a in sm.get("action_types") or []}
    with_params: dict[str, set[str]] = {}
    # host_by_vcode：validation code -> 挂载动作名（admission 条件的 $ 参数并入宿主动作 parameters）。
    host_by_vcode = {}
    for act_name, codes in mounted.items():
        for code in codes:
            host_by_vcode[code] = act_name
    for rule in sm.get("rule_types") or []:
        if rule.get("ruleType") != "validation":
            continue
        host = host_by_vcode.get(rule.get("code") or "")
        for cond in (rule.get("when") or {}).get("all") or []:
            left, right = cond.get("left"), cond.get("right")
            if isinstance(left, str) and left.startswith("$") and host:
                with_params.setdefault(host, set()).add(left[1:])
            if isinstance(right, str) and right.startswith("$") and host:
                with_params.setdefault(host, set()).add(right[1:])
        # trigger 的 with 键收集（cases / otherwise）
    for rule in sm.get("rule_types") or []:
        for seg in rule.get("cases") or []:
            for run_item in seg.get("run") or []:
                for key in (run_item.get("with") or {}):
                    if isinstance(key, str) and key.startswith("$"):
                        with_params.setdefault(
                            _action_ref(run_item.get("action"), action_name_by_code), set()).add(key[1:])
        for run_item in rule.get("otherwise") or []:
            for key in (run_item.get("with") or {}):
                if isinstance(key, str) and key.startswith("$"):
                    with_params.setdefault(
                        _action_ref(run_item.get("action"), action_name_by_code), set()).add(key[1:])
    actions = _reverse_actions(sm, mounted, validation_by_code, with_params)
    multi_alias = [f"{holder}->{target}×{len(aliases)}" for (holder, target), aliases in alias_index.items()
                   if len(aliases) > 1]
    return {
        "ontology": ontology,
        "version": version,
        "base_version": None,
        "governance": {"owner": "逆向导出（待人工补充）", "maturity": "experimental"},
        "entities": entities,
        "rules": rules,
        "actions": actions,
        "competency_questions": [],
        "open_questions": [],
        "conflicts": [],
        "assumptions": [
            "逆向导出：table_name 按 snake_case(实体名) 推导（平台 yaml 不含表名）",
            "逆向导出：links 别名按 snake_case(目标实体名) 重造（平台 yaml 不含别名）",
            "逆向导出：admission 的 lookup 实例定位平台不承载（动作运行时 instances 提供），需人工补",
            "逆向导出：空步骤动作按函数型占位（平台 yaml 不区分函数型/recipe），需人工确认",
            "逆向导出：动作 parameters 从步骤 $ 引用推导；类型统一按 string 占位，需人工核对",
            "逆向导出：CQ/OQ 平台不承载，competency_questions 为空——重新设计 CQ 后再定稿",
        ] + [f"逆向导出：{holder} 指向 {target} 有多条连线，别名已加序号去重，需人工重命名"
             for holder, target in multi_alias],
    }
