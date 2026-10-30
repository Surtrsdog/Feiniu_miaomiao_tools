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


def _ms(attr, default: str = "") -> str:
    """取属性里的 m_value，但保持字符串（``_mv`` 会转 float，不适用）。

    enemy_database 里几乎所有字段都包一层
    ``{"m_defined": true, "m_value": ...}``，``motion`` 就是典型：
    裸写 ``str(motion)`` 得到的是字典的 repr，跟 ``"FLY"`` 永远不等。
    """
    if isinstance(attr, dict):
        v = attr.get("m_value")
        if v is None:
            return default
        return str(v)
    if attr is None:
        return default
    return str(attr)


def _pick(override: Optional[dict], base: dict, key: str):
    """优先取 overwrittenData 中被显式定义的字段。"""
    if override:
        ov = override.get(key)
        if isinstance(ov, dict) and ov.get("m_defined"):
            return ov
    return base.get(key)


def _talent_value(override: Optional[dict], data: dict, key: str) -> float:
    """取 ``talentBlackboard`` 里某个 key 的数值。

    ``talentBlackboard`` 是**数组**而不是 ``{m_defined, m_value}`` 对象，
    所以不能用 :func:`_pick`。关卡覆盖时整份数组被替换掉，语义是
    「本关重写这张表」，而不是逐项 merge —— 实测 ``ro6_c_2`` 给的
    数组就是完整三项，与库里的默认三项一一对应。

    ⚠ **只认关卡覆盖，不回落到敌人库默认值**，这一点对
    ``Revive.unmovable_duration`` 尤其重要：

    * 库里只有 3 个敌人带这个键（角兽 ``enemy_1303_mhshep`` / 亢角兽
      ``enemy_1303_mhshep_2`` / 鬣犄兽 ``enemy_1304_mhwolf``），默认都是 150s。
    * 只有前两个真的「出场休憩」：PRTS 角兽页写「初始处于【休憩】状态：
      不进行攻击，出场一段时间内（默认为 150 秒）持有自缚」。鬣犄兽的
      能力只有「优先攻击角兽和亢角兽」，它的 150s 不是出场罚站。
    * 全库 2575 个缓存关里，这个键被关卡覆盖成正值的只有 **7 处**，
      而且全是角兽系（``ro6_c_2`` 的 90s 就是 PRTS 那句「出场 90 秒内
      无法移动」）；另有 21 处被显式覆盖成 0.0（= 本关不休憩）。

    所以「关卡显式给了正数」才是「本关确实出场罚站」的可靠信号，
    照搬库默认值会给大约 20 关的鬣犄兽凭空加 150 秒。
    没有覆盖时走 :func:`spawn_unmovable_default` 的角兽系白名单，
    这样 CF-1…CF-9 那些没写覆盖的角兽关也能显示对。
    """
    if not override:
        return 0.0
    tb = override.get("talentBlackboard")
    if not isinstance(tb, list):
        return 0.0
    for it in tb:
        if isinstance(it, dict) and it.get("key") == key:
            v = it.get("value")
            if isinstance(v, (int, float)) and not isinstance(v, bool):
                return float(v)
    return 0.0


#: 真的「出场休憩」的敌人 —— 只有角兽与亢角兽（handbook abilityList 里
#: 带「休憩」二字的就这两个，全库 2186 个敌人里查证过）。
#: 关卡用私有 id 引用它们时形如 ``enemy_1303_mhshep_a/_b/_c``，用前缀匹配。
REST_ENEMY_PREFIXES = ("enemy_1303_mhshep",)

#: PRTS 角兽页：「出场一段时间内（**默认为 150 秒**）持有自缚」。
REST_DEFAULT_SECONDS = 150.0


def spawn_unmovable_default(enemy_id: str) -> float:
    """敌人库里没被关卡覆盖时的默认出场罚站时长。

    只对角兽系返回 150s；鬣犄兽等一律 0。
    """
    eid = str(enemy_id or "")
    for pre in REST_ENEMY_PREFIXES:
        if eid == pre or eid.startswith(pre + "_"):
            return REST_DEFAULT_SECONDS
    return 0.0


def spawn_unmovable_of_ref(ref: Optional[dict]) -> float:
    """本关这条 ``enemyDbRefs`` 记录的「出场原地站多久」（秒）。0 表示不站。

    取值顺序：

    1. 关卡 ``overwrittenData.talentBlackboard`` 里显式给的
       ``Revive.unmovable_duration``（``ro6_c_2`` 的 90s 就是这条）。
       显式给 0.0 表示「本关不休憩」，要尊重它。
    2. 没写覆盖时，角兽系回落 150s（PRTS 写的默认值），其余敌人 0。

    刻意不查敌人库本体：关卡会用**私有 id**引用敌人，
    ``enemy_1303_mhshep_b`` / ``_c`` 这类变体在敌人库里根本不存在
    （``act24side_01``、``rogue5_2-2`` 都这么用），一旦要求先 ``stats()``
    成功，这些关的罚站就全丢了。私有变体靠前缀识别即可。
    """
    if not isinstance(ref, dict):
        return 0.0
    ov = ref.get("overwrittenData")
    if isinstance(ov, dict):
        tb = ov.get("talentBlackboard")
        if isinstance(tb, list):
            # 有覆盖就以覆盖为准，0.0 也是有效答案
            return max(0.0, _talent_value(ov, {}, "Revive.unmovable_duration"))
    return spawn_unmovable_default(str(ref.get("id") or ""))


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

    # motion 是 m_defined 包装：{'m_defined': True, 'm_value': 'FLY'}。
    # 原先写成 str(motion).upper() == "FLY"，拿字典的 repr 去比字符串，
    # 永远不成立 —— 全库 183 个飞行敌人的 is_flying 因此全是 False，
    # 沙盘的飞行判定与阻挡跟着一起错。_mv() 就是为这种包装写的。
    motion = _ms(data.get("motion"), "WALK").upper()
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
        is_flying=(motion == "FLY"),
        damage_type="PHYSICAL",
        spawn_unmovable=spawn_unmovable_of_ref(
            {"id": enemy_id, "overwrittenData": override}),
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