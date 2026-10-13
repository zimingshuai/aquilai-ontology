# Ontology DSL 规范 v0.2

> 版本：v0.2（2026-10-13，按 M0 POC 结论修订）｜ 正式版 source of truth
> v0.1→v0.2 变更：①衍生字段必须在实体 properties 声明；②外键字段保留属性 + links 并存；③增加方言 cookbook；④定义多跳反向聚合语法；⑤明确 upstream 语义；⑥lint 补充两条（依据：poc/m0/REPORT.md §五）
> 本质定位：面向 Aquilair 本体引擎的**本体元数据设计**（数据模型层 + 语义标注层 + 行为契约层），非 OWL 本体

## 1. 顶层结构

```yaml
ontology: <string>            # 本体标识（kebab-case，如 fnb、supplier-recon）
version: <string>             # 语义化版本，草稿态带 -draft.N 后缀
base_version: <string|null>   # 增量建模时基于的引擎快照版本；从零建库为 null
governance:                   # 本体级治理（新建本体必配；快照逆向导出可缺省，lint 降为 warning）
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
        derived: <bool>          # 可选，标注该字段由 derived_property 规则计算（lint 规则 7 方向 B
                                 #   依据：标了 derived: true 就必须有对应规则；不标则仅正向检查）
    links:                     # 可选；键 = 引用别名（同时是规则表达式的引用前缀）
      <alias>: <TargetEntity>   # 默认别名 = 目标表名 snake_case；可用短别名（如 wh）
    provenance:                # 可选
      { doc: <string>, reviewed: <bool> }
```

**两条强制约定（v0.2，引擎实测裁决）**：

1. **衍生字段必须在 properties 中声明**：derived_property 规则的目标字段必须已在该 upstream 实体的 properties 里声明（含 type/display_name/description），计算逻辑由规则承载。引擎实际形态即如此（fnb 的 SKUInWarehouse.properties 含 inventory_turnover_days / idd / inventory_level 等衍生字段）。类型为推断时在 assumptions 记录。
2. **外键字段保留为属性 + links 并存声明**：外键字段（如 supplier_code）作为普通属性保留声明，同时以 links 声明引用关系（引擎实际：fnb PurchaseOrder.properties 有 sku_code/wh_code 且 links 并存）。

**links 语义**：`alias: TargetEntity` 表示本实体持有指向 TargetEntity 的引用。反向一对多集合不写进 links（引擎侧由对方持有引用推导），但在规则表达式中可用复数名引用（如 `SUM(purchase_orders.total_order_qty)`）——**复数引用名 = 被引用方的表名 + s 或 其 links 短别名 + s，两种形态均合法**（引擎实证：`purchase_orders`（表名+s）、`sku_in_whs`（别名 sku_in_wh + s，而非表名+s 的 sku_in_warehouses）；M1 lint 按双形态白名单校验，v0.3 待引擎侧确认生成规则后收敛为单形态）。

## 3. rules（规则，三类）

**upstream 语义（v0.2 明确）**：upstream = 计算/条件所**依附的主实体**（引擎实测为单实体列表）。derived 的目标字段属于 upstream 实体；trigger 的 field 路径以 upstream 实体为起点；路径中经由的其他实体不是 upstream（如两跳聚合只写 [Supplier]）。

### 3.1 derived_property（衍生属性）

```yaml
- rule_type: derived_property
  name: <string>              # 规则名（中文，人审用）
  upstream: [<EntityName>]    # 依附的主实体（单实体）
  logic: "<目标字段>: <表达式>"  # 目标字段必须已声明于 upstream 实体 properties（§2 约定 1）
  description: <string>       # 口径的业务含义（人审重点）
```

**表达式方言**（引擎实测能力边界，lint 强制）：
- 四则运算 `+ - * /`、括号
- 点路径跨实体引用：`sku.abc_type`、多跳 `sku.product_category.pc_code`（前缀 = links 别名）
- 反向集合聚合（单跳）：`SUM(sales_orders.unfulfill_qty)`
- **多跳反向聚合（v0.2 定义的候选语法，待引擎侧验证）**：嵌套路径 `SUM(purchase_contracts.delivery_records.delivery_amount)`——从 upstream 实体沿 links 方向逐级取反向集合。fnb 实测无先例，首个使用场景必须标注 open_question 并在引擎沙箱验证；若不支持，回退方案为逐级衍生（先在中间实体算合计，再 SUM 到主实体）
- 函数：`SUM(x[, ...])`、`COALESCE(x, 默认值)`、`MAX(a, b)`
- 数值/字符串字面量

**方言 cookbook（v0.2 新增，引擎惯例示例——生成时优先采用，避免保守化）**：
- 除法兜底惯例：`COALESCE(x / y, 9999)`（引擎作者在 fnb 库存周转天数上的实际写法：`inventory_turnover_days: COALESCE(average_inventory_qty / average_daily_outbound_qty, 9999)`）——分母为空/异常时给哨兵值
- 加权平均惯例：`SUM(子集合.指标 * 子集合.权重) / SUM(子集合.权重)`（fnb 平均库存元天写法）
- 空值兜底：`COALESCE(字段, 0)`

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
| `properties.<f>.primary` | `...{is_primary}`（false 时编译省略键或置 false，以引擎快照形态为准） |
| `links.<alias>` | `{<E>: {links: {<alias>: <Target>}}}`（无 links 的实体编译回填 `{}`） |
| `rules[derived].logic` | `{rules: [{rule_type: "derived_property", logic: "字段: 表达式", upstream, downstream: "Computed Property", name, description}]}` |
| `rules[trigger].logic` | `{rules: [{rule_type: "trigger", logic: {ALL: [...]}, upstream, downstream: <action>, name, description}]}` |
| `rules[admission].logic` | `{rules: [{rule_type: "admission", logic: {ALL: [...]}, upstream: [<action>], downstream: "Action 准入拦截: <action>", name, description}]}` |

**编译剥离清单**：DSL 自有字段（governance / provenance / uom / enum_values / source / competency_questions / open_questions / conflicts / assumptions）引擎不存储，编译时必须剥离——编译产物只含引擎格式键。

**round-trip 校验口径**：DSL → 编译 → 引擎格式，与引擎实测快照做**深度逐键比对**；编译产物中出现任何引擎格式之外的键 = 失败。

## 7. lint 规则（M1 全集，确定性检查）

1. schema 合法：类型枚举、必填键、命名风格（实体 PascalCase、字段 snake_case）
2. 主键：每个实体至少 1 个 primary；主键字段类型建议 STRING
3. links 闭合：目标实体必须存在；别名在实体内唯一
4. 表达式静态检查：derived 的目标字段**已声明于** upstream 实体 properties（v0.2 约定 1）；引用前缀是合法 links 别名或复数引用；函数名在白名单内（SUM/COALESCE/MAX）
5. trigger：field 路径可解析；operator 合法；in 必须配数组
6. derived 的 `downstream: "Computed Property"` 由编译器回填，DSL 不写
7. **衍生字段一致性（v0.2）**：所有 derived 目标字段在 properties 中有声明；properties 中标注衍生的字段（如有约定标记）必须有对应 derived 规则
8. **外键-links 一致性（v0.2）**：links 别名与外键字段对应关系可解释；外键字段值域/类型与目标实体主键兼容（type 相同或均可字符串化）

受控词表检查（fnb/mfg 既有术语优先复用，新词入库走评审）——seeds 就绪后作为第 9 条启用。
