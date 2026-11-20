"""把本体引擎元数据快照逆向导出为 DSL v0.1 YAML（M0 POC 步骤：快照 -> DSL）。

主要 Input：get_meta_objects / get_meta_rules 的快照 JSON 文件（round-trip 基准，原样读取）。
主要 Output：符合 DSL v0.1 规范（poc/m0/dsl/README.md）的 YAML 模型文件（默认 poc/m0/fnb/fnb.model.yaml）。
导出原则：严格保真——description 空串照写、links 别名一字不改、治理字段不虚构；
引擎格式出现 DSL 无槽位的键 / 类型 / 规则类型时立即报错退出（缺口显性化，禁止静默丢弃）。
"""

# 标准库导入
import argparse
import json
import sys
from pathlib import Path
from typing import Any

# 第三方依赖导入
import yaml

# ===========一、常量与键集合校验表==========
# POC_ROOT：poc/m0 目录（由脚本位置向上定位，与运行时 cwd 无关）。
POC_ROOT = Path(__file__).resolve().parent.parent
# KNOWN_ENTITY_KEYS：引擎实体对象中 DSL 有对应槽位的键集合；集合外的键 = DSL 表达力缺口。
KNOWN_ENTITY_KEYS = {"display_name", "table_name", "description", "properties", "links"}
# KNOWN_PROPERTY_KEYS：引擎属性对象的键集合（data_type / is_primary 在 DSL 侧更名为 type / primary）。
KNOWN_PROPERTY_KEYS = {"display_name", "description", "data_type", "is_primary"}
# ALLOWED_DATA_TYPES：DSL v0.1 与引擎对齐的 7 种属性类型枚举。
ALLOWED_DATA_TYPES = {"STRING", "INTEGER", "DOUBLE", "DECIMAL", "BOOLEAN", "DATE", "TIMESTAMP"}
# KNOWN_RULE_KEYS：引擎规则对象的键集合（三类规则键面一致）。
KNOWN_RULE_KEYS = {"rule_type", "name", "upstream", "logic", "downstream", "description"}
# KNOWN_RULE_TYPES：DSL v0.1 支持的三种规则类型枚举。
KNOWN_RULE_TYPES = {"derived_property", "trigger", "admission"}
# DERIVED_DOWNSTREAM：引擎对 derived_property 规则固定的 downstream 常量（DSL 不承载，编译器回填）。
DERIVED_DOWNSTREAM = "Computed Property"


def _fail(location: str, detail: str) -> None:
    """缺口显性化退出：打印中文错误位置与详情后以非零码终止。

    Args:
        location: 出问题的元数据位置（如实体名、规则名）。
        detail: 缺口描述（未知键、非法类型等）。
    Raises:
        SystemExit: 总是触发，退出码 1。
    """
    print(f"错误：{location} 存在 DSL 无法承载的结构——{detail}", file=sys.stderr)
    raise SystemExit(1)


# ===========二、实体与属性导出==========
def _export_property(entity_name: str, field_name: str, field: dict[str, Any]) -> dict[str, Any]:
    """把引擎属性对象导出为 DSL 属性结构。

    Args:
        entity_name: 所属实体名（错误定位用）。
        field_name: 属性字段名（错误定位用）。
        field: 引擎属性对象（display_name / description / data_type / is_primary）。
    Returns:
        DSL 属性 dict（display_name / description / type，主键字段附加 primary: true）。
    """
    #   1. 校验键集合：出现 DSL 无槽位的键即失败（不静默丢弃信息）
    unknown_keys = set(field) - KNOWN_PROPERTY_KEYS
    if unknown_keys:
        _fail(f"属性 {entity_name}.{field_name}", f"未知键 {sorted(unknown_keys)}")
    #   2. 校验类型枚举：超出 7 种即 DSL 表达力缺口
    data_type = field.get("data_type")
    if data_type not in ALLOWED_DATA_TYPES:
        _fail(f"属性 {entity_name}.{field_name}", f"data_type={data_type!r} 不在 DSL 7 种类型枚举内")
    #   3. 组装 DSL 属性；description 空串照写；primary 仅在 true 时显式写出（false 为 DSL 缺省）
    prop: dict[str, Any] = {
        "display_name": field.get("display_name", ""),
        "description": field.get("description", ""),
        "type": data_type,
    }
    if field.get("is_primary"):
        prop["primary"] = True
    return prop


def _export_entity(entity_name: str, entity: dict[str, Any]) -> dict[str, Any]:
    """把引擎实体对象导出为 DSL 实体结构。

    Args:
        entity_name: 实体名（PascalCase，作为 DSL entities 的键）。
        entity: 引擎实体对象（display_name / table_name / description / properties / links）。
    Returns:
        DSL 实体 dict；links 为空时不输出该键（DSL 侧可选，编译器回填空 links）。
    """
    #   1. 校验实体级键集合
    unknown_keys = set(entity) - KNOWN_ENTITY_KEYS
    if unknown_keys:
        _fail(f"实体 {entity_name}", f"未知键 {sorted(unknown_keys)}")
    #   2. 逐属性导出（保持快照字段顺序）
    properties = {
        field_name: _export_property(entity_name, field_name, field)
        for field_name, field in entity.get("properties", {}).items()
    }
    #   3. 组装 DSL 实体；links 空字典省略（不虚构、不加噪）
    entity_out: dict[str, Any] = {
        "display_name": entity.get("display_name", ""),
        "table_name": entity.get("table_name", ""),
        "description": entity.get("description", ""),
        "properties": properties,
    }
    if entity.get("links"):
        entity_out["links"] = dict(entity["links"])
    return entity_out


# ===========三、规则导出==========
def _export_rule(rule: dict[str, Any], rule_index: int) -> dict[str, Any]:
    """把引擎规则对象导出为 DSL 规则结构（三类规则通用透传）。

    Args:
        rule: 引擎规则对象（rule_type / name / upstream / logic / downstream / description）。
        rule_index: 规则序号（错误定位用）。
    Returns:
        DSL 规则 dict；derived_property 不写 downstream（编译器回填固定常量），
        trigger / admission 的 downstream 原样保留。
    """
    #   1. 校验规则键集合与 rule_type 取值
    rule_type = rule.get("rule_type")
    if rule_type not in KNOWN_RULE_TYPES:
        _fail(f"规则[{rule_index}] {rule.get('name', '?')}", f"未知 rule_type={rule_type!r}")
    unknown_keys = set(rule) - KNOWN_RULE_KEYS
    if unknown_keys:
        _fail(f"规则[{rule_index}] {rule.get('name', '?')}", f"未知键 {sorted(unknown_keys)}")
    #   2. derived_property 的 downstream 引擎固定为 Computed Property；
    #    若引擎出现其他值即 DSL 无槽位承载，显性失败
    if rule_type == "derived_property" and rule.get("downstream") != DERIVED_DOWNSTREAM:
        _fail(
            f"规则[{rule_index}] {rule.get('name', '?')}",
            f"derived_property 的 downstream={rule.get('downstream')!r} 非 {DERIVED_DOWNSTREAM!r}",
        )
    #   3. 组装 DSL 规则（logic 为字符串或 ALL 结构 dict，原样透传）
    rule_out: dict[str, Any] = {
        "rule_type": rule_type,
        "name": rule.get("name", ""),
        "upstream": list(rule.get("upstream", [])),
        "logic": rule.get("logic"),
    }
    if rule_type != "derived_property":
        rule_out["downstream"] = rule.get("downstream", "")
    rule_out["description"] = rule.get("description", "")
    return rule_out


# ===========四、模型组装与落盘==========
def export_model(
    snapshot_objects: dict[str, Any], snapshot_rules: dict[str, Any], ontology: str, version: str
) -> dict[str, Any]:
    """把两份引擎快照组装为完整 DSL 模型 dict。

    Args:
        snapshot_objects: get_meta_objects 快照（实体名 -> 实体对象）。
        snapshot_rules: get_meta_rules 快照（{"rules": [...]}）。
        ontology: 本体标识（如 fnb）。
        version: 语义化版本号（草稿态带 -draft.N 后缀）。
    Returns:
        DSL 模型 dict（ontology / version / base_version / entities / rules）。
    """
    #   1. 实体：按快照顺序逐个导出
    entities = {
        entity_name: _export_entity(entity_name, entity)
        for entity_name, entity in snapshot_objects.items()
    }
    #   2. 规则：按快照列表顺序逐条导出
    rules = [_export_rule(rule, idx) for idx, rule in enumerate(snapshot_rules.get("rules", []))]
    #   3. 顶层组装：治理字段快照中不存在，按缺省不虚构（不写 governance）
    return {
        "ontology": ontology,
        "version": version,
        "base_version": None,
        "entities": entities,
        "rules": rules,
    }


def main() -> None:
    """命令行入口：读快照 -> 导出 DSL -> 写 YAML，打印中文统计摘要。"""
    parser = argparse.ArgumentParser(description="引擎元数据快照逆向导出为 DSL YAML")
    parser.add_argument(
        "--objects",
        default=POC_ROOT / "fnb" / "snapshot_objects.json",
        help="get_meta_objects 快照 JSON 路径（默认 poc/m0/fnb/snapshot_objects.json）",
    )
    parser.add_argument(
        "--rules",
        default=POC_ROOT / "fnb" / "snapshot_rules.json",
        help="get_meta_rules 快照 JSON 路径（默认 poc/m0/fnb/snapshot_rules.json）",
    )
    parser.add_argument(
        "--output",
        default=POC_ROOT / "fnb" / "fnb.model.yaml",
        help="输出的 DSL YAML 路径（默认 poc/m0/fnb/fnb.model.yaml）",
    )
    parser.add_argument("--ontology", default="fnb", help="本体标识（默认 fnb）")
    parser.add_argument("--version", default="0.1.0-draft.1", help="语义化版本（默认 0.1.0-draft.1）")
    args = parser.parse_args()

    #   1. 读取两份快照（round-trip 基准，原样读入不做任何整理）
    snapshot_objects = json.loads(Path(args.objects).read_text(encoding="utf-8"))
    snapshot_rules = json.loads(Path(args.rules).read_text(encoding="utf-8"))
    #   2. 逆向导出并落盘 YAML（allow_unicode 保持中文可读，sort_keys=False 保持插入顺序）
    model = export_model(snapshot_objects, snapshot_rules, args.ontology, args.version)
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        yaml.safe_dump(model, allow_unicode=True, sort_keys=False, default_flow_style=False, width=120),
        encoding="utf-8",
    )
    #   3. 打印统计摘要（==== 定界的关键事件）
    rules = model["rules"]
    rule_type_counts: dict[str, int] = {}
    for rule in rules:
        rule_type_counts[rule["rule_type"]] = rule_type_counts.get(rule["rule_type"], 0) + 1
    property_count = sum(len(e["properties"]) for e in model["entities"].values())
    link_count = sum(len(e.get("links", {})) for e in model["entities"].values())
    print(f"====DSL 逆向导出完成====: {output_path}")
    print(f"实体数: {len(model['entities'])}，属性总数: {property_count}，links 总数: {link_count}")
    print(f"规则数: {len(rules)}，类型分布: {rule_type_counts}")


if __name__ == "__main__":
    # Windows 控制台默认编码可能是 GBK，强制 UTF-8 避免中文摘要乱码
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    main()
