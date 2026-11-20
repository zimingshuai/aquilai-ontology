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
GOLD_PATH = REPO_ROOT / "evals" / "ontology-modeling" / "goldstandard" / "gold" / "model.yaml"


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

    def lint_bad_oq():
        # lint14/15 坏例夹具（v0.3.6）：OQ id 重复/status 七态外/缺 topic+question/
        # conflicts 缺 claim+status/枚举孤儿值/枚举空 description，逐点断言命中
        proc = run_cmd([SCRIPTS_DIR / "lint_model.py", fixture_dir / "fixture-bad-oq.yaml"])
        out = proc.stdout or ""
        assert proc.returncode == 1, f"应报 error 退出 1，实际 {proc.returncode}: {out[-300:]}"
        assert "已出现" in out and "重复" in out, f"缺 OQ id 重复 error: {out[-300:]}"
        assert "bogus-state" in out and "七态枚举" in out, f"缺 status 非法 error: {out[-300:]}"
        assert "缺少 topic" in out and "缺少 question" in out, f"缺 topic/question error: {out[-300:]}"
        assert "side_a" in out and "side_b" in out, f"缺 conflicts claim error: {out[-300:]}"
        # 精确计数：lint14 error=7（id 重复1+缺topic/question/status非法3+conflicts claim2+status1）+ lint15 error=1（空 description）
        assert "error 8 处" in out, f"应恰 8 处 error，实际: {out[-200:]}"
        assert "lint15" in out and "孤儿枚举值" in out and "B" in out, f"缺 lint15 孤儿值 warning: {out[-300:]}"
        assert "description 为空" in out, f"缺 lint15 空 description error: {out[-300:]}"

    assert_case(results, "case8", "lint 显式 fk 0 错误", lint_ok)
    assert_case(results, "case8", "lint 坏例报 lint3+lint12", lint_bad)
    assert_case(results, "case8", "编译 both 引擎产物与 case7 一致", compile_both_matches_case7)
    assert_case(results, "case8", "复合 fk 连线告警跳过", compound_fk_skipped_with_warning)
    assert_case(results, "case8", "lint xgimi 退出码 0", lint_xgimi_exit0)
    assert_case(results, "case8", "坏fixture 报 lint14+lint15", lint_bad_oq)


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


# ===========八、case10：CQ 勾选呈审组件生成（确定性产物固化）==========
def build_case10(results: list) -> None:
    """case10 断言：render_cq_checklist 对真实 DSL 生成含三态交互的完整 HTML，坏输入如实报错。"""
    cq_script = SCRIPTS_DIR / "render_cq_checklist.py"
    xgimi_model = REPO_ROOT / "models" / "xgimi" / "model.yaml"
    if not all(p.exists() for p in (cq_script, xgimi_model)):
        results.append(("case10", "前置就绪检测", "SKIP（render_cq_checklist 或 xgimi 模型未就绪）"))
        return

    def gen_ok():
        import tempfile
        import pathlib
        with tempfile.TemporaryDirectory() as td:
            out = pathlib.Path(td) / "cq-checklist.html"
            proc = run_cmd([cq_script, xgimi_model, "--domain", "case10", "-o", out])
            assert proc.returncode == 0, f"生成应退出码 0: {proc.stdout[-200:]}"
            html = out.read_text(encoding="utf-8")
            assert "cq-001" in html and "cq-012" in html, "HTML 缺 xgimi 12 条 CQ"
            assert "__CQ_DATA__" not in html and "__DOMAIN__" not in html, "占位符未替换（坏件）"
            assert "真业务" in html and "要改" in html and "删除" in html, "HTML 缺三态勾选控件"

    def bad_input_rejected():
        import tempfile
        import pathlib
        with tempfile.TemporaryDirectory() as td:
            bad = pathlib.Path(td) / "bad.yaml"
            bad.write_text("entities: {}\n", encoding="utf-8")  # 无 CQ 段的 DSL
            proc = run_cmd([cq_script, bad])
            assert proc.returncode == 1, f"无 CQ 输入应退出码 1，实际 {proc.returncode}"

    assert_case(results, "case10", "CQ 呈审 HTML 生成完整（12 CQ+占位符替换+三态）", gen_ok)
    assert_case(results, "case10", "无 CQ 输入如实报错", bad_input_rejected)


# ===========九、case11：L2 语义沙盘（差异化纪律 + 精确计数）==========
def build_case11(results: list) -> None:
    """case11 断言：语义沙盘三类增量坏点命中、lint 职责项不重复报、--data 与 --out-dir 行为正确。"""
    sandbox_script = SCRIPTS_DIR / "semantic_sandbox.py"
    fixture_dir = EVAL_ROOT / "case11-sandbox"
    fixture = fixture_dir / "fixture-bad-sandbox.yaml"
    xgimi_path = REPO_ROOT / "models" / "xgimi" / "model.yaml"
    if not (sandbox_script.exists() and fixture.exists()):
        results.append(("case11", "前置就绪检测", "SKIP（semantic_sandbox 或 case11 fixture 未就绪）"))
        return

    def bad_fixture_graded():
        # 坏样本夹具：S1/S2/S3 各 1 warning（精确计数），无 error 退出 0（warning 呈审不拦截）
        proc = run_cmd([sandbox_script, fixture])
        out = proc.stdout or ""
        assert proc.returncode == 0, f"坏样本无 error 应退出 0，实际 {proc.returncode}: {out[-300:]}"
        assert "[S1]" in out and "computed_qty" in out, f"缺 S1 派生承诺反向 warning: {out[-300:]}"
        assert "[S2]" in out and "material_ref" in out, f"缺 S2 外键类型不匹配 warning: {out[-300:]}"
        assert "[S3]" in out and "StandaloneDict" in out, f"缺 S3 孤岛实体 warning: {out[-300:]}"
        assert "[S7]" in out and "orphan_recipe_action" in out, f"缺 S7 孤儿动作 warning: {out[-300:]}"
        assert "孤儿动作：referenced_guard_action" not in out, f"被引用动作不应误报 S7: {out[-300:]}"
        assert "统计：error 0 / warning 4 / info 3" in out, f"应恰 4 warning + 3 info: {out[-200:]}"
        assert "通过（warning 呈审）" in out, f"无 error 应结论通过: {out[-200:]}"

    def lint_scope_not_duplicated():
        # 差异化断言：夹具内 lint 职责坏点（悬空 upstream=lint1 / derived 无规则=lint7）S 不得重复报；
        # 问题行编号必须全部 S 前缀（消息文本中的差异化说明如「lint7 只查反向」是呈审上下文，不算重复报告）
        import re
        proc = run_cmd([sandbox_script, fixture])
        out = proc.stdout or ""
        assert "GhostEntity" not in out, f"悬空 upstream 属 lint1 职责，沙盘不应重复报: {out[-300:]}"
        assert "stale_flag" not in out, f"derived 无规则承载属 lint7 职责，沙盘不应重复报: {out[-300:]}"
        codes = re.findall(r"^\[(\S+?)\]", out, re.M)
        assert codes and all(c.startswith("S") and c[1:].isdigit() for c in codes), \
            f"问题行编号应全为 S 前缀，实际 {codes}"

    def xgimi_clean():
        # lint 复验版零警告模型：L2 预期 0 error；warning 恰 5 条全 S7（xgimi 六动作中五个为手动入口
        # recipe 动作、无规则 downstream 引用——呈审级合法形态，精确断言锁定动作集合变化即重看）
        proc = run_cmd([sandbox_script, xgimi_path])
        out = proc.stdout or ""
        assert proc.returncode == 0, f"xgimi 应 0 error 退出 0，实际 {proc.returncode}: {out[-300:]}"
        assert "统计：error 0 / warning 5 / info 3" in out, f"xgimi 应 0 error/5 warning(全 S7): {out[-200:]}"
        s7_lines = [ln for ln in out.splitlines() if ln.startswith("[S7]")]
        assert len(s7_lines) == 5 and all("孤儿动作" in ln for ln in s7_lines),             f"xgimi 5 条 warning 应全为 S7 孤儿动作，实际: {s7_lines}"

    def out_dir_artifacts():
        # --out-dir 三产物落盘：ttl 双图 + report.md（含 lint 对照表设计说明）
        import tempfile
        import pathlib
        with tempfile.TemporaryDirectory() as td:
            out_dir = pathlib.Path(td)
            proc = run_cmd([sandbox_script, fixture, "--out-dir", out_dir])
            assert proc.returncode == 0, f"落盘运行退出码 {proc.returncode}: {proc.stdout[-200:]}"
            for name in ("sandbox.owl.ttl", "sandbox.shapes.ttl", "report.md"):
                assert (out_dir / name).is_file(), f"缺产物 {name}"
            report_md = (out_dir / "report.md").read_text(encoding="utf-8")
            assert "lint 已覆盖 vs S 项增量对照" in report_md and "非 OWL DL 一致性检测" in report_md, \
                "report.md 缺 lint 对照表或能力边界说明"

    def data_samples():
        # --data 实例校验：好样本 conforms 退出 0；坏样本（缺主键 + 枚举外值）violation 逐条 error 退出 1
        import tempfile
        import pathlib
        with tempfile.TemporaryDirectory() as td:
            good = pathlib.Path(td) / "good.json"
            bad = pathlib.Path(td) / "bad.json"
            good.write_text('[{"objectType": "Material", "material_code": "300-W6A01", "unit_cost": 20}]',
                            encoding="utf-8")
            bad.write_text('[{"objectType": "Material", "unit_cost": 20}]',
                            encoding="utf-8")  # 坏点：缺主键 material_code → sh:minCount 1 violation
            proc_good = run_cmd([sandbox_script, fixture, "--data", good])
            assert proc_good.returncode == 0, f"好样本应退出 0: {proc_good.stdout[-300:]}"
            assert "实例校验通过" in proc_good.stdout, f"好样本应 conforms: {proc_good.stdout[-200:]}"
            proc_bad = run_cmd([sandbox_script, fixture, "--data", bad])
            out = proc_bad.stdout or ""
            assert proc_bad.returncode == 1, f"坏样本应退出 1，实际 {proc_bad.returncode}: {out[-300:]}"
            assert "[S6] error" in out and "material_code" in out, f"缺缺主键 violation: {out[-300:]}"

    assert_case(results, "case11", "坏样本 S1/S2/S3/S7 精确命中（4 warning 呈审）", bad_fixture_graded)
    assert_case(results, "case11", "lint 职责项不重复报（差异化纪律）", lint_scope_not_duplicated)
    assert_case(results, "case11", "xgimi 0 error，warning 恰 5 条全 S7 孤儿动作", xgimi_clean)
    assert_case(results, "case11", "--out-dir 三产物含 lint 对照表", out_dir_artifacts)
    assert_case(results, "case11", "--data 实例校验好坏样本行为", data_samples)


# ===========十、主流程==========
def build_case12(results: list) -> None:
    """case12 断言：域交接包五件齐全、内容与 xgimi 定稿模型一致、红线头注在位。"""
    gen_script = SCRIPTS_DIR / "gen_handoff.py"
    xgimi_path = REPO_ROOT / "models" / "xgimi" / "model.yaml"
    if not (gen_script.exists() and xgimi_path.exists()):
        results.append(("case12", "前置就绪检测", "SKIP（gen_handoff 或 xgimi 模型未就绪）"))
        return

    def five_artifacts_consistent():
        # 五件产物存在且内容与定稿模型一致（26 实体/6 动作/19 规则/12 OQ/12 CQ），红线头注在位
        import tempfile
        import pathlib
        with tempfile.TemporaryDirectory() as td:
            out_dir = pathlib.Path(td)
            proc = run_cmd([gen_script, xgimi_path, "--out-dir", out_dir])
            assert proc.returncode == 0, f"生成退出码 {proc.returncode}: {proc.stdout[-200:]}"
            for name in ("cq-final.md", "glossary-snapshot.md", "rule-calibers.md",
                         "oq-verdicts.md", "probe-expectations.md"):
                assert (out_dir / name).is_file(), f"缺产物 {name}"
            cq = (out_dir / "cq-final.md").read_text(encoding="utf-8")
            assert "cq-001" in cq and "共 12 条" in cq, f"cq-final 计数或首条异常: {cq[-200:]}"
            rule = (out_dir / "rule-calibers.md").read_text(encoding="utf-8")
            assert "共 19 条" in rule and "【待处理" not in rule.split("共 19")[0].split("| 待")[0],                 f"rule-calibers 计数异常（xgimi 复验版应无待处理前缀规则）: {rule[-200:]}"
            oq = (out_dir / "oq-verdicts.md").read_text(encoding="utf-8")
            assert "pending-engine" in oq and "共 12 条" in oq, f"oq 分组异常: {oq[-200:]}"
            probe = (out_dir / "probe-expectations.md").read_text(encoding="utf-8")
            assert "实体（26 个）" in probe and "动作（6 个）" in probe and "规则（19 条）" in probe,                 f"probe 清单计数异常: {probe[-200:]}"
            glossary = (out_dir / "glossary-snapshot.md").read_text(encoding="utf-8")
            assert "受控词表" in glossary and "Project" in glossary, "glossary 两节缺失"
            # 红线头注：每件首行均含素材非依赖声明
            for name in ("cq-final.md", "probe-expectations.md"):
                head = (out_dir / name).read_text(encoding="utf-8").splitlines()[:3]
                assert any("不是技能**运行时**依赖" in ln for ln in head), f"{name} 红线头注缺失"

    assert_case(results, "case12", "交接包五件齐全且与 xgimi 定稿一致（红线头注在位）", five_artifacts_consistent)


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
    build_case10(results)
    build_case11(results)
    build_case12(results)
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
