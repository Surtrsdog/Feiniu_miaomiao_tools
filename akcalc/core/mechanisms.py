# -*- coding: utf-8 -*-
"""关卡机制（地形机关）识别：把 tileKey 翻译成人看得懂的机关。

为什么需要这一层
----------------
``mapData.tiles[].tileKey`` 是 96 个英文资源名（``tile_telin`` /
``tile_gazebo`` / ``tile_volcano`` ...），寻路分析原来只认红门/蓝门/
可走/不可走四类，其余全部当普通地面 —— 于是「这条路线会不会被传送」
「会不会踩到火山」这类问题完全看不出来。

这个模块负责三件事：

1. **分类**：把 96 个 tileKey 归到「传送 / 陷阱 / 增益 / 阻挡 / 特殊」
   五类，并给出中文名与说明。
2. **配对**：把传送门入口（``tile_telin``）与出口（``tile_telout``）
   按 ``tiles[].blackboard`` 里的 ``tile`` / ``mode`` 参数配成一组。
   解包里两者靠 blackboard 的 ``tile`` 序号对应，而不是靠坐标相邻。
3. **受影响判定**：给定一条路线的格子序列，算出它经过哪些机关。

数据来源全部是本地关卡缓存，不联网。
"""
from __future__ import annotations

import itertools
from typing import Dict, List, Optional, Sequence, Tuple

#: 机关大类 -> 显示名与配色（配色与 map_render 的调色板对齐）
CATEGORY_CN = {
    "portal": "传送",
    "trap": "危险地形",
    "buff": "增益地形",
    "wall": "阻挡 / 障碍",
    "special": "特殊机制",
}

#: 传送门用同一色系的两个深浅色区分入口/出口
PORTAL_IN = "tile_telin"
PORTAL_OUT = "tile_telout"

#: tileKey -> (大类, 中文名, 一句话说明)
#: 只收录「有机制含义」的格子；tile_road / tile_floor / tile_wall 等
#: 基础地形不在这里（它们是地图底板，不是机关）。
MECHANISMS: Dict[str, Tuple[str, str, str]] = {
    # ---------------------------------------------------------- 传送
    "tile_telin": ("portal", "传送入口", "踩上去会被传送到配对的出口格"),
    "tile_telout": ("portal", "传送出口", "入口配对的落点，本身不触发传送"),
    "tile_rabbithole_in_1": ("portal", "兔洞入口 1", "act53side 的兔洞，传送到 out_1"),
    "tile_rabbithole_out_1": ("portal", "兔洞出口 1", "兔洞入口 1 的落点"),
    "tile_rabbithole_out_2": ("portal", "兔洞出口 2", "兔洞的另一落点（二分岔）"),
    "tile_stairs": ("portal", "楼梯", "连接上下层的通路，跨层移动"),

    # ---------------------------------------------------------- 危险地形
    "tile_hole": ("trap", "落穴 / 深坑", "无底洞，掉下去即离场（飞行单位不落）"),
    "tile_volcano": ("trap", "火山口", "定时喷发，对范围内单位造成伤害"),
    "tile_volcano_emp": ("trap", "火山口（EMP）", "喷发时附带电磁脉冲效果"),
    "tile_corrosion": ("trap", "腐蚀地面", "站上去持续掉血，防御下降"),
    "tile_smog": ("trap", "毒雾", "持续造成法术伤害并降低命中"),
    "tile_toxic": ("trap", "毒性地面", "造成持续伤害"),
    "tile_toxicwall": ("trap", "毒墙", "墙体版毒性地形，不可通行且相邻受伤"),
    "tile_toxicroad": ("trap", "毒性地板", "可通行但持续掉血"),
    "tile_toxichill": ("trap", "寒毒地面", "同时附带减速与持续伤害"),
    "tile_deepwater": ("trap", "深水", "行走速度大幅下降，部分单位无法进入"),
    "tile_deepsea": ("trap", "深海", "深海地形，附带额外规则（如涨潮）"),
    "tile_mire": ("trap", "泥沼", "移动速度降低"),
    "tile_quicksand": ("trap", "流沙", "持续下沉，需要及时离开"),
    "tile_icetur": ("trap", "冰面（可转向）", "滑行改变朝向"),
    "tile_icestr": ("trap", "冰面（直线）", "强制沿直线滑行"),
    "tile_icetur_road": ("trap", "冰面道路", "冰面与道路的混合地形"),
    "tile_ice_road": ("trap", "结冰道路", "打滑，移动方向难以改变"),
    "tile_frost": ("trap", "霜冻地面", "附带寒冷效果"),
    "tile_burn": ("trap", "灼烧地面", "持续造成灼燃伤害"),
    "tile_infection": ("trap", "感染地面", "站上去会累积感染值"),
    "tile_infection_dqq": ("trap", "感染地面（DQQ）", "特殊玩法里的感染地形"),
    "tile_creep": ("trap", "菌毯", "敌方单位在菌毯上获得增益"),
    "tile_creepf": ("trap", "菌毯（飞行）", "飞行单位版菌毯"),
    "tile_forbidden": ("wall", "不可通行", "地图边界与禁入区，任何单位都不能过"),
    "tile_passable_wall": ("wall", "可破坏墙", "需要破坏后才能通行"),
    "tile_passable_wall_only_stops_fly": ("wall", "只挡飞行的墙", "地面可过、飞行不可过"),
    "tile_wooden_wall": ("wall", "木墙", "可被破坏的木质障碍"),
    "tile_alchemy_wall": ("wall", "炼金造物墙", "活动机制的临时墙体"),
    "tile_fence": ("wall", "栅栏", "不可通行的矮障碍"),
    "tile_fence_bound": ("wall", "边界栅栏", "地图边缘的围栏"),

    # ---------------------------------------------------------- 增益地形
    "tile_healing": ("buff", "治疗地面", "站上去每秒回复生命"),
    "tile_defup": ("buff", "防御强化地面", "站上去获得防御加成"),
    "tile_defbreak": ("buff", "防御削弱地面", "站上去防御被削弱（负面）"),
    "tile_atkup": ("buff", "攻击强化地面", "站上去获得攻击加成"),
    "tile_spup": ("buff", "技力回复地面", "站上去加速技力回复"),
    "tile_reed": ("buff", "芦苇丛", "可隐蔽，降低被索敌概率"),
    "tile_reedw": ("buff", "芦苇丛（宽）", "芦苇丛的宽版"),
    "tile_reedf": ("buff", "芦苇丛（飞行）", "飞行单位的隐蔽地形"),
    "tile_grass": ("buff", "草丛", "可隐蔽"),
    "tile_sleep_road": ("buff", "睡眠地面", "站上去进入睡眠（可回血）"),
    "tile_sleep_wall": ("buff", "睡眠墙", "睡眠地面旁的墙体"),

    # ---------------------------------------------------------- 特殊机制
    "tile_gazebo": ("special", "留声机", "激活后对所有单位施加增益/减益（看 blackboard）"),
    "tile_grvtybtn": ("special", "重力按钮", "踩下后切换重力方向 / 开启通路"),
    "tile_yinyang_switch": ("special", "阴阳开关", "切换阴阳状态，改变属性加成"),
    "tile_yinyang_road": ("special", "阴阳地面", "阴阳状态影响属性"),
    "tile_yinyang_wall": ("special", "阴阳墙", "随阴阳状态开合"),
    "tile_magic_circle": ("special", "魔法阵", "召唤 / 强化法阵"),
    "tile_magic_circle_h": ("special", "魔法阵（高台）", "高台版魔法阵"),
    "tile_balloon": ("special", "气球", "可被击破，落下改变地形"),
    "tile_balloon_fbd": ("special", "气球（禁飞区）", "气球 + 禁飞区机制"),
    "tile_acshop": ("special", "商店格", "可交互购买（活动机制）"),
    "tile_act27side": ("special", "act27side 机关", "活动专属机关地形"),
    "tile_act48side": ("special", "act48side 机关", "活动专属机关地形"),
    "tile_bnspck_road": ("special", "资源包地面", "携带资源包时才有意义的特殊地面"),
    "tile_cnvfuse": ("special", "传送带", "强制沿带方向移动"),
    "tile_cnvfuse_fbd": ("special", "传送带（禁放）", "传送带且禁止部署"),
    "tile_football": ("special", "足球场地面", "足球玩法专用地面"),
    "tile_bigforce": ("special", "强力弹簧", "提供大力度位移"),
    "tile_character": ("special", "角色预置格", "关卡预置干员的站位"),
    "tile_characterf": ("special", "角色预置格（飞行）", "飞行单位预置位"),
    "tile_merope": ("special", "墨罗佩", "活动专属机制地形"),
    "tile_rarope": ("special", "拉罗佩", "活动专属机制地形"),
    "tile_ristar_road": ("special", "星光地面", "星光活动机制地形"),
    "tile_ristar_road_forbidden": ("special", "星光禁行", "星光活动的禁行区"),
    "tile_alchemy_road": ("special", "炼金地面", "炼金活动机制地形"),
    "tile_woodrd": ("special", "木质通路", "可破坏的通路"),
    "tile_ftplant_road": ("special", "植物地面", "种植玩法机制地形"),
    "tile_replace_wall": ("special", "替换墙", "满足条件后变成墙 / 变回通路"),
    "tile_replace_road": ("special", "替换地面", "满足条件后被替换"),
    "tile_rcm_crate": ("special", "补给箱格", "可破坏的箱子占位"),
    "tile_rcm_operator": ("special", "干员预置格（RCM）", "RCM 玩法的干员站位"),
    "tile_empty": ("special", "空白格", "地图外空白，无地形"),
}

#: 大类 -> 渲染优先级（数字小的先画，避免机关被路线盖住）
DRAW_ORDER = {"wall": 0, "buff": 1, "trap": 2, "special": 3, "portal": 4}


def info(tile_key: str) -> Optional[Tuple[str, str, str]]:
    """返回 (大类, 中文名, 说明)；非机关地形返回 None。"""
    return MECHANISMS.get(tile_key or "")


def display_name(tile_key: str) -> str:
    rec = MECHANISMS.get(tile_key or "")
    return rec[1] if rec else (tile_key or "")


def category(tile_key: str) -> str:
    rec = MECHANISMS.get(tile_key or "")
    return rec[0] if rec else ""


def _bb_get(blackboard, key: str):
    """从 ``[{key,value,valueStr}]`` 里取一个值。"""
    for item in (blackboard or []):
        if isinstance(item, dict) and item.get("key") == key:
            v = item.get("value")
            return item.get("valueStr") if v is None else v
    return None


# summary() 里给参数配的中文标签，避免在界面上直接抛 raw key
_PARAM_CN = {
    "tile": "目标格",
    "mode": "模式",
    "interval": "间隔秒",
    "damage": "每跳伤害",
    "atk": "攻击倍率",
    "atk_scale": "攻击倍率",
    "attack_speed": "攻速",
    "move_speed": "移速",
    "duration": "持续秒",
    "prob": "概率",
    "interval_max": "最长间隔",
    "interval_min": "最短间隔",
    "special": "特殊",
    "def": "防御",
    "cd_min": "最短冷却",
    "cd_max": "最长冷却",
    "base_force_level": "力度等级",
    "HP_RECOVERY_PER_SEC_BY_MAX_HP_RATIO": "每秒回血(按上限)",
    "respawn_time": "重生秒",
    "value": "数值",
    "cooldown": "冷却秒",
    "attackspeed": "攻速",
    "dynamic": "动态",
    "falldown_stack_count": "下陷层数",
}


class Mechanism:
    """地图上的一个机关实例。"""

    __slots__ = ("row", "col", "tile_key", "cat", "name", "note",
                 "params", "pair_key")

    def __init__(self, row: int, col: int, tile_key: str,
                 params: Optional[dict] = None, pair_key: str = ""):
        self.row = int(row)
        self.col = int(col)
        self.tile_key = tile_key or ""
        rec = MECHANISMS.get(self.tile_key)
        self.cat = rec[0] if rec else "special"
        self.name = rec[1] if rec else (self.tile_key or "机关")
        self.note = rec[2] if rec else ""
        self.params = dict(params or {})
        self.pair_key = pair_key

    @property
    def pos(self) -> Tuple[int, int]:
        return (self.row, self.col)

    def summary(self) -> str:
        """一行摘要，给 tooltip / 状态栏用。"""
        s = self.name
        if self.pair_key:
            s += "（组 %s）" % self.pair_key
        if self.params:
            # 先按「界面最想先看到的」顺序取已知键，再补其它键
            order = ("tile", "mode", "interval", "damage", "atk", "atk_scale",
                     "attack_speed", "move_speed", "duration", "prob", "def",
                     "base_force_level", "HP_RECOVERY_PER_SEC_BY_MAX_HP_RATIO")
            keys = [k for k in order if k in self.params]
            keys += [k for k in self.params if k not in order]
            kv = []
            for k in keys:
                v = self.params[k]
                if isinstance(v, float) and abs(v - round(v)) < 1e-9:
                    v = int(round(v))
                kv.append("%s %s" % (_PARAM_CN.get(k, k), v))
                if len(kv) >= 4:
                    break
            if kv:
                s += "　" + " · ".join(kv)
        return s

    def __repr__(self) -> str:
        return "<Mechanism %s @%s>" % (self.tile_key, self.pos)


def extract(game_map) -> List[Mechanism]:
    """从 GameMap 抽出全部机关，并按传送门配对。

    ``game_map.tile_defs`` 保存了 ``mapData.tiles`` 原始定义（含
    blackboard），``game_map.tiles`` 已经过矩阵翻转把 tileKey 放到
    (row, col) 上。这里以 ``tiles`` 的坐标为准确位置，用 tile_defs
    里同 tileKey 的 blackboard 补参数。

    关键：**同一 tileKey 可以有多条 def，且参数不同**。
    例如 4-4 的 ``tile_infection`` 在 tiles 里出现两次（下标 33/56），
    原实现把同 key 的 blackboard 收进池子，发现池子不止一条就放弃
    （bb=None → params={}），于是悬停只剩「感染地面」四个字、
    看不到 damage 180 / duration 300 / atk_scale 0.5 / attack_speed 50。
    现在改为按每格自己的 ``tile.def_index`` 精确定位那一条 def。
    """
    if game_map is None:
        return []
    defs = getattr(game_map, "tile_defs", None) or []

    def _bb_for(tile) -> dict:
        """取该格自己的 blackboard；取不到再退回同 key 的唯一一份。"""
        # 注意：def_index 可以是 0，**不能**写成 `x or -1`，
        # 否则下标 0 会被当成「没有下标」丢掉。
        raw_idx = getattr(tile, "def_index", -1)
        idx = -1 if raw_idx is None else int(raw_idx)
        if 0 <= idx < len(defs):
            td = defs[idx]
            if isinstance(td, dict):
                bb = td.get("blackboard")
                if bb:
                    return bb
        key = getattr(tile, "tile_key", "") or ""
        cache = {}
        for td in defs:
            if isinstance(td, dict) and (td.get("tileKey") or "") == key:
                bb = td.get("blackboard")
                if bb:
                    cache[id(bb)] = bb
        # 只有在唯一时才能安全回退，否则宁可空着也不张冠李戴
        if len(cache) == 1:
            return next(iter(cache.values()))
        return {}

    out: List[Mechanism] = []
    seen = set()
    for row in (getattr(game_map, "tiles", None) or []):
        for tile in row:
            key = getattr(tile, "tile_key", "") or ""
            if key not in MECHANISMS:
                continue
            pos = (tile.row, tile.col)
            if pos in seen:
                continue
            seen.add(pos)
            bb = _bb_for(tile)
            # 全量收录 blackboard 键值，不再用白名单。
            # 白名单曾只留 13 个键，而解包里机关实际用过 40+ 种
            # （tile_defbreak 的 def、tile_bigforce 的 base_force_level、
            #  tile_healing 的 HP_RECOVERY_PER_SEC_BY_MAX_HP_RATIO…），
            # 导致 6029 个本应带参数的机关格里 3619 格退化成空。
            params: Dict[str, object] = {}
            for item in (bb or []):
                if not isinstance(item, dict):
                    continue
                k = item.get("key")
                if not k:
                    continue
                v = item.get("value")
                if v is None:
                    v = item.get("valueStr")
                if v is not None:
                    params[k] = v
            pair = ""
            if key in (PORTAL_IN, PORTAL_OUT):
                t = params.get("tile")
                pair = str(t) if t is not None else "?"
            out.append(Mechanism(tile.row, tile.col, key, params, pair))

    out.sort(key=lambda m: (DRAW_ORDER.get(m.cat, 9), m.row, m.col))
    return out


def group_by_cat(mechs: Sequence[Mechanism]) -> Dict[str, List[Mechanism]]:
    """按大类分组（保持渲染顺序）。"""
    out: Dict[str, List[Mechanism]] = {}
    for m in mechs:
        out.setdefault(m.cat, []).append(m)
    return out


def portals(mechs: Sequence[Mechanism]) -> List[Tuple[Mechanism, Mechanism, bool]]:
    """把传送门入口与出口配对成 (入口, 出口, 是否确定)。

    先说清楚一件事：**解包数据里没有收着一张配对表。**
    ``tile_telin`` / ``tile_telout`` 的 ``blackboard`` 在 1836 个关卡里
    只有 3 处非空（一个 ``act49side_boss_level_tile_mark`` 和一个
    ``mode``），也就是说入口到底通到哪个出口是由地图预制体里的组件
    决定的，JSON 导出时没有被带出来。因此这里只能**推断**：

    * 若入口与出口数量相等且都不超过 8 个（最大实测值是
      ``act2multi_05`` 的 8 个），用最小代价二分图匹配按曼哈顿距离
      配对 —— 这类关卡的传送门在线性布局里往往正好两两相邻，配出来
      的结果很稳。
    * 否则（数量不等 / 太多）退化成按出现顺序一对一，第三项标记为
      ``False`` 表示**只是猜的**，UI 上画成虚线。

    第三项就是「这个配对有多可信」。
    """
    ins = [m for m in mechs if m.tile_key == PORTAL_IN]
    outs = [m for m in mechs if m.tile_key == PORTAL_OUT]
    if not ins or not outs:
        return []

    def dist(a: Mechanism, b: Mechanism) -> int:
        return abs(a.row - b.row) + abs(a.col - b.col)

    # 数量相等且规模小 -> 最小代价匹配（暴力全排列，8! = 40320 可接受）
    if len(ins) == len(outs) and len(ins) <= 8:
        best: Optional[Tuple[int, List[int]]] = None
        for perm in itertools.permutations(range(len(outs))):
            total = sum(dist(ins[i], outs[perm[i]]) for i in range(len(ins)))
            if best is None or total < best[0]:
                best = (total, list(perm))
        if best is not None:
            return [(ins[i], outs[best[1][i]], True) for i in range(len(ins))]

    # 兜底：按出现顺序配对，标记为不确定
    pairs: List[Tuple[Mechanism, Mechanism, bool]] = []
    for i, a in enumerate(ins):
        if i < len(outs):
            pairs.append((a, outs[i], False))
    return pairs


def describe_level(game_map, limit: int = 6) -> List[str]:
    """给状态栏/提示用：这个关卡有哪些机制，各几个。"""
    mechs = extract(game_map)
    if not mechs:
        return []
    buckets = group_by_cat(mechs)
    lines = []
    for cat in ("portal", "trap", "buff", "wall", "special"):
        items = buckets.get(cat) or []
        if not items:
            continue
        names: Dict[str, int] = {}
        for m in items:
            names[m.name] = names.get(m.name, 0) + 1
        parts = ["%s×%d" % (n, c) for n, c in
                 sorted(names.items(), key=lambda kv: -kv[1])[:limit]]
        lines.append("%s：%s" % (CATEGORY_CN.get(cat, cat), "、".join(parts)))
    return lines
