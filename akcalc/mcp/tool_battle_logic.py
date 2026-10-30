"""MCP 工具：战斗逻辑数据（从客户端逆向提取）。

填补 MCP_FRAME_EVAL.md 中识别的 5 个数据缺口：

缺口 2：敌人攻击目标选择逻辑
    从 GameAssembly.dll 的 IL2CPP 元数据提取的 Torappu.Battle.Abilities
    类字段/方法名，归纳出目标选择规则。

缺口 3：技能 blackboard 参数释义
    敌人技能 blackboard 的 key 是英文 prefabKey/字段名，AI 不一定理解。
    本工具查 battle_logic.json 中的释义字典，返回中文描述和分类。

缺口 4：干员天赋触发条件
    从 Ability 类的方法签名（OnTick/OnCastStart/OnBuffTrigger 等）提取
    触发时机，让 AI 能机器解析天赋什么时候生效。

缺口 5：帧率统一
    stage_timeline 返回的时间是秒级浮点，本工具提供 fps 和帧号换算规则。
"""
from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Optional

from . import common
from .server import ok, error, tool

_logic: Optional[dict] = None


def _load() -> dict:
    global _logic
    if _logic is None:
        path = os.path.join(common.paths().data_dir, "battle_logic.json")
        if not os.path.isfile(path):
            raise FileNotFoundError("battle_logic.json not found: %s" % path)
        with open(path, encoding="utf-8") as f:
            _logic = json.load(f)
    return _logic


_TRIGGER_MEANINGS = {
    "OnTick": "每逻辑帧触发（约30次/秒）",
    "OnCastStart": "技能施放开始时触发",
    "OnCastEnd": "技能施放结束时触发",
    "OnCastOnTarget": "对目标施放时触发",
    "OnCastOnTile": "对格子施放时触发",
    "OnAttached": "ability 挂载到角色时触发（部署/技能激活）",
    "OnDetached": "ability 从角色移除时触发",
    "OnBuffStart": "buff 开始时触发",
    "OnBuffFinish": "buff 结束时触发",
    "OnBuffTrigger": "buff 触发时生效（周期性或事件驱动）",
    "OnEvent": "自定义事件触发",
    "OnSpellStart": "技能释放时触发",
    "OnWaitForPreDelay": "等待前置延迟时触发",
    "OnWaitForPostDelay": "等待后置延迟时触发",
    "DoTriggerSkill": "每帧检查并触发技能",
    "OnDestroyed": "销毁时触发",
}


def _explain_triggers(methods):
    out = {}
    for m in methods:
        out[m] = _TRIGGER_MEANINGS.get(m, "")
    return out


@tool(
    "battle_target_logic",
    "敌人攻击目标选择逻辑",
    "查敌人的攻击目标选择规则：怎么选目标、优先级、追踪冷却。"
    "数据来自客户端 IL2CPP 元数据中 Torappu.Battle.Abilities 类的字段和方法名。"
    "可按 prefabKey 查具体技能的目标选择行为，或查通用规则。",
    {
        "type": "object",
        "properties": {
            "prefab_key": {"type": "string", "description": "敌人的技能 prefabKey"},
            "query": {"type": "string", "description": "模糊查询关键词（melee/ranged/trace/aura）"},
        },
        "additionalProperties": False,
    },
)
def battle_target_logic(args):
    data = _load()
    ts = data.get("gap2_target_selection", {})
    pk = str(args.get("prefab_key") or "").strip()
    q = str(args.get("query") or "").strip().lower()

    if pk:
        behavior = data.get("gap2_target_selection", {}).get("prefab_key_behavior", {}).get(pk)
        cls = ts.get("classes", {}).get(pk)
        if behavior or cls:
            out = {"prefab_key": pk, "general_rule": ts.get("general_rule", {}), "priority_rules": ts.get("priority_rules", [])}
            if behavior: out["behavior"] = behavior
            if cls: out["class_detail"] = cls
            return ok(out)
        matched = []
        for k, v in ts.get("classes", {}).items():
            if pk.lower() in k.lower():
                matched.append({"name": k})
        if matched:
            return ok({"prefab_key": pk, "matched": matched, "general_rule": ts.get("general_rule", {})})
        return error("prefabKey=%r not found" % pk)

    if q:
        matched = []
        for k in ts.get("classes", {}):
            if q in k.lower():
                matched.append({"name": k})
        return ok({"query": q, "matched": matched, "count": len(matched), "general_rule": ts.get("general_rule", {})})

    return ok({"general_rule": ts.get("general_rule", {}), "priority_rules": ts.get("priority_rules", []), "class_count": len(ts.get("classes", {})), "target_types": data.get("target_types", {})})


@tool(
    "battle_blackboard_dict",
    "技能 blackboard 参数释义",
    "查敌人/干员技能 blackboard 的 key 释义。key 是英文字段名（如 atk_scale），本工具返回中文描述和分类。支持单 key、批量、按分类、模糊搜索。",
    {
        "type": "object",
        "properties": {
            "key": {"type": "string", "description": "查单个 key 的释义"},
            "keys": {"type": "array", "items": {"type": "string"}, "description": "批量查多个 key"},
            "category": {"type": "string", "description": "按分类列出所有 key"},
            "query": {"type": "string", "description": "模糊搜索"},
        },
        "additionalProperties": False,
    },
)
def battle_blackboard_dict(args):
    data = _load()
    bb = data.get("gap3_blackboard_dict", {})
    keys_dict = bb.get("keys", {})

    single = str(args.get("key") or "").strip()
    batch = args.get("keys") or []
    cat = str(args.get("category") or "").strip()
    q = str(args.get("query") or "").strip().lower()

    if single:
        entry = keys_dict.get(single)
        if entry:
            d = dict(entry); d["key"] = single
            return ok(d)
        return error("key=%r not found. Total keys: %d" % (single, len(keys_dict)))

    if batch:
        results = []
        undocumented = []
        for k in batch:
            entry = keys_dict.get(str(k))
            if entry:
                d = dict(entry); d["key"] = k
                results.append(d)
                if entry.get("source") in ("none", "") or not entry.get("desc"):
                    undocumented.append(k)
            else:
                undocumented.append(k)
        return ok({"queried": len(batch), "found": len(results), "undocumented": undocumented, "results": results})

    if cat:
        matched = []
        for k, v in keys_dict.items():
            if v.get("category") == cat:
                d = dict(v); d["key"] = k; matched.append(d)
        return ok({"category": cat, "count": len(matched), "keys": matched})

    if q:
        matched = []
        for k, v in keys_dict.items():
            if q in k.lower() or q in str(v.get("desc", "")).lower():
                d = dict(v); d["key"] = k; matched.append(d)
        return ok({"query": q, "count": len(matched), "results": matched[:50]})

    cats = {}
    for v in keys_dict.values():
        c = v.get("category", "")
        cats[c] = cats.get(c, 0) + 1
    return ok({
        "total_keys": bb.get("total_keys", len(keys_dict)),
        "documented": bb.get("documented", 0),
        "inferred": bb.get("inferred", 0),
        "undocumented": bb.get("undocumented", 0),
        "categories": dict(sorted(cats.items(), key=lambda x: -x[1])),
    })


@tool(
    "battle_talent_triggers",
    "天赋/技能触发条件",
    "查干员天赋/技能的触发时机和条件。数据从 IL2CPP 元数据中 Ability 类的方法签名提取。",
    {
        "type": "object",
        "properties": {
            "class_name": {"type": "string", "description": "Ability 类名"},
            "query": {"type": "string", "description": "模糊搜索触发类型"},
        },
        "additionalProperties": False,
    },
)
def battle_talent_triggers(args):
    data = _load()
    tt = data.get("gap4_talent_triggers", {})
    cn = str(args.get("class_name") or "").strip()
    q = str(args.get("query") or "").strip().lower()

    if cn:
        entry = tt.get("trigger_classes", {}).get(cn)
        if entry:
            return ok({"class_name": cn, "trigger_methods": entry.get("trigger_methods", []), "fields": entry.get("fields", []), "trigger_meaning": _explain_triggers(entry.get("trigger_methods", []))})
        matched = []
        for k, v in tt.get("trigger_classes", {}).items():
            if cn.lower() in k.lower():
                matched.append({"name": k, "trigger_methods": v.get("trigger_methods", [])})
        if matched:
            return ok({"class_name": cn, "matched": matched, "count": len(matched)})
        return error("class_name=%r not found" % cn)

    if q:
        matched = []
        for k, v in tt.get("trigger_classes", {}).items():
            hay = k.lower()
            methods_str = " ".join(v.get("trigger_methods", [])).lower()
            if q in hay or q in methods_str:
                matched.append({"name": k, "trigger_methods": v.get("trigger_methods", [])})
        return ok({"query": q, "count": len(matched), "results": matched[:50]})

    return ok({"description": tt.get("description", ""), "trigger_type_count": len(tt.get("trigger_classes", {})), "event_types": tt.get("event_types", {}), "trigger_meanings": _TRIGGER_MEANINGS, "class_count": len(tt.get("trigger_classes", {}))})


@tool(
    "battle_fps_info",
    "帧率与时间换算",
    "返回游戏帧率信息和时间与帧号换算规则。逻辑帧率约30 tick/s，渲染帧率60 FPS。",
    {
        "type": "object",
        "properties": {
            "time_sec": {"type": "number", "description": "把秒换算成逻辑帧号"},
            "frame": {"type": "integer", "description": "把逻辑帧号换算成秒"},
        },
        "additionalProperties": False,
    },
)
def battle_fps_info(args):
    data = _load()
    fps = data.get("gap5_fps", {})
    out = {
        "game_fps": fps.get("game_fps", 60),
        "logic_tick_rate": fps.get("logic_tick_rate", 30),
        "note": fps.get("note", ""),
        "time_to_frame_formula": fps.get("time_to_frame", ""),
        "frame_to_time_formula": fps.get("frame_to_time", ""),
        "muzzle_data_fps": fps.get("muzzle_data_fps", ""),
    }
    t = args.get("time_sec")
    if t is not None:
        tick = float(t)
        out["input_time_sec"] = tick
        out["output_frame"] = round(tick * fps.get("logic_tick_rate", 30))
        out["output_render_frame"] = round(tick * fps.get("game_fps", 60))
    f = args.get("frame")
    if f is not None:
        frame = int(f)
        out["input_frame"] = frame
        out["output_time_sec"] = round(frame / fps.get("logic_tick_rate", 30), 4)
    return ok(out)


@tool(
    "battle_logic_overview",
    "战斗逻辑总览",
    "一站式返回所有战斗逻辑数据的概览：目标选择规则、blackboard释义统计、天赋触发条件统计、帧率信息。",
    {"type": "object", "properties": {}, "additionalProperties": False},
)
def battle_logic_overview(args):
    data = _load()
    g3 = data.get("gap3_blackboard_dict", {})
    g4 = data.get("gap4_talent_triggers", {})
    return ok({
        "_meta": data.get("_meta", {}),
        "gap1_devices": data.get("gap1_devices", {}),
        "gap2_target_selection": {
            "general_rule": data.get("gap2_target_selection", {}).get("general_rule", {}),
            "priority_rules": data.get("gap2_target_selection", {}).get("priority_rules", []),
            "class_count": len(data.get("gap2_target_selection", {}).get("classes", {})),
        },
        "gap3_blackboard": {k: v for k, v in g3.items() if k != "keys"},
        "gap4_talent": {
            "description": g4.get("description", ""),
            "trigger_class_count": len(g4.get("trigger_classes", {})),
            "event_types": g4.get("event_types", {}),
        },
        "gap5_fps": data.get("gap5_fps", {}),
        "target_types": data.get("target_types", {}),
    })