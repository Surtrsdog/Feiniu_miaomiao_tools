# -*- coding: utf-8 -*-
"""怪物图鉴弹窗：展示单个敌人的特性、技能与各种抗性。

在路线分析右侧点击怪物图标时弹出。图标来自 PRTS（带磁盘缓存），
数据来自本地敌人库，断网时仍能显示文字，只是图标位置留占位。

技能文本的取数与排版**不在这里**：模型在 ``core/enemy_skills.py``
（PRTS 优先 + 档案补漏 + 解包结构注解），渲染在 ``ui/skill_render.py``。
本模块只决定「摆哪些卡片、按什么顺序摆」。两个入口（本弹窗与数据
索引）共用同一套渲染，避免「同一只怪两个地方两套说法」。
"""
from __future__ import annotations

import tkinter as tk
from typing import List

from ..core import enemy_codex as EC
from ..core import enemy_icons as EI
from ..core import enemy_skills as ES
from . import skill_render as ESR
from .annotation_card import AnnotationCard
from .widgets import (ACCENT, ACCENT_TXT, BG, BG_DEEP, BG_PANEL, BG_SUNKEN,
                      BORDER, CARD, CARD_HEAD, DIVIDER, FG, FG_DIM, FONT_NUM,
                      FONT_UI, FS_BODY, FS_H1, FS_MICRO, FS_SMALL, PAD_L,
                      PAD_M, PAD_S, PAD_XS, WARN, Card, ScrollFrame)

_ICON_PX = 128


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
        self._anno = None

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
        """解包技能代码（prefabKey + 节奏 + blackboard）。

        实现在 ``core/enemy_skills.skill_codes``——数据索引页也要用同一份，
        各写一遍必然分叉。
        """
        return ES.skill_codes(self._raw_entries())

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
            # 数据缺了也让人记事：本地没数据本身就是要记下来的事
            self._anno_card(body.inner)
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
        # 分工：带【技能名】的条目归下面的「技能」卡统一渲染（那里才有
        # PRTS 样式的名字 + 圆点 + 代码注解）；其余非技能段落全部归
        # 「天赋 / 能力」卡，TITLE 段（陆行姿态 / 天赋名等）原样保留。
        hb = self._handbook()
        secs = hb.sections(self.enemy_id) if hb.loaded else []
        self._talent_card(body.inner, secs,
                          handbook_missing=(not hb.loaded and bool(hb.error)))
        self._dmg_card(body.inner, hb)

        stats = ["%s  %s" % (k, v) for k, v in e["stats"]]
        self._card(body.inner, "基础面板", stats, columns=2)

        if e.get("immunes"):
            self._card(body.inner, "免疫", ["、".join(e["immunes"])], color=ACCENT)

        res = ["%s  %s" % (k, v) for k, v in e["resists"]]
        if e.get("extra"):
            res += ["%s  %s" % (k, v) for k, v in e["extra"]]
        self._card(body.inner, "抗性", res, columns=2)

        # 技能卡：PRTS 有记录就按 PRTS 排（游戏内口径），档案补漏，
        # 都配不上才显示 codex_entry 那句英文摘要兜底。
        #
        # 旧实现的门是 ``if codes:``——只有解包代码才画卡，于是 464 只
        # 「PRTS 有、解包没对上」的怪在弹窗里一个字都看不到技能描述。
        codes = self._skill_codes()
        prts = ES.load_prts(self.app).get(self.enemy_id) or []
        hb_named, _hb_plain = ES.split_handbook(secs)
        if prts or hb_named or codes:
            self._skill_code_card(body.inner, codes, secs, prts)
        elif e.get("skills"):
            self._card(body.inner, "技能（解包摘要）", e["skills"], wrap=True)

        # ------------------------------------------------------ 代码实现
        # 用户的问题很具体：「赤刃明霄陈的龙在代码上是怎么实现的」
        # 「黑蛇转阶段的火雨在代码上是怎么实现的」——这些内容在任何一段
        # 中文描述里都找不到，只存在于解包的 prefabKey + blackboard 里。
        # 卡片只在该实体确实有条目时出现，没结果就不占版面。
        self._code_impl_card(body.inner)

        self._anno_card(body.inner)

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

    def _ability_card(self, master, sections, title="特性") -> None:
        """渲染 abilityList 折好的小标题 + 条目（PRTS 风格）。"""
        card = tk.Frame(master, background=BG_PANEL, highlightthickness=1,
                        highlightbackground=DIVIDER)
        card.pack(fill="x", pady=(0, PAD_S))
        head = tk.Frame(card, background=BG_PANEL)
        head.pack(fill="x", padx=PAD_M, pady=(PAD_S, 2))
        tk.Label(head, text=title, background=BG_PANEL,
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

    def _talent_card(self, master, sections, handbook_missing=False) -> None:
        """「天赋 / 能力」卡：档案非技能段落 + talentBlackboard 参数说明。

        设计意图（只做 UI 层筛选，不改 core 解析）：

        * ``ES.strip_named`` 会把「带【技能名】的条目」剥掉，这些条目已经
          归技能卡；剥完之后剩下的「总述 + TITLE 段 + 散句」属于天赋/能力
          描写，必须完整保留——尤其是「陆行姿态」这类 TITLE 小标题。
        * 敌人库里的 ``talentBlackboard`` 只是参数数组，``codex_entry`` 已经
          用 ``bb_to_text`` 转成了中文短句，这里作为参数说明卡排在正文卡
          下面，不再单独开「天赋 / 光环」卡，避免同一主题两张卡。
        * 若档案和 talentBlackboard 都没有内容，显示明确兜底文案，不留空白。
        """
        talent = str(self._entry.get("talent") or "") if self._entry else ""
        secs_plain = ES.strip_named(sections or [])
        if not secs_plain and not talent:
            if handbook_missing:
                msg = ("缺少敌人档案数据（enemy_handbook_table.json），"
                       "到设置里更新一次数据即可显示天赋/能力描写。")
            else:
                msg = ("敌人档案里没有这只怪的天赋/能力描写，"
                       "解包数据里也没有 talentBlackboard 参数。")
            self._card(master, "天赋 / 能力", [msg], wrap=True)
            return
        if secs_plain:
            self._ability_card(master, secs_plain, title="天赋 / 能力")
        if talent:
            self._card(master, "天赋 / 能力参数",
                       [talent], wrap=True)

    def _code_impl_card(self, master) -> None:
        """「代码实现」卡：这套机制在解包 JSON 里到底是怎么写的。

        为什么单独开一张卡，而不是并进技能卡：
        技能卡讲的是**效果**（打多少、打几下、玩家看到什么），
        这张卡讲的是**实现**（哪个 prefabKey、哪些 blackboard 键、
        在哪个文件的哪个字段）。用户问「陈的龙在代码上怎么实现的」、
        「黑蛇的火雨在代码上怎么实现的」时，要的是后者。

        数据来自 ``core/extra_mechanics``：少数被点名问过的实体走人工
        精讲（带 GitHub 字段路径），其余实体走通用推导（读本地解包缓存
        现场生成）。两者都没有时整张卡不出现，不留空壳。
        """
        try:
            from ..core import extra_mechanics as XM
        except Exception:                                   # noqa: BLE001
            return
        if not self.enemy_id:
            return
        try:
            entries = XM.all_mechanics_for(self.enemy_id)
        except Exception:                                   # noqa: BLE001
            return
        if not entries:
            return

        card = Card(master, title="代码实现", accent=ACCENT)
        card.pack(fill="x", pady=(0, PAD_S))
        tk.Label(card.head_right,
                 text="解包 prefabKey / blackboard",
                 background=CARD_HEAD, foreground=FG_DIM,
                 font=(FONT_UI, FS_MICRO)).pack(side="left",
                                                padx=(0, PAD_S))

        for ent in entries:
            box = tk.Frame(card.body, background=BG_PANEL)
            box.pack(fill="x", pady=(0, PAD_M))

            head = tk.Frame(box, background=BG_PANEL)
            head.pack(fill="x")
            tag = "推导" if ent.get("derived") else "精讲"
            tk.Label(head, text="▸ %s" % str(ent.get("name") or ""),
                     background=BG_PANEL, foreground=FG,
                     font=(FONT_UI, FS_BODY, "bold"),
                     anchor="w", justify="left", wraplength=470).pack(
                side="left")
            tk.Label(head, text=tag, background=BG_PANEL,
                     foreground=FG_DIM, font=(FONT_UI, FS_MICRO)).pack(
                side="left", padx=(PAD_S, 0))

            text = str(ent.get("text") or "")
            if text:
                tk.Label(box, text=text, background=BG_PANEL,
                         foreground=FG_DIM, font=(FONT_UI, FS_SMALL),
                         anchor="w", justify="left", wraplength=470).pack(
                    fill="x", pady=(2, 0))

            path = str(ent.get("path") or "")
            if path:
                tk.Label(box, text="字段路径  %s" % path, background=BG_PANEL,
                         foreground=FG_DIM, font=(FONT_NUM, FS_MICRO),
                         anchor="w", justify="left", wraplength=470).pack(
                    fill="x", pady=(2, 0))

            # 原样代码片段折叠起来，需要逐字核对时再展开
            code = ent.get("code")
            if code:
                try:
                    import json as _json
                    pretty = _json.dumps(code, ensure_ascii=False, indent=2)
                except Exception:                           # noqa: BLE001
                    pretty = str(code)
                lines = pretty.split("\n")
                if len(lines) > 40:
                    lines = lines[:40] + ["…（已截断，点「查看原代码」看全文）"]
                btn = tk.Button(box, text="▾ 解包原文（%d 行）" % len(lines),
                                relief="flat", background=BG_DEEP,
                                foreground=ACCENT, activebackground=BG_PANEL,
                                activeforeground=ACCENT,
                                font=(FONT_UI, FS_MICRO),
                                highlightthickness=1, highlightbackground=BORDER,
                                cursor="hand2", padx=8, pady=0)
                holder = tk.Frame(box, background=BG_SUNKEN)

                def _toggle(h=holder, b=btn, ls=lines):      # noqa: ANN001
                    if h.winfo_ismapped():
                        h.pack_forget()
                        b.config(text="▾ 解包原文（%d 行）" % len(ls))
                    else:
                        for w in h.winfo_children():
                            w.destroy()
                        txt = tk.Text(h, height=min(len(ls), 18), wrap="none",
                                      background=BG_SUNKEN, foreground=FG,
                                      font=(FONT_NUM, FS_MICRO), bd=0,
                                      highlightthickness=0)
                        txt.insert("1.0", "\n".join(ls))
                        txt.config(state="disabled")
                        txt.pack(fill="both", expand=True)
                        h.pack(fill="x", pady=(2, 0))
                        b.config(text="▴ 收起")

                btn.config(command=_toggle)
                btn.pack(anchor="w", pady=(4, 0))
                holder.pack_forget()

        srcs = []
        for ent in entries:
            s = str(ent.get("source") or "")
            if s and s not in srcs:
                srcs.append(s)
        if srcs:
            tk.Label(card.body,
                     text="数据来源：" + "\n".join("· " + s for s in srcs[:4]),
                     background=BG_PANEL, foreground=FG_DIM,
                     font=(FONT_UI, FS_MICRO), anchor="w", justify="left",
                     wraplength=470).pack(fill="x", pady=(PAD_S, 0))
        card.harmonize()

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

    # ---------------------------------------------------------------- 技能

    def _skill_code_card(self, master, codes, sections, prts) -> None:
        """技能卡：PRTS 口径的名字 + 初始/消耗圆点 + 效果原文。

        排版照 PRTS 敌人页来——那才是玩家在游戏里看到的样子：

            ┌ 技能 ──────────────────── 查看原代码 ┐
            │ 烈焚灼息   ●19 消耗  ●19 初始  PRTS   │
            │ 使场上一名我方单位持续受到逐渐递增的真 │
            │ 实伤害……                              │
            │   档案补充：……                        │
            │   ↳ DragonFire                        │
            │     　dragon_fire.duration = 30.5 → … │
            │ ▸ 解包数值（enemyData.skills 原样）   │
            └───────────────────────────────────────┘

        **不再自己算配对**。旧版这里有一套 ``_pair_with_prts`` /
        ``_pair_skills`` / ``_prts_skill_block`` 的启发式，数据索引页那边
        另有一套，两边措辞和圆点规则都不一样，用户点哪个入口就看到哪种
        说法。现在配对在 ``core/enemy_skills.build_blocks``，渲染在
        ``ui/skill_render``，本方法只负责「摆卡片 + 挂按钮」。
        """
        card = Card(master, title="技能", accent=ACCENT)
        card.pack(fill="x", pady=(0, PAD_S))

        meta = ES.prts_meta(self.app)
        sub = ""
        if meta.get("generated_at"):
            sub = "PRTS 镜像 %s" % str(meta["generated_at"])[:10]
        if sub:
            tk.Label(card.head_right, text=sub, background=CARD_HEAD,
                     foreground=FG_DIM, font=(FONT_UI, FS_MICRO)).pack(
                side="left", padx=(0, PAD_S))

        btn = tk.Button(card.head_right, text="查看原代码", relief="flat",
                        background=BG_DEEP, foreground=ACCENT,
                        activebackground=BG_PANEL, activeforeground=ACCENT,
                        font=(FONT_UI, FS_MICRO), highlightthickness=1,
                        highlightbackground=BORDER, cursor="hand2",
                        padx=8, pady=0, command=self._open_skill_json)
        btn.pack(side="right")

        blocks = ES.build_blocks(self.enemy_id, sections, codes, prts)
        ESR.render_skills(card.body, blocks, ES.env(self.app), wrap=470,
                          max_bb=6)

        unpack = ESR.unpack_lines(codes)
        if unpack:
            ESR.collapsible(card.body, "解包数值（enemyData.skills 原样）",
                            unpack, wrap=460, note=ESR.UNPACK_NOTE)

        if not prts:
            # 说明为什么名字右边没有 PRTS 标记：用户会拿这里的字去和
            # PRTS 页面逐字对比，差异必须提前交代清楚。
            tk.Label(card.body,
                     text="PRTS 敌人页没有这只怪的技能记录（或抓取时该页"
                          "缺少技能表），以上描述来自游戏内敌人档案。",
                     background=CARD, foreground=FG_DIM,
                     font=(FONT_UI, FS_MICRO), anchor="w", justify="left",
                     wraplength=460).pack(fill="x", padx=PAD_M,
                                         pady=(PAD_S, 0))
        card.harmonize()

    def _open_skill_json(self) -> None:
        """「查看原代码」：解包 skills 原文 + 每个 key 的中文结构注解。

        payload 刻意只留 ``enemy_id`` + ``skills``（+ ``talentBlackboard``）：
        旧版把整条 enemyData 塞进去，属性/抗性/描述混在一起，用户想找
        「技能到底吃了哪些参数」得在一千多行 JSON 里滚。技能相关的字段
        就这几处，摊干净更好查。

        注解由 ``core/enemy_skills.skill_annotation`` 生成——JSON 本身
        一个字不改（用户要的是和官方解包逐字对得上的原文）。
        """
        entries = self._raw_entries()
        if not entries:
            return
        codes = ES.skill_codes(entries)
        if not codes:
            return
        talent = None
        for e in entries:
            if int(e.get("level", 0) or 0) == 0:
                ed = e.get("enemyData") or {}
                talent = ed.get("talentBlackboard")
                break
        if talent is None:
            ed = (entries[0].get("enemyData") or {})
            talent = ed.get("talentBlackboard")

        try:
            from .code_viewer import CodeViewerDialog
        except Exception:                                   # noqa: BLE001
            return

        payload = {"enemy_id": self.enemy_id,
                   "skills": [c.get("raw") for c in codes if c.get("raw")]}
        if talent:
            payload["talentBlackboard"] = talent

        annotate = ES.skill_annotation(self.app, self.enemy_id,
                                      payload["skills"], talent)
        try:
            CodeViewerDialog(
                self, "%s · 技能原代码" % (self.enemy_name or self.enemy_id),
                payload,
                github_url=("https://github.com/Kengxxiao/ArknightsGameData/"
                            "blob/master/zh_CN/gamedata/levels/enemydata/"
                            "enemy_database.json"),
                hint=("官方解包 enemy_database.json 中该敌人的 skills[] 原文。"
                      "`prefabKey` 是客户端注册的技能行为类名，"
                      "`blackboard` 是它的参数表，"
                      "`cooldown`/`initCooldown` 是消耗与初始冷却。"
                      "上方「结构注解」第一栏是**技能指令**：把 blackboard 的"
                      "键名按行为语义排成执行顺序（触发 → 选目标 → 生效 → 计时），"
                      "每一步都标注取自哪个键，可回原文核对；"
                      "解包本身没有客户端脚本，所以这一栏不叫「实现」而叫「反推」，"
                      "推不出的参数不会硬塞进指令，仍完整列在下面的参数表里。"),
                annotate=annotate)
        except Exception:                                   # noqa: BLE001
            pass
    def _anno_card(self, master) -> None:
        """「我的批注」卡：与图鉴页共用同一份批注（同一个 store）。

        弹窗和图鉴页写的是同一只怪，必须看到同一段字。各建各的 store 会
        出现「弹窗里补了一句，回到图鉴页却没有」，然后后写的覆盖先写的。
        这里带 ``with_io=True``：弹窗没有返回条，导出 / 导入只能放卡上。
        """
        if not self.enemy_id:
            return
        card = AnnotationCard(master, self.app, "enemy", self.enemy_id,
                              name=self.enemy_name, with_io=True)
        card.pack(fill="x", pady=(0, PAD_S))
        self._anno = card

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
        # 关窗前把没落盘的批注写掉（Esc / 点 X / 代码调用都走这里）
        card = getattr(self, "_anno", None)
        if card is not None:
            try:
                card.flush()
            except Exception:
                pass
            self._anno = None
        try:
            self.grab_release()
        except Exception:
            pass
        self.destroy()
