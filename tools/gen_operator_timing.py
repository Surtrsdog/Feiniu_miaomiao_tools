# -*- coding: utf-8 -*-
"""生成 akcalc/data/operator_attack_timing.json。

数据源
------
``zh_CN/gamedata/bakemuzzledata/character/<charKey>_defaultskin.json``
（仓库 Kengxxiao/ArknightsGameData）。这 465 个文件合计 72MB，全是逐帧
``trsData`` 浮点数组，图鉴只用得到「动画第几秒触发 OnAttack」这一个数，
所以构建期解析成 45KB 的派生表随包分发。

用法
----
1. 把 465 个 ``*_defaultskin.json`` 放进 ``--src`` 目录（平铺即可）。
2. ``py tools/gen_operator_timing.py --src <目录>``
3. 默认写到 ``akcalc/data/operator_attack_timing.json``。

为什么不直接读原始文件
----------------------
单文件 10KB~2MB，运行时逐个解析会拖慢图鉴打开速度；而且派生表里
「无普攻」的归因（解放者/阵法术师/吟游者/傀儡师）需要结合
``operators.json`` 的子职业判断，不适合放在 UI 层做。

归因说明
--------
465 个干员里 17 个没有普攻类动画，**全部是机制如此，不是解析失败**：

- ``NO_ATTACK``  吟游者（空/浊心斯卡蒂/海蒂/U-Official/魔王/三角初华）
                 与处决者（THRM-EX），本来就不普攻
- ``SKILL_ONLY`` 解放者（玛恩纳/司霆惊蛰/骋风/龙舌兰）与阵法术师
                 （林/蜜蜡/薄绿/圣聆初雪/卡涅利安），普攻只在技能期间
- ``DOLL``       傀儡师（双月），普攻在召唤物 Doll_Attack_Loop 上
"""
from __future__ import annotations

import argparse
import collections
import json
import os
import re
import statistics as st
import sys

FPS = 30
SUFFIX = "_defaultskin.json"

#: 普攻动画名优先级。``Attack_Loop`` 要单独列出来——德克萨斯这类干员
#: 只有 ``Attack_Loop``（没有 ``Attack``），漏了就会误判成「无普攻」。
ATK_PRIO = ("Attack", "Attack_Loop", "Attack_A", "Attack_B", "Attack_1",
            "Attack_2", "Attack_3", "Attack_C", "Attack01", "Attack02",
            "Attack1", "Attack2", "Attack3", "Combat")


def events_of(group):
    """``bakedEvents`` -> ``{动画名: {"OnAttack": 秒, "OnStart": 秒}}``。"""
    out = {}
    for name, rec in (group.get("bakedEvents") or {}).items():
        evs = rec.get("events") or []
        ts = rec.get("eventTime") or []
        got = {}
        for i, ev in enumerate(evs):
            if i >= len(ts):
                continue
            e = str(ev).lower()
            if e == "onattack":
                got.setdefault("OnAttack", ts[i])
            elif e in ("onstart", "onstrat", "onsart"):
                # 解包里有拼错的 OnStrat / OnSart，都算登场
                got.setdefault("OnStart", ts[i])
        if got:
            out[name] = got
    return out


def pick_attack(ev):
    """挑普攻动画名；挑不到返回 None。"""
    for name in ATK_PRIO:
        if name in ev and "OnAttack" in ev[name]:
            return name
    for name in ev:
        if re.sub(r"[^a-z]", "", name.lower()).startswith(("attack", "combat")):
            if "OnAttack" in ev[name]:
                return name
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", required=True, help="放 *_defaultskin.json 的目录")
    ap.add_argument("--operators", default=None,
                    help="operators.json 路径，默认自动找 akcalc/data/cache/")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    ops_path = args.operators or os.path.join(
        root, "akcalc", "data", "cache", "operators.json")
    out_path = args.out or os.path.join(
        root, "akcalc", "data", "operator_attack_timing.json")

    byid = {}
    if os.path.isfile(ops_path):
        ops = json.load(open(ops_path, encoding="utf-8")).get("operators") or {}
        byid = {v["char_id"]: v for v in ops.values() if v.get("char_id")}
    else:
        print("[warn] 找不到 operators.json，子职业归因会退化为 NO_ATTACK",
              file=sys.stderr)

    files = sorted(f for f in os.listdir(args.src) if f.endswith(SUFFIX))
    if not files:
        raise SystemExit("目录里没有 *%s：%s" % (SUFFIX, args.src))

    by_char, reasons = {}, collections.Counter()
    for fn in files:
        key = fn[:-len(SUFFIX)]
        raw = json.load(open(os.path.join(args.src, fn), encoding="utf-8"))
        groups = {g: events_of(v)
                  for g, v in (raw.get("bakedAnimDatas") or {}).items()}
        rec = byid.get(key) or {}
        sub = rec.get("sub_profession") or ""
        ent = {}

        if not groups:
            ent["r"] = "NO_ANIM"
            reasons["NO_ANIM"] += 1
            by_char[key] = ent
            continue

        main_g = "Front" if "Front" in groups else sorted(groups)[0]
        ev = groups[main_g]

        for sname in ("Start", "Start_1", "Start_2", "Start_3", "Start_B"):
            if sname in ev and "OnStart" in ev[sname]:
                ent["s"] = ev[sname]["OnStart"]
                break

        ak = pick_attack(ev)
        if ak:
            ent["a"] = ev[ak]["OnAttack"]
            if ak != "Attack":
                ent["n"] = ak
            reasons["OK"] += 1
            # Front/Back 不一致：正面朝右、背面朝左是两套动画，抬手帧
            # 可能差一两帧。主值取 Front（图鉴默认姿势），差异另存。
            for gname in groups:
                if gname == main_g:
                    continue
                k2 = pick_attack(groups[gname])
                v2 = groups[gname][k2]["OnAttack"] if k2 else None
                if v2 is None or abs(v2 - ent["a"]) > 1e-4:
                    ent["fb"] = [ent["a"], v2]
                    break
        else:
            atk_names = [k for k in ev if "OnAttack" in ev[k]]
            doll = [k for k in atk_names if "doll" in k.lower()]
            if doll:
                ent["r"] = "DOLL"
                ent["d"] = ev[doll[0]]["OnAttack"]
            elif atk_names:
                ent["r"] = "SKILL_ONLY"
            else:
                ent["r"] = "NO_ATTACK"
            reasons[ent["r"]] += 1

        sk = {}
        for name, e in ev.items():
            if not name.lower().startswith("skill") or "OnAttack" not in e:
                continue
            m = re.search(r"[Ss]kill_?0*(\d)", name)
            sk[name] = [e["OnAttack"], int(m.group(1)) if m else None]
        if sk:
            ent["k"] = sk

        by_char[key] = ent

    vals = [e["a"] for e in by_char.values() if "a" in e]
    doc = {"meta": {
        "source": "zh_CN/gamedata/bakemuzzledata/character/<charKey>_defaultskin.json",
        "repo": "Kengxxiao/ArknightsGameData",
        "unit": "second", "fps": FPS, "fps_supported": [30, 60, 120],
        "schema_version": 2, "note_frames": "帧数 = round(秒 * 30)",
        "field_a": "普攻抬手秒数", "field_s": "登场秒数（OnStart）",
        "field_n": "非 Attack 时的实际普攻动画名",
        "field_k": "技能抬手 {动画名: [秒, 槽位号]}",
        "field_d": "傀儡师的召唤物普攻抬手",
        "field_r": "无普攻归因 NO_ATTACK / SKILL_ONLY / DOLL / NO_ANIM",
        "field_fb": "Front/Back 不一致时的 [前, 后]",
        "char_keys": len(by_char), "with_timing": len(vals),
        "coverage": round(len(vals) / len(by_char), 4) if by_char else 0,
        "no_attack": reasons["NO_ATTACK"],
        "skill_only": reasons["SKILL_ONLY"],
        "doll": reasons["DOLL"],
        "skills_collected": sum(len(e.get("k") or {}) for e in by_char.values()),
        "front_back_conflict": sum(1 for e in by_char.values() if "fb" in e),
        "distinct_windup": len({round(v, 6) for v in vals}),
        "min": min(vals) if vals else None,
        "max": max(vals) if vals else None,
        "mean": round(st.mean(vals), 6) if vals else None,
        "median": round(st.median(vals), 6) if vals else None,
        "errors": 0,
    }, "by_char": dict(sorted(by_char.items()))}

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(doc, fh, ensure_ascii=False, separators=(",", ":"))

    m = doc["meta"]
    print("写出 %s  (%.1f KB)" % (out_path,
                                  os.path.getsize(out_path) / 1024.0))
    print("  干员 %d，有抬手 %d（覆盖率 %.2f%%）"
          % (m["char_keys"], m["with_timing"], m["coverage"] * 100))
    print("  无普攻: 真没有 %d / 仅技能 %d / 召唤物 %d"
          % (m["no_attack"], m["skill_only"], m["doll"]))
    print("  技能抬手 %d 条，抬手值 %d 种，范围 %.4f~%.4f 秒"
          % (m["skills_collected"], m["distinct_windup"], m["min"], m["max"]))


if __name__ == "__main__":
    main()
