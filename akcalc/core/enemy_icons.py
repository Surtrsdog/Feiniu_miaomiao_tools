"""怪物（敌人）图标：从 PRTS wiki 下载并本地缓存。

* PRTS 媒体站有防盗链，必须带完整浏览器头，否则 403。
* 图标文件名是「头像_敌人_<中文名>.png」，走 MediaWiki 的 md5 分目录
  （如 3/3e/）再取 /thumb/ 缩略图。
* 网络失败静默返回 None，界面用占位图，不能因为断网卡死。
"""
from __future__ import annotations

import hashlib
import io
import os
import threading
import urllib.error
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
_PREFIX = "头像_敌人_"

#: 游戏内敌人名 -> PRTS 实际文件名（去掉「头像_敌人_」前缀与 .png 后缀）。
#: 部分敌人在游戏里的名字和 wiki 文件名不一致（如带英文/引号/后缀变体），
#: 需要这张别名表才能取到正确头像。打包时随 akcalc/data 一起带入。
_alias: dict = {}
_alias_loaded = False


def _load_alias():
    """懒加载别名表（随包 akcalc/data/enemy_icon_alias.json）。"""
    global _alias, _alias_loaded
    if _alias_loaded:
        return _alias
    _alias_loaded = True
    import json
    for cand in _alias_candidates():
        try:
            if os.path.isfile(cand):
                with open(cand, "r", encoding="utf-8") as f:
                    _alias.update(json.load(f))
                break
        except Exception:
            continue
    return _alias


def _alias_candidates():
    here = os.path.dirname(os.path.abspath(__file__))
    yield os.path.join(here, "..", "data", "enemy_icon_alias.json")
    yield os.path.join(here, "enemy_icon_alias.json")
    import sys
    mp = getattr(sys, "_MEIPASS", None)
    if mp:
        yield os.path.join(mp, "akcalc", "data", "enemy_icon_alias.json")


def _resolve_name(name):
    """游戏内名字 -> PRTS 文件名用名（带别名纠正，去空白）。"""
    n = (name or "").strip()
    try:
        n = _load_alias().get(n, n)
    except Exception:
        pass
    return n


def _file_name(name):
    return _PREFIX + _resolve_name(name) + ".png"


def _hash_dirs(name):
    h = hashlib.md5(_file_name(name).encode("utf-8")).hexdigest()
    return "%s/%s" % (h[0], h[:2])


def icon_url(name, px=64):
    if not name:
        return ""
    resolved = _resolve_name(name)
    fname = _file_name(name).replace(" ", "_")
    q = urllib.parse.quote(fname)
    return "%s/thumb/%s/%s/%dpx-%s" % (_MEDIA, _hash_dirs(resolved), q, px, q)


def icon_page(name):
    """PRTS 敌人详情页地址。"""
    if not name:
        return "https://prts.wiki/"
    return "https://prts.wiki/w/" + urllib.parse.quote(name)


def icon_path(paths, name, px=64):
    safe = "".join(ch if ch not in '\\/:*?"<>|' else "_"
                   for ch in (name or ""))
    d = os.path.join(paths.data_dir, "icons", "enemy", str(px))
    return os.path.join(d, "%s.png" % safe)


def fetch_icon(name, px=64, timeout=20.0):
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


#: 占位图 CJK 字体缓存（按字号），避免每次画头像都重新加载字体。
_font_cache: dict = {}


def _cjk_font(size):
    """取一个可渲染中文的字体；找不到就返回 None（画首字会退化）。"""
    key = int(size)
    if key in _font_cache:
        return _font_cache[key]
    from PIL import ImageFont
    candidates = (
        r"C:\Windows\Fonts\simhei.ttf",
        r"C:\Windows\Fonts\msyh.ttc",
        r"C:\Windows\Fonts\msyhbd.ttc",
        r"C:\Windows\Fonts\simsun.ttc",
    )
    font = None
    for p in candidates:
        try:
            font = ImageFont.truetype(p, key)
            break
        except Exception:
            continue
    _font_cache[key] = font
    return font


def placeholder_icon(name, px=64):
    """无头像敌人用的占位图（内存生成，绝不落盘）。

    落盘会伪装成「已缓存」，导致 ``load_icon_async`` 在 ``os.path.isfile``
    处提前返回、再也不去 PRTS 补真实头像；所以这里只返回 PIL 图，让
    ``load_icon`` 对无图敌人依旧返回 None，后台补图照常工作。
    """
    try:
        from PIL import Image, ImageDraw
    except ImportError:
        return None
    try:
        px = int(px)
    except (TypeError, ValueError):
        px = 64
    if px <= 0:
        px = 64

    # 深色主题字面量（避免反向依赖 ui.widgets，用与主题一致的色值）
    bg = (31, 36, 46, 255)       # #1f242e
    border = (51, 60, 74, 255)   # #333c4a
    fg = (154, 165, 180, 255)    # #9aa5b4

    im = Image.new("RGBA", (px, px), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    r = max(2, int(px * 0.14))
    d.rounded_rectangle([0, 0, px - 1, px - 1], radius=r, fill=bg,
                        outline=border, width=1)

    nm = (name or "").strip()
    ch = nm[0] if nm else "?"
    font = _cjk_font(max(10, int(px * 0.48)))
    try:
        bbox = d.textbbox((0, 0), ch, font=font)
        w = bbox[2] - bbox[0]
        h = bbox[3] - bbox[1]
        x = (px - w) / 2 - bbox[0]
        y = (px - h) / 2 - bbox[1]
        d.text((x, y), ch, fill=fg, font=font)
    except Exception:
        d.text((px / 2, px / 2), ch, fill=fg, anchor="mm")
    return im


def load_icon(paths, name, px=64):
    """只读本地缓存，绝不联网（UI 线程安全，不会卡）。

    没缓存就返回 None，让调用方画占位图；想补图请用 ``load_icon_async``。
    优先读目标尺寸，读不到时用其它已缓存的尺寸（44/64/96/128）就近缩放，
    这样只要有一个尺寸下载成功，所有视图都能显示头像。
    """
    try:
        from PIL import Image
    except ImportError:
        return None
    p = icon_path(paths, name, px)
    if os.path.isfile(p):
        try:
            return Image.open(p).convert("RGBA")
        except Exception:
            try:
                os.remove(p)
            except OSError:
                pass
    # 回退到其它尺寸（按与目标尺寸的接近度排序）
    if px != 64 and os.path.isfile(icon_path(paths, name, 64)):
        p = icon_path(paths, name, 64)
    else:
        base = os.path.dirname(icon_path(paths, name, px))
        if os.path.isdir(base):
            sizes = []
            for d in os.listdir(base):
                if d.isdigit():
                    sizes.append(int(d))
            sizes.sort(key=lambda s: abs(s - px))
            for s in sizes:
                cand = icon_path(paths, name, s)
                if os.path.isfile(cand):
                    p = cand
                    break
    try:
        im = Image.open(p).convert("RGBA")
    except Exception:
        return None
    if im.width != px or im.height != px:
        try:
            im = im.resize((px, px), Image.LANCZOS)
        except Exception:
            pass
    return im


#: 本次进程内已确认「没有图」的名字，避免对无图敌人反复重试下载。
_negative: Set[str] = set()
#: 正在后台下载（或已排队）的名字，避免重复起线程。
_inflight: Set[str] = set()
_lock = threading.Lock()


def load_icon_async(paths, name, px=64, on_done: Optional[Callable] = None,
                    timeout=20.0):
    """后台下载图标到磁盘缓存，完成后在后台线程回调 on_done(im|None)。

    绝不阻塞 UI 线程。on_done 在下载线程里被调用，若需要更新界面，
    调用方自己用 ``widget.after(0, ...)`` 切回主线程。名字无图（403/404）
    会记入负面缓存，后续直接跳过。
    """
    p = icon_path(paths, name, px)
    if os.path.isfile(p):
        # 已缓存，直接同步读回（本地 IO 很快）
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
            # 已在下载中，等它完成（这里不重复回调；调用方可用缓存重试）
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