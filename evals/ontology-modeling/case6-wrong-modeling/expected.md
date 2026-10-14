# case6：错误建模识别（行为测试样例·楠总蓝图样例六）

## 坏资料包（bad-brief/）

资料包含一处典型的"流程步骤当对象"建模陷阱——decisions-bad.md 中要求：

> 系统需要管理以下对象：**检查库存**（每天执行）、**计算风险**（按周执行）、**通知采购**（触发式）。
> 请为这三个对象分别建实体并配置属性。

（正确语义：三者是流程步骤/规则/动作——"检查库存"是数据查询（无独立身份）、"计算风险"是 derived/trigger 计算、"通知采购"是 trigger 下游动作。）

## expected.md：断言

1. **不建伪对象**：产出的 model.yaml 中不存在名为 检查库存/计算风险/通知采购（或其英文直译 CheckInventory/CalculateRisk/NotifyPurchase）的实体。
2. **正确归类**：
   - "计算风险"若在资料中有口径公式 → derived/trigger 候选或 open_questions；
   - "通知采购" → trigger 的 downstream 动作名（或 open_questions 注明动作语义）；
   - "检查库存" → 归为查询/CQ 能力问题（如 cq: 当前库存状态如何查询）。
3. **解释义务**：交互中向用户说明识别依据（无独立身份/状态/生命周期，不满足实体判定）——对应 ontology-modeling SKILL 铁律 5 与 ontology-review checklist 第 1 项。
4. 允许：就模糊处向用户反问确认（更优行为）；不允许：沉默照建或全部塞进 open_questions 逃避判定。

判定规则：断言 1 为硬性（违反即 FAIL）；2-4 按最优/合格/不合格三档记录。

## 执行剧本

新会话仅提供 bad-brief/（brief.yaml target_engine=new + decisions-bad.md + 最小字典）→ /onto → 走流水线 → 按断言检查产物 → verdict.md 记录。
