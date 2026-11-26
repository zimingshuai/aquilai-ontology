# Ontology DSL 规范 v0.4

> 版本：v0.4（2026-11-26：平台 yaml 导入格式对标（docs/reference/新品上市POC-最新版-20261125_163759.zip 升级说明）——links 显式形态新增可选键 `cardinality`（n:1/1:1）；trigger 规则新增 `branches` 多分支与 `with` 动作参数映射（与旧 logic+downstream 二选一）；actions 新增声明式形态（`steps` 数据/通知步骤、`function` 函数型、`validation_rules` 挂载校验）；derived 增注编译关系路径自动推导。**全部新键可选，旧 DSL 零改动继续合法**——lint 新增第 16-19 条，仅对新键存在时校验）
> v0.3.6（2026-11-02：OQ schema 对齐复验版实战形态（topic/question/proposal 键 + 七态状态机，修订 v0.3.9 固化时未对齐的 q/四态）；lint 新增第 14 条 OQ/conflicts 结构与第 15 条枚举双写）
> v0.3.5（2026-11-02：xgimi 全产物遍历反哺——文件头治理注释三行、属性 source 锚点格式、枚举双写、衍生公式 description 重述、可空外键/自引用/单表多态约定、规则级 source 键、编译剥离清单补登 derived 与规则 source）
> v0.3.4（2026-10-15：关系语义名纪律——links 必须说清"是什么关系"，lint 第 13 条）
> v0.3（2026-10-13，按 M2/M3 与端到端复验的实证发现升级）
> v0.2.2→v0.3 变更：①links 支持显式 fk 声明（复合外键场景，xgimi 实证 13 连线收敛问题）；②lint 第 12 条规则名全局唯一（fnb 31 处重名实证：引擎合法但 studio-model code 需唯一）；③lint 第 9 条受控词表正式启用（同文档两次独立生成仅 7/26 实体同名的漂移实证）+ seeds/glossary.md 术语对照表机制。
> 本质定位：面向 Aquilair 本体引擎的**本体元数据设计**（数据模型层 + 语义标注层 + 行为契约层），非 OWL 本体

## 1. 顶层结构

**文件头治理注释三行（v0.3.5，xgimi 实证反哺）**：YAML 首个键之前以注释声明三行——①版本行（`# <域> 本体 DSL v<version>`）②依据行（`# 依据：models/<domain>/modeling-brief/...`，资料包定位）③状态行（`# 状态：draft——人审是唯一权威，未确认不得注册引擎`，定稿后改 `# 状态：final（人审通过 <日期>）`）。治理机读信息走 governance 键，这三行是**人读红线**——阅读文件第一眼就知道能不能注册引擎。

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
open_questions:                # 待确认问题（v0.3.9 固化、v0.3.6 对齐复验版实战形态——OQ 是建模质量的核心承载，禁止脑补铁律的落点）
  - id: OQ-NN                  #   域内唯一编号（大写 OQ- 前缀，lint14 校验格式与唯一性）
    topic: <string>            #   主题短语（问询单/呈审检索锚点，如"方言缺向上取整函数"）
    question: <string>         #   问题原文（完整一句话，说清缺口与影响）
    proposal: <string>         #   可选，建模侧提案（运行时契约/回退方案/验收用例）
    missing_from: <string>     #   缺在哪份材料/哪个环节（可空——方言边界类缺的是引擎能力而非材料）
    status: pending-engine | pending-business | pending-input | resolved
             | resolved-pending-engine | resolved-pending-business | resolved-pending-input
                               #   七态三组（v0.3.6 修订，xgimi 复验版 12 条 OQ 实证）：
                               #   pending-* 未裁决（等引擎/等业务方/等输入）；
                               #   resolved 已裁决且落地；resolved-pending-* 已裁决、待某方落地佐证
    resolution: <string>       #   裁决留痕（status 含 resolved 时必填：裁决内容+日期+裁决人；原文永不删除）
conflicts:                    # 口径冲突记录（v0.3 固化 schema，结构漂移=不合规）
  - topic: <string>           #   冲突主题（术语/口径名）
    side_a: { claim: <定义>, source: <来源文档#位置> }
    side_b: { claim: <定义>, source: <来源文档#位置> }
    status: pending|resolved  #   人审裁决前一律 pending
    impact: <string>          #   可选，受影响的规则/实体
assumptions: [ ... ]          # 生成假设清单
```

**两条写法约定（v0.3.5，xgimi 实证反哺）**：

1. **conflicts/assumptions 用显式空集合**：无冲突时写 `conflicts: []` 而非省略键——显式空数组表达"查过、结论为零"，省略会被误读为"没查过"。
2. **待决点行内交叉引用**：属性/规则 description 中涉及未决事项时，就地锚定 `（…见 open_questions）` / `（…见 assumptions）`（如"编码规则待确认，见 open_questions"），让待决点与具体字段互相可寻——禁止只在顶层 OQ 列表里登记而在字段处无痕。

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
        enum_values: [<string>]  # 可选，枚举值清单——声明枚举时 description 必须双写（见下方约定 3）
        source: <string>         # 可选，provenance（来源文档#位置——格式见下方约定 2）
        derived: <bool>          # 可选，标注该字段由 derived_property 规则计算（lint 规则 7 方向 B
                                 #   依据：标了 derived: true 就必须有对应规则；不标则仅正向检查）
                                 #   derived 字段须在 description 重述公式（见下方约定 4）
    links:                     # 可选；键 = 引用别名（同时是规则表达式的引用前缀）
      <alias>: <TargetEntity>   # 默认别名 = 目标表名 snake_case；可用短别名（如 wh）
    provenance:                # 可选
      { doc: <string>, reviewed: <bool> }
```

**两条强制约定（v0.2，引擎实测裁决）**：

1. **衍生字段必须在 properties 中声明**：derived_property 规则的目标字段必须已在该 upstream 实体的 properties 里声明（含 type/display_name/description），计算逻辑由规则承载。引擎实际形态即如此（fnb 的 SKUInWarehouse.properties 含 inventory_turnover_days / idd / inventory_level 等衍生字段）。类型为推断时在 assumptions 记录。
2. **外键字段保留为属性 + links 并存声明**：外键字段（如 supplier_code）作为普通属性保留声明，同时以 links 声明引用关系（引擎实际：fnb PurchaseOrder.properties 有 sku_code/wh_code 且 links 并存）。

**四条写法约定（v0.3.5，xgimi 21 实体全域 186 属性实证反哺）**：

3. **枚举双写**：声明 `enum_values` 的字段，description 必须逐一给出 `code=中文含义` 对照（如 `MP=量产；NPI-DVT=新品设计验证；…`），且**覆盖全部枚举值**——enum_values 编译时被剥离（§6），description 是引擎侧唯一的语义载体；漏写即产出"孤儿枚举值"（实证：xgimi stage 的 NPI-EVT 曾在任何产物中都查不到含义）。
4. **衍生公式重述**：`derived: true` 字段的 description 以「衍生：」前缀重述口径（如 `衍生：行用量 ÷ 基准数量`）——derived 标记与规则 logic 均不进引擎产物，description 重述保证人审/平台侧不回读 DSL 也能看懂口径。
5. **source 锚点格式**：`source: <材料类目录>/<文件名>#<章节锚点>`（如 `B_scenarios/xgimi-poc-design.md#附录A.2`）——材料分类目录/文件/锚点三级粒度全域一致，provenance 才能机器定位；规则级 source 同此格式（§3）。
6. **可空外键语义**：外键可空（如"仅替代类变化才有 bom_line_code"）时 DSL 无可空性键可用——**在字段 description 写明可空条件，并在 assumptions 登记推断依据**；平台导入时该 FK 是否必填以人审裁定为准。

**links 语义与显式 fk 声明（v0.3）**：

```yaml
    links:
      supplier: Supplier                          # 简写形态：外键字段 = 目标主键字段名（v0.2 约定不变）；不带基数（缺省 n:1）
      project: { target: Project, name: 隶属项目 }             # 显式形态：fk 可缺省（视同简写约定），仅声明关系语义名
      demand: { target: Demand, fk: [demand_id], name: 项目需求, description: 项目各来源需求（MPS/订单/预测）的挂载 }  # 显式形态：外键+语义名+业务定义
      # description（v0.3.7，用户实证：关系只有名字没有业务定义，平台侧全部空串）：一句话说清这条关系表达的业务含义/约束
      sku_in_wh: { target: SKUInWarehouse, fk: [sku_code, wh_code], cardinality: "n:1" }  # 复合外键（桥接引用）+ 基数（v0.4）
```

**links 基数（v0.4 新增可选键 `cardinality`，仅显式形态可带）**：取值 `n:1 | 1:1`，方向语义 = 「本实体 : 目标实体」（本实体持有外键时通常 n:1）；缺省 `n:1`（与现行约定一致），简写形态不带基数。**`1:n` 与 `n:n` 不进 DSL**：一对多由目标侧实体的 links 表达（反向集合引擎侧推导，既有约定）；平台 n:n 无建模先例，不引入。lint 第 16 条：显式形态声明 cardinality 时取值必须 ∈ {n:1, 1:1}，其他取值报 error。

`alias: TargetEntity` 表示本实体持有指向 TargetEntity 的引用。**自引用 links 合法（v0.3.5 明示，xgimi 实证：Demand→Demand 的 covered_by）**：别名与被引用实体内同名 links 不冲突；规则表达式中沿自引用别名的引用照常解析，反向复数引用名生成规则不变（表名/别名 + s）。**关系语义名（name）是建模必填纪律（v0.3.4，用户实证：只建连线不说清"是什么关系"，拓扑与平台关系名不可读）**：每条 links 应声明中文关系语义名（动宾/偏正短语，如 订购物料/隶属项目/换算物料），进 studio-model 的 link name 与拓扑连线标签；简写形态无法带 name（lint13 提示）。**显式 fk 形态用于外键字段 ≠ 目标主键名的场景（fk 可缺省）**（xgimi 实证：PurchaseOrder 经 sku_code+wh_code 复合引用 SKUInWarehouse，简写约定无法表达，studio-model 编译报错）；fk 字段列表必须在 properties 中有声明（lint 校验）。反向一对多集合不写进 links（引擎侧推导），规则表达式中可用复数名引用（如 `SUM(purchase_orders.total_order_qty)`）——**复数引用名 = 被引用方的表名 + s 或 其 links 短别名 + s，两种形态均合法**（引擎实证：`purchase_orders`（表名+s）、`sku_in_whs`（别名 sku_in_wh + s）；多形态白名单校验，收敛为单形态待引擎侧确认）。

**受控词表（v0.3 正式启用，lint 第 9 条）**：新建/增量建模时须对照 `seeds/glossary.md` 术语对照表优先复用既有命名；跨域同义实体（如 fnb `SKU` ↔ mfg `Material`）与同域历史版本命名（如 xgimi 两版 `RunSnapshot`↔`CalculationRun`）都登记在 glossary——**同域重跑必须走增量模式（diff/复用）而非从零生成**；新术语入库在人审时裁定。

## 3. rules（规则，三类）

**upstream 语义（v0.2 明确）**：upstream = 计算/条件所**依附的主实体**（引擎实测为单实体列表）。derived 的目标字段属于 upstream 实体；trigger 的 field 路径以 upstream 实体为起点；路径中经由的其他实体不是 upstream（如两跳聚合只写 [Supplier]）。

### 3.1 derived_property（衍生属性）

```yaml
- rule_type: derived_property
  name: <string>              # 规则名（中文，人审用）
  upstream: [<EntityName>]    # 依附的主实体（单实体）
  logic: "<目标字段>: <表达式>"  # 目标字段必须已声明于 upstream 实体 properties（§2 约定 1）
  description: <string>       # 口径的业务含义（人审重点）
  source: <string>            # 可选，provenance（v0.3.5 固化，xgimi 10 条规则全带实证——格式同 §2 约定 5；
                             #   规则 source 编译时剥离（§6），DSL 是唯一溯源载体）
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

**编译关系路径自动推导（v0.4 增注——表达式方言不变，编译行为契约，编译器实施）**：DSL 点路径（如 `sku.product_category.pc_code`）在编译到平台计算规则时**自动推导关系路径**（平台侧 `expressionSources.relationPath`，见 2026-10-20 升级说明：外部实体属性必须明确关系路径）——从输出实体沿 links 图取最短路径：路径**唯一**即自动生成；存在**多条**路径即编译报错，要求建模侧改写表达式（显式经由确定的 links 别名逐跳表达，消除歧义）——不猜。

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
  source: <string>            # 可选，provenance（v0.3.5，同 §3.1——触发规则的出处多为异常小节/红线段，
                             #   source 是"这条规则为什么存在"的唯一线索）
```

**operator 枚举**：`== != > >= < <= in`（value 为数组时必须用 in）。

**branches 多分支形态（v0.4 新增，与旧 `logic`+`downstream` 二选一，同现即 error——lint 第 17 条）**：

```yaml
- rule_type: trigger
  name: 上市事项执行状态
  upstream: [DishLaunchItem]
  branches:
    - condition: { ALL: [ {field: <字段或别名.字段路径>, operator: <op>, value: <标量或数组>} ] }
      downstream: <action_name>     # 命中此分支即触发该动作
      with: { "<$参数名>": <常量 | "@Entity.attr"> }      # 可选：动作参数映射，键带 $ 前缀
    - condition: { ALL: [...] }
      downstream: <action_name>
      with: {...}
    - downstream: <action_name>    # 无条件项即兜底分支（otherwise）
      with: {...}
  description: ...
  source: ...
```

**branches 约束（lint 第 17 条，仅 branches 存在时校验——旧 DSL 零改动合法）**：
- `branches` 与旧 `logic`/`downstream` 并存即 error（两种形态二选一，不猜哪种生效）；
- branches 至少一个**条件分支**（含 condition 项）；**兜底分支**（无 condition 项）至多一个且必须是最后一项（对应平台 cases→if/else_if、otherwise→else，分支按数组顺序首中即止）；
- condition 沿用既有条件结构：`{ALL: [...]}` 合取、field 以 upstream 实体为起点可解析、operator 沿用枚举 `== != > >= < <= in`、in 配数组；
- `with` 的键为动作参数名，**必须带 `$` 前缀书写**（如 `$status`）且参数须在 `downstream` 动作的 parameters 中（对照时忽略前缀差异：`$x` ≡ `x`——兼容 recipe 动作不带 $ 与声明式动作带 $ 两种 parameters 键书写）；
- `with` 的值只允许**常量**或 **`@Entity.attr`** 形式（实体须存在、字段须在其 properties 声明）。

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

## 4. actions（动作，v0.2.2：M3 按引擎 8 个真实 action 实测定稿；v0.4：新增声明式形态）

action body 是可执行 Python 源码（无法声明式生成）——DSL 声明**元数据 + 骨架配方（recipe）**，编译器生成 body 骨架，业务逻辑人工插桩（`# TODO` 标记处）。

**声明式形态（v0.4 新增，新键 `steps` 与旧 `recipe`+`body_ref` 互斥，同现即 error——lint 第 18 条）**——数据/通知类动作不再生成 Python 骨架，步骤即动作本体（对齐平台 2026-10-23 简化报文）：

```yaml
actions:
  - name: update_recon_status            # snake_case
    description: <中文三要素：业务语义 + 写操作风险 + 确认卡要求>
    parameters: { "<$参数名>": "string|float" }     # 仍必写（lint 与文档用；平台 yaml 侧由步骤推导，不重复）
    steps:                                # 与 recipe 互斥；函数型动作不写 steps
      - type: data
        entity: <EntityName>              # 目标实体，须存在
        operation: create | update
        assignments:                       # 字段赋值，键须在该实体 properties 声明
          <field>: <常量 | "@param:$参数名" | "@Entity.attr">
      - type: notification
        channel: dingtalk
        recipients: <常量 | "@param:$参数名" | "@Entity.attr">
        content: <常量 | "@param:$参数名" | "@Entity.attr">
    function: { name: <函数名>, description: <一句话> }   # 可选：函数型动作（平台函数是代码包元数据，
                                                          # 不随 yaml 往返——编译导入说明标注，DSL 只声明契约）
    validation_rules: [<admission 规则名>]                # 可选：挂载的准入校验（rule_type: admission）
```

**声明式形态约束（lint 第 18/19 条，仅新键存在时校验）**：
- `steps` 与 `recipe` 并存即 error、`steps` 与 `function` 并存即 error（函数型动作不带步骤）；
- `parameters` 仍必写：DSL 侧是 lint 对照与文档的唯一参数口径（平台 yaml 侧由步骤推导，编译时不重复生成）；
- **参数名 $ 前缀约定**：声明式动作的 parameters 键、`@param:$参数` 引用与 trigger 分支 `with` 的键均以带 `$` 的完整参数名书写；lint 对照 parameters 时忽略前缀差异（`$x` ≡ `x`），兼容 recipe 动作（键不带 $，v0.2.2 形态）与声明式动作（键带 $）两种书写；
- `steps` 逐项可解析：`type` ∈ {data, notification}；data 步骤的 `entity` 须存在、`operation` ∈ {create, update}、assignments 字段须在该实体 properties 声明、值形态合法（常量 / `@param:$参数` 且参数在本动作 parameters / `@Entity.attr` 且实体字段可解析）；notification 步骤的 `channel`/`recipients`/`content` 必填非空且值形态合法；
- `validation_rules` 引用的规则必须存在、`rule_type: admission`、且其 upstream 即本动作名（lint 第 19 条）。

**骨架配方形态（v0.2.2 既有，recipe + body_ref）**：

```yaml
actions:
  - name: <action_name>            # snake_case
    description: <中文描述，强制三要素：业务语义 + 写操作风险声明 + 确认卡要求>
    parameters: { <参数名>: "str"|"float" }   # 引擎类型标注为字符串；可选参数加 `?` 后缀（如 "float?"）
    supports_sandbox: <bool>       # 写操作默认 true
    recipe: modify_instance|state_transition|create_records   # 骨架配方（三选一）
    recipe_config: { ... }         # 配方参数，见下
    body_ref: <path>               # 生成后的骨架文件路径（人工插桩后此文件回填编译）
```

**三种配方（引擎 8 个真实 action 归纳）与 recipe_config**：

1. `modify_instance`（单实例字段修改：disable_strategy / modify_plan / modify_material_in_plant_stock 型）：
   `{target_entity, lookup: {主键字段: "@param:参数名"}, set_fields: {字段: "@param:参数名"|常量}, status_guard: {field, expect}}`
2. `state_transition`（状态机迁移+级联：confirm_solution / execute_solution 型）：
   `{target_entity, lookup, from_status, to_status, cascade: [{entity, via, from, to}]}`
3. `create_records`（计算生成记录：evaluate_solution / run_supply_demand_allocation 型）：
   `{target_entity, input_entities: [<查询的输入实体>], output_fields: [<生成字段>]}`——骨架只给查询输入 + `# TODO 业务计算` 区 + edits.create 样例

**body 骨架的统一模式（生成器必须遵循，全部来自实测）**：`@action` 装饰器；签名含隐式 `store: OntologyStore | None = None`；docstring = description 原文；`edits = OntologyEdits(); store = store or OntologyStore()` 开头；主键定位 `store.query_instances("<Entity>")` + `next(...)`；存在性/状态前置校验 `raise ValueError(中文消息)`；实例重建排除 property 属性（`if not isinstance(getattr(type(obj), k, None), property): setattr(...)`）；变更走 `edits.modify/modify/create`；返回 `edits`。主键生成模式（create 类）：`f"前缀-{参数}-{时间戳%-Y%m%d%H%M%S%f[:-3]}-{uuid4().hex[:4]}"`。

**宿主 API 实证（2026-10-14 平台 SDK：docs/reference/aquilair-sdk-template.py）**：`OntologyEdits` 为编辑意图容器（CREATE/UPDATE/DELETE 三种操作，同对象重复编辑自动合并，`get_edits` 只返回意图不发 HTTP——真正写回由 Action Runtime 负责）；查询侧 `EntityEndpoint.static().load()` / `.where(FieldRef.eq(...))` / `.search_around(link_code)`（关系点访问）；`EditableObject` 跟踪字段级变更。**人工插桩 body 时以该 SDK API 为准**。平台关系模型（RelationDefinition）含 source_name/target_name 正反向访问名与 1:1/1:N/N:1/N:N 四种基数——超出 yaml 模板表达力的部分（N:N、反向名）由平台 metadata-service 生成 SDK 时承载，DSL/yaml 侧维持桥表建模与单 name 约定。

**编译目标**：`engine-bundle/actions.json`——结构对齐 mfg 引擎 get_meta_actions 实测：`{actions: [{action_name, description, parameters, supports_sandbox, body: <body_ref 文件内容字符串>}], sandbox_execution: {parameter: "sandbox", accepts: ..., usage: ...}}`。

**平台关系的完整字段要求（SDK RelationDefinition 实证）**：code / source / target / cardinality（1:1、1:N、N:1、N:N 四种）/ source_name 与 target_name（正反向访问名）/ source_field 与 target_field——**全部非空**。yaml 模板的 link_types 需 code/source/target/name/cardinality/sourcePropertyCode/targetPropertyCode 非空（name 必填为 2026-10-14 导入平台实证踩坑）；正反向名与 N:N 由平台 metadata-service 在生成 SDK 时承载，DSL 侧维持单 name + 桥表建模。

**平台连线模型（2026-10-15 workspace 999 浏览器实测，决定性）**：平台"新建关系"表单只收 关系名称/源实体/目标实体/基数；保存后详情面板的关联属性区——**1 侧自动填充为目标实体主键且禁改（"主键自动填充"），N 侧选单外键字段（必填，未完善弹"请先完善必填项"告警）**。**平台连线 = 单字段对硬约束，不支持复合主键连线**——复合主键实体必须单列主键化（Palantir 路线：独立业务编码主键，平台先例 list_id）才能进平台；复合键的联合唯一性以普通属性 + description 语义承载。

**lint 新增（第 10-11 条）**：admission 规则的 upstream 引用的 action 必须在 actions 中声明；admission 的 `@param:` 引用必须对应 action parameters 的参数名。

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
| `links.<alias>`（简写或显式 fk） | `{<E>: {links: {<alias>: <Target>}}}`（无 links 的实体编译回填 `{}`）；studio-model 编译的 targetPropertyCode 取显式 fk 字段（简写取目标主键名） |
| `rules[derived].logic` | `{rules: [{rule_type: "derived_property", logic: "字段: 表达式", upstream, downstream: "Computed Property", name, description}]}` |
| `rules[trigger].logic` | `{rules: [{rule_type: "trigger", logic: {ALL: [...]}, upstream, downstream: <action>, name, description}]}` |
| `rules[admission].logic` | `{rules: [{rule_type: "admission", logic: {ALL: [...]}, upstream: [<action>], downstream: "Action 准入拦截: <action>", name, description}]}` |

**v0.4 新键的编译映射去向（DSL → 平台 yaml，studio-model/导入格式；缺省新键的旧 DSL 编译行为不变）**：

| DSL | 平台 yaml 目标 |
|---|---|
| `links.<alias>.cardinality` | `link_types[].cardinality`（缺省 n:1 由编译器回填；1:n 不进 DSL，由目标侧连线表达） |
| `rules[trigger].branches` | 触发规则 `cases` / `otherwise`（条件分支按序映射 if/else_if、兜底映射 else；`with` 映射 `run` 项的动作参数映射） |
| `actions[].steps` | `action_types[].steps`（data 步骤 → {type, entity, operation, assignments}；notification 步骤 → {type, channel, recipients, content}；平台侧参数由步骤推导，DSL parameters 不重复编译） |
| `actions[].function` | 函数契约标注（平台函数是代码包元数据、不随 yaml 往返——编译导入说明中标注，DSL 只声明契约） |
| `actions[].validation_rules` | `action_types[].validation_rules`（引用的 admission 规则编译为 `rule_types` 的 `ruleType: validation` 并挂载到该动作） |

**编译剥离清单**：DSL 自有字段（实体级 governance / provenance；属性级 uom / enum_values / source / **derived**；规则级 **source**；顶层 competency_questions / open_questions / conflicts / assumptions）引擎不存储，编译时必须剥离——编译产物只含引擎格式键。**v0.3.5 补登两项（xgimi 遍历实证：此前两处剥离无记载）**：①属性级 `derived` 在 engine 目标下实际被剥离（引擎侧无法区分自然属性与计算属性；studio-model 目标保留为 isDerived，见 §8），②规则级 `source` 全量剥离——**剥离后 description 成为引擎侧唯一语义载体，故 §2 约定 3/4（枚举双写、衍生重述）是强制项而非建议**。

**round-trip 校验口径**：DSL → 编译 → 引擎格式，与引擎实测快照做**深度逐键比对**；编译产物中出现任何引擎格式之外的键 = 失败。

## 7. lint 规则（v0.4 全集，确定性检查；第 16-19 条仅对新键存在时校验——旧 DSL 零新报错）

1. schema 合法：类型枚举、必填键、命名风格（实体 PascalCase、字段 snake_case）
2. 主键：每个实体至少 1 个 primary；主键字段类型建议 STRING
3. links 闭合：目标实体必须存在；别名在实体内唯一；**显式 fk 的字段必须在本实体 properties 声明且目标实体存在（v0.3）**
4. 表达式静态检查：derived 的目标字段**已声明于** upstream 实体 properties（v0.2 约定 1）；引用前缀是合法 links 别名或复数引用；函数名在白名单内（SUM/COALESCE/MAX）
5. trigger：field 路径可解析；operator 合法；in 必须配数组
6. derived 的 `downstream: "Computed Property"` 由编译器回填，DSL 不写
7. **衍生字段一致性（v0.2）**：所有 derived 目标字段在 properties 中有声明；`derived: true` 标记的字段必须有对应 derived 规则
8. **外键-links 一致性（v0.2）**：外键字段与 links 声明对应可解释；类型与目标主键兼容
9. **受控词表（v0.3 启用）**：实体名对照 seeds/glossary.md——与既有术语同义但异名时报 warning（提示复用/登记）；glossary 文件缺失时降级跳过并提示
10. admission 的 upstream action 存在性；`@param:` 引用与 action parameters 对应（v0.2.2）
11. admission 的 `{param: 名}` 引用与 action parameters 对应（v0.2.2）
12. **规则名全局唯一（v0.3）**：同名规则跨实体重复报 error（引擎合法但 studio-model code 需唯一，fnb 31 处重名实证）
13. **关系业务语义名（v0.3.4）**：links 未声明 name（简写形态或显式缺省）报 warning——只表达"有指向"未说清是什么关系，建议显式形态声明 name
13b. **关系业务定义（v0.3.7）**：显式形态 links 缺 description 报 warning——关系只有名字没有业务定义，平台侧关系描述为空串（用户实证）
14. **OQ/conflicts 结构（v0.3.6）**：OQ 逐条校验 id 格式（`OQ-NN` 大写，不符报 warning）/ id 域内唯一 / topic+question 非空 / status 在七态枚举内 / status 含 resolved 必带 resolution——违规报 error；conflicts 逐条校验 topic+side_a.claim+side_b.claim 非空、status 在 pending|resolved 内——违规报 error（实证：schema 漂移曾致同域两版 OQ 键名/状态机各说各话，机器无一拦截）
15. **枚举双写（v0.3.6）**：声明 enum_values 的字段 description 缺失报 error；enum code 未在 description 出现报 warning（孤儿枚举值——enum_values 编译剥离后 description 是唯一语义载体；实证：xgimi 复验版 29 个枚举字段中 2 个存在孤儿值）
16. **links 基数（v0.4）**：显式形态声明 `cardinality` 时取值必须 ∈ {n:1, 1:1}——其他取值报 error（1:n 由目标侧 links 表达、n:n 不进 DSL）；简写形态不查（缺省 n:1）
17. **trigger 分支（v0.4）**：同一 trigger 规则 `branches` 与 `logic`/`downstream` 并存报 error；branches 结构违规报 error——条件分支缺 condition/downstream、兜底分支非末项或超过一个、`with` 参数名不带 `$` 前缀或不在 downstream 动作 parameters、`with` 值形式非法（非常量且非 @Entity.attr 可解析形态）、condition 结构不合法（沿用第 5 条条件校验逻辑）
18. **声明式动作步骤（v0.4）**：`steps` 与 `recipe` 并存报 error、`steps` 与 `function` 并存报 error；steps 逐项——type 枚举（data/notification）、data 的 entity 存在且 operation 枚举（create/update）、assignments 字段在该实体 properties、值形态合法（常量 / `@param:$参数` 且参数存在 / `@Entity.attr` 且可解析）；notification 的 channel/recipients/content 非空且值形态合法。缺省豁免：无新键的旧 DSL 零新报错
19. **挂载校验（v0.4）**：`validation_rules` 引用的规则名不存在报 error；引用规则 `rule_type != admission` 报 error；引用规则的 upstream 与本动作名不一致报 error
20. **准入字段可解析（v0.4）**：admission 的 `check: instance` 条目 `field` 须可从该 `entity` 解析（属性或点路径），否则报 error——v0.4 起 admission 编进平台 validation，字段必被编译解析，lint 与编译器同判（评测夹具引用不存在字段的盲区实证）

## 8. studio-model 互导格式（v0.4，2026-11-26 对齐平台官方导入规范——`docs/reference/新品上市POC-最新版-*.zip` 内升级说明）

studio-model YAML 是**平台导入/导出的官方载体**（与引擎注册 JSON 并存）。现行格式四段（2026-10-20/10-23/11-02 三次格式变更后的形态，官方说明为准）：

```yaml
format: studio-model
object_types: [ {code, name, description, enabled, attrs: [{code, name, type, required, isKey, defaultValue, description, isDerived}]} ]
link_types:   [ {code, source, target, name, cardinality, description, sourcePropertyCode, targetPropertyCode} ]
rule_types:   [ {code, name, description, ruleType: calculation|trigger|validation, mode, ruleConfig, ...} ]
action_types: [ {code, name, description, enabled, validation_rules?, steps} ]
```

**类型映射**：STRING↔string、BOOLEAN↔boolean、DATE↔date、TIMESTAMP↔datetime、DOUBLE↔double、**INTEGER↔integer（精确保留，不再压 double）**、DECIMAL→double（逆向 double→DSL DOUBLE 并注记，不猜 INTEGER）。模板侧 string 存数值的字段（如 sled_days）是模板质量问题，lint 报 warning。

**编译约定（DSL → studio-model，v0.4 全面切新格式）**：
- 实体→object_type（code=实体名、name=display_name）；`derived: true` 或衍生规则目标字段 → attrs.isDerived=true。
- links→link_type：`{source: 目标实体, target: 本实体, sourcePropertyCode: 目标主键, targetPropertyCode: 外键字段}`；基数按翻转映射（DSL `cardinality` n:1（本实体:目标）→ 平台该方向 `1:n`、1:1→`1:1`，未声明缺省同 n:1）；关系 name 平台必填非空（显式形态声明，未声明时编译器兜底 = 目标实体 display_name）。
- **计算规则表达式（10-20 新格式）**：DSL 点路径 → `${别名.属性code}` 占位符 + `ruleConfig.expressionSources`（别名→{entityCode, relationPath}）；自身属性 `relationPath: []`；关系路径由编译器沿 links 图 BFS **自动推导**——最短路径唯一自动采用，多条等长报 error 指名不猜；同一 (实体, 路径) 共用一个别名；路径跳数不限（xgimi 实证 3 跳）。**旧中文名引用格式 `[实体名.属性名]` 已废弃（平台导入校验会拒绝缺关系路径的历史格式）**。
- **trigger → rule_types[trigger]**（10-23/11-02 新格式）：旧形态（logic+downstream）→ `mode: single` + `cases[0]`；branches → `mode: multi` + cases + 可选 `otherwise`（分支上限 10）；条件 `field` 路径 → `left: "@实体.属性"`、operator 映射（`==`→eq、`!=`→ne、`>`→gt、`>=`→gte、`<`→lt、`<=`→lte、`in`→in）；`downstream` → `run[].action`（稳定 code）；`with` 键保留 `$` 前缀、值=常量或 `@实体.属性`。
- **admission → rule_types[validation] + 挂载**：`check: param` → `left: "$参数"`、`check: instance` → `left: "@实体.属性"`（lookup 不编进 when——实例定位由动作运行时 instances 提供，导入说明注明）；`downstream` 文本 → `failureMessage`；规则 code 挂载到宿主动作 `action_types[].validation_rules`。
- **动作 → action_types**（10-23 简化报文）：声明式 steps 逐项映射（data：`{type, entity, operation, assignments}`，值=常量/`"$参数"`/`"@实体.属性"`；notification：`{type, channel, recipients, content}`）；**不写 parameters**（平台由步骤 `$参数` 推导）；函数型与 recipe 动作 `steps: []` 并在 import-README 列「需平台侧配置」名单；trigger 引用但未声明的动作（平台内置）同样列入 import-README（不静默）；trigger 与 action 每条带 `enabled: true`。
- code 生成（rel_/rule_/action_ 前缀）：稳定 hash（如 md5(关键要素)[:8]），保证重复编译幂等。

**逆向（studio-model → DSL，`export_dsl.py --platform-yaml`）**：结构直接映射 + 表达式占位符按 expressionSources 还原为点路径（正向段用 links 别名、反向段用持有方复数引用名）；cases→trigger（multi）/validation→admission（含挂载还原）；action_types→声明式动作（空步骤按函数型占位）。**有损处一律注记进 assumptions**（table_name/links 别名按 snake_case 惯例重造、lookup 平台不承载、parameters 从引用推导、CQ 空）。**往返保证**：编译→逆向→lint→再编译，产物 sha256 字节一致（case14 与 xgimi 双实证）。旧引擎快照入口（--objects/--rules）保留。lint 输入支持：对 studio-model 文件做结构检查（主键存在、连线属性可解析、悬空引用、孤立实体、表达式函数白名单、isDerived 与 calculation 输出一致性）。

## 9. 变更集（changeset）格式

增量建模（base_version 非 null）时，产出与目标快照的变更集：

```json
{
  "changeset_id": "<hash>",
  "base_version": "<基于的快照版本>",
  "generated_at": "<ISO8601>",
  "operations": [
    {"op": "add|remove|replace", "path": "/entities/<E>", "...": "add/replace 携带新值，remove 仅 path"},
    {"op": "add", "path": "/entities/<E>/properties/<f>"},
    {"op": "remove", "path": "/links/<alias>"},
    {"op": "replace", "path": "/rules/<name>/logic"}
  ],
  "breaking": [{"op_ref": <序号>, "reason": "<影响说明>"}],
  "summary": {"add": n1, "remove": n2, "replace": n3}
}
```

**breaking 判定（确定性规则）**：remove 实体/属性/links/规则、replace 属性 type、replace 主键集合、replace 规则 logic = **breaking**（影响下游查询/技能/看板，须人审重点关注）；add 类与 display_name/description 变更 = 非 breaking。变更集附 **diff 版拓扑**（新增绿 `style` 高亮 / 删除红 strikethrough / 修改黄）。

**版本冲突校验（行为测试样例四的基础）**：变更集携带 base_version；导入/评审时若目标快照当前版本 ≠ base_version → **拒绝并要求重读快照重新生成 diff**，禁止强推覆盖。
