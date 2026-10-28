"""PRTS Map 等效地图数据抓取与解析。

关于数据源的重要说明
--------------------
`map.prts.wiki` 子站已不可访问（DNS 无法解析），PRTS 的关卡页面本身
也不包含任何格点数据（仅有地图尺寸、敌人情报与关卡装置）。
因此本模块改用 **PRTS.Map 当初所渲染的同一份游戏原始数据**：

    https://github.com/Kengxxiao/ArknightsGameData
    zh_CN/gamedata/levels/obt/<章节>/level_<关卡>.json

这份数据是客户端解包结果，字段与 PRTS.Map 展示的完全一致
（mapData.map / tiles / passableMask / routes / options 等），
所以渲染出来的地图与 PRTS.Map 相同。

下载策略
--------
GitHub 的 contents API 对 >1MB 的文件返回空 content，
故大文件走 git/blobs API（按 sha 取 base64）。
"""
from __future__ import annotations

import base64
import json
import os
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from . import net
from .models import (GameMap, Route, RoutePoint, Tile, WAIT_SENTINEL_MIN,
                     checkpoint_kind, clamp_wait_time, motion_mode_name)

GH_API = "https://api.github.com/repos/Kengxxiao/ArknightsGameData"
GH_HEADERS = {"Accept": "application/vnd.github+json"}

#: 免鉴权的裸文件通道。api.github.com 匿名额度很低（60 次/小时），
#: 一旦限流就整体不可用；raw.githubusercontent.com 没有这个限制，
#: 因此**优先走 raw**，API 只作为目录列举的兜底。
GH_RAW = "https://raw.githubusercontent.com/Kengxxiao/ArknightsGameData/master"
GH_OBT = "zh_CN/gamedata/levels/obt"

#: 关卡文件所在的分类目录
LEVEL_CATEGORIES = [
    "main", "hard", "activities", "campaign", "crisis", "guide",
    "legion", "memory", "promote", "recalrune", "roguelike", "rune",
    "sandbox", "training", "weekly",
]

CACHE_VERSION = 1

#: 所有「敌人进场」门类型，来自 mapData.tiles 的 tileKey。
#: 老数据只用 tile_start，新章节 / 联机 / 其他玩法又加了一批变体，
#: 只认 tile_start 会导致这些图一个红门都画不出来。
SPAWN_KEYS = {
    "tile_start",              # 普通红门
    "tile_flystart",           # 无人机专用入场点
    "tile_start_cooperate",    # 联机协作关
    "tile_start_dqq",           # 特殊玩法
    "tile_ftstart",            # 足球/技巧关入场
}
#: 所有「防守目标」门类型（蓝门）
GOAL_KEYS = {
    "tile_end",
    "tile_end_cooperate",
    "tile_enemygoal",          # 足球关：敌人要进的球门
    "tile_allygoal",           # 足球关：己方球门
    "tile_end_dqq",
}


# --------------------------------------------------------------- 通行掩码归一化

#: 部分关卡（尤其新章节）的 passableMask 是整数枚举，不是字符串。
#:
#: 它是**位掩码**：bit0 = 地面可走，bit1 = 飞行可过。这个解释由 tileKey
#: 与 mask 的相关性实测标定（全库 25 万格）::
#:
#:   tile_road / tile_floor / tile_start / tile_end / tile_telin / tile_telout
#:       字符串形态一律 ``ALL``，数值形态一律 ``3``  → 3 = ALL
#:   tile_forbidden / tile_wall
#:       字符串形态一律 ``FLY_ONLY``，数值形态一律 ``2``  → 2 = FLY_ONLY
#:
#: 所以 0/1/2/3 必须依次是 NONE / WALK_ONLY / FLY_ONLY / ALL。
#: 早期版本把 3 映射成 ``NONE``、把 0 映射成 ``ALL``，导致 102 个老活动关
#: （act6d5 / act7mini / act10mini / act13mini / act14mini / act1lock …）
#: 的路面全部被判成不可通行——图能画出来，但每条路线都「无法寻路」。
_MASK_BY_INT = {
    0: "NONE", 1: "WALK_ONLY", 2: "FLY_ONLY", 3: "ALL",
}


#: 高度枚举。和 passableMask 一样，早期关卡的 heightType 是整数：
#: 0 = LOWLAND（地面），1 = HIGHLAND（高台）。全库合计 9066 格这样写。
_HEIGHT_BY_INT = {0: "LOWLAND", 1: "HIGHLAND"}

#: 可部署类型枚举。同样有数值形态（全库 9066 格），由 tileKey 相关性标定：
#: tile_forbidden/tile_floor/tile_start → 'NONE' 对应 0；tile_road → 'MELEE'
#: 对应 1；tile_wall → 'RANGED' 对应 2；其余高台可放 → 'ALL' 对应 3。
_BUILD_BY_INT = {0: "NONE", 1: "MELEE", 2: "RANGED", 3: "ALL"}


def _norm_height(v) -> str:
    """把客户端的 heightType 归一化成 LOWLAND / HIGHLAND / DEEPWATER / WALL / NONE。

    归一化必须放在解析层而不是渲染层：身高类型会被寻路（能不能走）、
    部署（能不能放干员）、渲染（配色）三处同时用到，任何一处漏改都会
    出现「图能画出来但路算不对」。上层只要拿到的永远是字符串就不会再
    踩这个坑。
    """
    if isinstance(v, bool):
        return "LOWLAND"
    if isinstance(v, int):
        return _HEIGHT_BY_INT.get(v, "LOWLAND")
    s = str(v or "").strip().upper()
    if s.isdigit():
        return _HEIGHT_BY_INT.get(int(s), "LOWLAND")
    return s or "LOWLAND"


def _norm_buildable(v) -> str:
    """把客户端的 buildableType 归一化成 NONE / MELEE / RANGED / ALL。

    老关卡的 buildableType 是整数枚举（全库 9066 格）。不归一化的话
    ``Tile.buildable_melee`` / ``buildable_ranged`` 里的 ``in ("MELEE","ALL")``
    全都判 False，表现是「图能画出来、路也算得通，但任何一个格子都部署不了
    干员」。映射由 tileKey 相关性标定：tile_road 的 'MELEE' 对应 1、
    tile_wall 的 'RANGED' 对应 2、tile_forbidden/floor 的 'NONE' 对应 0。
    """
    if isinstance(v, bool):
        return "ALL" if v else "NONE"
    if isinstance(v, int):
        return _BUILD_BY_INT.get(v, "NONE")
    s = str(v or "").strip().upper()
    if not s:
        return "NONE"
    if s.isdigit():
        return _BUILD_BY_INT.get(int(s), "NONE")
    if s in ("MELEE", "RANGED", "ALL", "NONE"):
        return s
    return "NONE"


def _norm_passable(mask) -> str:
    """把客户端的 passableMask 归一化成 ALL / WALK_ONLY / FLY_ONLY / NONE。

    注意 mask 可能是 str，也可能是 int——新章节数据里用的是整数枚举。
    旧代码直接 .upper()，碰到整数就抛 AttributeError，整张图加载失败。
    """
    if isinstance(mask, bool):
        mask = int(mask)
    if isinstance(mask, int):
        return _MASK_BY_INT.get(mask, "ALL")
    mask = str(mask or "").upper()
    if mask.isdigit():
        return _MASK_BY_INT.get(int(mask), "ALL")
    if mask in ("WALK_AND_FLY", "ALL", ""):
        return "ALL"
    if mask == "WALK_ONLY":
        return "WALK_ONLY"
    if mask == "FLY_ONLY":
        return "FLY_ONLY"
    if mask == "NONE":
        return "NONE"
    return "ALL"


# --------------------------------------------------------------- 解析

def parse_level(data: dict, level_id: str = "") -> GameMap:
    """把关卡 JSON 解析成 GameMap。"""
    map_data = data.get("mapData") or {}
    matrix: List[List[int]] = map_data.get("map") or []
    tiles_raw: List[dict] = map_data.get("tiles") or []

    # ------------------------------------------------------------------
    # 重要：`map` 矩阵的行序是**自下而上**（第 0 行 = 地图最下面一行），
    # 而 `routes` 里的 startPosition / checkpoints 坐标是**自上而下**
    # （row 0 = 最上面一行，与 PRTS.Map 显示一致）。
    #
    # 若不翻转，出怪口与目标点会错位到地图另一侧，表现为大量路线不可达。
    # 实测（26 个内置关卡、828 条路线）：
    #   不翻转 -> 696/828 可达；翻转 -> 828/828 可达，且无任何关卡变差。
    # ------------------------------------------------------------------
    matrix = list(reversed(matrix))

    gm = GameMap(level_id=level_id or data.get("levelId", ""))
    gm.name = data.get("name") or level_id
    gm.options = data.get("options") or {}
    gm.tile_defs = tiles_raw

    height = len(matrix)
    width = max((len(r) for r in matrix), default=0)
    gm.height = height
    gm.width = width

    for r in range(height):
        row: List[Tile] = []
        for c in range(width):
            idx_list = matrix[r] if r < len(matrix) else []
            idx = idx_list[c] if c < len(idx_list) else -1
            if 0 <= idx < len(tiles_raw):
                td = tiles_raw[idx]
                tile = Tile(
                    row=r, col=c,
                    tile_key=td.get("tileKey", ""),
                    height_type=_norm_height(td.get("heightType", "LOWLAND")),
                    buildable_type=_norm_buildable(td.get("buildableType", "NONE")),
                    passable_mask=_norm_passable(td.get("passableMask", "ALL")),
                    def_index=idx,
                )
            else:
                tile = Tile(row=r, col=c, tile_key="", passable_mask="NONE")
            row.append(tile)
        gm.tiles.append(row)

    # ---- 真实门格
    # tiles 里的 tile_start / tile_end 才是地图上画着的红门 / 蓝门。
    # 之前用「路线起点/终点」代替，会同时出现两个问题：
    #   1) 多条路线共用同一格，方框被反复覆盖，颜色互相打架；
    #   2) 路线端点常常在门格外面一格（怪是从门外走进来的），看着就错位。
    # 这里直接从 tiles 收集，渲染层只按这份数据画框。
    for r in range(height):
        for c in range(width):
            k = gm.tiles[r][c].tile_key
            if k in SPAWN_KEYS:
                gm.spawn_tiles.append((r, c))
            elif k in GOAL_KEYS:
                gm.goal_tiles.append((r, c))

    # ---- 路线
    # 注意：motionMode=E_NUM 是剧情/占位路线（起点终点均为 (0,0)），
    # 并无可走路径，需要过滤，否则会误导寻路分析。
    for i, rt in enumerate(data.get("routes") or []):
        # 部分关卡（迷你游戏等）的 routes 里混着 null 占位元素，
        # 直接 rt.get 会抛 AttributeError 让整张图加载失败。
        if not isinstance(rt, dict):
            continue
        if str(rt.get("motionMode", "")).upper() == "E_NUM":
            continue
        r = _parse_route(rt, i)
        r.index = i
        gm.routes.append(r)
    for i, rt in enumerate(data.get("extraRoutes") or []):
        if not isinstance(rt, dict):
            continue
        if str(rt.get("motionMode", "")).upper() == "E_NUM":
            continue
        r = _parse_route(rt, 1000 + i)
        r.index = 1000 + i
        gm.routes.append(r)
    return gm


def _parse_route(rt: dict, index: int) -> Route:
    sp = rt.get("startPosition") or {}
    ep = rt.get("endPosition") or {}
    off = rt.get("spawnOffset") or {}
    route = Route(
        motion_mode=motion_mode_name(rt.get("motionMode", "WALK")),
        start=(int(sp.get("row", 0)), int(sp.get("col", 0))),
        end=(int(ep.get("row", 0)), int(ep.get("col", 0))),
        allow_diagonal_move=bool(rt.get("allowDiagonalMove", True)),
        spawn_offset=(float(off.get("x", 0.0) or 0.0),
                      float(off.get("y", 0.0) or 0.0)),
    )
    for cp in rt.get("checkpoints") or []:
        pos = cp.get("position") or {}
        ro = cp.get("reachOffset") or {}
        raw_wait = float(cp.get("time", 0.0) or 0.0)
        route.checkpoints.append(RoutePoint(
            row=float(pos.get("row", 0)),
            col=float(pos.get("col", 0)),
            kind=checkpoint_kind(cp.get("type", "MOVE")),
            wait_time=clamp_wait_time(raw_wait),
            wait_sentinel=raw_wait >= WAIT_SENTINEL_MIN,
            reach_offset=(float(ro.get("x", 0.0) or 0.0),
                          float(ro.get("y", 0.0) or 0.0)),
        ))
    return route


# --------------------------------------------------------------- 下载

def list_level_files(category: str) -> List[str]:
    """列出某分类目录下的关卡文件名。

    只有 contents API 能列举目录，而它匿名额度很低（60 次/小时），
    限流时返回空列表——此时请直接用 ``download_level`` 按已知 ID 探测，
    raw 通道不受这个限制。
    """
    url = f"{GH_API}/contents/{GH_OBT}/{category}"
    try:
        entries = net.fetch_json(url, headers=GH_HEADERS, tries=2)
    except net.FetchError:
        return []
    if not isinstance(entries, list):
        return []
    return [e["name"] for e in entries
            if e.get("type") == "file" and e.get("name", "").endswith(".json")]


def download_level(level_id: str, category: str = "main",
                   rel_path: str = "") -> dict:
    """下载单个关卡 JSON。

    路径规则由 catalog 推断（活动关在 levels/activities/<活动>/，
    其余在 levels/obt/<分类>/），走 jsDelivr 裸文件通道——比 GitHub
    API 稳定，也不会撞速率限制。
    """
    from . import gamedata as GD
    from .catalog import guess_path

    candidates = []
    if rel_path:
        candidates.append(rel_path)
    guessed = guess_path(level_id, "", "")
    if guessed not in candidates:
        candidates.append(guessed)
    # 老规则兜底：按 level_id 前缀猜 obt 目录
    prefixes = []
    if "_" in level_id:
        prefixes.append(level_id.split("_", 1)[0])
    if category and category not in prefixes:
        prefixes.append(category)
    for pref in prefixes:
        full = level_id if level_id.startswith(pref + "_") else "%s_%s" % (pref, level_id)
        rel = "levels/obt/%s/level_%s.json" % (pref, full)
        if rel not in candidates:
            candidates.append(rel)
    # 活动关：把 stageId 前缀当目录名再试一次
    if "_" in level_id:
        head = level_id.split("_", 1)[0]
        rel = "levels/activities/%s/level_%s.json" % (head, level_id)
        if rel not in candidates:
            candidates.append(rel)

    tried = []
    for rel in candidates:
        tried.append(rel)
        try:
            return GD.fetch_json(rel, timeout=120, tries=2)
        except Exception:
            continue
    raise net.FetchError(
        "关卡不存在或无法访问: %s（已尝试 %d 个路径）" % (level_id, len(tried)))


# --------------------------------------------------------------- 缓存

@dataclass
class LevelCache:
    """关卡数据的本地缓存（存原始 JSON）。"""

    root: str

    def _path(self, level_id: str) -> str:
        safe = level_id.replace("/", "_").replace("\\", "_")
        return os.path.join(self.root, f"{safe}.json")

    def load(self, level_id: str) -> Optional[dict]:
        p = self._path(level_id)
        try:
            with open(p, "r", encoding="utf-8") as f:
                return json.load(f)
        except (OSError, ValueError):
            return None

    def save(self, level_id: str, data: dict) -> None:
        os.makedirs(self.root, exist_ok=True)
        try:
            with open(self._path(level_id), "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False)
        except OSError:
            pass

    def list_cached(self) -> List[str]:
        try:
            return sorted(n[:-5] for n in os.listdir(self.root) if n.endswith(".json"))
        except OSError:
            return []


def get_level(level_id: str, category: str = "main",
              cache: Optional[LevelCache] = None,
              rel_path: str = "") -> Optional[GameMap]:
    """获取并解析关卡，优先走本地缓存。

    磨难/突袭变体的 stage_id 形如 ``main_00-01#f#``，游戏数据仓库里并没有
    对应的独立文件（``#`` 在 URL 里是锚点，请求必然失败），而它的地形与
    出怪和普通版一致。所以带 ``#`` 的关卡先直接命中普通版，失败了再按
    原 id 试一次，避免用户选到这类关卡时白屏。

    **缓存键统一用 rel_path**（拿得到的话）。肉鸽关卡一个 levelId 对应
    多张地图（换皮图），1033 个 stage_id 只映射到 638 个文件；如果按
    stage_id 存，同一张图会被重复下载多次，而且 ``list_cached()`` 返回
    的是文件名，跟 stage_id 永远对不上——列表里明明下过却全显示 ○。
    """
    fallback = level_id.split("#", 1)[0] if "#" in level_id else ""

    def _key(rel: str, sid: str) -> str:
        """缓存键：优先用地图相对路径，退回落 stage_id。

        注意要去掉 ``.json`` 后缀——``LevelCache._path`` 自己会加，
        传 ``levels/.../x.json`` 进去会变成 ``x.json.json``，
        于是所有缓存都读不中、每次重新下载。
        """
        k = rel or sid
        if k.endswith(".json"):
            k = k[:-5]
        return k

    # 候选缓存键：rel_path 优先，其次 stage_id（兼容旧缓存布局）
    keys: List[str] = []
    if rel_path:
        keys.append(_key(rel_path, level_id))
    keys.append(level_id)
    if fallback:
        if rel_path:
            keys.append(_key(rel_path.split("#", 1)[0], fallback))
        keys.append(fallback)

    data: Optional[dict] = None
    used_key = ""
    if cache:
        for k in keys:
            data = cache.load(k)
            if data is not None:
                used_key = k
                break
    if data is None:
        target_id, target_rel = level_id, rel_path
        if fallback:
            target_id = fallback
            target_rel = rel_path.split("#", 1)[0] + ".json" if rel_path else ""
        try:
            data = download_level(target_id, category, rel_path=target_rel)
        except net.FetchError:
            return None
        if cache:
            # 按 rel_path 落盘，和批量下载/别的关卡共用同一份
            cache.save(_key(target_rel or rel_path, level_id), data)
    elif cache and used_key != _key(rel_path, level_id):
        # 老布局（stage_id 命名）命中：顺手写成 rel_path 键，
        # 这样下次 list_cached() 也能认出来
        try:
            cache.save(_key(rel_path, level_id), data)
        except Exception:
            pass
    return parse_level(data, level_id)


# --------------------------------------------------------------- 内置关卡清单

#: 常用关卡，供 UI 直接选择（避免每次列目录）
COMMON_LEVELS: List[Tuple[str, str, str]] = [
    ("main_01-07", "main", "1-7 暴君"),
    ("main_01-12", "main", "1-12 代价"),
    ("main_02-10", "main", "2-10 黄沙"),
    ("main_03-08", "main", "3-8 最后一只巨兽"),
    ("main_04-04", "main", "4-4 无法阻挡"),
    ("main_04-07", "main", "4-7 灯火将熄"),
    ("main_04-10", "main", "4-10 玉碎"),
    ("main_05-03", "main", "5-3 恶客盈门"),
    ("main_05-07", "main", "5-7 生死与共"),
    ("main_05-10", "main", "5-10 长夜终尽"),
    ("main_06-05", "main", "6-5 解决方式"),
    ("main_06-11", "main", "6-11 一笔勾销"),
    ("main_07-04", "main", "7-4 并肩"),
    ("main_07-09", "main", "7-9 阴谋"),
    ("main_07-16", "main", "7-16 无匹"),
    ("main_08-05", "main", "8-5 铜墙铁壁"),
    ("main_08-11", "main", "8-11 狂徒"),
    ("main_09-07", "main", "9-7 坚壁"),
    ("main_09-12", "main", "9-12 固守"),
    ("main_09-13", "main", "9-13 以暴制暴"),
    ("main_10-05", "main", "10-5 沙盘"),
    ("main_10-11", "main", "10-11 观火"),
    ("main_11-05", "main", "11-5 静默"),
    ("main_11-12", "main", "11-12 抉择"),
    ("main_12-05", "main", "12-5 见证"),
    ("main_12-17", "main", "12-17 醒来"),
    ("main_13-05", "main", "13-5 潜行"),
    ("hard_11-01", "hard", "H11-1"),
    ("hard_12-01", "hard", "H12-1"),
]