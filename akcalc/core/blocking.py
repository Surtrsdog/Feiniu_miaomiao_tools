"""阻挡与阻挡偏移计算。

依据 PRTS「作战机制 - 碰撞体积与位置识别」：

* 干员碰撞体积为半径 0.25 格的圆。
* 阻挡走【中点判定】：比较坐标距离。
  地面阻挡半径 0.70709997（平方 0.49999037）
  飞行阻挡半径 0.8944 x 倍率（平方 0.79995137 x 倍率^2）
  判定使用【平方值】比较。
* 阻挡偏移：向已有敌人的格子空降干员时，敌人坐标被推到
  干员圆心为圆心、半径 0.5 的圆边界上，方向为「干员圆心 -> 敌人中心」的射线。
  敌人在方格正中心（敌我距离 < 0.00001）时不发生偏移。
* 多敌人被同一挡多干员阻挡时，若后阻挡者 0.1 半径内有更早阻挡的敌人，
  会产生不超过 0.2 距离、表现为旋转的偏移。
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import List, Optional, Sequence, Tuple

from . import constants as C

Point = Tuple[float, float]


# --------------------------------------------------------------- 坐标 helper

def tile_center(row: float, col: float) -> Point:
    """地块中心坐标。使用 (row, col) 浮点坐标系，中心为整数格。"""
    return (float(row), float(col))


def dist(a: Point, b: Point) -> float:
    return math.hypot(a[0] - b[0], a[1] - b[1])


def dist_sq(a: Point, b: Point) -> float:
    return (a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2


# --------------------------------------------------------------- 阻挡判定

def ground_block_radius_sq(radius_multiplier: float = 1.0) -> float:
    """地面阻挡半径平方。装置可覆写为固定值 0.49999037。"""
    return C.BLOCK_RADIUS_GROUND_SQ * (radius_multiplier ** 2)


def fly_block_radius_sq(radius_multiplier: float = 1.0) -> float:
    """飞行阻挡半径平方 = 0.79995137 x 倍率^2。"""
    return C.BLOCK_RADIUS_FLY_SQ_COEF * (radius_multiplier ** 2)


def is_blocked(operator_pos: Point, enemy_pos: Point,
               flying: bool = False, radius_multiplier: float = 1.0,
               override_sq: Optional[float] = None) -> bool:
    """敌人是否处于该干员的阻挡范围内（中点判定，用平方比较）。"""
    if override_sq is not None:
        threshold = override_sq
    elif flying:
        threshold = fly_block_radius_sq(radius_multiplier)
    else:
        threshold = ground_block_radius_sq(radius_multiplier)
    return dist_sq(operator_pos, enemy_pos) <= threshold


def block_distance(operator_pos: Point, enemy_pos: Point) -> float:
    """干员与敌人的实际距离（格）。"""
    return dist(operator_pos, enemy_pos)


# --------------------------------------------------------------- 阻挡偏移

@dataclass
class OffsetResult:
    """一次阻挡偏移的结果。"""

    moved: bool = False
    origin: Point = (0.0, 0.0)       # 偏移前敌人坐标
    final: Point = (0.0, 0.0)        # 偏移后敌人坐标
    distance: float = 0.0            # 实际位移量
    reason: str = ""


def apply_block_offset(operator_pos: Point,
                       enemy_pos: Point,
                       radius: float = C.BLOCK_OFFSET_RADIUS,
                       existing_blockers: Optional[Sequence[Point]] = None,
                       secondary_mode: str = "additional") -> OffsetResult:
    """计算空降干员时对已存在于该格的敌人造成的阻挡偏移。

    参数
    ----
    operator_pos: 干员圆心坐标（通常为格中心）
    enemy_pos:    敌人当前坐标
    radius:       偏移目标圆半径，默认 0.5
    existing_blockers: 同一干员已阻挡的其他敌人坐标，用于二次偏移
    secondary_mode:
        "additional" —— 二次偏移视为叠加在主偏移之上的额外旋转量，
                        额外位移上限 0.2（默认，更贴近原文「产生不超过 0.2
                        距离的、表现为旋转的阻挡偏移」的字面读法）
        "total"      —— 二次偏移后，相对原始坐标的总位移上限 0.2

    返回
    ----
    OffsetResult，含偏移前后的坐标。

    规则
    ----
    1. 若敌人在方格正中心（敌我距离 < 0.00001），不偏移。
    2. 否则沿「干员圆心 -> 敌人中心」射线，把敌人推到半径 0.5 的圆边界。
    3. 若存在更早被阻挡的敌人且其间距 < 0.1，则额外叠加
       不超过 0.2 的旋转（切向）偏移。

    备注
    ----
    第 3 条的「0.2」在 PRTS 原文中存在两种可能读法（额外量 / 总量），
    故此处以 secondary_mode 参数暴露，默认取 "additional"。
    """
    res = OffsetResult(origin=enemy_pos, final=enemy_pos)
    d = dist(operator_pos, enemy_pos)

    if d < C.CENTER_EPSILON:
        res.reason = "敌人在方格正中心（距离 < 0.00001），不发生阻挡偏移"
        return res

    # 单位方向向量：干员圆心 -> 敌人中心
    ux = (enemy_pos[0] - operator_pos[0]) / d
    uy = (enemy_pos[1] - operator_pos[1]) / d
    primary = (operator_pos[0] + ux * radius, operator_pos[1] + uy * radius)
    target = primary
    primary_dist = dist(enemy_pos, primary)

    note = ""
    if existing_blockers:
        for idx, b in enumerate(existing_blockers):
            gap = dist(primary, b)
            if gap >= C.SECONDARY_OFFSET_CHECK_RADIUS:
                continue
            # 需要推开到 0.1 之外
            need = C.SECONDARY_OFFSET_CHECK_RADIUS - gap
            if gap > 1e-9:
                vx, vy = (primary[0] - b[0]) / gap, (primary[1] - b[1]) / gap
            else:
                # 完全重合：取垂直于主方向的切向，表现为「旋转」
                vx, vy = -uy, ux
            cand = (primary[0] + vx * need, primary[1] + vy * need)

            extra = dist(primary, cand)
            if secondary_mode == "total":
                total = dist(enemy_pos, cand)
                if total > C.SECONDARY_OFFSET_MAX and total > 1e-12:
                    dx = (cand[0] - enemy_pos[0]) / total
                    dy = (cand[1] - enemy_pos[1]) / total
                    cand = (enemy_pos[0] + dx * C.SECONDARY_OFFSET_MAX,
                            enemy_pos[1] + dy * C.SECONDARY_OFFSET_MAX)
            else:  # additional
                if extra > C.SECONDARY_OFFSET_MAX and extra > 1e-12:
                    dx = (cand[0] - primary[0]) / extra
                    dy = (cand[1] - primary[1]) / extra
                    cand = (primary[0] + dx * C.SECONDARY_OFFSET_MAX,
                            primary[1] + dy * C.SECONDARY_OFFSET_MAX)

            note = (
                f"存在更早阻挡的敌人 #{idx + 1}（与主偏移点间距 {gap:.4f} < 0.1），"
                f"叠加旋转偏移 {dist(primary, cand):.4f}"
                f"（上限 0.2，模式 {secondary_mode}）"
            )
            target = cand
            break

    res.final = target
    res.moved = True
    res.distance = dist(enemy_pos, target)

    base = (f"沿「干员圆心 -> 敌人中心」射线推至半径 {radius:g} 圆边界，"
            f"主偏移 {primary_dist:.4f} 格，总位移 {res.distance:.4f} 格")
    res.reason = f"{base}；{note}" if note else base
    return res


def offset_preview(operator_pos: Point,
                   enemy_pos: Point,
                   steps: int = 12,
                   radius: float = C.BLOCK_OFFSET_RADIUS) -> List[Point]:
    """生成偏移过程中的采样点，供 UI 画射线动画。"""
    res = apply_block_offset(operator_pos, enemy_pos, radius=radius)
    if not res.moved:
        return [enemy_pos]
    pts = []
    for i in range(steps + 1):
        t = i / steps
        pts.append((
            enemy_pos[0] + (res.final[0] - enemy_pos[0]) * t,
            enemy_pos[1] + (res.final[1] - enemy_pos[1]) * t,
        ))
    return pts


# --------------------------------------------------------------- 多敌人分布

def distribute_on_circle(center: Point, count: int,
                         radius: float = C.BLOCK_OFFSET_RADIUS,
                         start_angle: float = 0.0) -> List[Point]:
    """把多个敌人均匀分布在阻挡圆上，用于预估挡多干员的占位。"""
    out = []
    for i in range(count):
        ang = start_angle + 2 * math.pi * i / max(1, count)
        out.append((center[0] + math.cos(ang) * radius,
                    center[1] + math.sin(ang) * radius))
    return out


# --------------------------------------------------------------- 行动受阻

def avoid_force(actual_speed: float, theoretical_speed: float) -> float:
    """避障力大小 = max(实际移速 / 理论移速, 0.5)。"""
    if theoretical_speed <= 0:
        return C.AVOID_FORCE_MIN
    return max(actual_speed / theoretical_speed, C.AVOID_FORCE_MIN)


def stalled_escape_speed(move_speed: float) -> float:
    """寻路断绝时，敌人离开当前格的匀速速度（格/秒）。

    避障力与寻路加速度 (目标移速 - 实际移速) * 8 平衡：
        0.5 = (0 - v) * 8  =>  v = 0.0625
    对移速 > 0.25 的敌人，该值为常数 0.0625。
    """
    force = C.AVOID_FORCE_MIN
    return force / C.AVOID_ACCEL_COEF