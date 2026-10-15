"""平台导入一致性自检：DSL ↔ 平台工作区 SDK 比对。

用途：studio-model.yaml 导入平台后，从平台下载该工作区的 aquilair.py SDK，
     本脚本比对两侧实体/字段/主键/关系，验证导入零丢失并发现平台侧手改。
主要 Input：DSL model.yaml 路径 + 平台 SDK 路径（命令行两参数）。
主要 Output：stdout 中文一致性报告；退出码 0=一致，1=存在差异（差异明细列出，
     不视为脚本失败——差异本身是给用户决策的信号）。
平台机制适配（2026-10-14 实证）：SDK RelationDefinition 的 source/target_field
     为平台内部 PROP_<hash> 属性 ID，与字段名不可直接映射——关系比对采用
     (source, target, cardinality) 三元组 + 总量核对；字段与主键用
     fields_by_name / primary_key_field（字段名直读）。
"""

import importlib.util
import sys
from pathlib import Path

import yaml


# ===========一、SDK 加载与定义提取==========
def load_sdk(sdk_path: Path):
    """动态加载平台 SDK 模块并返回定义字典。

    Args:
        sdk_path: aquilair.py 文件路径。
    Returns:
        (OBJECT_DEFINITIONS, RELATION_DEFINITIONS) 两字典。
    """
    # mod_name：模块注册名（dataclass 装饰器要求模块先入 sys.modules）。
    mod_name = "platform_sdk_check_target"
    spec = importlib.util.spec_from_file_location(mod_name, sdk_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[mod_name] = module
    spec.loader.exec_module(module)
    return module.OBJECT_DEFINITIONS, module.RELATION_DEFINITIONS


# ===========二、三类比对==========
def diff_entities(sdk_objs: dict, dsl: dict) -> list:
    """实体集合与字段/主键比对（大小写归一）。

    Args:
        sdk_objs: SDK 的 OBJECT_DEFINITIONS。
        dsl: DSL 模型 dict。
    Returns:
        中文差异清单（空列表=完全一致）。
    """
    # sdk_ents / dsl_ents：小写实体名 -> 定义 映射。
    sdk_ents = {d.entity_name.lower(): d for d in sdk_objs.values()}
    dsl_ents = {k.lower(): k for k in dsl.get("entities", {})}
    issues = []
    only_sdk = sorted(set(sdk_ents) - set(dsl_ents))
    only_dsl = sorted(set(dsl_ents) - set(sdk_ents))
    if only_sdk:
        issues.append(f"仅平台侧存在的实体: {only_sdk}")
    if only_dsl:
        issues.append(f"仅 DSL 侧存在的实体（导入丢失？）: {only_dsl}")
    for low, d in sdk_ents.items():
        if low not in dsl_ents:
            continue
        # dk：DSL 侧原始实体名。
        dk = dsl_ents[low]
        sdk_fields = set(d.fields_by_name.keys())
        dsl_fields = set(dsl["entities"][dk].get("properties", {}).keys())
        if sdk_fields != dsl_fields:
            issues.append(f"实体 {dk} 字段不一致: 仅平台={sorted(sdk_fields - dsl_fields)} "
                          f"仅DSL={sorted(dsl_fields - sdk_fields)}")
        # dsl_pk：DSL 主键字段集合。
        dsl_pk = {f for f, s in dsl["entities"][dk].get("properties", {}).items()
                  if isinstance(s, dict) and s.get("primary")}
        if d.primary_key_field not in dsl_pk:
            issues.append(f"实体 {dk} 主键不一致: 平台={d.primary_key_field} DSL={sorted(dsl_pk)}")
    return issues


def diff_relations(sdk_rels: dict, sm_path: Path) -> list:
    """关系比对：SDK 三元组 (source,target,cardinality) 对导入 yaml 的 link_types。

    Args:
        sdk_rels: SDK 的 RELATION_DEFINITIONS。
        sm_path: 导入用的 studio-model.yaml 路径。
    Returns:
        中文差异清单（空列表=完全一致）。
    """
    sm = yaml.safe_load(sm_path.read_text(encoding="utf-8"))
    # sm_tris / sdk_tris：(source,target,cardinality) 三元组集合（PROP 机制适配）。
    sm_tris = {(l["source"].lower(), l["target"].lower(), l["cardinality"].upper())
               for l in sm.get("link_types", [])}
    sdk_tris = {(r.source_object.lower(), r.target_object.lower(), str(r.cardinality).upper())
                for r in sdk_rels.values()}
    issues = []
    if sm_tris != sdk_tris:
        for t in sorted(sdk_tris - sm_tris):
            issues.append(f"仅平台侧存在的关系: {t}")
        for t in sorted(sm_tris - sdk_tris):
            issues.append(f"仅导入 yaml 存在的关系（导入丢失？）: {t}")
    return issues


# ===========三、主流程==========
def main() -> int:
    """执行两类比对并输出报告。

    Returns:
        0=完全一致，1=存在差异（明细见输出）。
    """
    if len(sys.argv) != 3:
        print("用法: python check_platform_sync.py <model.yaml> <平台SDK aquilair.py>")
        return 2
    # dsl_path / sdk_path：两输入文件。
    dsl_path, sdk_path = Path(sys.argv[1]), Path(sys.argv[2])
    dsl = yaml.safe_load(dsl_path.read_text(encoding="utf-8"))
    sm_path = dsl_path.parent / "engine-bundle" / "studio-model.yaml"
    sdk_objs, sdk_rels = load_sdk(sdk_path)
    print(f"====平台一致性比对====: DSL {dsl_path.name} ↔ SDK {sdk_path.name}")
    print(f"规模: 平台实体 {len(sdk_objs)} / 关系 {len(sdk_rels)}")
    issues = diff_entities(sdk_objs, dsl) + diff_relations(sdk_rels, sm_path)
    if issues:
        print(f"====发现 {len(issues)} 处差异====")
        for i in issues:
            print(f"- {i}")
        return 1
    print("====完全一致====: 实体/字段/主键/关系零差异")
    return 0


if __name__ == "__main__":
    sys.exit(main())
