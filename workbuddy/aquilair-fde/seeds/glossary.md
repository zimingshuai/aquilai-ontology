# 术语对照表（glossary）——受控词表 v0.3

> lint 第 9 条的数据源：同义/历史命名对照，防止跨域与跨版本命名漂移（实证：同文档两次独立从零生成仅 7/26 实体同名）。
> 登记规则：人审时裁定入库；"建议名"为当前推荐命名，"已知别名"列出历史上出现过的命名（不判对错，lint 命中别名时报 warning 提示对照）。

## 跨域同义对照（fnb ↔ mfg）

| 概念 | fnb 命名 | mfg 命名 | 说明 |
|---|---|---|---|
| 物料/商品 | SKU | Material | 业务语义对应（最小跟踪单位），跨域打通时显式映射，不静默合并 |
| 存储节点 | Warehouse | Plant | 仓库 ↔ 工厂 |
| 库存载体 | SKUInWarehouse | MaterialInPlant | 同构三元结构（物料×位置×库存） |
| 位置间转移 | ReplenishmentOrder | TransferPlan | 调拨语义 |

## 同域历史版本对照（xgimi 两版实证，2026-10-13）

| 概念 | 上次试用版（21 实体） | 本次复验版（26 实体，建议名） |
|---|---|---|
| 运行快照 | RunSnapshot | CalculationRun |
| 工程变更 | EcnChange | EcnRecord |
| 授权 | Authorization | MaterialAuthorization |
| 替代 | Substitution | SubstitutionPermission |
| 单位换算 | UomConversion | UnitConversion |
| 历史案例 | HistoryCase | HistoricalCase |
| 呆滞风险 | ObsolescenceRisk | SlowMovingRisk |
| 处置方案 | ObsolescenceSolution | SolutionPlan |
| 策备建议 | ReplenishmentSuggestion | SourcingSuggestion |
| 供应商条件 | SupplierMaterialCondition | SupplierSupplyCondition |
| 两版同名 | Project、Material、Supplier、Demand、Supply、BomLine、VendorReferenceList（7 个） | — |

> 使用约定：xgimi 本体定稿（人审通过）后，定稿版命名固化为该域标准；后续增量必须复用，禁止再从零生成。
