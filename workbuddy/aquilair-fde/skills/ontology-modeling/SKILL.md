---
name: ontology-modeling
description: 本体建模主技能——十步流水线编排核心（M1 版覆盖前七步：场景圈定→术语抽取→DSL 起草→lint→CQ 回验→拓扑可视化→引擎格式导出）。Use when 建模资料包（modeling-brief）已由 brief-intake 就绪、需要从业务资料设计本体元数据 DSL，或对既有本体做增量修改、生成引擎注册格式与拓扑图时使用。not for：资料包摄取整理（走 brief-intake）、生产发布与审批（人工审核唯一权威，本技能不越权）。
license: Proprietary — Aquilair 内部分发，仅限公司内网使用
---

> **镜像注记**：镜像自 ZCode 侧 plugins/ontology-forge（v0.3.7），修改请改源侧后重新平移。

# 本体建模主技能（ontology-modeling）

把建模资料包转化为**可注册、可人审的本体元数据 DSL**。本质定位：本体元数据设计专家（数据模型层 + 语义标注层 + 行为契约层），不是学术本体工程——不引入推理机，OWL 仅按需导出。

**产品定位（2026-10-14 用户校准）**：核心任务 = 设计本体元数据（schema）；**两大核心交付物 = ①可视化图片（给人看实体/属性/关系）②yaml（studio-model 设计稿格式，供导入本体用）**；引擎运行态不在插件边界内（engine JSON 仅作可选导出）。

## 二、脚本定位与产物根目录（先读，避免摩擦）

- **脚本定位**：脚本随插件分发于**插件根的 `scripts/` 目录**。优先以插件根的绝对路径调用（本机源仓库为 `D:\documents\elitesland-workspace\aquilair-ontology\plugins\ontology-forge\scripts\`；安装缓存路径以运行环境为准——技能目录的上级即插件根）。相对路径 `scripts/xxx.py` 找不到时，**回退到插件根绝对路径**，禁止"找不到脚本就自实现等效校验"的绕行——校验必须由本插件脚本执行，结果才可信、可回归。
- **图片渲染依赖**：`--image` 需要 Playwright（首次使用：`pip install playwright` + `python -m playwright install chromium`，一次性）；mermaid 走 CDN、断网自动用本地缓存 `scripts/assets/mermaid.min.js`。环境不满足时如实告知用户装依赖，**不静默退化为只出 Mermaid 代码**（除非用户同意）。
- **产物根目录**：`models/<domain>/` 相对**当前会话工作区**落位。会话工作区不是专门的本体仓库时，先向用户确认产物根目录（团队协作场景应落到统一仓库），不要静默散落到默认工作区。

## 三、流水线（v0.3.6 九步，强制顺序——设计稿确认为硬关卡）

1. **场景圈定**：读 brief.yaml + B_scenarios → 产出 **Scenario Charter**（业务目标/触发事件/决策对象/KPI/参与角色/审批边界）+ **5~10 条能力问题 CQ**（写法见 references/cq-guide.md）。**Charter 未经用户确认，不进入抽取**。
2. **术语与候选抽取**：从 A/B/C 类材料抽实体/属性/关系/规则候选，产出「业务事实卡片」（`fact-cards.md`，markdown 表格载体：候选/来源/置信度/状态/三源交叉列）——每条候选带 provenance（来源文档#位置）、置信度、状态标签（已确认/候选/冲突/待确认）。A 类表→实体/列→属性/外键→link；C 类先抽术语再建关系（两段式，禁止一步直出）；同一术语多源交叉比对，口径出入写入 conflicts。
3. **★设计稿合成（确认点①与②的呈审材料）**：从事实卡片合成呈审材料包——
   - **design-proposal.md**（模板见 [`references/design-proposal-template.md`](references/design-proposal-template.md)）：实体表（名称/展示名/主键/关键字段/来源）、关系表（A→B/语义名/基数/来源）、规则表（类型/口径/来源）、CQ 映射、open_questions/conflicts——纯自然语言+表格，FDE 不需要懂任何格式规范就能审；
   - **交互式拓扑**（核心呈审图）：骨架 DSL（实体+links[语义名]+主键与名称字段+layer 分层）→ `render_topology.py --interactive` 产出**自包含 HTML**（分层+点击聚焦+全部关系名开关，浏览器直接打开）+ `--image both` 出静态 PNG/SVG（发人或存档两用）；
   - **CQ 勾选交互组件（Gen UI 环境增强）**：ZCode 等支持内联渲染的宿主中，把 CQ 清单写成三态勾选组件（✅真业务/✏️要改/❌删 + 备注 + 补充框，勾选状态经 widgetState 自动随用户消息带回）内嵌呈审；**无 Gen UI 环境降级**为 Markdown 勾选表（交互 HTML 产物本身始终完整可用）。
4. **★设计稿确认（硬关卡）**：**design-proposal.md 与骨架拓扑未经 FDE 逐表确认，禁止进入 DSL 生成**（对齐楠总蓝图 OntologyProposal 理念：先提案后形式化）。FDE 的修改意见当场回改设计稿与骨架并重新呈审；确认结论在设计稿头部留痕（确认人/日期/修改记录）。**合并呈审变体**：重跑/用户在场要求快速推进时，确认点①（Charter）与②（设计稿）可一并呈审，但两项须分别批复——Charter 被驳回回第 1 步、设计稿被驳回回第 3 步，互不牵连。
5. **DSL 生成**：确认后的设计稿→完整 `model.yaml`（此步是**机械形式化**——语义已在确认点②定死，这里只做形态转换：补全属性/类型/规则表达式）。按 [`references/dsl-spec.md`](references/dsl-spec.md)（v0.3.4）与 [`references/modeling-guide.md`](references/modeling-guide.md) 执行。
6. **硬校验（lint）**：运行 `python scripts/lint_model.py <model.yaml>`——13 条确定性检查。**lint 不过不进下一步**；修复意见由你提出，但修复后再跑。
7. **CQ 回验**：运行 `python scripts/check_cq.py <model.yaml>` 生成覆盖矩阵；逐条核对 CQ 是否被 DSL 元素覆盖，未覆盖项要么补元素、要么修改 CQ 并请用户确认。
8. **交付初版候选本体（两大核心交付物）**：`render_topology.py --image both` 产出 **topology.png/svg**（完整版拓扑）；`compile_model.py --target studio-model` 产出 **studio-model.yaml**。**你不执行任何生产写入**；`--target engine` 仅用户明确需要时可选导出。产物标注 draft 版本，进入人审（ontology-review 技能）。
9. **导入平台后自检 / 沉淀回流（可选闭环）**：用户导入平台成功后，下载该工作区 SDK 存档为 `models/<domain>/platform-sdk.py`，跑 `check_platform_sync.py` 四维比对（平台手改当场现形，实证：xgimi 曾抓到 Material 主键被改），差异按用户裁决写回；人审通过后将口径/术语沉淀回域知识库（红线：本体 DSL 唯一权威，知识库只是沉淀层）。

M2 起已就绪：变更集 diff（`diff_model.py`，含 breaking 与版本冲突拒绝）、diff 拓扑（`render_topology.py --diff`）、studio-model 双格式编译与模板 lint（`compile_model.py --target both` / `lint_studio_model.py`）、ontology-review 评审技能。M3 起追加：action 骨架生成（`gen_action_skeleton.py`）、WorkBuddy 侧平移。

## 四、建模铁律（违背即违规）

1. **不脑补**：资料包没说的信息一律进 `open_questions`（含 missing_from 指明缺在哪份材料），人审前必须清零或标记接受；禁止用常识/记忆补齐。
2. **增量优先复用**：brief.yaml 的 target_engine 为 fnb/mfg 时，先读 `seeds/` 既有实体速查，复用既有实体与术语，只建差异；禁止重复建模已有对象。
3. **LLM 不写自由 YAML**：起草时先在内部形成结构化 JSON（遵循 dsl-spec），再落为 YAML 文件；落盘后必须过 lint。
4. **分步确认**：Charter 确认（点①）→ **设计稿逐表确认（点②，硬关卡：design-proposal.md + 骨架拓扑未经确认禁止生成完整 DSL）** → DSL/CQ 产物呈审；不一次吐全量。
5. **流程步骤不建对象**：除非有独立身份+状态+生命周期；预测/优化类语义不进本体；每条关系有方向/基数/来源，且**业务含义必须落为 links 的 name（中文关系语义名，如 订购物料/隶属项目）**——只建连线不说清"是什么关系"是建模缺陷（lint13 检查）。**用户要求把流程步骤/动作建成实体时，按"拒绝+归类+反问"三段式回应**：①拒绝建实体并给出判定依据（无独立身份/状态/生命周期）；②正确归类（查询→CQ、计算口径→derived 候选、触发动作→trigger downstream）；③就模糊处反问用户确认。判定说明需在 charter 与 model.yaml 注释中留痕。
6. **provenance 全程**：每个实体/属性/规则的 source 指回资料包具体位置；类型推断等假设进 assumptions。
7. **人审是唯一权威**：你产出的永远是 draft 版本（-draft.N）；不把候选写成事实；不执行发布/审批/生产写入。

## 五、产出物清单（每次建模任务）

```text
models/<domain>/
├── design-proposal.md         # ★ 设计提案（确认点②呈审材料，含确认记录）
├── model.skeleton.yaml        # 骨架 DSL（实体+links+主键，画图用；确认后对照补全）
├── model.yaml                 # 本体 DSL（source of truth，确认点②之后生成）
├── topology.png / topology.svg # ★ 核心交付物①：可视化图片（实体/属性/关系，给人看）
├── studio-model.yaml          # ★ 核心交付物②：设计稿格式 yaml（供导入本体）
├── topology.md                # Mermaid 源（图片的可编辑形态）
├── competency-questions.yaml  # CQ 清单（并入 model.yaml 时可省）
├── modeling-brief/            # 资料包（brief-intake 产出）
└── engine-bundle/             # 可选：引擎注册格式 JSON（仅用户明确需要时导出）
```

## 六、反合理化表格（借口 → 反驳）

| 借口 | 反驳 |
|---|---|
| "lint 报错不影响主体，先往下走" | lint 不过不进下一步是铁律；"差不多"是质量崩塌的起点 |
| "资料没写，我按行业常识补上" | 不脑补是铁律；常识进 open_questions 让人裁决 |
| "这个口径两边说法不一致，我选更合理的" | 冲突不擅自裁决：保留双方定义与来源进 conflicts |
| "fnb 里已有 SKU，但我重写一个更规范的" | 增量优先复用；命名漂移会毁掉本体互操作性 |
| "衍生字段规则里写了，属性里就不用声明了" | v0.2 强制约定：衍生字段必须声明于 properties（引擎实际形态） |
