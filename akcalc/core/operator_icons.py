"""干员头像：从 PRTS wiki 下载并本地缓存。

与敌人图标同源（media.prts.wiki），但文件名前缀是「头像_」（不带「敌人_」）：
    https://media.prts.wiki/thumb/<d>/<dd>/<px>px-头像_<中文名>.png

缓存到 ``data/icons/operator/<px>/<干员名>.png``。网络失败静默返回 None，
UI 用占位图，不因断网卡死。
"""
from __future__ import annotations

import hashlib
import io
import os
import threading
import urllib.parse
import urllib.request
from typing import Callable, Optional, Set

_HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                   "AppleWebKit/537.36 (KHTML, like Gecko) "
                   "Chrome/131.0.0.0 Safari/537.36"),
    "Accept": ("image/avif,image/webp,image/apng,image/svg+xml,"
               "image/*,*/*;q=0.8"),
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Referer": "https://prts.wiki/",
    "sec-ch-ua": '"Chromium";v="131", "Not_A Brand";v="24"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"Windows"',
    "Sec-Fetch-Dest": "image",
    "Sec-Fetch-Mode": "no-cors",
    "Sec-Fetch-Site": "same-site",
}

_MEDIA = "https://media.prts.wiki"
_PREFIX = "头像_"


def _file_name(name):
    return _PREFIX + (name or "").strip() + ".png"


def _hash_dirs(name):
    h = hashlib.md5(_file_name(name).encode("utf-8")).hexdigest()
    return "%s/%s" % (h[0], h[:2])


def icon_url(name, px=128):
    if not name:
        return ""
    fname = _file_name(name).replace(" ", "_")
    q = urllib.parse.quote(fname)
    return "%s/thumb/%s/%s/%dpx-%s" % (_MEDIA, _hash_dirs(name), q, px, q)


def icon_page(name):
    """PRTS 干员详情页地址。"""
    if not name:
        return "https://prts.wiki/"
    return "https://prts.wiki/w/" + urllib.parse.quote(name)


def icon_path(paths, name, px=128):
    safe = "".join(ch if ch not in '\\/:*?"<>|' else "_"
                   for ch in (name or ""))
    d = os.path.join(paths.data_dir, "icons", "operator", str(px))
    return os.path.join(d, "%s.png" % safe)


def fetch_icon(name, px=128, timeout=20.0):
    url = icon_url(name, px)
    if not url:
        return None
    try:
        req = urllib.request.Request(url, headers=_HEADERS)
        with urllib.request.urlopen(req, timeout=timeout) as r:
            if not (r.headers.get("Content-Type") or "").startswith("image/"):
                return None
            return r.read()
    except Exception:
        return None


def load_icon(paths, name, px=128):
    """只读本地缓存，绝不联网（UI 线程安全，不会卡）。"""
    try:
        from PIL import Image
    except ImportError:
        return None
    p = icon_path(paths, name, px)
    if not os.path.isfile(p):
        return None
    try:
        return Image.open(p).convert("RGBA")
    except Exception:
        try:
            os.remove(p)
        except OSError:
            pass
        return None


#: 本次进程内已确认「没有图」的名字，避免对无图干员反复重试下载。
_negative: Set[str] = set()
#: 正在后台下载（或已排队）的名字，避免重复起线程。
_inflight: Set[str] = set()
_lock = threading.Lock()


def load_icon_async(paths, name, px=128, on_done: Optional[Callable] = None,
                    timeout=20.0):
    """后台下载图标到磁盘缓存，完成后在后台线程回调 on_done(im|None)。

    不阻塞 UI 线程。on_done 在下载线程里被调用，更新界面需调用方自己
    ``widget.after(0, ...)`` 切回主线程。无图名字记入负面缓存。
    """
    p = icon_path(paths, name, px)
    if os.path.isfile(p):
        try:
            from PIL import Image
            im = Image.open(p).convert("RGBA")
            if on_done:
                on_done(im)
            return
        except Exception:
            try:
                os.remove(p)
            except OSError:
                pass
    with _lock:
        if name in _negative:
            if on_done:
                on_done(None)
            return
        if name in _inflight:
            if on_done:
                on_done(None)
            return
        _inflight.add(name)

    def worker():
        raw = fetch_icon(name, px, timeout=timeout)
        im = None
        if raw:
            try:
                from PIL import Image
                im = Image.open(io.BytesIO(raw)).convert("RGBA")
            except Exception:
                im = None
        if im is not None:
            try:
                os.makedirs(os.path.dirname(p), exist_ok=True)
                im.save(p, "PNG")
            except OSError:
                pass
        else:
            with _lock:
                _negative.add(name)
        with _lock:
            _inflight.discard(name)
        if on_done:
            try:
                on_done(im)
            except Exception:
                pass

    t = threading.Thread(target=worker, daemon=True)
    t.start()