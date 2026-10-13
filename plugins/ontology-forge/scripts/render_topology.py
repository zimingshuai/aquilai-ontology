"""DSL 模型拓扑可视化：把实体 / links / 规则三要素渲染为 Mermaid classDiagram。

主要 Input：DSL YAML 模型路径（位置参数）+ 可选 -o 输出路径（默认模型同目录 topology.md）。
主要 Output：Markdown 文件（含 ```mermaid classDiagram 代码块）——实体=class（主键带 🔑），
links=关联线（目标 "1" --> "*" 持有方 : 别名），derived 目标字段与 trigger 条件在 note 标注；
不画能力问题（CQ）。逻辑结构驱动，不含实体名特判。
"""

# 标准库导入
import argparse
import sys
from pathlib import Path
from typing import Any

# 第三方依赖导入
import yaml


# ===========一、文本清洗（Mermaid 语法安全）==========
def _sanitize(text: Any) -> str:
    """把任意值清洗为 Mermaid note 安全文本。

    Args:
        text: 待清洗的规则名/表达式/条件值等。
    Returns:
        替换掉双引号与尖括号（避免破坏 note 字符串或被当作 HTML 标签）后的文本。
    """
    # 尖括号全角化：既保住 >=/<= 语义，又不与 <br/> 换行标记冲突。
    return (
        str(text)
        .replace('"', "'")
        .replace("<=", "≤")
        .replace(">=", "≥")
        .replace("<", "＜")
        .replace(">", "＞")
    )


def _fmt_value(value: Any) -> str:
    """格式化 trigger 条件值：数组转 [a, b, c]，其余转字符串。

    Args:
        value: 条件 value 字段（标量或数组）。
    Returns:
        展示用字符串。
    """
    if isinstance(value, list):
        return "[" + ", ".join(str(v) for v in value) + "]"
    if isinstance(value, bool):
        return str(value).lower()  # 忠实 YAML 原文的小写 true/false
    return str(value)


# ===========二、class 成员与关联线渲染==========
def _member_lines(entity: dict[str, Any]) -> list[str]:
    """渲染实体属性为 class 成员行（主键追加 🔑 标记）。

    Args:
        entity: DSL 实体定义 dict（properties / links）。
    Returns:
        Mermaid 成员行列表，如 `+sku_code : STRING 🔑`。
    """
    lines = []
    for field, spec in (entity.get("properties") or {}).items():
        if not isinstance(spec, dict):
            continue
        # pk_mark：主键标记（复合主键每字段都标）。
        pk_mark = " 🔑" if spec.get("primary") else ""
        lines.append(f"        +{field} : {spec.get('type', '?')}{pk_mark}")
    return lines


def _link_lines(entities: dict[str, Any]) -> list[str]:
    """渲染 links 为 class 关联线：目标 "1" --> "*" 持有方 : 别名。

    Args:
        entities: 实体名 -> 实体定义 dict。
    Returns:
        Mermaid 关联线行列表；持有方 links 别名即线的标签。
    """
    lines = []
    for holder, entity in entities.items():
        links = entity.get("links") or {}
        if not isinstance(links, dict):
            continue
        for alias, target in links.items():
            if isinstance(target, str) and target in entities:
                # 持有方持引用（多端），目标被引用（1 端）。
                lines.append(f'    {target} "1" --> "*" {holder} : {alias}')
    return lines


# ===========三、规则 note 渲染（derived 目标字段 + trigger 条件）==========
def _note_lines(model: dict[str, Any]) -> list[str]:
    """按 upstream 实体聚合规则，渲染 note for 块（每实体至多一条，<br/> 换行）。

    Args:
        model: DSL 模型 dict（读 entities / rules）。
    Returns:
        Mermaid note 行列表；无规则的实体不产生 note。
    """
    # notes：实体 -> note 文本片段列表（derived / trigger 混排）。
    notes: dict[str, list[str]] = {}
    for rule in model.get("rules") or []:
        if not isinstance(rule, dict):
            continue
        upstreams = [u for u in (rule.get("upstream") or []) if isinstance(u, str)]
        if not upstreams:
            continue
        entity = upstreams[0]  # v0.2 upstream 为单元素；异常多元素时取主实体展示
        rule_type = rule.get("rule_type")
        if rule_type == "derived_property":
            logic = str(rule.get("logic") or "")
            notes.setdefault(entity, []).append(f"【衍生】{_sanitize(logic)}")
        elif rule_type == "trigger":
            conds = []
            logic = rule.get("logic")
            all_conds = logic.get("ALL") if isinstance(logic, dict) else None
            for cond in all_conds or []:
                if isinstance(cond, dict) and cond.get("field"):
                    conds.append(
                        f"{cond['field']} {_sanitize(cond.get('operator'))} "
                        f"{_sanitize(_fmt_value(cond.get('value')))}"
                    )
            cond_text = " 且 ".join(conds) if conds else "（无条件）"
            notes.setdefault(entity, []).append(
                f"【触发】{_sanitize(rule.get('name'))}: {cond_text}"
            )
    return [
        f'    note for {entity} "{"<br/>".join(parts)}"'
        for entity, parts in notes.items()
    ]


# ===========四、整体渲染与落盘==========
def render_topology(model: dict[str, Any]) -> str:
    """把 DSL 模型渲染为完整 Markdown 文档（含 mermaid 代码块）。

    Args:
        model: safe_load 得到的 DSL 模型 dict。
    Returns:
        Markdown 全文字符串。
    """
    entities = model.get("entities") or {}
    lines = [
        f"# 本体拓扑：{model.get('ontology', '?')}（{model.get('version', '?')}）",
        "",
        "> 由 render_topology.py 从 DSL 自动生成；仅含实体 + links + 规则三要素，不含能力问题（CQ）。",
        "> 图例：🔑 = 主键；关联线 `目标 \"1\" --> \"*\" 持有方 : 别名` = 持有方实体的 links 别名持有指向目标的引用；",
        "> 【衍生】= derived_property（目标字段: 表达式）；【触发】= trigger 条件摘要（多条件合取）。",
        "",
        "```mermaid",
        "    classDiagram",
    ]
    for name, entity in entities.items():
        if not isinstance(entity, dict):
            continue
        lines.append(f"    class {name} {{")
        lines.extend(_member_lines(entity))
        lines.append("    }")
    lines.extend(_note_lines(model))
    lines.extend(_link_lines(entities))
    lines.append("```")
    return "\n".join(lines) + "\n"


def main() -> None:
    """命令行入口：读 DSL -> 渲染 -> 写 topology.md，打印中文摘要。"""
    parser = argparse.ArgumentParser(description="DSL 模型拓扑可视化（Mermaid classDiagram）")
    parser.add_argument("model", help="DSL YAML 模型路径")
    parser.add_argument("-o", "--output", default=None,
                        help="输出 Markdown 路径（默认模型同目录 topology.md）")
    args = parser.parse_args()
    model_path = Path(args.model)
    model = yaml.safe_load(model_path.read_text(encoding="utf-8"))
    if not isinstance(model, dict) or not isinstance(model.get("entities"), dict):
        print("错误：模型缺少 entities 映射结构", file=sys.stderr)
        raise SystemExit(2)
    # out_path：输出路径，缺省与模型同目录。
    out_path = Path(args.output) if args.output else model_path.parent / "topology.md"
    out_path.write_text(render_topology(model), encoding="utf-8")
    link_count = sum(len((e.get("links") or {})) for e in model["entities"].values()
                     if isinstance(e, dict) and isinstance(e.get("links"), dict))
    print(f"====拓扑渲染完成====: {model_path} -> {out_path}")
    print(f"实体数: {len(model['entities'])}，links 数: {link_count}，"
          f"规则数: {len(model.get('rules') or [])}")


if __name__ == "__main__":
    # CLI 脚本本体即调试入口：python render_topology.py <model.yaml> 跑真实模型。
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    main()
