"""敌人数据：从关卡 JSON 的 enemyDbRefs + 全局敌人库解析。

关卡 JSON 的 `enemyDbRefs` 只是引用：
    {"useDb": true, "id": "enemy_1002_nsabr", "level": 0,
     "overwrittenData": {...} | null}

真实面板在全局敌人库 `levels/enemydata/enemy_database.json`（约 15MB）。
`overwrittenData` 是该关对某些字段的覆盖（m_defined=true 时生效）。

因此：
  * 只解析「本关出现的敌人」时，用 enemyDbRefs 的 id 去库里查，
    再叠加 overwrittenData 覆盖 —— 无需下载全量库到 UI 层，但需要库本体。
  * 若尚未下载库，可先用 overwrittenData 里存在的字段 + 占位提示。
"""
from __future__ import annotations

import base64
import json
import os
from typing import Dict, Iterable, List, Optional, Set

from . import net
from .models import EnemyStats

GH_API = "https://api.github.com/repos/Kengxxiao/ArknightsGameData"
GH_HEADERS = {"Accept": "application/vnd.github+json"}
ENEMY_DB_PATH = "zh_CN/gamedata/levels/enemydata/enemy_database.json"


def _mv(attr) -> float:
    """取属性里的 m_value（兼容裸数字）。"""
    if isinstance(attr, dict):
        if not attr.get("m_defined", True) and attr.get("m_value") is None:
            return 0.0
        return float(attr.get("m_value") or 0.0)
    if isinstance(attr, (int, float)):
        return float(attr)
    return 0.0


def _pick(override: Optional[dict], base: dict, key: str):
    """优先取 overwrittenData 中被显式定义的字段。"""
    if override:
        ov = override.get(key)
        if isinstance(ov, dict) and ov.get("m_defined"):
            return ov
    return base.get(key)


def parse_enemy_data(enemy_id: str, entry: dict,
                     override: Optional[dict] = None) -> EnemyStats:
    """从敌人库单体 entry（含 enemyData）构造 EnemyStats。"""
    data = entry.get("enemyData") or {}

    def val(key: str, default: float = 0.0) -> float:
        return _mv(_pick(override, data, key))

    name_obj = _pick(override, data, "name")
    if isinstance(name_obj, dict):
        name = name_obj.get("m_value") or enemy_id
    else:
        name = str(name_obj or enemy_id)

    attrs = data.get("attributes") or {}

    def attr(key: str) -> float:
        ov = override.get("attributes") if override else None
        if isinstance(ov, dict) and isinstance(ov.get(key), dict) and ov[key].get("m_defined"):
            return _mv(ov[key])
        return _mv(attrs.get(key))

    motion = data.get("motion") or ""
    ev = EnemyStats(
        enemy_id=enemy_id,
        name=name,
        hp=attr("maxHp"),
        atk=attr("atk"),
        defense=attr("def"),
        magic_resist=attr("magicResistance"),  # 官方数据已是点数（30.0 = 30）
        move_speed=attr("moveSpeed") or 1.0,
        weight=attr("massLevel") or attr("weight"),
        block_cost=int(attr("blockCnt") or 1),
        attack_interval=attr("baseAttackTime") or 1.5,
        is_flying=(str(motion).upper() == "FLY"),
        damage_type="PHYSICAL",
    )
    return ev


class EnemyLibrary:
    """全局敌人库，按需下载并缓存到本地（约 15MB，仅首次）。"""

    def __init__(self, cache_path: str):
        self.cache_path = cache_path
        #: enemy_id -> [entry, ...]（同一 id 可能有多个等级变体）
        self._by_id: Dict[str, List[dict]] = {}
        self._loaded = False

    # -------------------------------------------------- 加载

    @property
    def loaded(self) -> bool:
        return self._loaded

    @property
    def by_id(self) -> Dict[str, List[dict]]:
        """enemy_id -> [entry, ...]。图鉴要按 id 反查，公开出来。"""
        return self._by_id

    def load_cached(self) -> bool:
        try:
            with open(self.cache_path, "r", encoding="utf-8") as f:
                raw = json.load(f)
        except (OSError, ValueError):
            return False
        self._by_id = raw.get("by_id") or {}
        self._loaded = bool(self._by_id)
        return self._loaded

    def download(self, progress=None) -> None:
        """下载并解析全局敌人库。"""
        from . import gamedata as GD
        if progress:
            progress("下载敌人库（约 15 MB，走 jsDelivr）…")
        edb = GD.fetch_enemy_database(timeout=300, tries=3)
        if progress:
            progress("解析敌人库…")

        by_id: Dict[str, List[dict]] = {}
        for ref in edb.get("enemies") or []:
            key = ref.get("Key") or ""
            by_id[key] = ref.get("Value") or []
        self._by_id = by_id
        self._loaded = True

        try:
            os.makedirs(os.path.dirname(self.cache_path), exist_ok=True)
            with open(self.cache_path, "w", encoding="utf-8") as f:
                json.dump({"by_id": by_id}, f, ensure_ascii=False)
            if progress:
                progress("敌人库已缓存")
        except OSError:
            pass

    # -------------------------------------------------- 查询

    def get(self, enemy_id: str, level: int = 0) -> Optional[dict]:
        entries = self._by_id.get(enemy_id)
        if not entries:
            return None
        # 选择最接近的 level
        best = min(entries, key=lambda e: abs(int(e.get("level", 0)) - level))
        return best

    def stats(self, enemy_id: str, level: int = 0,
              override: Optional[dict] = None) -> Optional[EnemyStats]:
        e = self.get(enemy_id, level)
        if not e:
            return None
        return parse_enemy_data(enemy_id, e, override)


def level_enemy_ids(raw: dict) -> List[str]:
    """列出本关引用的敌人 id（去重、保持出现顺序）。"""
    out: List[str] = []
    seen: Set[str] = set()
    for ref in raw.get("enemyDbRefs") or []:
        eid = ref.get("id")
        if eid and eid not in seen:
            seen.add(eid)
            out.append(eid)
    return out


def level_enemy_overrides(raw: dict) -> Dict[str, Optional[dict]]:
    """本关对各敌人字段的覆盖。"""
    out: Dict[str, Optional[dict]] = {}
    for ref in raw.get("enemyDbRefs") or []:
        eid = ref.get("id")
        if eid:
            out[eid] = ref.get("overwrittenData")
    return out


def enemies_of_level(raw: dict, lib: Optional[EnemyLibrary] = None) -> List[EnemyStats]:
    """提取本关敌人列表；需要 lib 已加载，否则只能返回空。"""
    ids = level_enemy_ids(raw)
    ovs = level_enemy_overrides(raw)
    out: List[EnemyStats] = []
    for eid in ids:
        level = 0
        for ref in raw.get("enemyDbRefs") or []:
            if ref.get("id") == eid:
                level = int(ref.get("level", 0) or 0)
                break
        if lib and lib.loaded:
            st = lib.stats(eid, level, ovs.get(eid))
            if st:
                out.append(st)
        else:
            # 无库时退化为占位
            out.append(EnemyStats(enemy_id=eid, name=eid))
    return out