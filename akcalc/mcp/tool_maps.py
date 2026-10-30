"""MCP 工具：地图与关卡数据。

关卡来源两级：

1. ``akcalc/data/catalog.json`` —— 4521 个关卡的索引（stage_id / 代号 /
   中文名 / 章节 / 玩法分类 / 解包路径）。
2. ``akcalc/data/cache/levels/*.json`` —— 已下载并解析过的地图。本机
   已有 2629 张。没缓存的关卡工具不会自己去下载（外接 AI 不该在用户
   不知情时触发 15MB 流量），而是明确告诉你「先在本体里打开一次」。

地图返回什么
------------
``GameMap`` 有地块矩阵、路线、红门/蓝门。直接倒出全部地块对 AI 太长
（有些图 12×20=240 格），所以默认给「紧凑版」：
地形用字符画，门和可部署位单独列。需要原始矩阵时显式
``include_grid=true``。
"""
from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

from . import common
from .server import ok, error, tool

#: 地形字符画用的映射（与 MapRenderer 的配色语义一致）
_CHAR_HEIGHT = {"LOWLAND": ".", "HIGHLAND": "^", "WALL": "#"}
_CHAR_BUILD = {"MELEE": "m", "RANGED": "r", "ALL": "a", "NONE": ""}


def _stages() -> List[dict]:
    return common.catalog().get("stages") or []


def _find_stage(level_id: str) -> Optional[dict]:
    """按 stage_id / 代号（4-4）/ 中文名找关卡。"""
    if not level_id:
        return None
    q = str(level_id).strip()
    stages = _stages()
    for s in stages:
        if s.get("stage_id") == q:
            return s
    ql = q.lower()
    for s in stages:
        if str(s.get("code") or "").lower() == ql:
            return s
    for s in stages:
        if str(s.get("stage_id") or "").lower() == ql:
            return s
    for s in stages:
        if str(s.get("name") or "") == q:
            return s
    # 模糊
    for s in stages:
        hay = "%s %s %s" % (s.get("code"), s.get("name"),
                            s.get("stage_id"))
        if ql in hay.lower():
            return s
    return None


def _cache_root() -> str:
    return common.paths().levels_cache_dir


def _load_map(stage: dict):
    """从本地缓存读地图；不做网络下载。"""
    from ..core import maps as M
    sid = str(stage.get("stage_id") or "")
    path = str(stage.get("path") or "")
    lc = M.LevelCache(_cache_root())
    gm = M.get_level(level_id=sid, category=str(stage.get("category") or "main"),
                     cache=lc, rel_path=path)
    return gm


def _grid_art(gm) -> List[str]:
    """把地块画成字符画（行 0 在最上方）。"""
    out = []
    for row in gm.tiles:
        line = []
        for t in row:
            if t is None:
                line.append(" ")
                continue
            h = getattr(t, "height_type", "LOWLAND")
            ch = _CHAR_HEIGHT.get(h, "?")
            if ch == ".":
                b = _CHAR_BUILD.get(getattr(t, "buildable_type", "NONE"), "")
                if b:
                    ch = b
            line.append(ch)
        out.append("".join(line))
    return out


def _map_summary(gm) -> Dict[str, Any]:
    """MapSummary 的实际字段（不要凭印象写 reachable/unreachable 之类）。"""
    from ..core import routes as R
    analyses = R.analyze_all(gm, move_speed=1.0)
    sm = R.summarize(gm, analyses)
    return {
        "route_count": sm.route_count,
        "walk_routes": sm.walk_routes,
        "fly_routes": sm.fly_routes,
        "reachable_routes": sm.reachable_routes,
        "min_time": round(sm.min_time, 3),
        "max_time": round(sm.max_time, 3),
        "ground_tiles": sm.ground_count,
        "fly_tiles": sm.fly_count,
    }


@tool(
    "map_catalog_status",
    "关卡索引状态",
    "看关卡索引有多少关、本地缓存了多少张地图、按玩法分类的分布。",
    {"type": "object", "properties": {}, "additionalProperties": False},
)
def map_catalog_status(args: dict) -> dict:
    stages = _stages()
    root = _cache_root()
    n_cached = 0
    if os.path.isdir(root):
        for r, _d, fs in os.walk(root):
            n_cached += len([x for x in fs if x.endswith(".json")])
    from collections import Counter
    cats = Counter(s.get("category") or "?" for s in stages)
    return ok({
        "stages_indexed": len(stages),
        "maps_cached": n_cached,
        "cache_root": root,
        "categories": dict(cats.most_common()),
        "note": ("工具只读本地缓存，不会自行下载。要查没缓存的关卡，"
                 "请先在软件里打开一次该关卡。"),
    })


@tool(
    "map_search",
    "搜索关卡",
    "按代号（4-4）、中文名、stage_id 片段找关卡，返回索引信息。",
    {
        "type": "object",
        "properties": {
            "query": {"type": "string",
                      "description": "代号 / 中文名 / stage_id 片段"},
            "category": {"type": "string",
                         "description": "限定玩法分类，如 main / roguelike / activity"},
            "limit": {"type": "integer", "description": "默认 20",
                      "minimum": 1, "maximum": 200},
        },
        "required": ["query"],
        "additionalProperties": False,
    },
)
def map_search(args: dict) -> dict:
    q = str(args.get("query") or "").strip()
    if not q:
        return error("query 不能为空")
    cat = args.get("category")
    limit = int(args.get("limit") or 20)
    ql = q.lower()
    hits = []
    for s in _stages():
        if cat and str(s.get("category")) != cat:
            continue
        hay = "%s %s %s" % (s.get("code"), s.get("name"), s.get("stage_id"))
        if ql in hay.lower():
            hits.append({
                "stage_id": s.get("stage_id"),
                "code": s.get("code"),
                "name": s.get("name"),
                "category": s.get("category"),
                "group_name": s.get("group_name"),
                "difficulty": s.get("difficulty"),
                "cached": s.get("cached"),
            })
            if len(hits) >= limit:
                break
    return ok({"query": q, "category": cat, "count": len(hits),
               "results": hits})


@tool(
    "map_get",
    "地图详情",
    "拿一张地图：尺寸、地形字符画、红门/蓝门坐标、可部署位、路线概览。"
    "默认不返回完整地块矩阵（用 include_grid=true 才返回）。",
    {
        "type": "object",
        "properties": {
            "level": {"type": "string",
                      "description": "stage_id 或代号，如 main_04-04 / 4-4"},
            "include_grid": {"type": "boolean",
                             "description": "是否返回完整地块矩阵（很大）"},
            "include_routes": {"type": "boolean",
                               "description": "是否返回每条路线的检查点"},
            "move_speed": {"type": "number",
                           "description": "推演用的移动速度倍率，默认 1.0"},
        },
        "required": ["level"],
        "additionalProperties": False,
    },
)
def map_get(args: dict) -> dict:
    lv = str(args.get("level") or "").strip()
    if not lv:
        # 最常见的误用：照着 map_search 传了 query。这里必须点名说清，
        # 否则只会得到「找不到 ''」，让人以为是关卡不存在。
        extra = ""
        if "query" in args:
            extra = (" 你传的是 query，本工具的关卡参数名是 level"
                     "（query 是 map_search 用的）。")
        return error(
            "缺少 level 参数：请传 stage_id 或代号，例如 "
            "{\"level\": \"4-4\"} 或 {\"level\": \"main_04-04\"}。"
            + extra + " 不知道 id 就先调 map_search。")
    stage = _find_stage(lv)
    if not stage:
        return error(
            "关卡索引里找不到：%r。用 map_search 按代号或中文名搜一下，"
            "拿到 stage_id 再来。" % lv)
    gm = _load_map(stage)
    if gm is None:
        return error(
            "关卡 %s 的本地地图缓存不存在。请先在「肥牛妙妙工具」里打开"
            "一次这一关（会自动下载并缓存），然后再调用。"
            % stage.get("stage_id"))

    out: Dict[str, Any] = {
        "stage_id": gm.level_id or stage.get("stage_id"),
        "code": stage.get("code"),
        # parse_level 在关卡 JSON 没 name 字段时用 level_id 兜底，
        # 所以 gm.name 可能等于 "main_04-04"。中文名从 catalog 拿。
        "name": stage.get("name") or gm.name,
        "category": stage.get("category"),
        "group_name": stage.get("group_name"),
        "size": {"rows": gm.height, "cols": gm.width},
        "spawn_tiles": [list(x) for x in gm.spawn_tiles],
        "goal_tiles": [list(x) for x in gm.goal_tiles],
        "options": gm.options,
        # 这三个在 models.GameMap 上是 @property，不是方法——
        # 加括号会 TypeError: 'int' object is not callable
        "life": gm.max_life,
        "initial_cost": gm.initial_cost,
        "max_cost": gm.max_cost,
        "route_count": len(gm.routes),
        "terrain_art": _grid_art(gm),
        "legend": {".": "低地(可站)", "m": "低地可部署(近战)",
                   "r": "低地可部署(远程)", "a": "低地可部署(近战+远程)",
                   "^": "高台", "#": "墙/不可通行", " ": "界外"},
    }

    # 可部署位
    # buildable_melee / buildable_ranged 在 models.Tile 上是 @property，
    # 用 getattr 取到的是 bool，加 () 会 'bool' object is not callable。
    melee, ranged = [], []
    for row in gm.tiles:
        for t in row:
            if t is None:
                continue
            if getattr(t, "buildable_melee", False):
                melee.append([t.row, t.col])
            if getattr(t, "buildable_ranged", False):
                ranged.append([t.row, t.col])
    out["deployable"] = {"melee": melee, "ranged": ranged,
                         "melee_count": len(melee),
                         "ranged_count": len(ranged)}

    # 路线
    routes = []
    for rt in gm.routes:
        item = {
            "index": rt.index,
            "motion_mode": rt.motion_mode,
            "start": list(rt.start),
            "end": list(rt.end),
            "checkpoints": len(rt.checkpoints),
        }
        if args.get("include_routes"):
            item["path"] = [
                {"row": p.row, "col": p.col, "kind": p.kind,
                 "wait": p.wait_time}
                for p in rt.checkpoints
            ]
        routes.append(item)
    out["routes"] = routes

    # 预置装置（trap_027_stone 等）
    devices = []
    for dev in (getattr(gm, "devices", None) or []):
        devices.append({
            "row": dev.row, "col": dev.col,
            "token_key": dev.token_key,
            "alias": dev.alias,
            "category": dev.category,
            "direction": dev.direction,
            "hidden": dev.hidden,
            "block_cnt": dev.block_cnt,
            "max_hp": dev.max_hp,
            "operable": dev.operable,
            "stack_size": dev.stack_size,
        })
    out["devices"] = devices
    out["device_count"] = len(devices)

    if args.get("include_grid"):
        out["grid"] = [
            [{"row": t.row, "col": t.col, "key": t.tile_key,
              "height": t.height_type, "buildable": t.buildable_type,
              "passable": t.passable_mask} if t else None
             for t in row]
            for row in gm.tiles
        ]
    return ok(out)


@tool(
    "map_list",
    "关卡清单",
    "按玩法分类列关卡，或看有哪些分类。用于「列集成战略的所有关卡」。",
    {
        "type": "object",
        "properties": {
            "category": {"type": "string",
                         "description": "main / roguelike / activity / crisis ..."},
            "cached_only": {"type": "boolean",
                            "description": "只要本地已缓存地图的关卡"},
            "query": {"type": "string", "description": "可选名字过滤"},
            "limit": {"type": "integer", "description": "默认 100",
                      "minimum": 1, "maximum": 5000},
        },
        "additionalProperties": False,
    },
)
def map_list(args: dict) -> dict:
    cat = args.get("category")
    cached_only = bool(args.get("cached_only"))
    q = str(args.get("query") or "").strip().lower()
    limit = int(args.get("limit") or 100)

    # 判断哪些 stage 有缓存
    root = _cache_root()
    cached_ids = set()
    if os.path.isdir(root):
        for r, _d, fs in os.walk(root):
            for x in fs:
                if x.endswith(".json"):
                    cached_ids.add(x[:-5])

    rows = []
    for s in _stages():
        if cat and str(s.get("category")) != cat:
            continue
        sid = str(s.get("stage_id") or "")
        rel = str(s.get("path") or "")
        key = rel[:-5] if rel.endswith(".json") else sid
        is_cached = (sid in cached_ids) or (key in cached_ids)
        if cached_only and not is_cached:
            continue
        if q:
            hay = "%s %s %s" % (s.get("code"), s.get("name"), sid)
            if q not in hay.lower():
                continue
        rows.append({
            "stage_id": sid, "code": s.get("code"), "name": s.get("name"),
            "category": s.get("category"), "group_name": s.get("group_name"),
            "difficulty": s.get("difficulty"), "cached": is_cached,
        })
        if len(rows) >= limit:
            break
    return ok({"category": cat, "cached_only": cached_only,
               "returned": len(rows), "results": rows})
