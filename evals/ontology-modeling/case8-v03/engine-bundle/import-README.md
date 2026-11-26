# 引擎注册产物（engine-bundle）

- 溯源：由 compile_model.py 从 `fixture-ok.yaml` 编译生成，重新编译会覆盖本目录文件，请勿手改。

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

DSL 自有字段不进入产物：实体级 governance / provenance，属性级 uom / enum_values / source /
derived（引擎侧不区分自然属性与计算属性；studio-model 目标保留为 isDerived），规则级 source，
顶层 competency_questions / open_questions / conflicts / assumptions（规则仅保留引擎需要的
name 与人审用的 description——剥离后 description 是引擎侧唯一语义载体，枚举含义与衍生公式
口径必须已在 DSL 的 description 双写）。编译内置白名单自查，产物出现引擎格式之外的键即报错终止。

## 导入流程

1. 人工审核本目录 JSON 产物（共 4 个实体、6 条规则、1 个动作）与 DSL 的一致性；
2. 审核通过后由平台侧按 `get_meta_objects` / `get_meta_rules` 的注册格式执行注册；
3. 注册结果以引擎快照为准回流（增量建模的 base_version 依据）。

## Studio 模板产物（studio-model.yaml，平台 2026-11 新导入格式）
- 由同一 DSL 编译：实体->object_types、links->link_types（cardinality 按 DSL cardinality 翻转）、  derived_property->calculation（表达式占位符 ${别名.属性code} + expressionSources 逐别名声明  实体与关系路径；自身属性路径为空数组）、trigger->cases/otherwise/with、admission->validation  （when 条件 + failureMessage + 挂载动作 validation_rules）、actions->action_types 声明式步骤；  code 用 rel_/rule_/action_+md5 稳定 hash，重复编译字节一致（幂等）。
- 规模：object_types 4 个 / link_types 3 条 / rule_types 6 条 / action_types 1 个。
- action_types 不写 parameters：平台由步骤中的 $参数 推导（官方口径）。
- admission/validation 规则的实例定位由动作运行时的 instances 提供（DSL lookup 不编进 when，平台侧按动作调用上下文定位实例）。
- **recipe 动作（1 项，需平台侧配置）**：
  - recipe 动作「freeze_supplier」：需平台侧按骨架实现配置（body_ref 见 DSL，引擎注册格式由 --target engine 产物承载）
- **未在 DSL actions 声明（2 项，需平台侧配置）**：
  - 动作「mark_recon_review」被规则引用但未在 DSL actions 声明（平台内置/需平台侧配置），run/挂载引用按 action_<动作名> 推导 code，请人工核对
  - 动作「mark_supplier_frozen」被规则引用但未在 DSL actions 声明（平台内置/需平台侧配置），run/挂载引用按 action_<动作名> 推导 code，请人工核对
