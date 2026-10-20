"""WorkBuddy 上传包构建：从插件根打 aquilair-fde-<version>.zip。

用途：单内容多清单架构下，WorkBuddy 分发包不再手工维护镜像目录——
     本脚本直接从插件根（plugins/ontology-forge/）按打包清单收集内容，
     版本号读 .codebuddy-plugin/plugin.json，输出到仓库 workbuddy/ 目录。
主要 Input：无必填参数（插件根按脚本位置自定位；--out 可选指定输出目录）。
主要 Output：workbuddy/aquilair-fde-<version>.zip——zip 内根目录为 aquilair-fde/，
     含 WorkBuddy 清单/总控提示词/头像/技能/种子/手册/scripts；条目路径统一
     正斜杠（避免 Windows 反斜杠导致平台解析失败）；排除 __pycache__ 与
     其他平台清单（.zcode-plugin/.claude-plugin/.codex-plugin）。
"""

import argparse
import json
import sys
import zipfile
from pathlib import Path

# PLUGIN_ROOT：插件根目录（scripts/ 的上一级）
PLUGIN_ROOT = Path(__file__).resolve().parent.parent
# CODEBUDDY_MANIFEST：WorkBuddy 清单路径（版本号来源）
CODEBUDDY_MANIFEST = PLUGIN_ROOT / ".codebuddy-plugin" / "plugin.json"
# PACKAGE_NAME：zip 内根目录名（WorkBuddy Expert 规范：插件名即目录名）
PACKAGE_NAME = "aquilair-fde"
# INCLUDE_ITEMS：打包清单——插件根下的相对目录/文件，存在才打包（缺失报错的是清单必需项）
INCLUDE_ITEMS = (
    ".codebuddy-plugin",
    "agents",
    "avatars",
    "skills",
    "seeds",
    "docs",
    "scripts",
)
# REQUIRED_ITEMS：必需项——缺一即失败（ WorkBuddy 平台解析的硬依赖）
REQUIRED_ITEMS = (".codebuddy-plugin", "agents", "avatars", "skills")
# EXCLUDED_DIRS：排除目录——Python 编译缓存不进分发包
EXCLUDED_DIRS = {"__pycache__"}
# EXCLUDED_FILES：scripts 内排除的工程性文件（脚本文档属仓库工程资产，不随包膨胀）
EXCLUDED_FILES = {"README.md"}


# ===========一、版本与清单读取==========
def read_version() -> str:
    """读 WorkBuddy 清单的版本号。

    Args:
        无。
    Returns:
        形如 "0.4.1" 的语义化版本字符串。
    Raises:
        FileNotFoundError: 清单文件不存在。
        KeyError: 清单缺 version 字段。
    """
    manifest = json.loads(CODEBUDDY_MANIFEST.read_text(encoding="utf-8"))
    return manifest["version"]


# ===========二、文件收集==========
def collect_files() -> list[str]:
    """按打包清单收集插件根下的相对文件路径。

    Args:
        无。
    Returns:
        相对插件根的正斜杠文件路径列表（已排序，保证 zip 内容可复现）。
    Raises:
        FileNotFoundError: 任一必需项缺失。
    """
    collected: list[str] = []
    for item in INCLUDE_ITEMS:
        target = PLUGIN_ROOT / item
        if not target.exists():
            if item in REQUIRED_ITEMS:
                raise FileNotFoundError(f"打包必需项缺失: {target}")
            continue
        if target.is_file():
            collected.append(item)
            continue
        for path in sorted(target.rglob("*")):
            if not path.is_file():
                continue
            if any(part in EXCLUDED_DIRS for part in path.parts):
                continue
            rel = path.relative_to(PLUGIN_ROOT).as_posix()
            if item == "scripts" and path.name in EXCLUDED_FILES:
                continue
            collected.append(rel)
    return collected


# ===========三、打包执行==========
def pack(out_dir: Path) -> Path:
    """构建 WorkBuddy 上传 zip。

    Args:
        out_dir: zip 输出目录（不存在则创建）。
    Returns:
        生成的 zip 文件路径。
    Raises:
        FileNotFoundError: 必需项缺失（由 collect_files 抛出）。
    """
    version = read_version()
    files = collect_files()
    out_dir.mkdir(parents=True, exist_ok=True)
    zip_path = out_dir / f"{PACKAGE_NAME}-{version}.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for rel in files:
            # zip 内路径：aquilair-fde/<相对路径>，统一正斜杠
            zf.write(PLUGIN_ROOT / rel, f"{PACKAGE_NAME}/{rel}")
    return zip_path


# ===========四、模块入口==========
def main() -> int:
    """命令行入口：构建并报告结果。

    Args:
        无。
    Returns:
        进程退出码：0=成功，1=失败。
    """
    parser = argparse.ArgumentParser(description="构建 WorkBuddy 上传 zip")
    # --out：可选输出目录，默认仓库根 workbuddy/（构建产物区）
    parser.add_argument("--out", type=Path, default=PLUGIN_ROOT.parent.parent / "workbuddy", help="zip 输出目录（默认仓库 workbuddy/）")
    args = parser.parse_args()
    try:
        zip_path = pack(args.out)
    except (FileNotFoundError, KeyError, json.JSONDecodeError) as exc:
        print(f"====打包失败====: {exc}")
        return 1
    size_kb = zip_path.stat().st_size // 1024
    print(f"====打包完成====: {zip_path}（{size_kb}KB，{len(collect_files())} 个文件）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
