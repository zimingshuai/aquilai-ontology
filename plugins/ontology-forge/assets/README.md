# assets/ —— 插件静态资源

> 插件规范的标准资源位：随插件整体分发的非代码资产（渲染缓存、图标、模板等）。

## 一、资源清单

| 资源 | 用途 | 引用方 |
|---|---|---|
| mermaid.min.js | mermaid **11.17.2** UMD 单文件（3.4MB）——`--image` 渲染的断网降级缓存（CDN 优先，本地兜底，双失败中文报错不静默） | scripts/render_image.py |

## 二、版本锁

CDN 与本地缓存**必须是同一版本**，由 `scripts/render_image.py` 的 `MERMAID_VERSION` 单一常量约束：

- CDN 地址按该常量拼接（`https://cdn.jsdelivr.net/npm/mermaid@{版本}/dist/mermaid.esm.min.mjs`），不得写 `mermaid@11` 这类浮动 major——否则联网侧浮动到最新 11.x、断网侧固定缓存版本，同一份 DSL 在两种环境下可能渲染出不同版式，拓扑 diff 图跨端不可复现。
- 升级 mermaid 时两件事一起做：改 `MERMAID_VERSION`，同时用同版本 `dist/mermaid.min.js` 覆盖本目录缓存文件。
- 一致性由 `scripts/check_dist.py` 门禁校验（锁定常量 vs 缓存内实际 `version` 字段）。

## 三、分发要求

本目录属**必随包分发**项：WorkBuddy 分发包（`scripts/pack_workbuddy.py`）把 `assets/` 列入必需项，缺失即构建失败；`check_dist.py` 另断言 zip 内缓存非空。原因：`ontology-modeling` 技能承诺 `--image` 断网走本地缓存兜底，缓存不进包则该承诺在分发形态下不成立。
