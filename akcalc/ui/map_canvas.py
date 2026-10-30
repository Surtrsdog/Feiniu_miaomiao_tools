# -*- coding: utf-8 -*-
"""地图画布（PIL 后端）。

旧实现每帧 ``delete("all")`` 后重建 500~900 个 Canvas item，实测单帧
30~80 ms，播放时界面卡死。这里改成离屏渲染：PIL 合成整帧 -> 一张
``PhotoImage`` -> 单个 canvas item，实测单帧 8 ms（≈120fps），
画布 item 数恒为 1。

对外接口与旧版保持一致（``set_map`` / ``set_frame`` / ``set_spawn_points``
/ ``redraw`` / 各种 ``on_*`` 回调 / ``spawn_points`` / ``_enemy_hit``），
path_panel 无需改动。
"""
from __future__ import annotations

import math
import tkinter as tk
from typing import Callable, Dict, List, Optional, Sequence, Tuple

from PIL import Image, ImageDraw, ImageTk

from ..core.coords import col_letter, coord_label, parse_label
from ..core.models import GameMap, Tile
from ..core.routes import RouteAnalysis, tile_to_pixel
from .map_render import BG, ROUTE_PALETTE, MapRenderer, _dot_sprite, _font, _rgba
from .widgets import ACCENT

Coord = Tuple[int, int]

#: 兼容旧导入
COLOR_TEXT = (238, 242, 247)
COLOR_TEXT_DIM = (154, 165, 180)

#: 地图悬停提示框的描边/标题色。
#:
#: 原来是两档橙色（#ffb4a2 敌人 / #ff9f8a 出怪点），和伤害计算页的
#: 蓝色体系对不上，也容易和地图里红色的敌人标记混。统一成 ACCENT，
#: 和伤害计算图表的悬停浮层用同一个强调色。
_TIP_ACCENT = ACCENT


class MapCanvas(tk.Canvas):
    """地图绘制与交互（PIL 离屏渲染）。"""

    def __init__(self, master, **kw):
        super().__init__(master, background="#171b22", highlightthickness=0,
                         **kw)
        self._r = MapRenderer()
        self._photo: Optional[ImageTk.PhotoImage] = None
        self._item: Optional[int] = None
        self._img_cache = None
        self._cache_key = None
        #: 兼容旧属性
        self.markers: list = []
        self._enemy_hit: List[Tuple[float, float, float, int]] = []

        self.on_cell_click: Optional[Callable[[int, int], None]] = None
        self.on_hover: Optional[Callable[[Optional[Tile]], None]] = None
        self.on_spawn_click: Optional[Callable[[Coord, list], None]] = None
        self.on_enemy_click: Optional[Callable[[dict], None]] = None
        #: 右键回调 ``(row, col, enemy_dict|None)``。沙盘用它来做
        #: 「右键干员 -> 撤退/开技能」「右键敌人 -> 减速」「右键空格 -> 部署」。
        #: 只加回调、不改原有的左键语义，寻路面板不受影响。
        self.on_cell_right_click: Optional[Callable] = None
        #: 悬停到具体对象时的回调 ``(kind, payload)``，kind 取
        #: ``"enemy"`` / ``"tile"`` / ``None``。左键那套 ``on_hover`` 只给
        #: Tile，拿不到敌人，沙盘需要敌人的实时状态。
        self.on_object_hover: Optional[Callable] = None

        self.bind("<Button-1>", self._click)
        self.bind("<Button-3>", self._right_click)
        self.bind("<Motion>", self._motion)
        self.bind("<Leave>", self._leave)
        self.bind("<Configure>", self._on_resize)

    # ------------------------------------------------------------ 属性代理

    def _p(self):
        return self._r

    @property
    def game_map(self):
        return self._r.game_map

    @game_map.setter
    def game_map(self, v):
        self._r.game_map = v

    @property
    def analyses(self):
        return self._r.analyses

    @analyses.setter
    def analyses(self, v):
        self._r.analyses = list(v or [])

    @property
    def cell(self):
        return self._r.cell

    @cell.setter
    def cell(self, v):
        self._r.cell = int(v)

    @property
    def origin_x(self):
        return self._r.origin_x

    @origin_x.setter
    def origin_x(self, v):
        self._r.origin_x = int(v)

    @property
    def origin_y(self):
        return self._r.origin_y

    @origin_y.setter
    def origin_y(self, v):
        self._r.origin_y = int(v)

    @property
    def spawn_points(self):
        return self._r.spawn_points

    @spawn_points.setter
    def spawn_points(self, v):
        self._r.spawn_points = dict(v or {})

    @property
    def frame_enemies(self):
        return self._r.frame_enemies

    @frame_enemies.setter
    def frame_enemies(self, v):
        self._r.frame_enemies = list(v or [])

    def _proxy(name):
        def get(self):
            return getattr(self._r, name)
        def set(self, v):
            setattr(self._r, name, v)
        return property(get, set)

    selected = _proxy("selected")
    hover = _proxy("hover")
    highlight_route = _proxy("highlight_route")
    hover_spawn = _proxy("hover_spawn")
    hover_enemy = _proxy("hover_enemy")
    show_ground = _proxy("show_ground")
    show_fly = _proxy("show_fly")
    show_routes = _proxy("show_routes")
    show_cost = _proxy("show_cost")
    show_dots = _proxy("show_dots")
    isolate_route = _proxy("isolate_route")
    highlight_enemy = _proxy("highlight_enemy")
    flip_v = _proxy("flip_v")
    flip_h = _proxy("flip_h")
    # 机关（传送门 / 火山 / 留声机……）图层开关。没有这个代理时，
    # 外部 `canvas.show_mech = False` 只会在 Canvas 上挂一个死属性，
    # 渲染器读到的一直是默认 True，看起来就是「这个开关没反应」。
    show_mech = _proxy("show_mech")
    # 点中的传送门及其去向路径：((r,c), (dr,dc), certain, path)
    portal_link = _proxy("portal_link")
    del _proxy

    # ------------------------------------------------------------ 缩放/翻转

    def set_zoom(self, zoom: float) -> None:
        """地图放大倍数（1.0 = 自适应铺满）。"""
        self._r.set_zoom(zoom)
        self.fit_cell()          # fit() 内部会重新 _clamp_pan 并算原点
        self.redraw()

    def zoom_by(self, ratio: float) -> None:
        self.set_zoom(self._r.zoom * ratio)

    def reset_view(self) -> None:
        """恢复默认缩放 / 平移 / 翻转。"""
        self._r.reset_view()
        self.fit_cell()
        self.redraw()

    def set_flip(self, v=None, h=None) -> None:
        """翻转地图显示（只改渲染，不改坐标数据）。"""
        if v is not None:
            self._r.flip_v = bool(v)
        if h is not None:
            self._r.flip_h = bool(h)
        self._r.invalidate()
        self.redraw()

    def pan_by(self, dx: float, dy: float) -> None:
        self._r.pan_x += dx
        self._r.pan_y += dy
        self.fit_cell()          # _clamp_pan 需要新的 cell
        self.redraw()

    def set_paths(self, paths) -> None:
        """注入 Paths（用于干员头像加载）。"""
        self._r.set_paths(paths)
        self._r.invalidate()
        self.redraw()

    def set_map(self, game_map: Optional[GameMap],
                analyses: Optional[Sequence[RouteAnalysis]] = None) -> None:
        """切图。注意不清空 spawn_points：调用方通常先铺好出怪点再 set_map。"""
        self._r.set_map(game_map, analyses)
        # 换图后上一张图的敌人位置毫无意义，必须清掉，否则会画到新图上
        self._r.frame_enemies = []
        self._r.hover = None
        self._r.hover_enemy = None
        self._r.hover_spawn = None
        self._enemy_hit = []
        self.redraw()

    def set_spawn_points(self, points: Dict[Coord, list]) -> None:
        self._r.spawn_points = dict(points or {})
        self.redraw()

    def set_frame(self, enemies: Sequence[dict]) -> None:
        """设置动画帧并重绘。这是播放时每帧调用的热点路径。"""
        self._r.frame_enemies = list(enemies or [])
        self._paint()

    def set_markers(self, markers) -> None:
        self.markers = list(markers or [])
        self.redraw()

    def set_sandbox(self, data) -> None:
        """把沙盘棋子推给渲染器。

        ``data`` 是 ``None`` 或一个 dict：
        ``{"boxes": set[(r,c)], "operators": {(r,c): OperatorPiece},
        "range": set[(r,c)], "block": set[(r,c)], "slow": [(r,c), ...],
        "selected_op": (r,c) | None}``。

        ⚠ 只改动态层。渲染器的静态底图 key 里**只**包含
        「沙盘是否启用」这一个布尔，所以反复放箱子不会重建底图
        （60 ms），否则拖动石块会明显卡顿。
        """
        self._r.sandbox = data
        self.redraw()

    def fit_cell(self) -> None:
        self._r.fit(max(self.winfo_width(), 400), max(self.winfo_height(), 300))

    # ------------------------------------------------------------ 绘制

    def redraw(self) -> None:
        """重绘一帧。

        静态层由 render() 内部按 key 自行判断是否重建，这里**不能**无条件
        invalidate——否则每次悬停移动都要重烘焙整张地图（约 60ms），
        播放时会被拖成逐帧卡顿。
        """
        self._paint()

    def _on_resize(self, _e=None) -> None:
        w, h = self.winfo_width(), self.winfo_height()
        if w < 20 or h < 20:
            return
        self._r.fit(w, h)
        # 窗口大小变化只改视口裁剪参数，静态主图不用重烘焙
        # （invalidate 会白重建整张底图，拖窗口会卡）。
        self._paint()

    def _paint(self) -> None:
        """渲染一帧并贴到画布上（只更新一个 item）。"""
        w, h = self.winfo_width(), self.winfo_height()
        if w < 20 or h < 20:
            w, h = 640, 480
        self._r.fit(w, h)
        im = self._r.render()
        self._photo = ImageTk.PhotoImage(im)
        if self._item is None:
            self._item = self.create_image(0, 0, anchor="nw", image=self._photo)
        else:
            self.itemconfig(self._item, image=self._photo)
        self._update_hit()
        self._draw_tooltips()

    # ------------------------------------------------------------ 命中区

    def _update_hit(self) -> None:
        """把当前帧敌人的屏幕位置算成圆形命中区。"""
        self._enemy_hit = []
        gm = self._r.game_map
        if not gm:
            return
        r = max(4.0, self._r.cell * 0.155)
        n = len(self._r.frame_enemies)
        for i, en in enumerate(self._r.frame_enemies):
            row = float(en.get("row", 0))
            col = float(en.get("col", 0))
            x, y = self._r.tile_xy(row, col)
            if n > 1:
                same = [j for j, o in enumerate(self._r.frame_enemies)
                        if abs(float(o.get("row", 0)) - row) < 0.28
                        and abs(float(o.get("col", 0)) - col) < 0.28]
                if len(same) > 1:
                    k = same.index(i)
                    ang = 2 * math.pi * k / len(same) - math.pi / 2
                    off = r * 1.15
                    x += math.cos(ang) * off
                    y += math.sin(ang) * off
            self._enemy_hit.append((x, y, r * 1.7, i))

    # ------------------------------------------------------------ 提示框

    def _draw_tooltips(self) -> None:
        """在图片层之上补画 tooltip（用 Canvas 文字，省得整帧重合成）。"""
        self.delete("tip")
        gm = self._r.game_map
        if not gm:
            return
        # 敌人
        if self._r.hover_enemy is not None and \
                0 <= self._r.hover_enemy < len(self._r.frame_enemies):
            en = self._r.frame_enemies[self._r.hover_enemy]
            row = float(en.get("row", 0))
            col = float(en.get("col", 0))
            x, y = self._r.tile_xy(row, col)
            # timeline 给的是 enemy_name / label，没有 name 键。
            # 早先只读 name，所以悬停永远只显示「敌人」两个字。
            nm = (en.get("enemy_name") or en.get("label")
                  or en.get("name") or "敌人")
            lines = [str(nm)]
            # 本关编号：和右侧「本关出怪」表的「次序」列是同一套数字，
            # 用户看到图上某只可以直接去表里找到对应那一行。
            num = en.get("number")
            if num:
                lines.append("本关第 %d 只" % int(num))
            eid = en.get("enemy_id")
            if eid:
                lines.append("编号 %s" % eid)
            hp = en.get("hp")
            if hp is not None:
                lines.append("生命 %s" % _fmt_big(hp))
            df = en.get("defense")
            if df is not None:
                lines.append("防御 %d" % int(df))
            mr = en.get("magic_resist")
            if mr is not None:
                # 法抗按点数显示（0~100），与干员面板口径一致；
                # 带小数时才补一位，避免「50.0」这种噪声。
                lines.append("法抗 %s" % _fmt_num(mr))
            # ---- 精确坐标
            # 敌人位置是「格中心 + reachOffset」的连续值，所以必须给到
            # 小数位：整数格坐标在贴墙走的关卡里会差半格，玩家拿它去
            # 对轴会得出错误结论。格坐标本身（第几行第几列）另起一行，
            # 因为那是游戏内显示的编号，两者含义不同不能混写。
            # 翻转过地图的话，显示坐标要按当前的 disp_rc 换算回来，
            # 否则「图上看着在左下角，读数却是右上角」。
            drow, dcol = self._r.disp_rc(row, col)
            lines.append("坐标 %s" % _fmt_rc(drow, dcol, gm))
            lines.append("点击查看详情")
            self._tip(x, y, self._r.cell * 0.3, lines, _TIP_ACCENT)
        # 装置
        elif self._r.hover is not None and gm.devices:
            row, col = self._r.hover
            dev = None
            for d in gm.devices:
                if d.row == row and d.col == col and not d.hidden:
                    dev = d
                    break
            if dev is not None:
                x, y = self._r.tile_xy(row, col)
                cat_names = {"A": "改路装置", "B": "阻挡装置",
                             "C": "功能装置", "D": "装饰"}
                nm = self._r._device_name(dev) or dev.token_key
                lines = ["%s %s" % (cat_names.get(dev.category, "装置"), nm)]
                if dev.token_key:
                    lines.append("键值 %s" % dev.token_key)
                if dev.direction:
                    lines.append("朝向 %s" % dev.direction)
                if dev.block_cnt:
                    lines.append("阻挡数 %d" % dev.block_cnt)
                if dev.max_hp:
                    lines.append("生命 %d" % dev.max_hp)
                if dev.stack_size > 1:
                    lines.append("堆叠 ×%d" % dev.stack_size)
                lines.append("坐标 %s" % coord_label(row, col, gm.height))
                self._tip(x, y, self._r.cell * 0.3, lines, _TIP_ACCENT)
        # 出怪点
        elif self._r.hover_spawn and self._r.hover_spawn in self._r.spawn_points:
            row, col = self._r.hover_spawn
            items = self._r.spawn_points[(row, col)]
            x, y = self._r.tile_xy(row, col)
            lines = ["出怪点 %s" % coord_label(row, col, gm.height)]
            for nm, cnt, t in items[:4]:
                lines.append("%s ×%d  %.1fs" % (nm, cnt, t))
            if len(items) > 4:
                lines.append("还有 %d 种…" % (len(items) - 4))
            self._tip(x, y, self._r.cell * 0.26, lines, _TIP_ACCENT)

    def _tip(self, cx, cy, rad, lines, accent) -> None:
        fs = 9
        w = max(len(s) for s in lines) * (fs + 3) + 16
        h = len(lines) * (fs + 6) + 10
        tx = cx + rad + 10
        ty = cy - h / 2
        W = self.winfo_width()
        H = self.winfo_height()
        if tx + w > W - 4:
            tx = cx - rad - 10 - w
        if tx < 2:
            tx = 2
        if ty < 2:
            ty = 2
        if ty + h > H - 2:
            ty = H - 2 - h
        self.create_rectangle(tx, ty, tx + w, ty + h, fill="#0e1218",
                              outline=accent, width=1, tags="tip")
        self.create_text(tx + 7, ty + 5, text=lines[0], anchor="nw",
                         fill=accent, font=("Microsoft YaHei UI", fs + 1, "bold"),
                         tags="tip")
        for i, s in enumerate(lines[1:]):
            self.create_text(tx + 7, ty + 5 + (i + 1) * (fs + 6), text=s,
                             anchor="nw", fill="#c6d2e0",
                             font=("Microsoft YaHei UI", fs), tags="tip")

    # ------------------------------------------------------------ 交互

    def _tile_at_event(self, event) -> Coord:
        r, c = self._r.pixel_tile(event.x, event.y)
        return r, c

    def _click(self, event) -> None:
        # 1) 敌人圆点
        for cx, cy, hit, idx in self._enemy_hit:
            if (event.x - cx) ** 2 + (event.y - cy) ** 2 <= hit ** 2:
                if self.on_enemy_click and 0 <= idx < len(self._r.frame_enemies):
                    self.on_enemy_click(self._r.frame_enemies[idx])
                    return
        if not self._r.game_map:
            return
        r, c = self._tile_at_event(event)
        if r < 0:
            return
        # 2) 出怪点
        if self._r.show_dots and (r, c) in (self._r.spawn_points or {}):
            if self.on_spawn_click:
                self.on_spawn_click((r, c), self._r.spawn_points[(r, c)])
                return
        self._r.selected = (r, c)
        self.redraw()
        if self.on_cell_click:
            self.on_cell_click(r, c)

    def _right_click(self, event) -> None:
        """右键：先判敌人，再判格子。

        顺序和左键相反是有意的——左键点敌人圆点想「看这只」，右键点
        敌人想「给这只加状态」。如果先判格子，圆点压在格子上时右键
        永远只能拿到格子。
        """
        enemy = self._enemy_at(event.x, event.y)
        if enemy is not None:
            if self.on_cell_right_click:
                self.on_cell_right_click(-1, -1, enemy)
            return
        if not self._r.game_map:
            return
        r, c = self._tile_at_event(event)
        if r < 0:
            return
        if self.on_cell_right_click:
            self.on_cell_right_click(r, c, None)

    def _enemy_at(self, x: float, y: float):
        """命中的敌人 dict，没有则 None。"""
        for cx, cy, hit, idx in self._enemy_hit:
            if (x - cx) ** 2 + (y - cy) ** 2 <= hit ** 2:
                if 0 <= idx < len(self._r.frame_enemies):
                    return self._r.frame_enemies[idx]
                return None
        return None

    def _motion(self, event) -> None:
        if not self._r.game_map:
            return
        r, c = self._tile_at_event(event)
        new_hover = (r, c) if r >= 0 else None

        new_enemy = None
        for cx, cy, hit, idx in self._enemy_hit:
            if (event.x - cx) ** 2 + (event.y - cy) ** 2 <= hit ** 2:
                new_enemy = idx
                break
        new_spawn = None
        if new_hover and new_hover in (self._r.spawn_points or {}):
            new_spawn = new_hover

        changed = (new_hover != self._r.hover or
                   new_enemy != self._r.hover_enemy or
                   new_spawn != self._r.hover_spawn)
        self._r.hover = new_hover
        self._r.hover_enemy = new_enemy
        self._r.hover_spawn = new_spawn
        if changed:
            self._paint()
            if self.on_hover:
                t = self._r.game_map.tile_at(*new_hover) if new_hover else None
                self.on_hover(t)
            if self.on_object_hover:
                if new_enemy is not None and 0 <= new_enemy < len(
                        self._r.frame_enemies):
                    self.on_object_hover("enemy",
                                         self._r.frame_enemies[new_enemy])
                elif new_hover:
                    self.on_object_hover("tile", new_hover)
                else:
                    self.on_object_hover(None, None)

    def _leave(self, _event) -> None:
        if self._r.hover or self._r.hover_enemy is not None or self._r.hover_spawn:
            self._r.hover = None
            self._r.hover_enemy = None
            self._r.hover_spawn = None
            self.redraw()
            if self.on_hover:
                self.on_hover(None)
            if self.on_object_hover:
                self.on_object_hover(None, None)

    def _dim(self, color: str, t: float) -> str:
        return color


def _fmt_big(v) -> str:
    try:
        v = float(v)
    except (TypeError, ValueError):
        return str(v)
    if v >= 10000:
        return "%.1f 万" % (v / 10000.0)
    return "%d" % int(v)


def _fmt_num(v) -> str:
    """数值显示：整数不补小数点，有小数才留一位。"""
    try:
        f = float(v)
    except (TypeError, ValueError):
        return str(v)
    if abs(f - round(f)) < 1e-9:
        return "%d" % int(round(f))
    return "%.1f" % f


def _fmt_rc(row: float, col: float, gm) -> str:
    """把连续格坐标格式化成「M4 (3.43, 7.00)」这种形式。

    游戏里给玩家看的编号是 行->字母、列->数字（走 ``coord_label``），
    而寻路运算内部用的是 (row, col) 浮点。两个都给，并统一保留两位
    小数——PRTS 的偏移量就精确到小数点后两位，多给位数反而不好对。
    """
    r = int(round(row))
    c = int(round(col))
    name = ""
    if gm is not None:
        try:
            name = coord_label(r, c, gm.height)
        except Exception:
            name = ""
    tag = ("%s " % name) if name else ""
    return "%s(%.2f, %.2f)" % (tag, row, col)
