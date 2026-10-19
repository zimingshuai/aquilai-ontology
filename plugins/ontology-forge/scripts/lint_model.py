"""DSL v0.3 模型硬校验器（lint）——ontology-forge 工具链第一环。

主要 Input：DSL YAML 模型文件路径（命令行位置参数）。
主要 Output：stdout 中文 lint 报告 + 退出码（0=通过；1=存在 error；2=文件/解析失败）。
实现 dsl-spec.md §7 全部 12 条确定性检查：第 1-8 条 v0.2 既有（schema/主键/links 闭合/
表达式方言/trigger/下游声明/衍生一致/外键一致）；第 9 条受控词表（v0.3，解析逻辑在
lint_glossary.py）；第 10-11 条动作准入（v0.2.2 §4）；第 12 条规则名全局唯一（v0.3，
studio-model code 需唯一）；外加 v0.2 §3 的 upstream 单元素约束。links 同时支持简写
``alias: Target`` 与显式 fk ``alias: {target, fk: [字段...]}``（简写行为不变）。
error 影响退出码，warning 仅提示。逻辑完全由 DSL 结构驱动，不含实体名特判。
"""

# 标准库导入
import re
import sys
from pathlib import Path
from typing import Any, Optional

# 第三方依赖导入
import yaml

# 项目内部模块导入
import lint_glossary

# ===========一、常量与 YAML 加载（重复键检测）==========
# ALLOWED_TYPES：§2 属性类型 7 枚举（与引擎 data_type 同名）。
ALLOWED_TYPES = {"STRING", "INTEGER", "DOUBLE", "DECIMAL", "BOOLEAN", "DATE", "TIMESTAMP"}
# ALLOWED_OPERATORS：§3.2 trigger 的 operator 枚举。
ALLOWED_OPERATORS = {"==", "!=", ">", ">=", "<", "<=", "in"}
# FUNC_WHITELIST：§3.1 表达式函数白名单。
FUNC_WHITELIST = {"SUM", "COALESCE", "MAX"}
# PARAM_REF_RE：admission logic 中 "@param:参数名" 引用的匹配正则（lint 规则 11）。
PARAM_REF_RE = re.compile(r"@param:([A-Za-z_]\w*)")
# KNOWN_RULE_TYPES：DSL 三种规则类型。
KNOWN_RULE_TYPES = {"derived_property", "trigger", "admission"}
# PASCAL_RE / SNAKE_RE：实体 PascalCase、字段 snake_case 的命名风格正则。
PASCAL_RE = re.compile(r"^[A-Z][A-Za-z0-9]*$")
SNAKE_RE = re.compile(r"^[a-z][a-z0-9]*(?:_[a-z0-9]+)*$")
# TOKEN_RE：表达式方言 token——数值/字符串字面量、点路径、四则与括号逗号。
TOKEN_RE = re.compile(
    r"(?P<num>\d+(?:\.\d+)?)|(?P<str>'[^']*'|\"[^\"]*\")"
    r"|(?P<path>[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)*)|(?P<op>[+\-*/(),])"
)
# _DUP_KEYS：YAML 重复键收集器（加载时填充；links 别名/字段名在 YAML 层重复即暴露）。
_DUP_KEYS: list[str] = []


class _StrictLoader(yaml.SafeLoader):
    """带重复键检测的 SafeLoader：PyYAML 默认对重复键静默后者覆盖，这里改为显式记录。"""


def _strict_mapping(loader: "_StrictLoader", node: yaml.Node, deep: bool = False) -> dict:
    """构造 mapping 并把重复键记入 _DUP_KEYS（值取后者保证后续检查可继续）。

    Args:
        loader: 当前 loader 实例。
        node: YAML mapping 节点。
        deep: 是否深度构造子节点。
    Returns:
        构造完成的 dict。
    """
    loader.flatten_mapping(node)
    mapping: dict[Any, Any] = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in mapping:
            _DUP_KEYS.append(str(key))
        mapping[key] = loader.construct_object(value_node, deep=deep)
    return mapping


_StrictLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _strict_mapping)


# ===========二、报告收集器==========
class Report:
    """lint 问题收集与中文报告渲染。

    Input: 无（构造即空）。
    对外能力: err/warn 分级记录、error_count/warning_count 统计、render 输出报告文本。
    Return: 通过属性与 render() 方法提供结果。
    """

    def __init__(self) -> None:
        # items：问题列表，元素为 (级别, 中文消息)。
        self.items: list[tuple[str, str]] = []

    def err(self, tag: str, where: str, detail: str) -> None:
        """记录一条 error（影响退出码）。Args: tag 规则编号；where 定位；detail 详情。"""
        self.items.append(("error", f"〔{tag}〕{where}——{detail}"))

    def warn(self, tag: str, where: str, detail: str) -> None:
        """记录一条 warning（仅提示）。Args: tag 规则编号；where 定位；detail 详情。"""
        self.items.append(("warning", f"〔{tag}〕{where}——{detail}"))

    @property
    def error_count(self) -> int:
        """error 条数。"""
        return sum(1 for level, _ in self.items if level == "error")

    @property
    def warning_count(self) -> int:
        """warning 条数。"""
        return sum(1 for level, _ in self.items if level == "warning")

    def render(self, path: Path) -> str:
        """渲染中文报告文本。Args: path 被检查的模型路径。Returns: 多行报告字符串。"""
        lines = [f"====lint 开始====: {path}"]
        if not self.items:
            lines.append("未发现问题。")
        lines.extend(f"[{level}] {msg}" for level, msg in self.items)
        verdict = "通过" if self.error_count == 0 else "未通过"
        lines.append(f"====lint {verdict}====: error {self.error_count} 处，warning {self.warning_count} 处")
        return "\n".join(lines)


# ===========三、schema 与主键检查（lint 规则 1、2）==========
def _check_schema(model: dict, report: Report) -> None:
    """lint 规则 1：顶层必填键、命名风格、类型枚举、实体/属性必填键。

    Args:
        model: DSL 模型 dict。
        report: 问题收集器。
    Returns:
        None。
    """
    for key in ("ontology", "version", "entities"):
        if key not in model:
            report.err("lint1 schema", "模型顶层", f"缺少必填键 {key}")
    entities = model.get("entities")
    if not isinstance(entities, dict):
        report.err("lint1 schema", "模型顶层", "entities 缺失或不是映射结构")
        return
    # governance：本体级治理为建议必配；快照导出的 DSL（如 fnb）天然没有，降为 warning。
    gov = model.get("governance")
    if not isinstance(gov, dict):
        report.warn("lint1 schema", "模型顶层", "未配置 governance（owner/maturity），新建本体应补齐")
    for key in ("owner", "maturity"):
        if isinstance(gov, dict) and not gov.get(key):
            report.warn("lint1 schema", "governance", f"缺少 {key}")
    for name, ent in entities.items():
        if not PASCAL_RE.match(str(name)):
            report.err("lint1 schema", f"实体 {name}", "命名不符合 PascalCase")
        if not isinstance(ent, dict):
            report.err("lint1 schema", f"实体 {name}", "定义不是映射结构")
            continue
        for key in ("display_name", "table_name", "description", "properties"):
            if key not in ent:
                report.err("lint1 schema", f"实体 {name}", f"缺少必填键 {key}")
        for field, spec in (ent.get("properties") or {}).items():
            where = f"实体 {name}.{field}"
            if not SNAKE_RE.match(str(field)):
                report.err("lint1 schema", where, "字段命名不符合 snake_case")
            if not isinstance(spec, dict):
                report.err("lint1 schema", where, "属性定义不是映射结构")
                continue
            for key in ("display_name", "type"):
                if key not in spec:
                    report.err("lint1 schema", where, f"缺少必填键 {key}")
            if spec.get("type") not in ALLOWED_TYPES:
                report.err("lint1 schema", where, f"type={spec.get('type')!r} 不在 7 种枚举内")
            if "enum_values" in spec and not isinstance(spec["enum_values"], list):
                report.err("lint1 schema", where, "enum_values 必须为数组")


def _check_primary_keys(entities: dict, report: Report) -> None:
    """lint 规则 2：每实体至少 1 个 primary；主键非 STRING 给 warning。

    Args:
        entities: 实体名 -> 实体定义 dict。
        report: 问题收集器。
    Returns:
        None。
    """
    for name, ent in entities.items():
        props = ent.get("properties") or {}
        pk_fields = [f for f, s in props.items() if isinstance(s, dict) and s.get("primary")]
        if not pk_fields:
            report.err("lint2 主键", f"实体 {name}", "没有任何 primary=true 的主键字段")
        for field in pk_fields:
            if props[field].get("type") != "STRING":
                report.warn("lint2 主键", f"实体 {name}.{field}", f"主键类型为 {props[field].get('type')}，建议 STRING")


# ===========四、links 与外键一致性检查（lint 规则 3、8）==========
def _link_parts(value: Any) -> tuple[Optional[str], Optional[list[str]], Optional[str]]:
    """解析单个 links 项（简写或显式形态，dsl-spec v0.3.4 §2）。

    Args:
        value: links 别名对应的值（目标名字符串，或 {target, fk?, name?} 映射）。
    Returns:
        (目标实体名, 显式外键字段列表或 None, 结构错误消息或 None) 三元组；
        简写形态 fk 为 None；显式形态 fk **可缺省**（视同简写外键约定，
        常见于仅声明关系语义名 name 的场景），仅 fk 存在但非法（空列表/含
        非字符串）时返回结构错误。
    """
    if isinstance(value, str):
        return value, None, None
    if isinstance(value, dict) and isinstance(value.get("target"), str):
        fk = value.get("fk")
        if fk is None:
            return value["target"], None, None  # 仅声明 name 的显式形态，外键按简写约定
        if isinstance(fk, list) and fk and all(isinstance(f, str) and f for f in fk):
            return value["target"], fk, None
        return value["target"], None, "显式形态的 fk 必须为非空字符串列表（如 [sku_code, wh_code]）或省略"
    return None, None, "links 项必须为『目标实体名字符串』或『{target, fk}』映射"


def _iter_links(ent: dict) -> list[tuple[str, Optional[str], Optional[list[str]], Optional[str]]]:
    """取实体 links 的 (别名, 目标, 显式外键, 结构错误) 列表。

    Args:
        ent: 实体定义 dict。
    Returns:
        四元组列表（结构由 _link_parts 给出）；links 结构非法时返回空。
    """
    links = ent.get("links") if isinstance(ent.get("links"), dict) else None
    return [(alias,) + _link_parts(value) for alias, value in (links or {}).items()]


def _link_target(ent: dict, alias: str) -> Optional[str]:
    """取实体 links[alias] 的目标实体名（两种形态统一出口）。Args: ent 实体定义；alias 别名。Returns: 目标名或 None。"""
    for alias_, target, _fk, _err in _iter_links(ent):
        if alias_ == alias:
            return target
    return None


def _check_links(entities: dict, report: Report) -> None:
    """lint 规则 3：links 目标实体存在；别名在实体内唯一（YAML 重复键检测兜底）；
    显式 fk 形态的每个外键字段必须在本实体 properties 中声明（v0.3）。

    Args:
        entities: 实体名 -> 实体定义 dict。
        report: 问题收集器。
    Returns:
        None。
    """
    for name, ent in entities.items():
        if ent.get("links") is not None and not isinstance(ent.get("links"), dict):
            report.err("lint3 links", f"实体 {name}", "links 不是映射结构")
            continue
        own_props = ent.get("properties") or {}
        for alias, target, fk, err in _iter_links(ent):
            where = f"实体 {name}.links.{alias}"
            if err:
                report.err("lint3 links", where, err)
                continue
            if target not in entities:
                report.err("lint3 links", where, f"目标实体 {target!r} 不存在")
            if fk is not None:
                for field in fk:
                    if field not in own_props:
                        report.err("lint3 links", where,
                                   f"显式 fk 字段 {field!r} 未在本实体 properties 声明（v0.3 约定）")
            # lint13：关系业务语义名缺失（简写形态无 name / 显式形态未写 name）——warning
            # （用户实证：只建连线不说清"是什么关系"，拓扑与平台关系名不可读）
            raw = (ent.get("links") or {}).get(alias)
            has_name = isinstance(raw, dict) and isinstance(raw.get("name"), str) and raw["name"].strip()
            if not has_name:
                report.warn("lint13 关系语义名", where,
                            "缺少关系业务语义名（name）——只表达'有指向'未说清是什么关系，"
                            "建议显式形态声明 name（如 订购物料/隶属项目）")
            # lint13b：关系业务定义缺失（v0.3.7，用户实证平台侧全空串）
            has_desc = isinstance(raw, dict) and isinstance(raw.get("description"), str) and raw["description"].strip()
            if not has_desc:
                report.warn("lint13 关系语义名", where,
                            "缺少关系业务定义（description）——一句话说明该关系表达的业务含义/约束，进平台关系的业务定义字段")
    for key in _DUP_KEYS:
        report.err("lint3 links", "YAML 结构", f"重复键 {key!r}（links 别名/字段名必须实体内唯一）")


def _check_foreign_keys(entities: dict, report: Report) -> None:
    """lint 规则 8：links 存在时本实体应有与目标主键同类型的外键字段（不兼容给 warning）。

    Args:
        entities: 实体名 -> 实体定义 dict。
        report: 问题收集器。
    Returns:
        None。
    """
    for name, ent in entities.items():
        # own_types：本实体全部属性类型集合。
        own_types = {s.get("type") for s in (ent.get("properties") or {}).values()
                     if isinstance(s, dict)}
        for alias, target, _fk, err in _iter_links(ent):
            if err or not isinstance(entities.get(target), dict):
                continue  # 结构错误/目标不存在已由 lint3 报告
            # pk_types：目标实体主键类型集合。
            pk_types = {s.get("type") for s in (entities[target].get("properties") or {}).values()
                        if isinstance(s, dict) and s.get("primary")}
            if pk_types and not (pk_types & own_types):
                report.warn("lint8 外键", f"实体 {name}.links.{alias}",
                            f"未找到与 {target} 主键类型({'/'.join(sorted(map(str, pk_types)))})"
                            " 兼容的外键字段（v0.2 约定 2：外键属性与 links 并存）")


# ===========五、表达式静态检查（lint 规则 4/6/7 + upstream 约束）==========
def _build_plural_index(entities: dict) -> dict[str, dict[str, set[str]]]:
    """构建复数引用索引：复数前缀 -> {被指向实体 -> set(引用方实体)}。

    复数名候选 = 实体表名+s（引擎惯例 purchase_orders）∪ 全局 links 中指向该实体的
    别名+s（引擎惯例 sku_in_whs）；某实体的复数名可在「它 links 指向的实体」的表达式中
    作为反向集合引用前缀。

    Args:
        entities: 实体名 -> 实体定义 dict。
    Returns:
        复数引用索引 dict。
    """
    # plural_names：实体 -> 可用复数名集合。
    plural_names: dict[str, set[str]] = {}
    for name, ent in entities.items():
        plural_names.setdefault(name, set()).add(str(ent.get("table_name") or "") + "s")
    for ent in entities.values():
        for alias, target, _fk, _err in _iter_links(ent):
            plural_names.setdefault(target, set()).add(alias + "s")
    index: dict[str, dict[str, set[str]]] = {}
    for holder, names in plural_names.items():
        for target in {t for _a, t, _f, e in _iter_links(entities.get(holder, {})) if not e}:
            for prefix in names:
                index.setdefault(prefix, {}).setdefault(target, set()).add(holder)
    return index


def _path_ok(segs: list[str], idx: int, entity: str, entities: dict,
             plural_index: dict) -> bool:
    """递归判定点路径第 idx 段起能否从 entity 实体解析到末段属性。

    Args:
        segs: 路径分段列表。
        idx: 当前段下标。
        entity: 当前解析所在实体名。
        entities: 实体名 -> 实体定义 dict。
        plural_index: _build_plural_index 产物。
    Returns:
        可解析返回 True。
    """
    ent = entities.get(entity)
    if not isinstance(ent, dict):
        return False
    seg = segs[idx]
    last = idx == len(segs) - 1
    if last:
        return seg in (ent.get("properties") or {})  # 末段必须落在属性上
    # 正向引用：沿 links 别名前进（简写/显式形态统一取目标实体名）。
    nxt = _link_target(ent, seg)
    if nxt is not None and nxt in entities and _path_ok(
            segs, idx + 1, nxt, entities, plural_index):
        return True
    # 反向引用：沿复数引用前进（多跳逐级取反向集合）。
    return any(_path_ok(segs, idx + 1, holder, entities, plural_index)
               for holder in plural_index.get(seg, {}).get(entity, ()))


def _check_expression(expr: str, upstreams: list[str], entities: dict,
                      plural_index: dict, report: Report, where: str) -> None:
    """lint 规则 4 表达式部分：token 白名单、函数白名单、引用前缀可解析。

    Args:
        expr: 表达式字符串（不含「目标字段:」前缀）。
        upstreams: upstream 实体名列表（起点候选）。
        entities: 实体名 -> 实体定义 dict。
        plural_index: 复数引用索引。
        report: 问题收集器。
        where: 报告定位串。
    Returns:
        None。
    """
    tokens: list[tuple[str, str]] = []
    bad_chars: list[str] = []
    pos = 0
    while pos < len(expr):
        if expr[pos].isspace():
            pos += 1
            continue
        match = TOKEN_RE.match(expr, pos)
        if not match:
            bad_chars.append(expr[pos])
            pos += 1
            continue
        tokens.append((match.lastgroup, match.group(match.lastgroup)))
        pos = match.end()
    if bad_chars:
        report.err("lint4 表达式", where,
                   f"表达式含方言外语法元素 {''.join(bad_chars)!r}（仅支持四则/点路径/字面量与 SUM/COALESCE/MAX）")
        return
    for i, (kind, text) in enumerate(tokens):
        if kind != "path":
            continue
        next_is_open = i + 1 < len(tokens) and tokens[i + 1] == ("op", "(")
        if next_is_open and "." not in text:  # 函数名 token
            if text not in FUNC_WHITELIST:
                report.err("lint4 表达式", where, f"函数 {text!r} 不在白名单 SUM/COALESCE/MAX 内")
            continue
        segs = text.split(".")
        if not any(u in entities and _path_ok(segs, 0, u, entities, plural_index)
                   for u in upstreams):
            report.err("lint4 表达式", where,
                       f"引用 {text!r} 无法从 upstream（{'/'.join(upstreams) or '∅'}）解析："
                       "前缀须为 upstream 属性、links 别名或指向 upstream 的复数引用")


def _derived_target(logic: Any) -> tuple[Optional[str], Optional[str]]:
    """拆分 derived 的 logic「目标字段: 表达式」。

    Args:
        logic: 规则 logic 字段（应为字符串）。
    Returns:
        (目标字段, 表达式) 二元组；结构不合法时对应位置为 None。
    """
    if not isinstance(logic, str) or ":" not in logic:
        return None, None
    target, expr = logic.split(":", 1)
    return target.strip() or None, expr.strip() or None


def _check_trigger(rule: dict, entity_upstreams: list[str], entities: dict,
                   plural_index: dict, report: Report, where: str) -> None:
    """lint 规则 5：trigger 条件 field 可解析、operator 合法、in 配数组。

    Args:
        rule: trigger 规则 dict。
        entity_upstreams: upstream 实体名列表（实体存在者）。
        entities: 实体名 -> 实体定义 dict。
        plural_index: 复数引用索引。
        report: 问题收集器。
        where: 报告定位串。
    Returns:
        None。
    """
    logic = rule.get("logic")
    conds = logic.get("ALL") if isinstance(logic, dict) else None
    if not isinstance(conds, list) or not conds:
        report.err("lint5 trigger", where, "logic.ALL 须为非空条件数组（当前引擎仅支持 ALL 合取）")
        return
    for cond in conds:
        if not isinstance(cond, dict) or not cond.get("field"):
            report.err("lint5 trigger", where, f"条件结构不合法：{cond!r}")
            continue
        op = cond.get("operator")
        value = cond.get("value")
        where_cond = f"{where} 条件 {cond['field']}"
        if op not in ALLOWED_OPERATORS:
            report.err("lint5 trigger", where_cond, f"operator={op!r} 不在枚举 ==/!=/>/>=/</<=/in 内")
        if op == "in" and not isinstance(value, list):
            report.err("lint5 trigger", where_cond, f"operator=in 的 value 必须为数组，得到 {value!r}")
        if isinstance(value, list) and op != "in":
            report.err("lint5 trigger", where_cond, f"value 为数组时 operator 必须为 in，当前 {op!r}")
        segs = str(cond["field"]).split(".")
        if entity_upstreams and not any(
                _path_ok(segs, 0, u, entities, plural_index) for u in entity_upstreams):
            report.err("lint5 trigger", where_cond,
                       f"field 无法从 upstream（{'/'.join(entity_upstreams)}）解析")


def _check_rules(model: dict, entities: dict, plural_index: dict,
                 report: Report) -> None:
    """lint 规则 4/5/6/7 与 upstream 单元素约束的规则侧主检查。

    Args:
        model: DSL 模型 dict。
        entities: 实体名 -> 实体定义 dict。
        plural_index: 复数引用索引。
        report: 问题收集器。
    Returns:
        None。
    """
    derived_targets: set[tuple[str, str]] = set()  # (upstream 实体, 衍生目标字段) 集合
    # actions_index：DSL actions 段索引（动作名 -> 动作定义，admission 的 lint 10/11 对照用）。
    actions_index: dict[str, dict] = {
        str(a.get("name")): a for a in (model.get("actions") or [])
        if isinstance(a, dict) and isinstance(a.get("name"), str)
    }
    for idx, rule in enumerate(model.get("rules") or []):
        if not isinstance(rule, dict):
            report.err("lint1 schema", f"rules[{idx}]", "规则不是映射结构")
            continue
        name = str(rule.get("name") or f"规则[{idx}]")
        where = f"规则「{name}」"
        rule_type = rule.get("rule_type")
        if rule_type not in KNOWN_RULE_TYPES:
            report.err("lint1 schema", where, f"未知 rule_type={rule_type!r}")
            continue
        upstream_raw = rule.get("upstream") or []
        # §3 upstream 语义：依附主实体单元素；多元素即 error（v0.2）
        if len(upstream_raw) != 1:
            report.err("§3 upstream", where,
                       f"upstream 有 {len(upstream_raw)} 个元素（{'/'.join(map(str, upstream_raw))}）；"
                       "v0.2 规定 upstream=依附主实体单元素，路径经由的其他实体不算 upstream")
        upstreams = [u for u in upstream_raw if isinstance(u, str)]
        if (unknown := [u for u in upstreams if u not in entities]) and rule_type != "admission":
            report.err("lint1 schema", where, f"upstream 实体不存在：{'/'.join(unknown)}")
        # lint 规则 6：derived 的 downstream 由编译器回填，DSL 不得声明；trigger/admission 必须自带
        if rule_type == "derived_property" and "downstream" in rule:
            report.err("lint6 downstream", where,
                       f"derived_property 不得声明 downstream（{rule['downstream']!r}），编译时回填 Computed Property")
        if rule_type in ("trigger", "admission") and not rule.get("downstream"):
            report.err("lint6 downstream", where, f"{rule_type} 规则缺少 downstream")
        if rule_type == "admission":
            # v0.2.2 §4：admission 依附动作（upstream 为 action 名而非实体），走规则 10/11 专项检查
            _check_admission(rule, actions_index, where, report)
            continue
        entity_upstreams = [u for u in upstreams if u in entities]
        if rule_type == "derived_property":
            target, expr = _derived_target(rule.get("logic"))
            if not target or not expr:
                report.err("lint4 表达式", where, "logic 须为「目标字段: 表达式」字符串")
                continue
            if "." in target:
                report.err("lint4 表达式", where, f"目标字段 {target!r} 不得含点路径")
            # lint 规则 7 方向 A：目标字段必须已声明于 upstream 实体 properties
            if not any(target in (entities[u].get("properties") or {})
                       for u in entity_upstreams):
                report.err("lint7 衍生一致", where,
                           f"目标字段 {target!r} 未声明于 upstream 实体 properties（v0.2 约定 1）")
            elif entity_upstreams:
                derived_targets.add((entity_upstreams[0], target))
            _check_expression(expr, entity_upstreams, entities, plural_index, report, where)
        else:
            _check_trigger(rule, entity_upstreams, entities, plural_index, report, where)
    # lint 规则 7 方向 B：properties 中显式标记 derived 的字段必须有规则承载
    for name, ent in entities.items():
        for field, spec in (ent.get("properties") or {}).items():
            if isinstance(spec, dict) and spec.get("derived") and \
                    (name, field) not in derived_targets:
                report.err("lint7 衍生一致", f"实体 {name}.{field}",
                           "属性标记 derived=true 但没有以它为目标的 derived_property 规则")


def _check_rule_names(model: dict, report: Report) -> None:
    """lint 规则 12（v0.3）：规则名在 rules 数组内全局唯一——同名跨实体重复即 error，
    同名每处报一条并列出所在实体（引擎侧合法，但 studio-model 的 code=md5(规则名) 需唯一）。

    Args:
        model: DSL 模型 dict。
        report: 问题收集器。
    Returns:
        None。
    """
    # owners：规则名 -> 出现处列表（upstream 首元素，admission 为动作名，缺失记 ?）。
    owners: dict[str, list[str]] = {}
    for rule in model.get("rules") or []:
        if not isinstance(rule, dict) or not isinstance(rule.get("name"), str) or not rule["name"]:
            continue
        upstream = rule.get("upstream") or []
        owner = str(upstream[0]) if upstream and isinstance(upstream[0], str) else "?"
        owners.setdefault(rule["name"], []).append(owner)
    for name, holder_list in owners.items():
        if len(holder_list) > 1:
            for holder in holder_list:
                report.err("lint12 规则名唯一", f"规则「{name}」（{holder}）",
                           f"规则名全局重复 {len(holder_list)} 处：{'/'.join(holder_list)}"
                           "（引擎合法但 studio-model code 需唯一，请消歧）")


# ===========六、动作准入检查（lint 规则 10/11，dsl-spec §4）==========
def _collect_param_refs(node: Any, refs: list[str]) -> None:
    """递归收集 admission logic 中的参数引用（两种形态）。

    Args:
        node: logic 任意子节点（str / dict / list / 标量）。
        refs: 收集列表（原地追加）：字符串 "@param:名" 与 {param: 名} dict 引用的参数名。
    Returns:
        None。
    """
    if isinstance(node, str):
        refs.extend(match.group(1) for match in PARAM_REF_RE.finditer(node))
    # {param: <参数名>} 为引擎 value 位置的参数引用形态（键集合恰为 param），其余容器递归展开
    elif isinstance(node, dict) and set(node) == {"param"} and isinstance(node.get("param"), str):
        refs.append(node["param"])
    elif isinstance(node, (dict, list)):
        for value in (node.values() if isinstance(node, dict) else node):
            _collect_param_refs(value, refs)


def _check_admission(rule: dict, actions_index: dict[str, dict],
                     where: str, report: Report) -> None:
    """lint 规则 10/11：admission 的 upstream action 声明与参数引用合法性。

    Args:
        rule: admission 规则 dict（upstream 为 action 名列表）。
        actions_index: DSL actions 段索引（动作名 -> 动作定义）。
        where: 报告定位串。
        report: 问题收集器。
    Returns:
        None。
    """
    upstreams = [u for u in (rule.get("upstream") or []) if isinstance(u, str)]
    #   1. 规则 10：upstream 引用的动作名必须在 DSL actions 段声明
    for act in [u for u in upstreams if u not in actions_index]:
        report.err("lint10 action声明", where, f"upstream 引用的动作 {act!r} 未在 DSL actions 中声明")
    #   2. 规则 11：logic 中 @param:名 / {param: 名} 引用必须存在于对应动作的 parameters
    #    （动作未声明的情形已由规则 10 报告，无从对照 parameters，跳过避免重复计数）
    known_params: set[str] = set()
    for act in (valid_actions := [u for u in upstreams if u in actions_index]):
        if isinstance(params := actions_index[act].get("parameters"), dict):
            known_params |= set(params)
    if not valid_actions:
        return
    refs: list[str] = []
    _collect_param_refs(rule.get("logic"), refs)
    for ref in dict.fromkeys(refs):  # 去重保序
        if ref not in known_params:
            report.err("lint11 参数引用", where,
                       f"参数引用 {ref!r} 不存在于 upstream 动作（{'/'.join(valid_actions)}）的 parameters")


# ===========七、主流程与命令行入口==========
def lint_model(model: dict, report: Report) -> None:
    """执行全部 lint 检查（入口聚合）。Args: model DSL 模型 dict；report 问题收集器。Returns: None。"""
    _check_schema(model, report)
    _check_rule_names(model, report)  # lint 规则 12：规则名全局唯一（v0.3）
    entities = model.get("entities")
    if not isinstance(entities, dict):
        return
    _check_primary_keys(entities, report)
    _check_links(entities, report)
    _check_foreign_keys(entities, report)
    lint_glossary.check_entities(entities, report)  # lint 规则 9：受控词表（v0.3，缺表降级跳过）
    _check_rules(model, entities, _build_plural_index(entities), report)


def main() -> int:
    """命令行入口：加载 YAML -> 逐项 lint -> 输出中文报告与退出码。"""
    if len(sys.argv) != 2:
        print("用法: python lint_model.py <model.yaml>", file=sys.stderr)
        return 2
    path = Path(sys.argv[1])
    if not path.is_file():
        print(f"错误：文件不存在 {path}", file=sys.stderr)
        return 2
    _DUP_KEYS.clear()
    try:
        model = yaml.load(path.read_text(encoding="utf-8"), Loader=_StrictLoader)
    except yaml.YAMLError as exc:
        print(f"错误：YAML 解析失败——{exc}", file=sys.stderr)
        return 2
    if not isinstance(model, dict):
        print("错误：模型顶层不是映射结构", file=sys.stderr)
        return 2
    report = Report()
    lint_model(model, report)
    print(report.render(path))
    return 1 if report.error_count else 0


if __name__ == "__main__":
    # CLI 脚本本体即调试入口：python lint_model.py <model.yaml> 跑真实模型。
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    sys.exit(main())
