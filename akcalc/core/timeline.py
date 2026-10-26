"""出怪时间轴：把关卡 waves 展开成「第几秒、哪个敌人、走哪条路线」。

关卡 JSON 的波次是三层嵌套：

    waves[]                    波（preDelay / postDelay）
      └ fragments[]             片段（preDelay / actions[]）
           └ actions[]          动作（actionType / key / count / preDelay /
                                interval / routeIndex）

时间累计规则
------------
    t = wave.preDelay + Σ(本 wave 内此前 fragment 的 preDelay + 其中的生成耗时)
        + fragment.preDelay + action.preDelay
同一 action 生成 count 个敌人，第 i 个（i 从 0 起）时间为
``t + i * interval``。

``fragments`` 在旧版关卡里是直接给 ``actions`` 的，这里两种都兼容。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

#: 只统计真正生成敌人的动作
SPAWN_TYPES = ("SPAWN", "SPAWN_EXTRA")


@dataclass
class SpawnEvent:
    """一次出怪。"""

    time: float                 # 出现时间（秒）
    enemy_id: str = ""
    enemy_name: str = ""
    count: int = 1              # 这一批的总数
    seq: int = 0                # 在批次内的序号（0 起）
    route_index: int = -1       # 对应 GameMap.routes 的 index
    wave_index: int = 0
    fragment_index: int = 0
    action_index: int = 0

    @property
    def label(self) -> str:
        return self.enemy_name or self.enemy_id


@dataclass
class SpawnGroup:
    """PRTS.Map 风格的「一次出怪」条目。

    PRTS 的「本关出怪」不是按敌人种类汇总，而是**按出场顺序一行一行
    往下排**，同一批（同一个 action、count>1）算一条，例如::

        6 | x2 | 7 ~ 8 | 5s | 18s | 18s | 路线

    对应字段：seq（次序）、count（数量）、seq_range（批次内序号范围）、
    interval（出现间隔）、time（时间点）、stage_time（阶段时间点）、
    route_index（路线）。
    """

    seq: int = 0                   # 全局第几批（1 起）
    enemy_id: str = ""
    enemy_name: str = ""
    count: int = 1
    interval: float = 0.0          # 批内出怪间隔（秒）
    time: float = 0.0              # 首只出现时间（相对本阶段开始时）
    stage_time: float = 0.0        # 相对本阶段（波次）开始的时间
    route_index: int = -1
    wave_index: int = 0
    #: 该批次覆盖的 SpawnEvent 列表（点击隔离路线时用第一条的路线）
    events: List["SpawnEvent"] = field(default_factory=list)

    @property
    def label(self) -> str:
        return self.enemy_name or self.enemy_id

    @property
    def last_time(self) -> float:
        return self.time + max(0, self.count - 1) * self.interval

    @property
    def seq_range(self) -> str:
        """批次内的序号范围文本，如 ``7 ~ 8``；单只时就是 ``7``。"""
        if self.count <= 1:
            return str(self.seq)
        return "%d ~ %d" % (self.seq, self.seq + self.count - 1)

    @property
    def interval_text(self) -> str:
        if self.count <= 1:
            return "—"
        if self.interval <= 0:
            return "同时"
        return _fmt_sec(self.interval)

    @property
    def time_text(self) -> str:
        return _fmt_sec(self.time)

    @property
    def stage_time_text(self) -> str:
        return _fmt_sec(self.stage_time)


def _fmt_sec(v: float) -> str:
    """秒数格式化：整数不带小数点，非整数保留一位。"""
    try:
        v = float(v)
    except (TypeError, ValueError):
        return "—"
    if abs(v - round(v)) < 0.05:
        return "%ds" % int(round(v))
    return "%.1fs" % v


@dataclass
class RouteSpawn:
    """某条路线上的出怪序列（时间轴用）。"""

    route_index: int
    events: List[SpawnEvent] = field(default_factory=list)

    @property
    def first_time(self) -> float:
        return min((e.time for e in self.events), default=0.0)

    @property
    def last_time(self) -> float:
        return max((e.time for e in self.events), default=0.0)

    @property
    def total(self) -> int:
        return sum(e.count for e in self.events)


@dataclass
class Timeline:
    """整关的出怪时间轴。"""

    events: List[SpawnEvent] = field(default_factory=list)
    #: enemy_id -> 中文名
    names: Dict[str, str] = field(default_factory=dict)
    #: wave_index -> 该波开始的绝对时间，用于「阶段时间点」列
    wave_start: Dict[int, float] = field(default_factory=dict)
    #: id(SpawnEvent) -> 该只敌人在**本关全局的编号**（1 起，按出场顺序）。
    #: 由 :meth:`assign_numbers` 填充。「本关出怪」表的次序列用的就是同一
    #: 套编号，所以悬停提示里的编号能和表格行对上。
    numbers: Dict[int, int] = field(default_factory=dict)

    def assign_numbers(self) -> None:
        """给每只敌人生成「本关第几只」的全局编号（1 起，按出场顺序）。

        为什么不用 ``SpawnEvent.seq``：那个 ``seq`` 是**批次内**的序号
        （同一批 count 只里的第几个），绝大多数敌人都是 0，拿来当编号
        没有意义，用户会看到满屏「0 号」。

        编号规则与 :meth:`groups` 完全一致（同一批 merge 后连续编号），
        这样读数和「本关出怪」表的「次序」列永远一致。
        """
        self.numbers.clear()
        for g in self.groups():
            for i, ev in enumerate(sorted(g.events,
                                          key=lambda x: (x.time, x.seq))):
                self.numbers[id(ev)] = g.seq + i

    def number_of(self, event) -> int:
        """取某只敌人的本关编号；没编号时返回 0。"""
        n = self.numbers.get(id(event))
        if n:
            return n
        # 缓存没建或对象被重建过，退化成按出场顺序临时算
        return 0

    @property
    def duration(self) -> float:
        """最后一个敌人**出现**的时刻（秒）。"""
        return max((e.time for e in self.events), default=0.0)

    def span(self, analyses=None) -> float:
        """整段动画应该播多久。

        不能直接用 ``duration``：它只到最后一只敌人「出场」为止，
        而敌人出场后还要走完全程（H8-4 的乌萨斯平民出场后要罚站
        270 秒）。这里把每条路线的 ``total_time`` 叠加到最后一支出场
        时间上，必要时再留 1 秒尾巴。
        """
        base = self.duration
        if not analyses:
            return base + 1.0
        by_idx = {}
        for a in analyses:
            by_idx[a.route_index] = a
        end = base
        for e in self.events:
            a = by_idx.get(e.route_index)
            if not a:
                continue
            if a.total_time > 0:
                end = max(end, e.time + a.total_time)
        return max(base, end) + 1.0

    @property
    def total_spawns(self) -> int:
        return len(self.events)

    def by_route(self) -> Dict[int, RouteSpawn]:
        out: Dict[int, RouteSpawn] = {}
        for e in self.events:
            rs = out.get(e.route_index)
            if rs is None:
                rs = out[e.route_index] = RouteSpawn(route_index=e.route_index)
            rs.events.append(e)
        for rs in out.values():
            rs.events.sort(key=lambda x: x.time)
        return out

    def at(self, seconds: float, tolerance: float = 0.5) -> List[SpawnEvent]:
        """取某一时刻正在出现的敌人。"""
        return [e for e in self.events if abs(e.time - seconds) <= tolerance]

    def enemy_ids(self) -> List[str]:
        seen: Dict[str, None] = {}
        for e in self.events:
            seen[e.enemy_id] = None
        return list(seen)

    def groups(self) -> List["SpawnGroup"]:
        """把出怪事件合并成 PRTS 风格的逐条列表（按出场顺序）。

        同一批出怪（相同 wave/fragment/action/route，count>1 的多只）
        合并成一条，序号按「全局第几只」连续编号。
        """
        out: List[SpawnGroup] = []
        # 事件已按 (time, route_index) 排好序；这里按批次标识聚合，
        # 并保持出场顺序（Python dict 有序）。
        buckets: Dict[tuple, List[SpawnEvent]] = {}
        order: List[tuple] = []
        for e in self.events:
            key = (e.wave_index, e.fragment_index, e.action_index,
                   e.enemy_id, e.route_index)
            if key not in buckets:
                buckets[key] = []
                order.append(key)
            buckets[key].append(e)
        seq = 0
        for key in order:
            evs = sorted(buckets[key], key=lambda x: (x.time, x.seq))
            if not evs:
                continue
            head = evs[0]
            # 阶段时间点 = 相对本波开始（wave.preDelay 之后）
            stage_ref = self.wave_start.get(head.wave_index, 0.0)
            g = SpawnGroup(
                seq=seq + 1,
                enemy_id=head.enemy_id,
                enemy_name=head.enemy_name or head.enemy_id,
                count=len(evs),
                interval=(evs[1].time - evs[0].time) if len(evs) > 1 else 0.0,
                time=head.time,
                stage_time=head.time - stage_ref,
                route_index=head.route_index,
                wave_index=head.wave_index,
                events=evs,
            )
            out.append(g)
            seq += len(evs)
        out.sort(key=lambda g: (g.time, g.wave_index, g.seq))
        # 排序后重新编号，保证「次序」列严格对应出场顺序
        for i, g in enumerate(out):
            g.seq = i + 1 if i == 0 else out[i - 1].seq + out[i - 1].count
        return out


def _f(v, default: float = 0.0) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def _i(v, default: int = 0) -> int:
    try:
        return int(v)
    except (TypeError, ValueError):
        return default


def parse_timeline(raw: dict,
                   names: Optional[Dict[str, str]] = None) -> Timeline:
    """把关卡 JSON 解析成时间轴。"""
    names = names or {}
    tl = Timeline(names=dict(names))
    waves = raw.get("waves") or []

    for wi, wave in enumerate(waves):
        wave_start = _f(wave.get("preDelay"))
        tl.wave_start[wi] = wave_start
        t_cursor = wave_start

        # 兼容两种结构：wave.actions / wave.fragments[].actions
        if wave.get("actions") is not None and not wave.get("fragments"):
            frags = [{"preDelay": 0.0, "actions": wave.get("actions") or []}]
        else:
            frags = wave.get("fragments") or []

        for fi, frag in enumerate(frags):
            t_cursor += _f(frag.get("preDelay"))
            span = 0.0
            for ai, act in enumerate(frag.get("actions") or []):
                kind = str(act.get("actionType") or "").upper()
                if kind not in SPAWN_TYPES:
                    continue
                eid = act.get("key") or ""
                count = max(1, _i(act.get("count"), 1))
                interval = _f(act.get("interval"))
                t0 = t_cursor + _f(act.get("preDelay"))
                route = act.get("routeIndex")
                route_index = _i(route, -1) if route is not None else -1
                for k in range(count):
                    tl.events.append(SpawnEvent(
                        time=t0 + k * interval,
                        enemy_id=eid,
                        enemy_name=names.get(eid, eid),
                        count=count,
                        seq=k,
                        route_index=route_index,
                        wave_index=wi,
                        fragment_index=fi,
                        action_index=ai,
                    ))
                # 本批最后一个的生成时间也算进游标
                span = max(span, _f(act.get("preDelay")) + (count - 1) * interval)
            t_cursor += span
            post = _f(frag.get("postDelay"))
            if post:
                t_cursor += post

    tl.events.sort(key=lambda e: (e.time, e.route_index))
    # 立刻分配「本关第几只」，这样任何调用方（悬停提示、图表、
    # positions_at）拿到的编号都一致，不必记得自己调一次。
    tl.assign_numbers()
    return tl


def fill_names(timeline: Timeline, lookup) -> Timeline:
    """用敌人库/手册补全中文名。lookup(enemy_id) -> str | None"""
    for e in timeline.events:
        if e.enemy_name == e.enemy_id:
            nm = lookup(e.enemy_id)
            if nm:
                e.enemy_name = nm
                timeline.names[e.enemy_id] = nm
    return timeline


# --------------------------------------------------------------- 位置推算

def positions_at(timeline: "Timeline", seconds: float,
                 analyses, game_map, speed: float = 1.0,
                 rich: bool = False):
    """推算 seconds 时刻各敌人所在格。

    返回 [(row, col, 标签, 颜色索引)]：
    * 只用已出现（time <= seconds）且尚未走到终点的敌人；
    * 沿路线按「已过秒数」逐段推进，**罚站时间真的会停住**；
    * 瞬移（APPEAR_AT_POS）按落点直接跳过去。

    ``rich=True`` 时每项改为字典，额外带 enemy_id / 攻击移速等，
    供地图上的出怪点悬停与点击详情使用。

    罚站为何单独处理
    ----------------
    旧实现是 ``frac = elapsed / total_time`` 再去插值整条折线，问题有二：

    1. **起点罚站被整段忽略。** H8-4 的乌萨斯平民路线只有
       ``[{type: WAIT_FOR_SECONDS, time: 270}]``，没有任何 MOVE 检查点，
       270 秒只能落在起点节点上；而 total_time 只由
       ``seg.wait_after``（到达停驻）累加，起点那段从未计入。
    2. **中途停驻不影响位置。** 停驻只是把 total_time 拉长，敌人在
       停驻期间照样匀速往前爬，看起来"边罚站边走路"。

    现在改为调用 ``RouteAnalysis.pose_at(elapsed)``，它先吃掉出发前
    停驻，再逐段「移动 -> 原地停 wait_after 秒」，物理意义正确。

    坐标精度
    --------
    ``row`` / ``col`` 是**带 reachOffset 的连续浮点坐标**，例如
    ``(3.5, 7.0)`` 表示「第 3 行第 7 列这一格的中心偏下半格」。格中心
    就是整数值本身，所以 ``row_i = round(row)`` 就是它当前压在哪一格。
    这里不做四舍五入——图鉴的悬停提示要显示两位小数，提前取整等于
    把信息扔了。
    """
    out = []
    if not timeline or not analyses or not game_map:
        return out
    by_idx = {a.route_index: a for a in analyses}
    for e in timeline.events:
        if e.time > seconds:
            continue
        a = by_idx.get(e.route_index)
        if not a or not a.reachable:
            continue
        if a.total_time <= 0:
            continue
        elapsed = seconds - e.time
        if elapsed >= a.total_time:
            continue                      # 已离场
        pose = a.pose_at(elapsed)
        if pose is None:
            continue
        row, col = pose
        frac = min(1.0, max(0.0, elapsed / a.total_time))
        # row_i / col_i 只用于「压在哪个格」的显示与同格扇出，取最近的
        # 整格即可；精确位置请用 row / col 这两个浮点值。
        row_i = int(round(row))
        col_i = int(round(col))
        if rich:
            out.append({
                "row": row,
                "col": col,
                "row_i": row_i,
                "col_i": col_i,
                "label": "",
                "color": e.enemy_name or e.enemy_id,
                "enemy_id": e.enemy_id,
                "enemy_name": e.enemy_name or e.enemy_id,
                "time": e.time,
                "route_index": e.route_index,
                "fraction": frac,
                "seq": getattr(e, "seq", 0),
                # 本关全局编号（1 起）。和「本关出怪」表的「次序」一致，
                # 悬停提示用它告诉用户「这只到底是本关第几只」。
                "number": timeline.number_of(e),
                # 距出生已过多少秒（悬停提示里说明「走了多久」）
                "elapsed": elapsed,
            })
        else:
            out.append((row, col, "", e.enemy_name or e.enemy_id))
    return out


def active_events(timeline: "Timeline", seconds: float):
    """返回 seconds 时刻仍在场的出怪事件（已出现且未走到终点）。"""
    if not timeline:
        return []
    return [e for e in timeline.events if e.time <= seconds]
