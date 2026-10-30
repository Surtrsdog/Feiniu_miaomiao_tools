# -*- coding: utf-8 -*-
"""给「查看原代码」弹窗用的**技能指令合成器**。

## 为什么需要这一层

`codex_fields.json` 的 ``tokens`` 能告诉你 ``atk_scale`` 是「攻击力倍率」，
但它回答不了用户真正问的那句：

    这个技能到底**按什么顺序做了哪几件事**？

「描述 JSON」和「具体指令」的差别就在这里。原始 ``blackboard`` 是一袋
无序的键值对，而技能在客户端里是一串动作：**先选目标 → 再生效 → 再结算
时长**。同一个 ``duration = 8``，在「自己加速 8 秒」和「让敌人眩晕 8 秒」
两种技能里含义完全不同——只看键值对永远分不出来。

所以本模块按 ``blackboard`` 的键名把参数归到「触发 / 目标 / 生效 / 时长 /
位移 / 召唤 / 投射物 / 资源」八个槽位，再用槽位合成一串**有序的动作描述**。
每个动作都注明它由哪个键推出（方括号里的键名），可逐条回溯到解包原文；
推不出的就明说推不出，不编造。

## 数据边界（必须说清）

解包只有 ``prefabKey``（客户端注册的行为类名）+ ``blackboard``（数值袋）。
真正的执行体（行为树 / 状态机）在客户端二进制里，**数据里不存在**。
所以这里给的是「从数值与键名反推出的动作序列」，而非官方脚本；
凡是由命名约定推断的地方都如实标出。敌人技能连
``codex_fields.json`` 的 ``statemachines`` 都没有（那里只收录干员技能），
这一点也要写出来，不能拿干员状态机去套。
"""
from __future__ import annotations

import re
from typing import Dict, List, Optional, Tuple

#: 键名 → (槽位, 中文谓词)。槽位决定合成顺序，谓词决定怎么念。
#:
#: 只收录**键名本身就说明了行为**的写法。像 ``value`` / ``cnt`` 这种
#: 脱离上下文毫无意义的键不收录——硬猜会把「留声机增益」说成「攻击」。
_ACTIONS: Dict[str, Tuple[str, str]] = {
    # ---- 伤害
    "atk_scale": ("effect", "造成攻击力 %s 倍的伤害"),
    "damage_scale": ("effect", "最终伤害再乘 %s"),
    "ep_damage_ratio": ("effect", "附带相当于伤害 %s 倍的元素损伤"),
    "damage": ("effect", "造成 %s 点伤害"),
    "true_damage": ("effect", "造成 %s 点真实伤害"),
    "hp_ratio": ("effect", "按目标最大生命 %s 倍结算"),
    # ---- 控制
    "stun": ("effect", "眩晕目标"),
    "block": ("effect", "阻挡数变为 %s"),
    "force": ("move", "以力度 %s 推开/拉近目标"),
    "dist": ("move", "位移距离 %s 格"),
    # ---- 自身增益
    "atk": ("effect", "攻击力修正 %s"),
    "attack_speed": ("effect", "攻击速度修正 %s"),
    "base_attack_time": ("effect", "攻击间隔改为 %s 秒"),
    "move_speed": ("effect", "移动速度倍率修正 %s"),
    "def": ("effect", "防御力修正 %s"),
    "magic_resistance": ("effect", "法术抗性修正 %s"),
    "damage_resistance": ("effect", "受到伤害减免 %s"),
    "invincible": ("effect", "进入无敌状态"),
    "block_cnt": ("effect", "阻挡数修正 %s"),
    # ---- 治疗
    "heal_scale": ("effect", "治疗量 = 攻击力 × %s"),
    # ---- 时长
    "duration": ("duration", "持续 %s 秒"),
    "hit_duration": ("duration", "命中判定窗口 %s 秒"),
    "interval": ("duration", "每 %s 秒一次"),
    # ---- 目标 / 范围
    "range_radius": ("target", "以自身为圆心半径 %s 格"),
    "max_target": ("target", "最多命中 %s 个目标"),
    "projectile_range": ("target", "投射物射程 %s"),
    "max_cnt": ("target", "数量上限 %s"),
    "times": ("target", "结算 %s 次"),
    # ---- 召唤 / 产出
    "enemy_key": ("summon", "召唤单位：%s"),
    "branch_id": ("summon", "走分支 %s"),
    "item_id": ("summon", "涉及道具 %s"),
    "item_count": ("summon", "数量 %s"),
    "produce_cost_item_id": ("summon", "消耗道具 %s"),
    "produce_cost_item_count": ("summon", "消耗数量 %s"),
    "respawn_time": ("summon", "重生所需 %s 秒"),
    "max_stack_cnt": ("summon", "最多叠 %s 层"),
    # ---- 投射物
    "projectile_life_time": ("projectile", "投射物存活 %s 秒"),
    "projectile_delay_time": ("projectile", "投射物延迟 %s 秒"),
    # ---- 技力
    "sp": ("resource", "技力变化 %s"),
}

#: 槽位的合成顺序 = 一个技能在客户端里的大致执行顺序。
_SLOT_ORDER: List[Tuple[str, str]] = [
    ("trigger", "触发条件"),
    ("target", "选取目标"),
    ("summon", "产生单位 / 资源"),
    ("projectile", "投射物"),
    ("effect", "结算效果"),
    ("move", "位移"),
    ("resource", "技力"),
    ("duration", "计时"),
]

#: ``prefabKey`` 尾部的形态标记。``Immo[Rage]`` = 同一个行为类的狂暴变体。
_FORM_RE = re.compile(r"^(?P<base>.+?)\[(?P<form>[^\]]+)\]$")

#: 已知的行为类名词典（小写匹配）。只收语义明确、且在解包里高频出现的，
#: 目的是让「slapshot → 拍击」这种一眼能懂；查不到就保留原名并注明。
_PREFAB_CN: Dict[str, str] = {
    "slapshot": "拍击（近身单体）",
    "clearance": "清场（范围清除）",
    "produce": "产出（生成道具 / 单位）",
    "powerattack": "重击（蓄力强攻）",
    "boom": "爆破（范围伤害）",
    "boomb": "连环爆破",
    "blink": "瞬移",
    "summon": "召唤",
    "switch": "形态切换",
    "reborning": "重生中",
    "reborn": "重生",
    "passtheball": "传递（把效果转给别的单位）",
    "charge": "冲锋",
    "devour": "吞噬",
    "eat": "进食",
    "startrun": "进入逃跑状态",
    "throw": "投掷",
    "throwspear": "掷矛",
    "immo": "点燃 / 灼烧",
    "dancefire": "舞焰（范围点燃）",
    "heal": "治疗",
    "shield": "护盾",
    "teleport": "传送",
    "snipe": "狙击",
    "bomb": "炸弹",
    "wave": "冲击波",
}


def _fmt(v) -> str:
    """数值转字符串：整数不带小数点，浮点最多留 4 位，None 留空。"""
    if v is None or v == "":
        return ""
    if isinstance(v, bool):
        return "是" if v else "否"
    if isinstance(v, float):
        if v == int(v):
            return str(int(v))
        return ("%.4f" % v).rstrip("0").rstrip(".")
    return str(v)


def parse_prefab(prefab: str) -> Tuple[str, str, str]:
    """拆开 ``prefabKey``：``(base, form, cn)``。

    ``Immo[Rage]`` -> ``('Immo', 'Rage', '点燃 / 灼烧')``。
    形态标记是**同一个行为类的不同阶段 / 变体**（狂暴、半血、重生），
    不拆开就会把 ``Immo`` 和 ``Immo[Rage]`` 当成两个无关技能。
    """
    raw = str(prefab or "").strip()
    if not raw:
        return ("", "", "")
    m = _FORM_RE.match(raw)
    base, form = (m.group("base"), m.group("form")) if m else (raw, "")
    cn = _PREFAB_CN.get(base.strip().lower(), "")
    return (base.strip(), form.strip(), cn)


def _action_of(key: str) -> Optional[Tuple[str, str]]:
    """查一个 blackboard key 属于哪个槽位、怎么念。

    先整键匹配，再退到「末段匹配」——``attack@atk_scale`` 这种带作用域
    前缀的写法，语义其实由末段决定。
    """
    k = str(key or "").strip()
    if not k:
        return None
    hit = _ACTIONS.get(k.lower())
    if hit:
        return hit
    if "@" in k:
        hit = _ACTIONS.get(k.rsplit("@", 1)[1].lower())
        if hit:
            return hit
    return None


def _to_f(v) -> Optional[float]:
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def build_instructions(code: dict,
                       tokens: Optional[Dict[str, dict]] = None,
                       *, trig_keys: str = "initCooldown / cooldown",
                       trig_word: str = "施放",
                       ) -> List[dict]:
    """把一个技能的 ``blackboard`` 合成**有序的指令序列**。

    返回 ``[{"seq": 1, "slot": "effect", "text": "...", "key": [...],
    "value": ..., "desc": ...}, ...]``。``key`` 保留原始键名，界面上每一条
    都能回溯到解包原文，不丢掉可核查性。

    ``trig_keys`` / ``trig_word`` 让调用方改写「触发」那一步的键名与动词：
    敌人侧是 ``initCooldown / cooldown``（冷却），干员侧是
    ``initSp / spCost``（技力）。同一套合成逻辑，两种口径必须标对，
    否则回溯到原文时会对不上号。
    """
    tokens = tokens or {}
    prefab = str((code or {}).get("key") or "")
    _base, _form, _cn = parse_prefab(prefab)

    # ---- 收集：键 -> 槽位
    slots: Dict[str, List[dict]] = {}
    for item in ((code or {}).get("blackboard") or []):
        if isinstance(item, dict):
            k = item.get("key")
            v = item.get("value")
            vs = item.get("valueStr")
        elif isinstance(item, (list, tuple)):
            k = item[0] if len(item) > 0 else None
            v = item[1] if len(item) > 1 else None
            vs = item[2] if len(item) > 2 else None
        else:
            continue
        k = str(k or "").strip()
        if not k:
            continue
        shown = _fmt(vs if vs not in (None, "") else v)
        act = _action_of(k)
        if act is None:
            continue
        slot, tpl = act
        if "%s" in tpl:
            try:
                text = tpl % shown
            except TypeError:
                text = tpl.replace("%s", shown)
        else:
            # 谓词不带占位符（如 stun / invincible）：把数值作补充说明，
            # 免得「眩晕目标」把关键的秒数藏掉了。
            text = tpl + (("（%s）" % shown) if shown else "")
        slots.setdefault(slot, []).append({
            "text": text, "key": k, "value": shown,
            "desc": str((tokens.get(k) or {}).get("desc") or ""),
        })

    # ---- 触发方式：由 cooldown / initCooldown（敌人）或 spCost / initSp（干员）推出
    # 两边的单位根本不同：敌人是**秒**（冷却计时），干员是**技力点数**
    # （击杀/自然回复累积）。同一个 15 在敌人身上是「第 15 秒」，
    # 在干员身上是「落地带 15 点技力」，混着说会误导。
    trig: List[dict] = []
    cd = _to_f(code.get("cooldown"))
    ini = _to_f(code.get("init"))
    spc = _to_f(code.get("sp_cost"))
    op_side = "spCost" in str(trig_keys)
    unit = "点技力" if op_side else "秒"
    if cd is not None and ini is not None:
        if cd >= 9999 and ini >= 9999:
            trig.append({
                "text": "常驻被动（%s 被标成 %s，等于不主动施放）" % (trig_keys, _fmt(cd)),
                "key": trig_keys,
                "value": "%s / %s" % (_fmt(ini), _fmt(cd)), "desc": ""})
        elif cd <= 0 and ini <= 0:
            # cooldown=0 说成「每 0 秒一次」是废话：它表示条件一满足就立刻
            # 生效，真正的触发条件在 prefabKey 的行为类里（例如 Devour 的
            # 「生命值低于阈值」）。这里只能如实说「无冷却」。
            trig.append({
                "text": "无冷却：条件一满足就立刻触发（触发条件本身在行为类里）",
                "key": trig_keys,
                "value": "%s / %s" % (_fmt(ini), _fmt(cd)), "desc": ""})
        else:
            if op_side:
                trig.append({
                    "text": "落地自带 %s 点技力，攒满 %s 点可%s，此后每轮重新攒 %s 点"
                            % (_fmt(ini), _fmt(cd), trig_word, _fmt(cd)),
                    "key": trig_keys,
                    "value": "%s / %s" % (_fmt(ini), _fmt(cd)), "desc": ""})
            else:
                trig.append({
                    "text": "开局第 %s 秒可首次%s，之后每 %s 秒一次"
                            % (_fmt(ini), trig_word, _fmt(cd)),
                    "key": trig_keys,
                    "value": "%s / %s" % (_fmt(ini), _fmt(cd)), "desc": ""})
    elif cd is not None:
        trig.append({"text": "每 %s %s%s一次" % (_fmt(cd), unit, trig_word),
                     "key": trig_keys, "value": _fmt(cd), "desc": ""})
    if spc:
        trig.append({"text": "施放另需 %s 点技力" % _fmt(spc),
                     "key": "spCost", "value": _fmt(spc), "desc": ""})
    if trig:
        slots["trigger"] = trig

    # ---- 合成：按槽位顺序展开
    out: List[dict] = []
    seq = 0
    for slot, _label in _SLOT_ORDER:
        for row in (slots.get(slot) or []):
            seq += 1
            out.append({"seq": seq, "slot": slot, "text": row["text"],
                        "key": row["key"], "value": row["value"],
                        "desc": row["desc"]})
    return out


def instruction_lines(insts: List[dict], *, head: str = "") -> List[str]:
    """把指令序列排成缩进文本（供代码查看器与「复制全部」用）。"""
    if not insts:
        return []
    out: List[str] = [head or "按解包数值反推的执行顺序（%d 步）："
                              % len(insts)]
    for it in insts:
        out.append("  %d. %s　[%s]" % (it["seq"], it["text"], it["key"]))
    return out


def prefab_meaning(prefab: str, *, is_skill_id: bool = False) -> str:
    """一行说明 prefabKey / prefabId 的含义（界面标题下的那行小字）。

    ``is_skill_id=True`` 时按干员技能口径解释：那里 ``prefabId`` 填的其实
    就是技能 ID（``skchr_xxx_1``）本身，不含行为类语义，只有 ``skillId``
    编号能说明「这是第几个技能」。分不清这两种口径会把 ``skchr_skadi2_3``
    当成一个查不到的行为类去报「词典未收录」，那是误导。
    """
    base, form, cn = parse_prefab(prefab)
    if not base:
        return "这条技能没有 prefabKey：解包只给了数值，连行为类名都没有。"
    if is_skill_id:
        tail = base.rsplit("_", 1)[-1]
        how = ("末段 _%s 表示技能序号（1/2/3 对应一/二/三技能）"
               % tail) if tail.isdigit() else ""
        return ("prefabId 填的是技能 ID 本身（%s），不是行为类名，"
                "解包没有给它任何语义标签；%s" % (base, how or "无可拆解的序号"))
    bits = []
    if cn:
        bits.append("行为类「%s」≈ %s" % (base, cn))
    else:
        bits.append("行为类「%s」（词典未收录，按原名保留）" % base)
    if form:
        bits.append("形态标记 [%s]：同一个行为类的变体 / 阶段" % form)
    return "；".join(bits)


__all__ = ["build_instructions", "instruction_lines", "parse_prefab",
           "prefab_meaning"]
