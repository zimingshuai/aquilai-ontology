> 域交接包（handoff）——技能工厂（aquilair-skill-forge）立项素材。
> 红线：本文件是技能**制造时**的输入素材，不是技能**运行时**依赖；
> 动作/规则/字段等易变结构一律以平台 MCP 实时元数据为准，本包内容不沉淀为快照。

# OQ 裁决记录与能力边界

> 用途：resolved 组是 calibers 口径节的 provenance 素材；pending-engine 组是技能能力边界
> （「平台无承载」类声明）的素材——技能被要求做无承载之事时如实说明，不降级。

## 已裁决（口径出处）

| OQ | 议题 | 裁决 | 状态 |
|---|---|---|---|
| OQ-01 | 策备建议量向上取整（方言边界） | 已裁决（2026-10-14，用户）：A 方案——引擎方言扩展 CEILING 取整函数；扩展落地后由 derived 规则承载表达式（方言扩展需求转引擎侧，方言 cookbook 待办） | resolved-pending-engine |
| OQ-02 | 多级 BOM 迭代展开（方言边界） | 已裁决（2026-10-14，用户）：C 方案——动作域承载，见 actions.expand_demand_to_requirement | resolved |
| OQ-03 | 需求去重与覆盖关系选取（方言边界） | 已裁决（2026-10-14，用户）：C 方案——动作域承载，见 actions.expand_demand_to_requirement | resolved |
| OQ-04 | 供给分配优先级与稳定排序（方言边界） | 已裁决（2026-10-14，用户）：C 方案——动作域承载，见 actions.allocate_supply | resolved |
| OQ-05 | 分期滚动结转（方言边界） | 已裁决（2026-10-14，用户）：C 方案——动作域承载，见 actions.compute_period_balance | resolved |
| OQ-06 | 替代资格多条件检查（方言边界） | 已裁决（2026-10-14，用户）：C 方案——动作域承载，见 actions.check_substitution_qualification | resolved |
| OQ-07 | 方案措施数据调整与完整重算（方言边界/动作域） | 已裁决（2026-10-14，用户）：C 方案——动作域承载，见 actions.recompute_scenario | resolved |
| OQ-08 | 授权生效版本选择（方言边界） | 已裁决（2026-10-14，用户）：B 方案——预计算，数据侧维护"当前有效授权"视图/字段 | resolved |
| OQ-09 | 防重复归因上限约束（admission 候选） | 已裁决（2026-10-14，用户）：立即落地 admission 拦截——见 admission 规则「归因不得超案例总量」（upstream actions.record_cause_attribution） | resolved |

## pending-engine（技能能力边界素材）

| OQ | 议题 | 卡点 | 状态 |
|---|---|---|---|
| OQ-01 | 策备建议量向上取整（方言边界） | 无（文档口径齐全，缺的是引擎方言能力——由引擎侧裁决是否扩展取整函数） | resolved-pending-engine |

## 其他待办（等业务方/等输入）

| OQ | 议题 | 状态 |
|---|---|---|
| OQ-10 | 主案例 ECN 编号缺失 | pending-business |
| OQ-11 | 参考清单外发审批流程未定义 | pending-business |
| OQ-12 | known_at"V0 之前"的精确时点 | pending-business |

共 12 条（resolved 9 / pending-engine 1 / 其他 3；
resolved-pending-* 条目同时具有口径出处与能力边界价值，在前两组双列属预期）。
