"""DSL v0.2 模型编译器：把 YAML 模型编译为本体引擎注册格式与 Studio 模板（自 poc/m0/scripts 迁移增强）。

主要 Input：DSL YAML 模型路径（位置参数）+ --target 编译目标（engine / studio-model / both，默认 both）。
主要 Output:<模型目录>/engine-bundle/ 下产物——engine 目标产出三件（objects.json（实体注册表）、
rules.json（规则注册表，二者序列化参数与 M0 POC 版完全一致：ensure_ascii=False、indent=2）、
import-README.md（平台侧导入说明））；DSL 含 actions 段时（v0.2.2 §4）engine 目标额外产出
actions.json（动作注册表，结构对齐 mfg 引擎 get_meta_actions 实测：逐 action 读 body_ref 指向的
骨架文件内容为 body——缺骨架文件时报错并提示先运行 gen_action_skeleton.py，不产出该文件；
sandbox_execution 为引擎统一的沙箱执行约定常量）；无 actions 段不生成该文件（gold/fnb 行为不变）。
studio-model 目标额外产出 studio-model.yaml（dsl-spec §8 互导格式，trigger/admission 不进模板并告警
列出；links 外键缺失的连线跳过并报错列出（不猜），此时退出码 1 但产物照写以便人工处理）。编译只取
引擎格式白名单键，DSL 自有字段（governance/provenance/uom/enum_values/source 及顶层
CQ/open_questions/conflicts/assumptions）按 dsl-spec §6 编译剥离清单剥离，产物不含引擎格式之外的键
（内置自查）。通用性要求：编译逻辑完全由 DSL 结构驱动，不含任何实体名特判。
"""

# 标准库导入
import argparse
import json
import sys
from pathlib import Path
from typing import Any

# 第三方依赖导入
import yaml

# 项目内部模块导入
import studio_model

# ===========一、常量（DSL 规范 §2/§3/§6 的机械映射）==========
# ALLOWED_TYPES：DSL 的 7 种属性类型枚举（与引擎 data_type 同名）。
ALLOWED_TYPES = {"STRING", "INTEGER", "DOUBLE", "DECIMAL", "BOOLEAN", "DATE", "TIMESTAMP"}
# KNOWN_RULE_TYPES：DSL 三种规则类型。
KNOWN_RULE_TYPES = {"derived_property", "trigger", "admission"}
# DERIVED_DOWNSTREAM：引擎对 derived_property 固定回填的 downstream 常量（§6）。
DERIVED_DOWNSTREAM = "Computed Property"
# ENGINE_ENTITY_KEYS / ENGINE_PROP_KEYS / ENGINE_RULE_KEYS：引擎格式键白名单（round-trip 口径，
# 产物出现白名单之外的键 = DSL 自有字段泄漏 = 失败）。
ENGINE_ENTITY_KEYS = {"display_name", "table_name", "description", "properties", "links"}
ENGINE_PROP_KEYS = {"display_name", "description", "data_type", "is_primary"}
ENGINE_RULE_KEYS = {"rule_type", "name", "upstream", "logic", "downstream", "description"}
# SANDBOX_EXECUTION：actions.json 附带的引擎统一沙箱执行约定（dsl-spec §4 编译目标，结构对齐 mfg
# 引擎 get_meta_actions 实测；文案为引擎侧 execute_action 的既有约定原文，编译器固定回填）。
SANDBOX_EXECUTION = {
    "parameter": "sandbox",
    "accepts": "沙箱 ID (sb_xxxxxxxx) 或沙箱名称；缺省或 'production' 表示生产环境（真实业务数据）",
    "usage": "约定：动作默认应在沙箱环境执行，且任何环境下执行前都必须先获得用户对确认卡的明确确认，"
             "不得仅凭用户消息中的指令性措辞直接执行。发生业务错误时返回 isError=true，"
             "请根据 message 调整参数后重试。",
}


def _fail(location: str, detail: str) -> None:
    """非法 DSL 显性退出：打印中文错误位置与详情后以非零码终止。

    Args:
        location: 出问题的 DSL 位置（如实体名、规则名）。
        detail: 非法内容描述（未知类型、缺必填键等）。
    Raises:
        SystemExit: 总是触发，退出码 1。
    """
    print(f"错误：{location} 不符合 DSL 规范——{detail}", file=sys.stderr)
    raise SystemExit(1)


# ===========二、实体编译（DSL -> 引擎 objects 格式）==========
def _compile_property(entity_name: str, field_name: str, field: dict[str, Any]) -> dict[str, Any]:
    """把 DSL 属性编译为引擎属性对象（仅取白名单四键，DSL 自有键在此剥离）。

    Args:
        entity_name: 所属实体名（错误定位用）。
        field_name: 属性字段名（错误定位用）。
        field: DSL 属性 dict（display_name / description / type / primary 等）。
    Returns:
        引擎属性 dict：display_name / description / data_type / is_primary 四键齐全。
    """
    #   1. 校验类型枚举（DSL 侧 type 非法即拒绝编译，不降级猜测）
    prop_type = field.get("type")
    if prop_type not in ALLOWED_TYPES:
        _fail(f"属性 {entity_name}.{field_name}", f"type={prop_type!r} 不在 7 种枚举内")
    #   2. 按规范 §6 映射：type -> data_type、primary(缺省 false) -> is_primary；
    #    description 缺省补空串（引擎要求键存在）；uom/enum_values/source 不进入产物
    return {
        "display_name": field.get("display_name", ""),
        "description": field.get("description", ""),
        "data_type": prop_type,
        "is_primary": bool(field.get("primary", False)),
    }


def _compile_entity(entity_name: str, entity: dict[str, Any]) -> dict[str, Any]:
    """把 DSL 实体编译为引擎实体对象（仅取白名单五键，governance/provenance 在此剥离）。

    Args:
        entity_name: 实体名（PascalCase）。
        entity: DSL 实体 dict（display_name / table_name / description / properties / links）。
    Returns:
        引擎实体 dict：五键齐全，links 缺省回填空 dict（引擎格式固定含 links 键）。
    """
    #   1. 逐属性编译（保持 DSL 字段顺序）
    properties = {
        field_name: _compile_property(entity_name, field_name, field)
        for field_name, field in (entity.get("properties") or {}).items()
    }
    #   2. 组装引擎实体；links 为 DSL 可选键，缺省/为 None 时回填空 dict
    return {
        "display_name": entity.get("display_name", ""),
        "table_name": entity.get("table_name", ""),
        "description": entity.get("description", ""),
        "properties": properties,
        "links": dict(entity.get("links") or {}),
    }


# ===========三、规则编译（DSL -> 引擎 rules 格式）==========
def _compile_rule(rule: dict[str, Any], rule_index: int) -> dict[str, Any]:
    """把 DSL 规则编译为引擎规则对象（按 rule_type 分派，规范 §6 映射表）。

    Args:
        rule: DSL 规则 dict（rule_type / name / upstream / logic [/ downstream] / description）。
        rule_index: 规则序号（错误定位用）。
    Returns:
        引擎规则 dict：rule_type / name / upstream / logic / downstream / description 六键齐全；
        derived_property 的 downstream 回填固定常量，trigger / admission 原样透传。
    """
    #   1. 校验 rule_type 与必填键
    rule_type = rule.get("rule_type")
    if rule_type not in KNOWN_RULE_TYPES:
        _fail(f"规则[{rule_index}] {rule.get('name', '?')}", f"未知 rule_type={rule_type!r}")
    for required_key in ("name", "upstream", "logic"):
        if required_key not in rule:
            _fail(f"规则[{rule_index}] {rule.get('name', '?')}", f"缺少必填键 {required_key}")
    #   2. 分派 downstream：derived_property 回填常量；trigger / admission 必须自带
    if rule_type == "derived_property":
        downstream = DERIVED_DOWNSTREAM
    elif "downstream" not in rule:
        _fail(f"规则[{rule_index}] {rule.get('name', '?')}", f"{rule_type} 规则缺少 downstream")
    else:
        downstream = rule["downstream"]
    #   3. 组装引擎规则（logic 为字符串或 ALL 结构 dict，按 DSL 原样透传）
    return {
        "rule_type": rule_type,
        "name": rule.get("name", ""),
        "upstream": list(rule.get("upstream", [])),
        "logic": rule.get("logic"),
        "downstream": downstream,
        "description": rule.get("description", ""),
    }


def compile_model(model: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    """把完整 DSL 模型编译为引擎注册格式两份产物。

    Args:
        model: safe_load 得到的 DSL 模型 dict（须含 entities，rules 可空）。
    Returns:
        二元组 (objects, rules_payload)：objects 为实体名 -> 引擎实体对象；
        rules_payload 为 {"rules": [引擎规则对象, ...]}，顺序与 DSL 列表一致。
    """
    #   1. 校验顶层必填键 entities
    if "entities" not in model or not isinstance(model["entities"], dict):
        _fail("模型顶层", "缺少必填键 entities 或其不是映射结构")
    #   2. 实体：按 DSL 声明顺序编译（顶层 DSL 自有键 governance/competency_questions 等天然不进入）
    objects = {
        entity_name: _compile_entity(entity_name, entity)
        for entity_name, entity in model["entities"].items()
    }
    #   3. 规则：按 DSL 列表顺序编译
    rules_payload = {
        "rules": [_compile_rule(rule, idx) for idx, rule in enumerate(model.get("rules") or [])]
    }
    return objects, rules_payload


# ===========四、剥离自查（§6 round-trip 口径）==========
def assert_engine_only(objects: dict[str, Any], rules_payload: dict[str, Any]) -> list[str]:
    """自查编译产物键集合不超出引擎格式白名单（DSL 自有字段泄漏 = 失败）。

    Args:
        objects: 编译产物实体注册表。
        rules_payload: 编译产物规则注册表。
    Returns:
        泄漏项中文描述列表（空 = 无泄漏）。
    """
    leaks: list[str] = []
    for ename, ent in objects.items():
        leaks.extend(f"实体 {ename} 泄漏键 {k}" for k in set(ent) - ENGINE_ENTITY_KEYS)
        for fname, prop in ent["properties"].items():
            leaks.extend(f"属性 {ename}.{fname} 泄漏键 {k}" for k in set(prop) - ENGINE_PROP_KEYS)
    for idx, rule in enumerate(rules_payload["rules"]):
        leaks.extend(f"规则[{idx}] {rule.get('name', '?')} 泄漏键 {k}"
                     for k in set(rule) - ENGINE_RULE_KEYS)
    return leaks


# ===========五、actions 编译（dsl-spec §4，v0.2.2）==========
def _compile_actions(model: dict[str, Any], model_path: Path, bundle_dir: Path) -> Path | None:
    """把 DSL actions 段编译为引擎动作注册表（无 actions 段不生成文件，返回 None）。

    Args:
        model: safe_load 得到的 DSL 模型 dict（actions 段可空）。
        model_path: 源 DSL 模型路径（body_ref 相对路径的解析基准）。
        bundle_dir: engine-bundle 目录路径。
    Returns:
        二元组 (产物路径, 动作数)：无 actions 段时为 (None, 0)。
    Raises:
        SystemExit: action 缺 body_ref 或 body_ref 文件不存在时退出码 1（提示先跑骨架生成器）。
    """
    actions = model.get("actions") or []
    if not actions:
        return None, 0  # 无 actions 不生成该文件：gold/fnb 既有行为不变
    compiled: list[dict[str, Any]] = []
    errors: list[str] = []
    for idx, action in enumerate(actions):
        name = action.get("name") or f"actions[{idx}]"
        where = f"动作 {name}"
        body_ref = action.get("body_ref")
        if not body_ref:
            errors.append(f"{where} 缺少 body_ref（骨架文件路径），无法回读 body")
            continue
        #   1. body_ref 相对路径按模型目录解析（与 gen_action_skeleton.py 输出口径一致）
        body_path = Path(body_ref)
        if not body_path.is_absolute():
            body_path = model_path.parent / body_path
        if not body_path.is_file():
            errors.append(
                f"{where} 的 body_ref 文件不存在：{body_path}——"
                f"请先运行 python gen_action_skeleton.py {model_path.name} 生成骨架（人工插桩后回填编译）")
            continue
        #   2. 组装引擎格式键（get_meta_actions 实测结构；body 为骨架文件内容字符串）
        compiled.append({
            "action_name": name,
            "description": action.get("description", ""),
            "parameters": dict(action.get("parameters") or {}),
            "supports_sandbox": bool(action.get("supports_sandbox", True)),
            "body": body_path.read_text(encoding="utf-8"),
        })
    if errors:
        for error in errors:
            print(f"错误：{error}", file=sys.stderr)
        raise SystemExit(1)  # 引擎注册缺 body 无意义：不产出 actions.json，错误全量列出
    out_actions = bundle_dir / "actions.json"
    out_actions.write_text(
        json.dumps({"actions": compiled, "sandbox_execution": SANDBOX_EXECUTION},
                   ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return out_actions, len(compiled)


# ===========六、落盘与命令行入口==========
def _write_import_readme(bundle_dir: Path, model_path: Path,
                         objects: dict[str, Any], rules_payload: dict[str, Any],
                         actions_count: int = 0) -> None:
    """生成 import-README.md：说明各产物的引擎注册格式与导入流程。

    Args:
        bundle_dir: engine-bundle 目录路径。
        model_path: 源 DSL 模型路径（溯源展示用）。
        objects: 编译产物实体注册表（统计展示用）。
        rules_payload: 编译产物规则注册表（统计展示用）。
        actions_count: 动作数（0 = 模型无 actions 段，README 不提该文件）。
    Returns:
        None。
    """
    text = (
        "# 引擎注册产物（engine-bundle）\n\n"
        f"- 溯源：由 compile_model.py 从 `{model_path.name}` 编译生成，重新编译会覆盖本目录文件，请勿手改。\n\n"
        "## 文件与引擎注册格式的对应\n\n"
        "- `objects.json`：实体注册表，对应本体引擎 `get_meta_objects` 返回结构\n"
        "  （实体名 -> display_name / table_name / description / properties"
        "（display_name / description / data_type / is_primary）/ links）。\n"
        "- `rules.json`：规则注册表，对应本体引擎 `get_meta_rules` 返回结构\n"
        "  （rules 列表：rule_type / name / upstream / logic / downstream / description；\n"
        "  derived_property 的 downstream 固定回填 \"Computed Property\"）。\n"
    )
    if actions_count:
        text += (
            "- `actions.json`：动作注册表，对应本体引擎 `get_meta_actions` 返回结构\n"
            "  （actions 列表：action_name / description / parameters / supports_sandbox /"
            " body=骨架源码字符串；body 自各 body_ref 骨架文件读取，业务逻辑由人工插桩后回填编译；\n"
            "  sandbox_execution 为引擎统一的沙箱执行约定）。\n"
        )
    if actions_count:
        review_line = (f"1. 人工审核本目录 JSON 产物（共 {len(objects)} 个实体、"
                       f"{len(rules_payload['rules'])} 条规则、{actions_count} 个动作）与 DSL 的一致性；\n")
    else:
        # 无 actions：保持既有措辞逐字不变（gold/fnb 的 engine-bundle 回归口径）
        review_line = (f"1. 人工审核本目录两份 JSON（共 {len(objects)} 个实体、"
                       f"{len(rules_payload['rules'])} 条规则）与 DSL 的一致性；\n")
    text += (
        "\n## 编译剥离说明（dsl-spec §6）\n\n"
        "DSL 自有字段不进入产物：实体级 governance / provenance，属性级 uom / enum_values / source，\n"
        "顶层 competency_questions / open_questions / conflicts / assumptions（规则仅保留引擎需要的\n"
        "name 与人审用的 description）。编译内置白名单自查，产物出现引擎格式之外的键即报错终止。\n\n"
        "## 导入流程\n\n"
        + review_line
        + "2. 审核通过后由平台侧按 `get_meta_objects` / `get_meta_rules` 的注册格式执行注册；\n"
        "3. 注册结果以引擎快照为准回流（增量建模的 base_version 依据）。\n"
    )
    (bundle_dir / "import-README.md").write_text(text, encoding="utf-8")


def _compile_engine_target(model: dict[str, Any], model_path: Path, bundle_dir: Path) -> None:
    """engine 目标编译落盘：编译 -> 剥离自查 -> 写三件产物 -> 打印统计（与既有版本行为一致）。

    Args:
        model: safe_load 得到的 DSL 模型 dict。
        model_path: 源 DSL 模型路径。
        bundle_dir: engine-bundle 目录路径。
    Returns:
        None；产物键泄漏时 SystemExit(1)。
    """
    #   1. 编译为引擎注册格式并做剥离自查（DSL 自有字段泄漏即失败）
    objects, rules_payload = compile_model(model)
    leaks = assert_engine_only(objects, rules_payload)
    if leaks:
        for leak in leaks:
            print(f"错误：编译产物泄漏 DSL 自有字段——{leak}", file=sys.stderr)
        raise SystemExit(1)
    #   2. 落盘两份 JSON（序列化参数与 M0 POC 版完全一致：ensure_ascii=False、indent=2）
    out_objects = bundle_dir / "objects.json"
    out_rules = bundle_dir / "rules.json"
    out_objects.write_text(
        json.dumps(objects, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    out_rules.write_text(
        json.dumps(rules_payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    #   3. actions 编译（dsl-spec §4：读 body_ref 骨架内容；无 actions 段跳过且不生成文件）
    out_actions, actions_count = _compile_actions(model, model_path, bundle_dir)
    #   4. 生成导入说明并打印统计摘要（==== 定界的关键事件）
    _write_import_readme(bundle_dir, model_path, objects, rules_payload, actions_count)
    rule_type_counts: dict[str, int] = {}
    for rule in rules_payload["rules"]:
        rule_type_counts[rule["rule_type"]] = rule_type_counts.get(rule["rule_type"], 0) + 1
    property_count = sum(len(e["properties"]) for e in objects.values())
    print(f"====DSL 编译完成====: {model_path}")
    print(f"实体数: {len(objects)}，属性总数: {property_count}，规则数: {len(rules_payload['rules'])}")
    print(f"规则类型分布: {rule_type_counts}")
    print(f"====剥离自查通过====: 产物仅含引擎格式键")
    outputs = [out_objects, out_rules]
    if out_actions is not None:
        outputs.append(out_actions)
        print(f"动作数: {actions_count}")
    outputs.append(bundle_dir / "import-README.md")
    print(f"产物: {' / '.join(map(str, outputs))}")


def _compile_studio_target(model: dict[str, Any], model_path: Path,
                           bundle_dir: Path, *, alone: bool) -> int:
    """studio-model 目标编译落盘（dsl-spec §8 互导格式）。

    Args:
        model: safe_load 得到的 DSL 模型 dict。
        model_path: 源 DSL 模型路径。
        bundle_dir: 产物目录路径（studio-model.yaml 与 JSON 同级）。
        alone: 是否为 --target studio-model 单独目标（决定 README 全量重写还是追加章节）。
    Returns:
        退出码：0=无编译错误；1=存在编译错误（产物仍写出供人工处理）。
    """
    #   1. 编译：类型映射 / links->1:n 连线 / derived->calculation；trigger 不进模板
    studio, errors, warnings = studio_model.compile_studio_model(model)
    #   2. YAML 落盘（sort_keys=False 保持模板键序；width 放宽避免长表达式折行；稳定 hash 保证幂等）
    out_studio = bundle_dir / "studio-model.yaml"
    out_studio.write_text(
        yaml.dump(studio, allow_unicode=True, sort_keys=False, default_flow_style=False, width=4096),
        encoding="utf-8",
    )
    #   3. README：单独目标写简头 + Studio 章节；both 目标在引擎 README 末尾追加章节
    section = studio_model.studio_readme_section(studio, errors, warnings)
    readme_path = bundle_dir / "import-README.md"
    if alone:
        header = (
            "# Studio 模板产物（studio-model.yaml）\n\n"
            f"- 溯源：由 compile_model.py --target studio-model 从 `{model_path.name}` 编译生成，"
            "重新编译会覆盖，请勿手改。本目标不产出引擎注册 JSON（需要时改用 --target engine/both）。\n"
        )
        readme_path.write_text(header + section, encoding="utf-8")
    else:
        with readme_path.open("a", encoding="utf-8") as readme_file:
            readme_file.write(section)
    #   4. 错误/告警全量输出（不掩盖），再打印统计摘要（==== 定界的关键事件）
    for error in errors:
        print(f"错误：{error}", file=sys.stderr)
    for warning in warnings:
        print(f"警告：{warning}")
    print(f"====studio-model 编译完成====: {out_studio}")
    print(f"object_types: {len(studio['object_types'])}，link_types: {len(studio['link_types'])}，"
          f"rule_types: {len(studio['rule_types'])}，编译错误: {len(errors)}，告警: {len(warnings)}")
    return 1 if errors else 0


def main() -> None:
    """命令行入口：读 DSL YAML -> 按 --target 编译引擎注册格式与/或 Studio 模板并落盘。"""
    parser = argparse.ArgumentParser(description="DSL YAML 编译为本体引擎注册格式与 Studio 模板")
    parser.add_argument("model", help="DSL YAML 模型路径")
    parser.add_argument("-o", "--bundle-dir", default=None,
                        help="输出目录（默认 <模型目录>/engine-bundle）")
    parser.add_argument("--target", choices=("engine", "studio-model", "both"), default="both",
                        help="编译目标：engine=仅引擎注册 JSON（与既有版本行为一致）；"
                             "studio-model=仅 Studio 模板 YAML；both=两者（默认）。"
                             "studio-model 产物为 <bundle>/studio-model.yaml；trigger/admission 规则"
                             "不进模板（stdout 告警列出，需引擎侧配置）；links 外键缺失的连线跳过并报错"
                             "（不猜），此时退出码 1 但产物照写")
    args = parser.parse_args()
    model_path = Path(args.model)
    # bundle_dir：产物目录，缺省为模型同目录下的 engine-bundle。
    bundle_dir = Path(args.bundle_dir) if args.bundle_dir else model_path.parent / "engine-bundle"
    bundle_dir.mkdir(parents=True, exist_ok=True)

    #   1. 读取 DSL 模型（YAML 结构驱动编译，无任何实体名特判）
    model = yaml.safe_load(model_path.read_text(encoding="utf-8"))
    #   2. engine 目标（产物与字节级输出同既有版本）
    if args.target in ("engine", "both"):
        _compile_engine_target(model, model_path, bundle_dir)
    #   3. studio-model 目标（错误全量列出后退出码 1，产物照写）
    if args.target in ("studio-model", "both"):
        sys.exit(_compile_studio_target(model, model_path, bundle_dir,
                                        alone=args.target == "studio-model"))


if __name__ == "__main__":
    # CLI 脚本本体即调试入口：python compile_model.py <model.yaml> 跑真实模型。
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    main()
