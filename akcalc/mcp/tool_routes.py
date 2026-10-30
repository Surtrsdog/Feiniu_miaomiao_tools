"""MCP 工具：路线数据。

路线是本工具最有价值的部分之一——它把关卡 JSON 里那串
``checkpoints`` 变成「按秒计时、带停驻、带偏移」的行进曲线：

* ``total_time`` —— 这条路线从出生到进蓝门要多少秒
* ``pose_at(t)`` —— 第 t 秒时在哪个格子（含 0.5 格偏移）
* ``wait_span_at(t)`` —— 第 t 秒是否在停驻，还要等多久

这些是「敌人几秒到我家门口」这类问题的答案，外接 AI 靠自己算不出来
（要重建 wait_for_seconds、wait_current_fragment_time、偏移量、
瞬移语义）。

## 为什么强调「蓝门目的地」

用户投诉过「敌人应该朝自己的目标蓝门走，不是最近蓝门」。数据层面确实
如此：``Route.end`` 是关卡 JSON 里写死的终点，本工具返回的就是它，
**不做任何「最近蓝门」推断**。有些关卡的 end 不落在 goal_tiles 上
（约 5.4%，多为演出/特殊机制），工具会标 ``on_goal_tile: false``。
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from . import common
from .server import ok, error, tool

from . import tool_maps as TM


def _analyses(gm, move_speed: float = 1.0):
    from ..core import routes as R
    return R.analyze_all(gm, move_speed=move_speed)


def _route_dict(a, gm, with_nodes: bool = False) -> Dict[str, Any]:
    goal = set(tuple(x) for x in gm.goal_tiles)
    d: Dict[str, Any] = {
        "index": a.route_index,
        "motion_mode": a.motion_mode,
        "flying": a.flying,
        "reachable": a.reachable,
        "total_time": round(a.total_time, 3),
        "move_time": round(a.move_time, 3),
        "wait_time": round(a.wait_time, 3),
        "pre_wait": round(a.pre_wait, 3),
        "total_length": round(a.total_length, 3),
        "teleports": a.teleports,
        "vanish": a.vanish,
    }
    if a.note:
        d["note"] = a.note
    if not a.reachable:
        d["failed_at"] = a.failed_at
    path = a.full_path
    if path:
        d["start"] = list(path[0])
        d["end"] = list(path[-1])
        d["on_goal_tile"] = tuple(path[-1]) in goal
    if with_nodes:
        d["nodes"] = [{"row": n.row, "col": n.col, "elapsed": round(n.time, 3)}
                      for n in getattr(a, "nodes", [])]
    return d


@tool(
    "route_list",
    "关卡的路线清单",
    "列出某关所有敌人的行进路线：起点、终点、总耗时、是否飞行、终点是否"
    "落在蓝门上。对应「这关有几个红门、敌人多久到」。",
    {
        "type": "object",
        "properties": {
            "level": {"type": "string",
                      "description": "stage_id 或代号，如 main_04-04 / 4-4"},
            "move_speed": {"type": "number",
                           "description": "移动速度倍率，默认 1.0（=1 格/秒基准）"},
            "with_nodes": {"type": "boolean",
                           "description": "是否返回每条路线的逐点时间"},
        },
        "required": ["level"],
        "additionalProperties": False,
    },
)
def route_list(args: dict) -> dict:
    lv = str(args.get("level") or "").strip()
    stage = TM._find_stage(lv)
    if not stage:
        return error("关卡索引里找不到：%r。先用 map_search。" % lv)
    gm = TM._load_map(stage)
    if gm is None:
        return error("关卡 %s 没有本地地图缓存，请先在软件里打开一次。"
                     % stage.get("stage_id"))
    speed = float(args.get("move_speed") or 1.0)
    analyses = _analyses(gm, speed)
    rows = [_route_dict(a, gm, bool(args.get("with_nodes")))
            for a in analyses]
    times = [a.total_time for a in analyses if a.reachable and a.total_time > 0]
    return ok({
        "stage_id": gm.level_id or stage.get("stage_id"),
        "code": stage.get("code"),
        # parse_level 在关卡 JSON 缺 name 时用 level_id 兜底，
        # 所以中文名要优先取 catalog。
        "name": stage.get("name") or gm.name,
        "size": {"rows": gm.height, "cols": gm.width},
        "move_speed": speed,
        "route_count": len(analyses),
        "reachable": sum(1 for a in analyses if a.reachable),
        "min_time": round(min(times), 3) if times else 0.0,
        "max_time": round(max(times), 3) if times else 0.0,
        "routes": rows,
    })


@tool(
    "route_pose",
    "敌人位置推算",
    "算某条路线在第 t 秒时敌人落在哪个格子（含半格偏移），以及是否正在"
    "停驻。用于「第 30 秒这个敌人在哪」。",
    {
        "type": "object",
        "properties": {
            "level": {"type": "string", "description": "stage_id 或代号"},
            "route_index": {"type": "integer", "description": "路线下标，从 0 起"},
            "times": {
                "type": "array",
                "items": {"type": "number"},
                "description": "要查的秒数列表，如 [0, 10, 30, 60]",
            },
            "move_speed": {"type": "number", "description": "默认 1.0"},
        },
        "required": ["level", "route_index", "times"],
        "additionalProperties": False,
    },
)
def route_pose(args: dict) -> dict:
    lv = str(args.get("level") or "").strip()
    idx = int(args.get("route_index") or 0)
    times = args.get("times") or []
    if not times:
        return error("times 不能为空")
    if len(times) > 200:
        return error("times 最多 200 个")
    stage = TM._find_stage(lv)
    if not stage:
        return error("关卡索引里找不到：%r" % lv)
    gm = TM._load_map(stage)
    if gm is None:
        return error("关卡 %s 没有本地地图缓存。" % stage.get("stage_id"))
    speed = float(args.get("move_speed") or 1.0)
    analyses = _analyses(gm, speed)
    hit = [a for a in analyses if a.route_index == idx]
    if not hit:
        return error("这关只有 %d 条路线（下标 0~%d），没有 %d。"
                     % (len(analyses), len(analyses) - 1, idx))
    a = hit[0]
    if not a.reachable:
        return error("路线 %d 不可达（failed_at=%d）：%s"
                     % (idx, a.failed_at, a.note or "数据缺失"))

    out = []
    for t in times:
        try:
            tf = float(t)
        except (TypeError, ValueError):
            out.append({"time": t, "error": "不是数字"})
            continue
        if tf > a.total_time + 1e-6:
            out.append({"time": tf, "beyond_end": True,
                        "note": "超过总耗时 %.3fs，已进蓝门"
                                % a.total_time})
            continue
        pose = a.pose_at(tf)
        wait = a.wait_span_at(tf)
        item: Dict[str, Any] = {"time": tf}
        if pose:
            item["row"] = round(pose[0], 4)
            item["col"] = round(pose[1], 4)
        else:
            item["row"] = item["col"] = None
        item["waiting"] = wait is not None and wait > 0
        if wait is not None:
            item["wait_remaining"] = round(wait, 3)
        out.append(item)
    return ok({
        "level": gm.level_id or stage.get("stage_id"),
        "route_index": idx,
        "total_time": round(a.total_time, 3),
        "move_speed": speed,
        "samples": out,
    })


@tool(
    "route_at_second",
    "某秒有哪些敌人在场",
    "反查：第 t 秒时哪些路线上的敌人还在图上、各自在哪一格。对应「第 30 "
    "秒场上都有谁」。",
    {
        "type": "object",
        "properties": {
            "level": {"type": "string"},
            "time": {"type": "number", "description": "秒"},
            "move_speed": {"type": "number", "description": "默认 1.0"},
        },
        "required": ["level", "time"],
        "additionalProperties": False,
    },
)
def route_at_second(args: dict) -> dict:
    lv = str(args.get("level") or "").strip()
    t = float(args.get("time") or 0)
    stage = TM._find_stage(lv)
    if not stage:
        return error("关卡索引里找不到：%r" % lv)
    gm = TM._load_map(stage)
    if gm is None:
        return error("关卡 %s 没有本地地图缓存。" % stage.get("stage_id"))
    speed = float(args.get("move_speed") or 1.0)
    analyses = _analyses(gm, speed)
    on_map = []
    for a in analyses:
        if not a.reachable:
            continue
        if t < 0 or t > a.total_time:
            continue
        pose = a.pose_at(t)
        if not pose:
            continue
        on_map.append({
            "route_index": a.route_index,
            "row": round(pose[0], 4),
            "col": round(pose[1], 4),
            "flying": a.flying,
            "remaining": round(a.total_time - t, 3),
        })
    return ok({"level": gm.level_id or stage.get("stage_id"), "time": t,
               "move_speed": speed, "on_map": len(on_map),
               "routes": on_map})


@tool(
    "route_summary",
    "路线总览",
    "某关的路线统计：可行走/飞行路线数、最短最长耗时、可达性。比 "
    "route_list 轻。",
    {
        "type": "object",
        "properties": {
            "level": {"type": "string"},
            "move_speed": {"type": "number", "description": "默认 1.0"},
        },
        "required": ["level"],
        "additionalProperties": False,
    },
)
def route_summary(args: dict) -> dict:
    lv = str(args.get("level") or "").strip()
    stage = TM._find_stage(lv)
    if not stage:
        return error("关卡索引里找不到：%r" % lv)
    gm = TM._load_map(stage)
    if gm is None:
        return error("关卡 %s 没有本地地图缓存。" % stage.get("stage_id"))
    speed = float(args.get("move_speed") or 1.0)
    from ..core import routes as R
    analyses = _analyses(gm, speed)
    sm = R.summarize(gm, analyses)
    return ok({
        "stage_id": sm.level_id or stage.get("stage_id"),
        "code": stage.get("code"),
        "name": stage.get("name") or gm.name,
        "size": {"rows": sm.height, "cols": sm.width},
        "ground_tiles": sm.ground_count,
        "fly_tiles": sm.fly_count,
        "route_count": sm.route_count,
        "walk_routes": sm.walk_routes,
        "fly_routes": sm.fly_routes,
        "reachable_routes": sm.reachable_routes,
        "min_time": round(sm.min_time, 3),
        "max_time": round(sm.max_time, 3),
        "move_speed": speed,
    })
