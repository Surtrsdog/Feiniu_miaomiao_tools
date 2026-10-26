# -*- coding: utf-8 -*-
"""干员伤害类型判定。

为什么需要这张表
----------------
官方 ``character_table.json`` **没有**攻击伤害类型字段
（``attackType`` 恒为 None），PRTS 干员页也只有「职业 / 分支」。
历史上 ``operators.json`` 里 463 位干员的 ``attack_type`` 全是
``PHYSICAL``，导致史尔特尔（术战者）、艾雅法拉（中坚术师）、望
（特种·术战体系棋子）这类**打不出物理伤害**的角色，在结果栏里
被算成物理伤害，数值全错。

真正的判定依据是**分支（子职业）**：游戏里每个分支固定一种攻击
伤害类型。本表按 PRTS 中文分支名归纳，源码侧的英文 id 也一并映射，
两种写法都认。
"""
from __future__ import annotations

import re
from typing import Optional, Tuple

from . import constants as C

#: 中文分支名 -> 伤害类型
_SUB_CN = {
    # ---------------- 法术（术师系）
    "中坚术师": C.DMG_MAGICAL, "扩散术师": C.DMG_MAGICAL,
    "轰击术师": C.DMG_MAGICAL, "链术师": C.DMG_MAGICAL,
    "驭械术师": C.DMG_MAGICAL, "秘术师": C.DMG_MAGICAL,
    "阵法术师": C.DMG_MAGICAL, "本源术师": C.DMG_MAGICAL,
    "塑灵术师": C.DMG_MAGICAL,
    # ---------------- 法术（近卫 / 重装 / 辅助 / 医疗）
    "术战者": C.DMG_MAGICAL,      # 史尔特尔：普攻即法术
    "驭法铁卫": C.DMG_MAGICAL,     # 石棉 / 森蚺
    "巫役": C.DMG_MAGICAL,        # 灵知 / 巫恋（技能的减法抗按法术算）
    "咒愈师": C.DMG_MAGICAL,       # 夜魔 / 火神
    "削弱者": C.DMG_MAGICAL,       # 初雪
    "工匠": C.DMG_MAGICAL,        # 罗宾 / 温蒂以外的装置多为法术
    "炼金师": C.DMG_MAGICAL,
    "怪杰": C.DMG_MAGICAL,        # 老玛（法术）
    "吟游者": C.DMG_MAGICAL,
    "护佑者": C.DMG_MAGICAL,
    # ---------------- 元素
    "本源铁卫": C.DMG_ELEMENTAL,
    "本源近卫": C.DMG_ELEMENTAL,
    "裂空炮手": C.DMG_ELEMENTAL,
    "守望者": C.DMG_ELEMENTAL,
    # ---------------- 治疗（不产生伤害）
    "医师": C.DMG_HEAL, "疗养师": C.DMG_HEAL, "群愈师": C.DMG_HEAL,
    "链愈师": C.DMG_HEAL, "行医": C.DMG_HEAL,
    # ---------------- 物理（显式列出，便于阅读；默认也是物理）
    "领主": C.DMG_PHYSICAL, "无畏者": C.DMG_PHYSICAL,
    "斗士": C.DMG_PHYSICAL, "剑豪": C.DMG_PHYSICAL,
    "强攻手": C.DMG_PHYSICAL, "处决者": C.DMG_PHYSICAL,
    "铁卫": C.DMG_PHYSICAL, "守护者": C.DMG_PHYSICAL,
    "决战者": C.DMG_PHYSICAL, "不屈者": C.DMG_PHYSICAL,
    "重剑手": C.DMG_PHYSICAL, "武者": C.DMG_PHYSICAL,
    "收割者": C.DMG_PHYSICAL, "解放者": C.DMG_PHYSICAL,
    "重射手": C.DMG_PHYSICAL, "炮手": C.DMG_PHYSICAL,
    "神射手": C.DMG_PHYSICAL, "攻城手": C.DMG_PHYSICAL,
    "散射手": C.DMG_PHYSICAL, "投掷手": C.DMG_PHYSICAL,
    "回环射手": C.DMG_PHYSICAL, "猎手": C.DMG_PHYSICAL,
    "钩索师": C.DMG_PHYSICAL, "推击手": C.DMG_PHYSICAL,
    "撼地者": C.DMG_PHYSICAL, "伏击客": C.DMG_PHYSICAL,
    "哨戒铁卫": C.DMG_PHYSICAL, "战术家": C.DMG_PHYSICAL,
    "情报官": C.DMG_PHYSICAL, "行商": C.DMG_PHYSICAL,
    "佣兵": C.DMG_PHYSICAL, "策士": C.DMG_PHYSICAL,
    "游击手": C.DMG_PHYSICAL, "巡空者": C.DMG_PHYSICAL,
    "教官": C.DMG_PHYSICAL, "执旗手": C.DMG_PHYSICAL,
    "陷阱师": C.DMG_PHYSICAL, "召唤师": C.DMG_PHYSICAL,
    "傀儡师": C.DMG_PHYSICAL, "怪盗": C.DMG_PHYSICAL,
    "链术士": C.DMG_MAGICAL,
    # ---------------- 补录（此前靠职业兜底，兜错了）
    # 这五个分支在旧表里没有条目，落到「职业兜底」分支：狙击/先锋/辅助
    # 都被当成物理。速射手、尖兵、冲锋手、要塞确实是物理，但**凝滞师
    # 是法术**（安洁莉娜、初雪、地灵），21 位干员里有 12 位被算成物理，
    # 「安洁莉娜 三技能」这类 DPS 直接偏离一个数量级。
    "速射手": C.DMG_PHYSICAL,
    "尖兵": C.DMG_PHYSICAL,
    "冲锋手": C.DMG_PHYSICAL,
    "要塞": C.DMG_PHYSICAL,
    "凝滞师": C.DMG_MAGICAL,
}

#: 英文子职业 id -> 伤害类型（官方表用）
_SUB_EN = {
    "corecaster": C.DMG_MAGICAL, "splashcaster": C.DMG_MAGICAL,
    "blastcaster": C.DMG_MAGICAL, "chain": C.DMG_MAGICAL,
    "funnel": C.DMG_MAGICAL, "mystic": C.DMG_MAGICAL,
    "phalanx": C.DMG_MAGICAL, "primcaster": C.DMG_MAGICAL,
    "soulcaster": C.DMG_MAGICAL,
    "artsfghter": C.DMG_MAGICAL, "artsprotector": C.DMG_MAGICAL,
    "ritualist": C.DMG_MAGICAL, "incantationmedic": C.DMG_MAGICAL,
    "underminer": C.DMG_MAGICAL, "craftsman": C.DMG_MAGICAL,
    "alchemist": C.DMG_MAGICAL, "geek": C.DMG_MAGICAL,
    "bard": C.DMG_MAGICAL, "blessing": C.DMG_MAGICAL,
    "primprotector": C.DMG_ELEMENTAL, "primguard": C.DMG_ELEMENTAL,
    "skybreaker": C.DMG_ELEMENTAL, "watchman": C.DMG_ELEMENTAL,
    "physician": C.DMG_HEAL, "healer": C.DMG_HEAL,
    "ringhealer": C.DMG_HEAL, "chainhealer": C.DMG_HEAL,
    "wandermedic": C.DMG_HEAL,
}

#: 整个职业就是法术（分支缺失时的兜底）
_PROF_CN_MAGIC = {"术师"}
_PROF_EN_MAGIC = {"CASTER"}


def guess_damage_type(profession: str = "", sub_profession: str = "",
                      default: str = C.DMG_PHYSICAL) -> str:
    """按分支 / 职业推断伤害类型；判不出时返回 ``default``。"""
    sub = (sub_profession or "").strip()
    if sub:
        if sub in _SUB_CN:
            return _SUB_CN[sub]
        if sub in _SUB_EN:
            return _SUB_EN[sub]
        # 中文名里含这些字的，基本是法术体系
        for kw in ("术师", "术战", "术铁卫", "巫", "咒愈"):
            if kw in sub:
                return C.DMG_MAGICAL
    prof = (profession or "").strip()
    if prof in _PROF_CN_MAGIC or prof.upper() in _PROF_EN_MAGIC:
        return C.DMG_MAGICAL
    return default


def describe(dtype: str) -> Tuple[str, str]:
    """伤害类型 -> (短名, 全名)。"""
    short = {C.DMG_PHYSICAL: "物理", C.DMG_MAGICAL: "法术",
             C.DMG_ELEMENTAL: "元素", C.DMG_TRUE: "真实",
             C.DMG_HEAL: "治疗"}
    return short.get(dtype, "物理"), C.DMG_TYPE_LABELS.get(dtype, dtype)

#: 技能描述里出现这些词，就说明该技能打的是这种伤害。
#: 有些干员普攻是物理（陷阱师、狙击），但技能明确写了「造成法术伤害」，
#: 典型就是望的「天下劫」（atk_scale 380% 的法术伤害）——此时以技能为准。
_SKILL_HINTS = (
    ("法术伤害", C.DMG_MAGICAL),
    ("法术", C.DMG_MAGICAL),
    ("元素伤害", C.DMG_ELEMENTAL),
    ("真实伤害", C.DMG_TRUE),
    ("治疗", C.DMG_HEAL),
)

#: 描述了「法术」但**不是**在打法伤的分句模式。
#: 银灰真银斩写「获得一定比例的法术闪避」、星熊写「法术抗性提升」、
#: 赫默写「获得法术护盾」——这些都是在讲防御/减伤，跟输出无关。
#: 不排掉的话，银灰（纯物理）会被判成法术干员。
_NOT_DAMAGE_CLAUSE = re.compile(
    r"法术(?:闪避|抗性|护盾|屏障|吸收|抵抗|免疫|伤害减免|反伤|反射)|"
    r"(?:提升|提高|增加|受到|降低|减少|无视|无视掉)[^，。；\n]{0,12}法术(?:抗性|闪避|护盾)")

#: 只有这些写法才说明「本干员自己打法伤」。用来压掉两类误判：
#:   塞雷娅 钙质化「附近所有敌军受到的法术伤害+20%」——她在增伤，不输出；
#:   深律「停止攻击并专心对周围友方角色进行治疗」——他根本不攻击了。
#: 注意描述里的模板是 ``{{color|#F49800|法术}}``，关键字会被拆到
#: 花括号中间，所以匹配前先把模板语法清掉再看。
_DEALS_MAGIC = re.compile(
    r"伤害类型变为\s*(?:法术|魔法)|"
    r"造成[^。；\n]{0,30}?法术伤害|"
    r"攻击[^。；\n]{0,16}?法术伤害|"
    r"普通攻击[^。；\n]{0,16}?法术|"
    r"相当于攻击力[^。；\n]{0,30}?法术|"
    r"每秒[^。；\n]{0,20}?法术伤害")

#: 「伤害类型变为 真实」这种改写：模板展开后关键字之间会多出空格，
#: 字面量 ``"真实伤害"`` 反而搜不到。这里直接抓「变为 X」的 X。
_CHANGED_TO = re.compile(
    r"(?:伤害类型)?变为\s*(真实|法术|魔法|元素|物理)|"
    r"(?:普通)?攻击的?伤害类型\s*(?:变为|改为)\s*(真实|法术|魔法|元素|物理)")

#: 「停止攻击 / 专心治疗」这类描述说明该技能不产生普攻伤害。
_STOPS_ATTACKING = re.compile(r"停止攻击|专心对|不再攻击|不进行攻击")

#: 提到「治疗」但**不是**在说本干员给别人治疗的分句：
#:   舍身突击「不再成为其他角色的治疗目标」——这是**防御性**描述，
#:   技能本身是纯物理加攻。不排掉会被判成 HEAL。
#:   以暴制暴「立即对自身进行一次相当于攻击力 X 的治疗，之后攻击间隔
#:   缩短」／精准痛击「每次攻击治疗自身相当于造成伤害 X 的生命值」
#:   ——都是**自我回血**，本人仍是输出，不能整体判成治疗干员。
#: 间隔给到 {0,40}：中间常夹着 ``{heal_scale:0%}`` 这种占位符，
#: 卡太紧会漏匹配。「自身」可能出现在「治疗」两侧，两种语序都要覆盖。
_NOT_HEAL_CLAUSE = re.compile(
    r"(?:不再)?成为[^。；\n]{0,24}?治疗目标|"
    r"治疗(?:效果|量|效率)[^。；\n]{0,8}?(?:降低|减少|下降|无效)|"
    r"无法(?:被)?治疗|不受治疗|"
    r"(?:对)?(?:自身|自己|本人)[^。；\n]{0,40}?治疗|"
    r"治疗(?:自身|自己|本人)")

#: 匹配**最内层**的 ``{{...}}`` 模板（body 里不能再有花括号）。
#: 配合循环展开，就能处理 ``{{*|60%|{{color|#0098DC|+60%}}}}`` 这种嵌套。
_TPL = re.compile(r"\{\{([^{}]*)\}\}")


def _plain(desc: str) -> str:
    """剥掉 PRTS 模板语法，只留可读文字。

    描述写成 ``{{color|#F49800|法术}}``，直接搜「法术伤害」永远搜不到
    （关键字被包在模板里），必须先把模板展开。

    注意**不能整个丢掉模板**：``{{color|#F49800|法术}}`` 的实际显示文本
    就是最后一段「法术」，把它删掉只会让描述变成「造成相当于攻击力 的
    伤害」，反而丢了唯一的类型线索。所以这里取模板的**显示段**：
    ``{{a|b|c}}`` -> ``c``，嵌套时递归处理。

    与 ``handbook.strip_tags`` 的分工：那个只处理 ``<$ba.stun>`` 这类
    尖括号标签，管不到 ``{{}}`` 模板，两者互不替代。
    """
    if not desc:
        return ""
    t = str(desc)
    # 反复展开模板，直到没有 {{...}}（处理嵌套）
    for _ in range(6):
        m = _TPL.search(t)
        if not m:
            break
        body = m.group(1)
        # {{a|b|c}} 的显示文本是最后一段
        shown = body.rsplit("|", 1)[-1] if "|" in body else body
        t = t[:m.start()] + " " + shown + " " + t[m.end():]
    t = re.sub(r"<[^<>]{0,24}>", " ", t)     # 富文本标签
    t = t.replace("{{", " ").replace("}}", " ")
    t = re.sub(r"\s+", " ", t)
    return t


#: 只是「别人受到的伤害变化」，不说明本干员在打法伤。
#: 塞雷娅 钙质化：「附近所有敌军受到的法术伤害 +20%」——
#: 她是**增伤拐**，那一句讲的是目标挨打时多掉血，不是她自己打法伤。
_BUFFS_OTHERS = re.compile(
    r"(?:敌军|敌人|敌方)[^。；\n]{0,16}?受到的?法术伤害|"
    r"使[^。；\n]{0,16}?受到的?法术伤害|"
    r"受到的法术伤害\s*[+＋]|"
    r"法术伤害(?:提升|增加|降低|减少|减免)")


def from_skill_text(desc: str, default: str = "") -> str:
    """从技能描述里抠出伤害类型。

    优先级：明确写「XX伤害」的 > 笼统的「法术」> 无信息时返回 default。
    这样望的三技能会被判成法术，而他的普攻仍然是物理。

    匹配前先剔掉「法术闪避 / 法术抗性 / 法术护盾」这类**防御性**表述，
    否则银灰、星熊这些纯物理干员会因为技能里带一句「法术闪避」而被
    整个判成法术输出（面板会切到法术类型，DPS 算出来差一个数量级）。

    再往下还有一层门槛：光提到「法术」不够，必须能看出**这个干员自己
    在打法伤**。塞雷娅「附近所有敌军受到的法术伤害 +20%」只是在增伤，
    深律「停止攻击并专心治疗」根本不攻击——这两位都不该被判成法术干员。
    """
    text = desc or ""
    if not text:
        return default
    plain = _plain(text)
    # 先把「给别人增伤 / 抗性」的分句整段去掉，
    # 否则「法术伤害」这个字面量会被塞雷娅的增伤句直接命中。
    plain = _BUFFS_OTHERS.sub(" ", plain)
    # 「伤害类型变为 真实」这类改写单独抓：
    # 模板展开后关键字被空格隔开，下面的字面量匹配会漏掉。
    m = _CHANGED_TO.search(plain)
    if m:
        tok = m.group(1) or m.group(2)
        mapped = {"真实": C.DMG_TRUE, "元素": C.DMG_ELEMENTAL,
                  "法术": C.DMG_MAGICAL, "魔法": C.DMG_MAGICAL,
                  "物理": C.DMG_PHYSICAL}.get(tok)
        if mapped:
            return mapped
    # 再找「XX伤害」这种明确表述（用剥过模板的文本）
    for kw in ("真实伤害", "元素伤害", "法术伤害", "物理伤害"):
        if kw in plain:
            return {
                "真实伤害": C.DMG_TRUE,
                "元素伤害": C.DMG_ELEMENTAL,
                "法术伤害": C.DMG_MAGICAL,
                "物理伤害": C.DMG_PHYSICAL,
            }[kw]
    # 再退一步：只提了「法术」，但必须不是防御性表述
    stripped = _NOT_DAMAGE_CLAUSE.sub("", plain)
    if "法术" in stripped:
        # 该技能主动放弃了普攻（深律），或只是给别人增伤（塞雷娅），
        # 都不改自己的伤害类型
        if _STOPS_ATTACKING.search(plain):
            return default
        if not _DEALS_MAGIC.search(stripped):
            return default
        return C.DMG_MAGICAL
    if "治疗" in stripped:
        # 「不再成为其他角色的治疗目标」是在讲防御，不是在讲治疗别人
        if _NOT_HEAL_CLAUSE.search(stripped):
            return default
        return C.DMG_HEAL
    return default


def resolve(profession: str = "", sub_profession: str = "",
            skill_desc: str = "") -> str:
    """综合分支与技能描述给出最终伤害类型。

    规则：**治疗职业永远算治疗**，其余情况技能描述优先——技能写明了
    法术就是法术；没写明才用分支。

    为什么治疗要短路
    ----------------
    医疗干员的技能描述里经常出现「法术」二字，但那是在讲**抗性/护盾**，
    不是在讲输出：
      闪灵 三技能「教条力场：使攻击范围内的友方单位防御力提升，
            并获得一定比例的法术闪避」
      夜莺 三技能「圣域：…… 攻击范围内的友方单位法术抗性提升」
    按「描述里提到法术就是法伤」去判，闪灵、夜莺会被算成法术输出干员，
    面板自动切到「法术伤害」并给出一个 DPS —— 而她们根本不造成伤害。
    所以医疗分支直接返回 HEAL，让上层保留「治疗」语义（不产生 DPS）。
    """
    base = guess_damage_type(profession, sub_profession)
    if base == C.DMG_HEAL:
        return C.DMG_HEAL
    from_text = from_skill_text(skill_desc, "")
    if from_text and from_text != C.DMG_HEAL:
        return from_text
    return base
