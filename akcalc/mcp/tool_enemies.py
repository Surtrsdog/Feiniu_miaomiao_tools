"""MCP 工具：敌人数据。

覆盖四个来源，外接 AI 一次调用就能拿全：

* ``enemy_database.json``  —— 面板数值（生命/攻击/防御/抗性/速度/重量）
* ``enemy_handbook_table.json`` —— 天赋、能力、描述、标签、伤害类型
* ``bakemuzzledata``      —— **抬手（攻击前摇）**，这是本作独有的
* ``codex_entry()``       —— 上面两者拼好的图鉴视图

为什么把抬手单独做成工具
------------------------
别的数据源（PRTS、各种 wiki API）都没有抬手时间——它藏在 Spine 动画
烘焙数据里。外接 AI 做「这个敌人会不会在我撤退前打出来」这类推算时，
抬手是必需的。
"""
from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional

from ..core import enemy_timing as ETIM
from . import common
from .server import ok, error, tool

# ---------------------------------------------------------------- 辅助

_STAT_KEYS = ("hp", "atk", "defense", "magic_resist", "move_speed",
              "weight", "block_cost", "attack_interval", "is_flying",
              "damage_type", "spawn_unmovable")


def _stats_dict(st) -> dict:
    out = {}
    for k in _STAT_KEYS:
        if hasattr(st, k):
            out[k] = getattr(st, k)
    return out


def _all_ids() -> List[str]:
    lib = common.require_enemy_lib()
    return sorted(lib.by_id.keys())


def _resolve_id(query: str) -> Optional[str]:
    """把 id / 中文名 / 部分名解析成 enemy_id。

    外接 AI 常常只知道中文名（「源石虫」）或记得半个 id（``slime``），
    所以三级匹配：精确 id → 精确中文名 → 模糊。
    """
    if not query:
        return None
    q = str(query).strip()
    lib = common.require_enemy_lib()
    if q in lib.by_id:
        return q
    ql = q.lower()
    for eid in lib.by_id:
        if eid.lower() == ql:
            return eid
    # 中文名精确
    from ..core import enemy_codex as EC
    for eid, ents in lib.by_id.items():
        if not ents:
            continue
        ed = ents[0].get("enemyData") or {}
        nm = EC._clean(str(EC._mv(ed.get("name"), "") or ""))
        if nm == q:
            return eid
    # 手册显示名
    try:
        hb = common.handbook()
        eid = hb.find_id(q)
        if eid and eid in lib.by_id:
            return eid
    except Exception:
        pass
    # 模糊：id 含 / 名字含
    for eid in lib.by_id:
        if ql in eid.lower():
            return eid
    for eid, ents in lib.by_id.items():
        if not ents:
            continue
        ed = ents[0].get("enemyData") or {}
        nm = EC._clean(str(EC._mv(ed.get("name"), "") or ""))
        if q and q in nm:
            return eid
    return None


def _timing_payload(enemy_id: str) -> Optional[dict]:
    hit = ETIM.get(enemy_id, common.paths())
    if not hit:
        return None
    a = hit.get("a")
    out = {
        "attack_windup_seconds": a,
        # 帧是原始数据（解包按 30fps 烘焙），不是估算值
        "attack_windup_frames": ETIM.sec_to_frames(a),
        "fps": ETIM.FPS,
    }
    if hit.get("anim"):
        out["anim"] = hit["anim"]
    if hit.get("all"):
        allv = hit["all"]
        out["by_animation"] = allv
        out["by_animation_frames"] = {
            k: ETIM.sec_to_frames(v)
            for k, v in allv.items() if isinstance(v, (int, float))
        }
    if hit.get("skill_only"):
        out["note"] = "普攻动画缺失，OnAttack 事件取自技能动作"
    return out


# ---------------------------------------------------------------- 工具

@tool(
    "enemy_library_status",
    "敌人库状态",
    "查看敌人库是否已加载、条目数、抬手表覆盖率。任何 enemy_* 工具报"
    "「敌人库还没下载」时先调这个。",
    {"type": "object", "properties": {}, "additionalProperties": False},
)
def enemy_library_status(args: dict) -> dict:
    lib = common.enemy_lib()
    hb = common.handbook()
    tstat = ETIM.stats(common.paths())
    return ok({
        "enemy_database": {
            "loaded": lib.loaded,
            "entries": len(lib.by_id),
            "cache_path": common.paths().enemies_cache,
        },
        "handbook": {
            "loaded": getattr(hb, "loaded", False),
            "error": getattr(hb, "error", "") or None,
        },
        "attack_timing": tstat,
    })


@tool(
    "enemy_search",
    "搜索敌人",
    "按名字或 id 片段查敌人，返回匹配的 id 与中文名。只给关键词，别猜"
    "完整 id。",
    {
        "type": "object",
        "properties": {
            "query": {"type": "string",
                      "description": "中文名或 id 片段，如「源石虫」「slime」「黑蛇」"},
            "limit": {"type": "integer", "description": "最多返回条数，默认 20",
                      "minimum": 1, "maximum": 200},
        },
        "required": ["query"],
        "additionalProperties": False,
    },
)
def enemy_search(args: dict) -> dict:
    q = str(args.get("query") or "").strip()
    limit = int(args.get("limit") or 20)
    if not q:
        return error("query 不能为空")
    from ..core import enemy_codex as EC
    lib = common.require_enemy_lib()
    ql = q.lower()
    hits = []
    for eid in sorted(lib.by_id):
        ents = lib.by_id.get(eid) or []
        nm = ""
        if ents:
            ed = ents[0].get("enemyData") or {}
            nm = EC._clean(str(EC._mv(ed.get("name"), "") or ""))
        if ql in eid.lower() or (q and q in nm):
            hits.append({"enemy_id": eid, "name": nm,
                         "levels": len(ents)})
            if len(hits) >= limit:
                break
    return ok({"query": q, "count": len(hits), "results": hits})


@tool(
    "enemy_get",
    "敌人详情",
    "拿单个敌人的完整数据：面板数值、天赋能力、标签、免疫、技能、"
    "**抬手（攻击前摇）**。query 可以是 id 或中文名。"
    "传 stage 则返回**该关覆盖后**的面板（enemyDbRefs 的 "
    "overwrittenData / 等级变体），不是库里基础值。",
    {
        "type": "object",
        "properties": {
            "query": {"type": "string",
                      "description": "enemy_id 或中文名，如 enemy_1007_slime / 源石虫"},
            "level": {"type": "integer",
                      "description": "等级变体（0 起），默认 0", "minimum": 0},
            "stage": {"type": "string",
                      "description": "关卡 stage_id 或代号（如 4-4）。给了就按本关的"
                                     " overwrittenData 与等级变体算面板"},
            "include_raw": {"type": "boolean",
                            "description": "是否附原始 enemyData（很大，默认 false）"},
        },
        "required": ["query"],
        "additionalProperties": False,
    },
)
def enemy_get(args: dict) -> dict:
    q = str(args.get("query") or "").strip()
    level = int(args.get("level") or 0)
    eid = _resolve_id(q)
    if not eid:
        return error("找不到敌人：%r。先用 enemy_search 搜一下。" % q)
    lib = common.require_enemy_lib()

    # ---- 关卡覆盖：同一个敌人不同关数值可能差三分之一（4-4 源石虫
    # 1650 -> 2200），少人核算必须按本关的真实面板算，不能拿库里基础值。
    stage_arg = str(args.get("stage") or "").strip()
    override = None
    stage_ref: Dict[str, Any] = {}
    if stage_arg:
        from . import tool_stage as TS
        stage_ref = TS.stage_enemy_ref(stage_arg, eid)
        if stage_ref.get("error") and not stage_ref.get("found"):
            # 关卡本身没有本地数据 / 本关没这个敌人：明确说清，别退回基础值
            # 让调用方误以为拿到的是本关真实面板。
            return error(stage_ref["error"] + "（stage=%r）" % stage_arg)
        override = stage_ref.get("override")
        level = int(stage_ref.get("level") or 0)

    st = lib.stats(eid, level, override)
    from ..core import enemy_codex as EC
    entries = lib.by_id.get(eid) or []
    ce = EC.codex_entry(entries, level, eid) if entries else {}

    hb = common.handbook()
    out: Dict[str, Any] = {
        "enemy_id": eid,
        "name": ce.get("name") or (st.name if st else ""),
        "level": level,
        "levels_available": len(entries),
        "stats": _stats_dict(st) if st else {},
        "codex": ce,
        "attack_timing": _timing_payload(eid),
    }

    # ---- blackboard 参数释义（缺口 3 补齐）
    try:
        from . import tool_battle_logic as TBL
        logic = TBL._load()
        bb_dict = logic.get("gap3_blackboard_dict", {}).get("keys", {})
        skills_raw = []
        if isinstance(entries, list) and entries:
            lv_idx = min(level, len(entries) - 1)
            ed_data = entries[lv_idx].get("enemyData", {}) if isinstance(entries[lv_idx], dict) else {}
            skills_raw = ed_data.get("skills") or []
            # Handle {m_defined, m_value} wrapper
            if isinstance(skills_raw, dict):
                skills_raw = skills_raw.get("m_value") or []
        if isinstance(skills_raw, list):
                annotated = []
                for sk in skills_raw:
                    if not isinstance(sk, dict):
                        continue
                    bb = sk.get("blackboard", [])
                    ann = []
                    if isinstance(bb, list):
                        for item in bb:
                            if isinstance(item, dict):
                                key = str(item.get("key", ""))
                                entry = bb_dict.get(key)
                                ann.append({
                                    "key": key,
                                    "value": item.get("value"),
                                    "desc": (entry or {}).get("desc", ""),
                                    "category": (entry or {}).get("category", ""),
                                    "documented": bool((entry or {}).get("desc")),
                                })
                    sk2 = dict(sk)
                    sk2["blackboard_annotated"] = ann
                    annotated.append(sk2)
                if annotated:
                    out["skills_annotated"] = annotated
    except Exception:
        pass
    if stage_arg:
        out["stage"] = {k: stage_ref.get(k)
                        for k in ("stage_id", "code", "name") if stage_ref.get(k)}
        base = lib.stats(eid, level)
        bd = _stats_dict(base) if base else {}
        out["stats_base"] = bd
        diff = {k: [bd.get(k), v] for k, v in out["stats"].items()
                if k in bd and bd.get(k) != v}
        out["overridden"] = diff
        if override:
            from . import tool_stage as TS
            out["override_fields"] = TS.overridden_fields(override)
            out["stats_note"] = (
                "stats 已按本关 overwrittenData 覆盖，stats_base 是敌人库基础值；"
                "overridden 里 [基础值, 本关值]。换关数值会变，别当常数用。")
        else:
            out["stats_note"] = "本关没有 overwrittenData，stats 与库基础值一致。"
    if getattr(hb, "loaded", False):
        out["handbook"] = {
            "display_name": hb.display_name(eid),
            "description": hb.description(eid),
            "tags": hb.tags(eid),
            "race": hb.race(eid),
            "damage_types": hb.damage_types(eid),
            "sections": hb.sections(eid),
        }
    if args.get("include_raw") and entries:
        lv = min(level, len(entries) - 1)
        out["raw"] = entries[lv]
    return ok(out)


@tool(
    "enemy_attack_timing",
    "敌人抬手（攻击前摇）",
    "查敌人的抬手时间：攻击动画播到第几帧/第几秒才真正打出伤害。"
    "数据来自解包 bakemuzzledata 的 OnAttack 事件，按 30 帧每秒烘焙，"
    "所以帧数是原始数据不是估算。同时返回帧和秒。可选批量。",
    {
        "type": "object",
        "properties": {
            "queries": {
                "type": "array",
                "items": {"type": "string"},
                "description": "敌人 id 或中文名列表；留空则返回全部（很大）",
            },
        },
        "additionalProperties": False,
    },
)
def enemy_attack_timing(args: dict) -> dict:
    qs = args.get("queries") or []
    if not qs:
        data = ETIM.load(common.paths())
        items = {k: v.get("a") for k, v in data.items()}
        frames = {k: ETIM.sec_to_frames(v) for k, v in items.items()}
        return ok({"fps": ETIM.FPS, "count": len(items),
                   "unit": "秒与帧都给；second 为秒，frame 为帧",
                   "by_id": items, "by_id_frames": frames})

    out = []
    for q in qs:
        eid = _resolve_id(str(q))
        if not eid:
            out.append({"query": q, "error": "找不到这个敌人"})
            continue
        t = _timing_payload(eid)
        if not t:
            out.append({"query": q, "enemy_id": eid,
                        "attack_windup_seconds": None,
                        "note": "该敌人无攻击动画（多为箱子/门/载具等非战斗单位）"})
        else:
            out.append(dict(t, query=q, enemy_id=eid))
    return ok({"fps": ETIM.FPS, "count": len(out), "results": out})


@tool(
    "attack_timing_convert",
    "抬手单位换算（帧⇄秒 + 30/60/120 帧率档）",
    "把抬手在「帧」和「秒」之间换算，并给出同一时长在 30/60/120 fps "
    "三个运行档位下的帧号。明日方舟逻辑按 30 帧每秒运行（帧号是解包"
    "原始数据）；60/120 是高刷设备的插值帧，同一时长帧号成比例"
    "（14 帧@30 == 28 帧@60 == 56 帧@120）。三种用法："
    "(1) 给 value + from_unit 直接换算，例 value=14, from_unit=frame；"
    "(2) 给 enemy 查某个敌人的抬手并同时给出帧和秒；"
    "(3) 什么都不给，返回换算表（1~60 帧对应多少秒）。",
    {
        "type": "object",
        "properties": {
            "value": {"type": "number", "description": "要换算的数值"},
            "from_unit": {
                "type": "string",
                "enum": ["second", "frame"],
                "description": "value 的单位，默认 second",
            },
            "fps": {
                "type": "integer",
                "enum": [30, 60, 120],
                "description": "value 为帧时它属于哪个档位，默认 30"
                               "（游戏逻辑帧率）",
            },
            "enemy": {
                "type": "string",
                "description": "敌人 id 或中文名；给了就直接查它的抬手",
            },
            "count": {
                "type": "integer",
                "description": "什么都不给时，换算表列到多少帧，默认 60",
            },
        },
        "additionalProperties": False,
    },
)
def attack_timing_convert(args: dict) -> dict:
    enemy = args.get("enemy")
    if enemy:
        eid = _resolve_id(str(enemy))
        if not eid:
            return error("找不到这个敌人：%s" % enemy)
        t = _timing_payload(eid)
        if not t:
            return ok({"enemy_id": eid, "fps": ETIM.FPS,
                       "attack_windup_frames": None,
                       "attack_windup_seconds": None,
                       "note": "该敌人无攻击动画（非战斗单位）"})
        return ok(dict(t, enemy_id=eid))

    if args.get("value") is not None:
        from_unit = str(args.get("from_unit") or "second")
        # fps 档：输入的「帧」按这个档位解释。默认 30（逻辑真帧）。
        try:
            fps_sel = int(args.get("fps") or 30)
        except (TypeError, ValueError):
            fps_sel = 30
        if fps_sel not in ETIM.SUPPORTED_FPS:
            return error("fps 只支持 %s，收到：%r"
                         % (list(ETIM.SUPPORTED_FPS), args.get("fps")))
        val = args.get("value")
        if (from_unit.lower() in ("frame", "frames", "f", "帧")
                and fps_sel != ETIM.FPS):
            # 折回 30fps 逻辑帧再统一换算
            try:
                f30 = int(round(float(val) * ETIM.FPS / fps_sel))
            except (TypeError, ValueError):
                return error("value 必须是数字")
            res = ETIM.convert(max(f30, 0), "frame")
        else:
            res = ETIM.convert(val, from_unit)
        if "error" in res:
            return error(res["error"])
        res = dict(res)
        res["selected_fps"] = fps_sel
        res["note"] = ("30 为逻辑真帧（解包原始数据）；60/120 为插值帧，"
                       "时长与 30 帧一致")
        return ok(res)

    # 换算表
    try:
        n = int(args.get("count") or 60)
    except (TypeError, ValueError):
        n = 60
    n = max(1, min(n, 600))
    rows = []
    for f in range(n + 1):
        tab = ETIM.at_fps_table(f) or {}
        rows.append({"frame": f,
                     "second": round(ETIM.frames_to_sec(f), 4),
                     "at_60fps": tab.get("60"),
                     "at_120fps": tab.get("120")})
    return ok({"fps": ETIM.FPS,
               "sec_per_frame": round(ETIM.SEC_PER_FRAME, 6),
               "supported_fps": list(ETIM.SUPPORTED_FPS),
               "note": "30 帧 = 1 秒（逻辑帧率，帧号是解包原始数据）；"
                       "60/120 为插值帧",
               "table": rows})


@tool(
    "enemy_list",
    "敌人清单",
    "按条件筛敌人：飞行、体重、伤害类型、生命区间等。用于「列出血量最高"
    "的 10 个敌人」这类问题。",
    {
        "type": "object",
        "properties": {
            "flying_only": {"type": "boolean", "description": "只要飞行单位"},
            "damage_type": {"type": "string",
                            "description": "PHYSICAL / MAGIC / NONE / HEAL"},
            "min_hp": {"type": "number", "description": "最低生命值"},
            "max_hp": {"type": "number", "description": "最高生命值"},
            "sort_by": {"type": "string",
                        "description": "hp / atk / defense / move_speed / weight",
                        "enum": ["hp", "atk", "defense", "move_speed",
                                 "weight", "attack_interval"]},
            "descending": {"type": "boolean",
                           "description": "是否降序，默认 true"},
            "limit": {"type": "integer", "description": "最多条数，默认 30",
                      "minimum": 1, "maximum": 500},
        },
        "additionalProperties": False,
    },
)
def enemy_list(args: dict) -> dict:
    lib = common.require_enemy_lib()
    only_fly = bool(args.get("flying_only"))
    dmg = (args.get("damage_type") or "").upper()
    minhp = args.get("min_hp")
    maxhp = args.get("max_hp")
    sort_by = args.get("sort_by") or "hp"
    desc = args.get("descending")
    desc = True if desc is None else bool(desc)
    limit = int(args.get("limit") or 30)

    rows = []
    for eid in lib.by_id:
        st = lib.stats(eid, 0)
        if not st:
            continue
        if only_fly and not st.is_flying:
            continue
        if dmg and str(st.damage_type).upper() != dmg:
            continue
        if minhp is not None and st.hp < float(minhp):
            continue
        if maxhp is not None and st.hp > float(maxhp):
            continue
        rows.append({"enemy_id": eid, "name": st.name,
                     "hp": st.hp, "atk": st.atk,
                     "defense": st.defense,
                     "magic_resist": st.magic_resist,
                     "move_speed": st.move_speed,
                     "weight": st.weight,
                     "attack_interval": st.attack_interval,
                     "is_flying": st.is_flying,
                     "damage_type": st.damage_type})
    rows.sort(key=lambda r: r.get(sort_by) or 0, reverse=desc)
    return ok({"total_matched": len(rows), "returned": min(limit, len(rows)),
               "sort_by": sort_by, "descending": desc,
               "results": rows[:limit]})
