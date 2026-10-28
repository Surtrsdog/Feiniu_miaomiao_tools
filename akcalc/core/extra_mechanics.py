# -*- coding: utf-8 -*-
"""额外机制图鉴数据：把「解包代码里能看到的机制」整理成可检索条目。

背景
----
干员/敌人的很多机制在游戏里以「技能 prefabKey + 黑板参数」的形式存在，
而不是一个显式的 ``token`` / ``summon`` 实体。图鉴 UI 只展示文字描述时，
玩家会问「陈的龙在哪里」「黑蛇转阶段火雨在代码里是什么」。

本模块只保存静态数据 + 两个纯函数，不在 import 时读任何大 JSON，
不依赖 tkinter。数据来源是解包仓库的原始 JSON（字段路径写在每个条目的
``source`` 里），由探针脚本核对过，``code`` 里存的是精简后的真实片段。

用法::

    from akcalc.core.extra_mechanics import mechanics_for, search_mechanics

    mechanics_for("enemy_1515_bsnake")   # 黑蛇
    mechanics_for("char_1050_chen3")     # 赤刃明霄陈
    search_mechanics("火雨")             # 模糊搜
"""
from __future__ import annotations

from typing import Dict, List

# ---------------------------------------------------------------------------
# 实体 id 别名：图鉴 UI 可能只拿到中文名或简称。
# ---------------------------------------------------------------------------
ENTITY_ALIASES: Dict[str, str] = {
    "enemy_1515_bsnake": "enemy_1515_bsnake",
    "黑蛇": "enemy_1515_bsnake",
    "不死的黑蛇": "enemy_1515_bsnake",
    "“不死的黑蛇”": "enemy_1515_bsnake",
    "char_1050_chen3": "char_1050_chen3",
    "赤刃明霄陈": "char_1050_chen3",
    "赤霄陈": "char_1050_chen3",
}


# ---------------------------------------------------------------------------
# 机制数据
# ---------------------------------------------------------------------------
# 数据源：Kengxxiao/ArknightsGameData（master 分支，zh_CN/gamedata）。
# 字段路径用 ``.`` 表示对象属性、``[i]`` 表示数组下标；
# 敌人库的 ``enemies[]`` 每个元素是 ``{Key: enemy_id, Value: [level 变体]}``。
# ---------------------------------------------------------------------------
MECHANICS: Dict[str, List[dict]] = {
    # =========================================================================
    # 黑蛇（“不死的黑蛇”）enemy_1515_bsnake
    # =========================================================================
    "enemy_1515_bsnake": [
        {
            "name": "转阶段火雨（不息恶火 / ScreenAttack）",
            "kind": "敌人",
            "entity_key": "enemy_1515_bsnake",
            "entity_name": "“不死的黑蛇”",
            "source": (
                "Kengxxiao/ArknightsGameData@master "
                "zh_CN/gamedata/levels/enemydata/enemy_database.json "
                "-> enemies[Key=enemy_1515_bsnake].Value[0].enemyData.skills[3]"
            ),
            "path": "enemyData.skills[3]",
            "code": {
                "prefabKey": "ScreenAttack",
                "priority": 1,
                "cooldown": 0.0,
                "initCooldown": 0.0,
                "spCost": 0,
                "blackboard": [
                    {"key": "atk_scale", "value": 1.0, "valueStr": None},
                    {"key": "duration", "value": 28.0, "valueStr": None},
                    {"key": "interval", "value": 2.0, "valueStr": None},
                    {"key": "trig_cnt", "value": 10.0, "valueStr": None},
                    {"key": "invincible", "value": 15.0, "valueStr": None},
                ],
            },
            "text": (
                "黑蛇的「火雨」在代码里是敌人技能表里的一个技能 prefabKey="
                "ScreenAttack：持续 28 秒、每 2 秒触发 1 次、共 10 次全屏打击"
                "（atk_scale=1.0，即每次 100% 攻击力），并带 15 秒无敌。"
                "handbook 里对应的描述是「生命值降至 0 时释放【不息恶火】"
                "对全场造成巨额法术伤害，并进入狂暴状态」；转阶段动作本身"
                "由引擎按 prefabKey 播放，火雨的具体弹道/特效不在 JSON 里。"
            ),
        },
        {
            "name": "召唤能量聚合体（SummonFlame + 关卡 branch）",
            "kind": "敌人",
            "entity_key": "enemy_1515_bsnake",
            "entity_name": "“不死的黑蛇”",
            "source": (
                "Kengxxiao/ArknightsGameData@master "
                "zh_CN/gamedata/levels/enemydata/enemy_database.json "
                "-> enemyData.skills[0]；"
                "zh_CN/gamedata/levels/obt/main/level_main_08-17.json "
                "-> branches.bsnake_flame 与 predefines.tokenInsts"
            ),
            "path": "enemyData.skills[0] + level.branches.bsnake_flame",
            "code": {
                "skill": {
                    "prefabKey": "SummonFlame",
                    "priority": 0,
                    "cooldown": 50.0,
                    "initCooldown": 75.0,
                    "spCost": 0,
                    "blackboard": [
                        {"key": "branch_id", "value": 0.0,
                         "valueStr": "bsnake_flame"},
                    ],
                },
                "level_branch": {
                    "branch_id": "bsnake_flame",
                    "actions": [
                        {"actionType": "ACTIVATE_PREDEFINED",
                         "key": "trap_021_flame#2"},
                        {"actionType": "ACTIVATE_PREDEFINED",
                         "key": "trap_021_flame#3"},
                    ],
                },
                "predefined_token": {
                    "characterKey": "trap_021_flame",
                    "hidden": True,
                },
            },
            "text": (
                "狂暴后「召唤能量聚合体」是敌人技能 + 关卡分支组合实现的："
                "敌人技能 SummonFlame 的黑板 branch_id=bsnake_flame，"
                "关卡文件 branches.bsnake_flame 里按波次 ACTIVATE_PREDEFINED "
                "预置的 trap_021_flame（隐藏 token），火圈位置由关卡覆盖的 "
                "talentBlackboard hint.location/hint.interval 给出。"
            ),
        },
        {
            "name": "烈焚灼息（DragonFire 点燃/引爆）",
            "kind": "敌人",
            "entity_key": "enemy_1515_bsnake",
            "entity_name": "“不死的黑蛇”",
            "source": (
                "Kengxxiao/ArknightsGameData@master "
                "zh_CN/gamedata/levels/enemydata/enemy_database.json "
                "-> enemyData.skills[1..2] 与 enemyData.talentBlackboard"
            ),
            "path": "enemyData.skills[1..2] + enemyData.talentBlackboard",
            "code": {
                "skills": [
                    {"prefabKey": "Ignite",
                     "blackboard": [
                         {"key": "dragon_fire.duration", "value": 30.5},
                         {"key": "dragon_fire.baseDamage", "value": 50.0},
                         {"key": "dragon_fire.addOnDamage", "value": 180.0},
                         {"key": "dragon_fire.addOnDuration", "value": 30.0},
                     ]},
                    {"prefabKey": "DragonFireExplode",
                     "blackboard": [
                         {"key": "atk_scale", "value": 1.0},
                         {"key": "dragon_fire.duration", "value": 30.5},
                         {"key": "dragon_fire.baseDamage", "value": 50.0},
                         {"key": "dragon_fire.addOnDamage", "value": 180.0},
                         {"key": "dragon_fire.addOnDuration", "value": 30.0},
                     ]},
                ],
                "talentBlackboard": [
                    {"key": "fire.attack@dragon_fire.duration",
                     "value": 30.5},
                    {"key": "fire.attack@dragon_fire.baseDamage",
                     "value": 50.0},
                    {"key": "fire.attack@dragon_fire.addOnDamage",
                     "value": 180.0},
                    {"key": "fire.attack@dragon_fire.addOnDuration",
                     "value": 30.0},
                ],
            },
            "text": (
                "【烈焚灼息】是一个叠在敌人技能与 talentBlackboard 上的 "
                "dot 效果：Ignite 给目标挂 dot（持续 30.5s、基础 50 真实伤害、"
                "每跳递增 180），DragonFireExplode 引爆并溅射；"
                "talentBlackboard 里 fire.attack@dragon_fire.* 说明这些参数"
                "还会被普攻附带的灼息复用。"
            ),
        },
    ],

    # =========================================================================
    # 赤刃明霄陈 char_1050_chen3
    # =========================================================================
    "char_1050_chen3": [
        {
            "name": "赤霄·天喟的龙形剑气（「龙」）",
            "kind": "干员",
            "entity_key": "char_1050_chen3",
            "entity_name": "赤刃明霄陈",
            "source": (
                "Kengxxiao/ArknightsGameData@master "
                "zh_CN/gamedata/excel/skill_table.json "
                "-> skchr_chen3_3.levels[0]；"
                "zh_CN/gamedata/excel/character_table.json "
                "-> char_1050_chen3.skills / displayTokenDict"
            ),
            "path": "skill_table.skchr_chen3_3.levels[0]",
            "code": {
                "skillId": "skchr_chen3_3",
                "name": "赤霄·天喟",
                "prefabId": "skchr_chen3_3",
                "rangeId": "3-12",
                "duration": 20.0,
                "blackboard": [
                    {"key": "hp_ratio", "value": 0.06, "valueStr": None},
                    {"key": "projectile_min_atk_scale", "value": 5.0,
                     "valueStr": None},
                    {"key": "attack@atk_scale", "value": 1.5,
                     "valueStr": None},
                    {"key": "attack@max_target", "value": 3.0,
                     "valueStr": None},
                ],
                "description": (
                    "技能开启时向前释放一道可转向的剑气，对穿过的敌人造成"
                    "相当于其当前生命值 6% 的法术伤害（至少造成自身攻击力 "
                    "500% 的法术伤害）；攻击范围扩大，每次攻击对最多 3 名"
                    "地面敌人造成 3 次攻击力 150% 的法术伤害"
                ),
            },
            "text": (
                "陈的「龙」不是召唤物：character_table.json 里 "
                "char_1050_chen3 的 displayTokenDict 为 null，三个技能的 "
                "overrideTokenKey 也全是 null，token_table.json 里没有 chen3 "
                "相关 token。龙的实体就是三技能「赤霄·天喟」的引擎特效/"
                "弹道，代码里只表现为 skill_table 的 prefabId=skchr_chen3_3"
                " + 黑板上的一串伤害参数；龙的外形由引擎按 prefabId 播放，"
                "解包 JSON 里不存在独立的「龙」实体。"
            ),
        },
        {
            "name": "形意洞照（弱点伤害）",
            "kind": "干员",
            "entity_key": "char_1050_chen3",
            "entity_name": "赤刃明霄陈",
            "source": (
                "Kengxxiao/ArknightsGameData@master "
                "zh_CN/gamedata/excel/character_table.json "
                "-> char_1050_chen3.talents[0].candidates[0]"
            ),
            "path": "character_table.char_1050_chen3.talents[0]",
            "code": {
                "prefabKey": "1",
                "name": "形意洞照",
                "blackboard": [
                    {"key": "atk", "value": 0.08, "valueStr": None},
                    {"key": "attack_speed", "value": 8.0, "valueStr": None},
                ],
                "description": "攻击力+8%，攻击速度+8，攻击变为弱点伤害",
            },
            "text": (
                "天赋「形意洞照」在代码里由 talent blackboard 驱动："
                "atk=0.08、attack_speed=8，并挂一个弱点伤害标记；"
                "图鉴文本「攻击力+8%，攻击速度+8，变为」在旧缓存里被截断，"
                "官方原文是「攻击变为弱点伤害」。"
            ),
        },
    ],
}


# ---------------------------------------------------------------------------
# 查询接口
# ---------------------------------------------------------------------------

def _resolve_key(entity_key: str) -> str:
    """把中文名/简称归一成实体 id。"""
    k = str(entity_key or "").strip()
    return ENTITY_ALIASES.get(k, k)


def mechanics_for(entity_key: str) -> List[dict]:
    """按敌人 id（``enemy_1515_bsnake``）或干员 id（``char_1050_chen3``）
    返回该实体的额外机制条目列表；未知实体返回空列表。

    也接受中文名/简称，例如 ``mechanics_for("黑蛇")``。

    注意：这里**只**返回人工精讲的静态条目。要拿到「静态 + 从本地解包
    现场推导」的完整列表，请用 ``all_mechanics_for``。
    """
    return list(MECHANICS.get(_resolve_key(entity_key), []))


def search_mechanics(kw: str) -> List[dict]:
    """按关键词模糊搜机制，覆盖 name / kind / source / text / entity 字段。"""
    needle = str(kw or "").strip().lower()
    out: List[dict] = []
    if not needle:
        return out
    for entity_key, entries in MECHANICS.items():
        for entry in entries:
            haystack = " ".join([
                str(entry.get("name") or ""),
                str(entry.get("kind") or ""),
                str(entry.get("entity_key") or entity_key),
                str(entry.get("entity_name") or ""),
                str(entry.get("source") or ""),
                str(entry.get("text") or ""),
            ]).lower()
            if needle in haystack:
                out.append(dict(entry))
    return out


# ===========================================================================
# 下面是**通用推导层**：静态表只能覆盖被点名问过的少数实体，而图鉴里
# 每个敌人/干员都该能查到「它这套机制在解包代码里长什么样」。
# 所以这里从本地解包缓存现场推导，不预先存 2186 条静态数据。
#
# 约束（与静态表一致）：
#   * import 时不读大 JSON——全部走惰性加载 + 模块级缓存；
#   * 不依赖 tkinter、不 import akcalc 里任何较重的模块；
#   * 任一环节异常都退化返回空列表，绝不让图鉴打不开。
# ===========================================================================

# prefabKey -> 一句话说明。键来自全库统计（739 种 prefabKey），
# 这里覆盖出现频次高、玩家最常问的那些；未登记的走通用兜底文案。
PREFAB_NOTES: Dict[str, str] = {
    "ScreenAttack": "全屏打击：按黑板 duration/interval/trig_cnt 定时对全场结算若干次",
    "SummonFlame": "召唤：按黑板 branch_id 走关卡 branches，激活预置好的 token",
    "Summon": "召唤：生成一个独立 token 实体，位置/数量由黑板参数决定",
    "summon": "召唤：生成一个独立 token 实体，位置/数量由黑板参数决定",
    "Ignite": "点燃：给目标挂持续伤害（dot），参数在 dragon_fire.* / fire.* 黑板键里",
    "DragonFireExplode": "点燃引爆：把已挂上的点燃层数一次性结算",
    "Reborning": "复活/转阶段：血量归零后按 reborn.* 参数重生并切换形态",
    "Charge": "冲锋：沿固定方向位移，撞到目标结算伤害",
    "ChargeAttack": "冲锋攻击：位移 + 撞击伤害组合",
    "Blink": "瞬移：直接改坐标，跳过路径寻路",
    "blink": "瞬移：直接改坐标，跳过路径寻路",
    "Boom": "爆炸：在目标点做范围结算",
    "boomb": "爆炸（延时）：先埋设再引爆",
    "Devour": "吞噬：直接把目标移除出战斗",
    "Eat": "进食：吞掉目标并获得增益",
    "Fly": "飞行：切换为空中单位，只受对空攻击影响",
    "StunAttack": "眩晕攻击：命中后施加眩晕，时长在黑板里",
    "Lasso": "拉拽：把目标拉向自己",
    "Doom": "厄运：条件触发的高额/即死结算",
    "Roar": "咆哮：以自身为中心的范围光环效果",
    "AOE": "范围攻击：对半径内全部目标结算",
    "MultiAttack": "多段攻击：一次攻击拆成多段命中",
    "CrossAttack": "十字攻击：按十字方向结算",
    "PowerAttack": "强力攻击：单次高倍率结算",
    "slapshot": "拍击：近身单次结算",
    "clearance": "清场：一次性清掉范围内单位",
    "Produce": "产出：定期生成资源/单位",
    "switch": "形态切换：换一套属性与技能表",
    "StartBattle": "开场触发：战斗开始时执行一次",
    "passtheball": "传球：把某个目标在单位之间传递",
    "Fire": "火焰：范围持续伤害",
    "bigAttack": "大范围攻击：超大半径结算",
    "switch": "形态切换：换一套属性与技能表",
    "Reborn": "复活：血量归零后重生",
}

# 黑板键 -> 中文标签。只用于把参数说人话，未登记的键原样保留。
_BB_CN: Dict[str, str] = {
    "atk_scale": "攻击倍率",
    "atk": "攻击倍率",
    "damage": "伤害",
    "duration": "持续秒",
    "interval": "间隔秒",
    "trig_cnt": "触发次数",
    "cooldown": "冷却秒",
    "initCooldown": "初始冷却",
    "spCost": "技力消耗",
    "prob": "概率",
    "max_target": "最大目标数",
    "attack_speed": "攻速",
    "move_speed": "移速",
    "invincible": "无敌秒",
    "branch_id": "分支 id",
    "hp_ratio": "生命比例",
    "reborn.max_hp": "重生生命比例",
    "reborn.duration": "重生耗时",
    "baseDamage": "基础伤害",
    "addOnDamage": "附加伤害",
    "addOnDuration": "附加持续",
    "range_radius": "作用半径",
}

_ED_CACHE: object = None
_OP_CACHE: object = None


def _cache_dir() -> str:
    """定位解包缓存目录。失败返回空串，调用方据此退化。"""
    try:
        import os
        here = os.path.dirname(os.path.abspath(__file__))
        return os.path.join(os.path.dirname(here), "data", "cache")
    except Exception:
        return ""


def _load_json(name: str):
    """惰性读取缓存 JSON；失败返回 None（绝不抛）。"""
    import json
    import os
    d = _cache_dir()
    if not d:
        return None
    p = os.path.join(d, name)
    if not os.path.exists(p):
        return None
    try:
        with open(p, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def _enemy_db() -> dict:
    """enemy_database.json 的 by_id（{enemy_id: [变体...]}）。"""
    global _ED_CACHE
    if _ED_CACHE is None:
        d = _load_json("enemy_database.json") or {}
        _ED_CACHE = d.get("by_id") or {}
    return _ED_CACHE if isinstance(_ED_CACHE, dict) else {}


def _operators() -> dict:
    """operators.json 的 operators（{显示名: 记录}）。"""
    global _OP_CACHE
    if _OP_CACHE is None:
        d = _load_json("operators.json") or {}
        _OP_CACHE = d.get("operators") or {}
    return _OP_CACHE if isinstance(_OP_CACHE, dict) else {}


def _pick_variant(variants):
    """优先取 level 0（基础形态），否则取第一个。"""
    if not isinstance(variants, list) or not variants:
        return None
    for v in variants:
        if isinstance(v, dict) and v.get("level") in (0, "0"):
            return v
    for v in variants:
        if isinstance(v, dict):
            return v
    return None


def _localized(x) -> str:
    """解包里的名字常是 {m_defined, m_value}，取人话。"""
    if isinstance(x, dict):
        return str(x.get("m_value") or x.get("m_defined") or "")
    return str(x or "")


def _bb_summary(bb) -> str:
    """把 [{key,value}] 黑板压成一行中文。"""
    if not isinstance(bb, list):
        return ""
    parts = []
    for it in bb:
        if not isinstance(it, dict):
            continue
        k = str(it.get("key") or "")
        if not k:
            continue
        v = it.get("value")
        if v is None:
            v = it.get("valueStr")
        if v is None:
            continue
        if isinstance(v, float) and abs(v - round(v)) < 1e-9:
            v = int(round(v))
        parts.append("%s %s" % (_BB_CN.get(k, k), v))
        if len(parts) >= 6:
            parts.append("…")
            break
    return " · ".join(parts)


def _slim_skill(sk: dict) -> dict:
    """技能条目只留看得懂的部分，别把整段 JSON 塞进 UI。"""
    out = {}
    for k in ("prefabKey", "priority", "cooldown", "initCooldown", "spCost"):
        if k in sk:
            out[k] = sk[k]
    bb = sk.get("blackboard")
    if bb:
        out["blackboard"] = [
            {"key": it.get("key"), "value": it.get("value"),
             "valueStr": it.get("valueStr")}
            for it in bb if isinstance(it, dict)
        ]
    return out


def _generic_text(prefab_key: str, bb_text: str) -> str:
    note = PREFAB_NOTES.get(prefab_key) or PREFAB_NOTES.get(
        prefab_key.lower() if isinstance(prefab_key, str) else "")
    if not note:
        note = ("该机制在解包里以「prefabKey + blackboard 参数」的形式存在，"
                "技能本体由引擎按 prefabKey 播放，JSON 里只有参数、没有特效资源。")
    if bb_text:
        return note + "　参数：" + bb_text
    return note


def derive_enemy(entity_key: str) -> List[dict]:
    """从本地敌人库现场推导某个敌人的代码级实现。"""
    out: List[dict] = []
    try:
        variants = _enemy_db().get(entity_key)
        var = _pick_variant(variants)
        if not var:
            return out
        ed = var.get("enemyData") or {}
        if not isinstance(ed, dict):
            return out
        name = _localized(ed.get("name")) or entity_key

        for i, sk in enumerate(ed.get("skills") or []):
            if not isinstance(sk, dict):
                continue
            pk = str(sk.get("prefabKey") or "")
            bb_text = _bb_summary(sk.get("blackboard"))
            out.append({
                "name": "技能 prefabKey「%s」" % (pk or "(空)"),
                "kind": "敌人",
                "entity_key": entity_key,
                "entity_name": name,
                "source": ("本地解包缓存 akcalc/data/cache/enemy_database.json"
                           " -> by_id[%s][level=%s].enemyData.skills[%d]"
                           % (entity_key, var.get("level"), i)),
                "path": "enemyData.skills[%d]" % i,
                "code": _slim_skill(sk),
                "text": _generic_text(pk, bb_text),
                "derived": True,
            })

        tb = ed.get("talentBlackboard")
        if tb:
            out.append({
                "name": "天赋黑板参数（talentBlackboard）",
                "kind": "敌人",
                "entity_key": entity_key,
                "entity_name": name,
                "source": ("本地解包缓存 akcalc/data/cache/enemy_database.json"
                           " -> by_id[%s][level=%s].enemyData.talentBlackboard"
                           % (entity_key, var.get("level"))),
                "path": "enemyData.talentBlackboard",
                "code": [
                    {"key": it.get("key"), "value": it.get("value"),
                     "valueStr": it.get("valueStr")}
                    for it in tb if isinstance(it, dict)
                ],
                "text": ("天赋不是一段文字，而是一组黑板键值，引擎按 key 读参数；"
                         "参数：" + (_bb_summary(tb) or "（空）")),
                "derived": True,
            })
    except Exception:
        return out
    return out


def _find_operator(entity_key: str):
    """按 char_id 或中文名找干员记录。"""
    ops = _operators()
    if not ops:
        return None, ""
    for disp, rec in ops.items():
        if not isinstance(rec, dict):
            continue
        if str(rec.get("char_id") or "") == entity_key or disp == entity_key:
            return rec, disp
    return None, ""


def derive_operator(entity_key: str) -> List[dict]:
    """从本地干员库现场推导某个干员的代码级实现。"""
    out: List[dict] = []
    try:
        rec, disp = _find_operator(entity_key)
        if not rec:
            return out
        cid = str(rec.get("char_id") or entity_key)
        name = str(rec.get("name") or disp or cid)

        for sk in (rec.get("skills") or []):
            if not isinstance(sk, dict):
                continue
            idx = sk.get("index")
            sn = str(sk.get("name") or "")
            levels = sk.get("levels") or {}
            lv1 = levels.get("1") if isinstance(levels, dict) else None
            code = {"index": idx, "name": sn,
                    "tree_type": sk.get("tree_type"),
                    "trigger_type": sk.get("trigger_type")}
            if isinstance(lv1, dict):
                for k in ("atk_multiplier", "flat_atk", "attack_speed",
                          "interval_delta", "dmg_scale", "hit_count",
                          "duration", "cost", "initial"):
                    if k in lv1:
                        code[k] = lv1[k]
            out.append({
                "name": "技能 %s「%s」" % (idx, sn),
                "kind": "干员",
                "entity_key": cid,
                "entity_name": name,
                "source": ("本地解包缓存 akcalc/data/cache/operators.json"
                           " -> operators[%s].skills[index=%s]" % (disp, idx)),
                "path": "operators.skills[index=%s]" % idx,
                "code": code,
                "text": ("技能在代码里是一张数值表（倍率/连击/持续/消耗），"
                         "以及若干 prefab/特效引用；具体演出由引擎按技能 id 播放。"),
                "derived": True,
            })

        for j, t in enumerate(rec.get("talents") or []):
            if isinstance(t, (list, tuple)) and len(t) >= 2:
                tn, td = str(t[0]), str(t[1])
            elif isinstance(t, dict):
                tn = str(t.get("name") or "")
                td = str(t.get("description") or "")
            else:
                continue
            out.append({
                "name": "天赋「%s」" % tn,
                "kind": "干员",
                "entity_key": cid,
                "entity_name": name,
                "source": ("本地解包缓存 akcalc/data/cache/operators.json"
                           " -> operators[%s].talents[%d]" % (disp, j)),
                "path": "operators.talents[%d]" % j,
                "code": {"name": tn, "description": td},
                "text": ("天赋在代码里是「名字 + 描述 + 一组黑板参数」，"
                         "描述里的数值由黑板键填充。"),
                "derived": True,
            })
    except Exception:
        return out
    return out


def all_mechanics_for(entity_key: str) -> List[dict]:
    """静态精讲 + 通用推导合并。图鉴 UI 应该调这个。

    静态条目在前（人写的、带 GitHub 字段路径），推导条目在后。
    同名条目只保留静态那份。
    """
    key = _resolve_key(entity_key)
    out = list(MECHANICS.get(key, []))
    seen = {str(e.get("name") or "") for e in out}
    for e in derive_enemy(key) + derive_operator(key):
        if str(e.get("name") or "") in seen:
            continue
        seen.add(str(e.get("name") or ""))
        out.append(e)
    return out


def has_mechanics(entity_key: str) -> bool:
    """图鉴用来决定要不要画这张卡，避免空卡片占地方。"""
    try:
        return bool(all_mechanics_for(entity_key))
    except Exception:
        return False

