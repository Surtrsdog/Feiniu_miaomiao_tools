# -*- coding: utf-8 -*-
"""敌人图鉴文本：PRTS 风格的能力 / 技能描述。

为什么要单独一份数据
--------------------
路线分析用的 ``enemy_database.json``（由 ``levels/enemydata`` 打包而来）
只有**数值和技能代码**，没有任何一句人话：

    {"prefabKey": "LandSwingTail", "cooldown": 12.0,
     "blackboard": [{"key": "atk_scale", "value": 1.4}]}

而 ``excel/enemy_handbook_table.json``（游戏内「敌人档案」页签）里才有
真正的描述文本，字段是 ``abilityList``：

    [{"text": "无法被阻挡", "textFormat": "NORMAL"},
     {"text": "陆行姿态",   "textFormat": "TITLE"},
     {"text": "【咆哮】使所有友方单位眩晕", "textFormat": "NORMAL"}]

``textFormat`` 的三种取值不是排版噪声，语义要照抄：

* ``TITLE``  —— 小标题（换形态 / 换阶段时出现），要起新段落；
* ``NORMAL`` —— 正文一条，按项目符号排；
* ``SILENCE``—— 表示「这一条会被沉默打断」，图上要单独标出来。

文本里还夹着 ``<$ba.stun>晕眩</>`` 这类富文本标记（``<$`` / ``<@``
开头），标签本身要剥掉但**标签中间的字必须留下**，否则会出现
「使范围内所有单位」这种缺主语的句子。``strip_tags`` 就是干这个的，
并且比正则稳：正则版本遇到 ``<$ba.dt.burning>灼燃损伤</>`` 这种带
点号的长 key 容易贪婪匹配到下一个 ``>`` 上。
"""
from __future__ import annotations

import json
import os
import re
from typing import Dict, List, Optional

#: 富文本标签：以 ``<`` 开头 ``>`` 结尾，内部不含 ``<``（避免跨标签贪婪）
_TAG_RE = re.compile(r"<[^<>]*>")
#: 解包文本里偶尔真的会出现换行转义
_NL_RE = re.compile(r"\\n|\r\n|\r")


def strip_tags(text: str) -> str:
    """剥掉 ``<$ba.xxx>`` / ``<@eb.xxx>`` 之类的富文本标签，保留正文。

    例：``使范围内所有单位<$ba.stun>晕眩</>`` -> ``使范围内所有单位晕眩``
    """
    if not text:
        return ""
    out = _TAG_RE.sub("", str(text))
    return _NL_RE.sub(" ", out).strip()


#: textFormat -> 中文说明（图鉴里要解释这个标记是什么意思）
FORMAT_HINTS = {
    "TITLE": "小标题",
    "NORMAL": "正文",
    "SILENCE": "可被沉默",
}


class HandbookIndex:
    """``enemy_handbook_table.json`` 的只读索引。

    文件约 1.4 MB，只在打开图鉴时懒加载一次，之后全进程复用。
    """

    def __init__(self, path: str = ""):
        self.path = path or ""
        self._by_id: Dict[str, dict] = {}
        self._name_to_id: Dict[str, str] = {}
        self._loaded = False
        self._error = ""

    # ---------------------------------------------------------- 加载

    @property
    def loaded(self) -> bool:
        return self._loaded

    @property
    def error(self) -> str:
        return self._error

    def load(self) -> bool:
        if self._loaded:
            return True
        if not self.path or not os.path.isfile(self.path):
            self._error = "缺少 enemy_handbook_table.json"
            return False
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                raw = json.load(f)
        except (OSError, ValueError) as e:
            self._error = "读取失败：%s" % e
            return False
        data = (raw or {}).get("enemyData") or raw or {}
        if not isinstance(data, dict):
            self._error = "结构异常（enemyData 不是字典）"
            return False
        self._by_id = data
        for eid, rec in data.items():
            if not isinstance(rec, dict):
                continue
            nm = strip_tags(str(rec.get("name") or ""))
            if nm:
                # 同名敌人有多档时保留第一个（手册里通常就是基础档）
                self._name_to_id.setdefault(nm, eid)
        self._loaded = True
        return True

    # ---------------------------------------------------------- 查询

    def get(self, enemy_id: str) -> Optional[dict]:
        if not self.load():
            return None
        return self._by_id.get(enemy_id or "")

    def find_id(self, name: str) -> str:
        """按中文名反查 enemy_id（路线里的名字未必带 id）。"""
        if not self.load():
            return ""
        return self._name_to_id.get((name or "").strip(), "")

    def display_name(self, enemy_id: str) -> str:
        rec = self.get(enemy_id)
        return strip_tags(str((rec or {}).get("name") or ""))

    def description(self, enemy_id: str) -> str:
        rec = self.get(enemy_id)
        return strip_tags(str((rec or {}).get("description") or ""))

    def raw_abilities(self, enemy_id: str) -> List[dict]:
        """原始 ``abilityList``（保留 textFormat，便于图鉴标出可沉默项）。"""
        rec = self.get(enemy_id)
        out = []
        for item in ((rec or {}).get("abilityList") or []):
            if not isinstance(item, dict):
                continue
            text = strip_tags(str(item.get("text") or ""))
            if not text:
                continue
            out.append({
                "text": text,
                "format": str(item.get("textFormat") or "NORMAL").upper(),
            })
        return out

    def sections(self, enemy_id: str) -> List[dict]:
        """把 ``abilityList`` 折成「小标题 + 若干条正文」。

        返回值形如::

            [{"title": "",          "lines": [{"text": "无法被阻挡", "silence": False}]},
             {"title": "陆行姿态",   "lines": [{"text": "【咆哮】…", "silence": False}]}]

        第一条如果前面没有 ``TITLE``，title 就是空串（表示「总述」段）。
        """
        out: List[dict] = []
        cur: Optional[dict] = None
        for item in self.raw_abilities(enemy_id):
            fmt = item["format"]
            if fmt == "TITLE":
                cur = {"title": item["text"], "lines": []}
                out.append(cur)
                continue
            if cur is None:
                cur = {"title": "", "lines": []}
                out.append(cur)
            cur["lines"].append({
                "text": item["text"],
                "silence": fmt == "SILENCE",
            })
        return [s for s in out if s["lines"] or s["title"]]

    def tags(self, enemy_id: str) -> List[str]:
        rec = self.get(enemy_id)
        tags = (rec or {}).get("enemyTags") or []
        return [str(t) for t in tags if str(t).strip()]

    def damage_types(self, enemy_id: str) -> List[str]:
        rec = self.get(enemy_id)
        return [str(d) for d in ((rec or {}).get("damageType") or [])]

    def race(self, enemy_id: str) -> str:
        rec = self.get(enemy_id)
        return str((rec or {}).get("race") or "")


#: 伤害类型 -> 中文（图鉴里要显示「攻击造成什么伤害」）
DAMAGE_CN = {
    "PHYSIC": "物理",
    "MAGIC": "法术",
    "HEAL": "治疗",
    "NO_DAMAGE": "无伤害",
    "TRUE": "真实",
    "ELEMENT": "元素",
}


def damage_text(codes: List[str]) -> str:
    names = [DAMAGE_CN.get(c, c) for c in codes if c]
    return "、".join(names)
