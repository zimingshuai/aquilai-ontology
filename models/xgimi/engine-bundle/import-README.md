# 引擎注册产物（engine-bundle）

- 溯源：由 compile_model.py 从 `model.yaml` 编译生成，重新编译会覆盖本目录文件，请勿手改。

## 文件与引擎注册格式的对应

- `objects.json`：实体注册表，对应本体引擎 `get_meta_objects` 返回结构
  （实体名 -> display_name / table_name / description / properties（display_name / description / data_type / is_primary）/ links）。
- `rules.json`：规则注册表，对应本体引擎 `get_meta_rules` 返回结构
  （rules 列表：rule_type / name / upstream / logic / downstream / description；
  derived_property 的 downstream 固定回填 "Computed Property"）。

## 编译剥离说明（dsl-spec §6）

DSL 自有字段不进入产物：实体级 governance / provenance，属性级 uom / enum_values / source，
顶层 competency_questions / open_questions / conflicts / assumptions（规则仅保留引擎需要的
name 与人审用的 description）。编译内置白名单自查，产物出现引擎格式之外的键即报错终止。

## 导入流程

1. 人工审核本目录两份 JSON（共 26 个实体、18 条规则）与 DSL 的一致性；
2. 审核通过后由平台侧按 `get_meta_objects` / `get_meta_rules` 的注册格式执行注册；
3. 注册结果以引擎快照为准回流（增量建模的 base_version 依据）。

## Studio 模板产物（studio-model.yaml）
- 由同一 DSL 按 dsl-spec §8 编译：实体->object_types、links->link_types（1:n，外键=目标主键同名属性）、  derived_property->rule_types（calculation，表达式中文名引用）；code 用 rel_/rule_+md5 稳定 hash，  重复编译字节一致（幂等）。
- 规模：object_types 26 个 / link_types 39 条 / rule_types 13 条。
- **5 条 trigger/admission 规则不进模板**（模板仅承载 calculation，需引擎侧配置）：呆滞风险触发复核、工程变更预防检查触发、授权数量变化重核算、替代关系变化复核分配方案、冻结供给排除待核查
