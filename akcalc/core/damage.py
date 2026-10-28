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
from typing import Dict, List, Optional, Sequence

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
    # 法术穿透（专用于法术分量；为空时法术分支回退用 def_pen_*）
    res_pen_flat: float = 0.0
    res_pen_percent: float = 0.0

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
    penetration_note: str = ""   # 穿透生效说明（无穿透时为空）
    steps: List[str] = field(default_factory=list)  # 计算过程逐步说明


@dataclass
class DamageComponent:
    """混伤（一次攻击同时打出多种伤害）里的一个分量。

    每个分量有独立的伤害类型、倍率、附加攻击力与穿透。物理分量的
    穿透作用在防御上，法术分量的穿透作用在法抗上——两者互不串扰，
    这正是「混伤要按类型分别计算」的落点。
    """

    damage_type: str = C.DMG_PHYSICAL
    attack_multiplier: float = 1.0   # 本分量的攻击力倍率
    flat_attack_bonus: float = 0.0   # 本分量的附加攻击力
    hit_count: int = 1               # 本分量的连击数
    # 物理穿透（只对物理分量生效）
    def_pen_flat: float = 0.0
    def_pen_percent: float = 0.0
    def_down_percent: float = 0.0    # 减防 %
    # 法术穿透（只对法术分量生效）
    res_pen_flat: float = 0.0
    res_pen_percent: float = 0.0
    label: str = ""


@dataclass
class MultiTypeInput:
    """一次「混伤攻击」的完整输入：共享面板攻击力 + 若干伤害分量。"""

    attack: float = 0.0
    components: List[DamageComponent] = field(default_factory=list)
    target_defense: float = 0.0   # 物理防御
    target_res: float = 0.0       # 法术抗性（点）
    target_eres: float = 0.0      # 元素抗性（点）
    damage_boost: float = 0.0     # 脆弱/易伤，作用于全部分量
    final_scaler: float = 1.0     # 末端倍率，作用于全部分量
    label: str = ""

    @property
    def is_mixed(self) -> bool:
        """是否真的混伤（含不止一种会结算伤害的类型）。"""
        dtypes = {c.damage_type for c in self.components}
        return len(dtypes) > 1


@dataclass
class MultiTypeResult:
    """混伤计算汇总：每个分量一个 DamageResult，再合并成 DPH/DPS。"""

    results: List[DamageResult] = field(default_factory=list)
    base_attack: float = 0.0
    label: str = ""

    @property
    def final_damage(self) -> float:
        """单次总伤害：各分量单发之和。"""
        return sum(r.final_damage for r in self.results)

    @property
    def total_damage(self) -> float:
        """DPH：各分量 final_damage x hit_count 之和。"""
        return sum(r.total_damage for r in self.results)

    def per_type(self) -> Dict[str, float]:
        """按伤害类型汇总的 DPH（final x hit）。"""
        out: Dict[str, float] = {}
        for r in self.results:
            out[r.damage_type] = out.get(r.damage_type, 0.0) + r.total_damage
        return out

    def per_type_hit(self) -> Dict[str, float]:
        """按伤害类型汇总的单次伤害（各分量单发之和，不含连击）。"""
        out: Dict[str, float] = {}
        for r in self.results:
            out[r.damage_type] = out.get(r.damage_type, 0.0) + r.final_damage
        return out


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
        # 命中穿透时明确写出「少算了多少」：只给一个有效防御数字，
        # 玩家看不出穿透到底有没有生效（尤其天赋被动的固定穿透）。
        # 目标本来就没抗性时穿透不产生收益，这种场合不刷提示。
        if (inp.def_pen_flat or inp.def_pen_percent) and _d > 0:
            _no_pen = (1.0 - inp.def_pen_percent) * max(0.0, _d)
            # 两边都要过 5% 保底再比，否则 A 打不穿防御时会写出
            # 「单次伤害 -52 -> 168」这种负数，看着像算错了。
            _raw_no = max(min_dmg, A - _no_pen)
            _raw_pen = max(min_dmg, raw)
            _gain = _raw_pen - _raw_no
            if _gain > 1e-9:
                res.penetration_note = (
                    f"物理穿透生效：无视 {inp.def_pen_flat:g} 点防御"
                    + (f" + {inp.def_pen_percent * 100:g}% 穿透"
                       if inp.def_pen_percent else "")
                    + f"，有效防御 {_d:g} -> {effective:g}，"
                      f"单次伤害 {_raw_no:g} -> {_raw_pen:g}"
                      f"（+{_gain:g}）"
                )
                res.steps.append(res.penetration_note)
        res.steps.append(f"物理伤害 = A - 有效防御 = {A:g} - {effective:g} = {raw:g}")
    elif dt == C.DMG_MAGICAL:
        # 法术穿透优先用 res_pen_*；缺省时回退到 def_pen_*（历史兼容：
        # 旧调用只填 def_pen_*，法术分支一直借它当法穿用）。
        pen_pct = inp.res_pen_percent if inp.res_pen_percent else inp.def_pen_percent
        pen_flat = inp.res_pen_flat if inp.res_pen_flat else inp.def_pen_flat
        effective = (1.0 - pen_pct) * max(0.0, inp.target_defense - pen_flat)
        res.effective_resist = effective
        raw = C.ELEMENT_RATIO * A * max(0.0, C.RESIST_BASE - effective)
        res.steps.append(
            f"有效法抗 = (1 - {pen_pct:g}) x max(0, "
            f"{inp.target_defense:g} - {pen_flat:g}) = {effective:g}"
        )
        if (pen_flat or pen_pct) and inp.target_defense > 0:
            _no_pen = (1.0 - pen_pct) * max(0.0, inp.target_defense)
            _raw_no = C.ELEMENT_RATIO * A * max(0.0, C.RESIST_BASE - _no_pen)
            # 同物理分支：两边都过保底再比，避免出现负数伤害对比
            _raw_no = max(min_dmg, _raw_no)
            _raw_pen = max(min_dmg, raw)
            _gain = _raw_pen - _raw_no
            if _gain > 1e-9:
                res.penetration_note = (
                    f"法术穿透生效：无视 {pen_flat:g} 点法抗"
                    + (f" + {pen_pct * 100:g}% 穿透" if pen_pct else "")
                    + f"，有效法抗 {inp.target_defense:g} -> {effective:g}，"
                      f"单次伤害 {_raw_no:g} -> {_raw_pen:g}（+{_gain:g}）"
                )
                res.steps.append(res.penetration_note)
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


def component_input(inp: MultiTypeInput, comp: DamageComponent) -> DamageInput:
    """把一个混伤分量展开成单类型的 DamageInput（与 compute_multi 同规则）。

    每个分量的目标抗性按它的伤害类型选：
      物理分量 -> target_defense（防御，吃减防/物穿）
      法术分量 -> target_res（法抗，吃法穿）
      元素分量 -> target_eres（元素抗性，不吃穿透）
      真实/治疗 -> 不参与抗性
    脆弱与最终倍率对全部分量统一乘一次。
    """
    target = inp.target_defense
    if comp.damage_type == C.DMG_MAGICAL:
        target = inp.target_res
    elif comp.damage_type == C.DMG_ELEMENTAL:
        target = inp.target_eres
    return DamageInput(
        attack=inp.attack,
        damage_type=comp.damage_type,
        attack_multiplier=comp.attack_multiplier,
        flat_attack_bonus=comp.flat_attack_bonus,
        target_defense=target,
        def_pen_flat=comp.def_pen_flat,
        def_pen_percent=comp.def_pen_percent,
        def_down_percent=comp.def_down_percent,
        res_pen_flat=comp.res_pen_flat,
        res_pen_percent=comp.res_pen_percent,
        damage_boost=inp.damage_boost,
        final_scaler=inp.final_scaler,
        hit_count=max(1, comp.hit_count),
        label=comp.label or inp.label,
    )


def compute_multi(inp: MultiTypeInput) -> MultiTypeResult:
    """混伤：把每个分量独立算一遍，再汇总。"""
    res = MultiTypeResult(label=inp.label)
    if not inp.components:
        return res
    for comp in inp.components:
        res.results.append(compute_damage(component_input(inp, comp)))
    return res


def multi_dps(res: MultiTypeResult, interval: float) -> float:
    """混伤的 DPS：DPH（各分量 final x hit 之和）/ 攻击间隔。"""
    if interval <= 0:
        return 0.0
    return res.total_damage / interval


def multi_per_hit(res: MultiTypeResult) -> float:
    """混伤单次总伤害（各分量单发之和，不含连击）。"""
    return res.final_damage


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

# ------------------------------------------------------------------ 召唤物汇总

@dataclass
class SummonInput:
    """一个召唤物参与输出的输入（与干员本体分开算）。

    为什么召唤物要单独一条通道
    --------------------------
    召唤物的伤害和干员本体是**两条独立的攻击流**：

      * 攻击力不同 —— 令本体 473，她的「弦惊」是 823
      * 攻击间隔不同 —— 本体 1.6s，「弦惊」1.5s
      * 抗性口径不同 —— 两者都吃同一目标的防御/法抗，但各自带
        不同的穿透（召唤物自身天赋不通用干员天赋）

    所以不能把召唤物的攻击力塞进干员本体那一份公式，必须单独
    ``compute_damage`` 之后再相加，否则间隔与穿透都会串。
    """

    name: str = "召唤物"
    attack: float = 0.0
    interval: float = 1.0
    damage_type: str = C.DMG_PHYSICAL
    attack_multiplier: float = 1.0
    hit_count: int = 1
    #: 同一个召唤物同时在场的数量（令最多 4 个「弦惊」）
    count: int = 1
    def_pen_flat: float = 0.0
    def_pen_percent: float = 0.0
    res_pen_flat: float = 0.0
    res_pen_percent: float = 0.0


@dataclass
class SummonResult:
    """召唤物汇总结果：每个召唤物的单项 + 合计。"""

    results: List[DamageResult] = field(default_factory=list)
    inputs: List[SummonInput] = field(default_factory=list)

    @property
    def per_hit(self) -> float:
        """一次「召唤物齐射」的单次伤害合计（含数量）。"""
        return sum(r.total_damage for r in self.results)

    @property
    def dps(self) -> float:
        """召唤物 DPS 合计：每个召唤物各自除以自己的攻击间隔。"""
        return sum(_summon_dps(r, i) for r, i in zip(self.results, self.inputs))

    @property
    def total(self) -> int:
        return len(self.results)

    def per_type(self) -> Dict[str, float]:
        out: Dict[str, float] = {}
        for r in self.results:
            out[r.damage_type] = out.get(r.damage_type, 0.0) + r.total_damage
        return out


def _summon_dps(r: DamageResult, inp: SummonInput) -> float:
    if inp.interval <= 0:
        return 0.0
    return r.total_damage / inp.interval


def compute_summon(inp: SummonInput, target_defense: float = 0.0,
                   target_res: float = 0.0, target_eres: float = 0.0,
                   damage_boost: float = 0.0,
                   final_scaler: float = 1.0) -> DamageResult:
    """按召唤物自己的攻击力/间隔/类型结算一次攻击。

    ``count``（同时在场数量）作为整体倍率乘到结果上：3 个「弦惊」齐射
    的单次伤害与 DPH 都是单个的 3 倍。不用 hit_count 表达数量，因为
    hit_count 只影响 total_damage，会让「单次伤害」指标漏乘数量。
    """
    dt = inp.damage_type
    target = target_defense
    if dt == C.DMG_MAGICAL:
        target = target_res
    elif dt == C.DMG_ELEMENTAL:
        target = target_eres
    d_inp = DamageInput(
        attack=inp.attack,
        damage_type=dt,
        attack_multiplier=inp.attack_multiplier,
        target_defense=target,
        def_pen_flat=inp.def_pen_flat,
        def_pen_percent=inp.def_pen_percent,
        res_pen_flat=inp.res_pen_flat,
        res_pen_percent=inp.res_pen_percent,
        damage_boost=damage_boost,
        final_scaler=final_scaler,
        hit_count=max(1, inp.hit_count),
        label=inp.name,
    )
    r = compute_damage(d_inp)
    n = max(1, inp.count)
    if n != 1:
        r.final_damage *= n
        r.total_damage *= n
        r.steps.append("同时在场上限 x%d：单次与 DPH 均乘 %d" % (n, n))
    return r


def compute_summons(summons: Sequence[SummonInput],
                    target_defense: float = 0.0,
                    target_res: float = 0.0,
                    target_eres: float = 0.0,
                    damage_boost: float = 0.0,
                    final_scaler: float = 1.0) -> SummonResult:
    """把一组召唤物逐条结算后汇总。"""
    out = SummonResult()
    for s in summons:
        if s.attack <= 0:
            continue
        out.inputs.append(s)
        out.results.append(compute_summon(
            s, target_defense, target_res, target_eres,
            damage_boost, final_scaler))
    return out
