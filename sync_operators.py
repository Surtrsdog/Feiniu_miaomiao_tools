# -*- coding: utf-8 -*-
"""同步 PRTS 全图鉴干员数据到本地缓存。

用法：
    python sync_operators.py              # 增量同步（只补缺失的）
    python sync_operators.py --all        # 全量重抓
    python sync_operators.py 克莱门莎 能天使   # 只抓指定干员作测试

固定 API（可写进其它脚本复用）
------------------------------
1) 列出全部干员页：
   https://prts.wiki/api.php?action=query&list=categorymembers
       &cmtitle=Category:干员&cmlimit=500&format=json&formatversion=2

2) 批量取 wikitext（一次 50 页，推荐）：
   https://prts.wiki/api.php?action=query&generator=categorymembers
       &gcmtitle=Category:干员&gcmlimit=50&gcmnamespace=0
       &prop=revisions&rvprop=content&rvslots=main
       &format=json&formatversion=2

3) 单页 wikitext：
   https://prts.wiki/api.php?action=parse&page=<干员名>&prop=wikitext
       &format=json&formatversion=2
"""
from __future__ import annotations

import io
import os
import sys
import time

# 只在「以脚本方式运行」时接管 stdout（控制台是 GBK，中文会崩）。
# 被 GUI import 时绝不能动 sys.stdout——冻结的 windowed 程序里它是 None
# 或 PyInstaller 的 NullWriter，包装会破坏调用方的输出流。
if __name__ == "__main__" and sys.stdout is not None:
    try:
        import io as _io

        if hasattr(sys.stdout, "buffer"):
            sys.stdout = _io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8",
                                           errors="replace")
    except (ValueError, AttributeError, OSError):
        pass

ROOT = os.path.dirname(os.path.abspath(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from akcalc.core import net                     # noqa: E402
from akcalc.core import prts_operator as PO    # noqa: E402
from akcalc.core import skills as SK           # noqa: E402
from akcalc.core.paths import Paths            # noqa: E402

BATCH = 50          # 每次请求的页数
RETRY_PAUSE = 2.0   # 失败重试间隔


def fetch_batch(cont=None):
    """批量取 50 页 wikitext，返回 (页面列表, 下一个 continue)。"""
    params = {
        "action": "query",
        "generator": "categorymembers",
        "gcmtitle": "Category:干员",
        "gcmlimit": str(BATCH),
        "gcmnamespace": "0",
        "prop": "revisions",
        "rvprop": "content",
        "rvslots": "main",
        "format": "json",
        "formatversion": "2",
    }
    if cont:
        params["gcmcontinue"] = cont
    url = net.build_query(PO.PRTS_API, params)
    d = net.fetch_json(url, timeout=120)
    pages = []
    for p in d.get("query", {}).get("pages", []):
        rev = (p.get("revisions") or [{}])[0]
        slots = rev.get("slots", {}).get("main", {})
        content = slots.get("content") or rev.get("content") or ""
        if p.get("title") and content:
            pages.append((p["title"], content))
    nxt = (d.get("continue") or {}).get("gcmcontinue")
    return pages, nxt


def main(argv):
    args = [a for a in argv[1:] if not a.startswith("-")]
    all_flag = "--all" in argv

    paths = Paths.default()
    paths.ensure()
    cache = PO.OperatorCache.load(paths.operators_cache)
    if all_flag:
        cache.data = {}
    print("缓存路径：%s" % paths.operators_cache)
    print("现有干员：%d 位" % len(cache.data))

    if args:
        # 只抓指定干员
        for name in args:
            try:
                wt = PO.fetch_wikitext(name)
                op = PO.parse_operator(name, wt)
                if op and op.phases:
                    op.skills = SK.parse_skills(wt, PO._find_template)
                    cache.put(name, op)
                    print("  OK   %-16s E%d  ★%d  %s"
                          % (name, op.max_elite, op.rarity, op.profession))
                else:
                    print("  SKIP %-16s 解析不出属性模板" % name)
            except Exception as e:
                print("  FAIL %-16s %s: %s" % (name, type(e).__name__, e))
        cache.save()
        print("已保存，共 %d 位" % len(cache.data))
        return 0

    # 增量模式下，若缓存已覆盖全图鉴且都带技能，直接返回，避免每次扫 463 页
    if not all_flag:
        try:
            names_now = PO.list_operator_names()
        except Exception:
            names_now = []
        if names_now:
            have = set(cache.data)
            want = set(names_now)
            missing = want - have
            # 注意：机器人/2 星等干员本来就没有技能模板，
            # 「无技能」不能当作缺失，否则短路永远不成立。
            if not missing:
                n_skill = sum(1 for d in cache.data.values() if d.get("skills"))
                print("已是最新：%d 位干员全部在缓存中（其中 %d 位有技能），无需同步"
                      % (len(have), n_skill))
                return 0
            print("待补充：缺 %d 位干员" % len(missing))

    # 全量 / 增量同步
    total_new = 0
    total_seen = 0
    cont = None
    page_no = 0
    t0 = time.time()
    while True:
        page_no += 1
        try:
            pages, cont = fetch_batch(cont)
        except Exception as e:
            print("  批次 %d 失败（%s），%.0fs 后重试…" % (page_no, e, RETRY_PAUSE))
            time.sleep(RETRY_PAUSE)
            try:
                pages, cont = fetch_batch(cont)
            except Exception as e2:
                print("  重试仍失败，跳过该批次：%s" % e2)
                pages, cont = [], None

        for title, wt in pages:
            total_seen += 1
            if not all_flag and title in cache.data:
                continue
            try:
                op = PO.parse_operator(title, wt)
            except Exception as e:
                print("  解析失败 %-16s %s" % (title, e))
                continue
            if not op or not op.phases:
                continue
            try:
                op.skills = SK.parse_skills(wt, PO._find_template)
            except Exception:
                op.skills = []
            cache.put(title, op)
            total_new += 1

        cache.save()   # 每批存一次，中断也不丢进度
        print("  批次 %-3d 累计 %4d/%d 页，新增 %4d，耗时 %.0fs"
              % (page_no, total_seen, len(cache.data), total_new, time.time() - t0))

        if not cont:
            break
        time.sleep(0.3)   # 轻量限速，避免给 PRTS 压力

    cache.save()
    print()
    print("完成：缓存共 %d 位干员（本次扫描 %d 页，新增 %d），用时 %.0fs"
          % (len(cache.data), total_seen, total_new, time.time() - t0))
    with_skills = sum(1 for d in cache.data.values() if d.get("skills"))
    print("其中带技能数据：%d 位" % with_skills)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))