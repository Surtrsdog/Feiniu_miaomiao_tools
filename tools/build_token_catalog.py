# -*- coding: utf-8 -*-
"""从 character_table.json + skill_table.json 提取装置目录。"""
from __future__ import annotations
import json, os, sys, glob
from collections import OrderedDict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHAR_PATH = os.path.join(ROOT, "akcalc", "data", "cache", "character_table.json")
SKILL_PATH = os.path.join(ROOT, "akcalc", "data", "skill_table_full.json")
LEVELS_DIR = os.path.join(ROOT, "akcalc", "data", "cache", "levels")
OUT_PATH = os.path.join(ROOT, "akcalc", "data", "token_catalog.json")

def _load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def _is_token(cd):
    return cd.get("profession") in ("TOKEN", "TRAP")

def _get_attr(cd, name, default=0):
    try:
        phases = cd.get("phases") or []
        if not phases: return default
        attrs = phases[0].get("attributesKeyFrames") or []
        if not attrs: return default
        return attrs[0].get("data", {}).get(name, default)
    except: return default

def _get_skill(cd, skill_table):
    skills = cd.get("skills") or []
    if not skills: return (None, "")
    sid = skills[0].get("skillId")
    if not sid: return (None, "")
    sk = skill_table.get(sid)
    if not isinstance(sk, dict): return (sid, "")
    levels = sk.get("levels") or []
    if not levels: return (sid, "")
    return (sid, levels[0].get("description") or "")

def _classify(text, block_cnt):
    if "改变敌人" in text and "路线" in text: return ("A", True)
    if block_cnt > 0: return ("B", False)
    return ("C", False)

def _collect_inst_keys():
    """扫描全部关卡文件的 tokenInsts，收集实际出现的装置 key。"""
    keys = set()
    for f in glob.glob(os.path.join(LEVELS_DIR, "**", "*.json"), recursive=True):
        try:
            with open(f, "r", encoding="utf-8") as fh:
                d = json.load(fh)
            pre = d.get("predefines")
            if not isinstance(pre, dict):
                continue
            for it in (pre.get("tokenInsts") or []):
                if isinstance(it, dict):
                    k = (it.get("inst") or {}).get("characterKey")
                    if k:
                        keys.add(k)
        except Exception:
            pass
    return keys

def build():
    ct = _load_json(CHAR_PATH)
    st = _load_json(SKILL_PATH)
    inst_keys = _collect_inst_keys()
    tokens = OrderedDict()
    stats = {"A":0,"B":0,"C":0,"D":0}
    for key in sorted(inst_keys):
        cd = ct.get(key)
        if cd is None:
            # 未知 key → D 类
            stats["D"] += 1
            tokens[key] = OrderedDict([
                ("name",key),("category","D"),("affects_route",False),
                ("block_cnt",0),("max_hp",0),("def",0),
                ("magic_resist",0.0),("operable",False),
                ("skill_id",None),("skill_text","")])
            continue
        name = cd.get("name") or key
        bc = int(_get_attr(cd, "blockCnt", 0) or 0)
        hp = int(_get_attr(cd, "maxHp", 0) or 0)
        df = int(_get_attr(cd, "def", 0) or 0)
        mr = float(_get_attr(cd, "magicResistance", 0.0) or 0.0)
        sid, text = _get_skill(cd, st)
        cat, ar = _classify(text, bc)
        stats[cat] += 1
        tokens[key] = OrderedDict([
            ("name",name),("category",cat),("affects_route",ar),
            ("block_cnt",bc),("max_hp",hp),("def",df),
            ("magic_resist",mr),("operable",False),
            ("skill_id",sid),("skill_text",text)])
    return OrderedDict([
        ("version",1),
        ("generated_from","character_table.json + skill_table_full.json + level tokenInsts"),
        ("stats",OrderedDict([("A",stats["A"]),("B",stats["B"]),
            ("C",stats["C"]),("D",stats["D"]),("total",sum(stats.values()))])),
        ("tokens",tokens)])

def main():
    r = build()
    a_keys = sorted(k for k,v in r["tokens"].items() if v["category"]=="A")
    print("A 类 (%d):" % len(a_keys))
    for k in a_keys: print("  %s: %s" % (k, r["tokens"][k]["name"]))
    for c in ("A","B","C","D"): print("  %s: %d" % (c, r["stats"][c]))
    print("  total:", r["stats"]["total"])
    with open(OUT_PATH,"w",encoding="utf-8") as f:
        f.write(json.dumps(r,ensure_ascii=False,indent=2))
    sz = os.path.getsize(OUT_PATH)
    print("Output: %s (%.1f KB)" % (OUT_PATH, sz/1024))
    assert sz < 100*1024, "file too large: %d" % sz
    print("OK < 100 KB")

if __name__ == "__main__": main()
