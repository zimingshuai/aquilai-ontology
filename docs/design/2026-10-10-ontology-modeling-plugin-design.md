# LLM 自动化本体建模插件技术方案（ontology-forge / Aquilair FDE Plug-in）

> 设计日期：2026-10-10 ｜ 状态：方案设计（待评审）
> 需求人：zishuai（开发侧）｜协同蓝图来源：楠总 × Codex 会话（2026-09-21，WorkBuddy 侧）
> 输入依据：本工作区 3 个历史会话 + 9-24 调研报告 + 2026-10-10 三路增量调研（输入/交互、产出/导入/评审、目标引擎格式规约）

## 一、结论（TL;DR）

1. **产品定位**：面向 FDE / 开发人员的 ZCode 插件（产品名 Aquilair FDE Plug-in，WorkBuddy 侧可平移），把新业务域接入本体引擎的时间从"数周手工建模"压缩到"半天人审"。核心流水线：**上传文档 → 自然语言交互圈定场景（Scenario Charter + 能力问题 CQ）→ 分层抽取候选（带 provenance）→ 起草本体 DSL（YAML）→ 硬校验 + CQ 回验 → Mermaid 拓扑 → 变更集 → 导入既有 MCP 本体引擎（preview → 确认 → apply → validate）→ 人工审核（Git PR + checklist）**。
2. **格式决策**：主产物为 **LinkML 风格 YAML DSL**（内部走 JSON 约束输出再确定性序列化，LLM 直出 YAML 可靠性差已被 JSONSchemaBench 类研究证实）；OWL/Turtle 仅作可选导出（gen-owl），服务需要 W3C 互操作的场合。DSL 必须覆盖目标引擎五元素：**实体 / 属性 / links / 三类规则（derived·trigger·admission）/ 动作**。
3. **导入目标已精确摸清**：团队既有 fnb（15 实体，只读）与 mfg（10 实体 + 8 action + 沙箱）两个 stdio MCP 本体引擎共用同一套元数据 schema（详见 §7.1）。**当前两者均无 schema 写接口**——导入环节分两期落地：一期"生成引擎注册格式文件 + 人工导入"，二期由平台侧补齐**变更集级写接口**（契约直接采用楠总方案：preview→apply→validate，apply 只认 change_set_id + content_hash）。
4. **与楠总 Codex 蓝图的关系**：本方案 = 楠总 WorkBuddy 侧 FDE Plug-in 蓝图（agent 提示词 + 5 skills + Studio MCP 变更集契约 + 6 类测试样例）在 ZCode 侧的工程落地与细化，两者共享 OntologyProposal 数据契约与权威边界原则（AI 只产草稿，人工审核是唯一入口）。
5. **最高风险已前置**：①LLM 生成质量（M0 POC 验证）；②动作 body 是 Python 源码、无法声明式生成（DSL 只生成元数据 + 骨架，人工插桩）；③schema 写接口依赖平台侧排期（一期用文件导入绕行，不阻塞插件开发）。

## 二、需求画像与历史证据链

### 2.1 用户原始需求（2026-10-10 本会话）

> 开发一个基于 LLM 的自动化本体建模 agent 或插件。FDE 或开发人员**上传文档**（结构待设计）→ 通过自然语言与 coding agent 交互 → 产出**本体元数据设计的拓扑**和 **YAML 或 OWL** → 导入团队**既有本体 stdio（MCP）服务** → 后续**人工审核**。

### 2.2 三个会话的证据链与需求演进

| 会话 | 时间 | 关键产出 | 对本方案的贡献 |
|---|---|---|---|
| ① 插件开发咨询（ZCode） | 09-24 | 调研报告（LinkML/CQ/Palantir 三件套/lint 硬规则/插件结构）+ ontology-forge 蓝图 | 方法论与选型依据：YAML 为源、七步流水线、Palantir No-exceptions 规则落 lint |
| ② 楠总 × Codex（macOS） | 09-21~24 | Aquilair FDE Plug-in 完整蓝图（WorkBuddy Expert 形态） | 产品契约：OntologyProposal 格式、变更集级 Studio MCP 工具契约、权威边界、5 skills、6 类测试样例、四阶段开发路径 |
| ③ 本会话（ZCode） | 10-10 | 需求明确化 + 三路增量调研 | **需求演进：从"从零设计、不复用引擎"→"导入既有 MCP 引擎"**；目标引擎格式规约实测；输入文档/可视化/导入/人审的业界验证 |

**贯穿三个会话的共识（不可违背的设计原则）**：
- AI 生成的草案 ≠ 已批准的生产模型；**人工审核是唯一权威入口**。
- LLM 只做"生成候选 + 按意见修订"；**机器可判定的校验全部交给确定性工具**（lint/校验器/引擎 dry-run）。
- 写入必须走 **preview → 确认 → apply** 两阶段，apply 只认预览返回的 change_set_id，杜绝"预览与写入不一致"。
- 建模顺序**决策驱动**：先明确业务要做什么决策（CQ），再反推最小本体。
- 不把候选设计写成事实、不脑补补齐、缺失信息显式列为待确认问题（provenance + open_questions）。

### 2.3 本质定位：本体元数据设计专家，而非学术本体工程（2026-10-13 用户确认）

**澄清**：本插件与传统本体建模（语义网/知识表示）有本质差异。我们做的是**面向自家本体引擎的元数据设计**——一个懂引擎规范的"本体元数据设计专家 agent"（即楠总蓝图 `profession: "Aquilair 本体实施专家"` 的定位），产出物是可注册的元数据资产，不是可推理的知识表示。

本体元数据的三层内涵（注意"元数据"不只是字段注释，含行为契约）：

| 层 | 内容 | 传统对应物 |
|---|---|---|
| 数据模型层 | 实体、属性、主键、links | 传统数据建模（ER 模型） |
| 语义标注层 | display_name、description、口径、术语同义词 | 数据字典/术语表（让 LLM 可理解） |
| 行为契约层 | derived 口径、trigger、admission、action 定义 | 业务规则引擎的规则声明 |

**对方案的三处校准**：
1. **OWL 从"可选导出"降级为"按需附件"**：无外部互操作需求则砍掉 gen-owl 线——产物收敛为 DSL YAML + 引擎注册格式 + Mermaid 拓扑。
2. **不引入推理机**：HermiT/Pellet（一致性/分类推理）在本方案无位置——校验空间是确定性的（命名/类型枚举/关系闭合/口径语法/CQ 覆盖），全部由 lint 脚本承担。
3. **术语校准**：借鉴的本体工程概念（CQ、复用优先、OD101 步骤）定性为**方法论借鉴而非本体论承诺**；文档与交互语言不暗示"在建 OWL 本体"。

**不变**：CQ 驱动、复用优先、受控词表治理、人工审核唯一权威——问题本质仍是"把业务语义显式化、机器可读"。

## 三、总体架构

### 3.1 端到端流水线（十步）

```text
①输入摄入        brief-intake 摄取技能：上传任意文档 → 自动分类归位(A/B/C/D)
                → 生成 brief.yaml + 缺口报告 → 补齐后按输入类型路由解析管线，
                统一产出「业务事实卡片」
②场景圈定        自然语言交互 → Scenario Charter（业务目标/触发事件/决策对象/KPI/
                参与角色/审批边界）+ 5~10 条能力问题 CQ —— 未完成不进入下一步
③术语与候选抽取   实体/属性/关系/规则候选，每条带 provenance（来源文档+位置）、
                置信度、状态标签（已确认/候选/冲突/待确认）
④本体起草        内部 JSON（约束输出）→ 确定性序列化为 YAML DSL 草稿
⑤拓扑可视化      Mermaid classDiagram（实体/属性/关系/基数）+ Action/规则 note
⑥硬校验          lint 三层：DSL schema 合法性 → 建模规范（Palantir 硬规则+受控词表）
                → 目标引擎格式兼容性（data_type 枚举/主键/links 别名/表达式语法）
⑦CQ 回验         逐条核对能力问题是否被 DSL 元素覆盖，judge 评估报告
⑧变更集生成      与目标引擎当前快照 diff → JSON Patch 风格 changeset
                （add/remove/replace + breaking 标记 + diff 版 Mermaid）
⑨导入            一期：导出引擎注册格式文件+人工导入；二期：MCP preview→确认卡→apply→validate
⑩人工审核        Git PR 式评审（YAML diff + 拓扑图 + checklist）→ 合并 → 固化为 eval 回归用例
```

### 3.2 组件分工（LLM / 确定性工具 / 人）

| 环节 | LLM（生成与语义判断） | 确定性工具（对错可机器判定） | 人 |
|---|---|---|---|
| 摄入/抽取 | 术语/实体/关系/规则候选、provenance 标注 | 文档解析、字段类型推断规则 | 补充口径、裁决冲突 |
| 起草 | DSL 草稿、命名建议 | JSON→YAML 序列化、schema 校验 | 关键边界确认 |
| 校验 | lint/评审意见→修订建议 | lint 三层、CQ 覆盖矩阵生成 | — |
| 导入 | — | diff、changeset、breaking 检测 | **确认卡拍板** |
| 审核 | 评审报告草稿（checklist 逐项） | diff 渲染、拓扑图生成 | **终审唯一权威** |

## 四、输入文档结构设计（"建模资料包"模板）

业界无统一"本体建模输入模板"（调研确认，这本身是产品差异点），按输入形态分四类。**资料包不要求用户手动组织**——`brief-intake` 摄取技能（2026-10-13 用户确认的产品入口）负责自动分类归位：FDE/开发/业务人员随手上传任意文档（可多次追加），技能分类归位到下列结构并生成 brief.yaml 与缺口报告：

**brief-intake 技能设计（建模任务的统一入口）**
1. 逐份扫描判型：schema（DDL/数据字典/字段表 Excel）｜场景（决策/规则/流程/制度）｜访谈（记录/口述/会议纪要）｜参考（行业模板/竞品/既有本体导出）
2. 归位 A/B/C/D 目录 + 摄取日志记录原始文件名（provenance 起点）
3. 生成交互确认 brief.yaml（场景名/owner/目标引擎/来源系统从文档推断，用户确认）
4. 每份文档生成源摘要页（一句话定位 + 关键内容清单），作为后续 provenance 锚点与解析路由依据
5. **缺口报告**：对照理想资料包检查（有无 DDL？有无决策清单？），明确"缺什么、建议找谁要什么"
6. 术语冲突预检：跨文档口径冲突提前写入 brief.yaml 的 known_conflicts

与知识库的边界（§4.3）：intake 是**任务级**资料包整理（一次建模一份），aquilair-knowledge 是**域级**知识沉淀（持续积累）；资料量大或跨任务复用时，intake 支持从知识库 raw/ 层选材。

规范目录结构（intake 的归位目标，对用户透明）：

```text
modeling-brief/
├── brief.yaml              # 资料包清单：场景名、业务负责人、目标引擎（fnb/mfg/新）、
│                           #   系统来源清单、已知术语冲突声明
├── A_schema/               # A 类：结构化 schema（优先级最高，映射确定性最强）
│   ├── ddl.sql             #   DDL 导出（表/主键/外键/注释）
│   └── data_dictionary.xlsx #  数据字典（ISO 11179 风格，见下）
├── B_scenarios/            # B 类：业务场景与规则文档
│   ├── decisions.md        #   决策清单：谁、依据什么信息、做什么决策、KPI
│   ├── rules.md            #   业务规则/口径定义（如"可用库存"的算法）
│   └── processes.md        #   流程/制度文档（事件、状态流转、审批链）
├── C_interviews/           # C 类：访谈记录/口述（自由文本，两段式抽取）
│   └── *.md|*.txt
└── D_reference/            # D 类：参考材料（竞品功能表、行业模板、既有本体导出）
    └── existing_ontology.json  # 如做增量建模，从目标引擎导出的当前快照
```

**A 类数据字典字段规范**（每字段一行，ISO 11179 简化版；这是语义还原质量的上限）：

| 列 | 必填 | 说明 |
|---|---|---|
| table_name / field_name | ✅ | 物理表名/字段名 |
| business_term | ✅ | 业务术语（中文名） |
| definition | ✅ | 业务定义/口径（一句话讲清"是什么、怎么算"） |
| data_type / uom | ✅/– | 类型；量纲/单位（kg、元、天） |
| enum_values | – | 枚举值与含义 |
| pk / fk_target | – | 主键标记 / 外键指向 |
| source_system | – | 来源系统（ERP/WMS/MES） |
| owner | – | 字段责任人 |

**各输入管线的处理策略**（调研依据：RIGOR 2025 按 schema 增量生成 + 独立 judge；OntoEKG 非结构化文本两阶段）：
- **A 类**：表→实体、列→属性、外键→link 候选（外键语义命名是公认难点 → 受控词表 + 人审）
- **B 类**：决策清单直接映射 CQ 与 Scenario Charter；规则文档 → derived/trigger/admission 候选
- **C 类**：先抽术语/实体候选（第一阶段），再建关系（第二阶段），禁止一步直出本体
- **D 类**：既有本体快照 → 增量 diff 模式（复用优先，不重复建已有实体）

### 4.3 输入来源分级与知识库层的关系（2026-10-13 补充决策）

**问题**：输入是文档，是否需要引入文档知识库层（如 Karpathy llm-wiki 式工具）来管理文档知识？

**决策**：**不引入外部 llm-wiki 项目；与团队既有 `aquilair-knowledge` 知识库技能衔接，但定位为"可选输入源 + 下游沉淀层"，不做建模必经的前置层。**

理由与边界：

1. **团队已有同构资产**：`aquilair-knowledge-wiki` 技能（一次摄取、持久编译：raw 原始层 + glossary/index/log/analyses 编译层、溯源问答、再摄取迭代）与 llm-wiki 理念同构，且已在技能工厂体系内（mfg 域样板已编译）。引入第二套知识库系统 = 双系统维护 + 边界混乱，无能力增量。
2. **标准路径不需要前置知识库**：建模资料包是任务级结构化输入（体量可控，直接进上下文），provenance 直接引用资料包文件路径。仅当 FDE 面对散落企业文档（wiki/Confluence/手册群）时，先走知识库摄取编译，再从 glossary/index **生成** modeling-brief（"知识库 → 资料包"桥，M3 交付）——知识库是原料粗加工车间，不在建模主链路上。
3. **沉淀方向（探索复利）**：建模人审合并后，将口径定义、术语表、CQ、冲突裁决回流知识库 glossary/analyses，供业务问答溯源与增量建模复用（对齐 OntoMind DataOps "Wiki 沉淀" 的方向：wiki 是产物，不是前置）。
4. **红线**（楠总蓝图原文）：**不得将知识库、文档目录或 Agent 记忆等同于业务本体**——本体 DSL 是唯一 source of truth，知识库只做原料组织与成果沉淀；增量建模时引擎快照（get_meta_objects 实测）永远优先于知识库编译页。

## 五、DSL 设计（YAML 规范）

### 5.1 设计原则

- **YAML 为源、OWL 为导出**（LinkML 官方立场：单向无损；YAML 行级 diff 干净、git 友好、FDE 可读）。
- 内部表示用 **JSON + schema 约束输出**，序列化为 YAML 由确定性代码完成——LLM 永远不直接书写自由 YAML。
- 元模型 = **目标引擎五元素 + Palantir 治理字段**，用 LinkML 的 classes/slots/annotations 承载，不发明新语言（会话①决策）。
- 编译目标双份：①团队引擎注册格式（JSON，精确对齐 §7.1 规约）；②LinkML 工具链产物（JSON Schema/OWL/SHACL/文档/ER 图，白嫖生态）。

### 5.2 DSL 示例（以 FNB 库存域"SKU 在库状态"为例，含五元素）

```yaml
# model.yaml —— 本体 DSL 源文件（source of truth，进 git）
ontology: fnb_inventory
version: 0.2.0-draft.1
base_version: 0.1.0            # 增量建模时基于的引擎快照版本
governance:
  owner: zhang.fde             # Palantir 规则：每个对象必配负责人
  maturity: experimental       # experimental | active | deprecated

entities:
  SKUInWarehouse:              # 实体名 PascalCase（对齐引擎惯例）
    display_name: SKU在库状态
    table_name: sku_in_warehouse     # snake_case（注意：不假设与实体名有变换关系）
    description: 表达特定 SKU 在具体仓库中的进销存属性及流转量化指标
    governance: { owner: zhang.fde, maturity: experimental }
    properties:
      sku_in_wh_code: { display_name: SKU-仓库编码, type: STRING, primary: true }
      onhand_inventory_qty: { display_name: 实时库存数量, type: DOUBLE, uom: 件 }
      safety_stock: { display_name: 安全库存, type: DOUBLE, source: A.data_dictionary#L42 }
    links:                     # 键 = 引用别名 = 规则表达式引用前缀（引擎语义）
      sku: SKU
      warehouse: Warehouse
      # 反向集合：复数表名（purchase_orders、sku_in_whs），DSL 显式声明不靠推断
    provenance: { doc: modeling-brief/A_schema/ddl.sql, reviewed: true }

rules:
  - rule_type: derived_property
    name: 库存周转天数
    upstream: [SKUInWarehouse]
    logic: "inventory_turnover_days: COALESCE(average_inventory_qty / average_daily_outbound_qty, 9999)"
    # 表达式语法 = 目标引擎方言：四则 + 点路径跨实体 + SUM/COALESCE/MAX
  - rule_type: trigger
    name: 高周转告警
    upstream: [SKUInWarehouse]
    logic:
      ALL:
        - { field: sku.abc_type, operator: in, value: [A, B, C] }
        - { field: inventory_turnover_days, operator: "<=", value: 10 }
    downstream: update_inventory_level
  - rule_type: admission       # 仅含 action 的本体需要
    name: 调拨量不超可用库存
    upstream: [execute_transfer]
    logic:
      ALL:
        - check: instance
          entity: MaterialInPlant
          lookup: { plant_id: "@param:source_plant", material_id: "@param:material" }
          field: available_qty
          operator: ">="
          value: { param: total_qty }

actions:                       # DSL 只声明元数据；body 生成骨架后人工插桩（§5.3）
  - name: execute_transfer
    description: 执行确认后的调拨
    parameters: { transfer_id: str, total_qty: float }
    supports_sandbox: true
    body_ref: ./actions/execute_transfer.py.tmpl   # 代码模板，含 OntologyEdits 返回骨架

competency_questions:          # CQ：需求规格 + 验收用例 + 回归测试，一物三用
  - id: cq-001
    q: 哪些 SKU 在哪些仓库的库存低于安全线？
    covered_by: [SKUInWarehouse.safety_stock, SKUInWarehouse.onhand_inventory_qty]
  - id: cq-002
    q: 某仓库当前未到货的调拨量有多少？
    covered_by: [SKUInWarehouse.undelivery_replenishment_qty]

open_questions:                # 禁止脑补：缺失信息显式列出，人审前必须清零或标记接受
  - { q: "「可用库存」是否扣除在途调拨？", status: pending, refs: [B_scenarios/rules.md] }

conflicts: []                  # 跨部门口径冲突（保留双方定义 + 来源，交人裁决）
assumptions: []                # 生成时的假设清单
```

### 5.3 动作（actions）的诚实处理

目标引擎的 action body 是**可执行 Python 源码**（@action 装饰器 + 类型注解 + 返回 OntologyEdits），无法从声明式 DSL 生成。策略：
1. DSL 声明动作元数据（name/参数/沙箱支持/admission 规则）；
2. 编译器按模板生成 **body 骨架**（docstring、参数、OntologyEdits 空结构）；
3. 业务逻辑人工实现（FDE/开发），插件做骨架→成品的**结构与准入校验**；
4. 一期建议：**新本体先不含 action**（对齐 fnb 形态：derived + trigger 已覆盖大部分语义），action 二期再开。

## 六、拓扑可视化

| 场景 | 方案 | 依据 |
|---|---|---|
| 终端 / Markdown（主战场） | **Mermaid classDiagram**：实体=class（属性带类型+主键标记）、link=带基数箭头、Action/derived=stereotype+note | Mermaid 原生支持 8 种 UML 关系与基数；LinkML `gen-erdiagram` 可直接产出 Mermaid ER 图（不自研图生成） |
| 变更集评审 | **diff 版 Mermaid**：新增绿色（`style` 高亮）/ 删除红删除线 / 修改黄 | 让评审人 10 秒看懂改动面 |
| Web 交互视图（可选导出） | 单文件 HTML：DSL→OWL→OWL2VOWL→WebVOWL 内联嵌入 | 纯静态无依赖，2025 年社区维护中 |
| 引擎快照反向可视化 | 拉取 get_meta_objects → 同一套渲染器 | 支持增量建模时的"当前拓扑 vs 提案拓扑"并排 |

能力边界（如实）：Mermaid 无法表达属性值约束/公理——此类信息放 YAML + CQ 矩阵，不在图上硬塞。

## 七、导入既有本体引擎

### 7.1 目标引擎格式规约（实测，两引擎同 schema）

| 元素 | 结构（关键键名，精确） |
|---|---|
| 实体 | `{display_name, table_name, description, properties{字段:{display_name,description,data_type,is_primary}}, links{别名:目标实体}}` |
| data_type 枚举 | `STRING / INTEGER / DOUBLE / DECIMAL / BOOLEAN / DATE / TIMESTAMP`（仅 7 种） |
| 主键 | `is_primary: true`，支持复合主键（多字段同 true） |
| links 键 | 引用别名（= 表达式引用前缀），默认目标表名 snake_case，可短别名（`wh`、`problem`）；反向集合用复数表名（`purchase_orders`、`sku_in_whs`） |
| 规则 | `derived_property`（`"目标字段: 表达式"`）｜`trigger`（`{ALL:[{field,operator,value}]}`→downstream action）｜`admission`（param/instance 检查，支持 `@param:` 注入与嵌套查找） |
| 动作 | `{action_name, description, parameters{名:"str"|"float"}, supports_sandbox, body: Python 源码}` |
| 引擎差异 | fnb：15 实体、只读、无 action；mfg：10 实体、8 action+沙箱、table_name 为 PascalCase、多 admission 规则 |

### 7.2 两期导入策略（关键 gap 处理）

**现实**：两个引擎当前均无 schema 写接口（get_meta_actions 只有业务动作）。楠总蓝图中的"Studio MCP"是规划契约。

- **一期（插件侧自闭环）**：编译器产出**引擎注册格式文件**（实体/规则 JSON + action Python 骨架，键名精确对齐 §7.1）+ 导入说明；由平台侧现有初始化流程注册（人审通过后执行）。插件提供 `export_engine_bundle` 产物 + **round-trip 校验**（导出→注册→get_meta_objects 比对一致）。
- **二期（平台侧补接口后切换）**：变更集级 MCP 工具，契约直接采用楠总方案（已评审过的设计，不重造）：

```text
get_project_context → get_ontology_snapshot → preview_ontology_changeset
→ 用户确认（确认卡） → apply_ontology_changeset → validate_ontology_draft
→ get_ontology_snapshot（回读校验） → submit_ontology_review
```

安全设计（楠总方案原文要求）：`preview` 返回 `change_set_id + content_hash`；`apply` **只接受** `change_set_id + content_hash + base_version`（不再接受模型临时生成的内容，杜绝预览≠写入）；版本冲突时拒绝并要求重读重生成；不暴露 publish/approve/hard_delete/execute_production_action。

变更集格式：**JSON Patch（RFC 6902）风格** + breaking 标记（先例：oasdiff 内置 755 条 breaking 规则、Atlas/Prisma 的 diff→plan→apply 模式）。

## 八、人工审核工作流

1. **产物进 git**：`models/<domain>/{model.yaml, competency-questions.yaml, topology.md, changesets/}` —— YAML 行级 diff 即变更说明，天然获得 PR 评审（先例：OBO Foundry/ODK、EDM Council ontology-publisher、Palantir IaC-for-Ontology）。
2. **评审视图**（PR 描述模板自动生成）：diff 版 Mermaid 拓扑 + CQ 覆盖矩阵 + lint 报告 + open_questions 清单（未清零不许合）。
3. **评审 checklist**（OQuaRE 质量模型 + Palantir 硬规则裁剪为 8~12 项）：命名符合受控词表、无缩写命名、主键内在唯一、外键 `{object}_id` 命名、无孤儿实体、关系有方向/基数/业务含义、derived 口径有来源、CQ 全覆盖、无"流程步骤建成对象"、动作不越权。
4. **确认卡**（导入执行前）：列出变更摘要 + breaking 项 + 影响面（哪些衍生属性/动作/技能受影响），用户明确同意才 apply——MCP 官方人审模式（工具执行前用户同意）+ 团队沙箱确认卡惯例。
5. **越权红线**（楠总方案原文）：可以生成/更新草稿；**拒绝**跳过评审直接发布生产、拒绝硬删除、拒绝生产回写。

## 九、插件目录结构（ZCode 版）

```text
ontology-forge/
├── .zcode-plugin/plugin.json          # ZCode 清单（WorkBuddy 侧平移为 .codebuddy-plugin）
├── .mcp.json                          # 挂载：目标本体引擎（fnb/mfg，stdio）+ 本插件工具服务
├── skills/
│   ├── brief-intake/                # 摄取技能：上传文档自动分类归位 + brief.yaml
│   │   └── references/intake-rules.md  #   + 缺口报告（建模统一入口，§4）
│   ├── ontology-modeling/             # 主技能：十步流水线编排（§3.1）
│   │   ├── SKILL.md
│   │   └── references/
│   │       ├── modeling-guide.md      # 建模规范（Palantir 硬规则 + 受控词表 + 引擎方言）
│   │       ├── dsl-schema.md          # DSL 规范（§5）+ JSON Schema
│   │       ├── input-templates.md     # 建模资料包模板（§4）
│   │       └── cq-guide.md            # CQ 写法与分类
│   ├── scenario-discovery/            # 场景圈定 → Scenario Charter（楠总契约）
│   ├── ontology-review/               # 评审技能：checklist 终审报告
│   └── ontology-import/               # 变更集生成 + 引擎导入（一期文件/二期MCP）
├── commands/onto.md                   # /onto <业务域描述> 斜杠命令入口
├── scripts/                           # 确定性工具链（全部非 LLM）
│   ├── parse_inputs.py                # A/B/C/D 类输入解析 → 业务事实卡片(JSON)
│   ├── lint_model.py                  # 三层 lint（schema/规范/引擎兼容）
│   ├── compile_model.py               # DSL → 引擎注册格式 + LinkML 多目标
│   ├── render_topology.py             # DSL/引擎快照 → Mermaid（含 diff 版）
│   ├── diff_model.py                  # 快照 diff → changeset + breaking 标记
│   └── check_cq.py                    # CQ → DSL 元素覆盖矩阵
├── models/                            # 产出物（source of truth，进 git）
│   └── <domain>/{model.yaml, competency-questions.yaml, topology.md}
├── seeds/                             # 种子本体：GS1(GTIN/GLN/SSCC)对齐字段 + SCOR 流程实体
│                                      #   + fnb/mfg 既有实体速查（复用优先）
└── evals/ontology-modeling/           # 回归用例（§十一）
```

WorkBuddy 平移映射：skills 同构；`agents/aquilair-fde.md`（总控提示词，楠总方案已有全文）↔ ZCode 的 skills+commands 组合；`.mcp.json` 中 Studio MCP 从 streamableHttp 换 stdio 既有引擎。

## 十、技能与提示词要点（主技能 SKILL.md 核心约束）

1. **权威边界**（继承楠总原文）：不得绕过审核直接写生产；不得把候选写成事实；不得脑补补齐——缺失即列 open_questions；已批准本体优先于历史文档。
2. **建模边界**：区分 Object/Property/Link/Event/Rule/Action；流程步骤不建对象（除非有独立身份+状态+生命周期）；预测/优化归算法域不进本体；关系必带方向/基数/业务含义/来源。
3. **交互节奏**：Scenario Charter 未确认不建模；实体清单先确认再展开属性；每类元素（实体/属性/关系/规则）**分步确认**，不一次吐全量（HITL 学术共识：分步确认优于批量审）。
4. **工具纪律**：凡 lint 不过不进下一步；写入前必须先读快照；preview 不可跳过；工具失败不得重复创建规避。
5. **产出纪律**：每次任务输出八件套（场景与范围/提案摘要/对象关系列表/冲突与待确认/变更预览/校验结果/草稿版本或未写入原因/下一步评审责任人）——楠总方案原文。

## 十一、测试体系

**六类行为测试样例**（楠总方案原文，每例含 user-request / source-materials / existing-ontology / expected-scenario-charter / expected-ontology-proposal / expected-tool-sequence / expected-diff / expected-review）：

| # | 样例 | 核心断言 |
|---|---|---|
| 1 | 从零生成（餐饮库存访谈+WMS字典+空引擎） | 先 Charter 再本体；preview→确认→草稿 0.1.0-draft.1；不发布 |
| 2 | 增量修改（新场景接入已有本体） | 复用既有实体，只新增差异；不重复建模 |
| 3 | 业务定义冲突（两个部门"可用库存"口径不一） | 保留双定义+标记冲突+待确认；不擅自定稿 |
| 4 | 版本冲突（preview 基于 v3，引擎已到 v4） | apply 被拒；重读重生成；不覆盖 |
| 5 | 越权请求（"不用评审直接发布"） | 拒绝发布；引导评审流程 |
| 6 | 错误建模（把流程步骤建成对象） | 识别为流程/规则/Action；不建伪对象 |

**回归体系**：每次真实建模沉淀为 eval 用例（输入资料包 → DSL 断言），防 skill 改动导致建模能力退化（复用团队 promptfoo 惯例）。

## 十二、风险与信息缺口

| # | 风险/缺口 | 等级 | 缓解 |
|---|---|---|---|
| 1 | LLM 生成 DSL 质量未实测（全方案最关键假设） | 高 | M0 POC：手写小域 gold standard 对照生成（会话①既定） |
| 2 | 引擎无 schema 写接口（平台侧排期不可控） | 高 | 一期文件导入+round-trip 校验自闭环；契约已定，接口就绪即切换 |
| 3 | action body 无法声明式生成 | 中 | 一期不含 action；二期骨架模板+人工插桩+结构校验 |
| 4 | 中文业务资料抽取质量未验证 | 中 | POC 用真实中文资料包；必要时按 A/B/C/D 分管线调 prompt |
| 5 | 受控词表冷启动（多域命名漂移） | 中 | seeds/ 预置 fnb+mfg 既有术语；lint 强制；新词入库走评审 |
| 6 | LinkML 官方文档超时未直核（生成器清单三源交叉） | 低 | POC 时逐一验证 |
| 7 | Web 调研若干来源未核实（Palantir 最佳实践正文、JSONSchemaBench 编号等，见调研报告标注） | 低 | 不影响架构决策，实施时按需补核 |

## 十三、分期计划

- **M0（1~2 天）POC** ✅ **已完成并通过（2026-10-13，报告：poc/m0/REPORT.md）**：三假设全部验证——①fnb 全量（15 实体/157 属性/60 规则）round-trip 差异为零（字节级复验）；②合成域盲测结构零漂移且两处比人工 gold 更正确；③编译器纯结构驱动可行。产出 DSL v0.2 修订清单 6 条（方言 cookbook/多跳聚合语法等），M1 前执行；gold 修订后作回归基线。
- **M1（1~2 周）最小闭环**：插件骨架（plugin-creator 六步）+ **brief-intake 摄取技能**（上传文档自动分类归位 + brief.yaml 生成 + 缺口报告）+ 主技能前六步（摄入→Charter→抽取→起草→lint→可视化）+ 一期文件导入 + git 产物。一个真实新业务域端到端跑通。
- **M2（2~3 周）质量与导入**：CQ 回验 + diff/changeset + 评审 checklist + 六类行为测试前四类 + evals 回归。
- **M3** ✅ **已完成（2026-10-13，除变更集 MCP 接入外全部交付）**：action/admission 生成——dsl-spec §4 v0.2.2 定稿（三种 recipe 配方，mfg 8 个真实 action 实测归纳）+ `gen_action_skeleton.py`（骨架 py_compile 可过、TODO 插桩标记）+ compile actions 编译目标 + lint 第 10-11 条；行为测试五六样例（case5 越权×4 话术 / case6 错误建模陷阱资料包）；WorkBuddy 侧平移（`workbuddy/aquilair-fde/`：quickPrompts×3 + 总控提示词五章节含楠总蓝图红线原文 + 三技能镜像）；aquilair-knowledge 衔接（选材入口 + 沉淀回流第 8 步）。**遗留**：变更集 MCP 接入（依赖平台侧接口排期，契约已在 §7.2 冻结）；lint_model.py 329 行超 code-style 上限 29 行（架构取舍：lint 规则集中单文件，已记录在案）。

## 十四、来源清单（增量调研，2026-10-10）

| # | 来源 | 类型/日期 |
|---|---|---|
| 1 | ISO/IEC 11179 数据字典标准（en.wikipedia.org/wiki/ISO/IEC_11179；iso.org/standard/50340.html） | 国际标准，Part1 2023 更新 |
| 2 | RIGOR: RAG 从关系 schema 生成本体（arxiv.org/abs/2506.01232） | 论文 2025-06 |
| 3 | OntoEKG 非结构化企业文本本体构建（github.com/LiberAI/OntoEKG） | 开源 2026-02 |
| 4 | Keet CQ 五分类（ceur-ws.org/Vol-4176）；cq4oe-benchmark（github.com/oeg-upm） | 论文 2025 / 基准 |
| 5 | van Cauter 等 HITL 预标注（aclanthology.org 2024）；Tsaneva 2025（ScienceDirect） | 论文 |
| 6 | GS1 Web Vocabulary（gs1.org/voc）；SCOR Digital Standard（ASCM）；SCORVoc | 行业标准 |
| 7 | Meckler 2024 工业 KG 程序模型（arxiv.org/abs/2409.13425） | 论文 |
| 8 | LinkML（pypi 1.11.1，2026-05-20；linkml.io generators/FAQ/erdiagram；PMC12993438 2025 框架论文） | 官方/论文 |
| 9 | ESWC 2025 LLM 生成 OWL 评估（arxiv.org/abs/2503.05388） | 论文 2025-03 |
| 10 | Mermaid classDiagram 文档（mermaid.js.org，2026 现行） | 官方 |
| 11 | WebVOWL（github.com/VisualDataWeb/WebVOWL）；"Making WebVOWL Great Again"（vbn.aau.dk 2025） | 开源 |
| 12 | MCP 官方：server-concepts（人审）、Elicitation spec（2026-07）、Client Best Practices；glama.ai / workos.com / itential.com 解读 | 官方+社区 2025-2026 |
| 13 | RFC 6902 JSON Patch；oasdiff（github.com/oasdiff/oasdiff，755 breaking 规则）；Atlas（atlasgo.io）；Prisma | 标准/开源 |
| 14 | WebProtégé（Tudorache 2013 PMC；Horridge 2019 ACM；protege.stanford.edu） | 论文/官方 |
| 15 | OBO Foundry/ODK、EDM Council ontology-publisher（github.com/edmcouncil/ontology-publisher）、Palantir "Implementing IaC for Ontology"（2024-08）、OLIVAW（arXiv 2025-10） | 开源/实践 |
| 16 | OQuaRE（Duque-Ramos 2014 PMC）；metaphactory 治理指南（blog.metaphacts.com 2024-10） | 论文/实践 |
| 17 | timbr Data Agents（docs.timbr.ai）；Stardog Voicebox（stardog.com 2023-04）；PuppyGraph Palantir 综述（2026-05） | 商业 |
| 18 | 楠总 × Codex 会话（桌面 rollout JSONL，2026-09-21~24）：FDE Plug-in 蓝图全文 | 内部一手 |
| 19 | 本工作区会话①（2026-09-24 调研报告及方案讨论） | 内部一手 |
| 20 | 目标引擎格式实测：fnb get_meta_objects（15 实体）；mfg get_meta_objects/actions/rules（10 实体/8 action） | 内部实测 2026-10-10 |

## 附：待用户拍板的决策

1. **试点域**：选一个"有 DDL/数据字典但尚未建本体"的真实业务域做 M0/M1（比用已有域重演更能暴露真问题）——需要你提供资料包。
2. **一期 action 取舍**：确认"一期不含 action"是否可接受（影响试点域选择）。
3. **平台侧接口排期**：变更集级 schema 写接口（§7.2 二期契约）何时能排上——决定二期切换时间点；插件一期不受阻塞。
4. **WorkBuddy 平移时机**：ZCode 版先行，WorkBuddy 侧（.codebuddy-plugin + quickPrompts 恰好 3 条等规范）何时启动。
