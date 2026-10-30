# -*- coding: utf-8 -*-
"""设置窗口：字号档位等界面偏好。

用独立 Toplevel 而不是塞进主界面，是为了不跟「伤害计算 / 寻路分析」
两个视图抢空间——那个窗口已经排得很满了。

两个设计要点（来自用户反馈）：

* **字号只影响预览，点「完成」才真正应用。** 以前每点一个单选项就
  立刻遍历整棵控件树重设字体，整窗重排一次，连点几下会明显卡顿。
* 底部显示版本号（当前 ``2.1``），并提供「从 GitHub 检查更新」
  按钮——只读 Releases 元数据，查到新版本就把下载链接给用户，
  不自动下载替换（单文件 exe 运行中替换自身在 Windows 上做不到）。

另外还放了两块功能配置：

* **抬手单位换算器** —— 帧 ⇄ 秒，按 30 帧/秒。图鉴里已经是双单位，
  但玩家算撤退时机时常常要单独换算某个数字，比手算快。
* **MCP 接口** —— 生成外接 AI（Claude Desktop / Cursor / Cline）需要的
  配置，一键复制，并提供不依赖客户端的自检。
"""

from __future__ import annotations

import threading
import tkinter as tk
import webbrowser
from tkinter import ttk
from typing import Callable, Optional

from ..core import enemy_timing as ETIM
from ..core import settings as SET
from ..core import update_check as UC
from ..mcp import client_config as MCC
from . import widgets as W
from .widgets import (ACCENT, BG, BG_DEEP, BG_PANEL, BG_SUNKEN, BORDER,
                      DIVIDER, FG, FG_DIM, FONT_NUM, FONT_UI, FS_BODY,
                      FS_H1, FS_MICRO, FS_SMALL, OK, PAD_L, PAD_M, PAD_S,
                      PAD_XS, WARN)

#: 当前版本号。发版时只改 core/update_check.py 里的那一处，这里跟着走，
#: 免得 web 界面和旧 tkinter 界面显示出两个不同的版本号。
APP_VERSION = UC.APP_VERSION

#: 版本号后缀说明，显示在版本号旁边
APP_VERSION_HINT = "测试版"

#: 项目 GitHub 地址（「检查更新」从 Releases 拉版本清单）
GITHUB_REPO = "https://github.com/Surtrsdog/Feiniu_miaomiao_tools"

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
        # 小屏（1366x768 笔记本）内容会超过屏幕高度，不能锁死尺寸，
        # 否则底部「完成」按钮永远点不到。
        self.resizable(True, True)
        self.minsize(560, 360)
        self.transient(master)

        self._saved_label = app.settings.get("font_size",
                                            SET.DEFAULT_FONT_LABEL)
        self.var_font = tk.StringVar(value=self._saved_label)
        #: 用户是否按过「完成」。直接叉掉窗口视为放弃修改。
        self._committed = False
        #: 「检查更新」是否正在后台跑（防重复点击）
        self._checking = False
        #: MCP 自检是否正在跑
        self._mcp_testing = False
        self._build()
        # 先把布局跑一遍，滚动内容的 reqheight 才是真实值
        try:
            self.update_idletasks()
        except Exception:                                   # noqa: BLE001
            pass
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

        # 底部按钮固定在窗口底部，不跟着滚动 —— 「完成」必须永远可见。
        foot = tk.Frame(self, background=BG)
        foot.pack(side="bottom", fill="x", padx=PAD_L, pady=(0, PAD_M))
        ttk.Button(foot, text="恢复默认", style="App.TButton",
                   command=self.reset).pack(side="left")
        ttk.Button(foot, text="完成", style="Accent.TButton",
                   command=self.commit).pack(side="right")

        # 中间是可滚动内容区：小屏时滚一滚就能看全，不会挤掉按钮。
        scroll = W.ScrollFrame(self)
        scroll.pack(fill="both", expand=True, padx=PAD_L,
                    pady=(PAD_M, 0))
        body = scroll.inner
        self._scroll = scroll

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
                 font=(FONT_UI, FS_SMALL), wraplength=500,
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

        # ---- 抬手单位换算
        self._build_convert_card(body)

        # ---- MCP 接口
        self._build_mcp_card(body)

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

        # 内容高度可能变化（比如配置 JSON 换行），让滚动区重新量一次
        try:
            self.after_idle(self._scroll.refresh)
        except Exception:                                   # noqa: BLE001
            pass

        try:
            W.harmonize(self)
        except Exception:
            pass

    # ------------------------------------------------------ 抬手换算

    def _build_convert_card(self, body) -> None:
        """帧 ⇄ 秒换算器。"""
        card = tk.Frame(body, background=BG_PANEL, highlightthickness=1,
                        highlightbackground=DIVIDER)
        card.pack(fill="x", pady=(PAD_M, 0))
        tk.Label(card, text="抬手单位换算", background=BG_PANEL,
                 foreground=ACCENT,
                 font=(FONT_UI, FS_BODY, "bold")).pack(
            anchor="w", padx=PAD_M, pady=(PAD_S, 1))
        tk.Label(card,
                 text="明日方舟逻辑按 30 帧/秒运行，帧和秒精确互转；"
                      "60/120 是高刷设备上的插值帧，同一时长帧号成比例"
                      "（14 帧@30 == 28 帧@60）。先选档位再换算。",
                 background=BG_PANEL, foreground=FG_DIM,
                 font=(FONT_UI, FS_SMALL), wraplength=500,
                 justify="left").pack(anchor="w", padx=PAD_M)

        row = tk.Frame(card, background=BG_PANEL)
        row.pack(fill="x", padx=PAD_M, pady=(PAD_S, 2))
        tk.Label(row, text="数值", background=BG_PANEL, foreground=FG_DIM,
                 font=(FONT_UI, FS_SMALL)).pack(side="left", padx=(0, PAD_XS))
        self.var_conv = tk.StringVar(value="14")
        ent = tk.Entry(row, textvariable=self.var_conv, width=8,
                       background=BG_SUNKEN, foreground=FG,
                       insertbackground=FG, relief="flat",
                       font=(FONT_NUM, FS_BODY))
        ent.pack(side="left", ipady=2, padx=(0, PAD_S))
        ent.bind("<KeyRelease>", lambda e: self._refresh_convert())

        self.var_conv_unit = tk.StringVar(value="frame")
        for text, val in (("帧", "frame"), ("秒", "second")):
            tk.Radiobutton(row, text=text, value=val,
                           variable=self.var_conv_unit,
                           background=BG_PANEL, foreground=FG,
                           activebackground=BG_PANEL,
                           selectcolor=BG_DEEP,
                           font=(FONT_UI, FS_SMALL),
                           command=self._refresh_convert).pack(
                side="left", padx=(0, PAD_S))

        # 帧率档：30 = 逻辑真帧；60/120 = 插值帧。见 enemy_timing.
        # SUPPORTED_FPS 的注释——明日方舟本质 30 帧游戏，高刷靠插帧。
        row2 = tk.Frame(card, background=BG_PANEL)
        row2.pack(fill="x", padx=PAD_M, pady=(0, 2))
        tk.Label(row2, text="帧率档", background=BG_PANEL, foreground=FG_DIM,
                 font=(FONT_UI, FS_SMALL)).pack(
            side="left", padx=(0, PAD_XS))
        self.var_conv_fps = tk.StringVar(value="30")
        for val in ETIM.SUPPORTED_FPS:
            tk.Radiobutton(row2, text="%d fps" % val, value=str(val),
                           variable=self.var_conv_fps,
                           background=BG_PANEL, foreground=FG,
                           activebackground=BG_PANEL,
                           selectcolor=BG_DEEP,
                           font=(FONT_UI, FS_SMALL),
                           command=self._refresh_convert).pack(
                side="left", padx=(0, PAD_S))

        self.lbl_conv = tk.Label(card, text="", background=BG_PANEL,
                                 foreground=ACCENT,
                                 font=(FONT_NUM, FS_BODY, "bold"))
        self.lbl_conv.pack(anchor="w", padx=PAD_M, pady=(0, 2))
        # 三档对照行（次要信息，小一号）
        self.lbl_conv_fps = tk.Label(card, text="", background=BG_PANEL,
                                     foreground=FG_DIM,
                                     font=(FONT_NUM, FS_SMALL))
        self.lbl_conv_fps.pack(anchor="w", padx=PAD_M, pady=(0, PAD_M))
        self._refresh_convert()

    def _refresh_convert(self) -> None:
        """按所选档位换算，写进结果行和三档对照行。

        输入的「帧」按当前帧率档解释：选了 60fps 再输 28 帧，
        指的是 60fps 口径的 28 帧（= 14 帧@30 = 0.467 秒）。
        """
        unit = str(self.var_conv_unit.get() or "frame")
        try:
            fps_sel = int(str(self.var_conv_fps.get() or "30"))
        except ValueError:
            fps_sel = 30
        raw = str(self.var_conv.get() or "").strip()

        txt = color = sub = ""
        if not raw:
            txt, color = "输入一个数字", FG_DIM
        else:
            try:
                val = float(raw)
            except ValueError:
                txt, color = "请输入数字", WARN
            else:
                # 先折回 30fps 逻辑帧，再统一输出三档
                if unit in ("frame", "frames", "f", "帧") and fps_sel != 30:
                    frame30 = ETIM.frames_at(
                        max(int(round(val * 30.0 / fps_sel)), 0), 30)
                    res = (ETIM.convert(frame30, "frame")
                           if isinstance(frame30, int)
                           else {"error": "换算失败"})
                else:
                    res = ETIM.convert(val, unit)
                if "error" in res:
                    txt, color = res["error"], WARN
                else:
                    txt = res["formatted"]
                    # 只有「帧」输入才按档位解释；秒是绝对单位，
                    # 档位再怎么切，0.4667 秒就是 0.4667 秒
                    is_frame = unit in ("frame", "frames", "f", "帧")
                    if is_frame and fps_sel != 30:
                        at = res.get("frames_at_fps") or {}
                        txt = txt.replace(
                            "%d 帧" % res["frame"],
                            "%d 帧@%dfps" % (at.get(str(fps_sel),
                                                    res["frame"]), fps_sel),
                            1)
                    color = ACCENT
                    at = res.get("frames_at_fps") or {}
                    if at:
                        sub = ("@30fps %s 帧 ｜ @60fps %s 帧 ｜ "
                               "@120fps %s 帧（60/120 为插值帧）"
                               % (at.get("30"), at.get("60"), at.get("120")))
        try:
            self.lbl_conv.configure(text=txt, foreground=color)
            self.lbl_conv_fps.configure(text=sub)
        except Exception:                                   # noqa: BLE001
            pass

    # ------------------------------------------------------ MCP

    def _build_mcp_card(self, body) -> None:
        """MCP 接口：显示命令、给可复制的配置、带自检。"""
        card = tk.Frame(body, background=BG_PANEL, highlightthickness=1,
                        highlightbackground=DIVIDER)
        card.pack(fill="x", pady=(PAD_M, 0))
        hrow = tk.Frame(card, background=BG_PANEL)
        hrow.pack(fill="x", padx=PAD_M, pady=(PAD_S, 1))
        tk.Label(hrow, text="MCP 接口", background=BG_PANEL,
                 foreground=ACCENT,
                 font=(FONT_UI, FS_BODY, "bold")).pack(side="left")
        self.lbl_mcp_tools = tk.Label(
            hrow, text="", background=BG_PANEL, foreground=FG_DIM,
            font=(FONT_UI, FS_MICRO))
        self.lbl_mcp_tools.pack(side="left", padx=(PAD_S, 0))

        tk.Label(card,
                 text="让 Claude Desktop / Cursor / Cline 这类 AI 客户端"
                      "直接读本软件的敌人、干员、地图、路线数据。"
                      "把下面的配置粘进客户端的 MCP 配置里，重启客户端即可。",
                 background=BG_PANEL, foreground=FG_DIM,
                 font=(FONT_UI, FS_SMALL), wraplength=500,
                 justify="left").pack(anchor="w", padx=PAD_M)

        # 实际命令：输错路径最容易出问题，直接显示出来
        self.lbl_mcp_cmd = tk.Label(
            card, text="", background=BG_PANEL, foreground=FG,
            font=(FONT_NUM, FS_MICRO), wraplength=500,
            justify="left", anchor="w")
        self.lbl_mcp_cmd.pack(fill="x", padx=PAD_M, pady=(PAD_XS, 0))

        # 配置 JSON（只读文本框，可选中复制）
        box = tk.Frame(card, background=BG_PANEL)
        box.pack(fill="x", padx=PAD_M, pady=(PAD_S, 0))
        self.txt_mcp = tk.Text(box, height=7, width=46, wrap="none",
                               background=BG_DEEP, foreground=FG,
                               insertbackground=FG, relief="flat",
                               font=(FONT_NUM, FS_MICRO))
        self.txt_mcp.pack(side="left", fill="x", expand=True)
        sb = tk.Scrollbar(box, command=self.txt_mcp.yview)
        sb.pack(side="right", fill="y")
        self.txt_mcp.configure(yscrollcommand=sb.set)

        brow = tk.Frame(card, background=BG_PANEL)
        brow.pack(fill="x", padx=PAD_M, pady=(PAD_S, PAD_M))
        ttk.Button(brow, text="复制配置", style="App.TButton",
                   command=self.copy_mcp_config).pack(side="left")
        self.btn_mcp_test = ttk.Button(brow, text="自检", style="App.TButton",
                                       command=self.test_mcp)
        self.btn_mcp_test.pack(side="left", padx=(PAD_S, 0))
        self.lbl_mcp = tk.Label(brow, text="", background=BG_PANEL,
                                foreground=FG_DIM,
                                font=(FONT_UI, FS_MICRO))
        self.lbl_mcp.pack(side="left", padx=(PAD_S, 0))

        self._fill_mcp()

    def _fill_mcp(self) -> None:
        """把命令和配置填进控件。"""
        try:
            st = MCC.status()
        except Exception:                                   # noqa: BLE001
            st = {}
        try:
            self.lbl_mcp_tools.configure(
                text="%d 个工具　协议 %s" % (
                    st.get("tool_count", 0), st.get("protocol", "")))
        except Exception:                                   # noqa: BLE001
            pass
        try:
            self.lbl_mcp_cmd.configure(
                text="命令：%s" % (st.get("command") or ""))
        except Exception:                                   # noqa: BLE001
            pass
        try:
            text = MCC.config_json()
        except Exception:                                   # noqa: BLE001
            text = ""
        try:
            self.txt_mcp.configure(state="normal")
            self.txt_mcp.delete("1.0", "end")
            self.txt_mcp.insert("1.0", text)
            # state=disabled 只挡编辑；Tk 的 Text 在 disabled 下仍能
            # 拖选 + Ctrl+C，正是「只读但可复制」想要的效果。
            self.txt_mcp.configure(state="disabled")
        except Exception:                                   # noqa: BLE001
            pass

    def copy_mcp_config(self) -> None:
        """复制 MCP 配置到剪贴板。"""
        try:
            text = MCC.config_json()
        except Exception as e:                              # noqa: BLE001
            text = ""
            err = str(e)
        else:
            err = ""
        try:
            self.clipboard_clear()
            self.clipboard_append(text)
            self.lbl_mcp.configure(text="配置已复制到剪贴板",
                                   foreground=OK)
        except Exception:                                   # noqa: BLE001
            self.lbl_mcp.configure(text="复制失败%s" % (
                "：" + err if err else ""), foreground=WARN)

    def test_mcp(self) -> None:
        """后台跑一遍 MCP 自检（initialize + tools/list）。

        必须在后台线程：打包版第一次跑要加载敌人库（15MB JSON），
        在主线程做会让设置窗口卡住好几秒，用户会以为死了。
        """
        if self._mcp_testing:
            return
        self._mcp_testing = True
        try:
            self.btn_mcp_test.configure(state="disabled")
            self.lbl_mcp.configure(text="正在自检…", foreground=FG_DIM)
        except Exception:                                   # noqa: BLE001
            pass

        def worker():
            # 这里**不能**调 serve()。serve() 会把 sys.stdin/stdout/stderr
            # 换成协议流并进入阻塞主循环——在 GUI 的后台线程里这么干，
            # 等于把进程的标准流偷走，实测整个程序 exit 1 直接没了。
            # handle() 是纯函数：吃一个请求、吐一个响应，不碰全局状态。
            try:
                from ..mcp import server as SRV
                init = SRV.handle({
                    "jsonrpc": "2.0", "id": 1, "method": "initialize",
                    "params": {"protocolVersion": SRV.PROTOCOL_VERSION,
                               "clientInfo": {"name": "settings"}},
                })
                proto = ((init or {}).get("result") or {}).get(
                    "protocolVersion", "")
                lst = SRV.handle({"jsonrpc": "2.0", "id": 2,
                                  "method": "tools/list"})
                n = len(((lst or {}).get("result") or {}).get("tools") or [])
                okk = n > 0
                msg = ("自检通过：%d 个工具，协议 %s" % (n, proto)
                       if okk else "自检失败：没有拿到工具列表")
            except Exception as e:                          # noqa: BLE001
                okk = False
                msg = "自检失败：%s" % e
            try:
                self.after(0, lambda: self._apply_mcp_test(okk, msg))
            except Exception:                               # noqa: BLE001
                pass

        threading.Thread(target=worker, daemon=True).start()

    def _apply_mcp_test(self, okk: bool, msg: str) -> None:
        self._mcp_testing = False
        try:
            self.btn_mcp_test.configure(state="normal")
            self.lbl_mcp.configure(text=msg,
                                   foreground=OK if okk else WARN)
        except Exception:                                   # noqa: BLE001
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
        """居中，并且**把高度夹到屏幕可用范围内**。

        以前只取 reqheight，不看屏幕。内容一多（这次加了换算器和 MCP
        卡），reqheight 涨到 855px，1366x768 的笔记本上一开就超出，
        标题栏和底部按钮都在屏幕外。
        """
        self.update_idletasks()
        w = max(self.winfo_reqwidth(), 560)

        # 滚动区的 canvas 默认高 1px，包在 expand=True 里会让
        # winfo_reqheight() 只报到 362px（标题栏 + 底部按钮），
        # 内容的真实高度全丢了。所以有滚动区时用内容的 reqheight，
        # 再加上标题栏 / 底部按钮 / 外边距，才是「内容全放下」的高度。
        h = self.winfo_reqheight()
        sc = getattr(self, "_scroll", None)
        if sc is not None:
            try:
                inner_h = sc.inner.winfo_reqheight()
                chrome = h - max(sc.winfo_reqheight(), 1)
                if inner_h > 1:
                    # chrome = 标题栏 + 底部按钮 + 边距
                    h = inner_h + max(chrome, 100)
            except Exception:                               # noqa: BLE001
                pass
        h = max(h, 300)

        # 屏幕可用高度：去掉任务栏和标题栏的余量
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        avail_h = max(320, sh - 120)
        if h > avail_h:
            h = avail_h
        if w > sw - 40:
            w = max(360, sw - 40)

        try:
            px = self.app.winfo_rootx()
            py = self.app.winfo_rooty()
            pw = self.app.winfo_width()
            ph = self.app.winfo_height()
        except Exception:
            px = py = pw = ph = 0
        if pw > 0:
            x = px + (pw - w) // 2
            y = py + max(0, (ph - h) // 3)
        else:
            x = (sw - w) // 2
            y = max(0, (sh - h) // 3)
        # 别让窗口跑到屏幕外
        x = max(0, min(x, sw - w - 10))
        y = max(0, min(y, sh - h - 40))
        self.geometry("%dx%d+%d+%d" % (w, h, x, y))

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

