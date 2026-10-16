# assets/ —— 插件静态资源

> 插件规范的标准资源位：随插件整体分发的非代码资产（渲染缓存、图标、模板等）。

| 资源 | 用途 | 引用方 |
|---|---|---|
| mermaid.min.js | mermaid@11 UMD 单文件（3.4MB）——`--image` 渲染的断网降级缓存（CDN 优先，本地兜底，双失败中文报错不静默） | scripts/render_image.py |
