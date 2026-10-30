"""MCP 工具：战斗计算。

提供 7 个与明日方舟伤害/攻速/DPS/击杀时间/技能回转/沙盘常量
相关的纯计算工具，全部无副作用，可直接被 AI 客户端调用。
"""
from __future__ import annotations

import math
from typing import Any, Dict, List

from .server import tool, ok, error


# ================================================================
#  1. 单次伤害计算
# ================================================================

_DMG_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "attack": {"type": "number", "description": "面板攻击力"},
        "damage_type": {
            "type": "string",
            "enum": ["PHYSICAL", "MAGICAL", "ELEMENTAL", "TRUE", "HEAL"],
            "description": "伤害类型",
        },
        "attack_multiplier": {"type": "number", "description": "攻击力倍率"},
        "flat_attack_bonus": {"type": "number", "description": "附加攻击力"},
        "target_defense": {"type": "number", "description": "目标防御/法抗/元素抗性"},
        "def_pen_flat": {"type": "number", "description": "固定穿透（物理）"},
        "def_pen_percent": {"type": "number", "description": "百分比穿透（物理，0~1）"},
        "res_pen_flat": {"type": "number", "description": "固定法穿"},
        "res_pen_percent": {"type": "number", "description": "百分比法穿（0~1）"},
        "def_down_percent": {"type": "number", "description": "减防百分比（0~1）"},
        "damage_boost": {"type": "number", "description": "增伤/易伤（0~1 表示百分比）"},
        "final_scaler": {"type": "number", "description": "最终伤害倍率"},
        "hit_count": {"type": "integer", "minimum": 1, "description": "连击次数"},
        "ignore_min_damage": {
            "type": "boolean",
            "description": "是否忽略 5% 保底",
        },
    },
    "required": ["attack"],
    "additionalProperties": False,
}


@tool(
    "battle_damage_calc",
    "单次伤害计算",
    "根据攻击力、伤害类型、穿透、增伤等参数计算单次攻击的最终伤害。"
    "返回基本伤害、有效抗性、最终伤害、总伤害、是否触发保底及详细步骤。",
    _DMG_SCHEMA,
)
def battle_damage_calc(args: dict) -> dict:
    """工具 1：单次伤害计算。"""
    from ..core.damage import DamageInput, compute_damage

    try:
        inp = DamageInput(
            attack=float(args["attack"]),
            damage_type=str(args.get("damage_type", "PHYSICAL")),
            attack_multiplier=float(args.get("attack_multiplier", 1.0)),
            flat_attack_bonus=float(args.get("flat_attack_bonus", 0.0)),
            target_defense=float(args.get("target_defense", 0.0)),
            def_pen_flat=float(args.get("def_pen_flat", 0.0)),
            def_pen_percent=float(args.get("def_pen_percent", 0.0)),
            res_pen_flat=float(args.get("res_pen_flat", 0.0)),
            res_pen_percent=float(args.get("res_pen_percent", 0.0)),
            def_down_percent=float(args.get("def_down_percent", 0.0)),
            damage_boost=float(args.get("damage_boost", 0.0)),
            final_scaler=float(args.get("final_scaler", 1.0)),
            hit_count=int(args.get("hit_count", 1)),
            ignore_min_damage=bool(args.get("ignore_min_damage", False)),
        )
    except (KeyError, TypeError, ValueError) as exc:
        return error("参数解析失败：%s" % exc)

    res = compute_damage(inp)
    return ok({
        "base_damage": round(res.base_damage, 3),
        "effective_resist": round(res.effective_resist, 3),
        "raw_damage": round(res.raw_damage, 3),
        "final_damage": round(res.final_damage, 3),
        "min_damage": round(res.min_damage, 3),
        "hit_count": res.hit_count,
        "total_damage": round(res.total_damage, 3),
        "floored": res.floored,
        "damage_type": res.damage_type,
        "penetration_note": res.penetration_note,
        "steps": res.steps,
    })


# ================================================================
#  2. 混伤计算
# ================================================================

_MIXED_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "attack": {"type": "number", "description": "面板攻击力"},
        "target_defense": {"type": "number", "description": "目标防御力"},
        "target_res": {"type": "number", "description": "目标法抗"},
        "target_eres": {"type": "number", "description": "目标元素抗性"},
        "damage_boost": {"type": "number", "description": "全局增伤"},
        "final_scaler": {"type": "number", "description": "全局最终倍率"},
        "components": {
            "type": "array",
            "description": "伤害分量列表",
            "items": {
                "type": "object",
                "properties": {
                    "damage_type": {
                        "type": "string",
                        "enum": ["PHYSICAL", "MAGICAL", "ELEMENTAL", "TRUE", "HEAL"],
                    },
                    "attack_multiplier": {"type": "number"},
                    "flat_attack_bonus": {"type": "number"},
                    "hit_count": {"type": "integer", "minimum": 1},
                    "def_pen_flat": {"type": "number"},
                    "def_pen_percent": {"type": "number"},
                    "def_down_percent": {"type": "number"},
                    "res_pen_flat": {"type": "number"},
                    "res_pen_percent": {"type": "number"},
                    "label": {"type": "string"},
                },
                "additionalProperties": False,
            },
        },
    },
    "required": ["attack", "components"],
    "additionalProperties": False,
}


@tool(
    "battle_mixed_damage",
    "混伤计算",
    "一次攻击包含多个伤害分量（如同时造成物理+法术伤害）时，"
    "按各分量的类型、倍率、穿透分别结算后汇总。"
    "返回每个分量的独立结果与合计 DPH / DPS。",
    _MIXED_SCHEMA,
)
def battle_mixed_damage(args: dict) -> dict:
    """工具 2：混伤（多分量）伤害计算。"""
    from ..core.damage import DamageComponent, MultiTypeInput, compute_multi

    raw_components = args.get("components")
    if not isinstance(raw_components, list) or not raw_components:
        return error("components 必须是非空数组")

    components: List[DamageComponent] = []
    for idx, c in enumerate(raw_components):
        if not isinstance(c, dict):
            return error("components[%d] 不是对象" % idx)
        try:
            components.append(DamageComponent(
                damage_type=str(c.get("damage_type", "PHYSICAL")),
                attack_multiplier=float(c.get("attack_multiplier", 1.0)),
                flat_attack_bonus=float(c.get("flat_attack_bonus", 0.0)),
                hit_count=int(c.get("hit_count", 1)),
                def_pen_flat=float(c.get("def_pen_flat", 0.0)),
                def_pen_percent=float(c.get("def_pen_percent", 0.0)),
                def_down_percent=float(c.get("def_down_percent", 0.0)),
                res_pen_flat=float(c.get("res_pen_flat", 0.0)),
                res_pen_percent=float(c.get("res_pen_percent", 0.0)),
                label=str(c.get("label", "")),
            ))
        except (TypeError, ValueError) as exc:
            return error("components[%d] 解析失败：%s" % (idx, exc))

    try:
        inp = MultiTypeInput(
            attack=float(args["attack"]),
            components=components,
            target_defense=float(args.get("target_defense", 0.0)),
            target_res=float(args.get("target_res", 0.0)),
            target_eres=float(args.get("target_eres", 0.0)),
            damage_boost=float(args.get("damage_boost", 0.0)),
            final_scaler=float(args.get("final_scaler", 1.0)),
        )
    except (KeyError, TypeError, ValueError) as exc:
        return error("顶层参数解析失败：%s" % exc)

    result = compute_multi(inp)
    # 把各分量结果序列化
    comp_results = []
    for r in result.results:
        comp_results.append({
            "damage_type": r.damage_type,
            "base_damage": round(r.base_damage, 3),
            "final_damage": round(r.final_damage, 3),
            "total_damage": round(r.total_damage, 3),
            "hit_count": r.hit_count,
            "floored": r.floored,
            "label": getattr(r, "label", ""),
            "steps": r.steps,
        })

    return ok({
        "final_damage": round(result.final_damage, 3),
        "total_damage": round(result.total_damage, 3),
        "per_type": {k: round(v, 3) for k, v in result.per_type().items()},
        "per_type_hit": {k: round(v, 3) for k, v in result.per_type_hit().items()},
        "component_count": len(result.results),
        "components": comp_results,
    })


# ================================================================
#  3. 攻速 → 有效攻击间隔
# ================================================================

_INTERVAL_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "base_interval": {
            "type": "number",
            "description": "基础攻击间隔（秒）",
        },
        "attack_speed": {
            "type": "number",
            "description": "攻速属性值（默认 100）",
        },
        "hit_count": {
            "type": "integer",
            "minimum": 1,
            "description": "每次攻击的hit数（默认 1）",
        },
    },
    "required": ["base_interval"],
    "additionalProperties": False,
}


@tool(
    "battle_attack_interval",
    "攻速换算有效攻击间隔",
    "根据基础攻击间隔和攻速属性，计算实际有效攻击间隔、"
    "每秒攻击次数、以及用于攻击回复技能的 SP 回复速率。",
    _INTERVAL_SCHEMA,
)
def battle_attack_interval(args: dict) -> dict:
    """工具 3：攻速 → 有效攻击间隔。"""
    from ..core.constants import ATTACK_SPEED_MIN, ATTACK_SPEED_MAX
    from ..core.damage import effective_attack_interval

    try:
        base_interval = float(args["base_interval"])
        if base_interval <= 0:
            return error("base_interval 必须大于 0")
    except (KeyError, TypeError, ValueError) as exc:
        return error("参数错误：%s" % exc)

    attack_speed = float(args.get("attack_speed", 100.0))
    hit_count = int(args.get("hit_count", 1))

    # 攻速 clamp 到 [10, 200]（与 effective_attack_interval 一致）
    clamped = max(ATTACK_SPEED_MIN, min(ATTACK_SPEED_MAX, attack_speed))
    eff = effective_attack_interval(base_interval, attack_speed)
    aps = 1.0 / eff if eff > 0 else 0.0
    sp_rate = aps  # 攻击回复：每秒回复量 = 每秒攻击次数

    return ok({
        "effective_interval": round(eff, 4),
        "attacks_per_second": round(aps, 4),
        "clamped_speed": clamped,
        "sp_rate_for_attack_recover": round(sp_rate, 4),
        "hit_count": hit_count,
    })


# ================================================================
#  4. 防御/抗性扫描曲线
# ================================================================

_CURVE_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "attack": {"type": "number", "description": "面板攻击力"},
        "damage_type": {
            "type": "string",
            "enum": ["PHYSICAL", "MAGICAL", "ELEMENTAL", "TRUE", "HEAL"],
        },
        "attack_multiplier": {"type": "number"},
        "base_interval": {
            "type": "number",
            "description": "攻击间隔（提供时额外计算 DPS）",
        },
        "attack_speed": {"type": "number", "description": "攻速（配合 base_interval 用）"},
        "def_pen_flat": {"type": "number"},
        "def_pen_percent": {"type": "number"},
        "resist_from": {"type": "number", "description": "扫描起始抗性（默认 0）"},
        "resist_to": {"type": "number", "description": "扫描结束抗性（默认 3000）"},
        "step": {"type": "number", "description": "扫描步长（默认 50）"},
    },
    "required": ["attack"],
    "additionalProperties": False,
}


@tool(
    "battle_dps_curve",
    "防御/抗性扫描曲线",
    "在给定抗性区间内逐点计算单次伤害，生成「抗性 → 伤害 → DPS」曲线。"
    "可用于找出破甲线或对比不同抗性下的输出表现。",
    _CURVE_SCHEMA,
)
def battle_dps_curve(args: dict) -> dict:
    """工具 4：防御/抗性扫描曲线 + 破甲线。"""
    from ..core.damage import (
        DamageInput, compute_damage, break_defense_threshold,
        effective_attack_interval,
    )

    try:
        attack = float(args["attack"])
    except (KeyError, TypeError, ValueError) as exc:
        return error("参数错误：%s" % exc)

    damage_type = str(args.get("damage_type", "PHYSICAL"))
    atk_mult = float(args.get("attack_multiplier", 1.0))
    def_pen_flat = float(args.get("def_pen_flat", 0.0))
    def_pen_pct = float(args.get("def_pen_percent", 0.0))
    resist_from = float(args.get("resist_from", 0.0))
    resist_to = float(args.get("resist_to", 3000.0))
    step = float(args.get("step", 50.0))

    if step <= 0:
        return error("step 必须大于 0")

    # 是否计算 DPS
    base_interval = args.get("base_interval")
    attack_speed = args.get("attack_speed")
    use_dps = base_interval is not None
    eff_interval = None
    if use_dps:
        try:
            base_interval_f = float(base_interval)
            spd = float(attack_speed) if attack_speed is not None else 100.0
            eff_interval = effective_attack_interval(base_interval_f, spd)
        except (TypeError, ValueError):
            use_dps = False

    points = []
    d = resist_from
    while d <= resist_to + 1e-9:
        inp = DamageInput(
            attack=attack,
            damage_type=damage_type,
            attack_multiplier=atk_mult,
            target_defense=d,
            def_pen_flat=def_pen_flat,
            def_pen_percent=def_pen_pct,
        )
        r = compute_damage(inp)
        pt: Dict[str, Any] = {
            "resist": round(d, 2),
            "damage": round(r.final_damage, 3),
        }
        if use_dps and eff_interval and eff_interval > 0:
            pt["dps"] = round(r.final_damage / eff_interval, 3)
        points.append(pt)
        d += step

    # 破甲线（仅对物理有意义）
    bdt = None
    if damage_type == "PHYSICAL":
        base_atk = attack * atk_mult
        bdt = round(break_defense_threshold(base_atk), 3)

    return ok({
        "points": points,
        "point_count": len(points),
        "break_defense_threshold": bdt,
        "damage_type": damage_type,
    })


# ================================================================
#  5. 击杀时间估算
# ================================================================

_KILL_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "target_hp": {"type": "number", "description": "目标生命值"},
        "damage_per_hit": {"type": "number", "description": "每次攻击造成的伤害"},
        "attack_interval": {"type": "number", "description": "攻击间隔（秒）"},
        "hit_count": {
            "type": "integer",
            "minimum": 1,
            "description": "每次攻击的hit数（影响 DPH）",
        },
    },
    "required": ["target_hp", "damage_per_hit", "attack_interval"],
    "additionalProperties": False,
}


@tool(
    "battle_kill_time",
    "击杀时间估算",
    "根据目标 HP、单次伤害和攻击间隔，估算所需命中次数、"
    "击杀时间、溢出伤害和 DPS。",
    _KILL_SCHEMA,
)
def battle_kill_time(args: dict) -> dict:
    """工具 5：击杀时间估算。"""
    import math

    try:
        target_hp = float(args["target_hp"])
        dph = float(args["damage_per_hit"])
        interval = float(args["attack_interval"])
        hit_count = int(args.get("hit_count", 1))
    except (KeyError, TypeError, ValueError) as exc:
        return error("参数错误：%s" % exc)

    if target_hp <= 0:
        return error("target_hp 必须大于 0")
    if dph <= 0:
        return error("damage_per_hit 必须大于 0")
    if interval <= 0:
        return error("attack_interval 必须大于 0")

    # 每次攻击的总伤害（含连击）
    total_dph = dph * max(1, hit_count)
    # 需要几次攻击（向上取整）
    hits_needed = math.ceil(target_hp / total_dph)
    # 击杀时间 = (hits - 1) * interval（第一刀在 t=0）
    kill_time = (hits_needed - 1) * interval
    # 溢出伤害
    overkill = hits_needed * total_dph - target_hp
    # DPS
    dps = total_dph / interval

    return ok({
        "hits_needed": hits_needed,
        "kill_time": round(kill_time, 4),
        "overkill_damage": round(overkill, 3),
        "dps": round(dps, 3),
        "damage_per_hit": dph,
        "total_dph": round(total_dph, 3),
        "target_hp": target_hp,
    })


# ================================================================
#  6. 技能 SP 回转模拟
# ================================================================

_SP_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "sp_cost": {"type": "number", "description": "技能 SP 消耗"},
        "duration": {"type": "number", "description": "技能持续时间（秒）"},
        "recover": {
            "type": "string",
            "enum": ["AUTO", "ATTACK", "DEFENSE", "NONE"],
            "description": "SP 回复类型",
        },
        "init_sp": {"type": "number", "description": "初始 SP"},
        "attack_interval": {
            "type": "number",
            "description": "攻击间隔（攻击回复时必填）",
        },
        "max_charge": {"type": "integer", "description": "可充能次数（默认 1）"},
        "sp_boost": {"type": "number", "description": "额外自然回复速率加成（点/秒）"},
        "recover_in_skill": {
            "type": "boolean",
            "description": "技能持续期间是否继续回 SP（默认自动判断）",
        },
        "end_time": {"type": "number", "description": "模拟结束时间（默认 180 秒）"},
        "at_time": {"type": "number", "description": "查询某时刻的状态"},
    },
    "required": ["sp_cost", "duration", "recover"],
    "additionalProperties": False,
}


@tool(
    "operator_sp_rotation",
    "技能 SP 回转模拟",
    "模拟指定技能在一段时间内的 SP 回转情况，返回各轮次的就绪/起止时间、"
    "总轮次、SP 回复速率，以及可选的某时刻状态快照。",
    _SP_SCHEMA,
)
def operator_sp_rotation(args: dict) -> dict:
    """工具 6：技能 SP 回转模拟。"""
    from ..core.sandbox_track import SkillCycle, SkillSim

    try:
        sp_cost = float(args["sp_cost"])
        duration = float(args["duration"])
        recover = str(args["recover"]).upper()
        init_sp = float(args.get("init_sp", 0.0))
        attack_interval = float(args.get("attack_interval", 1.0))
        max_charge = int(args.get("max_charge", 1))
        sp_boost = float(args.get("sp_boost", 0.0))
        end_time = float(args.get("end_time", 180.0))
        at_time = args.get("at_time")
    except (KeyError, TypeError, ValueError) as exc:
        return error("参数错误：%s" % exc)

    if sp_cost < 0:
        return error("sp_cost 不能为负")
    if duration < 0:
        return error("duration 不能为负")
    if attack_interval <= 0:
        return error("attack_interval 必须大于 0")
    if end_time <= 0:
        return error("end_time 必须大于 0")

    sk = SkillCycle(
        sp_cost=sp_cost,
        init_sp=init_sp,
        duration=duration,
        recover=recover,
        max_charge=max(max_charge, 1),
    )

    sim = SkillSim(attack_interval=attack_interval)

    # SP 回复速率
    rate = sim.sp_rate(sk, sp_boost)

    # 轮次列表
    cycles_list = sim.cycles(sk, end_time=end_time, boost=sp_boost)
    cycles_out = []
    for ready_at, active_from, active_to in cycles_list:
        cycles_out.append({
            "ready_at": round(ready_at, 4),
            "active_from": round(active_from, 4),
            "active_to": round(active_to, 4),
        })

    result: Dict[str, Any] = {
        "sp_rate": round(rate, 4),
        "sp_max": sk.sp_max,
        "cycles": cycles_out,
        "count": len(cycles_out),
    }

    # 可选：查询某时刻状态
    if at_time is not None:
        try:
            t = float(at_time)
            st = sim.state_at(sk, seconds=t, boost=sp_boost)
            result["state_at"] = {
                "time": t,
                "ready": st["ready"],
                "sp": round(st["sp"], 4),
                "need": st["need"],
                "active": st["active"],
                "next_in": round(st["next_in"], 4) if st["next_in"] is not None else None,
                "cycle_index": st["cycle_index"],
                "charges": st["charges"],
                "passive": st["passive"],
            }
        except (TypeError, ValueError) as exc:
            return error("at_time 解析失败：%s" % exc)

    return ok(result)


# ================================================================
#  7. 沙盘规格常量
# ================================================================

_SANDBOX_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "stage": {
            "type": "string",
            "description": "关卡 ID（可选，用于加载该关卡的选项）",
        },
        "include_constants": {
            "type": "boolean",
            "description": "是否包含通用常量（默认 true）",
        },
    },
    "additionalProperties": False,
}


@tool(
    "battle_sandbox_spec",
    "沙盘规格常量",
    "返回沙盘/战斗相关的核心常量：阻挡半径、碰撞体积、位移参数、"
    "DP 经济阈值、伤害保底系数等。可指定关卡 ID 获取该关选项。",
    _SANDBOX_SCHEMA,
)
def battle_sandbox_spec(args: dict) -> dict:
    """工具 7：沙盘规格常量查询。"""
    from ..core import constants as C
    from ..core.dp import REGEN_DISABLED_THRESHOLD

    include_constants = args.get("include_constants", True)
    stage_id = args.get("stage")  # 可选关卡 ID

    result: Dict[str, Any] = {}

    if include_constants:
        # ---- 阻挡常量 ----
        result["blocking"] = {
            "block_radius_ground": C.BLOCK_RADIUS_GROUND,
            "block_radius_ground_sq": C.BLOCK_RADIUS_GROUND_SQ,
            "block_radius_fly_coef": C.BLOCK_RADIUS_FLY_COEF,
            "block_radius_fly_sq_coef": C.BLOCK_RADIUS_FLY_SQ_COEF,
            "block_offset_radius": C.BLOCK_OFFSET_RADIUS,
            "center_epsilon": C.CENTER_EPSILON,
            "secondary_offset_check_radius": C.SECONDARY_OFFSET_CHECK_RADIUS,
            "secondary_offset_max": C.SECONDARY_OFFSET_MAX,
            "operator_collision_radius": C.OPERATOR_COLLISION_RADIUS,
            "avoid_force_min": C.AVOID_FORCE_MIN,
            "avoid_accel_coef": C.AVOID_ACCEL_COEF,
        }

        # ---- 移动常量 ----
        result["movement"] = {
            "move_multiplier_default": C.MOVE_MULTIPLIER_DEFAULT,
            "move_speed_min": C.MOVE_SPEED_MIN,
            "fps": C.FPS,
            "path_cost_obstacle": C.PATH_COST_OBSTACLE,
            "path_cost_hole": C.PATH_COST_HOLE,
        }

        # ---- 伤害常量 ----
        result["damage"] = {
            "min_damage_ratio": C.MIN_DAMAGE_RATIO,
            "element_ratio": C.ELEMENT_RATIO,
            "element_ratio_exact": C.ELEMENT_RATIO_EXACT,
            "resist_base": C.RESIST_BASE,
            "attack_speed_default": C.ATTACK_SPEED_DEFAULT,
            "attack_speed_min": C.ATTACK_SPEED_MIN,
            "attack_speed_max": C.ATTACK_SPEED_MAX,
            "attack_speed_hard_min": C.ATTACK_SPEED_HARD_MIN,
            "damage_types": {
                "physical": C.DMG_PHYSICAL,
                "magical": C.DMG_MAGICAL,
                "elemental": C.DMG_ELEMENTAL,
                "true": C.DMG_TRUE,
                "heal": C.DMG_HEAL,
            },
        }

        # ---- DP 经济常量 ----
        result["dp_economy"] = {
            "regen_disabled_threshold": REGEN_DISABLED_THRESHOLD,
        }

        # ---- 铁律（不可违反的游戏规则摘要）----
        result["iron_rules"] = [
            "真实伤害和治疗不吃任何抗性与穿透",
            "元素伤害不吃穿透，直接用元素抗性结算",
            "法术伤害用法抗结算，优先使用 res_pen_*（缺省回退 def_pen_*）",
            "物理伤害用防御力结算，减防只作用于物理",
            "所有伤害类型均有 5% 保底（MIN_DAMAGE_RATIO=0.05），除非显式忽略",
            "攻速 clamp 范围 [%d, %d]" % (C.ATTACK_SPEED_MIN, C.ATTACK_SPEED_MAX),
            "阻挡判定使用中点判定+平方距离比较",
            "SP 自然回复每秒 1 点，攻击回复每次攻击 1 点，受击回复沙盘按 0 处理",
            "可充能技能 SP 上限 = sp_cost × max_charge",
            "弹药技能持续时间 = ammo × attack_interval",
        ]

    # 如果指定了关卡，尝试加载该关卡选项（预留接口；
    # 实际关卡数据由 data 层提供，这里不做强依赖）
    if stage_id:
        result["stage"] = {
            "id": str(stage_id),
            "note": (
                "关卡特定选项需要数据层支持；此处仅回传请求的关卡 ID。"
                "请使用 tool_maps 获取关卡详细信息。"
            ),
        }

    return ok(result)
