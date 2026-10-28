"""沙盘粗轴画布：把「谁在第几秒部署、几秒撤、几秒开技能」画成一条时间轴。

与 ``timeline_canvas.py`` 的分工
===============================
* ``TimelineCanvas`` 是**出怪轴**：一行一条路线，画的是敌人什么时候出来。
* 这个 ``TrackCanvas`` 是**部署轴（粗轴）**：一行一枚干员，画的是玩家什么
  时候把他放下去、什么时候撤、什么时候开技能。下面还有一条 ``buff 轴``，
  画的是这次模拟里设过哪些减速/停顿。

两者共用同样的时间刻度与游标，所以沙盘里上下对齐看，就是「这波怪来的
时候我这个人有没有技能」。

为什么自己画而不是复用 TimelineCanvas
------------------------------------
出怪轴的行是「路线」，每行画的是**离散点**；粗轴的行是「干员」，每行画的
是**区间色条**（部署->撤退）加区间内的技能段。两者的命中检测、悬停提示、
颜色语义全不一样，硬塞进一个类会变成满屏 if。

坐标约定
--------
* 时间 -> x：``px(t)``，与出怪轴完全同一套 ``PAD_L / PAD_R`` 边距。
* 行 -> y：每行固定 ``ROW_H``，超出可视高度就按行滚动（``set_scroll``）。

交互
----
* 左键点色条 / 技能段 -> 选中该次部署（``on_pick``）
* 左键点空白处 -> 把游标移到那个时刻（``on_seek``）
* 右键 -> ``on_right_click(uid, x, y)``，由面板弹菜单
* 悬停 -> 画提示框（干员名 / 部署时刻 / 撤退时刻 / 技能轮次）
"""
from __future__ import annotations

import tkinter as tk
from typing import Dict, List, Optional, Tuple

from ..core.sandbox_track import ACT_DEPLOY, ACT_RETREAT, ACT_SKILL, CoarseTrack

BG_TL = "#1b2029"
GRID_TL = "#262d39"
TEXT_TL = "#e8ecf1"
TEXT_DIM_TL = "#9aa5b4"
CURSOR_TL = "#4ea1f7"
HOVER_TL = "#ffffff"

#: 部署色条配色。地面用蓝（与寻路主色一致），高台用紫，
#: 撤退后的区段压暗，技能段用橙——橙在全套里只用于「召唤物」，
#: 但那里是图表，这里是时间轴，不会混淆。
BAR_LOW = "#3d8ad6"
BAR_HIGH = "#8e7cc3"
BAR_SKILL = "#e67e22"
BAR_DEAD = "#3a4250"

PAD_L, PAD_R, PAD_T, PAD_B = 54, 16, 12, 22
ROW_H = 17
#: 粗轴上方留给时间刻度的位置
AXIS_H = 14


class TrackCanvas(tk.Canvas):
    """粗轴（部署轴）。"""

    def __init__(self, master, **kw):
        kw.setdefault("height", 132)
        super().__init__(master, background=BG_TL, highlightthickness=0, **kw)
        self.track: Optional[CoarseTrack] = None
        self.current_time = 0.0
        self.selected_uid = 0
        #: 轴总长（秒）。默认 180，由 ``set_track`` 按实际动作修正。
        self.total = 180.0
        self._hover_uid = 0
        self._bar_hits: List[Tuple[float, float, float, float, int, str]] = []
        self._t0, self._t1 = 0.0, 1.0
        self._row_h = ROW_H
        self._scroll = 0            # 第一行可见行号
        self._cw = 0
        self._ch = 0
        self._px = None
        #: 技能轮次缓存：uid -> [(from, to), ...]，避免每帧重算
        self._cycle_cache: Dict[int, List[Tuple[float, float]]] = {}

        self.on_seek = None            # (seconds)
        self.on_pick = None            # (uid)
        self.on_right_click = None     # (uid, x_root, y_root)

        self.bind("<Configure>", lambda e: self.redraw())
        self.bind("<Motion>", self._motion)
        self.bind("<Leave>", self._leave)
        self.bind("<Button-1>", self._click)
        self.bind("<Button-3>", self._right)
        self.bind("<MouseWheel>", self._wheel)

    # ------------------------------------------------------------ 数据

    def set_track(self, track: Optional[CoarseTrack], total: float = 0.0,
                  cycles: Optional[Dict[int, List[Tuple[float, float]]]] = None,
                  keep_view: bool = False) -> None:
        """换一份粗轴。

        ``total`` 为 0 时用 ``track.span()``（最晚动作）与 180 秒取大者：
        轴太短会把所有动作挤在左边，看不出节奏。
        """
        self.track = track
        self._cycle_cache = dict(cycles or {})
        if total > 0:
            self.total = max(1.0, float(total))
        elif track is not None:
            self.total = max(180.0, track.span())
        if not keep_view:
            self.selected_uid = 0
            self._hover_uid = 0
            self._scroll = 0
        self.redraw()

    def set_cycles(self, cycles: Dict[int, List[Tuple[float, float]]]) -> None:
        self._cycle_cache = dict(cycles or {})
        self.redraw()

    def set_current_time(self, seconds: float, redraw: bool = True) -> None:
        self.current_time = max(0.0, float(seconds))
        if redraw:
            self.redraw()

    def set_selected(self, uid: int) -> None:
        self.selected_uid = int(uid or 0)
        self.redraw()

    # ------------------------------------------------------------ 坐标

    def _x(self, t: float) -> float:
        span = max(1e-6, self._t1 - self._t0)
        return PAD_L + (t - self._t0) / span * max(1, self._cw - PAD_L - PAD_R)

    def _t_at(self, x: float) -> float:
        span = max(1e-6, self._t1 - self._t0)
        w = max(1, self._cw - PAD_L - PAD_R)
        return max(0.0, self._t0 + (x - PAD_L) / w * span)

    # ------------------------------------------------------------ 绘制

    def redraw(self) -> None:
        self.delete("all")
        w = max(self.winfo_width(), 300)
        h = max(self.winfo_height(), 90)
        self._cw, self._ch = w, h
        self._bar_hits = []
        tr = self.track
        dur = max(1.0, self.total)
        self._t0, self._t1 = 0.0, dur

        # 顶部刻度
        step = _nice_step(dur / 8.0)
        t = 0.0
        while t <= dur + 1e-6:
            x = self._x(t)
            self.create_line(x, AXIS_H, x, h - PAD_B, fill=GRID_TL)
            self.create_text(x, AXIS_H - 3, text=_fmt_t(t), anchor="s",
                             fill=TEXT_DIM_TL, font=("Consolas", 7))
            t += step

        rows = tr.all() if tr is not None else []
        if not rows:
            self.create_text(w / 2, (h + AXIS_H) / 2,
                             text="部署干员后，这里会显示部署 / 撤退 / 技能粗轴",
                             fill=TEXT_DIM_TL, font=("Microsoft YaHei UI", 9))
            self._draw_cursor(h)
            return

        avail = h - AXIS_H - PAD_B
        self._row_h = max(12, min(ROW_H, int(avail / max(1, len(rows))))) \
            if len(rows) <= 8 else ROW_H
        visible = max(1, int(avail // self._row_h))
        max_scroll = max(0, len(rows) - visible)
        if self._scroll > max_scroll:
            self._scroll = max_scroll
        shown = rows[self._scroll:self._scroll + visible]

        for i, dep in enumerate(shown):
            y = AXIS_H + i * self._row_h
            cy = y + self._row_h / 2
            self._draw_row(dep, y, cy, dur)

        # 左侧名字列（画在色条之后，压住越界的条）
        band = self.create_rectangle(0, AXIS_H, PAD_L - 6, h - PAD_B,
                                     fill=BG_TL, outline="")
        self.tag_lower(band)
        for i, dep in enumerate(shown):
            cy = AXIS_H + i * self._row_h + self._row_h / 2
            self.create_text(PAD_L - 8, cy, text=_short(dep.name, 5),
                             anchor="e", fill=TEXT_DIM_TL,
                             font=("Microsoft YaHei UI", 7))
        # 滚动提示
        if len(rows) > visible:
            self.create_text(w - PAD_R, h - 6,
                             text="滚轮翻页 %d-%d / %d"
                                  % (self._scroll + 1,
                                     self._scroll + len(shown), len(rows)),
                             anchor="e", fill=TEXT_DIM_TL,
                             font=("Consolas", 7))

        self._draw_cursor(h)
        if self._hover_uid:
            self._draw_tip(self._hover_uid, w, h)

    def _draw_row(self, dep, y: int, cy: float, dur: float) -> None:
        """画一行：部署->撤退的底条，技能段盖在上面。"""
        hit = self._bar_hits
        x0 = self._x(max(0.0, dep.deploy_time))
        x1 = self._x(min(dur, dep.retreat_time
                         if dep.retreat_time is not None else dur))
        if x1 < x0:
            x0, x1 = x1, x0
        alive = dep.retreat_time is None or dep.retreat_time > dur
        color = BAR_HIGH if dep.ground == "HIGH" else BAR_LOW
        bh = max(5, self._row_h - 7)
        top = cy - bh / 2
        if x1 - x0 >= 2:
            fill = color if alive else BAR_DEAD
            self.create_rectangle(x0, top, x1, top + bh, fill=fill,
                                  outline="" if alive else color, width=1)
            hit.append((x0, top, x1, top + bh, dep.uid, "bar"))
        # 技能段
        for (a, b) in self._cycle_cache.get(dep.uid, []):
            sa = self._x(min(dur, max(0.0, a)))
            sb = self._x(min(dur, max(0.0, b)))
            if sb - sa < 1:
                continue
            self.create_rectangle(sa, top + bh * 0.25, sb, top + bh * 0.75,
                                  fill=BAR_SKILL, outline="")
            hit.append((sa, top, sb, top + bh, dep.uid, "skill"))
        # 部署 / 撤退三角
        self.create_polygon(x0, top - 3, x0 - 3, top - 9, x0 + 3, top - 9,
                            fill=color, outline="")
        if dep.retreat_time is not None and dep.retreat_time <= dur:
            xr = self._x(dep.retreat_time)
            self.create_polygon(xr - 3, top - 9, xr + 3, top - 9, xr, top - 3,
                                fill=BAR_DEAD, outline=TEXT_DIM_TL)
        if dep.uid == self.selected_uid:
            self.create_rectangle(x0 - 1, top - 10, max(x0 + 2, x1) + 1,
                                  top + bh + 1, outline=HOVER_TL, width=1)

    def _draw_cursor(self, h: int) -> None:
        cx = self._x(max(0.0, min(self.current_time, self.total)))
        if cx < PAD_L or self._cw <= 0:
            return
        self.create_line(cx, AXIS_H - 1, cx, h - PAD_B, fill=CURSOR_TL, width=2)
        self.create_polygon(cx - 4, AXIS_H - 6, cx + 4, AXIS_H - 6,
                            cx, AXIS_H - 1, fill=CURSOR_TL, outline="")

    def _draw_tip(self, uid: int, w: int, h: int) -> None:
        tr = self.track
        dep = tr.get(uid) if tr is not None else None
        if dep is None:
            return
        lines = ["%s%s" % (dep.name or dep.op_id,
                           "（高台）" if dep.ground == "HIGH" else "（地面）"),
                 "部署 %.1fs" % dep.deploy_time]
        if dep.retreat_time is not None:
            lines.append("撤退 %.1fs（在场 %.1fs）"
                         % (dep.retreat_time,
                            dep.retreat_time - dep.deploy_time))
        else:
            lines.append("未撤退")
        if dep.skill_name:
            lines.append("技能 %s" % dep.skill_name)
        cyc = self._cycle_cache.get(uid) or []
        if cyc:
            lines.append("技能段 %d 次" % len(cyc))
        fs = 8
        tw = max(len(s) for s in lines) * (fs + 1) + 14
        th = len(lines) * (fs + 5) + 8
        tx = min(w - tw - 4, self._x(dep.deploy_time) + 12)
        ty = max(AXIS_H + 2, min(AXIS_H + 2, h - th - 2))
        self.create_rectangle(tx, ty, tx + tw, ty + th, fill="#252b36",
                              outline=HOVER_TL, width=1)
        for i, s in enumerate(lines):
            self.create_text(tx + 7, ty + 5 + i * (fs + 5), text=s,
                             anchor="nw",
                             fill=TEXT_TL if i == 0 else TEXT_DIM_TL,
                             font=("Microsoft YaHei UI", fs))

    # ------------------------------------------------------------ 交互

    def _hit(self, x: float, y: float) -> Tuple[int, str]:
        for (a, b, c2, d, uid, kind) in self._bar_hits:
            if a - 2 <= x <= c2 + 2 and b - 2 <= y <= d + 2:
                return (uid, kind)
        return (0, "")

    def _motion(self, event) -> None:
        uid, _kind = self._hit(event.x, event.y)
        if uid != self._hover_uid:
            self._hover_uid = uid
            self.redraw()
        self.configure(cursor="hand2" if uid else "")

    def _leave(self, _e=None) -> None:
        if self._hover_uid:
            self._hover_uid = 0
            self.redraw()

    def _click(self, event) -> None:
        uid, _kind = self._hit(event.x, event.y)
        if uid:
            self.selected_uid = uid
            if self.on_pick:
                self.on_pick(uid)
            self.redraw()
            return
        t = self._t_at(event.x)
        self.current_time = t
        self.redraw()
        if self.on_seek:
            self.on_seek(t)

    def _right(self, event) -> None:
        uid, _kind = self._hit(event.x, event.y)
        if uid and self.on_right_click:
            self.on_right_click(uid, event.x_root, event.y_root)

    def _wheel(self, event) -> None:
        tr = self.track
        if tr is None:
            return
        n = len(tr.all())
        avail = max(1, self._ch - AXIS_H - PAD_B)
        visible = max(1, int(avail // max(1, self._row_h)))
        if n <= visible:
            return
        delta = -1 if getattr(event, "delta", 0) > 0 else 1
        self._scroll = max(0, min(n - visible, self._scroll + delta))
        self.redraw()


# ---------------------------------------------------------------- 小工具


def _fmt_t(t: float) -> str:
    if t >= 60:
        return "%d:%02d" % (int(t // 60), int(t % 60))
    return "%.0fs" % t if abs(t - int(t)) < 1e-9 else "%.1fs" % t


def _nice_step(raw: float) -> float:
    """取 1/2/5×10^n 里第一个 >= raw 的步长（一直返回正数）。"""
    raw = float(raw)
    if not (raw > 0) or raw != raw:
        return 1.0
    exp = 1.0
    for _ in range(40):
        if exp * 10 > raw:
            break
        exp *= 10
    while exp > raw and exp > 1e-9:
        exp /= 10
    for mult in (1.0, 2.0, 5.0, 10.0):
        if exp * mult >= raw:
            return exp * mult
    return exp * 10.0


def _short(s: str, n: int) -> str:
    s = s or ""
    return s if len(s) <= n else s[:n - 1] + "…"
