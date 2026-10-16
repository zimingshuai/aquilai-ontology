# scripts/ —— 插件工具链（多技能共用的公共基础设施）

> 定位声明：这里的 13 个脚本是 **ontology-forge 插件的公共工具链层**，不是某个技能的私有实现。
> 调用方：ontology-modeling（流水线）、ontology-review（机器检查先行）、/onto 命令路由、WorkBuddy agent 总控提示词、evals 回归（全量覆盖）。
> 版本：随插件整体版本化（见 .zcode-plugin/plugin.json），与技能同版本演进，无独立漂移。

## 脚本清单

| 脚本 | 职责 | 主要调用方 |
|---|---|---|
| lint_model.py | DSL 硬校验（13 条） | ontology-modeling ⑥、ontology-review |
| check_cq.py | CQ 覆盖矩阵 | ontology-modeling ⑦、ontology-review |
| render_topology.py | 拓扑渲染（classDiagram / layered / --interactive / --diff / --image） | ontology-modeling ③⑧ |
| compile_model.py | DSL → studio-model.yaml / 引擎 JSON / actions.json | ontology-modeling ⑧ |
| diff_model.py | 变更集（JSON Patch + breaking + 版本冲突拒绝） | ontology-modeling（增量） |
| export_dsl.py | 引擎快照 JSON → DSL（逆向导出） | 增量建模 / 平台同步 |
| gen_action_skeleton.py | action 骨架生成（三配方） | ontology-modeling（动作域） |
| check_platform_sync.py | DSL ↔ 平台 SDK 一致性自检 | ontology-modeling ⑨（导入后闭环） |
| lint_studio_model.py | studio-model 模板结构 lint | 模板评审 |
| studio_model.py / lint_glossary.py / render_image.py | 内部模块（被 compile / lint / render import，勿直接调用） | — |

> 决策记录（2026-10-15）：若未来插件演化为"技能可独立拆分发售"，独享脚本按归属原则下沉到 `skills/<name>/scripts/`；当前整体分发形态下维持公共工具链定位。
