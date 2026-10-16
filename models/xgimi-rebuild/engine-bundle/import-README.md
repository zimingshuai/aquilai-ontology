# Studio 模板产物（studio-model.yaml）

- 溯源：由 compile_model.py --target studio-model 从 `model.yaml` 编译生成，重新编译会覆盖，请勿手改。本目标不产出引擎注册 JSON（需要时改用 --target engine/both）。

## Studio 模板产物（studio-model.yaml）
- 由同一 DSL 按 dsl-spec §8 编译：实体->object_types、links->link_types（1:n，外键字段取显式 fk，简写取目标主键同名属性）、  derived_property->rule_types（calculation，表达式中文名引用）；code 用 rel_/rule_+md5 稳定 hash，  重复编译字节一致（幂等）。
- 规模：object_types 25 个 / link_types 43 条 / rule_types 11 条。
- **2 条 trigger/admission 规则不进模板**（模板仅承载 calculation，需引擎侧配置）：呆滞风险触发、换料未到货检查
- **编译错误（对应元素已跳过，须人工处理后再编译）**：
  - 实体 Demand.links.covered_by 的目标实体 Demand 主键字段数=2（demand_id,record_version），单字段外键约定无法映射，该连线已跳过
  - 实体 Demand.links.supersedes 的目标实体 Demand 主键字段数=2（demand_id,record_version），单字段外键约定无法映射，该连线已跳过
  - 实体 ChangeRecord.links.authorization 的目标实体 MaterialAuthorization 主键字段数=3（project_code,material_code,auth_version），单字段外键约定无法映射，该连线已跳过
  - 实体 AllocationRecord.links.demand 的目标实体 Demand 主键字段数=2（demand_id,record_version），单字段外键约定无法映射，该连线已跳过
  - 实体 SourcingSuggestion.links.ref_list 的目标实体 VendorReferenceList 主键字段数=2（run_id,supplier_code），单字段外键约定无法映射，该连线已跳过
  - 实体 SolutionPlan.links.risk 的目标实体 SlowMovingRisk 主键字段数=2（run_id,material_code），单字段外键约定无法映射，该连线已跳过
