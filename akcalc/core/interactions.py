"""敌人与场景的交互：移速增益、光环、地形影响。

设计取舍
--------
游戏客户端里敌人之间的交互非常少：绝大多数「移速提升」都写在敌人
自己的 ``talentBlackboard`` / ``skills.blackboard`` 里，作用于自身
（例如 爱国者 狂暴后 ``immo_trigger[rage].move_speed = 0.1`` 即自身
移速 +10%）。真正作用于**其他敌人**的只有 ``Aura.*`` 系列键。

本模块的做法：

1. 从官方 ``enemy_database`` 抽出每个敌人的「自身移速修正」，
   归成可读的条目，用于修正动画里的行进时间；
2. 识别 ``Aura.*`` 键，作为「对场上其他敌人的影响」单独列出；
3. 场景影响（地形、路线上的等待节点）由 ``RouteAnalysis`` 已算好，
   这里只负责汇总成给人看的说明。

所有数值都来自官方数据，不做臆测。
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List, Optional

#: 光环键前缀：这类键才是真正影响「其他敌人」的
_AURA_RE = re.compile(r"^Aura\.", re.I)
#: 真正的移速值键。注意要排除 ``speed_up_duration`` 这类时长键，
#: 否则会把「加速持续 1 秒」误读成「移速 +100%」。
_SPEED_KEY_RE = re.compile(r"move_?speed(?:_add)?$|^speed$", re.I)


@dataclass
class SpeedModifier:
    """一条移速修正。"""

    source: str            # 来源，如 天赋 / 技能 XXX
    key: str               # 原始键名
    value: float           # 原始数值
    kind: str              # "self" 自身 / "aura" 光环（影响他人）
    note: str = ""         # 备注

    @property
    def percent(self) -> float:
        """折算成百分比增量（游戏里 1.0 表示 +100%）。"""
        return self.value * 100.0

    def label(self) -> str:
        if self.kind == "aura":
            return "光环：场上敌人移速 %+.0f%%" % self.percent
        return "自身移速 %+.0f%%" % self.percent


@dataclass
class EnemyInteraction:
    """一个敌人的交互汇总。"""

    enemy_id: str
    name: str = ""
    speed_mods: List[SpeedModifier] = field(default_factory=list)
    auras: List[SpeedModifier] = field(default_factory=list)
    skills: List[str] = field(default_factory=list)

    @property
    def total_self_percent(self) -> float:
        """自身移速修正。

        同一敌人常有多个互斥状态的键（如 ``M0SpeedUp`` / ``M1SpeedUp``
        是形态 0 / 形态 1 各自的加成），实际只会生效一个，因此取**绝对值
        最大的一条**而不是求和，避免出现「+600%」这种明显失真的数字。
        """
        if not self.speed_mods:
            return 0.0
        return max((m.percent for m in self.speed_mods), key=abs)

    @property
    def total_aura_percent(self) -> float:
        if not self.auras:
            return 0.0
        return max((m.percent for m in self.auras), key=abs)

    def has_any(self) -> bool:
        return bool(self.speed_mods or self.auras)

    def summary(self) -> str:
        parts = []
        if self.speed_mods:
            parts.append("移速 %+.0f%%" % self.total_self_percent)
        for a in self.auras:
            parts.append(a.label())
        return "　".join(parts) if parts else "无移速相关影响"

    def detail_lines(self) -> List[str]:
        """给人看的明细行。"""
        out = []
        for m in self.speed_mods:
            out.append("%s　%s　(%s)" % (m.label(), m.source, m.key))
        for m in self.auras:
            out.append("%s　%s　(%s)" % (m.label(), m.source, m.key))
        return out


def _bb_value(bb: dict) -> Optional[float]:
    v = bb.get("value")
    if v is None:
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _match_speed_key(key: str) -> bool:
    """判断键名是否是移速值本身。

    接受 ``Aura.move_speed`` / ``speedUp.move_speed`` /
    ``immo_trigger[rage].move_speed`` / ``move_speed_add``；
    拒绝 ``move_speed_duration`` / ``speed_up_duration`` 等时长键。
    """
    if not key:
        return False
    tail = key.rsplit(".", 1)[-1]
    return bool(_SPEED_KEY_RE.match(tail))


def extract(entry: dict, enemy_id: str = "") -> EnemyInteraction:
    """从一条 enemy_database 记录抽出交互信息。"""
    ed = (entry or {}).get("enemyData") or {}
    name_obj = ed.get("name") or {}
    name = name_obj.get("m_value") if isinstance(name_obj, dict) else str(name_obj or "")
    out = EnemyInteraction(enemy_id=enemy_id, name=name or "")

    for bb in ed.get("talentBlackboard") or []:
        key = str(bb.get("key") or "")
        if not _match_speed_key(key):
            continue
        val = _bb_value(bb)
        if val is None:
            continue
        kind = "aura" if _AURA_RE.match(key) else "self"
        mod = SpeedModifier(source="天赋", key=key, value=val, kind=kind)
        (out.auras if kind == "aura" else out.speed_mods).append(mod)

    for sk in ed.get("skills") or []:
        prefab = str(sk.get("prefabKey") or "")
        hit = False
        for bb in sk.get("blackboard") or []:
            key = str(bb.get("key") or "")
            if not _match_speed_key(key):
                continue
            val = _bb_value(bb)
            if val is None:
                continue
            kind = "aura" if _AURA_RE.match(key) else "self"
            mod = SpeedModifier(source="技能 %s" % prefab, key=key,
                                value=val, kind=kind, note=prefab)
            (out.auras if kind == "aura" else out.speed_mods).append(mod)
            hit = True
        if prefab and hit:
            out.skills.append(prefab)

    return out


def for_enemy(lib, enemy_id: str, level: int = 0) -> Optional[EnemyInteraction]:
    """从敌人库取某敌人的交互信息。"""
    if lib is None or not getattr(lib, "loaded", False):
        return None
    entries = None
    raw = getattr(lib, "raw", None)
    if isinstance(raw, dict):
        entries = (raw.get("by_id") or {}).get(enemy_id)
    if not entries:
        getter = getattr(lib, "get", None)
        if callable(getter):
            try:
                entries = getter(enemy_id, level)
            except TypeError:
                entries = None
    if not entries:
        return None
    if not isinstance(entries, list):
        entries = [entries]
    best = None
    best_lv = 0
    for e in entries:
        if not isinstance(e, dict):
            continue
        try:
            lv = int(e.get("level", 0) or 0)
        except (TypeError, ValueError):
            lv = 0
        if best is None or abs(lv - level) < abs(best_lv - level):
            best, best_lv = e, lv
    if best is None:
        return None
    return extract(best, enemy_id)


def speed_factor(mods: List[SpeedModifier]) -> float:
    """把自身移速修正折算成行进速度倍率。

    多个键是互斥状态，取绝对值最大的一条。
    """
    if not mods:
        return 1.0
    best = max((m.value for m in mods), key=abs)
    return max(0.1, 1.0 + best)


def describe_map_effects(game_map, analyses) -> List[str]:
    """汇总场景给敌人的影响（以已有分析结果为准，不臆测）。"""
    lines = []
    if not game_map:
        return lines
    waits = 0.0
    teleports = 0
    unreachable = 0
    for a in analyses or []:
        waits += getattr(a, "wait_time", 0.0)
        teleports += getattr(a, "teleports", 0)
        if not getattr(a, "reachable", True):
            unreachable += 1
    if waits > 0:
        lines.append("路线停驻：合计 %.0f 秒（CHECKPOINT 的 wait 时间）" % waits)
    if teleports:
        lines.append("瞬移节点：%d 处（APPEAR_AT_POS，不计行进路程）" % teleports)
    if unreachable:
        lines.append("不可行路线：%d 条（终点被地形阻断）" % unreachable)
    return lines