# -*- coding: utf-8 -*-
"""召唤物（token）数据与伤害计算。

为什么需要这一层
-----------------
原来的伤害计算只看干员本体，召唤师/战术家/工匠这类「靠召唤物输出」的
干员 DPS 会算成 0 或者严重偏低：

    令 三技能「弦惊」 → 本体的 473 攻击力只是召唤物的底板，
                       真正打伤害的是「弦惊」自己（atk 823）
    麦哲伦 三技能     → 本体几乎不输出，全靠龙腾.A（atk 753）
    凯尔希 三技能     → Mon3tr atk 1402，是凯尔希的两倍多

之前判断「召唤物数据拿不到」是**错的**。官方 ``character_table.json``
里有 931 个 ``token_*`` 实体，每个都带完整三阶段数值（atk/def/法抗/
攻击间隔），而且干员到召唤物的对应关系是显式的：

    character.skills[i].overrideTokenKey -> "token_10020_ling_soul3"
    character.displayTokenDict           -> {"token_10020_ling_soul3": true}

伤害倍率在 ``skill_table`` 的 ``sktok_*`` 技能里（已随包分发，
运行时不需要联网）。

数据来源与缓存
--------------
``character_table.json`` 有 30MB+，不适合每次启动都解析。本模块在
构建期把它精简成 ``data/cache/summon_stats.json``（只保留 token 的
名字/攻击/间隔/法抗/所属干员），体积约 100KB。

**不改动任何数据抓取逻辑**：只复用现有的 ``gamedata.fetch_json``，
精简产物与 ``module_stats.json`` 完全同构，由 paths.seed_if_needed
按同一条种子复制通道分发。
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from . import constants as C
from . import gamedata as GD

#: 精简后的召唤物数值表
SUMMON_CACHE_NAME = "summon_stats.json"

#: 攻击力不高于这个值的 token 一律视为纯装置（夹子、医疗探机、电池…）。
#: 实测这类 token 的攻击力被官方写成 100 占位，本身不参与输出。
_PLACEHOLDER_ATK = 100.0


def _mv(obj, default=None):
    """读取官方 m_defined/m_value 包装值。"""
    if isinstance(obj, dict):
        if not obj.get("m_defined", True):
            return default
        v = obj.get("m_value")
        return default if v is None else v
    return obj if obj is not None else default


def _phase_data(rec: dict, phase_index: int = -1) -> dict:
    """取某个精英阶段的最终属性帧。"""
    phases = rec.get("phases") or []
    if not phases:
        return {}
    try:
        p = phases[phase_index]
    except IndexError:
        return {}
    frames = p.get("attributesKeyFrames") or []
    if not frames:
        return {}
    return frames[-1].get("data") or {}


@dataclass
class Summon:
    """一个召唤物的可计算形态。"""

    token_id: str
    name: str
    owner: str = ""
    atk: float = 0.0
    interval: float = 1.0
    defense: float = 0.0
    res: float = 0.0
    block: float = 0.0
    max_hp: float = 0.0
    #: 攻击型（atk 高于占位值）才有 DPS 意义
    offensive: bool = False
    #: token 自带的技能 id（sktok_*），用于取伤害倍率
    skills: List[str] = field(default_factory=list)
    #: 该 token 的伤害类型
    damage_type: str = C.DMG_PHYSICAL

    def summary(self) -> str:
        return "%s（攻击 %.0f / 间隔 %.2fs）" % (self.name, self.atk, self.interval)


#: 名字里带这些词的是治疗/支援装置，不产生伤害。
#: 它们的 atk 值（如医疗探机 125）只是配置占位，不代表会打人。
_NON_DAMAGE_HINTS = ("医疗", "治疗", "探机", "回复", "电池", "哨戒",
                     "夹子", "陷阱", "信标", "补给")


def _is_offensive_token(name: str, atk: float, skills: List[str]) -> bool:
    """判断一个 token 到底是「会打人的召唤物」还是「纯装置」。

    ``atk > 100`` 这个单一阈值不够：赫默的医疗探机 atk=125，
    它是治疗装置，列进「召唤物输出」里会凭空多出 500 DPS。
    """
    if atk <= _PLACEHOLDER_ATK:
        return False
    if any(h in name for h in _NON_DAMAGE_HINTS):
        return False
    return True


def _guess_token_type(rec: dict) -> str:
    """推断召唤物伤害类型。

    召唤物几乎都是 ``notchar1`` 子职业，没有可用分支信息，
    只能看描述与名字里的线索。默认物理——绝大多数召唤物确实是物理
    （水獭、触手、摄影器、龙腾、戴乌、狼群…）。
    """
    name = str(rec.get("name") or "")
    desc = " ".join(str(rec.get(k) or "") for k in ("description", "itemDesc", "itemUsage"))
    text = name + " " + desc
    if "元素" in text:
        return C.DMG_ELEMENTAL
    if "真实" in text:
        return C.DMG_TRUE
    if "法术" in text or "法伤" in text:
        return C.DMG_MAGICAL
    return C.DMG_PHYSICAL


def parse_summon(token_id: str, rec: dict, owner: str = "") -> Optional[Summon]:
    """把官方 character_table 的一条 token 记录转成 :class:`Summon`。"""
    if not isinstance(rec, dict):
        return None
    d = _phase_data(rec)
    if not d:
        return None
    try:
        atk = float(d.get("atk") or 0.0)
    except (TypeError, ValueError):
        atk = 0.0
    try:
        interval = float(d.get("baseAttackTime") or 1.0)
    except (TypeError, ValueError):
        interval = 1.0
    if interval <= 0:
        interval = 1.0
    skills = []
    for s in (rec.get("skills") or []):
        sid = s.get("skillId")
        if sid and sid not in skills:
            skills.append(sid)
    name = str(rec.get("name") or token_id)
    return Summon(
        token_id=token_id,
        name=name,
        owner=owner,
        atk=atk,
        interval=interval,
        defense=float(_mv(d.get("def"), 0.0) or 0.0),
        res=float((d.get("magicResistance") or 0.0)) * 100.0,
        block=float(_mv(d.get("blockCnt"), 0.0) or 0.0),
        max_hp=float(_mv(d.get("maxHp"), 0.0) or 0.0),
        offensive=_is_offensive_token(name, atk, skills),
        skills=skills,
        damage_type=_guess_token_type(rec),
    )


def build_summon_stats(char_table: dict) -> Dict[str, dict]:
    """把官方 character_table.json 精简成 token_id -> 数值。

    只保留**有 displayTokenDict 的干员**所拥有的 token，这些才是玩家
    实际能摆上场的召唤物；把 931 个 token 全存下来既浪费体积，
    也会把剧情专用/敌方专用实体混进来。
    """
    out: Dict[str, dict] = {}
    for cid, rec in (char_table or {}).items():
        if cid.startswith("token_") or cid.startswith("trap_"):
            continue
        if not isinstance(rec, dict):
            continue
        tokens = rec.get("displayTokenDict") or {}
        if not tokens:
            continue
        owner = str(rec.get("name") or cid)
        # 干员技能 -> token 的显式映射，技能侧选中时用它精确定位召唤物
        skill_tokens: Dict[str, str] = {}
        for s in (rec.get("skills") or []):
            sid = s.get("skillId")
            tk = s.get("overrideTokenKey")
            if sid and tk and tk in tokens:
                skill_tokens[sid] = tk
        for tk in tokens:
            trec = (char_table or {}).get(tk)
            if not isinstance(trec, dict):
                continue
            sm = parse_summon(tk, trec, owner)
            if sm is None:
                continue
            entry = out.setdefault(tk, {
                "token_id": tk,
                "name": sm.name,
                "owners": [],
                "owner_ids": [],
                "atk": sm.atk,
                "interval": sm.interval,
                "def": sm.defense,
                "res": sm.res,
                "block": sm.block,
                "max_hp": sm.max_hp,
                "offensive": sm.offensive,
                "skills": sm.skills,
                "damage_type": sm.damage_type,
                "skill_map": {},
            })
            if owner not in entry["owners"]:
                entry["owners"].append(owner)
            if cid not in entry["owner_ids"]:
                entry["owner_ids"].append(cid)
            for sid, tk2 in skill_tokens.items():
                if tk2 == tk:
                    entry["skill_map"][sid] = tk
    return out


def download_and_simplify(paths, progress=None) -> Dict[str, dict]:
    """下载 character_table.json 并精简缓存（构建期/首次运行用）。

    与 :func:`operator_modules.download_and_simplify` 同构：
    联网只发生在**缓存缺失**时，成功后写本地，之后完全离线。
    """
    raw = GD.fetch_json(GD.EXCEL_CHAR, timeout=300, tries=2)
    stats = build_summon_stats(raw)
    try:
        os.makedirs(paths.cache_dir, exist_ok=True)
        with open(os.path.join(paths.cache_dir, SUMMON_CACHE_NAME),
                  "w", encoding="utf-8") as f:
            json.dump(stats, f, ensure_ascii=False)
    except OSError:
        pass
    return stats


class SummonLibrary:
    """本地召唤物库：token_id -> 数值。"""

    def __init__(self, paths):
        self.paths = paths
        self._data: Dict[str, dict] = {}
        self._loaded = False

    @property
    def cache_path(self) -> str:
        return os.path.join(self.paths.cache_dir, SUMMON_CACHE_NAME)

    @property
    def loaded(self) -> bool:
        return self._loaded

    def load_cached(self) -> bool:
        try:
            with open(self.cache_path, "r", encoding="utf-8") as f:
                self._data = json.load(f)
        except (OSError, ValueError):
            return False
        self._loaded = bool(self._data)
        return self._loaded

    def ensure(self, progress=None) -> None:
        """确保本地有召唤物库；没有则尝试下载一次。"""
        if self.load_cached():
            return
        try:
            self._data = download_and_simplify(self.paths, progress)
            self._loaded = bool(self._data)
        except Exception:
            self._loaded = False

    # ------------------------------------------------------------ 查询

    def get(self, token_id: str) -> Optional[Summon]:
        d = self._data.get(token_id)
        if not d:
            return None
        return Summon(
            token_id=d.get("token_id", token_id),
            name=d.get("name", token_id),
            owner=", ".join(d.get("owners") or []),
            atk=float(d.get("atk") or 0.0),
            interval=float(d.get("interval") or 1.0),
            defense=float(d.get("def") or 0.0),
            res=float(d.get("res") or 0.0),
            block=float(d.get("block") or 0.0),
            max_hp=float(d.get("max_hp") or 0.0),
            offensive=bool(d.get("offensive")),
            skills=list(d.get("skills") or []),
            damage_type=d.get("damage_type") or C.DMG_PHYSICAL,
        )

    def summons_of(self, char_id: str) -> List[dict]:
        """某个干员能召唤的全部 token（精简条目）。"""
        return [d for d in self._data.values()
                if char_id in (d.get("owner_ids") or [])
                or char_id in (d.get("owners") or [])]

    def summon_for_skill(self, char_id: str, skill_id: str = "",
                         skill_index: int = 0) -> Optional[Summon]:
        """按干员 + 技能定位召唤物。

        定位顺序：

        1. ``skill_id`` 精确命中 ``skill_map``（官方 overrideTokenKey 映射）
        2. 只有 1 个攻击型召唤物 -> 直接用它
        3. 按技能序号挑——官方技能 id 一律是 ``skchr_xxx_N`` 形式，
           末尾数字就是第几个技能（令 S3 -> ``..._3`` -> 弦惊）。
           缓存里的干员技能条目**没有 skill_id 字段**，所以 UI 只能
           靠序号定位；37 条 skill_map 全部符合这个命名，映射可靠。
        4. 还是挑不出来就返回 None（多召唤物且无映射 -> 让用户自己选）
        """
        cands = self.summons_of(char_id)
        if not cands:
            return None
        if skill_id:
            for d in cands:
                if skill_id in (d.get("skill_map") or {}):
                    return self.get(d["token_id"])
        offensive = [d for d in cands if d.get("offensive")]
        if len(offensive) == 1:
            return self.get(offensive[0]["token_id"])
        if skill_index:
            suffix = "_%d" % int(skill_index)
            for d in cands:
                for sid in (d.get("skill_map") or {}):
                    if sid.endswith(suffix):
                        return self.get(d["token_id"])
        return None

    def all_offensive(self) -> List[dict]:
        return [d for d in self._data.values() if d.get("offensive")]