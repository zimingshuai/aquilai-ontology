"""把 DSL v0.1 YAML 模型编译为本体引擎注册格式（M0 POC 步骤：DSL -> 引擎格式）。

主要 Input：DSL YAML 模型文件路径（默认 poc/m0/fnb/fnb.model.yaml）。
主要 Output：引擎注册格式两份 JSON——实体注册表（默认 poc/m0/fnb/compiled_objects.json）
与规则注册表（默认 poc/m0/fnb/compiled_rules.json），键名严格按 DSL 规范 §6 映射表。
通用性要求：编译逻辑完全由 DSL 结构驱动（遍历 entities/rules），不含任何实体名特判。
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
# POC_ROOT：poc/m0 目录（由脚本位置向上定位，与运行时 cwd 无关）。
POC_ROOT = Path(__file__).resolve().parent.parent
# ALLOWED_TYPES：DSL v0.1 的 7 种属性类型枚举（与引擎 data_type 同名对齐，无需改名）。
ALLOWED_TYPES = {"STRING", "INTEGER", "DOUBLE", "DECIMAL", "BOOLEAN", "DATE", "TIMESTAMP"}
# KNOWN_RULE_TYPES：DSL v0.1 的三种规则类型。
KNOWN_RULE_TYPES = {"derived_property", "trigger", "admission"}
# DERIVED_DOWNSTREAM：引擎对 derived_property 规则固定回填的 downstream 常量（规范 §6）。
DERIVED_DOWNSTREAM = "Computed Property"


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
    """把 DSL 属性编译为引擎属性对象。

    Args:
        entity_name: 所属实体名（错误定位用）。
        field_name: 属性字段名（错误定位用）。
        field: DSL 属性 dict（display_name / description / type / primary）。
    Returns:
        引擎属性 dict：display_name / description / data_type / is_primary 四键齐全。
    """
    #   1. 校验类型枚举（DSL 侧 type 非法即拒绝编译，不降级猜测）
    prop_type = field.get("type")
    if prop_type not in ALLOWED_TYPES:
        _fail(f"属性 {entity_name}.{field_name}", f"type={prop_type!r} 不在 7 种枚举内")
    #   2. 按规范 §6 映射：type -> data_type、primary(缺省 false) -> is_primary；
    #    description 缺省补空串（引擎要求键存在）
    return {
        "display_name": field.get("display_name", ""),
        "description": field.get("description", ""),
        "data_type": prop_type,
        "is_primary": bool(field.get("primary", False)),
    }


def _compile_entity(entity_name: str, entity: dict[str, Any]) -> dict[str, Any]:
    """把 DSL 实体编译为引擎实体对象。

    Args:
        entity_name: 实体名（PascalCase）。
        entity: DSL 实体 dict（display_name / table_name / description / properties / links）。
    Returns:
        引擎实体 dict：五键齐全，links 缺省回填空 dict（引擎格式固定含 links 键）。
    """
    #   1. 逐属性编译（保持 DSL 字段顺序）
    properties = {
        field_name: _compile_property(entity_name, field_name, field)
        for field_name, field in entity.get("properties", {}).items()
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


# ===========四、模型编译与落盘==========
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
    #   2. 实体：按 DSL 声明顺序编译
    objects = {
        entity_name: _compile_entity(entity_name, entity)
        for entity_name, entity in model["entities"].items()
    }
    #   3. 规则：按 DSL 列表顺序编译
    rules_payload = {
        "rules": [_compile_rule(rule, idx) for idx, rule in enumerate(model.get("rules") or [])]
    }
    return objects, rules_payload


def main() -> None:
    """命令行入口：读 DSL YAML -> 编译 -> 写两份 JSON，打印中文统计摘要。"""
    parser = argparse.ArgumentParser(description="DSL YAML 编译为本体引擎注册格式")
    parser.add_argument(
        "--model",
        default=POC_ROOT / "fnb" / "fnb.model.yaml",
        help="DSL YAML 模型路径（默认 poc/m0/fnb/fnb.model.yaml）",
    )
    parser.add_argument(
        "--out-objects",
        default=POC_ROOT / "fnb" / "compiled_objects.json",
        help="输出的实体注册 JSON 路径（默认 poc/m0/fnb/compiled_objects.json）",
    )
    parser.add_argument(
        "--out-rules",
        default=POC_ROOT / "fnb" / "compiled_rules.json",
        help="输出的规则注册 JSON 路径（默认 poc/m0/fnb/compiled_rules.json）",
    )
    args = parser.parse_args()

    #   1. 读取 DSL 模型（YAML 结构驱动编译，无任何实体名特判）
    model = yaml.safe_load(Path(args.model).read_text(encoding="utf-8"))
    #   2. 编译为引擎注册格式
    objects, rules_payload = compile_model(model)
    #   3. 落盘两份 JSON（ensure_ascii=False 保持中文原文）
    Path(args.out_objects).write_text(
        json.dumps(objects, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    Path(args.out_rules).write_text(
        json.dumps(rules_payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    #   4. 打印统计摘要（==== 定界的关键事件）
    rule_type_counts: dict[str, int] = {}
    for rule in rules_payload["rules"]:
        rule_type_counts[rule["rule_type"]] = rule_type_counts.get(rule["rule_type"], 0) + 1
    property_count = sum(len(e["properties"]) for e in objects.values())
    print(f"====DSL 编译完成====: {args.model}")
    print(f"实体数: {len(objects)}，属性总数: {property_count}，规则数: {len(rules_payload['rules'])}")
    print(f"规则类型分布: {rule_type_counts}")
    print(f"产物: {args.out_objects} / {args.out_rules}")


if __name__ == "__main__":
    # Windows 控制台默认编码可能是 GBK，强制 UTF-8 避免中文摘要乱码
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    main()
