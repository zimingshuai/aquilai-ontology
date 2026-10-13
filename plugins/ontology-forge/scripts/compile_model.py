"""DSL v0.2 模型编译器：把 YAML 模型编译为本体引擎注册格式（自 poc/m0/scripts 迁移增强）。

主要 Input：DSL YAML 模型路径（位置参数）。
主要 Output：<模型目录>/engine-bundle/ 下三件产物——objects.json（实体注册表）、
rules.json（规则注册表，二者序列化参数与 M0 POC 版完全一致：ensure_ascii=False、indent=2）、
import-README.md（平台侧导入说明）。编译只取引擎格式白名单键，DSL 自有字段
（governance/provenance/uom/enum_values/source 及顶层 CQ/open_questions/conflicts/assumptions）
按 dsl-spec §6 编译剥离清单剥离，产物不含引擎格式之外的键（内置自查）。
通用性要求：编译逻辑完全由 DSL 结构驱动，不含任何实体名特判。
"""

# 标准库导入
import argparse
import json
import sys
from pathlib import Path
from typing import Any

# 第三方依赖导入
import yaml

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


# ===========五、落盘与命令行入口==========
def _write_import_readme(bundle_dir: Path, model_path: Path,
                         objects: dict[str, Any], rules_payload: dict[str, Any]) -> None:
    """生成 import-README.md：说明两份产物的引擎注册格式与导入流程。

    Args:
        bundle_dir: engine-bundle 目录路径。
        model_path: 源 DSL 模型路径（溯源展示用）。
        objects: 编译产物实体注册表（统计展示用）。
        rules_payload: 编译产物规则注册表（统计展示用）。
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
        "  derived_property 的 downstream 固定回填 \"Computed Property\"）。\n\n"
        "## 编译剥离说明（dsl-spec §6）\n\n"
        "DSL 自有字段不进入产物：实体级 governance / provenance，属性级 uom / enum_values / source，\n"
        "顶层 competency_questions / open_questions / conflicts / assumptions（规则仅保留引擎需要的\n"
        "name 与人审用的 description）。编译内置白名单自查，产物出现引擎格式之外的键即报错终止。\n\n"
        "## 导入流程\n\n"
        f"1. 人工审核本目录两份 JSON（共 {len(objects)} 个实体、"
        f"{len(rules_payload['rules'])} 条规则）与 DSL 的一致性；\n"
        "2. 审核通过后由平台侧按 `get_meta_objects` / `get_meta_rules` 的注册格式执行注册；\n"
        "3. 注册结果以引擎快照为准回流（增量建模的 base_version 依据）。\n"
    )
    (bundle_dir / "import-README.md").write_text(text, encoding="utf-8")


def main() -> None:
    """命令行入口：读 DSL YAML -> 编译 -> 剥离自查 -> 写 engine-bundle 三件产物。"""
    parser = argparse.ArgumentParser(description="DSL YAML 编译为本体引擎注册格式（engine-bundle）")
    parser.add_argument("model", help="DSL YAML 模型路径")
    parser.add_argument("-o", "--bundle-dir", default=None,
                        help="输出目录（默认 <模型目录>/engine-bundle）")
    args = parser.parse_args()
    model_path = Path(args.model)
    # bundle_dir：产物目录，缺省为模型同目录下的 engine-bundle。
    bundle_dir = Path(args.bundle_dir) if args.bundle_dir else model_path.parent / "engine-bundle"
    bundle_dir.mkdir(parents=True, exist_ok=True)

    #   1. 读取 DSL 模型（YAML 结构驱动编译，无任何实体名特判）
    model = yaml.safe_load(model_path.read_text(encoding="utf-8"))
    #   2. 编译为引擎注册格式
    objects, rules_payload = compile_model(model)
    #   3. 剥离自查：产物键集合不得超出引擎格式白名单（DSL 自有字段泄漏即失败）
    leaks = assert_engine_only(objects, rules_payload)
    if leaks:
        for leak in leaks:
            print(f"错误：编译产物泄漏 DSL 自有字段——{leak}", file=sys.stderr)
        raise SystemExit(1)
    #   4. 落盘两份 JSON（序列化参数与 M0 POC 版完全一致：ensure_ascii=False、indent=2）
    out_objects = bundle_dir / "objects.json"
    out_rules = bundle_dir / "rules.json"
    out_objects.write_text(
        json.dumps(objects, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    out_rules.write_text(
        json.dumps(rules_payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    #   5. 生成导入说明并打印统计摘要（==== 定界的关键事件）
    _write_import_readme(bundle_dir, model_path, objects, rules_payload)
    rule_type_counts: dict[str, int] = {}
    for rule in rules_payload["rules"]:
        rule_type_counts[rule["rule_type"]] = rule_type_counts.get(rule["rule_type"], 0) + 1
    property_count = sum(len(e["properties"]) for e in objects.values())
    print(f"====DSL 编译完成====: {model_path}")
    print(f"实体数: {len(objects)}，属性总数: {property_count}，规则数: {len(rules_payload['rules'])}")
    print(f"规则类型分布: {rule_type_counts}")
    print(f"====剥离自查通过====: 产物仅含引擎格式键")
    print(f"产物: {out_objects} / {out_rules} / {bundle_dir / 'import-README.md'}")


if __name__ == "__main__":
    # CLI 脚本本体即调试入口：python compile_model.py <model.yaml> 跑真实模型。
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    main()
