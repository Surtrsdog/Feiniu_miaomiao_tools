"""地图坐标：把 (row, col) 换算成国际象棋式「A1 / C7」标注。

约定（与 PRTS.Map 一致）
------------------------
* 列 -> 字母 A、B、C …（列 0 是 A），超过 26 列继续 AA、AB。
* 行 -> 数字，**自下往上**数：最下面一行是 1。
  游戏里 row 0 是最上面一行，所以 数字 = 高度 - row。

于是左上角是 A<height>，右下角是 <末字母>1。
"""
from __future__ import annotations

from typing import Tuple


def col_letter(col: int) -> str:
    """列号 -> 字母（0 -> A, 25 -> Z, 26 -> AA）。"""
    if col < 0:
        return "?"
    out = ""
    n = col
    while True:
        out = chr(ord("A") + n % 26) + out
        n = n // 26 - 1
        if n < 0:
            break
    return out


def coord_label(row: int, col: int, height: int) -> str:
    """(row, col) -> 「A1」这样的坐标标签。"""
    return "%s%d" % (col_letter(col), max(1, height - row))


def coord_pair(row: int, col: int, height: int) -> Tuple[str, str]:
    return col_letter(col), str(max(1, height - row))


def parse_label(label: str, height: int):
    """把「C7」还原成 (row, col)，失败返回 None。"""
    if not label:
        return None
    letters = ""
    digits = ""
    for ch in label.strip().upper():
        if ch.isalpha():
            if digits:
                return None
            letters += ch
        elif ch.isdigit():
            digits += ch
        else:
            return None
    if not letters or not digits:
        return None
    n = 0
    for ch in letters:
        n = n * 26 + (ord(ch) - ord("A") + 1)
    col = n - 1
    row = height - int(digits)
    return (row, col)