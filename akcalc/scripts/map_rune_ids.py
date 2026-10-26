# -*- coding: utf-8 -*-
"""Query all 30 crisis training-ground map pages for 关卡id, then match seasons."""
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
        raise RuntimeError("not found: %s" % page)
    return d["parse"]["wikitext"]

def level_id(page):
    wt = api(page)
    m = re.search(r"关卡id=(level_[A-Za-z0-9_\-]+)", wt)
    name = re.search(r"\|名称=([^|\n]+)", wt)
    return (m.group(1) if m else None), (name.group(1).strip() if name else page)

MAPS = [
    "龙门外环 荒芜广场", "龙门外环 无人危楼", "切尔诺伯格 59区废墟",
    "未知沙漠 荒漠", "龙门 新街", "龙门 中转站", "龙门外环 霜冻废墟",
    "切尔诺伯格 破碎大道", "荒野 黄铁峡谷", "龙门 军械库东",
    "切尔诺伯格 荒废工厂", "切尔诺伯格 6区废墟", "荒野 风蚀高地",
    "哥伦比亚 闭锁监狱", "荒野 无序矿区", "卡西米尔 八号竞技场",
    "切尔诺伯格 遗弃地块", "荒野 狂嚎沙原", "荒野 炽热溶洞",
    "炎国 灰齐山麓", "萨尔贡 沙海遗迹", "卡西米尔 大骑士领酒吧街",
    "炎国 尚蜀山道", "伊比利亚 盐风溶洞", "维多利亚 小丘郡物流站",
    "维多利亚 伦蒂尼姆边缘区块", "乌萨斯 冻原矿场", "玻利瓦尔 在建沙滩",
    "维多利亚 迷雾战区", "荒野 无名庇护所",
]

out = {}
for m in MAPS:
    try:
        rid, name = level_id(m)
        out[name] = rid
        print("%-28s -> %s" % (name, rid))
    except Exception as e:
        print("%-28s -> ERR %s" % (m, e))

json.dump(out, open(r"F:\mini api\.build\rune_name_id.json", "w", encoding="utf-8"),
          ensure_ascii=False, indent=2)