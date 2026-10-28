# -*- coding: utf-8 -*-
"""「查看原代码」弹窗：解包原始 JSON + 结构注解。

干员技能与敌人图鉴共用一个查看器。数据本身是官方 skill_table.json /
enemy_database.json 里对应条目的原始结构，一个字都不改写。

## 为什么要加「结构注解」这一栏

只给 JSON 的话，用户查 bug 时看到的是 ``{"prefabKey": "DanceFire",
"blackboard": [{"key": "dance_fire.duration"...}]}``——``DanceFire`` 是
什么、``dance_fire.duration`` 中文是什么意思、它和 PRTS 上写的「初始 40
秒」对得上吗，全得自己猜。所以 JSON 上面再放一栏**结构注解**：每个
``prefabKey`` 一行、每个 ``blackboard`` key 查 ``codex_fields.json`` 的
``tokens`` 得到中文释义，查不到的**照原样列出**并标「暂无释义」加全库
出现次数——「哪个 key 没有释义」本身就是用户判断「解包有没有新增参数」
的线索，省略它才是真的在骗人。

JSON 区完全不动（仍是原文、可复制、可滚），注解只是**附加**的一栏，
可以拖分割条收小甚至收起，不影响原来「看原文」的用法。
"""
from __future__ import annotations

import json
import tkinter as tk
from typing import List, Optional

from .widgets import (ACCENT, ACCENT_TXT, BG, BG_DEEP, BG_PANEL, BG_SUNKEN,
                      BORDER, DIVIDER, FG, FG_DIM, FONT_NUM, FONT_UI, FS_BODY,
                      FS_MICRO, FS_SMALL, PAD_L, PAD_M, PAD_S, PAD_XS, ScrollFrame,
                      WARN)


#: 结构注解区的固定高度（像素）。约 9 行小字：够看到第一个技能的
#: prefabKey 和两三个参数，又不会把下面的 JSON 挤没。
_ANNOT_H = 150


class CodeViewerDialog(tk.Toplevel):
    """展示一段 JSON 原始代码的弹窗。"""

    def __init__(self, master, title: str, payload, github_url: str = "",
                 hint: str = "", annotate=None):
        """``annotate`` 是可选的 ``[{"title": ..., "lines": [...]}, ...]``。

        传了就多一栏「结构注解」；不传（或传空）时弹窗跟以前完全一样，
        所以老调用点不用改。
        """
        super().__init__(master)
        self.title("查看原代码 · %s" % title)
        self.configure(background=BG)
        self.transient(master)
        self.minsize(560, 480)
        self._payload = payload
        self._github_url = github_url
        self._hint = hint
        self._annot = [s for s in (annotate or []) if s]

        if isinstance(payload, (dict, list, tuple)):
            try:
                text = json.dumps(payload, ensure_ascii=False, indent=2)
            except (TypeError, ValueError):
                text = str(payload)
        else:
            text = str(payload)

        self._text = text
        self._build(title)
        # 有注解时窗口高一点，否则 640 高里扣掉标题栏 + 注解 + 按钮，
        # JSON 只剩三四行可见，看着像坏了。
        self._center(760, 800 if self._annot else 680)
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

        # 结构注解（可选）。放在 JSON 上方而不是下方：用户打开这个弹窗多半
        # 是「这段数据看不懂」，先给翻译、再给原文，比让人先滚过几百行
        # JSON 找线索合理。默认展开，但可以一键收起给 JSON 腾地方。
        if self._annot:
            self._build_annot()

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

    # ------------------------------------------------------------ 结构注解

    def _build_annot(self) -> None:
        """结构注解区：每节一个小标题 + 若干「key = 值 → 中文释义」行。

        用 ``ScrollFrame`` 而不是裸 Frame：一个敌人最多三四个技能、每个
        十几个 blackboard key，加起来能到三十多行，固定高度会顶掉下面
        的 JSON。给个上限高度（``_ANNOT_H``）让它自己滚。
        """
        holder = tk.Frame(self, background=BG_PANEL, highlightthickness=1,
                          highlightbackground=DIVIDER)
        holder.pack(fill="x", padx=PAD_L, pady=(0, 0))

        head = tk.Frame(holder, background=BG_PANEL)
        head.pack(fill="x", padx=PAD_M, pady=(PAD_S, 0))
        self._annot_btn = tk.Button(
            head, text="▾ 结构注解", relief="flat", background=BG_PANEL,
            foreground=ACCENT, activebackground=BG_PANEL,
            activeforeground=ACCENT_TXT, font=(FONT_UI, FS_SMALL, "bold"),
            highlightthickness=0, bd=0, cursor="hand2", padx=0, pady=0,
            command=self._toggle_annot)
        self._annot_btn.pack(side="left")
        tk.Label(head, text="每个 prefabKey / blackboard key 的中文释义，"
                          "查不到会明确标出",
                 background=BG_PANEL, foreground=FG_DIM,
                 font=(FONT_UI, FS_MICRO)).pack(side="left", padx=(PAD_S, 0))

        self._annot_box = tk.Frame(holder, background=BG_PANEL)
        self._annot_box.pack(fill="x", padx=PAD_M, pady=(PAD_XS, PAD_S))
        self._annot_scroll = ScrollFrame(self._annot_box)
        self._annot_scroll.configure(height=_ANNOT_H)
        self._annot_scroll.pack(fill="x")
        self._annot_scroll.pack_propagate(False)

        inner = self._annot_scroll.inner
        for sec in self._annot:
            tk.Label(inner, text="◆ " + str(sec.get("title") or ""),
                     background=BG, foreground=ACCENT_TXT,
                     font=(FONT_UI, FS_MICRO, "bold"), anchor="w",
                     justify="left").pack(fill="x", pady=(PAD_XS, 0))
            for ln in sec.get("lines") or []:
                txt = str(ln)
                # 缩进两级以上的行是「参数释义」，用更暗的颜色区分
                # 小标题和正文，扫读时不需要逐字看。
                dim = txt.startswith("    ") or txt.startswith("  ")
                tk.Label(inner, text=txt, background=BG,
                         foreground=FG_DIM if dim else FG,
                         font=(FONT_NUM if dim else FONT_UI, FS_MICRO),
                         anchor="w", justify="left", wraplength=640).pack(
                    fill="x")
        self._annot_scroll.refresh()

    def _toggle_annot(self) -> None:
        """收起 / 展开结构注解（不销毁控件，避免重建抖动）。"""
        open_now = bool(self._annot_box.winfo_manager())
        if open_now:
            self._annot_box.pack_forget()
            self._annot_btn.configure(text="▸ 结构注解")
        else:
            self._annot_box.pack(fill="x", padx=PAD_M, pady=(PAD_XS, PAD_S))
            self._annot_btn.configure(text="▾ 结构注解")

    def _annot_text(self) -> str:
        """结构注解的纯文本版（「复制全部」时跟 JSON 一起复制）。"""
        out = []
        for sec in self._annot:
            out.append("【%s】" % (sec.get("title") or ""))
            out.extend(str(ln) for ln in (sec.get("lines") or []))
            out.append("")
        return "\n".join(out)

    def _copy(self) -> None:
        """复制注解 + JSON。

        只复制 JSON 的话，用户粘到聊天里还是得自己解释 prefabKey；把注解
        一起带上，粘出去就是一份自带说明的片段。
        """
        body = self._text
        if self._annot:
            body = self._annot_text() + "\n" + body
        try:
            self.clipboard_clear()
            self.clipboard_append(body)
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
