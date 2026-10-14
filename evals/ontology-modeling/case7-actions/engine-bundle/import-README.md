# 引擎注册产物（engine-bundle）

- 溯源：由 compile_model.py 从 `gold-actions.yaml` 编译生成，重新编译会覆盖本目录文件，请勿手改。

## 文件与引擎注册格式的对应

- `objects.json`：实体注册表，对应本体引擎 `get_meta_objects` 返回结构
  （实体名 -> display_name / table_name / description / properties（display_name / description / data_type / is_primary）/ links）。
- `rules.json`：规则注册表，对应本体引擎 `get_meta_rules` 返回结构
  （rules 列表：rule_type / name / upstream / logic / downstream / description；
  derived_property 的 downstream 固定回填 "Computed Property"）。
- `actions.json`：动作注册表，对应本体引擎 `get_meta_actions` 返回结构
  （actions 列表：action_name / description / parameters / supports_sandbox / body=骨架源码字符串；body 自各 body_ref 骨架文件读取，业务逻辑由人工插桩后回填编译；
  sandbox_execution 为引擎统一的沙箱执行约定）。

## 编译剥离说明（dsl-spec §6）

DSL 自有字段不进入产物：实体级 governance / provenance，属性级 uom / enum_values / source，
顶层 competency_questions / open_questions / conflicts / assumptions（规则仅保留引擎需要的
name 与人审用的 description）。编译内置白名单自查，产物出现引擎格式之外的键即报错终止。

## 导入流程

1. 人工审核本目录 JSON 产物（共 4 个实体、6 条规则、1 个动作）与 DSL 的一致性；
2. 审核通过后由平台侧按 `get_meta_objects` / `get_meta_rules` 的注册格式执行注册；
3. 注册结果以引擎快照为准回流（增量建模的 base_version 依据）。
