# scripts/ —— 插件工具链（多技能共用的公共基础设施）

> 定位声明：这里的 18 个脚本是 **ontology-forge 插件的公共工具链层**，不是某个技能的私有实现。
> 调用方：ontology-modeling（流水线）、ontology-review（机器检查先行）、/onto 命令路由、WorkBuddy agent 总控提示词、evals 回归（全量覆盖）。
> 版本：随插件整体版本化（见 .zcode-plugin/plugin.json），与技能同版本演进，无独立漂移。

## 脚本清单

| 脚本 | 职责 | 主要调用方 |
|---|---|---|
| lint_model.py | DSL 硬校验 L1（条数以 lint_model.py docstring 为准） | ontology-modeling ⑥、ontology-review |
| semantic_sandbox.py | L2 语义沙盘——DSL 假设投影 OWL/SHACL 的语义自洽性检查（S1-S7，与 lint 编号独立） | ontology-modeling ⑥、ontology-review |
| check_cq.py | CQ 覆盖矩阵 | ontology-modeling ⑦、ontology-review |
| render_topology.py | 拓扑渲染（classDiagram / layered / --interactive / --diff / --image） | ontology-modeling ③⑧ |
| compile_model.py | DSL → studio-model.yaml / 引擎 JSON / actions.json | ontology-modeling ⑧ |
| diff_model.py | 变更集（JSON Patch + breaking + 版本冲突拒绝） | ontology-modeling（增量） |
| export_dsl.py | 引擎快照 JSON → DSL（逆向导出） | 增量建模 / 平台同步 |
| gen_action_skeleton.py | action 骨架生成（三配方） | ontology-modeling（动作域） |
| gen_handoff.py | 域交接包生成（本体定稿 → 技能工厂立项素材五件） | ontology-modeling ⑨（资产回流） |
| check_platform_sync.py | DSL ↔ 平台 SDK 一致性自检 | ontology-modeling ⑨（导入后闭环） |
| lint_studio_model.py | studio-model 模板结构 lint | 模板评审 |
| check_dist.py | 分发结构门禁（清单合规/口径漂移/规范断言） | 发布前自检、evals |
| pack_workbuddy.py | WorkBuddy zip 构建打包 | 发布前 |
| render_cq_checklist.py | CQ 勾选呈审 HTML 生成 | ontology-modeling ③ |
| studio_model.py / lint_glossary.py / render_image.py / owl_converter.py | 内部模块（被 compile / lint / render / sandbox import，勿直接调用） | — |

> 决策记录（2026-10-15）：若未来插件演化为"技能可独立拆分发售"，独享脚本按归属原则下沉到 `skills/<name>/scripts/`；当前整体分发形态下维持公共工具链定位。
