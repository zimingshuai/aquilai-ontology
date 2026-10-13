# M0 POC 报告：三假设验证结论

> 日期：2026-10-13 ｜ 验收方式：主代理独立复跑脚本 + 字节级复验 + 一手数据锚点验证（不以子代理汇报为准）
> 关联：docs/design/2026-10-10-ontology-modeling-plugin-design.md（方案）｜goldstandard/comparison.md（盲测对照分析）｜fnb/roundtrip_report.md（round-trip 报告）

## 一、结论（TL;DR）

| # | 假设 | 结论 | 证据 |
|---|---|---|---|
| 1 | DSL 能无损表达既有本体 | ✅ **通过** | fnb 全量（15 实体 / 157 属性 / 24 links / 60 规则）逆向导出 → 编译回引擎格式，round-trip 差异 **0**；字节级复验 compiled ≡ snapshot（35423 / 22560 字节） |
| 2 | LLM 从资料包生成 DSL 的质量 | ✅ **强阳性通过** | 合成域盲测（严格隔离 gold）：实体/字段/links/trigger/CQ 零漂移；**两处比人工 gold 更正确**（与引擎实际一致）；发现 1 条人工未察觉的真实口径冲突 + 4 条业务层待确认问题 |
| 3 | 编译器（DSL→引擎格式）可行性 | ✅ **通过** | 纯结构驱动、零实体名特判；比对器先经 8 个构造样例自测防假阳性；支持复合主键/短别名/空 links/空串描述等全部 fnb 实测形态 |

**判定：三假设全部通过，DSL 选型与流水线架构成立，进入 M1。**

## 二、验收记录（独立复验证据）

1. `python scripts/compile_model.py` → 15 实体 / 157 属性 / 60 规则（48 derived + 12 trigger），与快照统计一致
2. `python scripts/roundtrip_check.py` → 实体差异 0、规则差异 0、退出码 0
3. `cmp` 字节级复验：compiled_objects.json ≡ snapshot_objects.json；compiled_rules.json ≡ snapshot_rules.json
4. 锚点验证（排除缓存时效风险，见 §四）：复合主键 / PurchaseOrder links / SKUInWarehouse 23 属性与短别名 / 引擎 COALESCE 惯例，全部与 2026-10-10 主代理亲手拉取的一手元数据一致

## 三、盲测关键发现（详见 goldstandard/comparison.md）

**质量证据**：
- 结构零漂移：26 字段名/类型/主键、links 默认别名、trigger 条件树与阈值、CQ 全部与 gold 一致
- 生成侧两处比 gold 正确（引擎实际裁决）：①衍生字段声明进实体属性；②外键字段保留属性 + links 并存——**DSL 规范的约束把生成侧推向了与引擎一致的方向，这是规范设计生效的直接证据**
- 交叉审查超预期：抓到资料包中 rules.md（全量口径）vs decisions.md 决策 3（本期口径）的真实冲突，以及打标承载字段缺失、供应商+月份唯一性等 4 条 gold 未发现的问题；provenance 三源交叉标注、禁止脑补执行到位（9999 兜底不硬凑、拦截机制不发明）

**暴露的规范缺口（全部在规范侧，非生成侧错误）**：
1. 方言 cookbook 缺失 → 9999 兜底保守化（引擎惯例 `COALESCE(x/y, 9999)` 应写入规范示例）
2. 多跳反向聚合语法未定义（gold 嵌套写法 vs 生成侧扁平写法，均待引擎验证）
3. upstream 语义未明确（依附主实体 vs 依赖链数组）

## 四、环境偏差（如实记录）

- fnb MCP 端点（https://aquilair-mcp0.idcs.elitescloud.com/mcp）在 POC 期间连续 5 次 502（网关层，服务端后端不可达，跨约 2 分钟）
- 兜底：使用技能官方脚本 fetch_meta.py 于 **2026-09-30 从同一端点拉取落盘的缓存快照**（get_meta_* 原始返回，未手工整理），来源与时间戳固化于 fnb/snapshot_source_info.json
- 时效性风险处置：主代理用 **2026-10-10 亲手拉取的一手元数据**对缓存快照做锚点验证（实体清单/复合主键/links/属性数/规则惯例 5 组特征点），全部一致——快照可信
- 待办：fnb 引擎恢复后重拉一次快照复跑 round-trip（分钟级操作），当前结论不受影响

## 五、DSL v0.2 修订清单（M1 前执行）

| # | 修订 | 来源 |
|---|---|---|
| 1 | §2：衍生字段**必须**在实体 properties 声明（类型推断记 assumption） | 引擎实际 + 盲测 |
| 2 | §2：外键字段保留为属性 + links **并存**声明 | 引擎实际（fnb PurchaseOrder） |
| 3 | §3.1：增加方言 cookbook（`COALESCE(x/y, 9999)` 兜底等引擎惯例示例） | fnb 规则实测 |
| 4 | §3.1：定义多跳反向聚合语法（优先验证嵌套路径，fnb 无先例需引擎侧确认） | 盲测分歧 |
| 5 | §3：明确 upstream 语义 = 计算/条件依附的主实体 | 盲测分歧 |
| 6 | lint 补充：衍生字段属性声明检查、外键字段与 links 一致性检查 | 修订 1/2 机器化 |

同步事项：gold/model.yaml 按修订 1/2 更正（补衍生字段属性声明 + 外键字段属性），更新后作为 M1 回归基线。

## 六、其他记录

- 引擎数据自带两处疑似源头笔误已原样保真（非 DSL 问题，round-trip 不受影响）：`ForecastSalesDemand` 的 sku_name 规则引用 `sku.sku_code`；`InventoryRisk` 的 display_name/description 与 ForecastSalesTrace 错位（技能文档已知问题）
- 产物索引：`fnb/`（快照×3 + DSL + 编译产物×2 + 报告 + 溯源）、`scripts/`（export_dsl / compile_model / roundtrip_check，均可独立复跑）、`goldstandard/`（资料包 + gold + generated + comparison）
- 复现命令：`cd poc/m0 && python scripts/compile_model.py && python scripts/roundtrip_check.py`

## 七、M1 启动条件确认

- [x] DSL 表达力验证通过（本报告假设 1）
- [x] LLM 生成质量验证通过（假设 2，合成域）
- [x] 编译器可行性验证通过（假设 3）
- [ ] 真实试点域资料包（用户后续提供时替换合成域做增量复验，不阻塞 M1 骨架开发）
- [ ] fnb 引擎恢复后快照复拉（分钟级，不阻塞）
