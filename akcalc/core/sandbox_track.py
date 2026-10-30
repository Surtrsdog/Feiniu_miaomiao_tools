"""沙盘粗轴：记录干员部署 / 撤退 / 开技能的时间线。

「粗轴」是玩家对「部署轴」的叫法——它不追求逐帧精确，只记录
「第几秒在哪个格子放了谁、第几秒撤了、第几秒开技能」这些关键动作，
用于和别人的思路交流。

这个模块只做**数据 + 计算**，不碰 tkinter。

三条设计约定
============

1. **时间一律是游戏秒**，从关卡开始（0.0）计。不用墙钟，不用帧号。
   这样导出的 JSON 换台机器、换个播放速度都是同一个含义。

2. **干员的存在是一段区间** ``[deploy, retreat)``；未撤退则为无穷。
   轴上的每个动作都是「在某个时刻发生的事件」，事件列表按时间排序，
   渲染时从左到右扫一遍就能得到任意时刻的场上状态。

3. **技能回转按真实 SP 规则算**，但不模拟技能效果。
   用户明确说「你无需模拟干员技能情况 此时只需要模拟她的回转情况」，
   所以我们只算 SP：自然回复 + 攻击回复 + 受击回复，
   开了技能就进入持续期，结束后 SP 归零进入下一轮。
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

Coord = Tuple[int, int]

#: SP 回复类型。对应游戏里技能的 ``spRecoverType``。
SP_AUTO = "AUTO"          # 自然回复（不受阻回影响）
SP_ATTACK = "ATTACK"      # 攻击回复（打一下回一点，阻回时也回）
SP_DEFENSE = "DEFENSE"    # 受击回复
SP_NONE = "NONE"          # 不回复（一次性技能）

#: 触发方式。取自解包 ``skill_table_full.json`` 的 ``skillType``
#: （``AUTO`` / ``MANUAL`` / ``PASSIVE``），也兼容 PRTS 的
#: ``技能类型2``（「自动触发」/「手动触发」）。
#:
#: **这是「谁决定技能开启」的问题，和 ``recover``（SP 怎么涨）正交**：
#: 自然回复 + 手动触发（银灰真银斩）、攻击回复 + 自动触发（克洛丝
#: 二连射）都真实存在，不能用一个字段同时表达。
TRIG_AUTO = "AUTO"        # 自动触发：SP 一满立刻自己开，玩家不能选择时机
TRIG_MANUAL = "MANUAL"    # 手动触发：SP 满了要玩家点，什么时候开是用户决定的
TRIG_PASSIVE = "PASSIVE"  # 被动：落地生效，没有「开启」这个动作

#: 部署动作类型
ACT_DEPLOY = "deploy"
ACT_RETREAT = "retreat"
ACT_SKILL = "skill"


@dataclass
class SkillCycle:
    """一个技能的 SP 参数（从 skilldata 解析出来）。"""

    sp_cost: float = 0.0          # 需要多少 SP 才能开
    init_sp: float = 0.0          # 初始 SP
    duration: float = 0.0         # 技能持续时间（秒）
    recover: str = SP_AUTO        # 回复类型
    infer_attack: bool = False    # 是否按攻击间隔回复
    # B3 §6.4: 可充能次数（maxChargeTime，默认 1 = 普通）
    max_charge: int = 1
    # B3 §6.5: 持续类型（NONE / AMMO）
    duration_type: str = "NONE"
    # B3 §6.5: 弹药数（从 blackboard attack@trigger_time 取）
    ammo: int = 0
    #: 触发方式，见 ``TRIG_*``。默认 ``MANUAL``：宁可让用户自己点，
    #: 也不要把「理论最早可开」画成「真的开了」——后者会让用户误以为
    #: 轴上的技能段是既成事实。
    trigger: str = TRIG_MANUAL

    @property
    def is_auto_trigger(self) -> bool:
        """是不是「SP 满自动开」。只有这类才允许在轴上画推演出来的循环。"""
        return self.trigger == TRIG_AUTO

    @property
    def is_manual_trigger(self) -> bool:
        return self.trigger == TRIG_MANUAL

    @property
    def is_passive(self) -> bool:
        """没有「开启」这个动作。

        两种来源都算：``skillType == PASSIVE``（解包直接标注），
        或 ``sp_cost <= 0``（老数据/PRTS 没给消耗，等价于不需要 SP）。
        不能只看后者——有技能的 ``spCost`` 恰好是 0 但它仍需手动开启。
        """
        return self.trigger == TRIG_PASSIVE or self.sp_cost <= 0

    @property
    def is_continuous(self) -> bool:
        """持续到手动关闭（duration<=0 但 sp_cost>0）。"""
        return self.sp_cost > 0 and self.duration <= 0 and self.duration_type != "AMMO"

    @property
    def is_ammo(self) -> bool:
        """B3 §6.5: 弹药技能（durationType == AMMO）。"""
        return self.duration_type == "AMMO" and self.ammo > 0

    @property
    def sp_max(self) -> float:
        """B3 §6.4: SP 上限 = sp_cost × max_charge。"""
        return float(self.sp_cost * max(1, self.max_charge))


@dataclass
class TimelineEvent:
    """粗轴上的一个动作。"""

    time: float
    kind: str                     # deploy / retreat / skill
    uid: int = 0                  # 对应 Deployment 的 uid
    row: int = -1
    col: int = -1
    name: str = ""                # 冗余存一份，方便导出可读
    note: str = ""

    def to_dict(self) -> dict:
        d = {"t": round(float(self.time), 3), "kind": self.kind,
             "uid": int(self.uid)}
        if self.kind == ACT_DEPLOY:
            d["row"] = int(self.row)
            d["col"] = int(self.col)
            if self.name:
                d["name"] = self.name
        if self.note:
            d["note"] = self.note
        return d


@dataclass
class Deployment:
    """一次部署（从放下到撤走）。

    注意这不是 ``sandbox.OperatorPiece``：那个是「当前场上的一枚棋子」，
    这个是「历史上的一次部署」，两者生命周期不同。撤退后 Piece 没了，
    Deployment 仍然保留在粗轴上供导出。
    """

    uid: int
    row: int
    col: int
    op_id: str = ""
    name: str = ""
    profession: str = ""
    #: 部署位类型：``HIGH``(高台) / ``LOW``(地面)
    ground: str = "LOW"
    #: 阻挡数（地面干员才真正挡人）
    block_count: int = 0
    #: 是否远程位（远程位不能挡地面敌人）
    is_ranged: bool = False
    #: 这枚单位能否阻挡**飞行**敌人。
    #:
    #: 游戏里没有「飞行干员」，但用户的沙盘需求明确要求「飞行干员可以
    #: 阻挡飞行敌人」——指的是一部分单位（召唤物、地面近战对空）能拦
    #: 空中单位。数据包里没有这个字段，所以不猜：默认 False，由用户在
    #: 干员右键菜单里显式打开，再记进粗轴一起导出。
    can_block_fly: bool = False
    facing: str = "RIGHT"
    deploy_time: float = 0.0
    retreat_time: Optional[float] = None
    #: 技能参数（按选中的技能）
    skill: SkillCycle = field(default_factory=SkillCycle)
    skill_name: str = ""
    #: 用户手动记录的开技能时刻（粗轴上的 skill 事件）
    skill_uses: List[float] = field(default_factory=list)
    #: 部署费用（用于粗轴显示）
    cost: int = 0
    charges: int = 0
    #: 全员 SP 回复速度加成（「技力光环」这类天赋给的每秒额外点数）。
    #:
    #: 沙盘里每枚干员各自有一份 ``SkillCycle``，但白面鸮/陈/华法琳这类
    #: 天赋是**给别人**加回复速度的。把「谁给谁加了多少」存成规则太复杂
    #: 且数据里没有，所以这里只存一个已经汇总到本干员身上的额外速率
    #: （点/秒），由面板在算回转前叠加进 ``SkillSim.sp_rate``。
    sp_boost: float = 0.0

    @property
    def alive_from(self) -> float:
        return self.deploy_time

    def alive_at(self, seconds: float) -> bool:
        if seconds < self.deploy_time:
            return False
        return self.retreat_time is None or seconds < self.retreat_time

    def alive_span(self, total: float) -> Tuple[float, float]:
        """存活区间（未撤退则画到轴尾）。"""
        end = self.retreat_time if self.retreat_time is not None else total
        return (self.deploy_time, max(self.deploy_time, end))

    @property
    def blocking(self) -> int:
        """实际能挡几个。远程位是 0（高台不挡地面敌人）。"""
        if self.is_ranged:
            return 0
        return max(0, int(self.block_count))


class SkillSim:
    """技能回转模拟。

    只算 SP，不管技能效果。规则（实测自游戏）：

    * ``SP_AUTO``（自然回复）：每秒回 1 点，与是否攻击/阻挡无关。
    * ``SP_ATTACK``（攻击回复）：每次攻击回 1 点。攻击间隔已知时
      按 ``1 / attack_interval`` 折算成「每秒回复量」。
    * ``SP_DEFENSE``（受击回复）：被打才回，沙盘里没有攻击判定，
      按 0 处理并在提示里说明。

    「阻回」是玩家术语，指**技能持续期间该干员停止攻击**（如银灰
    真银斩期间仍在打，而某些技能会停顿）。技能持续期内我们不发
    攻击事件，所以攻击回复类的 SP 在持续期内本来就不涨——这与游戏
    一致，不需要额外开关。
    """

    def __init__(self, attack_interval: float = 1.0):
        self.attack_interval = max(0.05, float(attack_interval or 1.0))

    def sp_rate(self, sk: SkillCycle, boost: float = 0.0) -> float:
        """每秒回复的 SP 点数。

        ``boost`` 是**别的干员给的额外自然回复速率**（点/秒），例如白面鸮
        「技力光环 +0.30」、陈「每 3 秒全场 1 点」≈0.33、维娜 +0.2。
        游戏里这类光环只加速「自然回复」，对攻击/受击回复无效，所以
        只在 ``SP_AUTO`` 分支上叠加。
        """
        if sk.recover == SP_ATTACK:
            return 1.0 / self.attack_interval
        if sk.recover == SP_DEFENSE:
            return 0.0
        if sk.recover == SP_NONE:
            return 0.0
        return 1.0 + max(0.0, float(boost or 0.0))

    def cycles(self, sk: SkillCycle, end_time: float,
               start: float = 0.0,
               boost: float = 0.0) -> List[Tuple[float, float, float]]:
        """算出 [start, end_time] 内的技能轮次。

        返回 ``[(ready_at, active_from, active_to), ...]``。
        B3 §6.3-6.5 增强：
        - 攻击/受击回复技能在持续期间继续回 SP（recover_in_skill）
        - 可充能技能（max_charge > 1）SP 上限抬高
        - 弹药技能（AMMO）持续时间 = ammo × attack_interval
        """
        if sk.is_passive or sk.sp_cost <= 0:
            return []
        sp_max = sk.sp_max  # B3 §6.4: 可充能时上限更高
        sp = max(0.0, min(float(sk.init_sp), sp_max))
        t = max(0.0, float(start))
        end_time = max(t, float(end_time))
        rate = self.sp_rate(sk, boost)
        out: List[Tuple[float, float, float]] = []
        guard = 0

        # B3 §6.5: 弹药技能的「持续时间」= ammo × attack_interval
        if sk.is_ammo:
            ammo_dur = max(sk.ammo, 1) * self.attack_interval
            # 弹药技能只开一次就结束（不循环），因为弹药耗尽后退出
            if sp >= sk.sp_cost:
                ready = t
                active_to = min(end_time, ready + ammo_dur)
                out.append((ready, ready, active_to))
            return out

        while t < end_time and guard < 999:
            guard += 1
            if sp >= sk.sp_cost:
                ready = t
                if sk.is_continuous:
                    out.append((ready, ready, end_time))
                    break
                active_to = min(end_time, ready + max(0.0, sk.duration))
                out.append((ready, ready, active_to))
                # B3 §6.3: 攻击/受击回复在技能期间继续回 SP
                recover_in_skill = (sk.recover in (SP_ATTACK, SP_DEFENSE))
                if recover_in_skill:
                    carry = (active_to - ready) * rate
                    t = active_to
                    sp = min(sp_max, carry)
                else:
                    # 阻回：技能结束后 SP 归零
                    t = active_to
                    sp = 0.0
                continue
            if rate <= 0:
                break
            need = sk.sp_cost - sp
            dt = need / rate
            t += dt
            sp = min(sp_max, sk.sp_cost)  # B3 §6.4: 不超过可充能上限
        return out

    def state_at(self, sk: SkillCycle, seconds: float,
                 start: float = 0.0,
                 boost: float = 0.0) -> dict:
        """某时刻的技能状态，给悬停提示用。

        返回 ``{"ready": bool, "sp": float, "need": float,
        "active": bool, "next_in": float|None, "cycle_index": int,
        "charges": int}``。
        B3 §6.4: charges = 当前充能层数（floor(sp / sp_cost)）。
        """
        sp_max = sk.sp_max
        st = {"ready": False, "sp": 0.0, "need": float(sk.sp_cost),
              "active": False, "next_in": None, "cycle_index": 0,
              "passive": sk.is_passive, "charges": 0}
        if sk.is_passive or sk.sp_cost <= 0:
            st["ready"] = True
            return st
        rate = self.sp_rate(sk, boost)
        sp = max(0.0, min(float(sk.init_sp), sp_max))
        t = max(0.0, float(start))
        seconds = float(seconds)
        if seconds <= t:
            st["sp"] = sp
            st["ready"] = sp >= sk.sp_cost
            st["charges"] = int(sp // sk.sp_cost) if sk.sp_cost > 0 else 0
            st["next_in"] = max(0.0, (sk.sp_cost - sp) / rate) if rate else None
            return st
        idx = 0
        guard = 0
        while t < seconds and guard < 999:
            guard += 1
            if sp >= sk.sp_cost:
                if sk.is_continuous:
                    st.update(ready=True, active=True, sp=sp,
                              cycle_index=idx, next_in=None,
                              charges=int(sp // sk.sp_cost))
                    return st
                active_to = t + max(0.0, sk.duration)
                # B3 §6.5: 弹药技能的 active_to 用 ammo 计算
                if sk.is_ammo:
                    active_to = min(active_to,
                                    t + max(sk.ammo, 1) * self.attack_interval)
                if seconds < active_to:
                    st.update(ready=True, active=True, sp=sp,
                              cycle_index=idx,
                              next_in=max(0.0, active_to - seconds),
                              charges=int(sp // sk.sp_cost))
                    return st
                t = active_to
                # B3 §6.3: 攻击/受击回复在持续期间继续回 SP
                recover_in_skill = (sk.recover in (SP_ATTACK, SP_DEFENSE))
                if recover_in_skill:
                    carry = (active_to - t) * rate
                    sp = min(sp_max, carry)
                else:
                    sp = 0.0
                idx += 1
                continue
            if rate <= 0:
                st.update(sp=sp, ready=False, charges=int(sp // sk.sp_cost) if sk.sp_cost > 0 else 0)
                return st
            dt = (sk.sp_cost - sp) / rate
            if t + dt > seconds:
                sp += (seconds - t) * rate
                sp = min(sp_max, sp)
                t = seconds
                break
            t += dt
            sp = min(sp_max, sk.sp_cost)
        st["sp"] = min(sp, sp_max)
        st["ready"] = sp >= sk.sp_cost
        st["cycle_index"] = idx
        st["charges"] = int(st["sp"] // sk.sp_cost) if sk.sp_cost > 0 else 0
        if not st["ready"] and rate > 0:
            st["next_in"] = max(0.0, (sk.sp_cost - st["sp"]) / rate)
        return st


class CoarseTrack:
    """粗轴 + buff 轴的数据模型与 JSON 编解码。

    这是导出/导入的唯一入口。导出的 JSON 结构::

        {
          "format": "feiniu-sandbox-track",
          "version": 1,
          "stage": {"id": "main_08-04", "name": "..."},
          "duration": 180.0,
          "deployments": [
            {"uid": 1, "t": 12.5, "retreat": 95.0, "row": 3, "col": 5,
             "op_id": "char_113_cqbw", "name": "W", "ground": "HIGH",
             "facing": "RIGHT", "skill": "D12", "skill_uses": [40.0]}
          ],
          "buffs": [
            {"kind": "slow", "enemy": "...", "t": 30.0, "dur": 8.0,
             "mult": 0.5}
          ],
          "boxes": [[4, 2], [4, 3]]
        }

    导入时**不信任**文件内容：任何字段缺失都退回默认值，坏数据整份
    丢弃而不是半截应用，避免把界面搞成不可恢复的状态。
    """

    FORMAT = "feiniu-sandbox-track"
    VERSION = 1

    def __init__(self) -> None:
        self.clear()

    def clear(self) -> None:
        self.deployments: Dict[int, Deployment] = {}
        self.order: List[int] = []
        self._next_uid = 1
        #: 未绑定到具体部署的裸事件（保留导入的完整性）
        self.extra_events: List[TimelineEvent] = []
        self.stage_id = ""
        self.stage_name = ""
        self.duration = 0.0

    # ------------------------------------------------------------ 增删

    def next_uid(self) -> int:
        uid = self._next_uid
        self._next_uid += 1
        return uid

    def add(self, dep: Deployment) -> Deployment:
        if dep.uid <= 0:
            dep.uid = self.next_uid()
        else:
            self._next_uid = max(self._next_uid, dep.uid + 1)
        self.deployments[dep.uid] = dep
        self.order.append(dep.uid)
        return dep

    def get(self, uid: int) -> Optional[Deployment]:
        return self.deployments.get(int(uid))

    def remove(self, uid: int) -> bool:
        uid = int(uid)
        if uid in self.deployments:
            del self.deployments[uid]
            if uid in self.order:
                self.order.remove(uid)
            return True
        return False

    def all(self) -> List[Deployment]:
        """按部署时间排序的全部部署。"""
        return sorted(self.deployments.values(),
                      key=lambda d: (d.deploy_time, d.uid))

    def alive_at(self, seconds: float) -> List[Deployment]:
        return [d for d in self.all() if d.alive_at(seconds)]

    def events(self) -> List[TimelineEvent]:
        """把部署摊平成事件序列，按时间排序。"""
        out: List[TimelineEvent] = []
        for d in self.all():
            out.append(TimelineEvent(d.deploy_time, ACT_DEPLOY, d.uid,
                                     d.row, d.col, d.name))
            for t in d.skill_uses:
                out.append(TimelineEvent(t, ACT_SKILL, d.uid, d.row, d.col,
                                         d.name))
            if d.retreat_time is not None:
                out.append(TimelineEvent(d.retreat_time, ACT_RETREAT, d.uid,
                                         d.row, d.col, d.name))
        out.extend(self.extra_events)
        out.sort(key=lambda e: (e.time, e.kind != ACT_DEPLOY, e.uid))
        return out

    def span(self) -> float:
        """轴总长：最晚的动作时间，至少给 1 秒避免除零。"""
        ts = [e.time for e in self.events()]
        ts.append(float(self.duration or 0.0))
        return max(1.0, max(ts) if ts else 1.0)

    # ------------------------------------------------------------ 导出

    def to_dict(self) -> dict:
        deps = []
        for d in self.all():
            item = {
                "uid": d.uid,
                "t": round(float(d.deploy_time), 3),
                "row": int(d.row),
                "col": int(d.col),
                "ground": d.ground,
                "facing": d.facing,
            }
            if d.op_id:
                item["op_id"] = d.op_id
            if d.name:
                item["name"] = d.name
            if d.retreat_time is not None:
                item["retreat"] = round(float(d.retreat_time), 3)
            if d.skill_name:
                item["skill"] = d.skill_name
            # 技能回转参数必须一起落盘。``skill`` 这个名字键只是给人看的，
            # 真正驱动 skill_state / 悬停回转的是 ``skill_sp`` 这组数值：
            # 只存名字的话，导出的粗轴在别的机器上重建出来是
            # sp_cost=0 / init_sp=0，被当成「被动技能」，回转永远显示
            # 「可开启」，「悬停干员显示技能回转」直接失效。
            sk = d.skill
            if sk is not None and (sk.sp_cost or sk.init_sp or sk.duration
                                   or sk.recover not in (None, "", SP_AUTO)):
                item["skill_sp"] = {
                    "cost": round(float(sk.sp_cost or 0.0), 3),
                    "init": round(float(sk.init_sp or 0.0), 3),
                    "dur": round(float(sk.duration or 0.0), 3),
                    # recover 是字符串枚举（SP_AUTO / SP_INCREASE / …），
                    # 不是数值；这里统一成 str，导入侧才不会读成数字。
                    "recover": str(sk.recover or SP_AUTO),
                }
                if sk.infer_attack:
                    item["skill_sp"]["infer_attack"] = True
                # B3 §6.4-6.5: 新字段序列化
                if sk.max_charge > 1:
                    item["skill_sp"]["max_charge"] = int(sk.max_charge)
                if sk.duration_type and sk.duration_type != "NONE":
                    item["skill_sp"]["duration_type"] = sk.duration_type
                if sk.ammo > 0:
                    item["skill_sp"]["ammo"] = int(sk.ammo)
                # 触发方式必须落盘：不存的话导入回来一律是默认 MANUAL，
                # 自动触发的技能在轴上就画不出推演段了。
                if sk.trigger and sk.trigger != TRIG_MANUAL:
                    item["skill_sp"]["trigger"] = str(sk.trigger)
            if d.skill_uses:
                item["skill_uses"] = [round(float(t), 3) for t in d.skill_uses]
            if d.cost:
                item["cost"] = int(d.cost)
            if d.can_block_fly:
                item["block_fly"] = True
            if d.sp_boost:
                item["sp_boost"] = round(float(d.sp_boost), 4)
            # is_ranged / block_count 必须落盘。它们直接决定沙盘的
            # 阻挡判定（Deployment.blocking：远程位恒为 0），漏掉的话
            # 导出的粗轴换个机器打开，高台干员会被当成地面干员去挡路，
            # 「地面干员阻挡地面敌人、飞行干员阻挡飞行敌人」的结果全错。
            # 只在为真/非零时写，保持人工可读的 JSON 尽量短。
            if d.is_ranged:
                item["ranged"] = True
            if d.block_count:
                item["block"] = int(d.block_count)
            deps.append(item)
        return {
            "format": self.FORMAT,
            "version": self.VERSION,
            "stage": {"id": self.stage_id, "name": self.stage_name},
            "duration": round(float(self.span()), 3),
            "deployments": deps,
        }

    def dump(self, boxes=None, buffs=None) -> dict:
        """导出完整粗轴（额外带上箱子和 buff，便于复现）。

        ``boxes`` / ``buffs`` 即便是空也要**写出空数组**：文件是给人看的
        也是给程序读的，「没有 buff」和「这个版本不支持 buff」是两件事，
        少一个键就会让接收方猜。旧版本读到的空数组同样安全。
        """
        data = self.to_dict()
        data["boxes"] = [[int(r), int(c)] for (r, c) in sorted(boxes or ())]
        if data["boxes"]:
            data["box_count"] = len(data["boxes"])
        # buff 在内存里是 ``(key, t0, t1, mult)`` 四元组，直接 json.dumps 会
        # 变成 ``["k", 0.0, 10.0, 0.5]``——没有键名，用户看不出第三个数是
        # 结束时刻还是持续时长。这里落成带名字的对象，导入端两种都认。
        data["buffs"] = [_buff_to_dict(b) for b in (buffs or ())]
        data["buff_count"] = len(data["buffs"])
        return data

    def dumps(self, **kw) -> str:
        return json.dumps(self.dump(**kw), ensure_ascii=False, indent=2)

    # ------------------------------------------------------------ 导入

    @classmethod
    def from_dict(cls, raw) -> "CoarseTrack":
        """从 dict 还原。坏数据抛 ``ValueError``（由调用方提示用户）。"""
        if not isinstance(raw, dict):
            raise ValueError("文件内容不是一个 JSON 对象")
        fmt = raw.get("format")
        if fmt and fmt != cls.FORMAT:
            raise ValueError("不是粗轴文件（format=%r）" % fmt)
        tr = cls()
        stage = raw.get("stage") or {}
        if isinstance(stage, dict):
            tr.stage_id = str(stage.get("id") or "")
            tr.stage_name = str(stage.get("name") or "")
        try:
            tr.duration = max(0.0, float(raw.get("duration") or 0.0))
        except (TypeError, ValueError):
            tr.duration = 0.0
        deps = raw.get("deployments")
        if not isinstance(deps, list):
            deps = []
        for item in deps:
            if not isinstance(item, dict):
                continue
            dep = _deployment_from_dict(item)
            if dep is not None:
                tr.add(dep)
        return tr

    @classmethod
    def loads(cls, text: str) -> "CoarseTrack":
        try:
            raw = json.loads(text)
        except (ValueError, TypeError) as e:
            raise ValueError("JSON 解析失败：%s" % e)
        return cls.from_dict(raw)


def _as_float(v, default: float = 0.0) -> float:
    try:
        f = float(v)
    except (TypeError, ValueError):
        return default
    if f != f or f in (float("inf"), float("-inf")):   # NaN / inf
        return default
    return f


def _as_int(v, default: int = 0) -> int:
    try:
        return int(float(v))
    except (TypeError, ValueError):
        return default


def _buff_to_dict(item) -> dict:
    """把一段减速 buff 落成带键名的 dict。

    ``Sandbox.buffs`` 的元素是 ``(key, t0, t1, mult)``：``key`` 是「敌人
    标记」的复合串，``t0``/``t1`` 是**绝对时刻**的起止。导出给用户看时
    写成 ``{"key","t","dur","mult"}``——``t``+``dur`` 比 ``t0``+``t1``
    更贴近界面上「从几秒起减速多少秒」的说法。

    认不出的形状原样返回，由 JSON 自己决定怎么序列化，不要在这里丢数据。
    """
    if isinstance(item, dict):
        return dict(item)
    if isinstance(item, (list, tuple)) and len(item) >= 4:
        key = str(item[0] or "")
        t0 = _as_float(item[1], 0.0)
        t1 = _as_float(item[2], t0)
        return {
            "key": key,
            "t": t0,
            "dur": max(0.0, t1 - t0),
            "mult": max(0.0, min(1.0, _as_float(item[3], 1.0))),
        }
    return {"raw": item}


def _deployment_from_dict(item: dict) -> Optional[Deployment]:
    """单条部署的反序列化。位置非法就丢掉这一条，不污染整体。"""
    row = _as_int(item.get("row"), -1)
    col = _as_int(item.get("col"), -1)
    if row < 0 or col < 0:
        return None
    ground = str(item.get("ground") or "LOW").upper()
    if ground not in ("HIGH", "LOW"):
        ground = "LOW"
    dep = Deployment(
        uid=_as_int(item.get("uid"), 0),
        row=row, col=col,
        op_id=str(item.get("op_id") or ""),
        name=str(item.get("name") or ""),
        ground=ground,
        facing=str(item.get("facing") or "RIGHT"),
        deploy_time=max(0.0, _as_float(item.get("t"), 0.0)),
        skill_name=str(item.get("skill") or ""),
        cost=_as_int(item.get("cost"), 0),
        can_block_fly=bool(item.get("block_fly")),
        sp_boost=max(0.0, _as_float(item.get("sp_boost"), 0.0)),
        # 老版本导出的 JSON 没有 ranged / block 两个键，这时退回按
        # ground 判断（HIGH 就是远程位），比一律当近战安全得多。
        is_ranged=bool(item.get("ranged")) if "ranged" in item
        else (ground == "HIGH"),
        block_count=max(0, _as_int(item.get("block"), 0)),
    )
    rt = item.get("retreat")
    if rt is not None:
        val = _as_float(rt, -1.0)
        if val >= dep.deploy_time:
            dep.retreat_time = val
    uses = item.get("skill_uses")
    if isinstance(uses, list):
        dep.skill_uses = sorted(max(0.0, _as_float(t, 0.0)) for t in uses)
    # 技能回转参数。没有 skill_sp 的多半是本次修复（v1 早期）导出的老文件，
    # 或者该干员本来就没配技能——两种情况都保持 sp_cost=0 的「视为被动」，
    # 只是绝不能因为读不到就把名字也丢了。
    sp = item.get("skill_sp")
    if isinstance(sp, dict):
        try:
            dep.skill = SkillCycle(
                sp_cost=max(0.0, _as_float(sp.get("cost"), 0.0)),
                init_sp=max(0.0, _as_float(sp.get("init"), 0.0)),
                duration=max(0.0, _as_float(sp.get("dur"), 0.0)),
                recover=str(sp.get("recover") or "AUTO"),
                infer_attack=bool(sp.get("infer_attack")),
                # B3 §6.4-6.5: 新字段（老文件没有就取默认值）
                max_charge=max(1, _as_int(sp.get("max_charge"), 1)),
                duration_type=str(sp.get("duration_type") or "NONE"),
                ammo=max(0, _as_int(sp.get("ammo"), 0)),
                # 老文件没有 trigger：保持 MANUAL（默认值），这样手动
                # 技能不会被误画成自动循环，最坏情况只是少画推演段。
                trigger=str(sp.get("trigger") or TRIG_MANUAL),
            )
        except Exception:                                  # noqa: BLE001
            pass
    return dep


# ---------------------------------------------------------------- 部署校验


def ground_of_tile(tile) -> str:
    """地块属于高台还是地面。

    游戏里 ``height_type`` 只有 ``HIGHLAND`` / ``LOWLAND`` 两种，
    高台只能放远程位，地面只能放近战位。箱子两类都能放。
    """
    if tile is None:
        return ""
    return "HIGH" if str(getattr(tile, "height_type", "")).upper() == "HIGHLAND" \
        else "LOW"


def can_deploy(tile, is_ranged: bool, want: Optional[str] = None) -> Tuple[bool, str]:
    """判断这格能不能放。

    返回 ``(可以, 原因)``。原因在不能放时是给用户看的短句，
    能放时为空串。
    """
    if tile is None:
        return (False, "这里没有地块")
    kind = want or ("HIGH" if is_ranged else "LOW")
    ht = ground_of_tile(tile)
    if kind == "HIGH":
        if not getattr(tile, "buildable_ranged", False):
            return (False, "这里不是可部署的高台")
        if ht != "HIGH":
            return (False, "地面格放不了远程位干员")
        return (True, "")
    if not getattr(tile, "buildable_melee", False):
        return (False, "这里不是可部署的地面")
    if ht != "LOW":
        return (False, "高台放不了近战位干员")
    return (True, "")


# ---------------------------------------------------------------- 技力光环
#
# 用户明确要求「部分干员能给彼此交互 增加 sp 回复速度」。游戏里这类效果
# 全是**天赋**（白面鸮「技力光环」、陈「呵斥」、维娜·维多利亚 S3 被动、
# 华法琳「血液样本回收」……），文本格式只有三种主流写法，用正则能覆盖
# 到 89 条里的绝大多数。数据包里没有结构化字段，所以这里做文本解析，
# 并把「解析不出来」显式地当成 0——不猜数值。

#: 「技力自然回复速度0.3」「回复速度+0.2/秒」——直接就是点/秒
_RE_SP_RATE = re.compile(
    r"技力(?:自然)?回复速度\s*(?:提升|\+)?\s*([0-9]+(?:\.[0-9]+)?)")
#: 「每3秒回复全场友方角色1点」——换算成 1/3 点每秒。
#: 注意「1 点」和「技力」之间经常还夹着类型词（例如
#: 「1点攻击/受击技力」），所以尾巴要允许若干非数字字符。
_RE_SP_EVERY = re.compile(
    r"每\s*([0-9]+(?:\.[0-9]+)?)\s*秒[^。；]{0,24}?回复[^0-9。；]{0,14}"
    r"([0-9]+(?:\.[0-9]+)?)\s*点[^0-9。；]{0,12}技力")


def sp_boost_of_text(text: str) -> float:
    """从天赋/技能描述里抠出「每秒额外回复多少技力」。

    返回值是**点/秒**，与 ``SkillSim.sp_rate`` 的基准 1.0 同量纲
    （即「+0.30」就是每秒 1.30 点）。解析不出来返回 0.0。

    只认两种写法，其余一律不猜：

    * 「技力自然回复速度 0.3」/「回复速度+0.2/秒」-> 0.3 / 0.2
    * 「每 3 秒回复全场友方角色 1 点」-> 1/3
    """
    s = str(text or "")
    if not s or "技力" not in s:
        return 0.0
    m = _RE_SP_EVERY.search(s)
    if m:
        try:
            period = float(m.group(1))
            amount = float(m.group(2))
        except (TypeError, ValueError):
            period = amount = 0.0
        if period > 0 and amount > 0:
            # 「全场友方」才给得出去；「自身额外回复」这类不传播，
            # 但调用方已经按「谁给谁」分好了，这里只负责算速率。
            return amount / period
    m = _RE_SP_RATE.search(s)
    if m:
        try:
            v = float(m.group(1))
        except (TypeError, ValueError):
            return 0.0
        # 文本写的是「速度0.3」，理解为**额外** 0.3 点/秒
        return max(0.0, min(2.0, v))
    return 0.0
