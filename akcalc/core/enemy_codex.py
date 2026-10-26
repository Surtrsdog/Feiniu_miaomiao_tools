"""怪物图鉴数据：把敌人库里的松散 JSON 整理成图鉴要显示的结构。

敌人库里每个 entry 的 enemyData 含：
    name / description / attributes / skills / talentBlackboard / motion
attributes 里既有基础面板，也有 20 多个抗性开关与数值。图鉴要展示
「特性、技能、各种抗性」，所以这里做一层归一化。
"""
from __future__ import annotations

from typing import Dict, List, Optional, Tuple

#: (属性键, 中文名, 单位后缀, 是否百分比)
BASE_STATS = (
    ("maxHp", "生命值", "", False),
    ("atk", "攻击力", "", False),
    ("def", "防御力", "", False),
    ("magicResistance", "法术抗性", "", False),
    ("moveSpeed", "移动速度", "", False),
    ("baseAttackTime", "攻击间隔", " 秒", False),
    ("attackSpeed", "攻击速度", "", False),
    ("massLevel", "重量", "", False),
    ("blockCnt", "阻挡数", "", False),
    ("rangeRadius", "攻击半径", "", False),
)

#: 元素 / 损伤类抗性
ELEM_RESISTS = (
    ("epResistance", "元素抗性"),
    ("epDamageResistance", "元素伤害减免"),
    ("damageHitratePhysical", "物理闪避"),
    ("damageHitrateMagical", "法术闪避"),
)

#: 免疫开关
IMMUNES = (
    ("stunImmune", "眩晕"),
    ("silenceImmune", "沉默"),
    ("sleepImmune", "睡眠"),
    ("frozenImmune", "冻结"),
    ("levitateImmune", "浮空"),
    ("disarmedCombatImmune", "缴械"),
    ("fearedImmune", "恐惧"),
    ("palsyImmune", "麻痹"),
    ("attractImmune", "牵引"),
    ("teleportImmune", "传送"),
    ("groundBoundImmune", "束缚"),
)

#: 状态类数值抗性
STATE_RESISTS = (
    ("hpRecoveryPerSec", "生命回复/秒"),
    ("spRecoveryPerSec", "技力回复/秒"),
    ("epBreakRecoverSpeed", "元素回复速度"),
    ("baseForceLevel", "推力等级"),
    ("tauntLevel", "嘲讽等级"),
)

_MOTION_CN = {"WALK": "地面", "FLY": "飞行"}


def _mv(obj, default=0.0):
    if isinstance(obj, dict):
        if not obj.get("m_defined", True):
            return default
        v = obj.get("m_value")
        return default if v is None else v
    return obj if obj is not None else default


def _num(v) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


def _fmt(v: float) -> str:
    if abs(v - round(v)) < 1e-6:
        return "%d" % int(round(v))
    return "%.2f" % v


def _clean(text: str) -> str:
    """去掉客户端富文本标记：<@eb.key>无害</> -> 无害。"""
    if not text:
        return ""
    out, i, n = [], 0, len(text)
    while i < n:
        ch = text[i]
        if ch == "<":
            j = text.find(">", i)
            if j > i:
                i = j + 1
                continue
        out.append(ch)
        i += 1
    return "".join(out).replace("\\n", " ").strip()


def bb_to_text(blackboard) -> str:
    """把技能 blackboard 拟人化：move_speed 1.5 -> 移动速度 ×1.5。"""
    if not blackboard:
        return ""
    names = {
        "move_speed": "移动速度", "atk": "攻击力", "def": "防御力",
        "max_hp": "生命值", "attack_speed": "攻击速度",
        "block_free_time": "不可阻挡时间", "duration": "持续时间",
        "interval": "间隔", "range_radius": "范围半径",
        "magic_resistance": "法术抗性", "damage_scale": "伤害倍率",
        "stun": "眩晕时间", "bind": "束缚时间", "silence": "沉默时间",
        "cost": "费用", "hp_ratio": "生命比例阈值",
        "duration": "持续", "attack@damage_resistance": "攻击减伤",
        "damage_resistance": "受到伤害减免", "Aura.duration": "光环持续",
        "Aura.attack_speed": "光环攻速", "Aura.move_speed": "光环移速",
        "Aura.damage_resistance": "光环减伤",
        "Ally.def": "友军防御", "Ally.max_hp": "友军生命",
        "Aura.rage": "光环怒气", "ep_damage_resistance": "元素减伤",
    }
    parts = []
    for item in blackboard:
        if not isinstance(item, dict):
            continue
        key = item.get("key") or ""
        val = item.get("value")
        vs = item.get("valueStr")
        label = names.get(key)
        if label is None:
            head, _, tail = key.rpartition(".")
            pref = {"Aura": "光环·", "Ally": "友军·", "Enemy": "敌方·"}.get(head, "")
            label = pref + names.get(tail, tail or key)
        if vs:
            parts.append("%s %s" % (label, vs))
        elif val is not None:
            parts.append("%s %s" % (label, _fmt(_num(val))))
    return "、".join(parts)


def codex_entry(entries: List[dict], level: int = 0,
                enemy_id: str = "") -> Optional[dict]:
    """把同一 enemy_id 的多档 entry 整理成图鉴条目。

    entries 是敌人库里 by_id[eid] 的列表（每项 {"level","enemyData"}）。
    取最接近 level 的那一档，并把抗性 / 免疫 / 技能全部摊平。
    """
    if not entries:
        return None
    best = min(entries, key=lambda e: abs(int(e.get("level", 0) or 0) - level))
    ed = best.get("enemyData") or {}
    attrs = ed.get("attributes") or {}

    def a(key: str) -> float:
        return _num(_mv(attrs.get(key), 0.0))

    name = _clean(str(_mv(ed.get("name"), "") or ""))
    desc = _clean(str(_mv(ed.get("description"), "") or ""))

    stats: List[Tuple[str, str]] = []
    for key, label, unit, _pct in BASE_STATS:
        v = a(key)
        if key == "rangeRadius" and v <= 0:
            stats.append((label, "—"))
            continue
        stats.append((label, _fmt(v) + unit))

    resists: List[Tuple[str, str]] = []
    for key, label in ELEM_RESISTS:
        v = a(key)
        if abs(v - round(v)) > 1e-6 or v > 1:
            resists.append((label, "%.1f%%" % (v * 100 if v <= 1 else v)))
        else:
            resists.append((label, _fmt(v) + ("%" if key.startswith("damage") else "")))

    immunes = [cn for key, cn in IMMUNES if bool(_mv(attrs.get(key), False))]

    # 数值型状态抗性只显示非零的，避免一屏 0
    extra: List[Tuple[str, str]] = []
    for key, label in STATE_RESISTS:
        v = a(key)
        if abs(v) > 1e-9:
            extra.append((label.strip(), _fmt(v)))

    skills = []
    for sk in (ed.get("skills") or []):
        if not isinstance(sk, dict):
            continue
        key = sk.get("prefabKey") or sk.get("key") or "技能"
        cd = _num(sk.get("cooldown"))
        init = _num(sk.get("initCooldown"))
        bb = bb_to_text(sk.get("blackboard"))
        line = key
        if cd:
            line += "（冷却 %s 秒" % _fmt(cd)
            if init:
                line += "，初始 %s 秒" % _fmt(init)
            line += "）"
        if bb:
            line += "：" + bb
        skills.append(line)

    talent_bb = bb_to_text(ed.get("talentBlackboard"))
    motion = str(_mv(ed.get("motion"), "WALK")).upper()
    tags = _mv(ed.get("enemyTags"), []) or []

    return {
        "enemy_id": enemy_id,
        "level": int(best.get("level", 0) or 0),
        "name": name,
        "desc": desc,
        "stats": stats,
        "resists": resists,
        "immunes": immunes,
        "extra": extra,
        "skills": skills,
        "talent": talent_bb,
        "motion": _MOTION_CN.get(motion, motion),
        "tags": list(tags),
        "life_cost": int(_num(_mv(ed.get("lifePointReduce"), 1))),
    }