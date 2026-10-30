# -*- coding: utf-8 -*-
"""攻击范围模块（B4 §7）。"""
from __future__ import annotations
import json, os
from typing import Dict, List, Optional, Set, Tuple

_range_data = None
_range_path = None
_char_ranges = None
_char_ranges_path = None

def _load_range_table(path):
    global _range_data, _range_path
    if _range_data is not None and _range_path == path:
        return _range_data
    with open(path, "r", encoding="utf-8") as f:
        raw = json.load(f)
    out = {}
    for rid, rec in raw.items():
        grids = [(int(g["row"]), int(g["col"])) for g in rec.get("grids", [])]
        out[rid] = {"id": rid, "direction": int(rec.get("direction", 1)), "grids": grids}
    _range_data = out
    _range_path = path
    return out

def get_range_table():
    return _range_data or {}

def load_range_table(path):
    return _load_range_table(path)

def rotate_cells(cells, facing):
    if facing == "RIGHT": return set(cells)
    if facing == "DOWN":  return {(c, -r) for r, c in cells}
    if facing == "LEFT":  return {(-r, -c) for r, c in cells}
    if facing == "UP":    return {(-c, r) for r, c in cells}
    return set(cells)

def get_cells(range_id, facing="RIGHT"):
    tbl = _range_data
    if tbl is None: return None
    rec = tbl.get(range_id)
    if rec is None: return None
    return rotate_cells(rec["grids"], facing)

def range_exists(range_id):
    return (_range_data is not None) and (range_id in _range_data)

def _build_char_ranges(char_table_path, cache_output):
    """从 character_table.json 抽出 char_id → {elite: rangeId}。

    character_table.json 的 phases 是 list（不是 dict），
    rangeId 直接在 phases[i] 上（不在 level 内部）。
    """
    global _char_ranges, _char_ranges_path
    with open(char_table_path, "r", encoding="utf-8") as f:
        raw = json.load(f)
    out = {}
    for char_key, char_rec in raw.items():
        if not isinstance(char_rec, dict):
            continue
        # character_table 的 key 就是 char_id（如 char_102_texas）
        cid = char_key
        # 也尝试 "key" 字段作为备选
        if not cid or not cid.startswith("char_"):
            cid = char_rec.get("key") or ""
        if not cid.startswith("char_"):
            continue
        phases = char_rec.get("phases")
        if not isinstance(phases, list) or not phases:
            continue
        phase_map = {}
        for idx, p in enumerate(phases):
            if not isinstance(p, dict):
                continue
            rid = p.get("rangeId")
            if rid:
                phase_map[str(idx)] = str(rid)
        if phase_map:
            out[cid] = phase_map
    d = os.path.dirname(cache_output)
    if d:
        os.makedirs(d, exist_ok=True)
    with open(cache_output, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    _char_ranges = out
    _char_ranges_path = cache_output
    return out

def load_char_ranges(cache_path):
    global _char_ranges, _char_ranges_path
    if _char_ranges is not None and _char_ranges_path == cache_path:
        return _char_ranges or {}
    try:
        with open(cache_path, "r", encoding="utf-8") as f:
            _char_ranges = json.load(f)
        _char_ranges_path = cache_path
        return _char_ranges or {}
    except Exception:
        _char_ranges = {}; _char_ranges_path = cache_path; return {}

def get_char_range_id(char_id, elite_phase="0"):
    if _char_ranges is None: return None
    pm = _char_ranges.get(char_id)
    if pm is None: return None
    r = pm.get(elite_phase)
    if r: return r
    for pk in ("2","1","0"):
        r = pm.get(pk)
        if r: return r
    return None