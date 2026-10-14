# aquilair-fde（WorkBuddy Expert Plug-in 镜像）

Aquilair 本体建模插件（ontology-forge）在 **WorkBuddy 侧的平移镜像**。把新业务域接入本体引擎的时间从"数周手工建模"压缩到"半天人审"：资料摄取 → 场景圈定（CQ）→ DSL 起草 → 硬校验 → 变更集 diff → 引擎注册格式导出 → 人工审核（唯一权威）。

> 骨架来源：楠总 × Codex 蓝图（WorkBuddy Expert Plug-in 规范，2026-09-21~24）。
> 本目录为 M3 交付物（设计文档 §十三）。

## 一、目录结构

```text
aquilair-fde/
├── .codebuddy-plugin/plugin.json   # WorkBuddy 清单（expertType: agent；quickPrompts 恰好 3 条）
├── agents/aquilair-fde.md          # 总控提示词（权威边界/十步流程/建模边界/脚本使用规则/八件套）
├── skills/                         # 3 技能（镜像自 ZCode 侧，头部带镜像注记）
│   ├── brief-intake/               #   建模统一入口：文档判型归位 + brief.yaml + 缺口报告
│   │   └── references/intake-rules.md
│   ├── ontology-modeling/          #   建模主技能：十步流水线编排
│   │   └── references/（modeling-guide / dsl-spec / input-templates / cq-guide）
│   └── ontology-review/            #   评审技能：12 项 checklist + 变更集影响分析
└── README.md                       # 本文件
```

**scripts/ 不随本镜像分发**：Python 脚本无法在 WorkBuddy 侧插件包内直接分发执行。校验/编译/diff 脚本（lint_model / check_cq / render_topology / compile_model / diff_model / export_dsl 等）从 **ZCode 侧源仓库 `plugins/ontology-forge/scripts/`** 获取（或后续随平台打包机制分发），按插件根绝对路径调用——技能 SKILL.md 内已按此口径表述。

## 二、与 ZCode 侧的关系（源 vs 镜像）

| 侧 | 目录 | 角色 |
| --- | --- | --- |
| ZCode（源，**single source of truth**） | `plugins/ontology-forge/` | 3 技能 + 7 脚本 + seeds + evals，全量开发迭代在此侧进行 |
| WorkBuddy（镜像） | `workbuddy/aquilair-fde/`（本目录） | Expert 形态包装：plugin.json + 总控提示词 + 技能镜像 |

- 镜像侧每份 SKILL.md 头部带注记：`镜像自 ZCode 侧 plugins/ontology-forge，修改请改源侧后重新平移`——**修改一律改源侧，然后重新平移**，禁止双头编辑。
- 与源侧的预期差异仅有两类：镜像注记行、脚本路径的 WorkBuddy 通用表述；除此之外应与源侧逐字一致（可用 `diff -r` 校验）。
- ZCode 侧的 `commands/`（斜杠命令）、`models/`（产物样例）、`seeds/`、`evals/` 不平移——WorkBuddy Expert 用 quickPrompts + 总控提示词承载入口，产物落用户工作区。

## 三、quickPrompts 规则

WorkBuddy 规范：**quickPrompts 必须恰好 3 条**（多一条少一条都不合规），每条含中英双语字段，与 `defaultInitPrompt` 呼应、覆盖插件的三个主入口场景：

1. **从零起草**：帮我从业务资料开始设计一个可审核的本体草稿 → 走 brief-intake → ontology-modeling 全流水线。
2. **增量差异**：比较当前本体与这份业务方案的差异，只生成变更建议 → 走 diff 变更集（不落盘改写）。
3. **评审校验**：校验/评审当前本体是否支撑目标业务场景 → 走 ontology-review（只出报告不做裁决）。

## 四、二期 Studio MCP 挂接点（预埋，当前未启用）

本镜像按一期「本地脚本 + 文件导出」模式运行，**未配置 `dependencies.mcpServers`**——Studio MCP（变更集级 schema 写接口）尚待平台侧交付，属蓝图二期。接口就绪后：

1. 在 plugin.json 增加 `dependencies.mcpServers`，指向 `.mcp.json`（Studio MCP，streamableHttp 或 stdio 按平台交付形态）。
2. `agents/aquilair-fde.md` 标准流程第 7/8/9/10 步从一期文件模式切换为蓝图工具契约：

```text
get_project_context → get_ontology_snapshot → preview_ontology_changeset
→ 用户确认（确认卡） → apply_ontology_changeset → validate_ontology_draft
→ get_ontology_snapshot（回读校验） → submit_ontology_review
```

安全契约（楠总蓝图原文）：`preview` 返回 `change_set_id + content_hash`；`apply` **只接受** `change_set_id + content_hash + base_version`（杜绝预览≠写入）；版本冲突时拒绝并要求重读重生成；不暴露 publish / approve / hard_delete / execute_production_action。

## 五、行为测试样例（源自蓝图，回归断言）

六类样例的断言口径随技能镜像携带（详见 ZCode 侧 `evals/`）：从零生成（先 Charter 再本体，不发布）、增量复用（只建差异）、口径冲突（保留双定义不擅自定稿）、版本冲突（apply 被拒重读重生成）、越权请求（拒绝发布引导评审）、错误建模（流程步骤不建伪对象）。
