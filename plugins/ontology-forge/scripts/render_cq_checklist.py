"""CQ 勾选呈审组件生成：把 CQ 清单代入模板产出自包含 HTML。

用途：九步流水线第 1 步（Charter+CQ 呈审）与设计稿 CQ 映射呈审的确定性产物——
     此前"三态勾选组件"仅是 SKILL.md 提示词约定，agent 现场发挥有随机性；
     本脚本把它固化为模板代入（assets/cq-checklist.html），任何宿主行为一致。
主要 Input：CQ 来源文件（位置参数）——.json（[{id,q}] 或 {cqs:[…]} 或 {competency_questions:[…]}）
     或 .yaml/.yml（DSL model.yaml，取其 competency_questions 段；顶层为列表亦可）。
     可选 -o 输出 HTML 路径（默认与来源同目录同名 .html）。
主要 Output：自包含 cq-checklist.html（三态勾选 ✅真业务/✏️要改/❌删 + 备注 + 补充框 +
     一键生成批复文本），stdout 中文结果行；退出码 0=成功，1=输入错误（无 CQ/文件缺失/格式不识别）。
"""

import datetime
import json
import sys
from pathlib import Path

import yaml

# PLUGIN_ROOT：插件根目录（scripts/ 的上一级）
PLUGIN_ROOT = Path(__file__).resolve().parent.parent
# TEMPLATE_PATH：勾选组件模板（占位符 __DOMAIN__/__GENERATED_AT__/__CQ_DATA__）
TEMPLATE_PATH = PLUGIN_ROOT / "assets" / "cq-checklist.html"


# ===========一、CQ 提取==========
def extract_cqs(source: Path) -> list[dict]:
    """从 JSON/YAML 来源提取 (id, q) 列表。

    Args:
        source: CQ 来源文件路径——.json 接受 [{id,q}] / {cqs:[…]} / {competency_questions:[…]}；
            .yaml/.yml 接受 DSL model.yaml（取 competency_questions 段）或顶层列表。
    Returns:
        [{"id": "cq-001", "q": "…"}, …]（保序，id 缺省时按序号补 cq-NNN）。
    Raises:
        ValueError: 文件内找不到任何 CQ。
        FileNotFoundError: 来源文件不存在。
    """
    if not source.is_file():
        raise FileNotFoundError(f"CQ 来源文件不存在: {source}")
    text = source.read_text(encoding="utf-8")
    data = json.loads(text) if source.suffix == ".json" else yaml.safe_load(text)
    # cqs：候选 CQ 列表——按三种容器形态逐层解包
    if isinstance(data, list):
        cqs = data
    elif isinstance(data, dict):
        cqs = data.get("competency_questions") or data.get("cqs") or []
    else:
        cqs = []
    if not cqs:
        raise ValueError(f"未在 {source.name} 中找到 CQ（期望 competency_questions/cqs 段或顶层列表）")
    result = []
    for idx, item in enumerate(cqs, 1):
        # q_field：问题文本字段——兼容 q/question/text 三种命名
        q_text = item.get("q") or item.get("question") or item.get("text") or ""
        if not q_text:
            continue
        result.append({"id": str(item.get("id") or f"cq-{idx:03d}"), "q": str(q_text)})
    if not result:
        raise ValueError(f"{source.name} 的 CQ 段无有效问题文本（字段 q/question/text 均为空）")
    return result


# ===========二、模板代入==========
def render(cqs: list[dict], domain: str) -> str:
    """把 CQ 清单代入模板，返回完整 HTML 文本。

    Args:
        cqs: [{"id", "q"}, …] 列表（extract_cqs 产物）。
        domain: 域名（呈审标题展示用，默认取来源文件父目录名）。
    Returns:
        占位符全部替换后的自包含 HTML 文本。
    Raises:
        RuntimeError: 模板缺失或占位符不在模板中（模板被改动导致坏件）。
    """
    if not TEMPLATE_PATH.is_file():
        raise RuntimeError(f"模板缺失: {TEMPLATE_PATH}")
    template = TEMPLATE_PATH.read_text(encoding="utf-8")
    # replacements：三个占位符的替换对——逐项预检存在性，缺一即报（防模板漂移产出坏件）
    replacements = {
        "__DOMAIN__": domain,
        "__GENERATED_AT__": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
        "__CQ_DATA__": json.dumps(cqs, ensure_ascii=False),
    }
    for holder, value in replacements.items():
        if holder not in template:
            raise RuntimeError(f"模板缺占位符 {holder}——assets/cq-checklist.html 被改动，请对照门禁修复")
        template = template.replace(holder, value)
    return template


# ===========三、模块入口==========
def main() -> int:
    """命令行入口：提取 → 代入 → 落盘。

    Args:
        无（参数经 argparse 解析：来源文件必填，-o 输出路径可选，--domain 域名可选）。
    Returns:
        进程退出码：0=成功，1=输入错误。
    """
    import argparse
    parser = argparse.ArgumentParser(description="把 CQ 清单代入模板生成勾选呈审 HTML")
    parser.add_argument("source", type=Path, help="CQ 来源：.json（列表/cqs/competency_questions）或 .yaml（model.yaml）")
    parser.add_argument("-o", "--out", type=Path, default=None, help="输出 HTML 路径（默认来源同目录 cq-checklist.html）")
    parser.add_argument("--domain", default=None, help="域名（默认来源文件父目录名）")
    args = parser.parse_args()

    try:
        cqs = extract_cqs(args.source)
        domain = args.domain or args.source.resolve().parent.name
        html = render(cqs, domain)
    except (FileNotFoundError, ValueError, RuntimeError, json.JSONDecodeError, yaml.YAMLError) as exc:
        print(f"====生成失败====: {exc}")
        return 1
    out_path = args.out or args.source.resolve().parent / "cq-checklist.html"
    out_path.write_text(html, encoding="utf-8")
    print(f"====CQ 勾选呈审生成完成====: {out_path}（{len(cqs)} 条 CQ，域 {domain}）")
    print(f"使用方式：浏览器打开勾选 → 生成批复 → 复制文本回贴给建模 agent")
    return 0


if __name__ == "__main__":
    sys.exit(main())
