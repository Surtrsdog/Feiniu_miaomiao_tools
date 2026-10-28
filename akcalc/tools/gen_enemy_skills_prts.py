# -*- coding: utf-8 -*-
"""从 PRTS wiki 抓「敌人技能名 -> 冷却/初始」，生成 prefabKey 映射表。

## 为什么需要这个脚本

解包里 ``enemyData.skills[]`` 只有 ``prefabKey``（如 ``DragonFire``）和
``cooldown``/``initCooldown``，**没有中文名**；而中文名（日冕、烈焚灼息）
只存在于 ``enemy_handbook_table.json`` 的散文里，两份数据之间没有任何
id 互引。想可靠地把名字和代码对上，只能引入第三方权威数据。

PRTS 的敌人页 wikitext 正好补上这一环::

    |技能0=日冕
    |技能0初始=40
    |技能0消耗=40
    |技能0效果=对半径2.5范围内所有我方单位造成攻击力100%的法术普通伤害

字段语义要换算一下才对得上解包数据（这是本脚本的核心校正）：

* ``技能N初始`` == ``initCooldown``  —— 实测全部命中，是唯一的强锚点
* ``技能N消耗`` != ``spCost``（这里恒为 0），而是 **技能循环冷却**，
  对应 ``cooldown``
* PRTS 的「初始」在游戏内是「首次可释放时间」，即解包的 ``initCooldown``

配对策略（见 :func:`_match_level`）：
1. 取该敌人的**最高等级**记录（有技能的都是 L0，L1 只是数值覆盖）；
2. 按 **初始冷却** 做一对一贪心匹配；同初始值的多个候选用冷却打破平局；
3. 配不上的就留空，**绝不猜**。

输出 ``akcalc/data/enemy_skills_prts.json``::

    {"version": 1, "source": "...", "generated_at": "...",
     "skills": {"enemy_1503_talula": [
         {"index": 0, "name": "日冕", "init": 40.0, "cost": 40.0,
          "code": "DanceFire", "cooldown": 40.0, "confident": true}, ...]}}

用法::

    python akcalc/tools/gen_enemy_skills_prts.py            # 增量（有缓存就跳过）
    python akcalc/tools/gen_enemy_skills_prts.py --refresh  # 强制重抓
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = os.path.join(ROOT, "data", "cache")
DATA = os.path.join(ROOT, "data")
WIKI_CACHE = os.path.join(CACHE, "prts_enemy_wikitext")
OUT = os.path.join(DATA, "enemy_skills_prts.json")

API = "https://prts.wiki/api.php"
UA = "FeiNiuMiaoMiao/1.0 (akcalc enemy codex; contact via github)"

#: 敌人页常见命名后缀，按优先级依次尝试
PAGE_SUFFIXES = ("(敌方)", "", "/敌方", "(敌人)")

#: 任何 HTML 标签一律删掉。**上界必须足够宽**：PRTS 上带内联样式的
#: ``<span style="color:#fff;background:red;padding-inline:0.5em;
#: box-shadow:0 0 5px red;">`` 一个标签就有 84 个字符，旧版写成
#: ``{0,40}`` 直接漏掉，于是标签原文留在技能描述里显示给用户看
#: （``enemy_1587_ubbplwq`` 的「封锁区和平治理计划」就是这么脏的）。
#: 放宽到 300 且不允许跨 ``>``，不会误吞正文里的比较号。
_TAG_RE = re.compile(r"<[^>]{0,300}>")
_BR_RE = re.compile(r"<br\s*/?>", re.I)
#: wiki 内链：``[[结晶]]`` -> ``结晶``；``[[结晶|晶簇]]`` -> ``晶簇``
_WIKILINK_RE = re.compile(r"\[\[([^\[\]|]{0,60})(?:\|([^\[\]]{0,60}))?\]\]")
#: HTML 注释 ``<!--…-->`` 一律删掉（PRTS 上用来藏旧数值）
_HTML_COMMENT_RE = re.compile(r"<!--.*?-->", re.S)
#: 落单的竖线：``术语|ba.stun|晕眩``（半截模板残留）取最后一段当可见文本
_LONE_PIPE_RE = re.compile(
    r"[^|\s\[\]（）]{0,40}\|(?:[^|\s]{1,40}\|)*([^|\n]{0,60})")

#: 模板 → 显示文本。**逐条登记**，不做「统一取最后一段」的猜测：
#: 参数个数相同的模板取值位置并不一样（见下面 ``异常效果`` 与
#: ``变动数值lite``），猜错了界面上就会冒出「内容=」「原因=6」这种原文。
#:
#: 值是「取第几个参数」（第一个参数 = 1）。``异常效果|晕眩|免疫``
#: 在 PRTS 上渲染成「晕眩免疫」，两个都要，所以给 ``[1, 2]``。
_TPL_ARGSPEC = {
    # 术语：{{术语|ba.stun|晕眩}} -> 晕眩
    "术语": [3], "术语/custom": [2, 3],
    # 颜色：{{color|#FF4F0B|初始模式}} -> 初始模式
    "color": [3], "font": [2],
    # 状态：{{异常效果|自缚}} / {{异常效果|晕眩|免疫}} -> 自缚 / 晕眩免疫
    "异常效果": [2, 3], "特殊机制": [2], "技能类型": [2],
    # 数值变动：{{变动数值|900%|+}} -> 900%+ ；{{变动数值lite|down|蓝|说明}} -> 说明
    "变动数值": [2, 3], "变动数值lite": [4], "*": [2, 3], "**": [2, 3],
    "+": [2, 3],
    #: popup 的正文在具名参数 ``|内容=…`` 里，按「键名」取值
    "popup": ["内容"], "Popup": ["内容"], "_Popup": ["内容"],
    "popup/range": [2], "参阅": [3],
    #: 修正lite 只有第 2 段是位置参数，其余全是具名（原文=/原因=）
    "修正lite": [2], "修正": [2],
    # 纯样式 / 导航 / 资源模板：整段丢掉
    "Navigator": [], "敌人导航": [], "干员导航": [], "pathnav2": [],
    "spine": [], "spineId": [], "FULLPAGENAME": [], "#Widget:Mojibake": [],
    "mdi": [], "敌人头像": [], "材料消耗": [],
}
#: 没登记的模板统一走这条：保留最后一个不含 ``=`` 的参数；全带 ``=``
#: 就整段丢掉。模板名允许 ``#`` 开头（``{{#Widget:…}}``）与 ``/`` 结尾。
_TPL_ANY_RE = re.compile(r"\{\{([^{}|\n]{1,24}?)\s*(\|[^{}\n]*?)?\}\}")
_TPL_ARG_SPLIT = re.compile(r"\|")


def _tpl_render(name: str, body: str) -> str:
    """把一个模板替换成它在 PRTS 页面上的可见文本。

    ``_TPL_ARGSPEC`` 里既可以写位置序号（int，1 起），也可以写具名参数的
    键名（str）——``{{popup|内容=…}}`` 的正文只在 ``内容`` 这个具名参数里，
    按位置取会拿到空串。
    """
    name = (name or "").strip()
    parts = _TPL_ARG_SPLIT.split(body or "")
    spec = _TPL_ARGSPEC.get(name)
    if spec is not None:
        if not spec:
            return ""
        out = []
        for key in spec:
            if isinstance(key, str):
                for seg in parts:
                    if seg.startswith(key + "="):
                        out.append(seg[len(key) + 1:])
                        break
            elif key - 1 < len(parts):
                seg = parts[key - 1]
                if seg and "=" not in seg:
                    out.append(seg)
        return "".join(out)
    # 未登记：取最后一个「不带 = 的参数」
    for seg in reversed(parts):
        if seg and "=" not in seg:
            return seg
    return ""


def _clean(text: str) -> str:
    """去掉 wiki 标记，留纯文本。

    两个曾经把界面弄脏的坑：

    1. **顺序**。旧版先把 ``{{`` / ``}}`` 抹掉再跑正则，
       ``{{术语|ba.stun|晕眩}}`` 被拆成 ``术语|ba.stun|晕眩}}``，正则再也
       匹配不上，最后界面上出现「……可触发：术语」。
    2. **取值位置**。不同模板的显示文本不在同一个参数上，统一「取最后
       一段」会把 ``{{popup|内容=包含以下装置：…}}`` 变成 ``内容=…``、
       把 ``{{修正lite|※|原文=·|原因=6}}`` 变成 ``原因=6``。

    所以现在按模板名逐条登记（:data:`_TPL_ARGSPEC`），先渲染成可见文本，
    最后才清落单的花括号与竖线。
    """
    t = str(text or "")
    t = _HTML_COMMENT_RE.sub("", t)
    #: 先渲染模板、后转 ``<br>``：``_TPL_ANY_RE`` 不跨行，一旦提前把
    #: ``<br>`` 变成 ``\n``，正文里带换行的模板（``{{popup|内容=…<br>…}}``）
    #: 就整段匹配不上，最后只清出个 ``内容=成功0次`` 留在界面上。
    for _ in range(8):
        new = _TPL_ANY_RE.sub(lambda m: _tpl_render(m.group(1), m.group(2)), t)
        if new == t:
            break
        t = new
    t = _BR_RE.sub("\n", t)
    t = _TAG_RE.sub("", t)
    t = _WIKILINK_RE.sub(lambda m: (m.group(2) or m.group(1)), t)
    t = t.replace("'''", "").replace("''", "")
    # 命名空间链接（``[[:分类:xxx|显示]]``）：内链正则要求不带冒号，
    # 这类漏网的再兜一层——只留 ``|`` 后面的显示文本，没有就整段删。
    t = re.sub(r"\[\[:[^\[\]|]{0,80}(?:\|([^\[\]]{0,80}))?\]\]",
               lambda m: m.group(1) or "", t)
    t = t.replace("[[", "").replace("]]", "")
    # 没配对的模板残留（PRTS 上有 `{{污染` 这种断开的写法）：
    # 直接把花括号本身抹掉，比留个 `{{` 在界面上强。
    t = t.replace("{{", "").replace("}}", "")
    # 落单的竖线（半截模板被抹掉后常见）：`术语|ba.stun|晕眩` -> `晕眩`
    if "|" in t:
        t = _LONE_PIPE_RE.sub(lambda m: m.group(1) or "", t)
    return t.strip()


def _skill_name(raw: str) -> str:
    """技能名字段规整。

    PRTS 把「模式后缀」写在第二行，像::

        |技能0=消化<br>[消化模式]

    换行转成 ``\\n`` 之后要拼回去，否则界面上显示成两行、
    「[消化模式]」还会掉到下一行的开头。
    """
    t = _clean(raw)
    if not t:
        return ""
    lines = [ln.strip() for ln in t.split("\n") if ln.strip()]
    if not lines:
        return ""
    head = lines[0]
    for extra in lines[1:]:
        # 「[狂暴]」「[消化模式]」这类后缀直接贴着名字拼
        head += extra if extra.startswith("[") else (" " + extra)
    return head.strip()


def _wiki_get(params: dict, timeout: int = 45) -> dict:
    url = API + "?" + urllib.parse.urlencode(
        dict(params, format="json", formatversion="2"))
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as fh:
        return json.loads(fh.read().decode("utf-8"))


def _cache_path(title: str) -> str:
    """标题 -> 缓存文件路径。

    **不能**用「把非 ASCII 换成下划线」那套：中文标题会被整体压成
    一串 ``_``，几百个页面全撞到同一个文件上，缓存互相覆盖，
    表现为「明明抓到了页面，解析出来却是另一只敌人的技能」。
    这里用 标题的可读前缀 + 标题的哈希，保证唯一且便于人工排查。
    """
    import hashlib
    digest = hashlib.sha1(title.encode("utf-8")).hexdigest()[:12]
    prefix = re.sub(r"[^0-9A-Za-z_.\-]", "", title)[:24] or "page"
    return os.path.join(WIKI_CACHE, "%s_%s.txt" % (prefix, digest))


def fetch_pages(titles, refresh: bool = False) -> dict:
    """批量取页面 wikitext，结果按标题落到磁盘缓存。

    一次请求 50 页（MediaWiki 上限），中途 sleep 0.4s 避免打太快。
    返回 ``{requested_title: wikitext 或 ""}``。
    """
    os.makedirs(WIKI_CACHE, exist_ok=True)
    out, todo = {}, []
    for t in titles:
        p = _cache_path(t)
        if not refresh and os.path.isfile(p):
            try:
                with open(p, encoding="utf-8") as f:
                    out[t] = f.read()
                continue
            except OSError:
                pass
        todo.append((t, p))

    for i in range(0, len(todo), 50):
        chunk = todo[i:i + 50]
        got = {}
        try:
            d = _wiki_get({
                "action": "query", "prop": "revisions",
                "rvprop": "content", "rvslots": "main",
                "titles": "|".join(t for t, _ in chunk),
                "redirects": "1",
            })
        except Exception as e:                              # noqa: BLE001
            print("  批次 %d 请求失败: %s" % (i // 50 + 1, e))
            continue
        # 归一化：MediaWiki 会把请求名映射到规范名（重定向/空格差异）
        norm = {}
        for n in (d.get("query", {}).get("normalized") or []):
            norm[n.get("from") or ""] = n.get("to") or ""
        redir = {}
        for r in (d.get("query", {}).get("redirects") or []):
            redir[r.get("from") or ""] = r.get("to") or ""
        for page in (d.get("query", {}).get("pages") or []):
            title = page.get("title") or ""
            wt = ""
            if not page.get("missing"):
                revs = page.get("revisions") or [{}]
                wt = (revs[0].get("slots", {}).get("main", {})
                      .get("content") or "")
            got[title] = wt
        for want, path in chunk:
            key = want
            key = norm.get(key, key)
            key = redir.get(key, key)
            # 严格按规范名取。**不要**做「标题前缀相近就算命中」的宽松
            # 匹配：那会让「简饲源石虫」拿到「简饲源虫」的页面，
            # 结果解析出完全不相干的技能名，而且错得很隐蔽。
            wt = got.get(key, "")
            out[want] = wt
            try:
                with open(path, "w", encoding="utf-8") as f:
                    f.write(wt)
            except OSError:
                pass
        print("  批次 %d：%d 页，命中 %d" % (
            i // 50 + 1, len(chunk), sum(1 for t, _p in chunk if out.get(t))))
        time.sleep(0.4)
    return out


def _level0_block(wikitext: str) -> str:
    """截出 ``==级别0==`` 那一段。

    **必须按等级分开解析**。PRTS 的高等级段落会重写一遍技能表
    （有时只是改数值），如果整页一起正则，后出现的 ``技能0初始``
    会把 级别0 的值覆盖掉——表现为配不上任何代码，而且看起来像是
    「PRTS 数据缺失」，其实是自己读错了行。解包的 ``skills[]``
    对应的是 级别0，所以只认 级别0。
    """
    if not wikitext:
        return ""
    m = re.search(r"==\s*级别\s*0\s*==", wikitext)
    if not m:
        return wikitext          # 单等级页（大多数普通敌人）没有分节
    rest = wikitext[m.end():]
    nxt = re.search(r"==\s*[^=\n]{1,20}\s*==", rest)
    return rest[:nxt.start()] if nxt else rest


def parse_skills(wikitext: str) -> list:
    """从敌人页 wikitext 里抽出 ``技能N / 技能N初始 / 技能N消耗 / 技能N效果``。

    只读 级别0 那一段（见 :func:`_level0_block`），因为解包的
    ``enemyData.skills`` 就是按 级别0 给的。取不到名字就跳过该条
    ——名字是这条记录唯一有用的东西。
    """
    block = _level0_block(wikitext)
    if not block:
        return []
    found = {}
    #: 值部分**不能**用 ``[^\n|]*`` 拦：技能效果正文里带模板，
    #: ``{{术语|ba.stun|晕眩}}``、``{{color|#f00|红}}`` 里全是竖线，一拦就
    #: 只剩 ``{{术语``，后面的正文整段丢失 —— 这正是「可触发：术语」的来源。
    #: 真正的字段边界是「下一行以 ``|`` 开头且形如 ``|技能N…=``」，所以
    #: 值一直吃到下一个同类字段之前（用 lookahead 断句，允许跨行）。
    _FIELD = r"\|\s*技能(\d+)(初始|消耗|效果|名称)?\s*="
    pat = re.compile(
        _FIELD + r"([\s\S]*?)(?=" + _FIELD + r"|\n\s*\}\}|\n\s*\|[^\n=]{1,30}=|\Z)")
    for m in pat.finditer(block):
        idx = int(m.group(1))
        field = m.group(2) or "名称"
        val = m.group(3).strip()
        rec = found.setdefault(idx, {"index": idx})
        if field == "初始":
            rec["init"] = _num(val)
        elif field == "消耗":
            rec["cost"] = _num(val)
        elif field == "效果":
            rec["effect"] = _clean(val)
        else:
            rec["name"] = _skill_name(val)
    out = [r for r in found.values() if r.get("name")]
    out.sort(key=lambda r: r["index"])
    return out


def _num(text):
    try:
        return float(str(text).strip())
    except (TypeError, ValueError):
        return None


def _match_level(prts_skills, db_skills) -> list:
    """把 PRTS 的技能表和解包的同级 skills[] 对齐。

    唯一强锚点是 **初始冷却**，所以先按它一对一匹配；撞车时用冷却做
    平局决胜。配不上的留 ``code=""``，不猜。
    """
    pool = list(enumerate(db_skills))
    used = set()
    out = []
    for ps in prts_skills:
        want_init = ps.get("init")
        best, best_score = None, -1
        for i, sk in pool:
            if i in used:
                continue
            if want_init is None:
                continue
            try:
                got = float(sk.get("initCooldown"))
            except (TypeError, ValueError):
                continue
            score = 0
            if abs(got - want_init) < 1e-6:
                score += 10
            elif abs(got - want_init) <= 0.51:
                score += 6
            else:
                continue
            # 平局决胜：冷却
            want_cd = ps.get("cost")
            try:
                cd = float(sk.get("cooldown"))
            except (TypeError, ValueError):
                cd = None
            if want_cd is not None and cd is not None:
                if abs(cd - want_cd) < 1e-6:
                    score += 5
                elif abs(cd - want_cd) <= 0.51:
                    score += 3
            # 再拿效果里的关键词做弱校正
            eff = (ps.get("effect") or "")
            bb_keys = " ".join(str(b.get("key") or "").lower()
                               for b in (sk.get("blackboard") or []))
            for word, needle in (("持续", "duration"), ("半径", "range"),
                                 ("眩晕", "stun"), ("冻结", "freeze"),
                                 ("召唤", "summon"), ("攻击力", "atk_scale")):
                if word in eff and needle in bb_keys:
                    score += 2
            if score > best_score:
                best, best_score = i, score
        rec = dict(ps)
        if best is not None and best_score >= 10:
            used.add(best)
            sk = pool[best][1]
            rec["code"] = str(sk.get("prefabKey") or "")
            rec["cooldown"] = _num(sk.get("cooldown"))
            rec["confident"] = True
        else:
            rec["code"] = ""
            rec["cooldown"] = None
            rec["confident"] = False
        out.append(rec)

    # ---- 兜底：自动技能（PRTS 里「初始/消耗」写成 `/` 的）
    #
    # 这类技能没有冷却信息可锚。**不要**按顺序硬填——实测「消化/登场消化」
    # 这种和它同页的「储备能量/能量储备」之类的技能名顺序并不对应，
    # 按序填会把 32/36 的正确率打到 9/31。宁可留空，界面上就是没代码注解。
    return out
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--refresh", action="store_true", help="忽略缓存重新抓取")
    ap.add_argument("--limit", type=int, default=0, help="只处理前 N 个（调试）")
    args = ap.parse_args()

    hb_path = os.path.join(CACHE, "enemy_handbook_table.json")
    db_path = os.path.join(CACHE, "enemy_database.json")
    for p in (hb_path, db_path):
        if not os.path.isfile(p):
            print("缺少数据文件: %s" % p)
            return 2

    hb = json.load(open(hb_path, encoding="utf-8"))["enemyData"]
    db = json.load(open(db_path, encoding="utf-8"))["by_id"]

    # 处理**所有解包里带技能的敌人**，不只是关卡里出现过的。
    #
    # 一开始只扫关卡 ``enemyDbRefs``，理由是「图鉴打开的都是这些」——
    # 但那是错的：图鉴的敌人列表来自 ``enemy_handbook_table.json`` 全表，
    # 里面有一批只在活动/合约里出现过、主线缓存里查不到的敌人（曼弗雷德、
    # 「萨米的意志」、奎隆……）。按关卡取集合会把这些整批漏掉，
    # 表现为「明明 PRTS 上有技能表，表里却没有这只敌人」。
    targets = []
    for eid in sorted(db.keys()):
        recs = db.get(eid) or []
        if not any(((r.get("enemyData") or {}).get("skills") or [])
                   for r in recs):
            continue
        nm = str((hb.get(eid) or {}).get("name") or "").strip()
        if nm:
            targets.append((eid, nm))
    if args.limit:
        targets = targets[:args.limit]
    print("待处理：%d 个有技能的敌人（全量，不限于关卡内）" % len(targets))

    # 给每个敌人组一份候选页名
    titles = []
    for _eid, nm in targets:
        for suf in PAGE_SUFFIXES:
            titles.append(nm + suf)
    titles = list(dict.fromkeys(titles))
    print("候选页名 %d 个" % len(titles))

    pages = fetch_pages(titles, refresh=args.refresh)
    hit = sum(1 for t in titles if pages.get(t))
    print("抓到 wikitext：%d / %d" % (hit, len(titles)))

    skills_out = {}
    stat = {"enemy": 0, "code_total": 0, "code_ok": 0, "code_none": 0}
    for eid, nm in targets:
        wt = ""
        for suf in PAGE_SUFFIXES:
            wt = pages.get(nm + suf) or ""
            if wt:
                break
        if not wt:
            continue
        stat["enemy"] += 1
        prts = parse_skills(wt)
        if not prts:
            continue
        # 取技能最多的那条 level 记录
        best = None
        for r in (db.get(eid) or []):
            sk = (r.get("enemyData") or {}).get("skills") or []
            if best is None or len(sk) > len(best):
                best = sk
        if not best:
            continue
        matched = _match_level(prts, best)
        stat["code_total"] += len(matched)
        stat["code_ok"] += sum(1 for m in matched if m.get("code"))
        stat["code_none"] += sum(1 for m in matched if not m.get("code"))
        skills_out[eid] = matched

    payload = {
        "version": 1,
        "source": "PRTS 明日方舟中文 Wiki（敌人页 wikitext）",
        "source_url": "https://prts.wiki/",
        "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "note": ("技能中文名与初始/消耗来自 PRTS 敌人页；prefabKey 由 "
                 "初始冷却+冷却与解包 enemyData.skills 一一对应得到。"
                 "confident=false 表示没配上代码，界面上不给代码注解。"),
        "stats": stat,
        "skills": skills_out,
    }
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=1)

    print()
    print("写出 %s" % OUT)
    print("  敌人 %d 个 | 技能条目 %d 条 | 配上代码 %d（%.1f%%）| 未配上 %d" % (
        len(skills_out), stat["code_total"], stat["code_ok"],
        100.0 * stat["code_ok"] / max(stat["code_total"], 1), stat["code_none"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
