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
                      res_pen_flat: float = 0.0, res_pen_percent: float = 0.0,
                      def_down_percent: float = 0.0, final_scaler: float = 1.0,
                      boost: float = 0.0, hits: int = 1,
                      target_def: float = 0.0,
                      target_res: float = 0.0, target_eres: float = 0.0,
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
        # 单次伤害缩放（「相当于攻击力 60% 的 8 连发」）折进倍率，
        # 与主面板 _with_skill 的口径保持一致；漏掉它 DPS 会虚高。
        # 混伤技能的 dmg_scale 是物理分量倍率，这里同样折进物理倍率。
        scale = getattr(lv, "dmg_scale", 1.0) or 1.0
        if scale != 1.0:
            mult *= scale
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
        res_pen_flat=res_pen_flat, res_pen_percent=res_pen_percent,
        def_down_percent=def_down_percent,
        damage_boost=boost, final_scaler=final_scaler, hit_count=hit_count,
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


def _entry_is_mixed(e: CompareEntry) -> bool:
    """该槽位当前技能是否为混伤（物理 + 法术一次攻击同时结算）。"""
    sk, lv = e.chosen_skill()
    if sk is None or lv is None:
        return False
    return bool(getattr(lv, "magic_scale", 0.0) > 0)


def evaluate(entries: List[CompareEntry], **kw) -> List[CompareResult]:
    """算一遍每个槽位在当前目标抗性下的三项指标。

    混伤技能（magic_scale > 0）按分量分别计算再加总，而不是笼统当作
    单一伤害类型——否则法术分量要么吃错抗性、要么整段漏掉。
    """
    from . import constants as _C
    from . import damage_type as _DT

    out: List[CompareResult] = []
    dtype = kw.get("damage_type", _C.DMG_PHYSICAL)
    for i, e in enumerate(entries):
        sk, lv = e.chosen_skill()
        color = CV.COMPARE_COLORS[i % len(CV.COMPARE_COLORS)]
        label = e.label()
        skill_txt = "%s %s" % (sk.name, e.skill_level) if sk else ""

        if _entry_is_mixed(e):
            r = _evaluate_mixed(e, kw)
            if r is not None:
                out.append(CompareResult(
                    label=label, color=color, attack=r[0], interval=r[1],
                    per_hit=r[2], dph=r[3], dps=r[4], break_line=r[5],
                    skill=skill_txt))
            continue

        built = build_entry_input(e, **kw)
        if built is None:
            continue
        inp, iv, bl = built
        try:
            r = DMG.compute_damage(inp)
        except ValueError:
            continue
        out.append(CompareResult(
            label=label,
            color=color,
            attack=inp.attack * inp.attack_multiplier + inp.flat_attack_bonus,
            interval=iv,
            per_hit=r.final_damage,
            dph=r.total_damage,
            dps=DMG.compute_dps(r.final_damage, iv, max(1, inp.hit_count)),
            break_line=bl,
            skill=skill_txt,
        ))
    return out


def _evaluate_mixed(e: CompareEntry, kw) -> Optional[tuple]:
    """混伤槽位：返回 (攻击力, 间隔, 单次, DPH, DPS, 破甲线) 或 None。"""
    st_atk = e.stats()
    if st_atk is None:
        return None
    st, atk = st_atk
    sk, lv = e.chosen_skill()
    if sk is None or lv is None:
        return None

    from . import damage_type as _DT

    multiplier = kw.get("multiplier", 1.0)
    flat = kw.get("flat", 0.0)
    hits = max(1, kw.get("hits", 1))
    target_def = kw.get("target_def", 0.0)
    speed = kw.get("speed", 100.0)
    boost = kw.get("boost", 0.0)
    # 物理穿透 / 法术穿透分流（与主面板一致）
    phys_pen_pct = kw.get("pen_percent", 0.0)
    phys_pen_flat = kw.get("pen_flat", 0.0)
    mag_pen_flat = kw.get("res_pen_flat", 0.0)
    mag_pen_pct = kw.get("res_pen_percent", 0.0)
    def_down = kw.get("def_down_percent", 0.0)
    # 对比模式暂不读天赋被动，穿透以加拐为准

    op = e.operator
    phys_dtype = _DT.guess_damage_type(
        getattr(op, "profession", ""), getattr(op, "sub_profession", ""))
    if phys_dtype in (C.DMG_HEAL, "", None):
        phys_dtype = C.DMG_PHYSICAL

    stops = bool(getattr(lv, "stops_attack", False))
    skill_mult = 1.0 if stops else lv.atk_multiplier
    skill_hits = max(1, lv.hit_count)
    phys_scale = getattr(lv, "dmg_scale", 1.0) or 1.0
    mag_scale = lv.magic_scale
    total_hits = max(1, hits * skill_hits)

    comps: List[DMG.DamageComponent] = []
    if not stops:
        comps.append(DMG.DamageComponent(
            damage_type=phys_dtype,
            attack_multiplier=multiplier * skill_mult * phys_scale,
            flat_attack_bonus=flat + lv.flat_atk,
            hit_count=total_hits,
            def_pen_flat=phys_pen_flat,
            def_pen_percent=phys_pen_pct,
            def_down_percent=def_down,
            res_pen_flat=mag_pen_flat,
            res_pen_percent=mag_pen_pct,
            label="物理分量"))
    comps.append(DMG.DamageComponent(
        damage_type=C.DMG_MAGICAL,
        attack_multiplier=multiplier * skill_mult * mag_scale,
        flat_attack_bonus=flat + lv.flat_atk,
        hit_count=total_hits,
        def_pen_flat=phys_pen_flat,
        def_pen_percent=phys_pen_pct,
        res_pen_flat=mag_pen_flat,
        res_pen_percent=mag_pen_pct,
        label="法术分量"))

    m_inp = DMG.MultiTypeInput(
        attack=atk, components=comps,
        target_defense=target_def,
        target_res=kw.get("target_res", 0.0),
        target_eres=kw.get("target_eres", 0.0),
        damage_boost=boost, final_scaler=kw.get("final_scaler", 1.0))
    try:
        res = DMG.compute_multi(m_inp)
    except ValueError:
        return None

    interval_delta = lv.interval_delta
    speed_bonus = lv.attack_speed
    iv = DMG.effective_attack_interval(st.attack_interval + interval_delta,
                                       speed + speed_bonus)
    if iv <= 0:
        iv = 0.01

    break_line = 0.0
    if not stops and phys_dtype == C.DMG_PHYSICAL:
        phys_a = atk * (multiplier * skill_mult * phys_scale) + flat + lv.flat_atk
        break_line = DMG.break_defense_threshold(phys_a)

    base_atk = atk * (multiplier * skill_mult) + flat + lv.flat_atk
    return (base_atk, iv, res.final_damage, res.total_damage,
            DMG.multi_dps(res, iv), break_line)