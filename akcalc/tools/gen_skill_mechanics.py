# -*- coding: utf-8 -*-
"""生成 skill_mechanics.json: 技能判定摘要 (精简, 供 MCP + Web 共用)

不把 28MB 的 buff_template_data 塞进项目，而是预先提炼成每技能一份摘要：
  - 触发了哪些模板、每个模板的关键事件
  - 目标筛选 / 叠加规则 / 生命期
  - 段数 / 倍率 / 目标数（从 blackboard 实际取值）
"""
import json, os, re, sys, collections
G = r"F:\arknights_gamedata\ArknightsGameData\zh_CN\gamedata"
OUT = r"F:\mini api\akcalc\data\skill_mechanics.json"

bt = json.load(open(os.path.join(G,"battle","buff_template_data.json"), encoding="utf-8"))
st = json.load(open(r"F:\mini api\akcalc\data\skill_table_full.json", encoding="utf-8"))
ct = json.load(open(os.path.join(G,"excel","character_table.json"), encoding="utf-8"))

FAM = collections.defaultdict(list)
for k in bt:
    FAM[re.sub(r"\[.*$", "", k)].append(k)
BBPAT = re.compile(r"^([a-z0-9]+_(?:s|t|e|tr|s\d+)[a-z0-9_]*?)(\[[^\]]*\])?\.\w+$")

def resolve(sid, lv):
    ks = set()
    for b in (lv.get("blackboard") or []):
        m = BBPAT.match(b.get("key") or "")
        if m:
            t = m.group(1)
            ks.update(FAM.get(t) or FAM.get(re.sub(r"\[.*$","",t)) or [])
    if ks: return "A", sorted(ks)
    m = re.match(r"^skchr_(.+?)_(\d+)$", sid)
    if m:
        x, n = m.group(1), m.group(2)
        for cand in (f"{x}_s_{n}", f"{x}_s{n}"):
            if cand in FAM: return "B", sorted(FAM[cand])
    return "D", []

def walk(o, out):
    if isinstance(o, dict):
        if o.get("$type"): out.append(o)
        for v in o.values(): walk(v, out)
    elif isinstance(o, list):
        for v in o: walk(v, out)
    return out

# 节点类型 -> 中文动作（只解释高频且有判定含义的）
ACT = {
 "CreateBuff":"挂载 buff", "FinishBuff":"移除 buff", "FinishBuffsById":"按 id 移除 buff",
 "IfElse":"条件分支", "IfNot":"条件取反", "AlwaysNext":"无条件继续",
 "CheckContainsBuff":"检查是否存在 buff", "FilterByBlackboardValue":"按黑盒值筛选",
 "SwitchMode":"切换模式", "CreateEffect":"生成特效", "TriggerAbility":"触发天赋/能力",
 "AOEDamage":"范围伤害", "AdvancedApplyDamage":"结算伤害", "FixedValueDamage":"固定值伤害",
 "DamageViaMaxHpRatio":"按生命上限比例伤害", "DamageScale":"伤害缩放",
 "BlockDamage":"伤害免疫/拦截", "NoSourceDamage":"无来源伤害",
 "AssignValueToBB":"写入黑盒值", "CalculateBlackboardValueViaParams":"计算黑盒值",
 "PlayAudio":"播放音效", "PlayAnimation":"播放动画", "MoveTo":"位移",
 "AddStun":"眩晕", "AddSlow":"减速", "AddSilence":"沉默",
}

def summarize(tk):
    tpl = bt.get(tk)
    if not tpl: return None
    nodes = []; walk(tpl, nodes)
    acts = []
    seen = set()
    for n in nodes:
        sh = n.get("$type","").split("+")[-1].split(",")[0]
        if sh in ACT and sh not in seen:
            seen.add(sh); acts.append(ACT[sh])
    # 目标筛选
    tgt = collections.Counter()
    for n in nodes:
        to = n.get("_targetOptions")
        if isinstance(to, dict):
            for k in ("targetSide","targetMotion","targetCategory","abnormalFlag"):
                v = to.get(k)
                if v not in (None, False, ""):
                    tgt["%s=%s" % (k,v)] += 1
    # 叠加 / 生命期
    stack = collections.Counter(); life = collections.Counter()
    for n in nodes:
        bf = n.get("_buff")
        if isinstance(bf, dict):
            if bf.get("overrideType"): stack[bf["overrideType"]] += 1
            if bf.get("lifeTimeType"): life[bf["lifeTimeType"]] += 1
    # 直接伤害倍率键
    scale_keys = set()
    for n in nodes:
        for f in ("_atkScaleKey","_atkScaleVar"):
            v = n.get(f)
            if isinstance(v,str) and v: scale_keys.add(v)
    return {
        "template": tk,
        "events": list((tpl.get("eventToActions") or {}).keys()),
        "actions": acts[:10],
        "node_types": len(nodes),
        "targets": dict(tgt.most_common(6)),
        "stack": dict(stack.most_common(4)),
        "life": dict(life.most_common(4)),
        "scale_keys": sorted(scale_keys),
    }

# 建立 char -> 技能 映射
out = {"meta": {}, "operators": {}, "skills": {}}
nA=nB=nD=0
for cid, c in ct.items():
    if not cid.startswith("char_"): continue
    sks = c.get("skills") or []
    if not sks: continue
    op = {"name": c.get("name"), "skills": []}
    for sk in sks:
        sid = sk.get("skillId")
        if not sid: continue
        e = st.get(sid)
        if not e: continue
        lv = (e.get("levels") or [{}])[-1]
        tier, tks = resolve(sid, lv)
        if tier=="A": nA+=1
        elif tier=="B": nB+=1
        else: nD+=1
        bb = {b["key"]: b["value"] for b in (lv.get("blackboard") or [])}
        tpls = [x for x in (summarize(t) for t in tks) if x]
        rec = {
            "skill_id": sid,
            "name": lv.get("name"),
            "tier": tier,
            "templates": tpls,
        }
        out["skills"][sid] = rec
        op["skills"].append({
            "skill_id": sid, "name": lv.get("name"), "tier": tier,
            "slots": len(tpls),
            "actions": sorted({a for t in tpls for a in t["actions"]})[:8],
        })
    out["operators"][cid] = op

out["meta"] = {
    "source": "gamedata/battle/buff_template_data.json + excel/skill_table.json",
    "client": "2.7.81",
    "templates_total": len(bt),
    "operators": len(out["operators"]),
    "skills": len(out["skills"]),
    "tier_A": nA, "tier_B": nB, "tier_D": nD,
    "note": ("tier A = blackboard 键名直接点名模板（最可靠）；"
             "tier B = 按 skchr_X_N -> X_s_N 命名规则推断；"
             "tier D = 无对应模板（多为纯数值强化技能）。"
             "技能与模板的官方绑定关系存放在加密资源包里，本地无法解出，"
             "此处为推导结果。"),
}
json.dump(out, open(OUT,"w",encoding="utf-8"), ensure_ascii=False, separators=(",",":"))
print("已写出 %s (%.2f MB)" % (OUT, os.path.getsize(OUT)/1048576))
print("干员 %d, 技能 %d | A=%d B=%d D=%d" % (len(out["operators"]), len(out["skills"]), nA,nB,nD))
