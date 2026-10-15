"""studio-model 编译核心：DSL v0.3 -> Studio 模板 YAML dict（dsl-spec §8 互导约定）。

主要 Input：DSL 模型 dict（yaml.safe_load 产物，须含 entities）。
主要 Output：compile_studio_model 返回 (studio dict, errors, warnings)——studio dict 为
``{format, object_types, link_types, rule_types}``（键序按真实模板实证）；errors 为阻断性
错误中文描述（外键缺失 / 复合主键无法单字段映射 / 表达式引用不可解析，对应元素被跳过，
不猜）；warnings 为非阻断提示（trigger/admission 不进模板、复合外键连线不进模板（v0.3：
模板连线为单字段对，多字段外键需 Studio 侧手工配置）、code 撞名、四元组去重）。
类型映射：STRING->string、BOOLEAN->boolean、DATE->date、TIMESTAMP->datetime、
DOUBLE/INTEGER/DECIMAL->double；code 用 rel_/rule_ + md5 关键要素前 8 位稳定 hash（幂等）。
links 显式 fk（v0.3 §2）：单字段 fk 进模板（targetPropertyCode=fk 字段），
复合 fk 告警跳过（不猜、不取主字段凑数）。
"""

# 标准库导入
import hashlib
import re
from typing import Any, Optional

# ===========一、常量（§8 机械映射）==========
# TYPE_MAP：DSL 7 种属性类型 -> 模板侧类型（数值统一 double）。
TYPE_MAP = {
    "STRING": "string", "BOOLEAN": "boolean", "DATE": "date", "TIMESTAMP": "datetime",
    "DOUBLE": "double", "INTEGER": "double", "DECIMAL": "double",
}
# FUNC_WHITELIST：表达式函数白名单（与引擎方言一致，白名单外函数 error 不猜）。
FUNC_WHITELIST = {"SUM", "COALESCE", "MAX"}
# TOKEN_RE：DSL 表达式 token（与 lint_model 同一方言定义：数值/字符串/点路径/四则括号逗号）。
TOKEN_RE = re.compile(
    r"(?P<num>\d+(?:\.\d+)?)|(?P<str>'[^']*'|\"[^\"]*\")"
    r"|(?P<path>[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)*)|(?P<op>[+\-*/(),])"
)
# NOT_IN_TEMPLATE：模板不承载的规则类型（实证：两模板 ruleType 仅 calculation）。
NOT_IN_TEMPLATE = ("trigger", "admission")


def _stable_code(prefix: str, *parts: str) -> str:
    """生成稳定 code：前缀 + md5(竖线拼接要素) 前 8 位（同输入必同输出，编译幂等）。

    Args:
        prefix: code 前缀（rel_ / rule_）。
        parts: 参与哈希的关键要素（source/target/外键 或 规则名）。
    Returns:
        形如 rel_ab12cd34 的稳定 code 字符串。
    """
    return prefix + hashlib.md5("|".join(parts).encode("utf-8")).hexdigest()[:8]


def _entity_props(entity: dict[str, Any]) -> dict[str, Any]:
    """取实体 properties（非法结构兜底为空 dict）。Args: entity 实体定义。Returns: 属性 dict。"""
    return entity.get("properties") or {} if isinstance(entity, dict) else {}


def link_pair(value: Any) -> Optional[tuple[str, Optional[list[str]], Optional[str]]]:
    """解析单个 links 项为 (目标实体, 显式外键列表或 None, 显式关系业务名或 None)。

    Args:
        value: links 别名对应的值（目标名字符串，或 {target, fk, name} 映射）。
    Returns:
        简写 ``alias: Target`` -> (Target, None, None)；
        显式 ``{target, fk: [f], name: 业务名}`` -> (target, fk 列表, name 或 None)。
    """
    if isinstance(value, str):
        return value, None, None
    if isinstance(value, dict) and isinstance(value.get("target"), str):
        fk = value.get("fk")
        # link_name：显式关系业务名（可选 str）；非字符串或缺省按 None（编译器兜底）。
        link_name = value.get("name")
        if not isinstance(link_name, str) or not link_name.strip():
            link_name = None
        if isinstance(fk, list) and fk and all(isinstance(f, str) and f for f in fk):
            return value["target"], fk, link_name
        return value["target"], None, link_name  # fk 缺省视同简写外键约定（lint3 已报告结构问题）
    return None


def _entity_links(entity: dict[str, Any]) -> dict[str, tuple[str, Optional[list[str]], Optional[str]]]:
    """取实体 links 的 {别名: (目标实体, 显式外键列表或 None, 显式关系业务名或 None)}（形态非法项跳过）。

    Args: entity 实体定义。Returns: 别名 -> (target, fk, name) 映射。
    """
    links = entity.get("links") if isinstance(entity, dict) and isinstance(entity.get("links"), dict) else None
    return {a: pair for a, v in (links or {}).items()
            if (pair := link_pair(v)) is not None}


def _primary_keys(entity_name: str, entity: dict[str, Any]) -> list[str]:
    """取实体主键字段列表。Args: entity_name 实体名；entity 实体定义。Returns: 主键字段名列表。"""
    return [f for f, s in _entity_props(entity).items()
            if isinstance(s, dict) and s.get("primary")]


# ===========二、object_types 编译（实体 -> 模板对象类型）==========
def compile_object_types(model: dict[str, Any], derived_targets: set[tuple[str, str]]
                         ) -> tuple[list[dict[str, Any]], list[str]]:
    """把 DSL 实体编译为模板 object_types 列表。

    Args:
        model: DSL 模型 dict。
        derived_targets: (实体名, 衍生目标字段) 集合——isDerived 双来源之一（另一为 derived: true）。
    Returns:
        (object_types 列表, errors 中文描述列表)；类型非法的属性跳过并记 error。
    """
    objects: list[dict[str, Any]] = []
    errors: list[str] = []
    for name, ent in (model.get("entities") or {}).items():
        if not isinstance(ent, dict):
            errors.append(f"实体 {name} 定义不是映射结构，已跳过")
            continue
        # attrs：按 DSL 字段声明顺序逐个映射（isKey=primary、required 随主键、isDerived=标记或规则目标）。
        attrs = []
        for field, spec in _entity_props(ent).items():
            if not isinstance(spec, dict) or spec.get("type") not in TYPE_MAP:
                errors.append(f"属性 {name}.{field} 类型缺失或不在 7 种枚举内，已跳过该属性")
                continue
            attrs.append({
                "code": field, "name": spec.get("display_name", ""), "type": TYPE_MAP[spec["type"]],
                "required": bool(spec.get("primary")), "isKey": bool(spec.get("primary")),
                "defaultValue": "", "description": spec.get("description", "") or "",
                "isDerived": bool(spec.get("derived")) or (name, field) in derived_targets,
            })
        objects.append({
            "code": name, "name": ent.get("display_name", ""),
            "description": ent.get("description", "") or "", "enabled": True, "attrs": attrs,
        })
    return objects, errors


# ===========三、link_types 编译（links -> 模板连线）==========
def compile_link_types(model: dict[str, Any]) -> tuple[list[dict[str, Any]], list[str], list[str]]:
    """把 DSL links 编译为模板 link_types（§8：source=目标实体、target=本实体、1:n、
    sourcePropertyCode=目标主键、targetPropertyCode=外键字段，找不到即报错不猜）。

    外键字段取值（v0.3）：简写形态 = 目标主键字段名（约定不变）；显式 fk 单字段 = fk 字段；
    显式 fk 多字段（复合外键）= 模板连线为单字段对无法表达，告警跳过（不取主字段凑数）。

    Args:
        model: DSL 模型 dict。
    Returns:
        (link_types 列表, errors, warnings)；errors 对应连线被跳过（退出码 1）；
        warnings 记四元组去重与复合外键跳过（不阻断）。
    """
    entities = model.get("entities") or {}
    links_out: list[dict[str, Any]] = []
    errors: list[str] = []
    warnings: list[str] = []
    # seen：已生成四元组集合（source, target, sp, tp），同四元组视为同一关系去重。
    seen: set[tuple[str, str, str, str]] = set()
    for holder, ent in entities.items():
        for alias, (target, fk, link_name) in _entity_links(ent).items():
            if target not in entities or not isinstance(entities[target], dict):
                errors.append(f"实体 {holder}.links.{alias} 的目标实体 {target!r} 不存在，该连线已跳过")
                continue
            #   1. 目标主键：仅支持单主键映射（复合主键按 §8 约定无法给出单值 sourcePropertyCode）
            pk = _primary_keys(target, entities[target])
            if len(pk) != 1:
                errors.append(f"实体 {holder}.links.{alias} 的目标实体 {target} 主键字段数={len(pk)}"
                              f"（{','.join(pk) or '∅'}），单字段外键约定无法映射，该连线已跳过")
                continue
            #   2. 外键字段：显式 fk 优先（v0.3）；复合 fk（多字段）模板无法表达，告警跳过
            if fk is not None and len(fk) > 1:
                warnings.append(f"实体 {holder}.links.{alias} 为复合外键（{'+'.join(fk)}），"
                                "模板连线为单字段对无法表达，该连线未进模板（需 Studio 侧手工配置）")
                continue
            fk_field = fk[0] if fk is not None else pk[0]
            #   3. 外键字段必须已声明于本实体 properties（简写=目标主键名约定，显式=fk 字段，均不猜）
            if fk_field not in _entity_props(ent):
                origin = "显式 fk 字段" if fk is not None else f"按约定外键字段应为 {target} 主键同名属性"
                errors.append(f"实体 {holder}.links.{alias}：{origin}"
                              f" {fk_field!r}，但 {holder} 未声明该属性，该连线已跳过")
                continue
            quad = (target, holder, pk[0], fk_field)
            if quad in seen:
                warnings.append(f"实体 {holder}.links.{alias} 与已有连线四元组重复（{target}|{holder}|{fk_field}），已去重")
                continue
            seen.add(quad)
            # link_display_name：平台校验 link_types.name 必填非空——显式业务名优先，
            # 无则兜底用目标实体的中文展示名（"供应商"式名词关系名，模板先例可数名词合法），
            # 展示名异常缺失时最终兜底目标实体英文名，保证恒为非空字符串。
            link_display_name = link_name or (entities[target].get("display_name") or "").strip() or target
            links_out.append({
                "code": _stable_code("rel_", target, holder, fk_field), "source": target, "target": holder,
                "name": link_display_name, "cardinality": "1:n", "description": "",
                "sourcePropertyCode": pk[0], "targetPropertyCode": fk_field,
            })
    return links_out, errors, warnings


# ===========四、表达式中文名转换（code 引用 -> [display_name.字段display_name]）==========
def _plural_names(entities: dict[str, Any]) -> dict[str, set[str]]:
    """构建各实体的复数名集合：{实体名: {表名+s} ∪ {指向该实体的别名+s}}。Args: entities。Returns: 复数名索引。"""
    names: dict[str, set[str]] = {
        name: {str(ent.get("table_name") or "") + "s"} for name, ent in entities.items()
        if isinstance(ent, dict)
    }
    for ent in entities.values():
        for _alias, (target, _fk, _n) in _entity_links(ent).items():
            names.setdefault(target, set())
    for ent in entities.values():
        for alias, (target, _fk, _n) in _entity_links(ent).items():
            names[target].add(alias + "s")
    return names


def _resolve_tail(segs: list[str], idx: int, entity: str, entities: dict[str, Any],
                  plural: dict[str, set[str]]) -> Optional[str]:
    """回溯解析点路径第 idx 段起至倒数第二段，返回末段字段所在的链尾实体名。

    Args:
        segs: 路径分段列表。
        idx: 当前段下标。
        entity: 当前解析所在实体名。
        entities: 实体注册表。
        plural: 复数名索引。
    Returns:
        解析成功返回链尾实体名；失败返回 None。
    """
    if idx == len(segs) - 1:
        return entity  # 已到达末段字段所在实体
    seg = segs[idx]
    # 正向引用：seg 是当前实体的 links 别名（简写/显式形态统一取目标实体）。
    pair = _entity_links(entities.get(entity, {})).get(seg)
    if pair is not None and pair[0] in entities:
        tail = _resolve_tail(segs, idx + 1, pair[0], entities, plural)
        if tail:
            return tail
    # 反向引用：seg 是某实体的复数名（表名+s / 别名+s），且该实体 links 指向当前实体。
    for holder, holder_names in plural.items():
        if seg in holder_names and any(target == entity
                                       for target, _fk, _n in _entity_links(entities.get(holder, {})).values()):
            tail = _resolve_tail(segs, idx + 1, holder, entities, plural)
            if tail:
                return tail
    return None


def _join_tokens(parts: list[str]) -> str:
    """按模板实证空格风格拼接 token：括号/逗号紧贴前 token，其余以单空格相连。

    Args:
        parts: 已转换的 token 文本列表（引用已变为 [实体名.字段名] 形态）。
    Returns:
        拼接后的表达式字符串。
    """
    out = ""
    for i, tok in enumerate(parts):
        if i and tok not in ("(", ")", ",") and parts[i - 1] != "(":
            out += " "
        out += tok
    return out


def convert_expression(expr: str, upstream: str, entities: dict[str, Any],
                       where: str) -> tuple[str, list[str]]:
    """把 DSL 英文 code 表达式转换为模板中文名引用表达式。

    转换口径（§8）：``别名.字段`` / 复数引用 / 多跳路径统一取链尾实体与末段字段的
    display_name 生成 ``[实体名.字段名]``；单段本地字段取 upstream 自身前缀；
    SUM/COALESCE/MAX、四则、字面量原样保留。

    Args:
        expr: DSL 表达式字符串（不含「目标字段:」前缀）。
        upstream: upstream 实体名（路径解析起点）。
        entities: 实体注册表。
        where: 报错定位串（规则名）。
    Returns:
        (转换后表达式, errors 列表)；无法解析的引用保留原文并记 error（不猜）。
    """
    errors: list[str] = []
    parts: list[str] = []
    pos = 0
    while pos < len(expr):
        if expr[pos].isspace():
            pos += 1
            continue
        match = TOKEN_RE.match(expr, pos)
        if not match:
            errors.append(f"规则「{where}」表达式含方言外字符 {expr[pos]!r}，该字符原样保留")
            parts.append(expr[pos])
            pos += 1
            continue
        kind, text = match.lastgroup, match.group(match.lastgroup)
        pos = match.end()
        if kind in ("num", "str", "op"):
            parts.append(text)
            continue
        # 函数名 token：白名单外函数记 error（模板侧无对应能力，不猜转换）。
        if expr[pos:pos + 1] == "(" and "." not in text:
            if text not in FUNC_WHITELIST:
                errors.append(f"规则「{where}」表达式函数 {text!r} 不在白名单 SUM/COALESCE/MAX 内，原样保留")
            parts.append(text)
            continue
        # 点路径引用：解析链尾实体后取双方 display_name 组装 [实体名.字段名]。
        segs = text.split(".")
        tail = upstream if len(segs) == 1 else _resolve_tail(
            segs, 0, upstream, entities, _plural_names(entities))
        tail_props = _entity_props(entities.get(tail, {})) if tail else {}
        last = segs[-1]
        if tail and last in tail_props:
            entity_disp = entities[tail].get("display_name", "")
            parts.append(f"[{entity_disp}.{tail_props[last].get('display_name', '')}]")
        else:
            errors.append(f"规则「{where}」表达式引用 {text!r} 无法从 upstream（{upstream}）解析"
                          "（前缀须为 upstream 属性 / links 别名 / 复数引用），原文保留")
            parts.append(text)
    return _join_tokens(parts), errors


# ===========五、rule_types 编译（derived -> calculation）==========
def compile_rule_types(model: dict[str, Any]) -> tuple[list[dict[str, Any]], set[tuple[str, str]],
                                                        list[str], list[str]]:
    """把 DSL derived_property 规则编译为模板 calculation 规则；trigger/admission 不进模板。

    Args:
        model: DSL 模型 dict。
    Returns:
        四元组 (rule_types 列表, derived_targets 集合供 isDerived 标记, errors, warnings)。
    """
    entities = model.get("entities") or {}
    rules_out: list[dict[str, Any]] = []
    errors: list[str] = []
    warnings: list[str] = []
    derived_targets: set[tuple[str, str]] = set()
    seen_codes: dict[str, str] = {}
    for rule in model.get("rules") or []:
        if not isinstance(rule, dict):
            errors.append("存在非映射结构的规则项，已跳过")
            continue
        name = str(rule.get("name") or "?")
        if rule.get("rule_type") in NOT_IN_TEMPLATE:
            warnings.append(f"{rule['rule_type']} 规则「{name}」不进模板（模板仅承载 calculation），"
                            "需引擎侧配置")
            continue
        if rule.get("rule_type") != "derived_property":
            errors.append(f"规则「{name}」rule_type={rule.get('rule_type')!r} 未知，已跳过")
            continue
        upstreams = [u for u in (rule.get("upstream") or []) if isinstance(u, str)]
        logic = rule.get("logic") if isinstance(rule.get("logic"), str) and ":" in rule.get("logic") else None
        if not upstreams or upstreams[0] not in entities or not logic:
            errors.append(f"规则「{name}」upstream 缺失/实体不存在或 logic 非法，已跳过")
            continue
        upstream = upstreams[0]
        target_field, raw_expr = (part.strip() for part in logic.split(":", 1))
        props = _entity_props(entities[upstream])
        if target_field not in props:
            errors.append(f"规则「{name}」目标字段 {target_field!r} 未声明于 {upstream}.properties，已跳过")
            continue
        expression, expr_errors = convert_expression(raw_expr, upstream, entities, name)
        errors.extend(expr_errors)
        code = _stable_code("rule_", name)
        if code in seen_codes:
            warnings.append(f"规则「{name}」与「{seen_codes[code]}」同名，code={code} 重复"
                            "（code=md5(规则名)[:8]，重名规则请先在 DSL 侧消歧）")
        else:
            seen_codes[code] = name
        derived_targets.add((upstream, target_field))
        rules_out.append({
            "code": code, "name": name, "ruleType": "calculation", "mode": "single",
            "description": rule.get("description", "") or "",
            "ruleConfig": {"expression": expression},
            "outputEntityCode": upstream, "outputPropertyCode": target_field,
            "outputPropertyName": props[target_field].get("display_name", ""),
            "initializationStrategy": "full_recompute",
        })
    return rules_out, derived_targets, errors, warnings


# ===========六、总装与 README 增补==========
def compile_studio_model(model: dict[str, Any]) -> tuple[dict[str, Any], list[str], list[str]]:
    """总装：DSL 模型 -> studio-model dict（含全部三类元素与告警收集）。

    Args:
        model: DSL 模型 dict（须含 entities）。
    Returns:
        (studio dict, errors, warnings)；errors 非空时产物仍返回（可编译子集），由调用方决定退出码。
    """
    rule_types, derived_targets, errors, warnings = compile_rule_types(model)
    object_types, obj_errors = compile_object_types(model, derived_targets)
    link_types, link_errors, link_warnings = compile_link_types(model)
    return {
        "format": "studio-model",
        "object_types": object_types,
        "link_types": link_types,
        "rule_types": rule_types,
    }, errors + obj_errors + link_errors, warnings + link_warnings


def studio_readme_section(studio: dict[str, Any], errors: list[str],
                          warnings: list[str]) -> str:
    """生成 import-README.md 的 Studio 模板章节（追加段，含 trigger 告示与错误清单）。

    Args:
        studio: compile_studio_model 产物。
        errors: 编译错误列表（外键缺失等，逐条入 README 供人工处理）。
        warnings: 编译告警列表（trigger/admission 名单、复合外键名单、code 撞名）。
    Returns:
        可直接追加到 README 末尾的 Markdown 文本。
    """
    # trigger_names：不进模板的 trigger/admission 规则名单（从告警文本中提取规则名）。
    trigger_names = [w.split("「")[1].split("」")[0] for w in warnings if "不进模板" in w]
    lines = [
        "\n## Studio 模板产物（studio-model.yaml）\n",
        "- 由同一 DSL 按 dsl-spec §8 编译：实体->object_types、links->link_types（1:n，外键字段取显式 fk，"
        "简写取目标主键同名属性）、",
        "  derived_property->rule_types（calculation，表达式中文名引用）；code 用 rel_/rule_+md5 稳定 hash，",
        "  重复编译字节一致（幂等）。\n",
        f"- 规模：object_types {len(studio['object_types'])} 个 / link_types {len(studio['link_types'])} 条 /"
        f" rule_types {len(studio['rule_types'])} 条。\n",
    ]
    if trigger_names:
        lines.append(f"- **{len(trigger_names)} 条 trigger/admission 规则不进模板**（模板仅承载 calculation，"
                     "需引擎侧配置）：" + "、".join(trigger_names) + "\n")
    # compound_fks：复合外键连线名单（v0.3：模板连线为单字段对，多字段外键无法表达）。
    compound_fks = [w for w in warnings if "复合外键" in w]
    if compound_fks:
        lines.append(f"- **{len(compound_fks)} 条复合外键连线未进模板**（模板连线为单字段对，"
                     "需 Studio 侧手工配置）：\n")
        lines.extend(f"  - {w}\n" for w in compound_fks)
    if errors:
        lines.append("- **编译错误（对应元素已跳过，须人工处理后再编译）**：\n")
        lines.extend(f"  - {e}\n" for e in errors)
    code_dups = [w for w in warnings if "code=" in w and "重复" in w]
    if code_dups:
        lines.append(f"- 提示：{len(code_dups)} 条重名规则 code 相撞（code=md5(规则名)[:8]），"
                     "导入模板前建议先在 DSL 侧消歧重名规则。\n")
    return "".join(lines)


# ===========七、模块调试入口==========
if __name__ == "__main__":
    # 直接运行时对 gold 基准模型做一次编译自检，人工观察产物结构与告警。
    import sys
    import yaml
    sys.stdout.reconfigure(encoding="utf-8")
    _model = yaml.safe_load(
        __import__("pathlib").Path(__file__).resolve().parents[3].joinpath(
            "poc/m0/goldstandard/gold/model.yaml").read_text(encoding="utf-8"))
    _studio, _errors, _warnings = compile_studio_model(_model)
    print(yaml.dump(_studio, allow_unicode=True, sort_keys=False))
    print("errors:", _errors)
    print("warnings:", _warnings)
