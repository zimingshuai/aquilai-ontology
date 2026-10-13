# evals —— 建模行为回归体系（M2 版）

> 目的：防止技能/脚本改动导致建模能力与工具链行为退化（对齐团队 promptfoo 回归惯例）。
> 六类行为测试样例源自楠总 FDE Plug-in 蓝图；M2 落地前四类，样例五（越权拒绝）、六（错误建模识别）属 agent 行为测试，M3 自动化。

## 样例目录

| # | 样例 | 类型 | 断言方式 |
|---|---|---|---|
| 1 | `case1-from-scratch/` 从零生成 | 机械+行为 | **机械**（run_evals.py 自动）：gold 基准 lint 0 错、CQ 4 条全解析、编译幂等。**行为**（手动剧本）：仅凭 `../../poc/m0/goldstandard/modeling-brief/` 重新生成，对照 gold（结构零漂移容差见 README） |
| 2 | `case2-incremental/` 增量修改 | 机械 | gold-v2 fixture（脚本子代理产出）：diff 产出 5 类操作、breaking=2、幂等 |
| 3 | `case3-conflict/` 定义冲突 | 行为 | 资料包埋双口径 → 生成必须记 conflicts 不擅自定稿（手动剧本 + expected.md） |
| 4 | `case4-version-conflict/` 版本冲突 | 机械 | `--base-version` 不匹配 → diff 拒绝 exit 1（run_evals.py 自动） |

## 运行方式

```bash
cd evals/ontology-modeling && python run_evals.py
```

退出码 0 = 全部机械断言通过。行为类样例按各目录 `expected.md` 剧本手动执行（每次技能大改后跑一轮）。

## case1 行为剧本（从零生成对照）

1. 开新会话，仅提供 `poc/m0/goldstandard/modeling-brief/`（禁止暴露 gold/）。
2. 走 brief-intake → ontology-modeling 七步流水线。
3. 对照 `poc/m0/goldstandard/gold/model.yaml`（M0 盲测验收结论 comparison.md 为基线）：
   - **硬性**：实体集合/主键/links 一致；lint 0 错；CQ 全覆盖。
   - **容差**：表达式等价形态（如 COALESCE 兜底写法）、description 措辞、别名选择（默认规则内）。
   - **红线**：发明方言外函数、脑补未给信息、缺 open_questions 登记 = 不通过。
