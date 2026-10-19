# fnb 域既有实体速查表（引擎快照）

> 数据来源：`poc/m0/fnb/snapshot_objects.json`（引擎 get_meta_objects 实测快照，2026-10-13 M0 POC 提取）。
> 用途：本体建模时优先复用既有实体/字段/别名，避免另造同义词。
> **mfg 域速查已补：见 `mfg-entities.md`（2026-10-13 M2）。**

## 实体清单（15 个）

| 实体名 | 表名 | 展示名 | 主键字段 | links（别名→目标） | 属性数 |
|---|---|---|---|---|---|
| ProductCategory | product_category | 产品品类 | pc_code | — | 3 |
| SKU | sku | 商品SKU | sku_code | product_category→ProductCategory | 22 |
| Warehouse | warehouse | 仓库 | wh_code | — | 7 |
| PurchaseOrder | purchase_order | 采购订单 | purchase_order_nr | sku→SKU; warehouse→Warehouse; sku_in_warehouse→SKUInWarehouse | 15 |
| ReplenishmentOrder | replenishment_order | 调拨单 | replenishment_order_nr | sku_in_warehouse→SKUInWarehouse | 2 |
| SalesOrder | sales_order | 销售订单 | order_nr | sku→SKU; warehouse→Warehouse; sku_in_warehouse→SKUInWarehouse | 12 |
| SKUInWarehouse | sku_in_warehouse | SKU在库状态 | sku_in_wh_code | sku→SKU; warehouse→Warehouse; product_category_in_warehouse→ProductCategoryInWarehouse; inventory_in_warehouse→InventoryInWarehouse | 23 |
| ProductCategoryInWarehouse | product_category_in_warehouse | 品类在库状态 | pc_in_wh_code | product_category→ProductCategory; warehouse→Warehouse | 16 |
| InventoryInWarehouse | inventory_in_warehouse | 仓库库存总量 | inventory_code | warehouse→Warehouse | 12 |
| InventoryInWHProblem | inventory_in_wh_problem | 仓库库存业务问题 | problem_code | wh→InventoryInWarehouse; sku_in_wh→SKUInWarehouse | 5 |
| InventoryInWHCause | inventory_in_wh_cause | 仓库库存业务问题原因 | cause_code | problem→InventoryInWHProblem; sku_in_wh→SKUInWarehouse | 7 |
| ForecastSalesDemand | forecast_sales_demand | 预测销售需求 | order_nr | sku→SKU; warehouse→Warehouse | 8 |
| ForecastSalesTrace | forecast_sales_trace | 需求预测追踪记录 | trace_nr | sku→SKU; warehouse→Warehouse | 10 |
| InventoryRisk | inventory_risk | 需求预测追踪记录* | risk_code | warehouse→Warehouse | 9 |
| InventoryOptimizationSolution | inventory_optimization_solution | 库存优化方案 | solution_type, problem_code（复合） | — | 6 |

> *InventoryRisk 的 display_name 在引擎快照中即「需求预测追踪记录」（与 ForecastSalesTrace 同名，疑为快照侧复制残留）；
> 建模引用时以实体名/表名为准，如需更正展示名须走引擎侧变更。

## 常用引擎惯例摘录（3 条 derived 规则原文）

以下为快照 `get_meta_rules` 中的 derived_property 原文（`目标字段: 表达式`），体现引擎方言三惯例——
除法哨兵兜底 / 子集合加权平均 / 反向单跳聚合，新本体生成表达式时优先沿用：

1. **除法兜底惯例**（分母为空/异常给哨兵值 9999）——SKU库存周转天数（SKUInWarehouse）：
   `inventory_turnover_days: COALESCE(average_inventory_qty / average_daily_outbound_qty, 9999)`
2. **加权平均惯例**（SUM(指标×权重) / SUM(权重)；复数引用 `sku_in_whs` = links 别名 `sku_in_wh` + s）——仓库加权平均库存元天（InventoryInWarehouse）：
   `average_idd: SUM(sku_in_whs.idd * sku_in_whs.influencing_factor) / SUM(sku_in_whs.influencing_factor)`
3. **反向单跳聚合惯例**（复数引用 = 引用方表名 + s）——未交货销售订单量（SKUInWarehouse）：
   `undelivery_sales_qty: SUM(sales_orders.undelivery_qty)`

> 复数引用两种实测形态：表名+s（`purchase_orders`、`sales_orders`）与 links 别名+s（`sku_in_whs`）；
> 例外形态以引擎实际为准（dsl-spec §2）。
