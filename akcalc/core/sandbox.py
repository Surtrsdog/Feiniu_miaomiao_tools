"""沙盘推演：在寻路图上摆干员、放箱子、踢敌人、加减速。

这个模块只做「状态 + 计算」，完全不碰 tkinter。界面层（ui/sandbox_panel.py）
负责画和点，两者通过下面这几个方法交互。

设计上的三条铁律
================

1. **只有箱子影响寻路。**
   游戏里敌人的路线只被「道路障碍物 / 静态障碍物」改变；干员是碰撞级的
   阻挡——敌人照原路走过来，撞上了才停下开打，**不会提前绕路**。
   所以 `boxes` 会传给 ``analyze_all(blocked=...)``，`operators` 永远不会。
   把干员塞进 blocked 会画出「敌人绕开干员走」，这与游戏行为相反，
   属于错误的模拟，比不做还糟。

2. **减速只作用于移动段，罚站是常量。**
   实测 a001_02 route[0]：move_speed 1.0 -> 0.5 时，移动段 8.83s -> 17.66s
   精确翻倍，而 pre_wait 122.00s 一动不动。所以时间必须按段积分，
   直接拿 total_time 乘倍率会得出「减速 50% 后 261 秒到达」这种离谱结果。

3. **飞行单位不吃地面阻挡。**
   对 FLY 路线放箱子无效，箱子只对 GROUND 路线重算。
"""

from __future__ import annotations

import copy
import math
from typing import Dict, List, Optional, Set, Tuple

from . import routes as RT
from .models import GameMap, Route
from .pathfinding import find_path
from .sandbox_track import (ACT_SKILL, CoarseTrack, Deployment, SkillCycle,
                            SkillSim, can_deploy)

Coord = Tuple[int, int]


class OperatorPiece:
    """一枚干员棋子。

    只存摆放需要的最小信息：位置、朝向、干员 id 和用于显示的名字/职业。
    攻击范围用 `range_cells` 现算（选中时才算，不常驻）。

    阻挡相关的三个字段是后加的：``is_ranged`` 决定能不能挡地面敌人
    （高台上的远程位阻挡数为 0），``block_count`` 是能同时挡几只，
    ``can_block_fly`` 是「飞行干员可挡飞行敌人」那条规则——默认 False，
    只有明确知道该干员能拦飞行单位时才打开。
    """

    __slots__ = ("row", "col", "op_id", "name", "profession", "facing",
                 "range_cells", "uid", "is_ranged", "block_count",
                 "can_block_fly", "ground", "cost", "range_id")

    def __init__(self, row: int, col: int, op_id: str = "",
                 name: str = "", profession: str = "", facing: str = "RIGHT"):
        self.row = int(row)
        self.col = int(col)
        self.op_id = op_id
        self.name = name or (op_id or "干员")
        self.profession = profession or ""
        #: LEFT / RIGHT / UP / DOWN —— 影响攻击范围朝哪边展开
        self.facing = facing or "RIGHT"
        #: 选中时算好的攻击范围格集合（不选中时为 None，省内存）
        self.range_cells: Optional[Set[Coord]] = None
        #: B4 §7: 基础范围 id（如 "3-1"），从 character_table 取
        self.range_id: Optional[str] = None
        #: 对应 ``sandbox_track.Deployment.uid``，撤退时靠它回写粗轴
        self.uid = 0
        #: 远程位（高台）
        self.is_ranged = False
        #: 阻挡数
        self.block_count = 0
        #: 能否阻挡飞行敌人
        self.can_block_fly = False
        #: ``HIGH`` / ``LOW``
        self.ground = "LOW"
        #: 部署费用
        self.cost = 0

    @property
    def pos(self) -> Coord:
        return (self.row, self.col)

    @property
    def blocks(self) -> int:
        """实际阻挡数。远程位恒为 0。"""
        if self.is_ranged:
            return 0
        return max(0, int(self.block_count or 0))


class Sandbox:
    """沙盘状态与计算。

    典型用法::

        sb = Sandbox(game_map, timeline)
        sb.place_box(4, 2)              # 放箱子 -> 自动重算路径
        sb.place_operator(5, 3, ...)    # 放干员 -> 不影响路径
        sb.kick(event_key)              # 踢掉某只敌人
        sb.add_slow(event_key, 0.5, 10) # 减速 50%，持续 10 秒
        sb.pose_at(event_key, 30.0)     # 第 30 秒它在哪
    """

    def __init__(self, game_map: GameMap, timeline=None,
                 analyses: Optional[List[RT.RouteAnalysis]] = None,
                 fold_random: bool = False):
        self.game_map = game_map
        self.timeline = timeline
        #: 是否把 ``randomSpawnGroupKey`` 加权候选包折叠成一个代表。
        #:
        #: 候选包是「同 key 的几条动作里按 weight 抽一条」，全列出来会把
        #: 「N 选 1」当成 N 只——``act1multi_football`` 一个 ``ball`` 包下
        #: 就有 810 个备选，全列会显示 1393 只而实机一局约 584 只；
        #: ``rogue6_c-2``（咩的朋友）也会把角兽算成两倍。
        #: 默认 False 保持旧行为（全列备选，信息量大，适合研究）；
        #: 沙盘要模拟实机编队时置 True，见 ``timeline.fold_random_packs()``。
        self.fold_random: bool = bool(fold_random)
        #: 只有箱子进这里，干员永远不进
        self.boxes: Set[Coord] = set()
        #: enemy_id -> 出生后原地不能动的秒数（【休憩】）。
        #:
        #: 为什么不从路线里读：这个时长**不在路线检查点里**，它是敌人
        #: 天赋（``Revive.unmovable_duration``），还可能被关卡覆盖。
        #: 「咩的朋友」``ro6_c_2`` 的角兽 23 条路线 ``checkpoints`` 全是
        #: 空数组，只看路线会得出「罚站 0 秒」——实机是每只出场先站 90 秒
        #: （敌人库默认 150s，本关被 ``enemyDbRefs`` 覆盖成 90s）。
        #: 由 UI 层从 ``EnemyStats.spawn_unmovable`` 灌进来，核心不依赖敌人库。
        self.spawn_wait: Dict[str, float] = {}
        #: 按位置索引的干员棋子
        self.operators: Dict[Coord, OperatorPiece] = {}
        #: 最近一次 :meth:`deploy` 失败的原因（成功时清空）。
        #: 界面用它显示真实原因，避免把所有失败都说成「已经有干员了」。
        self.last_deploy_error: str = ""
        #: 被踢掉的敌人，键是 `_event_key()` 的返回值
        self.kicked: Set[str] = set()
        #: [(event_key, start_s, end_s, mult)] —— 减速区间
        self.buffs: List[Tuple[str, float, float, float]] = []
        #: 路线的基准分析（无箱子时）。放箱子后用它做「续算」的参照。
        self.base_analyses: List[RT.RouteAnalysis] = list(analyses or [])
        self.analyses: List[RT.RouteAnalysis] = list(analyses or [])
        #: 按 route_index 索引的分析结果，避免 analysis_for 每次线性扫描。
        #: 必须**立刻**用构造参数里的 analyses 填好：加载关卡时走的是
        #: ``Sandbox(gm, timeline, analyses)`` 这条路，不会经过
        #: :meth:`reanalyze`，以前这里留空就导致 analysis_for() 永远返回
        #: None -> pose_at() 返回 None -> 场上一只敌人都画不出来。
        self._by_route: Dict[int, RT.RouteAnalysis] = {
            int(getattr(ra, "route_index", -1)): ra
            for ra in self.analyses if ra is not None}
        #: 粗轴：部署 / 撤退 / 开技能的历史记录，与 operators 共用
        #: ``Deployment`` 对象，撤退时回写 ``retreat_time``。
        self.track: CoarseTrack = CoarseTrack()
        #: 技能回转模拟器（只算 SP，不模拟技能效果）。
        #: 全局默认（attack_interval=1.0），用于无 op_id 或查不到的降级。
        self.skill_sim: SkillSim = SkillSim(1.0)
        #: 按 ``op_id`` 缓存的技能回转模拟器——每个干员用真实的
        #: ``attack_interval`` 初始化，修复 89.4% 干员速率偏差。
        self._op_skill_sims: Dict[str, SkillSim] = {}
        #: 干员攻击间隔缓存：op_id -> float。懒加载自 operators.json。
        self._op_attack_interval: Dict[str, float] = {}
        #: 撤销 / 重做历史栈（UI 按钮 + Ctrl+Z / Ctrl+Y）。
        self._undo_stack: List[dict] = []
        self._redo_stack: List[dict] = []
        #: 阻挡分配缓存：同一配置反复问 pose_at 时只算一次。
        self._plan_cache_sig: Optional[tuple] = None
        self._plan_cache: Dict[str, tuple] = {}
        #: 逐敌人移速缓存：enemy_id -> base_speed（B批次接线用）。
        self._speed_table: Dict[str, float] = {}
        #: 按 ``(route_index, round(move_speed, 4))`` 缓存的路线分析
        #: （B3 §5.7 逐敌人移速）。``analysis_for`` 从这里取，
        #: 避免同一条路线对不同速度的敌人重复算。
        self._speed_cache: Dict[Tuple[int, float], "RT.RouteAnalysis"] = {}
        # B4 §7: 加载干员范围 id 缓存（char_id → {elite: rangeId}）
        self._load_char_ranges()
        # B2 §5: 部署费用经济系统
        opts = getattr(game_map, "options", None) or {}
        from .dp import DPEconomy, RedeployPenalty
        self.dp = DPEconomy(
            initial=float(opts.get("initialCost", 10)),
            cap=float(opts.get("maxCost", 99)),
            interval=float(opts.get("costIncreaseTime", 1.0)),
        )
        self._redeploy_penalty = RedeployPenalty()
        self.character_limit = int(opts.get("characterLimit", 8))
        self.max_life = int(opts.get("maxLifePoint", 3))
        self._life = int(self.max_life)
        if not self.analyses:
            self.recompute()
            # ⚠ 现算出来的这批结果同时也是「基准」：``box_check`` 拿
            # ``base_analyses`` 当参照判断「这块箱子有没有堵死路线」，留着
            # 空列表就等于闸门失效——任何箱子都会被判成安全。
            self.base_analyses = list(self.analyses)

    # ------------------------------------------------------------ 敌人标识

    @staticmethod
    def _event_key(ev) -> str:
        """给一只敌人一个稳定且唯一的键。

        `SpawnEvent` 里有 seq / route_index / wave_index / fragment_index /
        action_index，组合起来在单张图内唯一。不用 ``id(ev)``——那个在
        重建 timeline 后会变，存档/重算都对不上。
        """
        return "%s|%s|%s|%s|%s" % (
            getattr(ev, "route_index", -1),
            getattr(ev, "seq", -1),
            getattr(ev, "wave_index", -1),
            getattr(ev, "fragment_index", -1),
            getattr(ev, "action_index", -1),
        )

    def enemy_move_speed(self, event) -> float:
        """返回指定敌人的基础移速（格/秒）。

        优先从 ``_speed_table``（enemy_id → speed）取值；
        查不到时降级为 1.0。``_speed_table`` 由调用方
        （如 ``recompute_with_speeds`` 或外部初始化）填充。
        """
        eid = getattr(event, "enemy_id", "") or ""
        if eid in self._speed_table:
            return self._speed_table[eid]
        return 1.0

    def _speed_key(self, event) -> Tuple[int, float]:
        """返回 ``(route_index, round(speed, 4))`` 用于查速度缓存。"""
        idx = int(getattr(event, "route_index", -1))
        sp = round(float(self.enemy_move_speed(event)), 4)
        return (idx, sp)

    def _load_char_ranges(self) -> None:
        """B4 §7: 启动时加载干员范围 id 缓存 + 范围形状表。"""
        try:
            from . import ranges as _R
            import os
            base = os.path.join(os.path.dirname(__file__), "..", "data")
            base = os.path.normpath(base)
            # 加载范围形状表（73 个 id）
            rt = os.path.join(base, "range_table.json")
            if os.path.isfile(rt):
                _R.load_range_table(rt)
            # 加载干员 → rangeId 映射（461 个干员）
            cr = os.path.join(base, "cache", "char_ranges.json")
            if os.path.isfile(cr):
                _R.load_char_ranges(cr)
        except Exception:
            pass

    def _lookup_range_id(self, op_id: str) -> Optional[str]:
        """B4 §7：查干员的基础范围 id。

        优先从 ``character_table`` 缓存（``ranges.load_char_ranges``）取；
        查不到返回 ``None``（UI 退回 3×3 兜底）。
        """
        if not op_id:
            return None
        try:
            from . import ranges as _R
            return _R.get_char_range_id(op_id)
        except Exception:
            return None

    def events(self) -> list:
        """本关所有出怪事件（按时间排序）。

        ``fold_random=True`` 时先把随机候选包折叠成一个代表，见
        :attr:`fold_random`。

        分支出怪（``branches[]``，侵入式调用）已排除——它们是装置/陷阱
        触发的条件出怪，不属于波次正常出怪。
        """
        if self.timeline is None:
            return []
        if self.fold_random:
            try:
                evs = list(self.timeline.fold_random_packs())
            except AttributeError:
                evs = list(getattr(self.timeline, "events", []) or [])
        else:
            evs = list(getattr(self.timeline, "events", []) or [])
        # 排除分支出怪
        return [e for e in evs if not getattr(e, "branch", "")]

    def live_events(self) -> list:
        """没被踢掉的出怪事件。"""
        return [e for e in self.events() if self._event_key(e) not in self.kicked]

    # ------------------------------------------------------------ 摆放

    def boxes_only(self) -> Set[Coord]:
        """返回送进寻路的阻挡格。

        ⚠ 名字故意起得这么直白：**只有箱子**。干员绝不能出现在这里。
        每次要调 analyze_all 都用它，不要自己去拼路口。
        """
        return set(self.boxes)

    def place_box(self, row: int, col: int) -> bool:
        """放一个箱子。返回 False 表示这格本来就有箱子。"""
        pos = (int(row), int(col))
        if pos in self.boxes:
            return False
        self.boxes.add(pos)
        self._invalidate_plan()
        self.recompute()
        return True

    def remove_box(self, row: int, col: int) -> bool:
        pos = (int(row), int(col))
        if pos not in self.boxes:
            return False
        self.boxes.discard(pos)
        self._invalidate_plan()
        self.recompute()
        return True

    def clear_boxes(self) -> None:
        if self.boxes:
            self.boxes.clear()
            self._invalidate_plan()
            self.recompute()

    def place_operator(self, row: int, col: int, op_id: str = "",
                       name: str = "", profession: str = "",
                       facing: str = "RIGHT") -> OperatorPiece:
        """放一枚干员。**不触发路径重算**——干员不影响寻路。"""
        pos = (int(row), int(col))
        piece = OperatorPiece(row, col, op_id, name, profession, facing)
        self.operators[pos] = piece
        self._invalidate_plan()
        return piece

    def remove_operator(self, row: int, col: int) -> bool:
        ok = self.operators.pop((int(row), int(col)), None) is not None
        self._invalidate_plan()
        return ok

    def clear_operators(self) -> None:
        self.operators.clear()
        self._invalidate_plan()

    def operator_at(self, row: int, col: int) -> Optional[OperatorPiece]:
        return self.operators.get((int(row), int(col)))

    # ------------------------------------------------------------ 敌人操作

    def kick(self, event) -> None:
        """踢掉一只敌人（模拟被击杀）。"""
        self.kicked.add(self._event_key(event))
        self._invalidate_plan()

    def unkick(self, event) -> None:
        self.kicked.discard(self._event_key(event))
        self._invalidate_plan()

    def kick_all(self) -> None:
        for ev in self.events():
            self.kicked.add(self._event_key(ev))
        self._invalidate_plan()

    def restore_all(self) -> None:
        self.kicked.clear()
        self._invalidate_plan()

    def is_kicked(self, event) -> bool:
        return self._event_key(event) in self.kicked

    # ------------------------------------------------------------ 减速 buff

    def add_slow(self, event, mult: float, duration: float,
                 start: Optional[float] = None) -> None:
        """给一只敌人加一段减速 / 停顿。

        ``mult`` 是**速度倍率**（0.5 = 半速，不是「减 50%」），与游戏内
        ``move_speed`` 口径一致；``mult == 0`` 表示这一段**完全停住**
        （停顿/罚站效果），这是合法值，不能夹成 0.05——那样「停顿 3 秒」
        会变成 20 倍慢速，凭空多出 57 秒行程。``duration`` 是这段效果
        持续的**游戏秒**。

        起点会被夹到「这只敌人出场之后」：用户常把游标停在某处、对着
        一只还没出场的怪说「停顿 3 秒」，如果照字面把窗口放在游标上，
        整段会在它出现之前就过完，界面上看起来就是「设了没反应」。
        """
        mult = max(0.0, min(1.0, float(mult)))
        duration = max(0.0, float(duration))
        if duration <= 0:
            return
        spawn = float(getattr(event, "time", 0.0) or 0.0)
        t0 = float(start) if start is not None else spawn
        t0 = max(spawn, t0)
        self.buffs.append((self._event_key(event), t0, t0 + duration, mult))
        self._invalidate_plan()

    def clear_buffs(self, event=None) -> None:
        if event is None:
            self.buffs.clear()
        else:
            k = self._event_key(event)
            self.buffs = [b for b in self.buffs if b[0] != k]
        self._invalidate_plan()

    def buffs_of(self, event) -> List[Tuple[float, float, float]]:
        k = self._event_key(event)
        return [(a, b, m) for (kk, a, b, m) in self.buffs if kk == k]

    def speed_at(self, event, seconds: float) -> float:
        """seconds 时刻这只敌人的速度倍率。多个减速按乘法叠加。"""
        mult = 1.0
        for (a, b, m) in self.buffs_of(event):
            if a <= seconds < b:
                mult *= m
        return mult

    # ------------------------------------------------------------ 重算

    def recompute(self) -> List[RT.RouteAnalysis]:
        """重算所有路线（全局默认速度 1.0）。只有箱子参与，干员不参与。

        重算后清空按速度缓存——调用方需要时再调
        :meth:`rebuild_speed_cache`。
        """
        if not self.game_map:
            return []
        try:
            self.analyses = RT.analyze_all(
                self.game_map, blocked=self.boxes_only() or None)
        except Exception:
            # 寻路失败时保留上一次结果，别让界面直接变空
            if not self.analyses:
                self.analyses = []
        self._by_route = {int(getattr(ra, "route_index", -1)): ra
                          for ra in self.analyses}
        # 速度缓存失效（基础路线变了）
        self._speed_cache.clear()
        return self.analyses

    def rebuild_speed_cache(self) -> int:
        """B3 §5.7：按所有出怪事件的 ``moveSpeed`` 重建逐敌人移速缓存。

        遍历 ``events()``，对每个 ``(route_index, round(speed, 4))``
        组合算一次 ``analyze_route``，存入 ``_speed_cache``。
        返回新建的缓存条目数。
        """
        if not self.game_map or not self._by_route:
            return 0
        blocked = self.boxes_only() or None
        built = 0
        for ev in self.events():
            sk = self._speed_key(ev)
            if sk in self._speed_cache:
                continue
            idx = sk[0]
            if idx < 0 or idx >= len(self.game_map.routes):
                continue
            try:
                self._speed_cache[sk] = RT.analyze_route(
                    self.game_map, self.game_map.routes[idx],
                    move_speed=sk[1], blocked=blocked,
                    allow_diagonal=True)
                built += 1
            except Exception:
                continue
        return built

    def analysis_for(self, event_or_index) -> Optional[RT.RouteAnalysis]:
        """按出怪事件（或路线下标）取路线分析。

        B3 §5.7：传入 ``event`` 时优先查按 ``(route_index, speed)``
        缓存的分析结果（精确移速）；纯整数下标时退回全局默认
        （``_by_route``，speed=1.0）。
        """
        if isinstance(event_or_index, int):
            return self._by_route.get(int(event_or_index))
        ev = event_or_index
        idx = int(getattr(ev, "route_index", -1))
        # 优先查逐敌人移速缓存
        sk = self._speed_key(ev)
        ra = self._speed_cache.get(sk)
        if ra is not None:
            return ra
        # 降级：全局默认分析
        return self._by_route.get(idx)

    # ------------------------------------------------------------ 位置推算

    def spawn_unmovable_of(self, event) -> float:
        """这只敌人出生后要原地站多久（秒）。没有就 0。"""
        eid = getattr(event, "enemy_id", "") or ""
        try:
            return max(0.0, float(self.spawn_wait.get(eid, 0.0) or 0.0))
        except (TypeError, ValueError):
            return 0.0

    def pose_at(self, event, seconds: float) -> Optional[Tuple[float, float]]:
        """seconds 时刻这只敌人在哪（连续浮点格坐标）。

        实现要点：把「游戏时间」换算成「这条路线已经走了多久」，再交给
        ``RouteAnalysis.pose_at``。换算时要把这段路上的减速折算进去——
        减速期间敌人走得慢，同样的游戏时间对应的路线进度更少。

        阻挡是**在无阻挡轨迹之上加一段「原地罚站」**：先按无阻挡算出
        敌人会在哪个整格、什么时刻撞上干员；真被挡下（没超过该干员
        ``block_count`` 容量）后，从那一刻起位置就钉在干员格上，不再
        沿路线前进。容量按敌人到达该格的先后顺序分配。
        """
        ra = self.analysis_for(event)
        if ra is None or not getattr(ra, "reachable", True):
            return None
        t_spawn = float(getattr(event, "time", 0.0))
        elapsed_wall = float(seconds) - t_spawn
        if elapsed_wall < 0:
            return None
        # 出场罚站（【休憩】）：这段时间路线进度完全不涨，所以要先把
        # 它从墙上时长里扣掉，再折算减速。
        elapsed_wall -= self.spawn_unmovable_of(event)
        if elapsed_wall < 0:
            elapsed_wall = 0.0
        eff = self._effective_elapsed(event, elapsed_wall, t_spawn)
        try:
            plan = self._blocking_plan(seconds)
        except Exception:
            plan = {}
        rec = plan.get(self._event_key(event))
        if rec is not None:
            cell, arr_wall, release_wall, arr_eff, blocked = rec
            if blocked:
                if float(seconds) < float(arr_wall) - 1e-9:
                    # 还没走到阻挡格，正常走
                    pass
                elif float(seconds) < float(release_wall) - 1e-9:
                    # 正在被挡：用 blocking.py 几何模型算分散落点（bug C 修复）
                    anchor = self.block_anchor(event, seconds)
                    if anchor is not None:
                        return anchor
                    return (float(cell[0]), float(cell[1]))
                else:
                    # 干员已撤退，敌人从阻挡格继续走剩下的路
                    try:
                        resume = self._effective_elapsed(
                            event, max(0.0, float(seconds) - float(release_wall)),
                            float(release_wall))
                        return ra.pose_at(float(arr_eff) + resume)
                    except Exception:
                        pass
        try:
            return ra.pose_at(eff)
        except Exception:
            return None

    def _invalidate_plan(self) -> None:
        """状态变了，下一帧重新分配阻挡容量。"""
        self._plan_cache_sig = None
        self._plan_cache = {}

    def _plan_sig(self) -> tuple:
        """干员配置签名：配置不变时阻挡计划也不变。"""
        return tuple(sorted(
            (d.uid, d.row, d.col, d.deploy_time,
             d.retreat_time, d.block_count, d.can_block_fly)
            for d in self.track.all()
        ))

    def _route_cell_arrivals(self, ra) -> List[Tuple[Coord, float]]:
        """敌人无阻挡轨迹上每个格子的到达时刻（路线进度秒）。

        顺序与 ``RouteAnalysis.pose_at`` 一致：先吃 pre_wait（在起点
        原地），再逐段「移动 -> 停驻」。返回 ``[(格子, 到达时刻), ...]``。
        到达时刻是**路线进度时间**（``RouteAnalysis.pose_at`` 的入参），
        不是游戏墙钟；换算墙钟由 :meth:`_wall_elapsed_for_route` 负责。
        """
        out: List[Tuple[Coord, float]] = []
        acc = 0.0
        segs = [s for s in (getattr(ra, "segments", []) or [])
                if getattr(s, "path", None)]
        if segs:
            p0 = segs[0].path[0]
            out.append(((int(p0[0]), int(p0[1])), 0.0))
        acc = float(getattr(ra, "pre_wait", 0.0) or 0.0)
        for s in segs:
            path = s.path
            start = (int(path[0][0]), int(path[0][1]))
            if not out or out[-1][0] != start:
                out.append((start, acc))
            total = 0.0
            lens: List[float] = []
            for k in range(1, len(path)):
                d = math.hypot(path[k][0] - path[k - 1][0],
                               path[k][1] - path[k - 1][1])
                lens.append(d)
                total += d
            move = float(getattr(s, "time", 0.0) or 0.0)
            if total <= 0 or move <= 0:
                acc += move
            else:
                cum = 0.0
                for k, d in enumerate(lens, start=1):
                    cum += d
                    cell = (int(path[k][0]), int(path[k][1]))
                    arr = acc + move * (cum / total)
                    if out and out[-1][0] == cell:
                        continue
                    out.append((cell, arr))
                acc += move
            acc += float(getattr(s, "wait_after", 0.0) or 0.0)
        return out

    def _wall_elapsed_for_route(self, event, ra,
                                route_secs: float) -> float:
        """走完 ``route_secs`` 秒路线进度，需要多少墙钟秒（自出场起算）。

        与 :meth:`arrival_time` 同一套账：pre_wait / wait_after 是常量
        罚站，不乘减速；移动段交给 :meth:`_advance` 按 buff 折算。
        """
        route_secs = max(0.0, float(route_secs))
        spans = self.buffs_of(event)
        w = self.spawn_unmovable_of(event)
        pre = float(getattr(ra, "pre_wait", 0.0) or 0.0)
        take = min(route_secs, pre)
        w += take
        rem = route_secs - take
        for s in (getattr(ra, "segments", []) or []):
            move = float(getattr(s, "time", 0.0) or 0.0)
            if rem <= move:
                return w + self._advance(event, w, rem, spans)
            rem -= move
            w = self._advance(event, w, move, spans)
            wait = float(getattr(s, "wait_after", 0.0) or 0.0)
            if rem <= wait:
                return w + rem
            rem -= wait
            w += wait
        return w + rem

    def _blocking_plan(self, seconds: float):
        """seconds 时刻的阻挡分配：谁被哪枚干员挡在哪个格子。

        返回值以 ``_event_key`` 为键，值为 ``(阻挡格, 撞上干员的墙钟
        时刻, 解除阻挡的墙钟时刻, 撞上时已走的路线进度, 是否真被挡下)``。

        阻挡格的干员以「敌人到达那一刻是否在场」判断，而不是查询时刻：
        干员撤退后敌人要能从阻挡格继续往前走，不能凭空跳到路线末尾。

        ``block_count`` 按「同一格子、同一次部署」到达顺序分配：超出
        容量的敌人不被挡，继续沿路线前进（漏过去），这样阻挡数在全局上
        被严格限制住。
        """
        t = float(seconds)
        # 同配置内反复问每只敌人只算一次；状态计数对不上就失效重算。
        sig = self._plan_sig()
        if (self._plan_cache_sig == sig and self._plan_cache is not None):
            return self._plan_cache
        self._plan_cache_sig = sig
        self._plan_cache = {}
        plan = self._plan_cache
        # 候选按 (格, 部署 uid) 分组：同一格可能撤退后再部署，是两段
        # 独立的阻挡容量，不能混在一起分配。
        cands: Dict[Tuple[Coord, int], List[dict]] = {}
        for ev in self.live_events():
            if self.is_kicked(ev):
                continue
            t_spawn = float(getattr(ev, "time", 0.0))
            if t < t_spawn:
                continue
            ra = self.analysis_for(ev)
            if ra is None or not getattr(ra, "reachable", True):
                continue
            flying = bool(getattr(ra, "flying", False))
            key = self._event_key(ev)
            # B1 §4 bug A 修复：满票时 continue 看下一格，不再 break 整只丢弃
            for (cell, arr_eff) in self._route_cell_arrivals(ra):
                arr_wall = t_spawn + self._wall_elapsed_for_route(ev, ra,
                                                                  arr_eff)
                dep = None
                for d in self.track.all():
                    if (int(d.row), int(d.col)) != cell:
                        continue
                    if not d.alive_at(arr_wall):
                        continue
                    if d.is_ranged or int(d.block_count or 0) <= 0:
                        continue
                    if flying and not getattr(d, "can_block_fly", False):
                        continue
                    dep = d
                    break
                if dep is None:
                    continue
                release = (float(dep.retreat_time)
                           if dep.retreat_time is not None else math.inf)
                cands.setdefault((cell, dep.uid), []).append({
                    "arr_wall": arr_wall,
                    "key": key,
                    "arr_eff": arr_eff,
                    "release": release,
                    "cell": cell,
                })
                # B1 §4: 不 break —— 满票时继续看下一格（bug A 修复原逻辑在下方票券分配阶段处理）
        # 每格每段部署按到达先后发「挡票」；没拿到票的敌人漏过去。
        for (cell, uid), items in cands.items():
            dep = self.track.get(uid)
            cap = int(getattr(dep, "block_count", 0) or 0)
            for i, it in enumerate(sorted(items, key=lambda x: x["arr_wall"])):
                it["blocked"] = i < cap
        # 一只敌人可能经过多个阻挡格，取它真正被挡下的最早那一格。
        best_by_key: Dict[str, dict] = {}
        for items in cands.values():
            for it in items:
                if not it.get("blocked"):
                    continue
                cur = best_by_key.get(it["key"])
                if cur is None or it["arr_wall"] < cur["arr_wall"]:
                    best_by_key[it["key"]] = it
        for key, it in best_by_key.items():
            plan[key] = (it["cell"], it["arr_wall"], it["release"],
                         it["arr_eff"], True)
        return plan

    def _effective_elapsed(self, event, wall_elapsed: float,
                           t_spawn: float) -> float:
        """把墙上时间折算成「路线进度时间」。

        做法：把 [t_spawn, t_spawn+wall_elapsed] 按 buff 边界切成小段，
        每段用该段倍率折算。没有 buff 时就是恒等变换。

        ``m == 0``（停顿）时该段进度增量是 0——不是「乘个很小的数」，
        否则 3 秒停顿会被算成 0.15 秒进度，动画上看起来几乎没停。
        """
        spans = self.buffs_of(event)
        if not spans:
            return wall_elapsed
        t_end = t_spawn + wall_elapsed
        # 收集所有边界点
        cuts = {t_spawn, t_end}
        for (a, b, _m) in spans:
            if t_spawn < a < t_end:
                cuts.add(a)
            if t_spawn < b < t_end:
                cuts.add(b)
        pts = sorted(cuts)
        eff = 0.0
        for i in range(len(pts) - 1):
            a, b = pts[i], pts[i + 1]
            if b <= a:
                continue
            m = 1.0
            for (ba, bb, bm) in spans:
                if ba <= a < bb:
                    m *= bm
            eff += (b - a) * m
        return eff

    def arrival_time(self, event) -> Optional[float]:
        """这只敌人走到终点需要多少游戏秒（含减速/停顿）。

        罚站是常量，不乘倍率——这是实测出来的游戏行为。移动段则要按
        当时的速度倍率**逐段折算**。

        ⚠ 不能写成 ``move / m``：停顿（``m == 0``）时那样要么除零、要么
        被迫取一个「假装很快」的近似值。正确语义是「这段时间里路线进度
        完全不涨」，所以按 buff 边界切段、用进度速率正推墙上时间。
        """
        ra = self.analysis_for(event)
        if ra is None:
            return None
        t_spawn = float(getattr(event, "time", 0.0))
        # 出场罚站是常量，既不受减速影响，也不在 ra.total_time 里
        head = self.spawn_unmovable_of(event)
        spans = self.buffs_of(event)
        if not spans:
            return head + float(getattr(ra, "total_time", 0.0))
        w = t_spawn + head + float(getattr(ra, "pre_wait", 0.0) or 0.0)
        for seg in getattr(ra, "segments", []) or []:
            w = self._advance(event, w, float(getattr(seg, "time", 0.0) or 0.0),
                              spans)
            # 罚站不折算
            w += float(getattr(seg, "wait_after", 0.0) or 0.0)
        return max(0.0, w - t_spawn)

    def _advance(self, event, w0: float, route_secs: float, spans) -> float:
        """走完 ``route_secs`` 秒的**路线进度**，需要多少墙上秒。

        把 [w0, ...) 按 buff 边界切成倍率恒定的段：倍率 m 的段里，墙上
        1 秒推进 m 秒进度；m == 0 的段里进度不涨，墙上时间照走。
        """
        need = max(0.0, float(route_secs))
        w = float(w0)
        if need <= 0:
            return w
        cuts = set()
        for (a, b, _m) in spans:
            if b > w:
                cuts.add(float(a))
                cuts.add(float(b))
        pts = sorted(p for p in cuts if p > w)
        guard = 0
        while need > 1e-9 and guard < 4000:
            guard += 1
            m = self.speed_at(event, w)
            nxt = next((p for p in pts if p > w + 1e-12), None)
            if m <= 1e-9:
                # 停住：进度不涨，直接跳到这段效果的末尾
                if nxt is None:
                    # 永久停住（数据异常）：给一个可见的上限，别返回 inf
                    return w + need + 3600.0
                w = nxt
                continue
            if nxt is None:
                return w + need / m
            can = (nxt - w) * m
            if can >= need:
                return w + need / m
            need -= can
            w = nxt
        return w + need

    # ------------------------------------------------------------ 阻挡提示

    def overlap(self, seconds: Optional[float] = None) -> Set[Coord]:
        """路线会经过、且上面站着干员的格子。

        干员的唯一「功能」：提示这里会发生阻挡。**不改变路线。**

        ``seconds`` 给定时按粗轴回放那一刻在场的干员（拖动游标看过去
        时，阻挡提示也要跟着回到过去）；为 None 时按当前场上算。
        """
        ops = self.operators if seconds is None else self.operators_at(seconds)
        op_cells = set(ops.keys())
        if not op_cells:
            return set()
        hit: Set[Coord] = set()
        for ra in self.analyses:
            if getattr(ra, "flying", False):
                # 飞行单位不撞地面干员
                continue
            for seg in getattr(ra, "segments", []) or []:
                for pos in getattr(seg, "path", []) or []:
                    p = (int(pos[0]), int(pos[1]))
                    if p in op_cells:
                        hit.add(p)
        return hit

    def routes_through(self, row: int, col: int) -> List[int]:
        """哪些路线会经过这一格（给「放这里会不会漏怪」判断用）。

        一条路线可能来回多次经过同一格，所以按 route_index 去重；
        以前用 ``for/else + break`` 双重跳出，读起来费劲且容易改错。
        """
        want = (int(row), int(col))
        out: List[int] = []
        seen: Set[int] = set()
        for ra in self.analyses:
            idx = int(getattr(ra, "route_index", -1))
            if idx in seen:
                continue
            for seg in getattr(ra, "segments", []) or []:
                hit = any((int(p[0]), int(p[1])) == want
                          for p in (getattr(seg, "path", []) or []))
                if hit:
                    out.append(idx)
                    seen.add(idx)
                    break
        return out

    # ------------------------------------------------------------ 部署与阻挡

    def tile_at(self, row: int, col: int):
        """取地图上的地块，越界返回 None。"""
        gm = self.game_map
        if gm is None:
            return None
        try:
            if row < 0 or col < 0 or row >= gm.height or col >= gm.width:
                return None
            return gm.tiles[row][col]
        except (IndexError, TypeError):
            return None

    def deploy_check(self, row: int, col: int, is_ranged: bool,
                     cost: float = 0.0, now: Optional[float] = None) -> Tuple[bool, str]:
        """这格能不能放这枚干员。返回 ``(可以, 原因)``。

        规则（与游戏一致）：
        * 远程位只能放高台（``HIGHLAND`` + ``buildable_ranged``）
        * 近战位只能放地面（``LOWLAND`` + ``buildable_melee``）
        * 已有干员或箱子的格子不能放
        * B2 §5: 在场干员数达上限 → 拒绝
        * B2 §5: 费用不足 → 拒绝
        """
        pos = (int(row), int(col))
        if pos in self.operators:
            return (False, "这格已经有干员了")
        if pos in self.boxes:
            return (False, "这格有箱子")
        ok, why = can_deploy(self.tile_at(row, col), is_ranged)
        if not ok:
            return (False, why)
        # B2 §5: 人数上限
        t = float(now) if now is not None else 0.0
        alive = len(self.operators_alive(t))
        if alive >= self.character_limit:
            return (False, "在场干员已达上限 %d" % self.character_limit)
        # B2 §5: 费用
        self.dp.settle(t)
        if cost > 0 and not self.dp.can_afford(cost):
            return (False, "部署费用不足（需 %.0f，当前 %.0f）" % (cost, self.dp.current))
        return (True, "")

    def box_check(self, row: int, col: int) -> Tuple[bool, str]:
        """箱子能不能放这里。

        箱子的唯一硬约束是**不能把所有通往蓝门的路堵死**。游戏里
        玩家确实放不下这种箱子，所以这不只是体验问题，而是模拟
        正确性的一部分。

        判定办法：试放、重算、看是否有路线变不可达。任何一条原本
        可达的路线变成不可达，就拒绝。
        """
        pos = (int(row), int(col))
        if pos in self.boxes:
            return (False, "这格已经有箱子了")
        if pos in self.operators:
            return (False, "这格有干员")
        gm = self.game_map
        if gm is None:
            return (False, "还没载入地图")
        if self.tile_at(row, col) is None:
            return (False, "这里没有地块")
        self.boxes.add(pos)
        try:
            trial = RT.analyze_all(gm, blocked=set(self.boxes))
        except Exception:
            self.boxes.discard(pos)
            return (False, "寻路计算失败")
        self.boxes.discard(pos)
        base = {int(getattr(ra, "route_index", i)): ra
                for i, ra in enumerate(self.base_analyses)}
        dead = 0
        for i, ra in enumerate(trial):
            before = base.get(int(getattr(ra, "route_index", i)))
            if before is None:
                continue
            # 字段名是 reachable：RouteAnalysis 上没有 ok 属性，
            # 用 getattr(ra, "ok", True) 会永远拿到默认 True，闸门形同虚设。
            if bool(getattr(before, "reachable", True)) and \
                    not bool(getattr(ra, "reachable", True)):
                dead += 1
        if dead:
            return (False, "这块箱子会堵死 %d 条通往蓝门的路线" % dead)
        return (True, "")

    def deploy(self, row: int, col: int, dep: Deployment) -> bool:
        """把一次部署落到场上（同时登记粗轴）。

        ``dep`` 是 ``sandbox_track.Deployment``。让沙盘和粗轴共用同一个
        对象：撤退时把 ``retreat_time`` 填上，粗轴就自动有了正确区间，
        不需要在两处同步状态。

        失败时把原因写进 :attr:`last_deploy_error`，界面据此显示真实
        原因——返回 False 的原因有好几种，统一报「已经有干员了」会把
        「费用不足」「挡住蓝门」全说成占位冲突，用户根本无从下手。
        """
        self.last_deploy_error = ""
        pos = (int(row), int(col))
        if pos in self.operators:
            self.last_deploy_error = "这格已经有干员了"
            return False
        # B2 §5: 扣费（失败则拒绝部署）
        if dep.cost > 0 and not self.dp.spend(dep.cost):
            self.last_deploy_error = (
                "部署费用不足（需 %d，当前 %.0f）"
                % (int(dep.cost), float(self.dp.current)))
            return False
        self.track.add(dep)
        piece = OperatorPiece(row, col, dep.op_id, dep.name, dep.profession,
                              dep.facing)
        piece.uid = dep.uid
        piece.is_ranged = bool(dep.is_ranged)
        piece.block_count = int(dep.block_count)
        piece.can_block_fly = bool(getattr(dep, "can_block_fly", False))
        piece.ground = dep.ground
        piece.cost = int(dep.cost)
        # B4 §7: 查基础范围 id（从 operators.json 或 character_table 缓存）
        piece.range_id = self._lookup_range_id(dep.op_id)
        # B4 §7: 立即算出初始朝向的范围格
        if piece.range_id:
            try:
                from . import ranges as _R
                cells = _R.get_cells(piece.range_id, dep.facing or "RIGHT")
                if cells:
                    piece.range_cells = cells
            except Exception:
                pass
        self.operators[pos] = piece
        self._invalidate_plan()
        return True

    def retreat(self, row: int, col: int,
                at_time: Optional[float] = None) -> bool:
        """撤掉一枚干员，并在粗轴上记下撤退时刻。"""
        pos = (int(row), int(col))
        piece = self.operators.pop(pos, None)
        if piece is None:
            return False
        dep = self.track.get(int(getattr(piece, "uid", 0) or 0))
        if dep is not None and dep.retreat_time is None:
            dep.retreat_time = float(at_time or 0.0)
            # B2 §5: 撤退返还 + 再部署惩罚
            self.dp.refund(dep.cost)
            if dep.op_id:
                self._redeploy_penalty.add(dep.op_id)
        self._invalidate_plan()
        return True

    def retreat_all(self, at_time: Optional[float] = None) -> None:
        for pos in list(self.operators.keys()):
            self.retreat(pos[0], pos[1], at_time)
        self._invalidate_plan()

    def life_at(self, seconds: float) -> int:
        """B2 §5: 某时刻的剩余生命值。

        每只走到路线终点的敌人扣 ``lifePointReduce``（0 = 不计生命）。
        返回剩余生命值，不会低于 0。
        """
        t = float(seconds)
        lost = 0
        for ev in self.events():
            if self.is_kicked(ev):
                continue
            ra = self.analysis_for(ev)
            if ra is None or not getattr(ra, "reachable", True):
                continue
            t_spawn = float(getattr(ev, "time", 0.0))
            if t < t_spawn:
                continue
            at = self.arrival_time(ev)
            if at is not None and t >= t_spawn + at:
                # 这只敌人在 t 时刻已到达终点（漏了）
                reduce_val = int(getattr(ev, "lifePointReduce", 1) or 1)
                if reduce_val > 0:
                    lost += reduce_val
        return max(0, self.max_life - lost)

    def deploy_cost_for(self, op_id: str) -> float:
        """B2 §5: 算某干员当前实际部署费用（含再部署惩罚倍率）。

        从 operators.json 取基础费用，乘以惩罚倍率。
        查不到时返回 0。
        """
        base = self._get_operator_cost(op_id)
        mult = self._redeploy_penalty.multiplier(op_id)
        return round(base * mult, 1)

    def _get_operator_cost(self, op_id: str) -> float:
        """从 operators.json 取干员基础部署费用。"""
        try:
            from .prts_operator import OperatorCache as OC
            oc = OC()
            # op_id 是 char_id，需要反向查中文名
            data = oc.data
            for cname, info in data.items():
                if info.get("char_id") == op_id:
                    phases = info.get("phases", {})
                    for ep in sorted(phases.keys(), reverse=True):
                        lv_data = phases[ep]
                        if isinstance(lv_data, dict):
                            for lk in sorted(lv_data.keys(), reverse=True):
                                v = lv_data[lk]
                                if isinstance(v, dict) and "cost" in v:
                                    return float(v["cost"])
                    break
        except Exception:
            pass
        return 0.0

    def operators_alive(self, seconds: Optional[float] = None) -> List[OperatorPiece]:
        """某时刻在场的干员。seconds 为 None 时返回当前全部。"""
        if seconds is None:
            return list(self.operators.values())
        out = []
        for pc in self.operators.values():
            dep = self.track.get(int(getattr(pc, "uid", 0) or 0))
            if dep is not None and not dep.alive_at(float(seconds)):
                continue
            out.append(pc)
        return out

    def operators_at(self, seconds: Optional[float]) -> Dict[Coord, OperatorPiece]:
        """某时刻场上应显示的干员（按粗轴回放部署/撤退）。

        「当前场上」由 :attr:`operators` 给出；把游标拖回部署期时，
        ``operators`` 里的棋子已经按当前时刻撤退了，渲染只认它就会
        出现「人在粗轴上，地图上却消失」。所以渲染用本方法回放
        :class:`CoarseTrack`：部署了且未到撤退时刻的干员都算在场。
        """
        if seconds is None or not self.track.deployments:
            return dict(self.operators)
        t = float(seconds)
        out: Dict[Coord, OperatorPiece] = {}
        for dep in self.track.all():
            if not dep.alive_at(t):
                continue
            piece = self.operators.get((int(dep.row), int(dep.col)))
            if piece is None:
                # 已经撤退的干员：按粗轴重建一枚「影子」棋子，只用于
                # 渲染，不写回 self.operators。
                piece = OperatorPiece(dep.row, dep.col, dep.op_id, dep.name,
                                      dep.profession, dep.facing)
                piece.uid = dep.uid
                piece.is_ranged = bool(dep.is_ranged)
                piece.block_count = int(dep.block_count)
                piece.can_block_fly = bool(getattr(dep, "can_block_fly", False))
                piece.ground = dep.ground
                piece.cost = int(dep.cost)
            out[(int(dep.row), int(dep.col))] = piece
        return out

    def blockers(self, seconds: Optional[float] = None) -> List[OperatorPiece]:
        """真正能挡人的干员（近战位且阻挡数 > 0）。

        远程位干员（高台上的狙/术/奶）阻挡数是 0，不能挡地面敌人。
        """
        return [pc for pc in self.operators_alive(seconds)
                if not getattr(pc, "is_ranged", False)
                and int(getattr(pc, "block_count", 0) or 0) > 0]

    def set_block_fly(self, piece_or_uid, flag: bool) -> bool:
        """设置某枚干员能否阻挡飞行敌人。

        数据包里没有「飞行干员」这个概念，所以这个开关由用户点开，
        同时写回粗轴（``Deployment.can_block_fly``）与棋子
        （``OperatorPiece.can_block_fly``），保证「当前这一刻能不挡」
        和「导出的粗轴里能不能挡」永远一致。
        """
        dep = None
        piece = None
        if isinstance(piece_or_uid, Deployment):
            dep = piece_or_uid
        elif isinstance(piece_or_uid, OperatorPiece):
            piece = piece_or_uid
            dep = self.track.get(int(getattr(piece, "uid", 0) or 0))
        else:
            dep = self.track.get(int(piece_or_uid))
        if dep is not None:
            dep.can_block_fly = bool(flag)
            piece = piece or self.operators.get((dep.row, dep.col))
        if piece is not None:
            piece.can_block_fly = bool(flag)
        self._invalidate_plan()
        return dep is not None or piece is not None

    def blocked_by(self, row: float, col: float, enemy_flying: bool = False,
                   seconds: Optional[float] = None) -> Optional[OperatorPiece]:
        """这只敌人当前被谁挡住（没有则 None）。

        B1 §4: 使用 ``blocking.py`` 的平方距离几何模型（半径 0.707 格），
        替代原来的整数格取整判定。最大偏差从 0.5 格降到 0。
        """
        try:
            from . import blocking as BL
            for pc in self.blockers(seconds):
                if enemy_flying and not getattr(pc, "can_block_fly", False):
                    continue
                if BL.is_blocked((float(pc.row), float(pc.col)),
                                 (float(row), float(col)),
                                 flying=enemy_flying):
                    return pc
        except Exception:
            # 降级到整数格判定（兼容 blocking.py 加载失败）
            r = int(math.floor(float(row) + 0.5))
            c = int(math.floor(float(col) + 0.5))
            for pc in self.blockers(seconds):
                if (pc.row, pc.col) != (r, c):
                    continue
                if enemy_flying and not getattr(pc, "can_block_fly", False):
                    continue
                return pc
        return None

    def block_anchor(self, event, seconds: float) -> Optional[Tuple[float, float]]:
        """B1 §4: 被挡敌人的分散落点（bug C 修复）。

        用 ``blocking.apply_block_offset`` 把敌人推到干员半径 0.5 的圆边界上。
        返回 (row, col) 浮点坐标，失败时返回 None（调用方退回格中心）。
        """
        try:
            from . import blocking as BL
            plan = self._blocking_plan(seconds)
            rec = plan.get(self._event_key(event))
            if rec is None:
                return None
            cell, arr_wall, release_wall, arr_eff, blocked = rec
            if not blocked:
                return None
            op_pos = (float(cell[0]), float(cell[1]))
            ra = self.analysis_for(event)
            enemy_pos = ra.pose_at(arr_eff) if ra is not None else op_pos
            if enemy_pos is None:
                enemy_pos = op_pos
            result = BL.apply_block_offset(op_pos, enemy_pos)
            return result.final if result.moved else None
        except Exception:
            return None

    def blocked_count(self, piece: OperatorPiece,
                      seconds: Optional[float] = None) -> int:
        """某枚干员当前挡住了几只敌人（用于悬停显示）。

        要逐只敌人定位，代价比 ``blocked_by`` 高，只在悬停时调用。
        """
        if self.timeline is None:
            return 0
        if getattr(piece, "is_ranged", False):
            return 0
        if int(getattr(piece, "block_count", 0) or 0) <= 0:
            return 0
        t = float(seconds if seconds is not None else 0.0)
        n = 0
        for ev in self.live_events():
            pos = self.pose_at(ev, t)
            if pos is None:
                continue
            if (int(math.floor(pos[0] + 0.5)),
                    int(math.floor(pos[1] + 0.5))) == (piece.row, piece.col):
                n += 1
        return n

    def enemy_flags(self, event, seconds: float) -> dict:
        """一只敌人在某时刻的状态，给悬停提示用。

        返回 ``{"flying", "blocked_by", "blocked", "waiting",
        "wait_left", "slowed", "gone", "alive"}``。

        ``wait_left`` 是「还剩几秒罚站」：罚站是路线里
        ``WAIT_FOR_SECONDS`` 那类检查点，时长固定、不受减速影响，
        所以要单独算剩余量，不能拿总时长糊弄。

        飞行与否**必须**从 ``RouteAnalysis.flying`` 取，那个字段是
        ``routes.py`` 按 ``route.motionMode == "FLY"`` 算出来的。
        ``SpawnEvent`` 上没有 ``flying`` 字段，写 ``getattr(event,
        "flying", False)`` 会恒得 ``False``——飞行敌人于是被当成地面单位，
        地面干员照样能挡住它，而「开对空阻挡」永远没有效果。
        """
        ra = self.analysis_for(event)
        out = {"flying": bool(getattr(ra, "flying", False)),
               "blocked_by": None, "blocked": False, "waiting": False,
               "wait_left": 0.0, "slowed": 1.0, "gone": False,
               "alive": False}
        t = float(seconds)
        t_spawn = float(getattr(event, "time", 0.0))
        if t < t_spawn:
            return out
        out["alive"] = True
        if self.is_kicked(event):
            out["gone"] = True
            return out
        pos = self.pose_at(event, t)
        if pos is None:
            out["gone"] = True
            return out
        out["slowed"] = self.speed_at(event, t)
        pc = self.blocked_by(pos[0], pos[1], out["flying"], t)
        if pc is not None:
            out["blocked"] = True
            out["blocked_by"] = pc
        elapsed = float(t - t_spawn)
        # 出场罚站（【休憩】）优先于路线里的罚站：这段时间敌人还没开始
        # 沿路线走，`wait_span_at` 查不到它（角兽的路线连检查点都没有）。
        head = self.spawn_unmovable_of(event)
        if elapsed < head:
            out["waiting"] = True
            out["wait_left"] = max(0.0, head - elapsed)
            return out
        elapsed -= head
        elapsed = self._effective_elapsed(event, elapsed, t_spawn)
        if ra is not None and hasattr(ra, "wait_span_at"):
            try:
                span = ra.wait_span_at(elapsed)
                if span is not None:
                    out["waiting"] = True
                    out["wait_left"] = max(0.0, float(span))
            except Exception:
                pass
        return out

    # ------------------------------------------------------------ 技能回转

    def aura_boost_for(self, seconds: Optional[float] = None) -> float:
        """场上所有干员给「别人」的技力自然回复加成之和（点/秒）。

        用户要求「部分干员能给彼此交互 增加 sp 回复速度」。游戏里这类
        光环（白面鸮「技力光环」、陈「呵斥」、维娜 S3 被动）都是
        **同类取最高**，不相加；但不同来源（一个天赋 + 一个技能）是可以
        叠的。数据里分不出「同类」，所以按「取场上最大值」处理——
        这比相加更接近实机（相加会把白面鸮 + 陈算成 0.63，实机是 0.33
        与 0.30 取高 = 0.33）。

        ``seconds`` 给定时只算那一刻在场的干员。
        """
        best = 0.0
        for pc in self.operators_alive(seconds):
            dep = self.track.get(int(getattr(pc, "uid", 0) or 0))
            if dep is None:
                continue
            try:
                best = max(best, float(dep.sp_boost or 0.0))
            except (TypeError, ValueError):
                continue
        return best

    def _op_skill_sim(self, op_id: str) -> SkillSim:
        """返回指定干员的 ``SkillSim``（带真实 ``attack_interval``）。

        懒加载：首次查某 op_id 时从 ``operators.json`` 读
        ``attack_interval`` 并缓存。查不到时降级为全局默认
        ``self.skill_sim``（interval=1.0）。
        """
        if not op_id:
            return self.skill_sim
        sim = self._op_skill_sims.get(op_id)
        if sim is not None:
            return sim
        # 查缓存
        ai = self._op_attack_interval.get(op_id)
        if ai is None:
            ai = self._load_attack_interval(op_id)
            self._op_attack_interval[op_id] = ai
        sim = SkillSim(ai)
        self._op_skill_sims[op_id] = sim
        return sim

    def _load_attack_interval(self, op_id: str) -> float:
        """从 operators.json 加载指定干员的攻击间隔。"""
        try:
            import json, os as _os
            from ..core.paths import Paths as _P
            _paths = _P.default()
            with open(_paths.operators_cache, "r", encoding="utf-8") as _f:
                _data = json.load(_f)
            for _name, _rec in _data.get("operators", {}).items():
                if not isinstance(_rec, dict):
                    continue
                if _rec.get("char_id") == op_id or _rec.get("name") == op_id:
                    _p0 = (_rec.get("phases") or {}).get("0", {})
                    if not _p0:
                        continue
                    _lvl = sorted(
                        [k for k in _p0.keys() if str(k).isdigit()],
                        key=lambda x: int(x))[-1] if _p0 else None
                    if _lvl is None:
                        continue
                    _ai = float(_p0[_lvl].get("attack_interval", 1.0))
                    return max(0.05, _ai) if _ai > 0 else 1.0
        except Exception:
            pass
        return 1.0

    def skill_state(self, piece_or_uid, seconds: float) -> dict:
        """某枚干员在某时刻的技能回转状态。"""
        dep = None
        if isinstance(piece_or_uid, Deployment):
            dep = piece_or_uid
        else:
            uid = (int(getattr(piece_or_uid, "uid", 0) or 0)
                   if not isinstance(piece_or_uid, int) else int(piece_or_uid))
            dep = self.track.get(uid)
        if dep is None:
            return {"ready": False, "sp": 0.0, "need": 0.0, "active": False,
                    "next_in": None, "cycle_index": 0, "passive": True}
        if not dep.alive_at(float(seconds)):
            return {"ready": False, "sp": 0.0,
                    "need": float(dep.skill.sp_cost), "active": False,
                    "next_in": None, "cycle_index": 0, "passive": False,
                    "gone": True}
        # 别人给的光环加在自己头上：取「自身 boost」与「场上最高光环」
        # 的较大者，避免把同一枚干员的加成算两遍。
        boost = max(float(dep.sp_boost or 0.0),
                    self.aura_boost_for(float(seconds)))
        sim = self._op_skill_sim(dep.op_id)
        return sim.state_at(dep.skill, seconds, dep.deploy_time,
                            boost=boost)

    def use_skill(self, piece_or_uid, at_time: float) -> bool:
        """在粗轴上记一次「开技能」。

        只记录时刻，不改变任何战斗数值——用户明确要求「无需模拟干员
        技能情况 此时只需要模拟她的回转情况」。回转本身由
        :meth:`skill_state` 按 SP 规则算，这里记的时刻用于在轴上画标记。
        """
        dep = None
        if isinstance(piece_or_uid, Deployment):
            dep = piece_or_uid
        else:
            uid = (int(getattr(piece_or_uid, "uid", 0) or 0)
                   if not isinstance(piece_or_uid, int) else int(piece_or_uid))
            dep = self.track.get(uid)
        if dep is None:
            return False
        t = max(dep.deploy_time, float(at_time))
        dep.skill_uses.append(t)
        dep.skill_uses.sort()
        self._invalidate_plan()
        return True

    # ------------------------------------------------------------ 杂项

    def reset(self) -> None:
        """清空全部推演状态，回到初始。"""
        self.boxes.clear()
        self.operators.clear()
        self.kicked.clear()
        self.buffs.clear()
        self.track.clear()
        self.recompute()
        self._invalidate_plan()

    # ------------------------------------------------------------ 撤销 / 重做

    def push_history(self) -> None:
        """把当前可撤销状态压入历史栈。

        每次**会改变推演结果的**操作完成后调用（部署/撤退/箱子/减速/
        踢人/技能时刻/挡飞行/清空/导入）。调用前最好先把上一段 redo 作废。
        """
        try:
            snap = {
                "boxes": copy.deepcopy(self.boxes),
                "operators": copy.deepcopy(self.operators),
                "kicked": copy.deepcopy(self.kicked),
                "buffs": copy.deepcopy(self.buffs),
                "track": copy.deepcopy(self.track),
                "analyses": copy.deepcopy(self.analyses),
            }
        except Exception:
            # deepcopy 失败时不能把界面搞挂：这次就不入栈，撤销顶多少一步。
            return
        self._undo_stack.append(snap)
        self._redo_stack.clear()
        # 限制栈深，避免长会话里无界增长（界面行为足够，不是持久化）。
        if len(self._undo_stack) > 80:
            self._undo_stack = self._undo_stack[-80:]

    def _restore_history(self, snap: dict) -> None:
        self.boxes = snap["boxes"]
        self.operators = snap["operators"]
        self.kicked = snap["kicked"]
        self.buffs = snap["buffs"]
        self.track = snap["track"]
        self.analyses = snap["analyses"]
        self._invalidate_plan()

    def undo(self) -> bool:
        """撤到上一步。返回是否真的撤了。"""
        if not self._undo_stack:
            return False
        try:
            self._redo_stack.append(copy.deepcopy({
                "boxes": self.boxes,
                "operators": self.operators,
                "kicked": self.kicked,
                "buffs": self.buffs,
                "track": self.track,
                "analyses": self.analyses,
            }))
        except Exception:
            return False
        self._restore_history(self._undo_stack.pop())
        return True

    def redo(self) -> bool:
        """重做刚被撤销的一步。返回是否真的重做了。"""
        if not self._redo_stack:
            return False
        try:
            self._undo_stack.append(copy.deepcopy({
                "boxes": self.boxes,
                "operators": self.operators,
                "kicked": self.kicked,
                "buffs": self.buffs,
                "track": self.track,
                "analyses": self.analyses,
            }))
        except Exception:
            return False
        self._restore_history(self._redo_stack.pop())
        return True

    # ------------------------------------------------------------ 沙盘结束机制（批次 A1）

    # 敌人状态常量
    ST_PENDING = "PENDING"
    ST_MOVING = "MOVING"
    ST_BLOCKED = "BLOCKED"
    ST_WAITING = "WAITING"
    ST_SLOWED = "SLOWED"
    ST_LEAKED = "LEAKED"
    ST_VANISHED = "VANISHED"
    ST_KILLED = "KILLED"
    ST_STUCK = "STUCK"

    # 结束判据常量
    VERDICT_RUNNING = "RUNNING"
    VERDICT_ALL_RESOLVED = "ALL_RESOLVED"
    VERDICT_DEADLOCK = "DEADLOCK"
    VERDICT_TIMEOUT = "TIMEOUT"

    def _enemy_state(self, event, seconds: float) -> str:
        """返回单只敌人在 seconds 时刻的状态（八态之一）。"""
        t = float(seconds)
        t_spawn = float(getattr(event, "time", 0.0))

        # PENDING：还没出场
        if t < t_spawn:
            return self.ST_PENDING

        # KILLED：被踢掉
        if self.is_kicked(event):
            return self.ST_KILLED

        ra = self.analysis_for(event)
        if ra is None or not getattr(ra, "reachable", True):
            # 路线不可达 → 当成消失
            return self.ST_VANISHED

        # 检查是否已到达终点（LEAKED 或 VANISHED）
        pos = self.pose_at(event, t)
        if pos is None:
            # pose_at 返回 None 表示已离开路线
            if getattr(ra, "vanish", False):
                return self.ST_VANISHED
            # 非 vanish 路线到达终点 = 漏了
            return self.ST_LEAKED

        # 检查阻挡状态
        plan = {}
        try:
            plan = self._blocking_plan(t)
        except Exception:
            pass
        rec = plan.get(self._event_key(event))
        if rec is not None:
            cell, arr_wall, release_wall, arr_eff, blocked = rec
            if blocked:
                if float(release_wall) == math.inf:
                    # 永久阻挡 → STUCK
                    return self.ST_STUCK
                # 临时阻挡（干员会撤退）
                if t < float(release_wall) - 1e-9:
                    return self.ST_BLOCKED
                # 已过释放时间，继续走（下面会判断 MOVING/SLOWED）

        # 检查罚站（WAITING）——必须用状态判断，不用位移
        elapsed = float(t - t_spawn)
        head = self.spawn_unmovable_of(event)
        if elapsed < head:
            return self.ST_WAITING
        elapsed -= head
        route_elapsed = self._effective_elapsed(event, elapsed, t_spawn)
        if ra is not None and hasattr(ra, "wait_span_at"):
            try:
                span = ra.wait_span_at(route_elapsed)
                if span is not None and float(span) > 0:
                    return self.ST_WAITING
            except Exception:
                pass

        # 检查减速（SLOWED）
        speed = self.speed_at(event, t)
        if speed > 0 and speed < 1.0:
            return self.ST_SLOWED

        # 正常移动
        return self.ST_MOVING

    def state_at(self, seconds: float) -> dict:
        """返回沙盘在指定时刻的完整状态快照。

        返回 ``{time, enemies[], counts{}, verdict}``：
        * ``enemies[]`` 每项含 key / enemy_id / row / col / state /
          blocked_by / blocked_at / route_index / progress / eta_goal。
        * ``counts`` 含 moving/blocked/waiting/leaked/vanished/killed/stuck/pending。
        * ``verdict`` ∈ RUNNING | ALL_RESOLVED | DEADLOCK | TIMEOUT。
        """
        t = float(seconds)
        enemies_info = []
        counts = {self.ST_PENDING: 0, self.ST_MOVING: 0, self.ST_BLOCKED: 0,
                  self.ST_WAITING: 0, self.ST_SLOWED: 0, self.ST_LEAKED: 0,
                  self.ST_VANISHED: 0, self.ST_KILLED: 0, self.ST_STUCK: 0}

        for ev in self.events():
            state = self._enemy_state(ev, t)
            counts[state] = counts.get(state, 0) + 1

            entry = {
                "key": self._event_key(ev),
                "enemy_id": getattr(ev, "enemy_id", ""),
                "state": state,
                "route_index": int(getattr(ev, "route_index", -1)),
            }
            # 位置信息（非终态才有意义）
            if state not in (self.ST_LEAKED, self.ST_VANISHED, self.ST_KILLED):
                pos = self.pose_at(ev, t)
                if pos is not None:
                    entry["row"] = round(pos[0], 2)
                    entry["col"] = round(pos[1], 2)

            # 阻挡详情
            if state == self.ST_BLOCKED or state == self.ST_STUCK:
                try:
                    plan = self._blocking_plan(t)
                    rec = plan.get(self._event_key(ev))
                    if rec is not None:
                        cell, arr_wall, release_wall, arr_eff, blocked = rec
                        entry["blocked_by"] = {
                            "cell": [int(cell[0]), int(cell[1])],
                            "blocked_at": round(float(arr_wall), 2),
                            "release_at": None if release_wall == math.inf
                                           else round(float(release_wall), 2),
                        }
                        dep_uid = None
                        for d in self.track.all():
                            if (int(d.row), int(d.col)) == (int(cell[0]),
                                                              int(cell[1])):
                                dep_uid = d.uid
                                break
                        if dep_uid is not None:
                            entry["blocked_by"]["uid"] = dep_uid
                except Exception:
                    pass

            # 预计到达时间
            if state in (self.ST_MOVING, self.ST_SLOWED, self.ST_BLOCKED,
                         self.ST_WAITING, self.ST_PENDING):
                entry["eta_goal"] = self._eta_for_enemy(ev, t)

            enemies_info.append(entry)

        verdict = self._verdict_at(t, counts)
        return {
            "time": t,
            "enemies": enemies_info,
            "counts": counts,
            "verdict": verdict,
        }

    def _eta_for_enemy(self, event, current_t: float) -> Optional[float]:
        """估算敌人从当前时刻到到达蓝门还需多少秒。无法到达返回 None。"""
        ra = self.analysis_for(event)
        if ra is None or not getattr(ra, "reachable", True):
            return None
        if getattr(ra, "vanish", False):
            return None  # vanish 路线不到蓝门

        t_spawn = float(getattr(event, "time", 0.0))
        # 如果已被永久挡住
        state = self._enemy_state(event, current_t)
        if state == self.ST_STUCK:
            return None

        # 当前位置对应的路线进度
        pos = self.pose_at(event, current_t)
        if pos is None:
            # 已经到了（leaked/vanished）
            return 0.0

        # 从当前点算剩余路程需要的墙钟时间
        # 简化：用 arrival_time 减去已消耗的墙钟时间
        total_arrival = self.arrival_time(event)
        if total_arrival is None:
            return None
        elapsed = max(0.0, current_t - t_spawn)
        remaining = max(0.0, total_arrival - elapsed)
        # 如果被临时阻挡，加上等待释放的时间
        try:
            plan = self._blocking_plan(current_t)
            rec = plan.get(self._event_key(event))
            if rec is not None:
                _, arr_wall, release_wall, _, blocked = rec
                if blocked and release_wall != math.inf:
                    wait_more = max(0.0, float(release_wall) - current_t)
                    remaining += wait_more
        except Exception:
            pass
        return round(remaining, 2) if remaining < 9999 else None

    def _verdict_at(self, t: float, counts: dict) -> str:
        """根据当前状态计数判定沙盘结束类型。"""
        n_total = sum(counts.values())
        if n_total == 0:
            return self.VERDICT_ALL_RESOLVED

        terminal = {self.ST_LEAKED, self.ST_VANISHED, self.ST_KILLED}
        stagnant = {self.ST_BLOCKED, self.ST_WAITING, self.ST_STUCK}
        active = {self.ST_MOVING, self.ST_SLOWED}

        # 判据 A：全部解决
        if all(counts.get(s, 0) == 0 for s in active | {self.ST_PENDING} |
               stagnant):
            return self.VERDICT_ALL_RESOLVED

        # 判据 B：全部停滞（至少一只在停滞态，无活跃/待出场）
        has_stagnant = any(counts.get(s, 0) > 0 for s in stagnant)
        no_active = all(counts.get(s, 0) == 0 for s in active | {self.ST_PENDING})
        if has_stagnant and no_active:
            return self.VERDICT_DEADLOCK

        # 判据 C：安全上限
        # 找无阻挡总时长
        max_arrival = 0.0
        for ev in self.events():
            at = self.arrival_time(ev)
            if at is not None:
                max_arrival = max(max_arrival, float(at))
        safe_limit = max(600.0, 3.0 * max(300.0, max_arrival))
        if t > safe_limit:
            return self.VERDICT_TIMEOUT

        return self.VERDICT_RUNNING

    def solve_end(self) -> dict:
        """计算沙盘收尾时刻与最终判据。

        返回 ``{end_time, verdict, leaked, vanished, killed,
        stuck[], life_lost, warnings[]}``。多次调用幂等。

        算法：
        * 对每只敌人算「尘埃落定」时刻；
        * 取最大值作为 end_time；
        * 在 end_time 处做最终状态判定。
        """
        arrivals = []  # (end_time_for_this_enemy, event, reason)
        stuck_list = []
        leaked_list = []

        for ev in self.events():
            if self.is_kicked(ev):
                arrivals.append((float(getattr(ev, "time", 0.0)), ev,
                                 "killed"))
                continue

            ra = self.analysis_for(ev)
            t_spawn = float(getattr(ev, "time", 0.0))

            if ra is None or not getattr(ra, "reachable", True):
                arrivals.append((t_spawn, ev, "unreachable"))
                continue

            # 检查阻挡情况
            final_t = t_spawn
            reason = "normal"
            is_stuck = False

            # 遍历所有可能的阻挡格，找到最早的实际阻挡
            try:
                # 用一个足够晚的时刻来查阻挡计划
                far_t = t_spawn + 10000.0
                plan = self._blocking_plan(far_t)
                rec = plan.get(self._event_key(ev))
                if rec is not None:
                    cell, arr_wall, release_wall, arr_eff, blocked = rec
                    if blocked:
                        if float(release_wall) == math.inf:
                            # 永久阻挡 → STUCK
                            final_t = float(arr_wall)
                            reason = "stuck"
                            is_stuck = True
                            stuck_entry = {
                                "enemy_id": getattr(ev, "enemy_id", ""),
                                "key": self._event_key(ev),
                                "route_index": int(getattr(ev, "route_index",
                                                           -1)),
                                "cell": [int(cell[0]), int(cell[1])],
                                "blocked_at": round(float(arr_wall), 2),
                            }
                            # 找到阻挡者
                            for d in self.track.all():
                                if ((int(d.row), int(d.col)) ==
                                        (int(cell[0]), int(cell[1]))):
                                    stuck_entry["blocker_uid"] = d.uid
                                    stuck_entry["blocker_name"] = d.name
                                    break
                            stuck_list.append(stuck_entry)
                        else:
                            # 临时阻挡：从释放时刻继续走完剩余路程
                            release = float(release_wall)
                            # 剩余路程 = 总路程 - 到达阻挡格时的进度
                            remaining_route = (float(getattr(ra, "total_time", 0.0))
                                               - float(arr_eff))
                            if remaining_route <= 0:
                                final_t = release
                            else:
                                # 从释放点走完剩余需要多少墙钟秒
                                wall_remaining = self._wall_elapsed_for_route(
                                    ev, ra, remaining_route)
                                final_t = release + wall_remaining
                            reason = "blocked_then_released"
                    else:
                        # 不被挡 → 正常走到终点
                        at = self.arrival_time(ev)
                        final_t = t_spawn + (float(at) if at else 0.0)
                        reason = "normal"
                else:
                    # 无阻挡记录 → 正常走到终点
                    at = self.arrival_time(ev)
                    final_t = t_spawn + (float(at) if at else 0.0)
                    reason = "normal"
            except Exception:
                at = self.arrival_time(ev)
                final_t = t_spawn + (float(at) if at else 0.0)
                reason = "normal"

            # vanish 路线特殊处理
            if getattr(ra, "vanish", False) and not is_stuck:
                at = self.arrival_time(ev)
                final_t = t_spawn + (float(at) if at else 0.0)
                reason = "vanish"

            arrivals.append((final_t, ev, reason))

        if not arrivals:
            return {"end_time": 60.0, "verdict": self.VERDICT_ALL_RESOLVED,
                    "leaked": [], "vanished": [], "killed": [],
                    "stuck": [], "life_lost": 0, "warnings": []}

        end_time = max(a[0] for a in arrivals)
        end_time = max(end_time, 60.0)  # 至少 60 秒

        # 在 end_time 做最终状态判定（加微小 epsilon 避免边界处
        # pose_at 仍返回非 None 导致敌人被误判为 MOVING）
        final = self.state_at(end_time + 0.05)
        leaked = [e for e in final["enemies"]
                  if e["state"] == self.ST_LEAKED]
        vanished = [e for e in final["enemies"]
                    if e["state"] == self.ST_VANISHED]
        killed = [e for e in final["enemies"]
                  if e["state"] == self.ST_KILLED]

        # B2 §5: 生命值扣减——按敌人真实 lifePointReduce 计算
        # 0 表示不计生命的单位（召唤物、无害单位），不能漏算成 1
        life_lost = 0
        for e in leaked:
            reduce_val = int(getattr(e.get("event", {}), "lifePointReduce", 1) or 1)
            if reduce_val > 0:
                life_lost += reduce_val

        warnings = []
        if final["verdict"] == self.VERDICT_DEADLOCK:
            warnings.append("死锁：%d 只敌人被永久阻挡" %
                             final["counts"].get(self.ST_STUCK, 0))
        if len(leaked) > 0:
            warnings.append("%d 只敌人漏入蓝门" % len(leaked))

        return {
            "end_time": round(end_time, 2),
            "verdict": final["verdict"],
            "leaked": leaked,
            "vanished": vanished,
            "killed": killed,
            "stuck": stuck_list,
            "life_lost": life_lost,
            "warnings": warnings,
        }

    def summary(self) -> str:
        """一行状态描述，给状态栏用。"""
        n_ev = len(self.events())
        n_live = len(self.live_events())
        parts = ["敌人 %d/%d" % (n_live, n_ev)]
        if self.operators:
            parts.append("干员 %d" % len(self.operators))
        if self.boxes:
            parts.append("箱子 %d" % len(self.boxes))
        if self.buffs:
            parts.append("减速 %d" % len(self.buffs))
        if self.track.deployments:
            n_ret = sum(1 for d in self.track.all()
                        if d.retreat_time is not None)
            parts.append("粗轴 %d 部署/撤退 %d"
                         % (len(self.track.deployments), n_ret))
        return " · ".join(parts)
