"""寻路 / 路线模拟：把 GameMap + Route 变成可视化用的折线与时间线。

关键点
------
1. 每条 Route 由 start -> checkpoints... -> end 组成。
2. 相邻两点之间用 pathfinding.find_path 求加权最短路。
3. 移动时间 = 几何距离 / (移速 * moveMultiplier)。
   游戏内每帧位移 = 移速 * moveMultiplier / 帧率，故每秒 = 移速 * moveMultiplier。
4. 若某段不可达，标记失败并给出原因（墙/地穴/掩码不符）。

检查点语义（实测自关卡 JSON）
---------------------------
只有 ``MOVE`` 与 ``APPEAR_AT_POS`` 的 ``position`` 带真实坐标；
``WAIT_FOR_SECONDS`` / ``WAIT_CURRENT_FRAGMENT_TIME`` / ``DISAPPEAR``
的 ``position`` 恒为占位值 ``(0, 0)``，绝不能当成途经点——
否则每条带停驻的路线都会「绕经左上角」，表现为大量假不可达。

``APPEAR_AT_POS`` 表示敌人瞬移出现在该点，此段**不计移动路程**；
``DISAPPEAR`` 表示敌人当场离场，其后不再有位移贡献。
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple

from . import constants as C
from . import pathfinding as PF
from .models import GameMap, Route

Coord = Tuple[int, int]


@dataclass
class Node:
    """路线节点（内部用）。"""

    pos: Coord
    wait: float = 0.0
    teleport: bool = False       # 该节点由 APPEAR_AT_POS 瞬移到达
    vanish: bool = False         # 敌人到达该节点后离场
    #: 该节点相对格中心的偏移 ``(行偏移, 列偏移)``，来自 reachOffset
    off: Tuple[float, float] = (0.0, 0.0)


@dataclass
class RouteSegment:
    index: int
    start: Coord
    end: Coord
    path: List[Coord] = field(default_factory=list)
    length: float = 0.0          # 几何长度（格）
    cost: float = 0.0            # 加权寻路代价
    time: float = 0.0            # 移动耗时（秒）
    found: bool = True
    wait_after: float = 0.0      # 到达后的停驻时间
    teleport: bool = False       # 本段是瞬移（不计路程）


@dataclass
class RouteAnalysis:
    route_index: int
    motion_mode: str
    flying: bool
    segments: List[RouteSegment] = field(default_factory=list)
    total_length: float = 0.0
    move_time: float = 0.0
    wait_time: float = 0.0
    #: **出发前**在起点格上的停驻时长（秒）。
    #:
    #: 关卡 JSON 里形如 [{type: WAIT_FOR_SECONDS, time: 270}] 且没有任何
    #: MOVE 检查点的路线（H8-4 的乌萨斯平民就是这种），这个 270 秒会被
    #: 累加到 nodes[0]（起点）上。而下面计算 wait_time 时只累加
    #: ``seg.wait_after``（= 到达点的停驻），**起点节点的停驻完全没有
    #: 被统计**，于是总耗时只有一格的移动时间，动画里看起来刚出场就走到
    #: 终点了。这个字段专门补上那段时长。
    pre_wait: float = 0.0
    total_time: float = 0.0
    reachable: bool = True
    failed_at: int = -1
    note: str = ""
    #: APPEAR_AT_POS 瞬移次数
    teleports: int = 0
    #: 路线是否中途 DISAPPEAR 离场
    vanish: bool = False
    #: 各段的 ``reachOffset``（相对所属格中心的偏移，单位：格）。
    #:
    #: 关卡 JSON 里 MOVE 检查点带 ``reachOffset``（实测 |x|,|y| ≤ 0.5），
    #: 它表示「目标点相对格子中心的偏移」——这个值非 0 就是敌人贴墙走的
    #: 原因（见 PRTS《作战机制·行动的基本原理》）。原先只取整格坐标，
    #: 于是所有偏移被丢掉，动画里敌人永远走格子正中，跟游戏里差半格。
    #: ``seg_offsets[i]`` 是第 i 段**起点**节点的偏移，终点偏移看下一项。
    seg_offsets: List[Tuple[float, float]] = field(default_factory=list)
    #: 起点格的 ``spawnOffset``（同样相对格中心，单位：格，(行, 列)）
    start_offset: Tuple[float, float] = (0.0, 0.0)

    @property
    def full_path(self) -> List[Coord]:
        out: List[Coord] = []
        for s in self.segments:
            if not s.path:
                continue
            if out and out[-1] == s.path[0]:
                out.extend(s.path[1:])
            else:
                out.extend(s.path)
        return out

    def pose_at(self, elapsed: float) -> Optional[Tuple[float, float]]:
        """按「已过多少秒」求敌人所在的浮点格坐标；已离场返回 None。

        返回的是**贴合格子中心 + reachOffset 的连续坐标**：格 (r, c) 的
        中心就是 (r, c)，偏移量直接加上去。地图画布那边 ``tile_xy`` 也是
        把 (r, c) 当格中心画的，所以两边一致。

        这是动画的核心：**必须把罚站时间算进去**。旧实现直接拿
        ``elapsed / total_time`` 去插值整条折线，于是
        (a) 起点罚站被整段忽略，(b) 中途停驻只是把总时长拉长，敌人在
        停驻期间照样匀速往前爬。现在按段推进：先吃掉 pre_wait，
        再逐段「走完本段移动时间 -> 在本段终点停 wait_after 秒」。
        """
        if elapsed < 0:
            return None
        t = float(elapsed)
        segs = [s for s in self.segments if s.path]

        # 起点罚站：原地不动
        if self.pre_wait > 0:
            if t < self.pre_wait:
                if not segs:
                    return None
                r0, c0 = segs[0].path[0]
                return self._offset(r0, c0, 0)
            t -= self.pre_wait

        for i, s in enumerate(segs):
            if s.time > 0:
                if t < s.time:
                    frac = t / s.time
                    r, c = _interp_path(s.path, frac)
                    # 段内线性过渡「起点偏移 -> 终点偏移」。
                    # 不这么做的话，敌人会在到达检查点的瞬间从格子正中
                    # 横跳半格到贴墙位置，动画看起来像抽搐。
                    a = self._seg_off(i)
                    b = self._seg_off(i + 1)
                    return (r + a[0] + (b[0] - a[0]) * frac,
                            c + a[1] + (b[1] - a[1]) * frac)
                t -= s.time
            if s.wait_after > 0:
                if t < s.wait_after:
                    r1, c1 = s.path[-1]
                    # 停驻时站在「本段终点」的偏移位置上
                    return self._offset(r1, c1, i + 1)
                t -= s.wait_after
        return None

    def _seg_off(self, idx: int) -> Tuple[float, float]:
        """第 idx 个节点的 ``(行偏移, 列偏移)``，越界时返回零偏移。"""
        if 0 <= idx < len(self.seg_offsets):
            return self.seg_offsets[idx]
        return (0.0, 0.0)

    def _offset(self, r: float, c: float,
                idx: int) -> Tuple[float, float]:
        dr, dc = self._seg_off(idx)
        return (float(r) + dr, float(c) + dc)


def _interp_path(path: List[Coord], frac: float) -> Tuple[float, float]:
    """沿折线按比例插值到浮点格坐标。

    按**格**等分而不是按路径节点数等分：寻路（尤其 DDA 直连）产出的
    路径点疏密不均，按点数等分会忽快忽慢。
    """
    if not path:
        return (0.0, 0.0)
    if len(path) == 1:
        return (float(path[0][0]), float(path[0][1]))
    frac = min(1.0, max(0.0, float(frac)))
    if frac <= 0.0:
        return (float(path[0][0]), float(path[0][1]))
    if frac >= 1.0:
        return (float(path[-1][0]), float(path[-1][1]))

    # 累计每段长度，找到落点所在段
    total = 0.0
    lens = []
    for i in range(len(path) - 1):
        r0, c0 = path[i]
        r1, c1 = path[i + 1]
        d = math.hypot(r1 - r0, c1 - c0)
        lens.append(d)
        total += d
    if total <= 0:
        r0, c0 = path[0]
        return (float(r0), float(c0))
    want = frac * total
    acc = 0.0
    for i, d in enumerate(lens):
        if acc + d >= want or i == len(lens) - 1:
            seg_t = 0.0 if d <= 0 else (want - acc) / d
            seg_t = min(1.0, max(0.0, seg_t))
            r0, c0 = path[i]
            r1, c1 = path[i + 1]
            return (r0 + (r1 - r0) * seg_t, c0 + (c1 - c0) * seg_t)
        acc += d
    r1, c1 = path[-1]
    return (float(r1), float(c1))


def analyze_route(game_map: GameMap,
                  route: Route,
                  move_speed: float = 1.0,
                  blocked: Optional[set] = None,
                  allow_diagonal: Optional[bool] = None) -> RouteAnalysis:
    """分析一条敌人路线。"""
    flying = str(route.motion_mode).upper() == "FLY"
    diag = route.allow_diagonal_move if allow_diagonal is None else allow_diagonal
    mul = game_map.move_multiplier
    speed = PF.actual_move_speed(move_speed, mul)

    ra = RouteAnalysis(route_index=route.index, motion_mode=route.motion_mode,
                       flying=flying)

    # ---- 组装节点序列：Node(坐标, 停驻秒数, 是否瞬移到达, 是否离场)
    # 每个节点带自己的 reachOffset（换成 (行偏移, 列偏移)）。起点用
    # spawnOffset——两个字段语义相同，只是挂在路线还是检查点上。
    nodes: List[Node] = [Node(route.start, 0.0, off=route.spawn_offset_rc)]
    ra.start_offset = route.spawn_offset_rc
    for cp in route.checkpoints:
        kind = cp.kind_upper
        if cp.has_position:
            r = int(round(cp.row))
            c = int(round(cp.col))
            off = cp.offset_rc
            if cp.is_teleport:
                # 瞬移出现：不计路程，直接落点并重新起算
                nodes.append(Node((r, c), 0.0, teleport=True, off=off))
            else:
                nodes.append(Node((r, c), 0.0, off=off))
        else:
            # WAIT_* / DISAPPEAR：position 是占位值，只贡献停驻时间
            if nodes:
                nodes[-1].wait += cp.wait_time
            if kind == "DISAPPEAR":
                nodes[-1].vanish = True
    if not (nodes and nodes[-1].vanish):
        # 终点用零偏移：endPosition 没有对应的 offset 字段，
        # 沿用上一个节点的偏移更好看（敌人不会在最后一步跳回格子正中）。
        nodes.append(Node(route.end, 0.0, off=nodes[-1].off if nodes else (0.0, 0.0)))
    ra.teleports = sum(1 for n in nodes if n.teleport)
    ra.vanish = any(n.vanish for n in nodes)

    # 合并坐标相同的连续节点（停驻/瞬移累加）
    cleaned: List[Node] = []
    for n in nodes:
        if cleaned and cleaned[-1].pos == n.pos:
            prev = cleaned[-1]
            prev.wait += n.wait
            prev.teleport = prev.teleport or n.teleport
            prev.vanish = prev.vanish or n.vanish
            # 同格时保留后出现的那份偏移（更接近「最终落点」）
            if n.off != (0.0, 0.0):
                prev.off = n.off
            continue
        cleaned.append(Node(n.pos, n.wait, n.teleport, n.vanish, n.off))

    # 偏移表：segments[i] 是 cleaned[i] -> cleaned[i+1]，所以每段的
    # 起终点偏移就是 cleaned[i].off / cleaned[i+1].off。
    ra.seg_offsets = [tuple(n.off) for n in cleaned]

    # 出怪口/保护目标点在图数据里常被标为 tile_forbidden + FLY_ONLY（虚空行），
    # 敌人实际能从中生成并走入地图，故这些格必须强制视为可通行。
    force_open = {n.pos for n in cleaned}

    for i in range(1, len(cleaned)):
        a = cleaned[i - 1].pos
        b = cleaned[i].pos
        cur = cleaned[i]
        prev = cleaned[i - 1]
        seg = RouteSegment(index=i - 1, start=a, end=b, wait_after=cur.wait,
                           teleport=cur.teleport)
        if cur.teleport:
            # 瞬移：不寻路、不计路程，仅记录落点
            seg.found = True
            seg.length = 0.0
            seg.time = 0.0
            seg.path = [a, b]
        elif prev.vanish:
            # 上一段已离场，其后不应再有位移
            seg.found = True
            seg.length = 0.0
            seg.time = 0.0
        elif a == b:
            seg.found = True
            seg.length = 0.0
            seg.time = 0.0
        else:
            pr = PF.find_path(game_map, a, b, flying=flying,
                              allow_diagonal=diag, blocked=blocked,
                              force_open=force_open)
            seg.found = pr.found
            seg.path = pr.path
            seg.length = pr.length
            seg.cost = pr.cost
            seg.time = PF.travel_time(pr.length, move_speed, mul) if pr.found else 0.0
        if not seg.found:
            ra.reachable = False
            if ra.failed_at < 0:
                ra.failed_at = i - 1
        ra.segments.append(seg)
        ra.total_length += seg.length
        ra.move_time += seg.time
        ra.wait_time += seg.wait_after

    # 起点罚站：nodes[0].wait 是「还没出发就已经在起点站了多久」。
    # H8-4 的乌萨斯平民只有一个 WAIT_FOR_SECONDS=270、没有任何 MOVE
    # 检查点，270 全部落在 nodes[0] 上。旧实现只累加 seg.wait_after
    # （到达停驻），于是这 270 秒被彻底丢掉，动画里敌人刚出场就走到终点。
    if cleaned:
        ra.pre_wait = max(0.0, cleaned[0].wait)

    ra.total_time = ra.move_time + ra.wait_time + ra.pre_wait
    extra = []
    if ra.teleports:
        extra.append(f"{ra.teleports} 次瞬移")
    if ra.vanish:
        extra.append("中途离场")
    tail = ("（" + "，".join(extra) + "）") if extra else ""

    if not ra.reachable:
        ra.note = f"第 {ra.failed_at + 1} 段无法寻路（检查通行掩码 / 地穴 / 障碍）"
    elif ra.total_time > 0:
        parts = [f"移动 {ra.move_time:.2f}s"]
        if ra.wait_time > 0:
            parts.append(f"途中停驻 {ra.wait_time:.2f}s")
        if ra.pre_wait > 0:
            parts.append(f"出发前停驻 {ra.pre_wait:.2f}s")
        ra.note = (f"总路程 {ra.total_length:.2f} 格，"
                   + " + ".join(parts) + tail)
    else:
        ra.note = "起点与终点相同，无位移" + tail
    return ra


def analyze_all(game_map: GameMap, move_speed: float = 1.0,
                blocked: Optional[set] = None,
                allow_diagonal: Optional[bool] = None) -> List[RouteAnalysis]:
    return [analyze_route(game_map, r, move_speed, blocked, allow_diagonal)
            for r in game_map.routes]


# --------------------------------------------------------------- 坐标换算

def tile_to_pixel(row: float, col: float, cell: int,
                  pad_x: float = 0, pad_y: float = None) -> Tuple[float, float]:
    """格坐标 -> 画布像素（x, y）。列向右，行向下。

    pad_x / pad_y 是网格左上角在画布里的偏移；只给 pad_x 时两轴同值，
    兼容旧调用。
    """
    if pad_y is None:
        pad_y = pad_x
    return (pad_x + col * cell + cell / 2.0,
            pad_y + row * cell + cell / 2.0)


def pixel_to_tile(x: float, y: float, cell: int, pad: int = 0) -> Tuple[int, int]:
    """画布像素 -> 格坐标。"""
    return (int((y - pad) // cell), int((x - pad) // cell))


# --------------------------------------------------------------- 汇总统计

@dataclass
class MapSummary:
    level_id: str
    width: int
    height: int
    ground_count: int
    fly_count: int
    route_count: int
    walk_routes: int
    fly_routes: int
    min_time: float
    max_time: float
    reachable_routes: int


def summarize(game_map: GameMap, analyses: Sequence[RouteAnalysis]) -> MapSummary:
    ground = sum(1 for r in game_map.tiles for t in r if t.passable_ground)
    fly = sum(1 for r in game_map.tiles for t in r if t.passable_fly)
    times = [a.total_time for a in analyses if a.reachable and a.total_time > 0]
    return MapSummary(
        level_id=game_map.level_id,
        width=game_map.width, height=game_map.height,
        ground_count=ground, fly_count=fly,
        route_count=len(game_map.routes),
        walk_routes=sum(1 for r in game_map.routes if str(r.motion_mode).upper() != "FLY"),
        fly_routes=sum(1 for r in game_map.routes if str(r.motion_mode).upper() == "FLY"),
        min_time=min(times) if times else 0.0,
        max_time=max(times) if times else 0.0,
        reachable_routes=sum(1 for a in analyses if a.reachable),
    )