# -*- coding: utf-8 -*-
"""Build authoritative crisis-contract season -> rune map mapping from PRTS."""
import json
import re
import sys
import urllib.parse
import urllib.request

API = "https://prts.wiki/api.php"

def api(page):
    url = API + "?action=parse&prop=wikitext&format=json&formatversion=2&page=" + urllib.parse.quote(page)
    req = urllib.request.Request(url, headers={"User-Agent": "akcalc/1.0"})
    d = json.load(urllib.request.urlopen(req, timeout=60))
    if "error" in d:
        raise RuntimeError("page not found: %s" % page)
    return d["parse"]["wikitext"]

def parse_maps(wt):
    out = []
    for m in re.finditer(r"\{\{合约地图入口\|([^}]+?)\}\}", wt):
        body = m.group(1)
        region = re.search(r"区域=([^|\n]*)", body)
        loc = re.search(r"地点=([^|\n]*)", body)
        if region and loc:
            out.append((region.group(1).strip(), loc.group(1).strip()))
    return out

def map_rune_id(page):
    wt = api(page)
    m = re.search(r"level_(rune|crisis_v2)_[\w\-]+\.png", wt)
    if m:
        return m.group(0)[:-4]
    return None

SEASONS = [
    ("荒芜行动", 0), ("黄铁行动", 1), ("利刃行动", 2), ("燃灰行动", 3),
    ("铅封行动", 4), ("光谱行动", 5), ("蛮鳞行动", 6), ("松烟行动", 7),
    ("寻昼行动", 8), ("渊默行动", 9), ("尘环行动", 10), ("赝波行动", 11),
    ("起源行动", 12),
]

V2_SEASONS = [
    ("浊燃作战", 1), ("潮曦作战", 2), ("净罪作战", 3),
    ("弧光作战", 4), ("涤墨作战", 5),
]

def main():
    result = {"classic": {}, "v2": {}}
    for name, idx in SEASONS:
        page = "危机合约/" + name
        try:
            wt = api(page)
        except Exception as e:
            print("FAIL season", name, e, file=sys.stderr)
            continue
        maps = parse_maps(wt)
        if not maps:
            print("no maps", name, file=sys.stderr)
            continue
        region, loc = maps[0]
        mpage = region + " " + loc
        try:
            rid = map_rune_id(mpage)
        except Exception as e:
            rid = "ERR:" + str(e)
        result["classic"][name] = {"season_index": idx, "permanent": mpage, "rune_id": rid, "all_maps": maps}
        print(name, "->", mpage, "->", rid, file=sys.stderr)
    for name, idx in V2_SEASONS:
        page = "危机合约/" + name
        try:
            wt = api(page)
        except Exception as e:
            print("FAIL v2 season", name, e, file=sys.stderr)
            continue
        maps = parse_maps(wt)
        result["v2"][name] = {"season_index": idx, "all_maps": maps}
        print("V2", name, "->", maps, file=sys.stderr)
    print(json.dumps(result, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()