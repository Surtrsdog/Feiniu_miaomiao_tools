"""帧 ↔ 秒换算（敌人与干员共用）。

为什么单独成一个模块
--------------------
敌人抬手（:mod:`akcalc.core.enemy_timing`）和干员抬手
（:mod:`akcalc.core.operator_timing`）的数据结构不同，但**换算规则完全
相同**：解包数据按 30fps 烘焙，``eventTime`` 本质就是「帧号 / 30」。

如果两个模块各写一份 ``* 30``，迟早会出现「敌人图鉴说 19 帧、干员图
鉴说 20 帧」这种自相矛盾。所以常量与算法只在这里定义一次，两边都
``from .timing import ...``。

30 是真帧，60/120 是插值帧
--------------------------
游戏逻辑固定 **30 步/秒**，帧号是逻辑帧。60/120 只是高刷设备上的渲染
插值——同一时长下帧号成比例：14 帧@30 == 28 帧@60 == 56 帧@120。
所以对外报帧号时永远以 30 为准，另外附上三档对照表。
"""
from __future__ import annotations

from typing import Optional

from .constants import FPS as _GAME_FPS

#: 动画烘焙帧率。``eventTime`` 本质是帧号/30，秒↔帧是精确互转，不是估算。
#: 数值直接取自 :mod:`akcalc.core.constants`（沙盘物理模拟用的同一个帧率），
#: 保证图鉴报的帧号和沙盘跑的帧号永远不会分家。这里转成 int——帧号必须是
#: 整数，浮点 30.0 参与 ``round()`` 再变回 int 容易在边界上多算一帧。
FPS = int(_GAME_FPS)
assert FPS == _GAME_FPS, "constants.FPS 必须是整数帧率"

#: 支持展示/换算的运行帧率档位。60/120 是插值帧。
SUPPORTED_FPS = (30, 60, 120)

#: 一帧多少秒
SEC_PER_FRAME = 1.0 / FPS


def frames_at(frame, fps: int):
    """把 30fps 的帧号换算到别的运行帧率下的帧号。

    ``fps`` 只认 30/60/120。倍率不是整数时向上取整——插值帧宁可多报
    一帧（更保守），也不把「半帧」悄悄抹掉让人误判能卡过去。
    """
    if not isinstance(frame, int) or fps not in SUPPORTED_FPS:
        return None
    if fps == FPS:
        return frame
    v = frame * fps / FPS
    return int(v) if float(v).is_integer() else int(v) + 1


def at_fps_table(frame):
    """一个 30fps 帧号在三个档位下的对照表。

    返回 ``{"30": 14, "60": 28, "120": 56}``；输入非法返回 None。
    """
    if not isinstance(frame, int):
        return None
    return {str(f): frames_at(frame, f) for f in SUPPORTED_FPS}


def sec_to_frames(sec: Optional[float]) -> Optional[int]:
    """秒 -> 帧（四舍五入到整帧）。

    游戏数据是按帧烘焙的，所以这里四舍五入是**还原**原始帧号，
    不是估算。例：0.3333s -> 10 帧，0.4667s -> 14 帧。
    """
    if not isinstance(sec, (int, float)) or isinstance(sec, bool):
        return None
    return int(round(float(sec) * FPS))


def frames_to_sec(frame: Optional[int]) -> Optional[float]:
    """帧 -> 秒。30 帧 = 1.0 秒，1 帧 ≈ 0.0333 秒。"""
    if not isinstance(frame, (int, float)) or isinstance(frame, bool):
        return None
    return float(frame) / FPS


def convert(value: Optional[float], from_unit: str = "second") -> dict:
    """单位换算，给 MCP 的「换算工具」和设置页的预览用。

    ``from_unit`` 取 ``"second"`` / ``"frame"``。返回同时含两种单位
    与帧号的字典；非法输入返回 ``{"error": ...}``。
    """
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        return {"error": "value 必须是数字"}
    u = str(from_unit or "second").strip().lower()
    if u in ("second", "seconds", "s", "sec", "秒"):
        sec = float(value)
        frame = sec_to_frames(sec)
    elif u in ("frame", "frames", "f", "帧"):
        frame = int(round(float(value)))
        sec = frames_to_sec(frame)
    else:
        return {"error": "from_unit 只支持 second / frame，收到：%r" % from_unit}
    return {
        "fps": FPS,
        "frame": frame,
        "second": round(sec, 4),
        "formatted": "%d 帧 / %.3f 秒" % (frame, sec),
        # 同一抬手在三个运行档位下的帧号：游戏逻辑 30fps，
        # 60/120 是插值帧。14 帧@30 == 28 帧@60 == 56 帧@120。
        "frames_at_fps": at_fps_table(frame) or {},
    }
