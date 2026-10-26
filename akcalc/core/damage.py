"""伤害计算引擎。

严格依据 PRTS「游戏数据基础」的公式实现：

    基本伤害 A = 攻击力 x 攻击力倍率 + 附加攻击力

    物理:  DMG = max(0.05A, A - [(1-Ip) * max(0, D - Iv)])
    法术:  DMG = max(0.05A, 0.01A * max(0, 100 - (1-Ip) * max(0, D - Iv)))
    元素:  DMG = max(0.05A, 0.01A * max(0, 100 - D))
    真实:  DMG = A
    治疗:  DMG = A

其中 Ip 为百分比穿透，Iv 为固定穿透，D 为目标对应抗性。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

from . import constants as C


@dataclass
class DamageInput:
    """一次伤害计算的全部输入。"""

    attack: float                      # 面板攻击力
    damage_type: str = C.DMG_PHYSICAL
    attack_multiplier: float = 1.0     # 攻击力倍率（"提高至 380%" -> 3.8）
    flat_attack_bonus: float = 0.0     # 附加攻击力

    # 目标抗性最终结果
    target_defense: float = 0.0        # 防御力 / 法抗 / 元素抗性（按类型取用）

    # 穿透
    def_pen_flat: float = 0.0          # 固定穿透 Iv
    def_pen_percent: float = 0.0       # 百分比穿透 Ip（0~1）

    # 减防（只作用于物理）。0.2 表示目标防御力 -20%。
    # 必须做成字段而不是在调用方预先乘好：曲线要把「原始防御力」当横轴，
    # 如果提前折算，减防就只影响面板上的单点数值，扫曲线时被覆盖掉。
    def_down_percent: float = 0.0

    # 增伤
    damage_boost: float = 0.0          # 易伤/增伤，0.3 表示受到伤害 +30%
    final_scaler: float = 1.0          # 最终伤害倍率（降低类乘区）

    # 特殊
    hit_count: int = 1                 # 连击次数（用于总计）
    ignore_min_damage: bool = False    # 是否忽略 5% 保底（几乎总是 False）

    label: str = ""


@dataclass
class DamageResult:
    """伤害计算结果，保留中间量便于核对。"""

    base_damage: float = 0.0     # A
    effective_resist: float = 0.0  # D 参与运算后的有效值
    raw_damage: float = 0.0      # 应用保底前的伤害
    final_damage: float = 0.0    # 单次最终伤害（已取整）
    min_damage: float = 0.0      # 保底伤害 0.05A
    hit_count: int = 1
    total_damage: float = 0.0    # final_damage * hit_count
    floored: bool = False        # 是否触发保底
    damage_type: str = C.DMG_PHYSICAL
    steps: List[str] = field(default_factory=list)  # 计算过程逐步说明


def compute_base_attack(attack: float,
                        attack_multiplier: float = 1.0,
                        flat_bonus: float = 0.0) -> float:
    """基本伤害 A = 攻击力 x 攻击力倍率 + 附加攻击力。"""
    return attack * attack_multiplier + flat_bonus


def compute_damage(inp: DamageInput) -> DamageResult:
    """按伤害类型计算一次攻击的最终伤害。"""
    res = DamageResult(damage_type=inp.damage_type, hit_count=max(1, inp.hit_count))

    A = compute_base_attack(inp.attack, inp.attack_multiplier, inp.flat_attack_bonus)
    res.base_damage = A
    res.steps.append(
        f"基本伤害 A = 攻击力 {inp.attack:g} x 倍率 {inp.attack_multiplier:g}"
        f" + 附加 {inp.flat_attack_bonus:g} = {A:g}"
    )

    min_dmg = C.MIN_DAMAGE_RATIO * A
    res.min_damage = min_dmg

    dt = inp.damage_type

    if dt == C.DMG_TRUE or dt == C.DMG_HEAL:
        raw = A
        res.effective_resist = 0.0
        res.steps.append("真实伤害 / 治疗：不吃防御与抗性，直接等于基本伤害")
    elif dt == C.DMG_PHYSICAL:
        # 减防先乘到目标防御上（只作用于物理），再做穿透：
        #   D' = (1 - 减防%) * D
        #   effective = (1 - Ip) * max(0, D' - Iv)
        _d = inp.target_defense
        if inp.def_down_percent:
            _d = _d * max(0.0, 1.0 - inp.def_down_percent)
            res.steps.append(
                f"减防 {inp.def_down_percent * 100:g}%：防御力 "
                f"{inp.target_defense:g} -> {_d:g}"
            )
        effective = (1.0 - inp.def_pen_percent) * max(0.0, _d - inp.def_pen_flat)
        res.effective_resist = effective
        raw = A - effective
        res.steps.append(
            f"有效防御 = (1 - {inp.def_pen_percent:g}) x max(0, "
            f"{_d:g} - {inp.def_pen_flat:g}) = {effective:g}"
        )
        res.steps.append(f"物理伤害 = A - 有效防御 = {A:g} - {effective:g} = {raw:g}")
    elif dt == C.DMG_MAGICAL:
        effective = (1.0 - inp.def_pen_percent) * max(0.0, inp.target_defense - inp.def_pen_flat)
        res.effective_resist = effective
        raw = C.ELEMENT_RATIO * A * max(0.0, C.RESIST_BASE - effective)
        res.steps.append(
            f"有效法抗 = (1 - {inp.def_pen_percent:g}) x max(0, "
            f"{inp.target_defense:g} - {inp.def_pen_flat:g}) = {effective:g}"
        )
        res.steps.append(
            f"法术伤害 = 0.01 x A x max(0, 100 - 有效法抗) = "
            f"0.01 x {A:g} x max(0, 100 - {effective:g}) = {raw:g}"
        )
    elif dt == C.DMG_ELEMENTAL:
        # 元素伤害不吃穿透，直接用抗性 D
        effective = inp.target_defense
        res.effective_resist = effective
        raw = C.ELEMENT_RATIO * A * max(0.0, C.RESIST_BASE - effective)
        res.steps.append(
            f"元素伤害 = 0.01 x A x max(0, 100 - 元素抗性) = "
            f"0.01 x {A:g} x max(0, 100 - {effective:g}) = {raw:g}"
        )
    else:
        raise ValueError(f"未知伤害类型: {dt}")

    res.raw_damage = raw

    if not inp.ignore_min_damage and raw < min_dmg:
        res.floored = True
        res.steps.append(
            f"触发 5% 保底：raw {raw:g} < 保底 {min_dmg:g}，取 {min_dmg:g}"
        )
        raw = min_dmg
    else:
        res.steps.append(f"未触发保底：raw {raw:g} >= 保底 {min_dmg:g}")

    # 增伤与最终倍率
    if inp.damage_boost:
        res.steps.append(f"增伤 +{inp.damage_boost * 100:g}%：{raw:g} -> {raw * (1 + inp.damage_boost):g}")
        raw = raw * (1.0 + inp.damage_boost)
    if inp.final_scaler != 1.0:
        res.steps.append(f"最终倍率 x{inp.final_scaler:g}：{raw:g} -> {raw * inp.final_scaler:g}")
        raw = raw * inp.final_scaler

    res.final_damage = raw
    res.total_damage = raw * res.hit_count
    if res.hit_count > 1:
        res.steps.append(f"连击 x{res.hit_count}：总伤害 {res.total_damage:g}")
    return res


# ------------------------------------------------------------------ 批量分析

@dataclass
class MultiHitResult:
    """多次不同攻击的汇总。"""

    results: List[DamageResult] = field(default_factory=list)

    @property
    def total(self) -> float:
        return sum(r.total_damage for r in self.results)


def compute_kill_time(total_hp: float, damage_per_hit: float,
                      attack_interval: float) -> float:
    """估算击杀所需时间（秒）。"""
    if damage_per_hit <= 0:
        return float("inf")
    shots = total_hp / damage_per_hit
    return max(0.0, shots * attack_interval)


def compute_dps(damage_per_hit: float, attack_interval: float,
                hit_count: int = 1) -> float:
    """计算 DPS。attack_interval 为实际攻击间隔。"""
    if attack_interval <= 0:
        return 0.0
    return damage_per_hit * hit_count / attack_interval


def effective_attack_interval(t0: float, attack_speed: float = 100.0) -> float:
    """实际攻击间隔 T = T0 / (clamp(S, 10, 600) / 100)。"""
    s = max(C.ATTACK_SPEED_MIN, min(C.ATTACK_SPEED_MAX, attack_speed))
    return t0 / (s / 100.0)


def break_defense_threshold(A: float, min_ratio: float = C.MIN_DAMAGE_RATIO) -> float:
    """破甲线：使实际伤害刚好触底所需的防御力。

    物理解析解：A - D = 0.05A  =>  D = 0.95A
    """
    return A * (1.0 - min_ratio)


def damage_curve(attack: float, damage_type: str,
                 defense_from: float = 0.0, defense_to: float = 3000.0,
                 step: float = 50.0,
                 attack_multiplier: float = 1.0,
                 def_pen_flat: float = 0.0,
                 def_pen_percent: float = 0.0) -> List[tuple]:
    """生成「防御力 -> 伤害」曲线，用于绘图。"""
    out = []
    d = defense_from
    while d <= defense_to + 1e-9:
        inp = DamageInput(
            attack=attack, damage_type=damage_type,
            attack_multiplier=attack_multiplier,
            target_defense=d,
            def_pen_flat=def_pen_flat,
            def_pen_percent=def_pen_percent,
        )
        out.append((d, compute_damage(inp).final_damage))
        d += step
    return out