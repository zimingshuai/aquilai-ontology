# Ontology DSL v0.1 规范（M0 POC 冻结存档）

> ⚠️ **本文件为 v0.1 验证时点存档**（M0 round-trip 与盲测均基于 v0.1 执行，结论见 poc/m0/REPORT.md）。
> **正式版规范 v0.2 已移至**：`plugins/ontology-forge/skills/ontology-modeling/references/dsl-spec.md`
> v0.1 → v0.2 变更（M0 POC 产出，共 6 条）：①衍生字段必须在实体 properties 声明；②外键字段保留属性 + links 并存；③§3.1 增加方言 cookbook；④定义多跳反向聚合语法；⑤明确 upstream 语义；⑥lint 补充两条。变更与 v0.1 的 fnb.model.yaml 形态兼容（逆向导出本就按引擎实际形态生成）。

> 版本：v0.1（2026-10-13，M0 POC 冻结版）｜ 状态：POC 验证中，M1 前按 POC 结论修订
> 依据：docs/design/2026-10-10-ontology-modeling-plugin-design.md §5（五元素元模型）
> 本质定位：面向 Aquilair 本体引擎的**本体元数据设计**（数据模型层 + 语义标注层 + 行为契约层），非 OWL 本体

## 1. 顶层结构

```yaml
ontology: <string>            # 本体标识（kebab-case，如 fnb、supplier-recon）
version: <string>             # 语义化版本，草稿态带 -draft.N 后缀
base_version: <string|null>   # 增量建模时基于的引擎快照版本；从零建库为 null
governance:                   # 本体级治理（Palantir 规则：必配 owner + maturity）
  owner: <string>
  maturity: experimental|active|deprecated
entities: { ... }             # 实体（见 §2），必填
rules: [ ... ]                # 规则（见 §3），可空
actions: [ ... ]              # 动作（见 §4），一期不含，保留槽位
competency_questions: [ ... ] # 能力问题（见 §5）
open_questions: [ ... ]       # 待确认问题（禁止脑补，人审前必须清零或标记接受）
conflicts: [ ... ]            # 口径冲突记录（保留双方定义与来源）
assumptions: [ ... ]          # 生成假设清单
```

## 2. entities（实体）

```yaml
entities:
  <EntityName>:               # 实体名 PascalCase（对齐引擎惯例，如 SKUInWarehouse）
    display_name: <string>    # 中文展示名（必填；LLM 问答质量依赖它）
    table_name: <string>      # 物理表名（必填；不假设与实体名存在大小写变换关系）
    description: <string>     # 业务定义（必填）
    governance:               # 可选，缺省继承本体级
      { owner: <string>, maturity: <string> }
    properties:               # 必填，至少一个 primary
      <field_name>:           # 字段名 snake_case（对齐引擎惯例）
        display_name: <string>   # 必填
        description: <string>    # 可选（引擎要求键存在，可为空串）
        type: <enum>             # 必填，仅 7 种：STRING|INTEGER|DOUBLE|DECIMAL|BOOLEAN|DATE|TIMESTAMP
        primary: <bool>          # 可选，默认 false；支持复合主键（多字段 true）
        uom: <string>            # 可选，量纲（kg/元/天/件）
        enum_values: [<string>]  # 可选，枚举值清单
        source: <string>         # 可选，provenance（来源文档#位置）
    links:                     # 可选；键 = 引用别名（同时是规则表达式的引用前缀）
      <alias>: <TargetEntity>   # 默认别名 = 目标表名 snake_case；可用短别名（如 wh）
    provenance:                # 可选
      { doc: <string>, reviewed: <bool> }
```

**links 语义**：`alias: TargetEntity` 表示本实体持有指向 TargetEntity 的引用。反向一对多集合（如 SKU 可引用其所有 purchase_orders）**不写进 links**（引擎侧由对方持有引用推导），但在规则表达式中可用复数表名引用（如 `SUM(purchase_orders.total_order_qty)`）——**复数引用名 = 引用方表名 + s**（引擎实测惯例：`purchase_orders`、`sku_in_whs`）。例外（es 结尾等）以引擎实际为准，编译时从快照校验。

## 3. rules（规则，三类）

### 3.1 derived_property（衍生属性）

```yaml
- rule_type: derived_property
  name: <string>              # 规则名（中文，人审用）
  upstream: [<EntityName>]    # 依赖实体
  logic: "<目标字段>: <表达式>"  # 目标字段必须是某个 upstream 实体的属性
  description: <string>       # 口径的业务含义（人审重点）
```

**表达式方言**（引擎实测能力边界，lint 强制）：
- 四则运算 `+ - * /`、括号
- 点路径跨实体引用：`sku.abc_type`、多跳 `sku.product_category.pc_code`（前缀 = links 别名）
- 反向集合聚合：`SUM(sales_orders.unfulfill_qty)`
- 函数：`SUM(x[, ...])`、`COALESCE(x, 默认值)`、`MAX(a, b)`
- 数值/字符串字面量

### 3.2 trigger（触发规则）

```yaml
- rule_type: trigger
  name: <string>
  upstream: [<EntityName>]    # 条件所依附的实体
  logic:
    ALL:                      # 合取（当前引擎仅支持 ALL）
      - { field: <字段或别名.字段路径>, operator: <op>, value: <标量或数组> }
  downstream: <action_name>   # 触发的动作（引擎内置隐式 action 亦可，如 update_inventory_level）
  description: <string>
```

**operator 枚举**：`== != > >= < <= in`（value 为数组时必须用 in）。

### 3.3 admission（动作准入，仅含 action 的本体）

```yaml
- rule_type: admission
  name: <string>
  upstream: [<action_name>]   # 准入所依附的动作
  logic:
    ALL:
      - check: param         # 参数检查
        param: <参数名>
        operator: <op>
        value: <标量>
      - check: instance      # 实例检查
        entity: <EntityName>
        lookup: { <主键字段>: "@param:<参数名>" }   # @param: 注入；支持嵌套实体查找
        field: <字段或路径>
        operator: <op>
        value: <标量|{param: <参数名>}>
  downstream: "Action 准入拦截: <action_name>"
```

## 4. actions（动作，一期不含，槽位保留）

```yaml
- name: <action_name>          # snake_case
  description: <string>
  parameters: { <参数名>: "str"|"float" }   # 引擎类型标注为字符串
  supports_sandbox: <bool>
  body_ref: <path>             # Python body 模板（无法声明式生成，人工插桩）
```

## 5. competency_questions（能力问题）

```yaml
- id: <cq-NNN>
  q: <string>                  # 业务应能回答的问题（自然语言）
  covered_by: [<Entity.field 或 Entity>]   # 依赖的 DSL 元素（CQ 覆盖矩阵用）
```

## 6. 编译目标映射（DSL → 引擎注册格式）

| DSL | 引擎注册格式（get_meta_objects / get_meta_rules 返回结构） |
|---|---|
| `entities.<E>.display_name` | `{<E>: {display_name}}` |
| `entities.<E>.table_name` | `{<E>: {table_name}}` |
| `entities.<E>.description` | `{<E>: {description}}` |
| `properties.<f>.{display_name,description}` | `{<E>.properties.<f>: {display_name, description}}` |
| `properties.<f>.type` | `...{data_type}`（枚举同 DSL 7 种） |
| `properties.<f>.primary` | `...{is_primary}` |
| `links.<alias>` | `{<E>: {links: {<alias>: <Target>}}}` |
| `rules[derived].logic` | `{rules: [{rule_type: "derived_property", logic: "字段: 表达式", upstream, downstream: "Computed Property", name, description}]}` |
| `rules[trigger].logic` | `{rules: [{rule_type: "trigger", logic: {ALL: [...]}, upstream, downstream: <action>, name, description}]}` |
| `rules[admission].logic` | `{rules: [{rule_type: "admission", logic: {ALL: [...]}, upstream: [<action>], downstream: "Action 准入拦截: <action>", name, description}]}` |

**round-trip 校验口径**：DSL → 编译 → 引擎格式，与引擎实测快照（get_meta_* 原始返回）做**深度逐键比对**，允许差异仅限：治理字段（governance/provenance/uom/enum_values/source——引擎不存储）与 CQ/open_questions（插件自有产物）。其余任何差异 = round-trip 失败。

## 7. lint 规则（M0 最小集，确定性检查）

1. schema 合法：类型枚举、必填键、命名风格（实体 PascalCase、字段 snake_case）
2. 主键：每个实体至少 1 个 primary；主键字段类型建议 STRING
3. links 闭合：目标实体必须存在；别名在实体内唯一
4. 表达式静态检查：derived 的目标字段存在于 upstream 实体；引用前缀是合法 links 别名或复数引用；函数名在白名单内
5. trigger：field 路径可解析；operator 合法；in 必须配数组
6. 受控词表（fnb/mfg 既有术语优先复用，新词入库走评审）——M0 暂缓，M1 落地
