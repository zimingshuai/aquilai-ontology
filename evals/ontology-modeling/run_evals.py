"""建模行为回归体系：机械断言自动化入口。

用途：对 evals/ontology-modeling 下的行为测试样例执行可机器判定的断言
     （lint/check_cq/compile 幂等/diff 变更集/版本冲突拒绝/动作骨架与 actions.json），
     防止技能与脚本改动导致工具链行为退化。
主要 Input：无命令行参数；样例路径与插件脚本路径按相对位置解析。
主要 Output：stdout 中文断言结果表（PASS/FAIL/SKIP）+ 汇总退出码
     （0=全部通过或跳过，1=存在 FAIL）。
"""

import hashlib
import json
import subprocess
import sys
from pathlib import Path

# eval_root：本脚本所在目录（evals/ontology-modeling）。
EVAL_ROOT = Path(__file__).resolve().parent
# repo_root：仓库根（脚本向上三级）。
REPO_ROOT = EVAL_ROOT.parent.parent
# scripts_dir：插件确定性脚本目录。
SCRIPTS_DIR = REPO_ROOT / "plugins" / "ontology-forge" / "scripts"
# gold_path：M0 基准 DSL（人工设计、v0.2 修订后）。
GOLD_PATH = REPO_ROOT / "poc" / "m0" / "goldstandard" / "gold" / "model.yaml"


# ===========一、断言工具==========
def run_cmd(args: list) -> subprocess.CompletedProcess:
    """执行子进程命令并返回结果对象。

    Args:
        args: 命令参数列表（首元素为 python 脚本路径）。
    Returns:
        subprocess.CompletedProcess，超时 120 秒抛 TimeoutExpired。
    """
    # cmd：完整命令行（python 脚本 + 参数）。
    cmd = [sys.executable, str(args[0])] + [str(a) for a in args[1:]]
    return subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", timeout=120)


def file_sha256(path: Path) -> str:
    """计算文件 SHA256（幂等性断言用）。

    Args:
        path: 目标文件路径。
    Returns:
        十六进制摘要字符串。
    """
    return hashlib.sha256(path.read_bytes()).hexdigest()


def assert_case(results: list, case: str, name: str, fn) -> None:
    """执行单条断言并登记结果（异常也登记为 FAIL，不中断整体）。

    Args:
        results: 结果收集列表（三元组 case/name/ok）。
        case: 样例编号（如 case1）。
        name: 断言名（中文）。
        fn: 无参断言函数，断言失败抛 AssertionError。
    Returns:
        None。
    """
    try:
        fn()
        results.append((case, name, "PASS"))
    except AssertionError as exc:
        results.append((case, name, f"FAIL: {exc}"))
    except Exception as exc:  # noqa: BLE001 —— 回归脚本需把任何异常都登记为 FAIL
        results.append((case, name, f"FAIL(异常): {exc}"))


# ===========二、case1：从零生成（机械断言）==========
def build_case1(results: list) -> None:
    """case1 断言：gold 基准 lint 零错、CQ 全解析、编译幂等。"""
    def lint_ok():
        proc = run_cmd([SCRIPTS_DIR / "lint_model.py", GOLD_PATH])
        assert proc.returncode == 0, f"lint 退出码 {proc.returncode}: {proc.stdout[-200:]}"

    def cq_ok():
        proc = run_cmd([SCRIPTS_DIR / "check_cq.py", GOLD_PATH])
        assert proc.returncode == 0, f"CQ 退出码 {proc.returncode}: {proc.stdout[-200:]}"

    def compile_idempotent():
        out_dir = GOLD_PATH.parent / "engine-bundle"
        run_cmd([SCRIPTS_DIR / "compile_model.py", GOLD_PATH])
        # hash1：第一次编译产物摘要。
        hash1 = file_sha256(out_dir / "objects.json")
        run_cmd([SCRIPTS_DIR / "compile_model.py", GOLD_PATH])
        # hash2：第二次编译产物摘要，应与第一次一致（幂等）。
        hash2 = file_sha256(out_dir / "objects.json")
        assert hash1 == hash2, "两次编译 objects.json 摘要不一致（幂等性破坏）"

    assert_case(results, "case1", "lint 基准 0 错误", lint_ok)
    assert_case(results, "case1", "CQ 引用全解析", cq_ok)
    assert_case(results, "case1", "编译幂等", compile_idempotent)


# ===========三、case2：增量变更集（条件执行，依赖 fixture 与 diff_model）==========
def build_case2(results: list) -> None:
    """case2 断言：diff 产出 5 类操作、breaking=2、changeset 幂等。"""
    diff_script = SCRIPTS_DIR / "diff_model.py"
    fixture = EVAL_ROOT / "case2-incremental" / "gold-v2.yaml"
    if not diff_script.exists() or not fixture.exists():
        results.append(("case2", "前置就绪检测", "SKIP（diff_model 或 fixture 未就绪，M2 脚本子代理交付后启用）"))
        return

    def diff_ops():
        proc = run_cmd([diff_script, GOLD_PATH, fixture])
        assert proc.returncode == 0, f"diff 退出码 {proc.returncode}: {proc.stdout[-300:]}"
        cs_path = fixture.parent / "changeset.json"
        assert cs_path.exists(), "未生成 changeset.json"
        # text：变更集原文（幂等断言复用）。
        text = cs_path.read_text(encoding="utf-8")
        for op in ("\"add\"", "\"remove\"", "\"replace\""):
            assert op in text, f"缺少 {op} 操作"
        assert text.count("\"op\"") == 5, f"操作数应为 5，实际 {text.count(chr(34) + 'op' + chr(34))}"

    def breaking_count():
        proc = run_cmd([diff_script, GOLD_PATH, fixture])
        # breaking 行数：错误信息中 breaking 条目说明。
        assert proc.returncode == 0
        cs = (fixture.parent / "changeset.json").read_text(encoding="utf-8")
        assert "\"breaking\"" in cs and "\"reason\"" in cs, "breaking 清单缺失"

    def diff_idempotent():
        cs_path = fixture.parent / "changeset.json"
        run_cmd([diff_script, GOLD_PATH, fixture])
        # hash1/hash2：两次 diff 产物摘要。
        hash1 = file_sha256(cs_path)
        run_cmd([diff_script, GOLD_PATH, fixture])
        hash2 = file_sha256(cs_path)
        assert hash1 == hash2, "两次 diff 产物不一致（changeset_id 未做稳定 hash）"

    assert_case(results, "case2", "变更集 5 类操作", diff_ops)
    assert_case(results, "case2", "breaking 清单存在", breaking_count)
    assert_case(results, "case2", "变更集幂等", diff_idempotent)


# ===========四、case4：版本冲突拒绝==========
def build_case4(results: list) -> None:
    """case4 断言：base-version 不匹配时 diff 拒绝且提示重新生成。"""
    diff_script = SCRIPTS_DIR / "diff_model.py"
    if not diff_script.exists():
        results.append(("case4", "前置就绪检测", "SKIP（diff_model 未就绪）"))
        return

    def reject_mismatch():
        proc = run_cmd([diff_script, GOLD_PATH, GOLD_PATH, "--base-version", "0.0.9-不存在"])
        combined = (proc.stdout or "") + (proc.stderr or "")
        assert proc.returncode == 1, f"应拒绝退出码 1，实际 {proc.returncode}"
        assert "重新生成" in combined or "重新" in combined, f"错误信息缺'重新生成'指引: {combined[-200:]}"

    assert_case(results, "case4", "base_version 不匹配拒绝", reject_mismatch)


# ===========五、case7：动作编译目标（骨架生成 + actions.json + lint 10/11）==========
def build_case7(results: list) -> None:
    """case7 断言：骨架 py_compile、actions.json 结构、lint 第 10/11 条、gold 编译回归。"""
    gen_script = SCRIPTS_DIR / "gen_action_skeleton.py"
    fixture_dir = EVAL_ROOT / "case7-actions"
    gold_actions = fixture_dir / "gold-actions.yaml"
    if not (gen_script.exists() and gold_actions.exists()):
        results.append(("case7", "前置就绪检测", "SKIP（gen_action_skeleton 或 case7 fixture 未就绪）"))
        return

    def lint_gold_actions():
        proc = run_cmd([SCRIPTS_DIR / "lint_model.py", gold_actions])
        assert proc.returncode == 0, f"lint 退出码 {proc.returncode}: {proc.stdout[-300:]}"

    def skeleton_py_compile():
        proc = run_cmd([gen_script, gold_actions])
        assert proc.returncode == 0, f"骨架生成退出码 {proc.returncode}: {proc.stderr[-300:]}"
        skeletons = sorted((gold_actions.parent / "engine-bundle" / "actions").glob("*.py"))
        assert skeletons, "未生成任何骨架文件"
        # 骨架与生成器自身全部 py_compile（语法合法，不依赖引擎环境；run_cmd 自动前置 python）
        for py_file in [gen_script] + skeletons:
            proc = run_cmd(["-m", "py_compile", py_file])
            assert proc.returncode == 0, f"py_compile 失败 {py_file.name}: {proc.stderr[-200:]}"
        body = skeletons[0].read_text(encoding="utf-8")
        assert "TODO(人工插桩)" in body, "骨架缺少 TODO(人工插桩) 插桩标记"
        assert "def freeze_supplier(" in body and "@action" in body, "骨架缺 @action 装饰器或函数定义"

    def actions_json_shape():
        proc = run_cmd([SCRIPTS_DIR / "compile_model.py", gold_actions, "--target", "engine"])
        assert proc.returncode == 0, f"compile 退出码 {proc.returncode}: {proc.stderr[-300:]}"
        payload = json.loads((gold_actions.parent / "engine-bundle" / "actions.json").read_text(encoding="utf-8"))
        assert len(payload["actions"]) == 1, f"actions 数应为 1，实际 {len(payload['actions'])}"
        entry = payload["actions"][0]
        assert entry["action_name"] == "freeze_supplier"
        assert set(entry) == {"action_name", "description", "parameters", "supports_sandbox", "body"}, \
            f"action 键集不符: {sorted(entry)}"
        assert "@action" in entry["body"] and "def freeze_supplier" in entry["body"], "body 非骨架源码"
        assert payload["sandbox_execution"]["parameter"] == "sandbox", "sandbox_execution 结构缺失"

    def gold_engine_regression():
        # gold 编译回归：both 重编译全部产物与既有 engine-bundle 字节级一致（无 actions 不产 actions.json）
        bundle = GOLD_PATH.parent / "engine-bundle"
        before = {p.name: file_sha256(p) for p in sorted(bundle.glob("*")) if p.is_file()}
        proc = run_cmd([SCRIPTS_DIR / "compile_model.py", GOLD_PATH])
        assert proc.returncode == 0, f"gold 编译退出码 {proc.returncode}: {proc.stderr[-200:]}"
        after = {p.name: file_sha256(p) for p in sorted(bundle.glob("*")) if p.is_file()}
        diff = {k for k in set(before) | set(after) if before.get(k) != after.get(k)}
        assert before == after, f"gold 产物回归破坏，差异文件: {sorted(diff)}"

    def lint_bad_fixture(bad_name: str, expect_tag: str):
        proc = run_cmd([SCRIPTS_DIR / "lint_model.py", fixture_dir / bad_name])
        combined = proc.stdout or ""
        assert proc.returncode == 1, f"{bad_name} 应报 error 退出 1，实际 {proc.returncode}"
        assert expect_tag in combined, f"{bad_name} 输出缺 {expect_tag}: {combined[-300:]}"
        assert "error 1 处" in combined, f"{bad_name} 应精确 1 处 error: {combined[-200:]}"

    assert_case(results, "case7", "lint gold-actions 0 错误", lint_gold_actions)
    assert_case(results, "case7", "骨架生成 py_compile 通过", skeleton_py_compile)
    assert_case(results, "case7", "actions.json 结构对齐", actions_json_shape)
    assert_case(results, "case7", "gold 编译产物回归不变", gold_engine_regression)
    assert_case(results, "case7", "坏fixture 报 lint10", lambda: lint_bad_fixture("bad-action-ref.yaml", "lint10"))
    assert_case(results, "case7", "坏fixture 报 lint11", lambda: lint_bad_fixture("bad-param-ref.yaml", "lint11"))


# ===========六、主流程==========
def main() -> int:
    """执行全部机械断言并输出结果表。

    Returns:
        0=无 FAIL（PASS 与 SKIP 均视为通过），1=存在 FAIL。
    """
    # results：三元组收集列表（case/断言名/结果）。
    results: list = []
    build_case1(results)
    build_case2(results)
    build_case4(results)
    build_case7(results)
    print("\n====evals 回归结果====")
    for case, name, status in results:
        print(f"[{case}] {name}: {status}")
    # fail_count：FAIL 条目数。
    fail_count = sum(1 for _, _, s in results if s.startswith("FAIL"))
    print(f"====汇总====: PASS {sum(1 for _, _, s in results if s == 'PASS')} | "
          f"FAIL {fail_count} | SKIP {sum(1 for _, _, s in results if s.startswith('SKIP'))}")
    return 1 if fail_count else 0


if __name__ == "__main__":
    sys.exit(main())
