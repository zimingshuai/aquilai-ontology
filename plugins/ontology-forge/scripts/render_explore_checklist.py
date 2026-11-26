"""探索确认清单生成：把 exploration.yaml 的未定案条目代入模板产出自包含勾选 HTML。

用途：brief-intake 收尾的结构化探索记录（exploration.yaml）中，AI 建议与未决条目须经业务方逐条确认；
     本脚本把结构校验通过的记录按 8 个标准维度分组（组内必问项在前），只把未定案条目
     （proposed / pending）做成可勾选卡片，已定案条目放进折叠区供核对——任何宿主行为一致。
主要 Input：exploration.yaml 路径（位置参数，须结构合规）；可选 -o 输出 HTML 路径
     （默认来源同目录 explore-checklist.html）；可选 --domain 域名（默认来源文件父目录的上一级目录名）。
主要 Output：自包含 explore-checklist.html（三态勾选 + 选备选 + 一键生成批复文本）；
     stdout 中文结果行；退出码 0=成功，1=结构违规或模板/输出异常（不产出文件），2=文件缺失/解析失败。
"""

# 标准库导入
import datetime
import html
import json
import re
import sys
from pathlib import Path

# 项目内部模块导入
from check_exploration import build_parser, handoff_verdict, render_report, validate
from exploration_record import DIMENSIONS, TIME_FORMAT, UNRESOLVED_STATUSES, RecordLoadError, load_record

# PLUGIN_ROOT：插件根目录（scripts/ 的上一级）
PLUGIN_ROOT = Path(__file__).resolve().parent.parent
# TEMPLATE_PATH：探索确认清单模板
TEMPLATE_PATH = PLUGIN_ROOT / "assets" / "explore-checklist.html"
# PLACEHOLDERS：模板三个占位符（逐项预检存在性，防模板漂移产出坏件）
PLACEHOLDERS = ("__DOMAIN__", "__GENERATED_AT__", "__ITEM_DATA__")
# PLACEHOLDER_RE：占位符单遍替换正则（替换值不会被再次替换）
PLACEHOLDER_RE = re.compile(r"__(?:DOMAIN|GENERATED_AT|ITEM_DATA)__")
# UNSAFE_JSON_CHARS：注入数据里必须转义的字符及其 JSON 转义形式——尖括号与 & 全量转义，
# 一并消除 `</script>`（规格要求把 `</` 转义）、`<!--`、`-->`、`<script` 等可改写页面结构的序列
UNSAFE_JSON_CHARS = {"<": "\\u003c", ">": "\\u003e", "&": "\\u0026", "\u2028": "\\u2028", "\u2029": "\\u2029"}
# DEFAULT_OUTPUT_NAME：默认输出文件名（与来源文件同目录）
DEFAULT_OUTPUT_NAME = "explore-checklist.html"


# ===========一、页面数据构建==========
def build_page_data(record: dict) -> dict:
    """把结构合规的探索记录整理成页面数据模型（按标准维度顺序分组，组内必问项在前）。

    Args:
        record: 结构合规的探索记录 dict。
    Returns:
        含 domain / updated_at / interviewee 与 groups 的 dict；每个分组含 id、name、
        not_applicable（不适用说明，适用时为空串）、cards（未定案条目）、settled（已定案条目）。
    """
    # grouped：维度 id → 该维度下的条目（保持记录中的先后顺序）。
    grouped: dict[str, list[dict]] = {}
    for item in record["items"]:
        grouped.setdefault(item["dimension"], []).append(item)
    # dimension_by_id：维度 id → 覆盖声明。
    dimension_by_id = {dimension["id"]: dimension for dimension in record["dimensions"]}
    groups = []
    for dim_id, name in DIMENSIONS.items():
        # members：该维度下的全部条目；cards：其中的未定案条目（稳定排序：必问项在前）。
        members = grouped.get(dim_id, [])
        cards = sorted((item for item in members if item["status"] in UNRESOLVED_STATUSES),
                       key=lambda item: not item["must_ask"])
        settled = [item for item in members if item["status"] not in UNRESOLVED_STATUSES]
        dimension = dimension_by_id[dim_id]
        # not_applicable：维度判为不适用时的说明（理由与确认人）。
        not_applicable = ""
        if dimension["status"] == "not_applicable":
            not_applicable = f"{dimension['reason']}（确认人：{dimension['confirmed_by']}）"
        if cards or settled or not_applicable:
            groups.append({"id": dim_id, "name": name, "not_applicable": not_applicable,
                           "cards": cards, "settled": settled})
    return {"domain": record["domain"], "updated_at": record["updated_at"],
            "interviewee": record.get("interviewee") or "", "groups": groups}


# ===========二、模板代入==========
def _safe_json(payload) -> str:
    r"""序列化为可直接嵌入 <script> 的单行 JSON 文本（防止数据改写页面结构或提前闭合脚本/注释）。

    Args:
        payload: 页面数据模型。
    Returns:
        单行 JSON 文本：`<` `>` `&` 与行/段分隔符 U+2028/U+2029 一律转义为 `\uXXXX`——
        覆盖 `</script>`、`<!--`、`-->` 等序列；JS 求值后还原为原字符，数据不变。
    """
    text = json.dumps(payload, ensure_ascii=False)
    return text.translate(str.maketrans(UNSAFE_JSON_CHARS))


def render(page_data: dict, domain: str) -> str:
    """把页面数据代入模板，返回完整 HTML 文本。

    Args:
        page_data: build_page_data 的产物。
        domain: 域名（标题展示用）。
    Returns:
        占位符全部替换后的自包含 HTML 文本。
    Raises:
        RuntimeError: 模板缺失或占位符不在模板中（模板被改动导致坏件）。
    """
    if not TEMPLATE_PATH.is_file():
        raise RuntimeError(f"模板缺失: {TEMPLATE_PATH}")
    template = TEMPLATE_PATH.read_text(encoding="utf-8")
    # replacements：三个占位符的替换对。域名代入的是 HTML 文本位置，须转义以防改写页面结构；
    # 页面数据代入的是 <script> 内，由 _safe_json 防注入。
    replacements = {
        "__DOMAIN__": html.escape(domain),
        "__GENERATED_AT__": datetime.datetime.now().strftime(TIME_FORMAT),
        "__ITEM_DATA__": _safe_json(page_data),
    }
    for holder in PLACEHOLDERS:
        if holder not in template:
            raise RuntimeError(f"模板缺占位符 {holder}——assets/explore-checklist.html 被改动，请对照门禁修复")
    return PLACEHOLDER_RE.sub(lambda match: replacements[match.group(0)], template)


# ===========三、模块入口==========
def main() -> int:
    """命令行入口：加载 → 校验 → 构建页面数据 → 代入模板 → 落盘。

    Args:
        无（参数经 argparse 解析：source 必填，-o 输出路径与 --domain 域名可选）。
    Returns:
        进程退出码：0=成功；1=结构违规或模板/输出异常；2=文件缺失/解析失败。
    """
    parser = build_parser("把探索记录的未定案条目代入模板生成勾选呈审 HTML")
    parser.add_argument("source", type=Path, help="exploration.yaml 路径（须结构合规）")
    parser.add_argument("-o", "--out", type=Path, default=None,
                        help=f"输出 HTML 路径（默认来源同目录 {DEFAULT_OUTPUT_NAME}）")
    parser.add_argument("--domain", default=None, help="域名（默认取探索记录内的 domain 字段）")
    args = parser.parse_args()
    try:
        record = load_record(args.source)
    except RecordLoadError as exc:
        print(f"====探索确认清单生成失败====: {exc}")
        return 2
    problems = validate(record)
    if problems:
        print(render_report(args.source, record, problems))
        print("探索记录结构违规：不产出呈审页面")
        return 1
    # source_dir：来源文件所在目录（默认输出位置）；domain 优先级：--domain > 记录内 domain（结构合规时必有）。
    source_dir = args.source.resolve().parent
    domain = args.domain or record["domain"]
    try:
        # html_text：代入后的完整页面文本。
        html_text = render(build_page_data(record), domain)
        out_path = args.out or source_dir / DEFAULT_OUTPUT_NAME
        out_path.write_text(html_text, encoding="utf-8", newline="\n")
    except (RuntimeError, OSError) as exc:
        print(f"====探索确认清单生成失败====: {exc}")
        return 1
    verdict = handoff_verdict(record)
    # pending_count：待确认条目数（阻塞 + 提示）。
    pending_count = len(verdict["blocked"]) + len(verdict["hint"])
    print(f"====探索确认清单生成完成====: {out_path}（待确认 {pending_count} 条，"
          f"其中必问 {len(verdict['blocked'])} 条；已定案 {verdict['total'] - pending_count} 条，域 {domain}）")
    print("使用方式：浏览器打开逐条勾选 → 生成批复 → 复制文本回贴，由 apply_exploration_feedback.py 应用")
    return 0


if __name__ == "__main__":
    # CLI 脚本本体即调试入口：python render_explore_checklist.py <exploration.yaml> [-o out.html] [--domain 域名]。
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    sys.exit(main())
