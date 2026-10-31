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

#: 只统计真正生成敌人的动作。
#:
#: 关卡 JSON 里 ``actionType`` 有两种写法，必须都认：
#:
#: * 字符串枚举名 —— ``"SPAWN"`` / ``"SPAWN_EXTRA"``（新关卡用这个）
#: * **数值枚举** —— ``0`` 就是 ``SPAWN``，``5`` 是 ``SPAWN_EXTRA``
#:
#: 老活动关（``act10d5_*``、``act10mini_*``、``act7mini_*`` 等 117 个）用的是
#: 数值写法。旧代码 ``str(act.get("actionType")).upper()`` 把它们变成
#: ``"0"`` / ``"5"``，一个都匹配不上 —— 于是整关「本关出怪」是空的。
SPAWN_TYPES = ("SPAWN", "SPAWN_EXTRA")
#: Unpacked ``EnemyActionType`` enum → name
ACTION_TYPE_ENUM = {
    0: "SPAWN",
    1: "ACTIVATE_PREDEFINED",
    2: "DISPLAY_ENEMY_INFO",
    3: "ACTIVATE_PREDEFINED_GROUP",
    4: "PLAY_OPERA",
    5: "SPAWN_EXTRA",
    6: "TRIGGER_PREDEFINED",
    7: "CREATE_NPC",
}


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
    #: 解包里的 ``isUnharmfulAndAlwaysCountAsKilled``：这类单位没有威胁、
    #: 也不计入「剩余敌人总数」，是演出/平民/搬运物一类。H8-4 的「平民」、
    #: 纵怒里多出的「领舞者」都是它 —— 不是解析错了，是**本来就在出怪表里**，
    #: 只是实机里它们不挡路、不打人，玩家不会当成「怪」。
    harmless: bool = False
    #: 解包里的 ``isValid``：``False`` 表示这条出怪**永不触发**（未启用的
    #: 草稿/废案）。全库 2202 条，散布在 95 个地图里；``act36side_ex03``
    #: 更是 273 条全部 ``isValid=False``（整关本来不该出怪）。
    disabled: bool = False
    #: 解包里的 ``hiddenGroup``：同一关里**互斥**的几组出怪。
    #:
    #: 典型是「普通 / 突袭」两种编队写在同一份 waves 里，靠这个字段区分，
    #: 实机一局只出其中一组。``act1multi_06`` 就是 normal 408 只、raid 446 只、
    #: 无组 101 只——三组全显示会得到 955 只，而实机任一组最多约 509 只。
    #: 全库 6961 条、744 个地图有该字段。
    hidden_group: str = ""
    #: 解包里的 ``randomSpawnGroupKey``：同 key 的动作是**候选包**，按
    #: ``weight`` 抽一个出来。全库 10680 条、584 个地图。
    #: ``act1multi_football`` 单个 ``ball`` 包下就有 810 个备选。
    random_group: str = ""
    #: 该出怪在随机候选包里的权重（``randomSpawnGroupKey`` + ``weight``
    #: 才构成「同组按权重抽一条」的语义）；不属于候选包时为 0。
    weight: float = 0.0
    #: 该出怪来自 ``branches[]``（装置/陷阱触发的条件出怪），而不是按时间
    #: 排的 ``waves[]``。此时 :attr:`time` 只是「最早可能出现的时刻」，
    #: 真正何时出取决于对应装置是否被激活 —— 见 :attr:`branch`。
    branch: str = ""

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
    #: 无害单位（见 :attr:`SpawnEvent.harmless`）
    harmless: bool = False
    #: 该批次被门控字段筛掉了（isValid=False，或同组互斥里未选中）
    disabled: bool = False
    #: 该批次所在的互斥组名（SpawnEvent.hidden_group），空串表示无组
    hidden_group: str = ""
    #: 该批次属于随机候选包（SpawnGroup.random_group）
    random_group: str = ""
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

    def hostile_events(self) -> List["SpawnEvent"]:
        """剔除无害单位后的出怪。

        「本关出怪」的默认视图用这个——实机里平民、演出单位、被反复召唤的
        分身都不算要处理的敌人，混在列表里会让人误以为「这关多了怪」。
        想看全量（含无害）时直接用 ``self.events`` 或 ``groups(hostile_only=False)``。
        """
        return [e for e in self.events if not e.harmless]

    @property
    def harmless_count(self) -> int:
        """无害单位的出场次数（用于界面上标注「另有 N 个无害单位」）。"""
        return sum(1 for e in self.events if e.harmless)

    @property
    def disabled_count(self) -> int:
        """``isValid=False``（永不触发）的出怪条数。"""
        return sum(1 for e in self.events if e.disabled)

    def hidden_groups(self) -> List[str]:
        """本关所有的互斥组名（``hiddenGroup``），按出场顺序去重。"""
        seen: Dict[str, None] = {}
        for e in self.events:
            if e.hidden_group:
                seen[e.hidden_group] = None
        return list(seen)

    def random_groups(self) -> List[str]:
        """本关所有的随机候选包名（``randomSpawnGroupKey``），按出场顺序去重。"""
        seen: Dict[str, None] = {}
        for e in self.events:
            if e.random_group:
                seen[e.random_group] = None
        return list(seen)

    def random_pack_summary(self) -> List[Dict[str, object]]:
        """每个随机候选包的成员概览，供界面标注「这一包 N 选 1」。

        返回 ``[{group, members, weights, total, expect}, ...]``：
        ``members`` 是 ``[(enemy_id, enemy_name, count, weight), ...]``，
        ``total`` 是全列出时的只数，``expect`` 是按权重算的期望只数。
        """
        packs: Dict[str, List["SpawnEvent"]] = {}
        for e in self.events:
            if e.random_group and not e.disabled:
                packs.setdefault(e.random_group, []).append(e)
        out: List[Dict[str, object]] = []
        for g, evs in packs.items():
            # 同一 action 会按 count 拆成多条事件，先按 action 聚合
            per_act: Dict[tuple, List["SpawnEvent"]] = {}
            for e in evs:
                per_act.setdefault(
                    (e.wave_index, e.fragment_index, e.action_index), []).append(e)
            members = []
            total = 0
            wsum = 0.0
            expect = 0.0
            for _k, lst in per_act.items():
                first = lst[0]
                cnt = int(getattr(first, "count", len(lst)) or len(lst))
                w = float(getattr(first, "weight", 0.0) or 0.0)
                members.append((first.enemy_id, first.enemy_name, cnt, w))
                total += cnt
                wsum += w
                expect += cnt * w
            if wsum > 0:
                expect /= wsum
            else:
                expect = float(max((m[2] for m in members), default=0))
            out.append({
                "group": g,
                "members": members,
                "weights": [m[3] for m in members],
                "total": total,
                "expect": expect,
            })
        return out

    def fold_random_packs(self) -> List["SpawnEvent"]:
        """把随机候选包折叠成「实机一局真会出的那几条」。

        ``randomSpawnGroupKey`` 是**加权候选包**：同一个 key 下的多条
        spawn 是同一次抽取的备选，实机按 ``weight`` 抽其中**一条**。
        全库 568 个关卡、1354 个包受影响；最极端的
        ``act1multi_football`` 一个包挂了 **810** 个备选，全列出来会
        显示 1393 只，而实机一局只会出约 584 只。

        折叠规则（无随机数，可复现）：每个包**只留一条**代表——
        ``weight`` 最大的那条；``weight`` 相同则取 ``count`` 最大、
        再相同取先出现的。这样「本关有什么怪」不会漏掉主角，只数也
        不会翻倍。想看全部备选时用 ``self.events``。

        注意：包内成员若是同一种敌人但走不同路线（如 ``rogue6_c-2``
        的角兽 5 个包、每包 2 条同敌人不同路线），折叠后只数减半，
        这正是实机表现——同一次抽取只会从两条路线里挑一条出兵。
        """
        evs = [e for e in self.events if not e.disabled]
        packs: Dict[str, List["SpawnEvent"]] = {}
        for e in evs:
            if e.random_group:
                packs.setdefault(e.random_group, []).append(e)
        if not packs:
            return evs
        # 每个包里挑一条代表（按 action 聚合后比较）
        winner: Dict[str, tuple] = {}
        for g, lst in packs.items():
            per_act: Dict[tuple, List["SpawnEvent"]] = {}
            for e in lst:
                per_act.setdefault(
                    (e.wave_index, e.fragment_index, e.action_index), []).append(e)
            best_key = None
            best_score = None
            for k, sub in per_act.items():
                first = sub[0]
                score = (float(getattr(first, "weight", 0.0) or 0.0),
                         int(getattr(first, "count", len(sub)) or len(sub)),
                         -int(k[2]))
                if best_score is None or score > best_score:
                    best_score = score
                    best_key = k
            winner[g] = best_key
        out: List["SpawnEvent"] = []
        for e in evs:
            g = e.random_group
            if not g:
                out.append(e)
                continue
            if (e.wave_index, e.fragment_index, e.action_index) == winner.get(g):
                out.append(e)
        return out

    def effective_events(self, hidden_group: str = "",
                        fold_random: bool = False) -> List["SpawnEvent"]:
        """实机**真正会出**的怪：剔除废案 + 互斥组只留一组（可折叠随机包）。

        ``hiddenGroup`` 是同一关里互斥的几组编队（最典型的是「普通 / 突袭」
        写在同一份 waves 里），实机一局只出其中一组。原先不读这个字段，
        于是「普通」和「突袭」的怪被一起列出来——``act1multi_06`` 因此
        显示 955 只，而实机任一组最多约 509 只，看起来就像「多出一倍怪」。

        ``hidden_group`` 选哪一组：
          * 传具体组名 -> 只留该组 + 无组的那部分
          * 传空串（默认）-> 自动挑「出战数最多的那一组」，因为那是常规
            编队（raid/突袭 一般更少或相近，用组数最多的更接近实机常态）
          * 传 ``"__all__"`` -> 不折叠，全列（调试用）

        ``fold_random``（默认 False）控制 ``randomSpawnGroupKey`` 加权候选包
        是否折叠成一个代表。关掉时全列备选——对足球那类图会显示 1393 只，
        等于「多出敌人」；用户在沙盘里核对实机编队时应打开它。
        详情见 :meth:`Timeline.fold_random_packs`。
        """
        evs = [e for e in self.events if not e.disabled]
        if fold_random:
            evs = self.fold_random_packs()
            evs = [e for e in evs if not e.disabled]
        if hidden_group == "__all__":
            return evs
        groups = self.hidden_groups()
        if not groups:
            return evs
        pick = hidden_group
        if pick not in groups:
            # 自动挑「只数最多」的那一组（同数时取先出现的）
            best, best_n = groups[0], -1
            for g in groups:
                n = sum(1 for e in evs if e.hidden_group == g)
                if n > best_n:
                    best, best_n = g, n
            pick = best
        return [e for e in evs
                if not e.hidden_group or e.hidden_group == pick]

    def groups(self, hostile_only: bool = False,
               effective: bool = False,
               hidden_group: str = "",
               fold_random: bool = False,
               exclude_branch: bool = True) -> List["SpawnGroup"]:
        """把出怪事件合并成 PRTS 风格的逐条列表（按出场顺序）。

        同一批出怪（相同 wave/fragment/action/route，count>1 的多只）
        合并成一条，序号按「全局第几只」连续编号。

        ``hostile_only=True`` 时跳过无害单位（见
        :meth:`hostile_events`）。

        ``effective=True`` 时只列实机真正会出的怪——剔除 ``isValid=False``
        的废案、并把互斥的 ``hiddenGroup`` 折叠成一组（见
        :meth:`effective_events`）。这是「本关出怪」默认该用的模式。

        ``fold_random=True`` 时再把 ``randomSpawnGroupKey`` 加权候选包折叠成
        一个代表，避免把「N 选 1」显示成 N 只（见
        :meth:`Timeline.fold_random_packs`）。
        """
        out: List[SpawnGroup] = []
        # 事件已按 (time, route_index) 排好序；这里按批次标识聚合，
        # 并保持出场顺序（Python dict 有序）。
        buckets: Dict[tuple, List[SpawnEvent]] = {}
        order: List[tuple] = []
        source = (self.effective_events(hidden_group, fold_random=fold_random)
                  if effective
                  else list(self.events))
        for e in source:
            if hostile_only and e.harmless:
                continue
            if exclude_branch and getattr(e, "branch", ""):
                continue
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
                harmless=head.harmless,
                disabled=head.disabled,
                hidden_group=head.hidden_group,
                random_group=head.random_group,
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


def _num_enum(v):
    """``actionType`` 归一化成枚举名；认不出就返回 ``""``。"""
    if isinstance(v, bool):
        return ""
    if isinstance(v, int):
        return ACTION_TYPE_ENUM.get(v, "")
    s = str(v or "").strip().upper()
    if not s:
        return ""
    if s.isdigit():
        return ACTION_TYPE_ENUM.get(int(s), "")
    return s


def is_spawn_action(act) -> bool:
    """这个 action 会不会真的生成敌人。

    ``actionType`` 可能是枚举名（``"SPAWN"``）也可能是枚举序号（``0``），
    两者都要认——见 :data:`ACTION_TYPE_ENUM` 的说明。
    """
    try:
        return _num_enum(act.get("actionType")) in SPAWN_TYPES
    except AttributeError:
        return False


def parse_timeline(raw: dict,
                   names: Optional[Dict[str, str]] = None) -> Timeline:
    """把关卡 JSON 解析成时间轴。

    两处出怪来源都要读：

    * ``waves[]`` —— 按时间排的常规波次（绝大多数关卡的主体）
    * ``branches[]`` —— **装置/陷阱触发的条件出怪**。分支名就是触发它的
      装置 key（``trap_068_badbox#1``、``summon_cjglon``、``mbx1``、
      ``bonore_dfello1`` …），全库 744 个地图里有 4904 条 SPAWN。

    为什么必须读 branches
    --------------------
    原先只读 ``waves``。好在 744 个带 branches 的图里 738 个 waves 本身也有
    怪，所以只表现为「少数怪漏了」；但 ``act1dp_01/02/05/ex04/tr01`` 这 5 关
    **整关的怪全在 branches 里**（waves 只有 PLAY_OPERA 之类的演出动作），
    于是右侧「本关出怪」永远空白 —— 就是用户报的「部分关卡右侧没有本关出怪」。

    分支出怪的时间怎么算
    -------------------
    分支没有绝对时间轴，只有各自 phase 的 ``preDelay``。这里**不**把不同
    分支的时间相加（那会造出根本不存在的顺序），而是每个分支独立从 0 起算，
    并把结果标上 ``branch=<分支名>``。界面上这些条目显示为「条件出怪」，
    时间列的含义是「装置激活后第几秒」，而不是「开局后第几秒」。
    """
    names = names or {}
    tl = Timeline(names=dict(names))
    waves = raw.get("waves") or []

    def _add_actions(tl_, acts, wi, fi, base, branch=""):
        """把一段 actions 解析成事件，返回这段动作占用到的时间游标。"""
        t_cursor = base
        span_total = 0.0
        for ai, act in enumerate(acts):
            if not is_spawn_action(act):
                continue
            eid = act.get("key") or ""
            count = max(1, _i(act.get("count"), 1))
            interval = _f(act.get("interval"))
            t0 = t_cursor + _f(act.get("preDelay"))
            route = act.get("routeIndex")
            route_index = _i(route, -1) if route is not None else -1
            harmless = bool(act.get("isUnharmfulAndAlwaysCountAsKilled"))
            # 侵入式调用（enemy_10072_mpprhd）：第15章的隐藏 Boss，是 PRTS
            # 机制的一部分——不攻击、不扣生命值、不可阻挡。虽然数据里没标
            # isUnharmfulAndAlwaysCountAsKilled，但实质无害，按无害处理。
            if not harmless and "mpprhd" in eid:
                harmless = True
            # isValid=False = 这条出怪永不触发（废案/未启用）
            disabled = act.get("isValid") is False
            hidden_group = str(act.get("hiddenGroup") or "")
            random_group = str(act.get("randomSpawnGroupKey") or "")
            weight = _f(act.get("weight"))
            for k in range(count):
                tl_.events.append(SpawnEvent(
                    time=t0 + k * interval,
                    enemy_id=eid,
                    enemy_name=names.get(eid, eid),
                    count=count,
                    seq=k,
                    route_index=route_index,
                    wave_index=wi,
                    fragment_index=fi,
                    action_index=ai,
                    harmless=harmless,
                    disabled=disabled,
                    hidden_group=hidden_group,
                    random_group=random_group,
                    weight=weight,
                    branch=branch,
                ))
            # 本批最后一个的生成时间也算进游标
            span = _f(act.get("preDelay")) + (count - 1) * interval
            span_total = max(span_total, span)
        return span_total

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
            span = _add_actions(tl, frag.get("actions") or [], wi, fi, t_cursor)
            t_cursor += span
            post = _f(frag.get("postDelay"))
            if post:
                t_cursor += post

    # ---- branches[]：装置/陷阱触发的条件出怪 ---------------------------
    # wave_index 用 -1 标记「不属于任何波次」，_fill_isolate_info 等处按
    # route_index 找路线，不受影响。
    for bname, bdata in (raw.get("branches") or {}).items():
        if not isinstance(bdata, dict):
            continue
        # 每个分支独立计时，互不相加
        for fi, phase in enumerate(bdata.get("phases") or []):
            base = _f(phase.get("preDelay"))
            _add_actions(tl, phase.get("actions") or [], -1, fi, base,
                         branch=str(bname))

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
                 rich: bool = False,
                 hostile_only: bool = False,
                 fold_random: bool = False):
    """推算 seconds 时刻各敌人所在格。

    返回 [(row, col, 标签, 颜色索引)]：
    * 只用已出现（time <= seconds）且尚未走到终点的敌人；
    * 沿路线按「已过秒数」逐段推进，**罚站时间真的会停住**；
    * 瞬移（APPEAR_AT_POS）按落点直接跳过去。

    ``rich=True`` 时每项改为字典，额外带 enemy_id / 攻击移速等，
    供地图上的出怪点悬停与点击详情使用。

    ``hostile_only=True`` 时跳过 ``harmless`` 单位（鸭爵/高普尼克/流泪小子
    这类无威胁的随机出没单位），不画进地图。

    ``fold_random=True`` 时把同一 ``randomSpawnGroupKey`` 的候选包折叠成
    一个代表——随机出怪不会全部同时出现，只择一，所以不应该全部画。

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
    # 筛选事件：撇除无害单位 / 折叠随机候选包
    if fold_random:
        evs = timeline.fold_random_packs()
    else:
        evs = timeline.events
    if hostile_only:
        evs = [e for e in evs if not getattr(e, "harmless", False)]
    # 排除分支出怪（侵入式调用）：这些是装置/陷阱触发的条件出怪，
    # 不属于波次正常出怪，不应出现在地图动画里。
    evs = [e for e in evs if not getattr(e, "branch", "")]
    for e in evs:
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
