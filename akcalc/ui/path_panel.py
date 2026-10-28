"""寻路分析面板：关卡目录选择、地图渲染、路线分析、出怪时间轴。

与伤害计算完全独立——这里不出现任何干员相关的控件。
"""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Dict, List, Optional

from ..core import routes as RT
from ..core.catalog import (CATEGORY_DESC, CATEGORY_ORDER, Stage,
                            StageCatalog, StageGroup)
from ..core.coords import coord_label
from ..core.enemies import (enemies_of_level, level_enemy_ids,
                            level_enemy_overrides, spawn_unmovable_of_ref)
from ..core.maps import get_level
from ..core.models import EnemyStats, GameMap
from ..core.timeline import (Timeline, fill_names, parse_timeline,
                            positions_at)
from .map_canvas import MapCanvas
from .playback import PlaybackBar
from .timeline_canvas import TimelineCanvas
from .widgets import (ACCENT, ACCENT_SOFT, ACCENT_TXT, BG, BG_DEEP, BG_INPUT,
                      BG_PANEL,
                      BG_SUNKEN, BORDER, ComboBox, DIVIDER, FG, FG_DIM,
                      FONT_NUM, FONT_UI, FS_BODY, FS_MICRO, FS_NUM, FS_SMALL,
                      FS_TITLE, PAD_L, PAD_M, PAD_S, PAD_XS, SectionFrame,
                      harmonize)

#: 分类卡片的强调色。
#:
#: 全部统一为 ACCENT（和「伤害计算」同一支蓝）。以前 12 类关卡各配一个
#: 色相（紫/橙/绿/青/粉……），寻路首页看着比伤害计算页花得多，而且这些
#: 颜色和地图里的路线配色、机制机关配色互相干扰——用户在地图上看到一抹
#: 橙，分不清那是「活动关卡」的标签色还是「陷阱机关」。
#:
#: 现在分类只靠文字识别，颜色只表达「这是本页的强调元素」。
_CAT_ACCENT = {
    "main":       ACCENT,
    "sidestory":  ACCENT,
    "branchline": ACCENT,
    "activity":   ACCENT,
    "weekly":     ACCENT,
    "campaign":   ACCENT,
    "tower":      ACCENT,
    "crisis":     ACCENT,
    "roguelike":  ACCENT,
    "sandbox":    ACCENT,
    "guide":      FG_DIM,
    "other":      FG_DIM,
}

#: 分类卡片在「未分类」时统一用 ACCENT，避免 .get 的默认值和表里不一致。
_DEFAULT_CAT_ACCENT = ACCENT


class PathPanel(ttk.Frame):
    """寻路分析。"""

    def __init__(self, master, app):
        super().__init__(master, style="App.TFrame")
        self.app = app
        self.game_map: Optional[GameMap] = None
        self.analyses: List[RT.RouteAnalysis] = []
        self.enemies: List[EnemyStats] = []
        self.timeline: Optional[Timeline] = None
        self.catalog: Optional[StageCatalog] = None
        self._groups: List[StageGroup] = []
        self._stages: List[Stage] = []
        # 第三层「节点类型」当前可选列表，元素为 (key, 显示名, 数量)
        self._node_types: List[tuple] = []
        self._adversity_map: Dict[str, Stage] = {}
        #: 当前关卡的地图相对路径（缓存是按它落盘的），出怪列表要用
        self._cur_rel_path: str = ""
        #: 用户是否亲手勾过「撇除无害单位」；勾过就不再按关卡自动改默认值
        self._harmless_touched: bool = False

        self._build()

    # ------------------------------------------------------------ 构建

    def _build(self) -> None:
        # ---- 顶部：返回 + 标题
        bar = tk.Frame(self, background=BG)
        bar.pack(fill="x", padx=PAD_M, pady=(PAD_M, 0))
        self.app.build_panel_header(
            bar, "寻路分析", "PATHFINDING",
            "还原敌人行进路线与出怪时间轴（不含干员数据）")

        # ---- 分类主菜单 / 关卡详情 两层视图
        # 进入寻路分析先看到大分类（主题曲/插曲/别传…），点进去才到关卡。
        self._stack = tk.Frame(self, background=BG)
        self._stack.pack(fill="both", expand=True)
        self._build_cat_menu(self._stack)
        self._build_detail(self._stack)
        self.show_cat_menu()

    # ------------------------------------------------------------ 分类主菜单

    def _build_cat_menu(self, master) -> None:
        """分类主菜单：每个大分类一张卡片。"""
        self.cat_menu = tk.Frame(master, background=BG)

        head = tk.Frame(self.cat_menu, background=BG)
        head.pack(fill="x", padx=PAD_M, pady=(0, PAD_S))
        tk.Label(head, text="选择地图分类", background=BG, foreground=FG,
                 font=(FONT_UI, FS_TITLE + 2, "bold")).pack(anchor="w")
        self.lbl_cat_hint = tk.Label(
            head, text="分类方式与 PRTS 关卡一览一致。",
            background=BG, foreground=FG_DIM, font=(FONT_UI, FS_SMALL))
        self.lbl_cat_hint.pack(anchor="w", pady=(2, 0))

        # 可滚动区域：分类卡片按 3 列铺开
        wrap = tk.Frame(self.cat_menu, background=BG)
        wrap.pack(fill="both", expand=True, padx=PAD_M, pady=(0, PAD_M))

        self._cat_canvas = tk.Canvas(wrap, background=BG, highlightthickness=0)
        vsb = ttk.Scrollbar(wrap, orient="vertical",
                            command=self._cat_canvas.yview)
        self._cat_canvas.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y")
        self._cat_canvas.pack(side="left", fill="both", expand=True)

        self._cat_grid = tk.Frame(self._cat_canvas, background=BG)
        self._cat_win = self._cat_canvas.create_window(
            (0, 0), window=self._cat_grid, anchor="nw")

        def _on_conf(e=None):
            self._cat_canvas.configure(
                scrollregion=self._cat_canvas.bbox("all"))
            self._cat_canvas.itemconfigure(
                self._cat_win, width=self._cat_canvas.winfo_width())

        self._cat_grid.bind("<Configure>", _on_conf)
        self._cat_canvas.bind("<Configure>", _on_conf)
        for seq, delta in (("<MouseWheel>", None), ("<Button-4>", -1),
                           ("<Button-5>", 1)):
            self._cat_canvas.bind(
                seq, lambda e, d=delta: self._wheel(e, d))

        self._cat_cards = []
        self._fill_cat_cards()

    # ------------------------------------------------------------ 生命周期

    def suspend(self) -> None:
        """离开寻路分析时被 app 调用：停掉播放，释放后台定时器。

        为什么必须有这一手：``after`` 定时器挂在 Tk 解释器上，控件被
        ``pack_forget`` 之后**依然会继续触发**。以前切到伤害计算或图鉴，
        寻路分析仍在后台按 60fps 重绘地图（每帧烘焙 + 缩放），CPU 白白
        被吃掉一大块。这里显式停播，``PlaybackBar._frame`` 里还有第二道
        「看不见就停」的保险。
        """
        pb = getattr(self, "playback", None)
        if pb is not None:
            try:
                pb.suspend()
            except Exception:
                pass
        # 播放时画在地图上的敌人圆点会留在画布上，切回来的时候时间游标
        # 还在原地，但圆点已经不刷新了——清掉更不容易误会。
        self._clear_trail()

    def _wheel(self, event, delta):
        """滚轮：Windows 下 event.delta 是 120 的倍数。"""
        step = -1 if event.delta > 0 else 1
        self._cat_canvas.yview_scroll(step * 2, "units")

    def _fill_cat_cards(self) -> None:
        """按 CATEGORY_ORDER 生成分类卡片（只显示有关卡的分类）。"""
        for w in self._cat_grid.winfo_children():
            w.destroy()
        self._cat_cards = []

        cat = self.catalog
        total = 0
        rows = []
        for key, name in CATEGORY_ORDER:
            if not cat:
                continue
            groups = cat.category_groups(key)
            n = sum(len(g.stages) for g in groups)
            if n <= 0:
                continue
            desc = CATEGORY_DESC.get(key, "")
            rows.append((key, name, desc, n, len(groups)))
            total += n

        self.lbl_cat_hint.config(
            text="共 %d 关，分 %d 个分类。分类方式与 PRTS 关卡一览一致。"
                 % (total, len(rows)) if rows else "关卡目录尚未载入")

        for col in range(3):
            self._cat_grid.columnconfigure(col, weight=1, uniform="cat")

        for i, (key, name, desc, n, ng) in enumerate(rows):
            card = self._make_cat_card(
                self._cat_grid, key, name, desc, n, ng)
            card.grid(row=i // 3, column=i % 3, sticky="nsew",
                      padx=(0 if i % 3 == 0 else PAD_S,
                            0 if i % 3 == 2 else PAD_S),
                      pady=(0, PAD_S))
            self._cat_cards.append(card)

    def _make_cat_card(self, master, key, name, desc, n_stages, n_groups):
        """一张分类卡片：标题 + 关数 + 说明，整卡可点。"""
        accent = _CAT_ACCENT.get(key, _DEFAULT_CAT_ACCENT)
        card = tk.Frame(master, background=BG_PANEL, highlightthickness=1,
                        highlightbackground=DIVIDER, cursor="hand2")
        body = tk.Frame(card, background=BG_PANEL)
        body.pack(fill="both", expand=True, padx=PAD_M, pady=PAD_M)

        top = tk.Frame(body, background=BG_PANEL)
        top.pack(fill="x")
        tk.Label(top, text=name, background=BG_PANEL, foreground=FG,
                 font=(FONT_UI, FS_TITLE, "bold"),
                 cursor="hand2").pack(side="left")
        tk.Label(top, text="%d 关" % n_stages, background=BG_PANEL,
                 foreground=accent, font=(FONT_NUM, FS_SMALL, "bold"),
                 cursor="hand2").pack(side="right")

        tk.Label(body, text=desc, background=BG_PANEL, foreground=FG_DIM,
                 font=(FONT_UI, FS_MICRO), justify="left", anchor="w",
                 wraplength=280, cursor="hand2").pack(
                     fill="x", pady=(3, 0))
        tk.Label(body, text="%d 组  →" % n_groups, background=BG_PANEL,
                 foreground=accent, font=(FONT_UI, FS_MICRO),
                 anchor="w", cursor="hand2").pack(fill="x", pady=(PAD_XS, 0))

        def enter(_e=None):
            card.config(highlightbackground=accent, highlightthickness=2)

        def leave(_e=None):
            card.config(highlightbackground=DIVIDER, highlightthickness=1)

        def click(_e=None):
            self.open_category(key)

        for w in [card, body, top] + list(body.winfo_children()) + \
                 list(top.winfo_children()):
            w.bind("<Button-1>", click)
            w.bind("<Enter>", enter)
            w.bind("<Leave>", leave)
        harmonize(card, BG_PANEL)
        return card

    def show_cat_menu(self) -> None:
        """显示分类主菜单。"""
        self.detail_frame.pack_forget()
        self.cat_menu.pack(fill="both", expand=True)

    def show_detail(self) -> None:
        """显示关卡详情（地图 + 时间轴）。"""
        self.cat_menu.pack_forget()
        self.detail_frame.pack(fill="both", expand=True)

    def open_category(self, key: str) -> None:
        """从分类主菜单进入该分类的关卡列表。"""
        name = dict(CATEGORY_ORDER).get(key, key)
        self.var_cat.set(name)
        self._on_cat()
        self.show_detail()
        if self.var_group.get():
            self._on_group()
        self.app.status.set("%s — 选择章节/活动与关卡后点「加载地图」" % name)

    def back_to_menu(self) -> None:
        """从关卡详情返回分类主菜单。"""
        self.show_cat_menu()

    # ------------------------------------------------------------ 关卡详情

    def _build_detail(self, master) -> None:
        self.detail_frame = tk.Frame(master, background=BG)
        self._build_detail_inner(self.detail_frame)

    def _build_detail_inner(self, root) -> None:
        # ---- 关卡选择：分类 -> 分组 -> 关卡
        ctl = tk.Frame(root, background=BG)
        ctl.pack(fill="x", padx=PAD_M, pady=(PAD_S, PAD_S))
        box = tk.Frame(ctl, background=BG_PANEL, highlightthickness=1,
                       highlightbackground=DIVIDER)
        box.pack(fill="x")
        top = tk.Frame(box, background=BG_PANEL)
        top.pack(fill="x", padx=PAD_S, pady=PAD_S)

        btn_back = ttk.Button(top, text="← 分类", style="Ghost.TButton",
                              command=self.back_to_menu)
        btn_back.pack(side="left", padx=(0, PAD_S))

        def lbl(t):
            return tk.Label(top, text=t, background=BG_PANEL, foreground=FG_DIM,
                            font=(FONT_UI, FS_BODY))

        lbl("分类").pack(side="left", padx=(PAD_XS, 3))
        self.var_cat = tk.StringVar()
        self.cmb_cat = ComboBox(top, textvariable=self.var_cat, width=10,
                                state="readonly",
                                values=[n for _k, n in CATEGORY_ORDER])
        self.cmb_cat.pack(side="left", padx=(0, PAD_S))
        self.cmb_cat.bind("<<ComboboxSelected>>", lambda e: self._on_cat())

        lbl("章节/活动").pack(side="left", padx=(0, 3))
        self.var_group = tk.StringVar()
        self.cmb_group = ComboBox(top, textvariable=self.var_group, width=22,
                                  state="readonly", values=[])
        self.cmb_group.pack(side="left", padx=(0, PAD_S))
        self.cmb_group.bind("<<ComboboxSelected>>", lambda e: self._on_group())

        # ---- 第三层：肉鸽节点类型（作战 / 紧急作战 / 险路恶敌 …）
        # 只在集成战略下出现，其他分类没有这一层，所以默认 pack_forget。
        self.lbl_node = lbl("节点")
        self.var_node = tk.StringVar()
        self.cmb_node = ComboBox(top, textvariable=self.var_node, width=12,
                                 state="readonly", values=[])
        self.cmb_node.bind("<<ComboboxSelected>>", lambda e: self._on_node())

        lbl("关卡").pack(side="left", padx=(0, 3))
        self.var_level = tk.StringVar()
        self.cmb_level = ComboBox(top, textvariable=self.var_level, width=22,
                                  state="readonly", values=[])
        self.cmb_level.pack(side="left", padx=(0, PAD_S))
        self.cmb_level.bind("<<ComboboxSelected>>", lambda e: self.load_selected())

        # 文字搜索：图多了以后，只靠分类/主题/节点三层下拉还是难定位。
        # 这里按关卡显示名、关卡 id、主题名模糊匹配，实时收窄第四层下拉。
        lbl("搜索").pack(side="left", padx=(PAD_S, 3))
        self.var_search = tk.StringVar()
        ent_search = tk.Entry(top, textvariable=self.var_search, width=14,
                              background=BG_INPUT, foreground=FG,
                              insertbackground=FG, relief="flat",
                              font=(FONT_UI, FS_BODY),
                              highlightthickness=1, highlightbackground=BORDER,
                              highlightcolor=ACCENT)
        ent_search.pack(side="left", ipady=3, padx=(0, PAD_S))
        ent_search.bind("<KeyRelease>", lambda e: self._on_search())
        self.lbl_search = tk.Label(top, text="", background=BG_PANEL,
                                   foreground=ACCENT, font=(FONT_UI, FS_SMALL))
        self.lbl_search.pack(side="left", padx=(0, PAD_S))

        self.btn_load = ttk.Button(top, text="加载地图", style="Accent.TButton",
                                   command=self.load_selected)
        self.btn_load.pack(side="left", padx=(0, PAD_S))

        # 有磨难（FOUR_STAR）变体的地图，放一个「磨难」快捷按钮，
        # 一键把关卡下拉切到对应磨难版并加载（磨难地形/出怪与普通版一致）。
        self.btn_adversity = ttk.Button(
            top, text="磨难 ›", style="Ghost.TButton",
            command=self._jump_to_adversity)
        self.btn_adversity.pack(side="left", padx=(0, PAD_S))
        self.btn_adversity.pack_forget()

        # ---- 第二行：参数与图层
        row2 = tk.Frame(box, background=BG_PANEL)
        row2.pack(fill="x", padx=PAD_S, pady=(0, PAD_S))

        lbl2 = lambda t: tk.Label(row2, text=t, background=BG_PANEL,
                                  foreground=FG_DIM, font=(FONT_UI, FS_BODY))
        lbl2("移速").pack(side="left", padx=(PAD_XS, 3))
        self.var_speed = tk.StringVar(value="1.0")
        ent = tk.Entry(row2, textvariable=self.var_speed, width=5,
                       background=BG_INPUT, foreground=FG, insertbackground=FG,
                       relief="flat", font=(FONT_NUM, FS_NUM + 1),
                       highlightthickness=1, highlightbackground=BORDER,
                       highlightcolor=ACCENT)
        ent.pack(side="left", ipady=3)
        ent.bind("<KeyRelease>", lambda ev: self.recompute())

        tk.Frame(row2, background=DIVIDER, width=1).pack(
            side="left", fill="y", padx=PAD_S, pady=1)

        def chk(text, var, cmd):
            c = tk.Checkbutton(row2, text=text, variable=var,
                               background=BG_PANEL, foreground=FG,
                               selectcolor=BG_INPUT,
                               activebackground=BG_PANEL,
                               activeforeground=ACCENT,
                               font=(FONT_UI, FS_BODY), bd=0,
                               highlightthickness=0, command=cmd)
            c.pack(side="left", padx=(0, PAD_M))
            return c

        self.var_diag = tk.BooleanVar(value=True)
        chk("允许斜向", self.var_diag, self.recompute)
        self.var_ground = tk.BooleanVar(value=True)
        chk("地面层", self.var_ground, self._on_layer)
        self.var_fly = tk.BooleanVar(value=False)
        chk("飞行层", self.var_fly, self._on_layer)
        self.var_cost = tk.BooleanVar(value=False)
        chk("显示代价", self.var_cost, self._on_layer)
        self.var_time = tk.BooleanVar(value=True)
        chk("显示时间轴", self.var_time, self._on_timeline_toggle)

        # ---- 第三行：视图（翻转 / 放大）
        # 用户反馈「很多地图正反方向和游戏内不一致」——Unity 里摄像机
        # 的朝向跟数据坐标的行序不一定一致，所以不硬编码一个方向，而是
        # 给用户一个一键翻转。放大用于小地图（自律/高难关卡格子很小）。
        row3 = tk.Frame(box, background=BG_PANEL)
        row3.pack(fill="x", padx=PAD_S, pady=(0, PAD_S))

        lbl3 = lambda t: tk.Label(row3, text=t, background=BG_PANEL,
                                  foreground=FG_DIM, font=(FONT_UI, FS_BODY))
        lbl3("翻转").pack(side="left", padx=(PAD_XS, 3))
        self.var_flip_v = tk.BooleanVar(value=False)
        self.var_flip_h = tk.BooleanVar(value=False)

        def chk3(text, var, cmd):
            c = tk.Checkbutton(row3, text=text, variable=var,
                               background=BG_PANEL, foreground=FG,
                               selectcolor=BG_INPUT,
                               activebackground=BG_PANEL,
                               activeforeground=ACCENT,
                               font=(FONT_UI, FS_BODY), bd=0,
                               highlightthickness=0, command=cmd)
            c.pack(side="left", padx=(0, PAD_M))
            return c

        chk3("上下", self.var_flip_v, self._on_flip)
        chk3("左右", self.var_flip_h, self._on_flip)

        tk.Frame(row3, background=DIVIDER, width=1).pack(
            side="left", fill="y", padx=PAD_S, pady=1)

        lbl3("放大").pack(side="left", padx=(0, 3))
        self._zoom = 1.0
        self.lbl_zoom = tk.Label(row3, text="1.0×", background=BG_PANEL,
                                 foreground=FG, width=5,
                                 font=(FONT_NUM, FS_BODY), anchor="w")
        for txt, ratio in (("−", -1), ("+", +1)):
            b = tk.Button(row3, text=txt, width=2, bd=0, relief="flat",
                          background=BG_INPUT, foreground=FG,
                          activebackground=ACCENT, activeforeground="#10131a",
                          font=(FONT_UI, FS_BODY, "bold"), cursor="hand2",
                          command=(lambda r=ratio: self._zoom_step(r)))
            b.pack(side="left", padx=(0, 2))
        self.lbl_zoom.pack(side="left", padx=(PAD_XS, PAD_S))
        btn_rv = tk.Button(row3, text="重置视图", bd=0, relief="flat",
                           background=BG_INPUT, foreground=FG,
                           activebackground=ACCENT, activeforeground="#10131a",
                           font=(FONT_UI, FS_BODY), cursor="hand2", padx=PAD_S,
                           command=self._reset_view)
        btn_rv.pack(side="left")

        tk.Frame(row3, background=DIVIDER, width=1).pack(
            side="left", fill="y", padx=PAD_S, pady=1)

        # 机关图层：传送门 / 火山 / 留声机……默认打开。
        # 不知道传送门在哪，就看不出路线为什么突然跳到地图另一头。
        self.var_mech = tk.BooleanVar(value=True)
        chk3("地图机关", self.var_mech, self._on_layer)
        self.lbl_mech = tk.Label(row3, text="", background=BG_PANEL,
                                 foreground=FG_DIM, font=(FONT_UI, FS_MICRO),
                                 anchor="w")
        self.lbl_mech.pack(side="left", padx=(0, PAD_S))

        # ---- 主体：左侧地图 + 右侧信息
        body = tk.Frame(root, background=BG)
        body.pack(fill="both", expand=True, padx=PAD_M, pady=(0, PAD_M))

        left = tk.Frame(body, background=BG)
        left.pack(side="left", fill="both", expand=True)

        self.canvas = MapCanvas(left)
        self.canvas.pack(fill="both", expand=True)
        self.canvas.on_cell_click = self._on_cell_click
        self.canvas.on_hover = self._on_hover
        self.canvas.on_enemy_click = self._on_enemy_click
        self.canvas.on_spawn_click = self._on_spawn_click

        # ---- 时间轴（地图下方）
        self.tl_frame = tk.Frame(left, background=BG)
        self.tl_frame.pack(fill="x", pady=(PAD_S, 0))
        tl_head = tk.Frame(self.tl_frame, background=BG)
        tl_head.pack(fill="x")
        tk.Label(tl_head, text="出怪时间轴", background=BG, foreground=FG,
                 font=(FONT_UI, FS_BODY, "bold")).pack(side="left")
        self.lbl_tl = tk.Label(tl_head, text="（点击标记可将游标移到该时刻）",
                               background=BG, foreground=FG_DIM,
                               font=(FONT_UI, FS_MICRO))
        self.lbl_tl.pack(side="left", padx=PAD_S)

        self.timeline_canvas = TimelineCanvas(self.tl_frame, height=118)
        self.timeline_canvas.pack(fill="x", pady=(3, 0))
        self.timeline_canvas.on_seek = self._on_timeline_seek

        # ---- 播放控制条（开始/暂停/倍速/进度）
        self.playback = PlaybackBar(
            self.tl_frame, on_time=self._on_playback_time)
        self.playback.pack(fill="x", pady=(PAD_XS, 0))

        # ---- 右侧信息栏
        side = tk.Frame(body, background=BG, width=352)
        side.pack(side="left", fill="y", padx=(PAD_S, 0))
        side.pack_propagate(False)

        def make_text(sec, height):
            t = tk.Text(sec.body, height=height, background=BG_SUNKEN,
                        foreground="#b8c4d4", relief="flat",
                        font=(FONT_NUM, FS_SMALL + 1), wrap="word",
                        highlightthickness=0, padx=PAD_S, pady=PAD_S,
                        spacing1=1, spacing3=2, bd=0)
            t.pack(fill="x")
            t.configure(state="disabled")
            return t

        # 信息区：两列并排，省出纵向空间给下面两张表
        info_row = tk.Frame(side, background=BG)
        info_row.pack(fill="x", pady=(0, PAD_S))
        info_row.columnconfigure(0, weight=3, uniform="ir")
        info_row.columnconfigure(1, weight=2, uniform="ir")

        sec_info = SectionFrame(info_row, "地图信息")
        sec_info.grid(row=0, column=0, sticky="nsew", padx=(0, PAD_S))
        self.info = make_text(sec_info, 7)

        sec_tile = SectionFrame(info_row, "选中地块")
        sec_tile.grid(row=0, column=1, sticky="nsew")
        self.tile_info = make_text(sec_tile, 7)

        # ---- 出怪内容：按怪物图标铺网格，点图标弹图鉴。
        # 以前这里是「路线 / 敌人」两张表，路线序号与敌人统计对玩家没什么用，
        # 换成带图标的出怪清单，一眼能看出这关出哪些怪。
        sec_tables = SectionFrame(side, "本关出怪")
        sec_tables.pack(fill="both", expand=True, pady=PAD_S)
        # 清空按钮放在标题栏右侧：用户明确要求「在本关出怪的右侧增加
        # 一个按钮清空图上路径图保持整洁」。路线现在默认不画，一旦点过
        # 某一行就会留一条线，需要有个显眼的地方一键撤掉。
        self.btn_clear_paths = tk.Button(
            sec_tables.head_right, text="清空路径", relief="flat",
            background=BG_DEEP, foreground=FG_DIM,
            activebackground=BG_PANEL, activeforeground=ACCENT,
            font=(FONT_UI, FS_MICRO), highlightthickness=1,
            highlightbackground=BORDER, cursor="hand2",
            padx=8, pady=0, command=self._clear_paths)
        self.btn_clear_paths.pack(side="right")

        # 无害单位过滤：isUnharmfulAndAlwaysCountAsKilled 的怪（平民、演出
        # 单位、无限刷新的分身）在解包数据里确实有出场记录，但实机里既不
        # 打人也不挡路、还不计入「剩余敌人总数」。默认**显示**（它们在图
        # 上是真的会出现的），但给一个开关撇掉，方便对照实机观感。
        spawn_bar = tk.Frame(sec_tables.body, background=BG_PANEL)
        spawn_bar.pack(fill="x")
        # 「只列实机真会出的怪」：折叠 hiddenGroup 互斥组（普通/突袭写在同一份
        # waves 里，实机一局只出其中一组）+ 剔除 isValid=False 的废案。
        # act1multi_06 因此从 955 只降到 547 只，act36side_ex03 从 273 只降到 0。
        self.var_effective_only = tk.BooleanVar(value=True)
        self.chk_effective = tk.Checkbutton(
            spawn_bar, text="按实机编队", variable=self.var_effective_only,
            background=BG_PANEL, foreground=FG_DIM,
            activebackground=BG_PANEL, activeforeground=ACCENT,
            selectcolor=BG_DEEP, font=(FONT_UI, FS_MICRO),
            highlightthickness=0, bd=0, cursor="hand2",
            command=self._toggle_harmless)
        self.chk_effective.pack(side="right", padx=(0, PAD_XS))
        self.var_hide_harmless = tk.BooleanVar(value=False)
        self.chk_harmless = tk.Checkbutton(
            spawn_bar, text="撇除无害单位", variable=self.var_hide_harmless,
            background=BG_PANEL, foreground=FG_DIM,
            activebackground=BG_PANEL, activeforeground=ACCENT,
            selectcolor=BG_DEEP, font=(FONT_UI, FS_MICRO),
            highlightthickness=0, bd=0, cursor="hand2",
            command=self._toggle_harmless)
        self.chk_harmless.pack(side="right", padx=(0, PAD_XS))
        self.lbl_spawn_hint = tk.Label(
            spawn_bar, text="载入关卡后显示", background=BG_PANEL,
            foreground=FG_DIM, font=(FONT_UI, FS_MICRO), anchor="w")
        self.lbl_spawn_hint.pack(side="left", fill="x", expand=True)

        # 滚动区：怪物多的时候能滚
        wrapc = tk.Frame(sec_tables.body, background=BG_PANEL)
        wrapc.pack(fill="both", expand=True)
        self.spawn_canvas = tk.Canvas(wrapc, background=BG_PANEL,
                                      highlightthickness=0, bd=0)
        self.spawn_scroll = ttk.Scrollbar(wrapc, orient="vertical",
                                          command=self.spawn_canvas.yview)
        self.spawn_canvas.configure(yscrollcommand=self.spawn_scroll.set)
        self.spawn_scroll.pack(side="right", fill="y")
        self.spawn_canvas.pack(side="left", fill="both", expand=True)
        self.spawn_host = tk.Frame(self.spawn_canvas, background=BG_PANEL)
        self._spawn_win = self.spawn_canvas.create_window(
            (0, 0), window=self.spawn_host, anchor="nw")
        self.spawn_host.bind(
            "<Configure>",
            lambda e: self.spawn_canvas.configure(
                scrollregion=self.spawn_canvas.bbox("all")))
        self.spawn_canvas.bind(
            "<Configure>",
            lambda e: self.spawn_canvas.itemconfigure(self._spawn_win,
                                                      width=e.width))
        self.spawn_canvas.bind("<MouseWheel>", self._on_spawn_wheel)

        #: 出怪条目 widget（用于重建）
        self._spawn_tiles = []
        # 敌人 / 出怪点详情：常驻在右栏底部，点地图上的圆点或出怪口就填这里
        sec_detail = SectionFrame(side, "敌人详情")
        sec_detail.pack(fill="both", expand=True, pady=(0, PAD_S))
        self.lbl_detail_title = tk.Label(
            sec_detail.body, text="点地图上的敌人圆点或出怪口",
            background=BG_PANEL, foreground=FG_DIM,
            font=(FONT_UI, FS_MICRO), anchor="w")
        self.lbl_detail_title.pack(fill="x")
        self.detail_text = tk.Text(
            sec_detail.body, height=9, background=BG_SUNKEN,
            foreground="#b8c4d4", relief="flat",
            font=(FONT_NUM, FS_SMALL), wrap="word",
            highlightthickness=0, padx=PAD_S, pady=PAD_S,
            spacing1=1, spacing3=2, bd=0)
        self.detail_text.pack(fill="both", expand=True, pady=(2, 0))
        self.detail_text.configure(state="disabled")

        for sec in (sec_info, sec_tile, sec_tables, sec_detail):
            sec.harmonize()

        self._load_catalog()

    # ------------------------------------------------------------ 目录

    def _load_catalog(self) -> None:
        """从 App 取关卡目录，填分类下拉并刷新分类主菜单。"""
        self.catalog = getattr(self.app, "stage_catalog", None)
        if not self.catalog:
            self.cmb_cat.config(values=["（目录未就绪）"])
            self._fill_cat_cards()
            return
        self._mark_cached()
        names = [self.catalog.category_label(k) for k in self.catalog.categories()]
        self.cmb_cat.config(values=names)
        self._fill_cat_cards()

    def _mark_cached(self) -> None:
        """把本地已有地图文件的关卡标上 cached（下拉里显示 ● 而不是 ○）。

        磨难/突袭变体的 stage_id 带 ``#f#`` 后缀，缓存文件可能落在
        普通版 id 下（见 ``maps.get_level`` 的 fallback 逻辑），所以两
        种 id 都要查。

        肉鸽关卡要额外按 **rel_path** 查：1033 个 stage_id 只对应 638 张
        地图（换皮图共用），而缓存是按路径存的。只比 stage_id 的话，
        下好的图会全部显示 ○，用户以为没有缓存、每次重下。
        """
        if not self.catalog:
            return
        try:
            cached = set(self.app.level_cache.list_cached())
        except Exception:
            cached = set()

        def _rel_key(rel: str) -> str:
            safe = (rel or "").replace("/", "_").replace("\\", "_")
            return safe[:-5] if safe.endswith(".json") else safe

        for st in self.catalog.stages.values():
            if st.cached:
                continue
            base = st.stage_id.split("#", 1)[0]
            hit = st.stage_id in cached or base in cached
            if not hit:
                rel = getattr(st, "path", "") or ""
                if rel and _rel_key(rel) in cached:
                    hit = True
            st.cached = hit

    def _cat_key(self) -> str:
        name = self.var_cat.get()
        for k, label in CATEGORY_ORDER:
            if label == name:
                return k
        return ""

    def _on_cat(self) -> None:
        if not self.catalog:
            return
        key = self._cat_key()
        self._groups = self.catalog.category_groups(key)
        values = ["%s" % g.label for g in self._groups]
        self.cmb_group.config(values=values)
        if values:
            self.var_group.set(values[0])
            self._on_group()
        else:
            self.cmb_group.config(values=[])
            self.cmb_level.config(values=[])
            self.var_group.set("")
            self.var_level.set("")
            self._hide_node_layer()

    # ---------------------------------------------------------- 第三层：节点

    def _hide_node_layer(self) -> None:
        """收起「节点」这一层（非集成战略分类没有节点类型）。"""
        self._node_types = []
        try:
            self.cmb_node.config(values=[])
            self.var_node.set("")
            self.cmb_node.pack_forget()
            self.lbl_node.pack_forget()
        except Exception:
            pass

    def _show_node_layer(self, group) -> None:
        """按当前主题里实际存在的节点类型，铺开第三层下拉。

        只列真有的类型，并带上数量，方便一眼看出这个主题里有多少
        「紧急作战」「险路恶敌」。选「全部节点」等于不加这一层筛选。
        """
        try:
            types = self.catalog.node_types_in(group.group_id)
        except Exception:
            types = []
        if not types:
            self._hide_node_layer()
            return
        self._node_types = types
        values = ["全部节点（%d）" % sum(n for _k, _l, n in types)]
        values += ["%s（%d）" % (label, n) for _k, label, n in types]
        self.lbl_node.pack(side="left", padx=(0, 3), before=self.cmb_level)
        self.cmb_node.config(values=values)
        self.cmb_node.pack(side="left", padx=(0, PAD_S), before=self.cmb_level)
        self.var_node.set(values[0])

    def _node_key(self) -> str:
        """第三层当前选中的节点类型 key；「全部节点」返回空串。"""
        text = self.var_node.get()
        if not text or text.startswith("全部节点"):
            return ""
        for key, label, _n in getattr(self, "_node_types", []):
            if text.startswith(label):
                return key
        return ""

    def _on_node(self) -> None:
        g = self._current_group()
        if g is None:
            return
        self._fill_levels(g)

    def _on_group(self) -> None:
        g = self._current_group()
        if g is None:
            return
        if (g.group_id or "").startswith("rogue"):
            self._show_node_layer(g)
        else:
            self._hide_node_layer()
        self._fill_levels(g)

    def _current_group(self):
        text = self.var_group.get()
        for cand in self._groups:
            if cand.label == text:
                return cand
        return None

    def _on_search(self) -> None:
        """搜索词变化时重新收窄关卡下拉（分类/主题/节点层不动）。

        只在当前主题里过滤，不做跨主题的全局搜索——用户已经先选好
        主题再搜名字，比「一搜跳来跳去」更可预期。搜索词清空后恢复
        当前主题的完整关卡列表。
        """
        g = self._current_group()
        if g is None:
            return
        self._fill_levels(g)

    def _fill_levels(self, g) -> None:
        """按「小组 [+ 节点类型] [+ 搜索词]」把关卡填进第四层下拉。"""
        node = self._node_key()
        if node:
            try:
                pool = list(self.catalog.stages_in(g.group_id, node))
            except Exception:
                pool = [st for st in g.stages if st.node_type == node]
        else:
            pool = list(g.stages)
        # 文字搜索：命中关卡显示名 / 关卡 id / 主题名，不区分大小写。
        # 匹配用「拼出来的显示串」，这样用户敲 ISW-DF、ro1_b 这类 id
        # 或「开门请当心」这种关卡名都能命中。
        q = (getattr(self, "var_search", None) or tk.StringVar()).get()
        q = q.strip().lower()
        if q:
            def _blob(st):
                return " ".join((
                    st.label, st.stage_id, st.code, st.name,
                    getattr(st, "sub_name", "") or "",
                    g.name or "",
                )).lower()
            pool = [st for st in pool if q in _blob(st)]
        # 同一关会同时存在普通版与磨难/突袭版（stage_id 带 #f# 后缀），
        # 显示名相同但难度不同。下拉里两个都保留、加后缀区分，
        # 普通版排在前面（默认选中普通版）。
        pool.sort(key=lambda st: (st.difficulty_label != "", st.stage_id))
        self._stages = pool
        values = []
        for st in pool:
            d = st.difficulty_label
            # 已在本地缓存的地图直接标 ●，没缓存的标 ○ 提示需要联网
            mark = "●" if getattr(st, "cached", False) else "○"
            tag = "  [%s]" % d if d else ""
            values.append("%s%s %s" % (mark, tag, st.label))
        self.cmb_level.config(values=values)
        self.var_level.set(values[0] if values else "")
        # 搜索词生效时给个小结；没搜到时明确提示，别让用户以为下拉坏了。
        if hasattr(self, "lbl_search"):
            if q:
                self.lbl_search.config(
                    text=("%d 项" % len(pool)) if pool else "无匹配")
            else:
                self.lbl_search.config(text="")
        # 只有当前组里存在「磨难」变体时才显示一键跳转按钮。
        self._adversity_map = {
            st.stage_id.split("#", 1)[0]: st
            for st in pool
            if st.difficulty_label == "磨难"
        }
        if self._adversity_map:
            self.btn_adversity.pack(side="left", padx=(0, PAD_S))
        else:
            self.btn_adversity.pack_forget()

    def _jump_to_adversity(self) -> None:
        """一键跳转到当前关卡（或组内首个磨难关卡）的磨难版并加载。"""
        cur = self._current_stage()
        target = None
        if cur:
            target = self._adversity_map.get(cur.stage_id.split("#", 1)[0])
        if not target and self._adversity_map:
            # 当前选的是普通版但没对应的磨难，则按显示顺序取第一个磨难关
            target = next(iter(self._adversity_map.values()))
        if not target:
            return
        # 把下拉切到该磨难项
        for i, st in enumerate(self._stages):
            if st.stage_id == target.stage_id:
                self.var_level.set(self.cmb_level["values"][i])
                break
        self.load_selected()

    def _current_stage(self) -> Optional[Stage]:
        text = self.var_level.get()
        for st in self._stages:
            d = st.difficulty_label
            mark = "●" if getattr(st, "cached", False) else "○"
            tag = "  [%s]" % d if d else ""
            shown = "%s%s %s" % (mark, tag, st.label)
            if shown == text or st.label == text:
                return st
        return None

    # ------------------------------------------------------------ 加载

    def load_selected(self) -> None:
        st = self._current_stage()
        if not st:
            return
        self.app.status.set("正在加载 %s …" % st.stage_id)
        # 教学关（tr_*）等少数关卡在游戏数据仓库里没有独立地图文件，
        # 直接把原因说清楚，比只写「加载失败」有用。
        self.app.update_idletasks()
        try:
            gm = get_level(st.stage_id, st.category, self.app.level_cache,
                           rel_path=st.path)
        except Exception as e:
            self.app.status.set("加载失败：%s" % e)
            return
        if not gm:
            tip = ("该关卡官方数据中没有独立地图文件（教学关等）"
                   if st.stage_id.startswith("tr_")
                   else "检查网络后重试，或已缓存的关卡不受影响")
            self.app.status.set("加载失败：%s — %s" % (st.label, tip))
            return
        self.game_map = gm
        self.canvas.highlight_route = None
        # 换图必须退掉上一条图的隔离，否则新图会莫名其妙只显示一条线
        self.canvas.isolate_route = None
        # 高亮同理：上一条图的敌人 id 在新图上可能撞名
        self.canvas.highlight_enemy = None
        self._clear_trail()      # 换图丢弃上一条路线的拖尾残留
        # 记下当前关卡 id / 相对路径，_load_enemies 与空出怪原因都要用。
        # 以前只在 _load_enemies 之后才写 _cur_rel_path，而 _load_timeline
        # 和 _load_enemies 都已经在读它——顺序反了，首帧永远拿到上一张图的
        # 路径（换图后出怪数报 -1 的根因之一）。
        self._cur_level_id = st.stage_id
        self._cur_rel_path = getattr(st, "path", "") or ""
        # 先取时间轴，recompute 里的路线表要按它统计出怪数
        self._load_timeline(st.stage_id, gm, rel_path=self._cur_rel_path)
        self._auto_harmless_default()
        self.recompute()
        self._load_enemies(st.stage_id, self._cur_rel_path)
        self.app.status.set(
            "%s　%s×%s　路线 %d 条　出怪 %d 只　时长 %.0fs"
            % (st.label, gm.width, gm.height, len(gm.routes),
               self.timeline.total_spawns if self.timeline else 0,
               self.timeline.duration if self.timeline else 0))

    def _enemy_name_lookup(self):
        """enemy_id -> 中文名，先查手册再查敌人库。"""
        lib = self.app.enemy_lib
        manual = getattr(self.app, "enemy_names", None) or {}

        def lookup(eid: str) -> Optional[str]:
            nm = manual.get(eid)
            if nm:
                return nm
            try:
                st = lib.stats(eid)
                if st and st.name and st.name != eid:
                    return st.name
            except Exception:
                pass
            return None

        return lookup

    def _load_timeline(self, level_id: str, gm: GameMap,
                       rel_path: str = "") -> None:
        """读出怪时间轴。

        缓存键优先用**地图相对路径**：肉鸽里「紧急作战」和「普通作战」
        是同一张地图文件（levelId 完全相同，只有 difficulty 不同），
        按 stage_id 存会各存一份；而地图文件本身是按 rel_path 缓存的，
        只查 stage_id 就永远是空的——表现出来是出怪数为 -1。
        """
        raw = self._raw_for(level_id, rel_path)
        if not raw:
            self.timeline = None
            self.timeline_canvas.set_timeline(None)
            return
        tl = parse_timeline(raw)
        tl = fill_names(tl, self._enemy_name_lookup())
        self.timeline = tl
        self.timeline_canvas.set_timeline(tl, gm.height, gm.routes)
        # 播放时长要覆盖「出场 + 走完全程（含罚站）」，而它依赖
        # self.analyses——本函数在 recompute() **之前** 调用，
        # 此刻 analyses 还是上一张图的，所以时长放到 recompute 里设。
        if hasattr(self, "tl_frame"):
            self.lbl_tl.config(text="（共 %d 只）" % tl.total_spawns)
        self._build_spawn_points(tl, gm)

    def _build_spawn_points(self, tl, gm) -> None:
        """按「出怪格」汇总本关的出怪情况，供地图徽标与悬停提示。"""
        if not tl or not gm:
            if getattr(self, "canvas", None):
                self.canvas.set_spawn_points({})
            return
        routes = {r.index: r for r in gm.routes}
        pts = {}
        for e in tl.events:
            r = routes.get(e.route_index)
            if not r:
                continue
            key = (r.start[0], r.start[1])
            bucket = pts.setdefault(key, {})
            nm = e.enemy_name or e.enemy_id
            rec = bucket.get(nm)
            if rec is None:
                bucket[nm] = [1, e.time]
            else:
                rec[0] += 1
                rec[1] = min(rec[1], e.time)
        # 转成 [(name, count, first_time)]，按首次时间排序
        out = {}
        for key, bucket in pts.items():
            items = [(nm, n, t) for nm, (n, t) in bucket.items()]
            items.sort(key=lambda x: (x[2], -x[1]))
            out[key] = items
        self.canvas.set_spawn_points(out)

    def _on_spawn_wheel(self, ev) -> None:
        try:
            self.spawn_canvas.yview_scroll(int(-ev.delta / 120), "units")
        except Exception:
            pass

    def _spawn_hint_text(self) -> str:
        """出怪列表上方的说明，带上当前筛选状态。"""
        base = "点任意一行只看这条路线（再点退出）"
        tl = self.timeline
        if not tl:
            return base
        bits = []
        if self.var_effective_only.get():
            n_dis = tl.disabled_count
            if n_dis:
                bits.append("已剔 %d 条未启用" % n_dis)
            gs = tl.hidden_groups()
            if gs:
                bits.append("编队择一（%s）" % "/".join(gs))
            # 随机候选包（randomSpawnGroupKey）：同组按 weight 抽一条，
            # 全列会把「N 选 1」显示成 N 只，正是用户报的「多出敌人」。
            packs = tl.random_pack_summary()
            if packs:
                n_cut = sum(int(p["total"] - round(p["expect"])) for p in packs)
                bits.append("随机包择一（%d 包，少算 %d 只）"
                            % (len(packs), max(0, n_cut)))
        n_harm = getattr(tl, "harmless_count", 0)
        if n_harm:
            if self.var_hide_harmless.get():
                bits.append("已撇除 %d 个无害单位" % n_harm)
            else:
                bits.append("含 %d 个无害单位" % n_harm)
        if not bits:
            return base
        return base + "　·　" + "　·　".join(bits)

    def _auto_harmless_default(self) -> None:
        """按关卡自动决定「撇除无害单位」的默认勾选。

        用户报「H8-4 多出平民」——那 3 只其实是 `enemy_3001_upeopl`
        （乌萨斯平民），带 `isUnharmfulAndAlwaysCountAsKilled`，实机里确实
        会出场、能被打，只是不计数。它们躺在出怪表里，看起来就像凭空多出来
        的敌人，所以默认该藏。

        但不能一刀切成默认隐藏：全库有 38 个关卡**全部**出怪都是无害单位
        （`act1museum_*` 多索雷斯博物馆系列每关 34~142 条全是），隐藏后这
        些关的出怪表会直接变空，等于把「多出平民」换成「什么都没有」。
        所以按关卡自适应——只在这关还有货真价实的敌人时，才把无害的折叠掉。
        用户手动勾过就尊重用户的选择，不再自动改。
        """
        tl = self.timeline
        if tl is None or getattr(self, "_harmless_touched", False):
            return
        evs = tl.effective_events()
        if not evs:
            return
        n_harm = sum(1 for e in evs if e.harmless)
        # 全是有害才算「这关有真敌人」；全是无害就保持显示，否则表格会空
        self.var_hide_harmless.set(0 < n_harm < len(evs))

    def _toggle_harmless(self) -> None:
        """勾选「撇除无害单位」后重建出怪列表。

        只重建列表，不重新下载/解析地图——先把说明文字刷新了，即使还没
        选关卡也能立刻看到勾选框的反馈。

        置 `_harmless_touched`：用户一旦自己动过这个勾，换关时就不再按
        新关卡的数据自动改默认值，免得把人手选的偏好悄悄顶掉。
        """
        self._harmless_touched = True
        self.lbl_spawn_hint.config(text=self._spawn_hint_text())
        if self.game_map:
            self._load_enemies(self.game_map.level_id or "",
                               getattr(self, "_cur_rel_path", ""))

    def _raw_for(self, level_id: str, rel_path: str = "") -> Optional[dict]:
        """按与 ``get_level`` / ``_load_timeline`` 一致的候选链取关卡原始 JSON。

        缓存是**按地图相对路径**落盘的（肉鸽等场景里两个 stage 共用同一份
        地图文件），而 ``stage_id`` 常常带 ``#f#`` 之类的后缀、或干脆与
        文件名不同。只用 ``stage_id`` 当键会命中不到 —— 表现就是「左侧地图
        显示正常、右侧本关出怪空白」。全库 4521 关里有 1716 关是这个原因
        （984 关需要 rel_path、721 关需要去 ``#`` 后缀）。
        """
        cache = self.app.level_cache
        cands = []
        if rel_path:
            key = rel_path[:-5] if rel_path.endswith(".json") else rel_path
            cands.append(key)
        cands.append(level_id)
        if "#" in level_id:
            cands.append(level_id.split("#", 1)[0])
        for k in cands:
            if not k:
                continue
            raw = cache.load(k)
            if raw:
                return raw
        return None

    def _load_enemies(self, level_id: str, rel_path: str = "") -> None:
        """填「本关出怪」图标网格。

        每个出怪项显示 PRTS 怪物头像 + 名称 + 数量 / 首现时间，
        点图标弹出怪物图鉴（特性、技能、抗性）。
        """
        raw = self._raw_for(level_id, rel_path)
        self.enemies = []
        self._spawn_rows = []
        self._spawn_wait = {}
        # 清空整块出怪表，不能只销毁 _spawn_tiles 里登记的行。
        # 表头 head 和「本关全部 isValid=false」那种空提示 Label 是直接
        # grid 到 spawn_host 上的、没登记进 _spawn_tiles，只清后者会让它们
        # 越堆越多：同一关连点 5 次子控件数 8→9→10→11→12，来回切 20 次
        # 能叠出 10 份同样的 isValid 文案，糊成一片。
        for w in list(self.spawn_host.winfo_children()):
            try:
                w.destroy()
            except Exception:
                pass
        for w in self._spawn_tiles:
            try:
                w.destroy()
            except Exception:
                pass
        self._spawn_tiles = []
        self._spawn_photos = {}
        if not raw:
            self.lbl_spawn_hint.config(text="载入关卡后显示")
            return

        # 时间轴统计：每只敌人的数量与首次出现
        counts: Dict[str, int] = {}
        first: Dict[str, float] = {}
        if self.timeline:
            for e in self.timeline.events:
                counts[e.enemy_id] = counts.get(e.enemy_id, 0) + 1
                if e.enemy_id not in first or e.time < first[e.enemy_id]:
                    first[e.enemy_id] = e.time

        ids = level_enemy_ids(raw)
        lookup = self._enemy_name_lookup()
        lib = self.app.enemy_lib
        overrides = level_enemy_overrides(raw) or {}
        # 出场罚站（角兽的【休憩】）：这**不在路线里**，路线的 checkpoints
        # 可能是空数组（咩的朋友 33 条路线全是），只看路线会显示 0 秒，
        # 与沙盘对不上。时长在敌人天赋 Revive.unmovable_duration 上。
        self._spawn_wait = {}
        for ref in (raw.get("enemyDbRefs") or []):
            if not isinstance(ref, dict):
                continue
            eid = ref.get("id")
            if not eid:
                continue
            _w = spawn_unmovable_of_ref(ref)
            if _w > 0.01:
                self._spawn_wait[eid] = _w

        rows = []
        for eid in ids:
            st = None
            if lib.loaded:
                try:
                    st = lib.stats(eid, override=overrides.get(eid))
                except Exception:
                    st = None
            nm = (st.name if st and st.name and st.name != eid
                  else (lookup(eid) or eid))
            n = counts.get(eid, 0)
            t0 = first.get(eid)
            rows.append((eid, st, nm, n, t0))
            if st:
                self.enemies.append(st)

        self.lbl_spawn_hint.config(
            text=self._spawn_hint_text())

        # PRTS 风格逐条排列：按出场顺序一行一行往下，而不是按种类汇总。
        # 用户明确要求参考 https://map.ark-nights.com/map/hard_08-04
        # 的「本关出怪」表：序号 | 头像+名称 | 数量 | 间隔 | 时间点 |
        # 阶段时间点 | 路线。
        groups = (self.timeline.groups(hostile_only=self.var_hide_harmless.get(),
                                       effective=self.var_effective_only.get(),
                                       fold_random=self.var_effective_only.get())
                  if self.timeline else [])

        # 表头
        head = tk.Frame(self.spawn_host, background=BG_PANEL)
        head.grid(row=0, column=0, sticky="ew", pady=(0, 2))
        self.spawn_host.columnconfigure(0, weight=1)
        hcols = (("次序", 6, "center"), ("敌兵", 16, "w"), ("数量", 5, "center"),
                 ("间隔", 6, "center"), ("时间点", 7, "e"),
                 ("阶段", 7, "e"), ("路线", 5, "center"))
        for j, (t, w, anch) in enumerate(hcols):
            tk.Label(head, text=t, width=w, anchor=anch,
                     background=BG_PANEL, foreground=FG_DIM,
                     font=(FONT_UI, FS_MICRO)).grid(row=0, column=j,
                                                    sticky="ew", padx=1)

        if not groups:
            tk.Label(self.spawn_host, text=self._empty_spawn_reason(),
                     background=BG_PANEL, foreground=FG_DIM,
                     font=(FONT_UI, FS_MICRO), anchor="w",
                     justify="left", wraplength=430).grid(
                row=1, column=0, sticky="ew", pady=(2, 0))
            return

        rows = []
        for gi, g in enumerate(groups):
            rows.append(self._make_spawn_row(self.spawn_host, gi, g))
        for gi, row in enumerate(rows):
            row.grid(row=gi + 1, column=0, sticky="ew", padx=0, pady=0)
            self._spawn_tiles.append(row)
        # 记下这些行，_clear_isolation() 要靠它把选中高亮复位。
        # 以前这里只用局部变量 rows，self._spawn_rows 一直是空列表，
        # 于是「清空地图上的路径线」之后出怪表里那一行的边框不会恢复。
        self._spawn_rows = rows

    def _why_no_events(self) -> str:
        """一条 SPAWN 都没有时，说清**为什么**——光说「本就不出怪」会误导。

        零事件有几种完全不同的成因，用户看到的都是同一片空白：

        * 这一关压根没有敌人（剧情/教学关）
        * 有敌人，但走的是 **预置激活**——``ACTIVATE_PREDEFINED`` 把
          ``predefines`` 里预置好的敌人一次性激活。``act1enemyduel_02a``
          的 43 条 action 全是它，``enemyDbRefs`` 里有 36 个敌人，
          说「本就不出怪」是错的，应该说「由预置激活，读不出时间点」。
        * 只有剧情/演出 action（``STORY`` / ``PLAY_OPERA`` / ``PLAY_BGM``）
        * waves 里连 fragment 都没有（``act1enemyduel_01b``）

        这里**只读原始 JSON 做判断**，不碰解析逻辑，也不改 ``Timeline``。
        """
        raw = None
        try:
            raw = self._raw_for(getattr(self, "_cur_level_id", "") or
                                (self.game_map.level_id if self.game_map else ""),
                                getattr(self, "_cur_rel_path", "") or "")
        except Exception:
            raw = None
        if not isinstance(raw, dict):
            return "（这一关的数据里没有出怪记录——纯演出/机制关，本就不出怪）"

        from akcalc.core.timeline import _num_enum

        counts = {}
        n_actions = 0
        for w in (raw.get("waves") or []):
            if not isinstance(w, dict):
                continue
            for fr in (w.get("fragments") or []):
                if not isinstance(fr, dict):
                    continue
                for a in (fr.get("actions") or []):
                    if not isinstance(a, dict):
                        continue
                    n_actions += 1
                    k = _num_enum(a.get("actionType")) or "?"
                    counts[k] = counts.get(k, 0) + 1
        n_refs = len(raw.get("enemyDbRefs") or [])

        # 有 SPAWN 却解析不出事件：这才是真正的解析异常，必须说清
        if counts.get("SPAWN") or counts.get("SPAWN_EXTRA"):
            return ("（本关有 %d 条出怪动作，但都没解析成时间点——"
                    "可能缺少路线或出怪点坐标，属数据异常）"
                    % (counts.get("SPAWN", 0) + counts.get("SPAWN_EXTRA", 0)))

        if counts.get("ACTIVATE_PREDEFINED") or counts.get(
                "ACTIVATE_PREDEFINED_GROUP"):
            n_pre = (counts.get("ACTIVATE_PREDEFINED", 0)
                     + counts.get("ACTIVATE_PREDEFINED_GROUP", 0))
            return ("（本关 %d 条出怪动作全是「预置激活」ACTIVATE_PREDEFINED，"
                    "敌人（%d 个）由关卡预置字段在运行时激活，"
                    "解包数据里没有各自的出场时间点；"
                    "这类多为人机对战/对决关，沙盘不推演其波次）"
                    % (n_pre, n_refs))

        if n_actions == 0:
            return ("（这一关的波次数据里没有任何出怪动作——"
                    "纯演出/机制关，本就不出怪）")

        if n_refs == 0:
            return "（这一关的数据里没有敌人记录——纯演出/剧情关，本就不出怪）"

        kinds = "、".join("%s×%d" % (k, v)
                          for k, v in sorted(counts.items(), key=lambda x: -x[1]))
        return ("（本关 %d 条动作里没有出怪（SPAWN），只有 %s；"
                "敌人（%d 个）不由波次生成，沙盘无波次可推演）"
                % (n_actions, kinds, n_refs))

    def _empty_spawn_reason(self) -> str:
        """出怪列表为空时给出**具体原因**，而不是一句笼统的「没有记录」。

        用户报过「部分关卡右侧没有本关出怪」。空白本身有两种完全不同的成因，
        界面上必须说清是哪一种，否则看起来像解析失败：

        * 数据里压根没有敌人（纯演出/剧情关、部分教学关）
        * 有敌人，但全被 ``isValid=False`` 标成废案；或全被「按实机编队」
          折叠掉了。``act36side_ex03`` 就是 273 条全部 ``isValid=False``。
        """
        tl = self.timeline
        if tl is None:
            return "（这张地图读不到关卡数据，无法解析出怪）"
        if not tl.events:
            return self._why_no_events()
        n_dis = tl.disabled_count
        n_all = len(tl.events)
        if n_dis >= n_all:
            # 全库扫描的实测口径（2570 个关卡、93630 条 spawn action）：
            # isValid 只有两种取值——缺省（正常）与 False（废弃），
            # 没有任何一关出现「部分 False 部分缺省」以外的混合情况会
            # 让「全部 disabled」误判。所以这里可以断言实机不出怪。
            # 这类关卡多是「塔防小游戏」式的迷你活动（FD-1 繁荣滋长、
            # TG-1 双向通风、act36side_ex03）：波次全部 managedByScheduler
            # 由调度器驱动，模板出怪整体标成未启用，实机靠关卡脚本另行下发。
            return ("（本关 %d 条出怪在解包数据里全部标记为未启用 isValid=false，"
                    "属模板波次（多为迷你玩法关），实机由关卡脚本另行下发；"
                    "取消「按实机编队」可把模板原样列出来）" % n_all)
        if self.var_effective_only.get():
            gs = tl.hidden_groups()
            if gs:
                return ("（%d 条出怪全被编队择一折叠掉了，分组：%s；"
                        "取消「按实机编队」可看全量）" % (n_all, "/".join(gs)))
            packs = tl.random_pack_summary()
            if packs:
                return ("（%d 条出怪全被随机候选包择一折叠掉了，共 %d 个包：%s；"
                        "取消「按实机编队」可看全部备选）"
                        % (n_all, len(packs),
                           "/".join(str(p["group"]) for p in packs[:6])))
        if self.var_hide_harmless.get():
            # 必须确认**真的全**是无害单位再说这句话。以前只要勾了
            # 「撇除无害单位」就无条件返回「全是无害单位」——main_08-04
            # 只有 3 个无害、57 条里有 54 条是敌对，一旦因为别的原因
            # 让列表空掉，就会把成因说错。
            n_harm = getattr(tl, "harmless_count", 0)
            if n_harm >= n_all:
                return ("（本关 %d 条出怪全是无害单位，已被「撇除无害单位」"
                        "隐藏；取消勾选即可看到）" % n_all)
            return ("（本关 %d 条出怪里 %d 个是无害单位、剩下的被其他筛选条件"
                    "隐藏了；把「撇除无害单位」「按实机编队」都取消可看全量）"
                    % (n_all, n_harm))
        return "（本关没有可解析的出怪记录）"

    def _pre_wait_of(self, route_index: int, enemy_id: str = "") -> float:
        """这条路线开头的「原地罚站」秒数（没有就返回 0）。

        两个来源**相加**，因为它们各管一段时间：

        1. **路线里**的预罚站：路线第一个检查点是 ``WAIT_FOR_SECONDS``
           时，敌人刷出来之后会先在出生点站着不动，走完这段时间才开始
           沿路线前进。纵怒 ``ro6_c-6`` 的 route 0/1/2 就是 120s，导致
           那 3 只领舞者的实战到达时间（143~151s）比关卡时长（139s）
           还长。
        2. **敌人天赋**里的【休憩】：角兽出厂自带，写在
           ``Revive.unmovable_duration``，**完全不在路线上**。咩的朋友
           ``ro6_c_2`` 的 33 条路线 ``checkpoints`` 全是空数组，只看
           路线就会显示「罚站 0 秒」，而实机是 90 秒。

        ⚠ 只能按 ``RouteAnalysis.route_index`` 字段查，不能写
        ``analyses[route_index]``：``motionMode=E_NUM`` 的剧情占位路线在
        解析时就被丢掉了，列表位置 ≠ 原始下标（全库 1243 关存在错位）。
        按下标取会静默拿到隔壁那条的罚站时长。
        """
        total = 0.0
        if route_index is not None and route_index >= 0:
            for a in (getattr(self, "analyses", None) or []):
                if getattr(a, "route_index", -1) == route_index:
                    total += float(getattr(a, "pre_wait", 0.0) or 0.0)
                    break
        if enemy_id:
            total += float((getattr(self, "_spawn_wait", None) or {})
                           .get(enemy_id, 0.0) or 0.0)
        return total

    def _make_spawn_row(self, master, gi: int, g):
        """本关出怪表的一行（可点击隔离该路线）。"""
        eid = g.enemy_id
        nm = g.enemy_name or eid
        # 交替底色，长时间列表更好跟读
        bg = BG_SUNKEN if gi % 2 else BG_PANEL
        fg_sel = bg

        row = tk.Frame(master, background=bg, cursor="hand2")
        cells = []

        def cell(text, width, anch, color, font=None):
            lb = tk.Label(row, text=text, width=width, anchor=anch,
                          background=fg_sel, foreground=color,
                          font=font or (FONT_NUM, FS_MICRO))
            lb.pack(side="left", padx=1)
            cells.append(lb)
            return lb

        cell(str(g.seq), 6, "center", FG_DIM)
        # 小头像
        icon = tk.Canvas(row, width=18, height=18, background=fg_sel,
                         highlightthickness=0, bd=0, cursor="hand2")
        icon.pack(side="left", padx=(2, 2))
        self._draw_spawn_row_icon(icon, nm, eid, fg_sel)
        cells.append(icon)
        cell(nm if len(nm) <= 8 else nm[:7] + "…", 16, "w", FG,
             (FONT_UI, FS_MICRO))
        cell("×%d" % g.count if g.count > 1 else "×1", 5, "center",
             ACCENT_SOFT if g.count > 1 else FG_DIM)
        cell(g.interval_text, 6, "center", FG_DIM)
        cell(g.time_text, 7, "e", FG)
        cell(g.stage_time_text, 7, "e", FG_DIM)
        cell("R%d" % (g.route_index + 1) if g.route_index >= 0 else "—",
             5, "center", FG_DIM)

        # 分支出怪（branches[]，装置/陷阱触发）：时间点列显示的只是
        # 「装置开启后相对多久」，不是「这一关第几秒一定出」。不标记的话
        # 会和波次出怪混在一起，看起来像多出来的敌人。纵怒 ro6_c-6 的
        # 家族暗影灭迹人就属这类（vgctrl_bro 分支），它和领舞者共用 R0。
        br = ""
        try:
            evs = getattr(g, "events", None) or []
            br = next((e.branch for e in evs if getattr(e, "branch", "")), "")
        except Exception:
            br = ""
        if br:
            lb = cell("条件出怪", 9, "center", ACCENT_TXT)
            _bind_tip(lb, "这一条来自 branches[]「%s」分支，由装置/陷阱触发。"
                          "时间点列只是相对触发时刻的偏移，"
                          "不是「本关第几秒一定出」。" % br)
        else:
            cell("", 9, "center", FG_DIM)

        # 预罚站（路线第一个检查点就是 WAIT_FOR_SECONDS）标记。
        # 「时间点」列显示的是**出场**时间；如果敌人出场后原地不动
        # 上百秒，只看这一列会以为它立刻开始走。纵怒 ro6_c-6 就有
        # 3 只领舞者出场 0s、预罚站 120s，实到蓝门 143~151s，比关卡
        # 时长 139s 还长——列表里却和另外 6 只长得一模一样。
        pw = self._pre_wait_of(g.route_index, eid)
        if pw > 0.5:
            lb = cell("罚站%s" % _pw_text(pw), 9, "center", ACCENT_TXT)
            _route_pw = self._pre_wait_of(g.route_index)
            _spawn_pw = pw - _route_pw
            if _spawn_pw > 0.5:
                tip = ("该敌人天赋带【休憩】：出场后先在出生点站着不动 "
                       "%.1fs（关卡数据写的是这个数），之后才开始沿路线走。"
                       "这段时间不在路线上，所以别的面板可能显示 0。"
                       % _spawn_pw)
            else:
                tip = ("这条路线的第一个检查点是「原地等待 %.1fs」，"
                       "所以该敌出场后先在出生点罚站，%.1fs 后才开始移动"
                       % (pw, pw))
            _bind_tip(lb, tip)

        # 点击：隔离该路线，并把这只敌人在图上圈出来
        def on_click(_e=None, r=g.route_index, i=eid, s=nm):
            if r < 0:
                return
            if getattr(self.canvas, "isolate_route", None) == r:
                self._clear_isolate()
            else:
                self._isolate(r)
            self._highlight_enemy(i, r, s)

        # 双击：打开该敌人的图鉴
        def on_dbl(_e=None, i=eid, s=nm):
            self._open_codex(i, s, 0)

        for w in [row] + cells:
            w.bind("<Button-1>", on_click)
            w.bind("<Double-Button-1>", on_dbl)
        return row

    def _draw_spawn_row_icon(self, canvas, nm, eid, bg) -> None:
        """表格行里的小头像（16px）。"""
        try:
            from ..core import enemy_icons as EI
            im = EI.load_icon(self.app.paths, nm, 16)
            if im is not None:
                from PIL import ImageTk
                ph = ImageTk.PhotoImage(im)
                self._spawn_photos[eid + "@row"] = ph
                canvas.create_image(9, 9, image=ph)
                return
        except Exception:
            pass
        canvas.create_oval(1, 1, 17, 17, fill=BG_INPUT, outline=DIVIDER)
        canvas.create_text(9, 9, text=(nm or "?")[:1], fill=FG_DIM,
                           font=(FONT_UI, 8, "bold"))

    def _make_spawn_tile(self, master, eid, nm, n, t0, st):
        """一个出怪图标块。"""
        card = tk.Frame(master, background=BG_SUNKEN,
                        highlightthickness=1, highlightbackground=DIVIDER,
                        cursor="hand2")
        inner = tk.Frame(card, background=BG_SUNKEN)
        inner.pack(fill="x", padx=3, pady=3)

        icon = tk.Canvas(inner, width=44, height=44, background=BG_SUNKEN,
                         highlightthickness=0, bd=0, cursor="hand2")
        icon.pack(side="left")
        self._draw_spawn_icon(icon, nm, eid)

        box = tk.Frame(inner, background=BG_SUNKEN)
        box.pack(side="left", fill="both", expand=True, padx=(4, 0))
        name = nm if len(nm) <= 7 else nm[:6] + "…"
        lbl = tk.Label(box, text=name, background=BG_SUNKEN, foreground=FG,
                       font=(FONT_UI, FS_MICRO), anchor="w")
        lbl.pack(fill="x")
        sub = "%d 只" % n if n else "—"
        if t0 is not None:
            sub += " · %.0fs" % t0
        tk.Label(box, text=sub, background=BG_SUNKEN, foreground=FG_DIM,
                 font=(FONT_NUM, FS_MICRO), anchor="w").pack(fill="x")

        for w in (card, inner, icon, box, lbl):
            w.bind("<Button-1>", lambda e, i=eid, s=nm, lv=0: self._open_codex(i, s, lv))
        return card

    def _draw_spawn_icon(self, canvas, nm, eid) -> None:
        """画怪物头像；拿不到就画一个带首字的占位圆。

        本地缓存命中就直接画；否则后台下载，完成后回主线程补画，
        绝不因为联网阻塞 UI（这是敌人档案卡顿的主因）。
        """
        im = None
        try:
            from ..core import enemy_icons as EI
            im = EI.load_icon(self.app.paths, nm, 44)
        except Exception:
            im = None
        if im is not None:
            try:
                from PIL import ImageTk
                ph = ImageTk.PhotoImage(im)
                self._spawn_photos[eid] = ph    # 必须持引用，否则被 GC
                canvas.create_image(22, 22, image=ph)
                return
            except Exception:
                pass
        self._draw_spawn_placeholder(canvas, nm)
        # 后台补图
        try:
            from ..core import enemy_icons as EI
            EI.load_icon_async(
                self.app.paths, nm, 44,
                on_done=lambda im2, c=canvas, n=nm, i=eid:
                    self.after(0, self._on_spawn_icon_ready, c, n, i, im2))
        except Exception:
            pass

    def _draw_spawn_placeholder(self, canvas, nm) -> None:
        canvas.create_oval(2, 2, 42, 42, fill=BG_PANEL, outline=DIVIDER)
        canvas.create_text(22, 22, text=(nm or "?")[:1], fill=FG_DIM,
                           font=(FONT_UI, FS_BODY, "bold"))

    def _on_spawn_icon_ready(self, canvas, nm, eid, im) -> None:
        """后台敌人图标就绪后补画（主线程）。"""
        if im is None:
            return
        try:
            if not canvas.winfo_exists():
                return
            from PIL import ImageTk
            ph = ImageTk.PhotoImage(im)
            self._spawn_photos[eid] = ph
            canvas.delete("all")
            canvas.create_image(22, 22, image=ph)
        except Exception:
            pass

    def _open_codex(self, enemy_id: str, name, level: int = 0) -> None:
        """弹出怪物图鉴。

        name 可能是字符串，也可能是官方数据里那种
        ``{"m_defined": True, "m_value": "简饲源石虫"}`` 包装形式。
        直接丢给弹窗会把标题变成一串字典。这里先拆包。
        """
        if isinstance(name, dict):
            name = name.get("m_value") or name.get("value") or ""
        name = str(name or "")
        if not name or name == enemy_id:
            try:
                name = self._enemy_name_lookup()(enemy_id) or name
            except Exception:
                pass
        try:
            from .monster_codex import MonsterCodexDialog
            MonsterCodexDialog(self, self.app, name, enemy_id, level)
        except Exception:
            import traceback
            traceback.print_exc()
    # ------------------------------------------------------------ 计算

    def recompute(self) -> None:
        gm = self.game_map
        if not gm:
            return
        try:
            speed = float(self.var_speed.get())
        except ValueError:
            speed = 1.0
        self.analyses = RT.analyze_all(gm, move_speed=speed,
                                       allow_diagonal=self.var_diag.get())
        self.canvas.show_ground = self.var_ground.get()
        self.canvas.show_fly = self.var_fly.get()
        self.canvas.show_cost = self.var_cost.get()
        self.canvas.show_mech = self.var_mech.get()
        self.canvas.set_map(gm, self.analyses)
        # set_map 会重画，出怪点数据要在它之后重新灌一次
        self._build_spawn_points(self.timeline, gm)
        self._apply_playback_span()
        self._fill_info()
        self._update_mech_label(gm)

    def _update_mech_label(self, gm) -> None:
        """状态栏里写一句「本关有哪些机关」，没有机关就留空。"""
        lbl = getattr(self, "lbl_mech", None)
        if lbl is None:
            return
        if gm is None or not self.var_mech.get():
            lbl.config(text="")
            return
        try:
            from ..core.mechanisms import extract, portals
            ms = extract(gm)
        except Exception:
            lbl.config(text="")
            return
        if not ms:
            lbl.config(text="本关无机关")
            return
        n_portal = sum(1 for m in ms if m.cat == "portal")
        n_other = len(ms) - n_portal
        parts = []
        if n_portal:
            npair = len(portals(ms))
            parts.append("传送%d组" % npair)
        if n_other:
            parts.append("机关%d格" % n_other)
        lbl.config(text=" · ".join(parts) if parts else "")

    def _apply_playback_span(self) -> None:
        """把播放条时长对齐到「最后一支出场 + 该敌人走完全程」。

        不能只用 timeline.duration（最后一只**出场**的时刻）：
        H8-4 的乌萨斯平民出场后还要罚站 270 秒，用出场时刻当总时长的话
        动画会立刻结束，那 270 秒根本放不出来。
        """
        tl = self.timeline
        span = tl.span(self.analyses) if tl else 0.0
        if hasattr(self, "tl_frame") and tl:
            extra = ""
            if span > tl.duration + 1.5:
                extra = " · 全程 %.0fs" % span
            self.lbl_tl.config(
                text="（共 %d 只 · 出怪到 %.0fs%s）"
                     % (tl.total_spawns, tl.duration, extra))
        if getattr(self, "playback", None):
            self.playback.set_timeline(span)

    def _fill_info(self) -> None:
        gm = self.game_map
        if not gm:
            return
        s = RT.summarize(gm, self.analyses)
        tele = sum(a.teleports for a in self.analyses)
        van = sum(1 for a in self.analyses if a.vanish)
        tl = self.timeline
        lines = [
            "关卡    %s" % gm.level_id,
            "坐标    列 A~%s / 行 1~%d" % (
                __import__("akcalc.core.coords", fromlist=["col_letter"]).col_letter(gm.width - 1),
                gm.height),
            "尺寸    %d × %d = %d 格" % (s.width, s.height, s.width * s.height),
            "可走    地面 %d 格 / 飞行 %d 格" % (s.ground_count, s.fly_count),
            "路线    %d 条（地面 %d / 飞行 %d）" % (
                s.route_count, s.walk_routes, s.fly_routes),
            "可达    %d / %d" % (s.reachable_routes, s.route_count)
            + ("    瞬移 %d / 离场 %d" % (tele, van) if (tele or van) else ""),
            "耗时    %.1fs ~ %.1fs" % (s.min_time, s.max_time),
            "倍率    moveMultiplier = %s" % gm.move_multiplier,
            "生命    %s    费用 %s→%s" % (
                gm.max_life, gm.initial_cost, gm.max_cost),
        ]
        if tl and tl.events:
            # wave_index < 0 表示分支出怪（装置/陷阱触发），不算「波」
            n_wave = len({e.wave_index for e in tl.events if e.wave_index >= 0})
            n_branch = len({e.branch for e in tl.events if e.branch})
            lines.append("出怪    %d 只 / %d 波 / 最长 %.0fs"
                         % (tl.total_spawns, n_wave, tl.duration))
            if n_branch:
                lines.append("分支出怪 %d 组（装置/陷阱触发，非波次）" % n_branch)
        self.info.configure(state="normal")
        self.info.delete("1.0", "end")
        self.info.insert("1.0", "\n".join(lines))
        self.info.configure(state="disabled")

    # ------------------------------------------------------------ 敌人详情

    def _on_enemy_click(self, item: dict) -> None:
        """点地图上的敌人圆点：直接弹出敌人图鉴。"""
        eid = item.get("enemy_id") or ""
        if not eid:
            return
        nm = item.get("enemy_name") or ""
        try:
            nm = nm or self._enemy_name_lookup()(eid)
        except Exception:
            nm = nm or ""
        self._open_codex(eid, nm or eid, 0)

    def _on_spawn_click(self, coord, items) -> None:
        """点出怪点：列出这个口子的出怪清单，并聚焦到该格。"""
        self.selected = coord
        gm = self.game_map
        r, c = coord
        label = coord_label(r, c, gm.height) if gm else "?"
        lines = ["出怪点 %s　(row %d, col %d)" % (label, r, c), ""]
        total = sum(n for (_nm, n, _t) in items)
        lines.append("合计 %d 只 / %d 种" % (total, len(items)))
        lines.append("-" * 34)
        for nm, n, t in items:
            lines.append("%-12s ×%-3d  首现 %.1fs" % (nm, n, t))
        self.app.status.set("出怪点 %s　%d 只" % (label, total))
        self._show_detail_popup("出怪点 %s" % label, "\n".join(lines))

    def show_enemy_detail(self, enemy_id: str) -> None:
        """敌人介绍页：基础面板 + 本图数值 + 移速交互。"""
        from ..core import interactions as IX

        lib = getattr(self.app, "enemy_lib", None)
        st = self._enemy_stat(enemy_id)
        names = getattr(self.app, "enemy_names", {}) or {}
        name = (names.get(enemy_id) if isinstance(names, dict) else None) \
            or (st.name if st else "") or enemy_id

        lines = ["ID　%s" % enemy_id, ""]
        if st:
            lines += [
                "生命　%s" % _fmt_big(st.hp),
                "攻击　%s" % _fmt_big(st.atk),
                "防御　%s" % _fmt_big(st.defense),
                "法抗　%.0f" % st.magic_resist,   # 已是 0~100 的点数
                "移速　%.2f 格/秒" % st.move_speed,
                "重量　%.0f" % st.weight,
                "阻挡　%d" % st.block_cost,
                "间隔　%.2fs" % st.attack_interval,
                "类型　%s" % ("飞行" if st.is_flying else "地面"),
            ]
        else:
            lines.append("（敌人库未加载，只有名字可用）")

        # 交互：移速修正与光环
        it = None
        try:
            it = IX.for_enemy(lib, enemy_id, 0)
        except Exception:
            it = None
        lines += ["", "── 移速与交互 ──"]
        if it and it.has_any():
            for ln in it.detail_lines():
                lines.append(ln)
        else:
            lines.append("无移速相关天赋或技能")

        # 本图数值：数量 / 首现 / 走的路线
        cnt = 0
        first = None
        routes = set()
        if self.timeline:
            for e in self.timeline.events:
                if e.enemy_id == enemy_id:
                    cnt += 1
                    routes.add(e.route_index)
                    if first is None or e.time < first:
                        first = e.time
        lines += ["", "── 本图情况 ──"]
        if self.game_map:
            lines.append("地图　%s" % self.game_map.level_id)
        lines.append("数量　%d 只" % cnt)
        if first is not None:
            lines.append("首现　%.1fs" % first)
        if routes:
            lines.append("路线　%s" % "、".join(str(x) for x in sorted(routes)))
        else:
            lines.append("路线　（本图不出这只）")

        self._show_detail_popup("敌人　%s" % name, "\n".join(lines))

    def _show_detail_popup(self, title: str, text: str) -> None:
        """把详情写进右侧信息区（不弹窗，避免遮挡地图）。"""
        box = getattr(self, "detail_text", None)
        if box is None:
            return
        box.configure(state="normal")
        box.delete("1.0", "end")
        box.insert("1.0", text)
        box.configure(state="disabled")
        lbl = getattr(self, "lbl_detail_title", None)
        if lbl is not None:
            lbl.config(text=title)

    def _on_hover(self, tile) -> None:
        """悬停格子时在状态栏显示 A1 式坐标，以及这一格的机关是什么。"""
        gm = self.game_map
        if not gm or not tile:
            return
        r, c = self.canvas.hover if self.canvas.hover else (None, None)
        if r is None:
            return
        text = ("坐标 %s　(%d,%d)　地块 %s　高度 %s"
                % (coord_label(r, c, gm.height), r, c,
                   tile.tile_key or "(空)", tile.height_type))
        # 机关格补一句人话解释：tile_gazebo 这种英文名对用户没有意义
        try:
            from ..core.mechanisms import info as _minfo
            rec = _minfo(tile.tile_key or "")
        except Exception:
            rec = None
        if rec:
            text += "　▸ %s：%s" % (rec[1], rec[2])
        self.app.status.set(text)

    def _on_layer(self) -> None:
        if self.game_map:
            self.canvas.show_ground = self.var_ground.get()
            self.canvas.show_fly = self.var_fly.get()
            self.canvas.show_cost = self.var_cost.get()
            self.canvas.show_mech = self.var_mech.get()
            self.canvas.redraw()
            self._update_mech_label(self.game_map)

    def _on_timeline_toggle(self) -> None:
        if self.var_time.get():
            self.tl_frame.pack(fill="x", pady=(PAD_S, 0))
        else:
            self.tl_frame.pack_forget()

    # ---------------------------------------------------------- 视图（翻转/放大）

    def _on_flip(self) -> None:
        """翻转地图显示。

        不重算寻路：翻转只是渲染层的坐标变换，路线/出怪点的数据坐标
        完全不变，所以这里绝不能走 recompute()（那会重新跑一遍 A*，
        大图上要几百毫秒，点一下卡一下）。
        """
        if not self.game_map:
            return
        self.canvas.set_flip(v=self.var_flip_v.get(),
                             h=self.var_flip_h.get())
        # 隔离视图下的罚站标注也跟着翻，不需要额外处理（渲染层统一走 disp_rc）

    def _zoom_step(self, direction: int) -> None:
        """放大 / 缩小一档。"""
        if not self.game_map:
            return
        # 每档 ×1.25，范围 1.0 ~ 4.0：再大就只是看几个格子，没意义
        self._zoom = max(1.0, min(4.0, self._zoom * (1.25 ** direction)))
        self.canvas.set_zoom(self._zoom)
        self.lbl_zoom.config(text="%.2g×" % self._zoom)

    def _reset_view(self) -> None:
        """一键回到默认视图。"""
        self._zoom = 1.0
        if hasattr(self, "lbl_zoom"):
            self.lbl_zoom.config(text="1.0×")
        self.var_flip_v.set(False)
        self.var_flip_h.set(False)
        if getattr(self, "canvas", None):
            self.canvas.reset_view()
        self._clear_isolate()

    # ---------------------------------------------------------- 隔离路线

    def _isolate(self, route_index: int) -> None:
        """只显示某一条路线（点「本关出怪」里的一条时进入）。"""
        if not self.game_map:
            return
        if not (0 <= route_index < len(self.game_map.routes)):
            return
        self.canvas.isolate_route = route_index
        # 隔离视图画的是静态折线、不放动画，此时 highlight_enemy 没有圆点
        # 可套环，留着会让 canvas 认为需要重画（多一次无谓渲染）。
        self.canvas.highlight_enemy = None
        self.canvas.redraw()
        self._fill_isolate_info(route_index)

    def _clear_isolate(self) -> None:
        if getattr(self, "canvas", None):
            self.canvas.isolate_route = None
            self.canvas.highlight_enemy = None
            self.canvas.redraw()
        if hasattr(self, "lbl_detail_title"):
            self.lbl_detail_title.config(
                text="点地图上的敌人圆点或出怪口")

    def _clear_paths(self) -> None:
        """一键清空图上的所有路线，回到干净的地图。

        要同时清三个状态量，少清一个就会出现「按钮点了但线还在」:

        * ``isolate_route`` —— 出怪表点一行进入的单路线视图；
        * ``highlight_route`` —— 图例/高亮选中；
        * ``highlight_enemy`` —— 圈出来的那只敌人。

        清完把选中行也取消掉，否则表格里那行还是高亮态，用户会以为
        路线的显示状态和它不一致。
        """
        canvas = getattr(self, "canvas", None)
        if canvas is not None:
            canvas.isolate_route = None
            canvas.highlight_route = None
            canvas.highlight_enemy = None
            canvas.redraw()
        # 出怪表的行选中态（如果有）一并复位
        for row in (getattr(self, "_spawn_rows", None) or []):
            try:
                row.configure(highlightbackground=DIVIDER)
            except Exception:
                pass
        if hasattr(self, "lbl_detail_title"):
            self.lbl_detail_title.config(
                text="点地图上的敌人圆点或出怪口")
        try:
            self.app.status.set("已清空地图上的路径线")
        except Exception:
            pass

    # ---------------------------------------------------------- 敌人高亮

    def _highlight_enemy(self, enemy_id: str, route_index: int,
                         name: str = "") -> None:
        """把「本关出怪」里点中的那只敌人在地图上圈出来。

        为什么不能只改 ``highlight_route``：路线高亮只管折线颜色，
        敌人圆点该在哪还在哪，眼睛要找半天。这里额外给圆点加光晕和
        双环，并把名字强制画出来；如果这只敌人此刻在场，还会把播放
        游标挪到它身上，省得用户自己拖时间轴去找。

        匹配用 ``(enemy_id, route_index)`` 而不是单看 id：同一只敌人
        可能有两条不同路线，用户点的是具体某一行。
        """
        canvas = getattr(self, "canvas", None)
        if canvas is None:
            return
        eid = str(enemy_id or "")
        if not eid:
            canvas.highlight_enemy = None
            canvas.redraw()
            return
        canvas.highlight_enemy = (eid, int(route_index))
        canvas.redraw()
        where = self._first_spawn_time(eid, route_index)
        label = name or eid
        if where is None:
            self.app.status.set("已高亮 %s（这条路线没有匹配到出怪事件）" % label)
        else:
            self.app.status.set(
                "已高亮 %s　R%d　首现 %.1fs" % (label, route_index + 1, where))

    def _first_spawn_time(self, enemy_id: str, route_index: int):
        """这只敌人在该路线上的首次出现时间；没有就返回 None。"""
        tl = self.timeline
        if not tl:
            return None
        best = None
        for e in tl.events:
            if str(getattr(e, "enemy_id", "")) != str(enemy_id):
                continue
            if int(getattr(e, "route_index", -1)) != int(route_index):
                continue
            t = float(getattr(e, "time", 0.0) or 0.0)
            if best is None or t < best:
                best = t
        return best

    def _fill_isolate_info(self, route_index: int) -> None:
        """隔离视图下把这条路线的时间/罚站信息写到「敌人详情」栏。"""
        gm = self.game_map
        if not gm:
            return
        route = gm.route_by_index(route_index)
        if route is None:
            return
        a = None
        for x in self.analyses:
            if x.route_index == route_index:
                a = x
                break
        if hasattr(self, "lbl_detail_title"):
            self.lbl_detail_title.config(
                text="路线 %d（仅显示此线 · 再点一次退出）" % (route_index + 1))

        # 坐标标签要跟着「翻转」开关走：地图上的坐标带已经被 disp_rc 翻过，
        # 这里如果照数据坐标原样显示，用户上下翻转后看到的详情和地图对不上。
        def _lbl(pos):
            r, c = float(pos[0]), float(pos[1])
            try:
                r, c = self.canvas._r.disp_rc(r, c)
            except Exception:
                pass
            return coord_label(int(round(r)), int(round(c)), gm.height)

        lines = [
            "路线      %d" % (route_index + 1),
            "起点      %s" % _lbl(route.start),
            "终点      %s" % _lbl(route.end),
            "模式      %s%s" % (route.motion_mode,
                                "（飞行）" if str(route.motion_mode).upper() == "FLY" else ""),
        ]
        if a:
            lines.append("总路程    %.2f 格" % a.total_length)
            lines.append("移动耗时  %.2fs" % a.move_time)
            if a.pre_wait > 0:
                lines.append("出发罚站  %.1fs ← 在起点的停驻" % a.pre_wait)
            # 天赋罚站（角兽的【休憩】）：不在路线上，单独一行，免得
            # 「全程」和沙盘算出来的到达时刻对不上却看不出为什么。
            _tids = set()
            try:
                for _e in (self.timeline.events if self.timeline else []):
                    if getattr(_e, "route_index", -1) == route_index:
                        _tids.add(getattr(_e, "enemy_id", ""))
            except Exception:
                _tids = set()
            _tal = 0.0
            for _tid in _tids:
                _tal = max(_tal, float((getattr(self, "_spawn_wait", None) or {})
                                       .get(_tid, 0.0) or 0.0))
            if _tal > 0.5:
                lines.append("天赋罚站  %.1fs ← 【休憩】出场自缚（不在路线上）"
                             % _tal)
            if a.wait_time > 0:
                lines.append("途中罚站  %.1fs（共 %d 处）"
                             % (a.wait_time, self._count_waits(route)))
            _grand = a.total_time + _tal
            if _tal > 0.5:
                lines.append("全程      %.2fs（含天赋罚站 %.1fs）"
                             % (_grand, _tal))
            else:
                lines.append("全程      %.2fs" % a.total_time)
            if not a.reachable:
                lines.append("")
                lines.append("⚠ %s" % a.note)
        self.detail_text.configure(state="normal")
        self.detail_text.delete("1.0", "end")
        self.detail_text.insert("1.0", "\n".join(lines))
        self.detail_text.configure(state="disabled")

    def _count_waits(self, route) -> int:
        n = 0
        for cp in route.checkpoints:
            if cp.is_wait:
                n += 1
        return n

    def _on_timeline_seek(self, seconds: float) -> None:
        """点时间轴：把播放游标移到该时刻。"""
        if self.playback:
            self.playback.pause()
            self.playback.seek(seconds)
        # 跳转是离散操作，拖尾历史必须丢弃：否则会从跳转前的位置
        # 拉出一条横穿地图的假轨迹。
        self.__dict__["_trail_hist"] = {}
        self._on_playback_time(seconds)

    def _clear_trail(self) -> None:
        """清空拖尾历史（换图 / 跳转 / 重播时调用）。"""
        self.__dict__["_trail_hist"] = {}

    def _on_playback_time(self, seconds: float) -> None:
        """播放游标变化：重画地图上的敌人，并同步时间轴游标。"""
        tl = self.timeline
        gm = self.game_map
        if not tl or not gm:
            return
        pos = positions_at(tl, seconds, self.analyses, gm, rich=True)
        for item in pos:
            st = self._enemy_stat(item.get("enemy_id"))
            if st:
                item["hp"] = st.hp
                item["defense"] = st.defense
                # 法抗：悬停提示要求与生命/防御并列显示。
                # 这里的 st 是 EnemyStats，magic_resist 以点数计 0~100。
                item["magic_resist"] = getattr(st, "magic_resist", None)
        self.canvas.set_frame(pos)
        self.timeline_canvas.set_current_time(seconds)
        if not pos:
            self.app.status.set(
                "游戏时间 %.1fs　场上没有敌人" % seconds)
            return
        names = {}
        for item in pos:
            nm = item.get("enemy_name") or ""
            names[nm] = names.get(nm, 0) + 1
        txt = "、".join("%s×%d" % (k, v) for k, v in
                         sorted(names.items(), key=lambda kv: -kv[1])[:5])
        self.app.status.set(
            "游戏时间 %.1fs　场上 %d 只：%s%s"
            % (seconds, len(pos), txt,
               " …" if len(names) > 5 else ""))

    def _enemy_stat(self, enemy_id):
        """取敌人面板（带本关覆盖）。"""
        if not enemy_id:
            return None
        cache = self.__dict__.setdefault("_stat_cache", {})
        if enemy_id in cache:
            return cache[enemy_id]
        lib = getattr(self.app, "enemy_lib", None)
        st = None
        try:
            ov = (self.__dict__.get("_enemy_overrides") or {}).get(enemy_id)
            st = lib.stats(enemy_id, 0, ov) if lib and lib.loaded else None
        except Exception:
            st = None
        cache[enemy_id] = st
        return st
    def _on_cell_click(self, r: int, c: int) -> None:
        gm = self.game_map
        if not gm:
            return
        t = gm.tile_at(r, c)
        if not t:
            return
        lines = [
            "坐标    %s   (第%d行, 第%d列)" % (coord_label(r, c, gm.height), r + 1, c + 1),
            "地块    %s" % (t.tile_key or "(空)"),
            "高度    %s" % t.height_type,
            "建造    %s" % t.buildable_type,
            "通行    %s" % t.passable_mask,
        ]
        # 这个格子上有没有出怪
        if self.timeline:
            on = [e for e in self.timeline.events
                  if self._route_starts_at(e.route_index, (r, c))]
            if on:
                lines.append("出怪    " + "、".join(
                    "%s@%.0fs" % (e.label, e.time) for e in on[:3]))
        self.tile_info.configure(state="normal")
        self.tile_info.delete("1.0", "end")
        self.tile_info.insert("1.0", "\n".join(lines))
        self.tile_info.configure(state="disabled")

    def _route_starts_at(self, route_index: int, cell) -> bool:
        gm = self.game_map
        if not gm:
            return False
        for r in gm.routes:
            if r.index == route_index:
                return tuple(r.start) == tuple(cell)
        return False

    def show_enemy_by_name(self, name: str, enemy_id: str = "",
                           level: int = 0) -> None:
        """按名字打开怪物图鉴（右栏图标点的就是这条）。"""
        self._open_codex(enemy_id, name, level)


def _pw_text(v) -> str:
    """预罚站秒数的紧凑文本：120.0 -> ``120s``，82.5 -> ``82.5s``。"""
    try:
        f = float(v)
    except (TypeError, ValueError):
        return "—"
    if abs(f - round(f)) < 0.05:
        return "%ds" % int(round(f))
    return "%.1fs" % f


def _bind_tip(widget, text: str) -> None:
    """给一个小控件挂悬停提示（不依赖其它模块，出错静默）。"""
    state = {"win": None}

    def show(_e=None):
        if state["win"] is not None:
            return
        try:
            tw = tk.Toplevel(widget)
            tw.wm_overrideredirect(True)
            tw.configure(background=BG_DEEP)
            lbl = tk.Label(tw, text=text, justify="left",
                           background=BG_DEEP, foreground=FG,
                           font=(FONT_UI, FS_SMALL), padx=PAD_M, pady=PAD_S,
                           wraplength=300)
            lbl.pack()
            x = widget.winfo_rootx() + 12
            y = widget.winfo_rooty() + widget.winfo_height() + 4
            tw.wm_geometry("+%d+%d" % (x, y))
            state["win"] = tw
        except Exception:
            state["win"] = None

    def hide(_e=None):
        w = state["win"]
        state["win"] = None
        if w is not None:
            try:
                w.destroy()
            except Exception:
                pass

    widget.bind("<Enter>", show, add="+")
    widget.bind("<Leave>", hide, add="+")
    widget.bind("<Destroy>", lambda _e: hide(), add="+")


def _fmt_big(v) -> str:
    """大数字用「万」压缩，避免表格被撑开。"""
    try:
        f = float(v)
    except (TypeError, ValueError):
        return str(v)
    if f >= 10000:
        return "%.1f 万" % (f / 10000.0)
    return "%.0f" % f
