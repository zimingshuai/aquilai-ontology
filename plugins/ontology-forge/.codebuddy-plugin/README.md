# aquilair-fde（WorkBuddy Expert Plug-in）

Aquilair 本体建模插件（ontology-forge）的 **WorkBuddy 清单**。把新业务域接入本体引擎的时间从"数周手工建模"压缩到"半天人审"：资料摄取 → 场景圈定（CQ）→ DSL 起草 → 硬校验 → 变更集 diff → 引擎注册格式导出 → 人工审核（唯一权威）。

> 骨架来源：楠总 × Codex 蓝图（WorkBuddy Expert Plug-in 规范，2026-09-21~24）。

## 一、单内容多清单架构

插件内容**只有一份**，位于插件根（`plugins/ontology-forge/`），各平台清单并存引用同一份内容，不存在镜像/平移：

| 平台 | 清单 | 安装方式 |
| --- | --- | --- |
| WorkBuddy | `.codebuddy-plugin/plugin.json`（本目录） | 开放平台上传 zip（`scripts/pack_workbuddy.py` 构建于 `workbuddy/`） |
| ZCode | `.zcode-plugin/plugin.json` | 插件市场添加 `plugins/marketplace.json` 后安装 |
| Claude Code | `.claude-plugin/plugin.json` | `/plugin marketplace add <仓库>/plugins` 后安装 |
| Codex | `.codex-plugin/plugin.json` | `codex plugin marketplace add <仓库>/plugins` 后安装 |

共享内容（插件根）：`skills/`（3 技能）、`agents/aquilair-fde.md`（总控提示词）、`avatars/expert.png`、`seeds/`（种子资产）、`docs/`（使用手册）、`scripts/`（校验/编译/diff 脚本——**所有宿主通用**，WorkBuddy 有 Bash 工具可直接执行）。

## 二、WorkBuddy 包结构

zip 内根目录为 `aquilair-fde/`：

```text
aquilair-fde/
├── .codebuddy-plugin/plugin.json   # WorkBuddy 清单（expertType: agent；quickPrompts 恰好 3 条）
├── agents/aquilair-fde.md          # 总控提示词（权威边界/十步流程/建模边界/脚本使用规则/八件套）
├── avatars/expert.png              # 专家头像（512x512，平台必填）
├── skills/                         # 3 技能（brief-intake / ontology-modeling / ontology-review）
├── seeds/                          # 种子资产（glossary / mfg-entities / fnb-entities）
├── docs/user-guide.md              # FDE 使用手册
└── scripts/                        # lint_model / check_cq / render_topology / compile_model 等（Bash 调用）
```

发布前跑 `python plugins/ontology-forge/scripts/check_dist.py`——清单合规、agent frontmatter、zip 结构逐项断言，任一失败退出码 1。

## 三、quickPrompts 规则

WorkBuddy 规范：**quickPrompts 必须恰好 3 条**（多一条少一条都不合规），每条含中英双语字段，与 `defaultInitPrompt` 呼应、覆盖插件的三个主入口场景：

1. **从零起草**：帮我从业务资料开始设计一个可审核的本体草稿 → 走 brief-intake → ontology-modeling 全流水线。
2. **增量差异**：比较当前本体与这份业务方案的差异，只生成变更建议 → 走 diff 变更集（不落盘改写）。
3. **评审校验**：校验/评审当前本体是否支撑目标业务场景 → 走 ontology-review（只出报告不做裁决）。

## 四、二期 Studio MCP 挂接点（预埋，当前未启用）

本插件按一期「本地脚本 + 文件导出」模式运行，**未配置 `dependencies.mcpServers`**——Studio MCP（变更集级 schema 写接口）尚待平台侧交付，属蓝图二期。接口就绪后：

1. 在 plugin.json 增加 `dependencies.mcpServers`，指向 `.mcp.json`（Studio MCP，streamableHttp 或 stdio 按平台交付形态）。
2. `agents/aquilair-fde.md` 标准流程第 7/8/9/10 步从一期文件模式切换为蓝图工具契约：

```text
get_project_context → get_ontology_snapshot → preview_ontology_changeset
→ 用户确认（确认卡） → apply_ontology_changeset → validate_ontology_draft
→ get_ontology_snapshot（回读校验） → submit_ontology_review
```

安全契约（楠总蓝图原文）：`preview` 返回 `change_set_id + content_hash`；`apply` **只接受** `change_set_id + content_hash + base_version`（杜绝预览≠写入）；版本冲突时拒绝并要求重读重生成；不暴露 publish / approve / hard_delete / execute_production_action。

## 五、行为测试样例（源自蓝图，回归断言）

六类样例的断言口径随技能携带（详见仓库根 `evals/`）：从零生成（先 Charter 再本体，不发布）、增量复用（只建差异）、口径冲突（保留双定义不擅自定稿）、版本冲突（apply 被拒重读重生成）、越权请求（拒绝发布引导评审）、错误建模（流程步骤不建伪对象）。
