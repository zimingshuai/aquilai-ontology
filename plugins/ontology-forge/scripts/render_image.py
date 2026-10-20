"""Mermaid 源码 -> PNG/SVG 图片渲染模块（Playwright 无头浏览器 + mermaid 锁定版本）。

主要 Input：Mermaid 源码字符串（render_topology.py 从 topology.md 的 ```mermaid 块提取）
+ 输出基底路径（如 topology）+ 格式 png|svg|both。
主要 Output：topology.png（白底、宽度自适应图幅、2x 缩放保证清晰度）与 topology.svg（原始 SVG 落盘）。
资源加载链（不静默降级）：CDN ESM 优先 -> 本地缓存 assets/mermaid.min.js（UMD 单文件）降级
-> 两者皆不可用时抛中文错误并提示缓存方案。两侧版本由 MERMAID_VERSION 统一锁定，
保证同一份 DSL 在联网/断网下渲染版式一致。
"""

# 标准库导入
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

# 第三方依赖导入
from playwright.sync_api import sync_playwright

# 项目内部模块导入（无——本模块被 render_topology.py 调用，不依赖同目录其他模块）


# ===========一、常量（CDN 地址 / 缓存路径 / 页面模板）==========
# MERMAID_VERSION：mermaid 版本锁——CDN 与本地缓存必须同版本。
# 只钉 major（如 mermaid@11）会让联网侧浮动到最新 11.x、断网侧固定缓存版本，
# 同一份 DSL 在两种环境下可能渲染出不同版式，拓扑 diff 图跨端不可复现。
MERMAID_VERSION = "11.17.2"
# MERMAID_CDN_URL：按锁定版本拼 CDN ESM 入口（浏览器 import() 直接可用，子 chunk 由 CDN 解析）。
MERMAID_CDN_URL = f"https://cdn.jsdelivr.net/npm/mermaid@{MERMAID_VERSION}/dist/mermaid.esm.min.mjs"
# ASSET_CACHE_PATH：CDN 不可达时的本地降级缓存（同版本 UMD 单文件，含全部图型；插件根 assets/ 标准资源位）。
ASSET_CACHE_PATH = Path(__file__).parent.parent / "assets" / "mermaid.min.js"
# ASSET_URL_PATH：页面内引用本地缓存的 URL 路径（由本模块内置 HTTP 服务提供）。
ASSET_URL_PATH = "/assets/mermaid.min.js"
# VIEWPORT_SIZE：无头浏览器视口（截图按元素边界捕获，超出视口部分可截；视口仅影响初始布局）。
VIEWPORT_SIZE = {"width": 1600, "height": 900}
# PNG_SCALE：PNG 截图默认缩放倍数（device_scale_factor），2x 保证文字清晰度。
PNG_SCALE = 2
# PNG_MAX_WIDTH：PNG 输出目标最大宽度（像素）；自然图幅两倍超出该值时降低采样倍数，
# 下限 1x——超大图不为凑宽度目标做 <1x 缩采样（会糊字），如实按自然尺寸输出。
PNG_MAX_WIDTH = 4000

# _HTML_TEMPLATE：渲染页模板。占位符 __CDN_URL__ / __MERMAID_JSON__ / __ASSET_URL__ 由 _build_page_html 注入。
# 页面职责：加载 mermaid（CDN ESM -> 本地 UMD 缓存两级）-> mermaid.render 得 SVG -> 按 viewBox
# 显式设置宽高（mermaid 输出 width="100%"，在 inline-block 收缩容器中会塌陷；实测 useMaxWidth:false
# 配置对 classDiagram 不完全生效，故以 viewBox 兜底）-> SVG 串与实测宽高写回 window.__result；
# 任一环节失败写 window.__err（不静默吞错）。
_HTML_TEMPLATE = """<!DOCTYPE html>
<html><head><meta charset="utf-8"><style>
  html, body { margin: 0; padding: 0; background: #ffffff; }
  #stage { display: inline-block; background: #ffffff; padding: 8px; }
</style></head>
<body><div id="stage"></div>
<script type="module">
const CDN_URL = '__CDN_URL__';
const MERMAID_SRC = __MERMAID_JSON__;

// loadScript：动态注入 <script> 标签加载 UMD 文件（onload/onerror 决议，失败不静默）。
function loadScript(src) {
  return new Promise((resolve, reject) => {
    const s = document.createElement('script');
    s.src = src;
    s.onload = () => resolve();
    s.onerror = () => reject(new Error('script 加载失败: ' + src));
    document.head.appendChild(s);
  });
}

// window.__render：Python 侧 page.evaluate 调用的渲染入口。
window.__render = async () => {
  let mod, source;
  try {
    mod = await import(CDN_URL);           // 一级：CDN ESM
    source = 'cdn';
  } catch (e1) {
    try {
      await loadScript('__ASSET_URL__');   // 二级：本地 UMD 缓存
      mod = window.mermaid;
      source = 'cache';
    } catch (e2) {
      window.__err = 'BOTH_FAIL';          // 两级都失败：交由 Python 侧报中文错误
      return;
    }
  }
  const mermaid = mod.default ?? mod;
  // useMaxWidth:false 让 classDiagram 按自然图幅渲染（不被视口宽度拉伸/压缩）。
  mermaid.initialize({ startOnLoad: false, securityLevel: 'loose',
                       class: { useMaxWidth: false } });
  try {
    const { svg } = await mermaid.render('topo-svg', MERMAID_SRC);
    document.getElementById('stage').innerHTML = svg;
    // 兜底：按 viewBox 显式设置宽高——mermaid 输出 width="100%"，在 inline-block 收缩容器中
    // getBoundingClientRect 会塌成容器宽（实测塌成 300px），显式像素宽高让自然图幅真正生效。
    const el = document.querySelector('#stage svg');
    const vb = el.viewBox && el.viewBox.baseVal;
    if (vb && vb.width > 0) {
      el.setAttribute('width', String(Math.ceil(vb.width)));
      el.setAttribute('height', String(Math.ceil(vb.height)));
    }
    const rect = el.getBoundingClientRect();
    // outerHTML：带显式宽高的 SVG（落盘文件独立打开时不随窗口宽度缩放）。
    window.__result = { svg: el.outerHTML, width: Math.ceil(rect.width),
                        height: Math.ceil(rect.height), source: source };
  } catch (e) {
    window.__err = 'RENDER_FAIL: ' + (e && e.message ? e.message : String(e));
  }
};
</script></body></html>
"""


def _build_page_html(mermaid_src: str) -> str:
    """把 Mermaid 源码与 CDN 地址注入页面模板。

    Args:
        mermaid_src: Mermaid classDiagram 源码字符串。
    Returns:
        可直接由内置 HTTP 服务返回的完整 HTML 字符串。
    """
    # JSON.dumps 产物即合法 JS 字符串字面量（ensure_ascii=False 保中文可读）。
    return (
        _HTML_TEMPLATE
        .replace("__CDN_URL__", MERMAID_CDN_URL)
        .replace("__ASSET_URL__", ASSET_URL_PATH)
        .replace("__MERMAID_JSON__", json.dumps(mermaid_src, ensure_ascii=False))
    )


# ===========二、内置 HTTP 服务（页面 + 本地缓存文件）==========
class _RenderHandler(BaseHTTPRequestHandler):
    """渲染页内置 HTTP 服务处理器：/ 返回渲染页 HTML，ASSET_URL_PATH 返回本地缓存文件。

    Input:
        page_html: 类属性注入的渲染页 HTML（服务启动前设置）。
        asset_path: 类属性注入的本地缓存文件路径（可能不存在，存在才可服务）。
    Return:
        通过 HTTP 响应返回页面或缓存文件字节流；未命中路径返回 404。
    """

    page_html = ""  # 渲染页 HTML（_serve_render_page 启动前注入）
    asset_path: Path | None = None  # 本地缓存 mermaid UMD 文件路径

    def do_GET(self) -> None:  # noqa: N802（http.server 约定方法名）
        """按路径分发：/ -> 页面 HTML；ASSET_URL_PATH -> 缓存文件；其余 404。"""
        if self.path in ("/", "/index.html"):
            body, ctype = self.page_html.encode("utf-8"), "text/html; charset=utf-8"
        elif self.path == ASSET_URL_PATH and self.asset_path and self.asset_path.exists():
            body, ctype = self.asset_path.read_bytes(), "application/javascript"
        else:
            self.send_error(404)
            return
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: Any) -> None:  # noqa: A002（基类签名）
        """静音默认访问日志（渲染管线内部服务，不需要刷屏输出）。"""
        return


def _serve_render_page(page_html: str):
    """在 127.0.0.1 随机端口起内置 HTTP 服务并返回 (server, url)。

    Args:
        page_html: 渲染页完整 HTML。
    Returns:
        (ThreadingHTTPServer 实例, 页面 URL)；调用方负责 server.shutdown() 收尾。
    """
    handler_cls = type("_BoundRenderHandler", (_RenderHandler,),
                       {"page_html": page_html, "asset_path": ASSET_CACHE_PATH})
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler_cls)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server, f"http://127.0.0.1:{server.server_address[1]}/"


# ===========三、渲染主函数（Mermaid 源 -> SVG/PNG 文件）==========
def _load_and_render(browser: Any, url: str, scale: float) -> tuple[Any, Any, dict[str, Any]]:
    """在指定采样倍数的浏览器上下文中加载渲染页并执行 mermaid 渲染。

    Args:
        browser: Playwright Browser 实例。
        url: 内置 HTTP 服务的渲染页 URL。
        scale: device_scale_factor 采样倍数（影响后续元素截图像素密度）。
    Returns:
        (context, page, result)；result 含 svg 串 / width / height（CSS px）/ source。
    Raises:
        RuntimeError: mermaid 资源两级加载均失败（附中文缓存方案提示）或渲染本身失败。
    """
    context = browser.new_context(device_scale_factor=scale, viewport=VIEWPORT_SIZE)
    page = context.new_page()
    page.goto(url)
    page.evaluate("window.__render()")
    err = page.evaluate("window.__err")
    if err == "BOTH_FAIL":
        context.close()
        raise RuntimeError(
            "====mermaid 资源加载失败====: CDN 不可达（"
            f"{MERMAID_CDN_URL}），且本地缓存 {ASSET_CACHE_PATH} 不存在或不可用。"
            "请联网后重试，或将 mermaid@" + MERMAID_VERSION + " UMD 单文件（dist/mermaid.min.js）"
            "下载放置到上述缓存路径后再试。")
    if err:
        context.close()
        raise RuntimeError(f"====Mermaid 渲染失败====: {err}")
    return context, page, page.evaluate("window.__result")


def render_mermaid_image(mermaid_src: str, out_base: Path, fmt: str = "png") -> dict[str, Any]:
    """用无头浏览器把 Mermaid 源码渲染为 SVG/PNG 图片文件。

    Args:
        mermaid_src: Mermaid classDiagram 源码字符串。
        out_base: 输出基底路径（不含扩展名），如 topology -> topology.png / topology.svg。
        fmt: 输出格式 png | svg | both。
    Returns:
        产物信息 dict：svg/png（Path 或 None）、width/height（CSS 像素）、
        source（cdn|cache，标记 mermaid 资源实际来源）、scale（PNG 实际采样倍数）。
    Raises:
        RuntimeError: mermaid 资源两级加载均失败（附中文缓存方案提示），
            或 Mermaid 渲染本身失败，或 Playwright/Chromium 环境不可用。
    """
    info: dict[str, Any] = {"svg": None, "png": None, "width": 0, "height": 0,
                            "source": "", "scale": 0}
    server, url = _serve_render_page(_build_page_html(mermaid_src))
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            #   1. 首遍渲染（默认 2x 上下文）：SVG 落盘 + 测自然图幅宽度
            context, page, result = _load_and_render(browser, url, PNG_SCALE)
            if fmt in ("svg", "both"):
                svg_path = out_base.with_suffix(".svg")
                svg_path.write_text(result["svg"], encoding="utf-8")
                info["svg"] = svg_path
            info.update(width=result["width"], height=result["height"],
                        source=result["source"])
            #   2. PNG 截图：按自然宽定采样倍数（2x 起步；两倍超宽则降采样，下限 1x）
            if fmt in ("png", "both"):
                scale = max(1.0, min(PNG_SCALE, PNG_MAX_WIDTH / max(result["width"], 1)))
                if scale != PNG_SCALE:
                    context.close()
                    context, page, _ = _load_and_render(browser, url, scale)
                png_path = out_base.with_suffix(".png")
                page.locator("#stage svg").screenshot(path=str(png_path))
                info["png"], info["scale"] = png_path, scale
            context.close()
            browser.close()
    except RuntimeError:
        raise
    except Exception as exc:  # Playwright 环境类异常统一转中文提示
        raise RuntimeError(
            f"====图片渲染环境错误====: {type(exc).__name__}: {exc}。"
            "无头浏览器依赖 Playwright，首次使用需执行: python -m playwright install chromium") from exc
    finally:
        server.shutdown()
        server.server_close()
    return info


# ===========四、模块调试入口==========
if __name__ == "__main__":
    # 直接运行本模块可验证渲染管线连通性：python render_image.py
    import sys
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    # demo_src：最小 classDiagram 样例（1 实体 1 关联），用于人工观察 PNG/SVG 产出。
    demo_src = """classDiagram
    class SKU {
        +sku_code : STRING 🔑
    }
    class Warehouse {
        +wh_code : STRING 🔑
    }
    Warehouse "1" --> "*" SKU : stores
"""
    out = render_mermaid_image(demo_src, Path(__file__).parent / "_render_selftest", fmt="both")
    print(f"====自测渲染完成====: source={out['source']}, "
          f"{out['width']}x{out['height']} CSS px")
    print(f"SVG: {out['svg']}")
    print(f"PNG: {out['png']}")
