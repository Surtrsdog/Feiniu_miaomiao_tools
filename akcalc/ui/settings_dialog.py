# -*- coding: utf-8 -*-
"""设置窗口：字号档位等界面偏好。

用独立 Toplevel 而不是塞进主界面，是为了不跟「伤害计算 / 寻路分析」
两个视图抢空间——那个窗口已经排得很满了。

两个设计要点（来自用户反馈）：

* **字号只影响预览，点「完成」才真正应用。** 以前每点一个单选项就
  立刻遍历整棵控件树重设字体，整窗重排一次，连点几下会明显卡顿。
* 底部显示版本号（当前 ``beta2``），并提供「从 GitHub 检查更新」
  按钮——只读 Releases 元数据，查到新版本就把下载链接给用户，
  不自动下载替换（单文件 exe 运行中替换自身在 Windows 上做不到）。
"""

from __future__ import annotations

import threading
import tkinter as tk
import webbrowser
from tkinter import ttk
from typing import Callable, Optional

from ..core import settings as SET
from ..core import update_check as UC
from . import widgets as W
from .widgets import (ACCENT, BG, BG_DEEP, BG_PANEL, BG_SUNKEN, BORDER,
                      DIVIDER, FG, FG_DIM, FONT_NUM, FONT_UI, FS_BODY,
                      FS_H1, FS_MICRO, FS_SMALL, OK, PAD_L, PAD_M, PAD_S,
                      PAD_XS)

#: 当前版本号。发版时只改这一处。
APP_VERSION = "beta2"

#: 版本号后缀说明，显示在版本号旁边
APP_VERSION_HINT = "测试版"

#: 项目 GitHub 地址（「检查更新」从 Releases 拉版本清单）
GITHUB_REPO = "https://github.com/feiniu-miaomiao/feiniu-miaomiao-tools"

#: 预览用的示例文本
_PREVIEW_TEXT = "单次伤害 630　DPS 430"


class SettingsDialog(tk.Toplevel):
    """界面设置。字号先预览，点「完成」才应用并写回 settings.json。"""

    def __init__(self, master, app, on_close: Optional[Callable] = None):
        super().__init__(master)
        self.app = app
        self._on_close = on_close
        self.title("设置")
        self.configure(background=BG)
        self.resizable(False, False)
        self.transient(master)

        self._saved_label = app.settings.get("font_size",
                                            SET.DEFAULT_FONT_LABEL)
        self.var_font = tk.StringVar(value=self._saved_label)
        #: 用户是否按过「完成」。直接叉掉窗口视为放弃修改。
        self._committed = False
        #: 「检查更新」是否正在后台跑（防重复点击）
        self._checking = False
        self._build()
        self._center()
        self.protocol("WM_DELETE_WINDOW", self.close)
        self.bind("<Escape>", lambda e: self.close())
        try:
            W.style_dialog(self)
        except Exception:
            pass
        self._refresh_preview()

    # ---------------------------------------------------------- 界面

    def _build(self) -> None:
        head = tk.Frame(self, background=BG_PANEL, highlightthickness=1,
                        highlightbackground=DIVIDER)
        head.pack(fill="x")
        inner = tk.Frame(head, background=BG_PANEL)
        inner.pack(fill="x", padx=PAD_L, pady=PAD_S)
        tk.Label(inner, text="设置", background=BG_PANEL, foreground=FG,
                 font=(FONT_UI, FS_H1, "bold")).pack(side="left")
        # 这里原来还有一个「关闭 ✕」，和标题栏的 ✕ 重复（用户反馈多个 x 号）
        # 已删除，关闭请用标题栏或底部按钮。

        body = tk.Frame(self, background=BG)
        body.pack(fill="both", expand=True, padx=PAD_L, pady=PAD_M)

        # ---- 字体大小
        card = tk.Frame(body, background=BG_PANEL, highlightthickness=1,
                        highlightbackground=DIVIDER)
        card.pack(fill="x")
        tk.Label(card, text="字体大小", background=BG_PANEL, foreground=ACCENT,
                 font=(FONT_UI, FS_BODY, "bold")).pack(
            anchor="w", padx=PAD_M, pady=(PAD_S, 1))
        tk.Label(card,
                 text="下面的预览会立刻变化；点「完成」才把整套界面字号改过去。",
                 background=BG_PANEL, foreground=FG_DIM,
                 font=(FONT_UI, FS_SMALL), wraplength=360,
                 justify="left").pack(anchor="w", padx=PAD_M)

        row = tk.Frame(card, background=BG_PANEL)
        row.pack(fill="x", padx=PAD_M, pady=(PAD_S, PAD_M))
        for label, scale in SET.FONT_SCALES:
            rb = ttk.Radiobutton(row, text=label, value=label,
                                 variable=self.var_font,
                                 style="Card.TRadiobutton",
                                 command=lambda s=scale: self._refresh_preview())
            rb.pack(side="left", padx=(0, PAD_M))

        # 预览：只改这一个 Label 的字体，不碰其它控件
        prev = tk.Frame(card, background=BG_PANEL)
        prev.pack(fill="x", padx=PAD_M, pady=(0, PAD_M))
        tk.Label(prev, text="预览", background=BG_PANEL, foreground=FG_DIM,
                 font=(FONT_UI, FS_SMALL)).pack(side="left", padx=(0, PAD_S))
        self.lbl_prev = tk.Label(prev, text=_PREVIEW_TEXT,
                                 background=BG_PANEL, foreground=ACCENT,
                                 font=(FONT_NUM, 15, "bold"))
        self.lbl_prev.pack(side="left")

        # ---- 关于 / 版本
        about = tk.Frame(body, background=BG_PANEL, highlightthickness=1,
                        highlightbackground=DIVIDER)
        about.pack(fill="x", pady=(PAD_M, 0))
        tk.Label(about, text="关于", background=BG_PANEL, foreground=ACCENT,
                 font=(FONT_UI, FS_BODY, "bold")).pack(
            anchor="w", padx=PAD_M, pady=(PAD_S, 1))

        vrow = tk.Frame(about, background=BG_PANEL)
        vrow.pack(fill="x", padx=PAD_M, pady=(0, PAD_S))
        tk.Label(vrow, text="当前版本", background=BG_PANEL,
                 foreground=FG_DIM, font=(FONT_UI, FS_SMALL)).pack(side="left")
        tk.Label(vrow, text=APP_VERSION, background=BG_PANEL,
                 foreground=FG, font=(FONT_NUM, FS_BODY, "bold")).pack(
            side="left", padx=(PAD_S, PAD_XS))
        tk.Label(vrow, text=APP_VERSION_HINT, background=BG_PANEL,
                 foreground=FG_DIM, font=(FONT_UI, FS_MICRO)).pack(side="left")

        # 「检查更新」：只查 GitHub Releases，不自动下载替换
        urow = tk.Frame(about, background=BG_PANEL)
        urow.pack(fill="x", padx=PAD_M, pady=(0, PAD_M))
        self.btn_update = ttk.Button(urow, text="检查更新", style="App.TButton",
                                     command=self.check_update)
        self.btn_update.pack(side="left")
        self.lbl_update = tk.Label(
            urow, text="从 GitHub 读取最新版本信息",
            background=BG_PANEL, foreground=FG_DIM,
            font=(FONT_UI, FS_MICRO))
        self.lbl_update.pack(side="left", padx=(PAD_S, 0))

        # ---- 底部
        foot = tk.Frame(body, background=BG)
        foot.pack(fill="x", pady=(PAD_M, 0))
        ttk.Button(foot, text="恢复默认", style="App.TButton",
                   command=self.reset).pack(side="left")
        ttk.Button(foot, text="完成", style="Accent.TButton",
                   command=self.commit).pack(side="right")

        try:
            W.harmonize(self)
        except Exception:
            pass

    # ---------------------------------------------------------- 预览

    def _preview_scale(self) -> float:
        """当前单选项对应的字号倍数。"""
        cur = str(self.var_font.get())
        for label, scale in SET.FONT_SCALES:
            if label == cur:
                return float(scale)
        return 1.0

    def _refresh_preview(self) -> None:
        """只把预览那一个 Label 的字号换掉——不遍历整窗，因此不卡。"""
        scale = self._preview_scale()
        size = max(8, int(round(15 * scale)))
        try:
            self.lbl_prev.configure(font=(FONT_NUM, size, "bold"))
        except Exception:
            pass

    def _center(self) -> None:
        self.update_idletasks()
        w = max(self.winfo_reqwidth(), 420)
        h = max(self.winfo_reqheight(), 300)
        try:
            px = self.app.winfo_rootx()
            py = self.app.winfo_rooty()
            pw = self.app.winfo_width()
            ph = self.app.winfo_height()
        except Exception:
            px = py = pw = ph = 0
        if pw > 0:
            x = px + (pw - w) // 2
            y = py + (ph - h) // 3
        else:
            x = (self.winfo_screenwidth() - w) // 2
            y = (self.winfo_screenheight() - h) // 3
        self.geometry("%dx%d+%d+%d" % (w, h, max(0, x), max(0, y)))

    # ---------------------------------------------------------- 动作

    def commit(self) -> None:
        """点「完成」：此刻才把字号真正应用到整套界面。"""
        self._committed = True
        self._apply_saved()
        self.close()

    def _apply_saved(self) -> None:
        label = str(self.var_font.get())
        scale = self._preview_scale()
        self._saved_label = label
        try:
            self.app.set_font_scale(scale, label=label)
        except TypeError:
            # 兼容旧签名
            self.app.set_font_scale(scale)
        except Exception:
            pass

    def reset(self) -> None:
        """恢复默认：只改预览，仍需点「完成」才会应用。"""
        self.var_font.set(SET.DEFAULT_FONT_LABEL)
        self._refresh_preview()

    def check_update(self) -> None:
        """从 GitHub Releases 取最新版本号。

        **在后台线程里发请求**：设置窗口如果卡在 `urlopen` 上，用户会以为
        程序死了（GitHub 在国内经常要等到超时）。这里起一个 daemon 线程，
        结果用 ``after`` 回到主线程更新那一行灰字。

        查到新版只给链接、不自动下载——单文件 exe 正在运行时改不了自己，
        硬做要写「起个 bat 等进程退出再覆盖」，用户中途取消就留半成品。
        """
        if self._checking:
            return
        self._checking = True
        try:
            self.btn_update.configure(state="disabled")
            self.lbl_update.configure(text="正在检查…", foreground=FG_DIM)
        except Exception:                                   # noqa: BLE001
            pass

        def worker():
            try:
                info = UC.check_latest(APP_VERSION, UC.REPO)
            except Exception as e:                          # noqa: BLE001
                info = UC.UpdateInfo(False, current=APP_VERSION,
                                     error="检查失败：%s" % e)
            try:
                self.after(0, lambda: self._apply_update(info))
            except Exception:                               # noqa: BLE001
                pass

        threading.Thread(target=worker, daemon=True).start()

    def _apply_update(self, info) -> None:
        """把检查结果落到那一行灰字上（主线程）。"""
        self._checking = False
        try:
            self.btn_update.configure(state="normal")
        except Exception:                                   # noqa: BLE001
            pass
        color = FG_DIM
        text = info.summary()
        if info.ok and info.has_update:
            color = OK
            text = "%s　→ 新版下载页已复制到剪贴板" % info.summary()
            try:
                self.clipboard_clear()
                self.clipboard_append(info.url or "")
            except Exception:                               # noqa: BLE001
                text = info.summary()
        elif not info.ok:
            color = WARN
        try:
            self.lbl_update.configure(text=text, foreground=color)
        except Exception:                                   # noqa: BLE001
            pass
        # 有新版就弹一个能点「打开发布页」的框；没新版不打扰
        if info.ok and info.has_update:
            try:
                from tkinter import messagebox
                if messagebox.askyesno(
                        "发现新版本",
                        "%s\n\n当前版本：%s\n最新版本：%s%s\n\n"
                        "要打开 GitHub 发布页下载吗？" % (
                            "有新版本可用", info.current, info.latest,
                            ("\n发布时间：%s" % info.published)
                            if info.published else ""),
                        parent=self):
                    webbrowser.open(info.url or "")
            except Exception:                               # noqa: BLE001
                pass

    def close(self) -> None:
        # 没按「完成」就关掉 = 放弃本次改动，预览用的字号不要泄漏到主界面
        try:
            if callable(self._on_close):
                self._on_close()
        except Exception:
            pass
        self.destroy()

