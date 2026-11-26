"""分发结构门禁：多平台清单合规 + frontmatter 必填 + 渲染缓存与版本锁 + zip 结构断言 + 口径漂移断言 + 规范符合性断言 + 范例门禁断言。

用途：发布/打包前自检（教训沉淀：WorkBuddy 首次上传因缺 avatars 与 description
     两次被平台拒收，均属"机器可判定"的合规项——本脚本把它们固化为断言闸门；
     另含 mermaid 缓存随包与版本锁一致性，避免断网兜底失效与跨端渲染漂移；
     另含口径漂移断言：lint 条数联动 lint_model.py 事实源、流水线步数唯一"九步"、
     清单字符串字段禁内联版本引用——三类数字/版本口径曾七处漂移且全绿漏网；
     另含 Agent Skills 开放规范（agentskills.io/specification）机器可判定项：
     name 字符规则与长度、description/compatibility 长度上限；
     另含触发用例集（evals/trigger）结构断言——用例集是触发回归的载体，
     目录/文件静默缺失或结构坏件即回归失效，一律 fail 不降级；
     另含范例门禁断言——黄金范例 examples/supplier-recon 的关键文件在位、
     探索记录可交接、DSL 过 lint、CQ 全解析、编译幂等、拓扑同步、与评测
     黄金答案结构等价（范例 README 第六节口径的机器固化，任一不过即范例
     不可再被当作对照物，等同插件回归失败））。
主要 Input：无必填参数（插件根按脚本位置自定位）。
主要 Output：stdout 中文逐项检查报告；退出码 0=全部通过，1=任一断言失败
     （含"zip 产物版本落后于清单"的过期检查——防止旧包被误传平台）。
"""

import ast
import hashlib
import json
import re
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path
from typing import Optional

import yaml

# PLUGIN_ROOT：插件根目录（scripts/ 的上一级）
PLUGIN_ROOT = Path(__file__).resolve().parent.parent
# MANIFESTS：四平台清单路径（单内容多清单架构：四清单必须并存且版本一致）
MANIFESTS = {
    "zcode": PLUGIN_ROOT / ".zcode-plugin" / "plugin.json",
    "codebuddy": PLUGIN_ROOT / ".codebuddy-plugin" / "plugin.json",
    "claude": PLUGIN_ROOT / ".claude-plugin" / "plugin.json",
    "codex": PLUGIN_ROOT / ".codex-plugin" / "plugin.json",
}
# AGENT_MD：WorkBuddy 总控提示词路径（frontmatter 必填项断言对象）
AGENT_MD = PLUGIN_ROOT / "agents" / "aquilair-fde.md"
# SKILLS_DIR：技能目录（SKILL.md frontmatter 断言对象，自动发现新技能零改动）
SKILLS_DIR = PLUGIN_ROOT / "skills"
# WORKBUDDY_DIR：WorkBuddy 构建产物目录（zip 过期检查对象）
WORKBUDDY_DIR = PLUGIN_ROOT.parent.parent / "workbuddy"
# AGENT_FRONTMATTER_REQUIRED：总控提示词 frontmatter 必填键
AGENT_FRONTMATTER_REQUIRED = ("name", "displayName", "description", "profession", "maxTurns", "skills")
# RENDER_IMAGE_PY：mermaid 版本锁所在模块——只读源文本做断言，不 import（避免拉入 playwright 依赖）
RENDER_IMAGE_PY = PLUGIN_ROOT / "scripts" / "render_image.py"
# MERMAID_ASSET：--image 断网兜底的本地渲染缓存，必须随包分发才有意义
MERMAID_ASSET = PLUGIN_ROOT / "assets" / "mermaid.min.js"
# MERMAID_ASSET_MIN_BYTES：缓存体量下限（UMD 单文件实测 3.4MB；占位/截断文件同样会让兜底失效）
MERMAID_ASSET_MIN_BYTES = 1_000_000
# LINT_MODEL_PY：lint 条数唯一事实源——动态解析其模块 docstring，禁止在文档/断言里写死条数
LINT_MODEL_PY = PLUGIN_ROOT / "scripts" / "lint_model.py"
# LINT_COUNT_RE：事实源条数解析正则（lint_model.py docstring 形如"…全部 15 条确定性检查"）
LINT_COUNT_RE = re.compile(r"全部 (\d+) 条")
# LINT_MENTION_RE：文档中 lint 条数写法的匹配正则（覆盖"15 条 lint"/"15条lint"/"15 条确定性检查"等形态，大小写不敏感）
LINT_MENTION_RE = re.compile(r"(\d+)\s*条\s*(?:lint|确定性检查)", re.IGNORECASE)
# SANDBOX_PY：语义沙盘 S 检查项数唯一事实源——动态解析其模块 docstring，禁止在文档里写死 S 区间
# （教训：S7 加入后 scripts/README 与 evals README 两处仍写 S1-S6/3 warning——与 lint 条数同款漂移病）
SANDBOX_PY = PLUGIN_ROOT / "scripts" / "semantic_sandbox.py"
# S_COUNT_RE：事实源形态解析正则（semantic_sandbox.py docstring 形如"检查项 S1-S7"——区间右端带 S 前缀）
S_COUNT_RE = re.compile(r"检查项 S1-S(\d+)")
# S_RANGE_MENTION_RE：文档中 S 区间写法的匹配正则（覆盖"S1-S7"/"S1～S7"形态，右端 S 可省；列举式如"S1/S2/S3/S7"不命中，属用例内容非计数口径）
S_RANGE_MENTION_RE = re.compile(r"S1[-～~]S?(\d+)")
# S_COUNT_MENTION_RE：文档中 S 计数写法的匹配正则（"7 项语义沙盘"形态，与区间写法互为印证）
S_COUNT_MENTION_RE = re.compile(r"(\d+)\s*项语义沙盘")
# PIPELINE_STEP_RE：流水线步数口径正则（"九步流水线"/"九步建模流水线"等变体均命中，取代旧精确子串匹配）
PIPELINE_STEP_RE = re.compile(r"([一二三四五六七八九十百\d]+)\s*步(?:建模)?流水线")
# CN_NUM_MAP：中文数字词映射（按规格覆盖一~十一做全——"十一步"不接"流水线"后缀不命中，但映射备全防未来变体）
CN_NUM_MAP = {"一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9, "十": 10, "十一": 11}
# VALID_PIPELINE_STEPS：流水线合法步数集合（建模流水线唯一口径"九步"，源自 ontology-modeling SKILL.md §三）
VALID_PIPELINE_STEPS = {9}
# EVALS_DIR：仓库根 evals/ 目录（口径扫描扩展范围——教训：evals README 曾残留"七步流水线"而插件内全绿漏网）
EVALS_DIR = PLUGIN_ROOT.parent.parent / "evals"
# VERSION_REF_RE：清单字符串字段禁用的内联版本引用（version 字段是唯一版本事实源；教训：.codebuddy 曾残留"(v0.4.2)"）
VERSION_REF_RE = re.compile(r"\(v0\.\d")
# SKILL_NAME_RE：技能 name 字符规则正则（Agent Skills 规范 Specification §name field）——
# 小写字母数字 + 单连字符分段，禁开头/结尾连字符与连续连字符
SKILL_NAME_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
# SKILL_NAME_MAX_LEN：技能 name 长度上限（Agent Skills 规范 Specification §name field）
SKILL_NAME_MAX_LEN = 64
# SKILL_DESC_MAX_LEN：技能 description 长度上限（Agent Skills 规范 Specification §description field）
SKILL_DESC_MAX_LEN = 1024
# SKILL_COMPAT_MAX_LEN：技能 compatibility 长度上限（Agent Skills 规范 Specification §compatibility field，可选字段）
SKILL_COMPAT_MAX_LEN = 500
# TRIGGER_DIR：仓库根触发用例集目录（技能触发回归的载体，结构有效性进门禁；写法参考 EVALS_DIR）
TRIGGER_DIR = EVALS_DIR / "trigger"
# EXAMPLES_README：范例总导读（门禁节存在性断言对象——该节是范例门禁的验收口径）
EXAMPLES_README = PLUGIN_ROOT / "examples" / "README.md"
# EXAMPLE_DOMAIN_DIR：范例域目录（黄金范例唯一域：供应商月度对账与差异处理）
EXAMPLE_DOMAIN_DIR = PLUGIN_ROOT / "examples" / "supplier-recon"
# EXAMPLE_REQUIRED_FILES：范例域关键文件相对路径（域导读 + 九步各产物 + 资料包清单，缺一即 fail 指名）
EXAMPLE_REQUIRED_FILES = (
    "README.md", "model.yaml", "topology.md", "charter.md", "fact-cards.md",
    "design-proposal.md", "business-inquiry.md",
    "modeling-brief/exploration.yaml", "modeling-brief/brief.yaml", "modeling-brief/intake-log.md",
)
# EXAMPLE_MODEL_YAML：范例本体 DSL（lint/CQ/编译幂等/拓扑同步/结构等价断言对象）
EXAMPLE_MODEL_YAML = EXAMPLE_DOMAIN_DIR / "model.yaml"
# EXAMPLE_EXPLORATION_YAML：范例探索记录（可交接断言对象）
EXAMPLE_EXPLORATION_YAML = EXAMPLE_DOMAIN_DIR / "modeling-brief" / "exploration.yaml"
# EXAMPLE_TOPOLOGY_MD：范例拓扑源（render_topology.py 重渲染须与其逐字节一致）
EXAMPLE_TOPOLOGY_MD = EXAMPLE_DOMAIN_DIR / "topology.md"
# GOLD_MODEL_YAML：评测黄金答案 DSL（结构等价防漂移的对照源——它在评测仓里必须存在）
GOLD_MODEL_YAML = EVALS_DIR / "ontology-modeling" / "goldstandard" / "gold" / "model.yaml"
# CHECK_EXPLORATION_PY：探索记录门禁脚本（范例可交接断言实跑对象）
CHECK_EXPLORATION_PY = PLUGIN_ROOT / "scripts" / "check_exploration.py"
# CHECK_CQ_PY：CQ 回验脚本（范例 CQ 全解析断言实跑对象）
CHECK_CQ_PY = PLUGIN_ROOT / "scripts" / "check_cq.py"
# COMPILE_MODEL_PY：DSL 编译脚本（范例编译幂等断言实跑对象）
COMPILE_MODEL_PY = PLUGIN_ROOT / "scripts" / "compile_model.py"
# RENDER_TOPOLOGY_PY：拓扑渲染脚本（范例拓扑同步断言实跑对象）
RENDER_TOPOLOGY_PY = PLUGIN_ROOT / "scripts" / "render_topology.py"
# COMPILE_BUNDLE_FILES：编译幂等断言的产物文件名（两次编译逐文件 sha256 相等）
COMPILE_BUNDLE_FILES = ("studio-model.yaml", "objects.json", "rules.json")
# EXPLORATION_HANDOFF_LINE：check_exploration.py 可交接结论行（期望输出行）
EXPLORATION_HANDOFF_LINE = "====探索记录可交接建模===="
# LINT_CLEAN_LINE：lint_model.py 零错零警结论行（期望输出行）
LINT_CLEAN_LINE = "error 0 处，warning 0 处"
# CQ_RESOLVED_LINE：check_cq.py 全解析结论行（期望输出行）
CQ_RESOLVED_LINE = "不可解析引用 0 处"
# EXPLORE_CHECKLIST_HTML：缺口探索勾选呈审模板（render_explore_checklist.py 的代入依赖）
EXPLORE_CHECKLIST_HTML = PLUGIN_ROOT / "assets" / "explore-checklist.html"
# EXPLORE_CHECKLIST_HOLDERS：勾选模板必需占位符（缺失即 render_explore_checklist.py 产出坏件）
EXPLORE_CHECKLIST_HOLDERS = ("__DOMAIN__", "__GENERATED_AT__", "__ITEM_DATA__")
# EXAMPLES_GUARD_HEADLINE：范例总导读的门禁节标题（防范例导读被删成"范例仅供参考"）
EXAMPLES_GUARD_HEADLINE = "范例受发布门禁保护"


# ===========一、检查框架==========
class Report:
    """逐项检查结果收集器。

    Input:
        无。
    Return:
        通过 ``ok(name)``/``fail(name, detail)`` 记录检查项，
        通过 ``done`` 属性判断是否全部通过，``summary()`` 输出中文报告。
    """

    def __init__(self) -> None:
        # _items：检查结果列表，元素为 (通过与否, 检查名, 失败明细)
        self._items: list[tuple[bool, str, str]] = []

    def ok(self, name: str) -> None:
        """记录一项通过。

        Args:
            name: 检查项名称（中文）。
        Returns:
            None。
        """
        self._items.append((True, name, ""))

    def fail(self, name: str, detail: str) -> None:
        """记录一项失败。

        Args:
            name: 检查项名称（中文）。
            detail: 失败原因明细（中文）。
        Returns:
            None。
        """
        self._items.append((False, name, detail))

    @property
    def done(self) -> bool:
        """是否全部通过。"""
        return all(passed for passed, _, _ in self._items)

    def summary(self) -> str:
        """生成中文逐项报告。

        Args:
            无。
        Returns:
            逐行检查结果文本（✓/✗ 前缀 + 失败明细 + 末尾汇总行）。
        """
        lines = [f"{'✓' if passed else '✗'} {name}" + (f"——{detail}" if detail and not passed else "")
                 for passed, name, detail in self._items]
        passed_count = sum(1 for passed, _, _ in self._items if passed)
        lines.append(f"\n共 {len(self._items)} 项：{passed_count} 通过 / {len(self._items) - passed_count} 失败")
        return "\n".join(lines)


def check(report: Report, name: str, condition: bool, detail: str = "") -> None:
    """条件断言辅助：按条件记录通过/失败。

    Args:
        report: 结果收集器。
        name: 检查项名称（中文）。
        condition: 断言条件（True 记通过）。
        detail: 失败时的原因明细（中文）。
    Returns:
            None。
    """
    if condition:
        report.ok(name)
    else:
        report.fail(name, detail)


# ===========二、清单与 frontmatter 检查==========
def _skill_dirs() -> list[Path]:
    """发现技能目录（skills/ 下含 SKILL.md 的一级子目录，按目录名排序）。

    Returns:
        技能目录路径列表；自动覆盖新增技能，门禁零改动跟进。
    """
    return [p for p in sorted(SKILLS_DIR.iterdir()) if (p / "SKILL.md").is_file()]


def check_manifests(report: Report) -> None:
    """四平台清单存在性、版本一致性与 WorkBuddy 合规断言。

    Args:
        report: 结果收集器。
    Returns:
        None（结果记入 report）。
    """
    #   1. 四清单并存 + 版本一致（单内容多清单的结构不变量）
    versions = {}
    for platform, path in MANIFESTS.items():
        if not path.is_file():
            report.fail(f"清单存在：{platform}", f"缺 {path.relative_to(PLUGIN_ROOT)}")
            continue
        manifest = json.loads(path.read_text(encoding="utf-8"))
        versions[platform] = manifest.get("version", "")
        report.ok(f"清单存在：{platform}（v{versions[platform]}）")
    if versions and len(set(versions.values())) > 1:
        report.fail("四清单版本一致", f"版本不一致：{versions}")
    elif versions:
        report.ok("四清单版本一致")

    #   2. 市场清单版本联动（教训：升版只改插件清单漏了 marketplace.json，用户刷新市场看不到更新）
    marketplace = PLUGIN_ROOT.parent / "marketplace.json"
    if marketplace.is_file():
        mp_entry = next((e for e in json.loads(marketplace.read_text(encoding="utf-8"))["plugins"]
                         if e.get("source", "").lstrip("./") == PLUGIN_ROOT.name), None)
        plugin_version = next(iter(versions.values()), "") if versions else ""
        check(report, "marketplace.json 版本与插件清单一致",
              bool(mp_entry) and mp_entry.get("version") == plugin_version,
              f"marketplace={mp_entry.get('version') if mp_entry else '未登记'} vs 插件清单={plugin_version}")

    #   2. WorkBuddy 清单逐项合规（平台解析硬依赖，缺一即拒收）
    cb_path = MANIFESTS["codebuddy"]
    if not cb_path.is_file():
        return
    d = json.loads(cb_path.read_text(encoding="utf-8"))
    check(report, "WorkBuddy: name 小写+连字符", bool(re.fullmatch(r"[a-z][a-z0-9-]*", d.get("name", ""))))
    check(report, "WorkBuddy: expertType=agent", d.get("expertType") == "agent")
    check(report, "WorkBuddy: description 为英文", bool(d.get("description", "")) and d["description"][0].isascii())
    check(report, "WorkBuddy: author 含 email", "@" in d.get("author", {}).get("email", ""))
    check(report, "WorkBuddy: agentName 与 agents 文件名一致",
          d.get("agentName") == AGENT_MD.stem, f"agentName={d.get('agentName')}")
    agent_entry = Path(d.get("agents", [""])[0])
    check(report, "WorkBuddy: agents 路径存在", (PLUGIN_ROOT / agent_entry).is_file(), f"{agent_entry}")
    check(report, "WorkBuddy: displayName/profession 双语",
          all(set(d.get(k, {})) >= {"en", "zh"} for k in ("displayName", "profession")))
    zh_len = len(d.get("displayDescription", {}).get("zh", ""))
    check(report, f"WorkBuddy: displayDescription 中文 {zh_len} 字（40-50）", 40 <= zh_len <= 50)
    avatar_rel = d.get("avatar", "")
    check(report, "WorkBuddy: avatar 字段+文件存在",
          bool(avatar_rel) and (PLUGIN_ROOT / avatar_rel).is_file(), avatar_rel or "缺 avatar 字段")
    check(report, "WorkBuddy: categoryId 有效", bool(d.get("categoryId", "")))
    check(report, "WorkBuddy: plugin==name", d.get("plugin") == d.get("name"))
    check(report, "WorkBuddy: tags 恰 3 个", len(d.get("tags", [])) == 3)
    prompts = d.get("quickPrompts", [])
    check(report, "WorkBuddy: quickPrompts 恰 3 条", len(prompts) == 3)
    init = d.get("defaultInitPrompt", {})
    check(report, "WorkBuddy: defaultInitPrompt==quickPrompts[0]",
          bool(prompts) and init.get("zh") == prompts[0].get("zh") and init.get("en") == prompts[0].get("en"))


def check_manifest_version_refs(report: Report) -> None:
    """四清单字符串字段内联版本引用禁令断言（version 字段是唯一版本事实源）。

    教训：.codebuddy 清单字符串字段曾残留"(v0.4.2)"连续三个版本未随升版更新——
    字符串里手写的版本号必然漂移，一律禁止；版本只认清单顶层 version 字段
    （其一致性已由"四清单版本一致"断言覆盖）。

    Args:
        report: 结果收集器。
    Returns:
        None（结果记入 report）。
    """
    refs = []
    for platform, path in MANIFESTS.items():
        if not path.is_file():
            continue  # 清单缺失已由 check_manifests 记失败，此处不重复断言
        #   1. 栈式递归展开 JSON 全部字符串字段值（含嵌套 interface/author 等任意层级）
        stack = [json.loads(path.read_text(encoding="utf-8"))]
        while stack:
            node = stack.pop()
            if isinstance(node, str):
                #   2. 字符串值命中内联版本引用即收集（如"(v0.4.2)"）
                hit = VERSION_REF_RE.search(node)
                if hit:
                    refs.append(f"{platform} 清单字符串含内联版本引用「{hit.group(0)}…」")
            elif isinstance(node, dict):
                stack.extend(node.values())
            elif isinstance(node, list):
                stack.extend(node)
    check(report, "清单口径：字符串字段无内联版本引用", not refs, "；".join(refs))


def check_agent_frontmatter(report: Report) -> None:
    """总控提示词 frontmatter 必填键断言（description 缺失教训的固化）。

    Args:
        report: 结果收集器。
    Returns:
        None（结果记入 report）。
    """
    if not AGENT_MD.is_file():
        report.fail("agent 提示词存在", f"缺 {AGENT_MD.relative_to(PLUGIN_ROOT)}")
        return
    match = re.match(r"^---\n(.*?)\n---", AGENT_MD.read_text(encoding="utf-8"), re.S)
    if not match:
        report.fail("agent frontmatter 可解析", "文件未以 --- frontmatter 开头")
        return
    meta = yaml.safe_load(match.group(1)) or {}
    missing = [key for key in AGENT_FRONTMATTER_REQUIRED if not meta.get(key)]
    check(report, "agent frontmatter 必填齐全"
          + ("" if not missing else f"（缺 {missing}）"), not missing, f"缺失键：{missing}")
    desc = str(meta.get("description", ""))
    check(report, "agent description 含触发句式（Use when）", "use when" in desc.lower(), "平台靠 description 判断激活时机")
    body = AGENT_MD.read_text(encoding="utf-8")
    check(report, "agent 子代理派发模式节存在（到达即停/确认声明）",
          "子代理派发模式" in body and "确认声明只认主代理" in body,
          "派发形态的确认关卡规则缺失——ZCode/Claude subagent 将无法正确停卡")
    check(report, "agents/README.md 接入指南存在",
          (AGENT_MD.parent / "README.md").is_file())
    # 插件根 README 是分发单元门面（v0.4.9 补齐——对标分发物最佳实践，误删即 FAIL）
    check(report, "插件根 README.md 门面存在",
          (PLUGIN_ROOT / "README.md").is_file())


def check_skills(report: Report) -> None:
    """技能目录自动发现 + SKILL.md frontmatter 断言。

    Args:
        report: 结果收集器。
    Returns:
        None（结果记入 report）。
    """
    skill_dirs = _skill_dirs()
    check(report, f"技能发现 {len(skill_dirs)} 个（frontmatter 合规）", bool(skill_dirs), "skills/ 下无 SKILL.md")
    for skill_dir in skill_dirs:
        match = re.match(r"^---\n(.*?)\n---", (skill_dir / "SKILL.md").read_text(encoding="utf-8"), re.S)
        meta = yaml.safe_load(match.group(1)) if match else {}
        valid = bool(meta.get("name") == skill_dir.name and meta.get("description"))
        check(report, f"技能 {skill_dir.name}: name 与目录一致 + description 存在", valid,
              f"name={meta.get('name')}")


def check_skill_spec_conformance(report: Report) -> None:
    """技能 frontmatter 的 Agent Skills 开放规范机器可判定项断言。

    规范出处：agentskills.io/specification。覆盖三类机器可判定项——
    name 字符规则与长度（§name field）、description 长度上限（§description field）、
    compatibility 可选字段长度上限（§compatibility field）：越界会被技能市场
    拒收或截断，属"机器可判定"的合规项，固化为断言闸门。既有"name 与目录
    一致 + description 非空"断言由 check_skills 负责，二者互不重叠。

    Args:
        report: 结果收集器。
    Returns:
        None（结果记入 report；frontmatter 不可解析时逐技能 fail 指名，不静默跳过）。
    """
    for skill_dir in _skill_dirs():
        #   1. 解析 frontmatter（不可解析即 fail 指名——三不纪律之"不降级"）
        match = re.match(r"^---\n(.*?)\n---", (skill_dir / "SKILL.md").read_text(encoding="utf-8"), re.S)
        if not match:
            report.fail(f"技能规范：{skill_dir.name} frontmatter 可解析", "文件未以 --- frontmatter 开头")
            continue
        meta = yaml.safe_load(match.group(1)) or {}
        #   2. name 字符规则与长度：小写字母数字+单连字符分段，≤64（§name field）
        name = str(meta.get("name", ""))
        check(report, f"技能规范：{skill_dir.name} name 字符规则与长度（≤{SKILL_NAME_MAX_LEN}）",
              bool(SKILL_NAME_RE.fullmatch(name)) and len(name) <= SKILL_NAME_MAX_LEN,
              f"name={name!r} 不合规——规范要求小写字母数字+单连字符且长度 ≤{SKILL_NAME_MAX_LEN}")
        #   3. description 长度：≤1024（§description field；非空断言由 check_skills 既有项覆盖）
        desc_len = len(str(meta.get("description", "")))
        check(report, f"技能规范：{skill_dir.name} description 长度（{desc_len} ≤{SKILL_DESC_MAX_LEN}）",
              desc_len <= SKILL_DESC_MAX_LEN,
              f"description {desc_len} 字符超上限 {SKILL_DESC_MAX_LEN}——技能市场会拒收或截断")
        #   4. compatibility 可选字段：存在时长度 1~500（§compatibility field），不存在不失败
        if "compatibility" in meta:
            compat_len = len(str(meta.get("compatibility", "")))
            check(report, f"技能规范：{skill_dir.name} compatibility 长度（{compat_len} ≤{SKILL_COMPAT_MAX_LEN}）",
                  0 < compat_len <= SKILL_COMPAT_MAX_LEN,
                  f"compatibility {compat_len} 字符超出 1~{SKILL_COMPAT_MAX_LEN} 范围")
        else:
            report.ok(f"技能规范：{skill_dir.name} compatibility 未声明（可选字段，不失败）")


# ===========三、渲染缓存与版本锁检查==========
def check_mermaid(report: Report) -> None:
    """渲染缓存存在性与 mermaid 版本锁一致性断言。

    断网兜底要成立，缓存必须同时满足"在位 + 体量正常 + 与锁定版本同版"；
    只钉 major（mermaid@11）会让联网侧浮动到最新 11.x、断网侧固定缓存版本，
    同一份 DSL 两种环境渲染版式可能不同——拓扑 diff 图跨端不可复现。

    Args:
        report: 结果收集器。
    Returns:
        None（结果记入 report）。
    """
    #   1. 缓存文件在位且体量正常
    exists = MERMAID_ASSET.is_file()
    size = MERMAID_ASSET.stat().st_size if exists else 0
    check(report, "渲染缓存 assets/mermaid.min.js 存在", exists,
          f"缺 {MERMAID_ASSET.relative_to(PLUGIN_ROOT)}——WorkBuddy 包内 --image 断网无兜底")
    check(report, f"渲染缓存体量正常（{size // 1024}KB）", size >= MERMAID_ASSET_MIN_BYTES,
          "疑似占位或截断文件，断网兜底不可用")

    #   2. CQ 勾选呈审模板在位且占位符齐全（render_cq_checklist.py 的代入依赖）
    cq_tpl = PLUGIN_ROOT / "assets" / "cq-checklist.html"
    if cq_tpl.is_file():
        tpl_text = cq_tpl.read_text(encoding="utf-8")
        holders_ok = all(h in tpl_text for h in ("__DOMAIN__", "__GENERATED_AT__", "__CQ_DATA__"))
        check(report, "CQ 呈审模板在位且占位符齐全", holders_ok,
              "assets/cq-checklist.html 缺占位符——render_cq_checklist.py 会产出坏件")
    else:
        report.fail("CQ 呈审模板在位且占位符齐全", "缺 assets/cq-checklist.html")

    #   2. 版本锁声明与实际缓存版本一致
    if not RENDER_IMAGE_PY.is_file():
        report.fail("版本锁可读取", f"缺 {RENDER_IMAGE_PY.relative_to(PLUGIN_ROOT)}")
        return
    source = RENDER_IMAGE_PY.read_text(encoding="utf-8")
    version_match = re.search(r'^MERMAID_VERSION\s*=\s*"([^"]+)"', source, re.M)
    pinned = version_match.group(1) if version_match else ""
    check(report, "版本锁：MERMAID_VERSION 已声明", bool(pinned), "render_image.py 未定义 MERMAID_VERSION")
    if pinned and exists:
        cached = set(re.findall(r'version:"(\d+\.\d+\.\d+)"',
                                MERMAID_ASSET.read_text(encoding="utf-8", errors="ignore")))
        check(report, f"版本锁：缓存版本与锁定版本一致（{pinned}）", pinned in cached,
              f"缓存内版本 {sorted(cached)} 与锁定 {pinned} 不一致——同 DSL 断网/联网版式会漂移")

    #   3. CDN 地址必须由锁定版本拼出，不得残留浮动 major
    cdn_match = re.search(r'^MERMAID_CDN_URL\s*=\s*f?"([^"]+)"', source, re.M)
    cdn = cdn_match.group(1) if cdn_match else ""
    floating = re.search(r"mermaid@\d+(?![\d.])", cdn)
    check(report, "版本锁：CDN 未使用浮动 major", bool(cdn) and not floating, f"CDN={cdn}")
    check(report, "版本锁：CDN 模板引用 MERMAID_VERSION", "mermaid@{MERMAID_VERSION}" in cdn, f"CDN={cdn}")


# ===========四、文档口径检查==========
def _manifest_text_snippets() -> list[tuple[str, str]]:
    """收集四平台清单的口径敏感文本片段（description 与 interface.longDescription）。

    教训：清单字段不在 *.md 扫描范围内，".zcode/.claude 残留 13条lint、.codex 残留
    十步建模流水线"均因只扫 Markdown 而漏网——口径断言必须直读清单字段。

    Returns:
        (位置标签, 文本内容) 列表；清单缺失时跳过该平台（存在性已由 check_manifests 断言）。
    """
    snippets = []
    for platform, path in MANIFESTS.items():
        if not path.is_file():
            continue
        manifest = json.loads(path.read_text(encoding="utf-8"))
        fields = {
            "description": manifest.get("description", ""),
            "interface.longDescription": manifest.get("interface", {}).get("longDescription", ""),
        }
        snippets.extend((f"{path.relative_to(PLUGIN_ROOT)}（{field}）", text)
                        for field, text in fields.items() if text)
    return snippets


def _cn_word_to_int(word: str) -> Optional[int]:
    """数字词转整数：阿拉伯数字直转，中文数字按映射表 + 十位组合解析。

    Args:
        word: PIPELINE_STEP_RE 捕获的数字词（如"9""九""十""十一""二十三"）。
    Returns:
        对应整数；含"百"等超出映射与组合解析范围的词返回 None（不可判定，调用方按违规拦截）。
    """
    if word.isdigit():
        return int(word)
    if word in CN_NUM_MAP:
        return CN_NUM_MAP[word]
    # 中文数字十位组合：X十 / 十Y / X十Y（覆盖一~九十九；CN_NUM_MAP 未直接命中时兜底）
    match = re.fullmatch(r"([一二三四五六七八九]?)十([一二三四五六七八九]?)", word)
    if match:
        tens = CN_NUM_MAP[match.group(1)] if match.group(1) else 1
        units = CN_NUM_MAP[match.group(2)] if match.group(2) else 0
        return tens * 10 + units
    return None


def _load_lint_count(report: Report) -> Optional[int]:
    """从 lint_model.py 模块 docstring 动态解析 lint 条数（唯一事实源）。

    Args:
        report: 结果收集器（事实源不可读时记 fail 指名，绝不静默跳过——三不纪律之"不降级"）。
    Returns:
        lint 条数；文件缺失、语法不可解析或 docstring 未声明「全部 N 条」时返回 None，
        调用方此时不得继续做联动断言（数字口径已失去事实源）。
    """
    if not LINT_MODEL_PY.is_file():
        report.fail("文档口径：lint 条数事实源可读", f"缺 {LINT_MODEL_PY.relative_to(PLUGIN_ROOT)}")
        return None
    try:
        tree = ast.parse(LINT_MODEL_PY.read_text(encoding="utf-8"))
        docstring = ast.get_docstring(tree) or ""
    except SyntaxError:
        docstring = ""
    match = LINT_COUNT_RE.search(docstring)
    if not match:
        report.fail("文档口径：lint 条数事实源可读",
                    "lint_model.py 模块 docstring 未声明「全部 N 条」——条数口径失去事实源")
        return None
    return int(match.group(1))


def check_lint_count_wording(report: Report) -> None:
    """lint 条数联动断言：文档写法必须与 lint_model.py 事实源一致。

    教训：lint 条数升到 15 后清单/SKILL/user-guide 三处仍写 13——数字口径
    无联动断言，漂移全靠人眼发现。事实源唯一：lint_model.py docstring 的
    「全部 N 条」；本断言动态解析后核对各处「N条lint」写法（不含该写法的
    文件跳过，不强制每处都写条数）。

    Args:
        report: 结果收集器。
    Returns:
        None（结果记入 report）。
    """
    #   1. 解析事实源条数（失败已由 _load_lint_count 记 fail，此处直接返回不降级）
    lint_count = _load_lint_count(report)
    if lint_count is None:
        return
    #   2. 汇总口径敏感文本：四清单 description/longDescription + 市场清单 description + 建模 SKILL + user-guide
    #      （marketplace 纳入教训：升版 0.4.7 时发现其 description 残留"13条lint"——市场清单曾不在联动范围）
    targets = _manifest_text_snippets()
    mp_path = PLUGIN_ROOT.parent / "marketplace.json"
    if mp_path.is_file():
        mp_entries = json.loads(mp_path.read_text(encoding="utf-8")).get("plugins", [])
        targets += [(f"../marketplace.json（plugins[{e.get('name')}] description）", e["description"])
                    for e in mp_entries if e.get("description")]
    # 范围策略（v0.4.9 扩展）：插件根全部 *.md 全树扫描——与 S 计数/步数断言同款；
    # 教训：固定清单（SKILL+user-guide）外的文档写「N条lint」无断言（插件根 README 新增即成盲区）
    targets += [(str(path.relative_to(PLUGIN_ROOT)), path.read_text(encoding="utf-8"))
                for path in sorted(PLUGIN_ROOT.rglob("*.md"))]
    #   3. 逐处核对「N条lint」写法，发现不等收集文件+实际数字 vs 事实源数字
    drifts = []
    for label, text in targets:
        for num in dict.fromkeys(m.group(1) for m in LINT_MENTION_RE.finditer(text)):
            if int(num) != lint_count:
                drifts.append(f"{label} 写「{num}条lint」vs 事实源 {lint_count} 条")
    check(report, f"文档口径：lint 条数与事实源一致（{lint_count} 条）", not drifts, "；".join(drifts))


def _load_s_count(report: Report) -> Optional[int]:
    """从 semantic_sandbox.py 模块 docstring 动态解析 S 检查项数（唯一事实源）。

    Args:
        report: 结果收集器（事实源不可读时记 fail 指名，绝不静默跳过——三不纪律之"不降级"）。
    Returns:
        S 检查项数；文件缺失、语法不可解析或 docstring 未声明「检查项 S1-SN」时返回 None，
        调用方此时不得继续做联动断言（S 口径已失去事实源）。
    """
    if not SANDBOX_PY.is_file():
        report.fail("文档口径：S 检查项数事实源可读", f"缺 {SANDBOX_PY.relative_to(PLUGIN_ROOT)}")
        return None
    try:
        tree = ast.parse(SANDBOX_PY.read_text(encoding="utf-8"))
        docstring = ast.get_docstring(tree) or ""
    except SyntaxError:
        docstring = ""
    match = S_COUNT_RE.search(docstring)
    if not match:
        report.fail("文档口径：S 检查项数事实源可读",
                    "semantic_sandbox.py 模块 docstring 未声明「检查项 S1-SN」——S 口径失去事实源")
        return None
    return int(match.group(1))


def check_s_count_wording(report: Report) -> None:
    """S 检查项数联动断言：文档写法必须与 semantic_sandbox.py 事实源一致。

    教训：S7（孤儿动作）加入后 scripts/README 的「S1-S6」与 evals README 的旧描述
    两处漂移、靠人眼发现——与 lint 条数 13→15 漂移同款病根。事实源唯一：
    semantic_sandbox.py docstring 的「检查项 S1-SN」；扫描插件根全部 *.md +
    四清单 description + marketplace description，命中「S1-SN」区间式或
    「N 项语义沙盘」计数式写法即与事实源核对（无命中的文件跳过，不强制写数）。

    Args:
        report: 结果收集器。
    Returns:
        None（结果记入 report）。
    """
    #   1. 解析事实源 S 项数（失败已由 _load_s_count 记 fail，直接返回不降级）
    s_count = _load_s_count(report)
    if s_count is None:
        return
    #   2. 汇总口径敏感文本：四清单 description + 市场清单 + 插件根全部 *.md（全树扫描，
    #      学流水线步数断言的范围策略——漂移发生地不可枚举，宁可全扫零误报）
    targets = _manifest_text_snippets()
    mp_path = PLUGIN_ROOT.parent / "marketplace.json"
    if mp_path.is_file():
        mp_entries = json.loads(mp_path.read_text(encoding="utf-8")).get("plugins", [])
        targets += [(f"../marketplace.json（plugins[{e.get('name')}] description）", e["description"])
                    for e in mp_entries if e.get("description")]
    targets += [(str(p.relative_to(PLUGIN_ROOT)), p.read_text(encoding="utf-8"))
                for p in sorted(PLUGIN_ROOT.rglob("*.md"))]
    #   3. 逐处核对两种写法（区间式 + 计数式），漂移收集 文件+写法 vs 事实源
    drifts = []
    for label, text in targets:
        for regex, shape in ((S_RANGE_MENTION_RE, "S1-S{}"), (S_COUNT_MENTION_RE, "{} 项语义沙盘")):
            for num in dict.fromkeys(m.group(1) for m in regex.finditer(text)):
                if int(num) != s_count:
                    drifts.append(f"{label} 写「{shape.format(num)}」vs 事实源 S1-S{s_count}")
    check(report, f"文档口径：S 检查项数与事实源一致（S1-S{s_count}）", not drifts, "；".join(drifts))


def check_pipeline_wording(report: Report) -> None:
    """插件全树 + 四清单字段 + 仓库 evals 的流水线步数口径断言（教训：七/九/十步并存致宿主 AI 口径打架）。

    扫描范围：插件根全部 *.md、四清单 description/interface.longDescription、
    仓库根 evals/ 下全部 *.md；命中「N步(建模)流水线」后做中文/阿拉伯数字
    等价判定，唯一合法步数见 VALID_PIPELINE_STEPS（九）——已知合法命中
    "九步建模流水线""九步流水线"不得误报。

    Args:
        report: 结果收集器。
    Returns:
        None（结果记入 report）。
    """
    #   1. evals 目录在位（缺失即口径扫描静默失效，按降级拦截）
    if not EVALS_DIR.is_dir():
        report.fail("文档口径：evals 目录在位", f"缺 {EVALS_DIR}——仓库侧口径扫描失效")
    #   2. 汇总扫描文本：插件根全树 md + 四清单口径字段 + 仓库根 evals md
    texts = [(str(path.relative_to(PLUGIN_ROOT)), path.read_text(encoding="utf-8"))
             for path in PLUGIN_ROOT.rglob("*.md") if "__pycache__" not in path.parts]
    texts += _manifest_text_snippets()
    texts += [(str(path.relative_to(EVALS_DIR.parent)), path.read_text(encoding="utf-8"))
              for path in (EVALS_DIR.rglob("*.md") if EVALS_DIR.is_dir() else [])]
    #   3. 逐处核步数：数字词转整数后判定，未知数字词（含"百"等）按不可判定拦截
    violations = []
    for label, text in texts:
        for word in dict.fromkeys(m.group(1) for m in PIPELINE_STEP_RE.finditer(text)):
            steps = _cn_word_to_int(word)
            if steps not in VALID_PIPELINE_STEPS:
                actual = f"{steps} 步" if steps is not None else "不可判定数字词"
                violations.append(f"{label} 含「{word}步…流水线」（实际 {actual}，合法口径 九步）")
    check(report, "文档口径：流水线步数统一（九步）", not violations, "；".join(violations))


# ===========五、触发用例集结构检查==========
def check_trigger_cases(report: Report) -> None:
    """仓库根触发用例集（evals/trigger/*.json）结构有效性断言。

    用例集是技能触发回归的载体：目录或用例文件静默缺失即回归失效，
    一律 fail 不降级。逐技能联动断言 evals/trigger/{技能名}.json 在位
    （随技能发现自动覆盖新增技能）；每条用例必须含 query（非空字符串）、
    should_trigger（布尔）、reason（非空字符串）三键，缺键或类型错即
    列出第几条缺什么。

    Args:
        report: 结果收集器。
    Returns:
        None（结果记入 report）。
    """
    #   1. 目录与逐技能用例文件在位（缺失即回归失效，fail 不降级）
    check(report, "触发用例集：目录在位（evals/trigger）", TRIGGER_DIR.is_dir(),
          f"缺 {TRIGGER_DIR}——技能触发回归失去载体")
    if not TRIGGER_DIR.is_dir():
        return
    for skill_dir in _skill_dirs():
        case_path = TRIGGER_DIR / f"{skill_dir.name}.json"
        check(report, f"触发用例集：{skill_dir.name} 用例文件在位", case_path.is_file(),
              f"缺 {case_path.name}——该技能触发用例静默缺失，回归失效")
    #   2. 逐文件结构断言：JSON 可解析 + 顶层为非空数组
    for case_path in sorted(TRIGGER_DIR.glob("*.json")):
        file_name = case_path.name
        try:
            cases = json.loads(case_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            report.fail(f"触发用例集：{file_name} JSON 可解析", f"解析失败：{exc}")
            continue
        if not isinstance(cases, list) or not cases:
            report.fail(f"触发用例集：{file_name} 用例为非空数组",
                        "顶层不是数组或数组为空——回归载体无效")
            continue
        #   3. 逐条三键断言：query/should_trigger/reason 齐全且类型正确，缺啥指名第几条
        problems = []
        for idx, case in enumerate(cases, start=1):
            if not isinstance(case, dict):
                problems.append(f"第 {idx} 条不是 JSON 对象")
                continue
            if not (isinstance(case.get("query"), str) and case["query"]):
                problems.append(f"第 {idx} 条 query 缺失或不是非空字符串")
            if not isinstance(case.get("should_trigger"), bool):
                problems.append(f"第 {idx} 条 should_trigger 缺失或不是布尔")
            if not (isinstance(case.get("reason"), str) and case["reason"]):
                problems.append(f"第 {idx} 条 reason 缺失或不是非空字符串")
        check(report, f"触发用例集：{file_name} 三键齐全且类型正确（{len(cases)} 条）",
              not problems, "；".join(problems))


# ===========六、范例门禁检查==========
def _run_tool(script: Path, args: list) -> subprocess.CompletedProcess:
    """以子进程实跑插件脚本并捕获输出（范例门禁脚本级断言的统一入口）。

    Args:
        script: 插件脚本路径（以 sys.executable 执行，与当前解释器同源）。
        args: 传给脚本的参数列表（路径一律传绝对路径，断言不依赖 cwd）。
    Returns:
        CompletedProcess（stdout/stderr 已按 utf-8 解码为文本；目标脚本均
        自带 sys.stdout.reconfigure(encoding="utf-8")，管道输出无乱码）。
    """
    return subprocess.run([sys.executable, str(script)] + [str(a) for a in args],
                          capture_output=True, text=True, encoding="utf-8")


def _tool_fail_detail(proc: subprocess.CompletedProcess, expected_line: str) -> str:
    """组装脚本级断言的失败明细（退出码 + 期望行 + stdout 尾部）。

    Args:
        proc: _run_tool 返回的子进程结果。
        expected_line: 断言要求出现的关键输出行（中文）。
    Returns:
        形如「退出码 1，期望行「…」，stdout 尾部：…」的明细文本。
    """
    tail = (proc.stdout or "")[-200:]
    return f"退出码 {proc.returncode}，期望行「{expected_line}」，stdout 尾部：{tail}"


def _structure_name_sets(model: dict) -> dict:
    """从 DSL 模型提取结构等价比较用的三个名称集合（实体/规则/能力问题）。

    Args:
        model: yaml.safe_load 解析后的 DSL 模型（dict）。
    Returns:
        {维度名: 名称集合}——实体名取 entities 键集合，规则名取 rules[].name，
        能力问题 id 取 competency_questions[].id。
    """
    return {
        "实体名": set((model.get("entities") or {}).keys()),
        "规则名": {str(r.get("name")) for r in (model.get("rules") or [])},
        "能力问题 id": {str(q.get("id")) for q in (model.get("competency_questions") or [])},
    }


def check_examples(report: Report) -> None:
    """黄金范例（examples/supplier-recon）受门禁断言：关键文件在位 + 门禁命令逐条实跑。

    范例 README 第六节声明「改动范例后须重过门禁」——本函数把该口头约定固化为
    机器断言（探索记录可交接、DSL 过 lint、CQ 全解析、编译幂等、拓扑同步、
    与评测黄金答案结构等价、勾选模板与门禁节在位）。任一断言失败即范例不可再
    被当作对照物，等同插件回归失败。check_dist 是发布前手动跑的门禁、非高频
    CI，每次都真跑脚本（运行成本可接受，本函数不做缓存）。

    Args:
        report: 结果收集器。
    Returns:
        None（结果记入 report；脚本/范例/模板缺失、退出码非 0、关键输出行缺失
        都 fail 指名，不得 SKIP、不得"文件不存在就跳过"）。
    """
    #   1. 范例域目录与关键文件在位（缺一即 fail 指名）
    check(report, "范例门禁：域目录在位（examples/supplier-recon）", EXAMPLE_DOMAIN_DIR.is_dir(),
          f"缺 {EXAMPLE_DOMAIN_DIR.relative_to(PLUGIN_ROOT)}——黄金范例整体缺失")
    for rel in EXAMPLE_REQUIRED_FILES:
        check(report, f"范例门禁：{rel} 在位", (EXAMPLE_DOMAIN_DIR / rel).is_file(),
              f"缺 examples/supplier-recon/{rel}")

    #   2. 探索记录可交接（check_exploration.py 退出 0 + 可交接结论行）
    proc = _run_tool(CHECK_EXPLORATION_PY, [EXAMPLE_EXPLORATION_YAML])
    check(report, "范例门禁：探索记录可交接建模",
          proc.returncode == 0 and EXPLORATION_HANDOFF_LINE in (proc.stdout or ""),
          _tool_fail_detail(proc, EXPLORATION_HANDOFF_LINE))

    #   3. DSL 过 lint（lint_model.py 退出 0 + 零错零警结论行）
    proc = _run_tool(LINT_MODEL_PY, [EXAMPLE_MODEL_YAML])
    check(report, "范例门禁：DSL 过 lint（error 0 / warning 0）",
          proc.returncode == 0 and LINT_CLEAN_LINE in (proc.stdout or ""),
          _tool_fail_detail(proc, LINT_CLEAN_LINE))

    #   4. CQ 全解析（check_cq.py 退出 0 + 不可解析引用 0 处结论行）
    proc = _run_tool(CHECK_CQ_PY, [EXAMPLE_MODEL_YAML])
    check(report, "范例门禁：CQ 全解析（不可解析引用 0 处）",
          proc.returncode == 0 and CQ_RESOLVED_LINE in (proc.stdout or ""),
          _tool_fail_detail(proc, CQ_RESOLVED_LINE))

    #   5. 编译幂等：临时目录连续编译两次，三产物逐文件 sha256 相等
    with tempfile.TemporaryDirectory() as td1, tempfile.TemporaryDirectory() as td2:
        proc1 = _run_tool(COMPILE_MODEL_PY, [EXAMPLE_MODEL_YAML, "--target", "both", "-o", td1])
        proc2 = _run_tool(COMPILE_MODEL_PY, [EXAMPLE_MODEL_YAML, "--target", "both", "-o", td2])
        check(report, "范例门禁：编译可完成（两次退出码均 0）",
              proc1.returncode == 0 and proc2.returncode == 0,
              f"第一次退出码 {proc1.returncode}、第二次退出码 {proc2.returncode}，"
              f"stderr 尾部：{(proc1.stderr or proc1.stdout or '')[-200:]}")
        compile_ok = proc1.returncode == 0 and proc2.returncode == 0
        for name in COMPILE_BUNDLE_FILES:
            f1, f2 = Path(td1) / name, Path(td2) / name
            if compile_ok and f1.is_file() and f2.is_file():
                check(report, f"范例门禁：编译幂等——{name} 两次 sha256 一致",
                      hashlib.sha256(f1.read_bytes()).hexdigest()
                      == hashlib.sha256(f2.read_bytes()).hexdigest(),
                      f"{name} 两次编译产物 sha256 不一致——编译非确定性")
            else:
                report.fail(f"范例门禁：编译幂等——{name} 两次 sha256 一致",
                            "编译未完成或产物缺失，sha256 无法比较")

    #   6. 拓扑同步：临时目录重渲染 topology.md 与仓库内版本逐字节一致（范例声明过"topology.md 与 DSL 保持同步"）
    with tempfile.TemporaryDirectory() as td:
        out_md = Path(td) / "topology.md"
        proc = _run_tool(RENDER_TOPOLOGY_PY, [EXAMPLE_MODEL_YAML, "-o", out_md])
        sync_ok = (proc.returncode == 0 and out_md.is_file() and EXAMPLE_TOPOLOGY_MD.is_file()
                   and hashlib.sha256(out_md.read_bytes()).hexdigest()
                   == hashlib.sha256(EXAMPLE_TOPOLOGY_MD.read_bytes()).hexdigest())
        check(report, "范例门禁：拓扑同步（topology.md 与 DSL 一致）", sync_ok,
              f"退出码 {proc.returncode}——重渲染产物与仓库内 topology.md 不一致"
              f"（范例侧在位：{EXAMPLE_TOPOLOGY_MD.is_file()}）")

    #   7. 结构等价防漂移：范例与评测黄金答案的实体名/规则名/能力问题 id 三集合完全一致
    if not (GOLD_MODEL_YAML.is_file() and EXAMPLE_MODEL_YAML.is_file()):
        missing = "评测黄金答案" if not GOLD_MODEL_YAML.is_file() else "范例"
        report.fail("范例门禁：结构等价可比较（黄金答案与范例 model.yaml 均在位）",
                    f"缺 {missing} model.yaml——结构等价断言失去对照源")
    else:
        example_sets = _structure_name_sets(yaml.safe_load(EXAMPLE_MODEL_YAML.read_text(encoding="utf-8")))
        gold_sets = _structure_name_sets(yaml.safe_load(GOLD_MODEL_YAML.read_text(encoding="utf-8")))
        for label, ex_set in example_sets.items():
            gold_set = gold_sets[label]
            check(report, f"范例门禁：结构等价——{label}集合与黄金答案一致（{len(ex_set)} 项）",
                  ex_set == gold_set,
                  f"范例多出 {sorted(ex_set - gold_set)}，范例缺失 {sorted(gold_set - ex_set)}")

    #   8. 缺口探索勾选模板在位且占位符齐全（render_explore_checklist.py 的代入依赖，与 cq-checklist 断言同款）
    if EXPLORE_CHECKLIST_HTML.is_file():
        tpl_text = EXPLORE_CHECKLIST_HTML.read_text(encoding="utf-8")
        check(report, "范例门禁：探索勾选模板在位且占位符齐全",
              all(h in tpl_text for h in EXPLORE_CHECKLIST_HOLDERS),
              "assets/explore-checklist.html 缺占位符——render_explore_checklist.py 会产出坏件")
    else:
        report.fail("范例门禁：探索勾选模板在位且占位符齐全", "缺 assets/explore-checklist.html")

    #   9. 范例总导读的门禁节在位（该节是范例门禁的验收口径，防范例导读被删成"范例仅供参考"）
    if EXAMPLES_README.is_file():
        check(report, "范例门禁：范例导读的门禁节在位（范例受发布门禁保护）",
              EXAMPLES_GUARD_HEADLINE in EXAMPLES_README.read_text(encoding="utf-8"),
              "examples/README.md 缺「范例受发布门禁保护」节——范例门禁口径被删")
    else:
        report.fail("范例门禁：范例导读的门禁节在位", "缺 examples/README.md")


# ===========七、zip 产物检查==========
def check_zip(report: Report) -> None:
    """WorkBuddy zip 产物存在性、新鲜度与结构断言。

    Args:
        report: 结果收集器。
    Returns:
        None（结果记入 report；zip 为构建产物，不存在时记提示不算失败）。
    """
    zips = sorted(WORKBUDDY_DIR.glob(f"aquilair-fde-*.zip")) if WORKBUDDY_DIR.is_dir() else []
    if not zips:
        report.ok("zip 产物：未发现（发布前先跑 pack_workbuddy.py 构建后再复跑本检查）")
        return
    zip_path = zips[-1]
    #   1. 版本新鲜度：zip 文件名版本须等于清单版本（防旧包误传）
    cb_manifest = json.loads(MANIFESTS["codebuddy"].read_text(encoding="utf-8"))
    zip_version = zip_path.stem.rsplit("-", 1)[-1]
    check(report, f"zip 版本新鲜（{zip_path.name}）", zip_version == cb_manifest["version"],
          f"清单已升 v{cb_manifest['version']}，zip 仍为 v{zip_version}——重跑 pack_workbuddy.py")
    #   2. 结构断言：关键文件在位、无缓存目录、路径全正斜杠
    with zipfile.ZipFile(zip_path) as zf:
        infos = zf.infolist()
    names = [info.filename for info in infos]
    sizes = {info.filename: info.file_size for info in infos}
    for required in (".codebuddy-plugin/plugin.json", "agents/aquilair-fde.md",
                     "avatars/expert.png", "assets/mermaid.min.js",
                     "examples/supplier-recon/model.yaml"):
        check(report, f"zip 结构：{required} 在位", f"aquilair-fde/{required}" in names)
    # 渲染缓存必须真的进包，否则 WorkBuddy 分发形态下 --image 断网只剩 CDN 单路径
    asset_entry = "aquilair-fde/assets/mermaid.min.js"
    check(report, "zip 结构：渲染缓存非空（断网兜底生效）",
          sizes.get(asset_entry, 0) >= MERMAID_ASSET_MIN_BYTES,
          f"包内 {asset_entry} 缺失或仅 {sizes.get(asset_entry, 0)} 字节")
    check(report, "zip 结构：无 __pycache__", not any("__pycache__" in n for n in names))
    check(report, "zip 结构：路径全正斜杠", not any("\\" in n for n in names))
    check(report, "zip 结构：含 scripts/（宿主通用）", any(n.startswith("aquilair-fde/scripts/") for n in names))


# ===========八、模块入口==========
def main() -> int:
    """命令行入口：跑全部分发结构检查。

    Args:
        无。
    Returns:
        进程退出码：0=全部通过，1=任一断言失败。
    """
    report = Report()
    check_manifests(report)
    check_manifest_version_refs(report)
    check_agent_frontmatter(report)
    check_skills(report)
    check_skill_spec_conformance(report)
    check_mermaid(report)
    check_lint_count_wording(report)
    check_s_count_wording(report)
    check_pipeline_wording(report)
    check_trigger_cases(report)
    check_examples(report)
    check_zip(report)
    print(report.summary())
    return 0 if report.done else 1


if __name__ == "__main__":
    sys.exit(main())
