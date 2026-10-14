# case3 verdict：业务定义冲突

- 日期：2026-10-14
- 判定：**PASS**（4/4 断言符合，无禁止表现）
- 执行方式：单代理双角色模拟——同一执行代理先以「加载 ontology-forge:ontology-modeling 技能的建模 agent」身份按流水线第 1-3 步生成产物，再以「测评人」身份按 expected.md 冷静断言；非独立新会话执行，Charter 的"用户确认"环节由测试剧本代理推进（已在 charter.md 头部注明）。产物位于临时目录 D:\tmp\case3-out\（charter.md / fact-cards.json / model.yaml），资料包 D:\tmp\case3-brief\（金标准全量 + rules.md 替换为 rules-conflicted.md）。

## 断言逐条核查

### 断言 1：conflicts 结构化登记双口径 —— 符合

model.yaml `conflicts` 段（非空、结构化、非 description 内散写）：

```yaml
conflicts:
  - topic: 对账差异金额符号口径
    side_a:
      holder: 财务共享中心（王财务，2026-09 口径会）
      definition: 差异金额 = 发票金额 − 已对账金额（元）；正值=尚有未核对一致部分；负值=多对账，保留负值不取绝对值；无已对账金额按 0 处理
      source: "B_scenarios/rules.md#口径A"
      corroboration: "C_interviews/interview_finance.md#Q3（访谈与口径 A 一致）"
    side_b:
      holder: 内审部（李审计，2026-09 审计意见）
      definition: 差异金额 = |发票金额 − 已对账金额|（元，取绝对值），差异度量恒非负；理由：差异用于风险排序，负值会导致"多对账越多风险越小"的误导
      source: "B_scenarios/rules.md#口径B"
    status: pending
```

topic 与 expected.md 要求逐字一致；双方定义（含口径 B 的绝对值理由）与署名来源均保留；brief.yaml known_conflicts 为空，冲突由生成过程交叉比对自行发现（fact-cards.json FC-RULE-001 状态=冲突，发现路径有记录：B 类双口径声明 + C 类访谈佐证 side_a）。

### 断言 2：derived 不擅自定稿 —— 符合

- derived 规则「对账差异金额」logic 按口径 A 起草：`recon_diff_amount: invoice_amount - COALESCE(reconciled_amount, 0)`（无绝对值）。
- description 开头标注：`【口径 A 起草，口径待裁决】…审计口径 B（|发票金额 − 已对账金额| 取绝对值）同样有效待裁决，双方定义与来源见 conflicts——人审裁决前不得视为定稿`。
- conflicts 条目存在且 `status: pending`；同时 open_questions 第 1 条显式登记冲突待裁决并声明联动复核 recon_diff_rate 与复核触发阈值——三重满足（条目在 + pending + description 注明）。

### 断言 3：禁止表现 —— 三项均未出现

- 无冲突记录直接产出单一口径：否，conflicts 结构化存在。
- 静默丢弃口径 B：否，side_b 定义/理由/来源完整保留，且 derived description 与属性 description 中均提及口径 B 存在。
- 冲突只进 description 不进 conflicts 结构：否，description 仅作指引（"见 conflicts「对账差异金额符号口径」条目"），结构化记录在 conflicts。

### 断言 4：lint / check_cq 照常通过 —— 符合

- `python plugins/ontology-forge/scripts/lint_model.py D:\tmp\case3-out\model.yaml` → `====lint 通过====: error 0 处，warning 0 处`（exit 0）
- `python plugins/ontology-forge/scripts/check_cq.py …` → `====CQ 检查通过====: 6 条能力问题，不可解析引用 0 处`（exit 0）
- 冲突未阻塞结构校验，与 expected「冲突阻塞的是人审定稿而非 lint」一致。

## 过程记录（如实）

- 首次 lint 失败：description 文本中的 `conflicts[0]` 方括号在 YAML flow mapping 中被解析为流序列导致语法错误。按技能铁律「lint 不过不进下一步；修复后再跑」，改写为文字引用后重跑通过。该失败属 YAML 语法修复闭环，非断言相关违规。
- 次生观察（技能缺陷候选）：dsl-spec v0.2 未定义 conflicts 的标准条目结构（仅注释"保留双方定义与来源"），本例结构参考 rules-conflicted.md 文末声明格式自拟（topic/side_a/side_b/status/impact/discovered_by）。建议 v0.3 固化 conflicts 条目 schema 并纳入 lint 检查，否则不同会话产物结构可能漂移，评审侧难以机器比对。
