# -*- mode: python ; coding: utf-8 -*-
"""从 PRTS 技能模板解析可计算的数值。

PRTS 的技能描述把数值藏在模板里，例如：

    攻击力{{*|120%|{{color|#0098DC|+120%}}}}      -> 攻击力 +120%
    攻击力提高至{{color|#0098DC|225%}}            -> 攻击力 x2.25
    攻击速度{{+|60|{{color|#0098DC|+60}}}}        -> 攻速 +60
    攻击间隔{{+|(-0.22)|...}}                     -> 间隔 -0.22s
    {{color|#0098DC|5}}连射                        -> 5 连击

解析是「尽力而为」：只提取能可靠量化的项，其余留给用户手动填写。
同时保留原文，便于核对。
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

#: 技能等级标签（7 级 + 3 专精）
LEVEL_LABELS: List[Tuple[str, str]] = [
    ("技能1", "1"), ("技能2", "2"), ("技能3", "3"), ("技能4", "4"),
    ("技能5", "5"), ("技能6", "6"), ("技能7", "7"),
    ("技能专精1", "专一"), ("技能专精2", "专二"), ("技能专精3", "专三"),
]

#: 描述里的颜色模板（用来剥掉标记）
_COLOR_RE = re.compile(r"\{\{color\|[^|]*\|(.*?)\}\}", re.S)


@dataclass
class SkillLevel:
    """技能某一级的可量化数值。"""

    label: str = ""
    description: str = ""
    atk_multiplier: float = 1.0     # 攻击力倍率（"提高至 225%" -> 2.25）
    atk_bonus: float = 0.0          # 攻击力加算百分比（"+120%" -> 0.0 相对于倍率）
    flat_atk: float = 0.0           # 固定攻击力加成
    attack_speed: float = 0.0       # 攻速加成（加到 100 的基础上）
    interval_delta: float = 0.0     # 攻击间隔修正（秒，负数为缩短）
    interval_abs: float = 0.0       # 保留字段（历史上曾用于绝对间隔，现恒为 0）
    dmg_scale: float = 1.0          # 单次伤害缩放（「造成相当于攻击力 x% 的伤害」）
    #: 混伤：技能在普攻之外**额外**造成的法术伤害倍率，**相对技能期间的面板
    #: 攻击力**（含攻击力提升，例如「攻击力+110% 后每次攻击额外造成相当于
    #: 攻击力 100% 的法术伤害」的 magic_scale 就是 1.0，最终法术分量 =
    #: 面板攻击力 x atk_multiplier x magic_scale）。0 表示没有法术分量。
    magic_scale: float = 0.0
    #: 技能期间是否停止普攻（如重岳「强磁防卫」：停止攻击、只放法术范围伤）。
    #: 为真时物理分量为 0，只有 magic_scale 描述的那部分范围法术伤害。
    stops_attack: bool = False
    hit_count: int = 1              # 连射次数
    duration: float = 0.0           # 持续时间
    cost: float = 0.0               # 技力消耗
    initial: float = 0.0            # 初始技力
    extra: List[str] = field(default_factory=list)  # 识别到的其它项


@dataclass
class Skill:
    """一个技能。"""

    index: int = 1
    name: str = ""
    tree_type: str = ""      # 攻击回复 / 自动回复 / 被动 ...
    trigger_type: str = ""   # 自动触发 / 手动触发 ...
    levels: Dict[str, SkillLevel] = field(default_factory=dict)

    def level(self, key: str) -> Optional[SkillLevel]:
        return self.levels.get(key)

    @property
    def level_keys(self) -> List[str]:
        return [k for _, k in LEVEL_LABELS if k in self.levels]

    @property
    def max_level_key(self) -> str:
        ks = self.level_keys
        return ks[-1] if ks else ""


# ------------------------------------------------------------------ 数值提取

def plain(text: str) -> str:
    """剥掉 color/*/+ 等模板，只留可读文字。"""
    s = text
    # 反复剥离，直到不再变化（嵌套模板）
    for _ in range(6):
        t = re.sub(r"\{\{\*\|[^|]*\|(.*?)\}\}", r"\1", s, flags=re.S)
        t = re.sub(r"\{\{\+\|([^|]*)\|(.*?)\}\}", r"\1", t, flags=re.S)
        t = re.sub(r"\{\{color\|[^|]*\|(.*?)\}\}", r"\1", t, flags=re.S)
        if t == s:
            break
        s = t
    s = re.sub(r"<br\s*/?>", " ", s)
    s = re.sub(r"\{\{[^}]*\}\}", "", s)
    # 兜底的括号残片：上面几条正则按 `.*?` 非贪婪匹配，遇到
    # 「攻击范围扩大，攻击间隔{{*|(-1.65)|{{color|..|-1.65}}}}」这类
    # 嵌套写法会先吃掉内层，外层多出来的 `}}` 留在文本里，
    # 于是 1215 条技能描述尾部挂着「}}」。这里把剩下的括号清掉。
    s = s.replace("{{", "").replace("}}", "")
    return s.strip()


# 「攻击力提高至 225%」/「攻击力提升至{{color|..|225%}}」/「造成相当于攻击力121%的伤害」
_RE_ATK_TO = re.compile(
    r"攻击力(?:提升|提高|增加|上升)?至[^0-9%]{0,40}?(\d+(?:\.\d+)?)\s*%")
_RE_ATK_EQUIV = re.compile(
    r"相当于攻击力[^0-9%]{0,30}?(\d+(?:\.\d+)?)\s*%")
_RE_ATK_MUL = re.compile(r"攻击力\{\{\*\|\s*(\d+(?:\.\d+)?)\s*%")
_RE_ATK_FLAT = re.compile(r"攻击力\{\{\+\|\s*\(?(-?\d+(?:\.\d+)?)\)?")
_RE_SPEED = re.compile(r"攻击速度\{\{\+\|\s*\(?(-?\d+(?:\.\d+)?)\)?")
_RE_INTERVAL = re.compile(r"攻击间隔\{\{\+\|\s*\(?(-?\d+(?:\.\d+)?)\)?")
# 「攻击间隔延长(+1.4)」「较大幅度缩短(-1.5)」「(+0.2)」等纯文字写法
_RE_INTERVAL_TXT = re.compile(
    r"攻击间隔[^0-9+\-()。，,；;]{0,12}[（(]\s*([+\-]?\d+(?:\.\d+)?)\s*[)）]")
_RE_HITS = re.compile(r"(\d+)\s*连(?:射|击)")


def apply_official(lv: SkillLevel, entry: dict, lv_index: int) -> SkillLevel:
    """用官方 skill_table 的 blackboard 覆盖/补全一个技能等级。

    官方的键值比自然语言描述精确得多，凡是官方给了数值就以官方为准，
    只有官方没有的项才保留正则解析出来的结果。
    """
    from . import skilldata as SD  # 延迟导入

    off = SD.extract(entry, lv_index)
    if not off:
        return lv
    # 正则解析可能把「同一个倍率」同时写进了 atk_multiplier 和 dmg_scale
    # （烈焰魔剑：正则读到 310% 就两边都填 3.1），再相乘会平方放大 9.6 倍。
    # 覆盖前先把这种重复的记录挑出来清掉。
    if (lv.dmg_scale > 1.001 and abs(lv.dmg_scale - lv.atk_multiplier) < 1e-6):
        lv.dmg_scale = 1.0

    # 官方明确给了倍率才覆盖；默认 1.0 不算「给了」
    if abs(off.get("atk_multiplier", 1.0) - 1.0) > 1e-9:
        lv.atk_multiplier = off["atk_multiplier"]
    if off.get("flat_atk"):
        lv.flat_atk = off["flat_atk"]
    if off.get("attack_speed"):
        lv.attack_speed = off["attack_speed"]
    if off.get("interval_delta"):
        # 官方的 base_attack_time / interval 都是增量（负=缩短）
        lv.interval_delta = off["interval_delta"]
    # 官方给了单次伤害倍率(sc)、却没给任何攻击力加成 -> 说明这个技能
    # 压根没有面板增益。此时正则从描述里抓到的「攻击力+300%」多半是
    # 别的作用域（赤刃明霄陈 赤霄·绝影-驰 的 +300% 是斩击结束后才生效的
    # 增益，斩击本身是 480% x 10 次），必须丢掉，否则伤害虚高 4 倍。
    if (abs(off.get("atk_multiplier", 1.0) - 1.0) < 1e-9
            and off.get("dmg_scale", 1.0) != 1.0):
        lv.atk_multiplier = 1.0

    if off.get("dmg_scale", 1.0) != 1.0:
        # 只有当 dmg_scale 与 atk_multiplier 不是同一个数时才叠加。
        # 否则表示「正则解析和官方表描述的是同一件事」（如烈焰魔剑
        # 正则读到 310%、官方 atk_scale 也是 3.1），再乘一次伤害会平方放大。
        if abs(off["dmg_scale"] - lv.atk_multiplier) > 1e-6:
            lv.dmg_scale = off["dmg_scale"]
        else:
            lv.dmg_scale = 1.0
    # 连击数要两向同步。早先只写了 "> 1 才覆盖"，结果正则从
    # 描述里误读出的 8 连击（望「立即获得 8 枚棋子」）永远洗不掉，
    # 导致 DPS 虚高 8 倍。官方既然给了结论，就以官方为准。
    off_hits = int(off.get("hit_count", 1) or 1)
    seg = off.get("segments") or []
    if len(seg) >= 3:
        pass          # 多段倍率自带段数，不参与连击叠加
    else:
        lv.hit_count = max(1, off_hits)
    if off.get("duration"):
        lv.duration = off["duration"]
    if off.get("cost"):
        lv.cost = off["cost"]
    if off.get("initial"):
        lv.initial = off["initial"]
    # 混伤分量：官方检测到法术分量/停止普攻就覆盖（0 也算「给了结论」，
    # 因为默认就是 0/False，这里不需要「非默认才写」的判断）。
    if "magic_scale" in off:
        lv.magic_scale = off["magic_scale"]
    if "stops_attack" in off:
        lv.stops_attack = off["stops_attack"]
    lv.extra = list(dict.fromkeys(list(lv.extra) + list(off.get("extra") or [])))
    return lv


def parse_level(label: str, desc: str,
                duration: str = "", cost: str = "",
                initial: str = "") -> SkillLevel:
    """从一段技能描述里抽出数值。"""
    lv = SkillLevel(label=label, description=desc)
    lv.duration = _num(duration)
    lv.cost = _num(cost)
    lv.initial = _num(initial)

    if not desc:
        return lv

    # 攻击力：优先「提升至 X%」，其次「{{*|X%|...}}」
    # 注意：必须在「剥掉标记后的纯文本」上匹配百分数——
    # 原始描述里 {{color|#0098DC|225%}} 的 #0098DC 含数字，
    # 用 [^0-9%] 做跳板会在这里失败。
    ptext = plain(desc)
    m = _RE_ATK_TO.search(ptext)
    if m is None:
        m = _RE_ATK_EQUIV.search(ptext)
    if m:
        lv.atk_multiplier = float(m.group(1)) / 100.0
        lv.extra.append("攻击力提升至 %s%%" % m.group(1))
    else:
        m = _RE_ATK_MUL.search(desc)
        if m:
            lv.atk_multiplier = 1.0 + float(m.group(1)) / 100.0
            lv.extra.append("攻击力 +%s%%" % m.group(1))

    m = _RE_ATK_FLAT.search(desc)
    if m:
        lv.flat_atk = float(m.group(1))
        lv.extra.append("攻击力 %+g" % lv.flat_atk)

    m = _RE_SPEED.search(desc)
    if m:
        lv.attack_speed = float(m.group(1))
        lv.extra.append("攻速 %+g" % lv.attack_speed)

    m = _RE_INTERVAL.search(desc)
    if m is None:
        m = _RE_INTERVAL_TXT.search(ptext)
    if m:
        lv.interval_delta = float(m.group(1))
        lv.extra.append("间隔 %+g" % lv.interval_delta)

    m = _RE_HITS.search(ptext)
    if m:
        n = int(m.group(1))
        if 1 < n <= 20:
            lv.hit_count = n
            lv.extra.append("%d 连击" % n)

    return lv


def _num(s: str) -> float:
    if not s:
        return 0.0
    m = re.search(r"-?\d+(?:\.\d+)?", s)
    return float(m.group(0)) if m else 0.0


# ------------------------------------------------------------------ 技能解析

_OFFICIAL: Optional[dict] = None
_OFFICIAL_IDX: Optional[dict] = None


def _official_tables():
    """懒加载官方技能表 + 技能名索引（只读一次）。"""
    global _OFFICIAL, _OFFICIAL_IDX
    if _OFFICIAL is None:
        from . import skilldata as SD
        _OFFICIAL = SD.load(SD.default_path())
        _OFFICIAL_IDX = SD.build_name_index(_OFFICIAL)
    return _OFFICIAL, _OFFICIAL_IDX


_SKILL_TPL_RE = re.compile(r"\{\{\s*技能(?:2|3)?\s*(?=[|\n}])")


def _iter_skill_templates(text: str):
    """按出现顺序产出页面里的每个技能块。

    PRTS 的技能模板名是 ``{{技能}}``、``{{技能2}}``、``{{技能3}}``，
    但**编号并不等于技能槽位**：三技能也常写成 ``{{技能2``（真银斩就是这样），
    所以不能按名字查，必须顺序扫描、按出现次序当作第 1/2/3 技能。
    """
    from .prts_operator import _template_params  # 延迟导入，避免循环

    pos = 0
    idx = 0
    while True:
        m = _SKILL_TPL_RE.search(text, pos)
        if not m:
            break
        block = _find_braced(text, m.start())
        pos = m.end()
        if not block:
            continue
        try:
            p = _template_params(block)
        except Exception:
            continue
        # 只认带「技能名」的真技能块，跳过技能升级材料表之类
        if not (p.get("技能名") or "").strip():
            continue
        idx += 1
        if idx > 3:
            break
        yield idx, block


def _find_braced(text: str, start: int) -> str:
    """从 start 处的 ``{{`` 开始，返回配平的整段模板文本。"""
    if not text.startswith("{{", start):
        return ""
    depth = 0
    i = start
    n = len(text)
    while i < n - 1:
        two = text[i:i + 2]
        if two == "{{":
            depth += 1
            i += 2
            continue
        if two == "}}":
            depth -= 1
            i += 2
            if depth == 0:
                return text[start:i]
            continue
        i += 1
    return ""


def parse_skills(text: str, find_template, char_id: str = "") -> List[Skill]:
    """从整页 wikitext 解析全部技能。

    find_template(text, name) 由 prts_operator 提供，避免循环导入。
    """
    from .prts_operator import _template_params  # 延迟导入

    out: List[Skill] = []
    for idx, raw in _iter_skill_templates(text):
        p = _template_params(raw)
        name = plain(p.get("技能名", ""))
        if not name:
            continue
        sk = Skill(index=idx, name=name,
                   tree_type=plain(p.get("技能类型1", "")),
                   trigger_type=plain(p.get("技能类型2", "")))
        for prefix, label in LEVEL_LABELS:
            desc = p.get(prefix + "描述", "")
            if not desc:
                continue
            sk.levels[label] = parse_level(
                label, desc,
                duration=p.get(prefix + "持续", ""),
                cost=p.get(prefix + "消耗", ""),
                initial=p.get(prefix + "初始", ""),
            )
        if sk.levels:
            out.append(sk)

    # ---- 用官方 blackboard 校正（覆盖率远高于自然语言正则）
    try:
        table, idx = _official_tables()
    except Exception:
        return out
    if table:
        from . import skilldata as SD
        for sk in out:
            entry = SD.lookup(table, idx, char_id, sk.name, sk.index)
            if not entry:
                continue
            for label, lv in list(sk.levels.items()):
                apply_official(lv, entry, SD.level_index(label))
    return out


def skill_summary(sk: Skill, label: str) -> str:
    """生成一行可读的技能摘要（用于界面提示）。"""
    lv = sk.level(label)
    if not lv:
        return ""
    # 输出类数值与元信息分开收集：只有元信息（技力/持续）算不上「有效果」，
    # 那种情况要走下面的功能性技能提示。
    bits: List[str] = []
    if lv.atk_multiplier != 1.0:
        bits.append("攻击力 x%.2f" % lv.atk_multiplier)
    if lv.flat_atk:
        bits.append("攻击力 %+g" % lv.flat_atk)
    if lv.attack_speed:
        bits.append("攻速 %+g" % lv.attack_speed)
    if lv.interval_delta:
        bits.append("间隔 %+.2fs" % lv.interval_delta)
    if lv.hit_count > 1:
        bits.append("%d 连击" % lv.hit_count)
    if lv.dmg_scale != 1.0:
        bits.append("单发 x%.2f" % lv.dmg_scale)
    if getattr(lv, "magic_scale", 0.0):
        bits.append("法术分量 x%.2f" % lv.magic_scale)
    if getattr(lv, "stops_attack", False):
        bits.append("停止普攻")
    has_effect = bool(bits)          # 到这里 bits 里全是真正的输出加成
    if lv.duration:
        bits.append("持续 %gs" % lv.duration)
    if lv.cost:
        bits.append("技力 %g" % lv.cost)
    if has_effect:
        return "  ".join(bits)

    # 没有任何输出类数值时，告诉用户这是「本来就没有」还是「没解析出来」。
    # 这两件事体验上完全不同：前者是正确结果，后者是缺陷。
    desc = lv.description or ""
    if re.search(r"(防御力|法术抗性|生命上限|阻挡数|重量|部署费用|"
                 r"攻击范围|治疗|回复|隐身|迷彩|无法行动|停止攻击)", desc):
        return "功能性技能（不加输出，曲线与常态一致）"
    return "（未识别到可量化数值）"