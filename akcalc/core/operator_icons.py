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


def _safe_name(name):
    """文件名清洗：去掉换行/全角空格，再替换 Windows 非法字符。

    ``icon_path`` 与查找必须共用这一个函数，否则会用两个不同的名字
    建目录和找文件，永远对不上。
    """
    n = (name or "").replace("\r", "").replace("\n", "").replace("\t", "")
    n = n.strip().strip("\u3000").strip()
    return "".join(ch if ch not in '\\/:*?"<>|' else "_" for ch in n)


def icon_path(paths, name, px=128):
    d = os.path.join(paths.data_dir, "icons", "operator", str(px))
    return os.path.join(d, "%s.png" % _safe_name(name))


def _icon_roots(paths):
    """可写目录优先，随后是随包只读目录。

    exe 版里 461 张 128 档头像是打进 ``_MEIPASS`` 的（只读），可写目录
    一开始是空的。以前只认 ``paths.data_dir``，于是 exe 里**每张头像都
    返回 None**，界面全退回文字缩写——源码跑却完全正常，属于典型的
    「打包后才炸」。这里让读取多吃一个只读根，84MB 不必复制一遍。
    """
    roots = [os.path.join(paths.data_dir, "icons", "operator")]
    seed = getattr(paths, "seed_data_dir", None)
    if seed:
        p = os.path.join(seed, "icons", "operator")
        if p not in roots:
            roots.append(p)
    return roots


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


#: 进程内已缩放好的小图缓存：{(name, px): Image}。
#:
#: 为什么需要它：磁盘上只有 ``operator/128`` 这一档（461 张），但选择器
#: 要 24×24、右键菜单要 32×32。旧实现 ``load_icon(paths, name, 24)`` 会
#: 去找 ``operator/24/<name>.png``，那个目录根本不存在，于是**每一张都
#: 返回 None**——UI 看起来「已经改成头像了」，实际全退回文字缩写。
#: 现在改成：目标尺寸没有就挑一张现成的缩放，并按 (name, px) 记住结果，
#: 避免每次重建列表都重新缩放 400 多次。
_scaled_cache: dict = {}
_SCALED_MAX = 1024


def _available_px(paths) -> list:
    """磁盘上真实存在的尺寸档，按「离常用尺寸近」排序。"""
    out = set()
    for base in _icon_roots(paths):
        try:
            for d in os.listdir(base):
                if not d.isdigit():
                    continue
                p = os.path.join(base, d)
                if os.path.isdir(p) and any(
                        f.lower().endswith(".png") for f in os.listdir(p)):
                    out.add(int(d))
        except Exception:
            continue
    # 优先用不小于目标的档位（缩小比放大会好看），同档内取最小
    return sorted(out)


def _load_any_size(paths, name):
    """按任意可用尺寸找这张图，返回 (Image, 原始 px) 或 (None, 0)。"""
    from PIL import Image
    safe = _safe_name(name)
    if not safe:
        return None, 0
    for px in _available_px(paths):
        for base in _icon_roots(paths):
            p = os.path.join(base, str(px), "%s.png" % safe)
            if os.path.isfile(p):
                try:
                    return Image.open(p).convert("RGBA"), px
                except Exception:
                    continue
    return None, 0


def load_icon(paths, name, px=128):
    """只读本地缓存，绝不联网（UI 线程安全，不会卡）。

    目标尺寸没有缓存图时，取一张现成的缩放过去；都没有返回 None。
    这样 ``px=24`` 的小头像也能用上磁盘上的 128 档，不会全变文字。
    """
    try:
        from PIL import Image
    except ImportError:
        return None
    key = (name or "", int(px))
    hit = _scaled_cache.get(key)
    if hit is not None:
        return hit.copy()
    p = icon_path(paths, name, px)
    if os.path.isfile(p):
        try:
            im = Image.open(p).convert("RGBA")
            if len(_scaled_cache) < _SCALED_MAX:
                _scaled_cache[key] = im.copy()
            return im
        except Exception:
            try:
                os.remove(p)
            except OSError:
                pass
    im, got_px = _load_any_size(paths, name)
    if im is None:
        return None
    try:
        if got_px and got_px != int(px):
            im = im.resize((int(px), int(px)), Image.LANCZOS)
    except Exception:
        return None
    if len(_scaled_cache) < _SCALED_MAX:
        _scaled_cache[key] = im.copy()
    return im


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
    # 随包只读目录里已有就不必再联网（exe 版 461 张头像都在 _MEIPASS）
    for base in _icon_roots(paths)[1:]:
        sp = os.path.join(base, str(px), "%s.png" % _safe_name(name))
        if os.path.isfile(sp):
            try:
                from PIL import Image
                im = Image.open(sp).convert("RGBA")
                if on_done:
                    on_done(im)
                return
            except Exception:
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