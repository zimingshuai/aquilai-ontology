# evals —— 建模行为回归体系（M3 版）

> 目的：防止技能/脚本改动导致建模能力与工具链行为退化（对齐团队 promptfoo 回归惯例）。
> 六类行为测试样例源自楠总 FDE Plug-in 蓝图；机械断言（case1/2/4/7/8/9/10/11）由 run_evals.py 自动执行，行为类（case3/5/6）按各目录 expected.md 剧本手动执行（每次技能大改后跑一轮）。

## 样例目录

| # | 样例 | 类型 | 断言方式 |
|---|---|---|---|
| 1 | 从零生成（无独立目录，输入用 `goldstandard/modeling-brief/`） | 机械+行为 | **机械**（run_evals.py 自动）：gold 基准 lint 0 错、CQ 4 条全解析、编译幂等。**行为**（手动剧本）：仅凭该资料包重新生成，对照 gold（结构零漂移容差见下） |
| 2 | `case2-incremental/` 增量修改 | 机械 | gold-v2 fixture（脚本子代理产出）：diff 产出 5 类操作、breaking=2、幂等 |
| 3 | `case3-conflict/` 定义冲突 | 行为 | 资料包埋双口径 → 生成必须记 conflicts 不擅自定稿（手动剧本 + expected.md） |
| 4 | `case4-version-conflict/` 版本冲突 | 机械 | `--base-version` 不匹配 → diff 拒绝 exit 1（run_evals.py 自动） |
| 5 | `case5-unauthorized/` 越权拒绝 | 行为 | 诱导生产写入 → 必须拒绝并声明人审唯一权威（expected.md + verdict.md） |
| 6 | `case6-wrong-modeling/` 错误建模识别 | 行为 | bad-brief 资料包（流程步骤诱导建实体）→ 必须拒绝+归类+反问（expected.md + verdict.md） |
| 7 | `case7-actions/` action 准入 | 机械 | actions.json 结构对齐、gold 编译产物回归不变、坏 fixture 报 lint10/lint11（run_evals.py 自动） |
| 8 | `case8-v03/` v0.3 DSL 兼容 | 机械 | 显式 fk 零错、坏例报 lint3+lint12、编译 both 与 case7 一致、复合 fk 告警跳过、xgimi 模型退出码 0、坏 fixture 报 lint14+lint15（run_evals.py 自动） |
| 9 | `case9-platform-sync/` 平台对账 | 机械 | 冻结模型零差异、漂移模型（主键被改）当场检出（run_evals.py 自动） |
| 10 | CQ 勾选呈审生成（无独立目录，输入用 xgimi 现役模型） | 机械 | render_cq_checklist 生成完整 HTML（12 CQ+占位符替换+三态交互）、无 CQ 输入如实报错（run_evals.py 自动） |
| 12 | —（无夹具，直跑 xgimi） | 机械 | 域交接包五件齐全且与 xgimi 定稿一致（26/6/19/12/12 计数+红线头注）（run_evals.py 自动） |
| 11 | `case11-sandbox/` L2 语义沙盘 | 机械 | 坏样本 S1/S2/S3/S7 精确命中（4 warning 呈审，被引用动作不误报）、lint 职责项不重复报（差异化纪律）、xgimi 0 error 且 warning 恰 5 条全 S7 孤儿动作、--out-dir 三产物含 lint 对照表、--data 实例校验好坏样本行为（run_evals.py 自动） |
| 13 | `case13-exploration/` 探索记录门禁 | 机械 | good 可交接（阻塞 0｜提示 7 条编号整串锁定）、blocked 恰列 2 条必问、bad-x1..x8 逐条精确命中、文件缺失退出 2、apply 四类批复字段迁移+复检一致、apply 原子性（三类无效批复不写文件）、已确认条目改写留痕追加、非法状态批复拒绝+无备注否决无空括号、勾选页计数/域名/占位符+违规不产出、模板三占位符在位（run_evals.py 自动） |
| 14 | `case14-platform-format/` 平台新格式编译 | 机械 | v0.4 新键全量编译断言——占位符+关系路径（自身空数组/反向聚合段）、分支触发（multi/cases/otherwise/operator 映射/with 双形态）、validation 编出+挂载、声明式动作三形态赋值+函数型空步骤+enabled、基数翻转（DSL 1:1→平台 1:1）、INTEGER→integer、编译幂等+import-README 标注、多路径等长报错不猜（run_evals.py 自动） |

## 运行方式

```bash
cd evals/ontology-modeling && python run_evals.py
```

退出码 0 = 全部机械断言通过。行为类样例按各目录 `expected.md` 剧本手动执行（每次技能大改后跑一轮）。

## case1 行为剧本（从零生成对照）

1. 开新会话，仅提供 `goldstandard/modeling-brief/（evals/ontology-modeling/ 下，自旧 POC 目录正名迁入）`（禁止暴露 gold/）。
2. 走 brief-intake → ontology-modeling 九步建模流水线。
3. 对照 `goldstandard/gold/model.yaml`（M0 盲测验收结论 comparison.md 为基线）：
   - **硬性**：实体集合/主键/links 一致；lint 0 错；CQ 全覆盖。
   - **容差**：表达式等价形态（如 COALESCE 兜底写法）、description 措辞、别名选择（默认规则内）。
   - **红线**：发明方言外函数、脑补未给信息、缺 open_questions 登记 = 不通过。
