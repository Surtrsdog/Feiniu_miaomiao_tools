# -*- coding: utf-8 -*-
"""生成 stage_waves.json：全库出怪时间轴（精简，供 MCP 用）

为什么要在构建期抽出来
----------------------
「第 t 秒场上会出现什么」是少人课题的核心问题，但答案不在任何一张
现成表里：它要按 ``waves[].preDelay`` -> ``fragments[].preDelay`` ->
``actions[].preDelay / count / interval`` 一层层累加，还要读
``branches[]`` 里装置触发的条件出怪、认出 ``isValid=false`` 的废案、
``hiddenGroup`` 的互斥编队、``randomSpawnGroupKey`` 的随机候选包。

直接让外接 AI 读关卡 JSON 有两个问题：一是每关 JSON 100KB 量级、
全库 4010 个文件几百 MB；二是这套累加语义一旦理解错，时间轴整条错位
（不是少一点精度，是差一整段）。

所以这里在构建期把 4010 个关卡文件扫一遍，全部走
``akcalc.core.timeline.parse_timeline`` —— **和 GUI 沙盘同一个解析器**，
保证 MCP 报的时间轴和软件里看到的一模一样，不会两边各算一套。

输出格式（刻意压扁）
--------------------
每个关卡一份 ``{"code","name","cat","waves","dur","total","ids","spawns"}``：

* ``ids`` —— 本关敌人 id 池，``spawns`` 里用下标引用，省掉重复长字符串
* ``spawns`` —— 按 ``COLS`` 排列的数组，不用 dict 键名，体积约 1/4
* 第 10 列 ``[hidden_group, random_group, branch]`` 只在真有分组时才出现

一个 spawn 记录 = 一次「小队」出怪（即一个 SPAWN 动作），
``count`` 只、首只 ``t`` 秒、批内间隔 ``interval`` 秒。展开成逐只敌人
是 MCP 侧的事（``t + k * interval``），存的时候按批存省 40% 体积。
"""
import json
import os
import sys
import glob
import collections

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))          # F:\mini api
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from akcalc.core.timeline import parse_timeline          # noqa: E402

GR = r"F:\arknights_gamedata\ArknightsGameData"
GD = os.path.join(GR, "zh_CN", "gamedata")
CACHE = os.path.join(ROOT, "akcalc", "data", "cache", "levels")
CATALOG = os.path.join(ROOT, "akcalc", "data", "catalog.json")
OUT = os.path.join(ROOT, "akcalc", "data", "stage_waves.json")

#: spawn 数组的列序（MCP 侧按这个下标取，别凭印象）
COLS = ["t", "eid", "count", "interval", "route", "wave", "frag",
        "action", "flags", "groups"]
#: flags 位含义
FLAGS = {"1": "harmless", "2": "disabled", "4": "hidden_group",
         "8": "random_group", "16": "branch"}
_T_ROUND = 2


# --------------------------------------------------------------- 关卡索引

def _norm_rel(p):
    """catalog 里的 path 有两种前缀，统一成 levels/ 开头。"""
    p = str(p or "").replace("\\", "/")
    for pre in ("zh_CN/gamedata/", "zh_CN/"):
        if p.startswith(pre):
            p = p[len(pre):]
    return p


def _stem(p):
    b = os.path.splitext(os.path.basename(p))[0]
    return b[6:] if b.startswith("level_") else b


def _f(v):
    """宽容取浮点（preDelay 可能是 None / 缺省 / 字符串）。"""
    try:
        return float(v or 0.0)
    except (TypeError, ValueError):
        return 0.0


def catalog_index():
    """stage_id 与文件名 stem 都能查到的关卡记录（代号 / 中文名 / 分类）。"""
    out = {}
    try:
        with open(CATALOG, "r", encoding="utf-8") as f:
            cat = json.load(f)
    except (OSError, ValueError):
        return out
    for s in cat.get("stages") or []:
        sid = str(s.get("stage_id") or "")
        if not sid or "#" in sid:
            # 磨难/突袭变体和本体同一份地形与出怪，不单独占位
            continue
        out[sid] = s
        key = _stem(_norm_rel(s.get("path"))) if s.get("path") else ""
        if key and key not in out:
            out[key] = s
    return out


# --------------------------------------------------------------- 单关解析

def events_to_spawns(tl):
    """把 parse_timeline 的逐只事件折回「按小队」的 spawn 记录。

    必须折叠：一只 count=6 的源石虫小队占 6 条 event，存下来 6 倍冗余，
    而 MCP 侧本来就要按 ``t + k*interval`` 展开，折叠后不丢信息。
    """
    buckets = collections.OrderedDict()
    for e in tl.events:
        k = (e.branch, e.wave_index, e.fragment_index, e.action_index,
             e.route_index, e.enemy_id, e.harmless, e.disabled,
             e.hidden_group, e.random_group)
        buckets.setdefault(k, []).append(e)

    out = []
    for k, evs in buckets.items():
        (branch, wi, fi, ai, route, eid, harmless, disabled,
         hidden, random) = k
        evs.sort(key=lambda x: (x.time, x.seq))
        t0 = evs[0].time
        n = len(evs)
        interval = 0.0
        if n > 1:
            ds = sorted(round(evs[i + 1].time - evs[i].time, 3)
                        for i in range(n - 1))
            interval = ds[len(ds) // 2]
        flags = 0
        if harmless:
            flags |= 1
        if disabled:
            flags |= 2
        if hidden:
            flags |= 4
        if random:
            flags |= 8
        if branch:
            flags |= 16
        rec = [round(t0, _T_ROUND), eid, n, round(interval, 3),
               route, wi, fi, ai, flags]
        if flags & 28:                       # 4|8|16
            rec.append([hidden or "", random or "", branch or ""])
        out.append(rec)
    out.sort(key=lambda r: (r[0], r[4]))
    return out


def build_stage(raw, meta):
    tl = parse_timeline(raw)
    spawns = events_to_spawns(tl)

    ids, idx = [], {}
    for r in spawns:
        eid = r[1]
        if eid not in idx:
            idx[eid] = len(ids)
            ids.append(eid)
        r[1] = idx[eid]

    dur = 0.0
    total = 0
    for r in spawns:
        span = r[0] + max(0, r[2] - 1) * r[3]
        dur = max(dur, span)
        if not (r[8] & 2):                   # 不含废案
            total += r[2]

    rec = {
        "code": meta.get("code") or "",
        "name": meta.get("name") or "",
        "cat": meta.get("category") or "",
        "waves": len(raw.get("waves") or []),
        "dur": round(dur, 2),
        "total": total,
        "ids": ids,
        "spawns": spawns,
    }
    # 「模板波次」：出怪全被 isValid=false 标成未启用，实机由关卡脚本另发。
    # 原样保留（沙盘也是原样保留），但要标出来，别让 AI 当成真出怪。
    real = [r for r in spawns if not (r[8] & 2)]
    if spawns and not real:
        rec["tmpl"] = True
    # 整关的怪全在 branches[] 里（装置触发），waves 只有演出动作
    if spawns and all((r[8] & 16) for r in spawns):
        rec["branch_only"] = True
    return rec


# --------------------------------------------------------------- 主流程

def main():
    cat = catalog_index()
    files = sorted(glob.glob(os.path.join(GD, "levels", "**", "level_*.json"),
                             recursive=True))
    cached = set()
    if os.path.isdir(CACHE):
        cached = {os.path.splitext(n)[0] for n in os.listdir(CACHE)
                  if n.endswith(".json")}
    print("扫描 %d 个关卡文件 ..." % len(files))

    stages = {}
    n_err = 0
    n_spawn = 0
    for i, f in enumerate(files, 1):
        key = _stem(f)
        try:
            with open(f, "r", encoding="utf-8") as fh:
                raw = json.load(fh)
        except (OSError, ValueError) as e:
            n_err += 1
            print("  [跳过] %s: %s" % (key, e))
            continue
        try:
            rec = build_stage(raw, cat.get(key) or {})
        except Exception as e:                                  # noqa: BLE001
            n_err += 1
            print("  [解析失败] %s: %r" % (key, e))
            continue
        rec["cached"] = key in cached
        stages[key] = rec
        n_spawn += len(rec["spawns"])
        if i % 500 == 0:
            print("  %d/%d" % (i, len(files)))

    # catalog 里有些 stage_id 的文件名对不上（肉鸽换皮图：1033 个 id 只对应
    # 638 个文件），键没法直接命中时 MCP 还要能查——补一份别名表。
    alias = {}
    for s in cat.values():
        sid = str(s.get("stage_id") or "")
        rel = _stem(_norm_rel(s.get("path"))) if s.get("path") else ""
        if sid and rel and sid != rel and rel in stages and sid not in stages:
            alias[sid] = rel

    out = {
        "meta": {
            "source": "zh_CN/gamedata/levels/**/level_*.json",
            "generated_by": "akcalc/tools/gen_stage_waves.py",
            "stages": len(stages),
            "spawns": n_spawn,
            "errors": n_err,
            "cols": COLS,
            "flags": FLAGS,
            "t_note": ("t 是「开局后第几秒」（绝对时间），已按 "
                       "waves.preDelay + fragments.preDelay + "
                       "actions.preDelay 逐层累加，与 GUI 沙盘同一解析器。"
                       "branches[] 的条件出怪没有绝对时间轴，t 是「装置"
                       "激活后第几秒」（flags & 16 标出）。"),
            "unit_note": "count 只、首只 t 秒、批内间隔 interval 秒；"
                         "逐只时间 = t + k * interval。",
        },
        "alias": alias,
        "stages": stages,
    }
    tmp = OUT + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, separators=(",", ":"))
    os.replace(tmp, OUT)
    mb = os.path.getsize(OUT) / 1048576.0
    print("已写出 %s (%.2f MB)" % (OUT, mb))
    print("关卡 %d，出怪批次 %d，别名 %d，失败 %d"
          % (len(stages), n_spawn, len(alias), n_err))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())