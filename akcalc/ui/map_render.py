# -*- coding: utf-8 -*-
"""PIL 离屏渲染后端。

为什么不用 Canvas item
----------------------
旧版每帧 ``delete("all")`` 再重建 500+ 个 item，实测单帧 30 ms 且随路线数
线性增长，20fps 下界面直接卡死。改成「PIL 合成整帧 -> 单个 PhotoImage」
后，一帧只需一次 itemconfig，实测 110 fps，画布 item 从 538 降到 1。

分层策略
--------
* ``_base``：地形 + 路线 + 出怪点，**只在切图/切换显示项时重建**（含 2x
  超采样缩小，边缘抗锯齿）。
* 每帧：``_base.copy()`` -> 叠敌人精灵 -> 叠 tooltip -> 转 PhotoImage。

坐标约定与数据层一致：row 自下往上（第 1 行在最下面），col 自左往右。
"""
from __future__ import annotations

import math
import os
from typing import Dict, List, Optional, Sequence, Tuple

from PIL import Image, ImageDraw, ImageFilter, ImageFont

from ..core.coords import col_letter
from ..core.models import GameMap, Route, Tile

Coord = Tuple[int, int]

# ---------------------------------------------------------------- 配色（比旧版更分明）

BG = (23, 27, 34)
TILE_EDGE = (12, 15, 20)

LOWLAND = (58, 72, 94)
LOWLAND_HI = (74, 90, 116)
HIGHLAND = (104, 122, 150)
HIGHLAND_HI = (128, 148, 178)
DEEPWATER = (26, 62, 84)
DEEPWATER_HI = (36, 82, 108)
WALL = (118, 96, 62)
WALL_HI = (146, 120, 80)
ROAD = (70, 84, 112)
NONE_FILL = (16, 19, 24)
HOLE = (8, 10, 14)

SPAWN = (214, 68, 56)
GOAL = (56, 132, 224)      # 蓝门：敌人走向的终点
ROUTE = (92, 176, 255)
TEXT = (238, 242, 247)
TEXT_DIM = (154, 165, 180)
COORD = (120, 132, 154)
COORD_HL = (245, 197, 66)
GOLD = (245, 197, 66)
#: 「本关出怪」里被点中的那一行在地图上的高亮色。
#: 用青色而不是金色——金色已经被悬停占用，两者同时出现要能分清。
HILITE_RING = (64, 232, 214)
HILITE_GLOW = (48, 200, 190)

#: 机制机关配色。五类各一个主色，色相刻意拉开，远看能分得清：
#: 传送=青紫（与高亮环的青色接近但要更紫，避免混淆）、危险=橙红、
#: 增益=翠绿、阻挡=土黄、特殊=洋红。
MECH_COLORS = {
    "portal": (150, 110, 240),
    "trap": (236, 122, 58),
    "buff": (72, 196, 130),
    "wall": (176, 148, 84),
    "special": (214, 86, 190),
}

ROUTE_PALETTE = [
    (92, 176, 255), (240, 149, 74), (63, 209, 139), (240, 96, 90),
    (176, 125, 224), (46, 196, 182), (245, 197, 66), (74, 144, 226),
    (240, 106, 168), (22, 199, 154),
]

#: 超采样倍率：2x 已足够消除锯齿，3x 收益递减而内存翻倍
SS = 2

# ---------------------------------------------------------------- 字体

_FONT_CACHE: Dict[Tuple[str, int], ImageFont.FreeTypeFont] = {}


def _font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    """取中文字体；带缓存，缺字体时退回默认位图字体。"""
    key = ("b" if bold else "r", size)
    f = _FONT_CACHE.get(key)
    if f:
        return f
    names = ("msyhbd.ttc", "msyh.ttc") if bold else ("msyh.ttc", "msyhbd.ttc")
    for nm in names:
        p = os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts", nm)
        if os.path.isfile(p):
            try:
                f = ImageFont.truetype(p, size)
                _FONT_CACHE[key] = f
                return f
            except Exception:
                continue
    f = ImageFont.load_default()
    _FONT_CACHE[key] = f
    return f


def _norm_height(v) -> str:
    """heightType 归一化成字符串枚举。

    早期关卡的 ``heightType`` 是**整数**（0 = LOWLAND，1 = HIGHLAND），
    全库合计 9066 格（4898 高台 + 4168 地面）。老代码直接 ``.upper()``，
    碰到整数就抛 AttributeError，整张图渲染不出来 —— 这个坑不只影响
    机关图层，任何打开这些关卡的操作都会炸。
    """
    if isinstance(v, bool):
        return "LOWLAND"
    if isinstance(v, int):
        return "HIGHLAND" if v == 1 else "LOWLAND"
    s = str(v or "").strip().upper()
    if s.isdigit():
        return "HIGHLAND" if int(s) == 1 else "LOWLAND"
    return s or "LOWLAND"


def _rgba(c, a=255):
    return (c[0], c[1], c[2], a)


def _dashed(d, x0, y0, x1, y1, color, width: int = 2,
            dash: float = 6.0, gap: float = 5.0) -> None:
    """画虚线。PIL 没有虚线原语，这里按步长切段。"""
    dx, dy = x1 - x0, y1 - y0
    length = math.hypot(dx, dy)
    if length <= 0.001:
        return
    ux, uy = dx / length, dy / length
    pos = 0.0
    while pos < length:
        end = min(pos + dash, length)
        d.line([(x0 + ux * pos, y0 + uy * pos),
                (x0 + ux * end, y0 + uy * end)], fill=color, width=width)
        pos = end + gap


#: 机关字形：用一两字的简写而不是图标，打包时不必带图片资源。
#: 值为 (字形, 相对格子边长的字号比例)。
_MECH_GLYPH: Dict[str, Tuple[str, float]] = {
    "tile_telin": ("入", 0.44),
    "tile_telout": ("出", 0.44),
    "tile_rabbithole_in_1": ("兔", 0.42),
    "tile_rabbithole_out_1": ("兔", 0.42),
    "tile_rabbithole_out_2": ("兔", 0.42),
    "tile_stairs": ("阶", 0.42),
    "tile_hole": ("坑", 0.42),
    "tile_volcano": ("火", 0.44),
    "tile_volcano_emp": ("火", 0.44),
    "tile_corrosion": ("腐", 0.42),
    "tile_smog": ("雾", 0.42),
    "tile_toxic": ("毒", 0.42),
    "tile_toxicwall": ("毒", 0.42),
    "tile_toxicroad": ("毒", 0.42),
    "tile_toxichill": ("毒", 0.42),
    "tile_deepwater": ("深", 0.42),
    "tile_deepsea": ("海", 0.42),
    "tile_mire": ("沼", 0.42),
    "tile_quicksand": ("沙", 0.42),
    "tile_icetur": ("冰", 0.42),
    "tile_icestr": ("冰", 0.42),
    "tile_icetur_road": ("冰", 0.42),
    "tile_ice_road": ("冰", 0.42),
    "tile_frost": ("霜", 0.42),
    "tile_burn": ("燃", 0.42),
    "tile_infection": ("感", 0.42),
    "tile_infection_dqq": ("感", 0.42),
    "tile_creep": ("毯", 0.42),
    "tile_creepf": ("毯", 0.42),
    "tile_forbidden": ("", 0.0),        # 不可通行格子已经画了大叉，不再叠字
    "tile_passable_wall": ("墙", 0.40),
    "tile_passable_wall_only_stops_fly": ("墙", 0.40),
    "tile_wooden_wall": ("木", 0.42),
    "tile_alchemy_wall": ("墙", 0.40),
    "tile_fence": ("", 0.0),
    "tile_fence_bound": ("", 0.0),
    "tile_healing": ("愈", 0.44),
    "tile_defup": ("防", 0.42),
    "tile_defbreak": ("破", 0.42),
    "tile_atkup": ("攻", 0.42),
    "tile_spup": ("技", 0.42),
    "tile_reed": ("芦", 0.42),
    "tile_reedw": ("芦", 0.42),
    "tile_reedf": ("芦", 0.42),
    "tile_grass": ("草", 0.42),
    "tile_sleep_road": ("眠", 0.42),
    "tile_sleep_wall": ("眠", 0.42),
    "tile_gazebo": ("留", 0.44),
    "tile_grvtybtn": ("重", 0.44),
    "tile_yinyang_switch": ("阴", 0.42),
    "tile_yinyang_road": ("阴", 0.42),
    "tile_yinyang_wall": ("阴", 0.42),
    "tile_magic_circle": ("阵", 0.42),
    "tile_magic_circle_h": ("阵", 0.42),
    "tile_balloon": ("球", 0.42),
    "tile_balloon_fbd": ("球", 0.42),
    "tile_acshop": ("店", 0.42),
    "tile_cnvfuse": ("带", 0.42),
    "tile_cnvfuse_fbd": ("带", 0.42),
    "tile_football": ("球", 0.42),
    "tile_bigforce": ("弹", 0.42),
    "tile_character": ("位", 0.38),
    "tile_characterf": ("位", 0.38),
    "tile_replace_wall": ("换", 0.38),
    "tile_replace_road": ("换", 0.38),
    "tile_rcm_crate": ("箱", 0.40),
    "tile_rcm_operator": ("位", 0.38),
    "tile_empty": ("", 0.0),
}

#: 机关提取结果按 (id(game_map)) 缓存一层：静态层重建时不必每次重扫
#: 整张地图。用 id() 作键有极小概率撞上已回收对象——所以同时存一份
#: game_map 的弱引用校验。
_MECH_CACHE: Dict[int, Tuple[object, list, list]] = {}


def _mech_extract(gm: GameMap):
    """带缓存的 ``mechanisms.extract``。"""
    if gm is None:
        return []
    key = id(gm)
    hit = _MECH_CACHE.get(key)
    if hit is not None and hit[0] is gm:
        return hit[1]
    try:
        from ..core.mechanisms import extract as _ex
        mechs = _ex(gm)
    except Exception:
        mechs = []
    _MECH_CACHE[key] = (gm, mechs, [])
    if len(_MECH_CACHE) > 24:      # 别无限涨：地图切换几十次后清一次
        _MECH_CACHE.clear()
        _MECH_CACHE[key] = (gm, mechs, [])
    return mechs


def _mech_portals(mechs):
    """带缓存的 ``mechanisms.portals``。"""
    if not mechs:
        return []
    key = id(mechs)
    # 用列表本身的 id 做键不稳（每次都可能新建），所以改用「数量签名」
    sig = (len(mechs), sum(m.row * 31 + m.col for m in mechs))
    hit = _PORTAL_CACHE.get(sig)
    if hit is not None:
        return hit
    try:
        from ..core.mechanisms import portals as _po
        pairs = _po(mechs)
    except Exception:
        pairs = []
    if len(_PORTAL_CACHE) > 32:
        _PORTAL_CACHE.clear()
    _PORTAL_CACHE[sig] = pairs
    return pairs


_PORTAL_CACHE: Dict[Tuple[int, int], list] = {}


# ---------------------------------------------------------------- 精灵

_SPRITE_CACHE: Dict[Tuple, Image.Image] = {}


def _name_color(name: str):
    """把敌人名映射成稳定的 RGB 颜色（同名同色，便于区分兵种）。"""
    pal = ROUTE_PALETTE
    h = 0
    for ch in str(name):
        h = (h * 131 + ord(ch)) & 0x7FFFFFFF
    return pal[h % len(pal)]


def _dot_sprite(color, r: float, ring=True) -> Image.Image:
    """预渲染带柔边的圆形敌人标记（4x 超采样后缩小）。"""
    key = (color, round(r, 1), ring)
    sp = _SPRITE_CACHE.get(key)
    if sp:
        return sp
    s = 4
    # 画布要留出 1.6 倍半径的外发光空间，否则 glow 被裁成硬边
    rad = int(r * s * 1.7) + 6
    im = Image.new("RGBA", (rad * 2, rad * 2), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    cx = cy = rad
    # 外发光
    glow = Image.new("RGBA", im.size, (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    gd.ellipse([cx - r*s*1.5, cy - r*s*1.5, cx + r*s*1.5, cy + r*s*1.5],
               fill=_rgba(color, 70))
    glow = glow.filter(ImageFilter.GaussianBlur(r * s * 0.5))
    im.alpha_composite(glow)
    # 主体 + 白边
    if ring:
        d.ellipse([cx - r*s - 2, cy - r*s - 2, cx + r*s + 2, cy + r*s + 2],
                  fill=_rgba((255, 255, 255), 235))
    d.ellipse([cx - r*s, cy - r*s, cx + r*s, cy + r*s], fill=_rgba(color))
    # 高光
    d.ellipse([cx - r*s*0.42, cy - r*s*0.60, cx + r*s*0.06, cy - r*s*0.12],
              fill=(255, 255, 255, 120))
    # 缩到 1x：画布边长 rad*2 -> 实际显示时的直径（r 的 3.4 倍余量）
    side = max(8, int(round(rad * 2 / s * 1.0)))
    sp = im.resize((side, side), Image.LANCZOS)
    _SPRITE_CACHE[key] = sp
    return sp


class MapRenderer:
    """把地图状态渲染成 PIL 图像。纯逻辑，不依赖 tkinter。"""

    def __init__(self) -> None:
        self.game_map: Optional[GameMap] = None
        self.analyses: List = []
        self.width = 0
        self.height = 0
        self.cell = 48
        self.pad_l = 34
        self.pad_t = 26
        self.pad_r = 34
        self.pad_b = 30
        self.origin_x = 0
        self.origin_y = 0
        self.show_ground = True
        self.show_fly = False
        self.show_routes = True
        self.show_cost = False
        self.show_dots = True
        #: 是否显示地图机关（传送门 / 火山 / 留声机 ...）。默认开 ——
        #: 寻路分析不知道传送门在哪就完全看不出路线为什么突然跳位。
        self.show_mech = True
        self.selected: Optional[Coord] = None
        self.hover: Optional[Coord] = None
        self.highlight_route: Optional[int] = None
        #: 只显示这一条路线（点击「本关出怪」里某一条后进入）。此时不播
        #: 动画，只画一条静态折线，并且**才**显示罚站时长。
        self.isolate_route: Optional[int] = None
        self.spawn_points: Dict[Coord, List[tuple]] = {}
        self.hover_spawn: Optional[Coord] = None
        self.hover_enemy: Optional[int] = None
        self.frame_enemies: List[dict] = []
        #: 被「本关出怪」表格点中、需要在地图上圈出来的敌人。
        #: 存的是 ``(enemy_id, route_index)``：单靠 enemy_id 不够——
        #: 同一只敌人可能有多条撤离路线，用户点的是**某一行**，所以
        #: 路线也要匹配。为 None 表示没有高亮。
        self.highlight_enemy: Optional[Tuple[str, int]] = None
        #: 地图翻转。不同关卡在游戏内的朝向与解包数据并不总是一致，
        #: 因此给用户一个开关自己翻，而不是在数据层硬改（见 maps.parse_level
        #: 里那段关于 reversed(matrix) 的说明）。
        self.flip_v = False          # 上下翻转
        self.flip_h = False          # 左右翻转
        #: 缩放：1.0 = 自动铺满，>1 放大。配合 pan_x/pan_y 平移。
        self.zoom = 1.0
        self.pan_x = 0.0
        self.pan_y = 0.0
        self._base: Optional[Image.Image] = None
        self._base_key = None

    # ------------------------------------------------------------ 几何

    def set_map(self, game_map: Optional[GameMap], analyses=None) -> None:
        self.game_map = game_map
        self.analyses = list(analyses or [])
        self.invalidate()

    def invalidate(self) -> None:
        """标记静态层需要重建。"""
        self._base = None
        self._base_key = None

    def disp_rc(self, row: float, col: float):
        """数据格坐标 -> 显示格坐标（应用翻转）。

        这是一个**对合**运算：再算一次就回到原值，所以像素反查坐标时
        可以复用同一个函数。
        """
        gm = self.game_map
        r, c = row, col
        if gm:
            if self.flip_v:
                r = (gm.height - 1) - r
            if self.flip_h:
                c = (gm.width - 1) - c
        return r, c

    def reset_view(self) -> None:
        """回到默认视图：不翻转、自动铺满、不偏移。"""
        self.flip_v = False
        self.flip_h = False
        self.zoom = 1.0
        self.pan_x = 0.0
        self.pan_y = 0.0
        self.invalidate()

    def set_zoom(self, zoom: float) -> None:
        self.zoom = max(1.0, min(6.0, float(zoom)))

    def _clamp_pan(self) -> None:
        """把平移限制住，别让整张图被拖出画布外看不见。"""
        gm = self.game_map
        if not gm or not gm.width or not gm.height:
            return
        avail_w = self.width - self.pad_l - self.pad_r
        avail_h = self.height - self.pad_t - self.pad_b
        gw = self.cell * gm.width
        gh = self.cell * gm.height
        # 允许的偏移范围：图比视口大时最多滑到边缘对齐；比视口小时只能微调
        if gw <= avail_w:
            self.pan_x = 0.0
        else:
            lo = avail_w - gw - (avail_w - gw) / 2.0
            hi = (gw - avail_w) / 2.0
            self.pan_x = max(lo, min(hi, self.pan_x))
        if gh <= avail_h:
            self.pan_y = 0.0
        else:
            lo = avail_h - gh - (avail_h - gh) / 2.0
            hi = (gh - avail_h) / 2.0
            self.pan_y = max(lo, min(hi, self.pan_y))

    def fit(self, w: int, h: int) -> None:
        """按画布尺寸算格子大小与原点，结果尽量维持正方形格子。"""
        self.width, self.height = max(1, w), max(1, h)
        gm = self.game_map
        if not gm or not gm.width or not gm.height:
            return
        avail_w = self.width - self.pad_l - self.pad_r
        avail_h = self.height - self.pad_t - self.pad_b
        cell = min(avail_w / gm.width, avail_h / gm.height)
        # 放大：最小格宽 14px 是拖拽/点击的可操作下限
        cell = max(14.0, cell * max(1.0, self.zoom))
        self.cell = int(cell)
        gw = self.cell * gm.width
        gh = self.cell * gm.height
        # 注意顺序：_clamp_pan 依赖 self.cell，必须在 cell 定下来之后再调
        self._clamp_pan()
        self.origin_x = self.pad_l + int((avail_w - gw) / 2) + int(self.pan_x)
        self.origin_y = self.pad_t + int((avail_h - gh) / 2) + int(self.pan_y)

    def tile_xy(self, row: float, col: float) -> Tuple[float, float]:
        """格坐标 -> 像素中心点。

        注：row 0 是**数据上的最上面**一行（与 routes.tile_to_pixel 及关卡
        JSON 一致）。若用户打开了翻转开关，这里会先过一遍 disp_rc，
        因此所有绘制（地块、路线、出怪点、敌人圆点）都会一起翻转。
        """
        dr, dc = self.disp_rc(row, col)
        x = self.origin_x + (dc + 0.5) * self.cell
        y = self.origin_y + (dr + 0.5) * self.cell
        return x, y

    def pixel_tile(self, x: float, y: float) -> Tuple[int, int]:
        """像素 -> 数据格坐标（未翻转的 row/col）。"""
        gm = self.game_map
        if not gm:
            return -1, -1
        col = int((x - self.origin_x) // self.cell)
        row = int((y - self.origin_y) // self.cell)
        if 0 <= row < gm.height and 0 <= col < gm.width:
            # disp_rc 是对合的，再算一次就把显示格换回数据格
            r2, c2 = self.disp_rc(row, col)
            return int(r2), int(c2)
        return -1, -1

    # ------------------------------------------------------------ 渲染

    def render(self, enemies: Optional[Sequence[dict]] = None) -> Image.Image:
        """渲染一整帧。静态层有缓存，只在必要时重建。"""
        if enemies is not None:
            self.frame_enemies = list(enemies)
        # 注意：不要把 hover / selected / frame_enemies 放进 key。
        # 它们画在动态层，放进来会导致鼠标每动一格就重建静态层（约 60ms），
        # 播放与悬停都会一顿一顿的。highlight_route 会改变整条路线配色，
        # 必须留在 key 里。
        key = (id(self.game_map), self.width, self.height, self.cell,
               self.show_ground, self.show_fly, self.show_routes, self.show_cost,
               self.show_dots, self.highlight_route, self.isolate_route,
               self.show_mech,
               self.flip_v, self.flip_h, self.origin_x, self.origin_y,
               len(self.analyses), tuple(sorted(self.spawn_points.keys())),
               # 隔离视图下高亮标记画在静态层（那张图没有敌人圆点），
               # 所以必须进 key，否则点了表格行地图上不会有反应。
               self.highlight_enemy if self.isolate_route is not None else None)
        if self._base is None or key != self._base_key:
            self._base = self._build_base()
            self._base_key = key
        im = self._base.copy()
        self._draw_enemies(im)
        self._draw_hover_layer(im)
        return im

    # -------------------------------------------------- 静态层

    def _build_base(self) -> Image.Image:
        w, h = self.width, self.height
        ss = SS
        im = Image.new("RGB", (w * ss, h * ss), BG)
        gm = self.game_map
        if not gm:
            im = im.resize((w, h), Image.LANCZOS)
            dd = ImageDraw.Draw(im)
            dd.text((w // 2, h // 2), "请选择关卡后加载地图",
                    font=_font(14), fill=_rgba(TEXT_DIM), anchor="mm")
            return im

        self._draw_tiles(ImageDraw.Draw(im), gm, ss)
        # 机制机关（传送门 / 火山 / 留声机 ...）画在底图上、路线之下。
        # 它们是「地形自带的东西」，用半透明色块 + 符号表示，不能像路线
        # 那样整块盖住格子，否则地图会看不清。这里直接画在底图层，
        # 天然不透明，也就不需要 alpha 合成。
        self._draw_mechanisms(im, gm, ss)
        # 路线 / 出怪点 / 坐标带半透明，必须画在覆盖层上再整体合成，
        # 否则半透明像素只是把 alpha 写进底图，Tk 贴图时会与窗口背景
        # 混色，整张图变灰变脏（旧版就是这个毛病）。
        ov = Image.new("RGBA", im.size, (0, 0, 0, 0))
        od = ImageDraw.Draw(ov)
        self._draw_coords(od, gm, ss)
        self._draw_routes(od, gm, ss)
        self._draw_spawn_points(im, ov, od, gm, ss)
        self._draw_doors(od, gm, ss)   # 真实红门 / 蓝门
        # 传送门的配对连线要压在门框之上，否则会被其他覆盖物切断
        self._draw_portal_links(od, gm, ss)
        # 罚站时长只在隔离视图里画，且必须压在最上层，否则会被门框/出怪点盖住
        self._draw_route_marks(od, gm, ss)
        # 隔离视图不放动画，没有敌人圆点可套环，于是把高亮做成
        # 「路线起点处的呼吸环 + 指向路线的箭头」，让用户依然能一眼
        # 定位到刚才点的那一行是哪条线。
        self._draw_isolate_highlight(od, gm, ss)
        out = Image.alpha_composite(im.convert("RGBA"), ov)
        return out.resize((w, h), Image.LANCZOS)

    def _tile_fill(self, t: Optional[Tile]):
        """地块底色与高光色。"""
        if t is None:
            return NONE_FILL, NONE_FILL
        ht = _norm_height(t.height_type)
        if ht == "HIGHLAND":
            return HIGHLAND, HIGHLAND_HI
        if ht == "DEEPWATER":
            return DEEPWATER, DEEPWATER_HI
        if ht == "WALL":
            return WALL, WALL_HI
        if ht == "NONE":
            return HOLE, HOLE
        return LOWLAND, LOWLAND_HI

    def _draw_tiles(self, d, gm: GameMap, ss: int) -> None:
        cell = self.cell * ss
        ox, oy = self.origin_x * ss, self.origin_y * ss
        gap = max(1, int(ss * 1.5))
        for r in range(gm.height):
            for c in range(gm.width):
                t = gm.tile_at(r, c)
                if t is not None and not self.show_ground:
                    ht = _norm_height(t.height_type)
                    if ht in ("LOWLAND", "DEEPWATER"):
                        continue
                # 翻转：数据格 (r,c) 画到显示位置 (dr,dc)
                dr, dc = self.disp_rc(r, c)
                x0 = ox + dc * cell
                y0 = oy + dr * cell
                x1, y1 = x0 + cell - gap, y0 + cell - gap
                fill, hi = self._tile_fill(t)
                rad = max(2, int(cell * 0.10))
                d.rounded_rectangle([x0, y0, x1, y1], radius=rad,
                                    fill=_rgba(fill), outline=_rgba(TILE_EDGE),
                                    width=max(1, ss // 2))
                # 顶部高光条，做出「凸起」的厚度感
                band = max(1, int(cell * 0.14))
                d.rounded_rectangle([x0 + gap, y0 + gap, x1 - gap, y0 + band],
                                    radius=max(1, int(cell * 0.06)),
                                    fill=_rgba(hi, 150))
                ht = _norm_height(t.height_type) if t else ""
                # 高台：底部投影
                if ht == "HIGHLAND":
                    d.rectangle([x0 + gap, y1 - band, x1 - gap, y1],
                                fill=_rgba((0, 0, 0), 60))
                # 深水：波纹
                elif ht == "DEEPWATER":
                    wy = y0 + cell * 0.62
                    d.line([x0 + cell*0.18, wy, x0 + cell*0.44, wy],
                           fill=_rgba((120, 190, 220), 110), width=max(1, ss))
                    d.line([x0 + cell*0.56, wy + cell*0.14,
                            x0 + cell*0.82, wy + cell*0.14],
                           fill=_rgba((120, 190, 220), 110), width=max(1, ss))
                # 不可通行：叉
                if t is not None and not t.passable_ground and not t.passable_fly:
                    m = cell * 0.26
                    d.line([x0+m, y0+m, x1-m, y1-m], fill=_rgba((220, 120, 110), 170),
                           width=max(1, ss))
                    d.line([x1-m, y0+m, x0+m, y1-m], fill=_rgba((220, 120, 110), 170),
                           width=max(1, ss))
                if self.show_cost:
                    self._draw_cost(d, gm, r, c, x0, y0, cell, ss)
        self._draw_grid_labels(d, gm, ss)

    def _draw_cost(self, d, gm, r, c, x0, y0, cell, ss):
        t = gm.tile_at(r, c)
        if not t:
            return
        cost = c + 1
        d.text((x0 + cell * 0.5, y0 + cell * 0.5), str(cost),
               font=_font(max(8, int(cell / ss * 0.34))),
               fill=_rgba((255, 255, 255), 150), anchor="mm")
        return

    def _draw_grid_labels(self, d, gm, ss):
        """我方部署格用淡点标出可部署位置。"""
        cell = self.cell * ss
        ox, oy = self.origin_x * ss, self.origin_y * ss
        for r in range(gm.height):
            for c in range(gm.width):
                t = gm.tile_at(r, c)
                if not t:
                    continue
                if t.buildable_melee or t.buildable_ranged:
                    dr, dc = self.disp_rc(r, c)
                    x = ox + (dc + 0.5) * cell
                    y = oy + (dr + 0.5) * cell
                    rr = max(1.0, cell * 0.045)
                    d.ellipse([x - rr, y - rr, x + rr, y + rr],
                              fill=_rgba((255, 255, 255), 55))

    # -------------------------------------------------- 路线

    def _route_pixels(self, route: Route) -> List[Tuple[float, float]]:
        """路线的像素折线。瞬移段用 nan 打断。

        **为什么要用 analyze 的路径而不是检查点连线**

        关卡数据里 ``routes[].checkpoints`` **不是**敌人的实际行走轨迹，它
        只是「路径点指令」序列：每条指令只说「去 (r,c) 格」「停 N 秒」
        「进传送」。两个相邻指令之间敌人**怎么走过去是寻路算出来的**
        （PRTS〈作战机制·行动的基本原理〉：敌人用 SPFA 求最短路，遇到
        障碍物按寻路代价绕行）。

        旧实现直接把这些检查点连成线，于是画出来的是「两点之间的直线」，
        既会穿墙、也不反映绕行，更没有和寻路结果保持一致——这就是
        「又弯曲又丑还不符合实际情况」的根因（弯是样条、丑是连错）。

        现在优先用 ``RouteAnalysis`` 里 ``segments[].path`` 的**逐格真实
        路径**。只有拿不到分析结果时才退回检查点连线（并在没有检查点时
        退到 start->end）。
        """
        ra = self._analysis_for(route)
        if ra is not None and ra.segments:
            pts: List[Tuple[float, float]] = []
            for seg in ra.segments:
                path = list(seg.path or [])
                if not path:
                    continue
                if seg.teleport:
                    # 瞬移：断开，不画连线
                    if pts:
                        pts.append((float("nan"), float("nan")))
                for (r, c) in path:
                    pts.append(self.tile_xy(r, c))
            if len(pts) >= 2:
                return pts

        # ---- 兜底：没有分析结果，只能连检查点
        pts = []
        for cp in route.checkpoints:
            if not cp.has_position:
                continue
            if cp.is_teleport and pts:
                pts.append((float("nan"), float("nan")))
            pts.append(self.tile_xy(cp.row, cp.col))
        if not pts:
            pts.append(self.tile_xy(route.start[0], route.start[1]))
            pts.append(self.tile_xy(route.end[0], route.end[1]))
        return pts

    def _analysis_for(self, route: Route):
        """按 ``route.index`` 找到对应的 ``RouteAnalysis``；找不到返回 None。"""
        idx = getattr(route, "index", None)
        if idx is None or not self.analyses:
            return None
        for ra in self.analyses:
            if getattr(ra, "route_index", None) == idx:
                return ra
        return None

    def _smooth(self, pts: List[Tuple[float, float]],
                seg: int = 8) -> List[List[Tuple[float, float]]]:
        """折线分段；遇 nan 断开。

        **历史**：这里原本是一个 Catmull-Rom 样条（用 ``seg`` 个子采样点把
        折线插成曲线）。对直角走位完全是错的——敌人是沿格子中心逐格
        直线移动的，样条会在每个转弯处「抄近路」斜切过墙角，画出来的
        轨迹既不直也不符合实际路径，玩家拿来对位会被误导。

        现在直接返回原始折线点。保持函数名与签名（``_draw_routes`` /
        隔离视图 / 导出都依赖它），只是不再加工坐标。

        各段之间依然用 ``nan`` 断开（传送门这类瞬移不连线）。
        """
        segs: List[List[Tuple[float, float]]] = []
        cur: List[Tuple[float, float]] = []
        for p in pts:
            if p[0] != p[0]:           # nan -> 断开
                if len(cur) > 1:
                    segs.append(cur)
                cur = []
                continue
            cur.append(p)
        if len(cur) > 1:
            segs.append(cur)
        return segs

    def _draw_routes(self, d, gm: GameMap, ss: int) -> None:
        """画敌人路线。

        规则（用户要求）：
        * **没选中任何敌人 → 一条路线都不画**。整张图铺满折线时根本
          看不出地形和机关，可读性反而低于不画；
        * 选中了（点了右侧「本关出怪」里的一行，或者从图例里选了
          ``highlight_route``）→ **只画那一条**，其余全不画。

        以前是「全部画 + 选中的调亮」，路线一多就糊成一团。现在把
        「选中的那条」当成唯一可见对象，语义更干净。
        """
        if not self.show_routes or not gm.routes:
            return
        # 隔离视图（点中出怪表某一行）优先，只画那一条
        if self._draw_isolate_route(d, gm, ss):
            return
        # 没有隔离、也没有高亮 → 不画任何路线，保持地图干净
        if self.highlight_route is None:
            return
        if not (0 <= self.highlight_route < len(gm.routes)):
            return
        i = self.highlight_route
        route = gm.routes[i]
        color = ROUTE_PALETTE[i % len(ROUTE_PALETTE)]
        segs = self._smooth(self._route_pixels(route))
        lw = max(2, int(ss * 2.6))
        for s in segs:
            if len(s) < 2:
                continue
            pts = [(x * ss, y * ss) for x, y in s]
            d.line(pts, fill=_rgba(color, 70), width=lw + max(3, ss * 4),
                   joint="curve")
            d.line(pts, fill=_rgba(color, 255), width=lw, joint="curve")
            if len(pts) >= 2:
                for k in range(int(len(pts) * 0.35), len(pts) - 1,
                               max(6, int(len(pts) * 0.28))):
                    self._arrow(d, pts[k], pts[k + 1], color, 255, ss)

    def _draw_route_marks(self, d, gm: GameMap, ss: int) -> None:
        """罚站时长提示。

        **只在「点击本关出怪里的一条」进入的隔离视图里画**（isolate_route
        不为 None）。用户明确要求：「无需做地图上的显示」——大图上不
        显示罚站/检查点标记；只有单独看某一条路线时，才需要知道它在
        哪一格停多久。
        """
        if self.isolate_route is None or not gm.routes:
            return
        if not (0 <= self.isolate_route < len(gm.routes)):
            return
        route = gm.routes[self.isolate_route]
        cell = self.cell * ss
        if self.cell < 14:
            return
        fs = max(7, int(self.cell * ss * 0.22))

        # 罚站：WAIT 检查点不带坐标，停驻落在「上一个有坐标的节点」上
        # （与 routes.analyze_route 的 nodes[-1].wait 累加语义一致）。
        waits = {}   # (row, col) -> 秒
        last = (int(round(route.start[0])), int(round(route.start[1])))
        for cp in route.checkpoints:
            if cp.has_position:
                last = (int(round(cp.row)), int(round(cp.col)))
            elif cp.is_wait:
                waits[last] = waits.get(last, 0.0) + cp.wait_time
        # 排序：瞬移落点先画，罚站标记后画，保证标记在上层
        for (r, c), secs in sorted(waits.items()):
            if secs <= 0:
                continue
            x, y = self.tile_xy(r, c)
            x, y = x * ss, y * ss
            rbox = max(3.0, cell * 0.13)
            # 沙漏色方块 = 原地停驻
            d.rectangle([x - rbox, y - rbox, x + rbox, y + rbox],
                        fill=_rgba((245, 197, 66), 235),
                        outline=_rgba((10, 12, 18), 255),
                        width=max(1, ss))
            txt = ("%.0fs" % secs) if abs(secs - round(secs)) < 0.05 \
                else ("%.1fs" % secs)
            # 底色衬一下，避免压在亮色地块上读不清
            try:
                tw = int(d.textlength(txt, font=_font(fs, True)))
            except Exception:
                tw = int(fs * 0.62 * len(txt))
            pad = max(2, int(ss * 2))
            tx = x + rbox + 3
            d.rounded_rectangle(
                [tx - pad, y - fs * 0.75 - pad,
                 tx + tw + pad, y + fs * 0.75 + pad],
                radius=max(2, int(ss * 2)),
                fill=_rgba((18, 22, 30), 230),
                outline=_rgba((245, 197, 66), 200), width=max(1, ss))
            d.text((tx, y), txt, font=_font(fs, True),
                   fill=_rgba((255, 214, 120)), anchor="lm")

    def _draw_isolate_route(self, d, gm: GameMap, ss: int) -> bool:
        """隔离视图：只画一条路线，不画其它路线。

        返回 True 表示已接管路线绘制（调用方的 _draw_routes 应跳过）。
        这里刻意画成「静态折线」而非动画轨迹——用户要求
        「仅显示线不播放敌人行动动画」。
        """
        if self.isolate_route is None or not gm.routes:
            return False
        if not (0 <= self.isolate_route < len(gm.routes)):
            return False
        route = gm.routes[self.isolate_route]
        color = ROUTE_PALETTE[self.isolate_route % len(ROUTE_PALETTE)]
        segs = self._smooth(self._route_pixels(route))
        lw = max(3, int(ss * 3.2))
        for s in segs:
            if len(s) < 2:
                continue
            pts = [(x * ss, y * ss) for x, y in s]
            d.line(pts, fill=_rgba(color, 90), width=lw + max(3, int(ss * 4)),
                   joint="curve")
            d.line(pts, fill=_rgba(color, 250), width=lw, joint="curve")
        # 起点/终点加重标记
        for (r, c), col in (((route.start[0], route.start[1]), SPAWN),
                            ((route.end[0], route.end[1]), GOAL)):
            x, y = self.tile_xy(r, c)
            rr = max(4.0, self.cell * 0.16)
            d.ellipse([x * ss - rr * ss, y * ss - rr * ss,
                       x * ss + rr * ss, y * ss + rr * ss],
                      fill=_rgba(col, 235), outline=_rgba((255, 255, 255), 240),
                      width=max(1, ss))
        return True

    def _draw_mechanisms(self, im: Image.Image, gm: GameMap, ss: int) -> None:
        """把地图机关（传送门 / 火山 / 留声机 ...）标到格子上。

        为什么不用覆盖层：机关的颜色需要「一看就知道是危险还是增益」，
        半透明叠在深色底图上会整体发灰，橙红和土黄几乎分不出来。这里
        直接画在不透明底图上，用较暗的实色块 + 亮色描边，既醒目又不会
        把格子压得看不见。

        符号用文字简写而不是图标：打包时不需要额外图片资源，字号随格子
        缩放，4K 下也不会糊。
        """
        if not getattr(self, "show_mech", True):
            return
        mechs = _mech_extract(gm)
        if not mechs:
            return
        cell = self.cell * ss
        d = ImageDraw.Draw(im, "RGBA")
        for m in mechs:
            # 纯墙体 / 空白格不画色块：底层的格子本身已经有土黄墙体色
            # 与红色大叉，再叠一层只会让整张图变脏（tile_forbidden 单张
            # 图就能有几百格）。它们列在图例里说明，但不上色。
            if m.cat == "wall":
                continue
            dr, dc = self.disp_rc(m.row, m.col)
            x0 = self.origin_x * ss + dc * cell
            y0 = self.origin_y * ss + dr * cell
            x1, y1 = x0 + cell, y0 + cell
            col = MECH_COLORS.get(m.cat, (160, 160, 160))
            glyph, size = _MECH_GLYPH.get(m.tile_key, ("", 0.0))
            if not glyph:
                glyph = m.name[:1]
                size = 0.42
            inset = cell * 0.16
            # 底色块：压暗一点，保证上面的字形读得清
            base = tuple(int(v * 0.42) for v in col)
            d.rounded_rectangle([x0 + inset, y0 + inset, x1 - inset, y1 - inset],
                                radius=max(2, int(cell * 0.16)),
                                fill=_rgba(base, 205),
                                outline=_rgba(col, 235),
                                width=max(1, int(ss * 1.6)))
            d.text(((x0 + x1) / 2, (y0 + y1) / 2), glyph,
                   font=_font(max(9, int(cell / ss * size))),
                   fill=_rgba(col, 255), anchor="mm")

    def _draw_portal_links(self, d, gm: GameMap, ss: int) -> None:
        """传送门入口 -> 出口的连线。

        解包数据里没有配对表（见 ``core/mechanisms.portals`` 的说明），
        所以可信度分两档：数量严格相等并用最小代价匹配出来的画实线，
        顺序凑出来的画虚线，并在中点标一个 ``?`` —— 让用户一眼知道
        哪个结论是有依据的、哪个只是猜的。
        """
        if not getattr(self, "show_mech", True):
            return
        mechs = _mech_extract(gm)
        if not mechs:
            return
        pairs = _mech_portals(mechs)
        if not pairs:
            return
        col = MECH_COLORS["portal"]
        for a, b, certain in pairs:
            ax, ay = self.tile_xy(a.row, a.col)
            bx, by = self.tile_xy(b.row, b.col)
            ax, ay, bx, by = ax * ss, ay * ss, bx * ss, by * ss
            width = max(2, int(ss * 1.8))
            if certain:
                d.line([(ax, ay), (bx, by)], fill=_rgba(col, 220), width=width)
            else:
                _dashed(d, ax, ay, bx, by, _rgba(col, 200), width)
            # 中点标记：入口端画空心圈，出口端画实心点
            r = self.cell * ss * 0.20
            d.ellipse([ax - r, ay - r, ax + r, ay + r],
                      outline=_rgba(col, 255), width=max(2, int(ss * 1.5)))
            r2 = r * 0.62
            d.ellipse([bx - r2, by - r2, bx + r2, by + r2],
                      fill=_rgba(col, 235))
            if not certain:
                mx, my = (ax + bx) / 2, (ay + by) / 2
                d.text((mx, my), "?", font=_font(max(9, int(ss * 7))),
                       fill=_rgba(GOLD, 235), anchor="mm")

    def _draw_doors(self, d, gm, ss: int) -> None:
        """按 mapData.tiles 的真实门格画红门 / 蓝门。

        红门 = tile_start（敌人从这里进场），蓝门 = tile_end（防守目标）。
        每条路线的起终点不再画框：一张图通常只有 2~5 个门，却有几十条
        路线，按路线画会把同一格反复覆盖，颜色互相打架还外溢到邻格。
        """
        for (r, c) in getattr(gm, "spawn_tiles", []) or []:
            x, y = self.tile_xy(r, c)
            self._tile_box(d, x * ss, y * ss, ss, SPAWN, inset=0.10)
        for (r, c) in getattr(gm, "goal_tiles", []) or []:
            x, y = self.tile_xy(r, c)
            self._tile_box(d, x * ss, y * ss, ss, GOAL, inset=0.10)

    def _tile_box(self, d, x: float, y: float, ss: int, color,
                  inset: float = 0.14) -> None:
        """在格子上画一个方框（出血点红框 / 蓝门蓝框）。

        用方框而不是圆点的原因：格子本身是方的，方框正好把「这一格是
        出生格 / 终点格」标出来，圆点看着像恰好站在格心的敌人。
        """
        cell = self.cell * ss
        h = cell * (0.5 - inset)
        w = max(2, int(round(ss * 1.6)))
        box = [x - h, y - h, x + h, y + h]
        # 外发光：先糊一层半透明粗边
        glow = max(w + int(ss * 3), 4)
        d.rectangle(box, outline=_rgba(color, 70), width=glow)
        d.rectangle(box, outline=_rgba(color, 245), width=w)
        # 四角加粗，远看更清楚
        cw = max(3, int(cell * 0.16))
        for cx, cy, dx, dy in ((box[0], box[1], 1, 1),
                               (box[2], box[1], -1, 1),
                               (box[0], box[3], 1, -1),
                               (box[2], box[3], -1, -1)):
            d.line([(cx, cy), (cx + cw * dx, cy)], fill=_rgba(color, 255),
                   width=max(2, int(ss * 2)))
            d.line([(cx, cy), (cx, cy + cw * dy)], fill=_rgba(color, 255),
                   width=max(2, int(ss * 2)))

    def _arrow(self, d, p, q, color, alpha, ss):
        dx, dy = q[0] - p[0], q[1] - p[1]
        L = math.hypot(dx, dy)
        if L < 1:
            return
        ux, uy = dx / L, dy / L
        sz = max(3.0, ss * 4.5)
        tip = (p[0] + ux * sz, p[1] + uy * sz)
        l = (p[0] - uy * sz * 0.55, p[1] + ux * sz * 0.55)
        r = (p[0] + uy * sz * 0.55, p[1] - ux * sz * 0.55)
        d.polygon([tip, l, r], fill=_rgba(color, alpha))

    def _badge(self, d, x, y, r, color, ss):
        d.ellipse([x - r, y - r, x + r, y + r],
                  fill=_rgba((12, 15, 20), 220), outline=_rgba(color, 255),
                  width=max(1, ss))
        d.ellipse([x - r * 0.45, y - r * 0.45, x + r * 0.45, y + r * 0.45],
                  fill=_rgba(color))

    # -------------------------------------------------- 出怪点

    def _draw_spawn_points(self, base, ov, d, gm, ss) -> None:
        if not self.spawn_points:
            return
        rad = self.cell * 0.20
        gates = set(getattr(gm, "spawn_tiles", []) or [])
        for (row, col), items in self.spawn_points.items():
            x, y = self.tile_xy(row, col)
            x, y = x * ss, y * ss
            r = rad * ss
            hov = self.hover_spawn == (row, col)
            if hov:
                r *= 1.25
            # 柔光晕：单独模糊后合成到覆盖层，避免裁切与硬边
            gsz = int(r * 6) + 8
            gl = Image.new("RGBA", (gsz, gsz), (0, 0, 0, 0))
            ImageDraw.Draw(gl).ellipse(
                [gsz / 2 - r * 1.55, gsz / 2 - r * 1.55,
                 gsz / 2 + r * 1.55, gsz / 2 + r * 1.55],
                fill=_rgba(SPAWN, 120))
            gl = gl.filter(ImageFilter.GaussianBlur(r * 0.55))
            ov.alpha_composite(gl, (int(x - gsz / 2), int(y - gsz / 2)))
            # 红方框由 _draw_doors 按真实 tile_start 统一画。
            # 这里若也画一遍，同格会被描两次边（外发光叠加成硬块），
            # 且路线起点常在门格外一格，会画出「门在错位置」的错觉。
            # 框内加一点红色底衬，强调这是出怪格
            d.rectangle([x - r * 0.72, y - r * 0.72,
                         x + r * 0.72, y + r * 0.72],
                        fill=_rgba(SPAWN, 60))
            # 三角形箭头朝下，表示敌人从这里出现并往里走
            d.polygon([(x, y - r*0.30), (x - r*0.34, y + r*0.26),
                       (x + r*0.34, y + r*0.26)], fill=_rgba((255, 236, 232), 225))
            total = sum(it[1] for it in items)
            if self.cell >= 24:
                fs = max(7, int(self.cell * ss * 0.26))
                # 第一批出怪的时间点，让「何时出怪」一眼可见
                try:
                    t0 = min(float(it[2]) for it in items)
                except (TypeError, ValueError, IndexError):
                    t0 = None
                cap = str(total)
                if t0 is not None:
                    cap = "%d @%.0fs" % (total, t0)
                d.text((x + r * 1.20, y), cap, font=_font(fs, True),
                       fill=_rgba((255, 205, 190)), anchor="lm",
                       stroke_width=max(1, ss), stroke_fill=_rgba((10, 12, 18)))

    # -------------------------------------------------- 坐标

    def _draw_coords(self, d, gm, ss) -> None:
        cell = self.cell * ss
        ox, oy = self.origin_x * ss, self.origin_y * ss
        fs = max(8, int(10 * ss))
        # 这里只画「常态」坐标；悬停高亮由 _draw_hover_layer 覆盖重画，
        # 以免把悬停状态固化进静态层缓存。
        #
        # 翻转后坐标轴不能再用 gm.height - r：用户按下翻转就是希望眼前
        # 这张图跟游戏里一致，那么「自下往上编号」也必须跟着屏幕走，
        # 否则最下面一行还是写着 1，翻转等于白翻。这里改成按**显示行**
        # 编号，即显示最下面一行永远是 1。
        for c in range(gm.width):
            dc = (gm.width - 1 - c) if self.flip_h else c
            x = ox + (dc + 0.5) * cell
            letter = col_letter(c)
            d.text((x, oy - cell * 0.20), letter, font=_font(fs, True),
                   fill=_rgba(COORD), anchor="mm")
            d.text((x, oy + gm.height * cell + cell * 0.20), letter,
                   font=_font(fs, True), fill=_rgba(COORD), anchor="mm")
        for r in range(gm.height):
            dr = (gm.height - 1 - r) if self.flip_v else r
            y = oy + (dr + 0.5) * cell
            # 编号跟随显示行：显示最下面一行 = 1
            num = str(gm.height - dr)
            d.text((ox - cell * 0.22, y), num, font=_font(fs, True),
                   fill=_rgba(COORD), anchor="mm")
            d.text((ox + gm.width * cell + cell * 0.22, y), num,
                   font=_font(fs, True), fill=_rgba(COORD), anchor="mm")

    # -------------------------------------------------- 动态层

    def _draw_enemies(self, im: Image.Image) -> None:
        if not self.show_dots or not self.frame_enemies:
            return
        gm = self.game_map
        n = len(self.frame_enemies)
        r = max(4.0, self.cell * 0.155)
        fs = max(8, int(self.cell * 0.30))
        for i, en in enumerate(self.frame_enemies):
            row = en.get("row", 0)
            col = en.get("col", 0)
            x, y = self.tile_xy(float(row), float(col))
            # 重叠错开：同格多只时沿圆周微偏
            if n > 1:
                same = [j for j, o in enumerate(self.frame_enemies)
                        if abs(float(o.get("row", 0)) - float(row)) < 0.28
                        and abs(float(o.get("col", 0)) - float(col)) < 0.28]
                if len(same) > 1:
                    k = same.index(i)
                    ang = 2 * math.pi * k / len(same) - math.pi / 2
                    off = r * 1.15
                    x += math.cos(ang) * off
                    y += math.sin(ang) * off
            # 颜色统一解析：enemy["color"] 来自 timeline，存的是敌人名
            # 字符串（用于分流配色），不是 RGB 元组；直接丢给 ImageDraw
            # 会抛 str 无法转 int。先按名字哈希成稳定颜色。
            ecol = en.get("color") or (240, 96, 90)
            if isinstance(ecol, str):
                ecol = _name_color(ecol)
            hov = (self.hover_enemy == i)
            hit = self._is_highlighted(en)
            rr = r * (1.32 if hov else 1.0)
            # 高亮：先画一圈放射状光晕（呼吸感来自半径，不依赖动画），
            # 再在圆点外描两道环，保证在任何底色上都跳出来。
            if hit:
                gr = r * 3.2
                glow = Image.new("RGBA", (int(gr * 2), int(gr * 2)), (0, 0, 0, 0))
                gd = ImageDraw.Draw(glow)
                cx = cy = gr
                for k in range(6, 0, -1):
                    t = k / 6.0
                    gd.ellipse([cx - gr * t, cy - gr * t,
                                cx + gr * t, cy + gr * t],
                               fill=_rgba(HILITE_GLOW, int(46 * (1 - t) + 14)))
                im.alpha_composite(glow, (int(x - gr), int(y - gr)))
                dd0 = ImageDraw.Draw(im)
                for wd, al in ((3, 235), (1, 255)):
                    dd0.ellipse([x - r * 1.95, y - r * 1.95,
                                 x + r * 1.95, y + r * 1.95],
                                outline=_rgba(HILITE_RING, al), width=wd)
            sp = _dot_sprite(ecol, rr, ring=True)
            im.alpha_composite(sp, (int(x - sp.width / 2), int(y - sp.height / 2)))
            # 名字：只在格子够大或悬停时画，否则太挤
            if self.cell >= 30 or hov or hit:
                # timeline 给的键是 enemy_name / label，早先这里读 "name"
                # 永远为空，所以鼠标悬停看不到名字。
                name = (en.get("enemy_name") or en.get("label")
                        or en.get("name") or "")
                if name:
                    fx, fy = int(x + rr + 3), int(y)
                    dd = ImageDraw.Draw(im)
                    # 高亮时名字用高亮色 + 更粗描边，方便在密集处找到它
                    dd.text((fx, fy), name, font=_font(fs, hit),
                            fill=_rgba(HILITE_RING if hit else TEXT),
                            anchor="lm", stroke_width=2,
                            stroke_fill=_rgba((10, 12, 18)))

    def _is_highlighted(self, en: dict) -> bool:
        """该敌人是否属于当前被点中的那一行。"""
        hl = self.highlight_enemy
        if not hl:
            return False
        eid, ridx = hl
        if not eid:
            return False
        if str(en.get("enemy_id") or "") != str(eid):
            return False
        # route_index 为负表示「这一行没绑定具体路线」，此时只按 id 匹配
        if ridx is None or ridx < 0:
            return True
        try:
            return int(en.get("route_index", -1)) == int(ridx)
        except (TypeError, ValueError):
            return False

    def _draw_isolate_highlight(self, d, gm: GameMap, ss: int) -> None:
        """隔离视图里的静态高亮：在起点画双环，并标出这条线的起终点。

        非隔离视图不画——那时敌人圆点自己会带光晕，再叠一层起点环
        会跟出怪点标记打架。
        """
        if self.isolate_route is None or not self.highlight_enemy:
            return
        if not (0 <= self.isolate_route < len(gm.routes)):
            return
        route = gm.routes[self.isolate_route]
        r, c = route.start
        x, y = self.tile_xy(float(r), float(c))
        x, y = x * ss, y * ss
        rad = self.cell * ss * 0.72
        for k, (rr, al, wd) in enumerate((
                (rad * 1.42, 90, max(1, ss)),
                (rad * 1.12, 200, max(2, ss * 2)),
                (rad * 0.78, 240, max(1, ss)))):
            d.ellipse([x - rr, y - rr, x + rr, y + rr],
                      outline=_rgba(HILITE_RING, al), width=wd)
        # 中心一个小实心点，避免环中间全是空的看不出落点
        d.ellipse([x - rad * 0.16, y - rad * 0.16,
                   x + rad * 0.16, y + rad * 0.16],
                  fill=_rgba(HILITE_RING, 235))
        # 起点角标
        fs = max(9, int(self.cell * ss * 0.30))
        txt = "起点"
        f = _font(fs, True)
        try:
            tw = int(d.textlength(txt, font=f))
        except Exception:
            tw = fs * 2
        bx = x + rad * 1.55
        by = y - fs
        d.rounded_rectangle([bx, by, bx + tw + 8, by + fs + 8], radius=3,
                            fill=_rgba((10, 14, 20), 220),
                            outline=_rgba(HILITE_RING, 200))
        d.text((bx + 4, by + fs / 2 + 1), txt, font=f,
               fill=_rgba(HILITE_RING), anchor="lm")

    def _draw_coord_highlight(self, d) -> None:
        """悬停行/列坐标改成金色（画在动态层，不进静态缓存）。"""
        gm = self.game_map
        if not gm or not self.hover:
            return
        cell = self.cell
        ox, oy = self.origin_x, self.origin_y
        fs = max(8, 10)
        hr, hc = self.hover
        dr, dc = self.disp_rc(hr, hc)
        if 0 <= hc < gm.width:
            x = ox + (dc + 0.5) * cell
            d.text((x, oy - cell * 0.20), col_letter(hc), font=_font(fs, True),
                   fill=_rgba(COORD_HL), anchor="mm")
            d.text((x, oy + gm.height * cell + cell * 0.20), col_letter(hc),
                   font=_font(fs, True), fill=_rgba(COORD_HL), anchor="mm")
        if 0 <= hr < gm.height:
            y = oy + (dr + 0.5) * cell
            # 与 _draw_coords 一致：编号按显示行算
            num = str(gm.height - dr)
            d.text((ox - cell * 0.22, y), num, font=_font(fs, True),
                   fill=_rgba(COORD_HL), anchor="mm")
            d.text((ox + gm.width * cell + cell * 0.22, y), num,
                   font=_font(fs, True), fill=_rgba(COORD_HL), anchor="mm")

    def _draw_hover_layer(self, im: Image.Image) -> None:
        d = ImageDraw.Draw(im)
        self._draw_coord_highlight(d)
        # 悬停格子加亮框
        if self.hover and self.game_map:
            r, c = self.hover
            x, y = self.tile_xy(r, c)
            h = self.cell / 2.0 - 1
            d.rounded_rectangle([x - h, y - h, x + h, y + h], radius=3,
                                outline=_rgba(GOLD, 220), width=2)
        # 选中格
        if self.selected and self.game_map:
            r, c = self.selected
            x, y = self.tile_xy(r, c)
            h = self.cell / 2.0 - 1
            d.rounded_rectangle([x - h, y - h, x + h, y + h], radius=3,
                                outline=_rgba((92, 176, 255), 235), width=2)
        # 坐标徽标
        if self.hover:
            self._draw_coord_badge(d, im)

    def _draw_coord_badge(self, d, im) -> None:
        r, c = self.hover
        txt = "%s%d" % (col_letter(c), r + 1)
        fs = max(9, int(11))
        f = _font(fs, True)
        try:
            tw = int(d.textlength(txt, font=f))
        except Exception:
            tw = 8 * len(txt)
        pad = 5
        bx = self.origin_x + 2
        by = self.origin_y + 2
        d.rounded_rectangle([bx, by, bx + tw + pad*2, by + fs + pad],
                            radius=4, fill=_rgba((16, 20, 27), 235),
                            outline=_rgba(GOLD, 200))
        d.text((bx + pad, by + pad/2), txt, font=f, fill=_rgba(GOLD))


def _hex(s: str) -> Tuple[int, int, int]:
    s = s.lstrip("#")
    if len(s) == 3:
        s = "".join(ch * 2 for ch in s)
    try:
        return (int(s[0:2], 16), int(s[2:4], 16), int(s[4:6], 16))
    except Exception:
        return (240, 96, 90)