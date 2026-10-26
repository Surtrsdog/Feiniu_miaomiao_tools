# -*- coding: utf-8 -*-
"""「查看原代码」弹窗：展示 Kengxxiao/ArknightsGameData 解包数据的原始 JSON。

干员技能与敌人图鉴共用一个查看器。数据是官方 skill_table.json /
enemy_database.json 里对应条目的原始结构（保留 blackboard、spData、
attributes 等字段，方便阅读与理解），带一键复制与「在 GitHub 查看」跳转。
"""
from __future__ import annotations

import json
import tkinter as tk
from typing import Optional

from .widgets import (ACCENT, BG, BG_DEEP, BG_PANEL, BG_SUNKEN, BORDER,
                      DIVIDER, FG, FG_DIM, FONT_NUM, FONT_UI, FS_BODY,
                      FS_SMALL, PAD_L, PAD_M, PAD_S, PAD_XS)


class CodeViewerDialog(tk.Toplevel):
    """展示一段 JSON 原始代码的弹窗。"""

    def __init__(self, master, title: str, payload, github_url: str = "",
                 hint: str = ""):
        super().__init__(master)
        self.title("查看原代码 · %s" % title)
        self.configure(background=BG)
        self.transient(master)
        self.minsize(560, 480)
        self._payload = payload
        self._github_url = github_url
        self._hint = hint

        if isinstance(payload, (dict, list, tuple)):
            try:
                text = json.dumps(payload, ensure_ascii=False, indent=2)
            except (TypeError, ValueError):
                text = str(payload)
        else:
            text = str(payload)

        self._text = text
        self._build(title)
        self._center(720, 680)
        self.protocol("WM_DELETE_WINDOW", self.close)
        self.bind("<Escape>", lambda e: self.close())
        try:
            from .widgets import style_dialog
            style_dialog(self)
        except Exception:
            pass

    def _build(self, title: str) -> None:
        head = tk.Frame(self, background=BG_PANEL, highlightthickness=1,
                        highlightbackground=DIVIDER)
        head.pack(fill="x")

        bar = tk.Frame(head, background=BG_PANEL)
        bar.pack(fill="x", padx=PAD_L, pady=(PAD_S, 2))
        tk.Label(bar, text="查看原代码", background=BG_PANEL,
                 foreground=ACCENT, font=(FONT_UI, FS_SMALL)).pack(side="left")
        tk.Label(bar, text=title, background=BG_PANEL, foreground=FG,
                 font=(FONT_UI, FS_BODY, "bold")).pack(side="left",
                 padx=(PAD_M, 0))
        # 这里原来还有一个「关闭 ✕」，和标题栏自带的 ✕ 重复，
        # 用户反馈「出现多个 x 号」。标题栏与底部按钮已够用，删掉。

        if self._hint:
            tk.Label(head, text=self._hint, background=BG_PANEL,
                     foreground=FG_DIM, font=(FONT_UI, FS_SMALL),
                     anchor="w", justify="left",
                     wraplength=680).pack(fill="x", padx=PAD_L,
                     pady=(0, PAD_S))

        # 文本区
        wrap = tk.Frame(self, background=BG_SUNKEN, highlightthickness=1,
                        highlightbackground=BORDER)
        wrap.pack(fill="both", expand=True, padx=PAD_L, pady=PAD_M)
        self.txt = tk.Text(wrap, background=BG_SUNKEN, foreground=FG,
                           insertbackground=FG, wrap="none", borderwidth=0,
                           font=(FONT_NUM, FS_SMALL), relief="flat",
                           padx=PAD_M, pady=PAD_M)
        vs = tk.Scrollbar(wrap, orient="vertical", command=self.txt.yview,
                          background=BG_DEEP, troughcolor=BG_SUNKEN)
        hs = tk.Scrollbar(wrap, orient="horizontal", command=self.txt.xview,
                          background=BG_DEEP, troughcolor=BG_SUNKEN)
        self.txt.configure(yscrollcommand=vs.set, xscrollcommand=hs.set)
        self.txt.grid(row=0, column=0, sticky="nsew")
        vs.grid(row=0, column=1, sticky="ns")
        hs.grid(row=1, column=0, sticky="ew")
        wrap.rowconfigure(0, weight=1)
        wrap.columnconfigure(0, weight=1)

        self.txt.insert("1.0", self._text)
        self.txt.configure(state="disabled")

        # 底部按钮
        foot = tk.Frame(self, background=BG)
        foot.pack(fill="x", padx=PAD_L, pady=(0, PAD_M))
        tk.Button(foot, text="复制全部", command=self._copy, relief="flat",
                  background=BG_DEEP, foreground=FG, activebackground=BG_PANEL,
                  activeforeground=FG, font=(FONT_UI, FS_SMALL),
                  highlightthickness=1, highlightbackground=BORDER,
                  cursor="hand2", padx=12, pady=4).pack(side="left")
        if self._github_url:
            tk.Button(foot, text="在 GitHub 查看源文件", command=self._open_github,
                      relief="flat", background=BG_DEEP, foreground=ACCENT,
                      activebackground=BG_PANEL, activeforeground=ACCENT,
                      font=(FONT_UI, FS_SMALL), highlightthickness=1,
                      highlightbackground=BORDER, cursor="hand2",
                      padx=12, pady=4).pack(side="left", padx=(PAD_M, 0))

    def _copy(self) -> None:
        try:
            self.clipboard_clear()
            self.clipboard_append(self._text)
        except tk.TclError:
            pass

    def _open_github(self) -> None:
        import webbrowser
        try:
            webbrowser.open(self._github_url)
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


__all__ = ["CodeViewerDialog"]
