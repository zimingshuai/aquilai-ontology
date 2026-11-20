# M0 盲测对照分析（gold standard vs 盲测生成）

> 分析人：主代理（独立验收，非子代理自述）｜ 日期：2026-10-13
> 方法：逐项比对 gold/model.yaml（人工基准）与 generated/model.yaml（子代理仅凭资料包生成）
> 佐证基准：fnb 引擎真实元数据（get_meta_objects 实测）用于裁决两侧分歧

## 一、总判定：核心假设强阳性通过

「LLM 从资料包生成 DSL」质量超预期——结构正确率高，且**三处与 gold 的分歧中有两处是生成侧更正确**（与引擎实际一致，gold 人工基准反而遗漏）。

## 二、逐项对照

### 2.1 完全一致的部分 ✅
- 实体集合（4 个）、实体名/表名/展示名/描述
- 26 个原始字段：名称、类型、主键**零漂移**（命名治理假设得到验证）
- links：3 条，别名全部按规范默认（supplier / purchase_contract），无命名漂移
- trigger 规则 2 条：条件树、阈值（>2000 且 >0.05；frozen_flag==true）、downstream 动作名完全一致
- derived「对账差异金额」表达式逐字符一致（`invoice_amount - COALESCE(reconciled_amount, 0)`）
- CQ 4 条问题文本与 covered_by 基本一致
- provenance 全程标注；禁止脑补执行到位（9999 兜底不硬凑、拦截机制不发明、无承载字段不打标）

### 2.2 生成侧比 gold 更正确的两处（重要发现）⭐

1. **衍生字段以实体属性声明**：generated 把 recon_diff_amount / recon_diff_rate / total_delivery_amount 声明进实体 properties（并按 lint 规则4 论证了为什么必须声明）；gold 只写在规则 logic 里未声明属性。**引擎实际裁决**：fnb 的 get_meta_objects 里 SKUInWarehouse.properties 包含 inventory_turnover_days / idd / inventory_level 等衍生字段——**引擎把衍生字段放在实体属性中，generated 的理解正确，gold 有遗漏**。
2. **外键字段保留为属性 + links 并存**：generated 保留 supplier_code / contract_nr 为 STRING 属性同时声明 links；gold 只写 links 漏了外键字段属性。**引擎实际裁决**：fnb 的 PurchaseOrder.properties 里有 sku_code / wh_code 且 links 并存——**generated 正确，gold 有遗漏**。

结论：这两处不是"生成质量好"的偶然，而是 DSL 规范（lint 规则4 的字面要求 + links 语义描述）把生成侧推向了与引擎实际一致的方向——**规范约束生效的直接证据**。

### 2.3 合理偏差（规范缺口导致，非生成错误）⚠️

1. **差异率 9999 兜底**：gold 写 `COALESCE(recon_diff_amount / invoice_amount, 9999)`；generated 认为方言无条件分支、拒绝硬凑，只写基础除法并把兜底口径记入 oq-001。**引擎惯例裁决**：fnb 实测存在 `inventory_turnover_days: COALESCE(average_inventory_qty / average_daily_outbound_qty, 9999)`——引擎作者自己也用 COALESCE 包除法做 9999 兜底，gold 写法与引擎惯例一致。generated 因盲测隔离（未读引擎数据）而保守化。→ **规范修订：§3.1 增加方言 cookbook（引擎惯例示例），可消除此类偏差**。
2. **两跳反向聚合**：gold 写 `SUM(purchase_contracts.delivery_records.delivery_amount)`（嵌套路径，upstream=[Supplier]）；generated 写 `SUM(delivery_records.delivery_amount)`（扁平路径，upstream=[Supplier, PurchaseContract, DeliveryRecord]）。fnb 实测仅有一跳先例，两写法均待引擎验证——**规范缺口：多跳反向聚合语法未定义 + upstream 语义（依附主实体单元素 vs 依赖链数组）未明确**。
3. 衍生字段类型推断（DECIMAL/比率）：generated 以 assumption 记录（as-002），gold 未记录——generated 更严谨（人审时类型推断可见）。

### 2.4 生成侧超过 gold 的审查发现 ⭐

- **cf-001 真实口径冲突**：rules.md「交货总额=所有合同下全部交货（全量）」vs decisions.md 决策3「本期实际交付金额（隐含按期间）」——资料包真实存在的口径出入（主代理造包时未察觉、写 gold 时也未察觉），盲测代理交叉比对三源材料后抓到。
- **oq-005 打标承载字段缺失**：mark_recon_review 无物理承载字段（review_flag 之类）——真问题。
- **oq-006 供应商+月份唯一性**：访谈口头约定 vs DDL 无唯一约束——真问题。
- 6 条 open_questions + 8 条 assumptions 的完备性显著超过 gold（2 条 oq / 0 assumptions）。

## 三、对 DSL v0.1 的修订清单（POC 直接产出）

| # | 修订点 | 依据 |
|---|---|---|
| 1 | §2：衍生字段**必须**在实体 properties 声明（类型推断记 assumption） | 引擎实际 + 生成侧正确理解 |
| 2 | §2：外键字段保留为属性 + links **并存**声明 | 引擎实际（fnb PurchaseOrder） |
| 3 | §3.1：增加方言 cookbook：`COALESCE(x / y, 9999)` 兜底模式等引擎惯例示例 | fnb 实测惯例，消除保守化偏差 |
| 4 | §3.1：定义多跳反向聚合语法（嵌套 vs 扁平，待 fnb round-trip 数据佐证后定稿） | 两写法分歧 |
| 5 | §3：明确 upstream 语义 = 计算/条件所依附的主实体（对齐引擎实测形态） | upstream 形态分歧 |
| 6 | lint 补充：衍生字段属性声明检查、外键字段与 links 一致性检查 | 修订 1/2 的机器化 |

## 四、遗留

- gold/model.yaml 本身需按修订 1/2 更正（它有两处与引擎实际不符的遗漏），更新后作为 M1 的回归基线。
- 完整 POC 报告待 fnb round-trip（子代理 A）完成后合并输出。
