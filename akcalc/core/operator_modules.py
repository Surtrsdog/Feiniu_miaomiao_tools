"""干员模组数据：从 Kengxxiao/ArknightsGameData 的 uniequip_table.json 抓取。

* ``charEquip``：char_id -> [uniEquipId, ...]（该干员拥有的模组 id 列表）
* ``equipDict``：uniEquipId -> 模组详情（名称 / 描述 / 类型 / 解锁条件）

缓存到 ``data/cache/uniequip_table.json``，结构精简为 char_id -> [模组条目]，
避免每次进档案都现抓 20MB 大表。
"""
from __future__ import annotations

import json
import os
import re
from typing import Dict, List, Optional

from . import gamedata as GD
from .net import FetchError

#: 原始模组表（battle_equip_table.json）在 zh_CN/gamedata/ 下的相对路径。
#: uniequip_table.json 只有证章名称/描述，没有技能与天赋的黑板数值；
#: 完整数值在 battle_equip_table.json，供「查看原代码」展示。
BATTLE_EQUIP_PATH = "excel/battle_equip_table.json"
RAW_CACHE_NAME = "battle_equip_table.json"

#: 解锁精英阶段 -> 中文
_PHASE_CN = {"PHASE_0": "精英0", "PHASE_1": "精英1", "PHASE_2": "精英2"}

#: 模组类型 -> 中文
_TYPE_CN = {
    "INITIAL": "基础证章",
    "ORIGINAL": "原初证章",
    # ADVANCED 是**真正的模组**（有战斗数值的那种），旧版漏了这一项，
    # 于是幽灵鲨 / 泥岩 这些干员的模组类型直接显示成英文 "ADVANCED"。
    "ADVANCED": "模组",
    "MISSION": "任务证章",
    "STAGE": "关卡证章",
    "ACTIVITY": "活动证章",
    "CHALLENGE": "挑战证章",
}

#: 模组三阶段（模组等级 1/2/3）的属性键 -> 中文。
#: battle_equip_table.json 的 attributeBlackboard 只用这 8 个键，
#: 且值都是**累加总量**（不是相对上一级的增量）。
_ATTR_CN = {
    "atk": "攻击",
    "max_hp": "生命",
    "def": "防御",
    "attack_speed": "攻速",
    "cost": "费用",
    "magic_resistance": "法抗",
    "respawn_time": "再部署",
    "block_cnt": "阻挡",
}

#: 三阶段精简数值缓存（由 build_module_stats 生成）
STATS_CACHE_NAME = "module_stats.json"


def _mv(obj, default=None):
    if isinstance(obj, dict):
        if not obj.get("m_defined", True):
            return default
        v = obj.get("m_value")
        return default if v is None else v
    return obj if obj is not None else default


def _phase_cn(p):
    return _PHASE_CN.get(str(p).upper(), str(p))


def download_and_simplify(paths, progress=None):
    """下载 uniequip_table.json 并精简缓存，返回 char_id -> [模组]。"""
    raw = GD.fetch_json("excel/uniequip_table.json", timeout=300, tries=2)
    equip = raw.get("equipDict") or {}
    char_equip = raw.get("charEquip") or {}

    out: Dict[str, List[dict]] = {}
    for cid, ids in char_equip.items():
        mods = []
        for uid in ids or []:
            e = equip.get(uid)
            if not e:
                continue
            mods.append({
                "id": uid,
                "name": e.get("uniEquipName", ""),
                "desc": e.get("uniEquipDesc", ""),
                "type": _TYPE_CN.get(str(e.get("type") or ""),
                                    str(e.get("type") or "")),
                "typeName1": e.get("typeName1", ""),
                "unlock_phase": _phase_cn(e.get("unlockEvolvePhase")),
                "unlock_level": e.get("unlockLevel", 0),
                "unlock_favors": e.get("unlockFavors"),
                "show_phase": _phase_cn(e.get("showEvolvePhase")),
            })
        if mods:
            out[cid] = mods
    try:
        os.makedirs(paths.cache_dir, exist_ok=True)
        with open(os.path.join(paths.cache_dir, "uniequip_table.json"),
                  "w", encoding="utf-8") as f:
            json.dump(out, f, ensure_ascii=False)
    except OSError:
        pass
    return out


class ModuleLibrary:
    """本地模组库：char_id -> [模组条目]。"""

    def __init__(self, paths):
        self.paths = paths
        self._data: Dict[str, List[dict]] = {}
        self._loaded = False
        self._stats: Optional[Dict[str, dict]] = None

    @property
    def cache_path(self):
        return os.path.join(self.paths.cache_dir, "uniequip_table.json")

    @property
    def loaded(self):
        return self._loaded

    def load_cached(self) -> bool:
        try:
            with open(self.cache_path, "r", encoding="utf-8") as f:
                self._data = json.load(f)
        except (OSError, ValueError):
            return False
        self._loaded = True
        return True

    def ensure(self, progress=None) -> None:
        """确保本地有模组库；没有则下载。"""
        if self.load_cached():
            return
        try:
            self._data = download_and_simplify(self.paths, progress)
            self._loaded = True
        except FetchError:
            self._loaded = False

    def mods_of(self, char_id: str) -> List[dict]:
        return self._data.get(char_id) or []

    def raw_cache_path(self) -> str:
        return os.path.join(self.paths.cache_dir, RAW_CACHE_NAME)

    def load_raw(self) -> Dict:
        """懒加载原始 battle_equip_table.json（uniEquipId -> 完整条目）。

        优先读本地缓存，没有就返回 {}（不主动联网，避免卡 UI）。
        """
        try:
            with open(self.raw_cache_path(), "r", encoding="utf-8") as f:
                return json.load(f)
        except (OSError, ValueError):
            return {}

    def raw_entry(self, mod_id: str) -> dict:
        """取某个模组 id 的原始条目（equipLevel / parts / blackboard 等）。"""
        raw = self.load_raw()
        entry = raw.get(mod_id)
        return entry if isinstance(entry, dict) else {}

    def ensure_raw(self) -> None:
        """后台下载原始 battle_equip_table.json 到本地缓存（不阻塞）。"""
        if os.path.isfile(self.raw_cache_path()):
            return
        import threading

        def worker():
            try:
                raw = GD.fetch_json(BATTLE_EQUIP_PATH, timeout=480, tries=2)
                tmp = self.raw_cache_path() + ".tmp"
                with open(tmp, "w", encoding="utf-8") as f:
                    json.dump(raw, f, ensure_ascii=False)
                os.replace(tmp, self.raw_cache_path())
                # 拿到原始表后顺手重建精简数值表
                try:
                    build_module_stats(self.paths)
                except Exception:
                    pass
            except Exception:
                pass

        threading.Thread(target=worker, daemon=True).start()

    # ---------------------------------------------------- 三阶段数值

    @property
    def stats_cache_path(self) -> str:
        return os.path.join(self.paths.cache_dir, STATS_CACHE_NAME)

    def load_stats(self) -> Dict[str, dict]:
        """懒加载 module_stats.json（uniEquipId -> 三阶段数值）。"""
        if self._stats is not None:
            return self._stats
        try:
            with open(self.stats_cache_path, "r", encoding="utf-8") as f:
                self._stats = json.load(f)
        except (OSError, ValueError):
            self._stats = {}
        return self._stats

    def phases_of(self, mod_id: str) -> List[dict]:
        """取某个模组的三阶段数据（L1/L2/L3 的属性 + 特性 + 天赋）。

        返回 ``[{"level":1,"attrs":[...],"traits":[...],"talents":[...]}]``。
        本地精简表缺失时返回空列表（调用方退回纯文本展示）。
        """
        return (self.load_stats().get(mod_id) or {}).get("phases") or []


# ---------------------------------------------------------------- 数值表构建

_TAG_RE = re.compile(r"</?[^>]+>")
#: ``{key:0%}`` / ``{key}`` 占位符
_PH_RE = re.compile(r"\{([A-Za-z0-9_@.\[\]]+)\s*(?::([^}]*))?\}")


def _clean_text(t) -> str:
    if not t:
        return ""
    return _TAG_RE.sub("", str(t)).replace("\\n", "\n").strip()


def _fmt_num(v) -> str:
    if v is None:
        return ""
    try:
        f = float(v)
    except (TypeError, ValueError):
        return str(v)
    if abs(f - round(f)) < 1e-6:
        return "%d" % int(round(f))
    return "%g" % f


def _interp(txt: str, bb) -> str:
    """把描述里的 ``{key:0%}`` 占位符替换成黑板的实际数值。

    特性/天赋描述里只有约 8% 的键写成了占位符，其余数字是直接写在
    文案里的，所以这里**只做替换**，绝不反向用黑板重建文案。
    """
    if not txt:
        return ""

    def rep(m):
        key, spec = m.group(1), (m.group(2) or "")
        for it in (bb or []):
            if it.get("key") == key:
                vs = it.get("valueStr")
                if vs:
                    return str(vs)
                val = it.get("value")
                if val is None:
                    return m.group(0)
                if "%" in spec:
                    return "%d%%" % round(float(val) * 100)
                return _fmt_num(val)
        return m.group(0)

    return _PH_RE.sub(rep, txt)


def _first_candidate(bundle):
    if not isinstance(bundle, dict):
        return None
    for c in (bundle.get("candidates") or []):
        if isinstance(c, dict):
            return c
    return None


def build_module_stats(paths) -> Dict[str, dict]:
    """从 battle_equip_table.json 抽出每个模组三阶段的完整数值。

    产出 ``data/cache/module_stats.json``::

        {uniEquipId: {"phases": [
            {"level":1,
             "attrs":[{"key":"atk","cn":"攻击","value":34.0,"text":"攻击 +34"}],
             "traits":[{"text":"...","range":null,"prefab":null}],
             "talents":[{"text":"...","name":"...","prefab":"2","index":-1}]}]}}

    只保留 ``target`` 为 TRAIT / TALENT 的 part；``DISPLAY``（部署位提示）
    与 ``OVERWRITE_BATTLE_DATA`` 对图鉴展示没有意义，直接丢弃。
    """
    try:
        with open(os.path.join(paths.cache_dir, RAW_CACHE_NAME),
                  "r", encoding="utf-8") as f:
            raw = json.load(f)
    except (OSError, ValueError):
        return {}

    out: Dict[str, dict] = {}
    for mid, entry in (raw or {}).items():
        phases = (entry or {}).get("phases") or []
        if not phases:
            continue
        rec = {"phases": []}
        for ph in phases:
            try:
                lvl = int(ph.get("equipLevel") or 0)
            except (TypeError, ValueError):
                lvl = 0
            attrs = []
            for it in (ph.get("attributeBlackboard") or []):
                k = it.get("key")
                if not k:
                    continue
                v = it.get("value")
                cn = _ATTR_CN.get(k, k)
                try:
                    pos = float(v) >= 0
                except (TypeError, ValueError):
                    pos = True
                attrs.append({
                    "key": k, "cn": cn, "value": v,
                    "text": "%s %s%s" % (cn, "+" if pos else "", _fmt_num(v)),
                })
            traits, talents = [], []
            for part in (ph.get("parts") or []):
                tgt = part.get("target")
                if tgt == "TRAIT":
                    c = (_first_candidate(part.get("overrideTraitDataBundle"))
                         or _first_candidate(
                             part.get("addOrOverrideTraitDataBundle")))
                    if not c:
                        continue
                    bb = c.get("blackboard") or []
                    desc = _interp(_clean_text(
                        c.get("overrideDescripton")
                        or c.get("additionalDescription")
                        or c.get("description")), bb)
                    if desc:
                        traits.append({"text": desc,
                                       "range": c.get("rangeId"),
                                       "prefab": c.get("prefabKey")})
                elif tgt == "TALENT":
                    c = _first_candidate(part.get("addOrOverrideTalentDataBundle"))
                    if not c:
                        continue
                    bb = c.get("blackboard") or []
                    desc = _interp(_clean_text(
                        c.get("upgradeDescription")
                        or c.get("description")), bb)
                    if desc:
                        talents.append({"text": desc,
                                        "name": _clean_text(c.get("name")),
                                        "prefab": c.get("prefabKey"),
                                        "index": c.get("talentIndex")})
            rec["phases"].append({"level": lvl, "attrs": attrs,
                                  "traits": traits, "talents": talents})
        out[mid] = rec

    try:
        os.makedirs(paths.cache_dir, exist_ok=True)
        dst = os.path.join(paths.cache_dir, STATS_CACHE_NAME)
        tmp = dst + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(out, f, ensure_ascii=False, separators=(",", ":"))
        os.replace(tmp, dst)
    except OSError:
        pass
    return out