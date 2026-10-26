"""寻路计算引擎。

实现依据 PRTS「作战机制 - 敌人类单位行动与坐标」：

* 敌人使用 SPFA 类最短路寻路，始终走最短路径；
  相同路程时优先选择能缩短空间距离的路线。
* 遇到「类障碍物地块」时按寻路代价加权：
     普通障碍物 = 1000，地穴 = 1,000,000
* 地面敌人走地面通行掩码，飞行敌人走飞行通行掩码。
* 移动：每帧位移 = 移速 * moveMultiplier / 帧率。
"""
from __future__ import annotations

import heapq
import math
from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

from . import constants as C
from .models import GameMap, Route, Tile

Coord = Tuple[int, int]

#: 八方向 / 四方向
DIRS_4 = [(-1, 0), (1, 0), (0, -1), (0, 1)]
DIRS_8 = DIRS_4 + [(-1, -1), (-1, 1), (1, -1), (1, 1)]


@dataclass
class PathResult:
    """一次寻路的结果。"""

    path: List[Coord] = field(default_factory=list)
    cost: float = 0.0
    found: bool = False
    steps: int = 0
    #: 路径上除起点外每一格的累计代价与长度
    length: float = 0.0


def is_hole(tile: Tile) -> bool:
    key = (tile.tile_key or "").lower()
    return any(h in key for h in C.HOLE_TILE_HINTS)


def is_obstacle(tile: Tile) -> bool:
    """判断是否属于「类障碍物地块」，需要高寻路代价。"""
    if is_hole(tile):
        return False
    key = (tile.tile_key or "").lower()
    if any(h in key for h in C.OBSTACLE_TILE_HINTS):
        return True
    # 不可通行但非地穴的地块同样视为障碍
    return not (tile.passable_ground or tile.passable_fly)


def tile_enter_cost(tile: Tile, flying: bool = False) -> float:
    """进入某格的寻路代价。

    1 表示正常通行；类障碍物按游戏内权重累加。
    """
    if is_hole(tile):
        return float(C.PATH_COST_HOLE)
    if is_obstacle(tile):
        return float(C.PATH_COST_OBSTACLE)
    # 正常格子代价 1
    return 1.0


def can_enter(tile: Optional[Tile], flying: bool, allow_obstacle: bool = False) -> bool:
    """该单位能否进入此格。"""
    if tile is None:
        return False
    ok = tile.passable_fly if flying else tile.passable_ground
    if ok:
        return True
    return allow_obstacle


def find_path(
    game_map: GameMap,
    start: Coord,
    goal: Coord,
    flying: bool = False,
    allow_diagonal: bool = True,
    blocked: Optional[set] = None,
    allow_obstacle: bool = False,
    force_open: Optional[set] = None,
    no_corner_cut: bool = False,
) -> PathResult:
    """在格网上做加权最短路径搜索（Dijkstra / SPFA 等价实现）。

    参数
    ----
    start / goal: (row, col)
    flying: 是否飞行单位（影响通行掩码）
    allow_diagonal: 是否允许斜向移动
    blocked: 额外禁止进入的格子集合（如已被干员阻挡的格）
    allow_obstacle: 是否允许进入类障碍物地块（用于「强行前往」场景）
    force_open: 强制视为可通行的格子集合。用于「出怪口 / 保护目标点」，
        这类格在数据里常被标成 tile_forbidden + FLY_ONLY（虚空行），
        但敌人实际能从中生成并走入地图。
    no_corner_cut: 斜向移动时是否禁止「穿角」（两个正交格都不可通行）。
        游戏本身没有这条限制，默认关闭；开启可用于更保守的估算。

    说明
    ----
    游戏实际是 SPFA，但带非负权最短路与 Dijkstra 结果等价，
    这里用堆优化 Dijkstra 以保证 O(E log V) 性能。
    """
    blocked = blocked or set()
    force_open = force_open or set()
    res = PathResult()
    if game_map.width <= 0 or game_map.height <= 0:
        return res

    sr, sc = start
    gr, gc = goal
    if not (0 <= sr < game_map.height and 0 <= sc < game_map.width):
        return res
    if not (0 <= gr < game_map.height and 0 <= gc < game_map.width):
        return res

    dirs = DIRS_8 if allow_diagonal else DIRS_4

    def heuristic(r: int, c: int) -> float:
        # 允许斜向时用切比雪夫，否则用曼哈顿，保证可采纳
        dr, dc = abs(r - gr), abs(c - gc)
        return float(max(dr, dc) if allow_diagonal else dr + dc)

    # 起点恒可进入（敌人已在场）
    dist: Dict[Coord, float] = {(sr, sc): 0.0}
    prev: Dict[Coord, Coord] = {}
    hpush = [(heuristic(sr, sc), 0.0, (sr, sc))]
    visited = set()

    goal_reached = False
    while hpush:
        f, d, cur = heapq.heappop(hpush)
        if cur in visited:
            continue
        visited.add(cur)
        if cur == (gr, gc):
            goal_reached = True
            break

        r, c = cur
        for dr, dc in dirs:
            nr, nc = r + dr, c + dc
            if not (0 <= nr < game_map.height and 0 <= nc < game_map.width):
                continue
            nxt = (nr, nc)
            if nxt in visited or nxt in blocked:
                continue
            tile = game_map.tile_at(nr, nc)
            if nxt not in force_open:
                if not can_enter(tile, flying, allow_obstacle):
                    continue
                if no_corner_cut and dr and dc:
                    t1 = game_map.tile_at(r, nc)
                    t2 = game_map.tile_at(nr, c)
                    if not (can_enter(t1, flying) and can_enter(t2, flying)):
                        continue
            w = tile_enter_cost(tile, flying)
            # 斜向距离为 sqrt2
            nd = d + w * (math.sqrt(2.0) if (dr and dc) else 1.0)
            if nd < dist.get(nxt, float("inf")) - 1e-12:
                dist[nxt] = nd
                prev[nxt] = cur
                heapq.heappush(hpush, (nd + heuristic(nr, nc), nd, nxt))

    if not goal_reached:
        return res

    # 回溯
    path = [(gr, gc)]
    node = (gr, gc)
    while node != (sr, sc):
        node = prev[node]
        path.append(node)
    path.reverse()

    res.path = path
    res.cost = dist[(gr, gc)]
    res.found = True
    res.steps = len(path) - 1
    # 几何长度（格）
    length = 0.0
    for a, b in zip(path, path[1:]):
        length += math.hypot(b[0] - a[0], b[1] - a[1])
    res.length = length
    return res


def distance(a: Coord, b: Coord) -> float:
    """两格中心之间的几何距离（格）。"""
    return math.hypot(b[0] - a[0], b[1] - a[1])


# ------------------------------------------------------------- 移动时间

def actual_move_speed(move_speed: float, move_multiplier: float = C.MOVE_MULTIPLIER_DEFAULT) -> float:
    """实际移速（格/秒）。

    游戏内每帧位移 = 移速 * moveMultiplier / 帧率，
    因此每秒位移 = 移速 * moveMultiplier。
    """
    v = move_speed * move_multiplier
    return max(v, C.MOVE_SPEED_MIN * move_multiplier)


def travel_time(length_tiles: float, move_speed: float,
                move_multiplier: float = C.MOVE_MULTIPLIER_DEFAULT) -> float:
    """走完给定距离（格）所需时间（秒），不含停驻。"""
    v = actual_move_speed(move_speed, move_multiplier)
    if v <= 0:
        return float("inf")
    return length_tiles / v


@dataclass
class RouteTiming:
    """一条路线的完整时间线。"""

    total_time: float = 0.0
    move_time: float = 0.0
    wait_time: float = 0.0
    total_length: float = 0.0
    segments: List[dict] = field(default_factory=list)
    #: 若某段无法寻路，记录在第几段
    failed_segment: int = -1


def simulate_route(
    game_map: GameMap,
    route: Route,
    move_speed: float = 1.0,
    flying: bool = False,
    allow_diagonal: bool = True,
    blocked: Optional[set] = None,
) -> RouteTiming:
    """模拟一条路线：累加各段的移动时间与停驻时间。"""
    tm = RouteTiming()
    mul = game_map.move_multiplier

    # 组装路径点序列
    points: List[Coord] = [tuple(route.start)]  # type: ignore[list-item]
    waits: List[float] = [0.0]
    for cp in route.checkpoints:
        points.append((int(round(cp.row)), int(round(cp.col))))
        waits.append(cp.wait_time)
    if not route.checkpoints:
        points.append(tuple(route.end))  # type: ignore[arg-type]
        waits.append(0.0)

    cur = points[0]
    for i in range(1, len(points)):
        nxt = points[i]
        seg_blocked = set(blocked or ())
        pr = find_path(game_map, cur, nxt, flying=flying,
                       allow_diagonal=allow_diagonal, blocked=seg_blocked)
        seg = {
            "from": cur,
            "to": nxt,
            "wait": waits[i],
            "found": pr.found,
            "length": pr.length,
            "time": 0.0,
        }
        if pr.found:
            t = travel_time(pr.length, move_speed, mul)
            seg["time"] = t
            tm.move_time += t
            tm.total_length += pr.length
        else:
            if tm.failed_segment < 0:
                tm.failed_segment = i
        if i < len(waits) - 1 or route.checkpoints:
            tm.wait_time += waits[i]
        tm.segments.append(seg)
        cur = nxt

    tm.total_time = tm.move_time + tm.wait_time
    return tm


# ------------------------------------------------------------- 通行性统计

def passable_grid(game_map: GameMap, flying: bool = False) -> List[List[bool]]:
    """生成通行性矩阵，供绘图与统计。"""
    grid = []
    for r in range(game_map.height):
        row = []
        for c in range(game_map.width):
            t = game_map.tile_at(r, c)
            row.append(bool(t and (t.passable_fly if flying else t.passable_ground)))
        grid.append(row)
    return grid