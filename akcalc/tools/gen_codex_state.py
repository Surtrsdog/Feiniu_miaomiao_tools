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


def build_one(sid, sk):
    """把一个技能翻译成状态机描述。返回 None 表示不建模。"""
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
    if spt == "INCREASE_WITH_TIME" and inc > 0:
        first_t = "%.1f 秒" % (first / inc)
    else:
        first_t = "约 %.1f 点 SP" % first
    states.append({"state": "CHARGING（首次）",
                   "duration": first_t,
                   "note": "spCost − initSp = %g − %g" % (cost, init)})

    # ---- 之后每轮充能
    if spt == "INCREASE_WITH_TIME" and inc > 0:
        cyc_t = "%.1f 秒" % (cost / inc)
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
    metrics = {}
    if spt == "INCREASE_WITH_TIME" and inc > 0 and dur > 0:
        metrics["首次可开启"] = "%.1f 秒" % (first / inc)
        metrics["循环周期"] = "%.1f 秒" % (cost / inc + dur)
        cov = dur / (cost / inc + dur) * 100.0
        metrics["稳态覆盖率"] = "%.1f%%（%g / (%g + %g)）" % (
            cov, dur, cost / inc, dur)
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


def main():
    p = os.path.join(DATA, "skill_table_full.json")
    d = json.load(io.open(p, encoding="utf-8"))
    out = []
    for sid, sk in d.items():
        r = build_one(sid, sk)
        if r:
            out.append(r)
    # 只保留有完整 SP 循环的（能算出实际秒数的），避免图鉴被
    # 「不回复」类技能淹没
    full = [r for r in out
            if r["metrics"].get("循环周期") or r["metrics"].get("稳态覆盖率")]
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
