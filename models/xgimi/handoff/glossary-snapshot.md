> 域交接包（handoff）——技能工厂（aquilair-skill-forge）立项素材。
> 红线：本文件是技能**制造时**的输入素材，不是技能**运行时**依赖；
> 动作/规则/字段等易变结构一律以平台 MCP 实时元数据为准，本包内容不沉淀为快照。

# 术语与实体中文名对照（权威表快照）

> 用途：技能交付规范「中文名（编码）」双写的对照来源；术语定义可直接进 calibers 术语节。

## 受控词表（glossary_additions）

| 术语 | 定义 |
|---|---|
| 策备 | 电子料全量需求梳理→供应商备料/策备审批，输出授权外需求与供应商参考清单 |
| 点检 | 前后版本 BOM/风险BOM/替代/授权的自动对比与变化识别 |
| 呆滞 | 评估期末无法消耗的剩余物料风险 |
| known_at | 记录可见时间，以数据版本号（V0-V3）表达 |
| FACT-SIM | 事实记录与模拟记录分别保存的情景隔离约定 |
| 风险 BOM | NPI 阶段经批准的预估 BOM |

## 实体编码 ↔ 展示名

| 实体（编码） | 中文名 | 属性数 |
|---|---|---|
| Project | 项目 | 6 |
| Material | 物料 | 4 |
| UnitConversion | 单位换算 | 7 |
| Supplier | 供应商 | 3 |
| BomLine | BOM行 | 14 |
| EcnRecord | 工程变更记录 | 8 |
| Demand | 需求 | 10 |
| MaterialAuthorization | 物料授权 | 9 |
| Supply | 供给记录 | 11 |
| PurchaseOrder | 采购订单 | 17 |
| StockMovement | 库存流水 | 8 |
| SubstitutionPermission | 替代与转用许可 | 14 |
| SupplierSupplyCondition | 供应商供货条件 | 8 |
| DataVersion | 数据版本 | 4 |
| CalculationRun | 计算运行快照 | 9 |
| MaterialRequirement | 物料需求汇总 | 12 |
| InspectionChange | 点检变化记录 | 11 |
| ReviewTask | 复核任务 | 5 |
| SourcingSuggestion | 策备建议 | 9 |
| VendorReferenceList | 供应商参考清单 | 5 |
| PeriodSupplyBalance | 分期供需 | 12 |
| SlowMovingRisk | 呆滞风险 | 10 |
| SolutionPlan | 处理方案 | 15 |
| HistoricalCase | 历史呆滞案例 | 11 |
| CauseAttribution | 原因归因 | 6 |
| PreventionRule | 预防规则 | 6 |
