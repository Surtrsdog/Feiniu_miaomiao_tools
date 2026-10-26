# -*- coding: utf-8 -*-
"""用户设置：目前只有字号档位，读写 cache/settings.json。

单独成模块是为了让 UI 和测试都能拿同一份默认值，避免两边
各写一套字面量导致读回来的值和界面显示不一致。
"""

from __future__ import annotations

import io
import json
import os
from typing import Any, Dict

# 字号档位：显示名 -> 缩放比例
FONT_SCALES = (
    ("小", 0.85),
    ("标准", 1.0),
    ("大", 1.2),
    ("特大", 1.45),
)
DEFAULT_FONT_LABEL = "标准"

DEFAULTS: Dict[str, Any] = {
    "font_size": DEFAULT_FONT_LABEL,
}


def scale_of(label: str) -> float:
    """字号档位名 -> 缩放比例，未知的按标准处理。"""
    for name, sc in FONT_SCALES:
        if name == label:
            return sc
    return 1.0


def label_of(scale: float) -> str:
    """缩放比例 -> 最接近的档位名。"""
    best = DEFAULT_FONT_LABEL
    diff = 9.9
    for name, sc in FONT_SCALES:
        if abs(sc - scale) < diff:
            diff = abs(sc - scale)
            best = name
    return best


def load(path: str) -> Dict[str, Any]:
    """读设置；文件不存在或损坏都返回默认值，绝不抛异常。"""
    data = dict(DEFAULTS)
    try:
        with io.open(path, "r", encoding="utf-8") as f:
            raw = json.load(f)
        if isinstance(raw, dict):
            for k, v in raw.items():
                if isinstance(v, (str, int, float, bool)):
                    data[k] = v
    except (OSError, ValueError):
        pass
    if data.get("font_size") not in [n for n, _ in FONT_SCALES]:
        data["font_size"] = DEFAULT_FONT_LABEL
    return data


def save(path: str, data: Dict[str, Any]) -> bool:
    """写设置；失败返回 False（不因为写不了配置就把程序打挂）。"""
    try:
        d = os.path.dirname(path)
        if d:
            os.makedirs(d, exist_ok=True)
        with io.open(path, "w", encoding="utf-8", newline="\n") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except OSError:
        return False
