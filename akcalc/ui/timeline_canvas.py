"""出怪时间轴画布：横轴是游戏时间，纵轴是路线（或坐标），可拖动游标。

鼠标悬停在某个敌人标记上时，显示「第几秒 / 敌人名 / 从哪一格出发」。
"""
from __future__ import annotations

import tkinter as tk
from typing import Dict, List, Optional, Tuple

from ..core.coords import coord_label
from ..core.timeline import SpawnEvent, Timeline

BG_TL = "#1b2029"
GRID_TL = "#262d39"
AXIS_TL = "#3b4554"
TEXT_TL = "#e8ecf1"
TEXT_DIM_TL = "#9aa5b4"
#: 时间轴游标。原来是黄色 #f1c40f——全套里唯一的黄，视线全被它吸走，
#: 反而盖过了「当前时间」这个真正要看的量。改 ACCENT 蓝，和伤害计算
#: 图表的游标竖线同色。
CURSOR_TL = "#4ea1f7"
HOVER_TL = "#ffffff"

#: 路线配色（与地图路线色一致）。
#:
#: 第一条是 ACCENT 蓝（默认路线色），其余用蓝的深浅 + 少量红做区分。
#: 原来这里是 10 个不同色相（蓝/橙/绿/红/紫/青/黄……），和寻路首页的
#: 12 种关卡分类色撞在一起，用户分不清哪抹颜色是路线、哪抹是分类。
PALETTE = [
    "#4ea1f7",  # 蓝 主
    "#e74c3c",  # 红（第二层路线，敌我对比）
    "#8fc2f0",  # 蓝 浅
    "#ff8a7a",  # 红 浅
    "#3d8ad6",  # 蓝 中
    "#c0392b",  # 红 中
    "#6bb4ff",  # 蓝 更浅
    "#ffb4a2",  # 红 最浅
    "#2c6ba8",  # 蓝 深
    "#8e2b20",  # 红 深
]

PAD_L, PAD_R, PAD_T, PAD_B = 54, 16, 14, 26
ROW_H = 18


class TimelineCanvas(tk.Canvas):
    """出怪时间轴。"""

    def __init__(self, master, **kw):
        kw.setdefault("height", 150)
        super().__init__(master, background=BG_TL, highlightthickness=0, **kw)
        self.timeline: Optional[Timeline] = None
        self.height_map = 7
        #: route_index -> (row, col) 出怪点坐标，用于悬停提示显示「出发 Xx」
        self._route_starts: Dict[int, Tuple[int, int]] = {}
        self.current_time: float = 0.0
        self._hover_event: Optional[SpawnEvent] = None
        self._route_rows: Dict[int, int] = {}
        self._t0, self._t1 = 0.0, 1.0
        self._row_h = ROW_H

        self.on_seek = None            # 拖动游标回调
        self.bind("<Configure>", lambda e: self.redraw())
        self.bind("<Motion>", self._motion)
        self.bind("<Leave>", self._leave)
        self.bind("<Button-1>", self._click)

    # ------------------------------------------------------ 数据

    def set_timeline(self, timeline: Optional[Timeline],
                     height_map: int = 7, routes=None) -> None:
        self.timeline = timeline
        self.height_map = max(1, height_map)
        self._route_starts = {}
        if routes is not None:
            for rt in routes:
                try:
                    r, c = rt.start
                    # route_index 用的是原始 JSON routes 下标（Route.index），
                    # 不是本列表下标。
                    key = int(getattr(rt, "index", -1))
                    if key < 0:
                        continue
                    self._route_starts[key] = (int(r), int(c))
                except (TypeError, ValueError, AttributeError):
                    continue
        self.current_time = 0.0
        self._hover_event = None
        self.redraw()

    def set_current_time(self, seconds: float) -> None:
        self.current_time = max(0.0, seconds)
        self.redraw()

    # ------------------------------------------------------ 绘制

    def redraw(self) -> None:
        self.delete("all")
        tl = self.timeline
        w = max(self.winfo_width(), 320)
        h = max(self.winfo_height(), 100)

        if not tl or not tl.events:
            self.create_text(w / 2, h / 2, text="加载关卡后显示出怪时间轴",
                             fill=TEXT_DIM_TL,
                             font=("Microsoft YaHei UI", 9))
            return

        routes = sorted(tl.by_route())
        self._route_rows = {r: i for i, r in enumerate(routes)}
        rows = len(routes)
        avail = h - PAD_T - PAD_B
        self._row_h = max(9, min(ROW_H, int(avail / max(1, rows))))

        dur = max(1.0, tl.duration)
        self._t0, self._t1 = 0.0, dur * 1.02
        self._cw, self._ch = w, h

        px = lambda t: PAD_L + (t - self._t0) / (self._t1 - self._t0) * (w - PAD_L - PAD_R)
        self._px = px

        # 顶部时间刻度
        step = _nice_step(dur / 6.0)
        t = 0.0
        while t <= dur:
            x = px(t)
            self.create_line(x, PAD_T - 4, x, h - PAD_B, fill=GRID_TL)
            self.create_text(x, PAD_T - 6, text=_fmt_t(t), anchor="s",
                             fill=TEXT_DIM_TL, font=("Consolas", 7))
            t += step

        # 每条路线一行，标记出怪点
        for ri, row in self._route_rows.items():
            y = PAD_T + row * self._row_h + self._row_h / 2
            color = PALETTE[row % len(PALETTE)]
            rs = tl.by_route()[ri]
            x0 = px(rs.first_time)
            x1 = px(rs.last_time)
            if x1 > x0:
                self.create_line(x0, y, x1, y, fill=color, width=1)
            for e in rs.events:
                ex = px(e.time)
                hot = (e is self._hover_event)
                # 出怪标记圆点：最小 3px，正常按行高 45% 画，
                # 悬停再放大 2px。用户反馈原来的太小看不清。
                r0 = max(3, int(self._row_h * 0.45))
                if hot:
                    r0 += 2
                self.create_oval(ex - r0, y - r0, ex + r0, y + r0,
                                 fill=HOVER_TL if hot else color,
                                 outline="" if not hot else "#ffffff")

        # 左侧路线标：有坐标就显示「A7」这样的出怪口，否则退回 R 编号
        for ri, row in self._route_rows.items():
            y = PAD_T + row * self._row_h + self._row_h / 2
            if self._row_h >= 11:
                start = self._route_starts.get(ri)
                tag = (coord_label(start[0], start[1], self.height_map)
                       if start else "R%d" % ri)
                self.create_text(PAD_L - 6, y, text=tag, anchor="e",
                                 fill=TEXT_DIM_TL, font=("Consolas", 7))

        # 游标
        cx = px(self.current_time)
        self.create_line(cx, PAD_T - 2, cx, h - PAD_B, fill=CURSOR_TL, width=2)
        self.create_polygon(cx - 4, PAD_T - 8, cx + 4, PAD_T - 8, cx, PAD_T - 2,
                            fill=CURSOR_TL, outline="")

        # 悬停提示
        if self._hover_event is not None:
            e = self._hover_event
            self._draw_tip(e, px(e.time),
                           PAD_T + self._route_rows.get(e.route_index, 0)
                           * self._row_h + self._row_h / 2, w, h)

    def _draw_tip(self, e: SpawnEvent, ex: float, ey: float,
                  w: int, h: int) -> None:
        coord = ""
        if e.route_index >= 0:
            start = self._route_starts.get(e.route_index)
            if start:
                coord = "出发 %s" % coord_label(
                    start[0], start[1], self.height_map)
            else:
                coord = "路线 R%d" % e.route_index
        lines = [
            "%s" % _fmt_t(e.time),
            e.label,
            coord,
        ]
        if e.count > 1:
            lines.append("第 %d/%d 只" % (e.seq + 1, e.count))
        fs = 8
        tw = max(len(s) for s in lines) * (fs + 1) + 14
        th = len(lines) * (fs + 5) + 8
        tx = ex + 10
        ty = ey - th / 2
        if tx + tw > w - 4:
            tx = ex - tw - 10
        ty = max(2, min(ty, h - th - 2))
        self.create_rectangle(tx, ty, tx + tw, ty + th, fill="#252b36",
                              outline=HOVER_TL, width=1)
        for i, s in enumerate(lines):
            self.create_text(tx + 7, ty + 5 + i * (fs + 5), text=s, anchor="nw",
                             fill=TEXT_TL if i == 0 else TEXT_DIM_TL,
                             font=("Microsoft YaHei UI", fs))

    # ------------------------------------------------------ 交互

    def _at(self, x: float, y: float) -> Tuple[Optional[SpawnEvent], float]:
        """命中最接近的标记，并返回对应时间。"""
        tl = self.timeline
        if not tl or not tl.events:
            return None, 0.0
        t = self._t0 + (x - PAD_L) / max(1.0, self._cw - PAD_L - PAD_R) * (self._t1 - self._t0)
        t = max(0.0, min(t, self._t1))
        row = int((y - PAD_T) // self._row_h) if self._row_h else 0
        routes = sorted(self._route_rows)
        best, best_d = None, 1e9
        if 0 <= row < len(routes):
            ri = routes[row]
            for e in tl.by_route()[ri].events:
                d = abs(e.time - t)
                if d < best_d:
                    best, best_d = e, d
        if best_d > max(1.2, (self._t1 - self._t0) / 60.0):
            return None, t
        return best, t

    def _motion(self, event) -> None:
        e, t = self._at(event.x, event.y)
        if e is not self._hover_event:
            self._hover_event = e
            self.redraw()
        self.configure(cursor="hand2" if e else "")

    def _leave(self, _e=None) -> None:
        if self._hover_event is not None:
            self._hover_event = None
            self.redraw()

    def _click(self, event) -> None:
        e, t = self._at(event.x, event.y)
        self.current_time = e.time if e else t
        self.redraw()
        if self.on_seek:
            self.on_seek(self.current_time)


# ---------------------------------------------------------- 小工具

def _fmt_t(t: float) -> str:
    if t >= 60:
        return "%d:%02d" % (int(t // 60), int(t % 60))
    return "%.0fs" % t if t == int(t) else "%.1fs" % t


def _nice_step(raw: float) -> float:
    """取 1/2/5×10^n 里第一个 >= raw 的步长（一直返回正数）。"""
    raw = float(raw)
    if not (raw > 0) or raw != raw:      # 0 / 负数 / NaN
        return 1.0
    exp = 1.0
    # 限量上升，避免极端值死循环
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