"""MCP 工具：干员数据。

数据来源是 ``operators.json``（PRTS 抓取缓存，463 位干员，27MB），
字段包含：基础信息、各精英化各等级的完整面板、天赋、技能、信赖与潜能。

注意 ``attack_type``：本地缓存里这个字段历史上全是 PHYSICAL（PRTS 早期
抓取口径），``core/damage_type.py`` 专门做过修正。所以本模块给出的伤害
类型会经过那个修正器，而不是直接读缓存字形。
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from ..core import operator_timing as OTIM
from . import common
from .server import ok, error, tool


def _names() -> List[str]:
    return sorted(common.require_operators().data.keys())


def _resolve(name: str) -> Optional[str]:
    """把「银灰」「silverash」「char_172_svrash」都解析成缓存里的显示名。"""
    if not name:
        return None
    q = str(name).strip()
    data = common.require_operators().data
    if q in data:
        return q
    low = q.lower()
    for k in data:
        if k.lower() == low:
            return k
    # 按 char_id
    for k, v in data.items():
        if str(v.get("char_id") or "").lower() == low:
            return k
    # 模糊
    for k in data:
        if low in k.lower():
            return k
    for k, v in data.items():
        if low in str(v.get("char_id") or "").lower():
            return k
    return None


def _phase_table(rec: dict) -> Dict[str, Any]:
    """把 ``phases[e][lv]`` 摊平成可读结构。"""
    out = {}
    phases = rec.get("phases") or {}
    for elite, lvmap in phases.items():
        try:
            e = int(elite)
        except (TypeError, ValueError):
            continue
        entries = {}
        for lv, st in (lvmap or {}).items():
            entries[str(lv)] = st
        if entries:
            out["精英%d" % e] = entries
    return out


def _pick_level(rec: dict, elite: int, level: int) -> Optional[dict]:
    phases = rec.get("phases") or {}
    lvmap = phases.get(str(elite)) or phases.get(elite)
    if not lvmap:
        return None
    key = str(level)
    if key in lvmap:
        return lvmap[key]
    # 取最接近的等级
    try:
        best = min(lvmap.keys(), key=lambda k: abs(int(k) - int(level)))
    except (TypeError, ValueError):
        return None
    return lvmap[best]


@tool(
    "operator_library_status",
    "干员库状态",
    "查看干员缓存是否可用、干员数量与字段版本。operator_* 工具报错时先"
    "调这个。",
    {"type": "object", "properties": {}, "additionalProperties": False},
)
def operator_library_status(args: dict) -> dict:
    c = common.operator_cache()
    data = getattr(c, "data", {}) or {}
    return ok({
        "loaded": bool(data),
        "operators": len(data),
        "version": getattr(c, "version", None),
        "cache_path": common.paths().operators_cache,
        "note": ("缓存由 PRTS 抓取生成，首次使用需在软件里打开干员面板"
                 "让它抓取。" if not data else None),
    })


@tool(
    "operator_search",
    "搜索干员",
    "按名字 / char_id / 片段查干员。可同时按职业、星级、位置筛选。",
    {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "名字或 char_id 片段"},
            "profession": {"type": "string",
                           "description": "先锋/近卫/重装/狙击/术师/医疗/辅助/特种"},
            "rarity": {"type": "integer", "description": "星级 0~6（0 表示 1 星起）"},
            "position": {"type": "string",
                         "description": "近战位 / 远程位"},
            "limit": {"type": "integer", "description": "最多条数，默认 30",
                      "minimum": 1, "maximum": 500},
        },
        "additionalProperties": False,
    },
)
def operator_search(args: dict) -> dict:
    q = str(args.get("query") or "").strip()
    limit = int(args.get("limit") or 30)
    prof = args.get("profession")
    rarity = args.get("rarity")
    pos = args.get("position")

    data = common.require_operators().data
    low = q.lower()
    rows = []
    for name, rec in data.items():
        if q:
            hay = (name + " " + str(rec.get("char_id") or "")).lower()
            if low not in hay:
                continue
        if prof and str(rec.get("profession") or "") != prof:
            continue
        if pos and str(rec.get("position") or "") != pos:
            continue
        if rarity is not None:
            try:
                if int(rec.get("rarity") or 0) != int(rarity):
                    continue
            except (TypeError, ValueError):
                continue
        rows.append({
            "name": name,
            "char_id": rec.get("char_id"),
            "rarity": rec.get("rarity"),
            "profession": rec.get("profession"),
            "sub_profession": rec.get("sub_profession"),
            "position": rec.get("position"),
        })
    rows.sort(key=lambda r: (-(r.get("rarity") or 0), r.get("name") or ""))
    return ok({"query": q, "total_matched": len(rows),
               "returned": min(limit, len(rows)), "results": rows[:limit]})


@tool(
    "operator_get",
    "干员详情",
    "拿单个干员的完整数据：面板（按精英化/等级）、天赋、技能、信赖加成、"
    "潜能。默认返回精英 2 满级那一档的面板。",
    {
        "type": "object",
        "properties": {
            "query": {"type": "string",
                      "description": "干员名或 char_id，如「银灰」/ char_172_svrash"},
            "elite": {"type": "integer",
                      "description": "精英化阶段 0/1/2；不填则取该干员最高",
                      "minimum": 0, "maximum": 2},
            "level": {"type": "integer",
                      "description": "等级；不填则取该阶段最高", "minimum": 1},
        },
        "required": ["query"],
        "additionalProperties": False,
    },
)
def operator_get(args: dict) -> dict:
    q = str(args.get("query") or "").strip()
    name = _resolve(q)
    if not name:
        return error("找不到干员：%r。先用 operator_search 搜一下。" % q)
    rec = common.require_operators().data[name]

    phases = rec.get("phases") or {}
    elite_keys = []
    for k in phases:
        try:
            elite_keys.append(int(k))
        except (TypeError, ValueError):
            pass
    elite_keys.sort()
    if args.get("elite") is not None:
        elite = int(args["elite"])
    else:
        elite = elite_keys[-1] if elite_keys else 0

    lvmap = phases.get(str(elite)) or phases.get(elite) or {}
    if args.get("level") is not None:
        level = int(args["level"])
    else:
        lv = []
        for k in lvmap:
            try:
                lv.append(int(k))
            except (TypeError, ValueError):
                pass
        level = max(lv) if lv else 1

    st = _pick_level(rec, elite, level)

    out: Dict[str, Any] = {
        "name": name,
        "char_id": rec.get("char_id"),
        "rarity": rec.get("rarity"),
        "profession": rec.get("profession"),
        "sub_profession": rec.get("sub_profession"),
        "position": rec.get("position"),
        "attack_type": rec.get("attack_type"),
        "max_elite": rec.get("max_elite"),
        "requested": {"elite": elite, "level": level},
        "stats": st,
        "talents": rec.get("talents") or [],
        "skills": rec.get("skills") or [],
        "trust_bonus": rec.get("trust_bonus") or {},
        "potential_bonus": rec.get("potential_bonus") or {},
        "potential_ranks": rec.get("potential_ranks") or [],
        "elite_levels": {("精英%d" % e): sorted(
            (int(x) for x in (phases.get(str(e)) or phases.get(e) or {})
             if str(x).isdigit())) for e in elite_keys},
    }

    # 抬手 / 登场 / 技能抬手（解包 bake 里 OnAttack、OnStart 的时刻）。
    # 秒是原始值，帧按 30fps 还原；两者同时给，别让调用方自己乘 30。
    cid = str(rec.get("char_id") or "")
    s_sec = OTIM.start_seconds(cid)
    reason = OTIM.reason(cid)
    timing: Optional[Dict[str, Any]] = None
    if OTIM.seconds(cid) is not None or reason:
        timing = {
            "seconds": OTIM.seconds(cid),
            "frames": OTIM.frames(cid),
            "start_seconds": s_sec,
            "start_frames": OTIM.sec_to_frames(s_sec) if s_sec is not None else None,
            "fps": OTIM.FPS,
            "reason": reason,
            "reason_text": OTIM.REASONS.get(reason or "", None),
        }
        sk = OTIM.skills(cid)
        if sk:
            timing["skills"] = sk
    out["attack_timing"] = timing
    return ok(out)


@tool(
    "operator_list",
    "干员清单",
    "按职业/星级/位置列干员，或直接返回全部。用于「列所有六星术师」。",
    {
        "type": "object",
        "properties": {
            "profession": {"type": "string"},
            "rarity": {"type": "integer"},
            "position": {"type": "string"},
            "limit": {"type": "integer", "description": "默认 500",
                      "minimum": 1, "maximum": 1000},
        },
        "additionalProperties": False,
    },
)
def operator_list(args: dict) -> dict:
    return operator_search({
        "profession": args.get("profession"),
        "rarity": args.get("rarity"),
        "position": args.get("position"),
        "limit": args.get("limit") or 500,
    })


@tool(
    "operator_professions",
    "干员分类字典",
    "返回全部职业、子职业、星级、位置的取值，供其他查询用。",
    {"type": "object", "properties": {}, "additionalProperties": False},
)
def operator_professions(args: dict) -> dict:
    data = common.require_operators().data
    profs = {}
    for name, rec in data.items():
        p = str(rec.get("profession") or "")
        profs.setdefault(p, 0)
        profs[p] += 1
    subs = {}
    for name, rec in data.items():
        s = str(rec.get("sub_profession") or "")
        if not s:
            continue
        subs.setdefault(s, 0)
        subs[s] += 1
    rarities = {}
    for name, rec in data.items():
        r = rec.get("rarity")
        try:
            r = int(r)
        except (TypeError, ValueError):
            continue
        rarities[r] = rarities.get(r, 0) + 1
    positions = {}
    for name, rec in data.items():
        p = str(rec.get("position") or "")
        positions[p] = positions.get(p, 0) + 1
    return ok({
        "total": len(data),
        "professions": dict(sorted(profs.items(), key=lambda kv: -kv[1])),
        "sub_professions": dict(sorted(subs.items(), key=lambda kv: -kv[1])),
        "rarities": dict(sorted(rarities.items())),
        "positions": dict(sorted(positions.items(), key=lambda kv: -kv[1])),
    })
