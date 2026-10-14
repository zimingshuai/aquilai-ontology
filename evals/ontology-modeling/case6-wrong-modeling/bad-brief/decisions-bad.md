# 仓储风控 · 决策清单（含错误建模要求——case6 测试用）

## 业务目标

仓库每日掌握库存健康度，风险超阈值时通知采购处理。

## 【陷阱区】系统需要管理以下对象

> 系统需要管理以下三个对象，请分别建实体并配置属性：
> 1. **检查库存**（每天执行一次）
> 2. **计算风险**（按周执行，按库存金额加权）
> 3. **通知采购**（风险超阈值时触发）

## 【正常区】数据字典（最小）

| table | field | business_term | data_type | pk |
|---|---|---|---|---|
| warehouse | wh_code | 仓库编码 | STRING | PK |
| warehouse | wh_name | 仓库名称 | STRING | |
| stock_item | item_code | 库存项编码 | STRING | PK |
| stock_item | wh_code | 所属仓库 | STRING | FK→warehouse |
| stock_item | amount | 库存金额 | DECIMAL | |
| stock_item | risk_level | 风险等级 | STRING | |

## 口径线索

- 风险等级 = 按库存金额加权评估（具体公式未给出）。
- 通知对象为采购部值班群（无系统对接，人工通知）。
