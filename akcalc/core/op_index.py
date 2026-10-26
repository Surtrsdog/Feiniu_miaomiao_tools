# -*- coding: utf-8 -*-
"""干员分类索引：按职业 / 细分职业 / 星级 / 站位筛选，并给出稳定排序。

463 位干员如果只按名字排序，找一个人要翻很久。这里把缓存整理成带分类
的行，既能过滤，也让下拉列表按「职业 -> 细分职业 -> 星级」自然聚拢。
"""
from __future__ import annotations

from typing import Dict, Iterable, List, NamedTuple, Optional

#: 主职业展示顺序（与游戏内职业顺序一致）
PROFESSION_ORDER = ("先锋", "近卫", "重装", "狙击", "术师", "医疗", "辅助", "特种")
#: 站位展示顺序
POSITION_ORDER = ("近战位", "远程位")
#: 下拉里代表「不限」的选项
ALL = "全部"


def rarity_label(rarity: int) -> str:
    """缓存里的 rarity 是 0 基（0 -> 1 星）。"""
    return "%d星" % (int(rarity) + 1)


def parse_rarity_label(text: str) -> Optional[int]:
    """"6星" -> 5；"全部" / 非法值 -> None。"""
    t = (text or "").strip()
    if not t or t == ALL:
        return None
    if t.endswith("星"):
        t = t[:-1]
    try:
        return int(t) - 1
    except ValueError:
        return None


def _prof_rank(profession: str) -> int:
    try:
        return PROFESSION_ORDER.index(profession)
    except ValueError:
        return len(PROFESSION_ORDER)


class OperatorRow(NamedTuple):
    """分类所需的最小字段集。"""

    name: str
    rarity: int          # 0 基
    profession: str
    sub: str
    position: str


def _sort_key(row: OperatorRow):
    # 职业 -> 细分 -> 星级降序 -> 名字，让同类干员挨在一起
    return (_prof_rank(row.profession), row.sub, -row.rarity, row.name)


class OperatorIndex:
    """把干员缓存整理成可筛选、可排序的索引。"""

    def __init__(self, rows: Iterable[OperatorRow]):
        self._rows: List[OperatorRow] = sorted(rows, key=_sort_key)

    # ---------------------------------------------------------- 构造

    @classmethod
    def from_cache(cls, data: Dict[str, dict]) -> "OperatorIndex":
        rows = []
        for key, d in (data or {}).items():
            if not isinstance(d, dict):
                continue
            rows.append(OperatorRow(
                name=str(d.get("name") or key),
                rarity=int(d.get("rarity") or 0),
                profession=str(d.get("profession") or "未知"),
                sub=str(d.get("sub_profession") or ""),
                position=str(d.get("position") or ""),
            ))
        return cls(rows)

    # ---------------------------------------------------------- 基本读数

    def __len__(self) -> int:
        return len(self._rows)

    def __iter__(self):
        return iter(self._rows)

    def professions(self) -> List[str]:
        seen = {r.profession for r in self._rows}
        head = [p for p in PROFESSION_ORDER if p in seen]
        return head + sorted(seen - set(PROFESSION_ORDER))

    def subs_of(self, profession: Optional[str] = None) -> List[str]:
        if profession in (None, "", ALL):
            seen = {r.sub for r in self._rows if r.sub}
        else:
            seen = {r.sub for r in self._rows
                    if r.profession == profession and r.sub}
        return sorted(seen)

    def rarities(self) -> List[int]:
        """降序：6 星在前。"""
        return sorted({r.rarity for r in self._rows}, reverse=True)

    def positions(self) -> List[str]:
        seen = {r.position for r in self._rows if r.position}
        head = [p for p in POSITION_ORDER if p in seen]
        return head + sorted(seen - set(POSITION_ORDER))

    def row_of(self, name: str) -> Optional[OperatorRow]:
        for r in self._rows:
            if r.name == name:
                return r
        return None

    # ---------------------------------------------------------- 筛选

    def filter(self, *, profession=None, sub=None, rarity=None,
               position=None, query="") -> List[str]:
        """按条件筛选，返回按 _sort_key 排好序的名字列表。

        各参数传 None / "全部" / "" 都表示不限。
        """
        q = (query or "").strip().lower()
        out: List[str] = []
        for r in self._rows:
            if profession not in (None, "", ALL) and r.profession != profession:
                continue
            if sub not in (None, "", ALL) and r.sub != sub:
                continue
            if rarity is not None and r.rarity != rarity:
                continue
            if position not in (None, "", ALL) and r.position != position:
                continue
            if q and not self._matches(r, q):
                continue
            out.append(r.name)
        return out

    @staticmethod
    def _matches(row: OperatorRow, q: str) -> bool:
        """名字子串匹配；也支持直接按职业/细分/星级搜。"""
        if q in row.name.lower():
            return True
        if q in row.profession.lower() or q in row.sub.lower():
            return True
        return q in rarity_label(row.rarity).lower()

    # ---------------------------------------------------------- 展示

    def summary(self, names: List[str]) -> str:
        """把筛选结果压缩成一句分类统计，如 "近卫 90 ｜ 6★ 21"。"""
        rows = [r for r in self._rows if r.name in set(names)]
        if not rows:
            return "无匹配"
        profs = {}
        for r in rows:
            profs[r.profession] = profs.get(r.profession, 0) + 1
        parts = ["%s %d" % (p, n) for p, n in
                 sorted(profs.items(), key=lambda kv: -kv[1])[:3]]
        six = sum(1 for r in rows if r.rarity == 5)
        if len(prof_ := sorted({r.profession for r in rows})) == 1 and six:
            parts.append("6★ %d" % six)
        return " ｜ ".join(parts)