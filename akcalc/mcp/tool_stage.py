# -*- coding: utf-8 -*-
"""MCP 工具：关卡出怪时间轴（「第 t 秒场上有什么」）。

少人课题真正卡住的不是「这个敌人我打不打得动」，而是「第 t 秒场上会
出现什么、从哪条路线来、还剩多久到蓝门」。这条信息不在任何一张现成表里：

* 关卡 JSON 每关 100KB 量级，全库 4010 个文件几百 MB，外接 AI 读不动；
* 时间要按 ``waves[].preDelay`` -> ``fragments[].preDelay`` ->
  ``actions[].preDelay / count / interval`` 一层层累加，理解错一次整条
  时间轴就差一整段，不是差一点精度。

所以构建期用 ``akcalc/tools/gen_stage_waves.py`` 把全库扫一遍，走
``akcalc.core.timeline.parse_timeline``（**和 GUI 沙盘同一个解析器**），
压成 ``stage_waves.json``；本模块只做查询与展开。

## 时间口径

``t`` 是「开局后第几秒」，已含三层 preDelay 累加。实测 4-4 第一只源石虫
是 ``0 + 3 + 3 = 6`` 秒（wave / fragment / action 各一层），和软件里一致。

``branches[]`` 的条件出怪（装置 / 陷阱触发）**没有绝对时间轴**，``t`` 的
含义是「装置激活后第几秒」。本模块把这些记录标 ``branch``，并在
「第 t 秒场上有谁」里默认排除——它们的出场时刻取决于你怎么用装置，
算成开局计时会编出一条不存在的轴。

## 逐只展开

``spawns`` 一条 = 一次小队出怪：``count`` 只、首只 ``t`` 秒、批内间隔
``interval`` 秒，逐只时间 = ``t + k * interval``。

## 「还剩多久到蓝门」

到蓝门时刻 = 出场时刻 + 出场罚站（角兽系【休憩】）+ 该敌人**自己移速**
下的路线总耗时。这里不能对所有敌人套一个 ``move_speed``：源石虫 1.1、
无人机 0.8、大盾 0.85 各不相同，而 ``analyze_all`` 只吃一个全局速度。
所以要按 ``(route_index, speed)`` 逐个 ``analyze_route`` 重算——和沙盘
``Sandbox.rebuild_speed_cache`` 同一套做法。
"""
from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Optional, Tuple

from . import common
from .server import ok, error, tool

from . import tool_maps as TM

#: flags 位 -> 名字（与 stage_waves.json 的 meta.flags 一致）
_FLAG_BITS = ((1, "harmless"), (2, "disabled"), (4, "hidden_group"),
              (8, "random_group"), (16, "branch"))

#: 出场罚站字段名（角兽系【休憩】），见 core.enemies.spawn_unmovable_of
_WAIT_NOTE = "角兽系【休憩】时间内原地不动，到蓝门时刻要加上它"

_DATA: Optional[dict] = None
_DATA_PATH = ""
_NAMES: Optional[Dict[str, str]] = None
_CODE_INDEX: Optional[Dict[str, str]] = None


# ---------------------------------------------------------------- 数据加载

def _candidates(name: str) -> List[str]:
    """按优先级列出数据文件位置（可写目录 -> 包内 -> 源码目录）。"""
    out: List[str] = []
    try:
        p = common.paths()
    except Exception:                                        # noqa: BLE001
        p = None
    if p is not None:
        for d in (getattr(p, "data_dir", None),
                  getattr(p, "seed_data_dir", None)):
            if d:
                out.append(os.path.join(d, name))
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    out.append(os.path.join(here, "data", name))
    return out


def _load_json(name: str) -> Tuple[Any, str]:
    for p in _candidates(name):
        if p and os.path.isfile(p):
            try:
                with open(p, "r", encoding="utf-8") as f:
                    return json.load(f), p
            except (OSError, ValueError):
                continue
    return None, ""


def _waves() -> dict:
    """延迟加载 stage_waves.json（4.8MB，进程内缓存一次）。"""
    global _DATA, _DATA_PATH
    if _DATA is not None:
        return _DATA
    d, p = _load_json("stage_waves.json")
    _DATA = d if isinstance(d, dict) else {}
    _DATA_PATH = p
    return _DATA


def _names() -> Dict[str, str]:
    global _NAMES
    if _NAMES is None:
        d, _ = _load_json("enemy_names.json")
        _NAMES = d if isinstance(d, dict) else {}
    return _NAMES


def _code_index() -> Dict[str, str]:
    """代号（4-4）-> 关卡键。肉鸽换皮关的代号可能重复，先到先得。"""
    global _CODE_INDEX
    if _CODE_INDEX is None:
        idx: Dict[str, str] = {}
        for k, v in (_waves().get("stages") or {}).items():
            code = str((v or {}).get("code") or "").strip().lower()
            if code and code not in idx:
                idx[code] = k
        _CODE_INDEX = idx
    return _CODE_INDEX


def _stem(rel: str) -> str:
    b = os.path.splitext(os.path.basename(str(rel or "")))[0]
    return b[6:] if b.startswith("level_") else b


# ---------------------------------------------------------------- 关卡解析

def _find_stage(level: str) -> Optional[dict]:
    return TM._find_stage(level)


def _resolve(level: str) -> Tuple[Optional[dict], Optional[str], Optional[dict]]:
    """关卡名 -> (catalog 记录, stage_waves 键, stage_waves 记录)。

    查找顺序：stage_id -> 肉鸽别名 -> 文件名 stem -> 代号。代号兜底是必需
    的：``4-4`` 这种写法在 catalog 里是 ``code`` 字段，而 stage_waves.json
    的键是文件名 stem（``main_04-04``）。
    """
    data = _waves()
    stages = data.get("stages") or {}
    alias = data.get("alias") or {}
    q = str(level or "").strip()
    if not q:
        return None, None, None
    stage = _find_stage(q)
    keys: List[str] = []
    if stage:
        sid = str(stage.get("stage_id") or "")
        for k in (sid, alias.get(sid), _stem(stage.get("path") or "")):
            if k:
                keys.append(k)
    for k in (q, alias.get(q)):
        if k:
            keys.append(k)
    for k in keys:
        if k in stages:
            return stage, k, stages[k]
    code = str((stage or {}).get("code") or q).strip().lower()
    hit = _code_index().get(code)
    if hit:
        return stage, hit, stages.get(hit)
    return stage, None, None


def _load_raw(stage: Optional[dict], key: Optional[str]) -> Optional[dict]:
    """读缓存里的关卡原始 JSON（LevelCache 的键是 rel_path 去后缀）。

    不能省：``enemyDbRefs`` 里有本关的 ``overwrittenData``（4-4 的源石虫
    血量 1650 -> 2200 就在这里），敌人库本身是**基础值**。另外敌人的
    ``level`` 变体也只在 refs 里。
    """
    from ..core import maps as M
    lc = M.LevelCache(TM._cache_root())
    cands: List[str] = []
    if stage:
        path = str(stage.get("path") or "")
        sid = str(stage.get("stage_id") or "")
        if path:
            cands.append(path[:-5] if path.endswith(".json") else path)
        if sid:
            cands.append(sid)
            cands.append(sid.split("#", 1)[0])
    if key:
        cands.append(key)
    for k in cands:
        if not k:
            continue
        raw = lc.load(k)
        if isinstance(raw, dict):
            return raw
    return None


def _load_map(stage: Optional[dict], raw: Optional[dict]):
    from ..core import maps as M
    if raw is None:
        return None
    sid = str((stage or {}).get("stage_id") or "")
    try:
        return M.parse_level(raw, sid)
    except Exception:                                        # noqa: BLE001
        return None


# ---------------------------------------------------------------- spawn 展开

def _records(rec: dict) -> List[dict]:
    """把压缩的 spawns 行还原成带字段名的记录（9 列 / 10 列都认）。"""
    ids = rec.get("ids") or []
    names = _names()
    out: List[dict] = []
    for r in rec.get("spawns") or []:
        if not isinstance(r, list) or len(r) < 9:
            continue
        try:
            t = float(r[0])
            eidx = int(r[1])
            count = int(r[2])
            interval = float(r[3])
            route = int(r[4])
            wave = int(r[5])
            frag = int(r[6])
            act = int(r[7])
            flags = int(r[8] or 0)
        except (TypeError, ValueError):
            continue
        eid = ids[eidx] if 0 <= eidx < len(ids) else str(eidx)
        item: Dict[str, Any] = {
            "t": round(t, 2),
            "enemy_id": eid,
            "enemy": names.get(eid, eid),
            "count": count,
            "interval": round(interval, 3),
            "route": route,
            "wave": wave,
            "frag": frag,
            "act": act,
        }
        if flags:
            item["flags"] = [n for b, n in _FLAG_BITS if flags & b]
        if len(r) > 9 and isinstance(r[9], list):
            grp = (list(r[9]) + ["", "", ""])[:3]
            if grp[0]:
                item["hidden_group"] = grp[0]
            if grp[1]:
                item["random_group"] = grp[1]
            if grp[2]:
                item["branch"] = grp[2]
        out.append(item)
    return out


def _flag(item: dict, name: str) -> bool:
    return name in (item.get("flags") or ())


def _effective(recs: List[dict]) -> Tuple[List[dict], Dict[str, Any]]:
    """实机真正会出的那批：剔废案 + 互斥编队只留一组。

    和 ``Timeline.effective_events`` 同语义（组内只数最多的那组 = 常规
    编队）。随机候选包这里**不折叠**，但把包名留给调用方看——折叠会
    藏掉备选，少人课题有时正需要知道「这波是 N 选 1」。
    """
    total0 = len(recs)
    alive = [r for r in recs if not _flag(r, "disabled")]
    groups: Dict[str, int] = {}
    for r in alive:
        g = r.get("hidden_group")
        if g:
            groups[g] = groups.get(g, 0) + int(r.get("count") or 0)
    pick = ""
    if groups:
        pick = max(groups.items(), key=lambda kv: (kv[1], kv[0]))[0]
    out = [r for r in alive
           if not r.get("hidden_group") or r.get("hidden_group") == pick]
    info = {
        "dropped_disabled": total0 - len(alive),
        "hidden_groups": groups,
        "hidden_group_picked": pick or None,
        "dropped_hidden": len(alive) - len(out),
        "random_groups": sorted({r["random_group"] for r in out
                                 if r.get("random_group")}),
    }
    return out, info


# ---------------------------------------------------------------- 敌人数值

class _EnemyInfo:
    """本关敌人的等级 / 覆盖 / 移速（带缓存的薄封装）。

    ``overwrittenData`` 必须应用：4-4 的源石虫基础 1650 血，本关写 2200；
    爱国者系同理。移速也可能被覆盖，所以「到蓝门」的时间要拿覆盖后的值。
    """

    def __init__(self, raw: Optional[dict]):
        self.meta: Dict[str, dict] = {}
        for ref in ((raw or {}).get("enemyDbRefs") or []):
            eid = ref.get("id")
            if not eid or eid in self.meta:
                continue
            try:
                lv = int(ref.get("level") or 0)
            except (TypeError, ValueError):
                lv = 0
            self.meta[eid] = {"level": lv,
                              "override": ref.get("overwrittenData")}
        self._stats: Dict[str, Any] = {}
        self.lib = common.enemy_lib()

    def stats(self, eid: str):
        if eid in self._stats:
            return self._stats[eid]
        st = None
        if getattr(self.lib, "loaded", False):
            info = self.meta.get(eid) or {}
            try:
                st = self.lib.stats(eid, info.get("level", 0),
                                    info.get("override"))
            except Exception:                                # noqa: BLE001
                st = None
        self._stats[eid] = st
        return st

    def speed(self, eid: str) -> float:
        st = self.stats(eid)
        try:
            v = float(getattr(st, "move_speed", 0) or 0)
        except (TypeError, ValueError):
            v = 0.0
        return v if v > 0 else 1.0

    def wait(self, eid: str) -> float:
        st = self.stats(eid)
        try:
            return max(0.0, float(getattr(st, "spawn_unmovable", 0) or 0))
        except (TypeError, ValueError):
            return 0.0


class _Routes:
    """按 ``(route_index, 移速)`` 缓存路线分析（不同敌人移速不同）。"""

    def __init__(self, gm):
        self.gm = gm
        try:
            self.blocked = gm.route_blocking_cells() or None
        except Exception:                                    # noqa: BLE001
            self.blocked = None
        self._cache: Dict[Tuple[int, float], Any] = {}

    def get(self, route_index: int, speed: float):
        from ..core import routes as R
        key = (int(route_index), round(float(speed), 4))
        if key in self._cache:
            return self._cache[key]
        ra = None
        route = self.gm.route_by_index(key[0])
        if route is not None:
            try:
                ra = R.analyze_route(self.gm, route, move_speed=key[1],
                                     blocked=self.blocked)
            except Exception:                                # noqa: BLE001
                ra = None
            if ra is not None and not getattr(ra, "reachable", True):
                ra = None
        self._cache[key] = ra
        return ra


def _units(recs: List[dict], routes: Optional[_Routes],
           einfo: _EnemyInfo) -> List[dict]:
    """把「按批」的 spawn 展开成逐只，附带移速 / 罚站 / 到蓝门耗时。"""
    out: List[dict] = []
    for r in recs:
        cnt = max(1, int(r.get("count") or 1))
        step = float(r.get("interval") or 0.0)
        eid = r["enemy_id"]
        speed = einfo.speed(eid)
        wait = einfo.wait(eid)
        ra = routes.get(int(r["route"]), speed) if routes else None
        travel = float(getattr(ra, "total_time", 0.0) or 0.0) if ra else None
        for k in range(cnt):
            out.append({
                "t": r["t"] + k * step,
                "rec": r,
                "speed": speed,
                "wait": wait,
                "travel": travel,
                "ra": ra,
                "to_goal": (travel + wait) if travel is not None else None,
            })
    out.sort(key=lambda u: (u["t"], u["rec"]["route"]))
    return out


def _stage_brief(stage: Optional[dict], key: Optional[str],
                 rec: dict) -> Dict[str, Any]:
    d: Dict[str, Any] = {
        "stage_id": (stage or {}).get("stage_id") or key,
        "code": rec.get("code") or (stage or {}).get("code"),
        "name": rec.get("name") or (stage or {}).get("name"),
        "category": rec.get("cat") or (stage or {}).get("category"),
    }
    if rec.get("tmpl"):
        d["tmpl"] = True
    if rec.get("branch_only"):
        d["branch_only"] = True
    return d


def _no_data_hint(q: str) -> str:
    return (
        "关卡 %r 没有出怪数据。可能原因：教学关（tr_*）/ 塔防（tower）/ "
        "周常（weekly）这类关卡本身没有 waves，或者这份数据是从 "
        "zh_CN/gamedata/levels 全库抽取的、这关的解包文件不在其中。"
        "可以先用 map_search 确认关卡存在，再看 map_get 能否拿到地图。" % q)


# ---------------------------------------------------------------- 工具：时间轴

@tool(
    "stage_timeline",
    "关卡出怪时间轴",
    "某关的完整出怪时间轴：第几秒出什么怪、几只、间隔多少、走哪条路线、"
    "是不是废案/互斥组/装置触发。带 to_goal 时还能看到这批怪到蓝门要"
    "多少秒。对应「这关出怪节奏是什么样」。",
    {
        "type": "object",
        "properties": {
            "level": {"type": "string",
                      "description": "stage_id 或代号，如 main_04-04 / 4-4"},
            "enemy": {"type": "string",
                      "description": "只列这个敌人（id 或中文名片段）"},
            "effective": {"type": "boolean",
                          "description": "只列实机真会出的（剔 isValid=false "
                                         "废案、互斥编队只留一组），默认 false"},
            "with_arrival": {"type": "boolean",
                             "description": "是否算 to_goal（到蓝门秒数，"
                                            "含出场罚站），默认 true"},
            "limit": {"type": "integer", "minimum": 1,
                      "description": "最多返回多少条出怪批次，默认 150"},
        },
        "required": ["level"],
        "additionalProperties": False,
    },
)
def stage_timeline(args: dict) -> dict:
    q = str(args.get("level") or "").strip()
    if not q:
        return error("level 不能为空")
    stage, key, rec = _resolve(q)
    if not rec:
        return error(_no_data_hint(q))
    if not (rec.get("spawns") or []) and not rec.get("waves"):
        return error(_no_data_hint(q))

    recs = _records(rec)
    info: Dict[str, Any] = {}
    if args.get("effective"):
        recs, info = _effective(recs)

    flt = str(args.get("enemy") or "").strip()
    if flt:
        low = flt.lower()
        recs = [r for r in recs
                if low in r["enemy_id"].lower() or low in str(r["enemy"]).lower()]

    limit = int(args.get("limit") or 150)
    limit = max(1, min(limit, 2000))
    total_batches = len(recs)
    shown = recs[:limit]

    # ---- to_goal：每批怪到蓝门要多少秒（含出场罚站）
    with_arrival = args.get("with_arrival")
    with_arrival = True if with_arrival is None else bool(with_arrival)
    routes = einfo = None
    gm = None
    if with_arrival:
        raw = _load_raw(stage, key)
        gm = _load_map(stage, raw)
        if gm is not None:
            einfo = _EnemyInfo(raw)
            routes = _Routes(gm)
            for r in shown:
                eid = r["enemy_id"]
                ra = routes.get(int(r["route"]), einfo.speed(eid))
                if ra is None:
                    r["to_goal"] = None
                    continue
                r["to_goal"] = round(float(ra.total_time)
                                     + einfo.wait(eid), 3)
                w = einfo.wait(eid)
                if w:
                    r["spawn_wait"] = round(w, 3)

    waves: Dict[int, Dict[str, Any]] = {}
    for r in recs:
        wi = int(r.get("wave") if r.get("wave") is not None else -1)
        w = waves.setdefault(wi, {"wave": wi, "batches": 0, "units": 0,
                                  "first_t": None})
        w["batches"] += 1
        w["units"] += int(r.get("count") or 0)
        if w["first_t"] is None or r["t"] < w["first_t"]:
            w["first_t"] = r["t"]

    # 最后一只到蓝门的时刻：少人课题关心「这关多久彻底清空」
    last_arrival = None
    if routes is not None:
        for r in recs:
            tg = r.get("to_goal")
            if tg is None:
                continue
            end = r["t"] + max(0, int(r.get("count") or 1) - 1) \
                * float(r.get("interval") or 0.0) + float(tg)
            if last_arrival is None or end > last_arrival:
                last_arrival = end

    payload: Dict[str, Any] = _stage_brief(stage, key, rec)
    payload.update({
        "waves": rec.get("waves"),
        "duration": rec.get("dur"),
        "total_spawns": rec.get("total"),
        "batches": total_batches,
        "returned": len(shown),
        "truncated": len(shown) < total_batches,
        "first_spawn": shown[0]["t"] if shown else None,
        "last_arrival": (round(last_arrival, 2)
                         if last_arrival is not None else None),
        "fps_info": {
            "logic_tick_rate": 30,
            "render_fps": 60,
            "time_to_frame": "frame = round(time_sec * 30)",
            "frame_to_time": "time_sec = frame / 30",
            "note": "t 是秒级浮点。逻辑帧率 30 tick/s，帧号 = round(t*30)。",
        },
        "t_note": ("t = 开局后第几秒（已累加 wave/fragment/action 三层 "
                   "preDelay）；逐只时间 = t + k*interval。标 branch 的是"
                   "装置触发的条件出怪，t 相对装置激活时刻。"),
        "arrival_note": ("to_goal = 该批怪到蓝门秒数（已含出场罚站），"
                         "按敌人**自己的移速**重算路线；"
                         "该批最后一只进蓝门 = t + (count-1)*interval + to_goal。"),
        "wave_list": [waves[k] for k in sorted(waves)],
        "spawns": shown,
    })
    if info:
        payload["effective_filter"] = info
    if with_arrival and routes is None:
        payload["arrival_note"] = ("本关地图没有本地缓存，没算 to_goal"
                                   "（在软件里打开一次该关即可）。")
    return ok(payload)


# ---------------------------------------------------------------- 工具：某秒场面

def _field_at(t: float, units: List[dict], limit: int,
              branch_ok: bool, upcoming: int) -> Dict[str, Any]:
    on_field: List[Dict[str, Any]] = []
    n_branch = 0
    for u in units:
        rec = u["rec"]
        if rec.get("branch") and not branch_ok:
            continue
        tg = u.get("to_goal")
        arrive = None if tg is None else u["t"] + float(tg)
        if u["t"] > t:
            continue
        if arrive is not None and t >= arrive:
            continue
        ra = u.get("ra")
        if ra is None:
            continue
        if rec.get("branch"):
            n_branch += 1
        wait = float(u.get("wait") or 0.0)
        elapsed = t - u["t"]
        eff = elapsed - wait
        if eff < 0:
            eff = 0.0
        pose = ra.pose_at(eff)
        item: Dict[str, Any] = {
            "spawned_at": round(u["t"], 2),
            "enemy_id": rec["enemy_id"],
            "enemy": rec["enemy"],
            "route": rec["route"],
        }
        if pose:
            item["row"] = round(pose[0], 3)
            item["col"] = round(pose[1], 3)
            item["cell"] = [int(round(pose[0])), int(round(pose[1]))]
        if arrive is not None:
            item["to_blue"] = round(arrive - t, 2)
            item["arrive_at"] = round(arrive, 2)
        if wait and elapsed < wait:
            item["resting"] = round(wait - elapsed, 2)
        if rec.get("hidden_group"):
            item["hidden_group"] = rec["hidden_group"]
        if rec.get("branch"):
            item["branch"] = rec["branch"]
        st = u.get("hp")
        if st is not None:
            item["hp"] = st
        on_field.append(item)

    on_field.sort(key=lambda x: x["spawned_at"])
    n_total = len(on_field)
    if limit and n_total > limit:
        on_field = on_field[:limit]

    # 接下来要出的怪（按出场时刻）
    nxt: List[Dict[str, Any]] = []
    for u in units:
        if u["t"] <= t:
            continue
        rec = u["rec"]
        if rec.get("branch") and not branch_ok:
            continue
        item = {
            "spawns_at": round(u["t"], 2),
            "in": round(u["t"] - t, 2),
            "enemy_id": rec["enemy_id"],
            "enemy": rec["enemy"],
            "route": rec["route"],
        }
        if u.get("to_goal") is not None:
            item["arrive_at"] = round(u["t"] + float(u["to_goal"]), 2)
        if rec.get("hidden_group"):
            item["hidden_group"] = rec["hidden_group"]
        nxt.append(item)
        if len(nxt) >= max(1, upcoming):
            break

    return {
        "time": round(t, 2),
        "on_field": n_total,
        "shown": len(on_field),
        "truncated": len(on_field) < n_total,
        "enemies": on_field,
        "upcoming": nxt,
    }


@tool(
    "stage_field_at",
    "第 t 秒场上有什么",
    "某一秒场上还活着的敌人清单：谁、从哪条路线来、现在在哪一格、还有"
    "几秒到蓝门；同时给出接下来几只。对应少人课题的「第 30 秒场上是谁、"
    "我这条线扛不扛得住」。",
    {
        "type": "object",
        "properties": {
            "level": {"type": "string", "description": "stage_id 或代号"},
            "time": {"type": "number", "description": "单个时刻（秒）"},
            "times": {"type": "array", "items": {"type": "number"},
                      "description": "批量时刻，如 [20, 40, 60]"},
            "limit": {"type": "integer", "minimum": 1,
                      "description": "每个时刻最多列多少只在场的，默认 40"},
            "upcoming": {"type": "integer", "minimum": 0,
                         "description": "每个时刻附几只「接下来要出的」，默认 5"},
            "include_branch": {"type": "boolean",
                               "description": "是否包含装置触发的条件出怪，"
                                              "默认 false（那些 t 不是开局时间）"},
        },
        "required": ["level"],
        "additionalProperties": False,
    },
)
def stage_field_at(args: dict) -> dict:
    q = str(args.get("level") or "").strip()
    if not q:
        return error("level 不能为空")
    times: List[float] = []
    if args.get("times") is not None:
        for v in (args.get("times") or []):
            try:
                times.append(float(v))
            except (TypeError, ValueError):
                return error("times 里有非数字：%r" % (v,))
    if args.get("time") is not None:
        try:
            times.insert(0, float(args.get("time")))
        except (TypeError, ValueError):
            return error("time 不是数字：%r" % (args.get("time"),))
    if not times:
        return error("要给 time（单个）或 times（列表）")
    if len(times) > 60:
        return error("一次最多查 60 个时刻")
    if any(t < 0 for t in times):
        return error("time 不能是负数（t 是开局后第几秒）")

    stage, key, rec = _resolve(q)
    if not rec:
        return error(_no_data_hint(q))
    recs = _records(rec)
    if not recs:
        return error(_no_data_hint(q) + "（该关没有 SPAWN 动作）")

    raw = _load_raw(stage, key)
    gm = _load_map(stage, raw)
    routes = _Routes(gm) if gm is not None else None
    einfo = _EnemyInfo(raw)
    units = _units(recs, routes, einfo)
    if routes is None:
        return error(
            "关卡 %s 的地图没有本地缓存，算不了「还剩多久到蓝门」。"
            "请在软件里打开一次该关，或先用 stage_timeline 看出怪时刻。"
            % ((stage or {}).get("stage_id") or key))

    # 血量（覆盖后）一并给出，少人核算时最常接着问这句
    hp_by_eid: Dict[str, Any] = {}
    for eid in {u["rec"]["enemy_id"] for u in units}:
        st = einfo.stats(eid)
        hp_by_eid[eid] = getattr(st, "hp", None) if st is not None else None
    for u in units:
        u["hp"] = hp_by_eid.get(u["rec"]["enemy_id"])

    limit = int(args.get("limit") or 40)
    limit = max(1, min(limit, 500))
    upcoming = args.get("upcoming")
    upcoming = 5 if upcoming is None else max(0, min(int(upcoming), 50))
    branch_ok = bool(args.get("include_branch"))

    payload: Dict[str, Any] = _stage_brief(stage, key, rec)
    payload.update({
        "waves": rec.get("waves"),
        "duration": rec.get("dur"),
        "total_spawns": rec.get("total"),
        "move_speed_note": ("每个敌人按自己库里的移动速度重算路线耗时"
                            "（源石虫 1.1 / 无人机 0.8 ……），不是统一 1.0。"),
        "samples": [_field_at(t, units, limit, branch_ok, upcoming)
                    for t in times],
    })
    if not branch_ok:
        nb = sum(1 for u in units if u["rec"].get("branch"))
        if nb:
            payload["branch_excluded"] = (
                "%d 只条件出怪（装置触发）未计入，它们的 t 不是开局时间；"
                "需要时传 include_branch=true" % nb)
    if hp_by_eid:
        payload["hp_note"] = "hp 是**本关覆盖后**的血量（enemyDbRefs 的 overwrittenData）"
    return ok(payload)


# ---------------------------------------------------------------- 工具：索引状态

@tool(
    "stage_waves_status",
    "出怪时间轴数据状态",
    "看 stage_waves.json 是否就位、覆盖多少关、多少出怪批次。"
    "stage_timeline / stage_field_at 报「没有出怪数据」时先查这个。",
    {"type": "object", "properties": {}, "additionalProperties": False},
)
def stage_waves_status(args: dict) -> dict:
    data = _waves()
    meta = data.get("meta") or {}
    stages = data.get("stages") or {}
    return ok({
        "loaded": bool(stages),
        "path": _DATA_PATH or None,
        "stages": len(stages),
        "spawn_batches": meta.get("spawns"),
        "alias": len(data.get("alias") or {}),
        "errors": meta.get("errors"),
        "generated_by": meta.get("generated_by"),
        "cached_maps": sum(1 for v in stages.values() if (v or {}).get("cached")),
        "note": ("缺失时运行 python akcalc/tools/gen_stage_waves.py 重新生成"
                 if not stages else None),
    })

# ---------------------------------------------------------------- 供别的工具复用

def stage_enemy_ref(level: str, enemy_id: str) -> Dict[str, Any]:
    """查「某关里某个敌人」的引用记录（level 变体 + overwrittenData）。

    ``enemy_get(stage=...)`` 要的就是这条：全局敌人库给的是**基础值**，
    真实面板要再叠加本关 ``enemyDbRefs[].overwrittenData``。4-4 的源石虫
    库里的 1650 血在本关被写成 2200，只看库会低估 33%。
    """
    stage, key, rec = _resolve(level)
    out: Dict[str, Any] = {
        "stage_id": (stage or {}).get("stage_id") or key,
        "code": (rec or {}).get("code") or (stage or {}).get("code"),
        "name": (rec or {}).get("name") or (stage or {}).get("name"),
        "found": False,
        "level": 0,
        "override": None,
    }
    raw = _load_raw(stage, key)
    if raw is None:
        out["error"] = "本关原始 JSON 没有本地缓存（在软件里打开一次该关）"
        return out
    for ref in (raw.get("enemyDbRefs") or []):
        if ref.get("id") != enemy_id:
            continue
        try:
            out["level"] = int(ref.get("level") or 0)
        except (TypeError, ValueError):
            out["level"] = 0
        out["override"] = ref.get("overwrittenData")
        out["found"] = True
        break
    if not out["found"]:
        out["error"] = "本关 enemyDbRefs 里没有这个敌人（可能只在别的关出现）"
    return out


def overridden_fields(override: Optional[dict]) -> List[Dict[str, Any]]:
    """列出 ``overwrittenData`` 实际改写过的字段（``m_defined`` 为真才算）。

    要给用户「哪些数值是本关特有的」这份清单：AI 拿 2200 血去算，得知道
    这不是库里的常数，换关就变。
    """
    out: List[Dict[str, Any]] = []
    if not isinstance(override, dict):
        return out
    attrs = override.get("attributes")
    if isinstance(attrs, dict):
        for k, v in attrs.items():
            if isinstance(v, dict) and v.get("m_defined"):
                out.append({"field": "attributes." + str(k),
                            "value": v.get("m_value")})
    tb = override.get("talentBlackboard")
    if isinstance(tb, list) and tb:
        out.append({"field": "talentBlackboard",
                    "value": [{"key": it.get("key"), "value": it.get("value")}
                              for it in tb if isinstance(it, dict)]})
    for k, v in override.items():
        if k in ("attributes", "talentBlackboard"):
            continue
        if isinstance(v, dict):
            if v.get("m_defined"):
                out.append({"field": str(k), "value": v.get("m_value")})
        elif v is not None:
            out.append({"field": str(k), "value": v})
    return out