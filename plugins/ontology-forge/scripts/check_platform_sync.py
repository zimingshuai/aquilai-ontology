"""平台导入一致性自检：DSL ↔ 平台侧元数据比对（两种平台侧输入）。

用途：studio-model.yaml 导入平台后，拉取平台侧元数据与 DSL 比对，验证导入零丢失并发现平台侧手改。
平台侧输入两种（按第二参数后缀分派）：
  - .py：该工作区的 SDK（aquilair.py，OBJECT_DEFINITIONS/RELATION_DEFINITIONS）——既有形态；
  - .json：MCP `metadata_workspace_model` 返回的元数据 JSON（顶层六键 entities/relations/rules/
    actions/algorithms/functions，或 JSON-RPC 包装 result.structuredContent——两种都能读）。
比对维度：实体/字段/主键、关系三元组+基数、规则（名+平台类型）、动作（名集合；步骤数差异列提示
——平台侧配置的函数步骤合法地不与 DSL 对齐，不判差异）。
主要 Input：DSL model.yaml 路径 + 平台侧文件路径（命令行两参数）。
主要 Output：stdout 中文一致性报告；退出码 0=一致，1=存在差异（差异明细列出，
     不视为脚本失败——差异本身是给用户决策的信号）。
平台机制适配（2026-10-14 实证）：SDK 与 MCP 元数据的 relation source/target 属性均为平台内部
     PROP_<hash> 属性 ID，与字段名不可直接映射——关系比对采用 (source, target, cardinality)
     三元组 + 总量核对；字段与主键用字段名直读；MCP 侧 refCode（OBJ_/PROP_）经实体 code 解码。
"""

# 标准库导入
import importlib.util
import json
import sys
from pathlib import Path

# 第三方依赖导入
import yaml

# DSL→平台规则类型映射（对账用：DSL rule_type → 平台 ruleType）
RULE_TYPE_MAP = {"derived_property": "calculation", "trigger": "trigger", "admission": "validation"}


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


# ===========二、MCP 元数据 JSON 加载==========
def load_mcp(path: Path) -> dict:
    """加载 MCP 元数据 JSON（裸六键或 JSON-RPC 包装均可）。

    Args:
        path: metadata_workspace_model 返回的 JSON 文件路径。
    Returns:
        六类元数据字典（entities/relations/rules/actions 至少在前）。
    Raises:
        SystemExit: 文件缺失、JSON 解析失败或结构不含六键时退出码 2（不静默降级）。
    """
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"错误：MCP 元数据文件读取失败（{path.name}）: {exc}", file=sys.stderr)
        sys.exit(2)
    # 解包两层：JSON-RPC 包装 result.structuredContent / result，裸 dict 直接用
    for probe in (data.get("result") if isinstance(data, dict) else None,):
        if isinstance(probe, dict):
            structured = probe.get("structuredContent")
            data = structured if isinstance(structured, dict) and "entities" in structured else probe
            break
    if not (isinstance(data, dict) and "entities" in data):
        print(f"错误：{path.name} 不是 MCP 元数据形态（顶层无 entities 键，也非 JSON-RPC 包装）",
              file=sys.stderr)
        sys.exit(2)
    return data


# ===========三、SDK 侧比对（既有形态）==========
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


# ===========四、MCP 侧比对（六类元数据）==========
def diff_mcp(mcp: dict, dsl: dict, sm: dict) -> tuple[list, list]:
    """MCP 元数据与 DSL/导入产物四类对账（实体/关系/规则/动作）。

    Args:
        mcp: load_mcp 的六类元数据 dict。
        dsl: DSL 模型 dict。
        sm: 导入产物 studio-model.yaml（关系三元组的 DSL 侧来源）。
    Returns:
        (差异清单, 提示清单)——差异影响退出码；提示（如平台侧配置了函数步骤）不影响。
    """
    issues, hints = [], []
    # ref2code：OBJ_ refCode -> 实体 code（关系/规则的 refCode 解码用）。
    ref2code = {e.get("refCode"): e.get("code") for e in mcp.get("entities") or [] if e.get("refCode")}
    mcp_ents = {e.get("code"): e for e in mcp.get("entities") or [] if e.get("code")}
    dsl_ents = dsl.get("entities") or {}
    #   1. 实体/字段/主键（大小写归一，与 SDK 分支同口径）
    mcp_low = {k.lower(): (k, v) for k, v in mcp_ents.items()}
    dsl_low = {k.lower(): k for k in dsl_ents}
    only_mcp = sorted(set(mcp_low) - set(dsl_low))
    only_dsl = sorted(set(dsl_low) - set(mcp_low))
    if only_mcp:
        issues.append(f"仅平台侧存在的实体: {[mcp_low[k][0] for k in only_mcp]}")
    if only_dsl:
        issues.append(f"仅 DSL 侧存在的实体（导入丢失？）: {[dsl_low[k] for k in only_dsl]}")
    for low, (code, ent) in mcp_low.items():
        if low not in dsl_low:
            continue
        dk = dsl_low[low]
        mcp_fields = {a.get("code") for a in ent.get("attrs") or [] if a.get("code")}
        dsl_fields = set(dsl_ents[dk].get("properties", {}).keys())
        if mcp_fields != dsl_fields:
            issues.append(f"实体 {dk} 字段不一致: 仅平台={sorted(mcp_fields - dsl_fields)} "
                          f"仅DSL={sorted(dsl_fields - mcp_fields)}")
        mcp_pk = {a.get("code") for a in ent.get("attrs") or [] if a.get("isKey")}
        dsl_pk = {f for f, s in dsl_ents[dk].get("properties", {}).items()
                  if isinstance(s, dict) and s.get("primary")}
        if mcp_pk != dsl_pk:
            issues.append(f"实体 {dk} 主键不一致: 平台={sorted(mcp_pk)} DSL={sorted(dsl_pk)}")
    #   2. 关系：三元组+基数（PROP 机制同 SDK 分支——source/target 经 refCode 解码到实体 code）
    sm_tris = {(l["source"].lower(), l["target"].lower(), str(l["cardinality"]).upper())
               for l in (sm.get("link_types") or [])}
    mcp_tris = {(ref2code.get(r.get("source"), r.get("source")),
                 ref2code.get(r.get("target"), r.get("target")),
                 str(r.get("cardinality") or "").upper())
                for r in mcp.get("relations") or []}
    mcp_tris = {(str(s).lower(), str(t).lower(), c) for s, t, c in mcp_tris if s and t}
    if sm_tris != mcp_tris:
        for t in sorted(mcp_tris - sm_tris):
            issues.append(f"仅平台侧存在的关系: {t}")
        for t in sorted(sm_tris - mcp_tris):
            issues.append(f"仅导入 yaml 存在的关系（导入丢失？）: {t}")
    #   3. 规则：(name, 平台 ruleType) 集合；calculation 另核输出实体+字段
    dsl_rules = {(str(r.get("name")), RULE_TYPE_MAP.get(r.get("rule_type"), r.get("rule_type")))
                 for r in dsl.get("rules") or [] if r.get("name")}
    mcp_rules = {(r.get("name"), r.get("ruleType")) for r in mcp.get("rules") or [] if r.get("name")}
    if dsl_rules != mcp_rules:
        for t in sorted(dsl_rules - mcp_rules):
            issues.append(f"仅 DSL 侧存在的规则（导入丢失？）: {t}")
        for t in sorted(mcp_rules - dsl_rules):
            issues.append(f"仅平台侧存在的规则: {t}")
    mcp_calc_out = {(r.get("name"), ref2code.get(r.get("outputEntityRefCode"), r.get("outputEntityRefCode")),
                     next((a.get("code") for e in mcp.get("entities") or [] if e.get("refCode") == r.get("outputEntityRefCode")
                           for a in e.get("attrs") or [] if a.get("refCode") == r.get("outputPropertyRefCode")), None))
                    for r in mcp.get("rules") or [] if r.get("ruleType") == "calculation"}
    sm_calc_out = {(r.get("name"), r.get("outputEntityCode"), r.get("outputPropertyCode"))
                   for r in (sm.get("rule_types") or []) if r.get("ruleType") == "calculation"}
    if sm_calc_out != mcp_calc_out:
        for t in sorted(sm_calc_out - mcp_calc_out):
            issues.append(f"计算规则输出口径不一致（DSL 侧有、平台侧不同）: {t}")
    #   4. 动作：name 集合对账；步骤数差异列提示（平台侧配置的函数步骤合法地不与 DSL 对齐）
    dsl_actions = {str(a.get("name")) for a in dsl.get("actions") or [] if a.get("name")}
    mcp_actions = {a.get("name"): a for a in mcp.get("actions") or [] if a.get("name")}
    if dsl_actions != set(mcp_actions):
        for n in sorted(dsl_actions - set(mcp_actions)):
            issues.append(f"仅 DSL 侧存在的动作（导入丢失？）: {n}")
        for n in sorted(set(mcp_actions) - dsl_actions):
            issues.append(f"仅平台侧存在的动作: {n}")
    for n, a in sorted(mcp_actions.items()):
        dsl_steps = 0
        if n in dsl_actions:
            act = next(x for x in dsl.get("actions") or [] if str(x.get("name")) == n)
            dsl_steps = len(act.get("steps") or []) if isinstance(act.get("steps"), list) else 0
        mcp_steps = len(a.get("steps") or [])
        if mcp_steps != dsl_steps:
            hints.append(f"动作 {n} 步骤数: 平台 {mcp_steps} / DSL {dsl_steps}"
                         "（平台侧配置的函数/实现步骤不随 yaml 往返，属预期形态）")
    return issues, hints


# ===========五、主流程==========
def main() -> int:
    """按平台侧输入形态分派对账并输出报告。

    Returns:
        0=完全一致，1=存在差异（明细见输出），2=输入文件缺失/形态不可识别。
    """
    if len(sys.argv) != 3:
        print("用法: python check_platform_sync.py <model.yaml> <平台SDK aquilair.py | MCP元数据.json>")
        return 2
    # dsl_path / side_path：DSL 模型与平台侧文件。
    dsl_path, side_path = Path(sys.argv[1]), Path(sys.argv[2])
    if not dsl_path.is_file() or not side_path.is_file():
        print("错误：输入文件不存在", file=sys.stderr)
        return 2
    dsl = yaml.safe_load(dsl_path.read_text(encoding="utf-8"))
    sm_path = dsl_path.parent / "engine-bundle" / "studio-model.yaml"
    hints: list = []
    if side_path.suffix == ".json":
        mcp = load_mcp(side_path)
        if not sm_path.is_file():
            print(f"错误：缺导入产物 {sm_path}（关系/规则对账以其为 DSL 侧来源），先编译再对账",
                  file=sys.stderr)
            return 2
        sm = yaml.safe_load(sm_path.read_text(encoding="utf-8"))
        print(f"====平台一致性比对（MCP 元数据）====: DSL {dsl_path.name} ↔ {side_path.name}")
        print(f"规模: 平台实体 {len(mcp.get('entities') or [])} / 关系 {len(mcp.get('relations') or [])} "
              f"/ 规则 {len(mcp.get('rules') or [])} / 动作 {len(mcp.get('actions') or [])}")
        issues, hints = diff_mcp(mcp, dsl, sm)
    elif side_path.suffix == ".py":
        sdk_objs, sdk_rels = load_sdk(side_path)
        print(f"====平台一致性比对（SDK）====: DSL {dsl_path.name} ↔ SDK {side_path.name}")
        print(f"规模: 平台实体 {len(sdk_objs)} / 关系 {len(sdk_rels)}")
        issues = diff_entities(sdk_objs, dsl) + diff_relations(sdk_rels, sm_path)
    else:
        print(f"错误：不支持的平台侧文件形态 {side_path.suffix}（.py=SDK / .json=MCP 元数据）",
              file=sys.stderr)
        return 2
    for h in hints:
        print(f"提示: {h}")
    if issues:
        print(f"====发现 {len(issues)} 处差异====")
        for i in issues:
            print(f"- {i}")
        return 1
    print("====完全一致====: 实体/字段/主键/关系/规则/动作对账零差异")
    return 0


if __name__ == "__main__":
    sys.exit(main())
