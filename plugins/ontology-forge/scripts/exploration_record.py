"""需求探索记录（exploration.yaml v1）格式常量与加载器——探索侧三个脚本的共用底座。

用途：集中定义 exploration.yaml v1 的格式常量（标准维度、条目/联动枚举、编号格式、时间格式），
     并提供带重复键检测的加载器；check_exploration.py、apply_exploration_feedback.py、
     render_explore_checklist.py 一律从本模块取常量，不各自复制口径。
主要 Input：exploration.yaml 或批复文本文件的路径。
主要 Output：load_record 返回解析后的记录 dict，read_text_file 返回 UTF-8 文本；
     文件缺失、编码错误、YAML 语法错误、重复键一律抛 RecordLoadError（不吞异常、不用空数据继续）。
"""

# 标准库导入
import re
from pathlib import Path

# 第三方依赖导入
import yaml


# ===========一、格式常量（exploration.yaml v1 的唯一事实源）==========
# RECORD_FORMAT / RECORD_VERSION：顶层 format 与 version 的唯一合法值。
RECORD_FORMAT = "exploration-record"
RECORD_VERSION = 1
# DIMENSIONS：8 个标准维度（id → 名称），书写顺序即探索顺序。
DIMENSIONS = {
    "D1": "总体理解与范围",
    "D2": "业务对象、属性与关系",
    "D3": "状态与生命周期",
    "D4": "动作",
    "D5": "触发与联动",
    "D6": "计算口径与校验",
    "D7": "数据源与既有系统",
    "D8": "能力问题",
}
# REQUIRED_DIMENSIONS：必答维度（范围与能力问题不允许 not_applicable）。
REQUIRED_DIMENSIONS = ("D1", "D8")
# DIMENSION_STATUSES：维度覆盖状态（covered=有结论；not_applicable=不适用）。
DIMENSION_STATUSES = ("covered", "not_applicable")
# KINDS：条目结论类型枚举（property 为属性级结论：类型/计量单位/枚举取值/可空含义/维护方）。
KINDS = ("scope", "object", "property", "relation", "state", "action", "trigger",
         "rule", "constraint", "function", "query")
# LINKAGE_KINDS：必须在联动矩阵中判定过的条目类型（每个动作都须判定过是否联动）。
LINKAGE_KINDS = ("action", "trigger")
# BASES：结论依据（stated=用户/资料明示；inferred=AI 建议）。
BASES = ("stated", "inferred")
# STATUSES：条目状态；UNRESOLVED_STATUSES：其中的未定案状态（呈审勾选与阻塞/提示清单的判定范围）。
STATUSES = ("confirmed", "proposed", "pending", "rejected")
UNRESOLVED_STATUSES = ("proposed", "pending")
# ITEM_REQUIRED_KEYS：条目必填键。
ITEM_REQUIRED_KEYS = ("id", "dimension", "kind", "statement", "basis", "must_ask", "status", "source")
# LINKAGE_REQUIRED_KEYS：联动行必填键。
LINKAGE_REQUIRED_KEYS = ("id", "source_item", "verdict", "reason", "status")
# LINKAGE_VERDICTS / LINKAGE_STATUSES：联动判定结论与联动行状态枚举。
LINKAGE_VERDICTS = ("linkage", "none")
LINKAGE_STATUSES = ("confirmed", "proposed", "pending")
# ASKED_ROUNDS_MAX：asked_rounds 合法上限（0..2）。
ASKED_ROUNDS_MAX = 2
# ITEM_ID_RE / LINKAGE_ID_RE：条目与联动行编号格式。
ITEM_ID_RE = re.compile(r"^X-\d{3}$")
LINKAGE_ID_RE = re.compile(r"^L-\d{3}$")
# KEBAB_RE：domain 的 kebab-case 格式（小写字母数字 + 单连字符分段）。
KEBAB_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
# TIME_FORMAT：updated_at 与裁决留痕时间戳的格式。
TIME_FORMAT = "%Y-%m-%d %H:%M:%S"


# ===========二、记录加载==========
class RecordLoadError(Exception):
    """探索记录或批复文本读取失败（文件缺失、编码错误、YAML 语法错误、重复键）。

    Input:
        message: 中文失败原因。
    Return:
        由命令行入口捕获后以退出码 2 报告，不吞异常、不用空数据继续。
    """


class _StrictLoader(yaml.SafeLoader):
    """带重复键检测的 SafeLoader，并把时间样文本保持为字符串。"""


# 时间样文本（如 2026-11-25 10:00:00）不转日期对象：updated_at 等字段按文本校验与回写。
_StrictLoader.yaml_implicit_resolvers = {
    prefix: [(tag, regexp) for tag, regexp in resolvers if tag != "tag:yaml.org,2002:timestamp"]
    for prefix, resolvers in yaml.SafeLoader.yaml_implicit_resolvers.items()
}


def _strict_mapping(loader: "_StrictLoader", node: yaml.Node, deep: bool = False) -> dict:
    """构造 mapping，重复键直接报错（PyYAML 默认静默后者覆盖，会无声丢条目）。

    Args:
        loader: 当前 loader 实例。
        node: YAML mapping 节点。
        deep: 是否深度构造子节点。
    Returns:
        构造完成的 dict。
    Raises:
        yaml.constructor.ConstructorError: 键不可哈希或重复。
    """
    loader.flatten_mapping(node)
    mapping: dict = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        try:
            duplicated = key in mapping
        except TypeError:
            raise yaml.constructor.ConstructorError(None, None, "映射的键不可哈希", None)
        if duplicated:
            raise yaml.constructor.ConstructorError(
                None, None, f"第 {key_node.start_mark.line + 1} 行出现重复键「{key}」", None)
        mapping[key] = loader.construct_object(value_node, deep=deep)
    return mapping


_StrictLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _strict_mapping)


def read_text_file(path: Path, what: str) -> str:
    """读取 UTF-8 文本文件（容忍记事本常见的 BOM）。

    Args:
        path: 文件路径。
        what: 文件用途的中文名称（报错定位用，如「探索记录」「批复文本」）。
    Returns:
        文件全文。
    Raises:
        RecordLoadError: 文件不存在或不是 UTF-8 编码。
    """
    if not path.is_file():
        raise RecordLoadError(f"{what}文件不存在: {path}")
    try:
        return path.read_text(encoding="utf-8-sig")
    except UnicodeDecodeError as exc:
        raise RecordLoadError(f"{what}文件不是 UTF-8 编码（{path.name}）: {exc}") from exc


def load_record(path: Path) -> dict:
    """加载探索记录（文件缺失、编码错误、YAML 语法错误、重复键一律报错）。

    Args:
        path: exploration.yaml 路径。
    Returns:
        解析后的记录；顶层结构是否合规由 check_exploration.validate 的 X1 判定。
    Raises:
        RecordLoadError: 文件不存在或无法解析。
    """
    text = read_text_file(path, "探索记录")
    try:
        return yaml.load(text, Loader=_StrictLoader)
    except yaml.YAMLError as exc:
        raise RecordLoadError(f"探索记录解析失败（{path.name}）: {exc}") from exc


# ===========三、模块调试入口==========
if __name__ == "__main__":
    # 用法：python exploration_record.py <exploration.yaml>——只验证「能否加载」，结构校验见 check_exploration.py。
    import sys
    sys.stdout.reconfigure(encoding="utf-8")
    if len(sys.argv) != 2:
        print("用法: python exploration_record.py <exploration.yaml>")
        sys.exit(2)
    try:
        # record：命令行给定路径的探索记录（顶层是否为映射交给 check_exploration.py 判定）。
        record = load_record(Path(sys.argv[1]))
    except RecordLoadError as exc:
        print(f"====探索记录加载失败====: {exc}")
        sys.exit(2)
    print(f"====探索记录加载成功====: {sys.argv[1]}（顶层类型 {type(record).__name__}）")
