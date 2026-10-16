# 建模规范（modeling-guide）

> 主技能第 3 步（起草）的命名与结构规范。规则来源：Palantir Foundry 官方设计原则（No-exceptions 硬规则，见 docs/research 调研报告 Q6）+ 目标引擎实测惯例。DSL 语法见 dsl-spec.md，本文件管"建得好不好"。

## 一、命名规范（lint 第 1 条的展开）

| 对象 | 规则 | 正例 | 反例 |
|---|---|---|---|
| 实体名 | PascalCase，映射业务自然概念 | `PurchaseOrder`、`SKUInWarehouse` | `PO`（缩写）、`PurchaseOrderV2`（版本化命名） |
| table_name | snake_case，对齐源系统表名；不假设与实体名有变换关系 | `purchase_order` | — |
| 字段名 | snake_case，业务可读 | `safety_stock` | `ss`、`stk_qty` |
| 主键 | **单列**业务编码（内在唯一，不依赖运行时生成）——**禁复合主键**（平台连线为单字段对硬约束，2026-10-15 实测；联合唯一性用普通属性+语义说明承载） | `sku_code`、`list_id` | 自增 id、uuid、复合主键（多字段 primary） |
| 外键字段 | 指向目标表主键，命名取目标主键名 | `supplier_code` | `sid` |
| 时间戳 | `{动作}_time` / `{动作}_date`，类型对齐（TIMESTAMP/DATE） | `create_time`、`sign_date` | `t1` |
| 布尔 | `*_flag` / `is_*`，含义在 description 写明真/假各是什么 | `frozen_flag` | — |
| 量纲 | 数值量纲写 uom（元/件/天/比率） | `contract_amount` + uom:元 | 裸数值 |
| 展示名 | 中文业务术语（与 brief/访谈用语一致） | `安全库存` | 直译英文 |

## 二、Palantir 硬规则（引擎化裁剪）

1. **主键内在唯一**：主键值仅依赖对象自身属性，禁止排序号/运行时 uuid 充当主键。
2. **治理必配**：每个本体有 owner + maturity（experimental/active/deprecated）；实体级可覆盖。
3. **最小属性**：可由父对象/关联对象推导的属性只声明一处；快照型冗余字段（如同时有 `sku_code` 与 `sku_name`）按源系统实际保留但在 description 标注来源。
4. **孤立实体是设计缺陷信号**：没有 links 的实体要么补充关系，要么在 open_questions 说明为何独立。
5. **避免蜘蛛网**：links 表达业务上有意义的导航路径，不为"可能有用"建关系。
6. **命名稳定**：名称变更不得通过删除重建完成（保持实体名稳定，改 display_name）。

## 三、建模边界（对象/规则/动作的区分）

| 语义 | 归属 | 信号 |
|---|---|---|
| 业务名词（有身份、被引用） | 实体 | "一张/一个/一条 XX"可数、有编码 |
| 计算口径 | derived_property | "XX = A − B"式定义 |
| 条件触发动作 | trigger | "当…则…" |
| 参数/实例校验 | admission（M3） | "不允许 XX 超过 YY" |
| 流程步骤 | **不建对象** | 除非有独立身份+状态+生命周期（如"对账单"有状态机→实体；"通知采购"→trigger 下游） |
| 预测/优化/排程 | 不进本体 |

**关系三态判别（2026-10-16 用户概念辨析后固化）**：
1. **简单关系 → links 连线**：只带语义名（A 连 B + "订购物料"式业务含义）——绝大多数场景。
2. **关系实体化（Reification）→ 桥实体**：关系**本身**有身份要承载数据时——分配量、归因数量、有效期/批次、优先级、独立版本或状态机（先例：AllocationRecord/CauseAttribution/SubstitutionPermission/mfg 的 ObjectiveInStrategy）。判别问题："这条关系除了'A连B'还有自己的属性或生命周期吗？"
3. **复合主键连线放不下 → 单列主键化（Palantir）**：与实体化无关——是实体定位问题（平台连线为单字段对硬约束）。**禁止**为绕开连线限制而建 Link 实体（过度设计）；单列主键 + 联合唯一语义说明即可。 属算法域；其输入输出挂到实体的字段即可 |

## 四、受控词表策略

- 优先复用 `seeds/` 中 fnb/mfg 既有术语（实体名、字段名、展示名三层）。
- 新术语（新域接入）首次入库时在本体文件头部 `glossary_additions` 注记，人审时统一裁定是否与既有术语对齐（如 mfg `Material` vs fnb `SKU` 的对应关系在跨域场景显式声明，不静默合并）。
- 同义词/口语说法记入字段 description 或实体的别名说明，不改字段名。

## 五、表达式方言要点（起草 derived 时）

优先采用 dsl-spec.md §3.1 方言 cookbook 的引擎惯例写法（除法兜底 `COALESCE(x/y, 9999)`、加权平均、空值兜底），不要自行发明 IF/CASE/ABS 等白名单外函数——方言没有的能力进 open_questions，由引擎侧裁决扩展。
