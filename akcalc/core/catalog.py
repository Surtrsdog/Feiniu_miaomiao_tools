"""关卡目录：把全部关卡按「主线 / 活动 / 其他」分类，并提供下载路径。

数据来源
--------
stage_table.json（关卡表）+ zone_table.json（区域表），
以及 GitHub 文件树给出的**真实文件路径**——关卡 JSON 不在固定目录里：

    主线 / 资源 / 危机合约等 -> zh_CN/gamedata/levels/obt/<分类>/level_<id>.json
    活动关                  -> zh_CN/gamedata/levels/activities/<活动>/level_<id>.json

活动关的目录名取自 stage_table 里 zoneId 的前缀（如 act13d2_zone1
-> act13d2），实测与仓库目录一一对应，所以不用逐个探测。
"""
from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional, Tuple

#: 顶层分类的展示顺序与中文名。
#: 顺序与命名对齐 PRTS「关卡一览」与 map.ark-nights.com 的分区方式，
#: 玩家找图时的心智模型就是「主题曲 / 插曲 / 别传」，而不是活动 ID。
CATEGORY_ORDER = [
    ("main", "主题曲"),
    ("sidestory", "插曲"),
    ("branchline", "别传"),
    ("activity", "限时活动"),
    ("weekly", "资源收集"),
    ("campaign", "剿灭作战"),
    ("tower", "矢量突破"),
    ("crisis", "危机合约"),
    ("roguelike", "集成战略"),
    ("sandbox", "生息演算"),
    ("guide", "教学关卡"),
    ("other", "其他"),
]

#: 分类 -> 一句说明，显示在分类主菜单的卡片上
CATEGORY_DESC = {
    "main": "第 0~14 章主线剧情，按章节推进",
    "sidestory": "与主线剧情强关联的 Side Story",
    "branchline": "独立故事线的活动复刻（别传）",
    "activity": "限时活动关卡，含当期与往期",
    "weekly": "资源收集：经验、龙门币、芯片、技巧概要",
    "campaign": "剿灭作战：长周期大规模防守",
    "tower": "矢量突破 / CLIMB_TOWER 玩法",
    "crisis": "危机合约：赛季合约与常驻行动",
    "roguelike": "集成战略（肉鸽）关卡",
    "sandbox": "生息演算（沙盒）关卡",
    "guide": "新手引导与教学关",
    "other": "未归类的其他关卡",
}

#: zone.type -> 分类。官方 zone_table 里这一层就是 PRTS 的分区依据：
#: SIDESTORY=插曲，BRANCHLINE=别传，WEEKLY=资源收集……
_ZONE_TYPE_CATEGORY = {
    "MAINLINE": "main",
    "MAINLINE_ACTIVITY": "sidestory",
    "MAINLINE_RETRO": "sidestory",
    "SIDESTORY": "sidestory",
    "BRANCHLINE": "branchline",
    "ACTIVITY": "activity",
    "WEEKLY": "weekly",
    "CAMPAIGN": "campaign",
    "CLIMB_TOWER": "tower",
    "ROGUELIKE": "roguelike",
    "GUIDE": "guide",
}


@dataclass
class Stage:
    """一个关卡（目录条目）。"""

    stage_id: str
    code: str = ""
    name: str = ""
    zone_id: str = ""
    stage_type: str = ""
    category: str = "other"
    group_id: str = ""
    group_name: str = ""
    sub_name: str = ""
    path: str = ""
    difficulty: str = ""
    cost: int = 0
    cached: bool = False     # 本地已有地图文件，无需联网

    @property
    def label(self) -> str:
        if self.code and self.name:
            return "%s %s" % (self.code, self.name)
        return self.code or self.name or self.stage_id

    @property
    def is_variant(self) -> bool:
        """是否为磨难/突袭等高难变体。

        这类变体在 catalog 里 id 带 ``#f#``/``#t#`` 后缀，地形与出怪和
        普通版一致（仓库里也没有独立的地图文件），但掉落与敌人属性不同。
        """
        return "#" in self.stage_id or self.difficulty not in ("", "NORMAL")

    @property
    def difficulty_label(self) -> str:
        """难度的中文短标签，普通关返回空串。"""
        if self.difficulty == "FOUR_STAR":
            return "磨难"
        if self.difficulty == "SIX_STAR":
            return "突袭"
        return ""


@dataclass
class StageGroup:
    """二级分组（一章 / 一个活动）。"""

    group_id: str
    name: str
    category: str = "main"
    stages: List[Stage] = field(default_factory=list)

    @property
    def label(self) -> str:
        return "%s（%d 关）" % (self.name or self.group_id, len(self.stages))


_OBT_CATEGORIES = (
    "main", "hard", "campaign", "weekly", "crisis", "guide", "training",
    "memory", "legion", "promote", "recalrune", "roguelike", "rune",
    "sandbox", "activities",
)

#: 危机合约（常驻行动 / 赛季作战）的关卡不在 stage_table 的常规条目里，
#: 官方把它们放在 levels/obt/crisis/v2/level_crisis_v2_NN-MM.json，
#: 并且没有 code / name。这里内置赛季名与地图清单，
#: 让「危机合约」分类真的有关卡可选。
#: 第 15/16/17 章在新版数据里的 zone 名是「英文名 · 中文名」，
#: 前 14 章都是「第N章 · 中文名」。统一成后者，列表里才不会突兀。
MAINLINE_CHAPTER_NAMES = {
    "act2mainss_zone1": "第十五章 · 离解复合",
    "act3mainss_zone1": "第十六章 · 反常光谱",
    "act4mainss_zone1": "第十七章 · 相变临界",
}

#: 危机合约·经典赛季（旧版，共 13 届）与危机合约 2.0 赛季（共 5 届）的
#: 地图清单。两代合约的关卡都不在 stage_table 常规条目里，官方把地图放在
#: ``levels/obt/rune/level_rune_NN-MM.json``（经典）与
#: ``levels/obt/crisis/v2/level_crisis_v2_NN-MM.json``（2.0），
#: 且 JSON 里没有友好名，必须靠 PRTS 赛季页逐届核对。
#:
#: 每条为 ``(stage_id, 地图名, 常驻/轮换)``：
#: * 经典赛季：``rune_NN`` 编号与赛季一一对应，``rune_NN-01`` 是当届常驻地图，
#:   ``rune_NN-02``（若有）是当届新增轮换地图；荒芜行动（#0）没有自己编号的
#:   常驻图，常驻图沿用 02-02 破碎大道，轮换涵盖 rune_01 与 rune_02 全部 8 张。
#: * 2.0 赛季：``crisis_v2_NN`` 与赛季一一对应，``NN-01`` 为常驻图，其余为轮换；
#:   01-06 未被任何赛季引用（PRTS 页也仅标文件 id），归到浊燃作战名下。
CLASSIC_SEASONS = (
    ("荒芜行动", (
        ("rune_02-02", "破碎大道", "常驻"),
        ("rune_01-01", "荒芜广场", "轮换"),
        ("rune_01-02", "无人危楼", "轮换"),
        ("rune_01-03", "59区废墟", "轮换"),
        ("rune_02-01", "荒漠", "轮换"),
        ("rune_02-03", "新街", "轮换"),
        ("rune_02-04", "中转站", "轮换"),
        ("rune_02-05", "霜冻废墟", "轮换"),
    )),
    ("黄铁行动", (
        ("rune_03-01", "黄铁峡谷", "常驻"),
        ("rune_03-02", "军械库东", "轮换"),
    )),
    ("利刃行动", (
        ("rune_04-01", "荒废工厂", "常驻"),
    )),
    ("燃灰行动", (
        ("rune_05-01", "风蚀高地", "常驻"),
        ("rune_05-02", "6区废墟", "轮换"),
    )),
    ("铅封行动", (
        ("rune_06-01", "无序矿区", "常驻"),
        ("rune_06-02", "闭锁监狱", "轮换"),
    )),
    ("光谱行动", (
        ("rune_07-01", "八号竞技场", "常驻"),
    )),
    ("蛮鳞行动", (
        ("rune_08-01", "狂嚎沙原", "常驻"),
        ("rune_08-02", "遗弃地块", "轮换"),
    )),
    ("松烟行动", (
        ("rune_09-01", "灰齐山麓", "常驻"),
        ("rune_09-02", "炽热溶洞", "轮换"),
    )),
    ("寻昼行动", (
        ("rune_10-01", "大骑士领酒吧街", "常驻"),
        ("rune_10-02", "沙海遗迹", "轮换"),
    )),
    ("渊默行动", (
        ("rune_11-01", "盐风溶洞", "常驻"),
        ("rune_11-02", "尚蜀山道", "轮换"),
    )),
    ("尘环行动", (
        ("rune_12-01", "伦蒂尼姆边缘区块", "常驻"),
        ("rune_12-02", "小丘郡物流站", "轮换"),
    )),
    ("赝波行动", (
        ("rune_13-01", "在建沙滩", "常驻"),
        ("rune_13-02", "冻原矿场", "轮换"),
    )),
    ("起源行动", (
        ("rune_14-01", "无名庇护所", "常驻"),
        ("rune_14-02", "迷雾战区", "轮换"),
    )),
)

CRISIS_V2_SEASONS = (
    ("浊燃作战", (
        ("crisis_v2_01-01", "灰烬泽地", "常驻"),
        ("crisis_v2_01-02", "设防关隘", "轮换"),
        ("crisis_v2_01-03", "联邦监狱", "轮换"),
        ("crisis_v2_01-05", "翻修中沙滩", "轮换"),
        ("crisis_v2_01-06", "未命名地图", "轮换"),
        ("crisis_v2_01-07", "13区废墟", "轮换"),
    )),
    ("潮曦作战", (
        ("crisis_v2_02-01", "不朽厅堂", "常驻"),
        ("crisis_v2_02-02", "月落环巷", "轮换"),
        ("crisis_v2_02-03", "枯苇泥淖", "轮换"),
        ("crisis_v2_01-04", "实验基地封锁区", "轮换"),
    )),
    ("净罪作战", (
        ("crisis_v2_03-01", "浸血焦土", "常驻"),
        ("crisis_v2_03-02", "落尘狭路", "轮换"),
        ("crisis_v2_03-03", "蚀裂冰湖", "轮换"),
    )),
    ("弧光作战", (
        ("crisis_v2_04-01", "滞空焦点", "常驻"),
        ("crisis_v2_04-03", "熔炉检修口", "轮换"),
        ("crisis_v2_04-05", "巫诅骸地", "轮换"),
    )),
    ("涤墨作战", (
        ("crisis_v2_05-01", "墨染书阁", "常驻"),
        ("crisis_v2_05-03", "阴郁影棚", "轮换"),
        ("crisis_v2_05-05", "血刺坑道", "轮换"),
    )),
)

_ACT_RE = re.compile(r"^(act[0-9]+[a-z]*)")


def activity_dir(zone_id: str, stage_id: str) -> str:
    m = _ACT_RE.match(zone_id or "")
    if m:
        return m.group(1)
    m = _ACT_RE.match(stage_id or "")
    if m:
        return m.group(1)
    if "_" in (stage_id or ""):
        head = stage_id.split("_", 1)[0]
        if head.startswith("a") and head[1:].isdigit():
            return head
    return ""


def guess_path(stage_id: str, zone_id: str = "",
               stage_type: str = "") -> str:
    adir = activity_dir(zone_id, stage_id)
    if adir and (stage_type == "ACTIVITY" or adir.startswith("act")):
        return "levels/activities/%s/level_%s.json" % (adir, stage_id)
    if stage_id.startswith("crisis_v2_"):
        return "levels/obt/crisis/v2/level_%s.json" % stage_id
    head = stage_id.split("_", 1)[0] if "_" in stage_id else ""
    cat = head if head in _OBT_CATEGORIES else "main"
    return "levels/obt/%s/level_%s.json" % (cat, stage_id)


def classify(stage_type: str, stage_id: str, zone_id: str,
             zone_type: str = "") -> str:
    """判断顶层分类。

    优先用 zone_table 的 ``type``（官方分区，与 PRTS 一致：SIDESTORY
    是插曲、BRANCHLINE 是别传），没有再退回 stage_type 与 id 前缀。
    """
    zt = (zone_type or "").upper()
    st0 = (stage_type or "").upper()
    head = (stage_id or "").split("_", 1)[0]

    # id 前缀比 zone.type 更贴近玩家认知：
    #   hard_* 是主线高难（H 系列），zone 却挂在 MAINLINE 章节下。
    #   按需求「磨难去掉」：H 系列直接并入主题曲，不再单独成卡。
    # 注意 main_* 不能一律当主题曲：第 15/16/17 章的 id 也是 main_NN-*，
    # 但它们的 zone 是 MAINLINE_ACTIVITY（离解复合 / 反常光谱 /
    # 相变临界这三个「插曲」章节），必须交给下面的 zone.type 判断。
    if head == "hard":
        return "main"
    if head == "crisis":
        return "crisis"
    if head == "tower":
        return "tower"
    # 第 15/16/17 章的关卡 id 同样是 main_NN-*，但 zone 被官方挂在
    # actNmainss_zone 下（zone.type = MAINLINE_ACTIVITY）。这些仍然是
    # 主线章节，之前一律当插曲，导致主题曲里看不到第十五章以后的内容。
    if head == "main":
        return "main"

    if zt in _ZONE_TYPE_CATEGORY:
        cat = _ZONE_TYPE_CATEGORY[zt]
        # SUB（S3-1 这类支线前哨）与 SPECIAL_STORY（EG-3）虽然
        # stageType 不是 MAIN，但 zone 明确挂在 MAINLINE 章节下，
        # 属于主题曲的一部分，不应被当成插曲/别传。
        if cat == "main" and st0 in ("SUB", "SPECIAL_STORY", "MAIN"):
            return "main"
        return cat

    st = st0
    if st == "MAIN":
        return "main"
    if st in ("SUB", "SPECIAL_STORY"):
        return "main"
    if st == "ACTIVITY":
        return "activity"
    if st == "CLIMB_TOWER":
        return "tower"
    if st == "CAMPAIGN":
        return "campaign"
    if st == "DAILY":
        return "weekly"
    if st == "GUIDE":
        return "guide"
    return "other"


# 官方 zone_table 里 zoneName 全为空的活动（自走棋等玩法），
# 靠关卡名也推不出来（关卡 name 为空或就是 AC-1 这种代号）。
# 这里按活动 ID 补一张静态表，避免下拉里出现裸的 act1autochess。
_ZONE_ALIAS = {
    "act1autochess": "自走棋·新手教学",
    "act1vautochess": "自走棋·联机对战",
    "act2autochess": "自走棋·第二期",
}


def _alias_group_name(group_id: str) -> str:
    """按活动 ID 前缀查静态别名表。"""
    if not group_id:
        return ""
    key = group_id.split("_")[0].lower()
    return _ZONE_ALIAS.get(key, "")


def _derive_group_name(stages: List["Stage"]) -> str:
    """zone 表没给名字时，用组内关卡 name 的众数当组名。

    活动关的 name 字段通常是活动中文名（如「奇象收录时间！」），
    比裸的 act1arkhub 好读得多。
    """
    from collections import Counter
    cnt = Counter()
    for st in stages:
        nm = (st.name or "").strip()
        if nm and not nm.isascii():
            cnt[nm] += 1
    if not cnt:
        return ""
    best, _n = cnt.most_common(1)[0]
    return best


def _zone_group_name(zone: dict) -> str:
    first = zone.get("zoneNameFirst") or ""
    second = zone.get("zoneNameSecond") or ""
    third = zone.get("zoneNameThird") or ""
    if first and second:
        return "%s · %s" % (first, second)
    if second and third:
        return "%s · %s" % (second, third)
    return second or first or third or ""


def build_permanent_names(zone_table: dict):
    """收集「插曲 / 别传」永久分区的名字集合。

    游戏里活动结束后会进常驻，官方为此准备了 ``permanent_main_*``
    （插曲，与主线剧情关联）和 ``permanent_sub_*``（别传，独立故事线）
    两组分区。但这些分区本身**不挂任何关卡**，真实关卡仍在
    ``actXXXX_zoneN`` 上，两者靠 ``zoneNameSecond`` 同名对应
    （实测 20 个别传分区名 100% 命中）。

    返回 (插曲名集合, 别传名集合)。
    """
    zones = (zone_table or {}).get("zones") or {}
    sidestory, branchline = set(), set()
    for zid, z in zones.items():
        name = (z.get("zoneNameSecond") or "").strip()
        if not name:
            continue
        if zid.startswith("permanent_main"):
            sidestory.add(name)
        elif zid.startswith("permanent_sub"):
            branchline.add(name)
    return sidestory, branchline


class StageCatalog:
    """全部关卡的分类目录（离线可用，构建一次后缓存）。"""

    def __init__(self) -> None:
        self.stages: Dict[str, Stage] = {}
        self.groups: Dict[str, List[StageGroup]] = {}
        self._by_category: Dict[str, List[Stage]] = {}

    @classmethod
    def build(cls, stage_table: dict, zone_table: dict,
              paths: Optional[Iterable[str]] = None) -> "StageCatalog":
        cat = cls()
        zones = (zone_table or {}).get("zones") or {}
        stages_raw = (stage_table or {}).get("stages") or {}
        ss_names, bl_names = build_permanent_names(zone_table)

        path_map = {}
        for p in (paths or ()):
            if not p.endswith(".json"):
                continue
            base = p.rsplit("/", 1)[-1]
            if base.startswith("level_"):
                path_map.setdefault(base[6:-5], p)

        for sid, raw in stages_raw.items():
            if raw.get("isStoryOnly"):
                continue
            st = Stage(
                stage_id=sid,
                code=raw.get("code") or "",
                name=raw.get("name") or "",
                zone_id=raw.get("zoneId") or "",
                stage_type=raw.get("stageType") or "",
                difficulty=raw.get("difficulty") or "",
                cost=int(raw.get("apCost") or 0),
            )
            zone = zones.get(st.zone_id) or {}
            st.category = classify(st.stage_type, sid, st.zone_id,
                                   zone.get("type") or "")
            st.group_name = (MAINLINE_CHAPTER_NAMES.get(st.zone_id)
                             or _zone_group_name(zone))
            st.sub_name = zone.get("zoneNameSecond") or ""
            # 活动结束后进常驻的，按 permanent_* 分区名归到插曲/别传。
            # 注意 main_17-* 这类虽也命中「相变临界」，但它是主题曲正篇，
            # 已在 classify 里按 main_ 前缀归好，这里只处理活动前缀。
            if (st.category == "activity" and st.sub_name
                    and not sid.startswith("main_")):
                if st.sub_name in bl_names:
                    st.category = "branchline"
                elif st.sub_name in ss_names:
                    st.category = "sidestory"

            if st.category in ("activity", "sidestory", "branchline"):
                # 活动类按活动目录分组（act13side -> 一个组）
                st.group_id = activity_dir(st.zone_id, sid) or st.zone_id
            elif st.category == "main":
                st.group_id = st.zone_id or "main"
            else:
                st.group_id = st.zone_id or st.category

            real = path_map.get(sid)
            st.path = real if real else guess_path(sid, st.zone_id, st.stage_type)

            cat.stages[sid] = st
            cat._by_category.setdefault(st.category, []).append(st)

        # ---- 危机合约：stage_table 里没有，按 PRTS 核对的地图清单补出来
        for season_name, maps in CLASSIC_SEASONS:
            group_id = "rune_season_%s" % season_name
            for sid, mname, kind in maps:
                if sid in cat.stages:
                    continue
                st = Stage(
                    stage_id=sid,
                    code=sid.rsplit("_", 1)[-1],
                    name=mname,
                    zone_id="rune",
                    stage_type="CRISIS",
                    category="crisis",
                    group_id=group_id,
                    group_name="危机合约 · %s" % season_name,
                    sub_name="%s地图" % kind,
                    path=guess_path(sid),
                )
                cat.stages[sid] = st
                cat._by_category.setdefault("crisis", []).append(st)

        for season_name, maps in CRISIS_V2_SEASONS:
            group_id = "crisis_v2_season_%s" % season_name
            for sid, mname, kind in maps:
                if sid in cat.stages:
                    continue
                st = Stage(
                    stage_id=sid,
                    code=sid.rsplit("_", 1)[-1],
                    name=mname,
                    zone_id="crisis_v2",
                    stage_type="CRISIS",
                    category="crisis",
                    group_id=group_id,
                    group_name="危机合约 · %s" % season_name,
                    sub_name="%s地图" % kind,
                    path=guess_path(sid),
                )
                cat.stages[sid] = st
                cat._by_category.setdefault("crisis", []).append(st)


        cat._build_groups()
        return cat

    def _build_groups(self) -> None:
        self.groups = {}
        for cat_key, _label in CATEGORY_ORDER:
            items = self._by_category.get(cat_key) or []
            if not items:
                continue
            buckets = {}
            for st in items:
                buckets.setdefault(st.group_id, []).append(st)

            groups = []
            for gid, lst in buckets.items():
                lst.sort(key=_stage_sort_key)
                name = (lst[0].group_name or _derive_group_name(lst)
                        or _alias_group_name(gid) or gid)
                groups.append(StageGroup(
                    group_id=gid, name=name, category=cat_key, stages=lst))
            groups.sort(key=lambda g: _group_sort_key(g, cat_key))
            self.groups[cat_key] = groups

    def get(self, stage_id: str) -> Optional[Stage]:
        return self.stages.get(stage_id)

    def category_groups(self, category: str) -> List[StageGroup]:
        return self.groups.get(category) or []

    def categories(self) -> List[str]:
        return [k for k, _ in CATEGORY_ORDER if self.groups.get(k)]

    def category_label(self, category: str) -> str:
        for k, label in CATEGORY_ORDER:
            if k == category:
                return label
        return category

    def count_of(self, category: str) -> int:
        return len(self._by_category.get(category) or [])

    def total(self) -> int:
        return len(self.stages)

    def find_group(self, group_id: str) -> Optional[StageGroup]:
        for groups in self.groups.values():
            for g in groups:
                if g.group_id == group_id:
                    return g
        return None

    def to_dict(self) -> dict:
        return {"stages": [vars(s) for s in self.stages.values()]}

    def save(self, path: str) -> None:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(self.to_dict(), f, ensure_ascii=False)
        except OSError:
            pass

    @classmethod
    def load(cls, path: str) -> Optional["StageCatalog"]:
        try:
            with open(path, "r", encoding="utf-8") as f:
                raw = json.load(f)
        except (OSError, ValueError):
            return None
        rows = raw.get("stages") or []
        if not rows:
            return None
        cat = cls()
        for row in rows:
            st = Stage(**{k: v for k, v in row.items()
                          if k in Stage.__dataclass_fields__})
            cat.stages[st.stage_id] = st
            cat._by_category.setdefault(st.category, []).append(st)
        cat._build_groups()
        return cat


def _stage_sort_key(st: Stage):
    code = st.code or st.stage_id
    parts = re.split(r"(\d+)", code)
    key = []
    for p in parts:
        if p.isdigit():
            key.append((0, int(p)))
        elif p:
            key.append((1, p))
    return key


def _group_sort_key(g: StageGroup, category: str):
    if category == "main":
        m = re.search(r"main_(\d+)", g.group_id)
        if m:
            return (0, int(m.group(1)), "")
        m = re.search(r"act(\d+)mainss", g.group_id)
        if m:
            return (1, int(m.group(1)), "")
        return (2, 0, g.group_id)
    if category == "crisis":
        # 危机合约按赛季先后排序：经典赛季（荒芜 #0 ~ 起源 #12）在前，
        # 2.0 赛季（浊燃 #1 ~ 涤墨 #5）在后。
        classic = {n: i for i, (n, _m) in enumerate(CLASSIC_SEASONS)}
        v2 = {n: i for i, (n, _m) in enumerate(CRISIS_V2_SEASONS)}
        for name, idx in classic.items():
            if g.group_id == "rune_season_%s" % name:
                return (0, idx, "")
        for name, idx in v2.items():
            if g.group_id == "crisis_v2_season_%s" % name:
                return (1, idx, "")
        return (2, 0, g.group_id)
    m = re.search(r"(\d+)", g.group_id)
    if m:
        return (0, int(m.group(1)), g.group_id)
    return (1, 0, g.group_id)