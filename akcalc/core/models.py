"""数据模型：干员、敌人、地块、地图、路线。"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


@dataclass
class OperatorStats:
    """干员在某一等级下的面板数值。"""

    hp: float = 0.0
    atk: float = 0.0
    defense: float = 0.0
    magic_resist: float = 0.0  # 以点数计，0~100
    cost: int = 0
    block: int = 0
    attack_interval: float = 1.0  # 理论攻击间隔 T0
    redeploy: float = 70.0
    range_id: Optional[str] = None


@dataclass
class Operator:
    """干员基础数据。"""

    char_id: str
    name: str
    rarity: int = 0
    profession: str = ""
    sub_profession: str = ""
    position: str = ""  # 近战位 / 远程位
    attack_type: str = "PHYSICAL"  # 该干员的伤害类型（可由技能修改）

    #: 精英化阶段 -> 该阶段内可用的等级 -> 面板
    phases: Dict[int, Dict[int, OperatorStats]] = field(default_factory=dict)
    #: 信赖加成（满信赖时的数值增量）
    trust_bonus: Dict[str, float] = field(default_factory=dict)
    #: 潜能加成（满潜能时的总增量）
    potential_bonus: Dict[str, float] = field(default_factory=dict)
    #: 潜能逐级明细（潜能 2~6 共 5 档）：
    #: [{"rank": 2, "type": "cost", "value": -1.0, "text": "部署费用-1"}, ...]
    potential_ranks: List[dict] = field(default_factory=list)
    #: 天赋文本（用于人工核对，不参与计算）
    talents: List[Tuple[str, str]] = field(default_factory=list)
    #: 技能列表（core.skills.Skill），仅在缓存里保留可序列化形式
    skills: List[object] = field(default_factory=list)

    max_elite: int = 0

    def levels_of(self, elite: int) -> List[int]:
        return sorted(self.phases.get(elite, {}).keys())

    def stats_at(self, elite: int, level: int) -> Optional[OperatorStats]:
        phase = self.phases.get(elite)
        if not phase:
            return None
        if level in phase:
            return phase[level]
        if not phase:
            return None
        # 取最近的不超过 level 的档位
        candidates = [lv for lv in phase if lv <= level]
        if candidates:
            return phase[max(candidates)]
        return phase[min(phase)]


@dataclass
class EnemyStats:
    """敌人面板。"""

    enemy_id: str
    name: str = ""
    hp: float = 0.0
    atk: float = 0.0
    defense: float = 0.0
    magic_resist: float = 0.0  # 点数 0~100
    move_speed: float = 1.0
    weight: float = 0.0  # massLevel
    block_cost: int = 1  # 消耗几个阻挡数
    attack_interval: float = 1.5
    is_flying: bool = False
    damage_type: str = "PHYSICAL"
    #: 出生后原地不能动的秒数（【休憩】/ Revive.unmovable_duration）。
    #:
    #: 这个值**不在路线检查点里**，所以路线分析算不出它：角兽
    #: ``enemy_1303_mhshep`` 的 23 条路线 ``checkpoints`` 全是空数组，
    #: ``pre_wait`` 一路为 0。真实数据在敌人库的 ``talentBlackboard``
    #: 里（``Revive.unmovable_duration``），且**关卡可以覆盖**：敌人库
    #: 默认 150s，而「咩的朋友」``ro6_c_2`` 的 ``enemyDbRefs[0]`` 把它
    #: 覆盖成 90s —— PRTS 关卡页那句「出场 90 秒内无法移动」就是它。
    #: 2026-xx 修复「咩的朋友角兽罚站时间错误」即此项。
    spawn_unmovable: float = 0.0


@dataclass
class Tile:
    """地图地块。"""

    row: int
    col: int
    tile_key: str = ""
    height_type: str = "LOWLAND"
    buildable_type: str = "NONE"
    passable_mask: str = "ALL"
    # 该格对应 mapData.tiles 里的下标（-1 = 越界/无 def）。
    # 同一 tileKey 可能有多条 def（如 tile_infection 在本关出现两次、
    # 各自 blackboard 不同），只按 tileKey 查会退化成「参数未知」，
    # 所以必须记住自己用的是哪一条。
    def_index: int = -1

    @property
    def passable_ground(self) -> bool:
        return self.passable_mask in ("ALL", "WALK_ONLY")

    @property
    def passable_fly(self) -> bool:
        return self.passable_mask in ("ALL", "FLY_ONLY")

    @property
    def buildable_melee(self) -> bool:
        return self.buildable_type in ("MELEE", "ALL")

    @property
    def buildable_ranged(self) -> bool:
        return self.buildable_type in ("RANGED", "ALL")


#: 真正携带有效坐标的检查点类型。其余类型（WAIT_FOR_SECONDS /
#: WAIT_CURRENT_FRAGMENT_TIME / WAIT_CURRENT_WAVE_TIME / DISAPPEAR）在关卡
#: JSON 里的 position 一律是占位值 (0, 0)，**不能**当作途经点，否则会把
#: 路线算成绕经左上角。
#:
#: 全库实测（25 万条检查点）各类型的「有真实坐标」占比：
#:
#:   =========================  ======  ==========
#:   类型                        条数   有真实坐标
#:   =========================  ======  ==========
#:   MOVE                       254346  100.0%
#:   APPEAR_AT_POS               11328  100.0%
#:   PATROL_MOVE                  2021  100.0%  ← 原先漏了
#:   MAP_OFFSET_MOVE                 2  100.0%  ← 原先漏了
#:   WAIT_FOR_SECONDS            62084    8.2%
#:   WAIT_CURRENT_FRAGMENT_TIME   3919   11.0%
#:   WAIT_CURRENT_WAVE_TIME        560    0.5%
#:   DISAPPEAR                   11237    7.0%
#:   =========================  ======  ==========
#:
#: ``PATROL_MOVE``（巡逻移动，足球/活动图用）在此前被漏掉，于是它的坐标被
#: 当成占位值丢掉、转而把紧随其后的 WAIT 时长累加到**上一个**节点上。实测
#: 29 个关卡 2021 条检查点受影响，典型表现为 act26side_01 route0 把两段
#: 600 秒罚站都算到起点、得出 1200 秒的「出发前罚站」，而真实情况是中途
#: 在 (2,6)、(2,2) 巡逻后才停。
POSITIONED_CHECKPOINTS = frozenset({"MOVE", "APPEAR_AT_POS",
                                    "PATROL_MOVE", "MAP_OFFSET_MOVE"})

#: 检查点类型的数值枚举。
#:
#: 老活动关（act6d5 / act7mini / act10mini / act13mini / act14mini /
#: act1lock 等 102 关）的 ``routes[].checkpoints[].type`` 不是字符串而是
#: 整数。``motionMode`` 也是同样的数值形式（见 :data:`MOTION_MODES`）。
#:
#: 映射由「position 是否是占位 (0,0)」「time 是否非零」两条实测不变量标定
#: （全库 25 万条检查点）：
#:
#:   =====  =========================  ========  ======
#:   数值   含义                        有真实坐标  time>0
#:   =====  =========================  ========  ======
#:   0      MOVE                       8404/8406   0
#:   1      WAIT_FOR_SECONDS             10/2120   2118
#:   3      WAIT_CURRENT_FRAGMENT_TIME    0/62      62
#:   4      WAIT_CURRENT_WAVE_TIME        0/31      31
#:   5      DISAPPEAR                     0/240      0
#:   6      APPEAR_AT_POS               240/240      0
#:   =====  =========================  ========  ======
#:
#: 0/1/6 三项与字符串形态的语义完全对齐（MOVE 带坐标、WAIT_FOR_SECONDS
#: 带 time、APPEAR_AT_POS 带坐标且无 time）；5 无坐标无 time 且总是出现在
#: 路线末尾，对应 DISAPPEAR；3/4 都带 time 无坐标，按「跳跃幅度」分给
#: 两个 WAIT_CURRENT_* 变体（二者对停驻时长的贡献相同，分错不影响算路）。
CHECKPOINT_TYPES = {
    0: "MOVE",
    1: "WAIT_FOR_SECONDS",
    3: "WAIT_CURRENT_FRAGMENT_TIME",
    4: "WAIT_CURRENT_WAVE_TIME",
    5: "DISAPPEAR",
    6: "APPEAR_AT_POS",
}

#: 路线运动方式的数值枚举。``0`` = WALK（地面）、``1`` = FLY（飞行）。
MOTION_MODES = {0: "WALK", 1: "FLY"}

#: 「罚站到本关结束」的哨兵时长下限。
#:
#: 部分关卡用 999 / 1000 / 3000 / 9999 / 99999 秒表示「这只怪一直站着，
#: 别等了」，并不是真的要等这么久。全库 ``WAIT_FOR_SECONDS`` 的取值分布
#: 里有一条干净的断层——常规罚站最长只到 **600 秒**（600 出现 4 次），
#: 下一个取值直接跳到 **999 秒**（出现 751 次），正是哨兵：
#:
#:   ======  ======  说明
#:   取值    次数
#:   ======  ======  ==================
#:   ≤ 600   1492    真实罚站时长
#:   999      751    哨兵（永久停驻）
#:   1000      51    哨兵
#:   3000       5    哨兵
#:   9999      36    哨兵
#:   99999      6    哨兵
#:   ======  ======  ==================
#:
#: 若当成字面值，路线总时长会变成 10001 秒，时间轴被拉成一条直线、罚站
#: 提示显示「还剩 9999 秒」，就是「罚站时间混乱」的表现。
#:
#: 处理办法：把这类值**钳到** :data:`WAIT_SENTINEL_CLAMP`，既保留「永久」
#: 的语义，又不会污染时间轴刻度。
WAIT_SENTINEL_MIN = 900.0

#: 哨兵被钳制后使用的时长（秒）。取全部真实罚站的上界（600 秒），
#: 既覆盖了任何真实关卡的最长罚站，又让播放条刻度保持可读。
WAIT_SENTINEL_CLAMP = 600.0


def clamp_wait_time(v, limit: float = WAIT_SENTINEL_CLAMP) -> float:
    """把「永久停驻」哨兵时长钳到 ``limit``，其余原样返回。

    负值（``maxTimeWaitingForNextWave`` 里的 -1 之类）一律按 0 处理。
    """
    try:
        t = float(v or 0.0)
    except (TypeError, ValueError):
        return 0.0
    if t <= 0.0:
        return 0.0
    if t >= WAIT_SENTINEL_MIN:
        return float(limit)
    return t


def checkpoint_kind(v) -> str:
    """把检查点 ``type`` 归一化成字符串（兼容老关卡的数值枚举）。

    未知值原样转成字符串——上层的 ``kind_upper`` 判定会把它当成「不认识的
    类型」，既不占坐标也不加停驻时间，比当成 MOVE 把路线拽到 (0,0) 安全。
    """
    if isinstance(v, bool):
        return "MOVE"
    if isinstance(v, int):
        return CHECKPOINT_TYPES.get(v, str(v))
    s = str(v or "").strip()
    if not s:
        return "MOVE"
    if s.isdigit():
        return CHECKPOINT_TYPES.get(int(s), s)
    return s.upper()


def motion_mode_name(v, default: str = "WALK") -> str:
    """把 ``motionMode`` 归一化成 ``WALK`` / ``FLY``（兼容数值枚举）。"""
    if isinstance(v, bool):
        return default
    if isinstance(v, int):
        return MOTION_MODES.get(v, default)
    s = str(v or "").strip()
    if not s:
        return default
    if s.isdigit():
        return MOTION_MODES.get(int(s), default)
    return s.upper()


@dataclass
class RoutePoint:
    """路线检查点。

    kind 取值（实测自关卡 JSON）::

        MOVE                        走向 position
        APPEAR_AT_POS               在 position 处凭空出现（瞬移，不是走）
        WAIT_FOR_SECONDS            原地停驻 time 秒，position 为占位 (0,0)
        WAIT_CURRENT_FRAGMENT_TIME  原地停驻 time 秒，position 为占位 (0,0)
        DISAPPEAR                   原地离场，position 为占位 (0,0)
    """

    row: float
    col: float
    kind: str = "MOVE"
    wait_time: float = 0.0
    #: 该停驻是否来自「永久站桩」哨兵值（``time`` ≥ :data:`WAIT_SENTINEL_MIN`）。
    #:
    #: ``wait_time`` 已被 :func:`clamp_wait_time` 钳到
    #: :data:`WAIT_SENTINEL_CLAMP`，但一条路线里可能有**多个**哨兵停驻
    #: （act26side_01 route0 就是两段 999 秒中间夹着巡逻），逐个钳完再相加
    #: 仍会得到 1200 秒。所以保留这个标记，让 ``routes.analyze_route`` 知道
    #: 「这条路线存在无限站桩」，从而把**合计**压到上限，而不是逐项压。
    wait_sentinel: bool = False
    #: 目标点相对**所在格中心**的偏移，原始 JSON 的 ``reachOffset``。
    #: 存的是 ``(x, y)``：x 是横向（列方向），y 是纵向（行方向），
    #: 实测取值都在 ±0.5 以内。
    reach_offset: Tuple[float, float] = (0.0, 0.0)

    @property
    def offset_rc(self) -> Tuple[float, float]:
        """把 ``(x, y)`` 偏移换成 ``(行偏移, 列偏移)``。

        两套坐标的轴对应关系（``x`` -> 列、``y`` -> 行、正号）是实测
        标定的：拿全部关卡里 |offset| ≥ 0.3 的 1374 个检查点做检验，
        把偏移方向当成「敌人在墙的哪一侧」，8 种轴/符号组合里
        ``x→列, y→行, 取正`` 的可通行率最高（69.4%，次优 63.4%）；
        另一组独立检验（偏移后连线穿过不可通行格的比例）也得出同样结论。
        标定错了会让敌人整体偏到墙里去，所以别随手改符号。
        """
        return (float(self.reach_offset[1]), float(self.reach_offset[0]))

    @property
    def kind_upper(self) -> str:
        return str(self.kind).upper()

    @property
    def has_position(self) -> bool:
        """该检查点是否带真实坐标。"""
        return self.kind_upper in POSITIONED_CHECKPOINTS

    @property
    def is_teleport(self) -> bool:
        return self.kind_upper == "APPEAR_AT_POS"

    @property
    def is_wait(self) -> bool:
        return self.kind_upper.startswith("WAIT")

    @property
    def is_duration_wait(self) -> bool:
        """该 WAIT 检查点的 ``wait_time`` 是不是**真·秒数**。

        三种 WAIT 的语义差别很大（见 ``codex_fields.json`` 的
        checkpoints[].type 说明）：

          * ``WAIT_FOR_SECONDS``          — 原地停 ``time`` 秒   ← 只有它是时长
          * ``WAIT_CURRENT_FRAGMENT_TIME``— 停到**当前波次片段**结束
          * ``WAIT_CURRENT_WAVE_TIME``    — 停到**整波**结束

        后两者的 ``time`` 是「波次时间轴上的刻度值」，不是「要停多少秒」。
        把它们当秒数累加会得出荒谬的罚站时长——实测 ``act18d3_ex08`` R1
        被算成 600 秒（该关片段最长跨度只有 60 秒）、``main_05-07`` R1
        算成 220 秒（实际 29.5 秒）。全库共 458 条路线 / 86 个地图文件
        受影响。

        精确求解需要「停到第几秒」的那个时刻表（要按波次推进推算），
        这里暂按 0 处理并在 UI 上标注，避免给出错误数字。宁可少算也
        不要错算——错算会让用户误判出怪节奏。
        """
        return self.kind_upper == "WAIT_FOR_SECONDS"


@dataclass
class Route:
    """敌人行动路线。"""

    motion_mode: str = "WALK"
    start: Tuple[int, int] = (0, 0)
    end: Tuple[int, int] = (0, 0)
    checkpoints: List[RoutePoint] = field(default_factory=list)
    allow_diagonal_move: bool = True
    #: 起点格偏移，原始 JSON 的 ``spawnOffset``，同为 ``(x, y)``
    spawn_offset: Tuple[float, float] = (0.0, 0.0)
    #: 在原始 JSON routes 数组中的下标，便于回溯
    index: int = 0

    @property
    def spawn_offset_rc(self) -> Tuple[float, float]:
        """起点偏移换成 ``(行偏移, 列偏移)``，规则同 ``RoutePoint.offset_rc``。"""
        return (float(self.spawn_offset[1]), float(self.spawn_offset[0]))


@dataclass
class GameMap:
    """关卡地图。"""

    level_id: str
    name: str = ""
    width: int = 0
    height: int = 0
    #: [row][col] -> Tile
    tiles: List[List[Tile]] = field(default_factory=list)
    routes: List[Route] = field(default_factory=list)
    #: 真实出怪格 / 终点格，直接从 mapData.tiles 的 tile_start / tile_end
    #: 读出来。之前渲染是靠遍历每条路线的 start/end 画框，同一格会被
    #: 反复覆盖，而且路线端点≠门格，导致红蓝门位置混乱。
    spawn_tiles: List[Tuple[int, int]] = field(default_factory=list)
    goal_tiles: List[Tuple[int, int]] = field(default_factory=list)
    #: 关卡选项，含 moveMultiplier / maxLifePoint 等
    options: Dict[str, float] = field(default_factory=dict)
    #: 原始 tile 定义表（tileKey -> 属性），便于查代价
    tile_defs: List[Dict] = field(default_factory=list)

    def tile_at(self, row: int, col: int) -> Optional[Tile]:
        if 0 <= row < self.height and 0 <= col < self.width:
            return self.tiles[row][col]
        return None

    def route_by_index(self, index) -> Optional[Route]:
        """按 ``Route.index``（= 原始 JSON routes 下标）取路线。

        为什么需要这个：``routes`` 列表在解析时会丢掉 ``motionMode=E_NUM``
        的剧情占位路线（全库 9663 条），所以**列表位置 ≠ Route.index**。
        而 ``SpawnEvent.route_index`` 记的是原始 JSON 下标（见
        :class:`~.timeline.SpawnEvent` 的注释），UI 拿它去取路线时如果
        写成 ``gm.routes[route_index]`` 就会取到隔壁那条——表现为「点开出怪
        行，画出来的是别人走的线」。全库有 1980 关存在这种错位，涉及
        81813 只出怪（52.2%）。

        这里先按 ``Route.index`` 精确匹配（O(n)，但 n 通常 < 100，且
        UI 是点击时才走这条路，不热）。匹配不上再退回列表位置，保证
        老调用方（手工构造 GameMap、没有设 index 的测试）仍能工作。
        """
        if index is None:
            return None
        try:
            want = int(index)
        except (TypeError, ValueError):
            return None
        for r in self.routes:
            if r.index == want:
                return r
        if 0 <= want < len(self.routes):
            return self.routes[want]
        return None

    @property
    def move_multiplier(self) -> float:
        return float(self.options.get("moveMultiplier", 0.5))

    @property
    def max_life(self) -> int:
        return int(self.options.get("maxLifePoint", 3))

    @property
    def initial_cost(self) -> int:
        return int(self.options.get("initialCost", 10))

    @property
    def max_cost(self) -> int:
        return int(self.options.get("maxCost", 99))