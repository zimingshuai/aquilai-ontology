"""CQ 覆盖矩阵：校验 competency_questions.covered_by 引用的可解析性。

主要 Input：DSL YAML 模型路径（命令行位置参数）。
主要 Output：stdout 中文覆盖矩阵（Markdown 表：CQ id / 问题 / covered_by 引用 / 引用是否可解析）
+ 退出码（0=全部可解析或无 CQ；1=存在不可解析引用；2=文件/解析失败）。
校验口径：covered_by 每项为 `<Entity>` 或 `<Entity>.<field>`——Entity 必须存在于 entities，
field 必须存在于该实体 properties。
"""

# 标准库导入
import sys
from pathlib import Path
from typing import Any, Optional

# 第三方依赖导入
import yaml


# ===========一、引用解析==========
def _resolve_ref(ref: Any, entities: dict[str, Any]) -> Optional[str]:
    """解析单条 covered_by 引用。

    Args:
        ref: covered_by 列表中的引用项（应为字符串）。
        entities: 实体名 -> 实体定义 dict。
    Returns:
        解析成功返回 None；失败返回中文原因（用于矩阵「不可解析」列）。
    """
    if not isinstance(ref, str) or not ref.strip():
        return "引用为空或非字符串"
    # parts：按第一个点拆分为实体名与可选字段名。
    parts = ref.strip().split(".", 1)
    entity, field = parts[0], (parts[1] if len(parts) > 1 else None)
    if entity not in entities:
        return f"实体 {entity!r} 不存在"
    if field is None:
        return None  # 仅引用实体，存在即可解析
    props = entities[entity].get("properties") or {}
    if field not in props:
        return f"字段 {entity}.{field} 不在该实体 properties 中"
    return None


# ===========二、矩阵构建与输出==========
def check_cq(model: dict[str, Any], path: Path) -> int:
    """执行 CQ 覆盖检查并打印矩阵。

    Args:
        model: safe_load 得到的 DSL 模型 dict。
        path: 模型路径（报告头展示用）。
    Returns:
        退出码：0=通过；1=存在不可解析引用。
    """
    entities = model.get("entities") or {}
    cqs = model.get("competency_questions") or []
    print(f"====CQ 覆盖矩阵====: {path}")
    if not cqs:
        print("模型未声明 competency_questions，无矩阵可查。")
        print("====CQ 检查通过====: 0 条能力问题")
        return 0
    unresolved_count = 0  # 不可解析引用总数
    print()
    print("| CQ id | 问题 | covered_by 引用 | 引用是否可解析 |")
    print("|---|---|---|---|")
    for cq in cqs:
        if not isinstance(cq, dict):
            continue
        cq_id = str(cq.get("id", "?"))
        question = str(cq.get("q", "")).replace("|", "\\|")
        refs = cq.get("covered_by") or []
        # cell_refs / cell_status：矩阵两个单元格的行内文本。
        cell_refs, cell_status = [], []
        for ref in refs:
            reason = _resolve_ref(ref, entities)
            if reason is None:
                cell_refs.append(str(ref))
                cell_status.append(f"{ref} ✅")
            else:
                cell_refs.append(f"{ref} ❌")
                cell_status.append(f"{ref} ❌（{reason}）")
                unresolved_count += 1
        ref_text = "<br/>".join(cell_refs) if cell_refs else "（空，未声明支撑元素）"
        status_text = "<br/>".join(cell_status) if cell_status else "⚠️ 空"
        print(f"| {cq_id} | {question} | {ref_text} | {status_text} |")
    verdict = "通过" if unresolved_count == 0 else "未通过"
    print()
    print(f"====CQ 检查{verdict}====: {len(cqs)} 条能力问题，不可解析引用 {unresolved_count} 处")
    return 1 if unresolved_count else 0


# ===========三、命令行入口==========
def main() -> int:
    """命令行入口：加载 YAML -> 校验 CQ 引用 -> 输出矩阵与退出码。"""
    if len(sys.argv) != 2:
        print("用法: python check_cq.py <model.yaml>", file=sys.stderr)
        return 2
    path = Path(sys.argv[1])
    if not path.is_file():
        print(f"错误：文件不存在 {path}", file=sys.stderr)
        return 2
    try:
        model = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        print(f"错误：YAML 解析失败——{exc}", file=sys.stderr)
        return 2
    if not isinstance(model, dict):
        print("错误：模型顶层不是映射结构", file=sys.stderr)
        return 2
    return check_cq(model, path)


if __name__ == "__main__":
    # CLI 脚本本体即调试入口：python check_cq.py <model.yaml> 跑真实模型。
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    sys.exit(main())
