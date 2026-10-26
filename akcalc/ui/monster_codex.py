# -*- coding: utf-8 -*-
"""怪物图鉴弹窗：展示单个敌人的特性、技能与各种抗性。

在路线分析右侧点击怪物图标时弹出。图标来自 PRTS（带磁盘缓存），
数据来自本地敌人库，断网时仍能显示文字，只是图标位置留占位。
"""
from __future__ import annotations

import json
import os
import re
import tkinter as tk
from typing import List

from ..core import enemy_codex as EC
from ..core import enemy_icons as EI
from .widgets import (ACCENT, ACCENT_SOFT, ACCENT_TXT, BG, BG_DEEP, BG_PANEL, BG_SUNKEN,
                      BORDER, DIVIDER, FG, FG_DIM, FONT_NUM, FONT_UI, FS_BODY,
                      FS_H1, FS_MICRO, FS_SMALL, PAD_L, PAD_M, PAD_S, PAD_XS,
                      WARN, ScrollFrame)

_ICON_PX = 128

#: 档案条目开头若是「【技能名】…」，把技能名抽出来当标题。
#: 「日冕 + 狂暴」会写成「【日冕】\n【狂暴】●15 ●15 + /」这种两段式，
#: 这里只认第一个【】，其余部分留给正文。
_SKILL_NAME_RE = re.compile(r"^【([^】]{1,24})】\s*(.*)$", re.S)

#: 档案文本里的富文本标签：<$ba.buffres>抵抗</> → 抵抗。
#: 不剥掉的话界面上会直接显示尖括号标签，很难看。
_CLEAN_TAG_RE = re.compile(r"</?[^>]{0,24}>")


#: 描述里的关键词 → 该技能在黑板上必然出现的 key。
#: 用来把「文案」和「逻辑」配对，因为两份数据之间没有任何 id 互引。
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


def _board_sig(code: dict) -> tuple:
    """一个技能参数表的「指纹」，用来判断两个技能是不是同一套数值。

    「本体」和「狂暴/二阶段」形态在解包数据里通常是两张独立的 skills
    条目，但 blackboard 逐字相同，只有 prefabKey 多了 ``[Half]`` 之类
    的后缀。配对时需要把它们视为同一套数值，否则会互相抢位置。
    """
    bb = code.get("blackboard") or []
    return tuple((str(k), round(float(v), 3) if isinstance(v, (int, float))
                  else str(v)) for k, v, _s in bb)


def _pair_skills(named, codes) -> dict:
    """把「档案里的技能名」和「解包里的技能代码」尽量配成对。

    为什么需要「尽量」：这两份数据**在两个不同的文件里**
    （``enemy_handbook_table.json`` 的 ``abilityList`` 是文案，
    ``enemy_database.json`` 的 ``skills[]`` 是逻辑），文件之间
    **没有任何 id 互相引用**，官方自己也没建立映射。

    所以用两层锚点，从强到弱：

    1. **共现数值**——描述里写「持续 30.5s」，代码里恰好有
       ``dragon_fire.duration = 30.5``，这两个基本可以确定是同一个技能；
    2. **语义关键词**——描述写「持续受到逐渐递增的真实伤害」，代码里
       带 ``duration``/``interval`` 这类 DOT 参数的就更可能是它；写
       「半径 2.5 范围内」则更可能对应带 ``range_radius`` 的那个。

    配不上的**就不配**，代码块保持单列。宁可留白也不瞎配——
    配错比不配更糟，用户会拿它当结论。

    返回值把「置信度」也带出来：``{id(item): (code, 是否高置信)}``。
    有数值锚点才算高置信（``↳``），只有语义推测的标成 ``≈``，
    让用户一眼看出哪条是证据、哪条是猜的。
    """
    out = {}
    if not named or not codes:
        return out

    # 每个代码块的「参数名集合」与「数值集合」
    keys_by_code, nums_by_code = [], []
    for c in codes:
        ks, vs = set(), set()
        for key, val, _vs in (c.get("blackboard") or []):
            ks.add(str(key).lower())
            try:
                vs.add(round(float(val), 3))
            except (TypeError, ValueError):
                pass
        keys_by_code.append(ks)
        nums_by_code.append(vs)

    taken = set()
    #: 指纹 -> 抢到它的技能名 id 列表，用于事后发现「两个名字抢一套参数」
    groups_wanted: dict = {}
    for item in named:
        txt = " ".join(item.get("lines") or "")
        low = txt.lower()

        # ---- 锚点 1：共现数值（强证据）
        want = set()
        for m in re.finditer(r"(\d+(?:\.\d+)?)", txt):
            try:
                want.add(round(float(m.group(1)), 3))
            except ValueError:
                pass

        # ---- 锚点 2：关键词命中数（弱证据）
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
            # 同分时的平局决胜：优先**不带变体后缀**的那个。
            # 「狂暴/二阶段」形态（DragonFire[Half]、CircleAttack2）的
            # blackboard 和本体逐字相同，打分必然并列；档案里写的是本体
            # 技能，所以这里让本体赢。
            variant = 1 if re.search(r"[\[0-9]", str(codes[i].get("key") or "")) else 0
            scored.append((score, numeric, -variant, i))
        if not scored:
            continue
        scored.sort(reverse=True)
        best_score, best_num, _neg, best_i = scored[0]
        # 「第二名」必须排除**参数指纹相同**的变体，否则
        # 「本体 + [Half]/2」这种成对出现的技能永远打成平局、永远配不上。
        # 分组而不是逐个比较：同一组里谁排第一已经由 -variant 决定。
        best_sig = _board_sig(codes[best_i])
        runner = 0.0
        for sc, _num, _n, j in scored[1:]:
            if _board_sig(codes[j]) == best_sig:
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

    # ---- 冲突回收：两个不同的技能名抢同一套参数 → 谁都不给
    #
    # 典型例子：「锏」的档案里既有【肆虐风雪】（造成范围物理伤害）又有
    # 【瞬息杀机】（清空范围内技力），而解包那边 CircleAttack /
    # CircleAttack2 的 blackboard 完全一样（atk_scale + range_radius），
    # 光看参数根本分不出哪个对应哪个。这时候**两条都标成未配对**，
    # 让代码块单列展示——两个都猜错，不如老实说分不开。
    for sig, owners in groups_wanted.items():
        if len(owners) > 1:
            for oid in owners:
                out.pop(oid, None)
    return out


#: PRTS 把形态写进技能名（``纬地经天[第一形态][第二形态]``、
#: ``角力对决[初始模式]``），档案里只写裸名。去掉这些后缀再比对。
_BARE_NAME_RE = re.compile(r"[\[［][^\]］]{0,12}[\]］]")


#: PRTS 映射表缓存：``{enemy_id: {技能名: (code, confident)}}``
_PRTS_MAP_CACHE: dict = {"key": None, "data": {}}


def _prts_skill_map(app) -> dict:
    """读 ``data/enemy_skills_prts.json``（由 tools/gen_enemy_skills_prts.py 生成）。

    这份表是**外部权威数据**：解包和档案两个文件之间没有 id 互引，
    靠启发式最多只能配上三成。PRTS 敌人页把「技能名 + 初始 + 消耗」
    写在一起，而「初始冷却」在解包里是唯一的强锚点，两边对一遍就能
    把名字钉到 ``prefabKey`` 上。

    走 ``app._read_bundled_json`` 而不是自己拼路径：那个函数同时认识
    开发期的 ``akcalc/data`` 和打包后的 ``_MEIPASS``。文件不存在时
    返回空字典，界面自动退回纯启发式，不报错。
    """
    key = id(app)
    if _PRTS_MAP_CACHE["key"] == key:
        return _PRTS_MAP_CACHE["data"]
    data = {}
    try:
        raw = app._read_bundled_json("enemy_skills_prts.json") or {}
    except Exception:                                       # noqa: BLE001
        raw = {}
    for eid, items in (raw.get("skills") or {}).items():
        per = {}
        for it in items or []:
            nm = str(it.get("name") or "").strip()
            code = str(it.get("code") or "").strip()
            if nm and code:
                per[nm] = (code, bool(it.get("confident")))
        if per:
            data[str(eid)] = per
    _PRTS_MAP_CACHE["key"] = key
    _PRTS_MAP_CACHE["data"] = data
    return data


def _strip_named(sections) -> list:
    """从 ``handbook.sections()`` 里剔掉带【技能名】的条目。

    带【名】的走「技能」卡的 PRTS 排版（名字 + 冷却圆点 + 代码注解），
    不带【名】的是「免疫冻结」「攻击无视更多防御力」这类特性散句，
    留在「特性 / 技能描述」卡里。两边各管一段，避免同一句话出现两次。
    """
    out = []
    for sec in sections or []:
        keep = []
        for ln in sec.get("lines") or []:
            txt = str(ln.get("text") or "").strip()
            if not txt or _SKILL_NAME_RE.match(txt):
                continue
            keep.append(ln)
        if keep:
            out.append({"title": sec.get("title") or "", "lines": keep})
    return out


class MonsterCodexDialog(tk.Toplevel):
    """一只怪物的图鉴。"""

    def __init__(self, master, app, enemy_name: str, enemy_id: str = "",
                 level: int = 0):
        super().__init__(master)
        self.app = app
        self.enemy_name = enemy_name or ""
        self.enemy_id = enemy_id or ""
        self.level = int(level or 0)
        self._photo = None
        self._entry = None

        self._collect()
        # 调用方有时只给 enemy_id（数据字段图鉴就是这样），名字得自己补，
        # 否则标题栏与正文都显示「未知敌人」。
        if not self.enemy_name:
            nm = ""
            if self._entry:
                nm = str(self._entry.get("name") or "")
            if not nm:
                try:
                    nm = self._handbook().display_name(self.enemy_id)
                except Exception:
                    nm = ""
            if not nm and self.enemy_id:
                nm = self.enemy_id
            self.enemy_name = nm
        self.configure(background=BG)
        self.transient(master)
        self.minsize(560, 520)
        self.title("怪物图鉴 · %s" % (self.enemy_name or "未知"))
        self._build()
        self._center(620, 640)
        # 二次弹窗顶部（标题栏）以前是系统白底，跟主界面深色主题很不搭。
        # style_dialog 会把标题栏刷成深色并去掉左上角多余的菜单。
        try:
            from .widgets import style_dialog
            style_dialog(self)
        except Exception:
            pass
        self.protocol("WM_DELETE_WINDOW", self.close)
        self.bind("<Escape>", lambda e: self.close())

    # ------------------------------------------------------------ 数据

    def _collect(self) -> None:
        lib = getattr(self.app, "enemy_lib", None)
        if lib is None or not getattr(lib, "loaded", False):
            return
        entries = lib.by_id.get(self.enemy_id) if self.enemy_id else None
        if not entries and self.enemy_name:
            # 名字反查 id：路线的名字来自 enemy_names.json，未必带 id
            for eid, ents in lib.by_id.items():
                if not ents:
                    continue
                ed = ents[0].get("enemyData") or {}
                nm = EC._clean(str(EC._mv(ed.get("name"), "") or ""))
                if nm == self.enemy_name:
                    entries, self.enemy_id = ents, eid
                    break
        if entries:
            self._entry = EC.codex_entry(entries, self.level, self.enemy_id)

    # -------------------------------------------------------- 图鉴文本

    def _handbook(self):
        """懒取 ``HandbookIndex``（进程内复用一份）。"""
        hb = getattr(self.app, "_handbook_index", None)
        if hb is None:
            from ..core.handbook import HandbookIndex
            try:
                path = self.app.paths.handbook_cache
            except Exception:
                path = ""
            hb = HandbookIndex(path)
            hb.load()
            try:
                self.app._handbook_index = hb
            except Exception:
                pass
        return hb

    def _raw_entries(self) -> List[dict]:
        """本地敌人库里该 id 的全部原始 entry（用于取技能代码）。"""
        lib = getattr(self.app, "enemy_lib", None)
        if lib is None or not getattr(lib, "loaded", False):
            return []
        return list(lib.by_id.get(self.enemy_id) or [])

    def _skill_codes(self) -> List[dict]:
        """从原始 entry 里取技能代码（prefabKey + 冷却 + blackboard）。

        取「技能最多」的那一档：同一 enemy_id 有多档（0/1/2 级）时，
        基础档往往带全套技能，高等级档反而是空的。
        """
        best: List[dict] = []
        for e in self._raw_entries():
            ed = e.get("enemyData") or {}
            sks = [s for s in (ed.get("skills") or []) if isinstance(s, dict)]
            if len(sks) > len(best):
                best = sks
        out = []
        for sk in best:
            bb = []
            for item in (sk.get("blackboard") or []):
                if not isinstance(item, dict):
                    continue
                key = item.get("key") or ""
                if not key:
                    continue
                val = item.get("value")
                bb.append((key, val, item.get("valueStr")))
            out.append({
                "key": str(sk.get("prefabKey") or sk.get("key") or ""),
                "cooldown": sk.get("cooldown"),
                "init": sk.get("initCooldown"),
                "sp_cost": sk.get("spCost"),
                "blackboard": bb,
                "raw": sk,
            })
        return out


    # ------------------------------------------------------------ 界面

    def _build(self) -> None:
        head = tk.Frame(self, background=BG_PANEL, highlightthickness=1,
                        highlightbackground=DIVIDER)
        head.pack(fill="x")

        bar = tk.Frame(head, background=BG_PANEL)
        bar.pack(fill="x", padx=PAD_L, pady=(PAD_S, 2))
        tk.Label(bar, text="怪物图鉴", background=BG_PANEL, foreground=ACCENT,
                 font=(FONT_UI, FS_SMALL)).pack(side="left")

        titlerow = tk.Frame(head, background=BG_PANEL)
        titlerow.pack(fill="x", padx=PAD_L, pady=(0, PAD_M))

        # 图标
        self.icon_canvas = tk.Canvas(titlerow, width=_ICON_PX, height=_ICON_PX,
                                     background=BG_SUNKEN,
                                     highlightthickness=1,
                                     highlightbackground=BORDER, bd=0)
        self.icon_canvas.pack(side="left", padx=(0, PAD_M))
        self._load_icon()

        tbox = tk.Frame(titlerow, background=BG_PANEL)
        tbox.pack(side="left", fill="both", expand=True)
        tk.Label(tbox, text=self.enemy_name or "未知敌人", background=BG_PANEL,
                 foreground=FG, font=(FONT_UI, FS_H1, "bold"),
                 wraplength=330, justify="left", anchor="w").pack(
            fill="x", anchor="w")
        if self.enemy_id:
            tk.Label(tbox, text=self.enemy_id, background=BG_PANEL,
                     foreground=FG_DIM, font=(FONT_NUM, FS_SMALL)).pack(
                anchor="w", pady=(2, 0))

        body = ScrollFrame(self)
        body.pack(fill="both", expand=True, padx=PAD_L, pady=PAD_M)

        if not self._entry:
            tk.Label(body.inner, text="尚未下载敌人数据，无法显示图鉴内容。\n"
                                "到设置里更新一次数据即可。",
                     background=BG, foreground=FG_DIM,
                     font=(FONT_UI, FS_BODY), justify="left").pack(anchor="w")
            return

        e = self._entry
        if e.get("desc"):
            self._card(body.inner, "特性 / 描述", [e["desc"]], wrap=True)

        # ------------------------------------------------------ 档案文本
        # 这一段才是「人话」。旧版图鉴只有一行 description（一句话简介），
        # 技能栏又只有 prefabKey + 冷却这种代码味的东西，用户根本不知道
        # 一个敌人到底会干什么。excel/enemy_handbook_table.json 的
        # abilityList 是游戏内「敌人档案」原文，按 TITLE/NORMAL/SILENCE
        # 折成小标题 + 条目，直接搬过来。
        #
        # 注意分工：带【技能名】的条目归下面的「技能」卡统一渲染
        # （那里才有 PRTS 样式的名字 + 圆点 + 代码注解），这里只放
        # 特性类的散句。否则同一句话会在界面上出现两次。
        hb = self._handbook()
        secs = hb.sections(self.enemy_id) if hb.loaded else []
        secs_plain = _strip_named(secs)
        if secs_plain:
            self._ability_card(body.inner, secs_plain)
        elif not hb.loaded and hb.error:
            self._card(body.inner, "特性 / 技能描述",
                       ["缺少敌人档案数据（enemy_handbook_table.json），"
                        "到设置里更新一次数据即可显示技能描述。"],
                       wrap=True)
        self._dmg_card(body.inner, hb)

        stats = ["%s  %s" % (k, v) for k, v in e["stats"]]
        self._card(body.inner, "基础面板", stats, columns=2)

        if e.get("immunes"):
            self._card(body.inner, "免疫", ["、".join(e["immunes"])], color=ACCENT)

        res = ["%s  %s" % (k, v) for k, v in e["resists"]]
        if e.get("extra"):
            res += ["%s  %s" % (k, v) for k, v in e["extra"]]
        self._card(body.inner, "抗性", res, columns=2)

        # 「技能（数值摘要）」只在**没有**档案技能文本时兜底。
        # 有档案的时候它和下面的「技能」卡说的是同一件事，两份都摆出来
        # 属于重复噪音（而且摘要里的 prefabKey 口语化很差）。
        codes = self._skill_codes()
        if e.get("skills") and not codes:
            self._card(body.inner, "技能（数值摘要）", e["skills"], wrap=True)
        if codes:
            self._skill_code_card(body.inner, codes)
        if e.get("talent"):
            self._card(body.inner, "天赋 / 光环", [e["talent"]], wrap=True)

        foot = tk.Frame(body.inner, background=BG)
        foot.pack(fill="x", pady=(PAD_S, 0))
        meta = "行动方式 %s　｜　掉血 %d　｜　等级 %d" % (
            e.get("motion") or "—", e.get("life_cost") or 0, e.get("level") or 0)
        tk.Label(foot, text=meta, background=BG, foreground=FG_DIM,
                 font=(FONT_UI, FS_SMALL)).pack(side="left")
        link = tk.Label(foot, text="PRTS 详情  ↗", background=BG,
                        foreground=ACCENT, font=(FONT_UI, FS_SMALL),
                        cursor="hand2")
        link.pack(side="right")
        link.bind("<Button-1>", lambda ev: self._open_prts())

    def _ability_card(self, master, sections) -> None:
        """渲染 abilityList 折好的小标题 + 条目（PRTS 风格）。"""
        card = tk.Frame(master, background=BG_PANEL, highlightthickness=1,
                        highlightbackground=DIVIDER)
        card.pack(fill="x", pady=(0, PAD_S))
        head = tk.Frame(card, background=BG_PANEL)
        head.pack(fill="x", padx=PAD_M, pady=(PAD_S, 2))
        tk.Label(head, text="特性 / 技能描述", background=BG_PANEL,
                 foreground=ACCENT, font=(FONT_UI, FS_SMALL, "bold")).pack(side="left")
        tk.Label(head, text="来源：敌人档案 abilityList", background=BG_PANEL,
                 foreground=FG_DIM, font=(FONT_UI, FS_MICRO)).pack(side="right")

        for sec in sections:
            box = tk.Frame(card, background=BG_PANEL)
            box.pack(fill="x", padx=PAD_M, pady=(PAD_XS, 0))
            if sec.get("title"):
                tk.Label(box, text="◆ " + sec["title"], background=BG_PANEL,
                         foreground=ACCENT_TXT,
                         font=(FONT_UI, FS_SMALL, "bold"),
                         anchor="w", justify="left").pack(fill="x")
            for ln in sec["lines"]:
                row = tk.Frame(box, background=BG_PANEL)
                row.pack(fill="x", padx=(PAD_S, 0), pady=(1, 0))
                tk.Label(row, text="·", background=BG_PANEL,
                         foreground=FG_DIM,
                         font=(FONT_UI, FS_BODY)).pack(side="left",
                                                       anchor="n")
                tk.Label(row, text=ln["text"], background=BG_PANEL,
                         foreground=FG, font=(FONT_UI, FS_BODY),
                         anchor="w", justify="left", wraplength=430).pack(
                    side="left", fill="x", expand=True)
                if ln.get("silence"):
                    tk.Label(row, text="可沉默", background=BG_PANEL,
                             foreground=WARN, font=(FONT_UI, FS_MICRO)).pack(
                        side="right", padx=(PAD_XS, 0))
        tk.Frame(card, background=BG_PANEL, height=2).pack(fill="x",
                                                            pady=(0, PAD_S))

    def _dmg_card(self, master, hb) -> None:
        """攻击伤害类型 / 种族 / 标签（手册里的元信息）。"""
        from ..core import handbook as HB
        items = []
        dt = HB.damage_text(hb.damage_types(self.enemy_id)) if hb.loaded else ""
        if dt:
            items.append(("攻击伤害", dt))
        race = hb.race(self.enemy_id) if hb.loaded else ""
        if race:
            items.append(("种族", race))
        tags = hb.tags(self.enemy_id) if hb.loaded else []
        if tags:
            items.append(("标签", "、".join(tags)))
        if not items:
            return
        self._card(master, "分类", ["%s  %s" % (k, v) for k, v in items],
                   columns=2)

    def _skill_code_card(self, master, codes) -> None:
        """技能：PRTS 样式的人话 + 旁边的解包代码注解。

        以前这里只有 ``prefabKey + blackboard`` 这种纯代码，用户看不懂
        一个敌人到底会干什么。PRTS 的敌人页是「技能名 + 冷却/初始/消耗
        三个圆点 + 一句人话描述」，这里照那个样式排：

            ┌ 日冕 ─────────────────────────────────┐
            │  ●40  ○40  ✦/        ← 冷却/初始/消耗 │
            │  对半径2.5内所有我方单位造成100%法术伤害│
            └───────────────────────────────────────┘
               ↳ 代码注解：DanceFire  cooldown=40 …

        人话描述来自 enemy_handbook_table.json 的 abilityList；代码注解
        来自 enemy_database.json 的 skills[]。两者**本来是两个文件**，
        这里按顺序并排显示，并在无法配对时明确说明为什么配不上。
        """
        card = tk.Frame(master, background=BG_PANEL, highlightthickness=1,
                        highlightbackground=DIVIDER)
        card.pack(fill="x", pady=(0, PAD_S))
        head = tk.Frame(card, background=BG_PANEL)
        head.pack(fill="x", padx=PAD_M, pady=(PAD_S, 2))
        tk.Label(head, text="技能", background=BG_PANEL, foreground=ACCENT,
                 font=(FONT_UI, FS_SMALL, "bold")).pack(side="left")
        btn = tk.Button(head, text="查看原始 JSON", relief="flat",
                        background=BG_DEEP, foreground=ACCENT,
                        activebackground=BG_PANEL, activeforeground=ACCENT,
                        font=(FONT_UI, FS_MICRO), highlightthickness=1,
                        highlightbackground=BORDER, cursor="hand2",
                        padx=8, pady=0, command=self._open_skill_json)
        btn.pack(side="right")

        # ---- 人话描述：从档案里抽出带【】的技能名，按名归组
        named, plain = self._skill_texts()
        # 先问 PRTS 映射表（权威）；问不到再走启发式
        prts = _prts_skill_map(self.app).get(self.enemy_id) or {}
        pairs = self._pair_with_prts(named, codes, prts)
        if named:
            for item in named:
                hit = pairs.get(id(item))
                code, sure = (hit if hit else (None, False))
                self._prts_skill_block(card, item["name"], item.get("lines"),
                                       code=code, annotate=True, sure=sure)
        # ---- 剩余代码（没配上人话技能的）单列
        used = {id(c) for c, _s in pairs.values() if c is not None}
        codes_left = [c for c in codes if id(c) not in used]
        if codes_left:
            tk.Label(card, text="解包技能代码（enemyData.skills）",
                     background=BG_PANEL, foreground=FG_DIM,
                     font=(FONT_UI, FS_MICRO), anchor="w").pack(
                fill="x", padx=PAD_M, pady=(PAD_S, 0))
            for code in codes_left:
                self._code_block(card, code)

        tk.Frame(card, background=BG_PANEL, height=2).pack(fill="x",
                                                            pady=(0, PAD_S))

    # ---------------------------------------------------------- 技能人话

    def _pair_with_prts(self, named, codes, prts) -> dict:
        """PRTS 映射优先，剩下的再交给启发式。

        分层是刻意的：

        1. **PRTS 命中的**直接采用，标记为高置信（``↳``）——它的锚点是
           「初始冷却」这个精确数值，比任何关键词都硬；
        2. **PRTS 没覆盖的**名字，才退回 :func:`_pair_skills` 的数值/语义
           启发式，按它自己的置信度标 ``↳``/``≈``；
        3. 两边都没配上的，保持单列代码块。

        名字匹配要**容错后缀**：PRTS 把形态写进了技能名里
        （``纬地经天[第一形态][第二形态]``、``角力对决[初始模式]``），
        而档案里只有 ``纬地经天``。所以先按原名精确匹配，不中再按
        「去掉所有 ``[...]`` 后缀」的裸名找。裸名有多个候选时，
        只有**所有候选指向同一个 prefabKey** 才敢用，否则放弃。
        """
        out = {}
        if not named or not codes:
            return out
        # 代码字典里的字段名是 ``key``（见 ``_skill_codes``：它把
        # ``prefabKey`` 归一化成了 ``key``），不是 ``prefabKey``。
        by_key = {}
        for c in codes:
            key = str(c.get("key") or c.get("prefabKey") or "")
            if key:
                by_key.setdefault(key, c)

        # 裸名索引：去掉 [..] 后缀后 -> {code: (sure 聚合)}
        naked = {}
        for full, (code, sure) in prts.items():
            base = _BARE_NAME_RE.sub("", full).strip()
            if not base:
                continue
            slot = naked.setdefault(base, {})
            # 同一个裸名下出现多个不同 code 就记成冲突（置 None）
            if code in slot:
                slot[code] = slot[code] or sure
            else:
                slot[code] = sure if code not in slot else None
            if len(slot) > 1:
                for k in list(slot):
                    slot[k] = None

        left_named = []
        taken = set()
        for item in named:
            nm = str(item.get("name") or "").strip()
            hit = prts.get(nm)
            if hit is None:
                cand = naked.get(_BARE_NAME_RE.sub("", nm).strip()) or {}
                real = {k: v for k, v in cand.items() if v is not None}
                if len(real) == 1:
                    hit = next(iter(real.items()))
            if not hit:
                left_named.append(item)
                continue
            key, sure = hit
            code = by_key.get(key)
            if code is None:
                # PRTS 说有这个技能，但当前 level 的解包数据里没有这个
                # prefabKey（比如不同难度的档位不一样），不算配对。
                left_named.append(item)
                continue
            out[id(item)] = (code, bool(sure))
            taken.add(id(code))

        left_codes = [c for c in codes if id(c) not in taken]
        if left_named and left_codes:
            for k, v in _pair_skills(left_named, left_codes).items():
                out.setdefault(k, v)
        return out

    def _skill_texts(self) -> tuple:
        """从 abilityList 抽出「带【】的技能」与「无技能名的总述」。

        返回 ``(named, plain)``：named 是 ``[{name, lines}]``。
        同名多条会合并（日冕 + 日冕[狂暴] 在档案里是两条独立描述，
        但同名不同模式的条目游戏里也是分开写的，所以按出现顺序各留一条）。
        """
        hb = self._handbook()
        if not hb.loaded:
            return [], []
        named, plain = [], []
        for sec in hb.sections(self.enemy_id):
            for ln in sec.get("lines") or []:
                txt = str(ln.get("text") or "").strip()
                if not txt:
                    continue
                m = _SKILL_NAME_RE.match(txt)
                if m:
                    named.append({"name": m.group(1),
                                  "lines": [txt]})
                else:
                    plain.append(txt)
        return named, plain

    def _prts_skill_block(self, card, name: str, lines, code=None,
                          annotate: bool = False, sure: bool = True) -> None:
        """一个 PRTS 样式的技能块：技能名 + 三圆点 + 描述 + 代码注解。"""
        box = tk.Frame(card, background=BG_PANEL)
        box.pack(fill="x", padx=PAD_M, pady=(PAD_S, 0))

        nrow = tk.Frame(box, background=BG_PANEL)
        nrow.pack(fill="x")
        tk.Label(nrow, text=str(name), background=BG_PANEL, foreground=ACCENT,
                 font=(FONT_UI, FS_BODY, "bold"), anchor="w").pack(side="left")
        if code is not None:
            self._skill_dots(nrow, code)

        for ln in (lines or []):
            txt = _CLEAN_TAG_RE.sub("", str(ln))
            tk.Label(box, text=txt, background=BG_PANEL, foreground=FG,
                     font=(FONT_UI, FS_SMALL), anchor="w", justify="left",
                     wraplength=470).pack(fill="x", pady=(1, 0))

        if annotate and code is not None:
            self._code_annot(box, code, sure=sure)

    def _skill_dots(self, master, code: dict) -> None:
        """PRTS 那三个圆点：冷却 / 初始 / 消耗。

        档案里没有技能字节时这三个数来自 enemyData.skills，游戏内 PRTS
        也是这么标的。没有值就不画，避免出现「0」误导。
        """
        for val, cn in ((code.get("cooldown"), "冷却"),
                        (code.get("init"), "初始"),
                        (code.get("sp_cost"), "消耗")):
            if val is None:
                continue
            try:
                f = float(val)
            except (TypeError, ValueError):
                continue
            if f <= 0:
                continue
            tk.Label(master, text=" %s%s" % (cn, EC._fmt(f)),
                     background=BG_PANEL, foreground=FG_DIM,
                     font=(FONT_NUM, FS_MICRO)).pack(side="left", padx=(PAD_S, 0))

    def _code_annot(self, master, code: dict, sure: bool = True) -> None:
        """代码注解：prefabKey + 关键 blackboard，用等宽小字挂在描述下面。

        ``↳`` 表示有数值/参数证据匹配上，``≈`` 表示只有语义推测。
        不能把推测标成事实——用户会照着它算伤害。
        """
        krow = tk.Frame(master, background=BG_PANEL)
        krow.pack(fill="x", pady=(1, 0))
        mark = "↳" if sure else "≈"
        tk.Label(krow, text="%s %s" % (mark, code.get("key", "")),
                 background=BG_PANEL, foreground=ACCENT_TXT,
                 font=(FONT_NUM, FS_MICRO), anchor="w").pack(side="left")
        if not sure:
            tk.Label(krow, text="　推测", background=BG_PANEL,
                     foreground=WARN, font=(FONT_UI, FS_MICRO)).pack(side="left")
        bb = code.get("blackboard") or []
        if bb:
            parts = []
            for key, val, vs in bb[:6]:
                shown = vs if vs else (
                    EC._fmt(float(val)) if val is not None else "—")
                parts.append("%s=%s" % (key, shown))
            more = "" if len(bb) <= 6 else " …+%d" % (len(bb) - 6)
            tk.Label(krow, text="　" + " ".join(parts) + more,
                     background=BG_PANEL, foreground=FG_DIM,
                     font=(FONT_NUM, FS_MICRO), anchor="w").pack(
                side="left", fill="x", expand=True)

    def _code_block(self, card, code: dict) -> None:
        """纯代码块：没配上人话技能时的完整参数表。"""
        box = tk.Frame(card, background=BG_PANEL)
        box.pack(fill="x", padx=PAD_M, pady=(PAD_XS, 0))
        krow = tk.Frame(box, background=BG_PANEL)
        krow.pack(fill="x")
        tk.Label(krow, text=str(code["key"]), background=BG_PANEL,
                 foreground=ACCENT_TXT, font=(FONT_NUM, FS_SMALL),
                 anchor="w").pack(side="left")
        meta = []
        cd = code.get("cooldown")
        if cd:
            meta.append("冷却 %s" % EC._fmt(float(cd)))
        init = code.get("init")
        if init:
            meta.append("初始 %s" % EC._fmt(float(init)))
        sp = code.get("sp_cost")
        if sp:
            meta.append("消耗 %s" % EC._fmt(float(sp)))
        if meta:
            tk.Label(krow, text="　" + "　".join(meta), background=BG_PANEL,
                     foreground=FG_DIM, font=(FONT_UI, FS_MICRO)).pack(
                side="left")
        for key, val, vs in (code.get("blackboard") or []):
            line = "    %s = %s" % (key, vs if vs else (
                EC._fmt(float(val)) if val is not None else "—"))
            tk.Label(box, text=line, background=BG_PANEL, foreground=FG_DIM,
                     font=(FONT_NUM, FS_MICRO), anchor="w",
                     justify="left", wraplength=470).pack(fill="x")

    def _open_skill_json(self) -> None:
        """原始 enemyData（含 skills 全量），复用数据字段图鉴的代码查看器。"""
        entries = self._raw_entries()
        if not entries:
            return
        best = None
        for e in entries:
            if int(e.get("level", 0) or 0) == 0:
                best = e
                break
        if best is None:
            best = entries[0]
        if not isinstance(best, dict):
            return
        try:
            from .code_viewer import CodeViewerDialog
        except Exception:
            return
        payload = {"enemy_id": self.enemy_id, **best}
        try:
            CodeViewerDialog(
                self, self.enemy_id, payload,
                github_url=("https://github.com/Kengxxiao/ArknightsGameData/"
                            "blob/master/zh_CN/gamedata/levels/enemydata/"
                            "enemy_database.json"),
                hint=("官方解包 zh_CN/gamedata/levels/enemydata/"
                      "enemy_database.json 中该敌人的原始条目。"
                      "`skills[].prefabKey` 是技能代码名（对应游戏里的技能"
                      "逻辑类），`blackboard` 是它的参数表，"
                      "`cooldown`/`initCooldown` 是冷却与初始冷却。"
                      "文字描述请看上面的「特性 / 技能描述」，"
                      "那份来自 enemy_handbook_table.json。"))
        except Exception:
            pass

    def _card(self, master, title, lines, columns=1, wrap=False,
              color=None) -> None:
        card = tk.Frame(master, background=BG_PANEL, highlightthickness=1,
                        highlightbackground=DIVIDER)
        card.pack(fill="x", pady=(0, PAD_S))
        tk.Label(card, text=title, background=BG_PANEL, foreground=ACCENT,
                 font=(FONT_UI, FS_SMALL, "bold")).pack(
            anchor="w", padx=PAD_M, pady=(PAD_S, 2))
        grid = tk.Frame(card, background=BG_PANEL)
        grid.pack(fill="x", padx=PAD_M, pady=(0, PAD_S))
        if columns > 1:
            for c in range(columns):
                grid.columnconfigure(c, weight=1, uniform="cc")
        for i, line in enumerate(lines):
            lbl = tk.Label(grid, text=line, background=BG_PANEL,
                           foreground=color or FG, font=(FONT_UI, FS_BODY),
                           anchor="w", justify="left",
                           wraplength=(420 if wrap else 0))
            if columns > 1:
                lbl.grid(row=i // columns, column=i % columns, sticky="w",
                         padx=(0, PAD_M), pady=1)
            else:
                lbl.pack(anchor="w", pady=1)

    def _load_icon(self) -> None:
        im = None
        try:
            im = EI.load_icon(self.app.paths, self.enemy_name, _ICON_PX)
        except Exception:
            im = None
        c = self.icon_canvas
        if im is None:
            # 无头像：先画一个带首字的占位块（内存生成，不落盘），
            # 再后台补真实头像。
            try:
                im = EI.placeholder_icon(self.enemy_name, _ICON_PX)
            except Exception:
                im = None
        if im is not None:
            try:
                from PIL import ImageTk
                self._photo = ImageTk.PhotoImage(im)
                c.create_image(_ICON_PX // 2, _ICON_PX // 2, image=self._photo)
            except Exception:
                c.create_text(_ICON_PX // 2, _ICON_PX // 2, text="无图",
                              fill=FG_DIM, font=(FONT_UI, FS_BODY))
        # 后台补图，完成后回主线程刷新（无图敌人依旧会尝试下载）
        try:
            EI.load_icon_async(
                self.app.paths, self.enemy_name, _ICON_PX,
                on_done=lambda im2: self.after(0, self._on_icon_ready, im2))
        except Exception:
            pass

    def _on_icon_ready(self, im) -> None:
        """后台图标就绪后补画（主线程）。"""
        if im is None:
            return
        try:
            c = self.icon_canvas
            if not c.winfo_exists():
                return
            from PIL import ImageTk
            self._photo = ImageTk.PhotoImage(im)
            c.delete("all")
            c.create_image(_ICON_PX // 2, _ICON_PX // 2, image=self._photo)
        except Exception:
            pass

    def _open_prts(self) -> None:
        import webbrowser
        try:
            webbrowser.open(EI.icon_page(self.enemy_name))
        except Exception:
            pass

    def _center(self, w: int, h: int) -> None:
        self.update_idletasks()
        try:
            mw = self.master.winfo_rootx()
            my = self.master.winfo_rooty()
            mwid = self.master.winfo_width()
            mh = self.master.winfo_height()
        except Exception:
            mw = my = 0
            mwid, mh = 1280, 800
        x = mw + max(0, (mwid - w) // 2)
        y = my + max(0, (mh - h) // 3)
        self.geometry("%dx%d+%d+%d" % (w, h, x, y))

    def close(self) -> None:
        try:
            self.grab_release()
        except Exception:
            pass
        self.destroy()