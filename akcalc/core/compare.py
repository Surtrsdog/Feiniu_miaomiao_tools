# -*- coding: utf-8 -*-
"""对比模式的数据模型：把一个「对比槽位」的参数整理成 DamageInput。

UI 只负责收集每个槽位的下拉选择，换算成参数这件事放在这里，
好处是可以脱离 tkinter 单独测试（曲线、DPS、破甲线都能对账）。
"""
from __future__ import annotations

import copy
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from . import constants as C
from . import curves as CV
from . import damage as DMG
from .models import Operator

#: 单个槽位可对比的技能等级（技能本身各自选）
DEFAULT_SKILL_LEVELS = ("7", "专一", "专二", "专三")


@dataclass
class CompareEntry:
    """一位干员的对比参数。"""

    name: str = ""                       # 显示名（图例用）
    operator: Optional[Operator] = None
    elite: int = 2
    level: int = 90
    trust: bool = True
    potential: bool = False
    #: 技能下标（-1 表示不使用技能）
    skill_index: int = -1
    skill_level: str = "专三"

    def stats(self):
        """返回 (OperatorStats, 实际攻击力)；无干员或等级不存在时返回 None。"""
        op = self.operator
        if op is None:
            return None
        st = op.stats_at(self.elite, self.level)
        if st is None:
            return None
        atk = st.atk
        if self.trust:
            atk += op.trust_bonus.get("atk", 0.0)
        if self.potential:
            atk += op.potential_bonus.get("atk", 0.0)
        return st, atk

    def chosen_skill(self):
        """返回 (Skill, SkillLevel) 或 (None, None)。"""
        op = self.operator
        if op is None or self.skill_index < 0:
            return None, None
        skills = list(getattr(op, "skills", None) or [])
        if self.skill_index >= len(skills):
            return None, None
        sk = skills[self.skill_index]
        return sk, sk.level(self.skill_level)

    def label(self) -> str:
        """图例名：干员名 +（技能标记）。"""
        if not self.operator:
            return self.name or "空"
        sk, lv = self.chosen_skill()
        if sk is None:
            return self.operator.name
        return "%s S%d" % (self.operator.name, sk.index)


def build_entry_input(entry: CompareEntry,
                      *, damage_type: str = C.DMG_PHYSICAL,
                      multiplier: float = 1.0, flat: float = 0.0,
                      pen_percent: float = 0.0, pen_flat: float = 0.0,
                      boost: float = 0.0, hits: int = 1,
                      target_def: float = 0.0,
                      speed: float = 100.0):
    """把槽位参数换算成 (DamageInput, 实际攻击间隔, 破甲线)。

    攻击力、攻击间隔、连击、技能倍率全部按该干员自己的数值来，
    其余（穿透 / 增伤 / 目标抗性 / 攻速）作为公共条件传入。

    伤害类型是**每一位干员各自**的，不能用全局那一份
    -------------------------------------------------
    对比模式里 damage_type 是「公共条件」传进来的（用户在面板上选的那个
    单选按钮）。可是把史尔特尔（法术）和银灰（物理）放在一起比的时候，
    传进来的只有一个值：要么两个人全按物理算，要么全按法术算，总有一边
    是错的 —— 而且错得离谱（法术干员按物理算，对 800 防的敌人 DPS 会
    直接掉到 5% 保底）。

    所以这里改成：公共值只当「用户手工指定的默认」，实际计算时优先用
    该干员自己的分支类型。只有用户显式选了非物理（说明他就是要压测
    某种伤害类型）时才统一覆盖。
    """
    st_atk = entry.stats()
    if st_atk is None:
        return None
    st, atk = st_atk
    sk, lv = entry.chosen_skill()

    mult = multiplier
    flat_bonus = flat
    hit_count = max(1, hits)
    interval_delta = 0.0
    speed_bonus = 0.0
    if lv is not None:
        mult *= lv.atk_multiplier
        flat_bonus += lv.flat_atk
        hit_count = max(1, hit_count * lv.hit_count)
        interval_delta = lv.interval_delta
        speed_bonus = lv.attack_speed

    dtype = _entry_damage_type(entry, damage_type, lv)

    inp = DMG.DamageInput(
        attack=atk, damage_type=dtype,
        attack_multiplier=mult, flat_attack_bonus=flat_bonus,
        target_defense=target_def,
        def_pen_flat=pen_flat, def_pen_percent=pen_percent,
        damage_boost=boost, hit_count=hit_count,
    )
    iv = DMG.effective_attack_interval(st.attack_interval + interval_delta,
                                       speed + speed_bonus)
    if iv <= 0:
        iv = 0.01

    base_a = inp.attack * inp.attack_multiplier + inp.flat_attack_bonus
    break_line = (DMG.break_defense_threshold(base_a)
                  if dtype == C.DMG_PHYSICAL else 0.0)
    return inp, iv, break_line


def _entry_damage_type(entry: CompareEntry, common_type: str, lv) -> str:
    """决定某一位干员参与计算时用哪种伤害类型。

    优先级：
      1. 技能描述里写明「造成法术伤害 / 真实伤害」-> 以技能为准
         （陷阱师望的普攻是物理，但三技能是法伤）
      2. 该干员分支的固有类型（术师 -> 法术、医师 -> 治疗）
      3. 都拿不到才用公共条件里的值
    """
    from . import damage_type as DT

    op = getattr(entry, "operator", None)
    prof = getattr(op, "profession", "") if op is not None else ""
    sub = getattr(op, "sub_profession", "") if op is not None else ""
    desc = getattr(lv, "description", "") if lv is not None else ""

    from_text = DT.from_skill_text(desc, "")
    if from_text and from_text != C.DMG_HEAL:
        return from_text
    branch = DT.guess_damage_type(prof, sub, default="")
    if branch:
        # 医疗分支本来就不产生伤害；此时保留公共值，别把治疗算成 0 伤害
        if branch == C.DMG_HEAL:
            return common_type or C.DMG_PHYSICAL
        return branch
    return common_type or C.DMG_PHYSICAL


@dataclass
class CompareResult:
    """一个槽位的计算结果，用于汇总表。"""

    label: str
    color: str
    attack: float
    interval: float
    per_hit: float
    dph: float
    dps: float
    break_line: float
    skill: str = ""


def evaluate(entries: List[CompareEntry], **kw) -> List[CompareResult]:
    """算一遍每个槽位在当前目标抗性下的三项指标。"""
    from . import constants as _C
    out: List[CompareResult] = []
    dtype = kw.get("damage_type", _C.DMG_PHYSICAL)
    for i, e in enumerate(entries):
        built = build_entry_input(e, **kw)
        if built is None:
            continue
        inp, iv, bl = built
        try:
            r = DMG.compute_damage(inp)
        except ValueError:
            continue
        sk, lv = e.chosen_skill()
        out.append(CompareResult(
            label=e.label(),
            color=CV.COMPARE_COLORS[i % len(CV.COMPARE_COLORS)],
            attack=inp.attack * inp.attack_multiplier + inp.flat_attack_bonus,
            interval=iv,
            per_hit=r.final_damage,
            dph=r.total_damage,
            dps=DMG.compute_dps(r.final_damage, iv, max(1, inp.hit_count)),
            break_line=bl,
            skill="%s %s" % (sk.name, e.skill_level) if sk else "",
        ))
    return out