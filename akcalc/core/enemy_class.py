"""敌人分类：把敌人库里的原始字段归类成图鉴筛选维度。

数据来源是 enemy_database.json 里每条 enemyData 的字段：
* ``levelType``：NORMAL / ELITE / BOSS（普通 / 精英 / 领袖）
* ``motion``：WALK / FLY（地面 / 飞行）
* ``enemyTags``：种族标签（sarkaz / infection / machine …）
* ``damageType`` / ``applyWay``：伤害类型（物理 / 法术 / 治疗等）

PRTS 侧没有一份稳定的「敌人分类」结构化数据可抓，所以这里把
游戏客户端原始标签整理成稳定的中文分类，供图鉴筛选器使用。
"""
from __future__ import annotations

from typing import Dict, List

#: levelType -> 中文
LEVEL_TYPE_CN = {
    "NORMAL": "普通",
    "ELITE": "精英",
    "BOSS": "领袖",
}

#: motion -> 中文
MOTION_CN = {
    "WALK": "地面",
    "FLY": "飞行",
}

#: 种族标签 -> 中文（enemyTags 里实际出现的取值）
RACE_TAG_CN = {
    "infection": "感染生物",
    "sarkaz": "萨卡兹",
    "machine": "机械",
    "seamonster": "海嗣",
    "drone": "无人机",
    "wildanimal": "野生动物",
    "originiumartscraft": "源石技艺造物",
    "origen": "源石",
    "collapsal": "坍缩体",
    "mutant": "变异体",
    "animated": "活化",
    "phantom": "幻影",
    "eldritch": "邪魔",
    "npc": "剧情单位",
    "player": "我方单位",
}

#: 伤害类型
DAMAGE_TYPE_CN = {
    "PHYSICAL": "物理",
    "MAGICAL": "法术",
    "REAL": "真实",
    "HEAL": "治疗",
    "NONE": "无",
}

#: 攻击方式（applyWay）
APPLY_WAY_CN = {
    "MELEE": "近战",
    "RANGED": "远程",
    "ALL": "近远程",
    "NONE": "无攻击",
}

#: 分类维度顺序（筛选器下拉按此排列）
CATEGORY_DIMS = ("级别", "位置", "种族", "攻击方式")


def _mv(obj, default=None):
    """解包 {m_defined, m_value} 包装。

    注意：分类场景里 m_defined=False 只表示「没在数据里显式声明、取的是
    默认值」，而默认值本身仍有意义（levelType 默认 NORMAL、motion 默认
    WALK）。所以只要 m_value 存在就直接用，不做 m_defined 判断。
    """
    if isinstance(obj, dict):
        v = obj.get("m_value")
        return default if v is None else v
    return obj if obj is not None else default


def classify(enemy_data: dict) -> Dict[str, str]:
    """把一条 enemyData 归类，返回 {维度: 中文分类}。

    缺失的维度不写键，由 UI 层决定是否跳过筛选。
    """
    out: Dict[str, str] = {}

    lt = _mv(enemy_data.get("levelType"))
    if lt:
        out["级别"] = LEVEL_TYPE_CN.get(str(lt).upper(), str(lt))

    mo = _mv(enemy_data.get("motion"))
    if mo:
        out["位置"] = MOTION_CN.get(str(mo).upper(), str(mo))

    tags = _mv(enemy_data.get("enemyTags"), []) or []
    race = None
    for t in tags:
        t = str(t)
        if t in RACE_TAG_CN and t not in ("animated", "phantom"):
            race = RACE_TAG_CN[t]
            break
    if race is None:
        for t in tags:
            t = str(t)
            if t in RACE_TAG_CN:
                race = RACE_TAG_CN[t]
                break
    if race:
        out["种族"] = race

    dt = _mv(enemy_data.get("damageType"))
    if not dt:
        attrs = enemy_data.get("attributes") or {}
        dt = _mv(attrs.get("damageType"))
    if dt:
        out["伤害"] = DAMAGE_TYPE_CN.get(str(dt).upper(), str(dt))

    aw = _mv(enemy_data.get("applyWay"))
    if aw:
        out["攻击方式"] = APPLY_WAY_CN.get(str(aw).upper(), str(aw))

    return out


def all_dimensions(entries_by_id: Dict[str, list]) -> Dict[str, List[str]]:
    """遍历整库，返回每个维度的取值（按出现频率排，供筛选器）。"""
    from collections import Counter
    counts: Dict[str, Counter] = {}
    for eid, ents in entries_by_id.items():
        if not ents:
            continue
        ed = ents[0].get("enemyData") or {}
        c = classify(ed)
        for dim, val in c.items():
            counts.setdefault(dim, Counter())[val] += 1
    out: Dict[str, List[str]] = {}
    for dim in CATEGORY_DIMS:
        if dim in counts:
            out[dim] = [v for v, _ in counts[dim].most_common()]
    return out