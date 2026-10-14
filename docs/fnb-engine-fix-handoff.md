# fnb 引擎本体资产修缮清单（转交文档）

> 生成：2026-10-14 ｜ 来源：ontology-forge v0.3.1 lint 工具对引擎快照（get_meta_objects/get_meta_rules 实测，快照与 2026-10-14 复拉一致）的全量检查
> 性质：不影响 fnb 引擎当前业务运行（引擎 JSON 格式内均合法）；影响 studio-model 模板导出（code 需唯一）、LLM 语义理解（同名歧义）、跨域互操作
> 修完后验证方式：`python plugins/ontology-forge/scripts/lint_model.py <修订后的 fnb DSL>` → 0 error；或引擎侧修复后由 ontology-forge 重新逆向导出复验

## 一、规则名重复（10 组名字，41 处出现，其中 31 处为重复）

引擎按"实体+规则名"定位规则，重名合法；但导出 studio-model 时规则 code 由规则名生成唯一哈希，同名相撞无法导出。**修复建议：规则名加实体前缀消歧**（如「仓库编码」→「采购订单-仓库编码」「销售订单-仓库编码」…），语义不变。

| # | 规则名 | 重复处数 | 出现实体 |
|---|---|---|---|
| 1 | 品类编码 | 3 | SKU、SKUInWarehouse、ProductCategoryInWarehouse |
| 2 | 品类名称 | 3 | SKU、SKUInWarehouse、ProductCategoryInWarehouse |
| 3 | SKU编码 | 6 | PurchaseOrder、SalesOrder、SKUInWarehouse、InventoryInWHCause、ForecastSalesDemand、ForecastSalesTrace |
| 4 | 仓库编码 | **10** | PurchaseOrder、SalesOrder、SKUInWarehouse、ProductCategoryInWarehouse、InventoryInWarehouse、InventoryInWHProblem、InventoryInWHCause、ForecastSalesDemand、ForecastSalesTrace、InventoryRisk |
| 5 | SKU名称 | 3 | SalesOrder、SKUInWarehouse、ForecastSalesDemand |
| 6 | 仓库名称 | 4 | SKUInWarehouse、ProductCategoryInWarehouse、InventoryInWarehouse、InventoryRisk |
| 7 | 未到货采购量 | 3 | SKUInWarehouse、ProductCategoryInWarehouse、InventoryInWarehouse |
| 8 | 未到货调拨量 | 3 | SKUInWarehouse、ProductCategoryInWarehouse、InventoryInWarehouse |
| 9 | 未交货销售订单量 | 3 | SKUInWarehouse、ProductCategoryInWarehouse、InventoryInWarehouse |
| 10 | 销售订单缺货量 | 3 | SKUInWarehouse、ProductCategoryInWarehouse、InventoryInWarehouse |

> 这些重复多源于"冗余字段下卷规则"批量复制（每实体把 sku_code/wh_code 等带过来都叫同名）。

## 二、InventoryRisk 实体展示名/描述错位（复制粘贴残留）

| 项 | 当前值（错误） | 应为 |
|---|---|---|
| InventoryRisk.display_name | 需求预测追踪记录 | **库存风险** |
| InventoryRisk.description | 用于追踪需求预测量与实际需求量的偏差和评估指标值 | 用于追踪仓库库存风险的类型、等级、管控措施等（按其属性 risk_type/risk_level/control_measures 推断，请业务确认） |

危害：与 ForecastSalesTrace（展示名同为"需求预测追踪记录"）同名——LLM 问答无法分辨用户指哪个；studio-model 表达式中文名引用产生歧义。

## 三、附带疑似笔误（供核对，1 处）

- ForecastSalesDemand 域存在一条 sku_name 规则引用了 `sku.sku_code`（输出字段与引用字段疑似不匹配，请核对原始意图是否应为 `sku.sku_name`）。

## 修复优先级建议

1. InventoryRisk 展示名/描述（1 处改 2 个字段，5 分钟，立刻消除 LLM 歧义）——**正确值参照 Studio 侧模板**（demo 导出的 studio-model yaml 中 InventoryRisk.name 已是"库存风险"，MCP 注册表侧是错的）
2. 规则名消歧（41 处改名，建议按"实体-原名"前缀批量重命名；改完 studio-model 导出即可工作）——**Studio 侧模板规则名无重复**，可对照其命名
3. sku_name/sku_code 笔误核对（先与业务确认意图再改）

## 四、根因建议：明确 source of truth（2026-10-14 补充）

同一套 fnb 本体存在两个独立维护的载体：**Studio 模板（studio-model yaml）与 MCP 服务侧注册表（JSON）**——两者已显著漂移（实体字段级仅 6/14 一致；规则集也不同：JSON 侧 60 条 vs yaml 侧 16 条 calculation；本次两处问题恰好都只在 JSON 侧）。建议借本次修缮一并明确：**哪边是唯一维护源头，另一边改为由导出/同步机制生成**（ontology-forge 的 compile --target both / export_dsl 可承担双向转换），否则修完之后两边会再次各自漂移。
