# -*- mode: python ; coding: utf-8 -*-
"""伤害曲线引擎：把一个自变量扫一遍，算出各条曲线的点。

设计
----
UI 只需要「一组曲线 + 横轴说明」，所以统一成 CurveChart/CurveSeries。
所有曲线都复用 damage.compute_damage，保证与单点结果完全一致。
"""
from __future__ import annotations

import copy
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Sequence, Tuple

from . import constants as C
from . import damage as DMG


# ------------------------------------------------------------------ 数据结构

@dataclass
class CurveSeries:
    """一条曲线。"""

    name: str
    points: List[Tuple[float, float]] = field(default_factory=list)
    color: str = "#4ea1f7"
    unit: str = ""
    note: str = ""

    @property
    def max_y(self) -> float:
        return max((y for _, y in self.points), default=0.0)


@dataclass
class CurveChart:
    """一张图：横轴 + 若干条曲线。"""

    title: str = ""
    x_label: str = ""
    x_unit: str = ""
    y_label: str = ""
    y_unit: str = ""
    series: List[CurveSeries] = field(default_factory=list)
    desc: str = ""
    note: str = ""
    marker_x: Optional[float] = None
    marker_label: str = ""
    #: 对比模式下每位干员当前取值所在的横坐标，用于打点标记
    marker_xs: List[float] = field(default_factory=list)
    #: 只在悬停浮层里显示、不画成线的辅助数列。
    #: 用来把「该防御值下的 DPS / DPH」一直给全：
    #: 无论当前选的是哪条曲线，鼠标一指就能同时看到三个数。
    hover_series: List[CurveSeries] = field(default_factory=list)

    @property
    def x_range(self) -> Tuple[float, float]:
        xs = [x for s in self.series for x, _ in s.points]
        if not xs:
            return (0.0, 1.0)
        return (min(xs), max(xs))

    @property
    def y_range(self) -> Tuple[float, float]:
        ys = [y for s in self.series for _, y in s.points]
        if not ys:
            return (0.0, 1.0)
        lo = min(0.0, min(ys))
        hi = max(ys)
        if hi <= lo:
            hi = lo + 1.0
        return (lo, hi)


# ------------------------------------------------------------------ 曲线类型

CURVE_KINDS: Dict[str, str] = {
    "dmg_def":     "伤害 - 防御",
    "dmg_res":     "伤害 - 法抗",
    "dmg_elem":    "伤害 - 元素抗性",
    "dph":         "DPH - 防御",
    "dps":         "DPS - 防御",
    "dps_res":     "DPS - 法抗",
    "dmg_atk":     "伤害 - 攻击力",
    "dmg_mult":    "伤害 - 攻击力倍率",
    "dmg_pen":     "伤害 - 穿透",
    "dps_speed":   "DPS - 攻速",
}

DEFAULT_KIND = "dmg_def"


def _steps(lo: float, hi: float, n: int) -> List[float]:
    if n < 2:
        return [lo]
    return [lo + (hi - lo) * i / (n - 1) for i in range(n)]


def _sweep(inp: DMG.DamageInput,
           values: Sequence[float],
           setter: Callable[[DMG.DamageInput, float], None],
           selector: Callable[[DMG.DamageResult], float]) -> List[Tuple[float, float]]:
    out: List[Tuple[float, float]] = []
    for v in values:
        i2 = copy.copy(inp)
        setter(i2, v)
        try:
            r = DMG.compute_damage(i2)
        except ValueError:
            continue
        out.append((v, selector(r)))
    return out


def _per_hit(r: DMG.DamageResult) -> float:
    return r.final_damage


def _total_hit(r: DMG.DamageResult) -> float:
    return r.total_damage


def _dps_of(interval: float) -> Callable[[DMG.DamageResult], float]:
    def f(r: DMG.DamageResult) -> float:
        return DMG.compute_dps(r.final_damage, interval, max(1, r.hit_count))
    return f


# ------------------------------------------------------------------ 主入口

def build_chart(kind: str,
                inp: DMG.DamageInput,
                interval: float,
                *,
                x_max: float = 0.0,
                points: int = 121,
                break_line: float = 0.0) -> CurveChart:
    """按曲线类型生成一张图。

    kind      : CURVE_KINDS 中的键
    inp       : 当前参数
    interval  : 实际攻击间隔（秒）
    x_max     : 横轴上限，0 表示用默认
    points    : 采样点数
    break_line: 破甲线，会标一条竖线
    """
    chart = CurveChart()

    # ---------------- 防御类
    if kind in ("dmg_def", "dph", "dps"):
        hi = x_max or max(3000.0, inp.attack * 3.0)
        xs = _steps(0.0, hi, points)

        def set_def(i: DMG.DamageInput, v: float) -> None:
            i.damage_type = C.DMG_PHYSICAL
            i.target_defense = v

        # 防御轴只对物理伤害有意义。法术/元素/真实干员扫防御力是一条
        # 水平线（防御压根不参与运算），以前这里强制把 damage_type 改成
        # PHYSICAL，于是「史尔特尔 伤害-防御」画出一条随防御下降的曲线，
        # 看起来像在算物理伤害——完全错的。现在按干员自身的伤害类型
        # 决定画法：物理照常扫防御，其它类型画水平线并注明原因。
        _dt = getattr(inp, "damage_type", C.DMG_PHYSICAL)
        _is_phys = _dt == C.DMG_PHYSICAL

        if kind == "dph":
            chart.title = "DPH - 防御（每次攻击总伤害）"
            chart.y_label = "每次攻击总伤害"
            sel = _total_hit
        elif kind == "dps":
            chart.title = "DPS - 防御"
            chart.y_label = "伤害 / 秒"
            sel = _dps_of(interval)
        else:
            chart.title = "伤害 - 防御"
            chart.y_label = "单次伤害"
            sel = _per_hit

        chart.x_label = "防御力"
        chart.x_unit = "DEF"
        chart.y_unit = "伤害"
        _u = {"dmg_def": "单次", "dph": "DPH", "dps": "DPS"}[kind]

        if _is_phys:
            chart.series.append(CurveSeries(
                name="物理伤害", points=_sweep(inp, xs, set_def, sel),
                color="#4ea1f7", unit=_u))

        base_a = inp.attack * inp.attack_multiplier + inp.flat_attack_bonus
        minv = C.MIN_DAMAGE_RATIO * base_a * max(1, inp.hit_count)
        if kind == "dps" and interval > 0:
            minv /= interval
        if _is_phys:
            chart.series.append(CurveSeries(
                name="5% 保底线", points=[(x, minv) for x in xs],
                color="#7f8c99", note="保底", unit=_u))
        # 悬浮浮层里始终同时给出 DPH 与 DPS，
        # 不受当前选的曲线种类影响。
        if _is_phys:
            for _hk, _hname, _hunit in (("dph", "DPH", "DPH"), ("dps", "DPS", "DPS")):
                if _hk == kind:
                    continue
                _hsel = _total_hit if _hk == "dph" else _dps_of(interval)
                chart.hover_series.append(CurveSeries(
                    name=_hname, points=_sweep(inp, xs, set_def, _hsel),
                    unit=_hunit, note="hover"))
        if not _is_phys:
            # 法术 / 元素 / 真实伤害：防御力不参与运算，画一条水平线
            _cur = sel(DMG.compute_damage(inp))
            _tname = C.DMG_TYPE_LABELS.get(_dt, "当前伤害")
            chart.series.append(CurveSeries(
                name="%s（与防御力无关）" % _tname,
                points=[(x, _cur) for x in xs],
                color="#7f8c99", unit=_u,
                note="防御力不影响该伤害类型"))
            chart.desc = ("该干员造成%s，防御力对它没有影响，所以曲线是"
                          "一条水平线。想看随防御下降的曲线请切到物理干员，"
                          "或把伤害类型改成「物理伤害」。" % _tname)
        elif break_line > 0:
            chart.marker_x = break_line
            chart.marker_label = "破甲线"
        if _is_phys:
            chart.desc = ("物理：max(0.05A, A - max(0, DEF - 固定穿透) x (1 - 百分比穿透))"
                          "；A = 攻击力 x 倍率 + 附加攻击力")

    elif kind in ("dmg_res", "dps_res"):
        hi = x_max or 100.0
        xs = _steps(0.0, hi, points)

        def set_res(i: DMG.DamageInput, v: float) -> None:
            i.damage_type = C.DMG_MAGICAL
            i.target_defense = v

        # 法抗轴只对法术伤害有意义；对称地处理（见上面防御轴注释）
        _dt = getattr(inp, "damage_type", C.DMG_PHYSICAL)
        _is_mag = _dt == C.DMG_MAGICAL

        if kind == "dps_res":
            chart.title = "DPS - 法抗"
            chart.y_label = "伤害 / 秒"
            sel = _dps_of(interval)
        else:
            chart.title = "伤害 - 法抗"
            chart.y_label = "单次伤害"
            sel = _per_hit

        chart.x_label = "法术抗性"
        chart.x_unit = "RES"
        chart.y_unit = "伤害"
        _u = "DPS" if kind == "dps_res" else "单次"
        if _is_mag:
            chart.series.append(CurveSeries(
                name="法术伤害", points=_sweep(inp, xs, set_res, sel),
                color="#9b59b6", unit=_u))
            for _hk, _hname in (("dph", "DPH"), ("dps", "DPS")):
                if _hk == kind:
                    continue
                _hsel = _total_hit if _hk == "dph" else _dps_of(interval)
                chart.hover_series.append(CurveSeries(
                    name=_hname, points=_sweep(inp, xs, set_res, _hsel),
                    unit=_hname, note="hover"))
            chart.desc = "法术：max(0.05A, 0.01 x A x max(0, 100 - 有效法抗))"
        else:
            _cur = sel(DMG.compute_damage(inp))
            _tname = C.DMG_TYPE_LABELS.get(_dt, "当前伤害")
            chart.series.append(CurveSeries(
                name="%s（与法术抗性无关）" % _tname,
                points=[(x, _cur) for x in xs],
                color="#7f8c99", unit=_u,
                note="法术抗性不影响该伤害类型"))
            chart.desc = ("该干员造成%s，法术抗性对它没有影响，所以曲线是"
                          "一条水平线。" % _tname)

    elif kind == "dmg_elem":
        hi = x_max or 100.0
        xs = _steps(0.0, hi, points)

        # 元素抗性只影响元素伤害。物理/法术干员（如能天使）的伤害与元素
        # 抗性完全无关，不能画一条随它下降的线——那会让人以为「堆高元素
        # 抗性就能减能天使的伤害」，明显不成立。
        is_elem = inp.damage_type == C.DMG_ELEMENTAL

        def set_el(i: DMG.DamageInput, v: float) -> None:
            i.damage_type = C.DMG_ELEMENTAL
            i.target_defense = v

        def set_el_keep(i: DMG.DamageInput, v: float) -> None:
            i.target_defense = v          # 只改面板上的抗性数值，不动伤害类型

        chart.title = "伤害 - 元素抗性"
        chart.x_label = "元素抗性"
        chart.x_unit = "元素"
        chart.y_label = "单次伤害"
        chart.y_unit = "伤害"

        if is_elem:
            chart.series.append(CurveSeries(
                name="元素伤害", points=_sweep(inp, xs, set_el, _per_hit),
                color="#16a085", unit="单次"))
            chart.desc = "元素：max(0.05A, 0.01 x A x max(0, 100 - 元素抗性))"
        else:
            # 非元素干员：画一条水平线，并说明真实关系
            cur = _per_hit(DMG.compute_damage(inp))
            tname = C.DMG_TYPE_LABELS.get(
                getattr(inp, "damage_type", ""), "当前伤害")
            chart.series.append(CurveSeries(
                name="%s（与元素抗性无关）" % tname,
                points=[(x, cur) for x in xs],
                color="#7f8c99", unit="单次",
                note="元素抗性不影响该伤害类型"))
            chart.desc = ("该干员造成%s，元素抗性对它没有影响，"
                          "所以曲线是一条水平线。只有把伤害类型切到"
                          "「元素伤害」后，才会看到随元素抗性下降的曲线。"
                          % tname)

    # ---------------- 攻击侧
    elif kind == "dmg_atk":
        hi = x_max or max(500.0, inp.attack * 3.0)
        xs = _steps(0.0, hi, points)

        def set_atk(i: DMG.DamageInput, v: float) -> None:
            i.attack = v

        chart.title = "伤害 - 攻击力"
        chart.x_label = "面板攻击力"
        chart.x_unit = "ATK"
        chart.y_label = "单次伤害"
        chart.y_unit = "伤害"
        chart.series.append(CurveSeries(
            name="当前抗性下", points=_sweep(inp, xs, set_atk, _per_hit),
            color="#4ea1f7", unit="单次"))
        chart.desc = "固定目标抗性，扫描攻击力"

    elif kind == "dmg_mult":
        hi = x_max or 5.0
        xs = _steps(0.0, hi, points)

        def set_mul(i: DMG.DamageInput, v: float) -> None:
            i.attack_multiplier = v

        chart.title = "伤害 - 攻击力倍率"
        chart.x_label = "攻击力倍率"
        chart.x_unit = "x"
        chart.y_label = "单次伤害"
        chart.y_unit = "伤害"
        chart.series.append(CurveSeries(
            name="当前抗性下", points=_sweep(inp, xs, set_mul, _per_hit),
            color="#e67e22", unit="单次"))
        chart.desc = "A = 攻击力 x 倍率 + 附加攻击力"

    elif kind == "dmg_pen":
        xs = _steps(0.0, 100.0, points)

        def set_pen(i: DMG.DamageInput, v: float) -> None:
            i.def_pen_percent = v / 100.0

        chart.title = "伤害 - 百分比穿透"
        chart.x_label = "百分比穿透"
        chart.x_unit = "%"
        chart.y_label = "单次伤害"
        chart.y_unit = "伤害"
        chart.series.append(CurveSeries(
            name="当前抗性下", points=_sweep(inp, xs, set_pen, _per_hit),
            color="#f1c40f", unit="单次"))
        chart.desc = "有效抗性 = (1 - 穿透) x max(0, 抗性 - 固定穿透)"

    elif kind == "dps_speed":
        xs = _steps(C.ATTACK_SPEED_MIN, C.ATTACK_SPEED_MAX, points)
        pts: List[Tuple[float, float]] = []
        r = DMG.compute_damage(inp)
        for s in xs:
            iv = DMG.effective_attack_interval(interval, s)
            pts.append((s, DMG.compute_dps(r.final_damage, iv, max(1, r.hit_count))))
        chart.title = "DPS - 攻速"
        chart.x_label = "攻击速度"
        chart.x_unit = "攻速"
        chart.y_label = "伤害 / 秒"
        chart.y_unit = "DPS"
        chart.series.append(CurveSeries(
            name="当前攻击力下", points=pts, color="#2ecc71", unit="DPS"))
        chart.desc = "实际间隔 T = T0 / (clamp(攻速, 10, 600) / 100)"

    else:
        raise ValueError("未知曲线类型: %s" % kind)

    return chart


# ------------------------------------------------------------------ 多干员对比

#: 最多同时对比几位（与 UI 的槽位数一致）
MAX_COMPARE = 5

COMPARE_COLORS = ["#4ea1f7", "#e74c3c", "#2ecc71", "#f1c40f", "#9b59b6",
                  "#1abc9c", "#e67e22", "#ecf0f1"]


def compare_chart(kind: str,
                  entries: Sequence[Tuple[str, DMG.DamageInput, float]],
                  *,
                  x_max: float = 0.0,
                  points: int = 121,
                  break_lines: Optional[Sequence[float]] = None,
                  overlay_min: bool = False,
                  marker_xs: Optional[Sequence[float]] = None) -> CurveChart:
    """多组参数画在同一张图上，每组一条线。

    entries     : (图例名, DamageInput, 攻击间隔) 列表，顺序即配色顺序
    break_lines : 与 entries 等长的破甲线；只取第一条非零的画竖线
    overlay_min : 是否附一条 5% 保底线（多条线时保底各不相同，故默认不画）
    marker_xs   : 要在图上打点的横坐标（各自当前抗性），用于标出对比位置
    """
    if not entries:
        return CurveChart(title="无数据")

    base = build_chart(kind, entries[0][1], entries[0][2], x_max=x_max,
                       points=points)
    chart = CurveChart(
        title=base.title, x_label=base.x_label, x_unit=base.x_unit,
        y_label=base.y_label, y_unit=base.y_unit, desc=base.desc,
    )

    chart.series.append(CurveSeries(
        name=entries[0][0], points=base.series[0].points,
        color=COMPARE_COLORS[0]))

    for i, (label, inp, iv) in enumerate(entries[1:], start=1):
        ch = build_chart(kind, inp, iv, x_max=x_max, points=points)
        chart.series.append(CurveSeries(
            name=label, points=ch.series[0].points,
            color=COMPARE_COLORS[i % len(COMPARE_COLORS)]))

    # 保底线只在单条曲线时不产生歧义
    if overlay_min and len(chart.series) == 1:
        for s in base.series[1:]:
            chart.series.append(s)

    # 破甲线：只标第一个非零的（5 条线各标一条会糊成一团）
    if break_lines:
        for b in break_lines:
            if b and b > 0:
                chart.marker_x = float(b)
                chart.marker_label = "破甲线"
                break

    if marker_xs:
        xs = [x for x in marker_xs if x is not None]
        if xs:
            chart.marker_xs = xs

    chart.desc = "%d 位干员对比：%s" % (len(entries), base.desc or base.title)
    return chart