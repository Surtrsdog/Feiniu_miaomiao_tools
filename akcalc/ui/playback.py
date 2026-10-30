"""播放控制条：开始 / 暂停 / 倍速 / 进度条。

时间轴上的出怪动画需要一条独立的时间游标。这里把「游标状态」和
「界面控件」分开：

* ``PlaybackState`` 只管时间推进（纯逻辑，可单独测试）；
* ``PlaybackBar`` 负责把状态画成控件，并按帧驱动回调。

设计上刻意不依赖 tkinter 的 ``after`` 做定时器精度补偿以外的假设，
每帧根据真实经过时间推进，掉帧时进度也不会漂移。

离开面板必须停播
----------------
``after`` 定时器不会因为控件被 ``pack_forget`` 而消失。原先切到别的
功能页后播放仍在后台以 60fps 跑：既占 CPU，又在用户看不见的地方
改游标。现在有两道闸：

1. 面板切走时由外部调用 :meth:`PlaybackBar.suspend` 立即停播；
2. ``_frame`` 自身每帧检查面板是否还在屏幕上，被隐藏就自动停。
"""
from __future__ import annotations

import time
import tkinter as tk
from typing import Callable, List, Optional

from .widgets import (ACCENT, ACCENT_DIM, BG, BG_INPUT, BG_PANEL, BORDER,
                      DIVIDER, FG, FG_DIM, FONT_NUM, FONT_UI, FS_BODY,
                      FS_MICRO, FS_SMALL, PAD_M, PAD_S, PAD_XS, harmonize)

#: 可选倍速
SPEEDS = (0.5, 1.0, 1.5, 2.0, 4.0)

#: 单步跳转的档位（秒）。要求能精确到 0.1s 与 1s 两级。
STEP_SMALL = 0.1
STEP_LARGE = 1.0

#: 帧间隔（毫秒）。50ms ≈ 20fps，足够表现格间移动且不吃 CPU。
#: 动画帧间隔（毫秒）。50ms = 20fps，敌人看起来是一格一格跳的；
#: 现在渲染管线一帧只要 5~8ms，提到 16ms（约 60fps）才跟得上，
#: 敌人圆点在格与格之间是连续滑动的。
FRAME_MS = 16
#: 位置采样步长：插值粒度过粗也会显得顿挫
SAMPLE_SUB = 4


class PlaybackState:
    """播放游标的纯逻辑状态。"""

    def __init__(self, duration: float = 0.0):
        self.duration = max(0.0, float(duration or 0.0))
        self.time = 0.0
        self.speed = 1.0
        self.playing = False
        self._last_wall: Optional[float] = None

    # ---------------------------------------------------------- 控制

    def set_duration(self, duration: float) -> None:
        self.duration = max(0.0, float(duration or 0.0))
        if self.time > self.duration:
            self.time = self.duration

    def play(self) -> None:
        if self.duration <= 0:
            return
        if self.time >= self.duration:
            self.time = 0.0        # 播完再点播放就从头开始
        self.playing = True
        self._last_wall = None

    def pause(self) -> None:
        self.playing = False
        self._last_wall = None

    def toggle(self) -> None:
        self.pause() if self.playing else self.play()

    def seek(self, seconds: float) -> None:
        self.time = min(self.duration, max(0.0, float(seconds)))

    def seek_fraction(self, frac: float) -> None:
        self.seek(self.duration * min(1.0, max(0.0, frac)))

    def step(self, delta: float) -> None:
        """相对当前游标跳 delta 秒（可为负）。

        步进是离散定位操作，**先停在原地再跳**：否则播放中按一下
        「+0.1s」，游标会被下一帧的 tick 继续推着走，看起来像没生效。
        停播由调用方（``PlaybackBar.step``）负责，这里只搬时间。
        """
        self.seek(self.time + float(delta))

    def set_speed(self, speed: float) -> None:
        self.speed = float(speed) if speed > 0 else 1.0

    # ---------------------------------------------------------- 推进

    def tick(self) -> bool:
        """按真实时间推进一帧，返回是否仍在播放。"""
        if not self.playing:
            return False
        now = time.monotonic()
        if self._last_wall is None:
            self._last_wall = now
            return True
        dt = now - self._last_wall
        self._last_wall = now
        # 窗口被打断（拖拽、最小化）时 dt 可能很大，钳一下避免跳太远
        dt = min(dt, 0.5) * self.speed
        self.time = min(self.duration, self.time + dt)
        if self.time >= self.duration:
            self.playing = False
            return False
        return True

    @property
    def fraction(self) -> float:
        return self.time / self.duration if self.duration > 0 else 0.0

    def label(self) -> str:
        return "%s / %s" % (_fmt_clock(self.time), _fmt_clock(self.duration))


def _fmt_clock(sec: float) -> str:
    sec = max(0.0, float(sec or 0.0))
    m = int(sec // 60)
    s = sec - m * 60
    return "%02d:%04.1f" % (m, s)


def _tooltip(widget, text: str) -> None:
    """极简悬停提示（控件少、文案短，不引入通用 Tip 框架）。"""

    tip = {"win": None}

    def show(_e=None):
        if tip["win"] is not None:
            return
        try:
            x = widget.winfo_rootx() + 6
            y = widget.winfo_rooty() + widget.winfo_height() + 4
        except Exception:
            return
        win = tk.Toplevel(widget)
        win.wm_overrideredirect(True)
        win.wm_geometry("+%d+%d" % (x, y))
        tk.Label(win, text=text, background="#0e1218", foreground=FG,
                 font=(FONT_UI, FS_MICRO), padx=6, pady=2,
                 highlightthickness=1,
                 highlightbackground=DIVIDER).pack()
        tip["win"] = win

    def hide(_e=None):
        win = tip["win"]
        if win is not None:
            try:
                win.destroy()
            except Exception:
                pass
            tip["win"] = None

    widget.bind("<Enter>", show, add="+")
    widget.bind("<Leave>", hide, add="+")
    widget.bind("<Button-1>", lambda e: hide(), add="+")


class PlaybackBar(tk.Frame):
    """播放控制条。"""

    def __init__(self, master, on_time: Optional[Callable[[float], None]] = None,
                 on_state: Optional[Callable[[bool], None]] = None,
                 show_progress: bool = True, **kw):
        super().__init__(master, background=BG_PANEL, highlightthickness=1,
                         highlightbackground=DIVIDER, **kw)
        self.state = PlaybackState()
        self.on_time = on_time
        self.on_state = on_state
        self._after_id = None
        self._dragging = False
        self._show_progress = show_progress
        self._build()
        harmonize(self, BG_PANEL)

    # ---------------------------------------------------------- 构建

    def _build(self) -> None:
        row = tk.Frame(self, background=BG_PANEL)
        row.pack(fill="x", padx=PAD_M, pady=PAD_S)

        # 播放 / 暂停
        self.btn_play = tk.Label(row, text="▶  开始播放", background=ACCENT,
                                 foreground="#0c1017",
                                 font=(FONT_UI, FS_BODY, "bold"),
                                 padx=PAD_M, pady=3, cursor="hand2")
        self.btn_play.pack(side="left")
        self.btn_play.bind("<Button-1>", lambda e: self.toggle())

        # 复位
        self.btn_reset = tk.Label(row, text="⏮", background=BG_INPUT,
                                  foreground=FG, font=(FONT_UI, FS_BODY),
                                  padx=PAD_S, pady=3, cursor="hand2")
        self.btn_reset.pack(side="left", padx=(PAD_S, 0))
        self.btn_reset.bind("<Button-1>", lambda e: self.seek(0))

        # 微调时间：±1s / ±0.1s。
        # 播放中敌人圆点在两帧之间连续滑动，光靠眼睛很难确认「它现在
        # 到底在哪一格」，所以给四个单步按钮，配合精确坐标读数对位。
        self._step_btns = []
        for text, delta, tip in (
                ("-1s", -STEP_LARGE, "回退 1 秒"),
                ("-0.1s", -STEP_SMALL, "回退 0.1 秒"),
                ("+0.1s", STEP_SMALL, "前进 0.1 秒"),
                ("+1s", STEP_LARGE, "前进 1 秒")):
            b = tk.Label(row, text=text, background=BG_INPUT, foreground=FG,
                         font=(FONT_NUM, FS_MICRO), padx=PAD_XS, pady=3,
                         cursor="hand2")
            b.pack(side="left", padx=(PAD_XS, 0))
            b.bind("<Button-1>", lambda e, d=delta: self.step(d))
            _tooltip(b, tip)
            self._step_btns.append(b)

        # 时间
        self.lbl_time = tk.Label(row, text="00:00.0 / 00:00.0",
                                 background=BG_PANEL, foreground=FG,
                                 font=(FONT_NUM, FS_SMALL))
        self.lbl_time.pack(side="left", padx=(PAD_M, PAD_M))

        # 倍速
        tk.Label(row, text="倍速", background=BG_PANEL, foreground=FG_DIM,
                 font=(FONT_UI, FS_MICRO)).pack(side="left", padx=(0, PAD_XS))
        self.var_speed = tk.StringVar(value="1.0×")
        self.cmb_speed = tk.OptionMenu(row, self.var_speed,
                                       *["%.1f×" % s for s in SPEEDS],
                                       command=self._on_speed)
        self.cmb_speed.config(background=BG_INPUT, foreground=FG,
                              activebackground=DIVIDER, activeforeground=FG,
                              highlightthickness=0, bd=0, relief="flat",
                              font=(FONT_UI, FS_SMALL), width=5)
        self.cmb_speed["menu"].config(background=BG_INPUT, foreground=FG,
                                      font=(FONT_UI, FS_SMALL))
        self.cmb_speed.pack(side="left")

        # 进度条（可选：沙盘改用粗轴调节，不需要进度条）
        if self._show_progress:
            pwrap = tk.Frame(self, background=BG_PANEL)
            pwrap.pack(fill="x", padx=PAD_M, pady=(0, PAD_S))
            self.progress = tk.Canvas(pwrap, height=18, background=BG_INPUT,
                                      highlightthickness=0, cursor="hand2")
            self.progress.pack(fill="x")
            self.progress.bind("<Button-1>", self._on_progress_click)
            self.progress.bind("<B1-Motion>", self._on_progress_drag)
            self.progress.bind("<ButtonRelease-1>", self._on_progress_release)
            self.progress.bind("<Configure>", lambda e: self._draw_progress())
        else:
            self.progress = None

    # ---------------------------------------------------------- 对外

    def set_timeline(self, duration: float) -> None:
        """切关卡时重设时长并回到起点。"""
        self.pause()
        self.state.set_duration(duration)
        self.state.seek(0)
        self._refresh()

    def toggle(self) -> None:
        if self.state.playing:
            self.pause()
        else:
            self.start()

    def start(self) -> None:
        if self.state.duration <= 0:
            return
        self.state.play()
        self._refresh()
        self._schedule()

    def pause(self) -> None:
        self.state.pause()
        self._cancel()
        self._refresh()

    def seek(self, seconds: float) -> None:
        self.state.seek(seconds)
        self._refresh()
        self._emit()

    def step(self, delta: float) -> None:
        """单步跳转：先停播，再挪游标。

        必须先 ``pause()`` 再 ``seek()``——播放中直接 seek 的话，下一帧
        ``tick()`` 会接着累加时间，用户看到的是「按了但没停住」。
        """
        if self.state.playing:
            self.pause()
        self.state.step(delta)
        self._refresh()
        self._emit()

    def suspend(self) -> None:
        """面板被切走时调用：立即停播并取消定时器。

        只 ``pause()`` 不够——``pause`` 里已经 cancel 了 ``after``，
        但再加一层 try/except 兜底，避免控件已被销毁时抛 TclError。
        """
        try:
            self.state.pause()
            self._cancel()
            self._refresh()
        except Exception:
            pass

    def stop(self) -> None:
        self.pause()
        self.seek(0)

    # ---------------------------------------------------------- 内部

    def _visible(self) -> bool:
        """播放条是否真的在屏幕上（切走的面板不应继续跑动画）。"""
        try:
            return bool(self.winfo_ismapped())
        except Exception:
            return False

    def _schedule(self) -> None:
        self._cancel()
        self._after_id = self.after(FRAME_MS, self._frame)

    def _cancel(self) -> None:
        if self._after_id is not None:
            try:
                self.after_cancel(self._after_id)
            except Exception:
                pass
            self._after_id = None

    def _frame(self) -> None:
        self._after_id = None
        # 面板被切走（pack_forget / 换页）：立刻停，不要继续吃 CPU
        if not self._visible():
            self.state.pause()
            self._refresh()
            return
        still = self.state.tick()
        self._refresh()
        self._emit()
        if still:
            self._schedule()
        else:
            self._notify_state()

    def _emit(self) -> None:
        if self.on_time:
            self.on_time(self.state.time)

    def _notify_state(self) -> None:
        if self.on_state:
            self.on_state(self.state.playing)

    def _refresh(self) -> None:
        playing = self.state.playing
        # 播放中用 ACCENT_DIM（蓝的深一档），暂停用 ACCENT（亮蓝）：
        # 原来播放态是橙色 #e67e22，是这一页唯一的橙，和伤害计算的蓝体系
        # 完全对不上。现在两态都用蓝，靠明度区分「正在跑」和「停着」。
        self.btn_play.config(
            text="⏸  暂停播放" if playing else "▶  开始播放",
            background=ACCENT_DIM if playing else ACCENT)
        self.lbl_time.config(text=self.state.label())
        self._draw_progress()
        self._notify_state()

    def _on_speed(self, _value) -> None:
        try:
            sp = float(str(self.var_speed.get()).rstrip("×"))
        except ValueError:
            sp = 1.0
        self.state.set_speed(sp)

    def _draw_progress(self) -> None:
        if not self._show_progress or self.progress is None:
            return
        c = self.progress
        c.delete("all")
        w = c.winfo_width() or 200
        h = int(c.cget("height"))
        if w < 8:
            return
        # 轨道
        c.create_rectangle(0, h // 2 - 2, w, h // 2 + 2,
                           fill="#2c3444", outline="")
        # 已播部分
        f = self.state.fraction
        c.create_rectangle(0, h // 2 - 2, w * f, h // 2 + 2,
                           fill=ACCENT, outline="")
        # 游标
        x = w * f
        c.create_oval(x - 6, h // 2 - 6, x + 6, h // 2 + 6,
                      fill="#ffffff", outline=ACCENT, width=2)
        # 整秒刻度
        dur = self.state.duration
        if dur > 0:
            step = 10 if dur > 120 else 5
            t = step
            while t < dur:
                xx = w * (t / dur)
                c.create_line(xx, h // 2 - 5, xx, h // 2 + 5,
                              fill="#44536b")
                t += step

    def _frac_at(self, x: int) -> float:
        w = self.progress.winfo_width() or 1
        return min(1.0, max(0.0, x / float(w)))

    def _on_progress_click(self, event) -> None:
        self._dragging = True
        self.pause()
        self.seek(self.state.duration * self._frac_at(event.x))

    def _on_progress_drag(self, event) -> None:
        if self._dragging:
            self.seek(self.state.duration * self._frac_at(event.x))

    def _on_progress_release(self, event) -> None:
        self._dragging = False