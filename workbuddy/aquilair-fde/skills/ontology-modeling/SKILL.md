---
name: ontology-modeling
description: 本体建模主技能——十步流水线编排核心（M1 版覆盖前七步：场景圈定→术语抽取→DSL 起草→lint→CQ 回验→拓扑可视化→引擎格式导出）。Use when 建模资料包（modeling-brief）已由 brief-intake 就绪、需要从业务资料设计本体元数据 DSL，或对既有本体做增量修改、生成引擎注册格式与拓扑图时使用。not for：资料包摄取整理（走 brief-intake）、生产发布与审批（人工审核唯一权威，本技能不越权）。
license: Proprietary — Aquilair 内部分发，仅限公司内网使用
---

> **镜像注记**：镜像自 ZCode 侧 plugins/ontology-forge（v0.3.1），修改请改源侧后重新平移。

# 本体建模主技能（ontology-modeling）

把建模资料包转化为**可注册、可人审的本体元数据 DSL**。本质定位：本体元数据设计专家（数据模型层 + 语义标注层 + 行为契约层），不是学术本体工程——不引入推理机，OWL 仅按需导出。

## 二、脚本定位与产物根目录（先读，避免摩擦）

- **脚本定位**：4 个脚本随插件分发于**插件根的 `scripts/` 目录**。优先以插件根的绝对路径调用（本机源仓库为 `D:\documents\elitesland-workspace\aquilair-ontology\plugins\ontology-forge\scripts\`；安装缓存路径以运行环境为准——技能目录的上级即插件根）。相对路径 `scripts/xxx.py` 找不到时，**回退到插件根绝对路径**，禁止"找不到脚本就自实现等效校验"的绕行——校验必须由本插件脚本执行，结果才可信、可回归。
- **产物根目录**：`models/<domain>/` 相对**当前会话工作区**落位。会话工作区不是专门的本体仓库时，先向用户确认产物根目录（团队协作场景应落到统一仓库），不要静默散落到默认工作区。

## 三、流水线（M1 版七步，强制顺序）

1. **场景圈定**：读 brief.yaml + B_scenarios → 产出 **Scenario Charter**（业务目标/触发事件/决策对象/KPI/参与角色/审批边界）+ **5~10 条能力问题 CQ**（写法见 references/cq-guide.md）。**Charter 未经用户确认，不进入抽取**。
2. **术语与候选抽取**：从 A/B/C 类材料抽实体/属性/关系/规则候选，产出「业务事实卡片」（JSON）——每条候选带 provenance（来源文档#位置）、置信度、状态标签（已确认/候选/冲突/待确认）。A 类表→实体/列→属性/外键→link；C 类先抽术语再建关系（两段式，禁止一步直出）；同一术语多源交叉比对，口径出入写入 conflicts。
3. **DSL 起草**：按 [`references/dsl-spec.md`](references/dsl-spec.md)（v0.2）生成 `model.yaml`。命名与结构规范见 [`references/modeling-guide.md`](references/modeling-guide.md)；资料包模板与各输入管线的处理策略见 [`references/input-templates.md`](references/input-templates.md)。
4. **硬校验（lint）**：运行 `python scripts/lint_model.py <model.yaml>`——8 条确定性检查（schema 合法/主键/links 闭合/表达式静态检查/trigger 结构/衍生字段一致性/外键-links 一致性）。**lint 不过不进下一步**；修复意见由你提出，但修复后再跑。
5. **CQ 回验**：运行 `python scripts/check_cq.py <model.yaml>` 生成覆盖矩阵；逐条核对 CQ 是否被 DSL 元素覆盖，未覆盖项要么补元素、要么修改 CQ 并请用户确认。
6. **拓扑可视化**：运行 `python scripts/render_topology.py <model.yaml>` 产出 Mermaid classDiagram（topology.md），随 DSL 一并呈给用户。
7. **引擎格式导出（一期导入方式）**：运行 `python scripts/compile_model.py <model.yaml>` 产出引擎注册格式 JSON + 导入说明；人工审核通过后由平台侧注册。**你不执行任何生产写入**。
8. **沉淀回流（M3 起可选，人审通过后执行）**：将本次建模的可复用知识沉淀到域知识库（`aquilair-knowledge/sources/<域名>/`，无对应域则提示用户先建）——口径定义与冲突裁决进 glossary/analyses（好答案归档），新术语同义词映射补进 glossary。**红线不变**：本体 DSL 是唯一权威，知识库只是沉淀层；回流内容须注明来源为本体 `<domain>@<version>`，后续本体演进以 DSL 变更集为准（知识库发现过时走其再摄取流程）。

M2 起已就绪：变更集 diff（`diff_model.py`，含 breaking 与版本冲突拒绝）、diff 拓扑（`render_topology.py --diff`）、studio-model 双格式编译与模板 lint（`compile_model.py --target both` / `lint_studio_model.py`）、ontology-review 评审技能。M3 起追加：action 骨架生成（`gen_action_skeleton.py`）、WorkBuddy 侧平移。

## 四、建模铁律（违背即违规）

1. **不脑补**：资料包没说的信息一律进 `open_questions`（含 missing_from 指明缺在哪份材料），人审前必须清零或标记接受；禁止用常识/记忆补齐。
2. **增量优先复用**：brief.yaml 的 target_engine 为 fnb/mfg 时，先读 `seeds/` 既有实体速查，复用既有实体与术语，只建差异；禁止重复建模已有对象。
3. **LLM 不写自由 YAML**：起草时先在内部形成结构化 JSON（遵循 dsl-spec），再落为 YAML 文件；落盘后必须过 lint。
4. **分步确认**：实体清单先确认再展开属性；规则口径逐条带来源呈报；不一次吐全量。
5. **流程步骤不建对象**：除非有独立身份+状态+生命周期；预测/优化类语义不进本体；每条关系有方向/基数/业务含义/来源。
6. **provenance 全程**：每个实体/属性/规则的 source 指回资料包具体位置；类型推断等假设进 assumptions。
7. **人审是唯一权威**：你产出的永远是 draft 版本（-draft.N）；不把候选写成事实；不执行发布/审批/生产写入。

## 五、产出物清单（每次建模任务）

```text
models/<domain>/
├── model.yaml                 # DSL（source of truth）
├── competency-questions.yaml  # CQ 清单（并入 model.yaml 时可省）
├── topology.md                # Mermaid 拓扑
├── engine-bundle/             # 编译产物（引擎注册格式 JSON + 导入说明）
└── modeling-brief/            # 资料包（brief-intake 产出）
```

## 六、反合理化表格（借口 → 反驳）

| 借口 | 反驳 |
|---|---|
| "lint 报错不影响主体，先往下走" | lint 不过不进下一步是铁律；"差不多"是质量崩塌的起点 |
| "资料没写，我按行业常识补上" | 不脑补是铁律；常识进 open_questions 让人裁决 |
| "这个口径两边说法不一致，我选更合理的" | 冲突不擅自裁决：保留双方定义与来源进 conflicts |
| "fnb 里已有 SKU，但我重写一个更规范的" | 增量优先复用；命名漂移会毁掉本体互操作性 |
| "衍生字段规则里写了，属性里就不用声明了" | v0.2 强制约定：衍生字段必须声明于 properties（引擎实际形态） |
