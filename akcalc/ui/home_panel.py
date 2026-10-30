"""主界面：功能入口卡片。

伤害计算与寻路分析是两个完全独立的功能，这里用卡片并列入口；
下方另加「干员数据」「怪物数据图鉴」两栏常用索引，以后加新功能
只需往 FEATURES / EXTRA 里加一条。
"""
from __future__ import annotations

import tkinter as tk
from typing import Callable, List, Optional, Tuple

from .widgets import (ACCENT, ACCENT_DIM, BG, BG_DEEP, BG_PANEL, BG_SUNKEN,
                      BORDER, Card, DIVIDER, FG, FG_DIM, FONT_NUM, FONT_UI,
                      FS_BODY, FS_H1, FS_SMALL, FS_TITLE, HOVER, PAD_L,
                      PAD_M, PAD_S, PAD_XS, apply_dark_style, harmonize)

#: (键, 标题, 说明, 强调色)
#:
#: 强调色统一用 ACCENT（和「伤害计算」一致的蓝）。以前每张卡片一个色相
#: （绿/橙/紫/青），首页看起来像五个不相关的入口；统一之后是「同一套
#: 功能的一组入口」，靠位置和标题区分，不靠颜色区分。
FEATURES = [
    ("damage", "伤害计算",
     "按干员面板与技能倍率，算物理 / 法术 / 元素 / 真实伤害，\n"
     "并给出随敌方防御变化的 DPS 曲线。",
     ACCENT),
    ("path", "寻路分析",
     "按关卡地图还原敌人行进路线与出怪时间轴，\n"
     "查看每秒谁从哪个坐标出发。",
     ACCENT),
    ("sandbox", "沙盘推演",
     "在寻路图上摆干员、放箱子、踢敌人、加减速，\n"
     "实时看路线改道与到达时间的变化。",
     ACCENT),
]

#: 入口卡片下方的两个数据索引栏
#: (键, 标题, 说明, 强调色)
EXTRA = [
    ("op_index", "干员数据",
     "全部 463 名干员的职业、分支、面板与技能倍率查询。",
     ACCENT),
    ("monster_index", "怪物数据图鉴",
     "按名字检索敌人，查看特性、技能与各类抗性。",
     ACCENT),
]


class FeatureCard(tk.Frame):
    """一张功能入口卡片（整卡可点）。"""

    def __init__(self, master, key: str, title: str, desc: str,
                 accent: str, command: Callable[[], None],
                 compact: bool = False):
        super().__init__(master, background=BG_PANEL, highlightthickness=1,
                         highlightbackground=DIVIDER)
        self.key = key
        self.accent = accent
        self._command = command
        self._hover = False
        pad = PAD_M if compact else PAD_L

        body = tk.Frame(self, background=BG_PANEL)
        body.pack(fill="both", expand=True, padx=pad, pady=pad)

        head = tk.Frame(body, background=BG_PANEL)
        head.pack(fill="x")

        # 左侧强调色竖条：轻量视觉锚点，代替原来的装饰性图标
        bar = tk.Frame(head, background=accent, width=4, height=26)
        bar.pack(side="left", padx=(0, PAD_M))
        bar.pack_propagate(False)

        tbox = tk.Frame(head, background=BG_PANEL)
        tbox.pack(side="left", fill="x", expand=True)
        tk.Label(tbox, text=title, background=BG_PANEL, foreground=FG,
                 font=(FONT_UI, (FS_TITLE + 4) if not compact else (FS_H1 + 2),
                       "bold")).pack(anchor="w")

        tk.Label(body, text=desc, background=BG_PANEL, foreground=FG_DIM,
                 font=(FONT_UI, FS_BODY if not compact else FS_SMALL),
                 justify="left", anchor="w").pack(fill="x", pady=(PAD_S, 0))

        foot = tk.Frame(body, background=BG_PANEL)
        foot.pack(fill="x", pady=(PAD_S, 0))
        self.btn = tk.Label(foot, text="进入  →", background=BG_PANEL,
                            foreground=accent, font=(FONT_UI, FS_BODY, "bold"),
                            cursor="hand2")
        self.btn.pack(side="right")

        # 整卡可点
        for w in (self, body, head, tbox, foot, self.btn):
            w.bind("<Button-1>", lambda e: self._command())
        for w in (self, body, head, tbox, foot):
            w.bind("<Enter>", self._on_enter)
            w.bind("<Leave>", self._on_leave)
        self.btn.bind("<Enter>", self._on_enter)
        self.btn.bind("<Leave>", self._on_leave)

        harmonize(self, BG_PANEL)

    def _on_enter(self, _e=None) -> None:
        if self._hover:
            return
        self._hover = True
        self.config(highlightbackground=self.accent, highlightthickness=2)
        self.btn.config(foreground=ACCENT_DIM if self.accent != ACCENT_DIM else FG)

    def _on_leave(self, _e=None) -> None:
        self._hover = False
        self.config(highlightbackground=DIVIDER, highlightthickness=1)
        self.btn.config(foreground=self.accent)


class HomePanel(tk.Frame):
    """主界面：标题 + 功能卡片 + 数据索引栏。"""

    def __init__(self, master, app):
        super().__init__(master, background=BG)
        self.app = app
        self.cards: List[FeatureCard] = []
        self.extra_cards: List[FeatureCard] = []
        self._build()

    def _build(self) -> None:
        wrap = tk.Frame(self, background=BG)
        wrap.pack(fill="both", expand=True, padx=PAD_L, pady=(PAD_M, PAD_L))

        head = tk.Frame(wrap, background=BG)
        head.pack(fill="x", pady=(0, PAD_L))
        tk.Label(head, text="选择功能", background=BG, foreground=FG,
                 font=(FONT_UI, FS_TITLE + 4, "bold")).pack(anchor="w")

        # ---- 主功能
        grid = tk.Frame(wrap, background=BG)
        grid.pack(fill="both", expand=True)
        for col in range(len(FEATURES)):
            grid.columnconfigure(col, weight=1, uniform="feat")

        for col, (key, title, desc, accent) in enumerate(FEATURES):
            card = FeatureCard(
                grid, key, title, desc, accent,
                command=(lambda k=key: self.app.show_view(k)))
            card.grid(row=0, column=col, sticky="nsew",
                      padx=(0, PAD_M) if col < len(FEATURES) - 1 else 0)
            self.cards.append(card)
        grid.rowconfigure(0, weight=1)

        # ---- 数据索引
        tk.Label(wrap, text="数据索引", background=BG, foreground=FG,
                 font=(FONT_UI, FS_TITLE, "bold")).pack(anchor="w",
                                                        pady=(PAD_L, PAD_S))
        ex = tk.Frame(wrap, background=BG)
        ex.pack(fill="x")
        for col in range(len(EXTRA)):
            ex.columnconfigure(col, weight=1, uniform="extra")
        for col, (key, title, desc, accent) in enumerate(EXTRA):
            card = FeatureCard(
                ex, key, title, desc, accent,
                command=(lambda k=key: self.app.show_view(k)), compact=True)
            card.grid(row=0, column=col, sticky="nsew",
                      padx=(0, PAD_M) if col < len(EXTRA) - 1 else 0)
            self.extra_cards.append(card)