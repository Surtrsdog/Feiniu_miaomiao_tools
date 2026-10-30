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
#: 玩家找图时的心智模型就是「主题曲 / 插曲 / 别传 / Side Story」，而不是活动 ID。
CATEGORY_ORDER = [
    ("main", "主题曲"),
    ("sidestory", "插曲"),
    ("interlude", "Side Story"),
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

#: 关卡目录的 schema 版本。
#: 每次「改了目录该有哪些分类/字段」就 +1，旧 catalog.json 会被判定
#: 过期并自动重建。否则老用户升级后仍读旧缓存——比如 v1 的目录里
#: 根本没有肉鸽关卡，界面就会一直没有「集成战略」分类。
#:   v2: 加入集成战略（肉鸽）
#:   v3: 肉鸽关卡加 node_type（作战/紧急作战/险路恶敌…），用于三层筛选
#:   v4: 修复插曲分类——permanent_sidestory_* 分区名纳入插曲判定
#:   v5: 拆分插曲与 Side Story——插曲=15/16/17章(MAINLINE_ACTIVITY)，
#:       Side Story=permanent_sidestory_* 复刻活动，单独成一类
#:   v6: hard_15~17 归插曲；#f#/#s 难度变体不再入目录（同一张图）
CATALOG_SCHEMA = 6

#: 分类 -> 一句说明，显示在分类主菜单的卡片上
CATEGORY_DESC = {
    "main": "第 0~14 章主线剧情，按章节推进",
    "sidestory": "第 15/16/17 章：离解复合 / 反常光谱 / 相变临界",
    "interlude": "Side Story 活动复刻（大骑士领 / 雪山大典 / 万国峰会等）",
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
    node_type: str = ""      # 肉鸽节点类型（作战/紧急作战/险路恶敌…），非肉鸽为空

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
        """难度的中文短标签，普通关返回空串。

        主线/活动的 FOUR_STAR 是「磨难」，但**肉鸽里同一关的困难版是
        「紧急作战」**（普通作战 vs 紧急作战共用一张图），标成磨难会
        让人以为是主线那种突袭难度的独立关卡。
        """
        if self.category == "roguelike":
            if self.node_type == "emergency" or self.difficulty == "FOUR_STAR":
                return "紧急"
            return ""
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
    # 集成战略（肉鸽）：stage_table 里一条都没有，目录索引靠
    # roguelike_topic_table 现造（见 build_roguelike_stages），
    # 地图路径由 levelId 原样小写推导。
    #
    # 实测（498/498 命中，0 未命中）：仓库里肉鸽地图的路径就是
    #     levels/<levelId 小写>.json
    # 例如 Obt/Roguelike/RO1/level_rogue1_1-1
    #   -> levels/obt/roguelike/ro1/level_rogue1_1-1.json
    #     Obt/Roguelike/RO5/DLC1/level_rogue5_sv-1_dlc1
    #   -> levels/obt/roguelike/ro5/dlc1/level_rogue5_sv-1_dlc1.json
    #
    # ⚠ 两个坑都踩过：直接用 levelId 字面量（大写 RO1/DLC1）一律 404，
    # 必须整条 tolower()。也不能走下面 _OBT_CATEGORIES 的拼接——那条
    # 会给出 levels/obt/main/level_ro1_n_1_1.json 这种错路径。
    sid_low = (stage_id or "").lower()
    if re.match(r"^ro\d", sid_low) or sid_low.startswith("rogue"):
        return "levels/obt/roguelike/%s/level_%s.json" % (
            sid_low.split("_", 1)[0], sid_low)
    head = stage_id.split("_", 1)[0] if "_" in stage_id else ""
    cat = head if head in _OBT_CATEGORIES else "main"
    return "levels/obt/%s/level_%s.json" % (cat, stage_id)


def roguelike_level_path(level_id: str) -> str:
    """肉鸽 levelId -> CDN 相对路径。

    ``levelId`` 来自 roguelike_topic_table 的 ``details.rogue_N.stages[*]``，
    形如 ``Obt/Roguelike/RO1/level_rogue1_1-1``。仓库里的实际路径就是
    「整体小写」，全文 498 条实测 100% 命中。
    """
    lid = (level_id or "").strip().lower()
    if not lid:
        return ""
    if lid.endswith(".json"):
        lid = lid[:-5]
    if lid.startswith("levels/"):
        return lid + ".json"
    return "levels/%s.json" % lid


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
    #   但 hard_15-* 属于第 15 章（离解复合），应归插曲。
    # 注意 main_* 不能一律当主题曲：第 15/16/17 章的 id 也是 main_NN-*，
    # 但它们的 zone 是 MAINLINE_ACTIVITY（离解复合 / 反常光谱 /
    # 相变临界这三个「插曲」章节），必须交给下面的 zone.type 判断。
    if head == "hard":
        # hard_15-* ~ hard_17-* 属于插曲章节
        if zt in ("MAINLINE_ACTIVITY", "MAINLINE_RETRO"):
            return "sidestory"
        return "main"
    if head == "crisis":
        return "crisis"
    if head == "tower":
        return "tower"
    # 第 15/16/17 章的关卡 id 是 main_15-* / main_16-* / main_17-*，
    # zone.type = MAINLINE_ACTIVITY。用户要求这些归为「插曲」(sidestory)，
    # 不能和 0~14 章混在主题曲里。
    if head == "main":
        # 先检查 zone type：MAINLINE_ACTIVITY / MAINLINE_RETRO -> 插曲
        if zt in ("MAINLINE_ACTIVITY", "MAINLINE_RETRO"):
            return "sidestory"
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


#: 集成战略主题的展示顺序与中文名。
#: 官方 ``topics`` 里本来就有 ``name`` 字段（"傀影与猩红孤钻" 等），
#: 但它是**主题名**，玩家在列表里更习惯看到「IS1 / IS2」这种简称，
#: 所以拼成「IS1 · 傀影与猩红孤钻」。这个顺序也是游戏内的解锁顺序。
_ROGUELIKE_TOPIC_LABEL = {
    "rogue_1": "IS1",
    "rogue_2": "IS2",
    "rogue_3": "IS3",
    "rogue_4": "IS4",
    "rogue_5": "IS5",
    "rogue_6": "IS6",
}


#: 肉鸽节点类型 -> 排序权重 / 显示名。
#:
#: 依据是 ``roguelike_topic_table`` 里 stage 的 ``code`` 与 ``id`` 前缀：
#:   * ``ISW-NO`` + id ``ro*_n_*``   普通作战
#:   * ``ISW-NO`` + id ``ro*_e_*``   紧急作战（精英）
#:   * ``ISW-DF`` + id ``ro*_b_*``   险路恶敌（首领）
#:   * ``ISW-SP``/``ISW-DU``         特殊作战（事件/决斗）
#:   * id ``ro*_t_*``                结局作战
#:   * id ``ro*_ev_*``               事件节点（不一定是作战）
#: 这批名字和官方 ``code`` 一一对应，不是我编的。
ROGUELIKE_NODE_TYPES = [
    ("normal", "作战"),
    ("emergency", "紧急作战"),
    ("boss", "险路恶敌"),
    ("special", "特殊作战"),
    ("ending", "结局作战"),
    ("event", "事件节点"),
    ("variant", "换皮图"),
]

ROGUELIKE_NODE_LABEL = dict(ROGUELIKE_NODE_TYPES)
_ROGUELIKE_NODE_ORDER = {k: i for i, (k, _n) in enumerate(ROGUELIKE_NODE_TYPES)}


def roguelike_node_type(raw: dict) -> str:
    """判定一条肉鸽 stage 属于哪种节点。

    先看 id 前缀（最准：``b``=首领、``t``=结局、``e``=紧急），再看
    ``code`` 兜底。两者冲突时以 id 为准——官方 ``code`` 有 1 条是空格
    （萨卡兹某关），靠 code 会判不出来。
    """
    sid = (raw.get("id") or "").strip().lower()
    code = (raw.get("code") or "").strip().upper()
    # ro1_b_1 / ro4_duel_1 / ro5_dlc1_... 取第二段
    parts = sid.split("_")
    head = parts[1] if len(parts) > 1 else ""
    if head in ("b",):
        return "boss"
    if head in ("t",):
        return "ending"
    if head in ("e",):
        return "emergency"
    if head in ("ev",):
        return "event"
    if head in ("duel", "sv", "dv", "fs", "dlc1"):
        return "special"
    if head == "n":
        return "normal"
    # 前缀认不出来，退到 code
    if code == "ISW-DF":
        return "boss"
    if code in ("ISW-SP", "ISW-DU"):
        return "special"
    return "normal"


def _add_roguelike_stages(cat: "StageCatalog",
                          roguelike_topic: dict) -> None:
    """把集成战略（肉鸽）关卡补进目录。

    为什么必须单独补
    ----------------
    ``stage_table.json`` 里**一条肉鸽关卡都没有**（3643 条 stage 的
    stageType 只有 MAIN / SUB / GUIDE / SPECIAL_STORY / DAILY /
    ACTIVITY / CAMPAIGN / CLIMB_TOWER，没有 ROGUELIKE），
    ``zone_table`` 里那 6 个 ``rogue_N`` 分区也是空壳——挂关卡数全是 0。
    所以「集成战略」分类之前永远是空的，``_ZONE_TYPE_CATEGORY`` 里那条
    ``"ROGUELIKE": "roguelike"`` 根本走不到。

    真正的关卡清单只在 ``excel/roguelike_topic_table.json`` 的
    ``details.rogue_N.stages`` 里，每条带 ``levelId``（地图路径）和
    ``levelReplaceIds``（换皮图，如萨卡兹肉鸽的 91 张替换图）。

    规模：6 主题 / 775 条目 / 498 唯一 levelId / 638 张地图文件。
    """
    topics = (roguelike_topic or {}).get("topics") or {}
    details = (roguelike_topic or {}).get("details") or {}

    def _topic_sort(tid: str):
        m = re.search(r"(\d+)", tid or "")
        return (int(m.group(1)) if m else 999, tid)

    for tid in sorted(details.keys(), key=_topic_sort):
        det = details.get(tid) or {}
        raw_stages = det.get("stages") or {}
        if not isinstance(raw_stages, dict):
            continue
        topic_name = (topics.get(tid) or {}).get("name") or tid
        short = _ROGUELIKE_TOPIC_LABEL.get(tid)
        group_name = ("%s · %s" % (short, topic_name)) if short else topic_name

        for sid, raw in raw_stages.items():
            if not isinstance(raw, dict):
                continue
            if sid in cat.stages:
                continue
            level_id = (raw.get("levelId") or "").strip()
            if not level_id:
                continue
            st = Stage(
                stage_id=sid,
                code=raw.get("code") or "",
                name=raw.get("name") or "",
                zone_id=tid,
                stage_type="ROGUELIKE",
                category="roguelike",
                group_id=tid,
                group_name=group_name,
                sub_name="",
                difficulty=raw.get("difficulty") or "",
                path=roguelike_level_path(level_id),
            )
            # 节点类型：三五层筛选的第三层靠它分组
            st.node_type = roguelike_node_type(raw)
            st.sub_name = ROGUELIKE_NODE_LABEL.get(st.node_type, "")
            cat.stages[sid] = st
            cat._by_category.setdefault("roguelike", []).append(st)

            # 换皮图：同一关的地图替身（萨卡兹 91 张、岁的界园 49 张）。
            # 它们是**独立地图文件**，也要能单独选出来，否则那 140 张图
            # 在界面上完全看不到。
            for i, rep in enumerate(raw.get("levelReplaceIds") or []):
                rep_id = (rep or "").strip()
                if not rep_id:
                    continue
                vsid = "%s~r%d" % (sid, i + 1)
                if vsid in cat.stages:
                    continue
                vst = Stage(
                    stage_id=vsid,
                    code="",
                    name="%s（换皮 %d）" % (st.name or sid, i + 1),
                    zone_id=tid,
                    stage_type="ROGUELIKE",
                    category="roguelike",
                    group_id=tid,
                    group_name=group_name,
                    sub_name="换皮图",
                    difficulty=st.difficulty,
                    path=roguelike_level_path(rep_id),
                )
                vst.node_type = "variant"
                cat.stages[vsid] = vst
                cat._by_category.setdefault("roguelike", []).append(vst)


def build_permanent_names(zone_table: dict):
    """收集「插曲 / Side Story / 别传」永久分区的名字集合。

    游戏里活动结束后会进常驻，官方准备了几组永久分区：
    - ``permanent_main_*``（离解复合/反常光谱/相变临界 = 第15/16/17章 = 插曲）
    - ``permanent_sidestory_*``（84 个 Side Story 复刻分区，如大骑士领/雪山大典）
    - ``permanent_sub_*``（20 个别传分区，如失落旗舰等）

    这些永久分区本身**不挂任何关卡**，真实关卡仍在 ``actXXXX_zoneN`` 上，
    两者靠 ``zoneNameSecond`` 同名对应。

    返回 (插曲名集合, Side Story名集合, 别传名集合)。
    """
    zones = (zone_table or {}).get("zones") or {}
    sidestory, interlude, branchline = set(), set(), set()
    for zid, z in zones.items():
        name = (z.get("zoneNameSecond") or "").strip()
        if not name:
            continue
        if zid.startswith("permanent_main"):
            sidestory.add(name)
        elif zid.startswith("permanent_sidestory"):
            interlude.add(name)
        elif zid.startswith("permanent_sub"):
            branchline.add(name)
    return sidestory, interlude, branchline


class StageCatalog:
    """全部关卡的分类目录（离线可用，构建一次后缓存）。"""

    def __init__(self) -> None:
        self.stages: Dict[str, Stage] = {}
        self.groups: Dict[str, List[StageGroup]] = {}
        self._by_category: Dict[str, List[Stage]] = {}

    @classmethod
    def build(cls, stage_table: dict, zone_table: dict,
              paths: Optional[Iterable[str]] = None,
              roguelike_topic: Optional[dict] = None) -> "StageCatalog":
        cat = cls()
        zones = (zone_table or {}).get("zones") or {}
        stages_raw = (stage_table or {}).get("stages") or {}
        ss_names, il_names, bl_names = build_permanent_names(zone_table)

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
            # 跳过难度变体：#f# = 磨难（硬核），#s = 简单（故事模式）
            # 它们使用同一张地图，只增加列表噪音。
            if "#" in sid:
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
            # 活动结束后进常驻的，按 permanent_* 分区名归到对应分类。
            # 注意 main_17-* 这类虽也命中「相变临界」，但它是主题曲正篇，
            # 已在 classify 里按 main_ 前缀归好，这里只处理活动前缀。
            #
            # 分类对应：
            #   permanent_main_*      -> sidestory（插曲 = 15/16/17章）
            #   permanent_sidestory_* -> interlude（Side Story 复刻活动）
            #   permanent_sub_*       -> branchline（别传）
            if (st.category == "activity" and st.sub_name
                    and not sid.startswith("main_")):
                if st.sub_name in bl_names:
                    st.category = "branchline"
                elif st.sub_name in il_names:
                    st.category = "interlude"
                elif st.sub_name in ss_names:
                    st.category = "sidestory"

            if st.category in ("activity", "sidestory", "interlude",
                               "branchline"):
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

        # ---- 集成战略（肉鸽）：stage_table 里一条都没有，必须从
        #      roguelike_topic_table 现造索引。见 build_roguelike_stages。
        if roguelike_topic:
            _add_roguelike_stages(cat, roguelike_topic)

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

    def node_types_in(self, group_id: str) -> List[Tuple[str, str, int]]:
        """某个小组里实际存在的节点类型，返回 (key, 显示名, 数量)。

        只列出真的有内容的类型，按 :data:`ROGUELIKE_NODE_TYPES` 的顺序，
        界面据此决定第三层下拉该显示哪些项——不会出现「特殊作战 0 关」
        这种点了什么也没有的选项。
        """
        cnt = {}
        for st in self.stages.values():
            if st.group_id != group_id:
                continue
            nt = st.node_type or ""
            if not nt:
                continue
            cnt[nt] = cnt.get(nt, 0) + 1
        out = []
        for key, label in ROGUELIKE_NODE_TYPES:
            if cnt.get(key):
                out.append((key, label, cnt[key]))
        return out

    def stages_in(self, group_id: str, node_type: str = "") -> List[Stage]:
        """某个小组下的关卡；``node_type`` 非空时按节点类型再筛一层。

        肉鸽一个主题几十到近三百关，只靠一个长下拉很难找。三层筛选
        （分类 → 主题 → 节点类型）能把它压到十几条。
        """
        out = [st for st in self.stages.values() if st.group_id == group_id]
        if node_type:
            out = [st for st in out if (st.node_type or "") == node_type]
        return sorted(out, key=_stage_sort_key)

    def total(self) -> int:
        return len(self.stages)

    def find_group(self, group_id: str) -> Optional[StageGroup]:
        for groups in self.groups.values():
            for g in groups:
                if g.group_id == group_id:
                    return g
        return None

    def to_dict(self) -> dict:
        return {"v": CATALOG_SCHEMA, "stages": [vars(s) for s in self.stages.values()]}

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
        # 版本对不上就当读不出来，让调用方重建。旧版 catalog 里一条肉鸽
        # 关卡都没有，可它会被当成本地缓存优先命中——用户装了新版还是
        # 看不到「集成战略」，只能手动删文件才能恢复。
        if int(raw.get("v") or 0) != CATALOG_SCHEMA:
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