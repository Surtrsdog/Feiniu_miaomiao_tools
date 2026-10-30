"""干员抬手（攻击前摇）数据。

数据从哪来
----------
``bakemuzzledata/character/<charKey>_defaultskin.json``，与敌人用同一套
烘焙格式。**抬手 = 普攻动画里 ``OnAttack`` 事件的时间点**——从动画第 0
帧算起，动画播多久才真正打出这一下。

与敌人的关键差异
----------------
1. 干员按 ``charKey``（``char_263_skadi``）索引，中文名只做显示/搜索。
   异格与本体同名不同 ID，用中文名当主键会撞车。
2. 干员**多一个登场时刻**（``Start`` 动画的 ``OnStart``），敌人没有。
3. 干员**没有普攻动画**的比例远高于敌人，且原因很具体——
   不是解析漏了，而是机制本身如此：

   ============== ========================================== ==============
   reason         含义                                        代表干员
   ============== ========================================== ==============
   ``OK``         正常，有普攻抬手                            大部分
   ``NO_ATTACK``  没有普攻（吟游者纯光环 / 处决者自爆）       空、浊心斯卡蒂、THRM-EX
   ``SKILL_ONLY`` 普攻只在技能期间存在（解放者 / 阵法术师）   玛恩纳、林、卡涅利安
   ``DOLL``       普攻发生在召唤物上（傀儡师）                双月
   ``NO_ANIM``    该文件里连动画组都没有                      极少
   ============== ========================================== ==============

   ``SKILL_ONLY`` 那类的「普攻抬手」其实挂在 ``Skill_N_Loop`` 上，
   放在 :attr:`Entry.skills` 里，不该混进 ``a``。

技能抬手
--------
同一份 bake 的 ``bakedEvents`` 里，名字以 ``Skill`` 开头且带 ``OnAttack``
的条目就是技能施放时的攻击判定时刻。实测 465 个干员命中 846 条、158
种动画名（``Skill`` / ``Skill_1_Loop`` / ``Skill_2_Attack`` /
``Skill_Down_2_Loop`` / ``Skill_3_Loop_A`` …），命名极不统一。

所以这里**不做名字到技能槽的强解**：``slot`` 只在能正则提取到数字时
才给（``Skill_2`` -> 2），提取不到就是 None。图鉴展示时按「精确槽位 >
同前缀兜底」的顺序匹配，并在兜底时说明这是推定。

数值为 0 的含义
---------------
``a == 0.0`` 是**真实值**（瞬发无前摇，如阿米娅的 ``Skill`` /
``Skill_2``），不是缺数据。图鉴要显示「瞬发」，不能显示「未收录」。
"""
from __future__ import annotations

import json
import os
import re
from typing import Dict, Optional

from .timing import (  # noqa: F401
    FPS,
    SEC_PER_FRAME,
    SUPPORTED_FPS,
    at_fps_table,
    convert,
    frames_at,
    frames_to_sec,
    sec_to_frames,
)

#: 随包数据文件名
DATA_NAME = "operator_attack_timing.json"

#: 无普攻动画的归因码 -> 中文说明
REASONS = {
    "NO_ATTACK": "该干员没有普攻（吟游者光环 / 自爆单位）",
    "SKILL_ONLY": "普攻只存在于技能期间（解放者 / 阵法术师）",
    "DOLL": "普攻发生在召唤物上（傀儡师）",
    "NO_ANIM": "解包文件里没有动画数据",
}

_cache: Optional[Dict[str, dict]] = None
_cache_path = ""
_meta_cache: Optional[dict] = None


def _candidates(paths=None):
    """按优先级列出可能的数据文件位置。"""
    out = []
    if paths is not None:
        try:
            out.append(os.path.join(paths.data_dir, DATA_NAME))
        except Exception:
            pass
        try:
            seed = getattr(paths, "seed_data_dir", None)
            if seed:
                out.append(os.path.join(seed, DATA_NAME))
        except Exception:
            pass
    here = os.path.dirname(os.path.abspath(__file__))
    out.append(os.path.join(os.path.dirname(here), "data", DATA_NAME))
    return out


def _read_raw(paths=None):
    for p in _candidates(paths):
        if not p or not os.path.isfile(p):
            continue
        try:
            with open(p, "r", encoding="utf-8") as f:
                return json.load(f), p
        except Exception:
            continue
    return None, ""


def load(paths=None) -> Dict[str, dict]:
    """载入抬手表（进程内缓存）。返回 ``charKey -> 条目``。"""
    global _cache, _cache_path
    for p in _candidates(paths):
        if not p or not os.path.isfile(p):
            continue
        if _cache is not None and _cache_path == p:
            return _cache
        raw, _ = _read_raw(paths)
        data = raw.get("by_char") if isinstance(raw, dict) else None
        if isinstance(data, dict):
            _cache = data
            _cache_path = p
            return _cache
    if _cache is None:
        _cache = {}
    return _cache


def meta(paths=None) -> Dict[str, object]:
    """读 meta（覆盖率等）。"""
    global _meta_cache
    raw, _ = _read_raw(paths)
    if isinstance(raw, dict):
        m = raw.get("meta")
        if isinstance(m, dict):
            _meta_cache = dict(m)
            return _meta_cache
    return dict(_meta_cache or {})


def get(char_key: str, paths=None) -> Optional[dict]:
    """查一个干员的抬手数据。找不到返回 None。

    兼容皮肤后缀：``char_263_skadi_2`` / ``char_263_skadi_char_...`` 都会
    回落到 ``char_263_skadi``。
    """
    if not char_key:
        return None
    data = load(paths)
    hit = data.get(char_key)
    if hit is not None:
        return hit
    # 去掉尾部的 _2 / _3 之类变体号
    base = re.sub(r"_\d+$", "", char_key)
    if base != char_key and base in data:
        return data[base]
    # 皮肤文件名形如 charKey_charKey_skin#n，取第一段
    m = re.match(r"(char_\d+_[0-9a-z]+?)_", char_key)
    if m and m.group(1) in data:
        return data[m.group(1)]
    return None


def seconds(char_key: str, paths=None) -> Optional[float]:
    """只要普攻抬手秒数。没有普攻（含 SKILL_ONLY）返回 None。"""
    hit = get(char_key, paths)
    if not hit:
        return None
    v = hit.get("a")
    return float(v) if isinstance(v, (int, float)) and not isinstance(v, bool) else None


def frames(char_key: str, paths=None) -> Optional[int]:
    """只要普攻抬手帧数。"""
    sec = seconds(char_key, paths)
    return sec_to_frames(sec) if sec is not None else None


def start_seconds(char_key: str, paths=None) -> Optional[float]:
    """登场时刻（``Start`` 动画的 ``OnStart``）。"""
    hit = get(char_key, paths)
    if not hit:
        return None
    v = hit.get("s")
    return float(v) if isinstance(v, (int, float)) and not isinstance(v, bool) else None


def reason(char_key: str, paths=None) -> Optional[str]:
    """无普攻动画的归因码；有普攻返回 ``"OK"``；查不到返回 None。"""
    hit = get(char_key, paths)
    if not hit:
        return None
    if isinstance(hit.get("a"), (int, float)):
        return "OK"
    return hit.get("r") or None


def skills(char_key: str, paths=None) -> Dict[str, dict]:
    """该干员所有技能动画的抬手。

    返回 ``{动画名: {"a": 秒, "f": 帧, "slot": 槽位或 None}}``；
    没有则返回空字典。
    """
    hit = get(char_key, paths)
    if not hit:
        return {}
    raw = hit.get("k") or {}
    out = {}
    for name, pair in raw.items():
        try:
            a, slot = pair[0], pair[1]
        except Exception:
            continue
        if not isinstance(a, (int, float)):
            continue
        out[name] = {"a": float(a), "f": sec_to_frames(a), "slot": slot}
    return out


def skill_windup(char_key: str, slot: Optional[int] = None,
                 paths=None) -> Optional[dict]:
    """按技能槽位号取技能抬手。

    ``slot`` 为 1/2/3（对应界面上的技能一/二/三）。匹配顺序：

    1. 名字正则能提出同号数字的（``Skill`` 与 ``Skill_1`` 都算 1 号）；
    2. 提不出号但同一前缀只有一个的，当作该槽位（标记 ``fallback``）。

    这样玛恩纳的 ``Skill_2_Loop`` 能对上 2 号技能，而 ``Skill_Begin``
    这种无名号动画不会被硬塞给某个槽位。找不到返回 None。
    """
    if slot is None:
        return None
    allsk = skills(char_key, paths)
    if not allsk:
        return None
    exact = []
    fuzzy = []
    for name, rec in allsk.items():
        m = re.search(r"[Ss]kill_?0*(\d)", name)
        got = int(m.group(1)) if m else None
        if got == slot:
            exact.append((name, rec))
        elif got is None:
            fuzzy.append((name, rec))
    if exact:
        # 同槽多个动画时，带 Attack/Loop 的比 Begin/End 更接近「打出去那一下」
        exact.sort(key=lambda kv: (0 if re.search(r"(Attack|Loop)", kv[0], re.I) else 1, kv[0]))
        name, rec = exact[0]
        return {"anim": name, "a": rec["a"], "f": rec["f"],
                "slot": slot, "fallback": False}
    if len(fuzzy) == 1:
        name, rec = fuzzy[0]
        return {"anim": name, "a": rec["a"], "f": rec["f"],
                "slot": slot, "fallback": True}
    return None


def describe(char_key: str, paths=None) -> str:
    """一句话描述，给图鉴「基础面板」用。"""
    hit = get(char_key, paths)
    if not hit:
        return ""
    a = hit.get("a")
    if not isinstance(a, (int, float)):
        r = hit.get("r")
        return REASONS.get(r, "无普攻数据") if r else ""
    anim = hit.get("n") or "Attack"
    s = "抬手 %d 帧（%.3f 秒）" % (sec_to_frames(a), a)
    if anim != "Attack":
        s += "（动作 %s）" % anim
    return s


def describe_skill(char_key: str, slot: Optional[int] = None,
                   paths=None) -> str:
    """一句话描述某技能的抬手，给技能卡用。"""
    w = skill_windup(char_key, slot, paths)
    if not w:
        return ""
    if w["a"] == 0:
        return "技能抬手 0 帧（瞬发）"
    s = "技能抬手 %d 帧（%.3f 秒）" % (w["f"], w["a"])
    if w.get("fallback"):
        s += "（推定：%s）" % w["anim"]
    return s


def stats(paths=None) -> Dict[str, object]:
    """统计信息。"""
    m = meta(paths)
    data = load(paths)
    vals = [v.get("a") for v in data.values()
            if isinstance(v.get("a"), (int, float)) and not isinstance(v.get("a"), bool)]
    out = dict(m)
    out["loaded"] = len(data)
    out["covered"] = len(vals)
    if vals:
        out["fps"] = FPS
        fs = sorted(sec_to_frames(v) for v in vals)
        out["frame_min"] = fs[0]
        out["frame_max"] = fs[-1]
        out["frame_median"] = fs[len(fs) // 2]
        out["frame_mean"] = round(sum(fs) / len(fs), 2)
    return out
