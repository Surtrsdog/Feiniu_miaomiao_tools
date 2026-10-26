"""网络请求工具：带重试、超时与 UA 伪装。

本环境对部分域名有 TLS/限流问题，故统一走这里。
"""
from __future__ import annotations

import json
import socket
import ssl
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Dict, Optional

# 注意：PRTS Wiki 会拒绝浏览器 UA（返回 403），必须使用简洁的自定义 UA。
# 已实测：prts-calc/1.0、akcalc/1.0、python-urllib 默认值均可，
# 而伪装 Chrome 的 UA 会被 403。
DEFAULT_UA = "akcalc/1.0 (+local damage & pathfinding calculator)"

_SSL_CTX = ssl.create_default_context()
# 部分镜像证书链不完整，仅在失败时降级
_SSL_CTX_INSECURE = ssl.create_default_context()
_SSL_CTX_INSECURE.check_hostname = False
_SSL_CTX_INSECURE.verify_mode = ssl.CERT_NONE


class FetchError(RuntimeError):
    """网络抓取失败。"""


def fetch_bytes(url: str,
                tries: int = 5,
                timeout: float = 60.0,
                headers: Optional[Dict[str, str]] = None) -> bytes:
    """下载 URL 内容，失败自动重试并指数退避。"""
    h = {"User-Agent": DEFAULT_UA, "Accept": "*/*"}
    if headers:
        h.update(headers)

    last: Optional[Exception] = None
    for attempt in range(tries):
        for ctx in (_SSL_CTX, _SSL_CTX_INSECURE):
            try:
                req = urllib.request.Request(url, headers=h)
                with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
                    chunks = []
                    while True:
                        c = resp.read(131072)
                        if not c:
                            break
                        chunks.append(c)
                    return b"".join(chunks)
            except urllib.error.HTTPError as e:
                last = e
                # 4xx 不重试（除 403 限流与 429）
                if 400 <= e.code < 500 and e.code not in (403, 429):
                    raise FetchError(f"HTTP {e.code}: {url}") from e
                break
            except (urllib.error.URLError, socket.timeout, TimeoutError,
                    ConnectionError, OSError) as e:
                last = e
                continue
        time.sleep(min(1.0 * (attempt + 1), 4.0))
    raise FetchError(f"抓取失败（{tries} 次重试）：{url}: {last}")


def fetch_text(url: str, **kw) -> str:
    return fetch_bytes(url, **kw).decode("utf-8", "replace")


def fetch_json(url: str, **kw) -> Any:
    raw = fetch_bytes(url, **kw)
    return json.loads(raw.decode("utf-8", "replace"))


# ---------------------------------------------------------------- 镜像
# jsDelivr 对同一来源有稳定限速，换它的不同后端（CDN/Fastly/Gcore/
# Cloudflare 测试节点）等于换一条通道，实测单文件 1.3~2.9 秒；
# ghfast.top / gh-proxy.com 作为 GitHub raw 的代理轮换，约 2 秒。
# raw.githubusercontent.com 本机不可直连（超时），只作最后兜底。
JSDELIVR_BASES = (
    "https://cdn.jsdelivr.net/gh/",
    "https://fastly.jsdelivr.net/gh/",
    "https://testingcf.jsdelivr.net/gh/",
    "https://gcore.jsdelivr.net/gh/",
)

# (前缀, 形式) 形式 'gh' 表示后面直接拼 "<user>/<repo>@<ref>/<path>"
# 形式 'raw' 表示拼完整 raw.githubusercontent.com 的 URL 给它代理
GITHUB_PROXIES = (
    ("https://ghfast.top/", "raw"),
    ("https://gh-proxy.com/", "raw"),
)

RAW_GITHUB = "https://raw.githubusercontent.com/"


def github_raw_url(user: str, repo: str, ref: str, path: str) -> str:
    return "%s%s/%s/%s/%s" % (RAW_GITHUB, user, repo, ref, path)


def github_mirror_urls(user: str, repo: str, ref: str, path: str):
    """给同一个 GitHub 文件生成一串镜像 URL（按实测速度排序）。

    先 jsDelivr 各后端，再 GitHub 代理，最后直连 raw。
    """
    p = path.lstrip("/")
    out = []
    for base in JSDELIVR_BASES:
        out.append("%s%s/%s@%s/%s" % (base, user, repo, ref, p))
    raw = github_raw_url(user, repo, ref, path)
    for prefix, mode in GITHUB_PROXIES:
        out.append(prefix + raw)
    out.append(raw)
    return out


def fetch_first(urls, tries_per: int = 2, timeout: float = 30.0,
                headers: Optional[Dict[str, str]] = None,
                on_error=None) -> bytes:
    """依次试 urls，返回第一个成功的内容。

    全部失败时抛 FetchError。on_error(url, exc) 可选，用来记录日志。
    """
    last: Optional[Exception] = None
    for url in urls:
        try:
            return fetch_bytes(url, tries=tries_per, timeout=timeout,
                               headers=headers)
        except Exception as e:            # noqa: BLE001 — 镜像失败原因很多
            last = e
            if on_error:
                on_error(url, e)
    raise FetchError("所有镜像都失败：%s" % last)



def build_query(base: str, params: Dict[str, Any]) -> str:
    return base + ("&" if "?" in base else "?") + urllib.parse.urlencode(params)