# trigger —— 触发可靠性回归体系（第 0 关）

> 目的：技能不被触发，后续一切能力都白搭。本目录回归**「该不该触发」**这一层——
> 依据 [Agent Skills 官方规范](https://agentskills.io/skill-creation/optimizing-descriptions)
> 的 trigger eval 方法论落地（2026-11-04 反哺）。与 `../ontology-modeling/` 的行为层回归互补：
> **本目录测触发层（技能该不该被加载），那边测行为层（加载后做对没有）**。

## 用例集（三技能 × 正例 + near-miss 反例）

| 文件 | 技能 | 正例 | 反例 |
|---|---|---|---|
| `brief-intake.json` | 建模资料摄取 | 8 | 5 |
| `ontology-modeling.json` | 本体建模主技能 | 8 | 5 |
| `ontology-review.json` | 本体评审 | 5 | 4 |

格式：`{ "query": 用户原话, "should_trigger": true/false, "reason": 判定依据 }`。

**设计原则（增补用例时遵守）**：

- 正例沿四轴变化：**措辞**（正式/口语/带错别字）、**显式度**（点名领域 vs 只说意图——pushy 场景最有价值：用户没说「本体」但任务就是本体建模）、**细节**（一句话 vs 带文件路径的完整上下文）、**复杂度**（单步 vs 多步流程中的一环）。
- 反例必须是 **near-miss**：关键词与技能重叠但实际任务不同（如「设计订单库 ER 图」vs 本体建模、「review 这段代码」vs 本体评审）。明显无关的查询（「今天天气」）不具测试价值，不收。
- 每条 `reason` 写明判定依据——未来 description 改动导致边界移动时，reason 是仲裁参考。

## 运行方式（手动剧本）

1. 安装插件后开新会话，逐条发送 `query`（一条一个新会话，避免上下文串扰）。
2. 观察技能是否被加载：宿主可观测手段（ZCode 看 Skill 工具调用记录 / Claude Code 看日志）。
3. **每条跑 3 次**（模型非确定性），计算触发率 = 触发次数 / 3。
4. 判定：should_trigger=true 的查询触发率 > 0.5 算过；should_trigger=false 的触发率 < 0.5 算过。
5. 结果记入本目录 `verdict.md`（日期 / 插件版本 / 各查询触发率 / 失败清单）。

## description 优化循环（防过拟合）

description 大改后按以下流程优化触发（对齐官方规范）：

1. **分割**：用例集随机 60/40 分为 train / validation 两份（分割固定，跨迭代不变）。
2. **只看 train 失败改 description**：漏触发→description 太窄，补意图覆盖；误触发→太宽，收紧 not for 边界。**禁止**把失败查询的具体关键词抄进 description（那是过拟合）——要归纳它代表的意图类别。
3. **按 validation 通过率选最优迭代**——不是最后一版最好，可能前面的迭代泛化更好。
4. 优化后再写 5-10 条全新查询做最终检验（从未参与优化的查询才是诚实的泛化测试）。

## 触发时机（何时跑一轮）

- 三技能任一 description 改动后（必跑）。
- 新技能加入时：先建用例集再写 description（用例是 description 的需求规格）。
- 宿主升级 / 分发平台变化后（触发机制宿主相关）。
