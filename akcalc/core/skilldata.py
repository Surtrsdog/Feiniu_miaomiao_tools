# -*- coding: utf-8 -*-
"""从官方 skill_table.json 读取技能精确数值（取代 wikitext 正则猜测）。

为什么用官方表
--------------
PRTS 的文字描述是自然语言，同一件事有十几种写法
（「攻击力提升至225%」「造成相当于攻击力121%的伤害」「{{*|60%|+60%}}」…），
正则只能覆盖一部分，实测有 40% 以上的技能解析不出任何数值。
官方 blackboard 是结构化键值，直接给出倍率/间隔/连击数，覆盖率接近 100%。

字段语义（对照游戏内表现）
--------------------------
atk           技能期间攻击力倍率（2.0 = 提升至 200%）
atk_scale     同上，单次伤害的倍率（更常见于「造成相当于攻击力 x% 的伤害」）
base_attack_time  攻击间隔的「替换」值（不是增量！）
interval      攻击间隔增量或替换值，视技能而定；负数表示缩短
attack_speed  攻速加成
cnt / times / attack@times  连击数
duration      持续时间
cost          技力消耗
sp            初始技力
"""
from __future__ import annotations

import io
import json
import os
import re
from typing import Dict, List, Optional

CACHE_NAME = "skill_table.json"
FULL_NAME = "skill_table_full.json"

#: 随程序分发的精简技能表（akcalc/data/skill_table.json）
def default_path() -> str:
    import os
    return os.path.join(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))), "data", CACHE_NAME)


def _data_dir() -> str:
    import os
    return os.path.join(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))), "data")


def full_path() -> str:
    """完整原始 skill_table.json 的路径（含 spData/blackboard 等全部字段）。

    「查看原代码」要展示的正是这份原始结构；它随包分发（体积 7MB），
    打包后落在 _MEIPASS 里，这里按候选路径逐个找。
    """
    import os
    import sys
    cands = [os.path.join(_data_dir(), FULL_NAME)]
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        cands.append(os.path.join(meipass, FULL_NAME))
        cands.append(os.path.join(meipass, "akcalc", "data", FULL_NAME))
        cands.append(os.path.join(meipass, "data", FULL_NAME))
    for p in cands:
        if os.path.isfile(p):
            return p
    return cands[0]


#: 完整原始表的内存缓存（7MB，只读一次）
_FULL_TABLE = None


def load_full() -> Dict[str, dict]:
    """懒加载完整原始 skill_table.json（含 spData/blackboard/description）。"""
    global _FULL_TABLE
    if _FULL_TABLE is None:
        _FULL_TABLE = load(full_path())
    return _FULL_TABLE


def load(path: str) -> Dict[str, dict]:
    """读技能表，失败返回空字典。"""
    try:
        with io.open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def _bb(level: dict) -> Dict[str, float]:
    """把 blackboard 转成 key -> value 字典。

    同时兼容两种存储形态：
      原始官方表   {"blackboard": [{"key": "atk", "value": 2.0}, ...]}
      精简打包后   {"bb": {"atk": 2.0, ...}}
    """
    pre = level.get("bb")
    if isinstance(pre, dict):
        out: Dict[str, float] = {}
        for k, v in pre.items():
            try:
                out[k] = float(v)
            except (TypeError, ValueError):
                continue
        return out
    out = {}
    for b in level.get("blackboard") or []:
        k = b.get("key")
        if not k:
            continue
        try:
            out[k] = float(b.get("value"))
        except (TypeError, ValueError):
            continue
    return out


def _last(keys: List[str], bb: Dict[str, float], default: float = 0.0) -> float:
    for k in keys:
        if k in bb:
            return bb[k]
    return default


#: 中文数字 -> 阿拉伯数字（技能描述里「二连击」「八连击」很常见）
_CN_NUM = {"一": 1, "二": 2, "两": 2, "三": 3, "四": 4, "五": 5,
           "六": 6, "七": 7, "八": 8, "九": 9, "十": 10}

#: 「攻击变为二连击」「特殊的八连击」这类写法
#: 「造成相当于攻击力 350% 的伤害」
_RE_SCALE = re.compile(r"攻击力\s*<?[^0-9%]{0,12}?(\d{2,4}(?:\.\d+)?)\s*%")

_RE_HITS_CN = re.compile(r"([一二两三四五六七八九十])\s*连(?:击|射)")
_RE_TIMES_CN = re.compile(r"([一二两三四五六七八九十])\s*次")
_RE_TIMES_AR = re.compile(r"(?<![0-9.])(\d{1,2})\s*次")
_RE_HITS_AR = re.compile(r"(?<![0-9.])(\d{1,2})\s*连(?:击|射)")


#: 官方描述里夹着 <@ba.vup>10</> 这类富文本标签，标签会把数字和
#: 后面的「次 / 连击」隔开，不剥掉就永远匹配不上。
_RE_TAG = re.compile(r"<[^<>]{0,24}>")

#: 「第二次及以后使用时追加攻击力+30%」——这类**条件加成**不能算进
#: 无条件倍率。艾雅法拉二技能 bb 里 amgoat_s_1[b].atk=0.3 就是这么来的：
#: 第一次施放根本没有这 30%，老代码取值时把所有 ``[x].atk`` 一视同仁，
#: 于是「攻速+30」的技能被算成「攻击力 x1.60 且 2 连击」，完全对不上。
#:
#: 判定办法：描述里出现这些词，且该 blackboard 键的下标不是 [a]
#: （[a] 通常是基础段，[b]/[c] 才是追加段）。
_RE_COND = re.compile(r"第二次及以后|每使用过一次|每重复使用|再次使用|"
                      r"后续使用|第二次起|每使用一次技能|"
                      r"之后每次|叠加(?:至|到)?\s*最多")

#: 描述里标明「这一段是条件加成」的 blackboard 下标前缀。
#: 官方习惯用 [a] 表示无条件基础值、[b]/[c] 表示追加/叠加段。
_RE_SUB_IDX = re.compile(r"\[([a-z])\]")


def _is_conditional_key(key: str, desc: str) -> bool:
    """这个 blackboard 键是不是「满足条件才生效」的加成？

    只看两件事：
      1. 键名里有 ``[x]`` 这种分段下标，且下标不是 ``a``；
      2. 技能描述里确实写了「第二次及以后 / 每使用过一次」这类条件。
    两条都成立才认为是有条件——只满足一条可能是别的语义。

    这样艾雅法拉二技能只按基础段 ``[a]`` 算（攻速 +30，攻击力 x1.0），
    棘刺三技能同理（攻击力 +60%，而不是 +80%）。
    """
    if not desc:
        return False
    m = _RE_SUB_IDX.search(key or "")
    if not m:
        return False
    if m.group(1) == "a":
        return False
    return bool(_RE_COND.search(desc))


def _strip_tags(desc: str) -> str:
    """去掉描述里的富文本标签，只留可读文字。"""
    if not desc:
        return ""
    return _RE_TAG.sub("", desc)


def _render_desc(desc: str, bb: dict) -> str:
    """把描述里的 {attack@times} 这类占位符换成 blackboard 的真实数值。

    官方 desc 是模板，数字全在占位符里（能天使 S2：「攻击变为{attack@times}连射」）。
    不先渲染就去猜连击数，永远猜不出来。
    """
    if not desc:
        return ""
    text = str(desc)

    def repl(m):
        key = m.group(1).strip()
        for cand in (key, key.split(":")[0]):
            if cand in bb:
                v = bb[cand]
                try:
                    fv = float(v)
                    return str(int(fv)) if abs(fv - int(fv)) < 1e-9 else ("%g" % fv)
                except (TypeError, ValueError):
                    return str(v)
        return m.group(0)

    text = re.sub(r"\{([A-Za-z0-9_@.\[\]:]+)(?::[^}]*)?\}", repl, text)
    # {0%} {0%:0%} 这类格式占位符直接去掉
    text = re.sub(r"\{[^A-Za-z}][^}]*\}", "", text)
    return text


def _hits_backed_by_text(n: int, desc: str, bb: dict = None) -> bool:
    """blackboard 里的 cnt/times 到底是不是连击数？

    这个键的语义在实际数据里很不统一，至少有三种含义：

      * 真连击——「攻击变为 {cnt} 连射」(能天使、黑键等)
      * 拉普兰德式物件数——「立即获得 {cnt} 枚棋子」(望 三个技能全是)
      * 可叠加层数——「获得 {cnt} 层……防御力的增益」(石棉、塔露拉)

    后两种都不该参与 DPS 计算，否则会把伤害放大到数十倍
    （望三技能曾经被算成 8 连击，DPS 虚高到 23926）。

    判定方法：描述里必须出现「N 连击/连射」；或者出现「N 次」且
    没有「枚/个/发/层/格」这类明确指向其他对象的量词。
    """
    if n < 2 or not desc:
        return False
    text = _strip_tags(_render_desc(str(desc), bb or {}))

    # 1) 直接写了「N 连击/连射」——肯定是连击
    for m in _RE_HITS_AR.finditer(text):
        if int(m.group(1)) == n:
            return True
    for m in _RE_HITS_CN.finditer(text):
        if _CN_NUM.get(m.group(1), 1) == n:
            return True

    # 2) 写了「N 次」，且附近没有属于其他对象的量词
    #    （「x7 次所属于谁」::「对…造成 N 次…伤害」是连击，
    #     「获得 N 层」不是）
    if _RE_TIMES_AR.search(text, 0) and _counts_other_objects(text, n):
        return False
    for m in _RE_TIMES_AR.finditer(text):
        if int(m.group(1)) == n:
            return True
    for m in _RE_TIMES_CN.finditer(text):
        if _CN_NUM.get(m.group(1), 1) == n:
            return True
    return False


def _counts_other_objects(text: str, n: int) -> bool:
    """描述里是否出现「n + 枚/个/发/层/格…」？

    出现了就说明这个数字指的是别的东西（棋子数、层数、子弹数…），
    不能当连击数用。
    """
    units = "枚个发层格台梵部颗次根道束把份技能点"
    pat = re.compile(r"%d\s*(?:%s)" % (n, units))
    return bool(pat.search(text))


def _parse_hits_from_text(desc: str) -> int:
    """从技能描述里读连击数。

    有些技能的 blackboard 只给了单次伤害倍率，连击数只写在描述里
    （送葬人「最终旅程」：bb 只有 base_attack_time，描述写「二连击」）。
    这种漏掉的话整条技能的 DPS 会低一半。

    「次」这条线索最容易误判，必须排除三类看着像但完全不是连击的写法：

      1. **施放次数**：「每次部署后可发动 4 次技能」（闪击）、
         「可以充能 2 次」（陈、月见夜）——说的是技能能攒几次。
      2. **第二次及以后的追加效果**：「第二次及以后使用时追加攻击力」
         （艾雅法拉二技能）——说的是技能第几次施放。
      3. **层数 / 物件数**：「击中目标 3 次后」「立即获得 2 枚棋子」。

    排除办法：先按分句切开，去掉带这些语义的分句，再在剩下的文字里找
    「N 连击 / N 连射」。这么改之前，闪击的一技能（4 次技能）被算成
    4 连击、艾雅法拉二技能被算成 2 连击，DPS 直接翻好几倍。
    """
    if not desc:
        return 1
    desc = _strip_tags(desc)
    text = _drop_non_hit_clauses(desc)
    best = 1
    for m in _RE_HITS_AR.finditer(text):
        try:
            n = int(m.group(1))
        except ValueError:
            continue
        if 2 <= n <= 20:
            best = max(best, n)
    for m in _RE_HITS_CN.finditer(text):
        n = _CN_NUM.get(m.group(1), 1)
        if 2 <= n <= 20:
            best = max(best, n)
    if best > 1:
        return best
    # 「发动 10 次斩击」这种只写「次」不写「连击」的
    for m in _RE_TIMES_AR.finditer(text):
        try:
            n = int(m.group(1))
        except ValueError:
            continue
        if 2 <= n <= 20:
            best = max(best, n)
    for m in _RE_TIMES_CN.finditer(text):
        n = _CN_NUM.get(m.group(1), 1)
        if 2 <= n <= 20:
            best = max(best, n)
    return best


#: 分句里出现这些词，说明这一句讲的不是「一次攻击打几下」，
#: 整句排除掉再去找连击数。
_NON_HIT_CLAUSE = re.compile(
    r"第二次及以后|每使用过一次|再次使用|后续使用|第二次起|"
    r"可发动|c可以充能|可以充能|充能|"
    r"次技能|次部署|每次部署|"
    r"枚|个目标|层|格|发子弹|点费用|点技力|"
    r"最多|上限|叠加")


def _drop_non_hit_clauses(desc: str) -> str:
    """把「N 次」但语义不是连击的分句剔除，只留下讲攻击次数的部分。

    按中英文标点 + 换行切句，逐句判断，命中 :data:`_NON_HIT_CLAUSE`
    的句子整句丢掉。剩下的文字里如果还有「N 连击」才可信。
    """
    if not desc:
        return ""
    parts = re.split(r"[，,。；;！!？?\n]", desc)
    keep = [p for p in parts if p.strip() and not _NON_HIT_CLAUSE.search(p)]
    return "，".join(keep)


#: 官方 blackboard 的键名没有统一规范，实测同一件事有几十种写法：
#:   atk_scale / attack@atk_scale / attack@s2_atk_scale / atk_scale_2
#:   attack@tomimi_s_2.atk_scale / blkngt_s_2.atk_scale / atk_scale[normal]
#: 只认字面量 atk_scale 会漏掉一半以上的技能。下面这几个函数按
#: 「键里有没有这段语义」来找，取不到才走字面量精确匹配。
#: 只在特定目标/条件下才成立的下标，默认不能拿来当主倍率。
#: 例：反制电磁脉冲有 atk_scale[drone]=8.0 和 atk_scale[normal]=4.0，
#: 取 drone 会把对普通敌人的伤害高估一倍。
_SPECIAL_SUB = ("drone", "heavy", "light", "crit", "kill", "extra",
                "trigger", "period", "once", "debuff", "evade", "damage",
                "fake", "skill", "aoe")


def _key_rank(k: str) -> tuple:
    """键的优先级：越小越像「对普通目标的主倍率」。"""
    low = k.lower()
    special = 0
    if "[" in low:
        sub = low[low.find("[") + 1:low.rfind("]")] if "]" in low else ""
        special = 2 if sub in _SPECIAL_SUB else 1
    if ".atk" in low or "." in low.split("[")[0]:
        special = max(special, 1)          # xxx_s_2.atk_scale 这类
    return (special, len(k), k)


def _keys_with(bb: Dict[str, float], *needles: str) -> List[str]:
    """返回键名包含全部 needles 的键，按「越像主倍率」排序。"""
    out = [k for k in bb if all(n in k.lower() for n in needles)]
    out.sort(key=_key_rank)
    return out


def _first_val(bb: Dict[str, float], keys: List[str], *, lo: float = 0.0,
               hi: float = 100.0) -> Optional[float]:
    """按顺序取第一个落在 [lo, hi] 区间里的值。"""
    for k in keys:
        v = bb.get(k)
        if v is None or not (lo < v <= hi):
            continue
        return float(v)
    return None


def _fallback_multiplier(bb: Dict[str, float],
                         desc: str = "") -> Optional[float]:
    """通用兜底：从任意形态的键里找「攻击力倍率」。

    注意 atk 结尾但值为 0 的（如 attack@atk=0.0）要跳过，
    否则会把「攻击力 +0%」当成倍率 0 用。

    ``desc`` 用来剔除条件加成（见 :func:`_is_conditional_key`）：
    键名形如 ``xxx[b].atk`` 只有在描述写了「第二次及以后」时才是追加
    加成，此时**不能**计入无条件倍率。
    """
    def ok(k: str) -> bool:
        return not _is_conditional_key(k, desc)

    # 1) 明确的 scale 类键（可能是倍率，也可能是百分比）
    for k in _keys_with(bb, "atk_scale"):
        if not ok(k):
            continue
        v = bb[k]
        if v > 1.0001:
            return float(v)
    for k in _keys_with(bb, "atk_scale"):
        if not ok(k):
            continue
        v = bb[k]
        if 0.15 < v <= 1.0:
            return float(v)          # 例如 0.75 表示 75%
    # 2) xxx@atk 形式（+120% -> 1.2，是增量，要 +1）
    for k in _keys_with(bb, "atk"):
        if not ok(k):
            continue
        if k.endswith("@atk") or k.endswith(".atk"):
            v = bb[k]
            if 0.15 < v <= 8.0:
                return 1.0 + float(v)
    return None


def extract(skill_entry: dict, level_index: int = -1) -> dict:
    """从一个技能的某个等级取出可量化参数。

    返回 dict，键与 skills.SkillLevel 对齐：
      atk_multiplier / flat_atk / attack_speed / interval_delta /
      hit_count / duration / cost / initial / extra
    """
    levels = skill_entry.get("levels") or []
    if not levels:
        return {}
    lv = levels[max(0, min(level_index if level_index >= 0 else len(levels) - 1,
                           len(levels) - 1))]
    bb = _bb(lv)
    #: 剥掉富文本标签后的描述，用于判定「条件加成 / 连击数」等语义。
    _desc = _strip_tags(lv.get("desc") or lv.get("description") or "")

    # ---- 攻击力倍率
    # 三条键的语义完全不同，混淆会算出离谱结果（这里按官方描述逐个核对过）：
    #   atk              加算百分比 -> 总倍率 = 1 + atk
    #                    描述写「攻击力+{atk:0%}」，真银斩 atk=2.0 即 +200% => x3.0
    #   attack@atk_scale 直接就是倍率，描述写「提升至{attack@atk_scale}」
    #                    能天使过载 1.1 => x1.1
    #   atk_scale        单次伤害缩放，描述写「造成相当于攻击力 x% 的伤害」
    mul = 1.0
    dmg_scale = 1.0
    seg: List[float] = []          # 多段递减倍率的各段倍率
    if "atk" in bb:
        mul = 1.0 + bb["atk"]
        # atk 和 atk_scale 同时出现时多数是两件事都要算：
        #   抑扬格 atk=0.6 + atk_scale=2.25 -> 1.6 x 2.25（面板加成 + 单次倍率）
        #   阵雨连绵 atk=0.55 + atk_scale=2.4
        # 但也有 atk_scale 才是主倍率的（荆藤庇荫 0.5 就是单次伤害系数），
        # 两者相乘都符合官方描述，所以这里都保留。
        if "atk_scale" in bb and bb["atk_scale"] > 0:
            dmg_scale = bb["atk_scale"]
    elif any(_is_conditional_key(k, _desc) for k in bb
             if k.endswith("@atk") or k.endswith(".atk")):
        # 只有**条件型**的 ``xxx[b].atk``，没有无条件 atk：
        # 典型是艾雅法拉二技能（``amgoat_s_1[b].atk=0.3``，描述写
        # 「第二次及以后使用时追加攻击力+30%」）。第一次施放没有这层
        # 加成，所以倍率就是 1.0，绝不能算成 x1.30。
        # 这类技能的 atk_scale 若存在，按单次伤害缩放处理。
        if bb.get("atk_scale", 0) > 0:
            dmg_scale = bb["atk_scale"]
    elif "fk" in bb:
        # fk 是「面板攻击力的整倍率」，只有少数技能用它（如艾雅法拉 点燃）。
        # 此时同表的 atk_scale 是溅射那一半的倍率（点燃 fk=3.7、atk_scale=1.85），
        # 用 atk_scale 会把主目标伤害算低一半。
        mul = bb["fk"]
        # 注意：这里不再把 atk_scale 折成 dmg_scale。fk 类的 atk_scale 是
        # 「溅射部分相对主目标的比值」（点燃 3.7 vs 1.85），它描述的是范围
        # 里其它目标的伤害，不是主目标要再乘一遍的系数。以前折进来会让
        # 主目标 DPS 直接少一半。
    elif "attack@atk_scale" in bb:
        mul = bb["attack@atk_scale"]
    elif "attack@atk_scale_base" in bb:
        # 逻各斯「提喻」这类：每 attack@cooldown 秒打一次，
        # 倍率从 base 起按 delta 递增（对同一目标逐渐提高）。
        # 这里取 base，也就是最保守的下限值；上限会把总伤害算高。
        mul = bb["attack@atk_scale_base"]
    elif "success.atk_scale" in bb:
        # 断罪者「创世纪」：成功分支的倍率（success./failure. 前缀）
        mul = bb["success.atk_scale"]
    elif "atk_scale" in bb:
        # 有些技能是「依次造成 100%/92%/…/5%」，键是 atk_scale、atk_scale_2…
        # 这种要按段数求和（这里用均值 x 段数），否则总伤害会少算一大半。
        seg = [bb["atk_scale"]]
        for i in range(2, 13):
            v = bb.get("atk_scale_%d" % i)
            if v is None:
                break
            seg.append(v)
        if len(seg) >= 3:
            mul = sum(seg)                      # 逐段倍率之和
            hits = len(seg)                     # 段数记作命中次数
            seg = list(seg)
        else:
            dmg_scale = bb["atk_scale"]
    else:
        _fb = _fallback_multiplier(bb, _desc)
        if _fb is not None:
            mul = _fb
    if mul == 1.0 and dmg_scale == 1.0:
        # 描述里可能还写着「造成相当于攻击力 xxx% 的伤害」而 bb 没给
        # （少数技能确实如此），兜底扫一眼，扫不到就保持 1.0
        m = _RE_SCALE.search(lv.get("desc") or lv.get("description") or "")
        if m:
            try:
                v = float(m.group(1))
                if v > 100.0:
                    mul = v / 100.0
            except ValueError:
                pass

    # ---- 连击数（多段倍率已经给出段数时不再覆盖）
    multi_seg = len(seg) >= 3
    hits = 1
    if not multi_seg:
        for k in ("cnt", "times", "attack@times", "attack@cnt", "hit_times"):
            if k in bb and bb[k] >= 2:
                cand = int(round(bb[k]))
                # 【关键】cnt 并不总是连击数。盼的三个技能
                # cnt=2/2/8 分别是「2 枚棋子」「8 枚棋子」；
                # 石棉/塔露拉的 cnt 是「可叠加层数」，
                # 也不是连击。只有描述里真写了连击才认。
                if _hits_backed_by_text(cand, lv.get("desc") or
                                        lv.get("description") or "", bb):
                    hits = cand
                    break
    if hits == 1 and not multi_seg:
        # blackboard 没给连击数时去描述里读。三种写法都要认：
        #   「攻击变为二连击」（送葬人 最终旅程）
        #   「发动 10 次斩击」（赤刃明霄陈 赤霄·绝影-驰）
        #   「特殊的八连击」（阿莫里斯）
        hits = _parse_hits_from_text(lv.get("desc") or lv.get("description") or "")

    iv_delta = 0.0
    if "base_attack_time" in bb:
        iv_delta = bb["base_attack_time"]
    elif "interval" in bb:
        iv_delta = bb["interval"]
    iv_abs = 0.0
    speed = _last(["attack_speed", "attack@attack_speed"], bb, 0.0)
    dur = _last(["duration", "skill_duration"], bb, 0.0)
    cost = _last(["cost", "sp_cost"], bb, 0.0)
    init = _last(["sp", "init_sp"], bb, 0.0)
    flat = _last(["attack@atk", "atk_flat"], bb, 0.0)

    extra: List[str] = []
    if mul != 1.0:
        extra.append("攻击力 x%.2f" % mul)
    if hits > 1:
        extra.append("%d 连击" % hits)
    if iv_delta:
        extra.append("间隔 %+.2fs" % iv_delta)
    if speed:
        extra.append("攻速 %+g" % speed)

    return {
        "atk_multiplier": mul,
        "dmg_scale": dmg_scale,
        "flat_atk": flat,
        "attack_speed": speed,
        "interval_delta": iv_delta,
        "interval_abs": iv_abs,
        "hit_count": hits,
        "duration": dur,
        "cost": cost,
        "initial": init,
        "extra": extra,
    }


def skill_ids(char_id: str) -> List[str]:
    """由 char_id 推出三个技能的 id。

    官方命名是 ``char_<代号>`` -> ``skchr_<代号>_1/2/3``，但代号未必是
    拼音全拼（能天使是 ``char_103_angel``，不是 ``char_exusiai``），
    所以这个函数只作兜底；主路径用 :func:`build_name_index` 按技能名查。
    """
    if not char_id.startswith("char_"):
        return []
    stem = char_id[5:]
    # 去掉数字前缀 "103_angel" -> "angel"
    if "_" in stem:
        stem = stem.split("_", 1)[1]
    return ["skchr_%s_%d" % (stem, i) for i in (1, 2, 3)]


def build_name_index(table: Dict[str, dict]) -> Dict[str, List[str]]:
    """技能名 -> [技能 id]，用于在拿不到 char_id 规则时按名字回退。"""
    idx: Dict[str, List[str]] = {}
    for sid, entry in table.items():
        for lv in entry.get("levels") or []:
            nm = lv.get("name")
            if nm:
                idx.setdefault(nm, [])
                if sid not in idx[nm]:
                    idx[nm].append(sid)
                break
    return idx


def lookup(table: Dict[str, dict],
           name_index: Dict[str, List[str]],
           char_id: str,
           skill_name: str,
           slot: int) -> Optional[dict]:
    """先按 char_id 规则找，再按技能名找。

    按名字找时分两轮：优先 ``skchr_*``（干员专属技能），其次
    ``skcom_*`` / ``sktok_*``（通用/符卡技能）。

    为什么需要第二轮
    ----------------
    大量干员的一技能其实直接复用通用技能，官方表里根本没有
    ``skchr_<代号>_1``，只有 ``skcom_atk_up[1]`` 这样的共享条目
    （安德切尔的「攻击力强化·α型」、芬的「冲锋号令·α型」等）。
    老代码只认 ``skchr_``，于是这 95 个技能全部解析失败——图鉴里
    它们的「查看原代码」按钮点了没反应，状态时长等细节也补不出来。
    """
    for sid in skill_ids(char_id):
        if sid in table:
            # 编号对得上，但名字必须也吻合（防止 _2/_3 顺序不同的干员）
            e = table[sid]
            nm = ((e.get("levels") or [{}])[0]).get("name") or ""
            if nm == skill_name:
                return e
    cands = name_index.get(skill_name) or []
    # 第一轮：干员专属技能
    for sid in cands:
        if sid.startswith("skchr_"):
            return table[sid]
    # 第二轮：通用技能（skcom_*）/ 符卡技能（sktok_*）
    for sid in cands:
        e = table.get(sid)
        if isinstance(e, dict) and e.get("levels"):
            return e
    return None

#: 技能等级名 -> 官方 levels 下标。
#: 官方 levels 固定 10 项：0=1级 … 6=7级, 7=专一, 8=专二, 9=专三。
LEVEL_INDEX: Dict[str, int] = {
    "1": 0, "2": 1, "3": 2, "4": 3, "5": 4, "6": 5, "7": 6,
    "专一": 7, "专二": 8, "专三": 9,
    "M1": 7, "M2": 8, "M3": 9,
}


def level_index(label: str) -> int:
    """把界面上的等级名翻译成 levels 下标，认不出就给专三。"""
    return LEVEL_INDEX.get(str(label).strip(), 9)

