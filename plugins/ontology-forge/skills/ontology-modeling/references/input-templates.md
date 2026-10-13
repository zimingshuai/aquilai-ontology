# 输入模板与解析管线（input-templates）

> 建模资料包的标准结构（brief-intake 的归位终点）与各输入管线的处理策略。

## 一、资料包模板（modeling-brief）

```text
models/<domain>/modeling-brief/
├── brief.yaml              # 资料包清单（brief-intake 生成）
├── intake-log.md           # 摄取日志：归位映射 + 源摘要（provenance 锚点）
├── A_schema/               # A 类：结构化 schema（DDL / 数据字典）
├── B_scenarios/            # B 类：决策清单 / 口径规则 / 流程制度
├── C_interviews/           # C 类：访谈 / 口述 / 会议纪要
└── D_reference/            # D 类：参考材料 / 既有本体导出
```

## 二、数据字典字段规范（A 类，ISO 11179 简化版）

| 列 | 必填 | 说明 |
|---|---|---|
| table_name / field_name | ✅ | 物理表名/字段名 |
| business_term | ✅ | 业务术语（中文名 → display_name） |
| definition | ✅ | 业务定义/口径（一句话讲清"是什么、怎么算"） |
| data_type / uom | ✅/– | 类型（映射到 7 种枚举）；量纲 |
| enum_values | – | 枚举值与含义 |
| pk / fk_target | – | 主键标记 / 外键指向（→ links 候选） |
| source_system / owner | – | 来源系统 / 字段责任人 |

## 三、各输入管线处理策略（第 2 步抽取的路线）

**A 类（schema，确定性最强）**：
- 表 → 实体候选；列 → 属性候选；外键 → link 候选。
- 外键关系的**语义命名是公认难点**：fK→link 后，关系业务含义（一对多/多对多、正向叫什么）必须从 B/C 类材料找佐证；找不到进 open_questions。
- 类型映射：VARCHAR/TEXT→STRING、INT→INTEGER、FLOAT/REAL→DOUBLE、DECIMAL/NUMERIC→DECIMAL、BOOL/TINYINT(1)→BOOLEAN、DATE→DATE、DATETIME/TIMESTAMP→TIMESTAMP。

**B 类（场景规则）**：
- decisions.md → Scenario Charter + CQ（主力来源）。
- rules.md → derived/trigger 候选：识别"XX = 公式"句式（derived）与"当…则…"句式（trigger）。
- processes.md → 状态机（enum_values 佐证）与事件候选；流程步骤本身不建对象。

**C 类（访谈口述，两段式强制）**：
- 第一段只做术语与实体候选抽取（名词聚类、口径句式收集）；第二段才建关系与规则。
- 访谈与 A/B 类冲突时：**A/B 为准，冲突记入 conflicts**（口述是弱来源，但必须保留记录）。

**D 类（参考）**：
- existing_ontology.json（引擎快照）→ 增量建模的 diff 基准 + 复用清单。
- 行业模板（GS1/SCOR）→ 命名与结构参考，不直接复制（字段以客户实际系统为准）。

## 四、业务事实卡片（第 2 步的统一产出）

```json
{
  "candidates": [
    {
      "kind": "entity|property|link|rule|enum",
      "name": "Supplier",
      "content": { "...": "按 kind 而定，对齐 dsl-spec 结构" },
      "provenance": "A_schema/data_dictionary.md#supplier",
      "confidence": "high|medium|low",
      "status": "confirmed|candidate|conflict|pending",
      "cross_refs": ["C_interviews/interview_finance.md#Q1"]
    }
  ],
  "term_glossary": [
    { "term": "对账差异金额", "synonyms": ["差异额"], "definition_source": "B_scenarios/rules.md" }
  ]
}
```

抽取纪律：同一术语至少两源交叉（A+B 或 B+C）；单源高置信候选 status 最高为 candidate；三源打架进 conflicts。
