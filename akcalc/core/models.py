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


@dataclass
class Tile:
    """地图地块。"""

    row: int
    col: int
    tile_key: str = ""
    height_type: str = "LOWLAND"
    buildable_type: str = "NONE"
    passable_mask: str = "ALL"

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
#: WAIT_CURRENT_FRAGMENT_TIME / DISAPPEAR）在关卡 JSON 里的 position
#: 一律是占位值 (0, 0)，**不能**当作途经点，否则会把路线算成绕经左上角。
POSITIONED_CHECKPOINTS = frozenset({"MOVE", "APPEAR_AT_POS"})


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