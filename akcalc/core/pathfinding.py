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


def _raycast_clear(
    game_map: GameMap,
    a: Coord,
    b: Coord,
    flying: bool,
    blocked: set,
    force_open: set,
    allow_obstacle: bool,
) -> bool:
    """Bresenham 射线检测：a→b 直线上的每个格是否可通行。

    游戏的 SPFA._RaycastBresenhamLine / _RaycastSegmentLine 用 Bresenham
    直线算法检测线段经过的格子，再用 _CheckRectangeAllClear 检查
    矩形区域（RAYCAST_THICKNESS_HALF = _halfBodyWidth）是否全部清空。

    这里用 Bresenham 直线检测 + 穿角检测：
    - 遍历 a→b 直线上的每个格，不可通行的格阻挡射线
    - 斜向跨格时，两个正交格都必须可通行（身体宽度不能穿过墙角）
    """
    r0, c0 = a
    r1, c1 = b
    dr = abs(r1 - r0)
    dc = abs(c1 - c0)
    sr = 1 if r1 > r0 else -1
    sc = 1 if c1 > c0 else -1
    err = dc - dr
    r, c = r0, c0
    prev_r, prev_c = r0, c0
    first = True
    while True:
        if (r, c) != a and (r, c) != b:
            if (r, c) in blocked:
                return False
            tile = game_map.tile_at(r, c)
            if (r, c) not in force_open:
                if not can_enter(tile, flying, allow_obstacle):
                    return False
                if not flying and tile and is_hole(tile):
                    return False
        # 检测斜向跨格时的穿角
        if not first and r != prev_r and c != prev_c:
            t1 = game_map.tile_at(prev_r, c)
            t2 = game_map.tile_at(r, prev_c)
            if not flying:
                if t1 and (not can_enter(t1, flying, allow_obstacle) or is_hole(t1)):
                    if (prev_r, c) not in force_open:
                        return False
                if t2 and (not can_enter(t2, flying, allow_obstacle) or is_hole(t2)):
                    if (r, prev_c) not in force_open:
                        return False
        first = False
        prev_r, prev_c = r, c
        if (r, c) == (r1, c1):
            break
        e2 = 2 * err
        if e2 > -dr:
            err -= dr
            c += sc
        if e2 < dc:
            err += dc
            r += sr
    return True


def _smooth_path(
    game_map: GameMap,
    path: List[Coord],
    flying: bool,
    blocked: set,
    force_open: set,
    allow_obstacle: bool,
) -> List[Coord]:
    """路径平滑（_PostprocessAndMakeNextMapSmoothly 等价）。

    对路径上每对 (i, i+k) 节点，如果 a→b 的直线射线无阻挡，
    则移除中间的 k-1 个节点。从最远的可行对开始贪心处理。

    这模拟游戏的 SPFA 后处理：原始 NextMap 是逐格的，
    后处理用射线检测合并可直线到达的节点，形成长直线段。
    """
    if len(path) <= 2:
        return path
    result = [path[0]]
    i = 0
    while i < len(path) - 1:
        # 从最远的节点开始找可直线到达的目标
        j = len(path) - 1
        while j > i + 1:
            if _raycast_clear(game_map, path[i], path[j], flying,
                              blocked, force_open, allow_obstacle):
                break
            j -= 1
        result.append(path[j])
        i = j
    return result


def find_path(
    game_map: GameMap,
    start: Coord,
    goal: Coord,
    flying: bool = False,
    allow_diagonal: bool = True,
    blocked: Optional[set] = None,
    allow_obstacle: bool = False,
    force_open: Optional[set] = None,
    no_corner_cut: bool = True,
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
    no_corner_cut: 斜向移动时禁止「穿角」。默认开启。

        游戏的 SPFA 使用带身体宽度 (_halfBodyWidth) 的射线检测
        (_RaycastSegmentLine / _CheckRectangeAllClear) 来判定通行，
        因此斜走穿过墙/禁入区的角是不允许的。
        RAYCAST_THICKNESS_HALF 常量确保射线有厚度，不是无限细的线。

    说明
    ----
    游戏实际是 SPFA，但带非负权最短路与 Dijkstra 结果等价，
    这里用堆优化 Dijkstra 以保证 O(E log V) 性能。
    寻路完成后会做路径平滑（_PostprocessAndMakeNextMapSmoothly 等价），
    用射线检测合并可直线到达的节点。
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
            # 穿角检测始终执行（即使目标格在 force_open 中）。
            # force_open 只让敌人进入被标为 forbidden 的出怪口/蓝门，
            # 不应该让敌人斜穿墙角到达这些格。
            if dr and dc and not flying:
                t1 = game_map.tile_at(r, nc)
                t2 = game_map.tile_at(nr, c)
                if no_corner_cut:
                    if not (can_enter(t1, flying) and can_enter(t2, flying)):
                        continue
                # 地穴角始终不能穿
                if t1 and is_hole(t1):
                    continue
                if t2 and is_hole(t2):
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

    # 路径平滑（_PostprocessAndMakeNextMapSmoothly 等价）
    #
    # 游戏的 SPFA 在生成 NextMap 后做后处理：用 _RaycastSegmentLine
    # 检测路径上两个非相邻节点之间能否直线到达，如果可以就跳过中间节点。
    # _RaycastSegmentLine 使用 Bresenham 直线算法 + RAYCAST_THICKNESS_HALF
    # 检测线段上每个格子是否可通行。
    #
    # 这里用相同逻辑：对路径上每对 (i, i+k) 节点，检测能否直线到达，
    # 如果可以就移除中间节点。从远到近贪心处理。
    path = _smooth_path(game_map, path, flying, blocked, force_open,
                        allow_obstacle)

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


def stalled_escape_speed(move_speed: float,
                         move_multiplier: float = C.MOVE_MULTIPLIER_DEFAULT) -> float:
    """寻路断绝时，敌人离开当前格的匀速速度（格/秒）。

    游戏内避障力 = max(实际移速 / 理论移速, 0.5)，
    寻路加速度 = (目标移速 - 实际移速) * 8。
    寻路断绝时目标移速 = 0，所以：
        0.5 = (0 - v) * 8  =>  v = 0.0625
    对移速 > 0.25 的敌人，该值为常数 0.0625 格/秒。
    """
    return C.AVOID_FORCE_MIN / C.AVOID_ACCEL_COEF


def _obstacle_nearby(game_map: GameMap, r: int, c: int,
                     flying: bool, radius: int = 1) -> bool:
    """检查格子 (r,c) 周围 radius 格内是否有类障碍物地块。

    游戏的避障力计算会检测敌人脚下的格子周围是否有障碍物，
    有则施加转向力减慢移速。这里简化为布尔检测。
    """
    for dr in range(-radius, radius + 1):
        for dc in range(-radius, radius + 1):
            if dr == 0 and dc == 0:
                continue
            t = game_map.tile_at(r + dr, c + dc)
            if t and is_obstacle(t):
                return True
    return False


def travel_time_with_avoid(
    game_map: GameMap,
    path: List[Coord],
    move_speed: float,
    move_multiplier: float = C.MOVE_MULTIPLIER_DEFAULT,
    flying: bool = False,
) -> float:
    """计算路径行走时间，考虑避障力对移速的影响。

    游戏的 MoveController 每帧计算避障力：
    - 路径上每格周围有类障碍物时，敌人移速降低
    - 避障力 = max(actual_speed / theoretical_speed, 0.5)
    - 实际移速 = theoretical_speed * (1 - avoid_force * steering_factor)

    简化模型：路径经过的每一格，如果周围 1 格内有障碍物，
    则该格的行走速度乘以避障系数 0.7（中等减速）。
    """
    return sum(edge_times_with_avoid(game_map, path, move_speed,
                                     move_multiplier, flying))


def edge_times_with_avoid(
    game_map: GameMap,
    path: List[Coord],
    move_speed: float,
    move_multiplier: float = C.MOVE_MULTIPLIER_DEFAULT,
    flying: bool = False,
) -> List[float]:
    """逐边行走耗时（秒），供 pose_at 变速插值。

    与 travel_time_with_avoid 同一模型，但不加总——把每条边的耗时
    各自返回，让调用方可以在段内做非匀速推进。
    """
    v = actual_move_speed(move_speed, move_multiplier)
    out: List[float] = []
    if v <= 0 or len(path) < 2:
        return out

    for i in range(1, len(path)):
        r, c = path[i]
        # 几何距离（斜向 sqrt2）
        pr, pc = path[i - 1]
        seg_len = math.hypot(r - pr, c - pc)

        # 检查当前格周围是否有障碍物
        if not flying and _obstacle_nearby(game_map, r, c, flying, radius=1):
            # 避障减速：移速 * 0.7（避障力引起的转向减速）
            eff_v = v * 0.7
        else:
            eff_v = v

        if eff_v <= 0:
            out.append(float("inf"))
        else:
            out.append(seg_len / eff_v)
    return out


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
            # 用考虑避障力的行走时间（路径经过障碍物附近会减速）
            t = travel_time_with_avoid(game_map, pr.path, move_speed, mul, flying)
            seg["time"] = t
            tm.move_time += t
            tm.total_length += pr.length
        else:
            # 寻路断绝：敌人以停滞逃逸速度（0.0625 格/秒）匀速爬向目标
            if tm.failed_segment < 0:
                tm.failed_segment = i
            dist = distance(cur, nxt)
            escape_v = stalled_escape_speed(move_speed, mul)
            if escape_v > 0:
                t = dist / escape_v
                seg["time"] = t
                tm.move_time += t
                tm.total_length += dist
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