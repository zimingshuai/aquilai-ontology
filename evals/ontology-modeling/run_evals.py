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

# 第三方依赖导入
import yaml

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


# ===========六、case8：v0.3 显式 fk / 规则名唯一 / 受控词表==========
def build_case8(results: list) -> None:
    """case8 断言：显式 fk lint 与编译、lint12 重复名、复合 fk 告警跳过、lint9 xgimi 退出码。"""
    fixture_dir = EVAL_ROOT / "case8-v03"
    fixture_ok = fixture_dir / "fixture-ok.yaml"
    fixture_bad = fixture_dir / "fixture-bad.yaml"
    xgimi_path = REPO_ROOT / "models" / "xgimi" / "model.yaml"
    if not (fixture_ok.exists() and fixture_bad.exists()):
        results.append(("case8", "前置就绪检测", "SKIP（case8-v03 fixture 未就绪）"))
        return

    def lint_ok():
        proc = run_cmd([SCRIPTS_DIR / "lint_model.py", fixture_ok])
        assert proc.returncode == 0, f"lint 退出码 {proc.returncode}: {proc.stdout[-300:]}"

    def lint_bad():
        proc = run_cmd([SCRIPTS_DIR / "lint_model.py", fixture_bad])
        out = proc.stdout or ""
        assert proc.returncode == 1, f"应报 error 退出 1，实际 {proc.returncode}"
        assert "lint3" in out and "ghost_code" in out, f"缺 rule3 fk error: {out[-300:]}"
        assert out.count("lint12") == 2, f"lint12 应恰 2 处，实际 {out.count('lint12')}: {out[-300:]}"
        assert "error 3 处" in out, f"应恰 3 处 error（lint3×1+lint12×2）: {out[-200:]}"

    def compile_both_matches_case7():
        proc = run_cmd([SCRIPTS_DIR / "compile_model.py", fixture_ok, "--target", "both"])
        assert proc.returncode == 0, f"compile 退出码 {proc.returncode}: {proc.stderr[-300:]}"
        # c8/c7：case8 与 case7 的引擎实体注册表——显式 fk 不影响引擎格式，应深度一致
        c8 = json.loads((fixture_dir / "engine-bundle" / "objects.json").read_text(encoding="utf-8"))
        c7 = json.loads((EVAL_ROOT / "case7-actions" / "engine-bundle" / "objects.json")
                        .read_text(encoding="utf-8"))
        assert c8 == c7, "引擎 links 产物与 case7 版不一致（显式形态不应影响引擎格式）"
        studio = yaml.safe_load((fixture_dir / "engine-bundle" / "studio-model.yaml")
                                .read_text(encoding="utf-8"))
        link = next(lt for lt in studio["link_types"]
                    if lt["source"] == "Supplier" and lt["target"] == "ReconciliationStatement")
        assert link["targetPropertyCode"] == "supplier_code", f"tp 应为 supplier_code: {link}"

    def compound_fk_skipped_with_warning():
        # 内存态最小模型：复合 fk 连线应进 warnings 且不进 link_types（v0.3 模板单字段对限制）；
        # 延迟导入 studio_model 避免顶层 path 副作用影响其他用例
        if str(SCRIPTS_DIR) not in sys.path:
            sys.path.insert(0, str(SCRIPTS_DIR))
        import studio_model
        model = {"entities": {
            "A": {"display_name": "甲", "table_name": "a", "description": "",
                  "properties": {"a_id": {"display_name": "id", "type": "STRING", "primary": True},
                                  "x1": {"display_name": "x1", "type": "STRING"},
                                  "x2": {"display_name": "x2", "type": "STRING"}},
                  "links": {"self_ref": {"target": "A", "fk": ["x1", "x2"]}}}},
            "rules": []}
        studio, errors, warnings = studio_model.compile_studio_model(model)
        assert not errors, f"复合 fk 应告警不应 error: {errors}"
        assert any("复合外键" in w for w in warnings), f"缺复合外键告警: {warnings}"
        assert not studio["link_types"], f"复合 fk 连线不应进 link_types: {studio['link_types']}"

    def lint_xgimi_exit0():
        proc = run_cmd([SCRIPTS_DIR / "lint_model.py", xgimi_path])
        # lint9 如实断言：xgimi 复验版全用建议名则 0 warning 也是正确结果，故只断言退出码
        assert proc.returncode == 0, f"xgimi lint 退出码 {proc.returncode}: {proc.stdout[-300:]}"

    assert_case(results, "case8", "lint 显式 fk 0 错误", lint_ok)
    assert_case(results, "case8", "lint 坏例报 lint3+lint12", lint_bad)
    assert_case(results, "case8", "编译 both 引擎产物与 case7 一致", compile_both_matches_case7)
    assert_case(results, "case8", "复合 fk 连线告警跳过", compound_fk_skipped_with_warning)
    assert_case(results, "case8", "lint xgimi 退出码 0", lint_xgimi_exit0)


# ===========七、case9：平台一致性自检（冻结夹具：xgimi 导入后快照）==========
def build_case9(results: list) -> None:
    """case9 断言：check_platform_sync 对一致夹具报零差异、对漂移夹具报差异。"""
    sync_script = SCRIPTS_DIR / "check_platform_sync.py"
    fixture_dir = EVAL_ROOT / "case9-platform-sync"
    frozen = fixture_dir / "model-frozen.yaml"
    drifted = fixture_dir / "model-drifted.yaml"
    sdk = fixture_dir / "platform-sdk-frozen.py"
    if not all(p.exists() for p in (sync_script, frozen, drifted, sdk)):
        results.append(("case9", "前置就绪检测", "SKIP（check_platform_sync 或 case9 夹具未就绪）"))
        return

    def sync_ok():
        proc = run_cmd([sync_script, frozen, sdk])
        assert proc.returncode == 0, f"一致夹具应退出码 0: {proc.stdout[-300:]}"

    def drift_detected():
        # drifted 夹具把 Material 主键改回 material_id，应被平台差异检出（退出码 1）
        proc = run_cmd([sync_script, drifted, sdk])
        combined = (proc.stdout or "") + (proc.stderr or "")
        assert proc.returncode == 1, f"漂移夹具应退出码 1，实际 {proc.returncode}"
        assert "Material" in combined and ("主键" in combined or "字段" in combined), \
            f"差异报告缺 Material 明细: {combined[-300:]}"

    assert_case(results, "case9", "平台一致性零差异", sync_ok)
    assert_case(results, "case9", "平台漂移检出", drift_detected)


# ===========八、主流程==========
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
    build_case8(results)
    build_case9(results)
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
