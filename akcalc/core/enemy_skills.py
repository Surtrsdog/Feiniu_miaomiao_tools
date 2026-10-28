# -*- coding: utf-8 -*-
"""敌人/干员技能的文本模型与解包结构注解。

## 为什么要有这一层

图鉴原来有两套渲染：``ui/monster_codex.py`` 的弹窗、``ui/data_index.py``
的怪物详情。两边各写一份「技能名 + 冷却圆点 + 描述」，于是不可避免地
漂移——弹窗走 PRTS 映射，数据索引还在用「DanceFire（冷却 40 秒，初始
40 秒）：atk_scale 1」这种代码味摘要。同一只怪两个入口看到两种说法，
用户没法判断哪个是真的。

这里把**事实**（技能叫什么、初始/消耗多少、配到哪个 prefabKey、解包
参数怎么解释）集中成一份模型，UI 只负责画。模型本身不 import tk。

## 数据源优先级（PRTS 优先 + 档案补漏）

1. ``data/enemy_skills_prts.json``——PRTS wiki 抓的「技能名 / 初始 /
   消耗 / 效果」，效果一栏就是游戏内原文。有记录就**以它为准**。
2. ``enemy_handbook_table.json`` 的 ``abilityList``——游戏内敌人档案，
   与 PRTS 高度重合，但被富文本标签和分行切碎；只用来**补漏**
   （PRTS 没有的技能名）和**补充**（同名条目的额外句子）。
3. ``enemy_database.json`` 的 ``skills[]``——只有代码名和数值，没有人话。

## 三个必须踩住的坑

* PRTS ``消耗`` **不是** ``spCost``。``消耗`` 对应 ``cooldown``（循环
  冷却）；敌人 ``spCost`` 在 1773 条记录里 1538 条恒为 0，拿它当消耗
  会显示一排 0。见 ``tools/gen_enemy_skills_prts.py`` 的换算说明。
* PRTS ``初始`` 逐条等于 ``initCooldown``，是两份数据唯一可靠的数值锚点
  （也是 PRTS 记录能钉到 ``prefabKey`` 上的原因）。
* ``cost == 0`` 在 PRTS 里表示「这个技能不消耗技力 / 自动触发」，
  **不是缺失**。所以圆点照画，只是不写成「消耗 0」。同理 ``init == 0``
  表示「进图即可用」，也要画出来。

## 结构注解（给「查看原代码」用）

解包数据里**没有**技能指令级代码：``prefabKey`` 只是个注册名，真正的
状态机/行为树在客户端二进制里。所以注解只做三件事——把字段名翻成中文、
把 blackboard 的 key 查 ``codex_fields.json`` 的 tokens 拿释义、把
``initCooldown``/``cooldown`` 与 PRTS 的「初始/消耗」对一遍。查不到的
key **照样列出来**并标「暂无释义」+ 全局出现次数，让用户自己判断这是
罕见参数还是漏收的常用参数。绝不编造实现细节——用户会拿它当结论。
"""
from __future__ import annotations

import re
from typing import Dict, List, Optional, Tuple

#: PRTS 记录必须完整的 8 个键。少一个说明生成脚本换了格式，
#: 图鉴要能直接看出来而不是慢慢烂掉。
RECORD_KEYS = ("index", "name", "init", "cost", "effect", "code",
               "cooldown", "confident")

#: 富文本标签：<$ba.buffres>抵抗</> → 抵抗。
_TAG_RE = re.compile(r"</?[^>\n]{0,32}>")
#: PRTS 的 wiki 内链：[[闪亮果实]] → 闪亮果实。
_WIKILINK_RE = re.compile(r"\[\[([^\[\]\n]{1,40})\]\]")
#: 档案条目开头若是「【技能名】…」，把技能名抽出来当标题。
_BRACKET_NAME_RE = re.compile(r"^【([^】]{1,24})】\s*(.*)$", re.S)
#: PRTS 把形态写进技能名：纬地经天[第一形态] → 纬地经天。
_BARE_RE = re.compile(r"[\[［][^\]］]{0,12}[\]］]")

#: 描述关键词 → 该技能在黑板上很可能出现的 key（配对用的弱证据）。
_SKILL_HINTS = (
    (("持续", "每秒", "逐渐", "递增", "线性"), ("duration", "interval", "dot")),
    (("半径", "范围内", "范围"), ("range_radius", "range", "radius")),
    (("晕眩", "眩晕"), ("stun",)),
    (("冻结", "冰冻"), ("freeze", "frozen")),
    (("沉默",), ("silence",)),
    (("减速", "移动速度"), ("move_speed",)),
    (("攻击力", "%", "倍"), ("atk_scale",)),
    (("防御",), ("def", "def_scale")),
    (("召唤",), ("summon",)),
    (("治疗", "恢复"), ("heal_scale", "heal")),
)

#: 第一形态的正字标记。只认 PRTS 自己写出来的字面，不认列表顺序：
#: 实测 30 个裸名撞车组里，「列表第一条」与「带初始标记那条」有 10 组不同。
_FORM_FIRST = re.compile(
    r"(第一形态|1形态|初始模式|初始形态|一般模式|初生形态|正常形态|默认模式)")
#: 后续形态的正字标记，用来反证「剩下那条才是第一形态」。
_FORM_LATER = re.compile(
    r"(第二形态|第三形态|2形态|3形态|强化模式|进化形态|完美形态|狂暴|重生|"
    r"复活|显形|隐形|第二阶段|第三阶段|地面模式\(重生后\))")


# --------------------------------------------------------------- 文本清洗

def clean(text) -> str:
    """剥掉富文本标签与 wiki 内链，保留换行（换行是 PRTS 的条目分隔）。"""
    s = _TAG_RE.sub("", str(text if text is not None else ""))
    s = _WIKILINK_RE.sub(r"\1", s)
    return s.replace("\r\n", "\n").replace("\r", "\n").strip()


def effect_lines(text) -> List[str]:
    """把 PRTS ``effect`` 切成一行一条。

    PRTS 用 ``\n`` 分隔「触发条件 / 效果 / 备注」，直接一行一条排版
    最接近游戏内技能说明；行内多余空白折成单空格。
    """
    out = []
    for raw in clean(text).split("\n"):
        ln = re.sub(r"[ \t\u3000]+", " ", raw).strip()
        if ln and ln not in ("*", "-"):
            out.append(ln)
    return out


def split_handbook(sections) -> Tuple[List[dict], List[dict]]:
    """把 ``HandbookIndex.sections()`` 拆成「带【技能名】」与「散句」两类。

    named: ``[{name, text, silence}]``；plain: ``[{text, title, silence}]``。
    带【名】的归「技能」卡统一排版（PRTS 样式），散句归「特性」卡，
    避免同一句话在界面上出现两次。
    """
    named: List[dict] = []
    plain: List[dict] = []
    for sec in sections or []:
        title = clean(sec.get("title") or "")
        for ln in sec.get("lines") or []:
            txt = clean(ln.get("text") or "")
            if not txt:
                continue
            m = _BRACKET_NAME_RE.match(txt)
            if m:
                named.append({"name": clean(m.group(1)), "text": txt,
                              "silence": bool(ln.get("silence"))})
            else:
                plain.append({"text": txt, "title": title,
                              "silence": bool(ln.get("silence"))})
    return named, plain


def strip_named(sections) -> List[dict]:
    """只保留散句的 ``sections`` 形态（给「特性 / 技能描述」卡用）。"""
    out = []
    for sec in sections or []:
        keep = []
        for ln in sec.get("lines") or []:
            txt = clean(ln.get("text") or "")
            if not txt or _BRACKET_NAME_RE.match(txt):
                continue
            keep.append(ln)
        if keep:
            out.append({"title": sec.get("title") or "", "lines": keep})
    return out


# ------------------------------------------------------------- 数据加载

#: ``enemy_skills_prts.json`` 缓存（进程内一份）
_PRTS_CACHE: dict = {"key": None, "data": {}, "meta": {}}
#: ``codex_fields.json`` 的 tokens 索引缓存
_TOKEN_CACHE: dict = {"key": None, "data": {}}
#: 敌人技能 blackboard key 的全局出现次数缓存
_BB_STATS: dict = {"key": None, "data": {}}


def load_prts(app) -> Dict[str, List[dict]]:
    """读 PRTS 技能表，返回 ``{enemy_id: [record, ...]}``。

    8 个键一个不少地带上：``index/name/init/cost/effect/code/cooldown/
    confident``。旧实现在这里只留了 ``name/code/confident``，导致图鉴
    只能显示技能名——PRTS 的效果原文（也就是用户真正要的那句人话）
    被丢掉了。

    走 ``app._read_bundled_json`` 而不是自己拼路径：那个函数同时认识
    开发期的 ``akcalc/data`` 和打包后的 ``_MEIPASS``。
    """
    key = id(app)
    if _PRTS_CACHE["key"] == key:
        return _PRTS_CACHE["data"]
    raw = {}
    try:
        raw = app._read_bundled_json("enemy_skills_prts.json") or {}
    except Exception:                                       # noqa: BLE001
        raw = {}
    data: Dict[str, List[dict]] = {}
    for eid, items in (raw.get("skills") or {}).items():
        recs = []
        for it in items or []:
            if not isinstance(it, dict):
                continue
            rec = {}
            for k in RECORD_KEYS:
                rec[k] = it.get(k)
            rec["name"] = clean(rec.get("name") or "")
            rec["effect"] = clean(rec.get("effect") or "")
            rec["code"] = str(rec.get("code") or "").strip()
            rec["confident"] = bool(rec.get("confident"))
            try:
                rec["index"] = int(rec.get("index") or 0)
            except (TypeError, ValueError):
                rec["index"] = 0
            for f in ("init", "cost", "cooldown"):
                try:
                    rec[f] = float(rec[f]) if rec[f] is not None else None
                except (TypeError, ValueError):
                    rec[f] = None
            if rec["name"]:
                recs.append(rec)
        if recs:
            recs.sort(key=lambda r: r["index"])
            data[str(eid)] = recs
    _PRTS_CACHE["key"] = key
    _PRTS_CACHE["data"] = data
    _PRTS_CACHE["meta"] = raw.get("stats") or {}
    return data


def prts_meta(app) -> dict:
    """PRTS 表的自述统计（enemy / code_total / code_ok / code_none）。"""
    load_prts(app)
    return dict(_PRTS_CACHE["meta"] or {})


def handbook_index(app):
    """懒加载并复用一份 ``HandbookIndex``（挂在 app 上，避免重复读 1.4MB）。"""
    hb = getattr(app, "_handbook_index", None)
    if hb is not None:
        return hb
    from .handbook import HandbookIndex
    try:
        path = app.paths.handbook_cache
    except Exception:                                       # noqa: BLE001
        path = ""
    hb = HandbookIndex(path)
    try:
        hb.load()
    except Exception:                                       # noqa: BLE001
        pass
    try:
        app._handbook_index = hb
    except Exception:                                       # noqa: BLE001
        pass
    return hb


def skill_codes(entries) -> List[dict]:
    """从原始 enemyData entry 里取技能代码（prefabKey + 节奏 + blackboard）。

    取「技能最多」的那一档：同一 enemy_id 有多档（0/1/2 级）时，基础档
    往往带全套技能，高等级档反而只有数值覆盖。
    """
    best: List[dict] = []
    for e in entries or []:
        ed = (e or {}).get("enemyData") or {}
        sks = [s for s in (ed.get("skills") or []) if isinstance(s, dict)]
        if len(sks) > len(best):
            best = sks
    out = []
    for sk in best:
        bb = []
        for item in (sk.get("blackboard") or []):
            if not isinstance(item, dict):
                continue
            k = item.get("key") or ""
            if not k:
                continue
            bb.append((k, item.get("value"), item.get("valueStr")))
        out.append({
            "key": str(sk.get("prefabKey") or sk.get("key") or ""),
            "cooldown": sk.get("cooldown"),
            "init": sk.get("initCooldown"),
            "sp_cost": sk.get("spCost"),
            "blackboard": bb,
            "raw": sk,
        })
    return out
# ------------------------------------------------------- PRTS ↔ 代码配对

def bare_name(name: str) -> str:
    """去掉 ``[第一形态]`` 之类后缀，得到裸名。"""
    return _BARE_RE.sub("", name or "").strip()


def pick_form(candidates):
    """从「裸名相同、prefabKey 不同」的多个形态里挑一条（只认字面证据）。

    ``candidates`` 是 ``[(完整名, code, sure), ...]``。只有两种情况下给
    结果，其余一律 ``None`` 交给调用方放弃——配错比不配更糟，用户会拿
    它当结论：

    1. 恰好一条带「第一形态 / 初始模式 / 一般模式 / 初生形态」标记；
    2. 恰好一条**不带**任何后续形态标记（第二形态 / 狂暴 / 重生……），
       而其余都带（``日冕`` vs ``日冕[狂暴]``）。

    返回值恒为推测级：档案的 ``skills[]`` 里两个形态的码通常都在，没有
    任何数值能把它们分开，这本质是先验选择而非测量结论。
    """
    if not candidates:
        return None
    firsts = [t for t in candidates if _FORM_FIRST.search(t[0] or "")]
    if len(firsts) == 1:
        return (firsts[0][1], False)
    clean_ones = [t for t in candidates
                  if not _FORM_FIRST.search(t[0] or "")
                  and not _FORM_LATER.search(t[0] or "")]
    rest = [t for t in candidates if t not in clean_ones]
    if len(clean_ones) == 1 and rest and all(
            _FORM_LATER.search(t[0] or "") for t in rest):
        return (clean_ones[0][1], False)
    return None


def board_sig(code: dict) -> tuple:
    """一个技能参数表的「指纹」，用来判断两条技能是不是同一套数值。

    「本体」和「狂暴/二阶段」通常是两张独立 skills 条目，但 blackboard
    逐字相同，只有 prefabKey 多了 ``[Half]`` 之后缀。配对时必须把它们
    视为同一套数值，否则会互相抢位置。
    """
    bb = code.get("blackboard") or []
    return tuple((str(k), round(float(v), 3) if isinstance(v, (int, float))
                  else str(v)) for k, v, _s in bb)


def pair_heuristic(named, codes) -> dict:
    """启发式配对：共现数值（强）+ 语义关键词（弱）。

    两份数据在两个不同文件里（``abilityList`` 是文案、``skills[]`` 是
    逻辑），文件之间**没有任何 id 互引**，所以只能靠锚点：

    1. 描述写「持续 30.5s」而代码里恰好有 ``duration = 30.5``；
    2. 描述写「半径 2.5 范围内」而代码带 ``range_radius``。

    返回值 ``{id(item): (code, 是否高置信)}``；配不上的不出现。
    """
    out = {}
    if not named or not codes:
        return out

    keys_by_code, nums_by_code = [], []
    for c in codes:
        ks, vs = set(), set()
        for k, val, _vs in (c.get("blackboard") or []):
            ks.add(str(k).lower())
            try:
                vs.add(round(float(val), 3))
            except (TypeError, ValueError):
                pass
        keys_by_code.append(ks)
        nums_by_code.append(vs)

    taken = set()
    groups_wanted: dict = {}
    for item in named:
        txt = str(item.get("text") or line_text(item))
        low = txt.lower()

        want = set()
        for m in re.finditer(r"(\d+(?:\.\d+)?)", txt):
            try:
                want.add(round(float(m.group(1)), 3))
            except ValueError:
                pass
        hint_keys = set()
        for words, need in _SKILL_HINTS:
            if any(w in low for w in words):
                hint_keys.update(need)

        scored = []
        for i, ks in enumerate(keys_by_code):
            if i in taken:
                continue
            numeric = len(want & nums_by_code[i])
            semantic = sum(1 for h in hint_keys if any(h in k for k in ks))
            score = numeric * 10.0 + semantic * 2.0
            # 同分时优先**不带变体后缀**的：狂暴/二阶段的 blackboard 与本体
            # 逐字相同，打分必然并列，而档案写的是本体技能。
            variant = 1 if re.search(r"[\[0-9]", str(codes[i].get("key") or "")) else 0
            scored.append((score, numeric, -variant, i))
        if not scored:
            continue
        scored.sort(reverse=True)
        best_score, best_num, _neg, best_i = scored[0]
        best_sig = board_sig(codes[best_i])
        runner = 0.0
        for sc, _num, _n, j in scored[1:]:
            if board_sig(codes[j]) == best_sig:
                continue
            runner = sc
            break

        if best_num >= 1:
            taken.add(best_i)
            out[id(item)] = (codes[best_i], True)
            groups_wanted.setdefault(best_sig, []).append(id(item))
        elif best_score >= 2.0 and best_score - runner >= 2.0:
            taken.add(best_i)
            out[id(item)] = (codes[best_i], False)
            groups_wanted.setdefault(best_sig, []).append(id(item))

    # 冲突回收：两个不同技能名抢同一套参数 → 谁都不给。典型例子是「锏」的
    # 【肆虐风雪】与【瞬息杀机】共用 CircleAttack 那套 atk_scale+range_radius。
    for _sig, owners in groups_wanted.items():
        if len(owners) > 1:
            for oid in owners:
                out.pop(oid, None)
    return out


def line_text(item: dict) -> str:
    """兼容两种 named 形态（``text`` 或旧的 ``lines`` 列表）。"""
    if item.get("text"):
        return str(item["text"])
    return " ".join(str(x) for x in (item.get("lines") or []))


def pair_with_prts(named, codes, prts) -> dict:
    """PRTS 命中优先，剩下的再交给启发式。

    分层是刻意的：

    1. **PRTS 命中的**直接采用并标高置信——它的锚点是「初始冷却」这个
       精确数值，比任何关键词都硬；
    2. **PRTS 没覆盖的**名字才退回 :func:`pair_heuristic`，按它自己的
       置信度标 ``↳``/``≈``；
    3. 两边都没配上的保持单列代码块。

    名字匹配容错后缀：PRTS 把形态写进了技能名（``角力对决[初始模式]``），
    档案里只有裸名，所以先精确匹配、不中再按裸名找；裸名有多个候选时
    只有**都指向同一个 prefabKey** 才敢用，否则交给 :func:`pick_form`。
    """
    out = {}
    if not named:
        return out
    by_key = {}
    for c in codes or []:
        k = str(c.get("key") or c.get("prefabKey") or "")
        if k:
            by_key.setdefault(k, c)

    naked: Dict[str, list] = {}
    for full, (code, sure) in (prts or {}).items():
        base = bare_name(full)
        if base:
            naked.setdefault(base, []).append((full, code, bool(sure)))

    left_named = []
    taken = set()
    for item in named:
        nm = str(item.get("name") or "").strip()
        hit = (prts or {}).get(nm)
        if hit is None:
            cands = naked.get(bare_name(nm)) or []
            codeset = {c for _f, c, _s in cands}
            if len(codeset) == 1:
                _f, c, s = cands[0]
                hit = (c, s)
            elif len(codeset) > 1:
                hit = pick_form(cands)
        if not hit:
            left_named.append(item)
            continue
        key, sure = hit
        code = by_key.get(key)
        if code is None:
            # PRTS 说有这个技能，但当前档位的解包里没有这个 prefabKey
            # （不同难度档不一样），不算配对。
            left_named.append(item)
            continue
        out[id(item)] = (code, bool(sure))
        taken.add(id(code))

    left_codes = [c for c in (codes or []) if id(c) not in taken]
    if left_named and left_codes:
        for k, v in pair_heuristic(left_named, left_codes).items():
            out.setdefault(k, v)
    return out
# --------------------------------------------------------- 字段释义查询

def load_tokens(app) -> Dict[str, dict]:
    """``codex_fields.json`` 的 ``tokens`` 索引：``{key: {count, desc, ...}}``。

    只索引 200 个有释义的 token（全量 4335 个 token 里大多数没释义，
    列出来也没用）。命中规则见 :func:`lookup_token`。
    """
    key = id(app)
    if _TOKEN_CACHE["key"] == key:
        return _TOKEN_CACHE["data"]
    data: Dict[str, dict] = {}
    try:
        raw = app._read_bundled_json("codex_fields.json") or {}
    except Exception:                                       # noqa: BLE001
        raw = {}
    for t in raw.get("tokens") or []:
        if isinstance(t, dict) and t.get("key"):
            data[str(t["key"])] = t
    _TOKEN_CACHE["key"] = key
    _TOKEN_CACHE["data"] = data
    return data


def load_fields(app) -> Dict[str, dict]:
    """``codex_fields.json`` 的 ``fields`` 索引：``{name: record}``。"""
    try:
        raw = app._read_bundled_json("codex_fields.json") or {}
    except Exception:                                       # noqa: BLE001
        raw = {}
    out = {}
    for f in raw.get("fields") or []:
        if isinstance(f, dict) and f.get("name"):
            out[str(f["name"])] = f
    return out


def lookup_token(key: str, tokens: Optional[Dict[str, dict]] = None) -> dict:
    """按 key 查释义：先精确，再剥掉 ``前缀.`` 取末段。

    解包里的 blackboard key 有 ``dragon_fire.baseDamage`` 这种带命名空间
    的写法，含义与裸 ``baseDamage`` 相同，所以剥前缀是**结构性**的而不是
    猜测。返回 ``None`` 表示没查到——调用方要照原样显示 key 并标注，
    不能因为查不到就把它删了：用户正是靠「哪个 key 没释义」判断解包版
    本有没有新参数。
    """
    tokens = tokens or {}
    rec = tokens.get(key)
    if rec is not None:
        return rec
    tail = key.rpartition(".")[2]
    if tail and tail != key:
        return tokens.get(tail)
    return None


def load_bb_counts(app) -> Dict[str, int]:
    """敌人技能 blackboard key 的全局出现次数（扫一遍 2450 个 level 档）。

    没释义的 key 至少能显示「全库出现 N 次」，用户据此判断它是常见参数
    （值得补释义）还是一次性特例。结果缓存在 ``codex_fields.json`` 的
    ``tokens[].count`` 里拿不到的部分——那 200 个 token 的 count 是整个
    解包的口径，比「敌人技能」子集宽，不能混用。
    """
    key = id(app)
    if _BB_STATS["key"] == key:
        return _BB_STATS["data"]
    counts: Dict[str, int] = {}
    try:
        raw = app._read_bundled_json("enemy_database.json") or {}
        by_id = raw.get("by_id") or {}
    except Exception:                                       # noqa: BLE001
        by_id = {}
    for _eid, ents in by_id.items():
        for e in ents or []:
            ed = (e or {}).get("enemyData") or {}
            for sk in (ed.get("skills") or []):
                for it in (sk.get("blackboard") or []):
                    k = (it or {}).get("key")
                    if k:
                        counts[str(k)] = counts.get(str(k), 0) + 1
    _BB_STATS["key"] = key
    _BB_STATS["data"] = counts
    return counts


# ------------------------------------------------------------- 数值格式化

def fmt_num(v) -> str:
    """``40.0`` → ``40``，``2.5000`` → ``2.5``，``None`` → ``—``。

    解包里数值一律是 float，直接 str() 会得到满屏 ``1.0000000000000002``
    这类尾巴；统一走 ``%g`` 后再去掉 ``.0``。
    """
    if v is None:
        return "—"
    if isinstance(v, bool):
        return "是" if v else "否"
    if isinstance(v, str):
        return v
    try:
        f = float(v)
    except (TypeError, ValueError):
        return str(v)
    if f == int(f) and abs(f) < 1e15:
        return str(int(f))
    return ("%g" % f)


#: ``spType`` 枚举释义。``codex_fields.json`` 里**没有**这个字段的条目，
#: 所以按 ``skill_table_full.json`` 的实际取值内置一份，并标明来源不是
#: 解包释义表——不能让用户误以为是官方文档。
SPTYPE_CN = {
    0: "未知/0",
    1: "自动回复（随时间自然积攒）",
    2: "攻击回复（每次攻击 +increment）",
    4: "受击回复（每次受击 +increment）",
    8: "被动/无技力（落地即生效，不存在充能）",
}
SKILLTYPE_CN = {"MANUAL": "手动触发", "AUTO": "自动触发", "PASSIVE": "被动"}
DURTYPE_CN = {"NONE": "无弹药限制", "AMMO": "弹药制"}

#: 解包 ``skills[]`` 的字段释义。``codex_fields.json`` 里只有拼接形态的
#: ``enemyData.skills[]`` 一个条目，拆开的分字段（cooldown / initCooldown /
#: spCost / priority）都没收录，所以按 ``tools/gen_enemy_skills_prts.py``
#: 的换算结论内置。来源标注见 :data:`TIMING_SRC_NOTE`。
TIMING_SRC_NOTE = "口径见 tools/gen_enemy_skills_prts.py"
TIMING_DESC = {
    "cooldown": "技能循环冷却（秒）。PRTS 的「技能N消耗」对应的就是它，"
                "不是 spCost。",
    "initCooldown": "初始冷却（秒）。等于 PRTS 的「技能N初始」，即进图后"
                    "第一次可用的时间。",
    "spCost": "技力消耗。敌人侧这条几乎恒为 0（实测 1538/1773），"
              "拿它当「消耗」会显示一排 0，必须用 cooldown。",
    "priority": "同一次 AI 判定里多个技能都可触发时的优先级，数值大的先。",
}


def annotate_code(code: dict, rec: Optional[dict] = None,
                  tokens: Optional[Dict[str, dict]] = None,
                  fields: Optional[Dict[str, dict]] = None,
                  bb_counts: Optional[Dict[str, int]] = None) -> dict:
    """把一个技能代码对象翻成「人能读的结构注解」。

    只做**翻译与对照**，不推断逻辑：解包里没有技能指令，``prefabKey`` 只是
    客户端注册名，实现（状态机/行为树）不在解包数据中。任何「这个技能
    内部怎么跑」的结论都必须由 ``statemachines``（干员技能才有）给出，
    敌人侧没有对应数据，所以这里如实说没有。

    例外是 ``instructions`` 那一栏：它不读任何不存在的实现，只把
    ``blackboard`` 的**键名按行为语义归类排成执行顺序**——``atk_scale``
    必然发生在伤害结算、``duration`` 必然描述持续时间，这种先后关系由
    游戏机制本身决定，不是猜的。每条都带原始键名可回溯，推不出的键
    不进这一栏（仍会完整出现在 ``bb`` 里）。
    """
    tokens = tokens or {}
    fields = fields or {}
    bb_counts = bb_counts or {}
    prefab_rec = fields.get("prefabKey") or {}
    out = {
        "prefab": str(code.get("key") or ""),
        "prefab_desc": clean(prefab_rec.get("desc") or ""),
        "prefab_pitfall": clean(prefab_rec.get("pitfall") or ""),
        "bb": [],
        "timing": [],
        "notes": [],
        "undocumented": 0,
        "instructions": [],
        "prefab_meaning": "",
    }
    # ---- 指令序列：把 blackboard 的键名排成「触发 → 选目标 → 生效 → 计时」
    try:
        from . import skill_instructions as _SI
        out["instructions"] = _SI.build_instructions(code, tokens)
        out["prefab_meaning"] = _SI.prefab_meaning(out["prefab"])
    except Exception:                                       # noqa: BLE001
        # 指令合成是附加信息，坏了不能让整张注解表消失。
        out["instructions"] = []
    for k, v, vs in (code.get("blackboard") or []):
        hit = lookup_token(str(k), tokens)
        row = {
            "key": str(k),
            "value": fmt_num(vs if vs not in (None, "") else v),
            "desc": clean((hit or {}).get("desc") or ""),
            "category": clean((hit or {}).get("category") or ""),
            "documented": hit is not None,
            "count": bb_counts.get(str(k), 0),
            "alias": str(k).rpartition(".")[2] if "." in str(k) else "",
        }
        if hit is None:
            out["undocumented"] += 1
        out["bb"].append(row)

    # ---- 节奏三项与 PRTS 的交叉对照
    def _pair(label, db_val, prts_key):
        pv = (rec or {}).get(prts_key)
        note = ""
        if pv is not None and db_val is not None:
            try:
                d = abs(float(pv) - float(db_val))
            except (TypeError, ValueError):
                d = None
            if d is None:
                note = "无法比较"
            elif d < 1e-6:
                note = "与 PRTS 一致"
            elif d <= 0.51:
                note = "与 PRTS 差 %s 秒（抓取取整）" % fmt_num(d)
            else:
                note = "与 PRTS 差 %s 秒，仅供参考" % fmt_num(d)
        elif pv is None and rec:
            note = "PRTS 该条没有这一列"
        return {"label": label, "db": fmt_num(db_val),
                "prts": fmt_num(pv) if rec else None, "note": note}

    out["timing"].append(_pair("初始冷却 initCooldown",
                               code.get("init"), "init"))
    out["timing"].append(_pair("循环冷却 cooldown",
                               code.get("cooldown"), "cost"))
    sp = code.get("sp_cost")
    out["timing"].append({
        "label": "技力消耗 spCost", "db": fmt_num(sp), "prts": None,
        "note": "敌人侧恒为 0，不参与显示" if not sp else "非 0，额外标注"})

    if rec and rec.get("cost") in (0, 0.0):
        out["notes"].append(
            "PRTS 的「消耗」为 0，表示这个技能不按技力循环触发"
            "（自动/条件触发），不是数据缺失；此时循环节奏看 cooldown。")
    if code.get("sp_cost"):
        out["notes"].append(
            "spCost = %s 非 0：该技能的技力消耗确实存在，"
            "与 PRTS「消耗」（= cooldown）是两个量。" % fmt_num(code.get("sp_cost")))
    return out
# --------------------------------------------------------- 技能块（总装配）

def build_blocks(enemy_id: str, sections, codes, prts_recs) -> List[dict]:
    """把「PRTS / 档案 / 解包代码」三份东西拼成一份有序的技能块列表。

    排版顺序刻意跟游戏内技能面板一致——**PRTS 记录在前、按 PRTS 的
    ``index`` 排**，因为 PRTS 的顺序就是游戏里技能 0/1/2 的顺序；档案
    独有的技能名追加在后面。每条块自带 ``source``，UI 据此决定是否画
    ``↳`` 代码注解：

    * ``source="prts"``——PRTS 有记录，效果原文照排，数值用 PRTS 的
      初始/消耗（真值），``code`` 是同条 PRTS 记录钉住的 prefabKey。
    * ``source="handbook"``——PRTS 没这名，只有档案文案；数值退回解包的
      ``initCooldown``/``cooldown`` 并标「来自解包」。
    * ``source="code"``——两份文案都没有，只剩一个 prefabKey + blackboard，
      凑成一行的技术性条目（放最后，明说没有描述）。

    同名不同形态（``日冕`` / ``日冕[狂暴]``）按 PRTS 记录各自成块，因为
    PRTS 给了不同的 effect，合并会把两种形态的描述混成一段。
    """
    named, _plain = split_handbook(sections)
    codes = list(codes or [])
    recs = list(prts_recs or [])
    by_key: Dict[str, dict] = {}
    for c in codes:
        k = str(c.get("key") or "")
        if k:
            by_key.setdefault(k, c)

    blocks: List[dict] = []
    used_codes = set()
    used_named = set()

    # ---- 1) PRTS 记录（按 index）
    for rec in recs:
        key = str(rec.get("code") or "")
        code = by_key.get(key) if key else None
        # 名字对得上、但 PRTS 没钉住 code 的（confident=false），仍要显示
        # effect；此时按名字去档案里找同名条目拿不到代码，就留空。
        named_hit = None
        for item in named:
            if item.get("name") == rec.get("name"):
                named_hit = item
                break
        if code is not None:
            used_codes.add(id(code))
        elif named_hit is not None:
            # 名字同、代码不同：档案里这条技能确实存在，但 PRTS 没标 code，
            # 用裸名/形态逻辑补一条，保证「数值可以看」。
            pass
        if named_hit is not None:
            used_named.add(id(named_hit))
        lines = effect_lines(rec.get("effect"))
        extra = []
        if named_hit is not None:
            # 档案里同名条目的正文：PRTS 已覆盖的部分不再重复，只留补充句。
            body = clean(named_hit.get("text") or "")
            m = _BRACKET_NAME_RE.match(body)
            body = clean(m.group(2)) if m else body
            if body and not _covered(body, lines):
                extra.append(body)
        blocks.append({
            "name": rec.get("name") or "",
            "source": "prts",
            "sure": bool(rec.get("confident")),
            "code": code,
            "code_key": key,
            "init": rec.get("init"),
            "cost": rec.get("cost"),
            "lines": lines,
            "extra": extra,
            "silence": bool((named_hit or {}).get("silence")),
            # 原始 PRTS 记录留着：结构注解要拿它的 init/cost 跟解包对账，
            # 重建一份数字反而会丢掉「PRTS 到底有没有这一列」的区别。
            "rec": rec,
        })

    # ---- 2) 档案独有技能：PRTS 没有同名记录
    left_named = [it for it in named if id(it) not in used_named]
    left_codes = [c for c in codes if id(c) not in used_codes]
    pairs = pair_heuristic(left_named, left_codes) if left_named else {}
    for item in left_named:
        code, sure = pairs.get(id(item), (None, False))
        body = clean(item.get("text") or "")
        m = _BRACKET_NAME_RE.match(body)
        lines = [clean(m.group(2))] if m else [body]
        lines = [x for x in lines if x]
        blocks.append({
            "name": item.get("name") or "",
            "source": "handbook",
            "sure": bool(sure),
            "code": code,
            "code_key": str((code or {}).get("key") or ""),
            "init": (code or {}).get("init"),
            "cost": (code or {}).get("cooldown"),
            "lines": lines,
            "extra": [],
            "silence": bool(item.get("silence")),
            "from_unpack": code is not None,
        })
        if code is not None:
            used_codes.add(id(code))

    # ---- 3) 只剩代码的技能
    for c in codes:
        if id(c) in used_codes:
            continue
        blocks.append({
            "name": str(c.get("key") or "（未命名）"),
            "source": "code",
            "sure": False,
            "code": c,
            "code_key": str(c.get("key") or ""),
            "init": c.get("init"),
            "cost": c.get("cooldown"),
            "lines": [],
            "extra": [],
            "silence": False,
        })
    return blocks


def _covered(body: str, lines: List[str]) -> bool:
    """档案那句是否已被 PRTS 的效果行覆盖（避免同一句显示两遍）。

    判据是**字符集合包含**：档案常把 PRTS 的换行/标点吃掉或换个顺序，
    逐字比对会全部判成「不重复」，结果每张卡都出现两遍。
    """
    if not body:
        return True
    a = set(re.sub(r"[\s，。、；：（）()%]", "", body))
    for ln in lines:
        b = set(re.sub(r"[\s，。、；：（）()%]", "", ln))
        if not b:
            continue
        if a and b and len(a & b) / float(len(b)) >= 0.85:
            return True
    return False


def block_labels(block: dict) -> List[str]:
    """技能块的正文行（已清洗、已切行）。UI 与导出共用同一份文本。"""
    out = list(block.get("lines") or [])
    for extra in block.get("extra") or []:
        if extra and extra not in out:
            out.append(extra)
    if not out and block.get("source") == "code":
        out = ["（PRTS 与敌人档案都没有这个技能的描述，"
               "只有解包里的 prefabKey 和参数表）"]
    return out


def timing_text(block: dict) -> str:
    """技能块的「初始 / 消耗」一行。

    PRTS 的 ``cost`` 为 0 时不写「消耗 0」——0 表示不按技力循环触发，
    写成 0 秒会被读成「每 0 秒放一次」。只有两条都为 0/None 时才说
    「无节奏数据」。
    """
    init = block.get("init")
    cost = block.get("cost")
    src = "PRTS" if block.get("source") == "prts" else "解包"
    bits = []
    if init is not None:
        bits.append("初始 %s 秒" % fmt_num(init))
    if cost is not None and float(cost) > 0:
        bits.append("消耗 %s 秒" % fmt_num(cost))
    if not bits:
        return "无节奏数据"
    txt = " · ".join(bits)
    if cost is not None and not float(cost) > 0:
        txt += "（消耗为 0：不按技力循环触发）"
    return "%s（%s）" % (txt, src)


def dots(block: dict) -> List[tuple]:
    """技能名后面的节奏圆点：``[(秒数, 说明, 是否实心), ...]``。

    旧实现遇到 ``<= 0`` 就 ``continue``，于是 PRTS ``初始 = 0``（进图即可
    用，537 条）和 ``消耗 = 0`` 全都画不出点，用户看到的是「这技能没有
    冷却信息」。现在 0 也画，只有 ``None``（真没这一列）才跳过。
    """
    out = []
    init = block.get("init")
    cost = block.get("cost")
    if cost is not None:
        out.append((float(cost), "消耗", float(cost) > 0))
    if init is not None:
        out.append((float(init), "初始", True))
    return out
# ------------------------------------------------- 干员技能的结构注解

#: 干员技能 ``levels[]`` 里各字段的中文释义。``codex_fields.json`` 只收录了
#: 拼接形态（``levels[].duration / cost / initial``），拆开后的 ``spData.*``
#: 一个都没有，所以这里内置；来源是 ``skill_table_full.json`` 的实际取值
#: 加 ``statemachines`` 的推算口径，不是官方文档。
OPSKILL_FIELD_DESC = {
    "skillId": "技能 id（skchr_/skcom_ 前缀），skill_table 的主键",
    "iconId": "图标 id，与技能数值无关",
    "hidden": "是否在游戏内隐藏（未实装的技能为 true）",
    "name": "技能名（该等级）",
    "rangeId": "攻击范围 id，对应 range_table 里的格子图案",
    "description": "技能描述原文，含占位符（如 {atk_scale}）",
    "duration": "持续时间（秒）；0 表示瞬发/被动",
    "blackboard": "参数表：技能逻辑真正读的数值都在这里",
    "prefabId": "技能逻辑类名（客户端注册名），实现不在解包数据里",
    "spData": "技力配置（回复方式 / 消耗 / 初始 / 充能上限）",
    "spData.spType": "技力回复方式",
    "spData.spCost": "开启技能消耗的技力",
    "spData.initSp": "初始技力（落地/开局即有的部分）",
    "spData.increment": "每次回复事件增加的技力",
    "spData.maxChargeTime": "可充能次数（1 = 不可蓄力）",
    "spData.levelUpCost": "升级消耗（专精材料口径，非战斗数值）",
    "skillType": "触发方式",
    "durationType": "持续口径（弹药制会显示剩余发数）",
}


def load_statemachines(app) -> Dict[str, dict]:
    """``codex_fields.json`` 的 ``statemachines`` 索引：``{skill_id: record}``。

    这是**唯一**能说明「技能内部怎么跑」的数据（525 条，覆盖有状态机的
    干员技能）。敌人技能没有对应条目——所以敌人侧的注解必须明说「实现
    不在解包数据里」，不能拿干员状态机去套。
    """
    try:
        raw = app._read_bundled_json("codex_fields.json") or {}
    except Exception:                                       # noqa: BLE001
        raw = {}
    out = {}
    for m in raw.get("statemachines") or []:
        if isinstance(m, dict) and m.get("skill_id"):
            out[str(m["skill_id"])] = m
    return out


def annotate_operator_skill(skill_id: str, level: dict,
                            tokens: Optional[Dict[str, dict]] = None,
                            state: Optional[dict] = None,
                            bb_counts: Optional[Dict[str, int]] = None) -> dict:
    """把 ``skill_table_full.json`` 的一个技能等级翻成结构注解。

    与敌人侧的区别：干员技能**有** ``statemachines``（生命周期状态机），
    所以可以如实给出「充能 → 可开启 → 技能中」的时长；但 ``prefabId``
    依然只是注册名，具体指令级实现同样不在解包数据里。
    """
    tokens = tokens or {}
    level = level or {}
    sp = level.get("spData") or {}
    bb_counts = bb_counts or {}
    out = {
        "prefab": str(level.get("prefabId") or ""),
        "prefab_desc": "技能逻辑类名（客户端注册名）。解包只有这个名字和"
                       "参数表，实现（状态机/行为树）不在解包数据里。",
        "bb": [],
        "timing": [],
        "notes": [],
        "undocumented": 0,
        "sp_notes": [],
        "instructions": [],
        "prefab_meaning": "",
    }
    # 与敌人侧同一套合成器：干员技能的 blackboard 也是「参数袋」，
    # 键名的行为语义一样能把它们排成执行顺序。额外好处是干员侧还有
    # statemachines 给生命周期，两者合起来才接近「具体指令」。
    try:
        from . import skill_instructions as _SI
        out["instructions"] = _SI.build_instructions(
            {"key": out["prefab"],
             "cooldown": sp.get("spCost"), "init": sp.get("initSp"),
             "sp_cost": 0,
             "blackboard": [
                 (it.get("key"), it.get("value"), it.get("valueStr"))
                 for it in (level.get("blackboard") or [])
                 if isinstance(it, dict)]},
            tokens,
            # 干员技能攒的是技力，不是冷却：键名与动词都要跟着换，
            # 否则界面上写「initCooldown」而原文里只有 spCost，对不上号。
            trig_keys="initSp / spCost", trig_word="开启")
        out["prefab_meaning"] = _SI.prefab_meaning(out["prefab"],
                                                   is_skill_id=True)
    except Exception:                                       # noqa: BLE001
        out["instructions"] = []
    for item in (level.get("blackboard") or []):
        if not isinstance(item, dict):
            continue
        k = str(item.get("key") or "")
        if not k:
            continue
        hit = lookup_token(k, tokens)
        row = {
            "key": k,
            "value": fmt_num(item.get("valueStr")
                             if item.get("valueStr") not in (None, "")
                             else item.get("value")),
            "desc": clean((hit or {}).get("desc") or ""),
            "category": clean((hit or {}).get("category") or ""),
            "documented": hit is not None,
            "count": bb_counts.get(k, 0),
            "alias": k.rpartition(".")[2] if "." in k else "",
        }
        if hit is None:
            out["undocumented"] += 1
        out["bb"].append(row)

    sp_type = sp.get("spType")
    try:
        sp_key = int(sp_type)
    except (TypeError, ValueError):
        sp_key = sp_type
    out["timing"] = [
        {"label": "技力消耗 spCost", "db": fmt_num(sp.get("spCost")),
         "prts": None,
         "note": SPTYPE_CN.get(sp_key, "未收录的 spType")},
        {"label": "初始技力 initSp", "db": fmt_num(sp.get("initSp")),
         "prts": None, "note": ""},
        {"label": "持续时间 duration", "db": fmt_num(level.get("duration")),
         "prts": None, "note": "0 表示瞬发/被动"},
        {"label": "充能上限 maxChargeTime",
         "db": fmt_num(sp.get("maxChargeTime")), "prts": None,
         "note": "1 表示不可蓄力"},
        {"label": "触发方式 skillType", "db": str(level.get("skillType") or ""),
         "prts": None,
         "note": SKILLTYPE_CN.get(str(level.get("skillType")), "")},
        {"label": "持续口径 durationType",
         "db": str(level.get("durationType") or ""), "prts": None,
         "note": DURTYPE_CN.get(str(level.get("durationType")), "")},
    ]
    if sp_key == 8:
        out["sp_notes"].append(
            "spType = 8（被动/无技力）：落地即生效，不存在充能与开启动作，"
            "spCost/initSp 恒为 0 属正常。")
    elif SPTYPE_CN.get(sp_key):
        out["sp_notes"].append("spType = %s：%s。"
                               % (fmt_num(sp_type), SPTYPE_CN[sp_key]))
    if state:
        out["sp_notes"].append(
            "生命周期见 codex_fields.json 的 statemachines：%s"
            % clean(state.get("desc") or ""))
        for st in (state.get("states") or [])[:6]:
            out["sp_notes"].append("· %s：%s（%s）" % (
                clean(st.get("state") or ""), clean(st.get("duration") or ""),
                clean(st.get("note") or "")))
        if state.get("impl"):
            out["sp_notes"].append("实现口径：%s" % clean(state["impl"]))
        if state.get("pitfall"):
            out["sp_notes"].append("易错点：%s" % clean(state["pitfall"]))
    elif out["instructions"]:
        # 有指令但没状态机：说明这条技能的技能 ID 不在 525 条 statemachines
        # 里（多为新技能或召唤物技能）。如实说明，别让人以为漏读。
        out["sp_notes"].append(
            "codex_fields.json 的 statemachines 里没有这条技能的生命周期记录，"
            "所以只给得出上面那串动作顺序，给不出充能/冷却分段。")
    return out
#: 干员技能 blackboard key 的全局出现次数缓存
_OPSKILL_BB_STATS: dict = {"key": None, "data": {}}


def load_operator_bb_counts(app) -> Dict[str, int]:
    """干员技能 blackboard key 的全局出现次数（扫 skill_table_full 全等级）。

    口径与 :func:`load_bb_counts` 分开：敌人库和干员技能表是两份数据，
    把两边的次数混成一个数会让「全库出现 N 次」变成没有意义的数字。
    """
    key = id(app)
    if _OPSKILL_BB_STATS["key"] == key:
        return _OPSKILL_BB_STATS["data"]
    counts: Dict[str, int] = {}
    try:
        from . import skilldata as SD
        full = SD.load_full() or {}
    except Exception:                                       # noqa: BLE001
        full = {}
    for _sid, entry in full.items():
        if not isinstance(entry, dict):
            continue
        for lv in (entry.get("levels") or []):
            for it in ((lv or {}).get("blackboard") or []):
                k = (it or {}).get("key")
                if k:
                    counts[str(k)] = counts.get(str(k), 0) + 1
    _OPSKILL_BB_STATS["key"] = key
    _OPSKILL_BB_STATS["data"] = counts
    return counts


def env(app, *, with_operator: bool = False) -> dict:
    """一次把注解要用到的索引备齐（供 UI 传进渲染器）。

    ``with_operator`` 打开时才扫干员技能表：那一步要遍历
    ``skill_table_full.json`` 的全部等级（四万多条 blackboard），在图鉴
    弹窗里根本用不到，跟着算会明显拖慢打开速度。
    """
    out = {"tokens": load_tokens(app), "fields": load_fields(app),
           "bb": load_bb_counts(app)}
    if with_operator:
        out["op_bb"] = load_operator_bb_counts(app)
        out["states"] = load_statemachines(app)
    return out


def annotate_block(block: dict, env_: Optional[dict] = None) -> dict:
    """给一个技能块算出结构注解（``block["code"]`` 为空则返回空 dict）。"""
    code = block.get("code")
    if not code:
        return {}
    env_ = env_ or {}
    return annotate_code(code, block.get("rec"), env_.get("tokens"),
                         env_.get("fields"), env_.get("bb"))


def annotation_lines(annot: dict, *, max_bb: int = 0,
                     show_count: bool = True) -> List[str]:
    """把结构注解排成「一行一句」的纯文本，供代码查看器/复制使用。

    ``max_bb`` 为 0 表示全列（代码查看器要能看到所有 key，这正是用户
    要的「按 key 查释义」）；给正数则截断（技能卡里空间有限）。

    查不到释义的 key **照原样列出**并标「暂无释义」，绝不省略——用户
    判断「解包版本有没有新参数」靠的就是这个列表完不完整。
    """
    if not annot:
        return []
    out: List[str] = []
    # ---- 指令序列放最前：用户打开「查看原代码」问的第一句是「这技能干啥」，
    # 先给动作顺序，再给参数释义，比让人先滚过一袋键值对找线索合理。
    insts = annot.get("instructions") or []
    if insts:
        meaning = annot.get("prefab_meaning") or ""
        out.append("技能指令（按解包数值反推的执行顺序，共 %d 步）："
                   % len(insts))
        if meaning:
            out.append("  · %s" % meaning)
        for it in insts:
            out.append("  %d. %s　[%s]" % (it["seq"], it["text"], it["key"]))
        out.append("  说明：解包只有行为类名 + 数值袋，没有客户端脚本；"
                   "以上顺序由键名的行为语义推出，每一步都可回溯到原键。")
        out.append("")
    prefab = annot.get("prefab") or ""
    if prefab:
        out.append("prefabKey / prefabId：%s" % prefab)
        if annot.get("prefab_desc"):
            out.append("  含义：%s" % annot["prefab_desc"])
        if annot.get("prefab_pitfall"):
            out.append("  注意：%s" % annot["prefab_pitfall"])
    bb = annot.get("bb") or []
    if bb:
        limit = max_bb if max_bb and max_bb > 0 else len(bb)
        out.append("blackboard 参数（%d 项，其中 %d 项暂无释义）："
                   % (len(bb), annot.get("undocumented") or 0))
        for row in bb[:limit]:
            head = "  %s = %s" % (row["key"], row["value"])
            if row.get("documented"):
                desc = row.get("desc") or ""
                cat = row.get("category") or ""
                out.append("%s    → %s%s" % (head, desc,
                                             ("　[%s]" % cat) if cat else ""))
            else:
                cnt = row.get("count") or 0
                tail = ("（同类技能中出现 %d 次）" % cnt) if (cnt and show_count) else ""
                alias = row.get("alias") or ""
                via = ("　按末段「%s」也没查到" % alias) if alias else ""
                out.append("%s    → 暂无释义%s%s" % (head, via, tail))
        if limit < len(bb):
            out.append("  …另有 %d 项未展开" % (len(bb) - limit))
    timing = annot.get("timing") or []
    if timing:
        out.append("时间参数与 PRTS 对照：")
        for row in timing:
            if row.get("prts") is not None:
                out.append("  %s = %s　PRTS = %s　%s"
                           % (row["label"], row["db"], row["prts"],
                              row.get("note") or ""))
            else:
                note = row.get("note") or ""
                out.append("  %s = %s%s"
                           % (row["label"], row["db"],
                              ("　" + note) if note else ""))
    for note in (annot.get("notes") or []) + (annot.get("sp_notes") or []):
        out.append("说明：%s" % note)
    return out


def skill_annotation(app, enemy_id: str, skills, talent=None) -> List[dict]:
    """给「查看原代码」弹窗准备敌人技能的**结构注解**。

    返回 ``[{"title": "技能 0 · DanceFire", "lines": [...]}, ...]``，
    每个技能一节、最后一个天赋参数节。

    ## 为什么不能给出「指令级实现」

    用户想看的是「这个技能在代码里到底怎么跑的」。解包数据里**没有**
    这个东西：``enemy_database.json`` 只有 ``prefabKey``（客户端注册的
    行为类名，如 ``DanceFire``）和一袋 ``blackboard`` 数值；敌人技能也
    没有 ``codex_fields.json`` 的 ``statemachines`` 条目（那 525 条全是
    干员技能）。真正的指令在客户端二进制里。

    所以这里只做能诚实做到的事：把每个 key 的中文释义查出来、查不到就
    明标「暂无释义」并给出全库出现次数（用户据此判断是不是新参数），
    再把 ``initCooldown``/``cooldown``/``spCost`` 与 PRTS 的「初始/消耗」
    逐项对账。**不编造**实现细节——编出来的假状态机比没有更坏。
    """
    tokens = load_tokens(app)
    fields = load_fields(app)
    bb_counts = load_bb_counts(app)
    prts = load_prts(app).get(str(enemy_id)) or []
    #: prefabKey -> PRTS 记录，用来把「初始/消耗」的 PRTS 侧真值填进对照
    by_code = {}
    for rec in prts:
        k = str(rec.get("code") or "")
        if k:
            by_code.setdefault(k, rec)

    sections: List[dict] = []
    for i, sk in enumerate(skills or []):
        if not isinstance(sk, dict):
            continue
        code = {
            "key": str(sk.get("prefabKey") or ""),
            "cooldown": sk.get("cooldown"),
            "init": sk.get("initCooldown"),
            "sp_cost": sk.get("spCost"),
            "blackboard": [(it.get("key"), it.get("value"), it.get("valueStr"))
                           for it in (sk.get("blackboard") or [])
                           if isinstance(it, dict) and it.get("key")],
            "raw": sk,
        }
        rec = by_code.get(code["key"])
        annot = annotate_code(code, rec, tokens, fields, bb_counts)
        lines = annotation_lines(annot)
        if not lines:
            lines = ["（这条技能没有 prefabKey，也没有 blackboard）"]
        if rec is None:
            lines.append("PRTS 敌人页没有钉到这条 prefabKey（置信度不足），"
                         "因此无法与 PRTS 的「初始 / 消耗」逐项对账；"
                         "数值以解包为准。")
        sections.append({
            "title": "技能 %d · %s" % (i, code["key"] or "（无 prefabKey）"),
            "lines": lines,
        })

    if talent:
        tl = []
        for it in talent:
            if not isinstance(it, dict):
                continue
            k = str(it.get("key") or "")
            if not k:
                continue
            hit = lookup_token(k, tokens)
            val = fmt_num(it.get("valueStr")
                          if it.get("valueStr") not in (None, "")
                          else it.get("value"))
            if hit:
                tl.append("%s = %s　→ %s" % (k, val,
                                             clean(hit.get("desc") or "")))
            else:
                cnt = bb_counts.get(k) or 0
                tl.append("%s = %s　→ 暂无释义%s"
                          % (k, val, ("　全库 %d 次" % cnt) if cnt else ""))
        if tl:
            sections.append({"title": "天赋参数 talentBlackboard",
                             "lines": tl})
    return sections


def skill_summary(blocks) -> str:
    """一行式技能摘要（给列表/导出用），PRTS 名字优先。"""
    names = [b.get("name") for b in (blocks or []) if b.get("name")]
    if not names:
        return "—"
    if len(names) <= 2:
        return "、".join(names)
    return "%s 等 %d 个" % (names[0], len(names))