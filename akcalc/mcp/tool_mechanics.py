# -*- coding: utf-8 -*-
"""MCP 工具：技能机制 / 判定链查询。

数据来源是 ``skill_mechanics.json``（由 gamedata 预先提炼，约 0.37MB），
每个技能给出它挂载了哪些 buff 模板、这些模板在什么事件上做了什么。

**能回答什么**

  * 这个技能的伤害/控制走的是哪一套节点，而不是只看描述文字
  * 打谁：``targetSide`` / ``targetMotion``（WALK_ONLY = 只打地面移动单位）
  * 能不能叠：``overrideType``(STACK/EXTEND/UNIQUE) 与 ``maxStackCnt``
  * 什么时候断：``lifeTimeType``(INFINITY/LIMITED/IMMEDIATELY)
  * 事件时机：``ON_BUFF_START`` / ``ON_BUFF_TRIGGER`` / ``ON_ATTACK`` 等

**必须一起说的数据边界**

``skill_table.json`` 里只有 ``prefabId``，而技能到 buff 模板的官方绑定表
存在加密资源包（.ab）里，本地解不出来。因此这里的模板归属是**推导**的：

  * tier A —— ``blackboard`` 的键名里直接写了模板名
    （如 ``mlyss_s_3[unmoveable].duration``），最可靠
  * tier B —— 按 ``skchr_X_N`` 到 ``X_s_N`` 命名规则推断
  * tier D —— 找不到对应模板，通常是纯数值强化（只改 blackboard 和动画）

tier A/B 的结论可以说；tier D 必须说成「没有独立判定逻辑」，
而不是「数据缺失」。
"""
from __future__ import annotations

import json
import os
from typing import Dict, List, Optional

from .server import error, ok, tool

_DATA: Optional[dict] = None
_PATH = "skill_mechanics.json"

_BOUNDARY = (
    "模板归属是推导结果：skill_table 只给 prefabId，官方绑定表在加密资源包里。"
    "tier A 可靠、tier B 大概率正确、tier D 表示没有独立判定逻辑而非缺数据。"
)


def _load() -> dict:
    """延迟加载并缓存 skill_mechanics.json。"""
    global _DATA
    if _DATA is not None:
        return _DATA
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    path = os.path.join(base, "data", _PATH)
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            _DATA = json.load(f)
    except (OSError, ValueError):
        return {}
    return _DATA


def _skills() -> Dict[str, dict]:
    return (_load().get("skills") or {})


def _operators() -> Dict[str, dict]:
    return (_load().get("operators") or {})


def _find_operator(name: str) -> Optional[str]:
    """把显示名 / char_id / 片段解析成 char_id。"""
    data = _operators()
    if not data:
        return None
    q = str(name or "").strip()
    if not q:
        return None
    if q in data:
        return q
    low = q.lower()
    for cid, v in data.items():
        if str(v.get("name") or "") == q:
            return cid
    for cid, v in data.items():
        if cid.lower() == low:
            return cid
    for cid, v in data.items():
        if low in str(v.get("name") or "").lower():
            return cid
    for cid in data:
        if low in cid.lower():
            return cid
    return None


def _match_skill(sid_or_name: str) -> List[dict]:
    """按 skill_id 或技能名找技能记录。"""
    skills = _skills()
    if not skills:
        return []
    q = str(sid_or_name or "").strip()
    if not q:
        return []
    if q in skills:
        return [skills[q]]
    low = q.lower()
    hits = [v for k, v in skills.items() if k.lower() == low]
    if hits:
        return hits
    hits = [v for v in skills.values() if str(v.get("name") or "") == q]
    if hits:
        return hits
    return [v for v in skills.values() if q in str(v.get("name") or "")]


def _confidence_note(tier: Optional[str]) -> str:
    return {
        "A": "blackboard 键名里直接写了模板名，归属可靠",
        "B": "按 skchr_X_N -> X_s_N 命名规则推断，多数可靠但未经官方字段确认",
        "D": "没有独立判定模板，通常是纯数值强化（只改 blackboard 与动画）",
    }.get(str(tier or ""), "未标注")


@tool(
    "skill_mechanics_search",
    "查技能机制",
    "按技能名 / skill_id / 干员名查技能的判定机制：挂了哪些 buff 模板、"
    "打谁（阵营、移动状态、晕眩筛选）、能不能叠、什么时候失效、在什么事件上触发。"
    "比技能描述更接近实际判定逻辑——描述不写的目标筛选和叠加规则在这里。",
    {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "技能名（如「定点清算」）或 skill_id（如 skchr_wisdel_1）或干员名",
            },
            "limit": {
                "type": "integer",
                "description": "最多返回几条，默认 5",
                "minimum": 1,
                "maximum": 50,
            },
        },
        "required": ["query"],
        "additionalProperties": False,
    },
)
def skill_mechanics_search(args: dict) -> dict:
    q = str(args.get("query") or "").strip()
    limit = int(args.get("limit") or 5)
    if not q:
        return error("缺少 query 参数")

    skills = _skills()
    if not skills:
        return error("skill_mechanics.json 不可用，请先运行数据生成脚本")

    recs = _match_skill(q)
    source = "skill"
    if not recs:
        cid = _find_operator(q)
        if cid:
            source = "operator"
            op = _operators().get(cid) or {}
            recs = [skills[s["skill_id"]] for s in op.get("skills") or []
                    if s.get("skill_id") in skills]

    if not recs:
        return error("没有找到技能：%s" % q)

    out = []
    for r in recs[:limit]:
        tpls = r.get("templates") or []
        out.append({
            "skill_id": r.get("skill_id"),
            "name": r.get("name"),
            "confidence": r.get("tier"),
            "confidence_note": _confidence_note(r.get("tier")),
            "template_count": len(tpls),
            "templates": [{
                "template": t.get("template"),
                "events": t.get("events"),
                "actions": t.get("actions"),
                "node_count": t.get("node_types"),
                "targets": t.get("targets") or None,
                "stack": t.get("stack") or None,
                "life": t.get("life") or None,
                "scale_keys": t.get("scale_keys") or None,
            } for t in tpls[:8]],
            "truncated": len(tpls) > 8,
        })

    return ok({
        "query": q,
        "matched_by": source,
        "count": len(out),
        "results": out,
        "boundary": _BOUNDARY,
    })


@tool(
    "skill_mechanics_operator",
    "查干员的技能机制",
    "给出某位干员全部技能各自的判定机制摘要：每技能挂了几个 buff 模板、"
    "置信度、涉及哪些动作（挂 buff / 条件分支 / 范围伤害 / 眩晕等）。"
    "想快速扫一位干员所有技能的判定形态时用这个。",
    {
        "type": "object",
        "properties": {
            "operator": {
                "type": "string",
                "description": "干员名（如「缪尔赛思」）或 char_id（char_249_mlyss）",
            },
        },
        "required": ["operator"],
        "additionalProperties": False,
    },
)
def skill_mechanics_operator(args: dict) -> dict:
    q = str(args.get("operator") or "").strip()
    if not q:
        return error("缺少 operator 参数")
    cid = _find_operator(q)
    if not cid:
        return error("没有找到干员：%s" % q)
    op = _operators().get(cid) or {}
    skills = op.get("skills") or []
    if not skills:
        return error("该干员没有技能数据：%s" % cid)
    return ok({
        "char_id": cid,
        "name": op.get("name"),
        "skill_count": len(skills),
        "skills": skills,
        "boundary": _BOUNDARY,
    })


@tool(
    "skill_mechanics_status",
    "技能机制库状态",
    "查看 skill_mechanics.json 是否可用、覆盖了多少干员与技能、"
    "以及三档置信度各多少。skill_mechanics_* 报错时先调这个。",
    {"type": "object", "properties": {}, "additionalProperties": False},
)
def skill_mechanics_status(args: dict) -> dict:
    d = _load()
    meta = d.get("meta") or {}
    return ok({
        "loaded": bool(d),
        "operators": meta.get("operators"),
        "skills": meta.get("skills"),
        "templates_total": meta.get("templates_total"),
        "confidence": {
            "A": meta.get("tier_A"),
            "B": meta.get("tier_B"),
            "D": meta.get("tier_D"),
        },
        "client": meta.get("client"),
        "note": meta.get("note"),
    })
