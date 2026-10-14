# fnb 本体两份载体对照报告：Studio yaml（设计稿）vs MCP 注册表（实现）

> 生成：2026-10-14 ｜ 对比对象：
> - **yaml 侧（源头/设计稿）**：`C:\Users\zishuai\Downloads\demo_勿动_.yaml`（studio-model 格式，17 实体/16 规则）
> - **MCP 侧（实现）**：data-service-fnb 的元数据注册表（get_meta_objects/get_meta_rules 实测快照，15 实体/60 规则）
> 前提（用户确认）：MCP 就是按 metadata 的 yaml 写的；元数据与实例数据分离——本报告全部为**元数据层对比**，不涉及任何实例数据。

## 一、实体层（17 → 15）

| 情形 | 明细 |
|---|---|
| 同名对应 14 个 | 见属性层对比 |
| 实现时正式命名 | yaml `entity_beffe54c`（Studio 自动 hash 名）→ MCP `ReplenishmentOrder`（调拨单） |
| 实现时裁掉 2 个 | `entity_07bdc1cf`、`entity_68ea2800`（毛利计算结果/供应商，疑似 Studio 草稿对象，未实现） |

**中文名三处不一致**：

| 实体 | yaml（设计稿） | MCP（实现） | 判定 |
|---|---|---|---|
| InventoryRisk | **库存风险**（正确） | 需求预测追踪记录 | ❌ 实现时复制残留（与 ForecastSalesTrace 同名） |
| InventoryInWarehouse | 仓库库存汇总 | 仓库库存总量 | ⚠️ 措辞走样 |
| SKUInWarehouse | sku库存明细 | SKU在库状态 | ⚠️ 措辞走样 |

## 二、属性层（10 个同名实体有差异）

| 类别 | 明细 |
|---|---|
| **实现时新增**（合理） | inventory_code（InventoryInWarehouse 补主键）、solution_priority、wh_name、sku_name（冗余展示字段） |
| **实现时裁掉** | mae_value/mse_value（ForecastSalesTrace）、cause_description、del/price（sku） |
| **改名** | current_date → create_date（InventoryInWHProblem） |
| **类型不一致**（双向都有） | unit_cost、order_qty、due_date、cancel_flag 等；**sled_days：yaml=string（数值暗示，yaml 侧疑误）/ MCP=INTEGER** |

## 三、规则层（16 → 60，差异最大）

- yaml：16 条 calculation，**命名零重复**（下卷规则带"-仓库粒度"后缀消歧）
- MCP：48 derived + 12 trigger——实现时大幅扩展（trigger 全是 MCP 侧新增；derived 从 16 扩到 48）
- **41 处规则重名的来源找到了**：yaml 侧 4 条"-仓库粒度"下卷规则带消歧后缀；实现扩展到多实体（SKUInWarehouse/ProductCategoryInWarehouse/InventoryInWarehouse 三层各一份）时**统一丢了后缀**，复制成同名（如「未到货采购量」×3、「仓库编码」×10）。
- 同名规则交集仅 12 条。

## 四、结论与建议（修正此前"独立漂移"的判断）

1. **关系模型**：yaml（设计稿）→ 人工翻译 → MCP 注册表（实现）。差异三类：①合理实现扩展（主键/冗余字段/trigger/正式命名）；②**实现引入的错误**（InventoryRisk 错名、41 处丢后缀重名）；③双向演进不同步（yaml 改了没重写 MCP，MCP 扩了没回写 yaml）。
2. **修缮方向**（对应 docs/fnb-engine-fix-handoff.md）：
   - MCP 侧修 2 处错误：InventoryRisk 名字（正确值就在 yaml）；41 处规则重命名（参照 yaml 的后缀消歧法）
   - **建立 yaml→MCP 一致性校验闭环**：每次 yaml 变更后跑 `export_dsl`（MCP→DSL）与 yaml 的对比（本项目 diff_model 可直接承担），把"翻译走样"拦在发布前
3. **source of truth 确认为 yaml（设计稿）**——MCP 注册表应视为 yaml 的编译产物管理；长期可把"yaml→注册表"从人工翻译升级为工具生成（ontology-forge 的 compile 链路）。
