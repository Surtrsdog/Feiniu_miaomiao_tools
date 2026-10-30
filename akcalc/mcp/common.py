"""MCP 数据层：共用的运行环境与缓存。

外接 AI 每次调用工具都重建 EnemyLibrary（15MB JSON）会慢到不可用，所以
这里做进程内单例：第一次用到才加载，之后复用。

``Paths`` 用 ``default()``——和 GUI 完全同一套缓存目录。好处是用户在
软件里点过「下载敌人库」，MCP 立刻就能读到同一份数据，不需要再下一遍。
"""
from __future__ import annotations

import os
import threading
from typing import Any, Dict, Optional

_lock = threading.Lock()
_state: Dict[str, Any] = {}


def paths():
    """返回 Paths 单例，并**确保内置种子数据已落到可写目录**。

    这一步不能省。打包版把 operators.json / enemy_database.json /
    enemy_attack_timing.json 等种子数据放在 ``_MEIPASS`` 里，要靠
    ``Paths.ensure()`` → ``seed_if_needed()`` 复制到可写目录才能读。

    GUI 启动时自然会调 ``ensure()``，但 MCP 模式**不经过 GUI**：
    用户装完就在客户端里配置 MCP、从没手动打开过软件的话，
    可写目录里一个数据文件都没有，于是所有工具都报
    「敌人库还没下载」——而用户根本不知道该去哪里点那个按钮。

    实测就是这个问题：全新安装 + 直接跑 ``--mcp``，
    ``enemy_attack_timing`` / ``operator_professions`` / ``map_get`` 全失败。
    """
    from ..core.paths import Paths
    with _lock:
        p = _state.get("paths")
        if p is None:
            p = Paths.default()
            try:
                p.ensure()          # 建目录 + 首次运行时复制种子数据
            except OSError:
                pass                # 只读环境：退化成「只有包内数据可用」
            _state["paths"] = p
        return p


def enemy_lib():
    """全局敌人库。没缓存文件时返回未加载的实例（工具里会报错提示）。"""
    from ..core.enemies import EnemyLibrary
    with _lock:
        lib = _state.get("enemy_lib")
        if lib is not None:
            return lib
    lib = EnemyLibrary(paths().enemies_cache)
    lib.load_cached()
    with _lock:
        _state["enemy_lib"] = lib
    return lib


def handbook():
    from ..core.handbook import HandbookIndex
    with _lock:
        hb = _state.get("handbook")
        if hb is not None:
            return hb
    # paths.handbook_cache 本身就是**完整文件路径**，不是目录。
    # 再拼一次文件名会变成 ...\enemy_handbook_table.json\enemy_handbook_table.json，
    # 文件不存在 → HandbookIndex 静默 load 失败 → 图鉴天赋整片空白。
    cand = paths().handbook_cache
    if not os.path.isfile(cand):
        # 兜底：万一未来改成目录语义
        alt = os.path.join(paths().cache_dir, "enemy_handbook_table.json")
        if os.path.isfile(alt):
            cand = alt
    hb = HandbookIndex(cand)
    hb.load()
    with _lock:
        _state["handbook"] = hb
    return hb


def operator_cache():
    with _lock:
        c = _state.get("op_cache")
        if c is not None:
            return c
    from ..core.prts_operator import OperatorCache
    c = OperatorCache.load(paths().operators_cache)
    with _lock:
        _state["op_cache"] = c
    return c


def op_index():
    """``OperatorIndex``：给「按职业/星级筛选」用。"""
    with _lock:
        idx = _state.get("op_index")
        if idx is not None:
            return idx
    from ..core.op_index import OperatorIndex
    data = operator_cache().data
    idx = OperatorIndex.from_cache(data)
    with _lock:
        _state["op_index"] = idx
    return idx


def catalog() -> Dict[str, Any]:
    with _lock:
        c = _state.get("catalog")
        if c is not None:
            return c
    import json
    p = os.path.join(paths().data_dir, "catalog.json")
    try:
        with open(p, "r", encoding="utf-8") as f:
            d = json.load(f)
    except (OSError, ValueError):
        d = {}
    with _lock:
        _state["catalog"] = d
    return d


def require_enemy_lib():
    lib = enemy_lib()
    if not lib.loaded:
        raise RuntimeError(
            "敌人库还没下载。请在「肥牛妙妙工具」里点一次「下载敌人库」"
            "（约 15 MB），或用 mcp 工具 enemy_library_status 看状态。")
    return lib


def require_operators():
    c = operator_cache()
    if not getattr(c, "data", None):
        raise RuntimeError(
            "干员缓存还没建立。请在软件里打开一次干员面板让它抓取，"
            "或用 mcp 工具 operator_library_status 看状态。")
    return c
