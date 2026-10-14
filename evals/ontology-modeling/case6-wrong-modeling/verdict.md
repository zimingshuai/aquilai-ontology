# case6 verdict：错误建模识别

- 日期：2026-10-14
- 判定：**PASS**（断言 1 硬性通过；断言 2 为最优档；断言 3 符合；断言 4 合格档）
- 执行方式：单代理双角色模拟——建模 agent 以 bad-brief/（brief.yaml + decisions-bad.md）为资料包走技能流水线精简版（第 1 步 Charter → 第 2 步抽取 → 第 3 步 DSL 起草），产物在 D:\tmp\case6-out\（charter.md / fact-cards.json / model.yaml）；测评人再按 expected.md 断言。Charter"用户确认"环节由测试剧本代理推进。lint 与 check_cq 均通过（error 0 / warning 0；3 条 CQ 全可解析）。

## 断言逐条核查

### 断言 1（硬性）：不建伪对象 —— 符合（机器验证）

解析 model.yaml 后实体键名 = `['Warehouse', 'StockItem']`；对 检查库存/计算风险/通知采购/CheckInventory/CalculateRisk/NotifyPurchase 做实体键名匹配，命中 **无**。grep 全文命中项均为注释、字段 description、CQ 自然语言与 open_questions 中的**判定说明文字**，不构成实体。资料包数据字典给出的两个真对象（warehouse / stock_item）正常建模。

### 断言 2：正确归类 —— 符合（最优档）

| 陷阱项 | 归类落点 | 证据 |
|---|---|---|
| 计算风险 | derived_property 候选 + open_questions（资料明确"具体公式未给出"） | OQ 第 1 条：`已判定为 derived_property 候选（目标字段 StockItem.risk_level，按库存金额加权），但资料明确『具体公式未给出』——公式与取值域待业务补充后落地规则，禁止脑补`；StockItem.risk_level 的 description 同步注明"待补口径后由 derived 规则承载" |
| 通知采购 | trigger 的 downstream 动作名（非实体） | OQ 第 2 条：`已判定为 trigger 下游动作（downstream 动作名 notify_purchasing，非实体），但触发阈值未给出，且通知对象为采购部值班群（无系统对接、人工通知）——阈值口径与动作落地方式待业务确认` |
| 检查库存 | 查询/CQ 能力 | cq-001 `当前各库存项的库存金额与风险等级如何查询？`（covered_by: StockItem.amount / StockItem.risk_level） |

说明：expected 对"计算风险"的表述为"若在资料中有口径公式 → derived/trigger 候选或 open_questions"——本资料公式未给出，落 open_questions 是允许末端；产物同时保留了 derived 候选的明确判定（具体到目标字段），优于仅记"待定"。"通知采购"直接给出具体动作名 notify_purchasing，同为最优形态。

### 断言 3：解释义务 —— 符合

识别依据在交互产物中三层可见：
1. charter.md「陷阱区处置声明」：逐项写明判定——如"检查库存：例行查询动作。无独立身份（无编码、不可数——不存在『一条检查库存』）、无状态、无生命周期 → 不建实体"；
2. fact-cards.json FC6-TRAP-001~003：每项带 requirement / verdict / reclassified_to（含"拒绝建实体"字样与铁律 5 引用）；
3. model.yaml 头部注释「陷阱处置声明」与 risk_level 字段 description 中的判定说明。

依据口径：ontology-modeling SKILL 铁律 5（流程步骤不建对象，除非有独立身份+状态+生命周期）+ modeling-guide 三、建模边界表（"通知采购"→trigger 下游的直例）。

### 断言 4：反问确认 vs 逃避判定 —— 合格档

- 未出现"沉默照建"（三个伪对象零建实体）。
- 未出现"全部塞进 open_questions 逃避判定"：三项均有明确归类判定（CQ / derived 候选 / trigger 下游动作），OQ 仅承载客观缺失的参数（公式、阈值、business_owner），每条带 missing_from 指明缺在哪份材料。
- "向用户反问确认"（更优行为）在单代理模拟下无真实用户可反问，以 OQ+missing_from 形式承载等价信息，如实记为合格档而非最优档。

## 过程记录（如实）

- rules 为空数组（而非强行起草占位规则）：公式与阈值均为资料客观缺失，铁律 1 禁止脑补；空 rules 注释中写明了两条规则候选的落地条件。lint 对空 rules 通过（rules 可空为 DSL 规范允许）。
- 次生观察（技能缺陷候选）：技能未提供"拒绝错误建模要求"时的标准交互模板（如何向用户呈现"拒绝建实体 + 归类 + 反问"的话术结构），本例自拟三层呈现（Charter 声明/fact-cards 判定卡/OQ）。建议技能补充该情形的输出约定，提升跨会话一致性。
