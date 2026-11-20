"""DSL YAML → OWL/SHACL 一次性「假设投影」转换器（L2 语义沙盘的工件层，纯逻辑模块）。

主要 Input：DSL 模型 dict（YAML 已加载；结构合法性由 lint_model.py L1 负责，本模块不做结构
           校验——非法 links 项按跳过处理不报错，差异化纪律：结构层问题归 lint）。
主要 Output：convert() 返回三件套——
           ① OWL 公理图（rdflib.Graph）：实体→owl:Class、属性→owl:DatatypeProperty、
             links 别名→owl:ObjectProperty（domain/range 按 A1 假设推导）；
           ② SHACL shapes 图：每实体一个 NodeShape——主键 sh:minCount 1 + sh:maxCount 1（A2）、
             枚举 sh:in 静态清单（A4）、其余属性仅登记 path + sh:datatype（A3 不强加 minCount）；
           ③ 派生承诺表：derived_property 规则结构化清单（行为语义不转公理，供沙盘 S1 对照）。
           IRI 前缀 = urn:x-onto:<ontology名>:（URN 命名空间，不依赖网络解析）。
定位：离线设计侧质量门禁工件（本体世界的 CI）——一次性假设投影，检完即弃不构成运行时双表示；
     derived:true 属性经自定义注解谓词 xgimi:derivedPromise 关联规则名（按 logic 左值匹配）。
"""

# 标准库导入
import sys
from pathlib import Path
from typing import Any, Optional

# 第三方依赖导入（依赖缺失防御：中文报错退出码 3，不静默降级）
try:
    import yaml
    from rdflib import BNode, Graph, Literal, Namespace, URIRef
    from rdflib.collection import Collection
    from rdflib.namespace import OWL, RDF, RDFS, SH, XSD
except ImportError as exc:
    print(f"错误：语义沙盘工件依赖缺失（{exc}）——请安装：pip install rdflib owlrl pyshacl", file=sys.stderr)
    sys.exit(3)


# ===========一、常量与假设清单==========
# XSD_TYPE_MAP：DSL §2 七种属性类型 → XSD 数据类型映射（A5：derived 属性值类型按属性声明投影）。
XSD_TYPE_MAP = {
    "STRING": XSD.string, "INTEGER": XSD.integer, "DOUBLE": XSD.double,
    "DECIMAL": XSD.decimal, "BOOLEAN": XSD.boolean, "DATE": XSD.date,
    "TIMESTAMP": XSD.dateTime,
}
# DERIVED_PROMISE_LOCAL：derived 属性关联规则名的自定义注解谓词局部名（挂本体命名空间下，
# 如 urn:x-onto:xgimi:derivedPromise——谓词名 camelCase 与实体 PascalCase/字段 snake_case 天然不撞）。
DERIVED_PROMISE_LOCAL = "derivedPromise"
# ASSUMPTIONS：转换器补全的假设登记（声明性登记，报告必须原样输出）——这些是投影时
# 替建模者做的补全决定，必须与 DSL 显式声明区分，不是配置缺失的借口。
ASSUMPTIONS = (
    "A1 关系 domain/range 按 links 声明推导（两端字段类型现实未强制校验）",
    "A2 主键属性投影为 sh:minCount 1 + sh:maxCount 1；主键唯一性 SHACL 表达不了，未校验",
    "A3 DSL 无 required 语义，非主键属性不强加 sh:minCount（缺失不视为违约）",
    "A4 枚举 sh:in 仅静态声明约束清单，未对实例数据校验（除非沙盘提供 --data 样本）",
    "A5 derived 属性值类型按属性声明投影，规则表达式产出实际类型未验",
)


def base_namespace(model: dict) -> Namespace:
    """按 DSL ontology 名构造 URN 命名空间。

    Args:
        model: DSL 模型 dict（读顶层 ontology 键；缺失时用 model 兜底——沙盘不替代 lint 报缺键）。
    Returns:
        rdflib Namespace（urn:x-onto:<名>:），实体/属性/谓词 IRI 的公共前缀。
    """
    onto = str(model.get("ontology") or "model").strip() or "model"
    return Namespace(f"urn:x-onto:{onto}:")


def bind_prefix(graph: Graph, model: dict) -> None:
    """把本体命名空间以可读前缀绑定到图（Turtle 序列化时 IRI 显示为 prefix:局部名）。

    Args:
        graph: 待绑定的 rdflib 图（OWL 图与 shapes 图各绑一次）。
        model: DSL 模型 dict（取 ontology 名做前缀，连字符替换为下划线保 Turtle 前缀合法）。
    Returns:
        None。
    """
    onto = str(model.get("ontology") or "model").strip() or "model"
    graph.bind(onto.replace("-", "_"), base_namespace(model))


def link_pairs(ent: dict) -> list[tuple[str, Optional[str], Optional[list]]]:
    """解析实体 links 的 (别名, 目标实体名, 显式外键字段列表或 None) 列表。

    Args:
        ent: 实体定义 dict。
    Returns:
        三元组列表；简写 ``alias: Target`` 与显式 ``alias: {target, fk?}`` 两种形态统一出口，
        结构非法项跳过不报错（结构层问题归 lint，沙盘不重复检查）。
    """
    links = ent.get("links")
    if not isinstance(links, dict):
        return []
    pairs: list[tuple[str, Optional[str], Optional[list]]] = []
    for alias, value in links.items():
        if isinstance(value, str):
            pairs.append((str(alias), value, None))
        elif isinstance(value, dict) and isinstance(value.get("target"), str):
            fk = value.get("fk")
            pairs.append((str(alias), value["target"], fk if isinstance(fk, list) else None))
    return pairs


def _iter_props(ent: dict):
    """迭代实体 properties 中结构合法的 (字段名, 属性定义 dict)。Args: ent 实体定义 dict。"""
    props = ent.get("properties")
    for field, spec in (props.items() if isinstance(props, dict) else []):
        if isinstance(spec, dict):
            yield str(field), spec


def _collect_promises(model: dict) -> list[dict]:
    """收集 derived_property 规则的派生承诺（行为语义不转公理，结构化留给沙盘 S1）。

    Args:
        model: DSL 模型 dict。
    Returns:
        承诺表：每项 {rule: 规则名, entity: upstream 实体名, field: logic 左值目标字段, expr: 表达式}；
        logic 结构不合法的规则跳过（归 lint4）。
    """
    promises: list[dict] = []
    for rule in model.get("rules") or []:
        if not isinstance(rule, dict) or rule.get("rule_type") != "derived_property":
            continue
        logic = rule.get("logic")
        if not (isinstance(logic, str) and ":" in logic):
            continue
        target, expr = logic.split(":", 1)
        upstream = rule.get("upstream") or []
        promises.append({"rule": str(rule.get("name") or ""), "entity": str(upstream[0]) if upstream else "",
                         "field": target.strip(), "expr": expr.strip()})
    return promises


# ===========二、投影主转换==========
def convert(model: dict) -> tuple[Graph, Graph, list[dict]]:
    """把 DSL 模型一次性投影为 (OWL 公理图, SHACL shapes 图, 派生承诺表)。

    Args:
        model: DSL 模型 dict（结构合法性由 lint 负责；非法子结构按跳过处理）。
    Returns:
        三元组 (owl_graph, shapes_graph, promises)：前两者为 rdflib.Graph（Turtle 可序列化），
        第三者为 _collect_promises 产物（derived_property 规则结构化清单）。
    Raises:
        不主动抛出——语义网库内部异常由调用方（semantic_sandbox S4/S5）按 error 上报。
    """
    ns = base_namespace(model)
    # owl_graph：OWL 公理层投影 / shapes_graph：SHACL 约束层投影 / promises：派生承诺表
    owl_graph, shapes_graph = Graph(), Graph()
    bind_prefix(owl_graph, model)
    bind_prefix(shapes_graph, model)
    shapes_graph.bind("sh", SH)
    promises = _collect_promises(model)
    entities = model.get("entities")
    for name, ent in (entities.items() if isinstance(entities, dict) else []):
        if not isinstance(ent, dict):
            continue
        cls = ns[str(name)]
        #   1. 实体 → owl:Class + 展示名/业务定义标注
        owl_graph.add((cls, RDF.type, OWL.Class))
        owl_graph.add((cls, RDFS.label, Literal(str(ent.get("display_name") or ""), lang="zh")))
        owl_graph.add((cls, RDFS.comment, Literal(str(ent.get("description") or ""))))
        #   2. NodeShape 骨架（每实体一个，targetClass 指向对应类）
        shape = ns[f"Shape_{name}"]
        shapes_graph.add((shape, RDF.type, SH.NodeShape))
        shapes_graph.add((shape, SH.targetClass, cls))
        for field, spec in _iter_props(ent):
            prop = ns[f"{name}_{field}"]
            #   3. 属性 → owl:DatatypeProperty（domain=所属实体，range=XSD 类型）
            owl_graph.add((prop, RDF.type, OWL.DatatypeProperty))
            owl_graph.add((prop, RDFS.domain, cls))
            xsd_type = XSD_TYPE_MAP.get(str(spec.get("type")))
            if xsd_type is not None:
                owl_graph.add((prop, RDFS.range, xsd_type))
            #   4. derived 属性 → derivedPromise 注解谓词关联规则名（按承诺表 entity+field 匹配）
            if spec.get("derived"):
                for promise in promises:
                    if promise["entity"] == str(name) and promise["field"] == field:
                        owl_graph.add((prop, ns[DERIVED_PROMISE_LOCAL], Literal(promise["rule"])))
            #   5. 属性约束节点：主键 minCount/maxCount 1（A2）；枚举 sh:in（A4）；一律登记 datatype（A3）
            pnode = BNode()
            shapes_graph.add((shape, SH.property, pnode))
            shapes_graph.add((pnode, SH.path, prop))
            if xsd_type is not None:
                shapes_graph.add((pnode, SH.datatype, xsd_type))
            if spec.get("primary"):
                shapes_graph.add((pnode, SH.minCount, Literal(1)))
                shapes_graph.add((pnode, SH.maxCount, Literal(1)))
            enum_values = spec.get("enum_values")
            if isinstance(enum_values, list) and enum_values:
                head = BNode()
                shapes_graph.add((pnode, SH["in"], head))
                Collection(shapes_graph, head, [Literal(str(v)) for v in enum_values])
        #   6. links 别名 → owl:ObjectProperty（domain=持有方，range=目标——按 A1 假设推导）
        for alias, target, _fk in link_pairs(ent):
            obj_prop = ns[f"{name}_{alias}"]
            owl_graph.add((obj_prop, RDF.type, OWL.ObjectProperty))
            owl_graph.add((obj_prop, RDFS.domain, cls))
            owl_graph.add((obj_prop, RDFS.range, ns[target]))
    return owl_graph, shapes_graph, promises


# ===========三、模块调试入口（独立运行观察投影产物）==========
def _main() -> int:
    """独立调试入口：加载命令行模型并打印三件套概要（观察假设投影形态用，不做检查）。"""
    if len(sys.argv) != 2:
        print("用法: python owl_converter.py <model.yaml>（内部模块——L2 检查请跑 semantic_sandbox.py）",
              file=sys.stderr)
        return 2
    path = Path(sys.argv[1])
    if not path.is_file():
        print(f"错误：文件不存在 {path}", file=sys.stderr)
        return 2
    model = yaml.safe_load(path.read_text(encoding="utf-8"))
    owl_graph, shapes_graph, promises = convert(model)
    print(f"====假设投影概要====: {path}")
    print(f"OWL 公理图 {len(owl_graph)} 三元组 / SHACL shapes 图 {len(shapes_graph)} 三元组 / 派生承诺 {len(promises)} 条")
    print("----OWL Turtle（前 40 行）----")
    print("\n".join(owl_graph.serialize(format="turtle").splitlines()[:40]))
    print("----SHACL Turtle（前 40 行）----")
    print("\n".join(shapes_graph.serialize(format="turtle").splitlines()[:40]))
    print("----派生承诺表----")
    for promise in promises:
        print(f"{promise['entity']}.{promise['field']} <= {promise['expr']}（规则「{promise['rule']}」）")
    return 0


if __name__ == "__main__":
    # CLI 本体即调试入口：python owl_converter.py <model.yaml> 观察投影产物。
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    sys.exit(_main())
