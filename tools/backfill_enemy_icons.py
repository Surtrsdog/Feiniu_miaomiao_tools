# -*- coding: utf-8 -*-
"""批量补齐敌人头像：从 PRTS media 站下载「头像_敌人_<中文名>.png」。

用法（在 F:\mini api 下）：
    python tools/backfill_enemy_icons.py [--px 64] [--limit N]

读取 akcalc/data/enemy_names.json 里的全部中文名，跳过本地已有的
（akcalc/data/icons/enemy/<px>/<名>.png），并发下载缺失的，失败自动跳过。
PRTS media 有防盗链，复用 enemy_icons.py 的 fetch_icon（带完整浏览器头）。
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import threading

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from akcalc.core import enemy_icons as EI  # noqa: E402
from akcalc.core.paths import Paths  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--px", type=int, default=64)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--threads", type=int, default=8)
    args = ap.parse_args()

    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    paths = Paths(root)
    names_file = os.path.join(root, "akcalc", "data", "enemy_names.json")

    with open(names_file, "r", encoding="utf-8") as f:
        names = json.load(f)
    uniq = sorted(set(names.values()))

    todo = []
    for nm in uniq:
        p = EI.icon_path(paths, nm, args.px)
        if os.path.isfile(p):
            continue
        todo.append(nm)
    if args.limit:
        todo = todo[:args.limit]

    total = len(todo)
    print("待下载 %d 个（%d px）" % (total, args.px), flush=True)
    if not total:
        print("没有缺失的头像。")
        return 0

    done = [0]
    ok = [0]
    lock = threading.Lock()

    def worker():
        while True:
            with lock:
                if not todo:
                    break
                nm = todo.pop(0)
            im = EI.fetch_icon(nm, args.px, timeout=30.0)
            if im is not None:
                p = EI.icon_path(paths, nm, args.px)
                try:
                    os.makedirs(os.path.dirname(p), exist_ok=True)
                    with open(p, "wb") as f:
                        f.write(im)
                    ok[0] += 1
                except OSError:
                    pass
            with lock:
                done[0] += 1
                cur = done[0]
            if cur % 50 == 0 or cur == total:
                print("进度 %d/%d（成功 %d）" % (cur, total, ok[0]), flush=True)

    threads = [threading.Thread(target=worker, daemon=True)
               for _ in range(max(1, args.threads))]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    print("完成：成功 %d / %d" % (ok[0], total))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
