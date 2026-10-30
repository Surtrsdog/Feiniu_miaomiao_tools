# -*- coding: utf-8 -*-
"""MCP 工具：攻击范围（某干员站在某格时覆盖哪些格子）。

范围数据在 ``akcalc/data/range_table.json``：73 个 ``rangeId``，每条是
相对干员自身格子的**格偏移**，坐标系是「朝右」的基准。要换成别的朝向
就旋转——旋转规则已在 ``core/ranges.py::rotate_cells`` 里，这里直接复用，
不自己再写一套（写两套必然有一天两边不一致）。

干员用哪个 rangeId 不在 ``operators.json`` 里（463 位干员一个都没有
``ranges`` 字段，实测），而在 ``char_ranges.json``：``{char_id: {精英: rangeId}}``。
精英化会改范围（银灰 E2 才三格），所以查询要带 ``elite``。
"""
from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Optional, Tuple

from . import common
from .server import ok, error, tool

from ..core import ranges as RG

_TABLE: Optional[dict] = None
_TABLE_PATH = ""
_CHAR: Optional[dict] = None
_CHAR_PATH = ""

#: 朝向别名（玩家口语 -> ranges 的枚举名）
_FACING = {
    "right": "RIGHT", "r": "RIGHT", "右": "RIGHT", "向右": "RIGHT",
    "down": "DOWN", "d": "DOWN", "下": "DOWN", "向下": "DOWN",
    "left": "LEFT", "l": "LEFT", "左": "LEFT", "向左": "LEFT",
    "up": "UP", "u": "UP", "上": "UP", "向上": "UP",
}


def _candidates(name: str) -> List[str]:
    out: List[str] = []
    try:
        p = common.paths()
    except Exception:                                        # noqa: BLE001
        p = None
    if p is not None:
        for d in (getattr(p, "data_dir", None),
                  getattr(p, "seed_data_dir", None),
                  getattr(p, "cache_dir", None),
                  getattr(p, "seed_cache_dir", None)):
            if d:
                out.append(os.path.join(d, name))
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    out.append(os.path.join(here, "data", name))
    out.append(os.path.join(here, "data", "cache", name))
    return out


def _first_file(name: str) -> str:
    for p in _candidates(name):
        if p and os.path.isfile(p):
            return p
    return ""


def _table() -> dict:
    """加载并**注册**偏移表。

    ``RG.get_cells`` 在表没加载时返回 ``None`` 而不是报错——直接调会拿到
    空结果还以为这干员没范围。所以这里必须先 ``load_range_table``。
    """
    global _TABLE, _TABLE_PATH
    if _TABLE is not None:
        return _TABLE
    path = _first_file("range_table.json")
    _TABLE_PATH = path
    if path:
        try:
            RG.load_range_table(path)
        except Exception:                                    # noqa: BLE001
            pass
    try:
        _TABLE = RG.get_range_table() or {}
    except Exception:                                        # noqa: BLE001
        _TABLE = {}
    return _TABLE


def _chars() -> dict:
    global _CHAR, _CHAR_PATH
    if _CHAR is not None:
        return _CHAR
    path = _first_file("char_ranges.json")
    _CHAR_PATH = path
    data = {}
    if path:
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (OSError, ValueError):
            data = {}
    if not isinstance(data, dict):
        data = {}
    _CHAR = data
    return _CHAR


def _facing(v: Any) -> Optional[str]:
    s = str(v or "RIGHT").strip().lower()
    return _FACING.get(s, None)


def _grid(cells: List[Tuple[int, int]], center: bool = True) -> List[str]:
    """把偏移画成字符画：``O`` 是干员自己，``X`` 是覆盖格，``.`` 是空。"""
    if not cells:
        return []
    rows = [c[0] for c in cells] + ([0] if center else [])
    cols = [c[1] for c in cells] + ([0] if center else [])
    r0, r1 = min(rows), max(rows)
    c0, c1 = min(cols), max(cols)
    cov = set(cells)
    art: List[str] = []
    for r in range(r0, r1 + 1):
        line = []
        for c in range(c0, c1 + 1):
            if r == 0 and c == 0:
                line.append("O")
            elif (r, c) in cov:
                line.append("X")
            else:
                line.append(".")
        art.append("".join(line))
    return art


def _range_ids() -> List[str]:
    return sorted(_table().keys())


def _char_range_info(char_id: str) -> Dict[str, Any]:
    m = _chars().get(char_id)
    if not isinstance(m, dict):
        return {}
    return {str(k): v for k, v in m.items()}


def _elite_ids(info: Dict[str, Any]) -> Dict[str, str]:
    """"精英 0/1/2" -> rangeId。个别干员某阶段没记录就沿用上一阶段。"""
    out: Dict[str, str] = {}
    last = ""
    for e in ("0", "1", "2"):
        v = info.get(e) or last
        if v:
            out[e] = v
            last = v
    return out


def _cells_of(range_id: str, facing: str) -> Optional[List[Tuple[int, int]]]:
    _table()
    try:
        cells = RG.get_cells(range_id, facing)
    except Exception:                                        # noqa: BLE001
        return None
    if cells is None:
        return None
    return sorted((int(r), int(c)) for r, c in cells)


def _abs_cells(cells: List[Tuple[int, int]], row: int, col: int) -> List[List[int]]:
    return [[row + r, col + c] for r, c in cells]


@tool(
    "operator_range",
    "攻击范围",
    "某干员站在某个格子上能打到哪些格子。给 operator（或直接给 range_id）"
    "加上朝向，返回格偏移清单 + 字符画；带 row/col 时换算成地图绝对坐标，"
    "还能顺便判断几个目标格在不在范围内。对应「这个位置能不能同时覆盖两路」。",
    {
        "type": "object",
        "properties": {
            "operator": {"type": "string",
                         "description": "干员名 / char_id，如 银灰 / char_172_svrash"},
            "range_id": {"type": "string",
                         "description": "直接指定 rangeId（3-1 等），给了就不查干员"},
            "elite": {"type": "integer", "minimum": 0, "maximum": 2,
                      "description": "精英化阶段 0/1/2，默认取最高（多数干员 E2）"},
            "facing": {"type": "string",
                       "description": "朝向：RIGHT/LEFT/UP/DOWN（默认 RIGHT），"
                                      "也认 右/左/上/下"},
            "row": {"type": "integer",
                    "description": "干员所在地图行（给 row+col 才算绝对坐标）"},
            "col": {"type": "integer", "description": "干员所在地图列"},
            "targets": {"type": "array",
                        "description": "要判断是否被覆盖的格子 [[row,col], ...]",
                        "items": {"type": "array", "items": {"type": "integer"}}},
            "as_art": {"type": "boolean",
                       "description": "是否返回字符画，默认 true"},
        },
        "additionalProperties": False,
    },
)
def operator_range(args: dict) -> dict:
    facing = _facing(args.get("facing"))
    if facing is None:
        return error("facing 只能是 RIGHT/LEFT/UP/DOWN（或 右/左/上/下）")

    rid = str(args.get("range_id") or "").strip()
    op_name = ""
    char_id = ""
    phases: Dict[str, str] = {}
    elite_used: Optional[int] = None

    if not rid:
        q = str(args.get("operator") or "").strip()
        if not q:
            return error("要给 operator 或 range_id")
        from . import tool_operators as TO
        op_name = TO._resolve(q) or ""
        if not op_name:
            return error("找不到干员：%r。先用 operator_search 搜一下。" % q)
        rec = common.require_operators().data.get(op_name) or {}
        char_id = str(rec.get("char_id") or "")
        phases = _elite_ids(_char_range_info(char_id))
        if not phases:
            return error(
                "干员 %s（%s）在 char_ranges.json 里没有范围记录。"
                "这类通常是召唤物/装置，或者缓存缺这一条；"
                "可以直接传 range_id 指定范围。" % (op_name, char_id or "无 char_id"))
        elite = args.get("elite")
        if elite is None:
            elite = max(int(e) for e in phases)
        elite = int(elite)
        rid = phases.get(str(elite)) or phases.get(str(max(int(e) for e in phases)))
        elite_used = elite
    else:
        if rid not in _table():
            return error("range_id %r 不存在。可用：%s"
                         % (rid, ", ".join(_range_ids()[:40]) + " ..."))

    cells = _cells_of(rid, facing)
    if cells is None:
        return error("range_id %r 读取失败（range_table.json 没有加载成功）" % rid)

    payload: Dict[str, Any] = {
        "range_id": rid,
        "facing": facing,
        "cell_count": len(cells),
        "cells": [list(c) for c in cells],
        "cells_note": "相对干员自身格子的 (行偏移, 列偏移)，行向下为正、列向右为正",
    }
    if op_name:
        payload["operator"] = op_name
        payload["char_id"] = char_id
        payload["elite"] = elite_used
        payload["range_by_elite"] = phases
    if args.get("as_art") is not False:
        payload["art"] = _grid(cells)

    row = args.get("row")
    col = args.get("col")
    if row is not None and col is not None:
        try:
            r0, c0 = int(row), int(col)
        except (TypeError, ValueError):
            return error("row / col 要是整数")
        abs_cells = _abs_cells(cells, r0, c0)
        payload["origin"] = [r0, c0]
        payload["abs_cells"] = abs_cells
        payload["abs_note"] = ("地图绝对坐标 (row, col)，可直接和 map_get 的"
                               "格位、或 stage_field_at 的 cell 对照")
        tg = args.get("targets") or []
        if tg:
            hits = []
            for t in tg:
                try:
                    tr, tc = int(t[0]), int(t[1])
                except (TypeError, ValueError, IndexError):
                    continue
                hits.append({"cell": [tr, tc],
                             "covered": [tr, tc] in abs_cells})
            payload["targets"] = hits
            payload["targets_note"] = "covered=true 表示这格在范围内"
    elif args.get("targets"):
        return error("判断 targets 需要同时给 row 和 col（干员所在位置）")
    return ok(payload)


@tool(
    "operator_range_list",
    "攻击范围表 / 干员范围查询",
    "查范围表现状：有哪些 rangeId、某干员各精英化的 rangeId。"
    "operator_range 报错时先查这个。",
    {
        "type": "object",
        "properties": {
            "operator": {"type": "string",
                         "description": "给干员名则只查这一位（大小写/模糊）"},
            "limit": {"type": "integer", "minimum": 1,
                      "description": "列多少个 rangeId，默认 80"},
        },
        "additionalProperties": False,
    },
)
def operator_range_list(args: dict) -> dict:
    table = _table()
    q = str(args.get("operator") or "").strip()
    if q:
        from . import tool_operators as TO
        op_name = TO._resolve(q) or ""
        if not op_name:
            return error("找不到干员：%r" % q)
        rec = common.require_operators().data.get(op_name) or {}
        char_id = str(rec.get("char_id") or "")
        return ok({"operator": op_name, "char_id": char_id,
                   "range_by_elite": _elite_ids(_char_range_info(char_id)),
                   "char_ranges_loaded": bool(_chars()),
                   "note": "空表示 char_ranges.json 里没有这位（召唤物/装置）"})
    limit = max(1, min(int(args.get("limit") or 80), 200))
    ids = _range_ids()[:limit]
    shapes = {i: len(_cells_of(i, "RIGHT") or []) for i in ids}
    return ok({
        "loaded": bool(table),
        "path": _TABLE_PATH or None,
        "range_ids": ids,
        "total": len(table),
        "cell_counts": shapes,
        "char_ranges_path": _CHAR_PATH or None,
        "char_count": len(_chars()),
        "note": ("空表 = 打包时漏了 range_table.json（要同时加进 spec 的 "
                 "table_files 和 Paths.seed_if_needed 白名单）"),
    })