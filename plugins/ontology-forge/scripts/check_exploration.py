"""需求探索记录（exploration.yaml）结构校验与建模交接判定——brief-intake 收尾的确定性闸门。

用途：把口述/缺口探索的每条结论落成结构化条目后，由机器判定「结构是否合规」「必问项是否全部确认」，
     结构违规或存在必问未确认即拦截交接建模（不降级为人工目检）。
     检查项 X1-X8（全部 8 条）：X1 顶层结构、X2 维度覆盖、X3 条目必填与枚举、X4 编号唯一与格式、
     X5 状态机合法、X6 建议完整、X7 联动矩阵完整、X8 引用可解析——全部 error 级。
     公开函数 validate / handoff_verdict 与内部模块 exploration_record 的 load_record、格式常量
     供 apply_exploration_feedback.py 与 render_explore_checklist.py 复用，检查逻辑只在本模块实现一份。
主要 Input：exploration.yaml 路径（命令行位置参数）。
主要 Output：stdout 中文检查报告（首行事件 + 逐条 [Xn] 中文消息 + 交接判定 + 结论行）；
     退出码 0=结构合规且可交接建模；1=结构违规或存在阻塞项；2=文件缺失/解析失败。
"""

# 标准库导入
import argparse
import sys
from pathlib import Path
from typing import NoReturn

# 项目内部模块导入
from exploration_record import (
    ASKED_ROUNDS_MAX, BASES, DIMENSIONS, DIMENSION_STATUSES, ITEM_ID_RE, ITEM_REQUIRED_KEYS,
    KEBAB_RE, KINDS, LINKAGE_ID_RE, LINKAGE_KINDS, LINKAGE_REQUIRED_KEYS, LINKAGE_STATUSES,
    LINKAGE_VERDICTS, RECORD_FORMAT, RECORD_VERSION, REQUIRED_DIMENSIONS, STATUSES,
    UNRESOLVED_STATUSES, RecordLoadError, load_record,
)


# ===========一、检查项 X1-X8（全部 error 级）==========
def _text(value) -> bool:
    """非空字符串判定。Args: value 任意字段值。Returns: 是非空字符串返回 True。"""
    return isinstance(value, str) and value.strip() != ""


def _shown(value) -> str:
    """把任意值转成可读的中文展示文本。

    Args:
        value: 记录中的任意字段值。
    Returns:
        缺失显示「缺失」，字符串显示为「「值」」，其余显示字面量与类型名。
    """
    if value is None:
        return "缺失"
    if isinstance(value, str):
        return f"「{value}」"
    return f"{value!r}（类型 {type(value).__name__}）"


def _label(row: dict, named: str, ordinal: str) -> str:
    """生成行的定位名（有 id 用 id，否则用序号）。

    Args:
        row: 条目/维度/联动行 dict。
        named: 行的中文名（如「条目」）。
        ordinal: 无 id 时的序号说法（如「第 2 个条目」）。
    Returns:
        定位名文本。
    """
    row_id = row.get("id")
    return f"{named}「{row_id}」" if _text(row_id) else ordinal


def _numbered_items(record: dict) -> list[tuple[int, dict]]:
    """取条目映射行及其在 items 中的原始序号。

    Args:
        record: 探索记录 dict。
    Returns:
        (原始序号从 1 起, 条目 dict) 列表；items 不是列表时为空列表。
    """
    raw_items = record.get("items")
    if not isinstance(raw_items, list):
        return []
    return [(index, row) for index, row in enumerate(raw_items, 1) if isinstance(row, dict)]


def _missing(row: dict, key: str) -> str:
    """描述必填键的缺失形态。Args: row 所在行；key 键名。Returns: 「缺失」或「为空」。"""
    return "为空" if key in row else "缺失"


def _check_top(record: dict) -> list[str]:
    """X1 顶层结构：format / version / domain / updated_at。

    Args:
        record: 探索记录 dict（调用方已保证是映射）。
    Returns:
        中文违规消息列表。
    """
    messages = []
    if record.get("format") != RECORD_FORMAT:
        messages.append(f"format 必须为 {RECORD_FORMAT}，实际为{_shown(record.get('format'))}")
    # version：PyYAML 会把 yes/no 解析成布尔，须显式排除（True == 1）
    version = record.get("version")
    if isinstance(version, bool) or version != RECORD_VERSION:
        messages.append(f"version 必须为 {RECORD_VERSION}，实际为{_shown(version)}")
    domain = record.get("domain")
    if not (isinstance(domain, str) and KEBAB_RE.fullmatch(domain)):
        messages.append(f"domain 必填且须为 kebab-case（小写字母数字与单连字符分段），实际为{_shown(domain)}")
    if not _text(record.get("updated_at")):
        messages.append(f"updated_at 必填非空，实际为{_shown(record.get('updated_at'))}")
    return messages


def _check_dimensions(record: dict) -> list[str]:
    """X2 维度覆盖：8 个标准维度每个恰好一条，not_applicable 须有理由与确认人。

    Args:
        record: 探索记录 dict。
    Returns:
        中文违规消息列表。
    """
    dimensions = record.get("dimensions")
    if not isinstance(dimensions, list) or not dimensions:
        return [f"dimensions 必须是非空列表，实际为{_shown(dimensions)}"]
    messages = []
    # seen：已声明的维度 id → 出现次数（缺失与重复据此判定）。
    seen: dict[str, int] = {}
    for index, dimension in enumerate(dimensions, 1):
        if not isinstance(dimension, dict):
            messages.append(f"第 {index} 个维度不是映射（实际为{_shown(dimension)}）")
            continue
        dim_id = dimension.get("id")
        if not _text(dim_id):
            messages.append(f"第 {index} 个维度缺少 id")
            continue
        seen[dim_id] = seen.get(dim_id, 0) + 1
        label = f"维度「{dim_id}」"
        if dim_id not in DIMENSIONS:
            messages.append(f"{label}不是标准维度（标准维度为 D1-D{len(DIMENSIONS)}）")
        status = dimension.get("status")
        if status not in DIMENSION_STATUSES:
            messages.append(f"{label}的 status 非法：{_shown(status)}（只能为 {' / '.join(DIMENSION_STATUSES)}）")
            continue
        if status != "not_applicable":
            continue
        if dim_id in REQUIRED_DIMENSIONS:
            messages.append(f"{label}是必答维度，不允许 not_applicable")
            continue
        for key in ("reason", "confirmed_by"):
            if not _text(dimension.get(key)):
                messages.append(f"{label}为 not_applicable 但 {key} {_missing(dimension, key)}")
    for dim_id in DIMENSIONS:
        if seen.get(dim_id, 0) == 0:
            messages.append(f"缺少维度「{dim_id}」的覆盖声明（{len(DIMENSIONS)} 个标准维度每个恰好一条）")
        elif seen[dim_id] > 1:
            messages.append(f"维度「{dim_id}」重复声明 {seen[dim_id]} 次（每个标准维度恰好一条）")
    return messages


def _check_items(record: dict) -> list[str]:
    """X3 条目必填与枚举：必填键、维度引用、kind/basis/status 枚举、asked_rounds 取值。

    Args:
        record: 探索记录 dict。
    Returns:
        中文违规消息列表。
    """
    raw_items = record.get("items")
    if not isinstance(raw_items, list) or not raw_items:
        return [f"items 必须是非空列表，实际为{_shown(raw_items)}"]
    dimensions = record.get("dimensions")
    # declared：dimensions 段已声明的维度 id；dimensions 不是列表时不查维度引用（X2 已报，避免级联误报）
    declared = {row.get("id") for row in dimensions if isinstance(row, dict)} if isinstance(dimensions, list) else None
    messages = []
    for index, item in enumerate(raw_items, 1):
        if not isinstance(item, dict):
            messages.append(f"第 {index} 个条目不是映射（实际为{_shown(item)}）")
            continue
        label = _label(item, "条目", f"第 {index} 个条目")
        # broken：已报必填问题的键——后续维度引用与枚举检查对其跳过，同一根因只报一条
        broken: set[str] = set()
        for key in ITEM_REQUIRED_KEYS:
            value = item.get(key)
            if key == "must_ask":
                if not isinstance(value, bool):
                    broken.add(key)
                    messages.append(f"{label}的 must_ask 必须是布尔值，实际为{_shown(value)}")
            elif not _text(value):
                broken.add(key)
                detail = (_missing(item, key) if value is None or value == ""
                          else f"必须是非空字符串，实际为{_shown(value)}")
                messages.append(f"{label}的 {key} {detail}")
        # 维度引用只对通过必填检查的条目判定（缺失或非字符串已在上面报告，不级联重复）
        if "dimension" not in broken and declared is not None and item["dimension"] not in declared:
            messages.append(f"{label}的 dimension「{item['dimension']}」未在 dimensions 中声明")
        for key, allowed in (("kind", KINDS), ("basis", BASES), ("status", STATUSES)):
            if key not in broken and item.get(key) not in allowed:
                messages.append(f"{label}的 {key} 非法：{_shown(item.get(key))}（只能为 {' / '.join(allowed)}）")
        if "asked_rounds" in item:
            rounds = item["asked_rounds"]
            if isinstance(rounds, bool) or not isinstance(rounds, int) or not 0 <= rounds <= ASKED_ROUNDS_MAX:
                messages.append(f"{label}的 asked_rounds 必须是 0..{ASKED_ROUNDS_MAX} 的整数，实际为 {rounds!r}")
    return messages


def _check_ids(record: dict) -> list[str]:
    """X4 编号唯一与格式：条目 X-NNN、联动行 L-NNN。

    Args:
        record: 探索记录 dict。
    Returns:
        中文违规消息列表。
    """
    messages = []
    for key, pattern, prefix, named in (("items", ITEM_ID_RE, "X-", "条目"),
                                        ("linkage", LINKAGE_ID_RE, "L-", "联动")):
        rows = record.get(key)
        if not isinstance(rows, list):
            continue  # 段缺失已由 X3 / X7 报告
        # ids：字符串 id 列表（缺失或非字符串的 id 已由 X3 / X7 报告）。
        ids = [row.get("id") for row in rows if isinstance(row, dict) and isinstance(row.get("id"), str)]
        for row_id in dict.fromkeys(ids):
            if not pattern.fullmatch(row_id):
                messages.append(f"{named} id「{row_id}」格式非法（须为 {prefix}加三位数字，如 {prefix}001）")
            elif ids.count(row_id) > 1:
                messages.append(f"{named} id「{row_id}」重复 {ids.count(row_id)} 次（编号域内唯一、不复用）")
    return messages


def _check_state_machine(record: dict) -> list[str]:
    """X5 状态机合法：确认留痕、否决留痕、未决有原因与明确建议。

    Args:
        record: 探索记录 dict。
    Returns:
        中文违规消息列表。
    """
    messages = []
    for index, item in _numbered_items(record):
        label = _label(item, "条目", f"第 {index} 个条目")
        status, basis = item.get("status"), item.get("basis")
        has_resolution = _text(item.get("resolution"))
        if status == "confirmed" and basis == "inferred" and not has_resolution:
            messages.append(f"{label}已确认且来自 AI 建议（basis=inferred），resolution 须留痕")
        if status == "rejected" and not has_resolution:
            messages.append(f"{label}已否决，resolution 须留痕（原文保留）")
        if status == "pending":
            if not _text(item.get("pending_reason")):
                messages.append(f"{label}为 pending，pending_reason 须非空")
            if basis == "inferred" and not _text(item.get("proposal")):
                messages.append(f"{label}为 pending 且来自 AI 建议，proposal 须非空（未决也必须留明确建议）")
    return messages


def _check_rationale(record: dict) -> list[str]:
    """X6 建议完整：AI 建议与未定案条目必须带理由。

    Args:
        record: 探索记录 dict。
    Returns:
        中文违规消息列表。
    """
    messages = []
    for index, item in _numbered_items(record):
        if (item.get("basis") == "inferred" or item.get("status") in UNRESOLVED_STATUSES) \
                and not _text(item.get("rationale")):
            messages.append(f"{_label(item, '条目', f'第 {index} 个条目')}的 rationale 须非空"
                            "（basis=inferred 或 status 为 proposed/pending 时必填）")
    return messages


def _check_linkage(record: dict) -> list[str]:
    """X7 联动矩阵完整：行必填、来源可解析、动作/触发逐条判定、linkage 行三要素齐备。

    Args:
        record: 探索记录 dict。
    Returns:
        中文违规消息列表。
    """
    linkage = record.get("linkage")
    if not isinstance(linkage, list):
        return [f"linkage 必须是列表（无动作/触发联动时写空列表 linkage: []），实际为{_shown(linkage)}"]
    # items_valid：items 段是否为列表（不是则 X3 已报，跳过跨段检查以免级联误报）。
    items_valid = isinstance(record.get("items"), list)
    items = _numbered_items(record)
    # item_ids：条目 id 集合；judged：已在联动矩阵中作为 source_item 出现过的条目 id。
    item_ids = {item["id"] for _, item in items if isinstance(item.get("id"), str)}
    judged: set[str] = set()
    messages = []
    for index, row in enumerate(linkage, 1):
        if not isinstance(row, dict):
            messages.append(f"第 {index} 行联动不是映射（实际为{_shown(row)}）")
            continue
        label = _label(row, "联动", f"第 {index} 行联动")
        for key in LINKAGE_REQUIRED_KEYS:
            if not _text(row.get(key)):
                messages.append(f"{label}的 {key} {_missing(row, key)}")
        if _text(row.get("source_item")):
            if row["source_item"] in item_ids:
                judged.add(row["source_item"])
            elif items_valid:
                messages.append(f"{label}的 source_item「{row['source_item']}」指向不存在的条目")
        if row.get("verdict") not in LINKAGE_VERDICTS:
            messages.append(f"{label}的 verdict 非法：{_shown(row.get('verdict'))}"
                            f"（只能为 {' / '.join(LINKAGE_VERDICTS)}）")
        elif row["verdict"] == "linkage":
            for key in ("target_object", "on_failure"):
                if not _text(row.get(key)):
                    messages.append(f"{label}为 linkage 但 {key} {_missing(row, key)}")
            if not isinstance(row.get("rule_mediated"), bool):
                messages.append(f"{label}为 linkage 但 rule_mediated 必须是布尔值，"
                                f"实际为{_shown(row.get('rule_mediated'))}")
        if row.get("status") not in LINKAGE_STATUSES:
            messages.append(f"{label}的 status 非法：{_shown(row.get('status'))}"
                            f"（只能为 {' / '.join(LINKAGE_STATUSES)}）")
    for index, item in items:
        # 动作/触发条目的覆盖判定：先判 id 是字符串再做集合成员测试（不可哈希值不能进 set 查找）
        if item.get("kind") in LINKAGE_KINDS and not (isinstance(item.get("id"), str) and item["id"] in judged):
            messages.append(f"{_label(item, '条目', f'第 {index} 个条目')}（kind={item.get('kind')}）"
                            "未在 linkage 中作为 source_item 出现（每个动作都须判定过是否联动）")
    # actors：全部动作/触发条目（没有任何一条时联动矩阵应为空）。
    actors = [item for _, item in items if item.get("kind") in LINKAGE_KINDS]
    if not actors and linkage:
        messages.append(f"没有任何 action/trigger 条目，linkage 应为空列表（实际 {len(linkage)} 行）")
    return messages


def _check_refs(record: dict) -> list[str]:
    """X8 引用可解析：refs 中以 X- 开头的编号必须指向存在的条目。

    Args:
        record: 探索记录 dict。
    Returns:
        中文违规消息列表。
    """
    items = _numbered_items(record)
    # item_ids：条目 id 集合。
    item_ids = {item["id"] for _, item in items if isinstance(item.get("id"), str)}
    messages = []
    for index, item in items:
        if "refs" not in item:
            continue
        label = _label(item, "条目", f"第 {index} 个条目")
        refs = item["refs"]
        if not isinstance(refs, list):
            messages.append(f"{label}的 refs 必须是列表，实际为{_shown(refs)}")
            continue
        for ref in refs:
            if not isinstance(ref, str):
                messages.append(f"{label}的 refs 含非字符串元素 {_shown(ref)}")
            elif ref.startswith("X-") and ref not in item_ids:
                messages.append(f"{label}的 refs「{ref}」指向不存在的条目")
    return messages


# _CHECKS：检查项注册表（编号 → 检查函数），顺序即报告顺序；条数须与模块 docstring「全部 N 条」一致。
_CHECKS = (
    ("X1", _check_top), ("X2", _check_dimensions), ("X3", _check_items), ("X4", _check_ids),
    ("X5", _check_state_machine), ("X6", _check_rationale), ("X7", _check_linkage), ("X8", _check_refs),
)
# CHECK_COUNT：检查项条数——必须与模块 docstring 的「全部 N 条」一致（文档口径联动断言的事实源）。
CHECK_COUNT = len(_CHECKS)


# ===========二、校验聚合与交接判定==========
def validate(record: dict) -> list[tuple[str, str]]:
    """执行 X1-X8 全部检查项。

    Args:
        record: load_record 的返回值（顶层不是映射时只报 X1，其余检查无从展开）。
    Returns:
        (检查项编号, 中文消息) 列表，按检查项顺序与出现顺序排列；空列表表示结构合规。
    """
    if not isinstance(record, dict):
        return [("X1", f"顶层必须是映射，实际为{_shown(record)}")]
    return [(code, message) for code, check in _CHECKS for message in check(record)]


def handoff_verdict(record: dict) -> dict:
    """计算建模交接判定（须在 validate 零违规后调用）。

    Args:
        record: 结构合规的探索记录 dict。
    Returns:
        total 条目总数；status_counts 各状态条数；linkage_count 联动矩阵行数；
        blocked 阻塞清单（must_ask=true 且未定案）的 id 列表；hint 提示清单（其余未定案）的 id 列表；
        handoff 是否可交接建模（阻塞清单为空）。
    """
    items = record["items"]
    # unresolved：未定案条目（按出现顺序）。
    unresolved = [item for item in items if item["status"] in UNRESOLVED_STATUSES]
    counts = {status: 0 for status in STATUSES}
    for item in items:
        counts[item["status"]] += 1
    return {
        "total": len(items),
        "status_counts": counts,
        "linkage_count": len(record["linkage"]),
        "blocked": [item["id"] for item in unresolved if item["must_ask"]],
        "hint": [item["id"] for item in unresolved if not item["must_ask"]],
        "handoff": not any(item["must_ask"] for item in unresolved),
    }


# ===========三、报告渲染与命令行入口==========
def structure_line(error_count: int) -> str:
    """生成「结构违规」结论行。Args: error_count 结构违规条数。Returns: 结论行文本。"""
    return f"====探索记录结构违规====: {error_count} 条"


def handoff_lines(record: dict) -> list[str]:
    """生成交接判定段与结论行。

    Args:
        record: 探索记录 dict（须先确认 validate 零违规）。
    Returns:
        自「====交接判定====」起至三选一结论行的文本行列表。
    """
    verdict = handoff_verdict(record)
    counts = verdict["status_counts"]
    blocked, hint = verdict["blocked"], verdict["hint"]
    conclusion = ("====探索记录可交接建模====" if verdict["handoff"] else
                  f"====探索记录不可交接====: 必问项未确认 {len(blocked)} 条，须挂 Charter 一并呈审收口")
    return [
        "====交接判定====",
        f"条目总数：{verdict['total']}",
        f"状态计数：{'｜'.join(f'{status} {counts[status]}' for status in STATUSES)}",
        f"联动矩阵行数：{verdict['linkage_count']}",
        f"阻塞清单（必问未确认 {len(blocked)} 条）：{'、'.join(blocked) or '无'}",
        f"提示清单（非必问未确认 {len(hint)} 条）：{'、'.join(hint) or '无'}",
        conclusion,
    ]


def render_report(path: Path, record: dict, problems: list[tuple[str, str]]) -> str:
    """渲染完整检查报告（结构违规时只列违规与结论，不计算交接判定）。

    Args:
        path: 被检查的探索记录路径（取文件名用于首行）。
        record: 探索记录 dict。
        problems: validate 的返回值。
    Returns:
        多行报告文本。
    """
    lines = [f"====探索记录检查====: {path.name}"]
    lines += [f"[{code}] {message}" for code, message in problems]
    if problems:
        lines.append(structure_line(len(problems)))
    else:
        lines += handoff_lines(record)
    return "\n".join(lines)


class _Parser(argparse.ArgumentParser):
    """参数错误时输出中文事件行并以退出码 2 结束的解析器。"""

    def error(self, message: str) -> NoReturn:
        """覆盖默认的英文报错。

        Args:
            message: argparse 生成的错误说明。
        Returns:
            不返回（退出码 2）。
        """
        self.print_usage(sys.stderr)
        print(f"====参数错误====: {message}", file=sys.stderr)
        sys.exit(2)


def build_parser(description: str) -> argparse.ArgumentParser:
    """创建探索脚本共用的参数解析器（参数错误时中文事件行报错并以退出码 2 结束）。

    Args:
        description: 命令行说明（中文，显示在帮助里）。
    Returns:
        待调用方 add_argument 的解析器实例。
    """
    return _Parser(description=description)


def main() -> int:
    """命令行入口：加载 → 校验 → 交接判定 → 报告与退出码。

    Args:
        无（参数经 argparse 解析：source 为探索记录路径）。
    Returns:
        进程退出码：0=可交接建模；1=结构违规或存在阻塞项；2=文件缺失/解析失败。
    """
    parser = build_parser("需求探索记录结构校验与建模交接判定")
    parser.add_argument("source", type=Path, help="exploration.yaml 路径")
    args = parser.parse_args()
    try:
        record = load_record(args.source)
    except RecordLoadError as exc:
        print(f"====探索记录检查====: {args.source.name}")
        print(f"====探索记录读取失败====: {exc}")
        return 2
    problems = validate(record)
    print(render_report(args.source, record, problems))
    if problems:
        return 1
    return 0 if handoff_verdict(record)["handoff"] else 1


if __name__ == "__main__":
    # CLI 脚本本体即调试入口：python check_exploration.py <exploration.yaml>。
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    sys.exit(main())
