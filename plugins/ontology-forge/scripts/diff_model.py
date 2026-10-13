"""DSL 模型增量 diff：按 dsl-spec §9 生成两份 DSL YAML 之间的变更集 changeset.json。

主要 Input：base.yaml 与 target.yaml 两个位置参数（DSL v0.2 模型）+ 可选 --base-version <版本串>
（校验与 base DSL 的 version 是否一致，不一致即拒绝——需重读快照重新生成 diff，禁止强推）。
主要 Output：target 同目录 changeset.json（§9 格式：changeset_id 稳定 hash / base_version /
generated_at / operations / breaking / summary）+ stdout 中文摘要（操作数分布、逐条 breaking 说明）。
幂等设计：generated_at 取 target 文件 mtime（非当前时间）、changeset_id 由内容派生——
同一对输入跑两次产物字节一致。
"""

# 标准库导入
import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# 第三方依赖导入
import yaml

# ===========一、常量（diff 覆盖面）==========
# ENTITY_SCALAR_KEYS：实体级参与 diff 的标量字段（governance/provenance 治理字段不进 diff）。
ENTITY_SCALAR_KEYS = ("display_name", "table_name", "description")
# PROPERTY_KEYS：属性子字段 diff 覆盖面（DSL v0.2 §2 属性键全集）。
PROPERTY_KEYS = ("display_name", "description", "type", "primary", "uom", "enum_values", "source", "derived")
# RULE_KEYS：规则子字段 diff 覆盖面（DSL v0.2 §3 规则键全集）。
RULE_KEYS = ("rule_type", "upstream", "logic", "downstream", "description")


class _Collector:
    """操作与 breaking 收集器：统一追加 operations 并对 breaking 项记录 reason。

    Input:
        无初始化参数。
    Return:
        通过 ``operations``（§9 操作列表）与 ``breakings``（(序号, reason) 列表）暴露结果。
    """

    def __init__(self) -> None:
        # operations：§9 操作列表（op / path，add|replace 携带 value）。
        self.operations: list[dict[str, Any]] = []
        # breakings：breaking 项 (operations 序号, 中文 reason) 列表。
        self.breakings: list[tuple[int, str]] = []

    def emit(self, op: str, path: str, value: Any = None, reason: str | None = None) -> None:
        """追加一条操作；reason 非 None 时同时登记 breaking。

        Args:
            op: 操作类型 add|remove|replace。
            path: §9 路径（/entities/<E>、/entities/<E>/properties/<f>/<子字段> 等）。
            value: add/replace 携带的新值；remove 为 None。
            reason: breaking 原因；None 表示非 breaking。
        Returns:
            None。
        """
        entry: dict[str, Any] = {"op": op, "path": path}
        if value is not None:
            entry["value"] = value
        self.operations.append(entry)
        if reason is not None:
            self.breakings.append((len(self.operations) - 1, reason))


# ===========二、实体 diff（标量字段 / 属性 / links 逐项比）==========
def _diff_entity(name: str, base_ent: dict[str, Any], tgt_ent: dict[str, Any], out: _Collector) -> None:
    """diff 一个双方共有的实体：标量字段、属性逐子字段、links 逐别名。

    Args:
        name: 实体名。
        base_ent: base 侧实体定义。
        tgt_ent: target 侧实体定义。
        out: 操作收集器。
    Returns:
        None。
    """
    #   1. 实体级标量字段：值变即 replace（display_name/description 非 breaking，table_name 规格未列为 breaking）
    for key in ENTITY_SCALAR_KEYS:
        old, new = base_ent.get(key), tgt_ent.get(key)
        if old != new:
            out.emit("replace", f"/entities/{name}/{key}", new)
    #   2. 属性：base 侧先比（remove / 子字段 replace），target 侧再补新增
    base_props = base_ent.get("properties") or {}
    tgt_props = tgt_ent.get("properties") or {}
    for field, base_spec in base_props.items():
        if field not in tgt_props:
            out.emit("remove", f"/entities/{name}/properties/{field}",
                     reason=f"删除属性 {name}.{field}：下游查询/技能/看板可能引用该字段")
            continue
        _diff_property(name, field, base_spec or {}, tgt_props[field] or {}, out)
    for field, tgt_spec in tgt_props.items():
        if field not in base_props:
            out.emit("add", f"/entities/{name}/properties/{field}", tgt_spec)
    #   3. links：逐别名比（remove = breaking；目标实体变更 replace 非 breaking——§9 未列为 breaking）
    base_links = base_ent.get("links") or {}
    tgt_links = tgt_ent.get("links") or {}
    for alias, base_target in base_links.items():
        if alias not in tgt_links:
            out.emit("remove", f"/entities/{name}/links/{alias}",
                     reason=f"删除 links 别名 {alias}（实体 {name}）：规则表达式引用路径失效")
        elif base_target != tgt_links[alias]:
            out.emit("replace", f"/entities/{name}/links/{alias}", tgt_links[alias])
    for alias, tgt_target in tgt_links.items():
        if alias not in base_links:
            out.emit("add", f"/entities/{name}/links/{alias}", tgt_target)


def _diff_property(entity: str, field: str, base_spec: dict[str, Any],
                   tgt_spec: dict[str, Any], out: _Collector) -> None:
    """diff 一个双方共有的属性：逐子字段比较。

    Args:
        entity: 所属实体名。
        field: 属性字段名。
        base_spec: base 侧属性定义。
        tgt_spec: target 侧属性定义。
        out: 操作收集器。
    Returns:
        None。
    """
    for key in PROPERTY_KEYS:
        # primary 规范化：DSL 缺省即 false，键缺省与显式 false 等价
        old = base_spec.get(key, False) if key == "primary" else base_spec.get(key)
        new = tgt_spec.get(key, False) if key == "primary" else tgt_spec.get(key)
        if old == new:
            continue
        path = f"/entities/{entity}/properties/{field}/{key}"
        if key == "type":
            out.emit("replace", path, new,
                     reason=f"属性 {entity}.{field} 类型 {old} -> {new}：下游类型假设失效")
        elif key == "primary":
            out.emit("replace", path, new,
                     reason=f"属性 {entity}.{field} 主键标记 {old} -> {new}：主键集合变化，影响实例标识与引用查找")
        else:
            out.emit("replace", path, new)


# ===========三、规则 diff（按 name 匹配，子字段逐个比）==========
def _diff_rules(base_rules: list[Any], tgt_rules: list[Any], out: _Collector) -> None:
    """diff 规则列表：按 name 建索引匹配，logic/upstream/downstream/rule_type/description 任一变即子字段 replace。

    Args:
        base_rules: base 侧规则列表。
        tgt_rules: target 侧规则列表。
        out: 操作收集器。
    Returns:
        None。
    """
    #   1. 按 name 建索引（name 是规则身份；name 变 = 旧 remove + 新 add）
    base_by_name = {r.get("name"): r for r in base_rules if isinstance(r, dict)}
    tgt_by_name = {r.get("name"): r for r in tgt_rules if isinstance(r, dict)}
    #   2. base 侧：remove 与子字段 replace（remove 规则 / replace logic = breaking）
    for name, base_rule in base_by_name.items():
        if name not in tgt_by_name:
            out.emit("remove", f"/rules/{name}",
                     reason=f"删除规则「{name}」：衍生字段/触发行为失去计算来源")
            continue
        for key in RULE_KEYS:
            old, new = base_rule.get(key), tgt_by_name[name].get(key)
            if old == new:
                continue
            path = f"/rules/{name}/{key}"
            if key == "logic":
                out.emit("replace", path, new,
                         reason=f"规则「{name}」计算逻辑变更：衍生字段/触发口径改变")
            else:
                out.emit("replace", path, new)
    #   3. target 侧：新增规则（add 类，非 breaking）
    for name, tgt_rule in tgt_by_name.items():
        if name not in base_by_name:
            out.emit("add", f"/rules/{name}", tgt_rule)


# ===========四、模型级 diff 与 changeset 组装==========
def diff_models(base: dict[str, Any], target: dict[str, Any]) -> _Collector:
    """diff 两份 DSL 模型：实体集合增删 + 实体内部逐项 + 规则逐条。

    Args:
        base: base 侧 DSL 模型 dict。
        target: target 侧 DSL 模型 dict。
    Returns:
        填充完毕的 _Collector（operations + breakings）。
    """
    out = _Collector()
    base_entities = base.get("entities") or {}
    tgt_entities = target.get("entities") or {}
    #   1. base 侧实体：remove 整体 或 内部逐项 diff（确定性：按 base YAML 键序）
    for name, base_ent in base_entities.items():
        if not isinstance(base_ent, dict):
            continue
        if name not in tgt_entities:
            out.emit("remove", f"/entities/{name}",
                     reason=f"删除实体 {name}：下游查询/技能/看板可能引用该实体")
        else:
            _diff_entity(name, base_ent, tgt_entities[name] or {}, out)
    #   2. target 侧新增实体：整实体 add（携带完整定义，含其全部属性/links）
    for name, tgt_ent in tgt_entities.items():
        if isinstance(tgt_ent, dict) and name not in base_entities:
            out.emit("add", f"/entities/{name}", tgt_ent)
    #   3. 规则 diff
    _diff_rules(base.get("rules") or [], target.get("rules") or [], out)
    return out


def build_changeset(base_version: str, generated_at: str, out: _Collector) -> dict[str, Any]:
    """把 diff 结果组装为 §9 变更集 dict（changeset_id 由内容派生，幂等）。

    Args:
        base_version: 所基于的快照版本串。
        generated_at: 生成时间 ISO8601（取 target 文件 mtime，保证幂等）。
        out: 已填充的操作收集器。
    Returns:
        §9 变更集 dict。
    """
    #   1. changeset_id：对 base_version + operations 规范化串做 sha256，取前 16 位十六进制
    canonical = json.dumps(
        {"base_version": base_version, "operations": out.operations},
        ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    changeset_id = hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]
    #   2. summary：三类操作计数
    summary = {op: sum(1 for e in out.operations if e["op"] == op) for op in ("add", "remove", "replace")}
    return {
        "changeset_id": changeset_id,
        "base_version": base_version,
        "generated_at": generated_at,
        "operations": out.operations,
        "breaking": [{"op_ref": idx, "reason": reason} for idx, reason in out.breakings],
        "summary": summary,
    }


# ===========五、命令行入口==========
def main() -> None:
    """命令行入口：版本校验 -> diff -> 写 changeset.json -> 打印中文摘要。"""
    parser = argparse.ArgumentParser(description="两份 DSL YAML 的增量 diff（dsl-spec §9 变更集）")
    parser.add_argument("base", help="base DSL YAML 路径")
    parser.add_argument("target", help="target DSL YAML 路径（changeset.json 写到其同目录）")
    parser.add_argument("--base-version", default=None,
                        help="期望基于的快照版本串；与 base DSL 的 version 不一致即报错退出")
    args = parser.parse_args()

    #   1. 读取两份 DSL 模型
    base_path, tgt_path = Path(args.base), Path(args.target)
    base = yaml.safe_load(base_path.read_text(encoding="utf-8"))
    target = yaml.safe_load(tgt_path.read_text(encoding="utf-8"))
    if not isinstance(base, dict) or not isinstance(target, dict):
        print("错误：base/target 不是合法的 DSL 模型（缺少顶层映射结构）", file=sys.stderr)
        raise SystemExit(2)
    #   2. 版本冲突校验（§9：禁止强推覆盖，需重读快照重新生成 diff）
    base_version = args.base_version if args.base_version is not None else base.get("version")
    if args.base_version is not None and args.base_version != base.get("version"):
        print(f"错误：版本冲突——--base-version={args.base_version} 与 base DSL 的 "
              f"version={base.get('version')} 不一致；目标快照已演进，"
              f"需重读快照重新生成 diff，禁止强推", file=sys.stderr)
        raise SystemExit(1)
    #   3. diff 并落盘 changeset.json（generated_at 取 target mtime 保证幂等）
    out = diff_models(base, target)
    generated_at = datetime.fromtimestamp(tgt_path.stat().st_mtime, timezone.utc).isoformat()
    changeset = build_changeset(base_version, generated_at, out)
    out_path = tgt_path.parent / "changeset.json"
    out_path.write_text(json.dumps(changeset, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    #   4. 中文摘要：操作分布 + breaking 总数 + 逐条 breaking 说明
    print(f"====变更集生成完成====: {base_path} -> {tgt_path}（{out_path}）")
    print(f"操作数分布: add={changeset['summary']['add']}, "
          f"remove={changeset['summary']['remove']}, replace={changeset['summary']['replace']}")
    print(f"breaking 数: {len(changeset['breaking'])}")
    for item in changeset["breaking"]:
        ref = item["op_ref"]
        print(f"  [breaking #{ref}] {out.operations[ref]['path']} —— {item['reason']}")


if __name__ == "__main__":
    # CLI 脚本本体即调试入口：python diff_model.py <base.yaml> <target.yaml> [--base-version <版本串>]
    # Windows 控制台默认编码可能是 GBK，强制 UTF-8 避免中文摘要乱码
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    main()
