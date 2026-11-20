"""域交接包生成器——本体定稿产物 → 技能工厂立项素材（第五道工序向第六道工序的交付）。

主要 Input：DSL 模型 YAML 路径（位置参数）；可选 --out-dir 产物目录（缺省为模型同级 handoff/）。
主要 Output：handoff/ 五件（cq-final / glossary-snapshot / rule-calibers / oq-verdicts /
           probe-expectations，均带用途头注）+ stdout 中文清单；解析失败退出码 2。
定位红线：交接包是技能制造时的输入素材，不是技能运行时依赖——易变结构（动作/规则/字段）
           一律以平台 MCP 现查为准，本包仅提供实测预期与验收种子（「结构只在一处」哲学）。
"""

# 标准库导入
import argparse
import sys
from pathlib import Path
from typing import Any

# 第三方依赖导入
import yaml

# ===========一、常量与模型加载==========
# HANDOFF_HEADER：每件产物头部的用途与红线声明（素材非依赖，易变结构现查为准）。
HANDOFF_HEADER = (
    "> 域交接包（handoff）——技能工厂（aquilair-skill-forge）立项素材。\n"
    "> 红线：本文件是技能**制造时**的输入素材，不是技能**运行时**依赖；\n"
    "> 动作/规则/字段等易变结构一律以平台 MCP 实时元数据为准，本包内容不沉淀为快照。\n"
)


def load_model(path: Path) -> dict:
    """加载 DSL 模型 YAML。

    Args:
        path: 模型文件路径。
    Returns:
        解析后的模型 dict。
    Raises:
        SystemExit: 文件缺失或 YAML 解析失败时退出码 2（不静默降级）。
    """
    if not path.is_file():
        print(f"错误：模型文件不存在 {path}", file=sys.stderr)
        sys.exit(2)
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        print(f"错误：YAML 解析失败 {exc}", file=sys.stderr)
        sys.exit(2)
    if not isinstance(data, dict):
        print("错误：模型根结构不是映射", file=sys.stderr)
        sys.exit(2)
    return data


def _write(out_dir: Path, name: str, lines: list[str]) -> None:
    """写单件产物（UTF-8）。Args: out_dir 目录；name 文件名；lines 行列表。Returns: None。"""
    (out_dir / name).write_text("\n".join(lines) + "\n", encoding="utf-8")


# ===========二、五件产物生成==========
def gen_cq_final(model: dict) -> list[str]:
    """生成 cq-final.md：CQ 终版（技能验收用例的种子）。

    Args:
        model: DSL 模型 dict。
    Returns:
        Markdown 行列表。
    """
    cqs = model.get("competency_questions") or []
    lines = [HANDOFF_HEADER, "# CQ 终版（验收用例种子）", "",
             "> 用途：技能工厂第⑥步验收的评估用例生成输入——每条 CQ 即一个业务问题验收点；",
             "> 呈审三态勾选结果（真业务/要改/删）见模型目录 cq-checklist.html，人工批复为权威。", "",
             "| CQ | 业务问题 | 本体覆盖（covered_by） |", "|---|---|---|"]
    for cq in cqs:
        # cid/q/covered：CQ 三键；covered_by 缺失时标注未映射（如实呈现）
        cid = str(cq.get("id", "?"))
        q = str(cq.get("q", "")).replace("|", "\\|")
        covered = ", ".join(str(c) for c in (cq.get("covered_by") or [])) or "（未映射）"
        lines.append(f"| {cid} | {q} | {covered} |")
    lines += ["", f"共 {len(cqs)} 条。"]
    return lines


def gen_glossary_snapshot(model: dict) -> list[str]:
    """生成 glossary-snapshot.md：术语对照与实体中文名权威表。

    Args:
        model: DSL 模型 dict。
    Returns:
        Markdown 行列表。
    """
    glossary = model.get("glossary_additions") or []
    entities = model.get("entities") or {}
    lines = [HANDOFF_HEADER, "# 术语与实体中文名对照（权威表快照）", "",
             "> 用途：技能交付规范「中文名（编码）」双写的对照来源；术语定义可直接进 calibers 术语节。", "",
             "## 受控词表（glossary_additions）", "", "| 术语 | 定义 |", "|---|---|"]
    for g in glossary:
        term = str(g.get("term", "?")).replace("|", "\\|")
        definition = str(g.get("definition", "")).replace("|", "\\|")
        lines.append(f"| {term} | {definition} |")
    lines += ["", "## 实体编码 ↔ 展示名", "", "| 实体（编码） | 中文名 | 属性数 |", "|---|---|---|"]
    for code, ent in entities.items():
        display = str((ent or {}).get("display_name", "?")).replace("|", "\\|")
        attr_count = len((ent or {}).get("properties") or {})
        lines.append(f"| {code} | {display} | {attr_count} |")
    return lines


def gen_rule_calibers(model: dict) -> list[str]:
    """生成 rule-calibers.md：规则口径表（技能判定面的初始认知）。

    Args:
        model: DSL 模型 dict。
    Returns:
        Markdown 行列表。
    """
    rules = model.get("rules") or []
    lines = [HANDOFF_HEADER, "# 规则口径表（判定面初始认知）", "",
             "> 用途：让技能作者在实测前知道「哪些字段是规则回写、哪些判定可能无承载」；",
             "> 技能落地时判定面须从 metadata_list_rules **现查推导**，本表不得沉淀为技能内清单快照。", "",
             "| 规则名（含状态前缀） | 类型 | 上游实体 | 口径摘要 |", "|---|---|---|---|"]
    for rule in rules:
        name = str(rule.get("name", "?")).replace("|", "\\|")
        rtype = str(rule.get("rule_type", "?"))
        upstream = ", ".join(str(u) for u in (rule.get("upstream") or [])) or "—"
        desc = str(rule.get("description") or rule.get("logic") or "").split("。")[0].replace("|", "\\|")
        lines.append(f"| {name} | {rtype} | {upstream} | {desc} |")
    lines += ["", f"共 {len(rules)} 条；名称带【待处理】/【待讨论】前缀的规则在技能侧引用时必须注明状态。"]
    return lines


def gen_oq_verdicts(model: dict) -> list[str]:
    """生成 oq-verdicts.md：OQ 裁决记录与能力边界清单。

    Args:
        model: DSL 模型 dict。
    Returns:
        Markdown 行列表。
    """
    oqs = model.get("open_questions") or []
    # resolved 组：已裁决（含已裁决待落地）——口径出处素材
    resolved = [o for o in oqs if str(o.get("status", "")).startswith("resolved")]
    # pending_engine：等引擎能力——技能能力边界声明素材
    pending_engine = [o for o in oqs if "engine" in str(o.get("status", ""))]
    # pending_rest：等业务方/等输入
    pending_rest = [o for o in oqs if str(o.get("status", "")).startswith("pending") and o not in pending_engine]
    lines = [HANDOFF_HEADER, "# OQ 裁决记录与能力边界", "",
             "> 用途：resolved 组是 calibers 口径节的 provenance 素材；pending-engine 组是技能能力边界",
             "> （「平台无承载」类声明）的素材——技能被要求做无承载之事时如实说明，不降级。", ""]
    lines += ["## 已裁决（口径出处）", "", "| OQ | 议题 | 裁决 | 状态 |", "|---|---|---|---|"]
    for o in resolved:
        oid = str(o.get("id", "?"))
        topic = str(o.get("topic", "")).replace("|", "\\|")
        resolution = str(o.get("resolution") or "—").replace("|", "\\|")
        status = str(o.get("status", "?"))
        lines.append(f"| {oid} | {topic} | {resolution} | {status} |")
    lines += ["", "## pending-engine（技能能力边界素材）", "", "| OQ | 议题 | 卡点 | 状态 |", "|---|---|---|---|"]
    for o in pending_engine:
        oid = str(o.get("id", "?"))
        topic = str(o.get("topic", "")).replace("|", "\\|")
        missing = str(o.get("missing_from") or "—").replace("|", "\\|")
        status = str(o.get("status", "?"))
        lines.append(f"| {oid} | {topic} | {missing} | {status} |")
    lines += ["", "## 其他待办（等业务方/等输入）", "", "| OQ | 议题 | 状态 |", "|---|---|---|"]
    for o in pending_rest:
        oid = str(o.get("id", "?"))
        topic = str(o.get("topic", "")).replace("|", "\\|")
        lines.append(f"| {oid} | {topic} | {o.get('status', '?')} |")
    lines += ["", f"共 {len(oqs)} 条（resolved {len(resolved)} / pending-engine {len(pending_engine)} / 其他 {len(pending_rest)}；",
              "resolved-pending-* 条目同时具有口径出处与能力边界价值，在前两组双列属预期）。"]
    return lines


def gen_probe_expectations(model: dict) -> list[str]:
    """生成 probe-expectations.md：实测预期清单（比对用，不沉淀）。

    Args:
        model: DSL 模型 dict。
    Returns:
        Markdown 行列表。
    """
    entities = list((model.get("entities") or {}).keys())
    actions = [str(a.get("name")) for a in (model.get("actions") or []) if a.get("name")]
    rules = [str(r.get("name")) for r in (model.get("rules") or []) if r.get("name")]
    lines = [HANDOFF_HEADER, "# MCP 实测预期清单（比对用，不沉淀）", "",
             "> 用途：技能工厂第②步实测的预期输入——带着本清单去验证 19 工具，实测从盲摸变验证；",
             "> **本件比对后即弃**：与实时元数据的差异以平台为准并记入 facts 坑典，本清单不进技能资产",
             "> （历史实证：actions 三周内 15→22，快照必漂）。", "",
             f"- 实体（{len(entities)} 个）：" + "、".join(entities),
             f"- 动作（{len(actions)} 个）：" + "、".join(actions),
             f"- 规则（{len(rules)} 条）：" + "、".join(rules)]
    return lines


# ===========三、装配与命令行入口==========
def generate_handoff(model_path: Path, out_dir: Path) -> list[str]:
    """生成完整交接包五件。

    Args:
        model_path: 模型文件路径（仅用于报告）。
        out_dir: 产物目录（调用方已创建）。
    Returns:
        各产物文件名列表。
    """
    model = load_model(model_path)
    artifacts = [
        ("cq-final.md", gen_cq_final(model)),
        ("glossary-snapshot.md", gen_glossary_snapshot(model)),
        ("rule-calibers.md", gen_rule_calibers(model)),
        ("oq-verdicts.md", gen_oq_verdicts(model)),
        ("probe-expectations.md", gen_probe_expectations(model)),
    ]
    for name, lines in artifacts:
        _write(out_dir, name, lines)
    return [name for name, _ in artifacts]


def main() -> int:
    """命令行入口：解析参数并生成交接包。Returns: 退出码（0 成功；2 解析失败）。"""
    parser = argparse.ArgumentParser(description="域交接包生成器（本体定稿 → 技能工厂立项素材）")
    parser.add_argument("model", help="DSL 模型 YAML 路径")
    parser.add_argument("--out-dir", default=None, help="产物目录（缺省为模型同级 handoff/）")
    args = parser.parse_args()

    model_path = Path(args.model)
    out_dir = Path(args.out_dir) if args.out_dir else model_path.parent / "handoff"
    out_dir.mkdir(parents=True, exist_ok=True)
    names = generate_handoff(model_path, out_dir)
    print(f"====域交接包生成====: {model_path} → {out_dir}")
    for name in names:
        print(f"  ✓ {name}")
    print(f"共 {len(names)} 件；红线：制造素材，非技能运行时依赖。")
    return 0


if __name__ == "__main__":
    if len(sys.argv) > 1:
        # 带参：命令行模式（正常用法）
        raise SystemExit(main())
    # 无参自验：对 xgimi 定稿模型生成交接包（产物落临时目录观察形态）
    import tempfile

    _demo = Path(__file__).resolve().parents[3] / "models" / "xgimi" / "model.yaml"
    if _demo.is_file():
        with tempfile.TemporaryDirectory() as _td:
            _names = generate_handoff(_demo, Path(_td))
            print("自验产物：", "、".join(_names))
    else:
        print("自验跳过：未找到 xgimi 示例模型")
