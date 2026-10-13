---
description: 本体建模入口：从上传文档到本体 DSL 与引擎注册格式（摄取→建模→lint→CQ→拓扑→导出）
---

# /onto —— 本体建模命令

处理参数 `$ARGUMENTS`（业务域描述或资料包路径）：

1. **无资料包**：引导用户提供文档（说明四类资料的形态），然后走 `brief-intake` 技能摄取归位。
2. **有资料包**（用户给出路径或工作区已有 `models/<domain>/modeling-brief/`）：
   - 资料包未经 brief-intake 处理（缺 brief.yaml / intake-log.md）→ 先走 `brief-intake`。
   - 资料包已就绪 → 直接走 `ontology-modeling` 技能七步流水线。
3. **增量建模**（brief.yaml 的 target_engine 为 fnb/mfg）：在 `ontology-modeling` 流水线中启用 seeds 复用与快照 diff 模式。
