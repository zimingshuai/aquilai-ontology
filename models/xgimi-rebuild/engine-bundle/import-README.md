# Studio 模板产物（studio-model.yaml）

- 溯源：由 compile_model.py --target studio-model 从 `model.yaml` 编译生成，重新编译会覆盖，请勿手改。本目标不产出引擎注册 JSON（需要时改用 --target engine/both）。

## Studio 模板产物（studio-model.yaml）
- 由同一 DSL 按 dsl-spec §8 编译：实体->object_types、links->link_types（1:n，外键字段取显式 fk，简写取目标主键同名属性）、  derived_property->rule_types（calculation，表达式中文名引用）；code 用 rel_/rule_+md5 稳定 hash，  重复编译字节一致（幂等）。
- 规模：object_types 25 个 / link_types 49 条 / rule_types 11 条。
- **5 条 trigger/admission 规则不进模板**（模板仅承载 calculation，需引擎侧配置）：呆滞风险触发、换料未到货检查、授权数量变化重核算、替代关系变化复核分配、冻结供给排除待核查
