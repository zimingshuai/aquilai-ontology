"""深度逐键比对编译产物与引擎快照，生成 round-trip 验证报告（M0 POC 终验）。

主要 Input：compiled_objects / compiled_rules 两份编译产物与 snapshot_objects /
snapshot_rules 两份引擎快照（共四份 JSON）。
主要 Output：round-trip Markdown 报告（差异总数、逐条差异路径与两侧值、通过/失败结论）；
退出码 0=差异为零通过，1=存在差异失败（便于 CI 判定）。
比对口径（任务令 §5）：无豁免清单——编译产物只应含引擎格式键，多出/缺失/值不同均计差异。
"""

# 标准库导入
import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

# ===========一、常量==========
# POC_ROOT：poc/m0 目录（由脚本位置向上定位，与运行时 cwd 无关）。
POC_ROOT = Path(__file__).resolve().parent.parent
# MAX_VALUE_TEXT_LENGTH：差异明细中单侧值的最大渲染长度，超长截断保报告可读。
MAX_VALUE_TEXT_LENGTH = 120


def _render_value(value: Any) -> str:
    """把差异侧的值渲染为紧凑单行文本（超长截断）。

    Args:
        value: 任意 JSON 值（标量 / dict / list / None）。
    Returns:
        截断到 MAX_VALUE_TEXT_LENGTH 的 JSON 字符串表示（中文原样）。
    """
    # ensure_ascii=False 保持中文；单行化避免报告表格被换行撑破
    text = json.dumps(value, ensure_ascii=False)
    if len(text) > MAX_VALUE_TEXT_LENGTH:
        return text[: MAX_VALUE_TEXT_LENGTH - 3] + "..."
    return text


# ===========二、深度逐键差异收集==========
def deep_diff(compiled: Any, snapshot: Any, path: str, diffs: list[dict[str, str]]) -> None:
    """递归收集 compiled 与 snapshot 的全部深度差异（不做任何豁免或弱化）。

    Args:
        compiled: 编译产物侧的值（DSL -> 引擎格式）。
        snapshot: 引擎快照侧的值（round-trip 基准）。
        path: 当前值的定位路径（如 rules[3].logic.ALL[1].value）。
        diffs: 差异收集列表，每条含 path / compiled / snapshot 三键（值已渲染为文本）。
    Returns:
        None（结果写入 diffs）。
    """
    #   1. 类型不同即差异（bool 与 int 在 Python 中相等，须用 type() is 严格区分）
    if type(compiled) is not type(snapshot):
        diffs.append(
            {"path": path, "compiled": _render_value(compiled), "snapshot": _render_value(snapshot)}
        )
        return
    #   2. dict：键差集各记一条差异，共同键递归
    if isinstance(compiled, dict):
        for key in sorted(set(compiled) - set(snapshot)):
            diffs.append(
                {"path": f"{path}.{key}", "compiled": _render_value(compiled[key]), "snapshot": "<缺失>"}
            )
        for key in sorted(set(snapshot) - set(compiled)):
            diffs.append(
                {"path": f"{path}.{key}", "compiled": "<缺失>", "snapshot": _render_value(snapshot[key])}
            )
        for key in compiled:
            if key in snapshot:
                deep_diff(compiled[key], snapshot[key], f"{path}.{key}", diffs)
        return
    #   3. list：长度不等记一条，相等则按索引递归（顺序敏感，与任务口径一致）
    if isinstance(compiled, list):
        if len(compiled) != len(snapshot):
            diffs.append(
                {
                    "path": path,
                    "compiled": f"<长度 {len(compiled)}> {_render_value(compiled)}",
                    "snapshot": f"<长度 {len(snapshot)}> {_render_value(snapshot)}",
                }
            )
            return
        for index, (item_compiled, item_snapshot) in enumerate(zip(compiled, snapshot)):
            deep_diff(item_compiled, item_snapshot, f"{path}[{index}]", diffs)
        return
    #   4. 标量：类型已相同，值不等即差异（None / bool / str / int / float 统一覆盖）
    if compiled != snapshot:
        diffs.append(
            {"path": path, "compiled": _render_value(compiled), "snapshot": _render_value(snapshot)}
        )


# ===========三、报告渲染==========
def _render_section(title: str, diffs: list[dict[str, str]]) -> list[str]:
    """渲染报告中的一个比对章节（标题 + 差异数 + 差异表格或零差异说明）。

    Args:
        title: 章节标题（如「实体（objects）」）。
        diffs: 该章节收集到的差异列表。
    Returns:
        Markdown 行列表。
    """
    lines = [f"## {title}", "", f"差异数：**{len(diffs)}**", ""]
    if not diffs:
        lines += ["无差异，逐键完全一致。", ""]
        return lines
    lines += ["| # | 路径 | 编译产物值 | 快照值 |", "|---|---|---|---|"]
    for index, diff in enumerate(diffs, start=1):
        # 竖线转义避免破坏表格；路径中的反引号保持原样（JSON 路径不含反引号）
        safe_path = diff["path"].replace("|", "\\|")
        safe_compiled = diff["compiled"].replace("|", "\\|")
        safe_snapshot = diff["snapshot"].replace("|", "\\|")
        lines.append(f"| {index} | `{safe_path}` | {safe_compiled} | {safe_snapshot} |")
    lines.append("")
    return lines


def build_report(
    objects_diffs: list[dict[str, str]], rules_diffs: list[dict[str, str]], inputs: dict[str, str]
) -> str:
    """组装完整 round-trip Markdown 报告。

    Args:
        objects_diffs: 实体比对差异列表。
        rules_diffs: 规则比对差异列表。
        inputs: 比对输入文件路径映射（渲染到报告头部便于溯源）。
    Returns:
        完整报告文本。
    """
    total = len(objects_diffs) + len(rules_diffs)
    verdict = "通过（差异为零）" if total == 0 else f"失败（差异 {total} 处）"
    lines = [
        "# fnb 本体 DSL round-trip 比对报告",
        "",
        f"- 生成时间：{datetime.now().astimezone().isoformat(timespec='seconds')}",
        f"- 比对方向：编译产物 vs 引擎快照（深度逐键，无豁免清单）",
        f"- 编译产物：{inputs['compiled_objects']} / {inputs['compiled_rules']}",
        f"- 引擎快照：{inputs['snapshot_objects']} / {inputs['snapshot_rules']}",
        "",
        f"## 结论：{verdict}",
        "",
        f"- 实体差异：{len(objects_diffs)} 处",
        f"- 规则差异：{len(rules_diffs)} 处",
        "",
    ]
    lines += _render_section("实体（objects）", objects_diffs)
    lines += _render_section("规则（rules）", rules_diffs)
    return "\n".join(lines)


# ===========四、命令行入口==========
def main() -> None:
    """命令行入口：读四份 JSON -> 两组深度比对 -> 写报告 -> 按结果设退出码。"""
    parser = argparse.ArgumentParser(description="round-trip 深度逐键比对并生成报告")
    parser.add_argument(
        "--compiled-objects",
        default=POC_ROOT / "fnb" / "compiled_objects.json",
        help="编译产物实体 JSON 路径（默认 poc/m0/fnb/compiled_objects.json）",
    )
    parser.add_argument(
        "--snapshot-objects",
        default=POC_ROOT / "fnb" / "snapshot_objects.json",
        help="引擎快照实体 JSON 路径（默认 poc/m0/fnb/snapshot_objects.json）",
    )
    parser.add_argument(
        "--compiled-rules",
        default=POC_ROOT / "fnb" / "compiled_rules.json",
        help="编译产物规则 JSON 路径（默认 poc/m0/fnb/compiled_rules.json）",
    )
    parser.add_argument(
        "--snapshot-rules",
        default=POC_ROOT / "fnb" / "snapshot_rules.json",
        help="引擎快照规则 JSON 路径（默认 poc/m0/fnb/snapshot_rules.json）",
    )
    parser.add_argument(
        "--report",
        default=POC_ROOT / "fnb" / "roundtrip_report.md",
        help="输出的 Markdown 报告路径（默认 poc/m0/fnb/roundtrip_report.md）",
    )
    args = parser.parse_args()

    #   1. 读取四份 JSON
    compiled_objects = json.loads(Path(args.compiled_objects).read_text(encoding="utf-8"))
    snapshot_objects = json.loads(Path(args.snapshot_objects).read_text(encoding="utf-8"))
    compiled_rules = json.loads(Path(args.compiled_rules).read_text(encoding="utf-8"))
    snapshot_rules = json.loads(Path(args.snapshot_rules).read_text(encoding="utf-8"))
    #   2. 两组深度逐键比对（根路径分别标注侧别，便于差异定位）
    objects_diffs: list[dict[str, str]] = []
    rules_diffs: list[dict[str, str]] = []
    deep_diff(compiled_objects, snapshot_objects, "objects", objects_diffs)
    deep_diff(compiled_rules, snapshot_rules, "rules", rules_diffs)
    #   3. 渲染报告并落盘
    report_text = build_report(
        objects_diffs,
        rules_diffs,
        {
            "compiled_objects": str(Path(args.compiled_objects)),
            "compiled_rules": str(Path(args.compiled_rules)),
            "snapshot_objects": str(Path(args.snapshot_objects)),
            "snapshot_rules": str(Path(args.snapshot_rules)),
        },
    )
    Path(args.report).write_text(report_text, encoding="utf-8")
    #   4. 打印摘要并按结果设退出码（0=通过 1=失败，不弱化、不吞差异）
    total = len(objects_diffs) + len(rules_diffs)
    print(f"====round-trip 比对完成====: 实体差异 {len(objects_diffs)} 处，规则差异 {len(rules_diffs)} 处")
    print(f"报告: {args.report}")
    if total:
        print(f"结论: 失败（共 {total} 处差异，明细见报告）")
        raise SystemExit(1)
    print("结论: 通过（差异为零）")


if __name__ == "__main__":
    # Windows 控制台默认编码可能是 GBK，强制 UTF-8 避免中文摘要乱码
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    main()
