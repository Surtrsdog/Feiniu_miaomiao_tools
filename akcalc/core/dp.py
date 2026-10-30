"""部署费用（DP）经济系统。

B2 §5: 明日方舟的战术节奏由部署费用驱动。本模块实现：
- 费用自然回复（含停回 / 负费半速 / 上限封顶）
- 部署花费 / 撤退返还
- 再部署惩罚（每层 ×0.5，上限 2 层）
- 费用曲线生成（给 UI 画图）

关键设计约束
--------------
``settle()`` 必须支持**任意跳时**（沙盘时间轴可被游标拖动、
粗轴点击、撤销/重做），不能像实时游戏那样「往前走一格」。
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

#: 回复间隔超过此值视为「停回」（永不自然回复）
REGEN_DISABLED_THRESHOLD = 1000.0


@dataclass
class DPEconomy:
    """headless DP 经济状态机。

    Parameters
    ----------
    initial : float
        初始费用（options.initialCost）。
    cap : float
        费用上限（options.maxCost）。
    interval : float
        每 +1 费所需秒数（options.costIncreaseTime）；
        ``>= REGEN_DISABLED_THRESHOLD`` 视为停回。
    allow_negative : bool
        是否允许负费（可露希尔后机制），默认关。
    refund_ratio : float
        撤退返还比例，默认 1.0（全额返还本次实际消耗）。
    """

    initial: float = 10.0
    cap: float = 99.0
    interval: float = 1.0
    allow_negative: bool = False
    refund_ratio: float = 1.0

    current: float = field(init=False)
    _last_settle: float = field(init=False, default=0.0)
    regen_disabled: bool = field(init=False, default=False)

    def __post_init__(self):
        self.current = float(self.initial)
        self.regen_disabled = self.interval >= REGEN_DISABLED_THRESHOLD
        self._last_settle = 0.0

    # ------------------------------------------------------------------ 核心

    def settle(self, t: float) -> float:
        """结掉 [``_last_settle``, t] 的费用回复，返回当前费用。

        支持任意跳时（向前 / 向后都不报错）。向后跳时直接重置
        ``_last_settle``；向前跳时做分段积分处理负费半速与上限封顶。
        """
        t = float(t)
        if t <= self._last_settle + 1e-12:
            self._last_settle = max(t, 0.0)
            return self.current
        if self.regen_disabled:
            self._last_settle = t
            return self.current
        t0 = self._last_settle
        cur = self.current
        while t0 < t - 1e-12:
            if not self.allow_negative and cur < 0:
                cur = 0.0
            if cur < 0:
                rate = 0.5 / self.interval
                need = -cur
                dt_need = need / rate if rate > 0 else t - t0
                if t0 + dt_need <= t:
                    t0 += dt_need
                    cur = 0.0
                else:
                    cur += rate * (t - t0)
                    t0 = t
                    break
            else:
                rate = 1.0 / self.interval
                room = self.cap - cur
                if room <= 1e-12:
                    t0 = t
                    break
                dt_need = room / rate if rate > 0 else t - t0
                if t0 + dt_need <= t:
                    t0 += dt_need
                    cur = self.cap
                else:
                    cur += rate * (t - t0)
                    t0 = t
                    break
        self.current = cur
        self._last_settle = t0
        return cur

    def can_afford(self, cost: float) -> bool:
        """当前费用是否足够支付 *cost*。"""
        return self.current >= float(cost) - 1e-9

    def spend(self, cost: float) -> bool:
        """扣费。不足则返回 False 且不改变状态。"""
        c = float(cost)
        if not self.can_afford(c):
            return False
        self.current -= c
        return True

    def refund(self, cost: float) -> float:
        """撤退返还费用。返回实际返还额（受 refund_ratio 限制）。"""
        actual = float(cost) * self.refund_ratio
        self.current = min(self.cap, self.current + actual)
        return actual

    # ------------------------------------------------------------------ 曲线

    def curve(self, t0: float, t1: float,
              step: float = 1.0) -> List[Tuple[float, float]]:
        """生成 [t0, t1] 的费用曲线采样点，返回 [(time, dp), ...]。"""
        saved_last = self._last_settle
        saved_cur = self.current
        self.settle(t0)
        out: List[Tuple[float, float]] = []
        t = float(t0)
        while t <= t1 + 1e-9:
            self.settle(t)
            out.append((t, round(self.current, 4)))
            t += step
        # 还原状态（curve 是只读查询）
        self._last_settle = saved_last
        self.current = saved_cur
        return out

    # ------------------------------------------------------------------ 快照

    def snapshot(self) -> dict:
        """序列化当前状态（用于撤销/重做快照）。"""
        return {
            "current": self.current,
            "_last_settle": self._last_settle,
        }

    @classmethod
    def from_snapshot(cls, base: "DPEconomy", snap: dict) -> "DPEconomy":
        """从快照恢复（保留 base 的参数配置，只覆盖运行状态）。"""
        obj = cls(
            initial=base.initial,
            cap=base.cap,
            interval=base.interval,
            allow_negative=base.allow_negative,
            refund_ratio=base.refund_ratio,
        )
        obj.current = snap.get("current", base.initial)
        obj._last_settle = snap.get("_last_settle", 0.0)
        obj.regen_disabled = base.regen_disabled
        return obj


# ------------------------------------------------------------------- 再部署惩罚

class RedeployPenalty:
    """再部署惩罚追踪器。

    每次退场（撤退 / 击倒）累积一层，上限 2 层，
    每层给自己的待部署费用提供 ×0.5 倍率：

    ======== =========
    层数     费用倍率
    ======== =========
    0        x1.000
    1        x0.500
    2        x0.250（封顶）
    ======== =========
    """

    MAX_STACKS = 2
    _stacks: dict  # op_id -> int (0~MAX_STACKS)

    def __init__(self):
        self._stacks = {}

    def stacks(self, op_id: str) -> int:
        return min(self._stacks.get(op_id, 0), self.MAX_STACKS)

    def add(self, op_id: str) -> int:
        s = self.stacks(op_id) + 1
        self._stacks[op_id] = min(s, self.MAX_STACKS)
        return self._stacks[op_id]

    def multiplier(self, op_id: str) -> float:
        return 0.5 ** self.stacks(op_id)

    def reset(self, op_id: str) -> None:
        self._stacks.pop(op_id, None)

    def reset_all(self) -> None:
        self._stacks.clear()
