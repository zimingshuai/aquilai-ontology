"""探索记录批复应用：把勾选组件生成的批复文本确定性地应用到 exploration.yaml。

用途：用户在探索确认清单（render_explore_checklist.py 产出的勾选页面）里批复后，把批复文本回贴给
     agent；此前 agent 手改 YAML 状态易错（漏留痕、改错字段、改一半），本脚本把四种批复动作固化为
     确定性迁移，并先全校验后写入——任一行无效则原文件字节不变。
     四种批复动作：按建议（confirmed）/ 改为（confirmed 并替换陈述）/ 否决（rejected）/
     选备选（confirmed 并取该条 options 的对应项）。
     已确认条目的更正通道（与探索手册状态机一致）：confirmed 可经「改为 / 否决 / 选备选」再次批复
     ——statement 随动作更新、resolution 追加留痕不覆盖；「按建议」仅用于未定案条目，
     rejected 是终态不可再批复。
主要 Input：exploration.yaml（位置参数）；--feedback 批复文本文件（每行一条
     「<编号> <符号> <动作词>[:<备注>]」，符号仅人读、解析以动作词为准）；--by 确认人。
主要 Output：原地写回 exploration.yaml（updated_at 更新、首行加状态注释、未涉及条目原样保留）；
     stdout 应用摘要与复检结论行；退出码 0=已应用；1=批复无效（未写文件）；2=输入文件缺失/解析失败。
     复检的「可交接/不可交接」只输出文本，不改退出码。
"""

# 标准库导入
import argparse
import datetime
import os
import re
import sys
from pathlib import Path

# 第三方依赖导入
import yaml

# 项目内部模块导入
from check_exploration import build_parser, handoff_lines, structure_line, validate
from exploration_record import (
    TIME_FORMAT, UNRESOLVED_STATUSES, RecordLoadError, load_record, read_text_file,
)


# ===========一、批复解析==========
# LINE_RE：批复行解析正则——编号、可选符号（仅人读）、动作词（按建议/改为/否决/选备选X）、冒号引导的备注。
LINE_RE = re.compile(
    r"^(?P<item_id>X-\d{3})\s+(?:\S+\s+)?"
    r"(?P<verb>按建议|改为|否决|选备选(?P<letter>[A-Z]))"
    r"(?:\s*[:：]\s*(?P<payload>.*))?\s*$"
)
# DUMP_WIDTH：YAML 回写的行宽上限（取大值避免长句在空格处折行；只影响排版，不影响数据）。
DUMP_WIDTH = 4096
# RESOLUTION_SEPARATOR：resolution 中多条裁决留痕之间的分隔符。
RESOLUTION_SEPARATOR = "｜"


def parse_feedback(text: str, record: dict) -> tuple[list[dict], list[str]]:
    """解析批复文本并逐行校验可应用性（不修改 record）。

    Args:
        text: 批复文本全文（每行一条，空行跳过）。
        record: 结构合规的探索记录 dict（调用方须先确认 validate 零违规）。
    Returns:
        (动作列表, 问题列表)。动作元素含 item_id / verb / payload / choice / option_index；
        问题元素为带行号的中文说明，非空时调用方必须拒绝整批写入。
    """
    # items：条目 id → 条目。
    items = {item["id"]: item for item in record["items"]}
    actions: list[dict] = []
    problems: list[str] = []
    for line_no, raw_line in enumerate(text.splitlines(), 1):
        line = raw_line.strip()
        if not line:
            continue
        match = LINE_RE.match(line)
        if not match:
            problems.append(f"第 {line_no} 行无法识别（须为「<编号> <符号> <动作词>[:<备注>]」）：{line}")
            continue
        # verb：归一化后的动作词（选备选X 归为「选备选」，序号字母另存 choice）。
        verb = "选备选" if match["letter"] else match["verb"]
        item_id = match["item_id"]
        # payload：冒号后的备注/文本（改为的必填文本、否决的备注、选备选的回显原文）。
        payload = (match["payload"] or "").strip()
        if item_id not in items:
            problems.append(f"第 {line_no} 行：条目「{item_id}」不存在")
            continue
        item = items[item_id]
        # 状态准入：rejected 终态不可再批复；confirmed 仅开放「改为 / 否决 / 选备选」更正通道
        #（手册状态机：confirmed 可被后续批复改写、resolution 追加留痕），「按建议」只对未定案条目有意义。
        if item["status"] == "rejected":
            problems.append(f"第 {line_no} 行：条目「{item_id}」已否决（终态），不可再批复")
            continue
        if item["status"] == "confirmed" and match["verb"] == "按建议":
            problems.append(f"第 {line_no} 行：条目「{item_id}」已确认，「按建议」仅用于未定案条目；"
                            "如需更正请用「改为」或「否决」")
            continue
        if any(action["item_id"] == item_id for action in actions):
            problems.append(f"第 {line_no} 行：条目「{item_id}」重复批复（同一编号只能有一条批复）")
            continue
        if verb == "改为" and not payload:
            problems.append(f"第 {line_no} 行：条目「{item_id}」的「改为」缺文本")
            continue
        if verb == "按建议" and item["status"] == "pending" and not str(item.get("proposal") or "").strip():
            problems.append(f"第 {line_no} 行：条目「{item_id}」为 pending 但没有 AI 建议答案（proposal），"
                            "无法按建议——请改用「改为」或「否决」")
            continue
        # choice / option_index：选备选的序号字母与下标（A 对应 0）；其它动作分别为空串与 -1。
        choice, option_index = match["letter"], -1
        if verb == "选备选":
            option_index = ord(choice) - ord("A")
            options = item["options"] if isinstance(item.get("options"), list) else []
            if not 0 <= option_index < len(options):
                problems.append(f"第 {line_no} 行：条目「{item_id}」不存在备选{choice}"
                                f"（该条备选共 {len(options)} 个）")
                continue
        actions.append({"item_id": item_id, "verb": verb, "payload": payload,
                        "choice": choice, "option_index": option_index})
    return actions, problems


# ===========二、批复应用与写回==========
def _append_resolution(item: dict, text: str) -> None:
    """在条目 resolution 末尾追加一条裁决留痕。

    Args:
        item: 条目 dict（就地修改）。
        text: 本次留痕文本。
    Returns:
        None。
    """
    history = str(item.get("resolution") or "").strip()
    item["resolution"] = f"{history}{RESOLUTION_SEPARATOR}{text}" if history else text


def apply_actions(record: dict, actions: list[dict], by: str, now: str) -> list[str]:
    """把批复动作应用到记录（就地修改条目的 status / statement / resolution）。

    Args:
        record: 探索记录 dict（结构合规）。
        actions: parse_feedback 返回的动作列表（已校验可应用）。
        by: 确认人（写入留痕）。
        now: 当前时间文本。
    Returns:
        每条动作的应用摘要行。
    """
    items = {item["id"]: item for item in record["items"]}
    summaries: list[str] = []
    for action in actions:
        item = items[action["item_id"]]
        # before / statement_before：迁移前的状态与陈述（摘要与留痕用）。
        before, statement_before = item["status"], item["statement"]
        verb, payload = action["verb"], action["payload"]
        # stamp / after：留痕前缀与迁移后的状态。
        stamp, after = f"[{now}] {by}：", "rejected" if verb == "否决" else "confirmed"
        if verb == "按建议":
            if before == "pending":
                item["statement"] = item["proposal"]
                _append_resolution(item, f"原陈述：{statement_before}")
            _append_resolution(item, f"{stamp}按 AI 建议确认" + (f"（{payload}）" if payload else ""))
        elif verb == "改为":
            item["statement"] = payload
            _append_resolution(item, f"{stamp}改为「{payload}」（原陈述：{statement_before}）")
        elif verb == "否决":
            # 否决备注可空：无备注时留痕不带空括号
            _append_resolution(item, f"{stamp}否决" + (f"（{payload}）" if payload else ""))
        else:
            content = item["options"][action["option_index"]]
            item["statement"] = content
            _append_resolution(item, f"{stamp}选备选{action['choice']}（{content}）")
        item["status"] = after
        summaries.append(f"{item['id']} {verb}{action['choice'] if verb == '选备选' else ''}：{before} → {after}")
    return summaries


def write_back(path: Path, record: dict, by: str, now: str) -> None:
    """把应用后的记录写回文件（先写同目录临时文件，再原子替换目标文件）。

    Args:
        path: exploration.yaml 路径。
        record: 已应用批复的记录（就地更新 updated_at）。
        by: 确认人。
        now: 当前时间文本。
    Raises:
        OSError: 临时文件写入或替换失败（临时文件会被清理）。
    """
    record["updated_at"] = now
    header = (f"# {record['domain']} 探索记录 v{record['version']}\n"
              f"# 状态：{Path(__file__).name} 于 {now} 应用批复（确认人：{by}）\n")
    body = yaml.safe_dump(record, allow_unicode=True, sort_keys=False, width=DUMP_WIDTH)
    # tmp_path：同目录临时文件（与目标同盘，os.replace 才能原子替换）。
    tmp_path = path.with_name(f"{path.name}.tmp")
    try:
        tmp_path.write_text(header + body, encoding="utf-8", newline="\n")
        os.replace(tmp_path, path)
    finally:
        tmp_path.unlink(missing_ok=True)


def recheck(path: Path) -> list[str]:
    """重新加载写回的文件并复检（复用 check_exploration 的校验与结论行）。

    Args:
        path: 已写回的 exploration.yaml 路径。
    Returns:
        结构违规行，或交接判定段与结论行。
    Raises:
        RecordLoadError: 写回后的文件无法读取或解析。
    """
    record = load_record(path)
    problems = validate(record)
    if problems:
        return [f"[{code}] {message}" for code, message in problems] + [structure_line(len(problems))]
    return handoff_lines(record)


# ===========三、模块入口==========
def main() -> int:
    """命令行入口：加载 → 结构校验 → 批复全量校验 → 应用 → 写回 → 复检。

    Args:
        无（参数经 argparse 解析：source / --feedback / --by）。
    Returns:
        进程退出码：0=已应用；1=批复无效或探索记录结构违规（均未写文件）；2=输入文件缺失/解析失败。
    """
    parser = build_parser("把探索批复文本确定性地应用到 exploration.yaml")
    parser.add_argument("source", type=Path, help="exploration.yaml 路径（原地写回）")
    parser.add_argument("--feedback", type=Path, required=True, help="批复文本文件（勾选组件生成，每行一条）")
    parser.add_argument("--by", required=True, help="确认人（写入 resolution 留痕与文件头注）")
    args = parser.parse_args()
    if not args.by.strip():
        print("====参数错误====: --by 确认人不能为空", file=sys.stderr)
        return 2
    try:
        record = load_record(args.source)
        feedback_text = read_text_file(args.feedback, "批复文本")
    except RecordLoadError as exc:
        print(f"====批复应用失败====: {exc}")
        return 2
    print(f"====批复应用====: {args.source.name}（确认人：{args.by}）")
    problems = validate(record)
    if problems:
        for code, message in problems:
            print(f"[{code}] {message}")
        print(structure_line(len(problems)))
        print("探索记录结构违规，不应用批复（原文件未改动）")
        return 1
    actions, problems = parse_feedback(feedback_text, record)
    # 原子性：任一行有问题（即使其余行有效）或没有任何有效批复行，一律不写文件
    if problems or not actions:
        detail = (f"共 {len(problems)} 处问题，未写入任何改动（{args.source.name} 字节不变）"
                  if problems else "批复文本中没有有效批复行，未写入任何改动")
        print(f"====批复校验失败====: {detail}")
        for number, problem in enumerate(problems, 1):
            print(f"  {number}. {problem}")
        return 1
    # now：本次应用的统一时间戳（留痕与 updated_at 同刻）。
    now = datetime.datetime.now().strftime(TIME_FORMAT)
    for summary in apply_actions(record, actions, args.by, now):
        print(summary)
    try:
        write_back(args.source, record, args.by, now)
    except OSError as exc:
        print(f"====批复写入失败====: {exc}")
        return 1
    print(f"====批复应用完成====: {args.source}（已应用 {len(actions)} 条批复）")
    print("====复检====")
    try:
        for line in recheck(args.source):
            print(line)
    except RecordLoadError as exc:
        print(f"====复检失败====: 写回后的探索记录无法读取——{exc}")
        return 1
    return 0


if __name__ == "__main__":
    # CLI 脚本本体即调试入口：python apply_exploration_feedback.py <exploration.yaml> --feedback <批复文本> --by <确认人>。
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    sys.exit(main())
