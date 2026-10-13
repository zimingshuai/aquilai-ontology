# 自动化本体建模插件调研报告

> 调研日期：2026-09-24 ｜ 场景：技术方案设计（资料搜集 + 选型）
> 约束：从零设计，不复用既有 MCP 本体引擎；交付形态为 ZCode（Claude Code 兼容）插件

## 一、结论（TL;DR）

1. **LLM 自动本体建模样式已收敛，但共识是"半自动 + 人审"，不是端到端黑盒**。2024–2026 年综述与高引论文（Kommineni 2024，228 引用）一致采用：任务分解流水线（术语抽取 → 概念/关系 → schema 生成）+ 裁判模型（judge LLM）辅助评估 + 评估环节人工把关。完全自动化被明确判定为不可靠。
2. **不要自研建模 DSL，直接采用 LinkML**（YAML 声明式建模语言，开源成熟）：一个 schema 可编译出 JSON Schema / OWL / Python 类 / SQL DDL / SHACL 等多目标产物，自带校验器；且 LLM 训练语料中 LinkML 语料充足，生成质量有保障。
3. **评估锚点用能力问题（Competency Questions, CQ）**：这是本体工程 20 年来的主流任务型评估法——建模前先写"本体应能回答的问题清单"，建完逐条验证覆盖。CQ 同时是智能体流水线的"需求规格"与"回归测试用例"，一物两用。
4. **从 DDL/关系库建本体是成熟研究方向**（经典半自动方法 → 2025 年 RAG+LLM 方法）：表→类容易，**关系语义标注与命名是公认难点**，需要受控词表 + lint 治理。
5. **Palantir Foundry 证实两点：本体应是"操作型"三件套（Object 名词 + Action 动词 + Derived Property 逻辑），且其官方 API 至今对 schema 只读、无自动建模能力**——自动建模即使在 Palantir 生态也是空白区。其社区设计原则帖提供了大量可直接落成 lint 的企业级硬规则（主键/外键/命名/治理字段）。
6. **插件结构标准已明确**（本地 plugin-creator/zcode-guide 调研）：`.zcode-plugin/plugin.json` + skills/commands/agents/hooks + 可选 `.mcp.json`，开发遵循 plugin-creator 六步流程。

## 二、背景与调研问题

目标：开发一个自动化本体建模的 ZCode 插件。围绕五个子问题调研：

- Q1 本体工程的成熟方法论是什么（自动化它之前先了解它的手工形态）？
- Q2 LLM 时代自动本体构建做到了什么程度、什么范式？
- Q3 有哪些现成的声明式建模语言与工具链可以复用？
- Q4 怎么评估一个自动建出来的本体的质量？
- Q5 ZCode 插件的标准结构与开发流程是什么？

## 三、问题与解法

**手工本体建模的痛点**：高度依赖领域专家 + 本体工程师协作，周期以周/月计；术语口径不一致；模型质量难以客观评估；文档与模型脱节。传统工具（Protégé 等）解决"编辑"不解决"从零想清楚"。

**业界的解法演进**：
- 方法论层（1997–2008，仍是现行标准）：OD101 七步法（定域→复用→术语→类层级→属性→槽面→实例）与 METHONTOLOGY 生命周期（规范→概念化→形式化→实现→维护）被 NeOn 场景化框架（复用/融合/协作 9 场景）扩展。Bravo 2019 比较研究结论：METHONTOLOGY 与 NeOn 最完整。
- 自动化层（2008–2023）：Ontology Learning——从文本/数据库半自动抽取，RDB→OWL 映射有经典方法（Spanos 269 引用）。
- LLM 层（2023–2026）：任务分解 + prompting 成为主流（LLMs4OL 基准范式）；Kommineni 2024 提出代表性半自动流水线（CQ → TBox 本体 → ABox 填充 → 评估，judge LLM 打分，人审收尾）；2025 年出现 RAG 从关系 schema 生成本体。

## 四、核心发现

### Q1 方法论（自动化流水线的蓝本）

- OD101 七步：①确定领域与范围（产出 CQ）②考虑复用既有本体 ③枚举重要术语 ④定义类与层级 ⑤定义属性/槽 ⑥定义槽面（取值类型/基数/定义域）⑦创建实例。[Keet 教材](https://eng.libretexts.org/Bookshelves/Computer_Science/Programming_and_Computation_Fundamentals/An_Introduction_to_Ontology_Engineering_(Keet)/06%3A_Methods_and_Methodologies/6.01%3A_Methodologies_for_Ontology_Development)（稳定经典）
- METHONTOLOGY 五阶段：specification / conceptualization / formalization / implementation / maintenance；被 NeOn 扩展。[NeOn D5.4.1](https://research-archive.stem.open.ac.uk/stemra-data/uploads/sites/136/2025/03/NeOn_2008_D5.4.1.pdf)（2008，经典）
- 对决策的意义：**插件流水线应显式对齐这些阶段**（尤其"规范先行、复用检查、评估内建"），让智能体执行的是学界验证过的方法论，而不是即兴发挥。

### Q2 LLM 自动建模范式（2024–2026）

- 综述：[Li et al. 2025, Semantic Web Journal（53 页）]；[Perera et al. 2024]；Manchester 团队综述。共同主题：任务分解（术语抽取/分类关系学习/公理生成）、prompting 优于 fine-tuning（工程成本低）、端到端生成是新兴方向但评估不足。
- [Kommineni et al. 2024（arXiv:2403.08345，228 引用）](https://arxiv.org/abs/2403.08345)：CQ 提出→基于 CQ 开发本体（TBox）→构建 KG（ABox）→评估；开源 LLM + RAG + judge LLM 对照 ground truth 打分。**结论：评估环节必须 human-in-the-loop，完全自动化不可靠**。（注：仅核实到摘要级，七阶段细节未逐条核实）
- [van Cauter et al. 2024（ACL）]：LLM + human-in-the-loop 预标注，代码与 prompt 开源。
- 对决策的意义：**流水线分步 + judge 评估 + 人审门**是被验证的架构；judge LLM 打分模式可直接抄。

### Q3 工具链（选型）

| 候选 | 定位 | 优势 | 劣势 |
|---|---|---|---|
| **LinkML**（推荐） | YAML 声明式 schema/本体建模框架 | 生成器生态：JSON Schema/OWL/Python/SQL DDL/SHACL/RDFS；自带校验器；电子表格导入；学术维护活跃（2025 论文） | 语义网倾向，企业动作/行为语义（action）不原生，需扩展约定 |
| OWL + Protégé 直接写 | 传统语义网路线 | 表达力天花板最高 | XML/RDF 序列化对 LLM 生成与人审 diff 不友好，工具链重 |
| 自研 DSL | 完全可控 | 贴合业务 | 造轮子：校验器/生成器/文档全要自己写，且 LLM 不熟悉、生成质量差 |

- LinkML 关键事实：[Moxon et al. 2025 论文（PMC）](https://pmc.ncbi.nlm.nih.gov)；[官方 generator 文档](https://linkml.io)（**未核实**：官方文档访问超时，生成器清单经 PMC 论文 + Apache Ossie GitHub + 社区博客三源交叉，方向可信，细节需 POC 时逐一确认）。
- 佐证 LLM+LinkML 契合度：[OntoGPT（Monarch Initiative）](https://github.com/monarch-initiative/ontogpt) 用的正是"LinkML schema 约束 LLM 抽取"（SPIRES 方法，[Caufield 2024，253 引用](https://pmc.ncbi.nlm.nih.gov)），证明该组合在生产级科研工具中已跑通。

### Q4 评估方法

- [能力问题 CQ（Amith 2018 综述，155 引用）]：任务型评估主流——建模前定义"本体应能回答的问题"，建完逐条验证。Monfardini 等实证 CQ 能发现建模缺陷。
- 其他流派：gold-standard 对比、应用型测试（在下游应用中用）、指标型（一致性/覆盖率等）。
- 对决策的意义：**CQ = 需求规格 + 验收用例 + 回归测试**，插件应把"CQ 清单"作为强制产物，每个本体随附一个 `competency-questions.yaml`。

### Q5 从 DDL/RDB 建本体（企业场景主输入）

- 经典：[Spanos et al.（269 引用）]半自动 RDB→本体；[2023 综述]。
- 最新：[2025 arXiv：RAG + LLM 从关系 schema 生成 OWL]。
- 公认难点：**表→类映射容易；外键关系的语义标注（1:1/1:n/组合/继承）与业务命名难**——这正是 lint + 受控词表 + 人审要守的关口。
- 商业参照：[timbr.ai]（SQL 本体/知识图谱，佐证该需求真实存在且有市场）。

### Q6 Palantir Foundry Ontology（企业级标杆，2026-09-24 补充调研）

**组件模型（不用 W3C 标准，自有表示）**：
- **Object Type**：现实实体/事件的 schema 定义，背靠 backing dataset；要求唯一稳定非空的 primary key。
- **Link Type**：对象间关系（一对一/一对多等）。
- **Action Type**：对对象的写操作（写/编辑/审批），强制校验逻辑与安全检查，可配 submission criteria（准入）与 Revert。
- **Derived Property**：表达式/函数实时计算的属性，不落存储。
- 建模 UI 为 Ontology Manager；声明式开发走 Modeling Objectives（FMO，旧称 NMO）；支持 Ontology working state 导出/导入做环境流转。
- **Platform SDK 对 ontology schema 只有读操作，创建/修改 schema 是开放 feature request（2026-01 仍未实现）**；AIP Assist 能辅助生成代码/pipeline/artifact，但没有官方"自动生成 object types"能力。[Palantir 官方文档](https://palantir.com/docs)、[OSDK 博客](https://blog.palantir.com)（2024–2026，现行）

**官方设计原则一手来源**（[Ontology and Pipeline Design Principles，Palantir 员工 aszekely 的社区帖](https://community.palantir.com/t/ontology-and-pipeline-design-principles/5481)，2025-11）：
- 定位：**本体是组织的 API**（工程师/业务用户/AIP agent 的共享层），由三类组件构成：决策所需数据（名词）、记录决策的动作（动词）、评估决策的逻辑。
- 设计方法（决策驱动）：先描述"用户要做什么决策、依据什么信息"→ 名词与动词即 Object 与 Action → 检查既有本体复用 → **占位/mock 数据起草** → 前端（假数据建对象与应用）与数据工程（接真实数据）并行 → 高频业务反馈。
- **主键/外键硬规则（原文 "No exceptions"）**：`id` 列必须 string；必须内在唯一（仅依赖对象自身属性，不可为排序/运行时 uuid）；必须有独立 `id` 主键列；外键命名 `{foreign_object_type}_id`；组合 id 不做哈希；永不从 id 解析属性。
- 命名规范：映射自然语言业务概念、避免缩写（Aircraft 而非 AC）、避免 `Message_v2` 版本化命名、时间戳 `{verbed}_at_timestamp`、作者 `{verbed}_by_user`、link 用有意义名称（Manager/Direct Report）且复数方向用复数。
- 治理字段：每个对象必配 point of contact；维护 maturity 三态（Experimental/Active/Deprecated）；描述/图标/别名必填；backing dataset 要有调度与健康检查；非必要不开放可编辑。
- 结构规则：最小化属性（可从父对象推导的只标在父对象）；孤立对象是设计不佳信号，但也要避免"蜘蛛网"过度链接；Action 默认关闭 Revert。
- 项目分层模板：Datasource（每源系统一个：清洗/去 PII/健康检查）→ Integration（组表/派生主键）→ Ontology（对象与链接配置）→ Application（工作流应用，多数对象从这里起步再迁移）→ Sandbox（严禁业务数据）；Project 是权限原子单位，角色 OWNER/EDITOR/VIEWER/DISCOVERER。

**对本插件的决策意义**：
1. 目标本体模型应采用 Palantir 式"操作型三件套"（Object/Action/DerivedProperty）而非纯数据 schema——与学术本体（TBox/ABox）相比多了行为与决策语义，这也是 agent 消费所需的（OSDK/AIP 模式：本体告诉 agent"做什么、为什么、接下来发生什么"）。
2. 该帖的 No-exceptions 规则可直接落成 lint 规则集，是插件最有价值的资产之一。
3. "决策驱动起草 + mock 数据 + 复用检查"与学术方法论的 CQ 流程同构（CQ 的企业版=决策+信息需求），两条证据链交叉印证了同一流水线设计。
4. Palantir 官方 schema API 只读、无自动建模 → 自动建模插件的价值空白真实存在。

### Q7 插件标准结构（本地调研，子代理完成）

- manifest 探测顺序：`.zcode-plugin/plugin.json` → `.claude-plugin/plugin.json` → `.codex-plugin/plugin.json`；组件只声明真实存在的；路径不得逃逸插件根。
- 标准结构：`skills/<name>/SKILL.md`（frontmatter: name+description）、`commands/<cmd>.md`、`agents/<agent>.md`、`hooks/hooks.json`、`.mcp.json`（可选）、`marketplace.json`（市场清单，displayName_i18n 等展示字段在市场条目侧）。
- 开发流程：plugin-creator 六步（定义目标与验收样例 → 脚手架/手写 → 验证 → 本地测试市场 → 用户 UI 安装 → 交付状态如实标注）。
- 来源：`C:\Users\zishuai\.zcode\cli\plugins\cache\zcode-plugins-official\plugin-creator\0.1.1\skills\plugin-creator\SKILL.md` 及 references；zcode-guide/diagnosing-plugins；官方插件实例（documents/browser-use/android-emulator 等）。

## 五、风险与信息缺口

- **LinkML 官方文档未直接核实**（超时）：生成器完整清单与 CLI 参数需 POC 时确认；已标注于 Q3。
- **Kommineni 流水线仅摘要级**：七阶段细节（哪两步人审）未逐条核实，方向（评估需人审）可信。
- **LLM 生成 LinkML 的实际质量未验证**：这是整个方案最关键的假设，必须用 POC 先行验证（拿一个已知领域生成 + 对照手写模型）。
- **中文业务资料抽取质量**未调研（检索以英文文献为主）。
- **企业行为语义（action/规则）超出 LinkML 原生范围**：需在 LinkML 之上加自家约定（如 slot 的 `annotations` 声明业务动作），表达力够但无现成编译目标。

## 六、来源清单

| # | 来源 | 类型 | 日期 |
|---|---|---|---|
| 1 | Keet《An Introduction to Ontology Engineering》方法论章 | 教材 | 稳定经典 |
| 2 | NeOn Methodology D5.4.1（open.ac.uk）| 方法论文档 | 2008 |
| 3 | Suárez-Figueroa et al. NeOn 论文（oa.upm.es）| 论文 | 2015 |
| 4 | Bravo 2019 方法论比较（scielo.org.mx）| 论文 | 2019 |
| 5 | Li et al. 2025 LLM for Ontology Engineering 综述（Semantic Web Journal）| 综述 | 2025 |
| 6 | Perera et al. 2024 Exploring LLMs for Ontology Learning | 论文 | 2024 |
| 7 | LLMs4OL（GitHub）| 开源基准 | 2023– |
| 8 | Kommineni et al. arXiv:2403.08345 | 论文（228 引）| 2024-03 |
| 9 | van Cauter et al.（ACL Anthology）| 论文 | 2024 |
| 10 | Spanos et al. Bringing RDB into Semantic Web（269 引）| 论文 | 经典 |
| 11 | RAG of Ontologies from Relational Schemas（arXiv）| 论文 | 2025 |
| 12 | timbr.ai SQL Ontologies | 商业产品 | 现行 |
| 13 | Moxon et al. LinkML 论文（PMC/arXiv）| 论文 | 2025 |
| 14 | linkml.io generators 文档 | 官方文档 | **未核实（超时）** |
| 15 | OntoGPT（github.com/monarch-initiative/ontogpt）| 开源工具 | 现行 |
| 16 | Caufield et al. SPIRES 论文（PMC，253 引）| 论文 | 2024 |
| 17 | Amith et al. 2018 本体评估综述（PMC，155 引）| 综述 | 2018 |
| 18 | Monfardini et al. CQ 实证（inf.ufes.br）| 论文 | — |
| 19 | NIST The Evaluation of Ontologies | 报告 | — |
| 20 | 本地 plugin-creator / zcode-guide skills 及官方插件实例 | 本地规范 | 2026-09-24 子代理核实 |
| 21 | Palantir 官方文档（palantir.com/docs：Ontology 组件、Ontology Manager、AIP、OSDK）| 官方文档 | 现行 |
| 22 | Ontology and Pipeline Design Principles（community.palantir.com/t/ontology-and-pipeline-design-principles/5481，.json 原始端点全文核实）| 社区一手帖 | 2025-11 |
| 23 | Building with Palantir AIP: The OSDK（blog.palantir.com）| 官方博客 | 2024-02 |
| 24 | PuppyGraph / Elementum / timbr 对 Foundry 架构的第三方描述 | 第三方 | 2025–2026 |

## 七、建议下一步

1. **POC 验证核心假设**（1–2 天）：手写一个小领域 LinkML schema 作为 gold standard → 让 LLM 从同一领域的 DDL + 文档生成 → 对照差距。假设不过关则 DSL 选型重议。
2. 按 plugin-creator 六步创建插件骨架，先做最小闭环（lint + 生成 + CQ 校验）。
3. Kommineni 论文全文精读（PDF 可取自 Max Planck 库），补齐流水线阶段细节。
