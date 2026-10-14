"""受控词表检查（lint 第 9 条，dsl-spec v0.3）——glossary.md 术语对照表解析与实体名命中检查。

主要 Input：DSL 实体注册表（entities dict，仅取键名）与 seeds/glossary.md（按脚本相对位置定位）。
主要 Output：check_entities 无返回值——DSL 实体名命中 glossary「非建议名一侧」（如 xgimi 上次
试用版列 RunSnapshot 等）时逐条记 warning；glossary.md 缺失时打印提示并整体跳过（降级不报错）。
"""

# 标准库导入
import re
import sys
from pathlib import Path

# GLOSSARY_PATH：术语对照表路径（plugins/ontology-forge/seeds/glossary.md，随插件分发）。
GLOSSARY_PATH = Path(__file__).resolve().parents[1] / "seeds" / "glossary.md"
# PASCAL_WORD_RE：表格单元格内 PascalCase 实体名的提取正则（中文与纯数字均不匹配）。
PASCAL_WORD_RE = re.compile(r"[A-Z][A-Za-z0-9]*")


# ===========一、glossary 表格解析==========
def _cells(line: str) -> list[str]:
    """把一行 markdown 表格文本切为单元格列表。Args: line 表格行。Returns: 去空白后的单元格列表。"""
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def parse_glossary(text: str) -> tuple[set[str], set[str]]:
    """解析 glossary.md 全部表格，产出（已知名集合，非建议名集合）。

    机械规则（由表格结构驱动，不含域名特判）：
    - 列头含「上次试用版」的表 = 同域两版对照表：该列为非建议名一侧，列头含「复验版」的列为
      建议名一侧；其中概念列为「两版同名」的行，其名字双方共有，归建议名侧；
    - 其余表 = 跨域对照表：列头以「命名」结尾的列均为各自域的建议名；
    - 非建议名集合 = 试用版列名字 − 建议名集合（两版同名行由此被排除）。

    Args:
        text: glossary.md 全文。
    Returns:
        (known, deprecated) 二元组：known 为全部出现的实体名；deprecated 为命中即报 warning 的
        非建议名一侧。
    """
    # suggested：建议名一侧集合；legacy_pool：试用版列名字池（尚未扣除建议名）。
    suggested: set[str] = set()
    legacy_pool: set[str] = set()
    # lines：全文行列表；i：当前行下标（逐块推进）。
    lines = text.splitlines()
    i = 0
    while i < len(lines):
        if not lines[i].lstrip().startswith("|"):
            i += 1
            continue
        #   1. 收集一个连续表格块，取首行为表头
        block: list[str] = []
        while i < len(lines) and lines[i].lstrip().startswith("|"):
            block.append(lines[i])
            i += 1
        header = _cells(block[0])
        legacy_idx = next((k for k, h in enumerate(header) if "上次试用版" in h), None)
        if legacy_idx is None:
            #   2. 跨域对照表：「命名」结尾列全部为建议名
            for row in block[1:]:
                cells = _cells(row)
                suggested.update(
                    name for k, h in enumerate(header)
                    if h.endswith("命名") and k < len(cells)
                    for name in PASCAL_WORD_RE.findall(cells[k])
                )
            continue
        #   3. 同域两版对照表：试用版列 -> 名字池；复验版列与「两版同名」行 -> 建议名
        sugg_idx = next((k for k, h in enumerate(header) if "复验版" in h), None)
        for row in block[1:]:
            cells = _cells(row)
            same_in_both = cells and cells[0] == "两版同名"
            if sugg_idx is not None and sugg_idx < len(cells):
                suggested.update(PASCAL_WORD_RE.findall(cells[sugg_idx]))
            if legacy_idx < len(cells):
                names = set(PASCAL_WORD_RE.findall(cells[legacy_idx]))
                (suggested if same_in_both else legacy_pool).update(names)
    return suggested | legacy_pool, legacy_pool - suggested


# ===========二、实体名命中检查（lint 规则 9 入口）==========
def check_entities(entities: dict, report) -> None:
    """对照 glossary 检查 DSL 实体名：命中非建议名一侧逐条记 warning；缺表降级跳过。

    Args:
        entities: DSL 实体注册表（实体名 -> 实体定义，仅键名参与检查）。
        report: lint_model.Report 兼容收集器（需提供 warn(tag, where, detail)）。
    Returns:
        None。
    """
    if not GLOSSARY_PATH.is_file():
        print(f"提示：受控词表 {GLOSSARY_PATH} 不存在，lint9 跳过（降级不报错）")
        return
    _known, deprecated = parse_glossary(GLOSSARY_PATH.read_text(encoding="utf-8"))
    for name in entities:
        if name in deprecated:
            report.warn("lint9 受控词表", f"实体 {name}",
                        "曾用命名（glossary 非建议名一侧），对照 seeds/glossary.md 确认是否有意复用")


# ===========三、模块调试入口==========
if __name__ == "__main__":
    # 对插件自带的 glossary.md 跑一次解析，人工观察已知名与非建议名集合。
    sys.stdout.reconfigure(encoding="utf-8")
    _known, _deprecated = parse_glossary(GLOSSARY_PATH.read_text(encoding="utf-8"))
    print(f"已知名 {len(_known)} 个: {sorted(_known)}")
    print(f"非建议名 {len(_deprecated)} 个: {sorted(_deprecated)}")
