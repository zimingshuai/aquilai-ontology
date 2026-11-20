# Ontology Forge —— 本体驱动业务建模插件（多平台）

> 一套「资料摄取 → 本体建模 → 引擎格式交付」的**人审制**本体设计技能。与 FDE 自然语言协作，从业务资料（或零文档口述）产出**给人看的拓扑图 + 给平台导入的 yaml**。版本以 `.zcode-plugin/plugin.json` 为准（四平台清单版本一致）。

## 一、这个插件能做什么

把一批业务资料（DDL、数据字典、需求/规则/流程文档、访谈记录、既有本体导出——**或只有业务方口述**）变成一套可注册、可人审的本体元数据 DSL，并保证：

- **零资料也能开工**：口述场景走七维对话探索，把问出来的规格当资料（见 user-guide 用法 4）；
- **产出的永远是 draft**：人审是唯一发布权威——三个确认点 + 终审全在人，插件永不越权；
- **每个结论可溯源**：实体/属性/规则带资料出处，「资料里没写」的一律列成待确认问题（OQ）等你裁决，定稿前清零；
- **单一事实源**：DSL `model.yaml` 唯一权威，拓扑图/平台 yaml 全部由它生成，导入后 SDK 四维对账零漂移；
- **门禁全绿才出门**：L1 lint（条数以 `lint_model.py` docstring 为准）+ L2 语义沙盘（S1-S7）+ CQ 回验 + 分发门禁逐项断言——机器拦确定性缺陷，人审拦业务判断。

## 二、包含内容

```text
ontology-forge/
├── skills/                       # 三技能（本体流水线拆分）
│   ├── brief-intake/             #   第 0 步：资料摄取与口述探索（判型归位/完备度评分/冲突预检）
│   ├── ontology-modeling/        #   主技能：九步建模流水线（references/ 含 dsl-spec 格式权威）
│   └── ontology-review/          #   评审：机器检查先行 + 人审（唯一发布权威）
├── agents/aquilair-fde.md        # 总控 agent 人设（随插件自动注册，可派发子代理建模）
├── scripts/                      # 工具链（lint/沙盘/编译/拓扑/CQ/diff/平台对账/域交接/分发门禁）
├── seeds/                        # 种子资产：受控词表 + 既有域速查（随域定稿持续进化）
├── docs/user-guide.md            # 使用手册（FDE 版，完整流程走读）
├── assets/ avatars/ commands/    # 模板 / 头像 / /onto 命令
└── .zcode-plugin/ 等四平台清单    # 单内容多清单（ZCode/WorkBuddy/Claude Code/Codex 同一份内容）
```

## 三、安装（四平台，同一份插件内容）

| 平台 | 安装方式 |
|---|---|
| **ZCode** | Plugin Marketplace → Add → 指向 `plugins/marketplace.json` → 安装 Ontology Forge |
| **WorkBuddy** | 开放平台上传 `pack_workbuddy.py` 构建的 zip（详见 `.codebuddy-plugin/README.md`） |
| **Claude Code** | `/plugin marketplace add <仓库>/plugins` 后安装 |
| **Codex** | `codex plugin marketplace add <仓库>/plugins` 后安装 |

装好后 30 秒验证：新会话发一句「我有一份 XX 业务的需求文档，帮我建本体」——插件应开始引导给文件。

## 四、快速上手：说什么就能触发（完整表见 user-guide 第三节）

| 你说 | 插件做什么 |
|---|---|
| 「我有一份 XX 业务的需求文档和数据字典，帮我建本体」 | 摄取归位 → 九步流水线（只有 DDL 也能开工） |
| 「基于现有 XX 本体，新增一个 YY 场景，只出差异」 | 增量模式：复用既有实体、只建差异、出变更集 |
| 「这业务连文档都没有，我口头跟你说」 | 七维口述探索（范围→对象→关系→规则→动作→数据源→CQ） |

## 五、九步流水线（三个人工确认点）

```text
① 场景圈定 ★你确认 → ② 术语抽取 → ③ 设计稿合成 ★你逐表确认（硬关卡）
→ ④ DSL 生成 → ⑤ 硬校验（L1 lint + L2 语义沙盘，error 拦截）→ ⑥ CQ 回验
→ ⑦ 拓扑+双格式交付 → ⑧ 平台导入自检 → ⑨ 资产回流（glossary/域速查，越用越准）
```

完整流程走读、产物说明、常见问题：`docs/user-guide.md`。

## 六、质量与证据（为什么可以信任产出）

- **L1 lint 硬校验** + **L2 语义沙盘**（DSL 投影 OWL/SHACL 做语义自洽检查，检完即弃不引入推理机）+ **CQ 回验**（建完逐条验证本体能否回答立项时圈定的业务问题）+ **OQ 生命周期** + **平台 SDK 对账** + **人审唯一权威**；
- **以上不是自述，是回归资产**：行为回归（`evals/ontology-modeling/run_evals.py`）+ 分发门禁（`check_dist.py`，含 lint 条数/S 计数/步数口径的**事实源联动断言**——数字口径漂移会被机器抓住）+ 触发用例集（含 near-miss 反例）。改插件必跑，绿灯有据可查（条数以各脚本实时输出为准）。

## 七、运行环境

| 依赖 | 何时需要 | 安装 |
|---|---|---|
| Python 3.10+ 与 PyYAML | 必须（脚本工具链） | `pip install pyyaml` |
| rdflib + owlrl + pyshacl | L2 语义沙盘（缺失时明确报错退出，不静默跳过） | `pip install rdflib owlrl pyshacl` |
| Playwright | 只要拓扑图 PNG 才需要 | `pip install playwright && python -m playwright install chromium` |

## 八、文档导航

- **使用手册（先读）**：`docs/user-guide.md`
- **DSL 规范（格式权威）**：`skills/ontology-modeling/references/dsl-spec.md`
- **子代理派发约定**：`agents/README.md`
- **维护与分发（工厂视角）**：仓库根 `README.md`

---

许可：Proprietary —— Aquilair 内部分发，仅限公司内网使用。
