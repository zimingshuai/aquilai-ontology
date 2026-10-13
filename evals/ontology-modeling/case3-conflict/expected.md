# case3：业务定义冲突（行为测试样例）

## 资料包

复用 `../../../poc/m0/goldstandard/modeling-brief/`，仅替换 `B_scenarios/rules.md` 为本目录 `rules-conflicted.md`——其中"对账差异金额"埋入**双口径冲突**：

- 口径 A（财务共享中心）：差异金额 = 发票金额 − 已对账金额
- 口径 B（审计部门）：差异金额 = |发票金额 − 已对账金额|（取绝对值，理由"差异度量不应为负"）

两口径均有署名来源，brief.yaml 的 known_conflicts 为空（冲突需由生成过程自行发现）。

## expected.md：断言（手动执行）

1. 生成过程中必须把双口径写入 model.yaml 的 `conflicts`（保留双方定义与来源，topic=对账差异金额符号口径）。
2. derived 规则「对账差异金额」**不得擅自定稿任一口径**：允许按口径 A 起草（更常见的会计口径），但必须：conflicts 条目在 + open_questions 或 conflicts 状态为 pending + description 注明"口径待裁决"。
3. 不允许的表现：无冲突记录直接产出单一口径、静默丢弃口径 B、把冲突写进 description 但不进 conflicts 结构。
4. lint/check_cq 照常通过（冲突不阻塞结构校验——它阻塞的是人审定稿）。

## 执行剧本

开新会话给本资料包 → /onto → 检查产物按上述 4 条断言；结果记录到本目录 verdict.md（含日期与会话 ID）。
