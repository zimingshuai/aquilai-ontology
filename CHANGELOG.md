# 推送记录（CHANGELOG）

> 维护规则：**每次 push 走 `skill-forge/tools/push_record.py`**（打 tag `push/YYYY-MM-DD.N` +
> CHANGELOG 记一节 + 推送，三合一）——裸 push 视为违规。
> 回退方式：① 回看某次推送全量内容 `git show push/日期.序号 --stat`；② 回退单个文件/目录
> `git checkout push/日期.序号 -- <路径>`；③ 整体回退用 `git revert`（生成新提交，安全）；
> 禁用 `git reset --hard` 直推远程（违反只进不退）。
> 各节倒序排列（最新在上）；版本号不可变、只进不退。

## push/2026-11-20.1（2026-11-20 10:35）｜1 commits
- `06ed070` feat(v0.4.9): L2 语义沙盘+ontology-driven-dev 四样吸收+口述探索变体C+文档体系+域交接包——离线门禁/建模纪律/零资料入口/口径断言/技能工厂供料全链落地
> 要点：v0.4.9 七轮落地：L2 语义沙盘(S1-S7)/ontology-driven-dev 四样吸收/口述探索变体C/文档体系四层+S·lint 口径全树断言/域交接包五件(gen_handoff)/清理正名(xgimi-rebuild 删+goldstandard 迁 evals)；evals 29+check_dist 65 全绿

