"""studio-model 编译核心：DSL v0.4 -> Studio 平台导入 YAML dict（平台 2026-11 新导入格式）。

主要 Input：DSL 模型 dict（yaml.safe_load 产物，须含 entities）。
主要 Output：compile_studio_model 返回 (studio dict, errors, warnings)——studio dict 为
``{format, object_types, link_types, rule_types, action_types}``（顶层与四段键序按平台
2026-11-25 真实导出样本实证）；errors 为阻断性错误中文描述（外键缺失 / 复合主键无法
单字段映射 / 表达式或条件引用不可解析 / 多路径不可判定——对应元素跳过或原文保留，
不猜）；warnings 为非阻断提示（复合外键连线不进模板、code 撞名、四元组去重、
函数型/recipe 动作需平台侧配置、规则引用未声明动作）。
平台新导入格式要点（docs/reference/新品上市POC zip 内升级说明 + model.yaml 样本）：
- 计算规则：表达式占位符 ``${别名.属性code}`` + ruleConfig.expressionSources 逐别名声明
  (entityCode, relationPath)；自身属性 relationPath 为空数组；关系路径每段
  {relationCode, sourceEntityCode, targetEntityCode}（按遍历方向，方向可与 link_types
  定义相反）；历史格式（中文名引用、无路径）平台导入校验会失败——编译器整体切新格式。
- 关系路径推导：从输出实体（upstream）沿 DSL links 图 BFS——持有方向为正向边、被其他
  实体 links 指向为反向边；最短路径唯一自动采用，多条等长路径编译 error 指名（不猜）。
- trigger：cases/otherwise/with；admission：validation + when（挂 $ 参数与实例字段）+
  failureMessage；动作：action_types 声明式 steps（data/notification），函数型/recipe
  动作 steps 为空数组并在 import-README 列名单；action_types 不写 parameters（平台由
  步骤 $参数推导）。
- 类型映射：INTEGER->integer（不再压 double）、DECIMAL/DOUBLE->double、STRING->string、
  BOOLEAN->boolean、DATE->date、TIMESTAMP->datetime。
- links 可选 cardinality（DSL 方向=本实体:目标，n:1 缺省 | 1:1）编译翻转为平台方向
  （平台 source=目标实体）：n:1->1:n、1:1->1:1。
- code 用 rel_/rule_/action_ + md5 关键要素前 8 位稳定 hash（幂等）。
"""

# 标准库导入
import hashlib
import re
from typing import Any, Optional

# ===========一、常量（平台格式机械映射，集中声明）==========
# TYPE_MAP：DSL 7 种属性类型 -> 平台属性类型（INTEGER 保真为 integer，不再压 double）。
TYPE_MAP = {
    "STRING": "string", "BOOLEAN": "boolean", "DATE": "date", "TIMESTAMP": "datetime",
    "DOUBLE": "double", "INTEGER": "integer", "DECIMAL": "double",
}
# FUNC_WHITELIST：表达式函数白名单（与引擎方言一致，白名单外函数 error 不猜）。
FUNC_WHITELIST = {"SUM", "COALESCE", "MAX"}
# TOKEN_RE：DSL 表达式 token（与 lint_model 同一方言定义：数值/字符串/点路径/四则括号逗号）。
TOKEN_RE = re.compile(
    r"(?P<num>\d+(?:\.\d+)?)|(?P<str>'[^']*'|\"[^\"]*\")"
    r"|(?P<path>[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)*)|(?P<op>[+\-*/(),])"
)
# OPERATOR_MAP：DSL 条件操作符 -> 平台操作符（全集 eq/ne/gt/gte/lt/lte/in 的 DSL 方言子集）。
OPERATOR_MAP = {"==": "eq", "!=": "ne", ">": "gt", ">=": "gte", "<": "lt", "<=": "lte", "in": "in"}
# OPERATOR_REVERSE：平台操作符 -> DSL 操作符（逆向导出用；empty/not_empty/contains 等
# DSL 无槽位的操作符不在此表，逆向遇到即显性报错）。
OPERATOR_REVERSE = {v: k for k, v in OPERATOR_MAP.items()}
# CARDINALITY_FLIP：DSL links cardinality（本实体:目标）-> 平台 link cardinality
# （平台方向 source=目标实体、target=本实体，语义翻转）。
CARDINALITY_FLIP = {"n:1": "1:n", "1:1": "1:1"}
# PLATFORM_VALUE_KEYS：步骤/with/right 值来源里以 @/$ 开头的常量包装键（平台规范）。
CONSTANT_KEY = "constant"
# TRIGGER_CASE_LIMIT：平台 trigger 分支上限（cases + otherwise 总数，官方说明）。
TRIGGER_CASE_LIMIT = 10
# DATA_OPERATIONS：data 步骤 operation 白名单（平台简化报文，官方说明）。
DATA_OPERATIONS = ("create", "update")
# DECLARATIVE_STEP_TYPES：声明式步骤类型白名单（data / notification）。
DECLARATIVE_STEP_TYPES = ("data", "notification")


def _stable_code(prefix: str, *parts: str) -> str:
    """生成稳定 code：前缀 + md5(竖线拼接要素) 前 8 位（同输入必同输出，编译幂等）。

    Args:
        prefix: code 前缀（rel_ / rule_ / action_）。
        parts: 参与哈希的关键要素（连线四元组 / 规则名 / 动作名）。
    Returns:
        形如 rel_ab12cd34 的稳定 code 字符串。
    """
    return prefix + hashlib.md5("|".join(parts).encode("utf-8")).hexdigest()[:8]


def _entity_props(entity: dict[str, Any]) -> dict[str, Any]:
    """取实体 properties（非法结构兜底为空 dict）。Args: entity 实体定义。Returns: 属性 dict。"""
    return entity.get("properties") or {} if isinstance(entity, dict) else {}


def link_pair(value: Any) -> Optional[tuple[str, Optional[list[str]], Optional[str], str, str]]:
    """解析单个 links 项为 (目标实体, 显式外键列表或 None, 显式关系业务名或 None, 关系定义, 基数)。

    Args:
        value: links 别名对应的值（目标名字符串，或 {target, fk, name, cardinality} 映射）。
    Returns:
        简写 ``alias: Target`` -> (Target, None, None, "", "n:1")；
        显式 ``{target, fk: [f], name: 业务名, cardinality: 1:1}`` ->
        (target, fk 列表, name 或 None, description, cardinality)；基数非法时返回 None（不猜）。
    """
    if isinstance(value, str):
        return value, None, None, "", "n:1"
    if isinstance(value, dict) and isinstance(value.get("target"), str):
        fk = value.get("fk")
        # link_name：显式关系业务名（可选 str）；非字符串或缺省按 None（编译器兜底）。
        link_name = value.get("name")
        if not isinstance(link_name, str) or not link_name.strip():
            link_name = None
        # link_desc：关系业务定义（可选 str；缺省为空串——平台 description 字段）。
        link_desc = value.get("description")
        if not isinstance(link_desc, str):
            link_desc = ""
        # cardinality：v0.4 可选键（方向=本实体:目标，n:1 缺省 | 1:1）；非法值返回 None（不猜）。
        cardinality = value.get("cardinality", "n:1")
        if cardinality not in CARDINALITY_FLIP:
            return None
        if isinstance(fk, list) and fk and all(isinstance(f, str) and f for f in fk):
            return value["target"], fk, link_name, link_desc, cardinality
        return value["target"], None, link_name, link_desc, cardinality  # fk 缺省视同简写约定
    return None


def _entity_links(entity: dict[str, Any]) -> dict[str, tuple[str, Optional[list[str]], Optional[str], str, str]]:
    """取实体 links 的 {别名: (目标实体, 显式外键或 None, 关系业务名或 None, 定义, 基数)}。

    Args: entity 实体定义。Returns: 别名 -> 解析元组映射（形态非法项跳过）。
    """
    links = entity.get("links") if isinstance(entity, dict) and isinstance(entity.get("links"), dict) else None
    return {a: pair for a, v in (links or {}).items()
            if (pair := link_pair(v)) is not None}


def _primary_keys(entity_name: str, entity: dict[str, Any]) -> list[str]:
    """取实体主键字段列表。Args: entity_name 实体名；entity 实体定义。Returns: 主键字段名列表。"""
    return [f for f, s in _entity_props(entity).items()
            if isinstance(s, dict) and s.get("primary")]


# ===========二、object_types 编译（实体 -> 平台对象类型）==========
def compile_object_types(model: dict[str, Any], derived_targets: set[tuple[str, str]]
                         ) -> tuple[list[dict[str, Any]], list[str]]:
    """把 DSL 实体编译为平台 object_types 列表（键序按平台样本：code/name/description/enabled/attrs）。

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


# ===========三、link_types 编译（links -> 平台连线 + 关系路径边表）==========
def compile_link_types(model: dict[str, Any]
                       ) -> tuple[list[dict[str, Any]], dict[str, list[tuple[str, str]]], list[str], list[str]]:
    """把 DSL links 编译为平台 link_types，并构建表达式关系路径推导用的双向边表。

    连线口径：source=目标实体、target=本实体（方向与 2026-10 既有约定一致，平台样本
    实证该方向合法）；sourcePropertyCode=目标主键、targetPropertyCode=外键字段；
    cardinality 按 DSL cardinality 翻转写入（n:1->1:n、1:1->1:1，缺省 n:1）。

    Args:
        model: DSL 模型 dict。
    Returns:
        四元组 (link_types 列表, edges 边表, errors, warnings)；edges 为
        {实体名: [(邻接实体名, relationCode), ...]}——每条成功编出的连线产生
        正向边（本实体->目标）与反向边（目标->本实体），同一 relationCode 供
        计算规则 BFS 推导 relationPath；errors 对应连线被跳过（退出码 1）；
        warnings 记四元组去重与复合外键跳过（不阻断）。
    """
    entities = model.get("entities") or {}
    links_out: list[dict[str, Any]] = []
    # edges：邻接边表 {实体: [(邻接实体, relationCode), ...]}，正反向各记一条。
    edges: dict[str, list[tuple[str, str]]] = {}
    errors: list[str] = []
    warnings: list[str] = []
    # seen：已生成四元组集合（source, target, sp, tp），同四元组视为同一关系去重。
    seen: set[tuple[str, str, str, str]] = set()
    for holder, ent in entities.items():
        for alias, (target, fk, link_name, link_desc, cardinality) in _entity_links(ent).items():
            if target not in entities or not isinstance(entities[target], dict):
                errors.append(f"实体 {holder}.links.{alias} 的目标实体 {target!r} 不存在，该连线已跳过")
                continue
            #   1. 目标主键：仅支持单主键映射（复合主键无法给出单值 sourcePropertyCode）
            pk = _primary_keys(target, entities[target])
            if len(pk) != 1:
                errors.append(f"实体 {holder}.links.{alias} 的目标实体 {target} 主键字段数={len(pk)}"
                              f"（{','.join(pk) or '∅'}），单字段外键约定无法映射，该连线已跳过")
                continue
            #   2. 外键字段：显式 fk 优先；复合 fk（多字段）平台单字段连线无法表达，告警跳过
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
            # 无则兜底目标实体中文展示名，展示名异常缺失时最终兜底目标实体英文名。
            link_display_name = link_name or (entities[target].get("display_name") or "").strip() or target
            rel_code = _stable_code("rel_", target, holder, fk_field)
            links_out.append({
                "code": rel_code, "source": target, "target": holder,
                "name": link_display_name, "cardinality": CARDINALITY_FLIP[cardinality],
                "description": link_desc,
                "sourcePropertyCode": pk[0], "targetPropertyCode": fk_field,
            })
            # 关系路径边表：正向边（持有方向）+ 反向边（被指向），共用同一 relationCode
            # （平台允许遍历方向与 link_types 定义相反，升级说明 2026-10-20 官方口径）。
            edges.setdefault(holder, []).append((target, rel_code))
            edges.setdefault(target, []).append((holder, rel_code))
    return links_out, edges, errors, warnings


# ===========四、表达式关系路径推导（BFS 最短路径，多条等长即报错不猜）==========
def _plural_names(entities: dict[str, Any]) -> dict[str, set[str]]:
    """构建各实体的复数名集合：{实体名: {表名+s} ∪ {指向该实体的别名+s}}。Args: entities。Returns: 复数名索引。"""
    names: dict[str, set[str]] = {
        name: {str(ent.get("table_name") or "") + "s"} for name, ent in entities.items()
        if isinstance(ent, dict)
    }
    for ent in entities.values():
        for _alias, (target, _fk, _n, _d, _c) in _entity_links(ent).items():
            names.setdefault(target, set())
    for ent in entities.values():
        for alias, (target, _fk, _n, _d, _c) in _entity_links(ent).items():
            names[target].add(alias + "s")
    return names


def _resolve_tail(segs: list[str], idx: int, entity: str, entities: dict[str, Any],
                  plural: dict[str, set[str]]) -> Optional[str]:
    """回溯解析点路径第 idx 段起，返回末段字段所在的链尾实体名（只定实体，路径另由 BFS 推导）。

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
                                       for target, _fk, _n, _d, _c in _entity_links(entities.get(holder, {})).values()):
            tail = _resolve_tail(segs, idx + 1, holder, entities, plural)
            if tail:
                return tail
    return None


def shortest_paths(edges: dict[str, list[tuple[str, str]]], start: str, goal: str
                   ) -> list[list[tuple[str, str, str]]]:
    """BFS 收集 start 到 goal 的全部最短关系路径（供表达式/条件的关系路径推导）。

    Args:
        edges: compile_link_types 产出的双向边表。
        start: 起点实体名（规则输出实体 upstream）。
        goal: 终点实体名（引用属性所属实体）。
    Returns:
        最短路径列表；每条路径为段列表 [(from 实体, to 实体, relationCode), ...]；
        start==goal 返回 [[]]（空路径，自身属性）；不可达返回 []。
    """
    if start == goal:
        return [[]]
    if start not in edges or goal not in edges:
        return []
    # dist：BFS 层深度（仅记最短深度，重复邻居按首次入层）。
    dist: dict[str, int] = {start: 0}
    frontier = [start]
    while frontier:
        next_frontier: list[str] = []
        for entity in frontier:
            for neighbor, _code in edges.get(entity, []):
                if neighbor not in dist:
                    dist[neighbor] = dist[entity] + 1
                    next_frontier.append(neighbor)
        frontier = next_frontier
    if goal not in dist:
        return []
    # in_edges：入边索引 {实体: [(前驱实体, relationCode), ...]}，沿 dist 递减回溯收集全部最短路径。
    in_edges: dict[str, list[tuple[str, str]]] = {}
    for entity, adjacency in edges.items():
        for neighbor, code in adjacency:
            in_edges.setdefault(neighbor, []).append((entity, code))
    paths: list[list[tuple[str, str, str]]] = []

    def _backtrack(cur: str, acc: list[tuple[str, str, str]]) -> None:
        """从 goal 沿最短前驱回溯到 start，收集全部等长最短路径段。"""
        if cur == start:
            paths.append(list(reversed(acc)))
            return
        for prev, code in in_edges.get(cur, []):
            if dist.get(prev) == dist[cur] - 1:
                _backtrack(prev, acc + [(prev, cur, code)])

    _backtrack(goal, [])
    return paths


def _alias_name(index: int) -> str:
    """按源出现顺序生成表达式占位符别名（样本先例 x/y；超出后 x3、x4 机械递增）。

    Args:
        index: 该表达式内 (目标实体, 关系路径) 的首次出现序号（0 起）。
    Returns:
        别名字符串（x / y / z / x3 / x4 ...）。
    """
    if index < 3:
        return "xyz"[index]
    return f"x{index + 1}"


def _join_tokens(parts: list[str]) -> str:
    """按平台样本空格风格拼接 token：括号/逗号紧贴前 token，其余以单空格相连。

    Args:
        parts: 已转换的 token 文本列表（引用已变为 ${别名.属性code} 形态）。
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
                       edges: dict[str, list[tuple[str, str]]], where: str
                       ) -> tuple[str, dict[str, dict[str, Any]], list[str]]:
    """把 DSL 表达式编译为平台占位符表达式 + expressionSources（新导入格式核心）。

    转换口径：每个点路径引用（自身属性 / 别名链 / 复数引用）解析出链尾实体与末段字段，
    关系路径由 BFS 推导——最短路径唯一自动采用；多条等长路径 error 中文指名（含候选数与
    涉及实体，提示建模侧改写），不可达同样 error（不猜）；同一 (目标实体, 关系路径) 共用
    一个别名（平台样本先例）；自身属性 relationPath 为空数组。

    Args:
        expr: DSL 表达式字符串（不含「目标字段:」前缀）。
        upstream: upstream 实体名（路径解析起点 = 规则输出实体）。
        entities: 实体注册表。
        edges: compile_link_types 产出的双向边表。
        where: 报错定位串（规则名）。
    Returns:
        (占位符表达式, expressionSources 映射, errors 列表)；无法解析的引用保留原文
        并记 error（不进 expressionSources）。
    """
    errors: list[str] = []
    parts: list[str] = []
    # sources：别名 -> {entityCode, relationPath}；alias_index：按首次出现序分配别名。
    sources: dict[str, dict[str, Any]] = {}
    alias_keys: dict[tuple[str, tuple[tuple[str, str, str], ...]], str] = {}
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
        # 函数名 token：白名单外函数记 error（平台侧无对应能力，不猜转换）。
        if expr[pos:pos + 1] == "(" and "." not in text:
            if text not in FUNC_WHITELIST:
                errors.append(f"规则「{where}」表达式函数 {text!r} 不在白名单 SUM/COALESCE/MAX 内，原样保留")
            parts.append(text)
            continue
        # 点路径引用：解析链尾实体 -> BFS 推导关系路径 -> 占位符 + expressionSources。
        segs = text.split(".")
        tail = upstream if len(segs) == 1 else _resolve_tail(
            segs, 0, upstream, entities, _plural_names(entities))
        tail_props = _entity_props(entities.get(tail, {})) if tail else {}
        last = segs[-1]
        if not tail or last not in tail_props:
            errors.append(f"规则「{where}」表达式引用 {text!r} 无法从 upstream（{upstream}）解析"
                          "（前缀须为 upstream 属性 / links 别名 / 复数引用），原文保留")
            parts.append(text)
            continue
        paths = shortest_paths(edges, upstream, tail)
        if not paths:
            errors.append(f"规则「{where}」表达式引用 {text!r} 的目标实体 {tail} 在关系图上不可达"
                          "（连线缺失或被跳过），原文保留")
            parts.append(text)
            continue
        if len(paths) > 1:
            involved = sorted({e for path in paths for seg in path for e in seg[:2]})
            errors.append(f"规则「{where}」表达式引用 {text!r} 存在 {len(paths)} 条等长最短关系路径"
                          f"（涉及实体：{'、'.join(involved)}），无法自动确定关系路径——"
                          "请建模侧改写（换 upstream 或在中间实体上先建衍生规则），不猜")
            parts.append(text)
            continue
        path = paths[0]
        key = (tail, tuple(path))
        if key not in alias_keys:
            alias = _alias_name(len(alias_keys))
            alias_keys[key] = alias
            sources[alias] = {
                "entityCode": tail,
                "relationPath": [{"relationCode": code, "sourceEntityCode": src, "targetEntityCode": dst}
                                 for src, dst, code in path],
            }
        parts.append(f"${{{alias_keys[key]}.{last}}}")
    return _join_tokens(parts), sources, errors


# ===========五、条件与值映射（trigger when / validation when / with / assignments）==========
def _platform_value(value: Any, where: str, errors: list[str]) -> Any:
    """把 DSL 值映射为平台值来源：常量原样（裸 $ 开头用 {constant: 文本} 包装）、
    "@param:$x" 与 {param: X} -> "$x"、"@Entity.attr" 原样（实体名/字段名即平台 code）。

    Args:
        value: DSL 侧值（标量 / 数组 / "@param:$x" / "@Entity.attr" / {param: X} / {constant: 文本}）。
        where: 报错定位串。
        errors: 错误收集列表（就地追加）。
    Returns:
        平台侧值（原样引用或包装常量）。
    """
    if value is None:
        return None
    if isinstance(value, dict):
        if set(value) == {"param"} and isinstance(value.get("param"), str):
            return f"${value['param']}"
        return value  # {constant: 文本} 等既有平台包装原样透传
    if isinstance(value, str):
        # 值形态判定次序（与 lint17/18 的值形态白名单一致）：
        #   1. "@param:$x"（冻结语法参数引用）-> 平台 "$x"
        if value.startswith("@param:$") and len(value) > len("@param:$"):
            return value[len("@param:"):]
        #   2. "@Entity.attr"（冻结语法实体属性引用）-> 原样（可解析性由 lint 把关，编译器不重复校验）
        if value.startswith("@") and "." in value:
            return value
        #   3. 裸 @/$ 开头的常量文本：按平台规范包装防误读（@param: 前缀缺参、单段 @ 无点路径均落此分支）
        if value[:1] in ("@", "$"):
            errors.append(f"{where}：常量 {value!r} 以 @/$ 开头，已按平台规范包装为 {{constant: 文本}}")
            return {CONSTANT_KEY: value}
    return value


def _resolve_field(field: Any, upstream: str, entities: dict[str, Any],
                   edges: dict[str, list[tuple[str, str]]], where: str
                   ) -> Optional[tuple[str, str]]:
    """解析条件 field（单段属性或点路径）为 (目标实体名, 属性 code)，多路径/不可解析报 error。

    Args:
        field: DSL 条件字段（upstream 自身属性名，或跨实体点路径）。
        upstream: trigger upstream 实体名（路径解析起点）。
        entities: 实体注册表。
        edges: 关系路径边表。
        where: 报错定位串。
    Returns:
        (目标实体, 属性 code)；失败 None（错误已入 errors——由调用方收集，此处直接返回 None，
    错误文本由调用方按需补齐；本函数只负责机械解析，错误消息统一在调用方生成）。
    """
    if not isinstance(field, str) or not field:
        return None
    segs = field.split(".")
    tail = upstream if len(segs) == 1 else _resolve_tail(
        segs, 0, upstream, entities, _plural_names(entities))
    if not tail or segs[-1] not in _entity_props(entities.get(tail, {})):
        return None
    paths = shortest_paths(edges, upstream, tail)
    if len(paths) != 1:
        return None
    return tail, segs[-1]


def _compile_conditions(conditions: Any, upstream: str, entities: dict[str, Any],
                        edges: dict[str, list[tuple[str, str]]], where: str,
                        errors: list[str]) -> Optional[list[dict[str, Any]]]:
    """把 DSL 条组 ``{ALL: [{field, operator, value}, ...]}`` 编译为平台 ``when.all`` 条件列表。

    Args:
        conditions: DSL 条组 dict（仅 ALL，DSL 方言现状）。
        upstream: 路径解析起点实体。
        entities: 实体注册表。
        edges: 关系路径边表。
        where: 报错定位串。
        errors: 错误收集列表（就地追加，任一条件非法即返回 None）。
    Returns:
        平台条件项列表 [{left, operator, right?}, ...]；失败返回 None。
    """
    if not isinstance(conditions, dict) or not isinstance(conditions.get("ALL"), list):
        errors.append(f"规则「{where}」条件组缺少 ALL 列表（DSL 方言仅支持 ALL），该规则已跳过")
        return None
    out: list[dict[str, Any]] = []
    for idx, cond in enumerate(conditions["ALL"]):
        if not isinstance(cond, dict):
            errors.append(f"规则「{where}」条件[{idx}] 不是映射结构，该规则已跳过")
            return None
        operator = cond.get("operator")
        if operator not in OPERATOR_MAP:
            errors.append(f"规则「{where}」条件[{idx}] operator={operator!r} 不在 DSL 操作符表"
                          "（== / != / > / >= / < / <= / in），该规则已跳过")
            return None
        resolved = _resolve_field(cond.get("field"), upstream, entities, edges, where)
        if resolved is None:
            errors.append(f"规则「{where}」条件[{idx}] 字段 {cond.get('field')!r} 无法从 upstream"
                          f"（{upstream}）解析或存在多条等长关系路径，该规则已跳过")
            return None
        item = {"left": f"@{resolved[0]}.{resolved[1]}", "operator": OPERATOR_MAP[operator]}
        right = _platform_value(cond.get("value"), f"规则「{where}」条件[{idx}]", errors)
        if right is not None:
            item["right"] = right
        out.append(item)
    return out


def _with_dict(with_value: Any, where: str, errors: list[str]) -> Optional[dict[str, Any]]:
    """把 DSL 分支 ``with`` 映射（<$参数名> -> 常量 | @Entity.attr）编译为平台 run[].with。

    Args:
        with_value: DSL with 映射（键带 $ 前缀）。
        where: 报错定位串。
        errors: 错误收集列表（就地追加）。
    Returns:
        平台 with dict（键保留 $ 前缀、值走 _platform_value）；非法时 None。
    """
    if with_value is None:
        return None
    if not isinstance(with_value, dict):
        errors.append(f"规则「{where}」with 须为「<$参数名>: 值」映射结构，该规则已跳过")
        return None
    out: dict[str, Any] = {}
    for key, value in with_value.items():
        if not isinstance(key, str) or not key.startswith("$") or not key[1:]:
            errors.append(f"规则「{where}」with 键 {key!r} 须为 <$参数名> 形态，该规则已跳过")
            return None
        mapped = _platform_value(value, f"规则「{where}」with[{key}]", errors)
        out[key] = mapped if mapped is not None else None
    return out


def _action_code(name: str, action_index: dict[str, str]) -> str:
    """按动作名解析平台动作 code：DSL actions 声明的用稳定 hash code，未声明的按
    平台内置动作命名形态 ``action_<动作名>`` 推导（import-README 会列名单要求人工核对）。

    Args:
        name: DSL 动作名（trigger downstream / admission upstream 引用）。
        action_index: {动作名: 平台 code} 索引（由 DSL actions 段构建）。
    Returns:
        平台动作 code 字符串。
    """
    return action_index.get(name, "action_" + name)


# ===========六、规则编译（calculation / trigger / validation）==========
def compile_rule_types(model: dict[str, Any], edges: dict[str, list[tuple[str, str]]],
                       action_index: dict[str, str]
                       ) -> tuple[list[dict[str, Any]], set[tuple[str, str]], dict[str, list[str]], list[str], list[str]]:
    """把 DSL rules 全量编译为平台 rule_types（calculation + trigger + validation 三类齐编）。

    Args:
        model: DSL 模型 dict。
        edges: compile_link_types 产出的关系路径边表。
        action_index: {动作名: 平台动作 code} 索引（trigger run / admission 挂载引用）。
    Returns:
        五元组 (rule_types 列表, derived_targets 集合, validation_mounts 挂载表,
        errors, warnings)；validation_mounts 为 {动作名: [validation 规则 code, ...]}
        （供 action_types 挂载 validation_rules，DSL admission 的 upstream 为权威来源）；
        warnings 记 code 撞名与规则引用未声明动作（import-README 平移列出，不静默）。
    """
    entities = model.get("entities") or {}
    rules_out: list[dict[str, Any]] = []
    errors: list[str] = []
    warnings: list[str] = []
    derived_targets: set[tuple[str, str]] = set()
    # validation_mounts：动作名 -> 挂载的 validation 规则 code 列表（admission upstream 权威）。
    validation_mounts: dict[str, list[str]] = {}
    # referenced_actions：规则引用过的动作名（供 import-README 列「未在 DSL actions 声明」名单）。
    referenced_actions: set[str] = set()
    seen_codes: dict[str, str] = {}
    for rule in model.get("rules") or []:
        if not isinstance(rule, dict):
            errors.append("存在非映射结构的规则项，已跳过")
            continue
        name = str(rule.get("name") or "?")
        rule_type = rule.get("rule_type")
        code = _stable_code("rule_", name)
        if code in seen_codes:
            warnings.append(f"规则「{name}」与「{seen_codes[code]}」同名，code={code} 重复"
                            "（code=md5(规则名)[:8]，重名规则请先在 DSL 侧消歧）")
        else:
            seen_codes[code] = name
        if rule_type == "derived_property":
            compiled = _compile_calculation(rule, name, code, entities, edges, errors)
            if compiled:
                rules_out.append(compiled)
                upstream, target_field = compiled["outputEntityCode"], compiled["outputPropertyCode"]
                derived_targets.add((upstream, target_field))
        elif rule_type == "trigger":
            compiled = _compile_trigger(rule, name, code, entities, edges, action_index,
                                        referenced_actions, errors)
            if compiled:
                rules_out.append(compiled)
        elif rule_type == "admission":
            compiled = _compile_validation(rule, name, code, entities, edges,
                                            validation_mounts, referenced_actions, errors)
            if compiled:
                rules_out.append(compiled)
        else:
            errors.append(f"规则「{name}」rule_type={rule_type!r} 未知，已跳过")
    # referenced_but_undeclared：被规则引用但未在 DSL actions 声明的动作（内置/需平台侧配置）——
    # 现行「不进模板」告警语义平移为「列出名单请人工核对」，不再静默。
    for action_name in sorted(referenced_actions - set(action_index)):
        warnings.append(f"动作「{action_name}」被规则引用但未在 DSL actions 声明"
                        "（平台内置/需平台侧配置），run/挂载引用按 action_<动作名> 推导 code，请人工核对")
    return rules_out, derived_targets, validation_mounts, errors, warnings


def _compile_calculation(rule: dict[str, Any], name: str, code: str,
                         entities: dict[str, Any], edges: dict[str, list[tuple[str, str]]],
                         errors: list[str]) -> Optional[dict[str, Any]]:
    """单条 derived_property -> 平台 calculation 规则（键序按平台样本：code/name/description/
    ruleType/mode/outputEntityCode/outputPropertyCode/outputPropertyName/initializationStrategy/ruleConfig）。

    Args:
        rule: DSL 规则 dict。
        name: 规则名。code: 规则稳定 code。
        entities: 实体注册表。edges: 关系路径边表。errors: 错误收集列表。
    Returns:
        平台规则 dict；upstream/logic/目标字段非法时 None（错误已记）。
    """
    upstreams = [u for u in (rule.get("upstream") or []) if isinstance(u, str)]
    logic = rule.get("logic") if isinstance(rule.get("logic"), str) and ":" in rule.get("logic") else None
    if not upstreams or upstreams[0] not in entities or not logic:
        errors.append(f"规则「{name}」upstream 缺失/实体不存在或 logic 非法，已跳过")
        return None
    upstream = upstreams[0]
    target_field, raw_expr = (part.strip() for part in logic.split(":", 1))
    props = _entity_props(entities[upstream])
    if target_field not in props:
        errors.append(f"规则「{name}」目标字段 {target_field!r} 未声明于 {upstream}.properties，已跳过")
        return None
    expression, sources, expr_errors = convert_expression(raw_expr, upstream, entities, edges, name)
    errors.extend(expr_errors)
    return {
        "code": code, "name": name, "description": rule.get("description", "") or "",
        "ruleType": "calculation", "mode": "single",
        "outputEntityCode": upstream, "outputPropertyCode": target_field,
        "outputPropertyName": props[target_field].get("display_name", ""),
        "initializationStrategy": "full_recompute",
        "ruleConfig": {"expression": expression, "expressionSources": sources},
    }


def _compile_trigger(rule: dict[str, Any], name: str, code: str,
                     entities: dict[str, Any], edges: dict[str, list[tuple[str, str]]],
                     action_index: dict[str, str], referenced_actions: set[str],
                     errors: list[str]) -> Optional[dict[str, Any]]:
    """单条 trigger -> 平台 trigger 规则（旧形态 logic+downstream -> mode single；
    v0.4 branches -> mode multi + cases + 可选 otherwise）。

    Args:
        rule: DSL 规则 dict。name: 规则名。code: 规则稳定 code。
        entities: 实体注册表。edges: 关系路径边表。
        action_index: {动作名: code} 索引。referenced_actions: 引用动作名收集集合。
        errors: 错误收集列表。
    Returns:
        平台规则 dict；非法时 None（错误已记，该规则跳过）。
    """
    upstreams = [u for u in (rule.get("upstream") or []) if isinstance(u, str)]
    if not upstreams or upstreams[0] not in entities:
        errors.append(f"规则「{name}」upstream 缺失或实体不存在，已跳过")
        return None
    upstream = upstreams[0]
    has_branches = isinstance(rule.get("branches"), list)
    if has_branches == bool(isinstance(rule.get("logic"), dict) and rule.get("logic")):
        errors.append(f"规则「{name}」须恰用一种形态：旧形态（logic+downstream）或新形态 branches，已跳过")
        return None
    # downstream 动作引用编译为 run 项；with 键保留 $ 前缀、值走 _platform_value。
    def _run_item(action_name: Any, with_value: Any) -> Optional[dict[str, Any]]:
        """编译单条 (动作, with) 为平台 run 项；动作名非法时 None 并记 error。"""
        if not isinstance(action_name, str) or not action_name:
            errors.append(f"规则「{name}」downstream 动作名缺失或非法，该规则已跳过")
            return None
        referenced_actions.add(action_name)
        item: dict[str, Any] = {"action": _action_code(action_name, action_index)}
        with_out = _with_dict(with_value, name, errors)
        if with_out:
            item["with"] = with_out
        return item

    if has_branches:
        # 新形态 branches -> mode multi：条件分支逐个编译为 cases，末位兜底 -> otherwise。
        branches = rule["branches"]
        cases: list[dict[str, Any]] = []
        otherwise: list[dict[str, Any]] = []
        for idx, branch in enumerate(branches):
            if not isinstance(branch, dict):
                errors.append(f"规则「{name}」branches[{idx}] 不是映射结构，已跳过")
                return None
            run_item = _run_item(branch.get("downstream"), branch.get("with"))
            if run_item is None:
                return None
            if "condition" in branch:
                # 条件分支：condition.{ALL} -> when.all；run 列表在平台为单动作数组（DSL 单 downstream）。
                conditions = _compile_conditions(branch.get("condition"), upstream, entities,
                                                 edges, name, errors)
                if conditions is None:
                    return None
                cases.append({"when": {"all": conditions}, "run": [run_item]})
            else:
                # 兜底分支：无 condition（至多一个、应处末位——非末位记 error 不猜）。
                if idx != len(branches) - 1:
                    errors.append(f"规则「{name}」兜底分支（无 condition）必须位于 branches 末位，已跳过")
                    return None
                otherwise.append(run_item)
            if len(cases) + len(otherwise) > TRIGGER_CASE_LIMIT:
                errors.append(f"规则「{name}」分支总数超过平台上限 {TRIGGER_CASE_LIMIT}，已跳过")
                return None
        if not cases:
            errors.append(f"规则「{name}」branches 缺少条件分支，已跳过")
            return None
        trigger: dict[str, Any] = {
            "code": code, "name": name, "description": rule.get("description", "") or "",
            "ruleType": "trigger", "mode": "multi", "enabled": True, "cases": cases,
        }
        if otherwise:
            trigger["otherwise"] = otherwise
        return trigger
    # 旧形态：logic.{ALL} + downstream -> mode single + 恰一 case。
    conditions = _compile_conditions(rule.get("logic"), upstream, entities, edges, name, errors)
    if conditions is None:
        return None
    run_item = _run_item(rule.get("downstream"), None)
    if run_item is None:
        return None
    return {
        "code": code, "name": name, "description": rule.get("description", "") or "",
        "ruleType": "trigger", "mode": "single", "enabled": True,
        "cases": [{"when": {"all": conditions}, "run": [run_item]}],
    }


def _compile_validation(rule: dict[str, Any], name: str, code: str,
                        entities: dict[str, Any], edges: dict[str, list[tuple[str, str]]],
                        validation_mounts: dict[str, list[str]], referenced_actions: set[str],
                        errors: list[str]) -> Optional[dict[str, Any]]:
    """单条 admission -> 平台 validation 规则 + 挂载登记（check: param -> $ 参数条件；
    check: instance -> 实例字段条件，lookup 不编进 when——实例定位由动作运行时的
    instances 提供；downstream -> failureMessage；规则 code 进挂载动作 validation_rules）。

    Args:
        rule: DSL 规则 dict。name: 规则名。code: 规则稳定 code。
        entities: 实体注册表。edges: 关系路径边表。
        validation_mounts: {动作名: [validation code]} 挂载表（就地登记）。
        referenced_actions: 引用动作名收集集合。errors: 错误收集列表。
    Returns:
        平台 validation 规则 dict；非法时 None（错误已记）。
    """
    logic = rule.get("logic")
    if not isinstance(logic, dict) or not isinstance(logic.get("ALL"), list):
        errors.append(f"规则「{name}」admission 条件组缺少 ALL 列表，已跳过")
        return None
    upstreams = [u for u in (rule.get("upstream") or []) if isinstance(u, str)]
    if not upstreams:
        errors.append(f"规则「{name}」admission 缺少 upstream（挂载动作名），已跳过")
        return None
    conditions: list[dict[str, Any]] = []
    for idx, cond in enumerate(logic["ALL"]):
        if not isinstance(cond, dict):
            errors.append(f"规则「{name}」条件[{idx}] 不是映射结构，已跳过")
            return None
        operator = cond.get("operator")
        if operator not in OPERATOR_MAP:
            errors.append(f"规则「{name}」条件[{idx}] operator={operator!r} 不在 DSL 操作符表，已跳过")
            return None
        check = cond.get("check")
        if check == "param":
            # $ 参数条件：left = $<参数名>（平台校验规则可引用挂载动作的 $ 参数，官方口径）。
            param = cond.get("param")
            if not isinstance(param, str) or not param:
                errors.append(f"规则「{name}」条件[{idx}] check=param 缺少参数名，已跳过")
                return None
            item = {"left": f"${param}", "operator": OPERATOR_MAP[operator]}
        elif check == "instance":
            # 实例字段条件：left = @<实体code>.<属性code>（lookup 不编进 when——实例定位由
            # 动作运行时的 instances 提供，import-README 注明）。
            entity_name = cond.get("entity")
            if not isinstance(entity_name, str) or entity_name not in entities:
                errors.append(f"规则「{name}」条件[{idx}] check=instance 的实体 {entity_name!r} 不存在，已跳过")
                return None
            resolved = _resolve_field(cond.get("field"), entity_name, entities, edges, name)
            if resolved is None:
                errors.append(f"规则「{name}」条件[{idx}] 实例字段 {cond.get('field')!r} 无法在实体"
                              f" {entity_name!r} 上解析（须为该实体属性或点路径），已跳过")
                return None
            item = {"left": f"@{resolved[0]}.{resolved[1]}", "operator": OPERATOR_MAP[operator]}
        else:
            errors.append(f"规则「{name}」条件[{idx}] check={check!r} 须为 param 或 instance，已跳过")
            return None
        right = _platform_value(cond.get("value"), f"规则「{name}」条件[{idx}]", errors)
        if right is not None:
            item["right"] = right
        conditions.append(item)
    # 挂载登记：DSL admission 的 upstream（动作名）为权威来源，逐动作记录规则 code。
    for action_name in upstreams:
        referenced_actions.add(action_name)
        validation_mounts.setdefault(action_name, []).append(code)
    failure_message = rule.get("downstream")
    if not isinstance(failure_message, str) or not failure_message:
        errors.append(f"规则「{name}」admission 缺少 downstream（failureMessage 文本），已跳过")
        return None
    return {
        "code": code, "name": name, "description": rule.get("description", "") or "",
        "ruleType": "validation", "when": {"all": conditions},
        "failureMessage": failure_message,
    }


# ===========七、action_types 编译（声明式 steps / 函数型 / recipe）==========
def _step_value(value: Any, where: str, errors: list[str]) -> Any:
    """把步骤/with 赋值右值映射为平台值来源：``@param:$x`` -> ``"$x"``、
    ``@Entity.attr`` 原样、其余常量原样（以 @/$ 开头的常量按平台规范 {constant: 文本} 包装）。

    Args:
        value: DSL 侧赋值右值。
        where: 报错定位串。
        errors: 错误收集列表（就地追加；@param:$ 前缀属参数引用不算常量包装）。
    Returns:
        平台侧值。
    """
    if isinstance(value, str) and value.startswith("@param:$") and len(value) > len("@param:$"):
        return value[len("@param:"):]  # @param:$x -> "$x"（平台由步骤 $参数推导，官方口径）
    return _platform_value(value, where, errors)


def _compile_steps(action_name: str, steps: list, entities: dict[str, Any],
                   errors: list[str]) -> Optional[list[dict[str, Any]]]:
    """把 DSL 声明式 steps 逐项编译为平台步骤列表（data: type/entity/operation/assignments；
    notification: type/channel/recipients/content）。

    Args:
        action_name: 动作名（错误定位用）。
        steps: DSL steps 列表。
        entities: 实体注册表。
        errors: 错误收集列表（就地追加）。
    Returns:
        平台步骤列表；任一步骤非法返回 None（错误已记，动作整体跳过，不猜）。
    """
    steps_out: list[dict[str, Any]] = []
    for s_idx, step in enumerate(steps):
        where = f"动作 {action_name} steps[{s_idx}]"
        if not isinstance(step, dict) or step.get("type") not in DECLARATIVE_STEP_TYPES:
            errors.append(f"{where} 类型须为 data 或 notification，已跳过该动作")
            return None
        if step["type"] == "data":
            if step.get("entity") not in entities or step.get("operation") not in DATA_OPERATIONS:
                error = (f"{where} 的 entity 不存在或 operation 不在 {'/'.join(DATA_OPERATIONS)} 白名单内"
                         if step.get("entity") not in entities
                         else f"{where} 的 operation={step.get('operation')!r} 不在 {'/'.join(DATA_OPERATIONS)} 白名单内")
                errors.append(error + "，已跳过该动作")
                return None
            assignments: dict[str, Any] = {}
            for field, value in (step.get("assignments") or {}).items():
                assignments[str(field)] = _step_value(value, f"{where} 赋值[{field}]", errors)
            steps_out.append({
                "type": "data", "entity": step["entity"],
                "operation": step["operation"], "assignments": assignments,
            })
        else:
            # notification 步骤：channel / recipients / content 三键齐全，值映射同 data。
            notify: dict[str, Any] = {"type": "notification"}
            for key in ("channel", "recipients", "content"):
                if not isinstance(step.get(key), str) or not step.get(key):
                    errors.append(f"{where} 缺少 {key}，已跳过该动作")
                    return None
                notify[key] = _step_value(step[key], f"{where} {key}", errors)
            steps_out.append(notify)
    return steps_out


def compile_action_types(model: dict[str, Any], validation_mounts: dict[str, list[str]],
                         errors: list[str], warnings: list[str]) -> list[dict[str, Any]]:
    """把 DSL actions 段编译为平台 action_types（只编 DSL actions 声明的动作；
    规则引用的未声明动作由 compile_rule_types 告警列出，不在此编造）。

    Args:
        model: DSL 模型 dict。
        validation_mounts: {动作名: [validation 规则 code]}（admission upstream 权威来源）。
        errors: 错误收集列表。
        warnings: 告警收集列表（函数型/recipe 动作需平台侧配置名单，import-README 列出）。
    Returns:
        action_types 列表；无 actions 段时为空列表（顶层恒输出该段）。
    """
    entities = model.get("entities") or {}
    actions_out: list[dict[str, Any]] = []
    # rule_name_index：{规则名: 规则 code}——动作声明 validation_rules（规则名列表）映射用。
    rule_name_index = {str(r.get("name")): _stable_code("rule_", str(r.get("name")))
                       for r in (model.get("rules") or []) if isinstance(r, dict)}
    for idx, action in enumerate(model.get("actions") or []):
        if not isinstance(action, dict):
            errors.append(f"actions[{idx}] 不是映射结构，已跳过")
            continue
        name = str(action.get("name") or f"actions[{idx}]")
        where = f"动作 {name}"
        has_function = isinstance(action.get("function"), dict)
        has_steps = isinstance(action.get("steps"), list)
        if has_function and has_steps:
            errors.append(f"{where}：function 与 steps 互斥，已跳过")
            continue
        steps_out: list[dict[str, Any]] = []
        if has_steps:
            compiled_steps = _compile_steps(name, action["steps"], entities, errors)
            if compiled_steps is None:
                continue  # 步骤错误已全量记 error，该动作整体跳过（不猜）
            steps_out = compiled_steps
        elif has_function:
            # 函数型动作：函数代码包不随 yaml 往返（官方口径）——steps 置空数组并告警列入 README。
            warnings.append(f"函数型动作「{name}」：步骤不随 yaml 往返，需平台侧配置函数"
                            "（函数名与契约见 DSL 的 function 键）")
        else:
            # 旧 recipe 形态：引擎骨架实现不进平台 yaml——steps 置空数组并告警列入 README。
            warnings.append(f"recipe 动作「{name}」：需平台侧按骨架实现配置（body_ref 见 DSL，"
                            "引擎注册格式由 --target engine 产物承载）")
        # validation_rules：动作声明（规则名列表）与 admission upstream 挂载取并集——
        # 以 DSL admission 的 upstream 为权威，动作声明额外补充。
        mounted = list(validation_mounts.get(name, []))
        for rule_name in action.get("validation_rules") or []:
            if not isinstance(rule_name, str) or rule_name not in rule_name_index:
                errors.append(f"{where} validation_rules 引用的规则「{rule_name}」不存在，已跳过该动作")
                continue
            rule_code = rule_name_index[rule_name]
            if rule_code not in mounted:
                mounted.append(rule_code)
        entry: dict[str, Any] = {
            "code": _stable_code("action_", name), "name": name,
            "description": action.get("description", "") or "", "enabled": True,
        }
        if mounted:
            entry["validation_rules"] = mounted
        entry["steps"] = steps_out
        actions_out.append(entry)
    return actions_out


# ===========八、总装与 README 增补==========
def compile_studio_model(model: dict[str, Any]) -> tuple[dict[str, Any], list[str], list[str]]:
    """总装：DSL 模型 -> studio-model dict（平台新导入格式，含全部四段元素与告警收集）。

    Args:
        model: DSL 模型 dict（须含 entities）。
    Returns:
        (studio dict, errors, warnings)；errors 非空时产物仍返回（可编译子集），
        由调用方决定退出码。顶层键序：format / object_types / link_types /
        rule_types / action_types（action_types 恒输出段，无动作时为空列表）。
    """
    #   1. 先编 link_types：计算规则/条件的关系路径 BFS 需要边表（relationCode 与连线同源）。
    link_types, edges, link_errors, link_warnings = compile_link_types(model)
    #   2. 动作索引：{动作名: 平台 code}（code 为稳定 hash 纯函数，先行构建供规则引用）。
    action_index = {str(a.get("name")): _stable_code("action_", str(a.get("name")))
                    for a in (model.get("actions") or []) if isinstance(a, dict)}
    #   3. 规则全量编译（calculation / trigger / validation 按 DSL 声明顺序输出）。
    rule_types, derived_targets, validation_mounts, rule_errors, rule_warnings = \
        compile_rule_types(model, edges, action_index)
    #   4. 动作编译（挂载表并入 validation_rules）。
    action_types = compile_action_types(model, validation_mounts, rule_errors, rule_warnings)
    #   5. 实体编译（isDerived 标记需要 derived_targets）。
    object_types, obj_errors = compile_object_types(model, derived_targets)
    return {
        "format": "studio-model",
        "object_types": object_types,
        "link_types": link_types,
        "rule_types": rule_types,
        "action_types": action_types,
    }, link_errors + rule_errors + obj_errors, link_warnings + rule_warnings


def studio_readme_section(studio: dict[str, Any], errors: list[str],
                          warnings: list[str]) -> str:
    """生成 import-README.md 的 Studio 平台导入章节（新格式说明 + 平台侧待办名单）。

    Args:
        studio: compile_studio_model 产物。
        errors: 编译错误列表（逐条入 README 供人工处理）。
        warnings: 编译告警列表（函数型/recipe/未声明动作名单、复合外键、code 撞名）。
    Returns:
        可直接追加到 README 末尾的 Markdown 文本。
    """
    lines = [
        "\n## Studio 模板产物（studio-model.yaml，平台 2026-11 新导入格式）\n",
        "- 由同一 DSL 编译：实体->object_types、links->link_types（cardinality 按 DSL cardinality 翻转）、",
        "  derived_property->calculation（表达式占位符 ${别名.属性code} + expressionSources 逐别名声明",
        "  实体与关系路径；自身属性路径为空数组）、trigger->cases/otherwise/with、admission->validation",
        "  （when 条件 + failureMessage + 挂载动作 validation_rules）、actions->action_types 声明式步骤；",
        "  code 用 rel_/rule_/action_+md5 稳定 hash，重复编译字节一致（幂等）。\n",
        f"- 规模：object_types {len(studio['object_types'])} 个 / link_types {len(studio['link_types'])} 条 /"
        f" rule_types {len(studio['rule_types'])} 条 / action_types {len(studio['action_types'])} 个。\n",
        "- action_types 不写 parameters：平台由步骤中的 $参数 推导（官方口径）。\n",
    ]
    # has_validation：存在 admission 编出的 validation 规则时注明实例定位机制。
    if any(r.get("ruleType") == "validation" for r in studio["rule_types"]):
        lines.append("- admission/validation 规则的实例定位由动作运行时的 instances 提供"
                     "（DSL lookup 不编进 when，平台侧按动作调用上下文定位实例）。\n")
    # 函数型 / recipe / 未声明动作三类名单（告警文本标记词提取，逐条列出供平台侧配置）。
    for label, marker in (("函数型动作", "函数型动作"), ("recipe 动作", "recipe 动作"),
                          ("未在 DSL actions 声明", "被规则引用但未在 DSL actions 声明")):
        items = [w for w in warnings if marker in w]
        if items:
            lines.append(f"- **{label}（{len(items)} 项，需平台侧配置）**：\n")
            lines.extend(f"  - {w}\n" for w in items)
    # compound_fks：复合外键连线名单（平台连线为单字段对，多字段外键无法表达）。
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


# ===========九、模块调试入口==========
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
