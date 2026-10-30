# -*- coding: utf-8 -*-
"""生成 codex_fields.json 的 statemachines 段（状态机图鉴）。

设计依据见 docs/状态机图鉴_方案.md。这里只做**数据层**：把每个技能
的生命周期拆成状态与时长，UI 侧（ui/data_index.py）只负责画。

用法：python akcalc/tools/gen_codex_state.py
"""
import collections
import io
import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DATA = os.path.join(ROOT, "data")

#: spType 的中文解释。注意 "8" 是**整数**序列化后的字符串，不是拼写错误。
SPTYPE_CN = {
    "INCREASE_WITH_TIME": "自然回复（每秒 +increment）",
    "INCREASE_WHEN_ATTACK": "攻击回复（每次攻击 +increment）",
    "INCREASE_WHEN_TAKEN_DAMAGE": "受击回复（每次受击 +increment）",
    "8": "不回复（只能靠初始 SP / 外部充能）",
}

SKILLTYPE_CN = {
    "MANUAL": "手动触发（SP 满后点一下）",
    "AUTO": "自动触发（SP 满后立即开）",
    "PASSIVE": "被动常驻（没有 SP 循环）",
}


def last_level(sk):
    lv = sk.get("levels") or []
    return lv[-1] if lv else {}


def build_one(sid, sk, atk_interval=None):
    """把一个技能翻译成状态机描述。返回 None 表示不建模。

    ``atk_interval`` 是该干员的攻击间隔（秒）。攻击回复类技能靠它把
    「要打几次」换成「要多少秒」——没有它就只能报次数。受击回复类
    永远只能报次数，因为受击频率取决于敌人，不是干员的固有属性。
    """
    lv = last_level(sk)
    sd = lv.get("spData") or {}
    name = lv.get("name") or sid
    stype = str(lv.get("skillType") or "")
    spt = str(sd.get("spType"))
    cost = sd.get("spCost")
    init = sd.get("initSp")
    inc = sd.get("increment")
    charge = sd.get("maxChargeTime")
    durn = str(lv.get("durationType") or "NONE")
    dur = lv.get("duration")

    try:
        cost = float(cost) if cost is not None else 0.0
    except (TypeError, ValueError):
        cost = 0.0
    try:
        init = float(init) if init is not None else 0.0
    except (TypeError, ValueError):
        init = 0.0
    try:
        inc = float(inc) if inc is not None else 1.0
    except (TypeError, ValueError):
        inc = 1.0
    try:
        dur = float(dur) if dur is not None else 0.0
    except (TypeError, ValueError):
        dur = 0.0

    # 被动技能没有 SP 循环，不画状态机
    if stype == "PASSIVE":
        return None

    states = []
    # ---- 首次充能：从 initSp 起步
    first = max(0.0, cost - init)
    first_hits = first / inc if inc > 0 else 0.0
    # 攻击回复能换算成秒（干员攻击间隔固定）；受击回复不能（取决于挨打频率）
    atk_sec = None
    if (spt == "INCREASE_WHEN_ATTACK" and atk_interval and inc > 0):
        atk_sec = first / inc * float(atk_interval)
    if spt == "INCREASE_WITH_TIME" and inc > 0:
        first_t = "%.1f 秒" % (first / inc)
    elif atk_sec is not None:
        first_t = "%.1f 秒（%g 次攻击 × %.3f 秒）" % (
            atk_sec, first_hits, float(atk_interval))
    elif spt == "INCREASE_WHEN_ATTACK":
        first_t = "%g 次攻击" % first_hits
    elif spt == "INCREASE_WHEN_TAKEN_DAMAGE":
        first_t = "%g 次受击" % first_hits
    else:
        first_t = "约 %g 点 SP" % first
    states.append({"state": "CHARGING（首次）",
                   "duration": first_t,
                   "note": "spCost − initSp = %g − %g" % (cost, init)})

    # ---- 之后每轮充能
    cyc_hits = cost / inc if inc > 0 else 0.0
    cyc_sec = None
    if (spt == "INCREASE_WHEN_ATTACK" and atk_interval and inc > 0):
        cyc_sec = cost / inc * float(atk_interval)
    if spt == "INCREASE_WITH_TIME" and inc > 0:
        cyc_t = "%.1f 秒" % (cost / inc)
    elif cyc_sec is not None:
        cyc_t = "%.1f 秒（%g 次攻击 × %.3f 秒）" % (
            cyc_sec, cyc_hits, float(atk_interval))
    elif spt == "INCREASE_WHEN_ATTACK":
        cyc_t = "%g 次攻击" % cyc_hits
    elif spt == "INCREASE_WHEN_TAKEN_DAMAGE":
        cyc_t = "%g 次受击" % cyc_hits
    elif spt == "8":
        cyc_t = "不会自然填充"
    else:
        cyc_t = "%g 次触发" % cost
    states.append({"state": "CHARGING（循环）",
                   "duration": cyc_t,
                   "note": "每轮只按 spCost = %g 计" % cost})

    # ---- 可开启
    states.append({"state": "READY（可开启）",
                   "duration": "瞬时" if stype == "MANUAL" else "自动跳过",
                   "note": SKILLTYPE_CN.get(stype, stype)})

    # ---- 技能中
    if durn == "AMMO":
        act_t = "打完弹药为止"
        note = "durationType=AMMO，duration 无意义（常为 −1）"
    elif dur < 0:
        act_t = "无限（需手动关闭）"
        note = "duration = %g 表示无限" % dur
    elif dur == 0:
        act_t = "瞬时"
        note = "duration = 0，通常配合被动判定"
    else:
        act_t = "%.1f 秒" % dur
        note = "duration = %g" % dur
    states.append({"state": "ACTIVE（技能中）", "duration": act_t, "note": note})

    # ---- 冷却（与下次充能是同一状态）
    states.append({"state": "COOLDOWN → 下次 CHARGING",
                   "duration": "与循环充能同一段",
                   "note": "游戏里技能结束就直接从 0 攒，不存在独立冷却"})

    # ---- 稳态指标
    # 攻击回复能给出确定秒数（攻击间隔是干员固有属性）；受击回复给不出，
    # 因为挨打频率由敌人决定——这种情况下只报次数，不编秒数。
    metrics = {}
    charge_t = None
    if spt == "INCREASE_WITH_TIME" and inc > 0:
        charge_t = cost / inc
    elif spt == "INCREASE_WHEN_ATTACK" and atk_interval and inc > 0:
        charge_t = cost / inc * float(atk_interval)

    if charge_t is not None:
        # 瞬发技能（dur = 0）没有 ACTIVE 时长，但循环周期仍然等于充能时长
        metrics["首次可开启"] = "%.1f 秒" % (first / inc * (
            float(atk_interval) if spt == "INCREASE_WHEN_ATTACK" else 1.0))
        if dur > 0:
            metrics["循环周期"] = "%.1f 秒" % (charge_t + dur)
            cov = dur / (charge_t + dur) * 100.0
            metrics["稳态覆盖率"] = "%.1f%%（%g / (%g + %g)）" % (
                cov, dur, charge_t, dur)
        elif dur == 0:
            # 瞬发：没有 ACTIVE 时长，循环 = 充能 + 0
            metrics["循环周期"] = "%.1f 秒（每次充能后瞬发）" % charge_t
        else:
            # dur < 0 = 无限持续或弹药型，关不掉就谈不上循环
            metrics["循环周期"] = "%.1f 秒充能（技能持续到手动关闭）" % charge_t
    elif spt == "INCREASE_WHEN_ATTACK" and inc > 0:
        metrics["首次可开启"] = first_t
        if dur > 0 and atk_interval:
            metrics["说明"] = ("无攻击目标时不涨 SP；"
                               "上方秒数按不停攻击估算，是下限")
    elif spt == "INCREASE_WHEN_TAKEN_DAMAGE":
        metrics["首次可开启"] = first_t
        metrics["说明"] = "挨打频率由敌人决定，无法给出秒数"
    else:
        metrics["首次可开启"] = first_t

    if charge and float(charge or 0) > 1:
        metrics["可蓄力次数"] = "%g 次（需攒 %g × SP）" % (
            float(charge), float(charge))

    return {
        "name": name,
        "category": "状态机·干员技能生命周期",
        "kind": "技能状态机",
        "skill_id": sid,
        "desc": "%s；%s；%s" % (
            SKILLTYPE_CN.get(stype, stype),
            SPTYPE_CN.get(spt, spt),
            ("持续时间 %s" % act_t)),
        "states": states,
        "metrics": metrics,
        "data": "skill_table_full.json[%s].levels[-1] 的 spData / "
                "durationType / duration" % sid,
        "impl": "状态量全部来自解包数据：spType 决定怎么涨，spCost/initSp "
                "决定两段充能长度，durationType 优先于 duration 判断何时结束。",
        "pitfall": ("spType 为整数 8 时表示**不回复**，用 == \"...\" 判断会漏；"
                    "AMMO 技能的 duration 也是 −1，不能拿 duration 判时长。"),
    }


def _atk_interval_table():
    """char_id -> 攻击间隔（秒）。

    取**最高精英阶段、最高等级**的 ``attack_interval``。注意不能只看
    ``phases['2']``——克洛丝、史都华德这类只有精英 1 的干员没有该键，
    会全部漏掉。
    """
    p = os.path.join(DATA, "cache", "operators.json")
    try:
        ops = json.load(io.open(p, encoding="utf-8")).get("operators") or {}
    except (OSError, ValueError):
        return {}
    out = {}
    for _name, v in ops.items():
        cid = v.get("char_id")
        if not cid:
            continue
        ph = v.get("phases") or {}
        stages = [k for k in ph if str(k).isdigit()]
        if not stages:
            continue
        top = ph[max(stages, key=int)] or {}
        lvs = [k for k in top if str(k).isdigit()]
        if not lvs:
            continue
        ai = (top[max(lvs, key=int)] or {}).get("attack_interval")
        if ai:
            out[cid] = float(ai)
    return out


def _skill_owner_index():
    """skill_id -> char_id。

    ``skill_table_full`` 里没有 charKey，``operators.json`` 里也没有
    skill_id，两边只能用 ``skilldata.lookup()`` 按技能名握手（它能处理
    ``skcom_*`` 共用技能）。这里把结果反过来建成一张表。
    """
    try:
        sys.path.insert(0, os.path.dirname(os.path.dirname(HERE)))
        from akcalc.core import skilldata as SD
    except ImportError:
        return {}
    try:
        table = SD.load_full()
        ni = SD.build_name_index(table)
        p = os.path.join(DATA, "cache", "operators.json")
        ops = json.load(io.open(p, encoding="utf-8")).get("operators") or {}
    except (OSError, ValueError):
        return {}
    owner = {}
    for _name, v in ops.items():
        cid = v.get("char_id")
        if not cid:
            continue
        for sk in (v.get("skills") or []):
            nm = sk.get("name")
            if not nm:
                continue
            e = SD.lookup(table, ni, cid, nm, sk.get("index") or 1)
            sid = (e or {}).get("skillId")
            if sid and sid not in owner:
                owner[sid] = cid
    return owner


def main():
    p = os.path.join(DATA, "skill_table_full.json")
    d = json.load(io.open(p, encoding="utf-8"))
    ai_of = _atk_interval_table()
    owner = _skill_owner_index()
    out = []
    for sid, sk in d.items():
        ai = ai_of.get(owner.get(sid))
        r = build_one(sid, sk, ai)
        if r:
            out.append(r)
    # 保留三类可建模的：
    #   1) 自然回复 / 攻击回复：能算出秒数，有完整 SP 循环
    #   2) 受击回复：算不出秒数，但能报「要挨几次打」，对沙盘仍有意义
    # spType=8（不回复）且 spCost=0 的是被动技能，本来就没有 SP 循环，丢弃。
    def _keep(r):
        m = r["metrics"]
        return bool(m.get("循环周期") or m.get("稳态覆盖率")
                    or "次受击" in str(m.get("首次可开启") or ""))
    full = [r for r in out if _keep(r)]
    full.sort(key=lambda r: r["name"])

    cp = os.path.join(DATA, "codex_fields.json")
    cd = json.load(io.open(cp, encoding="utf-8"))
    cd["statemachines"] = full
    cd["stats"]["statemachines"] = len(full)
    json.dump(cd, io.open(cp, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("状态机条目 %d（可算稳态 %d / 总技能 %d） -> %s" % (
        len(out), len(full), len(d), cp))


if __name__ == "__main__":
    main()
