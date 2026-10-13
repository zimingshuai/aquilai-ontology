"""studio-model 模板结构硬校验器（lint）——dsl-spec §8 逆向输入侧检查。

主要 Input：Studio 模板 YAML 文件路径（命令行位置参数，format: studio-model）。
主要 Output：stdout 中文 lint 报告 + 退出码（0=通过，可含 warning；1=存在 error；2=文件/解析失败）。
检查项（试用评审 P0 均覆盖）：主键存在 / 连线实体与属性可解析 / 主键连主键（n 侧外键位
连到了主键）/ 孤立实体 / 表达式中文名引用可解析与函数白名单 / isDerived 与 calculation
输出双向一致 / string 类型字段的数值命名暗示。逻辑由模板结构驱动，不含实体名特判。
"""

# 标准库导入
import re
import sys
from pathlib import Path
from typing import Any, Optional

# 第三方依赖导入
import yaml

# ===========一、常量与结构加载（重复键检测）==========
# ALLOWED_TYPES：模板侧属性类型 5 枚举（§8 类型映射目标）。
ALLOWED_TYPES = {"string", "boolean", "date", "datetime", "double"}
# FUNC_WHITELIST：表达式函数白名单（与引擎方言一致）。
FUNC_WHITELIST = {"SUM", "COALESCE", "MAX"}
# NUMERIC_HINTS：数值命名暗示子串（type=string 却含其一 -> warning）。
NUMERIC_HINTS = ("qty", "days", "amount", "cost", "rate", "level")
# CARDINALITIES：合法基数枚举（n 侧判定依据：1:n 的 n 方=target，n:1 的 n 方=source）。
CARDINALITIES = {"1:n", "n:1", "1:1"}
# EXPR_TOKEN_RE：模板表达式 token——[中文名引用] / 数值 / 函数名 / 四则括号逗号。
EXPR_TOKEN_RE = re.compile(
    r"(?P<ref>\[[^\[\]]*\])|(?P<num>\d+(?:\.\d+)?)"
    r"|(?P<word>[A-Za-z_]\w*)|(?P<op>[+\-*/(),])"
)
# _DUP_KEYS：YAML 重复键收集器（同 lint_model 口径）。
_DUP_KEYS: list[str] = []


class _StrictLoader(yaml.SafeLoader):
    """带重复键检测的 SafeLoader：重复键显式记录而非静默后者覆盖。"""


def _strict_mapping(loader: "_StrictLoader", node: yaml.Node, deep: bool = False) -> dict:
    """构造 mapping 并把重复键记入 _DUP_KEYS。Args: loader；node；deep。Returns: 构造完成的 dict。"""
    loader.flatten_mapping(node)
    mapping: dict[Any, Any] = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in mapping:
            _DUP_KEYS.append(str(key))
        mapping[key] = loader.construct_object(value_node, deep=deep)
    return mapping


_StrictLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _strict_mapping)


# ===========二、报告收集器（同 lint_model 风格）==========
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
        """记录一条 error（影响退出码）。Args: tag 检查项编号；where 定位；detail 详情。"""
        self.items.append(("error", f"〔{tag}〕{where}——{detail}"))

    def warn(self, tag: str, where: str, detail: str) -> None:
        """记录一条 warning（仅提示）。Args: tag 检查项编号；where 定位；detail 详情。"""
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
        """渲染中文报告文本。Args: path 被检查的模板路径。Returns: 多行报告字符串。"""
        lines = [f"====lint(studio-model) 开始====: {path}"]
        if not self.items:
            lines.append("未发现问题。")
        lines.extend(f"[{level}] {msg}" for level, msg in self.items)
        verdict = "通过" if self.error_count == 0 else "未通过"
        lines.append(f"====lint(studio-model) {verdict}====: "
                     f"error {self.error_count} 处，warning {self.warning_count} 处")
        return "\n".join(lines)


# ===========三、结构/主键/类型检查（检查 0、1、7）==========
def lint_studio_model(model: dict, report: Report) -> None:
    """执行全部检查（入口聚合，按 object_types 存在性短路）。Args: model 模板 dict；report 收集器。Returns: None。"""
    if model.get("format") != "studio-model":
        report.warn("s0 结构", "顶层", f"format={model.get('format')!r} 非 studio-model（按该口径继续检查）")
    for key in _DUP_KEYS:
        report.err("s0 结构", "YAML 结构", f"重复键 {key!r}")
    objects = model.get("object_types")
    if not isinstance(objects, list):
        report.err("s0 结构", "顶层", "object_types 缺失或不是列表")
        return
    # entities / by_name：实体索引（code -> dict；name -> code 中文名反查，表达式解析用）。
    entities: dict[str, dict] = {}
    by_name: dict[str, str] = {}
    for obj in objects:
        if not isinstance(obj, dict) or not obj.get("code"):
            report.err("s0 结构", "object_types", f"存在缺 code 的对象类型项：{obj!r}")
            continue
        code = str(obj["code"])
        if code in entities:
            report.err("s0 结构", f"实体 {code}", "code 重复")
            continue
        entities[code] = obj
        # display 重复检测：实体 name 是表达式中文名引用的解析键，重名即歧义源（试用实证：
        # fnb 快照残留曾使两条实体同名，上卷引用解析错实体）。
        display = str(obj.get("name") or "")
        if display and display in by_name:
            report.warn("s0 结构", f"实体 {code}", f"name={display!r} 与实体 {by_name[display]} 重复"
                        "（表达式按 name 解析将产生歧义）")
        by_name[display] = code
    _check_attrs(entities, report)
    links = model.get("link_types") or []
    rules = model.get("rule_types") or []
    _check_links(links, entities, report)
    _check_isolated(links, entities, report)
    _check_rules(rules, entities, by_name, report)


def _check_attrs(entities: dict, report: Report) -> None:
    """检查 1（主键）/ 7（类型暗示）与属性结构合法性（type 枚举、attrs 重复 code）。

    Args:
        entities: code -> 对象类型 dict。
        report: 问题收集器。
    Returns:
        None。
    """
    for code, obj in entities.items():
        attrs = obj.get("attrs")
        if not isinstance(attrs, list) or not attrs:
            report.err("s0 结构", f"实体 {code}", "attrs 缺失或为空列表")
            continue
        # seen_codes：实体内属性 code 查重集合。
        seen_codes: set[str] = set()
        key_count = 0
        for attr in attrs:
            if not isinstance(attr, dict) or not attr.get("code"):
                report.err("s0 结构", f"实体 {code}", f"存在缺 code 的属性项：{attr!r}")
                continue
            attr_code = str(attr["code"])
            if attr_code in seen_codes:
                report.err("s0 结构", f"实体 {code}", f"属性 code 重复 {attr_code!r}")
                continue
            seen_codes.add(attr_code)
            if attr.get("type") not in ALLOWED_TYPES:
                report.err("s0 结构", f"实体 {code}.{attr_code}",
                           f"type={attr.get('type')!r} 不在 5 种模板枚举内")
            if attr.get("isKey"):
                key_count += 1
            if attr.get("type") == "string" and any(
                    part == hint or part.endswith(hint)
                    for part in attr_code.split("_") for hint in NUMERIC_HINTS):
                report.warn("s7 类型暗示", f"实体 {code}.{attr_code}",
                            "type=string 但字段名含数值暗示（qty/days/amount/cost/rate/level），疑应为 double")
        if key_count == 0:
            report.err("s1 主键", f"实体 {code}（{obj.get('name')}）", "没有任何 isKey=true 的主键属性")


# ===========四、连线与孤立实体检查（检查 2、3、4）==========
def _check_links(links: list, entities: dict, report: Report) -> None:
    """检查 2（连线可解析）/ 3（主键连主键：n 侧外键位连到了主键）。

    Args:
        links: link_types 列表。
        entities: code -> 对象类型 dict。
        report: 问题收集器。
    Returns:
        None。
    """
    for idx, link in enumerate(links):
        if not isinstance(link, dict):
            report.err("s0 结构", f"link_types[{idx}]", "不是映射结构")
            continue
        # where：连线定位（code + source->target）。
        where = f"连线 {link.get('code', '?')}（{link.get('source')}->{link.get('target')}）"
        source, target = link.get("source"), link.get("target")
        sp, tp = link.get("sourcePropertyCode"), link.get("targetPropertyCode")
        card = str(link.get("cardinality") or "")
        if card not in CARDINALITIES:
            report.err("s2 连线", where, f"cardinality={card!r} 不在 1:n/n:1/1:1 内")
        for role, ecode in (("source", source), ("target", target)):
            if ecode not in entities:
                report.err("s2 连线", where, f"{role} 实体 {ecode!r} 不在 object_types 中")
        # attrs_code：两侧实体属性 code 集合与主键集合（实体不存在时跳过属性级检查）。
        src_attrs = {str(a.get("code")) for a in entities.get(source, {}).get("attrs", [])
                     if isinstance(a, dict)}
        tgt_attrs = {str(a.get("code")) for a in entities.get(target, {}).get("attrs", [])
                     if isinstance(a, dict)}
        if source in entities and sp not in src_attrs:
            report.err("s2 连线", where, f"sourcePropertyCode {sp!r} 不在 {source} 的 attrs 中")
        if target in entities and tp not in tgt_attrs:
            report.err("s2 连线", where, f"targetPropertyCode {tp!r} 不在 {target} 的 attrs 中")
        # 检查 3（P0 主键连主键）：按基数定位 n 方，n 方外键位若连到自身主键即报错
        # （1:1 双主键互连属共享主键模式，不在此列）。
        src_keys = {str(a.get("code")) for a in entities.get(source, {}).get("attrs", [])
                    if isinstance(a, dict) and a.get("isKey")}
        tgt_keys = {str(a.get("code")) for a in entities.get(target, {}).get("attrs", [])
                    if isinstance(a, dict) and a.get("isKey")}
        if card == "1:n" and tp in tgt_keys:
            report.err("s3 主键连主键", where,
                       f"1:n 的 n 侧（{target}）外键位 targetPropertyCode={tp!r} 是其主键"
                       "（n 侧应连外键属性，主键连主键无法承载 1:n 数据关联）")
        if card == "n:1" and sp in src_keys:
            report.err("s3 主键连主键", where,
                       f"n:1 的 n 侧（{source}）外键位 sourcePropertyCode={sp!r} 是其主键"
                       "（n 侧应连外键属性，主键连主键无法承载 n:1 数据关联）")


def _check_isolated(links: list, entities: dict, report: Report) -> None:
    """检查 4：无任何连线涉及的实体 -> warning（模板可导入但图谱脱孤失败、规则跨实体引用将悬空）。

    Args:
        links: link_types 列表。
        entities: code -> 对象类型 dict。
        report: 问题收集器。
    Returns:
        None。
    """
    # linked：出现在任一连线 source/target 的实体 code 集合。
    linked = {link.get(key) for link in links if isinstance(link, dict) for key in ("source", "target")}
    for code, obj in entities.items():
        if code not in linked:
            report.warn("s4 孤立实体", f"实体 {code}（{obj.get('name')}）",
                        "无任何 link_types 连线涉及，跨实体引用/上卷规则将无法解析")


# ===========五、规则与表达式检查（检查 5、6）==========
def _check_expression(expr: Any, entities: dict, by_name: dict[str, str],
                      report: Report, where: str) -> None:
    """检查 5：表达式中文名引用可解析（按实体 name 与属性 name）+ 函数白名单 + 方言外字符。

    Args:
        expr: ruleConfig.expression（应为字符串）。
        entities: code -> 对象类型 dict。
        by_name: 实体 name -> code 索引。
        report: 问题收集器。
        where: 报告定位串。
    Returns:
        None。
    """
    if not isinstance(expr, str) or not expr.strip():
        report.err("s5 表达式", where, "ruleConfig.expression 缺失或为空")
        return
    pos = 0
    text = expr
    while pos < len(text):
        if text[pos].isspace():
            pos += 1
            continue
        match = EXPR_TOKEN_RE.match(text, pos)
        if not match:
            report.err("s5 表达式", where, f"含方言外字符 {text[pos]!r}（仅支持 [引用]/四则/数值与 SUM/COALESCE/MAX）")
            pos += 1
            continue
        kind, token = match.lastgroup, match.group(match.lastgroup)
        pos = match.end()
        if kind == "word":
            if text[pos:pos + 1] != "(":
                report.err("s5 表达式", where, f"裸标识符 {token!r} 不在 [] 引用内且非函数调用")
            elif token not in FUNC_WHITELIST:
                report.err("s5 表达式", where, f"函数 {token!r} 不在白名单 SUM/COALESCE/MAX 内")
        elif kind == "ref":
            inner = token[1:-1]
            if "." not in inner:
                report.err("s5 表达式", where, f"引用 {token!r} 缺少「实体名.属性名」点分隔")
                continue
            ename, aname = inner.split(".", 1)
            ecode = by_name.get(ename)
            if ecode is None:
                report.err("s5 表达式", where, f"引用 {token!r} 的实体名 {ename!r} 无法解析（按 object_types.name）")
                continue
            attr_names = {str(a.get("name")) for a in entities[ecode].get("attrs", [])
                          if isinstance(a, dict)}
            if aname not in attr_names:
                report.err("s5 表达式", where,
                           f"引用 {token!r} 的属性名 {aname!r} 不在 {ecode} 的 attrs.name 中")


def _check_rules(rules: list, entities: dict, by_name: dict[str, str],
                 report: Report) -> None:
    """检查 6：isDerived 与 calculation 输出双向一致（含输出实体/属性可解析）。

    Args:
        rules: rule_types 列表。
        entities: code -> 对象类型 dict。
        by_name: 实体 name -> code 索引。
        report: 问题收集器。
    Returns:
        None。
    """
    # derived_marks：isDerived=true 的 (实体 code, 属性 code) 集合。
    derived_marks: set[tuple[str, str]] = set()
    for code, obj in entities.items():
        for attr in obj.get("attrs", []) if isinstance(obj.get("attrs"), list) else []:
            if isinstance(attr, dict) and attr.get("isDerived") and attr.get("code"):
                derived_marks.add((code, str(attr["code"])))
    # calc_outputs：calculation 规则输出 (实体 code, 属性 code) 集合。
    calc_outputs: set[tuple[str, str]] = set()
    for idx, rule in enumerate(rules):
        if not isinstance(rule, dict):
            report.err("s0 结构", f"rule_types[{idx}]", "不是映射结构")
            continue
        where = f"规则 {rule.get('code', '?')}「{rule.get('name', '?')}」"
        if rule.get("ruleType") != "calculation":
            report.err("s6 衍生一致", where, f"ruleType={rule.get('ruleType')!r}（模板实证仅承载 calculation）")
            continue
        _check_expression((rule.get("ruleConfig") or {}).get("expression")
                          if isinstance(rule.get("ruleConfig"), dict) else rule.get("ruleConfig"),
                          entities, by_name, report, where)
        ecode, pcode = rule.get("outputEntityCode"), rule.get("outputPropertyCode")
        attrs_codes = {str(a.get("code")) for a in entities.get(ecode, {}).get("attrs", [])
                       if isinstance(a, dict)}
        if ecode not in entities:
            report.err("s6 衍生一致", where, f"outputEntityCode {ecode!r} 不在 object_types 中")
            continue
        if pcode not in attrs_codes:
            report.err("s6 衍生一致", where, f"outputPropertyCode {pcode!r} 不在 {ecode} 的 attrs 中")
            continue
        calc_outputs.add((ecode, pcode))
    # 方向 A：标了 isDerived 却无 calculation 输出承载。
    for ecode, pcode in sorted(derived_marks - calc_outputs):
        report.err("s6 衍生一致", f"属性 {ecode}.{pcode}",
                   "isDerived=true 但没有以其为输出的 calculation 规则")
    # 方向 B：calculation 输出的属性未标 isDerived。
    for ecode, pcode in sorted(calc_outputs - derived_marks):
        report.err("s6 衍生一致", f"规则输出 {ecode}.{pcode}",
                   "存在 calculation 输出但对应属性 isDerived≠true（实证：两者应严格对应）")


# ===========六、命令行入口==========
def main() -> int:
    """命令行入口：加载 YAML -> 逐项检查 -> 输出中文报告与退出码。"""
    if len(sys.argv) != 2:
        print("用法: python lint_studio_model.py <studio-model.yaml>", file=sys.stderr)
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
        print("错误：模板顶层不是映射结构", file=sys.stderr)
        return 2
    report = Report()
    lint_studio_model(model, report)
    print(report.render(path))
    return 1 if report.error_count else 0


if __name__ == "__main__":
    # CLI 脚本本体即调试入口：python lint_studio_model.py <studio-model.yaml> 跑真实模板。
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    sys.exit(main())
