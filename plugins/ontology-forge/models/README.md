# models/ —— 本体 DSL 产物目录

每次建模任务的产物按业务域组织（source of truth，进 git）：

```text
models/<domain>/
├── model.yaml                 # 本体 DSL（dsl-spec v0.2）
├── topology.md                # Mermaid 拓扑（render_topology 产出）
├── engine-bundle/             # 引擎注册格式编译产物 + 导入说明
└── modeling-brief/            # 资料包（brief-intake 产出）
```

首个真实业务域产物将在此目录创建；M0 验证用的合成域见 `../../poc/m0/goldstandard/`（不入本目录）。
