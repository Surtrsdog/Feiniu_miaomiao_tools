# -*- coding: utf-8 -*-
"""干员天赋被动解析：把「无视法术抗性 / 无视防御」这类穿透被动量化。

为什么要单独一层
----------------
天赋文本目前只是 ``Operator.talents``（``List[(名称, 效果)]``），图鉴里当
纯文本展示，从不参与伤害计算。但史尔特尔的「熔火：无视攻击目标 26 法术
抗性」、Pith 的「见我所见：攻击无视目标 20 法术抗性」这些是**货真价实的
法术穿透**，不算进去的话法伤干员对高法抗敌人的 DPS 会明显偏低。

这里只做「尽力而为」的量化，且**宁缺毋滥**：只认写得清清楚楚、无条件、
且属于干员自身攻击的「无视 X 点 / X% 法术抗性（或防御力）」。概率触发、
条件叠加、给队友的群体增益一律跳过，避免把不可靠的数字塞进公式。
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, List, Sequence, Tuple

#: 条件 / 概率 / 团队增益类天赋：不可靠，直接跳过。
_CONDITIONAL_HINTS = ("概率", "几率", "每", "叠加", "层", "成员", "友方",
                      "周围", "范围内", "阻挡时", "重量", "空中", "深海")

#: 「无视 X 法术抗性」—— 无百分号 => 固定穿透（点）。
_RE_RES_FLAT = re.compile(
    r"无视[^，。；;、]{0,12}?(\d+(?:\.\d+)?)\s*(?:点|的)?\s*(?:法术抗性|法抗)")
#: 「无视 X% 法术抗性」—— 带百分号 => 百分比穿透。
_RE_RES_PCT = re.compile(
    r"无视[^，。；;、]{0,20}?(\d+(?:\.\d+)?)\s*%\s*(?:的)?\s*(?:法术抗性|法抗)")
#: 「无视 X 防御力」—— 固定物穿（「无视目标 210 的防御力」）。
_RE_DEF_FLAT = re.compile(
    r"无视[^，。；;、]{0,12}?(\d+(?:\.\d+)?)\s*(?:点|的)?\s*防御力")
#: 「无视 X% 防御力」—— 百分比物穿（「无视其 50% 防御力」）。
_RE_DEF_PCT = re.compile(
    r"无视[^，。；;、]{0,20}?(\d+(?:\.\d+)?)\s*%\s*(?:的)?\s*防御力")
#: 「无视其防御力的 X%」—— 倒装写法（早露）。
_RE_DEF_PCT2 = re.compile(
    r"防御力\s*的\s*(\d+(?:\.\d+)?)\s*%")


@dataclass
class TalentPassives:
    """从天赋文本里可靠量化出的穿透被动。"""

    res_pen_flat: float = 0.0     # 无视 X 点法术抗性
    res_pen_percent: float = 0.0  # 无视 X% 法术抗性（0~1）
    def_pen_flat: float = 0.0     # 无视 X 点防御力
    def_pen_percent: float = 0.0  # 无视 X% 防御力（0~1）
    notes: List[str] = field(default_factory=list)


def _num(m) -> float:
    try:
        return float(m.group(1))
    except (ValueError, IndexError):
        return 0.0


def _reliable(effect: str) -> bool:
    """只保留无条件、干员自身攻击的天赋。"""
    return not any(h in (effect or "") for h in _CONDITIONAL_HINTS)


def _parse_one(effect: str) -> TalentPassives:
    p = TalentPassives()
    if not effect or not _reliable(effect):
        return p
    mp = _RE_RES_PCT.search(effect)
    if mp and _num(mp) > 0:
        p.res_pen_percent = min(1.0, _num(mp) / 100.0)
        p.notes.append("无视 %.0f%% 法术抗性" % (_num(mp)))
    mf = _RE_RES_FLAT.search(effect)
    if mf and _num(mf) > 0:
        p.res_pen_flat = _num(mf)
        p.notes.append("无视 %.0f 点法术抗性" % (_num(mf)))
    dp = _RE_DEF_PCT.search(effect)
    if dp and _num(dp) > 0:
        p.def_pen_percent = min(1.0, _num(dp) / 100.0)
        p.notes.append("无视 %.0f%% 防御力" % (_num(dp)))
    else:
        dp2 = _RE_DEF_PCT2.search(effect)
        if dp2 and _num(dp2) > 0:
            p.def_pen_percent = min(1.0, _num(dp2) / 100.0)
            p.notes.append("无视 %.0f%% 防御力" % (_num(dp2)))
    df = _RE_DEF_FLAT.search(effect)
    if df and _num(df) > 0:
        p.def_pen_flat = _num(df)
        p.notes.append("无视 %.0f 点防御力" % (_num(df)))
    return p


def parse_passives(talents) -> TalentPassives:
    """汇总一位干员的穿透被动。

    ``talents`` 里同一个天赋名会出现多档（精英/潜能/模组逐级增强），
    按天赋名分组后只取**最后一档**（数值最大），再对不同天赋名相加，
    避免把同一个天赋的 1/2/3 档叠三次。
    """
    by_name: Dict[str, str] = {}
    for entry in talents or []:
        name = entry[0] if isinstance(entry, (tuple, list)) else entry
        effect = entry[1] if isinstance(entry, (tuple, list)) else entry
        if name and effect:
            by_name[str(name)] = effect      # 同名的后一档覆盖前一档

    total = TalentPassives()
    for effect in by_name.values():
        one = _parse_one(effect)
        total.res_pen_flat += one.res_pen_flat
        total.res_pen_percent += one.res_pen_percent
        total.def_pen_flat += one.def_pen_flat
        total.def_pen_percent += one.def_pen_percent
        total.notes.extend(one.notes)

    total.res_pen_percent = min(1.0, total.res_pen_percent)
    total.def_pen_percent = min(1.0, total.def_pen_percent)
    return total


def parse_passives_at(talents, elite: int) -> TalentPassives:
    """按精英阶段挑选穿透被动（只取 ``<= elite`` 解锁的档位）。

    天赋条目形如 ``(名称, 效果, 解锁精英阶段)``；第三项为 -1 表示
    旧缓存缺少条件信息，此时照旧取同名最后一档。模组强化（同精英、
    数值更高）天然排在同名列表末尾，取最后一档即自动选到最高强化。
    """
    by_name: Dict[str, str] = {}
    by_name_elite: Dict[str, int] = {}
    for entry in talents or []:
        if not isinstance(entry, (tuple, list)) or len(entry) < 2:
            continue
        name = entry[0]
        effect = entry[1]
        if not name or not effect:
            continue
        elite_req = entry[2] if len(entry) >= 3 else -1
        try:
            elite_req = int(elite_req)
        except (TypeError, ValueError):
            elite_req = -1
        key = str(name)
        # 条件已知且高于当前精英阶段 -> 该档未解锁，跳过
        if elite_req >= 0 and elite_req > elite:
            continue
        # 同名取最后一档（同精英下模组强化排后面，数值更高）
        by_name[key] = effect
        by_name_elite[key] = elite_req

    total = TalentPassives()
    for effect in by_name.values():
        one = _parse_one(effect)
        total.res_pen_flat += one.res_pen_flat
        total.res_pen_percent += one.res_pen_percent
        total.def_pen_flat += one.def_pen_flat
        total.def_pen_percent += one.def_pen_percent
        total.notes.extend(one.notes)

    total.res_pen_percent = min(1.0, total.res_pen_percent)
    total.def_pen_percent = min(1.0, total.def_pen_percent)
    return total


def passives_of(operator) -> TalentPassives:
    """便捷入口：``Operator`` -> :class:`TalentPassives`。"""
    if operator is None:
        return TalentPassives()
    return parse_passives(getattr(operator, "talents", None) or [])


def passives_of_at(operator, elite: int) -> TalentPassives:
    """便捷入口：按精英阶段取 ``Operator`` 的穿透被动。"""
    if operator is None:
        return TalentPassives()
    return parse_passives_at(getattr(operator, "talents", None) or [], elite)
