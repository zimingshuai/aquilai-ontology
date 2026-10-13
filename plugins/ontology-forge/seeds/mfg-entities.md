# mfg 域既有实体速查表（引擎快照）

> 数据来源：MCP 服务 `data-service-mfg-sandbox` 生产环境 `get_meta_objects` / `get_meta_rules` 实测返回（2026-10-13 M2 提取）。
> 用途：本体建模时优先复用既有实体/字段/别名，避免另造同义词。fnb 域速查见 `fnb-entities.md`。

## 实体清单（10 个）

| 实体名 | 表名 | 展示名 | 主键字段 | links（别名→目标） | 属性数 |
|---|---|---|---|---|---|
| Plant | Plant | 工厂 / 生产基地 | plant_code | — | 3 |
| Material | Material | 物料 | material_code | — | 8 |
| PlantTransferRouting | PlantTransferRouting | 工厂调拨路径 | routing_code | source_plant→Plant; target_plant→Plant | 6 |
| MaterialInPlant | MaterialInPlant | 工厂物料 | material_in_plant_code | plant→Plant; material→Material | 12 |
| TransferOptimizationObjective | TransferOptimizationObjective | 调拨优化目标 | objective_code | — | 4 |
| TransferOptimizationStrategy | TransferOptimizationStrategy | 调拨优化策略 | strategy_code | — | 4 |
| TransferOptObjectiveInStrategy | TransferOptObjectiveInStrategy | 调拨策略优化目标配置 | objective_in_strategy_code | strategy→TransferOptimizationStrategy; objective→TransferOptimizationObjective | 6 |
| TransferOptimizationSolution | TransferOptimizationSolution | 调拨优化方案 | solution_code | strategy→TransferOptimizationStrategy | 6 |
| TransferPlan | TransferPlan | 调拨计划 | transfer_plan_code | opt_solution→TransferOptimizationSolution; material→Material; source_plant→Plant; target_plant→Plant; transfer_routing→PlantTransferRouting | 14 |
| TransferOptSolutionEvaluation | TransferOptSolutionEvaluation | 调拨优化方案评估 | solution_code | solution→TransferOptimizationSolution | 5 |

> 注：①`table_name` 与实体名同名（mfg 域注册惯例，与 fnb 的 snake_case 表名不同，勿假设大小写变换关系）；
> ② `TransferOptObjectiveInStrategy` 主键为组合编码（strategy_code + '_' + objective_code）；
> ③ `TransferOptSolutionEvaluation` 的主键 `solution_code` 同时是指向方案的引用字段（主键即外键）。

## 常用引擎惯例摘录（3 条 derived 规则原文）

以下为快照 `get_meta_rules` 中的 derived_property 原文（`目标字段: 表达式`），体现 mfg 域引擎方言
三惯例——MAX 下限哨兵兜底 / links 别名单跳引用 / 本地字段四则计算，新本体生成表达式时优先沿用：

1. **MAX 下限哨兵惯例**（算术结果非负夹逼；fnb 域未见，mfg 实测）——剩余可供应量（MaterialInPlant）：
   `remain_supply_qty: MAX(0.0, onhand_inventory_qty + undelivery_purchase_qty - undelivery_sales_qty)`
2. **links 别名单跳引用惯例**（跨实体属性直引）——单位成本（TransferPlan，经别名 transfer_routing）：
   `unit_cost: transfer_routing.unit_cost`
3. **本地字段四则惯例**（upstream 自身属性直接运算）——总调拨成本（TransferPlan）：
   `total_cost: unit_cost * total_qty`

> 规则全景：10 条 derived_property + 1 条 trigger（`unfulfill_sales_qty > 0` 自动触发调拨优化）+
> 4 条 admission（modify_plan 数量区间/计划状态/可供应量、run_supply_demand_allocation 策略启用校验）。
> admission 的 instance 检查支持嵌套 lookup（按 TransferPlan 反查起点工厂+物料再查 MaterialInPlant），为
> 引擎侧最复杂的准入形态，DSL §3.3 语法已覆盖。
