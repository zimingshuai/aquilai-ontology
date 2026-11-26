# 推送记录（CHANGELOG）

> 维护规则：**每次 push 走 `skill-forge/tools/push_record.py`**（打 tag `push/YYYY-MM-DD.N` +
> CHANGELOG 记一节 + 推送，三合一）——裸 push 视为违规。
> 回退方式：① 回看某次推送全量内容 `git show push/日期.序号 --stat`；② 回退单个文件/目录
> `git checkout push/日期.序号 -- <路径>`；③ 整体回退用 `git revert`（生成新提交，安全）；
> 禁用 `git reset --hard` 直推远程（违反只进不退）。
> 各节倒序排列（最新在上）；版本号不可变、只进不退。

## v0.6.0（2026-11-26）｜发版 tag `v0.6.0`

- DSL v0.4 + 编译器全面对齐平台新导入格式（官方升级说明）：计算规则占位符 + expressionSources 关系路径**自动推导**（最短且唯一才自动、多条等长报错不猜）、trigger 多分支 cases/otherwise/with、admission→validation 挂载、声明式动作 steps、INTEGER→integer、基数翻转
- lint 15→20 条（16-19 新键校验 + 20 准入字段可解析——补齐「lint 与编译器同判」盲区）；逆向导出 `--platform-yaml`（编译→逆向→lint→再编译**往返字节一致**，case14 与 xgimi 双实证）；平台对账支持 MCP 元数据 JSON 输入
- evals 回归 39→46（case14 平台新格式八组断言）；行为层实物范本 = case14 夹具（范例不硬造无据动作语义）

## v0.5.0（2026-11-26）｜发版 tag `v0.5.0`
- 需求探索侧对标 ontology-driven-dev 八维重做：少问且带建议问、必问六条、探索记录门禁三脚本、勾选批复闭环
- 黄金范例 examples/supplier-recon 随包分发并受发布门禁保护（check_dist 新增范例门禁断言组：探索记录可交接/lint/CQ/编译幂等/拓扑同步/结构等价）
- 发布门禁 65→90、evals 回归 29→39（新增 case13 需求探索记录门禁）

## push/2026-11-20.2（2026-11-20 11:38）｜1 commits
- `e6c21c9` chore(release): 发版 v0.4.9——CHANGELOG 版本节+发版 tag
> 要点：发版 v0.4.9（本体锻造师）

## v0.4.9（2026-11-20）｜发版 tag `v0.4.9`
- L2 语义沙盘 + ontology-driven-dev 四样吸收 + 口述探索变体 C + 文档体系 + 域交接包（离线门禁/建模纪律/零资料入口/口径断言/技能工厂供料全链）
- 详细演进见提交 06ed070（feat(v0.4.9)）；自上一安装版 0.4.7 起含 0.4.8/0.4.9 两轮（口径漂移治理 9 处、check_dist 45→63、OQ 七态对齐等见 dd66b17/79301eb）

## push/2026-11-20.1（2026-11-20 10:35）｜1 commits
- `06ed070` feat(v0.4.9): L2 语义沙盘+ontology-driven-dev 四样吸收+口述探索变体C+文档体系+域交接包——离线门禁/建模纪律/零资料入口/口径断言/技能工厂供料全链落地
> 要点：v0.4.9 七轮落地：L2 语义沙盘(S1-S7)/ontology-driven-dev 四样吸收/口述探索变体C/文档体系四层+S·lint 口径全树断言/域交接包五件(gen_handoff)/清理正名(xgimi-rebuild 删+goldstandard 迁 evals)；evals 29+check_dist 65 全绿

