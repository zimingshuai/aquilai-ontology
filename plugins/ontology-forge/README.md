# Ontology Forge —— 本体建模插件（多平台）

> 与 FDE 自然语言协作的本体设计插件：把业务资料（或零文档口述）变成**给人看的拓扑图 + 给 Aquilair 平台导入的 yaml**，全程人审制。版本以 `.zcode-plugin/plugin.json` 为准（四平台清单版本一致）。

## 一、插件是怎么工作的

三个技能接力 + 确定性脚本把关，你只在与你有关的决策点出场：

```text
文档/口述 ──▶ brief-intake ──▶ ontology-modeling（九步流水线）──▶ ontology-review（人审门）
              摄取与探索          ①Charter★ → ②事实卡片 → ③设计稿★（硬关卡）      机器检查先行
                                → ④DSL → ⑤lint+沙盘 → ⑥CQ回验 → ⑦交付          + checklist 评审
                                → ⑧平台导入对账 → ⑨资产回流
```

- **brief-intake**（摄取）：文档判型归位、资料清单、完备度评分、冲突预检；零文档/缺口场景走**八维探索**——少问且带建议问（可补全项批量过、必问项仅 6 条），结论逐条落探索记录 `exploration.yaml`，勾选批复、门禁判定可交接才进建模。
- **ontology-modeling**（主技能）：九步流水线如上；两个硬关卡（Charter 确认点①、设计稿逐表确认点②）之间插件不越权推进；DSL → 平台 yaml 全程机器编译。
- **ontology-review**（评审）：13 类 checklist 逐项带证据评审，只出报告不做裁决。

**你什么时候出场**：确认 brief.yaml → 批复探索勾选页（零文档场景）→ 确认章程与 CQ → **逐表审设计稿（最重要纠错点）** → 裁决待确认问题（OQ）→ 平台导入后看对账报告 → 定稿批准。

## 二、装好后怎么用

30 秒验证：**新开会话**（旧会话不加载新技能）说一句——

| 你说 | 触发 |
|---|---|
| 「我有一份 XX 业务的需求文档和数据字典，帮我建本体」 | 摄取 → 九步流水线（只有 DDL 也能开工） |
| 「这业务连文档都没有，我口头跟你说」 | 八维口述探索 → 勾选确认 → 建模 |
| 「基于现有 XX 本体，新增 YY 场景，只出差异」 | 增量模式（复用既有实体、出变更集与 breaking 标记） |
| 「检查/评审这个本体的质量」「它能支撑 XX 场景吗」 | 评审技能 |

**新手上手最快路径**：通读 `docs/user-guide.md`（详细操作手册）+ 对照 `examples/supplier-recon/`（九步全流程实物范例——每步产物长什么样、追溯链怎么走，看一遍就会）。

## 三、安装（四平台，同一份内容）

| 平台 | 方式 |
|---|---|
| ZCode | Plugin Marketplace → Add → 指向 `plugins/marketplace.json` → 安装 |
| WorkBuddy | 开放平台上传 `pack_workbuddy.py` 构建的 zip（见 `.codebuddy-plugin/README.md`） |
| Claude Code | `/plugin marketplace add <仓库>/plugins` 后安装 |
| Codex | `codex plugin marketplace add <仓库>/plugins` 后安装 |

运行环境：Python 3.10+ 与 PyYAML 必须；L2 语义沙盘另需 `rdflib owlrl pyshacl`；拓扑图 PNG 另需 Playwright（断网自动用插件内 mermaid 缓存）。

## 四、包结构

```text
ontology-forge/
├── skills/
│   ├── brief-intake/             # 摄取技能（references/exploration-guide 探索手册）
│   ├── ontology-modeling/        # 建模主技能（references/dsl-spec = DSL v0.4 格式权威）
│   └── ontology-review/          # 评审技能
├── agents/aquilair-fde.md        # 总控子代理（自动注册；派发约定见 agents/README.md）
├── scripts/                      # 确定性工具链 23 件（清单见 scripts/README.md）：
│                                 #   lint(20条)/语义沙盘/CQ回验/编译(平台新格式)/拓扑渲染/
│                                 #   变更集diff/平台对账(SDK或MCP JSON)/逆向导出(往返字节一致)/
│                                 #   探索门禁+批复写回+勾选页/域交接包/分发门禁/打包
├── examples/supplier-recon/      # 黄金范例（九步全流程实物，受发布门禁机器看守）
├── seeds/                        # 受控词表 + 域速查（随域定稿持续进化，越用越准）
├── docs/user-guide.md            # ★ 使用手册（FDE 版，先读这个）
├── assets/                       # 勾选页模板 + mermaid 离线缓存
└── .zcode-plugin/ 等四平台清单    # 单内容多清单（ZCode/WorkBuddy/Claude Code/Codex）
```

## 五、为什么可以信任产出

- **门禁链**：探索记录门禁（必问项未收口不进建模）→ L1 lint（20 条确定性检查，条数以脚本 docstring 为事实源）→ L2 语义沙盘（OWL/SHACL 语义自洽）→ CQ 回验 → 发布门禁 90 项（含**范例受门禁**：黄金范例与探索记录每次发布前实跑校验，范例漂移=发布失败）。
- **平台对齐**：编译产物对齐平台现行导入规范（官方升级说明实证）；计算规则关系路径**自动推导**（最短且唯一才自动，多条报错不猜）；逆向导出**往返字节一致**（编译→逆向→lint→再编译，回归锁定）。
- **以上不是自述是回归资产**：`evals/ontology-modeling/run_evals.py`（46 项）+ `check_dist.py`（90 项）——改插件必跑，绿灯有据可查。

## 六、文档导航

| 想了解 | 去哪 |
|---|---|
| **怎么用（先读）** | `docs/user-guide.md` |
| 每步产物实物对照 | `examples/supplier-recon/` |
| DSL 语法（格式权威） | `skills/ontology-modeling/references/dsl-spec.md` |
| 探索提问规则 | `skills/brief-intake/references/exploration-guide.md` |
| 脚本工具链清单 | `scripts/README.md` |
| 子代理派发约定 | `agents/README.md` |
| 维护与分发（工厂视角） | 仓库根 `README.md` |

---

许可：Proprietary —— Aquilair 内部分发，仅限公司内网使用。
