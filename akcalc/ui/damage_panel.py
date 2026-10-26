# -*- coding: utf-8 -*-
"""伤害计算面板：单点结果 + 多类型曲线 + 技能。

曲线由 core.curves 生成，这里只负责交互与绘制。
"""
from __future__ import annotations

import copy
import tkinter as tk
from tkinter import messagebox, ttk
from typing import Dict, List, Optional, Tuple

from ..core import buffs as BUFF
from ..core import constants as C
from ..core import damage_type as DT
from ..core import compare as CMP
from ..core import curves as CV
from ..core import damage as DMG
from ..core import skills as SK
from ..core.models import EnemyStats, Operator
from .widgets import (ACCENT, ACCENT_SOFT, BG, BG_INPUT, BG_PANEL, BORDER,
                      CARD, CARD_HEAD, ComboBox, DIVIDER, FG, FG_DIM,
                      FONT_NUM, FONT_UI, FS_BODY, FS_H1, FS_MICRO, FS_NUM,
                      FS_SMALL, HOVER, LabeledEntry, PAD_M, PAD_S, PAD_XS,
                      ResultBox, SectionFrame, SERIES, harmonize)


class DamagePanel(ttk.Frame):
    """伤害计算器。"""

    def __init__(self, master, app):
        super().__init__(master, style="App.TFrame")
        self.app = app
        self.operator: Optional[Operator] = None
        self.enemy: Optional[EnemyStats] = None
        self._skill: Optional[SK.Skill] = None
        self._chart: Optional[CV.CurveChart] = None
        #: 当前干员是不是医疗分支（他们不产生伤害，面板要给出提示而不是假 DPS）
        self._healer: bool = False

        self._build()
        self._rebuild_skill_choices()

    # ------------------------------------------------------------ 布局

    def _build(self) -> None:
        # ---- 顶部：返回 + 干员选择 + 分类筛选
        # 这套选择器只属于伤害计算；寻路面板完全看不到干员相关的控件。
        bar = tk.Frame(self, background=BG)
        bar.pack(fill="x", padx=PAD_M, pady=(PAD_M, 0))
        self.app.build_panel_header(bar, "伤害计算", "DAMAGE",
                                    "按干员面板与技能倍率计算伤害，并给出随防御变化的 DPS 曲线")

        tools = tk.Frame(self, background=BG)
        tools.pack(fill="x", padx=PAD_M, pady=(PAD_S, 0))
        card = tk.Frame(tools, background=BG_PANEL, highlightthickness=1,
                        highlightbackground=DIVIDER)
        card.pack(fill="x")
        self._tools_card = card

        pick = tk.Frame(card, background=BG_PANEL)
        pick.pack(fill="x", padx=PAD_S, pady=(PAD_S, 1))
        tk.Label(pick, text="干员", background=BG_PANEL, foreground=FG_DIM,
                 font=(FONT_UI, FS_BODY)).pack(side="left", padx=(PAD_XS, PAD_S))
        self.app.var_op = tk.StringVar()
        self.app.cmb_op = ComboBox(pick, textvariable=self.app.var_op, width=20,
                                   state="normal")
        self.app.cmb_op.pack(side="left", ipady=1)
        self.app.cmb_op.bind("<<ComboboxSelected>>",
                             lambda e: self.app.pick_operator())
        self.app.cmb_op.bind("<Return>", lambda e: self.app.pick_operator())
        self.app.btn_fetch = ttk.Button(pick, text="获取并计算",
                                        style="Accent.TButton",
                                        command=self.app.pick_operator)
        self.app.btn_fetch.pack(side="left", padx=PAD_S)

        # 筛选栏就挂在干员下拉右边、同一行里：按职业/星级/站位先收窄，
        # 再展开「干员」，不用在窗口上下反复找。寻路视图没有这些控件。
        self.app._build_filter_bar(pick, compact=True)

        outer = ttk.Frame(self, style="App.TFrame")
        outer.pack(fill="both", expand=True, pady=(PAD_S, 0))

        # 左列：输入（可滚动）
        left = ttk.Frame(outer, style="App.TFrame", width=268)
        left.pack(side="left", fill="y", padx=(6, 3), pady=6)
        left.pack_propagate(False)

        # 右列：结果 + 曲线
        right = ttk.Frame(outer, style="App.TFrame")
        right.pack(side="left", fill="both", expand=True, padx=(3, 6), pady=6)

        # ---------------- 干员
        sec_op = SectionFrame(left, "攻击方（干员）")
        sec_op.pack(fill="x", pady=(0, 5))
        b = sec_op.body
        self.lbl_operator = ttk.Label(b, text="未选择干员", style="CardHint.TLabel",
                                      wraplength=236)
        self.lbl_operator.pack(anchor="w", pady=(0, 3))

        row = ttk.Frame(b, style="App.TFrame")
        row.pack(fill="x")
        ttk.Label(row, text="精英", style="Card.TLabel").pack(side="left")
        self.var_elite = tk.StringVar(value="2")
        self.cmb_elite = ComboBox(row, textvariable=self.var_elite, width=4,
                                      state="readonly", values=["0", "1", "2"])
        self.cmb_elite.pack(side="left", padx=(3, 8))
        self.cmb_elite.bind("<<ComboboxSelected>>", lambda e: self._on_elite_change())

        ttk.Label(row, text="等级", style="Card.TLabel").pack(side="left")
        self.var_level = tk.StringVar(value="90")
        self.cmb_level = ComboBox(row, textvariable=self.var_level, width=5,
                                      state="readonly", values=["90"])
        self.cmb_level.pack(side="left", padx=3)
        self.cmb_level.bind("<<ComboboxSelected>>", lambda e: self.recompute())

        row2 = ttk.Frame(b, style="App.TFrame")
        row2.pack(fill="x", pady=(3, 0))
        self.var_trust = tk.BooleanVar(value=True)
        ttk.Checkbutton(row2, text="满信赖", variable=self.var_trust,
                        command=self.recompute).pack(side="left")
        self.var_pot = tk.BooleanVar(value=False)
        ttk.Checkbutton(row2, text="满潜能", variable=self.var_pot,
                        command=self.recompute).pack(side="left", padx=(6, 0))

        # ---------------- 技能
        sec_sk = SectionFrame(left, "技能（可选）")
        sec_sk.pack(fill="x", pady=5)
        bs = sec_sk.body
        self.var_skill = tk.StringVar(value="不使用技能")
        self.cmb_skill = ComboBox(bs, textvariable=self.var_skill, width=24,
                                      state="readonly", values=["不使用技能"])
        self.cmb_skill.pack(fill="x")
        self.cmb_skill.bind("<<ComboboxSelected>>", lambda e: self._on_skill_change())

        self.var_skill_lv = tk.StringVar(value="专三")
        self.cmb_skill_lv = ComboBox(bs, textvariable=self.var_skill_lv, width=8,
                                         state="readonly",
                                         values=["7", "专一", "专二", "专三"])
        self.cmb_skill_lv.pack(anchor="w", pady=(3, 0))
        self.cmb_skill_lv.bind("<<ComboboxSelected>>", lambda e: self._on_skill_change())

        self.lbl_skill = ttk.Label(bs, text="", style="CardHint.TLabel",
                                   wraplength=236, justify="left")
        self.lbl_skill.pack(anchor="w", pady=(3, 0))

        # ---------------- 加拐（队友增益）
        sec_buff = SectionFrame(left, "加拐（队友增益）")
        sec_buff.pack(fill="x", pady=5)
        bb = sec_buff.body

        # 不做预设模板：能加拐的干员太多，预设永远补不完，全部交给
        # 用户自己填。下面每个乘区都是独立输入项。
        ttk.Label(
            bb, text="同区内数值相加，不同区之间相乘。留 0 / 1.0 即为不启用。",
            style="CardHint.TLabel", wraplength=228, justify="left"
        ).pack(anchor="w", pady=(0, 3))

        # 乘区输入：按「攻击力 / 抗性 / 结果」三组，同区内加算、区间相乘
        self.buff_entries = {}
        self.buff_vars = {}
        for key, name, unit, desc in BUFF.ZONES:
            if unit == "%":
                lbl = "%s %%" % name
                dflt = "0"
            elif unit == "×":
                lbl = "%s ×" % name
                dflt = "1.0"
            else:
                lbl = name
                dflt = "0"
            e = LabeledEntry(bb, lbl, dflt, width=9)
            e.pack(fill="x")
            e.entry.bind("<KeyRelease>", lambda ev: self.recompute())
            self.buff_entries[key] = e
            self.buff_vars[key] = lbl

        # 固定项：面板攻击力、连击、目标防御在别处，这里只留攻速基准
        self.e_atk = LabeledEntry(bb, "面板攻击力", "540", width=9)
        self.e_atk.pack(fill="x")
        self.e_hits = LabeledEntry(bb, "连击次数", "1", width=9)
        self.e_hits.pack(fill="x")
        for e in (self.e_atk, self.e_hits):
            e.entry.bind("<KeyRelease>", lambda ev: self.recompute())

        rowt = ttk.Frame(bb, style="App.TFrame")
        rowt.pack(fill="x", pady=(3, 0))
        ttk.Label(rowt, text="伤害类型", style="Card.TLabel").pack(anchor="w")
        self.var_dtype = tk.StringVar(value=C.DMG_PHYSICAL)
        for val, label in [(C.DMG_PHYSICAL, "物理"), (C.DMG_MAGICAL, "法术"),
                           (C.DMG_ELEMENTAL, "元素"), (C.DMG_TRUE, "真实")]:
            ttk.Radiobutton(rowt, text=label, value=val, variable=self.var_dtype,
                            command=self.recompute).pack(side="left")

        # ---------------- 目标
        sec_tgt = SectionFrame(left, "目标（敌人）")
        sec_tgt.pack(fill="x", pady=5)
        bt = sec_tgt.body
        self.lbl_enemy = ttk.Label(bt, text="未选择敌人（可手动输入）",
                                   style="CardHint.TLabel", wraplength=236)
        self.lbl_enemy.pack(anchor="w", pady=(0, 3))
        # 防御 / 法抗 / 元素抗性必须分开：以前只有一个输入框，一个 200
        # 同时被当成防御和法抗用，法术计算里 200 法抗直接顶穿 100 的上限，
        # 于是「望」这类法术技能的伤害全被压到 5% 保底，看着像没算对。
        rowr = tk.Frame(bt, background=CARD)
        rowr.pack(fill="x")
        self.e_def = LabeledEntry(rowr, "防御", "200", width=6)
        self.e_def.pack(side="left", fill="x", expand=True)
        self.e_res = LabeledEntry(rowr, "法抗", "0", width=6)
        self.e_res.pack(side="left", fill="x", expand=True, padx=(PAD_XS, 0))
        self.e_eres = LabeledEntry(rowr, "元素抗性", "0", width=6)
        self.e_eres.pack(side="left", fill="x", expand=True, padx=(PAD_XS, 0))
        for _e in (self.e_def, self.e_res, self.e_eres):
            _e.entry.bind("<KeyRelease>", lambda ev: self.recompute())

        # 防御值滑块：默认窗口尺寸下输入框又窄又靠下，键盘点不准，
        # 给一条能拖的滑轨，拖完自动回填输入框。
        rowdf = ttk.Frame(bt, style="App.TFrame")
        rowdf.pack(fill="x", pady=(2, 0))
        self.var_def_slide = tk.DoubleVar(value=200.0)
        self.scl_def = ttk.Scale(rowdf, from_=0.0, to=3000.0, orient="horizontal",
                                 variable=self.var_def_slide,
                                 command=self._on_def_slide)
        self.scl_def.pack(side="left", fill="x", expand=True)
        self.lbl_def_slide = ttk.Label(rowdf, text="200", style="CardHint.TLabel",
                                       width=5, anchor="e")
        self.lbl_def_slide.pack(side="left", padx=(PAD_XS, 0))

        # ---------------- 右侧：结果
        sec_res = SectionFrame(right, "计算结果")
        sec_res.pack(fill="x")
        self.result = ResultBox(sec_res.body)
        # 计算过程固定 3 行高：内容多少都不该抢曲线的空间
        self.result.steps.config(height=3)
        # 贴合内容高度，剩余空间全部留给曲线
        self.result.pack(fill="x")

        # ---------------- 右侧：曲线
        sec_cv = SectionFrame(right, "伤害曲线")
        sec_cv.pack(fill="both", expand=True, pady=(5, 0))
        body = sec_cv.body

        top = ttk.Frame(body, style="App.TFrame")
        top.pack(fill="x")
        ttk.Label(top, text="曲线类型", style="Card.TLabel").pack(side="left")
        self.var_kind = tk.StringVar(value=CV.CURVE_KINDS[CV.DEFAULT_KIND])
        self.cmb_kind = ComboBox(top, textvariable=self.var_kind, width=18,
                                     state="readonly",
                                     values=list(CV.CURVE_KINDS.values()))
        self.cmb_kind.pack(side="left", padx=(4, 10))
        self.cmb_kind.bind("<<ComboboxSelected>>", lambda e: self.recompute())

        ttk.Label(top, text="横轴上限", style="Card.TLabel").pack(side="left")
        self.e_xmax = tk.Entry(top, width=7, background=BG_INPUT,
                               foreground=FG, insertbackground=FG, relief="flat",
                               font=(FONT_NUM, FS_NUM + 1), highlightthickness=1,
                               highlightbackground=BORDER, highlightcolor=ACCENT)
        self.e_xmax.pack(side="left", padx=4)
        self.e_xmax.bind("<KeyRelease>", lambda e: self.recompute())

        self.var_overlay = tk.BooleanVar(value=True)
        ttk.Checkbutton(top, text="叠加保底线", variable=self.var_overlay,
                        command=self.recompute).pack(side="left", padx=(10, 0))

        # 对比模式开关
        self.var_compare = tk.BooleanVar(value=False)
        ttk.Checkbutton(top, text="对比模式", variable=self.var_compare,
                        command=self.toggle_compare).pack(side="left", padx=(12, 0))

        self.lbl_curve = ttk.Label(body, text="", style="CardHint.TLabel",
                                   wraplength=700, justify="left")
        self.lbl_curve.pack(anchor="w", pady=(2, 0))

        # 对比汇总（DPS 降序），单干员模式下隐藏
        self.lbl_cmp_table = tk.Label(body, text="", background=BG_PANEL,
                                      foreground=FG,
                                      font=(FONT_NUM, FS_SMALL), justify="left",
                                      anchor="w", wraplength=700)

        # 对比槽位面板（默认隐藏）
        self.cmp_panel = ComparePanel(body, self)
        self._cmp_packed = False

        # 「放大图」按钮：把曲线放到独立大窗口里看
        self.btn_zoom = ttk.Button(sec_cv.head_right, text="放大图  ⤢",
                                   style="Ghost.TButton",
                                   command=self.open_zoom_chart)
        self.btn_zoom.pack(side="right")
        self._zoom_win = None

        self.chart = ChartCanvas(body, height=250)
        self.chart.config(height=250)
        self.chart.pack(fill="both", expand=True, pady=(PAD_S - 2, 0))

        # 建完所有子控件后统一调色：卡片内不再有更深的色块
        for sec in (sec_op, sec_sk, sec_buff, sec_tgt, sec_res, sec_cv):
            sec.harmonize()
        harmonize(sec_cv.head_right)
    # ------------------------------------------------------------ 放大图

    def open_zoom_chart(self, series_name: Optional[str] = None) -> None:
        """把当前曲线放到一个独立的大窗口里（可缩放、可悬停看数值）。

        series_name 不为空时只放大这一条曲线（对比模式下点某个干员的
        色条/名字，就单独看他的曲线）。
        """
        chart = getattr(self.chart, "_chart", None)
        if chart is None or not chart.series:
            messagebox.showinfo("放大图", "先选干员算出曲线，再放大查看。",
                                parent=self.winfo_toplevel())
            return
        if series_name:
            chart = self._filter_chart(chart, series_name)
            if chart is None:
                return
        # 已经开着就刷新并置前
        if self._zoom_win is not None:
            try:
                if self._zoom_win.winfo_exists():
                    self._zoom_canvas.draw(chart, self.chart._cur_x)
                    self._zoom_win.lift()
                    self._zoom_win.focus_set()
                    return
            except Exception:
                pass
            self._zoom_win = None

        top = tk.Toplevel(self)
        top.title("伤害曲线 · 放大图")
        top.configure(background=BG)
        top.geometry(self._zoom_geometry())
        top.minsize(720, 440)
        # 标题栏同步主界面的深色配色（item 11：二次弹窗顶部白得很丑）
        try:
            from .widgets import style_dialog
            style_dialog(top)
        except Exception:
            pass
        self._zoom_win = top

        # 顶部信息条
        head = tk.Frame(top, background=BG_PANEL, highlightthickness=1,
                        highlightbackground=DIVIDER)
        head.pack(fill="x")
        inner = tk.Frame(head, background=BG_PANEL)
        inner.pack(fill="x", padx=PAD_M, pady=PAD_S)
        tk.Label(inner, text="伤害曲线 放大图", background=BG_PANEL,
                 foreground=FG, font=(FONT_UI, FS_H1, "bold")).pack(side="left")
        self._zoom_hint = tk.Label(
            inner, text="鼠标移到图上可看该防御下的具体数值",
            background=BG_PANEL, foreground=FG_DIM,
            font=(FONT_UI, FS_SMALL))
        self._zoom_hint.pack(side="left", padx=PAD_M)

        # 关掉时清掉引用
        def _on_close():
            self._zoom_win = None
            self._zoom_canvas = None
            top.destroy()

        # 这里原来还有一个「关闭 ✕」标签，和标题栏自带的 ✕ 重复
        # （用户反馈二次弹窗里出现多个 x 号）。标题栏的 ✕ 已经能关，
        # Esc 也能关，这里不再画第二个。
        top.protocol("WM_DELETE_WINDOW", _on_close)

        wrap = tk.Frame(top, background=BG)
        wrap.pack(fill="both", expand=True, padx=PAD_M, pady=PAD_M)
        self._zoom_canvas = ChartCanvas(wrap, background=ChartCanvas.BG_CHART)
        self._zoom_canvas.pack(fill="both", expand=True)
        self._zoom_canvas.draw(chart, self.chart._cur_x)

        # Esc 关闭
        top.bind("<Escape>", lambda e: _on_close())
        try:
            top.transient(self.winfo_toplevel())
            top.lift()
        except Exception:
            pass

    def _filter_chart(self, chart, series_name: str):
        """只保留指定名称的那条曲线，做成一张新图（用于单干员放大）。"""
        keep = [x for x in chart.series if x.name == series_name]
        if not keep:
            # 名字不完全相等时按包含匹配（曲线名后面可能带技能后缀）
            keep = [x for x in chart.series if series_name in x.name]
        if not keep:
            messagebox.showinfo("放大图", "没找到「%s」的曲线。" % series_name,
                                parent=self.winfo_toplevel())
            return None
        one = CV.CurveChart()
        one.title = "%s · %s" % (chart.title, keep[0].name)
        one.x_label = chart.x_label
        one.x_unit = chart.x_unit
        one.y_label = chart.y_label
        one.y_unit = chart.y_unit
        one.desc = chart.desc
        one.series = keep
        return one

    def zoom_operator_curve(self, slot_index: int) -> None:
        """放大右上角某个对比槽位对应的曲线。"""
        chart = getattr(self.chart, "_chart", None)
        if chart is None or not chart.series:
            messagebox.showinfo("放大图", "先选干员算出曲线，再放大查看。",
                                parent=self.winfo_toplevel())
            return
        try:
            slot = self.cmp_panel.slots[slot_index]
            label = slot.entry.label()
        except Exception:
            return
        self.open_zoom_chart(label)

    @staticmethod
    def _zoom_geometry() -> str:
        """按屏幕大小给一个舒服的放大窗口尺寸并居中。"""
        try:
            import tkinter as _tk
            r = _tk._default_root
            if r is not None:
                sw = r.winfo_screenwidth()
                sh = r.winfo_screenheight()
            else:
                sw, sh = 1600, 900
            w = int(min(max(sw * 0.62, 860), 1360))
            h = int(min(max(sh * 0.58, 500), 820))
            x = int((sw - w) / 2)
            y = int((sh - h) / 2) - 20
            return "%dx%d+%d+%d" % (w, h, max(0, x), max(0, y))
        except Exception:
            return "1100x680"

    # ------------------------------------------------------------ 技能

    def _rebuild_skill_choices(self) -> None:
        """按当前干员刷新技能下拉。"""
        opts = ["不使用技能"]
        self._skills: List[SK.Skill] = []
        if self.operator:
            self._skills = list(getattr(self.operator, "skills", None) or [])
            for sk in self._skills:
                opts.append("S%d  %s" % (sk.index, sk.name))
        self.cmb_skill.config(values=opts)
        self.var_skill.set(opts[0])
        self._skill = None
        self.lbl_skill.config(text="")
        self._sync_skill_levels()

    def _sync_skill_levels(self) -> None:
        keys = self._skill.level_keys if self._skill else ["7", "专一", "专二", "专三"]
        self.cmb_skill_lv.config(values=keys)
        if keys and self.var_skill_lv.get() not in keys:
            self.var_skill_lv.set(keys[-1])

    def _on_skill_change(self) -> None:
        label = self.var_skill.get()
        self._skill = None
        for sk in getattr(self, "_skills", []):
            if label.startswith("S%d" % sk.index):
                self._skill = sk
                break
        self._sync_skill_levels()
        if self._skill:
            self.lbl_skill.config(
                text=SK.skill_summary(self._skill, self.var_skill_lv.get()))
        else:
            self.lbl_skill.config(text="")
        self._sync_dtype_from_skill()
        self.recompute()

    def _sync_dtype_from_skill(self) -> None:
        """技能描述写明伤害类型时以技能为准（望的三技能是法术）。

        普攻按分支走，但不少干员「技能换伤害类型」：望（陷阱师，普攻
        物理，天下劫 380% 法伤）、逻各斯等。技能描述优先。
        """
        op = self.operator
        if not op:
            return
        base = getattr(self, "_dtype_branch", None) or DT.guess_damage_type(
            op.profession, op.sub_profession)
        desc = ""
        lv = self._skill_value()
        if lv is not None:
            desc = lv.description or ""
        dt = DT.resolve(op.profession, op.sub_profession, desc)
        if dt != C.DMG_HEAL:
            self.var_dtype.set(dt)
        self._dtype_auto = dt

    def _skill_value(self) -> Optional[SK.SkillLevel]:
        """当前选中的技能等级，无技能时为 None。"""
        if not self._skill:
            return None
        return self._skill.level(self.var_skill_lv.get())

    # ------------------------------------------------------------ 数据同步

    def set_operator(self, op: Optional[Operator]) -> None:
        self.operator = op
        if not op:
            self.lbl_operator.config(text="未选择干员")
            return
        self.lbl_operator.config(
            text="%s｜%s·%s｜★%d" % (op.name, op.profession, op.sub_profession, op.rarity))
        # 按分支自动切换伤害类型：术战者 / 术师系打法术，医师生治疗……
        # 之前一律默认物理，导致史尔特尔、望这类角色结果栏显示物理伤害。
        #
        # 【医疗干员】没有「治疗」这个单选项（面板只有物理/法术/元素/真实），
        # 所以不能只写「if dtype != HEAL」就跳过——那样 var_dtype 会**保留
        # 上一个干员残留的值**：先看艾雅法拉（法术），再切到闪灵，
        # 闪灵就被当成法术输出算 DPS。这里显式回退到物理并打上标记，
        # 让 recompute 显示「该干员不造成伤害」而不是一个假的 DPS。
        dtype = DT.guess_damage_type(op.profession, op.sub_profession)
        if dtype == C.DMG_HEAL:
            self.var_dtype.set(C.DMG_PHYSICAL)
            self._healer = True
        else:
            self.var_dtype.set(dtype)
            self._healer = False
        self._dtype_auto = dtype
        self._dtype_branch = dtype
        elites = sorted(op.phases.keys())
        self.cmb_elite.config(values=[str(e) for e in elites])
        self.var_elite.set(str(max(elites)) if elites else "0")
        self._rebuild_skill_choices()
        self._on_elite_change()

    def _on_elite_change(self) -> None:
        if not self.operator:
            return
        try:
            elite = int(self.var_elite.get())
        except ValueError:
            return
        lvs = self.operator.levels_of(elite)
        if not lvs:
            return
        self.cmb_level.config(values=[str(v) for v in lvs])
        self.var_level.set(str(lvs[-1]))
        self.recompute()

    def _on_def_slide(self, _v=None) -> None:
        """滑块拖动 -> 回填防御输入框并重算。"""
        try:
            v = float(self.var_def_slide.get())
        except (TypeError, ValueError):
            return
        v = float(int(round(v)))
        self.lbl_def_slide.config(text="%d" % int(v))
        cur = (self.e_def.value or "").strip()
        if cur != "%d" % int(v):
            self.e_def.set("%d" % int(v))
        self.recompute()

    def _sync_def_slider(self, v: float) -> None:
        """外部设置防御值时同步滑块位置（不回触发重算）。"""
        try:
            self.var_def_slide.set(max(0.0, min(3000.0, float(v))))
            self.lbl_def_slide.config(text="%d" % int(v))
        except Exception:
            pass

    def set_enemy(self, en: Optional[EnemyStats]) -> None:
        self.enemy = en
        if not en:
            self.lbl_enemy.config(text="未选择敌人（可手动输入）")
            return
        self.lbl_enemy.config(
            text="%s｜HP %.0f｜DEF %.0f｜RES %.0f" % (en.name, en.hp, en.defense,
                                                     en.magic_resist))
        # 三项抗性分别回填：以前只有一个框，法抗和元素抗性根本填不进去，
        # 打法伤敌人时用的是敌方防御力当法抗，结果必然是错的。
        self.e_def.set("%d" % (en.defense or 0))
        self.e_res.set("%d" % (getattr(en, "magic_resist", 0) or 0))
        self.e_eres.set("%d" % (getattr(en, "element_resist", 0) or 0))
        self._sync_def_slider(en.defense)
        self.recompute()

    # ------------------------------------------------------------ 计算

    def _current_stats(self):
        op = self.operator
        if not op:
            return None
        try:
            elite = int(self.var_elite.get())
            level = int(self.var_level.get())
        except ValueError:
            return None
        st = op.stats_at(elite, level)
        if not st:
            return None
        atk = st.atk
        if self.var_trust.get():
            atk += op.trust_bonus.get("atk", 0.0)
        if self.var_pot.get():
            atk += op.potential_bonus.get("atk", 0.0)
        return st, atk

    def _f(self, entry, default: float) -> float:
        """从 LabeledEntry 读浮点数。"""
        try:
            return float(entry.var.get())
        except (ValueError, AttributeError, tk.TclError):
            return default

    def _make_input(self, atk: float, dtype: str, mult: float, flat: float,
                    pen_p: float, pen_f: float, boost: float, hits: int,
                    target_def: float, final_scaler: float = 1.0,
                    def_down: float = 0.0) -> DMG.DamageInput:
        return DMG.DamageInput(
            attack=atk, damage_type=dtype,
            attack_multiplier=mult, flat_attack_bonus=flat,
            target_defense=target_def,
            def_pen_flat=pen_f, def_pen_percent=pen_p,
            damage_boost=boost, hit_count=max(1, hits),
            final_scaler=final_scaler,
            def_down_percent=max(0.0, min(1.0, def_down)),
        )

    @staticmethod
    def _with_skill(inp: DMG.DamageInput, lv) -> DMG.DamageInput:
        """按技能等级派生一份新参数（不改动原对象）。

        技能对输出的影响有四条独立通道，缺一不可：
          atk_multiplier  面板攻击力倍率（真银斩 x3.0）
          flat_atk        固定攻击力加成
          hit_count       连击数（能天使 5 连射）
          dmg_scale       单次伤害缩放（阿米娅「攻击力 60% 的 8 连发」）
        攻击速度/间隔在外层按 interval 单独换算，不影响这里的伤害。
        """
        if lv is None:
            return inp
        i2 = copy.copy(inp)
        i2.attack_multiplier = inp.attack_multiplier * lv.atk_multiplier
        i2.flat_attack_bonus = inp.flat_attack_bonus + lv.flat_atk
        i2.hit_count = max(1, inp.hit_count * lv.hit_count)
        scale = getattr(lv, "dmg_scale", 1.0) or 1.0
        if scale != 1.0:
            # 单发缩放并入攻击力倍率：连击数已单独乘过，等效伤害一致
            i2.attack_multiplier *= scale
        return i2

    def _set_metrics(self, rows) -> None:
        """横向多列指标条：比竖排列表省一半高度，把空间留给曲线。"""
        frame = self.result.grid_frame
        for w in frame.winfo_children():
            w.destroy()
        keys = ("单次伤害", "DPH（每次攻击总伤害）", "DPS")
        # 短标签 + 6 列 x 2 行，指标区高度从 131px 降到 ~87px，省下的都给曲线
        short = {
            "单次伤害": "单次伤害", "DPH（每次攻击总伤害）": "DPH",
            "DPS": "DPS", "伤害类型": "类型",
            "基本伤害 A": "基本伤害 A", "保底 5%A": "保底 5%A",
            "有效抗性": "有效抗性", "实际攻击间隔": "攻击间隔",
            "连击次数": "连击", "破甲线": "破甲线", "技能": "技能",
        }
        per_row = 6
        max_rows = 2
        for idx, (label, value) in enumerate(rows):
            if idx >= per_row * max_rows:
                break
            r, c = divmod(idx, per_row)
            is_key = label in keys
            cell = tk.Frame(frame, background=BG_PANEL)
            cell.grid(row=r, column=c, sticky="w", padx=(0, PAD_M), pady=0)
            tk.Label(cell, text=short.get(label, label), background=BG_PANEL,
                     foreground=FG_DIM,
                     font=(FONT_UI, FS_SMALL), anchor="w").pack(anchor="w")
            valrow = tk.Frame(cell, background=BG_PANEL)
            valrow.pack(anchor="w")
            if is_key:
                # 关键指标：左侧一道强调色竖条 + 大号数字
                bar = tk.Frame(valrow, background=ACCENT, width=2)
                bar.pack(side="left", fill="y", padx=(0, 5))
                bar.pack_propagate(False)
            tk.Label(valrow, text=value, background=BG_PANEL,
                     foreground=ACCENT if is_key else FG,
                     font=(FONT_NUM, 15 if is_key else FS_NUM,
                           "bold" if is_key else "normal"),
                     anchor="w").pack(side="left")
        for r in range(max_rows):
            cell = tk.Frame(frame, background=BG_PANEL, height=1)
            cell.grid(row=r, column=per_row, sticky="nsw")

    # ------------------------------------------------------------ 对比模式

    def toggle_compare(self) -> None:
        """切换对比模式：显示/隐藏槽位面板，并重画。

        对比模式下槽位本身要占一条高度，所以把「计算过程」收起来，
        把省下的空间全部还给曲线——5 条线要看得清才谈得上对比。
        """
        on = bool(self.var_compare.get())
        if on and not self._cmp_packed:
            self.cmp_panel.pack(fill="x", pady=(PAD_XS, 0), before=self.chart)
            self._cmp_packed = True
            self.cmp_panel.refresh_choices()
        elif not on and self._cmp_packed:
            self.cmp_panel.pack_forget()
            self._cmp_packed = False
        try:
            self.result.set_steps_visible(not on)
        except AttributeError:
            pass
        self.recompute()

    def _compare_chart(self, kind: str, x_max: float):
        """对比模式：每位干员一条曲线。返回 (chart, 汇总行) 或 (None, [])。"""
        entries = self.cmp_panel.entries()
        if not entries:
            self.lbl_curve.config(text="对比模式：请在下方选择 2~5 位干员")
            return None, []

        # 公共条件：穿透 / 增伤 / 攻速 / 目标抗性 / 伤害类型都用当前加拐设置
        buf = self._read_buffs()
        pen_p = buf.res_percent()
        pen_f = buf.res_flat()
        boost = buf.fragile()
        hits = max(1, int(self._f(self.e_hits, 1.0)))
        speed = buf.get("aspd", 100.0) or 100.0
        dtype = self.var_dtype.get()
        target_def = self._defense_for_buffs(dtype)
        common = dict(damage_type=dtype, pen_percent=pen_p, pen_flat=pen_f,
                      boost=boost, hits=hits, target_def=target_def, speed=speed)

        triples = []
        break_lines = []
        for e in entries:
            built = CMP.build_entry_input(e, **common)
            if built is None:
                continue
            inp, iv, bl = built
            triples.append((e.label(), inp, iv))
            break_lines.append(bl)
        if not triples:
            self.lbl_curve.config(text="对比模式：所选干员没有可用面板数据")
            return None, []

        chart = CV.compare_chart(kind, triples, x_max=x_max,
                                 break_lines=break_lines,
                                 overlay_min=bool(self.var_overlay.get()),
                                 marker_xs=[target_def])

        # 汇总表（按 DPS 降序，一眼看出谁高）
        rows = CMP.evaluate(entries, **common)
        self._fill_compare_table(rows)

        names = "、".join(t[0] for t in triples)
        tip = "对比 %d 位：%s　｜　%s" % (
            len(triples), names,
            "%s（横轴 %s%s）" % (chart.title,
                                chart.x_label,
                                "/" + chart.x_unit if chart.x_unit else ""))
        if break_lines and any(break_lines):
            tip += "　｜　橙虚线为破甲线"
        self.lbl_curve.config(text=tip)
        return chart, rows

    def _fill_compare_table(self, rows) -> None:
        """无表格控件，用等宽字体在提示区下面列一行摘要。"""
        if not rows:
            return
        parts = []
        for r in sorted(rows, key=lambda x: -x.dps):
            parts.append("%s  DPS %.0f  DPH %.0f" % (r.label, r.dps, r.dph))
        self.lbl_cmp_table.config(text="　｜　".join(parts))

    # ------------------------------------------------------------ 加拐

    def _resist_for(self, dtype: str) -> float:
        """按伤害类型取对应的抗性输入。

        物理看法抗会算出个位数伤害——之前统一把「防御」那一格当万能抗性，
        法术技能（望的棋子、史尔特尔）全被掐到 5% 保底，看着就是算错了。
        """
        if dtype == C.DMG_MAGICAL:
            return self._f(self.e_res, 0.0)
        if dtype == C.DMG_ELEMENTAL:
            return self._f(self.e_eres, 0.0)
        return self._f(self.e_def, 0.0)

    def _defense_for_buffs(self, dtype: str) -> float:
        """取目标抗性原值。

        减防（``def_down``）现在作为 ``DamageInput.def_down_percent`` 传下去，
        **不能**在这里预先折算：曲线把「原始防御力」当横轴逐点扫描，
        若提前乘好，减防就只影响面板那一行数字，扫曲线时会被 set_def
        覆盖掉（用户看到的就是「填了减防但曲线没动」）。
        """
        return self._resist_for(dtype)

    def _read_buffs(self) -> "BUFF.BuffSet":
        """从界面上的乘区输入读出当前加拐配置。"""
        buf = BUFF.BuffSet()
        for key, name, unit, _desc in BUFF.ZONES:
            e = self.buff_entries.get(key)
            if e is None:
                continue
            # 「×」类乘区的默认值必须是 1.0（不启用），不是 0。
            # 这里之前写成 unit == "x"（ASCII x），而 ZONES 里的单位是
            # 全角乘号「×」(U+00D7)，比较永远为假 -> atk_final / final
            # 被读成 0.0，攻击力直接归零。清空输入框就复现。
            dflt = 1.0 if unit in ("×", "x", "X") else 0.0
            raw = e.var.get().strip()
            if not raw:
                val, on = dflt, False
            else:
                try:
                    val = float(raw)
                    on = True
                except ValueError:
                    val, on = dflt, False
            buf.set(key, val, on)
        if not buf.enabled.get("atk_final"):
            buf.set("atk_final", 1.0, False)
        if not buf.enabled.get("final"):
            buf.set("final", 1.0, False)
        return buf

    def recompute(self) -> None:
        st_atk = self._current_stats()
        if st_atk:
            st, atk = st_atk
            self.e_atk.set("%.0f" % atk)
            base_interval = st.attack_interval
        else:
            atk = self._f(self.e_atk, 0.0)
            base_interval = 1.0

        buf = self._read_buffs()
        mult = buf.atk_multiplier()
        flat = buf.flat_atk()
        pen_p = buf.res_percent()
        pen_f = buf.res_flat()
        boost = buf.fragile()
        hits = max(1, int(self._f(self.e_hits, 1.0)))
        speed = buf.get("aspd", 100.0)
        if speed <= 0:
            speed = 100.0
        dtype = self.var_dtype.get()
        # 按伤害类型选抗性；减防只作用于物理防御（法伤吃法抗，不受减防影响）
        target_def = self._defense_for_buffs(dtype)

        lv = self._skill_value()
        sk_interval_delta = lv.interval_delta if lv else 0.0
        sk_speed = lv.attack_speed if lv else 0.0

        def interval_of(speed_bonus: float, delta: float) -> float:
            iv = DMG.effective_attack_interval(base_interval + delta,
                                               speed + speed_bonus)
            return iv if iv > 0 else 0.01

        base_iv = interval_of(0.0, 0.0)
        sk_iv = interval_of(sk_speed, sk_interval_delta)
        interval = sk_iv if lv else base_iv

        base_inp = self._make_input(atk, dtype, mult, flat, pen_p, pen_f,
                                    boost, hits, target_def,
                                    final_scaler=buf.final_scaler(),
                                    def_down=buf.get("def_down", 0.0) / 100.0)
        sk_inp = self._with_skill(base_inp, lv)
        inp = sk_inp if lv else base_inp

        res = DMG.compute_damage(inp)
        dps = DMG.compute_dps(res.final_damage, interval, inp.hit_count)
        dph = res.final_damage * inp.hit_count
        break_line = (DMG.break_defense_threshold(res.base_damage)
                      if dtype == C.DMG_PHYSICAL else 0.0)

        rows = [
            ("单次伤害", "%.2f" % res.final_damage),
            ("DPH（每次攻击总伤害）", "%.2f" % dph),
            ("DPS", "%.1f" % dps),
            ("伤害类型", C.DMG_TYPE_LABELS.get(dtype, dtype)),
            ("基本伤害 A", "%.2f" % res.base_damage),
            ("保底 5%A", "%.2f%s" % (res.min_damage,
                                    "（已触发）" if res.floored else "")),
            ("有效抗性", "%.2f" % res.effective_resist),
            ("实际攻击间隔", "%.3f s" % interval),
        ]
        if getattr(self, "_healer", False):
            # 医疗干员不造成伤害：面板上没有「治疗」档，别让他们显示一个
            # 看着像伤害的 DPS。这里的数值仍然按当前类型算出来，
            # 但明确提示这是「治疗量估算」。
            rows[2] = ("DPS", "—（医疗干员）")
            self._set_metrics(rows)
            res.steps.insert(0, "【提示】%s 是医疗干员，不造成伤害；"
                                "下列数值可当作治疗量参考，"
                                "如需按输出计算请手动切换伤害类型。"
                             % self.operator.name)
            self.result.set_steps(res.steps)
            # 图表也换掉标题，避免误导
            self.lbl_curve.config(text="医疗干员：默认不展示输出曲线，"
                                       "可手动切换伤害类型后查看")
            self._chart = None
            self.chart.draw(None)
            return
        if inp.hit_count > 1:
            rows.append(("连击次数", str(inp.hit_count)))
        if break_line:
            rows.append(("破甲线", "%.1f" % break_line))
        if lv:
            rows.append(("技能", "%s %s" % (self._skill.name, self.var_skill_lv.get())))
        self._set_metrics(rows)
        self.result.set_steps(res.steps)

        # ---- 曲线
        kind = CV.DEFAULT_KIND
        for k, label in CV.CURVE_KINDS.items():
            if label == self.var_kind.get():
                kind = k
                break
        try:
            x_max = float(self.e_xmax.get())
        except (ValueError, tk.TclError):
            x_max = 0.0

        # ---- 对比模式：走另一条路径
        if self.var_compare.get():
            cmp_chart, _rows = self._compare_chart(kind, x_max)
            if cmp_chart is None:
                self.lbl_cmp_table.pack_forget()
                self._chart = None
                self.chart.draw(None)
                return
            if not self.lbl_cmp_table.winfo_ismapped():
                self.lbl_cmp_table.pack(anchor="w", pady=(1, 0),
                                        before=self.chart)
            self._chart = cmp_chart
            self.chart.draw(cmp_chart, current_x=target_def)
            return
        # 单干员模式：隐藏对比汇总
        if self.lbl_cmp_table.winfo_ismapped():
            self.lbl_cmp_table.pack_forget()

        chart = CV.build_chart(kind, inp, interval, x_max=x_max,
                               break_line=break_line)
        # 叠加「常态」对照（技能开启时才有意义）
        if lv:
            plain_chart = CV.build_chart(kind, base_inp, base_iv, x_max=x_max)
            chart.series[0] = CV.CurveSeries(
                name="技能中", points=chart.series[0].points, color="#e74c3c")
            chart.series.insert(1, CV.CurveSeries(
                name="常态", points=plain_chart.series[0].points,
                color="#4ea1f7"))

        if not self.var_overlay.get():
            chart.series = [s_ for s_ in chart.series if s_.note != "保底"]
            chart.series = chart.series[:1]

        self._chart = chart
        self.chart.draw(chart, current_x=target_def)
        note = chart.desc
        if lv:
            note += "　｜　已叠加技能「%s %s」与常态对照" % (
                self._skill.name, self.var_skill_lv.get())
        self.lbl_curve.config(text=note)


# ---------------------------------------------------------------- 对比模式

class CompareSlot:
    """一个对比槽位的控件集合。"""

    def __init__(self, parent, index: int, panel: "ComparePanel"):
        self.index = index
        self.panel = panel
        self.entry = CMP.CompareEntry(name="")
        self.operator: Optional[Operator] = None

        color = CV.COMPARE_COLORS[index % len(CV.COMPARE_COLORS)]
        outer = tk.Frame(parent, background=BG_PANEL,
                         highlightthickness=1, highlightbackground=DIVIDER)
        outer.pack(side="left", fill="x", expand=True, padx=(0, PAD_S))
        self.box = outer

        # 顶部色条：整条用该干员的曲线色，一眼对应图例。
        # 色条右端留一个 ⤢：点它只放大这一位干员的曲线。
        stripe_row = tk.Frame(outer, background=color, height=13)
        stripe_row.pack(fill="x")
        stripe_row.pack_propagate(False)
        stripe = tk.Frame(stripe_row, background=color, height=13)
        stripe.pack(side="left", fill="both", expand=True)
        self.btn_zoom_me = tk.Label(
            stripe_row, text="⤢", background=color, foreground="#10141a",
            font=(FONT_UI, FS_SMALL, "bold"), cursor="hand2", padx=4)
        self.btn_zoom_me.pack(side="right", fill="y")
        self.btn_zoom_me.bind("<Button-1>", lambda e, i=index: self._zoom_me(i))

        box = tk.Frame(outer, background=BG_PANEL)
        box.pack(fill="x", padx=5, pady=(2, 4))
        self.inner = box


        # 干员名（可输入）
        self.var_name = tk.StringVar()
        self.cmb = ComboBox(box, textvariable=self.var_name, state="normal", width=8,
                            compact=True)
        self.cmb.pack(fill="x", pady=(1, 1))
        self.cmb.bind("<<ComboboxSelected>>", lambda e: self._on_pick())
        self.cmb.bind("<Return>", lambda e: self._on_pick())

        # 技能（名字长，独占整行）
        self.var_skill = tk.StringVar(value="不使用技能")
        self.cmb_skill = ComboBox(box, textvariable=self.var_skill, width=8,
                                  state="readonly", values=["不使用技能"],
                                  compact=True)
        self.cmb_skill.pack(fill="x", pady=(0, 1))
        self.cmb_skill.bind("<<ComboboxSelected>>", lambda e: self._on_skill())

        # 精英 / 等级 / 技能等级：一行三个小下拉
        row2 = tk.Frame(box, background=BG_PANEL)
        row2.pack(fill="x")
        self.var_elite = tk.StringVar(value="2")
        self.cmb_elite = ComboBox(row2, textvariable=self.var_elite, width=2,
                                  state="readonly", values=["0", "1", "2"],
                                  compact=True)
        self.cmb_elite.pack(side="left")
        self.cmb_elite.bind("<<ComboboxSelected>>", lambda e: self._on_elite())
        self.var_level = tk.StringVar(value="90")
        self.cmb_level = ComboBox(row2, textvariable=self.var_level, width=3,
                                  state="readonly", values=["90"],
                                  compact=True)
        self.cmb_level.pack(side="left", padx=(1, 0))
        self.cmb_level.bind("<<ComboboxSelected>>", lambda e: self._changed())
        self.var_skill_lv = tk.StringVar(value="专三")
        self.cmb_skill_lv = ComboBox(row2, textvariable=self.var_skill_lv, width=3,
                                     state="readonly",
                                     values=list(CMP.DEFAULT_SKILL_LEVELS),
                                     compact=True)
        self.cmb_skill_lv.pack(side="left", padx=(1, 0))
        self.cmb_skill_lv.bind("<<ComboboxSelected>>", lambda e: self._changed())
        self.cmb_skill.bind("<<ComboboxSelected>>", lambda e: self._on_skill())

        # 双击色条或名字：同样能把这个干员的曲线单独放大
        for w in (stripe, stripe_row, outer, self.cmb):
            w.bind("<Double-Button-1>", lambda e, i=index: self._zoom_me(i))

    def _zoom_me(self, index: int) -> None:
        """双击槽位 -> 放大该干员的曲线。"""
        panel = self.panel.parent if hasattr(self.panel, "parent") else None
        if panel is None:
            return
        panel.zoom_operator_curve(index)

    # ---------------------------------------------------------- 事件

    def _on_pick(self) -> None:
        name = self.var_name.get().strip()
        if not name:
            return
        op = self.panel.resolve(name)
        if op is None:
            self.panel.lbl_tip.config(text="找不到干员「%s」" % name)
            return
        self.set_operator(op)

    def set_operator(self, op: Operator) -> None:
        self.operator = op
        self.var_name.set(op.name)
        elites = sorted(op.phases.keys())
        self.cmb_elite.config(values=[str(e) for e in elites])
        self.var_elite.set(str(max(elites)) if elites else "0")
        self._on_elite()

    def _on_elite(self) -> None:
        if not self.operator:
            return
        try:
            elite = int(self.var_elite.get())
        except ValueError:
            return
        lvs = self.operator.levels_of(elite)
        if not lvs:
            return
        self.cmb_level.config(values=[str(v) for v in lvs])
        self.var_level.set(str(lvs[-1]))
        self._changed()

    def _on_skill(self) -> None:
        """选技能后刷新可选等级（有的技能没有全部等级档）。"""
        self._sync_skill_levels()
        self._changed()

    def _sync_skill_levels(self) -> None:
        """按所选技能刷新等级候选，避免选了不存在的档位被静默忽略。"""
        keys: List[str] = []
        if self.operator:
            label = self.var_skill.get()
            if label.startswith("S"):
                try:
                    idx = int(label[1]) - 1
                except (ValueError, IndexError):
                    idx = -1
                skills = list(getattr(self.operator, "skills", None) or [])
                if 0 <= idx < len(skills):
                    keys = list(skills[idx].level_keys)
        if not keys:
            keys = list(CMP.DEFAULT_SKILL_LEVELS)
        self.cmb_skill_lv.config(values=keys)
        if self.var_skill_lv.get() not in keys:
            self.var_skill_lv.set(keys[-1])

    def _changed(self) -> None:
        self.panel.sync_from_slots()

    # ---------------------------------------------------------- 取值

    def build_entry(self) -> CMP.CompareEntry:
        e = self.entry
        e.name = self.var_name.get().strip()
        e.operator = self.operator
        try:
            e.elite = int(self.var_elite.get())
        except ValueError:
            e.elite = 2
        try:
            e.level = int(self.var_level.get())
        except ValueError:
            e.level = 90
        e.trust = self.panel.parent.var_trust.get()
        e.potential = self.panel.parent.var_pot.get()
        # 技能下标
        label = self.var_skill.get()
        e.skill_index = -1
        if self.operator and label.startswith("S"):
            try:
                e.skill_index = int(label[1]) - 1
            except (ValueError, IndexError):
                e.skill_index = -1
        e.skill_level = self.var_skill_lv.get()
        return e

    def refresh_skills(self) -> None:
        """干员变了就重建技能下拉。"""
        self.refresh_skills_preserve("")

    def refresh_skills_preserve(self, keep: str) -> None:
        """重建技能下拉，尽量保留原选择（干员没变时不会丢选择）。"""
        opts = ["不使用技能"]
        if self.operator:
            for sk in (getattr(self.operator, "skills", None) or []):
                opts.append("S%d  %s" % (sk.index, sk.name))
        self.cmb_skill.config(values=opts)
        self.var_skill.set(keep if keep in opts else opts[0])
        self._sync_skill_levels()

    def clear(self) -> None:
        self.operator = None
        self.var_name.set("")
        self.cmb_skill.config(values=["不使用技能"])
        self.var_skill.set("不使用技能")
        self.cmb_level.config(values=["90"])
        self.var_level.set("90")
        self.cmb_elite.config(values=["0", "1", "2"])
        self.var_elite.set("2")


class ComparePanel(tk.Frame):
    """对比槽位面板：至多 5 位干员，各自选精英/等级/技能。"""

    SLOTS = CV.MAX_COMPARE

    def __init__(self, master, parent: "DamagePanel"):
        super().__init__(master, background=BG_PANEL)
        self.parent = parent

        head = tk.Frame(self, background=BG_PANEL)
        head.pack(fill="x", pady=(0, 2))
        tk.Label(head, text="对比干员", background=BG_PANEL, foreground=ACCENT,
                 font=(FONT_UI, FS_BODY, "bold")).pack(side="left")
        self.lbl_tip = tk.Label(head, text="最多 5 位", background=BG_PANEL,
                                foreground=FG_DIM,
                                font=(FONT_UI, FS_SMALL))
        self.lbl_tip.pack(side="left", padx=(6, 0))
        ttk.Button(head, text="填入当前", style="App.TButton", width=8,
                   command=self.fill_current).pack(side="right", padx=2)
        ttk.Button(head, text="清空", style="App.TButton", width=4,
                   command=self.clear_all).pack(side="right", padx=2)

        rowbox = tk.Frame(self, background=BG_PANEL)
        rowbox.pack(fill="x")
        self.slots: List[CompareSlot] = []
        for i in range(self.SLOTS):
            self.slots.append(CompareSlot(rowbox, i, self))

        # 保证下拉候选是最新的
        self.refresh_choices()

    # ---------------------------------------------------------- 对外

    def refresh_choices(self) -> None:
        names = self.parent.app.operator_names()
        for s in self.slots:
            s.cmb.config(values=names)

    def resolve(self, name: str) -> Optional[Operator]:
        return self.parent.app.find_operator(name)

    def entries(self) -> List[CMP.CompareEntry]:
        """只返回真正选了干员的槽位（保持顺序）。"""
        out = []
        for s in self.slots:
            e = s.build_entry()
            if e.operator is not None:
                out.append(e)
        return out

    def fill_current(self) -> None:
        """把当前单干员模式的选择填进第一个空槽。"""
        op = self.parent.operator
        if not op:
            self.lbl_tip.config(text="先在上方选一位干员")
            return
        target = next((s for s in self.slots if s.operator is None), None)
        if target is None:
            self.lbl_tip.config(text="槽位已满（5 位）")
            return
        target.set_operator(op)
        target.refresh_skills()
        # 同步当前的精英 / 等级 / 技能选择
        target.var_elite.set(self.parent.var_elite.get())
        target._on_elite()
        target.var_level.set(self.parent.var_level.get())
        sk = self.parent.var_skill.get()
        if sk in target.cmb_skill.cget("values"):
            target.var_skill.set(sk)
        target.var_skill_lv.set(self.parent.var_skill_lv.get())
        target._changed()

    def clear_all(self) -> None:
        for s in self.slots:
            s.clear()
        self.lbl_tip.config(text="")
        self.parent.recompute()

    def sync_from_slots(self) -> None:
        """槽位改动后刷新技能下拉并重画。"""
        for s in self.slots:
            if s.operator is not None:
                cur = s.var_skill.get()
                s.refresh_skills_preserve(cur)
        n = len(self.entries())
        self.lbl_tip.config(text="已选 %d/%d 位" % (n, self.SLOTS) if n else "")
        self.parent.recompute()


# ---------------------------------------------------------------- 绘图

SERIES_FALLBACK = ["#4ea1f7", "#e74c3c", "#2ecc71", "#f1c40f", "#9b59b6", "#1abc9c"]
class ChartCanvas(tk.Canvas):
    """多曲线折线图：面积渐变 + 精细网格 + 胶囊图例 + 当前值标签。"""

    BG_CHART = "#1b2029"      # 图表底（比卡片更深一档）
    GRID = "#262d39"          # 主网格
    GRID_SOFT = "#212731"     # 次网格
    AXIS = "#3b4554"

    def __init__(self, master, **kw):
        kw.setdefault("background", self.BG_CHART)
        super().__init__(master, highlightthickness=0, bd=0, **kw)
        self._chart: Optional[CV.CurveChart] = None
        self._cur_x: Optional[float] = None
        # 悬停：hx 是悬停处的 x 值（防御），None 表示鼠标不在图上
        self._hover_x: Optional[float] = None
        self._plot = (0, 0, 0, 0, 0, 0, 0, 0)   # pad_l,pad_r,pad_t,pad_b,x0,x1,y0,y1
        self.bind("<Configure>", lambda e: self._redraw())
        self.bind("<Motion>", self._on_motion)
        self.bind("<Leave>", self._on_leave)

    # -------------------------------------------------- 对外

    def draw(self, chart: Optional[CV.CurveChart],
             current_x: Optional[float] = None) -> None:
        self._chart = chart
        self._cur_x = current_x
        self._redraw()

    # -------------------------------------------------- 悬停

    def pixel_to_x(self, x: float) -> Optional[float]:
        """画布 x 像素 -> 曲线上的 x 值（防御）。"""
        pad_l, pad_r, pad_t, pad_b, x0, x1, y0, y1 = self._plot
        w = max(self.winfo_width(), 160)
        if x1 <= x0 or not (pad_l <= x <= w - pad_r):
            return None
        return x0 + (x - pad_l) / max(1.0, (w - pad_l - pad_r)) * (x1 - x0)

    def x_to_pixel(self, x: float) -> float:
        pad_l, pad_r, pad_t, pad_b, x0, x1, y0, y1 = self._plot
        w = max(self.winfo_width(), 160)
        return pad_l + (x - x0) / max(1e-9, (x1 - x0)) * (w - pad_l - pad_r)

    def _on_motion(self, event) -> None:
        if not self._chart or not self._chart.series:
            return
        xv = self.pixel_to_x(event.x)
        if xv is None:
            if self._hover_x is not None:
                self._hover_x = None
                self._redraw()
            return
        if self._hover_x is None or abs(xv - self._hover_x) > 1e-9:
            self._hover_x = xv
            self._redraw()

    def _on_leave(self, _e=None) -> None:
        if self._hover_x is not None:
            self._hover_x = None
            self._redraw()

    # -------------------------------------------------- 工具

    def _nice_step(self, span: float, target_ticks: int = 5) -> float:
        if span <= 0:
            return 1.0
        raw = span / max(1, target_ticks)
        mag = 10 ** __import__("math").floor(__import__("math").log10(raw))
        for m in (1, 2, 2.5, 5, 10):
            if raw <= m * mag:
                return m * mag
        return 10 * mag

    @staticmethod
    def _mix(c1: str, c2: str, t: float) -> str:
        """按 t 在两色之间插值（t=0 取 c1）。"""
        a = [int(c1[i:i + 2], 16) for i in (1, 3, 5)]
        b = [int(c2[i:i + 2], 16) for i in (1, 3, 5)]
        return "#%02x%02x%02x" % tuple(
            int(a[i] + (b[i] - a[i]) * t) for i in range(3))

    def _clip_area(self, pts: List[float], color: str) -> None:
        """沿曲线下沿画一条阶梯状半透明填色（按列画竖线近似）。"""
        if len(pts) < 4:
            return
        step = 6.0
        x_first, x_last = pts[0], pts[-2]
        bottom = getattr(self, "_axis_bottom", self.winfo_height())
        shade = self._mix(self.BG_CHART, color, 0.10)
        fade = self._mix(self.BG_CHART, color, 0.04)
        x = x_first
        while x < x_last:
            y = self._interp_pts(pts, x)
            if y is not None and bottom > y + 2:
                self.create_line(x, y, x, bottom, fill=fade, width=step)
                self.create_line(x, y, x, y + (bottom - y) * 0.55,
                                 fill=shade, width=step)
            x += step

    @staticmethod
    def _interp_pts(pts: List[float], x: float) -> Optional[float]:
        """在折线（扁平 x,y 序列）上按 x 插值取 y。"""
        for i in range(0, len(pts) - 2, 2):
            x1, y1 = pts[i], pts[i + 1]
            x2, y2 = pts[i + 2], pts[i + 3]
            if (x1 <= x <= x2) or (x2 <= x <= x1):
                if x2 == x1:
                    return y1
                t = (x - x1) / (x2 - x1)
                return y1 + (y2 - y1) * t
        return None

    # -------------------------------------------------- 绘制

    def _redraw(self) -> None:
        self.delete("all")
        ch = self._chart
        w = max(self.winfo_width(), 160)
        h = max(self.winfo_height(), 100)
        if ch is None or not ch.series:
            self.create_text(w / 2, h / 2, text="选择干员后显示曲线",
                             fill="#4a5566", font=(FONT_UI, FS_BODY))
            return

        pad_l, pad_r, pad_t, pad_b = 58, 18, 34, 34
        self._axis_bottom = h - pad_b

        (x0, x1) = ch.x_range
        (y0, y1) = ch.y_range
        if x1 <= x0:
            x1 = x0 + 1
        if y1 <= y0:
            y1 = y0 + 1
        y1 = y1 + (y1 - y0) * 0.08
        self._plot = (pad_l, pad_r, pad_t, pad_b, x0, x1, y0, y1)

        def px(x: float) -> float:
            return pad_l + (x - x0) / (x1 - x0) * (w - pad_l - pad_r)

        def py(y: float) -> float:
            return h - pad_b - (y - y0) / (y1 - y0) * (h - pad_t - pad_b)

        # ---- 网格（主/次两级，越靠上越淡）
        ys = self._nice_step(y1 - y0)
        v = y0
        while v <= y1 + 1e-9:
            yy = py(v)
            self.create_line(pad_l, yy, w - pad_r, yy, fill=self.GRID_SOFT)
            v += ys
        xs = self._nice_step(x1 - x0)
        v = x0
        while v <= x1 + 1e-9:
            xx = px(v)
            self.create_line(xx, pad_t, xx, h - pad_b, fill=self.GRID_SOFT)
            v += xs

        # ---- 曲线（先画面积，再画线，保证线在最上层）
        self._axis_bottom = h - pad_b
        for i, s in enumerate(ch.series):
            if len(s.points) < 2:
                continue
            color = s.color or SERIES_FALLBACK[i % len(SERIES_FALLBACK)]
            if s.note != "保底":
                pts: List[float] = []
                for x, y in s.points:
                    pts.extend([px(x), py(y)])
                self._clip_area(pts, color)

        for i, s in enumerate(ch.series):
            if len(s.points) < 2:
                continue
            pts: List[float] = []
            for x, y in s.points:
                pts.extend([px(x), py(y)])
            color = s.color or SERIES_FALLBACK[i % len(SERIES_FALLBACK)]
            dash = (5, 4) if s.note == "保底" else ()
            self.create_line(*pts, fill=color,
                             width=1 if dash else 2,
                             dash=dash, capstyle="round", joinstyle="round")

        # ---- 坐标轴（只画左、下两条，颜色略亮于网格）
        self.create_line(pad_l, pad_t - 6, pad_l, h - pad_b, fill=self.AXIS)
        self.create_line(pad_l, h - pad_b, w - pad_r, h - pad_b, fill=self.AXIS)

        # ---- 刻度文字
        v = y0
        while v <= y1 + 1e-9:
            self.create_text(pad_l - 8, py(v), text=self._fmt(v), anchor="e",
                             fill="#6d7a8c", font=(FONT_NUM, FS_MICRO))
            v += ys
        v = x0
        while v <= x1 + 1e-9:
            self.create_text(px(v), h - pad_b + 8, text=self._fmt(v), anchor="n",
                             fill="#6d7a8c", font=(FONT_NUM, FS_MICRO))
            v += xs

        # ---- 轴标题
        self.create_text((pad_l + w - pad_r) / 2, h - 10,
                         text=("%s (%s)" % (ch.x_label, ch.x_unit)
                               if ch.x_unit else ch.x_label),
                         fill="#7e8b9d", font=(FONT_UI, FS_MICRO))
        self.create_text(8, pad_t - 14, text=ch.y_label, anchor="w",
                         fill="#7e8b9d", font=(FONT_UI, FS_MICRO))

        # ---- 破甲线
        if ch.marker_x is not None and x0 <= ch.marker_x <= x1:
            mx = px(ch.marker_x)
            self.create_line(mx, pad_t - 6, mx, h - pad_b, fill="#e67e22",
                             dash=(4, 3), width=1)
            txt = "%s %s" % (ch.marker_label or "", self._fmt(ch.marker_x))
            tw = self.create_text(mx + 5, pad_t - 14, text=txt.strip(),
                                  anchor="w", fill="#e67e22",
                                  font=(FONT_UI, FS_MICRO))
            bb = self.bbox(tw)
            if bb:
                self.create_rectangle(bb[0] - 3, bb[1] - 1, bb[2] + 3, bb[3] + 1,
                                      fill=self.BG_CHART, outline="")
                self.tag_raise(tw)

        # ---- 当前值竖线 + 每条曲线的点与数值
        if self._cur_x is not None and x0 <= self._cur_x <= x1:
            cx = px(self._cur_x)
            self.create_line(cx, pad_t - 6, cx, h - pad_b, fill="#f1c40f",
                             dash=(2, 3), width=1)
            real = [s for s in ch.series if s.note != "保底"]
            multi = len(real) > 1
            vals = {}
            for i, s in enumerate(ch.series):
                if s.note == "保底":
                    continue
                y = self._interp(s.points, self._cur_x)
                if y is None:
                    continue
                color = s.color or SERIES_FALLBACK[i % len(SERIES_FALLBACK)]
                vals[i] = (y, color)
            top_idx = max(vals, key=lambda k: vals[k][0]) if vals else None
            for i, (y, color) in vals.items():
                yy = py(y)
                self.create_oval(cx - 8, yy - 8, cx + 8, yy + 8,
                                 outline=color, width=1, fill="")
                self.create_oval(cx - 3, yy - 3, cx + 3, yy + 3,
                                 fill=color, outline=self.BG_CHART, width=1)
                if not multi:
                    off = -14
                else:
                    off = -12 if i == top_idx else 13
                label = self.create_text(cx + 6, yy + off, text="%.0f" % y,
                                         anchor="w", fill=color,
                                         font=(FONT_NUM, FS_MICRO, "bold"))
                bb = self.bbox(label)
                if bb:
                    self.create_rectangle(bb[0] - 3, bb[1] - 1,
                                          bb[2] + 3, bb[3] + 1,
                                          fill=self.BG_CHART, outline="")
                    self.tag_raise(label)

        # ---- 鼠标悬停层（画在最上层，盖住曲线）
        if self._hover_x is not None and x0 <= self._hover_x <= x1:
            self._draw_hover(ch, px, py, w, h, pad_l, pad_r, pad_t, pad_b)

        # ---- 图例（右上角胶囊，避免和左上角 y 轴标题打架）
        self._draw_legend(ch, w, pad_r)

    # -------------------------------------------------- 悬停浮层

    def _draw_hover(self, ch, px, py, w: int, h: int,
                    pad_l: int, pad_r: int, pad_t: int, pad_b: int) -> None:
        """鼠标处的竖线 + 每条曲线的取值浮层。"""
        hx = self._hover_x
        cx = px(hx)
        self.create_line(cx, pad_t - 4, cx, h - pad_b,
                         fill="#8fa3bb", dash=(2, 2), width=1)

        rows = []          # (颜色, 名字, 值, 是否虚线)
        for i, s in enumerate(ch.series):
            y = self._interp(s.points, hx)
            if y is None:
                continue
            color = s.color or SERIES_FALLBACK[i % len(SERIES_FALLBACK)]
            rows.append((color, s.name, y, s.note == "保底", i))
        # hover_series 只进浮层、不画线：让鼠标不管落在哪条
        # 曲线上，都能看到该防御值下的 DPS 与 DPH。
        for j, s in enumerate(getattr(ch, "hover_series", []) or []):
            y = self._interp(s.points, hx)
            if y is None:
                continue
            color = s.color or SERIES_FALLBACK[(len(rows) + j) % len(SERIES_FALLBACK)]
            rows.append((color, s.name, y, False, len(ch.series) + j))

        # 竖线上的取点圆
        for color, name, y, dashed, i in rows:
            yy = py(y)
            self.create_oval(cx - 4, yy - 4, cx + 4, yy + 4,
                             fill=color, outline=self.BG_CHART, width=1)

        if not rows:
            return

        # ---- 浮层文字
        # 标题写成「防御力 1601」这样，明确是哪个自变量
        xname = (ch.x_label or "横轴").replace(" ", "")
        head = "%s  %s%s%s" % (xname,
                               self._fmt(hx),
                               ch.x_unit or "",
                               "")
        fs = FS_SMALL
        # 每行统一成「指标  数值」，让用户一眼看出是 DPS 还是 DPH
        body = []
        for _c, name, y, _d, _i in rows:
            unit = ""
            for ser in list(ch.series) + list(getattr(ch, "hover_series", []) or []):
                if ser.name == name:
                    unit = (ser.unit or "").strip()
                    break
            body.append("%s  %s%s" % (name, self._fmt(y), unit))
        all_lines = [head] + body
        tw = max(len(t) for t in all_lines) * (fs + 1) + 30
        th = len(all_lines) * (fs + 5) + 12

        # 位置：鼠标右上方，靠边时翻到左侧
        tx = cx + 12
        if tx + tw > w - 4:
            tx = cx - tw - 12
        tx = max(4, tx)
        ty = pad_t + 4
        if ty + th > h - pad_b:
            ty = max(4, h - pad_b - th)

        self.create_rectangle(tx, ty, tx + tw, ty + th,
                              fill="#232a35", outline="#4a5568", width=1)
        # 标题
        self.create_text(tx + 8, ty + 6, text=head, anchor="nw",
                         fill="#ffffff", font=(FONT_NUM, fs, "bold"))
        # 每条曲线：小色块 + 名字 + 值（右对齐）
        y = ty + 6 + fs + 5
        for (color, name, val, dashed, _i) in rows:
            unit = ""
            for ser in ch.series:
                if ser.name == name:
                    unit = (ser.unit or "").strip()
                    break
            self.create_line(tx + 8, y + fs // 2 + 1, tx + 18, y + fs // 2 + 1,
                             fill=color, width=2,
                             dash=(3, 2) if dashed else ())
            self.create_text(tx + 22, y, text=name, anchor="nw",
                             fill="#c8d2e0", font=(FONT_UI, fs))
            if unit:
                # 单位标签（DPS/DPH）用暗色小字，跟在名字后面
                nm_w = len(name) * (fs + 1)
                self.create_text(tx + 24 + nm_w, y + 1, text=unit, anchor="nw",
                                 fill="#7f8b9c", font=(FONT_NUM, max(6, fs - 1)))
            self.create_text(tx + tw - 8, y, text=self._fmt(val), anchor="ne",
                             fill=color, font=(FONT_NUM, fs, "bold"))
            y += fs + 5

    def _draw_legend(self, ch, w: int, pad_r: int) -> None:
        """右上角图例：每项前面一小段线 + 名字，单条时也显示。"""
        items = []
        for i, s in enumerate(ch.series):
            if len(s.points) < 2:
                continue
            color = s.color or SERIES_FALLBACK[i % len(SERIES_FALLBACK)]
            name = s.name
            items.append((color, name, s.note == "保底"))
        if not items:
            return
        f = (FONT_UI, FS_MICRO)
        # 先算宽度
        widths = []
        for color, name, dashed in items:
            tw = self.create_text(-1000, -1000, text=" " + name, font=f)
            bb = self.bbox(tw)
            widths.append((bb[2] - bb[0]) if bb else 60)
            self.delete(tw)
        box_w = max(widths) + 26
        row_h = 15
        x_right = w - pad_r - 4
        x_left = x_right - box_w
        y_top = 6
        self.create_rectangle(x_left, y_top, x_right,
                              y_top + row_h * len(items) + 6,
                              fill=self._mix(self.BG_CHART, "#ffffff", 0.03),
                              outline=self.GRID)
        y = y_top + 11
        for (color, name, dashed), tw in zip(items, widths):
            self.create_line(x_left + 7, y, x_left + 20, y, fill=color,
                             width=2, dash=(4, 3) if dashed else ())
            self.create_text(x_left + 25, y, text=name, anchor="w",
                             fill="#c8d2e0", font=f)
            y += row_h

    def _fmt(self, v: float) -> str:
        av = abs(v)
        if av >= 10000:
            return "%.0fk" % (v / 1000.0)
        if av >= 100:
            return "%.0f" % v
        if av >= 10:
            return "%.1f" % v
        return "%.2f" % v

    def _interp(self, points: List[Tuple[float, float]],
                x: float) -> Optional[float]:
        if not points:
            return None
        if x <= points[0][0]:
            return points[0][1]
        if x >= points[-1][0]:
            return points[-1][1]
        for i in range(1, len(points)):
            xa, ya = points[i - 1]
            xb, yb = points[i]
            if xa <= x <= xb:
                if xb == xa:
                    return ya
                t = (x - xa) / (xb - xa)
                return ya + (yb - ya) * t
        return None