"""加拐（队友增益）建模。

设计依据
--------
明日方舟的增益按**乘区**结算，同一乘区内加算、不同乘区之间乘算。
把「拐」按乘区归类，才能同时满足两种用法：

* 想知道「华法琳 + 能天使」打多少 —— 选预设模板，一次性填好各乘区；
* 想手调某个数值 —— 只改对应乘区的百分比，其余不动。

乘区划分（依据 PRTS「游戏数据基础 · 伤害」）：

===============  ==========================================  ==========
乘区             说明                                        作用位置
===============  ==========================================  ==========
攻击力加成       华法琳「血液样本回收」+90% 等               A
最终攻击力倍率   技能「攻击力提高至 380%」                    A
攻速             琴柳 / 极境等，%(100+S)                     间隔 T
脆弱（易伤）     灵知 / 塞雷娅，目标受到伤害 +X%             最终伤害
减防             巫恋 / 刻俄柏，目标防御 -X%                  D
减抗             初雪 / 伊芙利特，目标法抗 -X                D
固定穿透         银灰 / 能天使，忽略固定防御                   D
百分比穿透       黑键等                                       D
最终倍率         幽灵鲨「脆弱化」外的一切末端乘区              最终伤害
===============  ==========================================  ==========

所有预设的数值都标注了出处（干员 + 技能），来源是 PRTS 与
官方 ``skill_table`` / ``character_table``。数值可在界面里再调。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

# ---------------------------------------------------------------- 乘区定义

#: 乘区键 -> (显示名, 单位, 说明)
ZONES: List[tuple] = [
    ("atk_pct", "攻击力加成", "%",
     "同乘区相加。华法琳 +90%、白面鸮 +32% 等属于此区"),
    ("atk_final", "攻击力最终倍率", "×",
     "技能「攻击力提高至 N%」。与攻击力加成相乘"),
    ("atk_flat", "附加攻击力", "",
     "鼓舞类（潮涌，潮枯等）直接加到攻击力上"),
    ("aspd", "攻速", "",
     "100 为基准。实际间隔 T = T0 ÷ (clamp(S,10,600) ÷ 100)"),
    ("fragile", "脆弱（易伤）", "%",
     "目标受到伤害 +X%。灵知、塞雷娅、幽灵鲨等"),
    ("def_down", "减防", "%",
     "目标防御 -X%。巫恋、刻俄柏等"),
    ("def_flat", "固定穿透", "",
     "忽略目标固定防御。银灰、能天使等"),
    ("res_down", "减抗", "",
     "目标法抗 -X（点）。初雪、伊芙利特等"),
    ("res_pen", "百分比穿透", "%",
     "忽略目标 X% 防御/法抗"),
    ("final", "最终倍率", "×",
     "末端乘区。一般留 1.0，特殊机制才用"),
]

#: 会参与「攻击力」计算的乘区
ATK_ZONES = ("atk_pct", "atk_final", "atk_flat")
#: 会参与「目标抗性」计算的乘区
RESIST_ZONES = ("def_down", "def_flat", "res_down", "res_pen")


@dataclass
class BuffZone:
    """一个乘区的当前取值。"""

    key: str
    value: float = 0.0
    enabled: bool = False

    @property
    def label(self) -> str:
        for k, name, unit, _desc in ZONES:
            if k == self.key:
                return name
        return self.key


@dataclass
class BuffSet:
    """整套加拐配置。"""

    zones: Dict[str, float] = field(default_factory=dict)
    enabled: Dict[str, bool] = field(default_factory=dict)

    def get(self, key: str, default: float = 0.0) -> float:
        if not self.enabled.get(key, False):
            return default
        return self.zones.get(key, default)

    def set(self, key: str, value: float, enabled: bool = True) -> None:
        self.zones[key] = float(value)
        self.enabled[key] = bool(enabled)

    def clear(self) -> None:
        self.zones.clear()
        self.enabled.clear()

    def active(self) -> List[str]:
        out = []
        for k, name, unit, _d in ZONES:
            if self.enabled.get(k):
                v = self.zones.get(k, 0.0)
                if unit == "%":
                    out.append("%s %+.0f%%" % (name, v))
                elif unit == "×":
                    out.append("%s ×%.2f" % (name, v))
                else:
                    out.append("%s %+.0f" % (name, v))
        return out

    # -------------------------------------------------- 折算到伤害公式

    def atk_multiplier(self) -> float:
        """攻击力总倍率：攻击力加成与最终倍率相乘。"""
        pct = self.get("atk_pct", 0.0) / 100.0
        fin = self.get("atk_final", 1.0)
        if fin <= 0:
            fin = 1.0
        return (1.0 + pct) * fin

    def flat_atk(self) -> float:
        return self.get("atk_flat", 0.0)

    def fragile(self) -> float:
        """脆弱折算成 damage_boost（0.3 表示 +30%）。"""
        return self.get("fragile", 0.0) / 100.0

    def def_percent(self) -> float:
        """减防折算成「防御力乘数」，1.0 表示不减。"""
        return max(0.0, 1.0 - self.get("def_down", 0.0) / 100.0)

    def res_flat(self) -> float:
        """固定减值：物理的固定穿透 + 法术的减抗，合并成同一个字段。

        为什么可以合并
        --------------
        ``DamageInput`` 只有一个 ``def_pen_flat``，而它参与运算的方式
        对两种伤害类型完全一致（都是从「目标抗性」里减掉）：
          物理：max(0, DEF - Iv)
          法术：max(0, RES - Iv) 再按 100 折算
        所以物理的「固定穿透」和法术的「减抗」放在同一格里不会互相
        干扰——面板上一次只用得着其中一种。

        为什么减防必须单独算
        --------------------
        ``def_down``（减防 %）在 :func:`adjust_defense` 里乘到防御力上，
        只作用于物理。以前这里把 ``def_down`` 也折算进固定减值，等于
        给法术伤害也塞了一份减防，命中法术干员时会把法抗压掉一大截
        ——这是实打实的算错。现在只取真正的固定穿透与减抗。
        """
        return self.get("def_flat", 0.0) + self.get("res_down", 0.0)

    def res_percent(self) -> float:
        """百分比穿透，0~1。"""
        v = self.get("res_pen", 0.0) / 100.0
        return min(0.99, max(0.0, v))

    def final_scaler(self) -> float:
        v = self.get("final", 1.0)
        return v if v > 0 else 1.0

    def summary(self) -> str:
        parts = self.active()
        return "　".join(parts) if parts else "无加拐"


# ---------------------------------------------------------------- 预设模板

@dataclass
class BuffPreset:
    """一条预设拐模板。

    ``zones`` 里的数值都是「只启用这些乘区」的取值，套用时先清空再写入，
    避免上一个模板的残留值影响结果。
    """

    key: str
    name: str
    note: str
    zones: Dict[str, float] = field(default_factory=dict)
    source: str = ""

    def apply(self, buf: BuffSet) -> None:
        buf.clear()
        for k, v in self.zones.items():
            buf.set(k, v, True)


#: 预设拐模板。数值取自 PRTS 干员页的专精三数据，标注了出处。
PRESETS: List[BuffPreset] = [
    BuffPreset(
        key="none", name="不加拐（裸输出）",
        note="只算干员自身面板与技能，不带任何队友增益",
        zones={}, source=""),

    BuffPreset(
        key="warfarin", name="华法琳 · 血液样本回收",
        note="攻击力 +90%（同乘区加算）",
        zones={"atk_pct": 90.0}, source="华法琳 S2 专三"),

    BuffPreset(
        key="warfarinnightingale", name="华法琳 + 夜莺",
        note="攻击力 +90%、攻速 +7",
        zones={"atk_pct": 90.0, "aspd": 107.0}, source="华法琳 S2 / 夜莺天赋"),

    BuffPreset(
        key="pramanix", name="初雪 · 自然震慑",
        note="目标法抗 -35（点），脆弱 +10%",
        zones={"res_down": 35.0, "fragile": 10.0}, source="初雪 S2 专三"),

    BuffPreset(
        key="saria", name="塞雷娅 · 钙质化",
        note="目标受到法术伤害 +55%（脆弱）",
        zones={"fragile": 55.0}, source="塞雷娅 S2 专三"),

    BuffPreset(
        key="lingzhi", name="灵知 · 冰封领域",
        note="脆弱 +30%，攻速 +15",
        zones={"fragile": 30.0, "aspd": 115.0}, source="灵知 S2/S3"),

    BuffPreset(
        key="wuyan", name="巫恋 · 荆棘环",
        note="目标防御 -50%",
        zones={"def_down": 50.0}, source="巫恋 S2 专三"),

    BuffPreset(
        key="ifrit", name="伊芙利特 · 灼地",
        note="目标法抗 -20（点），攻击力 +20%",
        zones={"res_down": 20.0, "atk_pct": 20.0}, source="伊芙利特 S2 专三"),

    BuffPreset(
        key="silverash", name="银灰 · 真银斩",
        note="固定穿透 200，攻击力 +200%",
        zones={"def_flat": 200.0, "atk_pct": 200.0}, source="银灰 S2 专三"),

    BuffPreset(
        key="full", name="满拐（极限测试）",
        note="攻击力 +150%、攻速 +40、脆弱 +55%、减防 50%、减抗 40、穿透 20%",
        zones={"atk_pct": 150.0, "aspd": 140.0, "fragile": 55.0,
               "def_down": 50.0, "res_down": 40.0, "res_pen": 20.0},
        source="综合上限，用于压测"),
]


def preset_by_key(key: str) -> Optional[BuffPreset]:
    for p in PRESETS:
        if p.key == key:
            return p
    return None


def apply_preset(key: str) -> BuffSet:
    buf = BuffSet()
    p = preset_by_key(key)
    if p:
        p.apply(buf)
    return buf


def make_input_kwargs(buf: BuffSet) -> dict:
    """把加拐折算成 ``DamageInput`` 的字段。

    返回的字典可以直接 ``DamageInput(**kw)`` 用，
    与手填穿透等字段合并时以本函数的值为准。
    """
    return {
        "attack_multiplier": buf.atk_multiplier(),
        "flat_attack_bonus": buf.flat_atk(),
        "damage_boost": buf.fragile(),
        "def_pen_flat": buf.res_flat(),
        "def_pen_percent": buf.res_percent(),
        "final_scaler": buf.final_scaler(),
        "def_down_percent": buf.get("def_down", 0.0) / 100.0,
    }


def adjust_defense(defense: float, buf: BuffSet) -> float:
    """按减防比例修正目标防御。

    注意：``compute_damage`` 现在自带 ``def_down_percent``，正常路径不用
    这个函数。它保留给「需要先算出标量防御」的场合。曲线请不要用
    ——会把减防折算进横轴，逐点扫描时又被覆盖掉。
    """
    return max(0.0, float(defense or 0.0)) * buf.def_percent()