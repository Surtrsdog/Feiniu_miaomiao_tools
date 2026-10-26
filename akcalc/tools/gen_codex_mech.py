# -*- coding: utf-8 -*-
"""生成 codex_fields.json 的 mechanics 段（活动关卡特殊机制图鉴）。

数据全部来自本地缓存，不联网：
* mapData.tiles[].tileKey  —— 地块机关（传送门、火山、坑洞……）
* options.configBlackBoard —— 关卡配置机制（战争迷雾、球赛规则……）

用法：python akcalc/tools/gen_codex_mech.py
"""
import collections
import glob
import io
import json
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)              # akcalc/
DATA = os.path.join(ROOT, "data")
LEVELS = os.path.join(DATA, "cache", "levels")

sys.path.insert(0, os.path.dirname(ROOT))
from akcalc.core import mechanisms as M


def load_zone_names():
    p = os.path.join(DATA, "cache", "zone_table.json")
    if not os.path.exists(p):
        return {}
    z = json.load(io.open(p, encoding="utf-8")).get("zones") or {}
    out = {}
    for k, v in z.items():
        m = re.match(r"^(act\d+[a-z]+)_?zone", k) or \
            re.match(r"^(act\d+[a-z]+\d+)_?zone", k)
        if m:
            nm = v.get("zoneNameSecond") or v.get("zoneNameFirst")
            if nm:
                out.setdefault(m.group(1), nm)
    return out


def activity_of(lid, zone_names):
    m = re.match(r"^(act\d+[a-z]+)", lid)
    if not m:
        return None
    b = m.group(1)
    if b in zone_names:
        return zone_names[b]
    for x, nm in zone_names.items():
        if x.startswith(b):
            return nm
    return None


def scan_levels():
    tile = collections.defaultdict(set)
    cfg = collections.defaultdict(set)
    for f in glob.glob(os.path.join(LEVELS, "*.json")):
        lid = os.path.basename(f)[:-5]
        try:
            d = json.load(io.open(f, encoding="utf-8"))
        except Exception:
            continue
        for t in ((d.get("mapData") or {}).get("tiles") or []):
            if isinstance(t, dict):
                k = t.get("tileKey") or ""
                if k in M.MECHANISMS:
                    tile[k].add(lid)
        for it in ((d.get("options") or {}).get("configBlackBoard") or []):
            cfg[it.get("key") or "?"].add(lid)
    return tile, cfg


CFG_DOC = {
    "enable_war_fog": ("战争迷雾", "视野被遮蔽，只能看到干员周围一小圈；未探索区域不显示敌人。", "视野"),
    "disable_character_gbuff": ("禁用干员全局增益", "本关不接受来自其他系统的干员 buff，面板数值即实战数值。", "规则"),
    "disable_enemy_gbuff": ("禁用敌人全局增益", "同理，敌人数值不被外部 buff 改写。", "规则"),
    "fallback_trap": ("兜底陷阱", "干员格被占据时补偿放置的陷阱，常见于「壶」类玩法。", "布阵"),
    "roll_when_select": ("选择时随机", "每次选人时重新随机，不能靠固定路线刷。", "随机"),
    "vase_start_character_count": ("初始携壶干员数", "开局带多少个「壶」单位，决定可放置次数。", "布阵"),
    "vase_character_vase_count": ("每人携壶数", "每个干员可以携带的壶数量上限。", "布阵"),
    "stadium_type": ("场地类型", "球赛玩法的场地模板，决定球门与边线布局。", "球赛"),
    "team_type": ("队伍类型", "球赛玩法的队伍配置。", "球赛"),
    "win_goal_difference": ("取胜净胜球", "净胜球达到该值即判胜。", "球赛"),
    "delta_buildable_cnt_penalty": ("可部署位惩罚", "每多占一个可部署位带来的额外代价。", "布阵"),
    "leftBoss": ("左侧 Boss 权重", "自走棋玩法里左侧 Boss 的出现权重。", "自走棋"),
    "rightBoss": ("右侧 Boss 权重", "自走棋玩法里右侧 Boss 的出现权重。", "自走棋"),
    "leftNormal": ("左侧普通权重", "自走棋左侧普通单位的权重。", "自走棋"),
    "rightNormal": ("右侧普通权重", "自走棋右侧普通单位的权重。", "自走棋"),
    "dialog_before_battle": ("战前剧情", "进场时播放的剧情文件。", "剧情"),
    "dialog_after_battle": ("战后剧情", "通关后播放的剧情文件。", "剧情"),
    "enemy_camera_param": ("敌方镜头参数", "自走棋观战镜头，不影响数值。", "自走棋"),
    "player_map_lr_boundary_col": ("玩家图左右边界", "自走棋玩家棋盘的分列边界。", "自走棋"),
    "player_map_lr_offset": ("玩家图左右偏移", "棋盘绘制偏移量。", "自走棋"),
    "player_map_ud_offset": ("玩家图上下偏移", "棋盘绘制偏移量。", "自走棋"),
}

CFG_SKIP = re.compile(
    r"^(rect_\d+|CAMERA_|default_pos|default_size|enemy_pos|enemy_size|"
    r"enemy_place_rect|battle_pos|battle_size|coin_panel_pos|"
    r"construct_view_scale|move_time|.*camera_param$)")


def build_mechanics(tile_use, cfg_use, zone_names):
    out = []
    for key, (cat, cn, desc) in M.MECHANISMS.items():
        lids = sorted(tile_use.get(key) or ())
        acts = sorted({a for a in (activity_of(x, zone_names) for x in lids) if a})
        rec = {
            "name": cn,
            "category": "活动机制·" + M.CATEGORY_CN.get(cat, cat),
            "kind": "地块机关",
            "desc": desc,
            "data": "mapData.tiles[].tileKey == %s" % key,
            "impl": "akcalc/core/mechanisms.py 的 MECHANISMS 表；寻路分析把它 "
                    "画成机关图层，除可通行判定外不改变路线几何。",
            "events": acts[:40],
            "stages": lids[:60],
        }
        if not lids:
            rec["pitfall"] = ("本批 1836 个关卡缓存里没有出现过这个 tileKey，"
                              "可能是旧版本残留，或只在未缓存的活动里使用。")
        elif acts:
            rec["desc"] = "%s（见于 %d 个关卡、%d 个活动）" % (
                desc, len(lids), len(acts))
        out.append(rec)

    for key, lidset in cfg_use.items():
        if CFG_SKIP.match(key) or key not in CFG_DOC:
            continue
        cn, desc, cat = CFG_DOC[key]
        lids = sorted(lidset)
        acts = sorted({a for a in (activity_of(x, zone_names) for x in lids) if a})
        out.append({
            "name": cn,
            "category": "活动机制·" + cat,
            "kind": "关卡配置",
            "desc": desc,
            "data": "options.configBlackBoard[] 中 key == %s" % key,
            "impl": "本项只作说明，不改变寻路与伤害计算。",
            "events": acts[:40],
            "stages": lids[:60],
        })
    out.sort(key=lambda r: (r["category"], r["name"]))
    return out


def main():
    zone_names = load_zone_names()
    tile_use, cfg_use = scan_levels()
    mechs = build_mechanics(tile_use, cfg_use, zone_names)
    p = os.path.join(DATA, "codex_fields.json")
    d = json.load(io.open(p, encoding="utf-8"))
    d["mechanics"] = mechs
    d["stats"]["mechanics"] = len(mechs)
    d["stats"]["mechanics_tile"] = sum(1 for m in mechs if m["kind"] == "地块机关")
    d["stats"]["mechanics_cfg"] = sum(1 for m in mechs if m["kind"] == "关卡配置")
    json.dump(d, io.open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("机制条目 %d（地块 %d / 配置 %d） -> %s" % (
        len(mechs), d["stats"]["mechanics_tile"],
        d["stats"]["mechanics_cfg"], p))


if __name__ == "__main__":
    main()
