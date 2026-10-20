# aquilair-ontology 插件工程仓

> Ontology Forge——LLM 辅助本体元数据设计插件（ZCode）。定位：与 FDE 自然语言交互，产出"给人看的拓扑图 + 给导入用的 yaml"。

## 目录职责（资产三类分离）

| 目录 | 职责 | 资产类别 |
|---|---|---|
| `plugins/ontology-forge/` | **插件源**（技能/脚本/规范/种子/手册）+ `plugins/marketplace.json`（本地市场） | 发布产物 |
| `plugins/ontology-forge/seeds/` | **插件自带资产**：受控词表（glossary）、既有域速查（fnb/mfg）、行业模板——**随使用持续进化**（每个域定稿后自动回流增长） | 种子资产 |
| `models/<domain>/` | **运行时业务资产**：各业务域的 DSL/设计稿/拓扑图/平台 yaml/问询单/资料包——插件生产的数据 | 运行资产 |
| `evals/` | 回归测试（行为样例 + 机械断言，改插件必跑） | 工程资产 |
| `docs/` | 设计决策记录（方案/调研/对照报告/转交文档）——插件为什么这样设计 | 工程资产 |
| `poc/` | M0 验证资产（round-trip/盲测基准，格式演进的对账锚点） | 工程资产 |
| `workbuddy/` | WorkBuddy 构建产物区（`pack_workbuddy.py` 生成的上传 zip，可随时重建） | 构建产物 |

## 资产流转规则

```text
新域（空白）──安装插件后零准备开工──→ models/<domain>/ 自动初始化标准资产树
    │                                        │ 流水线九步 + 三个确认点
    │                                        ▼
    │                                  域定稿（人审通过）
    │                                        │
    │                    ┌───────────────────┼───────────────────┐
    │                    ▼                   ▼                   ▼
    │          seeds/glossary.md      seeds/<domain>-entities.md   知识库沉淀（可选）
    │          （命名登记，重跑/       （域速查，增量与跨域          （口径/术语进
    │            增量自动复用）          对齐的资产参照）              aquilair-knowledge）
    └── 种子越用越厚 → 下一个域/下一次增量"起点不为零" → 插件与技能随使用进化
```

- **运行资产入库**：域定稿后的 `models/<domain>/` 提交共享（团队资产）；draft 过程态可本地暂存
- **种子是唯一分发资产**：随插件分发；`seeds/` 的任何增长都意味着插件能力的进化（记得升版本号）
- **同域更新走增量**（target_engine 指向既有域），禁止从零重跑（命名漂移防护，glossary 是数据源）

## 分发（给别的智能体用）

**分发单元 = `plugins/ontology-forge/` 一个目录**（自包含：多平台清单+技能+总控提示词+脚本+种子+头像），仓库其余部分是工厂资产不分发。**单内容多清单架构**：插件内容只有一份，四个平台清单并存引用（`.zcode-plugin` / `.codebuddy-plugin` / `.claude-plugin` / `.codex-plugin`，版本保持一致），不存在镜像/平移——改任何内容直接改插件根，然后按目标平台安装。

| 目标智能体 | 清单 | 安装方式 |
|---|---|---|
| ZCode | `.zcode-plugin/plugin.json` | 插件市场添加 `plugins/marketplace.json` 后安装 |
| WorkBuddy | `.codebuddy-plugin/plugin.json` | 开放平台上传 `workbuddy/aquilair-fde-<版本>.zip`（`python plugins/ontology-forge/scripts/pack_workbuddy.py` 构建，含 scripts/——WorkBuddy 有 Bash 可直接执行） |
| Claude Code | `.claude-plugin/plugin.json` | `/plugin marketplace add <仓库>/plugins` 后安装 |
| Codex | `.codex-plugin/plugin.json` | `codex plugin marketplace add <仓库>/plugins` 后安装 |

**发布门禁**：`python plugins/ontology-forge/scripts/check_dist.py`——四清单版本一致、WorkBuddy 清单 16 项合规、agent frontmatter 必填、SKILL.md frontmatter、zip 结构与版本新鲜度逐项断言，任一失败退出码 1（先跑 `pack_workbuddy.py` 再跑门禁做发布前全检）。

其他平台整目录分发：`git archive HEAD plugins/ontology-forge -o ontology-forge-<版本>.zip`。运行依赖：Python 3.10+ 与 pyyaml（图片另需 Playwright）。

## 快速链接

- 使用手册：`plugins/ontology-forge/docs/user-guide.md`
- DSL 规范（格式权威）：`plugins/ontology-forge/skills/ontology-modeling/references/dsl-spec.md`
- 回归：`cd evals/ontology-modeling && python run_evals.py`（改插件必跑，当前 20 断言）
