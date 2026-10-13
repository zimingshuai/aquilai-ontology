# case4：版本冲突（机械断言样例）

断言：`diff_model.py --base-version` 与 base DSL 的 version 不一致时拒绝生成变更集（exit 1 + 明确错误），**禁止强推覆盖**——对应楠总蓝图样例四（preview 基于 v3、引擎已到 v4 时 apply 必须被拒）。

执行：`run_evals.py` 自动覆盖（构造不匹配的 base-version 调用 diff_model，断言退出码 1 与错误信息关键字"重新生成"）。
