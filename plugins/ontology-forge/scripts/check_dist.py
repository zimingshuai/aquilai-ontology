"""分发结构门禁：多平台清单合规 + frontmatter 必填 + 渲染缓存与版本锁 + zip 结构断言。

用途：发布/打包前自检（教训沉淀：WorkBuddy 首次上传因缺 avatars 与 description
     两次被平台拒收，均属"机器可判定"的合规项——本脚本把它们固化为断言闸门；
     另含 mermaid 缓存随包与版本锁一致性，避免断网兜底失效与跨端渲染漂移）。
主要 Input：无必填参数（插件根按脚本位置自定位）。
主要 Output：stdout 中文逐项检查报告；退出码 0=全部通过，1=任一断言失败
     （含"zip 产物版本落后于清单"的过期检查——防止旧包被误传平台）。
"""

import json
import re
import sys
import zipfile
from pathlib import Path

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


def check_skills(report: Report) -> None:
    """技能目录自动发现 + SKILL.md frontmatter 断言。

    Args:
        report: 结果收集器。
    Returns:
        None（结果记入 report）。
    """
    skill_dirs = [p for p in sorted(SKILLS_DIR.iterdir()) if (p / "SKILL.md").is_file()]
    check(report, f"技能发现 {len(skill_dirs)} 个（frontmatter 合规）", bool(skill_dirs), "skills/ 下无 SKILL.md")
    for skill_dir in skill_dirs:
        match = re.match(r"^---\n(.*?)\n---", (skill_dir / "SKILL.md").read_text(encoding="utf-8"), re.S)
        meta = yaml.safe_load(match.group(1)) if match else {}
        valid = bool(meta.get("name") == skill_dir.name and meta.get("description"))
        check(report, f"技能 {skill_dir.name}: name 与目录一致 + description 存在", valid,
              f"name={meta.get('name')}")


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
def check_pipeline_wording(report: Report) -> None:
    """全插件 Markdown 的流水线步数口径断言（教训：七/九/十步并存致宿主 AI 口径打架）。

    Args:
        report: 结果收集器。
    Returns:
        None（结果记入 report）。
    """
    # forbidden：禁止的步数连写——建模流水线唯一口径是"九步"（ontology-modeling SKILL.md §三）
    forbidden = ("七步流水线", "十步流水线")
    md_files = [p for p in PLUGIN_ROOT.rglob("*.md") if "__pycache__" not in p.parts]
    hits = [f"{path.relative_to(PLUGIN_ROOT)} 含「{phrase}」"
            for path in md_files for phrase in forbidden
            if phrase in path.read_text(encoding="utf-8")]
    check(report, "文档口径：流水线步数统一（无七步/十步残留）", not hits, "；".join(hits))


# ===========五、zip 产物检查==========
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
                     "avatars/expert.png", "assets/mermaid.min.js"):
        check(report, f"zip 结构：{required} 在位", f"aquilair-fde/{required}" in names)
    # 渲染缓存必须真的进包，否则 WorkBuddy 分发形态下 --image 断网只剩 CDN 单路径
    asset_entry = "aquilair-fde/assets/mermaid.min.js"
    check(report, "zip 结构：渲染缓存非空（断网兜底生效）",
          sizes.get(asset_entry, 0) >= MERMAID_ASSET_MIN_BYTES,
          f"包内 {asset_entry} 缺失或仅 {sizes.get(asset_entry, 0)} 字节")
    check(report, "zip 结构：无 __pycache__", not any("__pycache__" in n for n in names))
    check(report, "zip 结构：路径全正斜杠", not any("\\" in n for n in names))
    check(report, "zip 结构：含 scripts/（宿主通用）", any(n.startswith("aquilair-fde/scripts/") for n in names))


# ===========六、模块入口==========
def main() -> int:
    """命令行入口：跑全部分发结构检查。

    Args:
        无。
    Returns:
        进程退出码：0=全部通过，1=任一断言失败。
    """
    report = Report()
    check_manifests(report)
    check_agent_frontmatter(report)
    check_skills(report)
    check_mermaid(report)
    check_pipeline_wording(report)
    check_zip(report)
    print(report.summary())
    return 0 if report.done else 1


if __name__ == "__main__":
    sys.exit(main())
