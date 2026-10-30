"""敌人抬手（攻击前摇）数据。

数据从哪来
----------
``bakemuzzledata/enemy/<enemy_id>.json`` 是游戏把 Spine 动画「烘焙」后的
产物，里面记录每个动画在哪些时间点触发事件：

```json
{"bakedAnimDatas": {"Default": {
    "bakedEvents": {"Attack": {"eventTime": [0.3333],
                               "events": ["OnAttack"]}},
    "bakedMPDatas": {...}
}}, "hash": "..."}
```

``eventTime[i]`` 与 ``events[i]`` 一一对应。**抬手 = 攻击动画里
``OnAttack`` 事件的时间点**——从动画第 0 帧算起，动画播多久才真正
打出这一下。这就是玩家说的「前摇」：抬手快的敌人（源石虫 0.33s）
贴脸就会掉血，抬手慢的（萨卡兹术师 1.0s、某些 BOSS 3s+）可以掐着
节奏卡位。

为什么不在运行时读原始 bake 文件
--------------------------------
2109 个文件 89MB，全是逐帧 ``trsData`` 浮点数组，图鉴只用得到那一
个时间点。构建期解析成 ``enemy_attack_timing.json``（0.22MB）随包
分发，运行时只读这张表。

动画名不止 ``Attack``
---------------------
实测 86 种动画名，带攻击语义的有 ``Attack`` / ``Attack_A`` /
``Attack_B`` / ``Attack_2`` / ``B_Attack`` / ``Combat`` /
``Attack_Up`` / ``Attack_Down`` / ``Attack_Loop`` 等。所以识别规则是
「名字含 attack/combat 且不含 skill/die/idle/stun」而不是等号判断。

优先级 ``Attack`` > ``Combat`` > ``Attack*`` > ``*_Attack`` >
``Skill`` 上的 OnAttack（施法型敌人的普攻动画常常缺失，事件挂在
Skill 轨道上）。

秒与帧
------
游戏按 **30 fps** 烘焙动画，``eventTime`` 的原始值本质就是
「帧号 / 30」。所以本模块同时提供两种单位：``seconds()`` / ``frames()``，
换算常量是 :data:`FPS`。

帧数不是近似值——实测 1857 条数据里 ``round(a*30)`` 与原始帧号的偏差
最大 0.001 帧（JSON 只存 4 位小数导致的舍入）。所以图鉴和 MCP 都能
放心把帧当准数用。
"""
from __future__ import annotations

import json
import os
import re
from typing import Dict, Optional

#: 随包数据文件名
DATA_NAME = "enemy_attack_timing.json"

from .timing import (  # noqa: F401  (re-export 保持旧调用点不变)
    FPS,
    SUPPORTED_FPS,
    SEC_PER_FRAME,
    frames_at,
    at_fps_table,
    sec_to_frames,
    frames_to_sec,
    convert,
)

_cache: Optional[Dict[str, dict]] = None
_cache_path = ""


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
    # 源码运行的兜底：本文件在 akcalc/core/ 下
    here = os.path.dirname(os.path.abspath(__file__))
    out.append(os.path.join(os.path.dirname(here), "data", DATA_NAME))
    return out


def load(paths=None) -> Dict[str, dict]:
    """载入抬手表（进程内缓存）。返回 ``enemy_id -> 条目``。"""
    global _cache, _cache_path
    for p in _candidates(paths):
        if not p or not os.path.isfile(p):
            continue
        if _cache is not None and _cache_path == p:
            return _cache
        try:
            with open(p, "r", encoding="utf-8") as f:
                raw = json.load(f)
        except Exception:
            continue
        data = raw.get("by_id") if isinstance(raw, dict) else None
        if isinstance(data, dict):
            _cache = data
            _cache_path = p
            return _cache
    if _cache is None:
        _cache = {}
    return _cache


def meta(paths=None) -> Dict[str, object]:
    """读 meta（覆盖率等），供设置页 / MCP 展示。"""
    for p in _candidates(paths):
        if p and os.path.isfile(p):
            try:
                with open(p, "r", encoding="utf-8") as f:
                    raw = json.load(f)
                if isinstance(raw, dict):
                    return dict(raw.get("meta") or {})
            except Exception:
                continue
    return {}


def get(enemy_id: str, paths=None) -> Optional[dict]:
    """查一个敌人的抬手数据。找不到返回 None。"""
    if not enemy_id:
        return None
    data = load(paths)
    hit = data.get(enemy_id)
    if hit:
        return hit
    # 变体后缀：enemy_1007_slime 的表项也可能只以 enemy_1007_slime_2 存在，
    # 反过来也成立。优先取无后缀的那个，保证同一敌人各等级一致。
    base = re.sub(r"_\d+$", "", enemy_id)
    if base != enemy_id and base in data:
        return data[base]
    for k, v in data.items():
        if re.sub(r"_\d+$", "", k) == base:
            return v
    return None


def seconds(enemy_id: str, paths=None) -> Optional[float]:
    """只要抬手秒数。"""
    hit = get(enemy_id, paths)
    if not hit:
        return None
    v = hit.get("a")
    return float(v) if isinstance(v, (int, float)) else None


def frames(enemy_id: str, paths=None) -> Optional[int]:
    """只要抬手帧数（按 :data:`FPS` 从秒还原）。"""
    sec = seconds(enemy_id, paths)
    return sec_to_frames(sec) if sec is not None else None





def describe(enemy_id: str, paths=None) -> str:
    """一句话描述，给图鉴卡片用。"""
    hit = get(enemy_id, paths)
    if not hit:
        return ""
    a = hit.get("a")
    if not isinstance(a, (int, float)):
        return ""
    anim = hit.get("anim") or ""
    fr = sec_to_frames(a)
    s = "抬手 %d 帧（%.3f 秒）" % (fr, a)
    if hit.get("skill_only"):
        s += "（取自技能动作 %s）" % anim
    elif anim and anim != "Attack":
        s += "（动作 %s）" % anim
    return s


def stats(paths=None) -> Dict[str, object]:
    """统计信息。

    ``meta`` 里的 ``coverage`` 是**嵌套字典**（``{covered, enemy_ids}``），
    早先这里直接 ``dict(meta)`` 摊平顶层，导致 ``out["covered"]`` 恒为
    None、``out["enemy_ids"]`` 也取不到。这里把嵌套项显式提到顶层，并
    用「实际载入的条目数」覆盖 ``covered``——meta 里记录的 1868 是构建时
    的中间数，与实际写入 ``by_id`` 的条数（1857）口径不一致，以实际为
    准，避免图鉴上出现两个互相矛盾的数字。
    """
    m = meta(paths)
    data = load(paths)
    vals = [v.get("a") for v in data.values()
            if isinstance(v.get("a"), (int, float))]
    out = dict(m)
    cov = m.get("coverage")
    if isinstance(cov, dict):
        # 嵌套结构：拆到顶层，别让调用方看到 None
        for k, v in cov.items():
            out.setdefault(k, v)
        out.pop("coverage", None)
        out["coverage"] = cov
    out["loaded"] = len(data)
    # meta 里的 covered 是构建中间值；以实际载入条目为准，两者必须一致
    out["covered"] = len(data)
    if isinstance(cov, dict) and "enemy_ids" in cov:
        out["enemy_ids"] = cov["enemy_ids"]
    if vals:
        vals_sorted = sorted(vals)
        out["min"] = vals_sorted[0]
        out["max"] = vals_sorted[-1]
        out["median"] = vals_sorted[len(vals_sorted) // 2]
        out["mean"] = round(sum(vals) / len(vals), 4)
        # 帧维度：玩家和 MCP 都更常按帧看
        frames_sorted = [sec_to_frames(v) for v in vals_sorted]
        out["fps"] = FPS
        out["frame_min"] = frames_sorted[0]
        out["frame_max"] = frames_sorted[-1]
        out["frame_median"] = frames_sorted[len(frames_sorted) // 2]
        out["frame_mean"] = round(sum(frames_sorted) / len(frames_sorted), 2)
    return out
