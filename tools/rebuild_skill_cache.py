# -*- mode: python ; coding: utf-8 -*-
"""重建 operators.json 里的技能数值。

背景
----
operators.json 里的 atk_multiplier / dmg_scale / hit_count 这些字段，
历史上是由 PRTS 页面文字的正则解析写进去的（prts_operator.py）。后来
装了官方 skill_table 的 blackboard 解析（skilldata.py），但缓存没重算，
导致「官方数据里的二连击、成功分支倍率」之类一直没生效。

这个脚本把每个技能等级的数值，按「描述正则 + 官方 blackboard 覆盖」
的完整流程重算一遍再写回，结果与首次全新同步完全一致。

用法
----
    python tools/rebuild_skill_cache.py            # 直接写回
    python tools/rebuild_skill_cache.py --dry-run  # 只看差异
"""
from __future__ import annotations

import argparse
import io
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from akcalc.core import skilldata as SD      # noqa: E402
from akcalc.core import skills as SK         # noqa: E402

CACHE = os.path.join(ROOT, 'akcalc', 'data', 'cache', 'operators.json')


def _entry_for(tbl, idx, op, skill):
    """按 char_id 拼技能 id 去找官方条目，找不到再按技能名找。"""
    for cand in SD.skill_ids(op.get('char_id') or ''):
        e = tbl.get(cand)
        if e and ((e.get('levels') or [{}])[0].get('name') == skill.get('name')):
            return e
    for sid in idx.get(skill.get('name', ''), []):
        return tbl[sid]
    return None


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--dry-run', action='store_true')
    args = ap.parse_args(argv)

    tbl = SD.load(SD.default_path())
    idx = SD.build_name_index(tbl)
    data = json.load(io.open(CACHE, encoding='utf-8'))
    ops = data['operators']
    print('技能表 %d 条 / 干员 %d 名' % (len(tbl), len(ops)))

    changed = 0
    suspicious = []
    for name, op in ops.items():
        for sk in (op.get('skills') or []):
            entry = _entry_for(tbl, idx, op, sk)
            if entry is None:
                continue
            for k, ld in (sk.get('levels') or {}).items():
                li = SD.LEVEL_INDEX.get(str(k), 9)
                lv = SK.parse_level(str(k), ld.get('description') or '',
                                    str(ld.get('duration') or ''), '', '')
                SK.apply_official(lv, entry, li)
                before = (ld.get('atk_multiplier'), ld.get('dmg_scale'),
                          ld.get('hit_count'), ld.get('interval_delta'))
                ld['atk_multiplier'] = lv.atk_multiplier
                ld['dmg_scale'] = lv.dmg_scale
                ld['hit_count'] = lv.hit_count
                ld['interval_delta'] = lv.interval_delta
                ld['attack_speed'] = lv.attack_speed
                ld['flat_atk'] = lv.flat_atk
                ld['extra'] = lv.extra
                after = (ld['atk_multiplier'], ld['dmg_scale'],
                         ld['hit_count'], ld['interval_delta'])
                if before != after:
                    changed += 1
                eff = ((ld['atk_multiplier'] or 1.0) *
                       (ld['dmg_scale'] or 1.0) *
                       (ld['hit_count'] or 1))
                if eff > 60.0:
                    suspicious.append((name, sk.get('name'), k, eff))

    print('数值变化 %d 项' % changed)
    if suspicious:
        print('倍率异常(>60x) %d 项，请人工核对:' % len(suspicious))
        for s in suspicious[:10]:
            print('   %-10s %-14s %s -> %.0fx' % s)
    if args.dry_run:
        print('(--dry-run，未写回)')
        return 0

    json.dump(data, io.open(CACHE, 'w', encoding='utf-8'),
              ensure_ascii=False, separators=(',', ':'))
    print('已写回 %s (%.2f MB)' % (CACHE, os.path.getsize(CACHE) / 1024 / 1024))
    return 0


if __name__ == '__main__':
    sys.exit(main())
