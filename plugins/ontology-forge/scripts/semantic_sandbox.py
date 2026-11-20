"""L2 语义沙盘门禁——DSL 假设投影为 OWL/SHACL 后的语义自洽性检查（离线设计侧质量门禁）。

主要 Input：DSL 模型 YAML 路径（位置参数）；可选 --data 实例样本 JSON（对象数组，含 objectType
           与属性键值）；可选 --out-dir 产物落盘目录。
主要 Output：stdout 中文分级报告（error/warning/info，格式参照 lint_model.py）+ 退出码
           （0=通过；1=存在 error；2=文件/解析失败；3=依赖缺失）；--out-dir 时落盘
           sandbox.owl.ttl / sandbox.shapes.ttl / report.md（含 lint 对照表设计说明）。
检查项 S1-S7（与 lint 1-15 编号独立、职责互斥——工作令候选中与 lint 重复的项已删除，
           对照表见 report.md 设计说明；原候选 S1 两项被 lint1/lint10/lint11 覆盖、
           原候选 S2 前半被 lint7 方向 B 覆盖，删后重编号）：
  S1 派生承诺反向：derived_property 规则产出字段未标 derived:true（warning——lint7 只查正向）；
  S2 外键类型精确匹配：links fk 字段类型 vs 目标主键类型（warning——lint8 只做类型集合交集判定）；
  S3 孤岛实体：links 图上无入边无出边（warning——独立主数据合法，呈审）；
  S7 孤儿动作：actions 动作未被任何 trigger/admission 规则 downstream 引用
           （warning——手动入口动作合法，呈审；参照 ontology-driven-dev 反向可追溯门禁）；
  S4 OWL 物化：owlrl DeductiveClosure 对投影图物化（异常=error；非 OWL DL 一致性检测）；
  S5 shapes 自检：生成的 SHACL shapes 图可被 pyshacl 加载（失败=error）；
  S6 实例数据校验：--data 提供时跑 pySHACL conforms 校验，violations 逐条 error。
差异化纪律：逻辑完全由 DSL 结构驱动，禁止实体名/字段名特判；人审权威不变——机器检查只拦确定性缺陷。
"""

# 标准库导入
import argparse
import json
import sys
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Optional

# 第三方依赖导入（依赖缺失防御：中文报错退出码 3，不静默降级——三不纪律）
try:
    import yaml
    import owlrl
    import pyshacl
    from rdflib import Graph, Literal, URIRef
    from rdflib.namespace import RDF, SH, XSD
except ImportError as exc:
    print(f"错误：语义沙盘依赖缺失（{exc}）——请安装：pip install rdflib owlrl pyshacl", file=sys.stderr)
    sys.exit(3)

# 项目内部模块导入
from owl_converter import ASSUMPTIONS, XSD_TYPE_MAP, base_namespace, convert, link_pairs


# ===========一、常量与 lint 对照表==========
# LINT_VS_S：lint 1-15 已覆盖 vs S 项增量对照表（差异化纪律的书面留痕，进 report.md 设计说明）。
LINT_VS_S = """| 工作令候选检查 | lint 实际覆盖 | 判定（差异化纪律） |
|---|---|---|
| rules.upstream 引用不存在实体 | lint1（upstream 实体不存在 error；admission 动作声明走 lint10） | 重复，删除不做 |
| admission @param 引用不存在 action 参数 | lint11（参数引用 error） | 重复，删除不做 |
| derived:true 属性无规则产出 | lint7 方向 B（error） | 重复，删除不做 |
| derived_property 规则产出字段未标 derived:true | lint7 方向 A 只查「目标字段声明于 properties」，不查 derived 标记 | 增量，保留为 S1（warning） |
| links fk 字段类型 vs 目标主键类型 | lint8 仅做「本实体属性类型集合 ∩ 目标主键类型集合 ≠ ∅」的集合级宽松判定 | 增量，保留为 S2（warning，字段级精确对照） |
| 孤岛实体 | 无对应检查 | 增量，保留为 S3（warning） |
| OWL 物化 / shapes 自检 / 实例数据校验 | 无对应（超出 lint 的确定性结构检查能力） | 保留为 S4/S5/S6 |

能力边界：S4 物化是 owlrl 的 OWL-RL/RDFS 规则闭包展开，只证明投影图可被规则集一致地物化，
**不是 OWL DL 一致性检测**（不含表推理与 SAT 检查）；行为语义（trigger/admission 的运行时行为）
不属于公理层，本沙盘不做行为仿真。"""


# ===========二、报告收集器（分级 error/warning/info）==========
class Report:
    """L2 沙盘问题收集与中文报告渲染。

    Input: 无（构造即空）。
    对外能力: error/warning/info 分级记录、三类计数属性、render 输出工作令规定格式的报告文本。
    Return: 通过属性与 render() 方法提供结果。
    """

    def __init__(self) -> None:
        # items：问题列表，元素为 (级别, 编号, 中文消息)。
        self.items: list[tuple[str, str, str]] = []

    def error(self, code: str, msg: str) -> None:
        """记录一条 error（影响退出码）。Args: code 检查项编号（S1-S7）；msg 中文消息。"""
        self.items.append(("error", code, msg))

    def warning(self, code: str, msg: str) -> None:
        """记录一条 warning（不拦截，呈审）。Args: code 检查项编号；msg 中文消息。"""
        self.items.append(("warning", code, msg))

    def info(self, code: str, msg: str) -> None:
        """记录一条 info（提示检查已执行/跳过原因）。Args: code 检查项编号；msg 中文消息。"""
        self.items.append(("info", code, msg))

    @property
    def error_count(self) -> int:
        """error 条数。"""
        return sum(1 for level, _, _ in self.items if level == "error")

    @property
    def warning_count(self) -> int:
        """warning 条数。"""
        return sum(1 for level, _, _ in self.items if level == "warning")

    @property
    def info_count(self) -> int:
        """info 条数。"""
        return sum(1 for level, _, _ in self.items if level == "info")

    def render(self, path: Path) -> str:
        """渲染工作令规定格式的中文报告文本。Args: path 被检查的模型路径。Returns: 多行报告字符串。"""
        lines = [f"====语义沙盘报告（L2）====: {path}"]
        lines += [f"[{code}] {level}: {msg}" for level, code, msg in self.items]
        lines.append("====假设清单（转换器补全，非 DSL 显式声明）====")
        lines += list(ASSUMPTIONS)
        lines.append(f"统计：error {self.error_count} / warning {self.warning_count} / info {self.info_count}")
        verdict = "不通过（error>0）" if self.error_count else "通过（warning 呈审）"
        lines.append(f"====结论====: {verdict}")
        return "\n".join(lines)


# ===========三、纯 DSL 结构检查（S1-S3，输入模型 dict）==========
def _promised_fields(model: dict) -> set[tuple[str, str]]:
    """取派生承诺集合 (upstream 实体, 目标字段)。Args: model DSL 模型 dict。Returns: 二元组集合。"""
    fields = set()
    for rule in model.get("rules") or []:
        if isinstance(rule, dict) and rule.get("rule_type") == "derived_property":
            logic = rule.get("logic")
            upstream = rule.get("upstream") or []
            if isinstance(logic, str) and ":" in logic and upstream:
                fields.add((str(upstream[0]), logic.split(":", 1)[0].strip()))
    return fields


def check_s1_promise_reverse(model: dict, entities: dict, report: Report) -> None:
    """S1 派生承诺反向：规则产出字段未标 derived:true（warning）。

    Args:
        model: DSL 模型 dict。
        entities: 实体名 -> 实体定义 dict。
        report: 问题收集器。
    Returns:
        None。derived:true 无规则的正向（lint7 方向 B）不做；upstream 实体不存在时跳过（lint1 职责）。
    """
    for entity, field in sorted(_promised_fields(model)):
        spec = entities.get(entity, {}).get("properties", {}).get(field) if entity in entities else None
        if isinstance(spec, dict) and not spec.get("derived"):
            report.warning("S1", f"规则产出字段 {entity}.{field} 未标记 derived:true——"
                           "derived_property 规则承诺计算该字段，属性侧应带衍生声明（lint7 只查反向）")


def check_s2_fk_types(entities: dict, report: Report) -> None:
    """S2 外键类型精确匹配（warning）：显式 fk 字段类型须在目标主键类型集合内；
    fk 缺省形态按简写约定（外键字段名=目标主键字段名）对照同名属性类型。

    Args:
        entities: 实体名 -> 实体定义 dict。
        report: 问题收集器。
    Returns:
        None。目标实体不存在/主键缺失时跳过（lint3/lint2 职责）。
    """
    for name, ent in entities.items():
        props = ent.get("properties") or {}
        for alias, target, fk in link_pairs(ent):
            target_ent = entities.get(target)
            if not isinstance(target_ent, dict):
                continue  # 目标不存在已由 lint3 报告
            target_props = target_ent.get("properties") or {}
            # pk_types：目标主键类型集合（lint2 保证非空，缺失时跳过避免重复报）
            pk_types = {str(s.get("type")) for s in target_props.values()
                        if isinstance(s, dict) and s.get("primary")}
            if not pk_types:
                continue
            where = f"实体 {name}.links.{alias}"
            if fk:
                for field in fk:
                    spec = props.get(field)
                    ftype = str(spec.get("type")) if isinstance(spec, dict) else None
                    if ftype and ftype not in pk_types:
                        report.warning("S2", f"{where} 外键字段 {field} 类型 {ftype} 与 {target}"
                                       f" 主键类型（{'/'.join(sorted(pk_types))}）不一致")
            else:
                for pk_field, pk_spec in target_props.items():
                    own = props.get(pk_field)
                    if isinstance(own, dict) and isinstance(pk_spec, dict) and pk_spec.get("primary") \
                            and own.get("type") and own.get("type") != pk_spec.get("type"):
                        report.warning("S2", f"{where} 外键字段 {pk_field}（按简写约定同名目标主键）类型"
                                       f" {own.get('type')} 与 {target} 主键类型 {pk_spec.get('type')} 不一致")


def check_s3_islands(entities: dict, report: Report) -> None:
    """S3 孤岛实体：links 图上无任何入边/出边的实体（warning——独立主数据合法，呈审）。

    Args:
        entities: 实体名 -> 实体定义 dict。
        report: 问题收集器。
    Returns:
        None。
    """
    # linked：links 图上出现过的实体集合（出边方与目标方都算有边）。
    linked: set[str] = set()
    for name, ent in entities.items():
        for _alias, target, _fk in link_pairs(ent):
            linked.add(str(name))
            linked.add(str(target))
    for name in entities:
        if str(name) not in linked:
            report.warning("S3", f"孤岛实体：{name}——links 图上无任何入边/出边（独立主数据合法，呈审）")


def check_s7_orphan_actions(model: dict, report: Report) -> None:
    """S7 孤儿动作（warning）：actions 段动作从未被 trigger/admission 规则 downstream 引用。

    Args:
        model: DSL 模型 dict。
        report: 问题收集器。
    Returns:
        None。手动入口动作（Agent/用户直调）合法，warning 呈审确认入口归属，不拦截。
    """
    # actions_defined：动作段声明的动作名列表；无 actions 段时本项跳过。
    actions_defined = [
        str(a.get("name"))
        for a in (model.get("actions") or [])
        if isinstance(a, dict) and a.get("name")
    ]
    if not actions_defined:
        return
    # referenced：规则 downstream 引用过的动作名集合；admission 的「Action 准入拦截: X」前缀剥掉后匹配。
    referenced: set[str] = set()
    for rule in model.get("rules") or []:
        if not isinstance(rule, dict):
            continue
        downstream = str(rule.get("downstream") or "").strip()
        if downstream.startswith("Action 准入拦截:"):
            downstream = downstream.split(":", 1)[1].strip()
        if downstream:
            referenced.add(downstream)
    for action_name in actions_defined:
        if action_name not in referenced:
            report.warning("S7", f"孤儿动作：{action_name}——未被任何 trigger/admission 规则 downstream 引用"
                          "（手动入口动作合法，呈审确认入口）")


# ===========四、语义网检查（S4-S6，输入投影图）==========
def check_s4_materialize(owl_graph: Graph, report: Report) -> None:
    """S4 OWL 物化：owlrl DeductiveClosure 对投影图副本做 OWL-RL 闭包（异常=error，不吞异常）。

    Args:
        owl_graph: owl_converter 产出的 OWL 公理图。
        report: 问题收集器。
    Returns:
        None。能力边界（非 OWL DL 一致性检测）随 info 条目与 report.md 设计说明注明。
    """
    try:
        work = Graph()
        for triple in owl_graph:
            work.add(triple)
        owlrl.DeductiveClosure(owlrl.OWLRL_Semantics).expand(work)
        report.info("S4", f"OWL 物化完成：{len(owl_graph)} → {len(work)} 三元组"
                    "（owlrl OWL-RL 闭包；非 OWL DL 一致性检测，能力边界见 report.md）")
    except Exception as exc:  # noqa: BLE001 —— 物化异常必须完整上报为 error，不许静默吞掉
        report.error("S4", f"OWL 物化失败（owlrl DeductiveClosure 异常）：{exc}")


def check_s5_shapes(shapes_graph: Graph, report: Report) -> None:
    """S5 shapes 自检：生成的 shapes 图可被 pyshacl 解析加载（失败=error）。

    Args:
        shapes_graph: owl_converter 产出的 SHACL shapes 图。
        report: 问题收集器。
    Returns:
        None。以空数据图跑一次校验暴露 shapes 自身结构错误（空图 conforms 属预期）。
    """
    try:
        pyshacl.validate(data_graph=Graph(), shacl_graph=shapes_graph, inference="none")
        count = len(set(shapes_graph.subjects(RDF.type, SH.NodeShape)))
        report.info("S5", f"SHACL shapes 图加载自检通过（{count} 个 NodeShape）")
    except Exception as exc:  # noqa: BLE001 —— shapes 坏件必须完整上报为 error，不许静默吞掉
        report.error("S5", f"SHACL shapes 图无法被 pyshacl 加载：{exc}")


def _typed_literal(value: Any, xsd_type: Any) -> Literal:
    """按声明类型构造 RDF 字面量；转换失败回退字符串字面量（交给 SHACL 报 datatype 违约，不静默丢弃）。

    Args:
        value: JSON 样本值。
        xsd_type: 属性声明类型对应的 XSD URIRef。
    Returns:
        rdflib Literal。
    """
    try:
        if xsd_type == XSD.integer:
            return Literal(int(value))
        if xsd_type == XSD.double:
            return Literal(float(value))
        if xsd_type == XSD.decimal:
            return Literal(Decimal(str(value)))
        if xsd_type == XSD.boolean:
            return Literal(value) if isinstance(value, bool) else Literal(str(value))
        if xsd_type in (XSD.date, XSD.dateTime):
            return Literal(str(value), datatype=xsd_type)
        return Literal(str(value))
    except (ValueError, TypeError, InvalidOperation):
        return Literal(str(value))


def check_s6_data(model: dict, entities: dict, shapes_graph: Graph,
                  data_path: Optional[Path], report: Report) -> None:
    """S6 实例数据校验：--data 样本组装 RDF 数据图跑 pySHACL conforms 校验，violations 逐条输出。

    Args:
        model: DSL 模型 dict。
        entities: 实体名 -> 实体定义 dict。
        shapes_graph: owl_converter 产出的 SHACL shapes 图。
        data_path: --data JSON 路径（None 表示未提供，记 info 跳过）。
        report: 问题收集器。
    Returns:
        None。violations 记 error（提供样本即声明要严格校验）；未知 objectType 记 error、
        未声明属性记 info（不拦截）。
    """
    if data_path is None:
        report.info("S6", "未提供数据样本，跳过实例校验")
        return
    records = json.loads(data_path.read_text(encoding="utf-8"))
    if not isinstance(records, list):
        report.error("S6", "--data 文件顶层必须是对象数组")
        return
    ns = base_namespace(model)
    data_graph = Graph()
    for idx, record in enumerate(records):
        if not isinstance(record, dict):
            report.error("S6", f"样本[{idx}] 不是 JSON 对象")
            continue
        obj_type = str(record.get("objectType") or "")
        if obj_type not in entities:
            report.error("S6", f"样本[{idx}] objectType={obj_type!r} 不在 DSL 实体集中")
            continue
        subj = ns[f"sample-{idx}"]
        data_graph.add((subj, RDF.type, ns[obj_type]))
        for key, value in record.items():
            if key == "objectType":
                continue
            spec = (entities[obj_type].get("properties") or {}).get(key)
            if not isinstance(spec, dict):
                report.info("S6", f"样本[{idx}] 属性 {key} 不在 {obj_type} properties 中，未投影")
                continue
            data_graph.add((subj, ns[f"{obj_type}_{key}"], _typed_literal(value, XSD_TYPE_MAP.get(str(spec.get("type"))))))
    conforms, results_graph, _text = pyshacl.validate(data_graph=data_graph, shacl_graph=shapes_graph, inference="none")
    if conforms:
        report.info("S6", f"实例校验通过（{len(records)} 条样本 conforms）")
        return
    for res in results_graph.subjects(RDF.type, SH.ValidationResult):
        # focus/path/message/severity：违规定位三元组（pyshacl 消息为库原文，保留可追溯性）；
        # 未自定义 sh:severity 时默认 Violation → error，显式降级（Warning/Info）→ warning 呈审
        focus = results_graph.value(res, SH.focusNode)
        path = results_graph.value(res, SH.resultPath)
        message = results_graph.value(res, SH.resultMessage)
        severity = results_graph.value(res, SH.resultSeverity)
        path_name = str(path).rsplit(":", 1)[-1].split("_", 1)[-1] if path is not None else "?"
        focus_name = str(focus).rsplit(":", 1)[-1] if focus is not None else "?"
        line = f"实例 <{focus_name}> 违反约束 {path_name}：{message}"
        if severity == SH.Warning:
            report.warning("S6", line)
        else:
            report.error("S6", line)


# ===========五、主流程与命令行入口==========
def run_sandbox(model: dict, data_path: Optional[Path], report: Report) -> tuple[Graph, Graph]:
    """执行全部 S1-S6 检查（入口聚合，供 CLI 与调试自验共用）。

    Args:
        model: DSL 模型 dict。
        data_path: --data 实例样本路径（可为 None）。
        report: 问题收集器。
    Returns:
        (OWL 图, shapes 图) 二元组（--out-dir 落盘复用）。
    """
    entities = model.get("entities") if isinstance(model.get("entities"), dict) else {}
    owl_graph, shapes_graph, _promises = convert(model)
    check_s1_promise_reverse(model, entities, report)
    check_s2_fk_types(entities, report)
    check_s3_islands(entities, report)
    check_s7_orphan_actions(model, report)
    check_s4_materialize(owl_graph, report)
    check_s5_shapes(shapes_graph, report)
    check_s6_data(model, entities, shapes_graph, data_path, report)
    return owl_graph, shapes_graph


def write_report_md(out_dir: Path, model: dict, report_text: str) -> None:
    """落盘 report.md：设计说明（定位/lint 对照表/能力边界）+ 完整报告文本。

    Args:
        out_dir: --out-dir 目录（已存在）。
        model: DSL 模型 dict（头部署名用）。
        report_text: Report.render 产物。
    Returns:
        None。
    """
    header = (f"# 语义沙盘报告（L2）——{model.get('ontology')} {model.get('version')}\n\n"
              "> 定位：离线设计侧质量门禁（本体世界的 CI）——DSL 一次性假设投影为 OWL/SHACL 做"
              "结构层查不出的语义自洽性检查；检完即弃不留双表示，人审权威不变。\n\n"
              "## 设计说明：lint 已覆盖 vs S 项增量对照\n\n" + LINT_VS_S + "\n\n## 检查结果\n\n```\n"
              + report_text + "\n```\n")
    (out_dir / "report.md").write_text(header, encoding="utf-8")


def main() -> int:
    """命令行入口：加载模型 -> S1-S6 检查 -> 输出中文报告与退出码（可选落盘三产物）。"""
    parser = argparse.ArgumentParser(description="L2 语义沙盘：DSL 假设投影 OWL/SHACL 的语义自洽性检查")
    parser.add_argument("model", help="DSL 模型 YAML 路径")
    parser.add_argument("--data", help="实例数据 JSON（对象数组，含 objectType 与属性键值）")
    parser.add_argument("--out-dir", help="产物落盘目录（sandbox.owl.ttl / sandbox.shapes.ttl / report.md）")
    args = parser.parse_args()
    path = Path(args.model)
    if not path.is_file():
        print(f"错误：文件不存在 {path}", file=sys.stderr)
        return 2
    data_path = Path(args.data) if args.data else None
    if data_path is not None and not data_path.is_file():
        print(f"错误：--data 文件不存在 {data_path}", file=sys.stderr)
        return 2
    try:
        model = yaml.safe_load(path.read_text(encoding="utf-8"))
        if data_path is not None:
            json.loads(data_path.read_text(encoding="utf-8"))  # 提前暴露 JSON 语法错误（退出码 2）
    except (yaml.YAMLError, json.JSONDecodeError, UnicodeDecodeError) as exc:
        print(f"错误：文件解析失败——{exc}", file=sys.stderr)
        return 2
    if not isinstance(model, dict):
        print("错误：模型顶层不是映射结构", file=sys.stderr)
        return 2
    report = Report()
    owl_graph, shapes_graph = run_sandbox(model, data_path, report)
    print(report.render(path))
    if args.out_dir:
        out_dir = Path(args.out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "sandbox.owl.ttl").write_bytes(owl_graph.serialize(format="turtle", encoding="utf-8"))
        (out_dir / "sandbox.shapes.ttl").write_bytes(shapes_graph.serialize(format="turtle", encoding="utf-8"))
        write_report_md(out_dir, model, report.render(path))
        print(f"====产物落盘====: {out_dir / 'sandbox.owl.ttl'} / {out_dir / 'sandbox.shapes.ttl'} / {out_dir / 'report.md'}")
    return 1 if report.error_count else 0


if __name__ == "__main__":
    # CLI 脚本本体即调试入口：python semantic_sandbox.py <model.yaml> [--data data.json] [--out-dir DIR]。
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    sys.exit(main())
