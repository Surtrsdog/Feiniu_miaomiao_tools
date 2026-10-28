# -*- coding: utf-8 -*-
"""伤害计算层全量回归：混伤分类型 / 模组 / 0抗基准 / 法穿被动 / 召唤物。

只在无头 Tk 里跑，不打开窗口、不改数据、不联网。
用法: PYTHONPATH='F:\mini api' python test_full_regression.py
"""
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import json
import os
import re
import tkinter as tk

import akcalc.ui.app as APP
from akcalc.core import prts_operator as PO
from akcalc.core import talents as TAL

FAIL = []
OK = []


def check(name, cond, detail=""):
    if cond:
        OK.append(name)
        print("  [OK]   %s %s" % (name, detail))
    else:
        FAIL.append(name)
        print("  [FAIL] %s %s" % (name, detail))


class Harness:
    def __init__(self):
        self.root = tk.Tk()
        self.root.withdraw()
        self.app = APP.App()
        self.app.withdraw()
        self.dp = self.app.damage_panel
        self.rows = []
        orig = self.dp._set_metrics

        def cap(r):
            self.rows.clear()
            self.rows.extend(r)
            orig(r)

        self.dp._set_metrics = cap

    def op(self, name):
        for cid, d in self.app.op_cache.data.items():
            if d.get("name") == name:
                return PO.dict_to_op(d)
        return None

    def pick(self, name, skill_label=None):
        op = self.op(name)
        if op is None:
            return False
        self.dp.set_operator(op)
        self.root.update_idletasks()
        if skill_label is not None:
            self.dp.var_skill.set(skill_label)
            self.dp._on_skill_change()
        else:
            self.dp.recompute()
        self.root.update_idletasks()
        return True

    def get(self, key):
        for k, v in self.rows:
            if k == key:
                return v
        return None

    def skills(self):
        return list(self.dp.cmb_skill.cget("values"))

    def series(self):
        ch = self.dp._chart
        return [s.name for s in (ch.series if ch else [])]

    def close(self):
        try:
            self.root.destroy()
        except Exception:
            pass


def num(s):
    try:
        return float(str(s).replace(",", "").replace("s", "").strip())
    except (TypeError, ValueError):
        return None


h = Harness()

# ---------------------------------------------------------------- 1. 混伤分类型
print("\n[1] 混伤必须按类型分别计算")
for name, kw in (("号角", "暴风号令"), ("瑕光", "先贤化身")):
    labels = [s for s in h.skills() if kw in s]
    if not labels:
        h.pick(name, None)
        labels = [s for s in h.skills() if kw in s]
    if not labels:
        check("%s 技能 %s 存在" % (name, kw), False, str(h.skills()[:6]))
        continue
    h.pick(name, labels[0])
    t = h.get("伤害类型") or ""
    check("%s 识别为混伤" % name, "混伤" in t, t)
    phys = num(h.get("物理伤害 DPS"))
    mag = num(h.get("法术伤害 DPS"))
    check("%s 有物理 DPS 行" % name, phys is not None, str(phys))
    check("%s 有法术 DPS 行" % name, mag is not None, str(mag))
    tot = num(h.get("DPS"))
    if tot and phys is not None and mag is not None:
        check("%s 分类型之和 == 总 DPS" % name,
              abs(phys + mag - tot) < 1.5,
              "%.1f + %.1f vs %.1f" % (phys, mag, tot))
    ser = h.series()
    check("%s 图中含物理分量线" % name, "物理伤害" in ser, str(ser))
    check("%s 图中含法术分量线" % name, "法术伤害" in ser, str(ser))
    check("%s 图中含总量线" % name, "总量" in ser, str(ser))

# ---------------------------------------------------------------- 2. 模组
print("\n[2] 模组属性要能选上并计入")
h.pick("史尔特尔", None)
mods = [m for m in h.dp.cmb_module.cget("values") if m != "无模组"]
check("史尔特尔 有可选模组", len(mods) >= 1, "%d 个" % len(mods))
if mods:
    a_off = num(h.get("单次伤害"))
    h.dp.var_module.set(mods[0])
    h.dp.var_module_lv.set("3")
    h.dp.recompute()
    h.root.update_idletasks()
    a_on = num(h.get("单次伤害"))
    check("选模组后伤害变化", a_off is not None and a_on is not None
          and abs(a_on - a_off) > 0.5,
          "%.1f -> %.1f" % (a_off or 0, a_on or 0))
    h.dp.var_module.set("无模组")
    h.dp.recompute()
    h.root.update_idletasks()

# ---------------------------------------------------------------- 3. 0 抗基准
print("\n[3] 面板 DPH/DPS 为 0 防御 / 0 法抗基准")
h.pick("银灰", None)
labels = [s for s in h.skills() if "真银斩" in s]
if labels:
    h.pick("银灰", labels[0])
base_dph = num(h.get("DPH（每次攻击总伤害）"))
base_dps = num(h.get("DPS"))
h.dp.e_def.var.set("1500")
h.dp.e_res.var.set("60")
h.dp.recompute()
h.root.update_idletasks()
after_dph = num(h.get("DPH（每次攻击总伤害）"))
after_dps = num(h.get("DPS"))
check("目标防御/法抗改变后 面板 DPH 不变",
      base_dph is not None and after_dph is not None
      and abs(after_dph - base_dph) < 0.01,
      "%s -> %s" % (base_dph, after_dph))
check("目标防御/法抗改变后 面板 DPS 不变",
      base_dps is not None and after_dps is not None
      and abs(after_dps - base_dps) < 0.01,
      "%s -> %s" % (base_dps, after_dps))
h.dp.e_def.var.set("200")
h.dp.e_res.var.set("0")
h.dp.recompute()
h.root.update_idletasks()

# ---------------------------------------------------------------- 4. 法穿被动
print("\n[4] 法术穿透天赋被动要算进去")
op = h.op("史尔特尔")
tp = TAL.passives_of(op)
check("史尔特尔 天赋解析出法穿", tp.res_pen_flat > 0,
      "res_pen_flat=%.0f" % tp.res_pen_flat)
p2 = TAL.passives_of(h.op("迷迭香"))
check("迷迭香 天赋解析出物穿", p2.def_pen_flat > 0,
      "def_pen_flat=%.0f" % p2.def_pen_flat)
p3 = TAL.passives_of(h.op("银灰"))
check("银灰 无穿透被动", p3.res_pen_flat == 0 and p3.def_pen_flat == 0,
      "res=%.0f def=%.0f" % (p3.res_pen_flat, p3.def_pen_flat))
# 面板数值要真的受法穿影响：史尔特尔打高法抗目标
h.pick("史尔特尔", None)
labels = [s for s in h.skills() if "黄昏" in s]
if labels:
    h.pick("史尔特尔", labels[0])
    h.dp.e_res.var.set("60")
    h.dp.recompute()
    h.root.update_idletasks()
    eff = num(h.get("有效抗性"))
    check("史尔特尔 有效法抗 < 目标法抗（法穿生效）",
          eff is not None and eff < 60.0, "有效=%s" % eff)
    h.dp.e_res.var.set("0")
    h.dp.recompute()
    h.root.update_idletasks()

# ---------------------------------------------------------------- 5. 召唤物
print("\n[5] 召唤物要计入伤害")
h.pick("令", None)
labels = [s for s in h.skills() if "宁作吾" in s]
if labels:
    h.pick("令", labels[0])
check("令 S3 自动选中弦惊", "弦惊" in (h.dp.var_summon.get() or ""),
      h.dp.var_summon.get())
sd = num(h.get("召唤物 “弦惊” DPS"))
check("弦惊 DPS 行存在", sd is not None and sd > 500, str(sd))
tot = num(h.get("DPS"))
own = num(h.get("本体 DPS"))
check("本体 + 召唤物 == 总 DPS",
      tot is not None and own is not None and sd is not None
      and abs((own + sd) - tot) < 1.5,
      "%.1f + %.1f vs %.1f" % (own or 0, sd or 0, tot or 0))
ser = h.series()
check("图中含召唤物曲线", any("召唤物" in s for s in ser), str(ser))
check("图中含合计曲线", any("本体 + 召唤物" in s for s in ser), str(ser))

# ------------------------------------------------- 5b. 穿透要看得见（- 用户反馈）
print("\n[5b] 穿透必须看得见：面板要明确写出减了多少")
h.pick("史尔特尔", None)
labels = [s for s in h.skills() if "黄昏" in s]
if labels:
    h.pick("史尔特尔", labels[0])
    # 法抗 0：穿透无收益，不该刷提示
    h.dp.e_res.var.set("0")
    h.dp.recompute()
    h.root.update_idletasks()
    d0 = "0"
    check("法抗 0 时不显示无意义的穿透提示", h.get("穿透") is None, d0)
    # 法抗 60：要有提示，且按目标实算的伤害要真的降下来
    h.dp.e_res.var.set("60")
    h.dp.recompute()
    h.root.update_idletasks()
    note = h.get("穿透") or ""
    check("史尔特尔 法穿提示出现", "法术穿透" in note, note[:70])
    check("穿透提示写明无视 26 点", "26" in note, note[:70])
    live = h.get("按目标实算")
    check("有「按目标实算」行", live is not None, str(live))
    # 穿透收益必须为正：有效法抗 60-26=34
    check("有效法抗 = 34（60 - 26）", num(h.get("有效抗性")) == 34.0,
          str(h.get("有效抗性")))
    # 穿透后的实算值应低于 0 抗基准（说明目标抗性真的起作用了）
    _live_n = num(str(live).split("（")[0])
    check("调目标法抗后，面板单次不变（0 抗基准）但实算会变",
          _live_n is not None and abs(_live_n - num(h.get("单次伤害"))) > 1.0,
          "实算 %s vs 基准 %s" % (_live_n, h.get("单次伤害")))
    h.dp.e_res.var.set("0")
    h.dp.recompute()
    h.root.update_idletasks()

# 穿透提示不得出现负数伤害（打不穿防御时曾写出 -52）
h.pick("迷迭香", None)
for dfn in ("800", "1200"):
    h.dp.e_def.var.set(dfn)
    h.dp.recompute()
    h.root.update_idletasks()
    note = h.get("穿透") or ""
    # 提示里出现 "->" 是正常的，要查的是有没有 " -数字" 这种负伤害
    check("迷迭香 防御 %s 时穿透提示无负数" % dfn,
          " -" not in note.replace(" -> ", " "), note[:70])
h.dp.e_def.var.set("200")
h.dp.recompute()
h.root.update_idletasks()

for kw, expect in (("重进酒", "清平"), ("笑鸣瑟", "逍遥")):
    labels = [s for s in h.skills() if kw in s]
    if labels:
        h.dp.var_skill.set(labels[0])
        h.dp._on_skill_change()
        h.root.update_idletasks()
        check("令 %s 自动换到 %s" % (kw, expect),
              expect in (h.dp.var_summon.get() or ""), h.dp.var_summon.get())

h.pick("凯尔希", None)
labels = [s for s in h.skills() if "熔毁" in s]
if labels:
    h.pick("凯尔希", labels[0])
    check("凯尔希 有 Mon3tr 时保留 DPS",
          h.get("DPS") not in (None, "—（医疗干员）"), str(h.get("DPS")))
    check("凯尔希 显示 Mon3tr DPS",
          num(h.get("召唤物 Mon3tr DPS")) is not None,
          str(h.get("召唤物 Mon3tr DPS")))

h.pick("闪灵", None)
labels = [s for s in h.skills() if "教条" in s]
if labels:
    h.pick("闪灵", labels[0])
    check("闪灵 仍是医疗（DPS 显示 —）",
          h.get("DPS") == "—（医疗干员）", str(h.get("DPS")))

h.pick("银灰", None)
check("银灰 无召唤物行", h.get("召唤物占总量") is None, "")
check("银灰 召唤物下拉只有不计入",
      len(h.dp.cmb_summon.cget("values")) == 1,
      str(h.dp.cmb_summon.cget("values")))

# ---------------------------------------------------------------- 6. 类型细分
print("\n[6] 不能把全部技能笼统当成单一物理/法术")
seen = []
for name in ("号角", "瑕光", "史尔特尔", "银灰", "艾雅法拉", "能天使"):
    if h.op(name) is None:
        continue
    h.pick(name, None)
    for lbl in h.skills()[1:]:
        h.dp.var_skill.set(lbl)
        h.dp._on_skill_change()
        h.root.update_idletasks()
        seen.append((name, str(h.get("伤害类型"))))
mixed = [x for x in seen if "混伤" in x[1]]
check("检出混伤技能（不止单一类型）", len(mixed) >= 1, str(mixed[:4]))
kinds = set(x[1] for x in seen)
check("不同类型都出现过", len(kinds) >= 2, str(kinds))

h.close()

# ------------------------------------------------ 7. 粗轴导出/导入不丢阻挡信息
print("\n[7] 粗轴 JSON 往返必须保住 is_ranged / block_count")
# 这两个字段决定 Deployment.blocking：远程位恒为 0。曾经漏了序列化，
# 导致导出的粗轴换台机器打开时高台干员被当成地面干员去挡路。
from akcalc.core import sandbox_track as SBX

_g = SBX.CoarseTrack()
_g.stage_id = "check"
_g.add(SBX.Deployment(uid=0, row=1, col=9, name="银灰", ground="LOW",
                      block_count=2, is_ranged=False))
_g.add(SBX.Deployment(uid=0, row=1, col=5, name="W", ground="HIGH",
                      block_count=1, is_ranged=True))
_g.add(SBX.Deployment(uid=0, row=2, col=2, name="飞行阻挡", ground="LOW",
                      block_count=1, is_ranged=False, can_block_fly=True))
_txt = _g.dumps()
_g2 = SBX.CoarseTrack.loads(_txt)
_by = {d.name: d for d in _g2.all()}
check("往返条数一致", len(_g2.all()) == 3, "%d 条" % len(_g2.all()))
check("高台干员 is_ranged 保住", _by["W"].is_ranged is True,
      "is_ranged=%s" % _by["W"].is_ranged)
check("高台干员 blocking 仍为 0", _by["W"].blocking == 0,
      "blocking=%d" % _by["W"].blocking)
check("地面干员阻挡数保住", _by["银灰"].blocking == 2,
      "blocking=%d" % _by["银灰"].blocking)
check("block_fly 保住", _by["飞行阻挡"].can_block_fly is True)
check("再次导出字节一致", _g2.dumps() == _txt)

# 老版本 JSON（没有 ranged / block 键）要按 ground 兜底，不能一律当近战
_old = SBX._deployment_from_dict(
    {"uid": 1, "t": 0, "row": 1, "col": 5, "ground": "HIGH", "name": "W"})
check("旧 JSON 按 ground 推断为远程位", _old.is_ranged is True,
      "is_ranged=%s" % _old.is_ranged)

# ------------------------------------ 8. 源代码栏必须是「指令」不是「描述 JSON」
print("\n[8] 源代码栏要给出技能指令，而不是只罗列描述 JSON")
# 用户的原话是「源代码栏显示技能实现的具体指令而非描述 JSON」。解包里
# 没有客户端脚本，能给的最近似物是：把 blackboard 的键名按行为语义排成
# 执行顺序（触发 → 选目标 → 生效 → 计时）。这一组锁死它确实在产出指令。
from akcalc.core import skill_instructions as SI
from akcalc.core import enemy_skills as ES

check("prefabKey 形态后缀要拆开", SI.parse_prefab("Immo[Rage]")[:2]
      == ("Immo", "Rage"), "%s" % (SI.parse_prefab("Immo[Rage]")[:2],))
check("prefabKey 能给出中文行为类",
      "灼烧" in SI.parse_prefab("Immo[Rage]")[2],
      SI.parse_prefab("Immo[Rage]")[2])
check("无 prefabKey 时如实说明", "没有 prefabKey" in SI.prefab_meaning(""))

_code = {"key": "throwspear[Rage]", "cooldown": 20.0, "init": 15.0,
         "sp_cost": 0,
         "blackboard": [("atk_scale", 1.35, None), ("duration", 8.0, None)]}
_inst = SI.build_instructions(_code)
check("指令能合成出来", len(_inst) >= 2, "%d 步" % len(_inst))
check("指令按执行顺序排（触发在生效前）",
      _inst[0]["slot"] == "trigger" and _inst[-1]["slot"] == "duration",
      "%s ... %s" % (_inst[0]["slot"], _inst[-1]["slot"]))
check("每一步都能回溯到原始键名",
      all(it.get("key") for it in _inst), "%d 步均有 key" % len(_inst))
check("指令文本带出真实数值",
      any("1.35" in it["text"] for it in _inst),
      str([it["text"] for it in _inst]))

# 无冷却不能写成「每 0 秒一次」这种废话
_z = SI.build_instructions({"key": "Devour", "cooldown": 0, "init": 0,
                            "sp_cost": 0, "blackboard": []})
check("cooldown=0 不说成「每 0 秒一次」",
      _z and "无冷却" in _z[0]["text"], _z[0]["text"] if _z else "空")

# annotate_code 必须把指令挂上去，且 annotation_lines 把它排在参数表之前
_a = ES.annotate_code(_code, None, {}, {}, {})
check("annotate_code 带 instructions",
      bool(_a.get("instructions")), "steps=%d" % len(_a.get("instructions") or []))
_lines = ES.annotation_lines(_a)
_i_pos = next((i for i, s in enumerate(_lines) if "技能指令" in s), -1)
_b_pos = next((i for i, s in enumerate(_lines) if "blackboard 参数" in s), -1)
check("指令栏排在参数表之前", _i_pos >= 0 and _b_pos > _i_pos,
      "指令@%d 参数@%d" % (_i_pos, _b_pos))
check("指令栏说明数据边界（不谎称有客户端脚本）",
      any("没有客户端脚本" in s for s in _lines))

# 干员侧口径不同：攒的是技力不是冷却，键名与单位都必须跟着换
_oc = {"key": "skchr_skadi2_3", "cooldown": 35.0, "init": 15.0,
       "sp_cost": 0, "blackboard": [("atk_scale", 0.7, None)]}
_oi = SI.build_instructions(_oc, {}, trig_keys="initSp / spCost", trig_word="开启")
check("干员侧触发键名用技力口径",
      _oi and "spCost" in _oi[0]["key"], _oi[0]["key"] if _oi else "空")
check("干员侧不说「第 15 秒」（技力不是时间）",
      _oi and "点技力" in _oi[0]["text"] and "秒" not in _oi[0]["text"],
      _oi[0]["text"] if _oi else "空")
check("干员侧动词是「开启」",
      _oi and "开启" in _oi[0]["text"], _oi[0]["text"] if _oi else "空")
check("干员 prefabId 不当行为类名解析",
      "技能 ID 本身" in SI.prefab_meaning("skchr_skadi2_3", is_skill_id=True))

# ------------------------------- 9. 粗轴导出必须保住技能回转参数（否则回转失效）
print("\n[9] 粗轴导出必须保住技能回转参数（否则悬停回转全是「可开启」）")
# 只存技能名字的话，导入侧重建出 sp_cost=0 —— SkillCycle.is_passive 为真，
# state_at 永远返回 ready=True，正好把「悬停干员显示技能回转」废掉。
_sk = SBX.SkillCycle(sp_cost=35.0, init_sp=15.0, duration=20.0,
                     recover=SBX.SP_AUTO, infer_attack=True)
_g3 = SBX.CoarseTrack()
_g3.stage_id = "skillcheck"
_g3.add(SBX.Deployment(uid=0, row=1, col=9, name="银灰", skill=_sk,
                       skill_name="真银斩"))
_t3 = _g3.dumps()
check("导出 JSON 带 skill_sp 数值", '"skill_sp"' in _t3)
_g4 = SBX.CoarseTrack.loads(_t3)
_d4 = _g4.all()[0]
check("导入后 sp_cost 保住", _d4.skill.sp_cost == 35.0,
      "sp_cost=%s" % _d4.skill.sp_cost)
check("导入后 init_sp / duration 保住",
      _d4.skill.init_sp == 15.0 and _d4.skill.duration == 20.0,
      "init=%s dur=%s" % (_d4.skill.init_sp, _d4.skill.duration))
check("导入后 recover / infer_attack 保住",
      _d4.skill.recover == SBX.SP_AUTO and _d4.skill.infer_attack is True,
      "recover=%s infer=%s" % (_d4.skill.recover, _d4.skill.infer_attack))
check("导入后不再被当成被动技能", _d4.skill.is_passive is False)
check("导入后技能名仍在", _d4.skill_name == "真银斩", _d4.skill_name)
_sim = SBX.SkillSim(1.0)
_at20 = _sim.state_at(_d4.skill, 20.0, 0.0)
_at60 = _sim.state_at(_d4.skill, 60.0, 0.0)
check("回转真的能推进（t=20 已充满）", _at20.get("ready") is True,
      "ready=%s sp=%s" % (_at20.get("ready"), _at20.get("sp")))
check("回转真的能推进（t=60 已消耗并重攒）",
      _at60.get("ready") is False and _at60.get("cycle_index", 0) >= 1,
      "ready=%s idx=%s next_in=%s" % (_at60.get("ready"),
                                      _at60.get("cycle_index"),
                                      _at60.get("next_in")))
check("技能参数往返字节一致", _g4.dumps() == _t3)
# 没有 skill_sp 的老文件要能读，且行为退回「视为被动」而不是报错
_old2 = SBX._deployment_from_dict(
    {"uid": 1, "t": 0, "row": 1, "col": 9, "ground": "LOW", "name": "无技能"})
check("无技能老数据仍可读", _old2 is not None
      and _old2.skill.is_passive is True, "is_passive=%s" % _old2.skill.is_passive)

# ------------------------- 10. 图鉴批注：敌人与干员分别导入导出，互不污染
print("\n[10] 图鉴批注必须按敌人/干员分别导入导出，且不许跨类污染")
import os as _os
import tempfile as _tf
from akcalc.core import annotations as ANNO


class _TmpPaths:
    """把批注库指到临时目录。

    `AnnotationStore` 只认 ``paths`` 上的几个属性，给一个鸭子类型就够。
    测试绝不能落到用户真实的 ``akcalc/data/cache/annotations_*.json``：
    以前这组直接写真实文件，跑一次回归就在用户数据里留下
    「爱国者一阶段高防」「银灰三技能清场」两条假批注。
    """

    def __init__(self, base):
        self.cache_dir = base
        self.annotations_enemy = _os.path.join(base, "annotations_enemy.json")
        self.annotations_operator = _os.path.join(base,
                                                  "annotations_operator.json")


_tmp10 = _tf.mkdtemp(prefix="annreg_")
_st10 = ANNO.AnnotationStore(_TmpPaths(_tmp10))
check("批注测试用的是临时文件（不碰用户数据）",
      _os.path.abspath(_st10.path_of("enemy")).startswith(
          _os.path.abspath(_tmp10)),
      _st10.path_of("enemy"))
check("批注只有敌人/干员两类", ANNO.KINDS == ("enemy", "operator"),
      str(ANNO.KINDS))
check("两类默认文件名不同",
      ANNO.default_file_name("enemy") != ANNO.default_file_name("operator"),
      "%s vs %s" % (ANNO.default_file_name("enemy"),
                    ANNO.default_file_name("operator")))
for _k in ANNO.KINDS:
    _st10.clear(_k, persist=False)
_st10.set("enemy", "enemy_1506_patrt", "爱国者一阶段高防", name="爱国者",
          persist=False)
_st10.set("operator", "char_172_svrash", "银灰三技能清场", name="银灰",
          persist=False)
_p10 = {}
# 导出文件必须放到**另一个**目录。以前和批注库同目录、且文件名一样
# （ANNO.default_file_name(k) 就是 store 自己的文件名），于是导出直接
# 覆盖了库文件；等 import_('enemy') 里 flush() 把已清空的 operator 数据
# 写回去，operator 的导出文件就被冲成空的了 —— 表现为
# 「导入 operator 恢复 1 条 added=0」。真实 UI 走文件对话框选路径，
# 不会撞名，所以这是测试自己的坑。
_out10 = _os.path.join(_tmp10, "exports")
_os.makedirs(_out10, exist_ok=True)
for _k in ANNO.KINDS:
    _fp = _os.path.join(_out10, ANNO.default_file_name(_k))
    _n10 = _st10.export(_k, _fp)
    _p10[_k] = _fp
    check("导出 %s 返回条数" % _k, _n10 == 1, "n=%s" % _n10)
    check("导出 %s 没覆盖批注库自己的文件" % _k,
          _os.path.abspath(_fp) != _os.path.abspath(_st10.path_of(_k)),
          _fp)
_txt_e = open(_p10["enemy"], encoding="utf-8").read()
_txt_o = open(_p10["operator"], encoding="utf-8").read()
check("敌人导出文件不含干员键", "char_172_svrash" not in _txt_e)
check("干员导出文件不含敌人键", "enemy_1506_patrt" not in _txt_o)
check("导出文件头标明类型",
      '"kind": "enemy"' in _txt_e and '"kind": "operator"' in _txt_o)
# 清空后分别导回：只回各自那一类
for _k in ANNO.KINDS:
    _st10.clear(_k, persist=False)
for _k in ANNO.KINDS:
    _added10, _kept10 = _st10.import_(_k, _p10[_k])
    check("导入 %s 恢复 1 条" % _k,
          _added10 == 1 and _st10.count(_k) == 1,
          "added=%s count=%s" % (_added10, _st10.count(_k)))
# 跨类导入必须被拒（否则怪物列表里会混进 char_xxx）
try:
    _st10.import_("enemy", _p10["operator"])
    check("跨类导入被拒绝", False, "没报错，干员批注混进了怪物批注")
except ANNO.AnnotationError:
    check("跨类导入被拒绝", True, "AnnotationError")
check("被拒后怪物批注未被污染", _st10.count("enemy") == 1
      and "char_172_svrash" not in _st10.all("enemy"),
      str(list(_st10.all("enemy"))))
# 老文件没有 kind 字段时仍要放行（不能把用户的历史备份锁死）
_legacy = _os.path.join(_tmp10, "legacy.json")
open(_legacy, "w", encoding="utf-8").write(
    '{"count":1,"entries":{"enemy_1507_patrt":{"name":"老","text":"老文件"}}}')
try:
    _la, _lk = _st10.import_("enemy", _legacy)
    check("无 kind 字段的老文件仍可导入", _la == 1, "added=%s" % _la)
except Exception as _e:
    check("无 kind 字段的老文件仍可导入", False, type(_e).__name__)
# 空白批注不收
check("空白批注被拒绝",
      _st10.set("enemy", "x_blank", "   ", persist=False) is False)
for _k in ANNO.KINDS:
    _st10.clear(_k, persist=False)

# ------------------- 11. 集成战略第二层筛选 / 无出怪关卡的原因说明
print("\n[11] 集成战略第二层筛选 + 无出怪关卡必须说明原因")
from akcalc.core.catalog import StageCatalog as _SC
from akcalc.core.paths import Paths as _P

_p11 = _P.default()
_cat11 = _SC.load(_os.path.join(str(_p11.data_dir), "catalog.json"))
_rogue11 = [s for s, st in _cat11.stages.items() if st.category == "roguelike"]
check("集成战略关卡表非空", len(_rogue11) > 500, "%d 关" % len(_rogue11))
_grp11 = sorted({_cat11.stages[s].group_id for s in _rogue11})
check("集成战略有 6 个主题（第一层）", len(_grp11) == 6, str(_grp11))
_allnodes = {}
for _g in _grp11:
    _t = _cat11.node_types_in(_g)
    _allnodes[_g] = _t
    check("主题 %s 有第二层节点类型" % _g, len(_t) >= 1,
          "/".join("%s(%d)" % (l, n) for _k, l, n in _t))
# 每个节点类型的关数之和必须等于该主题总关数（不能有关卡落到层外）
for _g in _grp11:
    _sum11 = sum(n for _k, _l, n in _allnodes[_g])
    _tot11 = len([s for s in _rogue11 if _cat11.stages[s].group_id == _g])
    check("主题 %s 节点关数合计等于总关数" % _g, _sum11 == _tot11,
          "%d vs %d" % (_sum11, _tot11))
# node_type 必须都是已知 key（不能冒出空串以外的野值）
_known11 = {"normal", "emergency", "boss", "ending", "event", "special",
            "variant"}
_bad11 = {k for _g in _grp11 for k, _l, _n in _allnodes[_g]
          if k not in _known11}
check("节点类型 key 都在已知集合内", not _bad11, str(_bad11))

# 无出怪关卡：isValid=False 必须能被识别并给出可读原因，不能显示空白
from akcalc.core.timeline import parse_timeline as _pt
import json as _json11
_d11 = str(_p11.levels_cache_dir)
_empt11 = 0
_checked11 = 0
_err11 = 0
for _fn in sorted(_os.listdir(_d11))[:400]:
    if not _fn.endswith(".json"):
        continue
    try:
        _raw11 = _json11.load(open(_os.path.join(_d11, _fn), encoding="utf-8"))
        _tl11 = _pt(_raw11)
    except Exception:
        _err11 += 1
        continue
    _checked11 += 1
    if _tl11.events and not _tl11.effective_events():
        _empt11 += 1
        # 这种关必须「全部 disabled」，否则是筛选逻辑漏掉了本该出怪的
        check("%s 空出怪只能是全部 isValid=false" % _fn[:-5],
              _tl11.disabled_count == len(_tl11.events),
              "%d/%d" % (_tl11.disabled_count, len(_tl11.events)))
check("关卡文件能正常解析（不是全军覆没）", _checked11 >= 300,
      "解析成功 %d 个，失败 %d 个" % (_checked11, _err11))
check("扫描到 isValid=false 关卡样本", _empt11 >= 1,
      "抽查 %d 个文件命中 %d 个" % (_checked11, _empt11))

# ---------------- 12. 「多出平民」：无害单位要自适应折叠，不能一刀切
print("\n[12] 无害单位自适应折叠（H8-4 平民不该冒出来，博物馆系列不能变空）")


def _eff(sid):
    _fp = _os.path.join(_d11, sid + ".json")
    if not _os.path.isfile(_fp):
        return None
    return _pt(_json11.load(open(_fp, encoding="utf-8")))


_t12 = _eff("main_08-04")
if _t12 is not None:
    _ev12 = _t12.effective_events()
    _nh12 = sum(1 for e in _ev12 if e.harmless)
    check("H8-4 有无害单位（平民）", _nh12 > 0, "%d 条" % _nh12)
    check("H8-4 也有真敌人（否则不能折叠）", _nh12 < len(_ev12),
          "%d/%d" % (_nh12, len(_ev12)))
    # 折叠后必须还剩东西
    _gs12 = _t12.groups(hostile_only=True, effective=True)
    check("H8-4 折叠平民后仍有出怪", len(_gs12) > 0, "%d 组" % len(_gs12))
    check("H8-4 折叠平民后不含平民",
          all(g.enemy_id != "enemy_3001_upeopl" for g in _gs12))
else:
    check("H8-4 有无害单位（平民）", False, "无缓存文件")

# 全库：存在「全部出怪都是无害单位」的关卡，这些关卡绝不能默认折叠
_allharm12 = []
for _fn in sorted(_os.listdir(_d11)):
    if not _fn.endswith(".json"):
        continue
    try:
        _tl12 = _pt(_json11.load(open(_os.path.join(_d11, _fn),
                                      encoding="utf-8")))
    except Exception:
        continue
    _ev12 = _tl12.effective_events()
    if _ev12 and all(e.harmless for e in _ev12):
        _allharm12.append(_fn[:-5])
    if len(_allharm12) >= 40:
        break
check("存在「全部出怪都是无害」的关卡（不能一刀切折叠）",
      len(_allharm12) > 0, "%d 个，如 %s" % (len(_allharm12), _allharm12[:3]))
if _allharm12:
    _t12b = _eff(_allharm12[0])
    check("%s 折叠后会变空（所以必须保持显示）" % _allharm12[0],
          len(_t12b.groups(hostile_only=True, effective=True)) == 0,
          "折叠后 0 组")

print("\n[13] 悬停干员必须真的显示技能回转（默认技能不能是「永远技能中」）")

# 用户要求「悬停干员显示技能回转」。以前 _pick_operator 取 skills[0]，银灰的
# 第一个技能是「强力击·γ型」（spCost=2、duration=0，is_continuous），
# SkillSim.state_at 对这类永远返回 active=True，悬停只剩一句「技能中」。
from akcalc.core.sandbox_track import SkillCycle, SkillSim  # noqa: E402
from akcalc.core import prts_operator as _PO13  # noqa: E402


def _is_continuous(_c):
    """``sp_cost>0`` 且无 ``duration``：state_at 对这类永远 ``active=True``。"""
    return float(getattr(_c, "sp_cost", 0) or 0) > 0 and \
        float(getattr(_c, "duration", 0) or 0) <= 0


# 不自建一套「技能 → SkillCycle」的复刻逻辑——那会和生产代码悄悄分叉
# （第一版就是死在 max(int(k)) 取到了专精前数据，spCost=0）。
# 生产代码已把这段抽成模块级 `_cycle_of`，测试直接复用同一份实现。
from akcalc.ui.sandbox_panel import _cycle_of as _cyc_of  # noqa: E402
from akcalc.ui.sandbox_panel import _default_skill_of as _default  # noqa: E402


_pool13 = _PO13.list_operator_names()
check("干员库可读", len(_pool13) > 100, "%d 个干员" % len(_pool13))

# 关键：技能不在 load_operator() 的返回值里（那个对象的 skills 恒为空），
# 必须走 UI 的同一条路——OperatorCache.data → dict_to_op。用错 API 会让
# 「默认技能」这组断言全在 0 个样本上假通过。
from akcalc.core import prts_operator as _POc13  # noqa: E402
from akcalc.core.paths import Paths as _P13  # noqa: E402

_oc13 = _POc13.OperatorCache.load(str(_P13.default().operators_cache))
_data13 = getattr(_oc13, "data", None) or {}
check("干员缓存里有数据（不是空表）", len(_data13) > 100, "%d 条" % len(_data13))

_n13 = 0
_bad13 = []
_cont13 = []
for _nm, _d in _data13.items():
    try:
        _op = _PO13.dict_to_op(_d)
    except Exception:
        continue
    _sks = list(getattr(_op, "skills", None) or [])
    if not _sks:
        continue
    _n13 += 1
    _any_active = any(_cyc_of(s).sp_cost > 0 for s in _sks)
    _pick = _default(_sks)
    _c = _cyc_of(_pick)
    # 只要该干员有主动技能，默认就必须落到主动技能上（被动没有回转可看）
    if _any_active and float(getattr(_c, "sp_cost", 0) or 0) <= 0:
        _bad13.append((_nm, getattr(_pick, "name", "")))
    # 持续型（sp_cost>0 且 duration<=0）会让 state_at 恒 active，
    # 只在该干员还存在「有 duration 的主动技能」时才算选错
    if _is_continuous(_c):
        _has_dur = any(_cyc_of(s).sp_cost > 0 and _cyc_of(s).duration > 0
                       for s in _sks)
        if _has_dur:
            _cont13.append((_nm, getattr(_pick, "name", "")))

check("干员技能能读到（不是 0 个样本假通过）", _n13 > 300, "有技能的干员 %d 个" % _n13)
check("有主动技能的干员，默认技能必是主动技能",
      _n13 > 0 and len(_bad13) == 0,
      "检查 %d 个，异常 %d 个 %s" % (_n13, len(_bad13), _bad13[:3]))
check("默认技能不会挑「持续型」（否则悬停只显示「技能中」）",
      _n13 > 0 and len(_cont13) == 0,
      "异常 %d 个 %s" % (len(_cont13), _cont13[:3]))

# 具体干员的默认技能得对得上（这几个人人都知道用哪个技能）
_want13 = {"银灰": "真银斩", "塞雷娅": "钙质化", "艾雅法拉": "火山",
           "能天使": "扫射模式"}
_got13 = {}
for _nm, _exp in _want13.items():
    _d = _data13.get(_nm)
    if not _d:
        continue
    _op = _PO13.dict_to_op(_d)
    _sks = list(getattr(_op, "skills", None) or [])
    _got13[_nm] = getattr(_default(_sks), "name", "")
check("热门干员默认技能符合直觉",
      all(_got13.get(_k) == _want13[_k] for _k in _got13)
      and len(_got13) == len(_want13),
      "、".join("%s→%s" % (k, v) for k, v in _got13.items()))

# 银灰真银斩 90SP/30s：悬停文案必须能走完「攒SP→就绪→技能中」
_sd13 = _data13.get("银灰")
if _sd13:
    _sv13 = _PO13.dict_to_op(_sd13)
    _sk13 = _default(list(_sv13.skills))
    _c13 = _cyc_of(_sk13)
    check("银灰默认技能是真银斩（90SP/30s）",
          getattr(_sk13, "name", "") == "真银斩"
          and _c13.sp_cost == 90.0 and _c13.duration == 30.0,
          "%s sp=%s dur=%s" % (getattr(_sk13, "name", ""),
                               _c13.sp_cost, _c13.duration))
    _sim13 = SkillSim()
    _seen_ready = _seen_active = _seen_charging = False
    # 采样要盖住「初始SP刚好充满」那一瞬（init_sp=75 / sp_cost=90 → t=15），
    # 以及技能结束后的下一轮。稀疏采样会漏掉 ready 这一态。
    for _t in range(0, 131, 5):
        _st13 = _sim13.state_at(_c13, float(_t), 0.0, 0.0)
        if _st13.get("active"):
            _seen_active = True
        elif _st13.get("ready"):
            _seen_ready = True
        elif float(_st13.get("sp", 0) or 0) > 0:
            _seen_charging = True
    check("真银斩回转三态都能出现（攒SP/就绪/技能中）",
          _seen_charging and _seen_ready and _seen_active,
          "charging=%s ready=%s active=%s"
          % (_seen_charging, _seen_ready, _seen_active))
    # 第二轮 SP 必须从 0 重新攒（不能沿用上一轮的 90）
    _st13b = _sim13.state_at(_c13, 60.0, 0.0, 0.0)
    check("技能结束后 SP 归零重新攒",
          float(_st13b.get("sp", 0) or 0) < _c13.sp_cost,
          "t=60 sp=%s / %s" % (_st13b.get("sp"), _c13.sp_cost))

# 悬停文案函数两处共用，必须对三种状态都给出可读文本。
# _skill_text 是实例方法 (self, dep, st)，从类上调用时 self 要显式占一位。
from akcalc.ui.sandbox_panel import SandboxPanel  # noqa: E402

_txt13 = {}
for _k, _st in (("passive", {"passive": True}),
                ("active", {"active": True, "next_in": 12.5}),
                ("ready", {"ready": True}),
                ("charging", {"sp": 30.0, "need": 90.0, "next_in": 60.0})):
    try:
        _txt13[_k] = SandboxPanel._skill_text(None, None, _st)
    except Exception as _e:
        _txt13[_k] = "ERR:%s" % _e
check("_skill_text 四种状态都有文案",
      all(v and not str(v).startswith("ERR") for v in _txt13.values()),
      " | ".join("%s=%s" % (k, v) for k, v in _txt13.items()))
check("_skill_text 技能中会给出剩余秒",
      "12.5" in str(_txt13.get("active", "")), _txt13.get("active", ""))
check("_skill_text 攒SP会给出 SP 进度",
      "30" in str(_txt13.get("charging", ""))
      and "90" in str(_txt13.get("charging", "")), _txt13.get("charging", ""))

# ---------------------------------------------------------------- 14 飞行判定
print("\n[14] 飞行敌人的判定（地面干员挡不住，开了对空才挡得住）")

from akcalc.core.sandbox import Sandbox as _SB14  # noqa: E402
from akcalc.core.timeline import parse_timeline as _PT14  # noqa: E402
from akcalc.core.maps import get_level as _GL14  # noqa: E402
import dataclasses as _dc14  # noqa: E402

# SpawnEvent 上没有 flying 字段——enemy_flags 若照它取，飞行敌人会永远
# 被当成地面单位，地面干员照样挡住它，而「开对空阻挡」永远没效果。
_SEV14 = _PT14({"routes": [], "enemies": []}).events if False else None
from akcalc.core.timeline import SpawnEvent as _SE14  # noqa: E402

check("SpawnEvent 没有 flying 字段（所以不能从它取）",
      "flying" not in [f.name for f in _dc14.fields(_SE14)],
      "%s" % [f.name for f in _dc14.fields(_SE14)])

# 找一张真有 FLY 路线的图
from akcalc.core.paths import Paths as _P14  # noqa: E402

_lc14 = _P14.default().levels_cache_dir
check("关卡缓存目录存在", os.path.isdir(str(_lc14)), "%s" % (_lc14,))
_roads14 = []
for _fn in sorted(os.listdir(str(_lc14))):
    if not _fn.endswith(".json"):
        continue
    try:
        _raw14 = json.load(open(os.path.join(str(_lc14), _fn), encoding="utf-8"))
    except Exception:
        continue
    _rts = [r for r in (_raw14.get("routes") or []) if isinstance(r, dict)]
    _nfly = sum(1 for r in _rts if str(r.get("motionMode")) == "FLY")
    if _nfly:
        _roads14.append((_fn[:-5], _nfly))
check("库里有 motionMode=FLY 的关卡", len(_roads14) > 20,
      "%d 个，如 %s" % (len(_roads14), _roads14[:3]))

_SID14 = "a001_05"
_gm14 = _GL14(_SID14, "main", None)
_raw14b = json.load(open(os.path.join(str(_lc14), _SID14 + ".json"),
                         encoding="utf-8"))
_tl14 = _PT14(_raw14b)
_sb14 = _SB14(_gm14, _tl14)
_f14 = [ra for ra in _sb14.base_analyses if ra.flying]
check("a001_05 的路线分析里 flying 被置位", len(_f14) > 0,
      "%d 条飞行路线，route %s"
      % (len(_f14), [ra.route_index for ra in _f14][:6]))

_fev14 = None
for _e in _tl14.events:
    _ra = _sb14.analysis_for(_e)
    if _ra is not None and _ra.flying:
        _fev14 = _e
        break
check("找得到飞行出怪", _fev14 is not None,
      "%s route %s" % (getattr(_fev14, "enemy_name", "—"),
                       getattr(_fev14, "route_index", "—")))

if _fev14 is not None:
    _ra14 = _sb14.analysis_for(_fev14)
    _t14 = float(_fev14.time) + _ra14.total_time * 0.4
    _fl14 = _sb14.enemy_flags(_fev14, _t14)
    check("enemy_flags 报告这只敌人是飞行的", _fl14["flying"] is True,
          "t=%.1f flying=%s" % (_t14, _fl14["flying"]))

    # 在飞行路线上放地面干员，关对空时不该挡住
    _cell14 = None
    for _pt in (_ra14.full_path or [])[1:]:
        _rr, _cc = int(round(_pt[0])), int(round(_pt[1]))
        _ok, _why = _sb14.deploy_check(_rr, _cc, False)
        if _ok:
            _cell14 = (_rr, _cc)
            break
    check("飞行路线上有可部署的地面格", _cell14 is not None, "%s" % (_cell14,))

    if _cell14:
        _pc14 = _sb14.place_operator(_cell14[0], _cell14[1], op_id="",
                                     name="银灰", profession="", facing="RIGHT")
        _pc14.is_ranged = False
        _pc14.ground = "LOW"
        _pc14.block_count = 2
        _pc14.can_block_fly = False
        _hit14 = None
        for _i in range(0, 401):
            _tt = float(_fev14.time) + _i * 0.25
            _pos = _sb14.pose_at(_fev14, _tt)
            if _pos and (int(round(_pos[0])), int(round(_pos[1]))) == _cell14:
                _hit14 = _tt
                break
        check("敌人确实经过这个格子", _hit14 is not None, "t=%s" % (_hit14,))
        if _hit14 is not None:
            _a14 = _sb14.enemy_flags(_fev14, _hit14)
            check("关着对空阻挡时，地面干员挡不住飞行敌人",
                  _a14["blocked"] is False,
                  "blocked=%s by=%s" % (_a14["blocked"],
                                        getattr(_a14["blocked_by"], "name", None)))
            _sb14.set_block_fly(_pc14, True)
            check("开启对空阻挡后 can_block_fly=True",
                  getattr(_pc14, "can_block_fly", False) is True, "")
            _b14 = _sb14.enemy_flags(_fev14, _hit14)
            check("开启对空阻挡后就能挡住飞行敌人",
                  _b14["blocked"] is True,
                  "blocked=%s by=%s" % (_b14["blocked"],
                                        getattr(_b14["blocked_by"], "name", None)))
            _sb14.set_block_fly(_pc14, False)
            _c14 = _sb14.enemy_flags(_fev14, _hit14)
            check("关回去就不挡了（不是单向开关）",
                  _c14["blocked"] is False, "blocked=%s" % _c14["blocked"])

# ---------------------------------------------------------------- 15 减速动画
print("\n[15] 右键敌人设减速：动画跟着变，罚站时长不动")

from akcalc.core.sandbox import Sandbox as _SB15  # noqa: E402
from akcalc.core.timeline import parse_timeline as _PT15  # noqa: E402
from akcalc.core.maps import get_level as _GL15  # noqa: E402

_SID15 = "main_07-16"
_gm15 = _GL15(_SID15, "main", None)
_raw15 = json.load(open(os.path.join(str(_lc14), _SID15 + ".json"),
                         encoding="utf-8"))
_tl15 = _PT15(_raw15)
_sb15 = _SB15(_gm15, _tl15)

# 找一只罚站时间够长的敌人，才能看清减速把移动段拉长
_ev15 = None
for _e in _tl15.events:
    _ra = _sb15.analysis_for(_e)
    if _ra and getattr(_ra, "wait_time", 0) > 50 and getattr(_ra, "reachable", True):
        _ev15 = _e
        break
check("找得到有长罚站的敌人", _ev15 is not None,
      getattr(_ev15, "enemy_name", "—"))

if _ev15 is not None:
    _ra15 = _sb15.analysis_for(_ev15)
    _w0 = _ra15.wait_time
    _t0 = float(_ev15.time)
    _samples = [_t0 + 5, _t0 + 20, _t0 + 40, _t0 + 80, _t0 + 115]
    _before = [_sb15.pose_at(_ev15, _t) for _t in _samples]
    _arr0 = _sb15.arrival_time(_ev15)

    _sb15.add_slow(_ev15, 0.5, 40.0)
    _after = [_sb15.pose_at(_ev15, _t) for _t in _samples]
    _arr1 = _sb15.arrival_time(_ev15)

    check("加减速后同一时刻位置变了（动画真的跟着变）",
          any(a != b for a, b in zip(_before, _after)),
          "%d/%d 个采样点位置不同"
          % (sum(1 for a, b in zip(_before, _after) if a != b), len(_samples)))
    check("减速让敌人更晚到达", _arr1 > _arr0,
          "%.1fs -> %.1fs" % (_arr0, _arr1))
    _ra15b = _sb15.analysis_for(_ev15)
    check("罚站时长不被减速改变（铁律：只拉长移动段）",
          abs(_ra15b.wait_time - _w0) < 1e-6,
          "%.1fs -> %.1fs" % (_w0, _ra15b.wait_time))
    check("速度系数在减速窗口内确实变小",
          _sb15.speed_at(_ev15, _t0 + 10) < 1.0,
          "speed=%.2f" % _sb15.speed_at(_ev15, _t0 + 10))
    _sb15.clear_buffs(_ev15) if hasattr(_sb15, "clear_buffs") else None
    check("能清掉这只的减速", not _sb15.buffs_of(_ev15)
          or all(b[2] <= 0 for b in _sb15.buffs_of(_ev15)),
          "%s" % (_sb15.buffs_of(_ev15),))

# 菜单标签不能把 %% 原样显示出来（add_command 不走 % 格式化）
import re as _re15  # noqa: E402
_src15 = open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           "akcalc", "ui", "sandbox_panel.py"),
              encoding="utf-8").read()
_bad_lbl = [ln.strip() for ln in _src15.splitlines()
            if "label=" in ln and "%%" in ln and "%" not in ln.split("label=")[1][:2]]
check("菜单 label 里没有多余的 %%", not _bad_lbl, "%s" % (_bad_lbl[:2],))

# ------------------------------------------------------- 16 传送门 / 机关悬停
print("\n[16] 传送门点击画路径 + 装置悬停显示名称（走真实 _on_load）")

from akcalc.core import mechanisms as _ME16  # noqa: E402

_cat16 = getattr(APP, "StageCatalog", None)
_app16 = None
try:
    _app16 = APP.App()
    _app16.withdraw()
    _app16.update()
    _app16.show_view("sandbox")
    _app16.update()
    _sp16 = _app16._sandbox_panel
except Exception as _e16:
    _sp16 = None
    check("沙盘面板能起来", False, "%s" % _e16)

check("沙盘面板能起来", _sp16 is not None, "")

if _sp16 is not None:
    _cat16 = getattr(_sp16.app, "stage_catalog", None)
    check("关卡的 stage_catalog 可用", _cat16 is not None,
          "%d 个关卡" % len(getattr(_cat16, "stages", {}) or {}))

    # 找一张真有传送门的关卡
    _hit16 = None
    for _sid, _st in list(getattr(_cat16, "stages", {}).items()):
        if "mini" not in _sid and "act10" not in _sid and "act21" not in _sid:
            continue
        try:
            _gm = _GL14(_sid, _st.category, None, rel_path=_st.path)
        except Exception:
            continue
        if _gm is None:
            continue
        _pr = _ME16.portals(_ME16.extract(_gm))
        if _pr:
            _hit16 = (_sid, _st, _gm, _pr)
            break
    check("找得到带传送门的关卡", _hit16 is not None,
          "%s 共 %d 对" % (getattr(_hit16[0] if _hit16 else None, "__str__", lambda: "—")(),
                          len(_hit16[3]) if _hit16 else 0))

    if _hit16 is not None:
        _sid16, _st16, _gm16, _pr16 = _hit16
        _lbl16 = "● " + (getattr(_st16, "label", "") or _st16.name)
        _sp16._stage_index[_lbl16] = _st16
        _sp16.cmb_stage.configure(
            values=list(_sp16.cmb_stage.cget("values") or []) + [_lbl16])
        _sp16.cmb_stage.set(_lbl16)
        _sp16._on_load()
        _app16.update()

        check("载入后 game_map 就位", _sp16.game_map is not None, "")
        check("_portal_map 被填充（不是空表）", len(_sp16._portal_map) > 0,
              "%s" % (_sp16._portal_map,))

        _prok16 = 0
        for (_r16, _c16) in list(_sp16._portal_map.keys()):
            _sp16.canvas.portal_link = None
            _sp16._on_cell_click(_r16, _c16)
            _app16.update()
            if _sp16.canvas.portal_link:
                _prok16 += 1
        check("每个传送门点一下都能画出路径",
              _prok16 == len(_sp16._portal_map) and _prok16 > 0,
              "%d/%d" % (_prok16, len(_sp16._portal_map)))

        # 出口段要通到蓝门，不能是空
        _r16, _c16 = list(_sp16._portal_map.keys())[0]
        _sp16._on_cell_click(_r16, _c16)
        _app16.update()
        _lnk16 = _sp16.canvas.portal_link
        check("传送路径有出口→蓝门那一段",
              _lnk16 is not None and len(_lnk16.get("exit_path") or []) > 0,
              "exit_path %d 点" % len((_lnk16 or {}).get("exit_path") or []))

        # 点普通格要清掉
        _sp16._on_cell_click(0, 0)
        _app16.update()
        check("点非传送门格会清掉传送线",
              _sp16.canvas.portal_link is None, "")

        # 悬停机关格要说出名字与功能
        _mech_ok = 0
        _mech_tot = 0
        for _mm in (_sp16._mechs or [])[:40]:
            _pos = getattr(_mm, "pos", None)
            if not _pos:
                continue
            _mech_tot += 1
            _sp16._hover_tile(_pos)
            _app16.update()
            if str(_mm.name or "") and str(_mm.name) in _sp16.lbl_hover.cget("text"):
                _mech_ok += 1
        check("悬停机关格会显示它的名字", _mech_tot and _mech_ok == _mech_tot,
              "%d/%d" % (_mech_ok, _mech_tot))

    try:
        _app16.destroy()
    except Exception:
        pass

# ------------------------------------------------- 17 图鉴批注卡片真的挂上去
print("\n[17] 图鉴对话框里批注卡片真的存在（不是只有数据层）")

from akcalc.ui.annotation_card import AnnotationCard as _AC17  # noqa: E402
from akcalc.ui.monster_codex import MonsterCodexDialog as _MCD17  # noqa: E402
from akcalc.core import annotations as _AN17  # noqa: E402

# 测试绝不能碰用户真实的批注文件。以前这组直接往
# akcalc/data/cache/annotations_*.json 里写，跑一次回归就在用户数据里
# 留下「回归测试批注」，还得手工清。改成把 app.paths 指到临时目录，
# store_for 会跟着建一份临时 store，真实文件一个字节都不动。
# 复用第 [10] 组定义的 _TmpPaths。
_tmpdir17 = _tf.mkdtemp(prefix="anno17_")


_app17 = None
try:
    _app17 = APP.App()
    _app17.withdraw()
    _app17.update()
    _app17.paths = _TmpPaths(_tmpdir17)
    _app17._annotation_store = _AN17.AnnotationStore(_app17.paths)
    _dlg17 = _MCD17(_app17, _app17, "爱国者", "enemy_1506_patrt", 0)
    _app17.update()
    _dlg17.update()
except Exception as _e17:
    _dlg17 = None
    check("图鉴对话框能创建", False, "%s" % _e17)

check("图鉴对话框能创建", _dlg17 is not None, "")
check("测试用的是临时批注文件（不污染用户数据）",
      os.path.abspath(_AN17.store_for(_app17).path_of("enemy")).startswith(
          os.path.abspath(_tmpdir17)),
      _AN17.store_for(_app17).path_of("enemy"))

if _dlg17 is not None:
    def _find17(w, acc):
        for _ch in w.winfo_children():
            if isinstance(_ch, _AC17):
                acc.append(_ch)
            _find17(_ch, acc)
        return acc

    _cards17 = _find17(_dlg17, [])
    check("对话框里挂了批注卡片", len(_cards17) >= 1,
          "%d 张" % len(_cards17))
    check("敌人图鉴的批注卡片 kind=enemy",
          _cards17 and all(getattr(c, "kind", "") == "enemy" for c in _cards17),
          "%s" % ([getattr(c, "kind", "?") for c in _cards17],))
    check("批注卡片的 key 是这只敌人的 id",
          _cards17 and any(getattr(c, "key", "") == "enemy_1506_patrt"
                           for c in _cards17),
          "%s" % ([getattr(c, "key", "?") for c in _cards17],))

    # 写入 → 读回 → 落盘 reload 三步都得成立
    _st17 = _AN17.store_for(_app17)
    _old17 = _st17.get("enemy", "enemy_1506_patrt")
    _st17.set("enemy", "enemy_1506_patrt", "回归测试批注", name="爱国者")
    check("批注写入后能读回",
          _st17.get("enemy", "enemy_1506_patrt") == "回归测试批注", "")
    _st17.flush()
    _st17.reload()
    check("批注落盘后 reload 还在",
          _st17.get("enemy", "enemy_1506_patrt") == "回归测试批注", "")

    # 两类各导各的，混着导必须被拒
    _d17 = _tf.mkdtemp()
    _p_e17 = os.path.join(_d17, "e.json")
    _p_o17 = os.path.join(_d17, "o.json")
    _n_e17 = _st17.export("enemy", _p_e17)
    _n_o17 = _st17.export("operator", _p_o17)
    check("敌人批注能单独导出", _n_e17 >= 1, "%d 条" % _n_e17)
    _je17 = json.load(open(_p_e17, encoding="utf-8"))
    check("导出的敌人批注文件自带 kind 标记",
          _je17.get("kind") == "enemy", "%r" % _je17.get("kind"))
    _rejected17 = 0
    for _src17, _dst17 in ((_p_e17, "operator"), (_p_o17, "enemy")):
        if not os.path.exists(_src17):
            continue
        try:
            _st17.import_(_dst17, _src17)
        except Exception:
            _rejected17 += 1
    check("两类批注不能互相导入", _rejected17 == 2, "%d/2 被拒" % _rejected17)

    # 还原
    if _old17:
        _st17.set("enemy", "enemy_1506_patrt", _old17, name="爱国者")
    else:
        _st17.remove("enemy", "enemy_1506_patrt")
    _st17.flush()
    try:
        _dlg17.destroy()
    except Exception:
        pass
    try:
        _app17.destroy()
    except Exception:
        pass

# ------------------------------------------- 18 「具体指令」在全库都拿得出来
print("\n[18] 每个有技能的敌人，「查看原代码」都要能给出具体指令（不是只有描述 JSON）")

from akcalc.core import enemy_skills as _ES18  # noqa: E402

_app18 = None
try:
    _app18 = APP.App()
    _app18.withdraw()
    _app18.update()
    for _ in range(400):
        _app18.update()
        if getattr(getattr(_app18, "enemy_lib", None), "loaded", False):
            break
except Exception as _e18:
    _app18 = None
    check("敌人库能载入", False, "%s" % _e18)

_by18 = getattr(getattr(_app18, "enemy_lib", None), "by_id", {}) or {}
check("敌人库有数据", len(_by18) > 1000, "%d 条" % len(_by18))

_withsk18 = []
for _eid18, _ents18 in _by18.items():
    try:
        _cs18 = _ES18.skill_codes(_ents18)
    except Exception:
        _cs18 = []
    if _cs18:
        _withsk18.append((_eid18, _ents18, _cs18))
check("有技能的敌人数不为零", len(_withsk18) > 500,
      "%d 个（共 %d）" % (len(_withsk18), len(_by18)))

_n_ann18 = 0
_n_instr18 = 0
_n_steps18 = {}
_fail18 = []
for _eid18, _ents18, _cs18 in _withsk18:
    _tal18 = None
    for _e18 in _ents18:
        if int(_e18.get("level", 0) or 0) == 0:
            _tal18 = (_e18.get("enemyData") or {}).get("talentBlackboard")
            break
    if _tal18 is None:
        _tal18 = (_ents18[0].get("enemyData") or {}).get("talentBlackboard")
    _raws18 = [c.get("raw") for c in _cs18 if c.get("raw")]
    try:
        _ann18 = _ES18.skill_annotation(_app18, _eid18, _raws18, _tal18)
    except Exception as _x18:
        _fail18.append((_eid18, str(_x18)[:50]))
        continue
    if not _ann18:
        _fail18.append((_eid18, "空注解"))
        continue
    _n_ann18 += 1
    _hit18 = False
    for _item18 in _ann18:
        for _ln18 in (_item18.get("lines") or []):
            _s18 = str(_ln18)
            if "技能指令" in _s18:
                _hit18 = True
                _m18 = re.search(r"共\s*(\d+)\s*步", _s18)
                if _m18:
                    _n_steps18[int(_m18.group(1))] = \
                        _n_steps18.get(int(_m18.group(1)), 0) + 1
    if _hit18:
        _n_instr18 += 1

check("每个有技能的敌人都能生成注解",
      _n_ann18 == len(_withsk18),
      "%d/%d%s" % (_n_ann18, len(_withsk18),
                   "" if not _fail18 else " 失败例 %s" % (_fail18[:3],)))
check("每条注解都含「技能指令」块（不是光秃秃的描述 JSON）",
      _n_instr18 == len(_withsk18),
      "%d/%d" % (_n_instr18, len(_withsk18)))
check("指令步骤数有多档（不是一律 1 步糊弄）",
      len(_n_steps18) >= 5, "%s" % dict(sorted(_n_steps18.items())))
check("指令明说没有客户端脚本（诚实边界）",
      any("没有客户端脚本" in s
          for s in (_ES18.annotation_lines(
              _ES18.annotate_code(_cs18[0], None, {}, {}, {})) or []))
      if _withsk18 else False,
      "")
if _app18 is not None:
    try:
        _app18.destroy()
    except Exception:
        pass

# ------------------------------- 19 图鉴界面上真的画出 PRTS 口径的圆点与字段
print("\n[19] 图鉴界面的技能卡是 PRTS 口径（●初始/●消耗 + 字段对照）")

from akcalc.ui.monster_codex import MonsterCodexDialog as _MCD19  # noqa: E402
import akcalc.ui.code_viewer as _CV19  # noqa: E402

_app19 = None
try:
    _app19 = APP.App()
    _app19.withdraw()
    _app19.update()
    for _ in range(400):
        _app19.update()
        if getattr(getattr(_app19, "enemy_lib", None), "loaded", False):
            break
    _dlg19 = _MCD19(_app19, _app19, "爱国者", "enemy_1506_patrt", 0)
    _app19.update()
    _dlg19.update()
except Exception as _e19:
    _dlg19 = None
    check("图鉴对话框能开（爱国者）", False, "%s" % _e19)

check("图鉴对话框能开（爱国者）", _dlg19 is not None, "")

if _dlg19 is not None:
    def _txt19(w, acc):
        for _ch in w.winfo_children():
            try:
                _cls = _ch.winfo_class()
                if _cls == "Label":
                    _t = _ch.cget("text")
                    if _t and str(_t).strip():
                        acc.append(str(_t))
                elif _cls == "Text":
                    acc.append(_ch.get("1.0", "end").strip())
            except Exception:
                pass
            _txt19(_ch, acc)
        return acc

    _all19 = _txt19(_dlg19, [])
    check("技能卡画出了初始/消耗圆点",
          any("初始" in t for t in _all19) and any("消耗" in t for t in _all19),
          "%d 条文字" % len(_all19))
    check("技能卡画出 prefabKey（客户端行为类名）",
          any("prefabKey" in t for t in _all19), "")
    check("界面上说明了 cooldown / initCooldown 的口径",
          any("initCooldown" in t and "初始" in t for t in _all19), "")

    # 「查看原代码」必须真的把内容交出去
    _got19 = {}
    _oi19 = _CV19.CodeViewerDialog.__init__

    def _pat19(self, master, title, payload, *a, **kw):
        _got19["title"] = title
        _got19["payload"] = payload
        _got19["kw"] = kw
        return _oi19(self, master, title, payload, *a, **kw)

    _CV19.CodeViewerDialog.__init__ = _pat19
    try:
        _dlg19._open_skill_json()
        _app19.update()
    except Exception as _x19:
        _got19["err"] = str(_x19)
    finally:
        _CV19.CodeViewerDialog.__init__ = _oi19

    check("「查看原代码」真的弹出了内容", bool(_got19.get("payload")),
          "%s" % (_got19.get("err") or sorted(_got19.keys())))
    _pl19 = _got19.get("payload") or {}
    check("payload 只留技能相关字段（不塞整条 enemyData）",
          set(_pl19.keys()) <= {"enemy_id", "skills", "talentBlackboard"},
          "%s" % (sorted(_pl19.keys()),))
    _ann19 = _got19.get("kw", {}).get("annotate")
    check("payload 带了结构注解", isinstance(_ann19, list) and len(_ann19) > 0,
          "%d 条" % (len(_ann19) if isinstance(_ann19, list) else 0))
    if isinstance(_ann19, list) and _ann19:
        _flat19 = " ".join(str(x) for it in _ann19
                           for x in (it.get("lines") or []))
        check("注解里真有「技能指令」而不是只有描述",
              "技能指令" in _flat19, _flat19[:90])

    try:
        _dlg19.destroy()
    except Exception:
        pass
    try:
        _app19.destroy()
    except Exception:
        pass

# ------------------ 20 出怪表：行要登记、空白原因要说得准、集成战略要能分两层
print("\n[20] 出怪表（行登记 / 空白原因 / 集成战略两层筛选）")

_app20 = None
try:
    _app20 = APP.App()
    _app20.withdraw()
    _app20.update()
    _app20.show_view("path")
    _app20.update()
    _pp20 = _app20._path_panel
    for _ in range(400):
        _app20.update()
        if _pp20.catalog is not None:
            break
except Exception as _e20:
    _pp20 = None
    check("寻路面板能开", False, "%s" % _e20)

check("寻路面板能开", _pp20 is not None and _pp20.catalog is not None, "")

if _pp20 is not None:
    def _lvl20(sid):
        _st = _pp20.catalog.stages.get(sid)
        if _st is None:
            return None
        _d = _st.difficulty_label
        _shown = "%s%s %s" % ("●" if getattr(_st, "cached", False) else "○",
                              ("  [%s]" % _d) if _d else "", _st.label)
        _pp20._stages = [_st]
        _pp20.var_level.set(_shown)
        _pp20.load_selected()
        _app20.update()
        return _st

    # 1) H8-4 这种正常关卡：行必须登记进 _spawn_rows，
    #    否则 _clear_isolation() 复位不了选中高亮
    _st20 = _lvl20("main_08-04")
    check("正常关卡能载入", _st20 is not None, "")
    _n_tiles20 = len(_pp20._spawn_tiles or [])
    _n_rows20 = len(_pp20._spawn_rows or [])
    check("出怪表的行有登记进 _spawn_rows（能复位高亮）",
          _n_rows20 > 0 and _n_rows20 == _n_tiles20,
          "rows=%d tiles=%d" % (_n_rows20, _n_tiles20))
    _gs20 = _pp20.timeline.groups(
        hostile_only=_pp20.var_hide_harmless.get(),
        effective=_pp20.var_effective_only.get()) if _pp20.timeline else []
    check("登记的行数等于实际画出来的分组数",
          _n_rows20 == len(_gs20), "rows=%d groups=%d" % (_n_rows20, len(_gs20)))

    # 2) 空白原因不能把「部分无害」说成「全部无害」
    _r20 = _pp20._empty_spawn_reason()
    _nall20 = len(_pp20.timeline.events)
    _nharm20 = getattr(_pp20.timeline, "harmless_count", 0)
    _said_all_harm20 = "全是无害单位" in _r20
    check("「部分无害」不能说成「全是无害单位」",
          not (_said_all_harm20 and _nharm20 < _nall20),
          "harmless=%d/%d → %s" % (_nharm20, _nall20, _r20[:60]))
    check("空白原因带上了真实的无害单位数",
          str(_nharm20) in _r20 or not _pp20.var_hide_harmless.get(),
          _r20[:80])

    # 3) 模板波次关卡要说清是 isValid=false，不能只说「没有记录」
    _st20b = _lvl20("act36side_ex03")
    if _st20b is not None and _pp20.timeline is not None:
        _r20b = _pp20._empty_spawn_reason()
        check("模板波次关说明是 isValid=false",
              "isValid" in _r20b, _r20b[:80])
        check("模板波次关不会谎称「没有出怪记录」",
              "没有出怪记录" not in _r20b, _r20b[:80])

    # 4) 集成战略的两层筛选：主题 -> 节点类型 -> 关卡数要精确对上
    try:
        _cats20 = list(_pp20.cmb_cat.cget("values") or [])
        check("分类下拉里有「集成战略」", "集成战略" in _cats20,
              "%d 项" % len(_cats20))
        _pp20.var_cat.set("集成战略")
        _pp20._on_cat()
        _app20.update()
        _groups20 = list(_pp20.cmb_group.cget("values") or [])
        check("第二层给出 6 个集成战略主题", len(_groups20) == 6,
              "%d 项" % len(_groups20))

        _tot20 = 0
        _all_match20 = True
        _detail20 = []
        for _g20 in _groups20:
            _pp20.var_group.set(_g20)
            _pp20._on_group()
            _app20.update()
            _nts20 = _pp20._node_types
            _c20 = sum(n[2] for n in _nts20)
            _tot20 += _c20
            _detail20.append((_g20.split("（")[0], len(_nts20), _c20))
            # 选第一个节点类型，关卡数应精确等于标称数
            if _nts20:
                _k20, _lab20, _cnt20 = _nts20[0]
                _pp20.var_node.set(_lab20)
                _pp20._on_node()
                _app20.update()
                _got20 = len(list(_pp20.cmb_level.cget("values") or []))
                if _got20 != _cnt20:
                    _all_match20 = False
                    _detail20.append(("  不符", _lab20, _got20, _cnt20))
        check("集成战略 6 主题合计 1033 关", _tot20 == 1033,
              "合计 %d；%s" % (_tot20, _detail20))
        check("每个主题的节点类型筛选后关卡数与标称一致",
              _all_match20, "%s" % (_detail20[-2:],))
        check("节点类型不止一层（有的主题 5 种、有的 7 种）",
              len(set(d[1] for d in _detail20 if isinstance(d[1], int))) >= 2,
              "%s" % [d for d in _detail20 if isinstance(d[1], int)])
    except Exception as _x20:
        check("集成战略两层筛选能跑通", False, "%s" % _x20)

    try:
        _app20.destroy()
    except Exception:
        pass

# ------------------------------- 21. 沙盘真的把地图画出来了 + PRTS 措辞上屏
print("\n[21] 沙盘渲染真的出图、PRTS 措辞真的上屏（不是只有数据层）")

from akcalc.ui.map_canvas import MapCanvas as _MC21  # noqa: E402
from akcalc.core import enemy_skills as _ES21  # noqa: E402

_app21 = None
try:
    _app21 = APP.App()
    # 注意：这里**不能** withdraw()。窗口不可见时 canvas 尺寸是 0，
    # 渲染帧就是一张 1x1 空图，看起来像「没画」——之前就是被这个坑过。
    _app21.geometry("1400x900+30+20")
    _app21.update()
    _app21.update_idletasks()
    _app21.show_view("sandbox")
    _app21.update()
    _sp21 = _app21._sandbox_panel
    _sp21.refresh_stages()
    _app21.update()
except Exception as _e21:
    _sp21 = None
    check("沙盘面板能打开（用于渲染检查）", False, "%s" % _e21)

check("沙盘面板能打开（用于渲染检查）", _sp21 is not None, "")

if _sp21 is not None:
    # 找一个默认可用的关卡并真正载入
    _lbl21 = None
    for _k21, _v21 in (_sp21._stage_index or {}).items():
        if getattr(_v21, "cached", False):
            _lbl21 = _k21
            break
    check("沙盘下拉里有已缓存的关卡可选", _lbl21 is not None, "%r" % _lbl21)
    if _lbl21:
        _sp21.cmb_stage.set(_lbl21)
        _sp21._on_load()
        _app21.update()
        _app21.update_idletasks()

    _cv21 = getattr(_sp21, "canvas", None)
    check("沙盘有 canvas 且是 MapCanvas", isinstance(_cv21, _MC21),
          type(_cv21).__name__)

    if _cv21 is not None:
        # 1) canvas 上只有 1 个 image 图元是**设计如此**：整幅地图由
        #    MapRenderer 用 PIL 烘成一张 PhotoImage 贴上，不是逐个图元画。
        #    所以「画没画」必须看那张图的像素，不能数 find_all()。
        _items21 = _cv21.find_all()
        check("沙盘 canvas 贴了地图图元", len(_items21) >= 1,
              "%d 个" % len(_items21))
        _bb21 = _cv21.bbox("all")
        check("沙盘图元有实际占位（不是零尺寸）",
              bool(_bb21) and (_bb21[2] - _bb21[0]) > 100
              and (_bb21[3] - _bb21[1]) > 100, "%r" % (_bb21,))
        try:
            _im21 = _cv21._r.render().convert("RGB")
            _w21, _h21 = _im21.size
            _cols21 = _im21.getcolors(maxcolors=1 << 24) or []
            _cols21.sort(reverse=True)
            _total21 = _w21 * _h21
            _top21 = _cols21[0][0] if _cols21 else 0
            _ratio21 = 1.0 - (_top21 / float(_total21 or 1))
            check("沙盘渲染帧有内容（不是纯色空图）",
                  len(_cols21) > 8 and _ratio21 > 0.05,
                  "%dx%d 颜色 %d 种，非主色占比 %.1f%%"
                  % (_w21, _h21, len(_cols21), _ratio21 * 100))
        except Exception as _imx21:
            check("沙盘渲染帧有内容（不是纯色空图）", False, "%s" % _imx21)

        # 2) 缩放真的改变了渲染器状态
        try:
            _z021 = float(_cv21._r.zoom)
            _cv21.zoom_by(1.25)
            _app21.update()
            _z121 = float(_cv21._r.zoom)
            check("沙盘缩放真的生效", _z121 > _z021,
                  "zoom %.3f -> %.3f" % (_z021, _z121))
            _cv21.set_zoom(1.0)
            _app21.update()
            check("沙盘缩放能复位", abs(float(_cv21._r.zoom) - 1.0) < 1e-6,
                  "zoom=%.3f" % float(_cv21._r.zoom))
        except Exception as _zx21:
            check("沙盘缩放真的生效", False, "%s" % _zx21)

    # 3) 粗轴：真实对象 + 真的能序列化出关卡 id
    _trk21 = getattr(getattr(_sp21, "sandbox", None), "track", None)
    check("沙盘挂的是 CoarseTrack", type(_trk21).__name__ == "CoarseTrack",
          type(_trk21).__name__)
    if _trk21 is not None:
        check("粗轴带了关卡 id",
              bool(getattr(_trk21, "stage_id", "")),
              "%r" % getattr(_trk21, "stage_id", ""))
        _t21 = _trk21.dumps()
        check("粗轴 dumps 带格式头", '"feiniu-sandbox-track"' in _t21,
              _t21[:90])
        check("粗轴 JSON 里有关卡段", '"stage"' in _t21,
              [ln.strip() for ln in _t21.split("\n") if "stage" in ln][:2])

# 4) PRTS 措辞：技能名与多行效果都必须真的出现在图鉴界面上
import json as _j21  # noqa: E402
try:
    _prts21 = _j21.load(open(r"F:\mini api\akcalc\data\enemy_skills_prts.json",
                             encoding="utf-8"))["skills"]
except Exception as _pe21:
    _prts21 = {}
    check("PRTS 技能库可读", False, "%s" % _pe21)
check("PRTS 技能库可读", bool(_prts21), "%d 个敌人" % len(_prts21))

check("cooldown 被标注为 PRTS 的「消耗」",
      "PRTS 的「技能N消耗」" in _ES21.TIMING_DESC.get("cooldown", ""),
      _ES21.TIMING_DESC.get("cooldown", "")[:60])
check("spCost 被标注为不可当消耗用",
      "会显示一排 0" in _ES21.TIMING_DESC.get("spCost", ""),
      _ES21.TIMING_DESC.get("spCost", "")[:60])

if _app21 is not None and _prts21:
    from akcalc.ui.monster_codex import MonsterCodexDialog as _MCD21  # noqa: E402

    def _txt21(w, acc):
        try:
            _t = w.cget("text")
            if _t:
                acc.append(str(_t))
        except Exception:
            pass
        for _c in w.winfo_children():
            _txt21(_c, acc)
        return acc

    # 爱国者：3 条 PRTS 技能，名字和效果首句都得在界面上
    _eid21 = "enemy_1506_patrt"
    _recs21 = _prts21.get(_eid21) or []
    check("爱国者有多条 PRTS 技能记录", len(_recs21) >= 2,
          "%d 条" % len(_recs21))
    try:
        _dlg21 = _MCD21(_app21, _app21, "爱国者", _eid21, 0)
        _app21.update()
        _dlg21.update()
        _blob21 = "\n".join(_txt21(_dlg21, []))
        _dlg21.destroy()
        _miss_name = [r for r in _recs21
                      if (r.get("name") or "").strip()
                      and (r.get("name") or "").strip() not in _blob21]
        check("PRTS 技能名全部上屏", not _miss_name,
              "缺 %r" % [_m.get("name") for _m in _miss_name][:3])
        _miss_eff = []
        for _r21 in _recs21:
            _head21 = ("" if not _r21.get("effect")
                       else _r21["effect"].split("\n")[0][:16])
            if _head21 and _head21 not in _blob21:
                _miss_eff.append(_head21)
        check("PRTS 技能效果首句全部上屏", not _miss_eff,
              "缺 %r" % _miss_eff[:3])
        check("界面出现「初始」「消耗」两栏",
              "初始" in _blob21 and "消耗" in _blob21, "")
    except Exception as _cx21:
        check("图鉴能打开爱国者", False, "%s" % _cx21)

# 5) 低置信（confident=False）条目不许给出代码注解
_low21 = [(e0, r0) for e0, rs0 in _prts21.items() for r0 in rs0
          if not r0.get("confident")]
check("存在低置信条目（用于验证克制显示）", len(_low21) > 0,
      "%d 条" % len(_low21))
check("低置信条目没有可展示的 prefabKey",
      all(not (r0.get("code") or "").strip() for _e0, r0 in _low21),
      "有 %d 条仍带 code" % sum(1 for _e0, r0 in _low21
                                if (r0.get("code") or "").strip()))

if _app21 is not None:
    try:
        _app21.destroy()
    except Exception:
        pass

# ======================================================================
print("\n[22] 随机候选包（randomSpawnGroupKey）折叠")
# ======================================================================
# 这一组盯的是「多出敌人」这一类投诉的**结构性**成因：同一个
# randomSpawnGroupKey 下的多条 SPAWN 是同一次抽取的备选（按 weight 抽
# 其中一条），全列出来就会把「N 选 1」显示成 N 只。全库 568 个关卡、
# 1354 个包、累计多算约 6900 只；最极端 act1multi_football 一个 ball 包
# 挂 810 个备选（1393 只 vs 实机约 584 只）。
import json as _json22
import os as _os22
from akcalc.core.timeline import parse_timeline as _pt22

_LC22 = _os22.path.join(_os22.path.dirname(_os22.path.abspath(__file__)),
                        "akcalc", "data", "cache", "levels")


def _load22(fn):
    p = _os22.path.join(_LC22, fn)
    if not _os22.path.exists(p):
        return None
    with open(p, encoding="utf-8") as f:
        return _json22.load(f)


_raw22 = _load22("levels_obt_roguelike_ro6_level_rogue6_c-2.json")
check("咩的朋友关卡缓存存在", _raw22 is not None, "缺 rogue6_c-2.json")
if _raw22 is not None:
    _tl22 = _pt22(_raw22)
    _n_all22 = len(_tl22.events)
    _n_fold22 = len(_tl22.fold_random_packs())
    check("咩的朋友事件数 43", _n_all22 == 43, "%d" % _n_all22)
    # 6 个包：g1 是 2 选 1，n1..n5 各是 2 选 1 的 count=2
    # 折叠后 43 -> 32（少 11 只：1 + 5*2）
    check("咩的朋友折叠后 32 只", _n_fold22 == 32, "%d" % _n_fold22)
    _packs22 = _tl22.random_pack_summary()
    check("咩的朋友有 6 个随机包", len(_packs22) == 6, "%d" % len(_packs22))
    check("随机包记录了期望只数",
          all(pk["expect"] < pk["total"] for pk in _packs22),
          str([(pk["group"], pk["total"], pk["expect"]) for pk in _packs22])[:120])
    # 角兽（enemy_1344_ddlamb）折叠后不该翻倍
    _lamb_all = sum(1 for e in _tl22.events if e.enemy_id == "enemy_1344_ddlamb")
    _lamb_fold = sum(1 for e in _tl22.fold_random_packs()
                     if e.enemy_id == "enemy_1344_ddlamb")
    check("角兽全列 20 只", _lamb_all == 20, "%d" % _lamb_all)
    check("角兽折叠后 10 只", _lamb_fold == 10, "%d" % _lamb_fold)

# 足球图：810 个备选一个包
_raw_fb22 = _load22("act1multi_football.json")
if _raw_fb22 is not None:
    _tlfb22 = _pt22(_raw_fb22)
    _fbpacks22 = _tlfb22.random_pack_summary()
    check("足球图有 1 个随机包", len(_fbpacks22) == 1,
          "%d" % len(_fbpacks22))
    if _fbpacks22:
        check("足球图包内有 810 个备选",
              len(_fbpacks22[0]["members"]) == 810,
              "%d" % len(_fbpacks22[0]["members"]))
    _nfb22 = len(_tlfb22.fold_random_packs())
    check("足球图折叠后 584 只", _nfb22 == 584, "%d" % _nfb22)

# 折叠必须是幂等的、且不吞掉非候选包
_tl22b = _pt22(_raw22) if _raw22 is not None else None
if _tl22b is not None:
    _once22 = _tl22b.fold_random_packs()
    check("折叠不丢无包事件",
          all(any(e is x for x in _once22)
              for e in _tl22b.events if not e.random_group),
          "有非候选包事件被丢掉")
    check("折叠结果不含同包重复",
          len({e.random_group for e in _once22 if e.random_group})
          == len({e.random_group for e in _tl22b.events if e.random_group}),
          "有包整包消失")

# effective_events / groups 的 fold_random 开关
if _tl22b is not None:
    _eff_no22 = len(_tl22b.effective_events(fold_random=False))
    _eff_yes22 = len(_tl22b.effective_events(fold_random=True))
    check("effective_events 关折叠时等于不折叠",
          _eff_no22 == _n_all22, "%d vs %d" % (_eff_no22, _n_all22))
    check("effective_events 开折叠时变少",
          _eff_yes22 < _eff_no22, "%d vs %d" % (_eff_yes22, _eff_no22))
    _g_no22 = len(_tl22b.groups(effective=True, fold_random=False))
    _g_yes22 = len(_tl22b.groups(effective=True, fold_random=True))
    check("groups 的 fold_random 生效", _g_yes22 < _g_no22,
          "%d vs %d" % (_g_yes22, _g_no22))

# 沙盘侧：Sandbox.fold_random 控制 events()
try:
    from akcalc.core.sandbox import Sandbox as _SB22
    from akcalc.core.maps import get_level as _gl22
    from akcalc.core.paths import Paths as _P22
    from akcalc.core.maps import LevelCache as _LC22c
    _paths22 = _P22.default()
    _cache22 = _LC22c(_paths22.levels_cache_dir)
    _gm22 = _gl22("ro6_c_2", "roguelike", _cache22,
                  rel_path="levels/obt/roguelike/ro6/level_rogue6_c-2.json")
    check("沙盘测试能取到 ro6_c_2 地图", _gm22 is not None, "get_level 返回 None")
    if _gm22 is not None and _tl22b is not None:
        _sb_no22 = _SB22(_gm22, _tl22b, fold_random=False)
        _sb_yes22 = _SB22(_gm22, _tl22b, fold_random=True)
        check("Sandbox 默认不折叠",
              len(_sb_no22.events()) == _n_all22,
              "%d" % len(_sb_no22.events()))
        check("Sandbox 折叠后事件变少",
              len(_sb_yes22.events()) == _n_fold22,
              "%d vs %d" % (len(_sb_yes22.events()), _n_fold22))
        # 折叠后仍能正常算到达时间（不能因为少了几只就崩）
        _ok22 = True
        try:
            for _e22 in _sb_yes22.events()[:5]:
                _sb_yes22.arrival_time(_e22)
        except Exception as _ex22:
            _ok22 = False
        check("折叠后 arrival_time 仍可用", _ok22, "")
except Exception as _exsb22:
    check("沙盘折叠接口可用", False, "%s" % _exsb22)

# UI 侧：两个面板都有开关，且默认打开
try:
    import akcalc.ui.app as _APP22
    _app22 = _APP22.App()
    _app22.geometry("1400x900+30+20")
    _app22.update()
    _app22.show_view("path")
    _app22.update()
    _pp22 = _app22._path_panel
    check("寻路面板有「按实机编队」开关",
          hasattr(_pp22, "var_effective_only"), "")
    check("寻路面板默认按实机编队",
          bool(_pp22.var_effective_only.get()), "")
    _app22.show_view("sandbox")
    _app22.update()
    _sp22 = _app22._sandbox_panel
    check("沙盘面板有「随机包择一」开关",
          hasattr(_sp22, "var_fold_random"), "")
    check("沙盘默认折叠随机包", bool(_sp22.var_fold_random.get()), "")
    check("沙盘开关有回调", hasattr(_sp22, "_toggle_fold_random"), "")
    try:
        _app22.destroy()
    except Exception:
        pass
except Exception as _exui22:
    check("随机包开关 UI 可用", False, "%s" % _exui22)

# ---------------------------------------------------------------- [23] 无害单位与罚站
print("\n[23] 无害单位折叠 / 预罚站 / 条件出怪标记")
try:
    import akcalc.ui.app as _APP23
    _app23 = _APP23.App()
    _app23.geometry("1400x900+30+20")
    _app23.update()

    # --- 寻路面板：H8-4 的 12 个平民被「撇除无害单位」挡在表外
    _app23.show_view("path")
    _app23.update()
    _pp23 = _app23._path_panel
    _st23 = _app23.stage_catalog.stages.get("hard_08-04")
    check("H8-4 在关卡目录里", _st23 is not None, "")
    if _st23 is not None:
        _d23 = getattr(_st23, "difficulty_label", "")
        _pp23._stages = [_st23]
        _pp23.var_level.set("%s%s %s"
                            % ("●" if getattr(_st23, "cached", False) else "○",
                               "  [%s]" % _d23 if _d23 else "", _st23.label))
        _pp23.load_selected()
        _app23.update()
        _all23 = _pp23.timeline.events
        _harm23 = [e for e in _all23 if getattr(e, "harmless", False)]
        check("H8-4 数据里有 12 个无害单位", len(_harm23) == 12,
              "%d" % len(_harm23))
        _gs23 = _pp23.timeline.groups(
            hostile_only=_pp23.var_hide_harmless.get(),
            effective=_pp23.var_effective_only.get(),
            fold_random=_pp23.var_effective_only.get())
        _shown23 = sum(g.count for g in _gs23)
        check("寻路面板不显示无害单位", not any(g.harmless for g in _gs23),
              "仍有无害混入")
        check("寻路面板显示 39 只（51 - 12 无害）", _shown23 == 39,
              "%d" % _shown23)

        # --- 预罚站：H8-4 的 R0~R3 都是 270s（平民专用停车位）
        _pw23 = {a.route_index: a.pre_wait for a in _pp23.analyses}
        check("H8-4 平民路线有 270s 预罚站",
              all(abs(_pw23.get(i, 0) - 270.0) < 0.5 for i in (0, 1, 2, 3)),
              str([_pw23.get(i) for i in (0, 1, 2, 3)]))
        check("H8-4 平民路线只有 1 个检查点（原地不动）",
              all(len(_pp23.game_map.route_by_index(i).checkpoints or []) == 1
                  for i in (0, 1, 2, 3)), "")
        # E_NUM 占位路线会被丢弃，Route.index 与列表位置不再一致；
        # 这里固定住「确实存在错位」这件事，防止以后改成按下标取。
        _nmis23 = sum(1 for r in _pp23.game_map.routes
                      if r.index >= len(_pp23.game_map.routes))
        check("H8-4 存在 Route.index 与列表位置错位",
              _nmis23 > 0 and len(_pp23.game_map.routes) < 52,
              "路线 %d 条，越界 index %d 个"
              % (len(_pp23.game_map.routes), _nmis23))
        check("route_by_index 能取到越界的那条",
              _pp23.game_map.route_by_index(51) is not None, "")
        check("按列表位置取会拿到别人（证明必须用 route_by_index）",
              _pp23.game_map.routes[0].index == 0
              and _pp23.game_map.route_by_index(38) is not None,
              "")

    # --- 纵怒：3 只领舞者带 120s 预罚站，超出关卡时长
    _st23b = _app23.stage_catalog.stages.get("ro6_c_6")
    check("纵怒在关卡目录里", _st23b is not None, "")
    if _st23b is not None:
        _d23b = getattr(_st23b, "difficulty_label", "")
        _pp23._stages = [_st23b]
        _pp23.var_level.set("%s%s %s"
                            % ("●" if getattr(_st23b, "cached", False) else "○",
                               "  [%s]" % _d23b if _d23b else "",
                               _st23b.label))
        _pp23.load_selected()
        _app23.update()
        _nz23 = [(a.route_index, a.pre_wait) for a in _pp23.analyses
                 if a.pre_wait > 0.5]
        check("纵怒有 3 条 120s 预罚站路线",
              len(_nz23) == 3 and all(abs(w - 120.0) < 0.5 for _r, w in _nz23),
              str(_nz23))
        # 领舞者 9 只；前 3 只到蓝门的时刻超过关卡时长。
        # ⚠ 必须按 Route.index 查分析，不能用 analyses[route_index]：
        # E_NUM 占位路线被丢弃后列表位置 ≠ Route.index（全库 1243 关
        # 存在这种错位），按位置取会静默取到隔壁那条。
        _dnc23 = [e for e in _pp23.timeline.events
                  if e.enemy_id == "enemy_10035_cnvdnc_2"]
        check("纵怒领舞者 9 只", len(_dnc23) == 9, "%d" % len(_dnc23))
        _byidx23 = {a.route_index: a for a in _pp23.analyses}
        _dur23 = float(getattr(_pp23.timeline, "duration", 0.0) or 0.0)
        _late23 = 0
        for _e23 in _dnc23:
            _a23 = _byidx23.get(_e23.route_index)
            if _a23 is None:
                continue
            # total_time 已含 pre_wait，不能再加一遍
            if _e23.time + _a23.total_time > _dur23:
                _late23 += 1
        check("纵怒有 3 只领舞者到得比关卡时长还晚", _late23 == 3,
              "%d" % _late23)
        check("total_time 已含 pre_wait（不重复计）",
              all(abs((_a.pre_wait + _a.move_time + _a.wait_time)
                      - _a.total_time) < 0.01 for _a in _pp23.analyses),
              "")
        # 分支出怪与波次出怪共用 R0：领舞者 + 家族暗影灭迹人
        _r0_23 = [e for e in _pp23.timeline.events if e.route_index == 0]
        check("纵怒 R0 上有 2 条事件（波次 + 分支）", len(_r0_23) == 2,
              "%d" % len(_r0_23))
        # 条件出怪：家族暗影灭迹人来自 vgctrl_bro 分支
        _br23 = [e for e in _pp23.timeline.events if getattr(e, "branch", "")]
        check("纵怒有 1 条分支出怪", len(_br23) == 1, "%d" % len(_br23))
        check("分支出怪标了来源分支",
              bool(_br23) and _br23[0].branch == "vgctrl_bro",
              _br23[0].branch if _br23 else "")
        check("寻路面板有预罚站辅助方法",
              hasattr(_pp23, "_pre_wait_of"), "")
        check("预罚站辅助方法算得对",
              abs(_pp23._pre_wait_of(0) - 120.0) < 0.5,
              "%s" % _pp23._pre_wait_of(0))
        check("无罚站路线返回 0", abs(_pp23._pre_wait_of(12) - 0.0) < 0.5,
              "%s" % _pp23._pre_wait_of(12))

    # --- 沙盘面板：无害单位默认显示（会出场），可手动撇除
    _app23.show_view("sandbox")
    _app23.update()
    _sp23 = _app23._sandbox_panel
    check("沙盘有无害单位开关", hasattr(_sp23, "var_hide_harmless"), "")
    check("沙盘默认不撇除无害单位（它们真的会出场）",
          not bool(_sp23.var_hide_harmless.get()), "")
    check("沙盘有无害单位回调", hasattr(_sp23, "_toggle_harmless"), "")
    check("沙盘有可见事件过滤方法", hasattr(_sp23, "_visible_events"), "")
    _sp23.refresh_stages()
    _app23.update()
    if _st23 is not None:
        _sp23._stage_index[_st23.label] = _st23
        _sp23.cmb_stage.configure(values=list(_sp23._stage_index.keys()))
        _sp23.cmb_stage.set(_st23.label)
        _sp23._on_load()
        _app23.update()
        _n_all23 = len(_sp23.sandbox.events())
        _n_vis23 = len(_sp23._visible_events())
        check("沙盘 H8-4 默认显示全部 51 条", _n_all23 == 51 and _n_vis23 == 51,
              "%d / %d" % (_n_all23, _n_vis23))
        _sp23.var_hide_harmless.set(True)
        _sp23._toggle_harmless()
        _app23.update()
        _n_vis23b = len(_sp23._visible_events())
        _n_harm23 = sum(1 for e in _sp23._visible_events()
                        if getattr(e, "harmless", False))
        check("沙盘撇除后剩 39 条", _n_vis23b == 39, "%d" % _n_vis23b)
        check("沙盘撇除后不含无害单位", _n_harm23 == 0, "%d" % _n_harm23)
        _txt23 = _sp23.lbl_sum.cget("text")
        check("沙盘标签写明撇掉几个", "12" in str(_txt23), str(_txt23))
        _sp23.var_hide_harmless.set(False)
        _sp23._toggle_harmless()
        _app23.update()
        check("沙盘取消撇除后恢复 51 条",
              len(_sp23._visible_events()) == 51,
              "%d" % len(_sp23._visible_events()))
    try:
        _app23.destroy()
    except Exception:
        pass
except Exception as _exui23:
    check("无害单位/罚站 UI 可用", False, "%s" % _exui23)

# ---------------------------------------------------------------- [24] 角兽休憩
# 「咩的朋友角兽罚站时间错误」：角兽的【休憩】时长**不在路线里**，
# 它在敌人天赋 Revive.unmovable_duration（PRTS：默认 150 秒持有自缚），
# 关卡还能覆盖 —— ro6_c_2 把它改成 90 秒。路线 checkpoints 是空数组，
# 所以只看路线会得出「罚站 0 秒」。
print("\n[24] 角兽【休憩】出场罚站")
try:
    from akcalc.core.enemies import (REST_DEFAULT_SECONDS,
                                     spawn_unmovable_default,
                                     spawn_unmovable_of_ref)

    check("角兽默认休憩 150s（PRTS 口径）",
          abs(spawn_unmovable_default("enemy_1303_mhshep") - 150.0) < 0.01,
          "%s" % spawn_unmovable_default("enemy_1303_mhshep"))
    check("亢角兽默认休憩 150s",
          abs(spawn_unmovable_default("enemy_1303_mhshep_2") - 150.0) < 0.01,
          "%s" % spawn_unmovable_default("enemy_1303_mhshep_2"))
    check("私有变体 _b 也认（前缀匹配）",
          abs(spawn_unmovable_default("enemy_1303_mhshep_b") - 150.0) < 0.01,
          "%s" % spawn_unmovable_default("enemy_1303_mhshep_b"))
    check("鬣犄兽不是休憩怪（库默认 150 不能套用）",
          abs(spawn_unmovable_default("enemy_1304_mhwolf") - 0.0) < 0.01,
          "%s" % spawn_unmovable_default("enemy_1304_mhwolf"))
    check("普通敌人没有出场罚站",
          abs(spawn_unmovable_default("enemy_1108_uterer_2") - 0.0) < 0.01,
          "%s" % spawn_unmovable_default("enemy_1108_uterer_2"))
    # 关卡覆盖优先
    _ov90 = {"overwrittenData": {"talentBlackboard": [
        {"key": "Revive.hp_ratio", "value": 0.999},
        {"key": "Revive.unmovable_duration", "value": 90.0}]}}
    check("关卡把角兽覆盖成 90s",
          abs(spawn_unmovable_of_ref(dict(_ov90, id="enemy_1303_mhshep")) - 90.0) < 0.01,
          "%s" % spawn_unmovable_of_ref(dict(_ov90, id="enemy_1303_mhshep")))
    _ov0 = {"overwrittenData": {"talentBlackboard": [
        {"key": "Revive.unmovable_duration", "value": 0.0}]}}
    check("关卡显式写 0 表示本关不休憩",
          abs(spawn_unmovable_of_ref(dict(_ov0, id="enemy_1303_mhshep")) - 0.0) < 0.01,
          "%s" % spawn_unmovable_of_ref(dict(_ov0, id="enemy_1303_mhshep")))

    # 沙盘端到端：动作必须真的停住，而不是只改文案
    _app24 = APP.App()
    _app24.update()
    _app24.show_view("sandbox")
    _app24.update()
    _sp24 = _app24._sandbox_panel
    _sp24.refresh_stages()
    _app24.update()
    _st24 = _app24.stage_catalog.stages.get("ro6_c_2")
    check("咩的朋友在关卡目录里", _st24 is not None, "")
    if _st24 is not None:
        _sp24._stage_index[_st24.label] = _st24
        _sp24.cmb_stage.configure(values=list(_sp24._stage_index.keys()))
        _sp24.cmb_stage.set(_st24.label)
        _sp24._on_load()
        _app24.update()
        _sb24 = _sp24.sandbox
        check("沙盘灌入了出场罚站表",
              abs(_sb24.spawn_wait.get("enemy_1303_mhshep", 0) - 90.0) < 0.01,
              "%s" % _sb24.spawn_wait)
        _hs24 = [e for e in _sb24.events()
                 if e.enemy_id == "enemy_1303_mhshep"]
        check("找得到角兽出怪", len(_hs24) > 0, "%d 条" % len(_hs24))
        if _hs24:
            _e24 = _hs24[0]
            _f0 = _sb24.enemy_flags(_e24, 0.0)
            _f45 = _sb24.enemy_flags(_e24, 45.0)
            _f95 = _sb24.enemy_flags(_e24, 95.0)
            check("t=0 角兽在罚站", _f0["waiting"] and abs(_f0["wait_left"] - 90.0) < 0.01,
                  "%s" % _f0["wait_left"])
            check("t=45 还剩 45s", _f45["waiting"] and abs(_f45["wait_left"] - 45.0) < 0.01,
                  "%s" % _f45["wait_left"])
            check("t=95 罚站已解除", not _f95["waiting"], "%s" % _f95["wait_left"])
            # 0~90s 必须原地不动（文案对了、动作没停 = 假修复）
            _p0 = _sb24.pose_at(_e24, 0.0)
            _pm = _sb24.pose_at(_e24, 60.0)
            check("0~90s 原地不动",
                  _p0 is not None and _pm is not None
                  and abs(_p0[0] - _pm[0]) < 1e-6 and abs(_p0[1] - _pm[1]) < 1e-6,
                  "%s vs %s" % (_p0, _pm))
            _ra24 = _sb24.analysis_for(_e24)
            _arr24 = _sb24.arrival_time(_e24)
            check("arrival_time 含 90s 出场罚站",
                  _arr24 is not None
                  and abs(_arr24 - (90.0 + _ra24.total_time)) < 0.01,
                  "%.1f vs 90+%.1f" % (_arr24 or -1, _ra24.total_time))
            # 粗轴/播放总长必须盖住「罚站 + 走路」，否则动画在敌人刚抬脚
            # 时就结束，看起来还是「没动」——文案对了动画不对，等于没修。
            _total24 = _sp24._track_total()
            _end24 = max(float(e.time) + (float(_sb24.arrival_time(e) or 0.0))
                         for e in _hs24)
            check("粗轴总长盖住最晚到达的角兽",
                  _total24 >= _end24 - 0.01,
                  "%.1f vs %.1f" % (_total24, _end24))
            check("粗轴总长超出 timeline.duration",
                  _total24 > float(_sp24.timeline.duration),
                  "%.1f > %.1f" % (_total24, float(_sp24.timeline.duration)))
    try:
        _app24.destroy()
    except Exception:
        pass
except Exception as _exui24:
    check("角兽休憩可用", False, "%s" % _exui24)

# ------------------------------------------------- [24b] 寻路面板也得一致
# 沙盘显示 90s 而寻路面板显示 0s，就是把矛盾直接摊在用户面前。
# 这里验 `_pre_wait_of` 把「路线预罚站」与「天赋休憩」相加，
# 同时确保纵怒那种纯路线罚站不会被重复叠加。
print("\n[24b] 寻路面板的天赋罚站")
try:
    _app24b = APP.App()
    _app24b.update()
    _app24b.show_view("path")
    _app24b.update()
    _pp24b = _app24b._path_panel

    def _load24b(sid):
        _st = _app24b.stage_catalog.stages.get(sid)
        if _st is None:
            return None
        if _st not in _pp24b._stages:
            _pp24b._stages.append(_st)
        _pp24b.var_level.set(_st.label)
        _pp24b.load_selected()
        _app24b.update()
        return _st

    _s2 = _load24b("ro6_c_2")
    check("咩的朋友能载入寻路面板", _s2 is not None, "")
    if _s2 is not None:
        check("寻路面板建了罚站表",
              abs((getattr(_pp24b, "_spawn_wait", {}) or {})
                  .get("enemy_1303_mhshep", 0) - 90.0) < 0.01,
              "%s" % getattr(_pp24b, "_spawn_wait", None))
        check("路线本身没有预罚站（checkpoints 为空）",
              abs(_pp24b._pre_wait_of(0) - 0.0) < 0.01,
              "%.1f" % _pp24b._pre_wait_of(0))
        check("加上天赋休憩 = 90s",
              abs(_pp24b._pre_wait_of(0, "enemy_1303_mhshep") - 90.0) < 0.01,
              "%.1f" % _pp24b._pre_wait_of(0, "enemy_1303_mhshep"))
        _rows_txt = []
        for _r in getattr(_pp24b, "_spawn_rows", []):
            for _w in _r.winfo_children():
                try:
                    _t = _w.cget("text")
                except Exception:
                    continue
                if _t:
                    _rows_txt.append(str(_t))
        check("出怪表出现「罚站90s」单元",
              any("罚站" in _t and "90" in _t for _t in _rows_txt),
              "%d 个罚站单元格" % len([_t for _t in _rows_txt if "罚站" in _t]))
        try:
            _pp24b._fill_isolate_info(0)
            _det = _pp24b.detail_text.get("1.0", "end")
            check("路线详情写明天赋罚站", "天赋罚站" in _det, "")
            check("路线详情全程含天赋罚站",
                  "103.6" in _det or "103.7" in _det,
                  [x for x in _det.splitlines() if "全程" in x])
        except Exception as _e24b:
            check("路线详情可用", False, "%s" % _e24b)

    # 纵怒是纯路线罚站（120s），不能被天赋表再叠一次
    _s6 = _load24b("ro6_c_6")
    check("纵怒能载入寻路面板", _s6 is not None, "")
    if _s6 is not None:
        check("纵怒没有天赋罚站表",
              not (getattr(_pp24b, "_spawn_wait", {}) or {}),
              "%s" % getattr(_pp24b, "_spawn_wait", None))
        check("纵怒路线罚站仍 120s",
              abs(_pp24b._pre_wait_of(0) - 120.0) < 0.01,
              "%.1f" % _pp24b._pre_wait_of(0))
        check("纵怒合计仍 120s（没被叠加成 210）",
              abs(_pp24b._pre_wait_of(0, "enemy_1283_sgkill_2") - 120.0) < 0.01,
              "%.1f" % _pp24b._pre_wait_of(0, "enemy_1283_sgkill_2"))
    try:
        _app24b.destroy()
    except Exception:
        pass
except Exception as _exui24b:
    check("寻路面板天赋罚站可用", False, "%s" % _exui24b)

# --------------------------------------- [24c] 粗轴总长必须盖住「走完全程」
# `timeline.duration` 只是最后一个**出怪**时刻，几乎每关都短于真正结束
# 时间（main_08-04 163 vs 193、hard_08-04 176 vs 274、
# act1multi_football 80 vs 357）。按出怪时刻收尾 → 动画在敌人半路就停，
# 用户看到的就是「站着不动」。这里逐关卡死这条不变量。
print("\n[24c] 粗轴总长覆盖走完全程（多关抽样）")
try:
    _app24c = APP.App()
    _app24c.update()
    _app24c.show_view("sandbox")
    _app24c.update()
    _sp24c = _app24c._sandbox_panel
    _sp24c.refresh_stages()
    _app24c.update()
    _cases24c = ["main_08-04", "hard_08-04", "ro6_c_2", "ro6_c_6",
                 "act24side_01", "act24side_06", "main_07-16",
                 "main_00-01", "act1multi_football"]
    for _sid in _cases24c:
        _st24c = _app24c.stage_catalog.stages.get(_sid)
        if _st24c is None:
            check("%s 在目录里" % _sid, False, "")
            continue
        _sp24c._stage_index[_st24c.label] = _st24c
        _sp24c.cmb_stage.configure(values=list(_sp24c._stage_index.keys()))
        _sp24c.cmb_stage.set(_st24c.label)
        _sp24c._on_load()
        _app24c.update()
        _sb24c = _sp24c.sandbox
        _tot24c = _sp24c._track_total()
        _end24c = 0.0
        for _e in _sb24c.events():
            _ar = _sb24c.arrival_time(_e)
            if _ar is not None:
                _end24c = max(_end24c, float(_e.time) + _ar)
        check("%s 粗轴 %.1f ≥ 最晚到达 %.1f" % (_sid, _tot24c, _end24c),
              _tot24c >= _end24c - 0.5, "%.1f vs %.1f" % (_tot24c, _end24c))
    try:
        _app24c.destroy()
    except Exception:
        pass
except Exception as _exui24c:
    check("粗轴总长多关可用", False, "%s" % _exui24c)

# ------------- 25. 集成战略第四层下拉：每一项都必须能在索引里找到自己
print("\n[25] 关卡下拉的去重与兜底（同名变体不能互相覆盖，空 label 要兜底）")
try:
    import akcalc.ui.app as _APP25

    _app25 = _APP25.App()
    _app25.geometry("1500x950+30+20")
    _app25.update()
    _app25.show_view("sandbox")
    _app25.update()
    _sp25 = _app25._sandbox_panel
    _sp25.refresh_stages()
    _app25.update()
    _cat25 = _app25.stage_catalog

    # 直接调 _fill_levels，绕开下拉联动，逐主题逐节点核对
    _sp25.cmb_cat.set(_cat25.category_label("roguelike"))
    _sp25._on_cat()
    _app25.update()
    _bad25 = []
    _tiers25 = 0
    for _g25 in _cat25.category_groups("roguelike"):
        _lbl25 = str(getattr(_g25, "label", ""))
        _hit25 = next((v for v in _sp25.cmb_group.cget("values")
                       if str(v).startswith(_lbl25.split("·")[0].strip())), None)
        if _hit25 is None:
            continue
        _sp25.cmb_group.set(_hit25)
        _sp25._on_group()
        _app25.update()
        for _v25 in list(_sp25.cmb_node.cget("values")):
            _sp25.cmb_node.set(_v25)
            _sp25._on_node()
            _app25.update()
            _vals25 = list(_sp25.cmb_stage.cget("values"))
            _tiers25 += 1
            # 三个条件：下拉项无重复、项数等于索引键数、每个键都指向不同关卡
            if len(_vals25) != len(set(_vals25)):
                _bad25.append("%s/%s 下拉有重复项" % (_lbl25[:12], _v25[:10]))
                continue
            if len(_vals25) != len(_sp25._stage_index):
                _bad25.append("%s/%s %d 项 vs %d 键"
                              % (_lbl25[:12], _v25[:10], len(_vals25),
                                 len(_sp25._stage_index)))
                continue
            _sids25 = [getattr(_sp25._stage_index[k], "stage_id", None)
                       for k in _vals25]
            if any(s is None for s in _sids25):
                _bad25.append("%s/%s 有项取不到关卡"
                              % (_lbl25[:12], _v25[:10]))
            elif len(set(_sids25)) != len(_sids25):
                _bad25.append("%s/%s 映射到重复 stage_id"
                              % (_lbl25[:12], _v25[:10]))
    check("集成战略 %d 个档位：下拉项与索引一一对应" % _tiers25,
          not _bad25 and _tiers25 >= 35, str(_bad25[:5]))

    # IS4 险路恶敌：21 关必须全在，且 ro4_b_4 / ro4_b_4_c 各自单独可达
    _sp25.cmb_group.set(next(v for v in _sp25.cmb_group.cget("values")
                             if str(v).startswith("IS4")))
    _sp25._on_group()
    _app25.update()
    _sp25.cmb_node.set(next(v for v in _sp25.cmb_node.cget("values")
                            if v.startswith("险路恶敌")))
    _sp25._on_node()
    _app25.update()
    check("IS4 险路恶敌 21 关全在索引里",
          len(_sp25._stage_index) == 21, str(len(_sp25._stage_index)))
    _map25 = {}
    for _v25 in _sp25.cmb_stage.cget("values"):
        _st25 = _sp25._stage_index.get(_v25)
        _map25[getattr(_st25, "stage_id", "")] = _v25
    check("ro4_b_4 与 ro4_b_4_c 都能单点",
          "ro4_b_4" in _map25 and "ro4_b_4_c" in _map25
          and _map25["ro4_b_4"] != _map25["ro4_b_4_c"],
          "%r / %r" % (_map25.get("ro4_b_4"), _map25.get("ro4_b_4_c")))
    # 真的载入其中一个，确认取到的是它自己（不是被覆盖后的兄弟关）
    _pick25 = _map25.get("ro4_b_4_c")
    if _pick25:
        _sp25.cmb_stage.set(_pick25)
        _sp25._on_load()
        _app25.update()
        check("选中 ro4_b_4_c 载入的就是 ro4_b_4_c",
              getattr(_sp25.stage, "stage_id", None) == "ro4_b_4_c",
              str(getattr(_sp25.stage, "stage_id", None)))

    # 空 label 兜底：ro4_b_9 的 label 是空格，不能显示成「● 」
    check("ro4_b_9 有可读显示名",
          "ro4_b_9" in _map25
          and len(_map25["ro4_b_9"].replace("●", "").replace("○", "").strip())
          >= 2, repr(_map25.get("ro4_b_9")))
    # 全库不应有空白显示名
    _sp25._fill_levels(list(_cat25.stages.values()))
    _app25.update()
    _blank25 = [v for v in _sp25.cmb_stage.cget("values")
                if not v.replace("●", "").replace("○", "").strip()]
    check("全库 %d 关没有空白显示名" % len(_cat25.stages), not _blank25,
          str(_blank25[:3]))

    try:
        _app25.destroy()
    except Exception:
        pass
except Exception as _exui25:
    check("关卡下拉去重与兜底", False, "%s" % _exui25)

# ------- 26. 出怪表切换关卡不能残留控件；零出怪的提示要说准为什么
print("\n[26] 出怪表不残留旧控件 + 零出怪必须说准原因")
try:
    import akcalc.ui.app as _APP26

    _app26 = _APP26.App()
    _app26.geometry("1500x950+30+20")
    _app26.update()
    _app26.show_view("path")
    _app26.update()
    _pp26 = _app26._path_panel
    _cat26 = _app26.stage_catalog

    def _ui_load26(_sid):
        _st = _cat26.stages.get(_sid)
        if _st is None:
            return None
        _pp26._stages = [_st]
        _mk = "●" if getattr(_st, "cached", False) else "○"
        _tg = "  [%s]" % _st.difficulty_label if _st.difficulty_label else ""
        _tx = "%s%s %s" % (_mk, _tg, _st.label)
        _pp26.cmb_level.configure(values=[_tx])
        _pp26.var_level.set(_tx)
        _pp26.load_selected()
        _app26.update()
        return len(_pp26.spawn_host.winfo_children())

    # 同一关连点 5 次：子控件数必须恒定（以前 8→9→10→11→12 一路涨）
    _seq26 = [_ui_load26("main_00-01") for _i in range(5)]
    check("同一关反复加载，出怪表控件数恒定", len(set(_seq26)) == 1,
          str(_seq26))
    # 正常关 ↔ 空提示关 来回切，各自仍恒定
    _a26 = [_ui_load26("main_00-01") for _i in range(3)]
    _b26 = [_ui_load26("act15mini_01") for _i in range(3)]
    check("正常关与空提示关来回切不累积",
          len(set(_a26)) == 1 and len(set(_b26)) == 1,
          "%r / %r" % (_a26, _b26))
    # 空提示文案只应有一份
    _ui_load26("act15mini_01")
    _n26 = 0
    for _w in _pp26.spawn_host.winfo_children():
        try:
            if "isValid" in str(_w.cget("text")):
                _n26 += 1
        except Exception:
            pass
    check("空出怪提示只出现一份", _n26 == 1, "找到 %d 份" % _n26)

    # 零出怪（完全没有 SPAWN）的关卡：提示必须说准成因，不能一律说
    # 「纯演出/机制关」。act*enemyduel_* 走的是 ACTIVATE_PREDEFINED，
    # 敌人（36~70 个）在预置字段里，说「本就不出怪」是错的。
    _ui_load26("act1enemyduel_02a")
    _r26 = _pp26._empty_spawn_reason()
    check("预置激活关说明是「预置激活」而非「本就不出怪」",
          "预置激活" in _r26 and "本就不出怪" not in _r26, _r26[:60])
    check("预置激活关报出了正确条数", "43 条" in _r26, _r26[:40])
    # 真正没有动作的关仍走「纯演出」措辞
    _ui_load26("act1enemyduel_01b")
    _r26b = _pp26._empty_spawn_reason()
    check("无动作的关仍说「没有任何出怪动作」",
          "没有任何出怪动作" in _r26b, _r26b[:60])
    # 只有 STORY 的关要说清只有剧情动作 + 敌人数
    _ui_load26("act1enemyduel_01a")
    _r26c = _pp26._empty_spawn_reason()
    check("只有剧情的关说清了 STORY 与敌人数",
          "STORY" in _r26c and "36" in _r26c, _r26c[:70])
    # 全部禁用（有事件但全废）仍走 isValid 措辞
    _ui_load26("act15mini_07")
    _r26d = _pp26._empty_spawn_reason()
    check("全禁用关仍说 isValid=false", "isValid=false" in _r26d, _r26d[:50])

    try:
        _app26.destroy()
    except Exception:
        pass
except Exception as _exui26:
    check("出怪表残留与零出怪说明", False, "%s" % _exui26)

print("\n" + "=" * 60)
print("通过 %d 项，失败 %d 项" % (len(OK), len(FAIL)))
if FAIL:
    print("失败项:")
    for f in FAIL:
        print("  -", f)
sys.exit(1 if FAIL else 0)
