"""DSL 模型拓扑可视化：把实体 / links / 规则三要素渲染为 Mermaid classDiagram。

主要 Input：DSL YAML 模型路径（位置参数）+ 可选 -o 输出路径（默认模型同目录 topology.md）
+ 可选 --diff <base.yaml>（渲染 target 相对 base 的差异拓扑，默认输出 topology-diff.md）。
主要 Output：Markdown 文件（含 ```mermaid classDiagram 代码块）——实体=class（主键带 🔑），
links=关联线（目标 "1" --> "*" 持有方 : 别名），derived 目标字段与 trigger 条件在 note 标注；
不画能力问题（CQ）。逻辑结构驱动，不含实体名特判。
--diff 模式：新增实体/属性/links 绿色高亮、删除红色、修改黄色（classDef + class + linkStyle；
Mermaid class 成员不支持删除线文本，删除项以红色 classDef + 行尾【删除】标签替代）；
差异判定复用 diff_model.diff_models（与 changeset.json 同一事实来源）。
--image png|svg|both（默认关闭，不传即保持纯 Markdown 行为零变化）：额外产出图片文件，
与 Markdown 同目录同名（topology.png/svg 或 topology-diff.png/svg）；渲染管线在
render_image.py（Playwright 无头浏览器 + mermaid@11，CDN 失败降级本地缓存，皆无则中文报错）。
"""

# 标准库导入
import argparse
import sys
from pathlib import Path
from typing import Any

# 第三方依赖导入
import yaml

# 项目内部模块导入（同目录：差异判定与 diff_model.py 共用同一逻辑；图片渲染管线独立模块）
from diff_model import diff_models
from render_image import render_mermaid_image



def _link_label(alias: str, value) -> tuple[str, str]:
    """解析单个 links 项为 (目标实体名, 连线标签)。

    Args:
        alias: links 别名。
        value: links 项（目标名字符串或 {target, fk, name} 映射）。
    Returns:
        (目标实体名, 标签)；显式形态带 name 时标签为"语义名"（关系业务语义），
        否则回退别名。
    """
    if isinstance(value, str):
        return value, alias
    if isinstance(value, dict) and isinstance(value.get("target"), str):
        return value["target"], str(value.get("name") or alias)
    return str(value), alias

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
        for alias, raw in links.items():
            target, label = _link_label(alias, raw)
            if isinstance(target, str) and target in entities:
                # 持有方持引用（多端），目标被引用（1 端）。
                lines.append(f'    {target} "1" --> "*" {holder} : {label}')
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


# ===========四、整体渲染（全量拓扑）==========
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


# ===========五、差异拓扑渲染（--diff）==========
# STYLE_CLASS：差异状态 -> Mermaid classDef 名（§9：绿增红删黄改）。
# 取舍说明：Mermaid class 成员不支持删除线，删除项以红色 classDef + 行尾【删除】标签替代；
# classDiagram 的 linkStyle 实测（mermaid@11）可解析但渲染不生效，故关联线变更以
# 标签文字【新增】/【删除】/【修改】+ 持有方实体黄色高亮表达，不输出 linkStyle 行。
STYLE_CLASS = {"added": "diffAdded", "removed": "diffRemoved", "modified": "diffModified"}


def _diff_index(base: dict[str, Any], target: dict[str, Any]) -> dict[str, Any]:
    """diff 两份模型并把 diff_model 的 operations 路径折叠为渲染用状态索引。

    Args:
        base: base 侧 DSL 模型 dict。
        target: target 侧 DSL 模型 dict。
    Returns:
        索引 dict：entities 项含 status（added|removed|modified|None）、props（字段级状态）、
        links（别名级状态）；rules 项为规则名 -> 状态。
    """
    out = diff_models(base, target)
    idx: dict[str, Any] = {"entities": {}, "rules": {}}
    for op in out.operations:
        parts = op["path"].split("/")
        if parts[1] == "entities":
            # ent：实体状态项；status 先由整实体 add/remove 或标量 replace 设定
            ent = idx["entities"].setdefault(parts[2], {"status": None, "props": {}, "links": {}})
            if len(parts) == 3:
                ent["status"] = "added" if op["op"] == "add" else "removed"
            elif parts[3] == "properties" and len(parts) == 5:
                ent["props"][parts[4]] = op["op"]  # 属性整体 add/remove
            elif parts[3] == "properties":
                # 子字段 replace；未被整体 add/remove 覆盖时标 modified
                if ent["props"].get(parts[4]) not in ("add", "remove"):
                    ent["props"][parts[4]] = "modified"
            elif parts[3] == "links":
                ent["links"][parts[4]] = op["op"]
            elif ent["status"] is None:
                ent["status"] = "modified"  # 实体级标量（display_name 等）replace
        elif len(parts) == 3:
            idx["rules"][parts[2]] = "added" if op["op"] == "add" else "removed"
        else:
            idx["rules"][parts[2]] = "modified"  # 规则子字段 replace
    # 子变更（属性/links）未升级 status 的共有实体 -> modified
    for ent in idx["entities"].values():
        if ent["status"] is None and (ent["props"] or ent["links"]):
            ent["status"] = "modified"
    return idx


def _member_lines_diff(ent_state: dict[str, Any] | None, tgt_ent: dict[str, Any] | None,
                       base_ent: dict[str, Any] | None) -> list[str]:
    """diff 模式成员行：target 属性带增删改标签；被删实体/被删属性画 base 侧成员。

    Args:
        ent_state: _diff_index 的实体状态项（无变更实体为 None）。
        tgt_ent: target 侧实体定义（实体被删时为 None）。
        base_ent: base 侧实体定义（新增实体时为 None）。
    Returns:
        Mermaid 成员行列表；整实体删除时不逐成员打标（红色 classDef 已表达）。
    """
    lines = []
    status = (ent_state or {}).get("status")
    props_status = (ent_state or {}).get("props", {})
    if status == "removed":
        # 整实体已删：画 base 全部成员（类级红色 classDef 表达删除，成员不逐个打标）
        for field, spec in (base_ent.get("properties") or {}).items():
            if isinstance(spec, dict):
                pk_mark = " 🔑" if spec.get("primary") else ""
                lines.append(f"        +{field} : {spec.get('type', '?')}{pk_mark}")
        return lines
    if tgt_ent is not None:
        for field, spec in (tgt_ent.get("properties") or {}).items():
            if not isinstance(spec, dict):
                continue
            pk_mark = " 🔑" if spec.get("primary") else ""
            tag = {"add": "【新增】", "modified": "【修改】"}.get(props_status.get(field), "")
            lines.append(f"        +{field} : {spec.get('type', '?')}{pk_mark}{tag}")
    if base_ent is not None:
        # 共有实体上被删的属性：按 base 定义画删除行
        for field, spec in (base_ent.get("properties") or {}).items():
            if props_status.get(field) == "remove" and isinstance(spec, dict):
                pk_mark = " 🔑" if spec.get("primary") else ""
                lines.append(f"        +{field} : {spec.get('type', '?')}{pk_mark}【删除】")
    return lines


def _note_lines_diff(target: dict[str, Any], base: dict[str, Any],
                     idx: dict[str, Any]) -> list[str]:
    """diff 模式规则 note：target 规则 + base 独有已删规则，带增删改标记与规则名。

    Args:
        target: target 侧 DSL 模型 dict。
        base: base 侧 DSL 模型 dict。
        idx: _diff_index 状态索引。
    Returns:
        Mermaid note 行列表；diff 专属格式（衍生/触发 note 均带规则名，全量模式不带）。
    """
    # rules_marked：[(规则 dict, 状态)]，target 全量在前、base 独有已删规则殿后
    rules_marked = [(r, idx["rules"].get(r.get("name")))
                    for r in (target.get("rules") or []) if isinstance(r, dict)]
    rules_marked += [(r, "removed") for r in (base.get("rules") or [])
                     if isinstance(r, dict) and idx["rules"].get(r.get("name")) == "removed"]
    notes: dict[str, list[str]] = {}
    for rule, status in rules_marked:
        upstreams = [u for u in (rule.get("upstream") or []) if isinstance(u, str)]
        if not upstreams:
            continue
        entity = upstreams[0]
        tag = {"added": "【新增】", "removed": "【删除】", "modified": "【修改】"}.get(status, "")
        if rule.get("rule_type") == "derived_property":
            notes.setdefault(entity, []).append(
                f"【衍生】{tag}{rule.get('name')}: {_sanitize(rule.get('logic'))}")
        elif rule.get("rule_type") == "trigger":
            logic = rule.get("logic")
            conds = []
            for cond in (logic.get("ALL") if isinstance(logic, dict) else None) or []:
                if isinstance(cond, dict) and cond.get("field"):
                    conds.append(f"{cond['field']} {_sanitize(cond.get('operator'))} "
                                 f"{_sanitize(_fmt_value(cond.get('value')))}")
            cond_text = " 且 ".join(conds) if conds else "（无条件）"
            notes.setdefault(entity, []).append(
                f"【触发】{tag}{_sanitize(rule.get('name'))}: {cond_text}")
    return [
        f'    note for {entity} "{"<br/>".join(parts)}"'
        for entity, parts in notes.items()
    ]


def _link_lines_diff(merged: dict[str, Any], b_entities: dict[str, Any],
                     idx: dict[str, Any]) -> list[str]:
    """diff 模式关联线：target 全量 links（带增删改标签）+ 共有实体上被删别名的删除线。

    Args:
        merged: 联合实体集（target 全量 + base 独有删除实体）。
        b_entities: base 侧实体表（取被删别名的目标实体用）。
        idx: _diff_index 状态索引。
    Returns:
        Mermaid 关联线行列表；变更以标签文字标记（linkStyle 渲染不生效，见取舍说明）。
    """
    lines = []
    for holder, ent in merged.items():
        state = idx["entities"].get(holder)
        if state and state["status"] == "removed":
            continue  # 整实体已删（红色 classDef 表达），其持有的关系线不再单画
        link_status = (state or {}).get("links", {})
        for alias, raw in (ent.get("links") or {}).items():
            tgt_name, label = _link_label(alias, raw)
            if isinstance(tgt_name, str) and tgt_name in merged:
                tag = {"add": "【新增】", "replace": "【修改】"}.get(link_status.get(alias), "")
                lines.append(f'    {tgt_name} "1" --> "*" {holder} : {label}{tag}')
        for alias, status in link_status.items():
            # 共有实体上被删的别名：按 base 定义补画删除线
            if status != "remove":
                continue
            tgt_name = ((b_entities.get(holder) or {}).get("links") or {}).get(alias)
            if isinstance(tgt_name, str) and tgt_name in merged:
                lines.append(f'    {tgt_name} "1" --> "*" {holder} : {alias}【删除】')
    return lines


def render_topology_diff(target: dict[str, Any], base: dict[str, Any]) -> tuple[str, dict[str, int]]:
    """把 target 相对 base 的差异渲染为差异拓扑 Markdown。

    Args:
        target: target 侧 DSL 模型 dict。
        base: base 侧 DSL 模型 dict。
    Returns:
        (Markdown 全文, 变更统计 dict)；统计含实体新增/删除/修改数与规则变更条数。
    """
    idx = _diff_index(base, target)
    t_entities = target.get("entities") or {}
    b_entities = base.get("entities") or {}
    # merged：联合实体集（target 序在前 + base 独有删除实体殿后）
    merged = {**{k: v for k, v in t_entities.items() if isinstance(v, dict)},
              **{k: v for k, v in b_entities.items()
                 if isinstance(v, dict) and k not in t_entities}}
    lines = [
        f"# 本体差异拓扑：{target.get('ontology', '?')}（{target.get('version', '?')}）",
        "",
        f"> 由 render_topology.py --diff 自动生成：target 相对 base"
        f"（{base.get('ontology', '?')} {base.get('version', '?')}）的差异，与 changeset.json 同一判定来源。",
        "> 图例：绿 class=新增实体，红 class=删除，黄 class=有修改；成员行尾【新增】/【删除】/【修改】为属性级标记，",
        "> 关联线标签尾【新增】/【删除】/【修改】为 links 级标记（持有方实体同步黄色高亮）。",
        "> 取舍：Mermaid class 成员不支持删除线、classDiagram 的 linkStyle 渲染不生效（mermaid@11 实测），",
        "> 删除项以红色 classDef 替代、links 变更以标签文字标记。",
        "",
        "```mermaid",
        "    classDiagram",
    ]
    #   1. class 块：联合实体集逐个渲染（新增实体用 target 定义，删除实体用 base 定义）
    for name, ent in merged.items():
        state = idx["entities"].get(name)
        lines.append(f"    class {name} {{")
        lines.extend(_member_lines_diff(state, t_entities.get(name), b_entities.get(name)))
        lines.append("    }")
        if state and state["status"]:
            lines.append(f"    class {name}:::{STYLE_CLASS[state['status']]}")
    #   2. 规则 note（diff 专属格式，带规则名与增删改标记）
    lines.extend(_note_lines_diff(target, base, idx))
    #   3. links：target 全量 + 删除别名补画（变更以标签文字标记）；classDef 须在 class::: 语句之后
    lines.extend(_link_lines_diff(merged, b_entities, idx))
    lines.append("    classDef diffAdded fill:#e6ffe6,stroke:#2e7d32,stroke-width:2px")
    lines.append("    classDef diffRemoved fill:#ffe6e6,stroke:#c62828,stroke-width:2px")
    lines.append("    classDef diffModified fill:#fffbe6,stroke:#f9a825,stroke-width:2px")
    lines.append("```")
    #   4. 变更摘要（与图呼应）
    statuses = [(idx["entities"].get(n) or {}).get("status") for n in merged]
    stats = {"added": statuses.count("added"), "removed": statuses.count("removed"),
             "modified": statuses.count("modified"), "rules": len(idx["rules"])}
    lines += ["", f"**变更摘要**：实体 新增 {stats['added']} / 删除 {stats['removed']} / "
                  f"修改 {stats['modified']}；规则变更 {stats['rules']} 条。", ""]
    return "\n".join(lines) + "\n", stats


# ===========六、图片输出（--image：Markdown -> Mermaid 源 -> PNG/SVG）==========
def _extract_mermaid_block(markdown: str) -> str:
    """从渲染产物 Markdown 中提取 ```mermaid 代码块源码。

    Args:
        markdown: render_topology / render_topology_diff 生成的 Markdown 全文。
    Returns:
        Mermaid 源码字符串（不含围栏行）。
    Raises:
        ValueError: Markdown 中未找到 mermaid 代码块。
    """
    lines = markdown.splitlines()
    inside = False
    block: list[str] = []
    for line in lines:
        if not inside and line.strip() == "```mermaid":
            inside = True
            continue
        if inside and line.strip() == "```":
            return "\n".join(block) + "\n"
        if inside:
            block.append(line)
    raise ValueError("Markdown 中未找到 ```mermaid 代码块，无法渲染图片")


def _write_images(content: str, md_path: Path, fmt: str) -> None:
    """提取 Mermaid 源并渲染图片，打印中文摘要（含尺寸与 mermaid 资源来源）。

    Args:
        content: 渲染产物 Markdown 全文。
        md_path: 已写出的 Markdown 路径（图片与其同目录同名，仅扩展名不同）。
        fmt: 图片格式 png | svg | both。
    Raises:
        ValueError: 未找到 mermaid 代码块；RuntimeError: 渲染环境或资源加载失败（中文提示）。
        两者均转为 stderr 中文报错 + SystemExit(2)（Markdown 已先行落盘，不受影响）。
    """
    try:
        src = _extract_mermaid_block(content)
        info = render_mermaid_image(src, md_path.with_suffix(""), fmt)
    except (ValueError, RuntimeError) as exc:
        print(f"错误：拓扑图片渲染失败——{exc}", file=sys.stderr)
        raise SystemExit(2) from exc
    parts = [str(p) for p in (info["png"], info["svg"]) if p]
    print(f"====拓扑图片渲染完成====: {', '.join(parts)}（自然图幅 {info['width']}x{info['height']} CSS px，"
          f"PNG 采样 {info['scale']}x，mermaid 来源: {info['source']}）")


# ===========七、命令行入口==========
def main() -> None:
    """命令行入口：读 DSL -> 全量或 --diff 差异渲染 -> 写 Markdown，打印中文摘要。"""
    parser = argparse.ArgumentParser(
        description="DSL 模型拓扑可视化（Mermaid classDiagram，支持 --diff 差异拓扑）")
    parser.add_argument("model", help="DSL YAML 模型路径（--diff 模式下为 target 模型）")
    parser.add_argument("-o", "--output", default=None,
                        help="输出 Markdown 路径（默认模型同目录 topology.md；--diff 模式为 topology-diff.md）")
    parser.add_argument("--diff", default=None, metavar="BASE_YAML",
                        help="base DSL YAML 路径：渲染 target 相对 base 的差异拓扑")
    parser.add_argument("--image", default=None, const="png", nargs="?", metavar="FMT",
                        choices=["png", "svg", "both"],
                        help="额外产出图片文件（不传=关闭，裸 --image=png，可选 png/svg/both），"
                             "与 Markdown 同目录同名；需 Playwright + Chromium（见 render_image.py）")
    args = parser.parse_args()
    model_path = Path(args.model)
    model = yaml.safe_load(model_path.read_text(encoding="utf-8"))
    if not isinstance(model, dict) or not isinstance(model.get("entities"), dict):
        print("错误：模型缺少 entities 映射结构", file=sys.stderr)
        raise SystemExit(2)
    if args.diff:
        #   1. diff 模式：读 base，渲染差异拓扑
        base_path = Path(args.diff)
        base = yaml.safe_load(base_path.read_text(encoding="utf-8"))
        if not isinstance(base, dict) or not isinstance(base.get("entities"), dict):
            print("错误：base 模型缺少 entities 映射结构", file=sys.stderr)
            raise SystemExit(2)
        content, stats = render_topology_diff(model, base)
        default_name = "topology-diff.md"
        out_path = Path(args.output) if args.output else model_path.parent / default_name
        out_path.write_text(content, encoding="utf-8")
        print(f"====差异拓扑渲染完成====: {base_path} + {model_path} -> {out_path}")
        print(f"变更实体: 新增 {stats['added']} / 删除 {stats['removed']} / 修改 {stats['modified']}，"
              f"规则变更: {stats['rules']} 条")
        if args.image:
            #   2. --image：差异拓扑同步出图（topology-diff.png/svg）
            _write_images(content, out_path, args.image)
        return
    #   2. 全量模式（原行为不变）：渲染 -> 写 topology.md
    out_path = Path(args.output) if args.output else model_path.parent / "topology.md"
    content = render_topology(model)
    out_path.write_text(content, encoding="utf-8")
    link_count = sum(len((e.get("links") or {})) for e in model["entities"].values()
                     if isinstance(e, dict) and isinstance(e.get("links"), dict))
    print(f"====拓扑渲染完成====: {model_path} -> {out_path}")
    print(f"实体数: {len(model['entities'])}，links 数: {link_count}，"
          f"规则数: {len(model.get('rules') or [])}")
    if args.image:
        #   3. --image：全量拓扑同步出图（topology.png/svg）
        _write_images(content, out_path, args.image)


if __name__ == "__main__":
    # CLI 脚本本体即调试入口：python render_topology.py <model.yaml> 跑真实模型。
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    main()
