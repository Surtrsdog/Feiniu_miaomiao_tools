"""沙盘推演面板：摆干员、记粗轴、放箱子、踢敌人、加减速。

与「寻路分析」的关系
====================
寻路分析只**看**，沙盘可以**改**。两者共用同一套 GameMap / Timeline /
RouteAnalysis，但沙盘额外维护一层「假设状态」——而且这一层严格遵守
``core/sandbox.py`` 里写下的三条铁律：

* 箱子 -> 真的重算路线（游戏里只有道路障碍物能改变路径）
* 干员 -> **不重算**，只标出「这里会发生阻挡」（干员是碰撞级阻挡，
  敌人照原路走过来撞上才停，不会提前绕路）
* 踢人 -> 从出怪表里拿掉
* 减速 -> 只拉长移动段，罚站时间不动

布局
====
::

    ┌──────────────────────────────┬────────────────
    │ 关卡筛选 / 模式 / 翻转放大图层 │  干员选择
    ├──────────────────────────────┤  （搜索 + 列表）
    │                              ├────────────────
    │        地图（MapCanvas）       │  已选择干员
    │                              ├────────────────
    ├──────────────────────────────┤  本关出怪
    │ 播放控制条                     │
    ├──────────────────────────────┤  操作按钮
    │ 粗轴（TrackCanvas）            │
    │ buff 轴                       │
    └──────────────────────────────┴────────────────

操作流
======
1. 右侧「干员选择」点一个干员 -> 进入「已选择干员」，可换技能
2. **右键**已选择列表里的那一项 -> 进入「待部署」
3. **右键**地图上可部署的格子 -> 真的落位（高台/地面会校验）
4. 右键场上干员 -> 撤退（写进粗轴）/ 开技能（只记时刻）/ 改朝向 /
   切换能否挡飞行
5. 右键敌人 -> 停顿 / 减速（带秒数），动画跟着变
6. 底部粗轴记录全部动作，可导出 / 导入 JSON 交流思路

计算全在 ``core/sandbox.py`` 与 ``core/sandbox_track.py``，这个文件只
负责画和点。
"""
from __future__ import annotations

import json
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from typing import Dict, List, Optional

try:
    from PIL import ImageTk
except Exception:  # pragma: no cover - 头像只是锦上添花
    ImageTk = None

from ..core import mechanisms as ME
from ..core import pathfinding as PF
from ..core import routes as RT
from ..core.catalog import CATEGORY_ORDER
from ..core.enemies import spawn_unmovable_of_ref
from ..core.maps import get_level
from ..core.models import GameMap
from ..core.sandbox import Sandbox
from ..core.sandbox_track import (CoarseTrack, Deployment, SkillCycle,
                                  SP_ATTACK, SP_AUTO, SP_DEFENSE, SP_NONE,
                                  sp_boost_of_text)
from ..core.skills import plain
from ..core.timeline import fill_names, parse_timeline
from .map_canvas import MapCanvas
from .playback import PlaybackBar
from .track_canvas import TrackCanvas
from .widgets import (ACCENT, ACCENT_SOFT, ACCENT_TXT, BG, BG_DEEP, BG_INPUT,
                      BG_PANEL, BG_SUNKEN, BORDER, ComboBox, DIVIDER, FG,
                      FG_DIM, FONT_NUM, FONT_UI, FS_BODY, FS_MICRO,
                      FS_SMALL, PAD_M, PAD_S, PAD_XS)

#: 操作模式
MODE_SELECT = "select"
MODE_OPERATOR = "operator"
MODE_BOX = "box"
MODE_SLOW = "slow"
MODE_KICK = "kick"

MODES = [
    (MODE_SELECT, "选中", "左键点格子：看路线经过哪些、能不能站人"),
    (MODE_OPERATOR, "放干员", "左键放一枚占位干员：只标阻挡，不改路线"),
    (MODE_BOX, "放箱子", "左键放箱子：真的重算路径，堵死蓝门会被拒绝"),
    (MODE_SLOW, "减速", "右键右侧出怪列表里的一只，给它加停顿/减速"),
    (MODE_KICK, "踢人", "点右侧出怪列表里的一只，把它从本关拿掉"),
]

FACINGS = ["RIGHT", "LEFT", "UP", "DOWN"]
FACING_CN = {"RIGHT": "朝右", "LEFT": "朝左", "UP": "朝上", "DOWN": "朝下"}

#: 技能回复类型的中文说明
SP_CN = {SP_AUTO: "自然回复", SP_ATTACK: "攻击回复",
         SP_DEFENSE: "受击回复", SP_NONE: "不回复 / 被动"}

#: 右键敌人时给的快捷停顿时长
STOP_PRESETS = [1.0, 2.0, 3.0, 5.0, 10.0]

#: 「干员选择」列表里代表箱子那一行的名字。
#: 箱子不是干员（没有技能、不回复 SP、不阻挡），但用户要在同一个列表里
#: 选它、右键它、再右键地图落位——所以给它一个哨兵名，走到 ``_pick_box``。
BOX_NAME = "箱子"


class SandboxPanel(tk.Frame):
    """沙盘推演主面板。"""

    def __init__(self, master, app):
        super().__init__(master, background=BG)
        self.app = app
        self.game_map: Optional[GameMap] = None
        self.timeline = None
        self.sandbox: Optional[Sandbox] = None
        self.stage = None
        self.mode = MODE_SELECT
        self.facing = "RIGHT"
        self.selected_event = None
        self._mode_btns: Dict[str, tk.Button] = {}
        self._ev_rows: List[dict] = []
        self._stage_index: Dict[str, object] = {}
        self._groups: List[object] = []
        self._node_types: List[tuple] = []
        #: 当前游标（秒）
        self._now = 0.0
        #: 右侧「已选择干员」：
        #: {"op","name","is_ranged","block","interval","cost","skills",
        #:  "skill","block_fly"}
        self._picked: List[dict] = []
        #: 被右键选中、等待「再右键地图落位」的候选下标
        self._pending_idx: Optional[int] = None
        self._op_cache: Dict[str, object] = {}
        self._op_names: List[str] = []
        self._menu = None
        self._sel_cell = None
        self._mechs: List[ME.Mechanism] = []
        self._portal_map: Dict[tuple, tuple] = {}
        self._zoom = 1.0
        self._cached_marked = False
        #: 干员头像的 PhotoImage 引用（没有引用会被 GC 清成白块）
        self._photos: Dict[str, object] = {}
        #: 撤销/重做按钮引用
        self._btn_undo = None
        self._btn_redo = None

        self._build()

    # ============================================================ 目录

    @property
    def catalog(self):
        """关卡目录**每次现取**。

        属性名是 ``app.stage_catalog``（不是 ``app.catalog``）——按后者
        取永远拿到 None，下拉一片空白。
        """
        return getattr(self.app, "stage_catalog", None)

    def refresh_stages(self) -> None:
        if self.catalog:
            self._mark_cached()
            self._fill_stages()

    def _mark_cached(self) -> None:
        """标出本地已有地图的关卡（● 已缓存 / ○ 需联网）。

        缓存按**地图相对路径**存盘，肉鸽 1033 条关卡只对应 638 张图
        （换皮图共用一份），只比 stage_id 会全部显示 ○。

        只算一次：4521 条关卡逐条比三遍键，每敲一个搜索字符都重算
        并不值得，而结果在一次会话里也不会变。
        """
        if self._cached_marked or not self.catalog:
            return
        try:
            cached = set(self.app.level_cache.list_cached())
        except Exception:
            return

        def _rel_key(rel: str) -> str:
            safe = (rel or "").replace("/", "_").replace("\\", "_")
            return safe[:-5] if safe.endswith(".json") else safe

        for st in self.catalog.stages.values():
            if st.cached:
                continue
            base = st.stage_id.split("#", 1)[0]
            hit = st.stage_id in cached or base in cached
            if not hit:
                rel = getattr(st, "path", "") or ""
                if rel and _rel_key(rel) in cached:
                    hit = True
            st.cached = hit
        self._cached_marked = True

    # ============================================================ 构建

    def _build(self) -> None:
        self.app.build_panel_header(self, "沙盘推演", "SANDBOX",
                                   "摆干员、记粗轴、放箱子、加减速，"
                                   "看路线和到达时间怎么变。")
        body = tk.Frame(self, background=BG)
        body.pack(fill="both", expand=True)

        left = tk.Frame(body, background=BG)
        left.pack(side="left", fill="both", expand=True)

        self._build_toolbar(left)

        self.canvas = MapCanvas(left)
        self.canvas.pack(fill="both", expand=True, pady=(PAD_S, 0))
        self.canvas.on_cell_click = self._on_cell_click
        self.canvas.on_cell_right_click = self._on_cell_right_click
        self.canvas.on_object_hover = self._on_object_hover
        self.canvas.on_enemy_click = self._on_enemy_click

        self.playback = PlaybackBar(left, on_time=self._on_playback_time)
        self.playback.pack(fill="x", pady=(PAD_XS, 0))

        self._build_track(left)

        right = tk.Frame(body, background=BG_PANEL, width=366,
                         highlightthickness=1, highlightbackground=DIVIDER)
        right.pack(side="right", fill="y")
        right.pack_propagate(False)

        self._build_picker(right)
        self._build_picked(right)
        self._build_events(right)
        self._build_footer(right)

        # Ctrl+Z / Ctrl+Y：办公软件式撤销重做。
        try:
            self.bind_all("<Control-z>", lambda e: self._on_undo())
            self.bind_all("<Control-y>", lambda e: self._on_redo())
        except Exception:
            pass

        self._mark_cached()      # 必须在 _fill_stages 之前：徽标靠它
        self._fill_stages()
        self._fill_picker()
        self._fill_picked()
        self.set_mode(MODE_SELECT)

    def _build_toolbar(self, parent) -> None:
        bar = tk.Frame(parent, background=BG_PANEL, highlightthickness=1,
                       highlightbackground=DIVIDER)
        bar.pack(fill="x")
        row = tk.Frame(bar, background=BG_PANEL)
        row.pack(fill="x", padx=PAD_M, pady=PAD_S)

        def lbl(master, t):
            tk.Label(master, text=t, background=BG_PANEL, foreground=FG_DIM,
                     font=(FONT_UI, FS_SMALL)).pack(side="left",
                                                    padx=(0, PAD_XS))

        lbl(row, "分类")
        self.cmb_cat = ComboBox(row, width=9,
                                values=[n for _k, n in CATEGORY_ORDER])
        self.cmb_cat.pack(side="left", padx=(0, PAD_S))
        self.cmb_cat.bind("<<ComboboxSelected>>", lambda e: self._on_cat())

        lbl(row, "主题")
        self.cmb_group = ComboBox(row, width=17, values=[])
        self.cmb_group.pack(side="left", padx=(0, PAD_S))
        self.cmb_group.bind("<<ComboboxSelected>>", lambda e: self._on_group())

        # 第三层只对集成战略出现：肉鸽一个主题几十到近三百关。
        self.lbl_node = tk.Label(row, text="节点", background=BG_PANEL,
                                 foreground=FG_DIM, font=(FONT_UI, FS_SMALL))
        self.var_node = tk.StringVar()
        self.cmb_node = ComboBox(row, width=12, textvariable=self.var_node,
                                 values=[])
        self.cmb_node.bind("<<ComboboxSelected>>", lambda e: self._on_node())

        lbl(row, "关卡")
        self.cmb_stage = ComboBox(row, width=19, values=[])
        self.cmb_stage.pack(side="left")
        self.cmb_stage.bind("<<ComboboxSelected>>", self._on_stage_pick)

        self.var_search = tk.StringVar()
        self.ent_search = tk.Entry(row, textvariable=self.var_search, width=8,
                                   background=BG_INPUT, foreground=FG,
                                   insertbackground=FG, relief="flat",
                                   font=(FONT_UI, FS_SMALL),
                                   highlightthickness=1,
                                   highlightbackground=BORDER,
                                   highlightcolor=ACCENT)
        self.ent_search.pack(side="left", ipady=2, padx=(PAD_S, 0))
        self.ent_search.bind("<KeyRelease>", lambda e: self._on_search())

        tk.Button(row, text="载入", relief="flat", background=ACCENT_SOFT,
                  foreground=FG, activebackground=ACCENT, activeforeground=BG,
                  font=(FONT_UI, FS_SMALL), highlightthickness=0,
                  cursor="hand2", padx=PAD_M, pady=1,
                  command=self._on_load).pack(side="left",
                                              padx=(PAD_S, PAD_M))

        lbl(row, "模式")
        for key, label, _tip in MODES:
            b = tk.Button(row, text=label, relief="flat", background=BG_DEEP,
                          foreground=FG_DIM, activebackground=ACCENT_SOFT,
                          activeforeground=FG, font=(FONT_UI, FS_SMALL),
                          highlightthickness=1, highlightbackground=BORDER,
                          cursor="hand2", padx=PAD_S, pady=1,
                          command=lambda k=key: self.set_mode(k))
            b.pack(side="left", padx=2)
            self._mode_btns[key] = b

        self.cmb_face = ComboBox(row, width=7,
                                 values=[FACING_CN[f] for f in FACINGS])
        self.cmb_face.pack(side="left", padx=(PAD_S, 0))
        self.cmb_face.bind("<<ComboboxSelected>>", self._on_facing)
        self.cmb_face.set(FACING_CN[self.facing])

        # ---- 第二行：翻转 / 放大 / 图层 / 重置
        row2 = tk.Frame(bar, background=BG_PANEL)
        row2.pack(fill="x", padx=PAD_M, pady=(0, PAD_S))

        lbl(row2, "翻转")
        self.var_flip_v = tk.BooleanVar(value=False)
        self.var_flip_h = tk.BooleanVar(value=False)
        for text, var in (("上下", self.var_flip_v), ("左右", self.var_flip_h)):
            tk.Checkbutton(row2, text=text, variable=var,
                           background=BG_PANEL, foreground=FG,
                           selectcolor=BG_INPUT, activebackground=BG_PANEL,
                           activeforeground=ACCENT, font=(FONT_UI, FS_SMALL),
                           bd=0, highlightthickness=0,
                           command=self._on_flip).pack(side="left",
                                                       padx=(0, PAD_S))

        self._sep(row2)

        lbl(row2, "放大")
        self.lbl_zoom = tk.Label(row2, text="1.0×", background=BG_PANEL,
                                 foreground=FG, width=5,
                                 font=(FONT_NUM, FS_SMALL), anchor="w")
        for txt, ratio in (("−", -1), ("+", +1)):
            tk.Button(row2, text=txt, width=2, bd=0, relief="flat",
                      background=BG_INPUT, foreground=FG,
                      activebackground=ACCENT, activeforeground="#10131a",
                      font=(FONT_UI, FS_SMALL, "bold"), cursor="hand2",
                      command=(lambda r=ratio: self._zoom_step(r))).pack(
                side="left", padx=(0, 2))
        self.lbl_zoom.pack(side="left", padx=(PAD_XS, PAD_S))

        self._sep(row2)

        lbl(row2, "图层")
        self.var_ground = tk.BooleanVar(value=True)
        self.var_fly = tk.BooleanVar(value=False)
        self.var_cost = tk.BooleanVar(value=False)
        self.var_mech = tk.BooleanVar(value=True)
        for text, var in (("地面层", self.var_ground),
                          ("飞行层", self.var_fly),
                          ("显示代价", self.var_cost),
                          ("地图机关", self.var_mech)):
            tk.Checkbutton(row2, text=text, variable=var,
                           background=BG_PANEL, foreground=FG,
                           selectcolor=BG_INPUT, activebackground=BG_PANEL,
                           activeforeground=ACCENT, font=(FONT_UI, FS_SMALL),
                           bd=0, highlightthickness=0,
                           command=self._on_layer).pack(side="left",
                                                        padx=(0, PAD_S))

        tk.Button(row2, text="重置视图", bd=0, relief="flat",
                  background=BG_INPUT, foreground=FG,
                  activebackground=ACCENT, activeforeground="#10131a",
                  font=(FONT_UI, FS_SMALL), cursor="hand2", padx=PAD_S,
                  command=self._reset_view).pack(side="left")

        self.lbl_hover = tk.Label(bar, text="", background=BG_PANEL,
                                  foreground=ACCENT_TXT,
                                  font=(FONT_UI, FS_MICRO), anchor="w",
                                  justify="left")
        self.lbl_hover.pack(fill="x", padx=PAD_M, pady=(0, PAD_XS))

    @staticmethod
    def _sep(parent) -> None:
        tk.Frame(parent, background=DIVIDER, width=1).pack(
            side="left", fill="y", padx=PAD_S, pady=1)

    def _build_track(self, parent) -> None:
        """底部粗轴 + buff 轴。"""
        box = tk.Frame(parent, background=BG)
        box.pack(fill="x", pady=(PAD_S, 0))

        head = tk.Frame(box, background=BG)
        head.pack(fill="x")
        tk.Label(head, text="粗轴", background=BG, foreground=FG,
                 font=(FONT_UI, FS_BODY, "bold")).pack(side="left")
        self.lbl_track = tk.Label(head, text="（部署 / 撤退 / 技能）",
                                  background=BG, foreground=FG_DIM,
                                  font=(FONT_UI, FS_MICRO))
        self.lbl_track.pack(side="left", padx=PAD_S)

        for text, cmd in (("导入粗轴", self._on_import),
                          ("导出粗轴", self._on_export)):
            tk.Button(head, text=text, relief="flat", background=BG_DEEP,
                      foreground=FG_DIM, activebackground=ACCENT_SOFT,
                      activeforeground=FG, font=(FONT_UI, FS_MICRO),
                      highlightthickness=1, highlightbackground=BORDER,
                      cursor="hand2", padx=PAD_S, pady=1,
                      command=cmd).pack(side="right", padx=(PAD_XS, 0))

        self.track_canvas = TrackCanvas(box, height=134)
        self.track_canvas.pack(fill="x", pady=(3, 0))
        self.track_canvas.on_seek = self._on_track_seek
        self.track_canvas.on_pick = self._on_track_pick
        self.track_canvas.on_right_click = self._on_track_right

        bhead = tk.Frame(box, background=BG)
        bhead.pack(fill="x", pady=(PAD_XS, 0))
        tk.Label(bhead, text="buff 轴", background=BG, foreground=FG,
                 font=(FONT_UI, FS_MICRO, "bold")).pack(side="left")
        self.lbl_buff = tk.Label(bhead, text="（右键敌人设置停顿/减速）",
                                 background=BG, foreground=FG_DIM,
                                 font=(FONT_UI, FS_MICRO))
        self.lbl_buff.pack(side="left", padx=PAD_S)
        tk.Button(bhead, text="清空 buff", relief="flat",
                  background=BG_DEEP, foreground=FG_DIM,
                  activebackground=ACCENT_SOFT, activeforeground=FG,
                  font=(FONT_UI, FS_MICRO), highlightthickness=1,
                  highlightbackground=BORDER, cursor="hand2", padx=PAD_S,
                  pady=1, command=self._on_clear_buff).pack(side="right")

        self.buff_canvas = tk.Canvas(box, height=28, background="#1b2029",
                                     highlightthickness=0)
        self.buff_canvas.pack(fill="x", pady=(2, 0))
        self.buff_canvas.bind("<Configure>",
                              lambda e: self._draw_buff_axis())

    def _build_picker(self, parent) -> None:
        head = tk.Frame(parent, background=BG_PANEL)
        head.pack(fill="x", padx=PAD_M, pady=(PAD_M, PAD_XS))
        tk.Label(head, text="干员选择", background=BG_PANEL,
                 foreground=ACCENT,
                 font=(FONT_UI, FS_BODY, "bold")).pack(side="left")
        self.var_opsearch = tk.StringVar()
        ent = tk.Entry(head, textvariable=self.var_opsearch, width=9,
                       background=BG_INPUT, foreground=FG,
                       insertbackground=FG, relief="flat",
                       font=(FONT_UI, FS_MICRO), highlightthickness=1,
                       highlightbackground=BORDER, highlightcolor=ACCENT)
        ent.pack(side="right", ipady=1)
        ent.bind("<KeyRelease>", lambda e: self._fill_picker())

        self.op_canvas, self.op_inner, self._op_win = self._scrolled(
            parent, height=116)

    def _build_picked(self, parent) -> None:
        head = tk.Frame(parent, background=BG_PANEL)
        head.pack(fill="x", padx=PAD_M, pady=(PAD_M, PAD_XS))
        tk.Label(head, text="已选择干员", background=BG_PANEL,
                 foreground=ACCENT,
                 font=(FONT_UI, FS_BODY, "bold")).pack(side="left")
        self.lbl_pending = tk.Label(head, text="", background=BG_PANEL,
                                    foreground=ACCENT_TXT,
                                    font=(FONT_UI, FS_MICRO))
        self.lbl_pending.pack(side="right")

        self.lbl_pick_hint = tk.Label(
            parent, text="右键已选择列表里的干员 → 再右键地图可部署格即可落位",
            background=BG_PANEL, foreground=FG_DIM, font=(FONT_UI, FS_MICRO),
            anchor="w", justify="left", wraplength=338)
        self.lbl_pick_hint.pack(fill="x", padx=PAD_M, pady=(0, PAD_XS))

        self.pick_canvas, self.pick_inner, self._pick_win = self._scrolled(
            parent, height=104)

    def _toggle_harmless(self) -> None:
        """切换「撇除无害单位」后重建出怪列表。

        只影响**列表显示**，不改 ``Sandbox.events()``——无害单位在实机里
        真的会出场（会走动、会挡路、可以被攻击），把它们从模拟里删掉
        会让沙盘和实机不符。这里只是让列表干净些。
        """
        self._fill_events()
        sb = self.sandbox
        if sb is not None:
            try:
                self._refresh_frame(self._now)
                self.canvas.set_sandbox(self._render_state())
            except Exception:
                pass

    def _visible_events(self) -> list:
        """出怪列表要显示的事件：按「撇除无害单位」过滤后的结果。"""
        sb = self.sandbox
        if sb is None:
            return []
        live = sb.live_events()
        if getattr(self, "var_hide_harmless", None) is not None \
                and self.var_hide_harmless.get():
            live = [e for e in live if not getattr(e, "harmless", False)]
        return live

    def _toggle_fold_random(self) -> None:
        """切换「随机包择一」后重建出怪列表与沙盘。

        随机候选包（``randomSpawnGroupKey``）是「同 key 按 weight 抽一条」，
        折叠与否会让总出怪数变化很大（咩的朋友 43 -> 32，足球图 1393 ->
        584），所以必须重建沙盘的 ``events()`` 视图并刷新右侧列表。
        """
        fold = bool(self.var_fold_random.get())
        sb = self.sandbox
        if sb is not None:
            sb.fold_random = fold
            # 候选包变了，之前选中的那只可能已经不在列表里
            self.selected_event = None
            self._pending_idx = None
        self._fill_events()
        if sb is not None:
            # 出怪集合变了，重新算帧并把状态推给画布，避免画布上留着
            # 已经不在列表里的敌人
            try:
                self.playback.set_timeline(self._track_total())
                self._refresh_frame(self._now)
                self.canvas.set_sandbox(self._render_state())
            except Exception:
                pass

    def _build_events(self, parent) -> None:
        head = tk.Frame(parent, background=BG_PANEL)
        head.pack(fill="x", padx=PAD_M, pady=(PAD_M, PAD_XS))
        tk.Label(head, text="本关出怪", background=BG_PANEL, foreground=ACCENT,
                 font=(FONT_UI, FS_BODY, "bold")).pack(side="left")
        self.lbl_sum = tk.Label(head, text="", background=BG_PANEL,
                                foreground=FG_DIM, font=(FONT_UI, FS_MICRO))
        self.lbl_sum.pack(side="right")
        # 「撇除无害单位」：和平民/演出单位共存的关卡（H8-4 有 12 个平民）
        # 里，沙盘原先把它们全列出来，看起来就像「这关多出平民」。
        # 无害单位（isUnharmfulAndAlwaysCountAsKilled）不计入剩余敌人总数，
        # 但**确实会出场**，所以默认关（不影响实机模拟），需要时手动撇除。
        self.var_hide_harmless = tk.BooleanVar(value=False)
        self.chk_harmless = tk.Checkbutton(
            head, text="撇除无害单位", variable=self.var_hide_harmless,
            background=BG_PANEL, foreground=FG_DIM,
            activebackground=BG_PANEL, activeforeground=ACCENT,
            selectcolor=BG_DEEP, font=(FONT_UI, FS_MICRO),
            highlightthickness=0, bd=0, cursor="hand2",
            command=self._toggle_harmless)
        self.chk_harmless.pack(side="right", padx=(0, PAD_S))
        # 随机候选包（randomSpawnGroupKey）折叠开关。默认开——沙盘的目的是
        # 模拟实机这一局，把「N 选 1」当成 N 只会让总出怪数翻倍
        # （足球图 1393 vs 584、咩的朋友 43 vs 32）。关掉可看全部备选。
        self.var_fold_random = tk.BooleanVar(value=True)
        self.chk_fold_random = tk.Checkbutton(
            head, text="随机包择一", variable=self.var_fold_random,
            background=BG_PANEL, foreground=FG_DIM,
            activebackground=BG_PANEL, activeforeground=ACCENT,
            selectcolor=BG_DEEP, font=(FONT_UI, FS_MICRO),
            highlightthickness=0, bd=0, cursor="hand2",
            command=self._toggle_fold_random)
        self.chk_fold_random.pack(side="right", padx=(0, PAD_S))

        self.lbl_hint = tk.Label(parent, text="先选关卡并载入",
                                 background=BG_PANEL, foreground=FG_DIM,
                                 font=(FONT_UI, FS_SMALL), anchor="w",
                                 justify="left", wraplength=338)
        self.lbl_hint.pack(fill="x", padx=PAD_M, pady=(0, PAD_XS))

        self.ev_canvas, self.ev_inner, self._ev_win = self._scrolled(
            parent, height=150, expand=True)

    def _scrolled(self, parent, height: int = 120, expand: bool = False):
        """带竖向滚轮的滚动区，返回 (canvas, inner, window_id)。"""
        wrap = tk.Frame(parent, background=BG_PANEL)
        if expand:
            wrap.pack(fill="both", expand=True, padx=PAD_M)
        else:
            wrap.pack(fill="x", padx=PAD_M)
        cv = tk.Canvas(wrap, height=height, background=BG_SUNKEN,
                       highlightthickness=0)
        sb = ttk.Scrollbar(wrap, orient="vertical", command=cv.yview)
        cv.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        cv.pack(side="left", fill="both", expand=True)
        inner = tk.Frame(cv, background=BG_SUNKEN)
        win = cv.create_window((0, 0), window=inner, anchor="nw")
        inner.bind("<Configure>",
                   lambda e, c=cv: c.configure(scrollregion=c.bbox("all")))
        cv.bind("<Configure>",
                lambda e, c=cv, w=win: c.itemconfigure(w, width=e.width))
        cv.bind("<MouseWheel>",
                lambda e, c=cv: c.yview_scroll(int(-e.delta / 120), "units"))
        return cv, inner, win

    def _build_footer(self, parent) -> None:
        foot = tk.Frame(parent, background=BG_PANEL)
        foot.pack(fill="x", padx=PAD_M, pady=PAD_S)
        for text, cmd in (("清空全部", self._on_reset),
                          ("撤一步", self._on_undo),
                          ("重做", self._on_redo),
                          ("撤销减速", self._on_clear_buff),
                          ("恢复被踢", self._on_restore)):
            b = tk.Button(foot, text=text, relief="flat", background=BG_DEEP,
                          foreground=FG_DIM, activebackground=ACCENT_SOFT,
                          activeforeground=FG, font=(FONT_UI, FS_MICRO),
                          highlightthickness=1, highlightbackground=BORDER,
                          cursor="hand2", padx=PAD_S, pady=1,
                          command=cmd)
            b.pack(side="left", padx=(0, PAD_XS))
            if text == "撤一步":
                self._btn_undo = b
            elif text == "重做":
                self._btn_redo = b

        self.lbl_detail = tk.Label(parent, text="", background=BG_PANEL,
                                   foreground=ACCENT_TXT,
                                   font=(FONT_UI, FS_MICRO), anchor="w",
                                   justify="left", wraplength=338)
        self.lbl_detail.pack(fill="x", padx=PAD_M, pady=(0, PAD_M))

    # ============================================================ 关卡筛选

    def _fill_stages(self) -> None:
        cat = self.catalog
        if not cat:
            return
        labels = [cat.category_label(k) for k in cat.categories()]
        self.cmb_cat.configure(values=labels)
        if labels and not self.cmb_cat.get():
            self.cmb_cat.set(labels[0])
            self._on_cat()

    def _cat_key(self) -> str:
        cat = self.catalog
        if not cat:
            return ""
        label = self.cmb_cat.get()
        for k in cat.categories():
            if cat.category_label(k) == label:
                return k
        return ""

    def _on_cat(self) -> None:
        cat = self.catalog
        if not cat:
            return
        key = self._cat_key()
        self._groups = cat.category_groups(key)
        names = [g.label for g in self._groups]
        self.cmb_group.configure(values=names)
        if names:
            self.cmb_group.set(names[0])
            self._on_group()
        else:
            self.cmb_group.set("")
            self._hide_node_layer()
            self._fill_levels([])

    def _on_group(self) -> None:
        g = self._current_group()
        if g is None:
            self._hide_node_layer()
            self._fill_levels([])
            return
        self._show_node_layer(g)
        self._refresh_levels()

    def _current_group(self):
        title = self.cmb_group.get()
        for g in self._groups:
            if g.label == title:
                return g
        return None

    def _hide_node_layer(self) -> None:
        self._node_types = []
        try:
            self.cmb_node.configure(values=[])
            self.var_node.set("")
            self.cmb_node.pack_forget()
            self.lbl_node.pack_forget()
        except Exception:
            pass

    def _show_node_layer(self, group) -> None:
        """第三层：按集成战略里实际存在的节点类型再筛一次。

        用户要求「集成战略内容没有分层的第二次筛选分层」。数据来自
        ``StageCatalog.node_types_in``（按 ``stage.node_type`` 统计），
        只列真有的类型并带数量；选「全部节点」等于不加这一层。
        """
        cat = self.catalog
        if not cat:
            return
        try:
            types = cat.node_types_in(group.group_id)
        except Exception:
            types = []
        if not types:
            self._hide_node_layer()
            return
        self._node_types = list(types)
        values = ["全部节点（%d）" % sum(n for _k, _l, n in types)]
        values += ["%s（%d）" % (label, n) for _k, label, n in types]
        self.lbl_node.pack(side="left", padx=(0, PAD_XS), before=self.cmb_stage)
        self.cmb_node.configure(values=values)
        self.cmb_node.pack(side="left", padx=(0, PAD_S), before=self.cmb_stage)
        if self.var_node.get() not in values:
            self.var_node.set(values[0])

    def _node_key(self) -> str:
        text = self.var_node.get()
        if not text or text.startswith("全部节点"):
            return ""
        for key, label, _n in self._node_types:
            if text.startswith(label):
                return key
        return ""

    def _on_node(self) -> None:
        self._refresh_levels()

    def _on_search(self) -> None:
        self._refresh_levels()

    def _refresh_levels(self) -> None:
        g = self._current_group()
        cat = self.catalog
        if g is None or not cat:
            return
        node = self._node_key()
        if node:
            try:
                pool = list(cat.stages_in(g.group_id, node))
            except Exception:
                pool = [s for s in g.stages if s.node_type == node]
        else:
            pool = list(g.stages)
        q = (self.var_search.get() or "").strip().lower()
        if q:
            def _blob(st):
                return " ".join((st.label, st.stage_id, st.code or "",
                                 st.name or "", st.sub_name or "",
                                 g.name or "")).lower()
            pool = [st for st in pool if q in _blob(st)]
        pool.sort(key=lambda st: (st.difficulty_label != "", st.stage_id))
        self._fill_levels(pool)

    def _fill_levels(self, pool) -> None:
        """把关卡填进第四层下拉。

        显示名重复时**必须**能区分开，否则字典键会互相覆盖——集成战略
        里同一个 ``name`` 常有好几个变体（``ro4_b_4`` 与 ``ro4_b_4_c``
        都叫「紧急授课」），原先 ``self._stage_index[label] = st`` 会让
        后一个盖掉前一个：IS4 险路恶敌下拉 21 项、索引只剩 17 个键，
        用户点第 18 项之后的关卡，``_on_load`` 拿到的其实是别的关。
        IS6 更严重（184 项只剩 119 个键，65 关点不到）。

        修法：先统计每个显示名出现几次，**重复的**一律追加 ``stage_id``
        作后缀，保证一键一关；不重复的保持原样，界面看上去没变化。
        """
        self._stage_index = {}
        base = []
        for st in pool:
            mark = "●" if getattr(st, "cached", False) else "○"
            tag = "  [%s]" % st.difficulty_label if st.difficulty_label else ""
            name = (st.label or "").strip()
            if not name:
                # 解包数据里有 1 关 label 是个空格（ro4_b_9，首领节点），
                # 直接拼出来就是「● 」，下拉里看不出是什么关。
                name = (st.code or "").strip() or st.stage_id
                sub = (getattr(st, "sub_name", "") or "").strip()
                if sub:
                    name = "%s %s" % (name, sub)
            base.append("%s%s %s" % (mark, tag, name))
        freq = {}
        for name in base:
            freq[name] = freq.get(name, 0) + 1
        labels = []
        for st, name in zip(pool, base):
            if freq[name] > 1:
                # 同名变体：后缀用 stage_id，它是唯一的
                name = "%s（%s）" % (name, st.stage_id)
            labels.append(name)
            self._stage_index[name] = st
        self.cmb_stage.configure(values=labels)
        if labels:
            self.cmb_stage.set(labels[0])
        else:
            self.cmb_stage.set("")

    def set_mode(self, key: str) -> None:
        self.mode = key
        for k, b in self._mode_btns.items():
            on = (k == key)
            b.configure(background=ACCENT_SOFT if on else BG_DEEP,
                        foreground=FG if on else FG_DIM)
        tip = next((t for k, _l, t in MODES if k == key), "")
        self.lbl_hint.configure(text=tip)

    def _on_facing(self, _e=None) -> None:
        label = self.cmb_face.get()
        for f, cn in FACING_CN.items():
            if cn == label:
                self.facing = f
                break

    def _on_stage_pick(self, _e=None) -> None:
        pass

    # ============================================================ 载入

    def _load_spawn_wait(self, raw) -> None:
        """把「出场原地站多久」灌进沙盘（角兽的【休憩】）。

        这个时长**不在路线里**。``ro6_c_2``（咩的朋友）的角兽 23 条路线
        ``checkpoints`` 全是空数组，所以路线分析给 ``pre_wait = 0``——
        界面上因此显示「罚站 0 秒」，而实机是每只出场先站 90 秒。

        真值在敌人库的 ``talentBlackboard`` 里
        （``Revive.unmovable_duration``，默认 150s），而且**关卡会覆盖**：
        ``ro6_c_2`` 的 ``enemyDbRefs`` 把它改成 90s，正好对上 PRTS 关卡页
        那句「角兽处于【休憩】状态时，出场 90 秒内无法移动」。

        取不到敌人库时静默跳过——宁可显示 0，也不要瞎猜一个数。
        """
        sb = getattr(self, "sandbox", None)
        if sb is None:
            return
        if not isinstance(raw, dict):
            return
        for ref in (raw.get("enemyDbRefs") or []):
            if not isinstance(ref, dict):
                continue
            eid = ref.get("id")
            if not eid:
                continue
            w = spawn_unmovable_of_ref(ref)
            # 0 秒是绝大多数敌人的正常情况，不占表位
            if w > 0.01:
                sb.spawn_wait[eid] = w

    def _enemy_name_lookup(self):
        lib = getattr(self.app, "enemy_lib", None)
        manual = getattr(self.app, "enemy_names", None) or {}

        def lookup(eid: str) -> Optional[str]:
            nm = manual.get(eid)
            if nm:
                return nm
            if lib is None:
                return None
            try:
                st = lib.stats(eid)
                if st and st.name and st.name != eid:
                    return st.name
            except Exception:
                pass
            return None
        return lookup

    def _current_stage(self):
        label = self.cmb_stage.get()
        st = self._stage_index.get(label)
        if st is None:
            self.refresh_stages()
            st = self._stage_index.get(self.cmb_stage.get())
        return st

    def _on_load(self) -> None:
        st = self._current_stage()
        if st is None:
            self.lbl_hint.configure(
                text="还没有关卡可选：关卡目录仍在载入，稍等一下再点「载入」。")
            return
        try:
            gm = get_level(st.stage_id, st.category, self.app.level_cache,
                           rel_path=st.path)
        except Exception as e:
            self.lbl_hint.configure(text="载入失败：%s" % e)
            return
        if gm is None:
            self.lbl_hint.configure(
                text="这张图没有取到数据。\n可能是网络问题，"
                     "或该关卡暂无地图文件（教学关等）。")
            return
        self.stage = st
        self.game_map = gm
        self.timeline = None
        # 出怪时间轴：缓存键优先用地图相对路径（肉鸽换皮图共用一份）
        cands = []
        if st.path:
            cands.append(st.path[:-5] if st.path.endswith(".json") else st.path)
        cands.append(st.stage_id)
        if "#" in st.stage_id:
            cands.append(st.stage_id.split("#", 1)[0])
        raw = None
        try:
            for k in cands:
                raw = self.app.level_cache.load(k)
                if raw:
                    break
        except Exception:
            raw = None
        if raw:
            try:
                tl = parse_timeline(raw)
                self.timeline = fill_names(tl, self._enemy_name_lookup())
            except Exception:
                self.timeline = None

        analyses = RT.analyze_all(gm)
        self.sandbox = Sandbox(gm, self.timeline, analyses,
                               fold_random=bool(self.var_fold_random.get()))
        self._load_spawn_wait(raw)
        tr = self.sandbox.track
        tr.stage_id = st.stage_id
        tr.stage_name = st.label or st.stage_id
        tr.duration = float(getattr(self.timeline, "duration", 0.0) or 0.0)

        self.selected_event = None
        self._picked = []
        self._pending_idx = None
        self._sel_cell = None
        self._now = 0.0
        self.lbl_pending.configure(text="")

        # 机关（传送门 / 火山 / 留声机……）：悬停要显示名称与功能
        try:
            self._mechs = ME.extract(gm)
        except Exception:
            self._mechs = []
        self._portal_map = {}
        try:
            for a, b, certain in ME.portals(self._mechs):
                self._portal_map[(a.row, a.col)] = ((b.row, b.col), certain)
        except Exception:
            pass

        self.canvas.set_map(gm, self.sandbox.analyses)
        self.canvas.portal_link = None   # 换图别把上一张图的传送线带过来
        self.canvas.set_spawn_points(self._spawn_points())
        self._apply_layers()
        self.playback.set_timeline(self._track_total())
        self.playback.seek(0.0)
        self._refresh_frame(0.0)
        self.canvas.set_sandbox(self._render_state())
        self.sandbox.push_history()
        self._fill_events()
        self._fill_picked()
        self._refresh_track()
        self.set_mode(self.mode)
        self._refresh_history_buttons()
        self.lbl_detail.configure(text="")
        self.lbl_hint.configure(
            text="右键「干员选择」里的干员 → 再右键地图可部署格即可落位。")
        self.lbl_detail.configure(
            text="%s　%s×%s　路线 %d 条　出怪 %d 只　时长 %.0fs"
                 % (st.label, gm.width, gm.height, len(gm.routes),
                    getattr(self.timeline, "total_spawns", 0)
                    if self.timeline else 0,
                    getattr(self.timeline, "duration", 0.0)
                    if self.timeline else 0.0))

    def _spawn_points(self):
        """按出怪格汇总，供地图徽标与悬停提示（与寻路分析一致）。"""
        tl, gm = self.timeline, self.game_map
        if not tl or not gm:
            return {}
        routes = {r.index: r for r in gm.routes}
        pts: Dict[tuple, Dict[str, list]] = {}
        for e in getattr(tl, "events", []):
            r = routes.get(getattr(e, "route_index", -1))
            if not r:
                continue
            key = (int(r.start[0]), int(r.start[1]))
            bucket = pts.setdefault(key, {})
            nm = getattr(e, "enemy_name", "") or getattr(e, "enemy_id", "")
            rec = bucket.get(nm)
            if rec is None:
                bucket[nm] = [1, float(getattr(e, "time", 0.0))]
            else:
                rec[0] += 1
                rec[1] = min(rec[1], float(getattr(e, "time", 0.0)))
        out = {}
        for key, bucket in pts.items():
            items = [(nm, n, t) for nm, (n, t) in bucket.items()]
            items.sort(key=lambda x: (x[2], -x[1]))
            out[key] = items
        return out

    # ============================================================ 图层

    def _on_layer(self) -> None:
        self._apply_layers()

    def _apply_layers(self) -> None:
        try:
            self.canvas.show_ground = self.var_ground.get()
            self.canvas.show_fly = self.var_fly.get()
            self.canvas.show_cost = self.var_cost.get()
            # show_mech 没被 MapCanvas 代理，得落到渲染器上；直接给
            # MapCanvas 赋同名属性只会生成一个无用 attribute，设置不生效。
            r = getattr(self.canvas, "_r", None)
            if r is not None:
                r.show_mech = self.var_mech.get()
                r.invalidate()
            self.canvas.redraw()
        except Exception:
            pass

    def _on_flip(self) -> None:
        try:
            self.canvas.set_flip(v=self.var_flip_v.get(),
                                 h=self.var_flip_h.get())
        except Exception:
            pass

    def _zoom_step(self, direction: int) -> None:
        self._zoom = max(1.0, min(4.0, self._zoom * (1.25 ** direction)))
        try:
            self.canvas.set_zoom(self._zoom)
        except Exception:
            pass
        self.lbl_zoom.configure(text="%.2g×" % self._zoom)

    def _reset_view(self) -> None:
        self._zoom = 1.0
        self.lbl_zoom.configure(text="1.0×")
        self.var_flip_v.set(False)
        self.var_flip_h.set(False)
        try:
            self.canvas.set_zoom(1.0)
            self.canvas.set_flip(v=False, h=False)
        except Exception:
            pass

    # ============================================================ 时间与帧

    def _on_playback_time(self, seconds: float) -> None:
        self._now = max(0.0, float(seconds))
        self._refresh_frame(self._now)
        self.canvas.set_sandbox(self._render_state())
        self.track_canvas.set_current_time(self._now)
        self._draw_buff_axis()

    def _refresh_frame(self, seconds: float) -> None:
        """把 seconds 时刻的敌人推到画布上。

        敌人的位置要按**减速后的进度**算，所以不用
        ``timeline.positions_at``（那个按无减速推算），而是逐只调
        ``Sandbox.pose_at``，它内部已经吃过 buff。
        """
        sb = self.sandbox
        if sb is None:
            return
        pos = []
        for ev in sb.live_events():
            t0 = float(getattr(ev, "time", 0.0))
            if t0 > seconds:
                continue
            sp = sb.pose_at(ev, seconds)
            if sp is None:
                continue
            row, col = float(sp[0]), float(sp[1])
            pos.append({
                "row": row, "col": col,
                "row_i": int(round(row)), "col_i": int(round(col)),
                "label": "", "color": getattr(ev, "enemy_id", ""),
                "enemy_id": getattr(ev, "enemy_id", ""),
                "enemy_name": (getattr(ev, "enemy_name", "")
                               or getattr(ev, "enemy_id", "")),
                "time": t0,
                "route_index": getattr(ev, "route_index", -1),
                "seq": getattr(ev, "seq", 0),
                "fraction": 0.0,
                "elapsed": seconds - t0,
                "number": 0,
            })
        self.canvas.set_frame(pos)

    def _on_track_seek(self, seconds: float) -> None:
        self._shift_to(seconds)

    def _on_track_pick(self, uid: int) -> None:
        sb = self.sandbox
        dep = sb.track.get(uid) if sb else None
        if dep is None:
            return
        self._sel_cell = (dep.row, dep.col)
        self.track_canvas.set_selected(uid, redraw=False)
        self.lbl_detail.configure(
            text="粗轴选中：%s\n部署 %.1fs%s"
                 % (dep.name or dep.op_id, dep.deploy_time,
                    ("　撤退 %.1fs" % dep.retreat_time)
                    if dep.retreat_time is not None else "　未撤退"))
        self.canvas.set_sandbox(self._render_state())

    def _on_track_right(self, uid: int, x_root: int, y_root: int) -> None:
        sb = self.sandbox
        dep = sb.track.get(uid) if sb else None
        if dep is None:
            return
        m = self._new_menu()
        m.add_command(label="游标跳到部署 (%.1fs)" % dep.deploy_time,
                      command=lambda: self._shift_to(dep.deploy_time))
        if dep.retreat_time is not None:
            m.add_command(label="游标跳到撤退 (%.1fs)" % dep.retreat_time,
                          command=lambda: self._shift_to(dep.retreat_time))
        m.add_separator()
        piece = sb.operators.get((dep.row, dep.col))
        if piece is not None:
            m.add_command(label="撤退 %s（%.1fs）" % (dep.name, self._now),
                          command=lambda: self._retreat_piece(piece))
        for t in (dep.skill_uses or []):
            m.add_command(label="技能记录 %.1fs" % t, state="disabled")
        m.tk_popup(x_root, y_root)

    def _shift_to(self, seconds: float) -> None:
        """把游标移到某时刻，四处视图同步。

        ``PlaybackBar`` 没有公开的 ``refresh()``，只有内部 ``_refresh()``；
        但 ``seek()`` 本身就会 ``_refresh() + _emit()``，所以这里只需要
        ``pause()`` 再 ``seek()``——多叫一次会叠加两倍重绘。
        """
        seconds = max(0.0, float(seconds))
        try:
            self.playback.pause()
            self.playback.seek(seconds)
        except Exception:
            pass
        self._now = seconds
        self._refresh_frame(seconds)
        self.track_canvas.set_current_time(seconds)
        self._draw_buff_axis()
        self.canvas.set_sandbox(self._render_state())

    # ============================================================ 干员选择

    def _op_library(self):
        if self._op_cache:
            return self._op_cache
        from ..core import prts_operator as PO
        cache = getattr(self.app, "op_cache", None)
        data = getattr(cache, "data", None) or {}
        out: Dict[str, object] = {}
        for name, d in data.items():
            try:
                out[name] = PO.dict_to_op(d)
            except Exception:
                continue
        self._op_cache = out
        self._op_names = sorted(out.keys())
        return out

    def _fill_picker(self) -> None:
        for w in self.op_inner.winfo_children():
            w.destroy()
        lib = self._op_library()
        kw = (self.var_opsearch.get() or "").strip().lower()
        names = self._op_names
        if kw:
            names = [n for n in names if kw in n.lower()]
        # 箱子也当成「可部署对象」出现在干员选择里：用户明确要求
        # 「在干员选择中选择箱子并部署箱子」。它会占一行、能进已选择
        # 列表、能右键待部署，只是落到地图上时走的是 box_check 而不是
        # deploy_check（箱子不能堵死任何一条通往蓝门的路线）。
        if not kw or kw in "箱子box":
            row = tk.Frame(self.op_inner, background=BG_SUNKEN)
            row.pack(fill="x")
            tk.Label(row, text="箱", background=BG_DEEP,
                     foreground=FG_DIM, font=(FONT_UI, FS_MICRO),
                     width=2).pack(side="left", padx=(2, 3), pady=1)
            tk.Label(row, text="箱子（障碍物）", background=BG_SUNKEN,
                     foreground=FG_DIM, font=(FONT_UI, FS_MICRO),
                     anchor="w").pack(side="left", fill="x", expand=True)
            for w in row.winfo_children():
                w.bind("<Button-1>", lambda e: self._pick_operator(BOX_NAME))
                w.bind("<Button-3>", lambda e: self._pick_operator(BOX_NAME))
            row.bind("<Button-1>", lambda e: self._pick_operator(BOX_NAME))
            row.bind("<Button-3>", lambda e: self._pick_operator(BOX_NAME))
        if not names:
            tk.Label(self.op_inner, text="（没有匹配的干员）",
                     background=BG_SUNKEN, foreground=FG_DIM,
                     font=(FONT_UI, FS_MICRO)).pack(pady=PAD_M)
            return
        for nm in names[:400]:
            op = lib.get(nm)
            pos = getattr(op, "position", "") or ""
            mark = "高" if pos == "远程位" else "地"
            row = tk.Frame(self.op_inner, background=BG_SUNKEN)
            row.pack(fill="x")
            av = self._make_avatar_label(row, nm, mark, BG_DEEP, ACCENT_TXT)
            av.pack(side="left", padx=(2, 3), pady=1)
            tk.Label(row, text=nm, background=BG_SUNKEN, foreground=FG,
                     font=(FONT_UI, FS_MICRO), anchor="w").pack(
                side="left", fill="x", expand=True)
            for w in row.winfo_children():
                w.bind("<Button-1>", lambda e, n=nm: self._pick_operator(n))
                w.bind("<Button-3>", lambda e, n=nm: self._pick_operator(n))
            row.bind("<Button-1>", lambda e, n=nm: self._pick_operator(n))
            row.bind("<Button-3>", lambda e, n=nm: self._pick_operator(n))

    def _make_avatar_label(self, parent, name: str, fallback: str,
                           bg: str, fg: str):
        """造一个 24×24 头像 Label；取不到图标时退回「高/地」文本 Label。

        同步加载（``OI.load_icon`` 只读本地缓存），保证列表重建后头像
        立即到位，不会出现异步回调把旧列表里的 Label 换掉的竞态。
        PhotoImage 存进 ``self._photos``，否则会被 GC 回收成白块。
        """
        from ..core import operator_icons as OI
        try:
            im = OI.load_icon(self.app.paths, name, 24)
        except Exception:
            im = None
        if im is not None and ImageTk is not None:
            try:
                photo = ImageTk.PhotoImage(im)
                self._photos[name] = photo
                return tk.Label(parent, image=photo, background=bg,
                                width=24, height=24)
            except Exception:
                pass
        return tk.Label(parent, text=fallback, background=bg, foreground=fg,
                        font=(FONT_UI, FS_MICRO), width=2)

    def _pick_operator(self, name: str) -> None:
        if name == BOX_NAME:
            self._pick_box()
            return
        lib = self._op_library()
        op = lib.get(name)
        if op is None:
            return
        if any(p["name"] == name for p in self._picked):
            self.lbl_detail.configure(text="%s 已经在已选择列表里了" % name)
            return
        pos = getattr(op, "position", "") or ""
        is_ranged = (pos == "远程位")
        st = None
        for elite, level in ((2, 90), (2, 80), (1, 70), (0, 1)):
            try:
                st = op.stats_at(elite, level)
            except Exception:
                st = None
            if st is not None:
                break
        skills = list(getattr(op, "skills", None) or [])
        interval = float(getattr(st, "attack_interval", 1.0) or 1.0) if st else 1.0
        item = {
            "op": op, "name": name, "is_ranged": is_ranged,
            "block": int(getattr(st, "block", 0) or 0) if st else 0,
            "interval": interval,
            "cost": int(getattr(st, "cost", 0) or 0) if st else 0,
            "skills": skills,
            "skill": self._default_skill(skills, interval),
            "block_fly": False,
            "sp_boost": self._sp_boost_of_op(op),
        }
        self._picked.append(item)
        self._fill_picked()
        self.lbl_detail.configure(
            text="已加入 %s（%s）。右键它 → 再右键地图%s格即可落位。"
                 % (name, "高台" if is_ranged else "地面",
                    "高台" if is_ranged else "地面"))

    def _default_skill(self, skills, interval: float = 1.0):
        """选默认技能（薄壳，见模块级 ``_default_skill_of``）。"""
        return _default_skill_of(skills, interval)

    def _pick_box(self) -> None:
        """把「箱子」加进已选择列表（和干员同一条流水线）。

        箱子也是右键→待部署→右键地图，但落位时用的是 ``box_check``：
        箱子的唯一作用是**改变寻路**，而它不能把任何一条通往蓝门的路线
        堵死（``box_check`` 逐格试放 + 重算，比较可达性）。
        """
        if any(p["name"] == BOX_NAME for p in self._picked):
            self.lbl_detail.configure(text="箱子已经在已选择列表里了")
            return
        item = {
            "op": None, "name": BOX_NAME, "is_ranged": False,
            "block": 0, "interval": 1.0, "cost": 0,
            "skills": [], "skill": None,
            "block_fly": False, "sp_boost": 0.0,
            "is_box": True,
        }
        self._picked.append(item)
        self._fill_picked()
        self.lbl_detail.configure(
            text="箱子已加入。右键它 → 再右键地图任意格即可放置；"
                 "会堵死通往蓝门路线的位置会被拒绝。")

    def _sp_boost_of_op(self, op) -> float:
        """这枚干员给别人加多少技力自然回复（点/秒）。

        用户要求「部分干员能给彼此交互 增加 sp 回复速度」。数据里只有
        **天赋/技能的文字描述**，没有结构化字段，所以用
        ``sp_boost_of_text`` 做文本解析；解析不出来就是 0（不猜）。
        """
        best = 0.0
        try:
            for tal in (getattr(op, "talents", None) or []):
                txt = plain(str(tal[1]) if len(tal) > 1 else "")
                best = max(best, sp_boost_of_text(txt))
            for sk in (getattr(op, "skills", None) or []):
                lv = None
                for k in (getattr(sk, "level_keys", None) or []):
                    lv = sk.level(k)
                if lv is None:
                    continue
                best = max(best, sp_boost_of_text(
                    plain(getattr(lv, "description", "") or "")))
        except Exception:
            return best
        return best

    def _fill_picked(self) -> None:
        for w in self.pick_inner.winfo_children():
            w.destroy()
        if not self._picked:
            tk.Label(self.pick_inner, text="（还没有选干员）",
                     background=BG_SUNKEN, foreground=FG_DIM,
                     font=(FONT_UI, FS_MICRO)).pack(pady=PAD_M)
            return
        for i, item in enumerate(self._picked):
            pending = (self._pending_idx == i)
            bg = ACCENT_SOFT if pending else BG_SUNKEN
            row = tk.Frame(self.pick_inner, background=bg)
            row.pack(fill="x", pady=1)
            if item.get("is_box"):
                # 箱子没有「高台/地面」也没有技能，别去 getattr 一个 None
                pos = "障碍"
            else:
                pos = "高台" if item["is_ranged"] else "地面"
            if item.get("is_box"):
                av = self._make_avatar_label(row, BOX_NAME, "箱", bg,
                                             FG if pending else FG_DIM)
            else:
                av = self._make_avatar_label(row, item["name"], pos, bg,
                                             FG if pending else FG_DIM)
            av.pack(side="left", padx=(3, 2))
            tk.Label(row, text="%s %s" % (pos, item["name"]), background=bg,
                     foreground=FG if pending else FG_DIM,
                     font=(FONT_UI, FS_MICRO), anchor="w").pack(
                side="left", padx=(3, 2))
            del_btn = tk.Label(row, text="✕", background=bg, foreground=FG_DIM,
                               font=(FONT_UI, FS_MICRO))
            del_btn.pack(side="right", padx=(2, 3))
            del_btn.bind("<Button-1>", lambda e, idx=i: self._drop_picked(idx))
            names = [getattr(s, "name", "") or ("技能%d" % (j + 1))
                     for j, s in enumerate(item.get("skills") or [])]
            if names:
                var = tk.StringVar()
                cur = item["skill"]
                var.set(getattr(cur, "name", "") if cur is not None
                        else names[0])
                cb = ComboBox(row, width=9, values=names, textvariable=var)
                cb.pack(side="right", padx=(0, 3))
                cb.bind("<<ComboboxSelected>>",
                        lambda e, idx=i, v=var: self._on_pick_skill(idx, v))
            for w in row.winfo_children():
                if w is del_btn:
                    continue
                w.bind("<Button-3>", lambda e, idx=i: self._arm_pending(idx))
            row.bind("<Button-3>", lambda e, idx=i: self._arm_pending(idx))
            row.bind("<Double-Button-1>",
                     lambda e, idx=i: self._arm_pending(idx))

    def _on_pick_skill(self, idx: int, var) -> None:
        if not (0 <= idx < len(self._picked)):
            return
        item = self._picked[idx]
        want = var.get()
        for s in item["skills"]:
            if (getattr(s, "name", "") or "") == want:
                item["skill"] = s
                break

    def _drop_picked(self, idx: int) -> None:
        if 0 <= idx < len(self._picked):
            self._picked.pop(idx)
            if self._pending_idx == idx:
                self._pending_idx = None
            elif self._pending_idx is not None and self._pending_idx > idx:
                self._pending_idx -= 1
            self._fill_picked()

    def _arm_pending(self, idx: int) -> None:
        """右键已选择列表：进入「待部署」，然后等一次地图右键。"""
        if not (0 <= idx < len(self._picked)):
            return
        self._pending_idx = None if self._pending_idx == idx else idx
        item = self._picked[idx]
        if self._pending_idx is None:
            self.lbl_pending.configure(text="")
            self.lbl_pick_hint.configure(
                text="右键已选择列表里的干员 → 再右键地图可部署格即可落位")
        else:
            if item.get("is_box"):
                self.lbl_pending.configure(text="待放置：箱子")
                self.lbl_pick_hint.configure(
                    text="现在右键地图上任意格 → 箱子会放到那里（会重算路径，"
                         "堵死蓝门的位置会被拒绝）。（右键同一项可取消）")
                self._fill_picked()
                return
            kind = "高台" if item["is_ranged"] else "地面"
            self.lbl_pending.configure(text="待部署：%s" % item["name"])
            self.lbl_pick_hint.configure(
                text="现在右键地图上的%s格 → %s 会落到那里。"
                     "（右键同一项可取消）" % (kind, item["name"]))
        self._fill_picked()

    # ============================================================ 右键地图

    def _on_cell_right_click(self, r: int, c: int, enemy) -> None:
        sb = self.sandbox
        if sb is None:
            return
        if enemy is not None:
            self._menu_enemy(enemy)
            return
        if r < 0 or c < 0:
            return
        if self._pending_idx is not None:
            self._deploy_pending(r, c)
            return
        piece = sb.operator_at(r, c)
        if piece is not None:
            self._menu_piece(piece)
            return
        self._menu_cell(r, c)

    def _deploy_pending(self, r: int, c: int) -> None:
        sb = self.sandbox
        if sb is None or self._pending_idx is None:
            return
        if not (0 <= self._pending_idx < len(self._picked)):
            self._pending_idx = None
            return
        item = self._picked[self._pending_idx]
        if item.get("is_box"):
            # 箱子走另一套判定：不看「能不能部署」，看「会不会堵死蓝门」
            ok, why = sb.box_check(r, c)
            if not ok:
                self.lbl_detail.configure(
                    text="不能在这里放箱子 (%d,%d)：%s" % (r, c, why))
                return
            sb.place_box(r, c)
            sb.push_history()
            self._pending_idx = None
            self.lbl_pending.configure(text="")
            self.lbl_pick_hint.configure(
                text="箱子已放置。它会重算路径；右键箱子可以移除。")
            self._fill_picked()
            self.lbl_detail.configure(
                text="箱子已放到 (%d,%d)。路线已重算——"
                     "看下方粗轴与右侧出怪的到达时间有没有变。"
                     % (r, c))
            self._after_change()
            return
        ok, why = sb.deploy_check(r, c, item["is_ranged"])
        if not ok:
            self.lbl_detail.configure(
                text="不能放在 (%d,%d)：%s" % (r, c, why))
            return
        cyc = self._skill_cycle_of(item.get("skill"), item.get("interval", 1.0))
        dep = Deployment(
            uid=0, row=r, col=c,
            op_id=str(getattr(item["op"], "char_id", "") or ""),
            name=item["name"],
            profession=str(getattr(item["op"], "profession", "") or ""),
            ground="HIGH" if item["is_ranged"] else "LOW",
            block_count=int(item.get("block", 0) or 0),
            is_ranged=bool(item["is_ranged"]),
            can_block_fly=bool(item.get("block_fly", False)),
            facing=self.facing, deploy_time=self._now, skill=cyc,
            skill_name=str(getattr(item.get("skill"), "name", "") or ""),
            cost=int(item.get("cost", 0) or 0),
            sp_boost=float(item.get("sp_boost", 0.0) or 0.0))
        if not sb.deploy(r, c, dep):
            self.lbl_detail.configure(text="(%d,%d) 已经有干员了" % (r, c))
            return
        sb.push_history()
        self._pending_idx = None
        self.lbl_pending.configure(text="")
        self.lbl_pick_hint.configure(
            text="已落位。右键场上的干员可以撤退 / 开技能。")
        self._fill_picked()
        cyc_cn = SP_CN.get(cyc.recover, cyc.recover)
        extra = ""
        if dep.sp_boost:
            extra = "　技力光环 +%.2f/s" % dep.sp_boost
        self.lbl_detail.configure(
            text="%s 已部署到 (%d,%d)，时刻 %.1fs。\n阻挡 %d，技能 %s（%s）%s"
                 % (item["name"], r, c, self._now, dep.blocking,
                    dep.skill_name or "—", cyc_cn, extra))
        self._after_change()

    def _skill_cycle_of(self, skill, interval: float) -> SkillCycle:
        """把 ``core.skills.Skill`` 翻成 ``SkillCycle``（薄壳，见模块级同名函数）。"""
        return _cycle_of(skill, interval)


    def _menu_piece(self, piece) -> None:
        """右键场上干员：撤退 / 开技能 / 改朝向 / 挡飞行 / 看回转。"""
        sb = self.sandbox
        if sb is None:
            return
        dep = sb.track.get(int(getattr(piece, "uid", 0) or 0))
        m = self._new_menu()
        m.add_command(label="撤退 %s（%.1fs）" % (piece.name, self._now),
                      command=lambda: self._retreat_piece(piece))
        if dep is not None:
            # SP 没满时按钮仍然要能点（用户可能就想记一个「我要在这时开」的
            # 计划点），但**必须**在文案里说清现在点下去会发生什么：以前不
            # 管 SP 多少都写「开启技能」，点了以后也只回一句「已记录…开
            # 技能」，看起来像技能真的开了，而悬停里 SP 还是 40/50。
            _st_now = sb.skill_state(dep, self._now)
            if _st_now.get("passive"):
                _lbl = "开启技能（%.1fs，被动无 SP）" % self._now
            elif _st_now.get("active"):
                _lbl = "开启技能（%.1fs，技能中）" % self._now
            elif _st_now.get("ready"):
                _lbl = "开启技能（%.1fs，SP 已满）" % self._now
            else:
                _lbl = ("开启技能（%.1fs，SP %.0f/%.0f 未满，仅记时刻）"
                        % (self._now, _st_now.get("sp", 0),
                           _st_now.get("need", 0)))
            m.add_command(label=_lbl, command=lambda: self._use_skill(dep))
        m.add_separator()
        for f in FACINGS:
            m.add_command(label="朝向 " + FACING_CN[f],
                          command=lambda ff=f: self._set_facing(piece, ff))
        if dep is not None:
            m.add_separator()
            fly = bool(getattr(piece, "can_block_fly", False))
            m.add_command(
                label=("取消对空阻挡" if fly else "开启对空阻挡（能挡飞行敌人）"),
                command=lambda: self._toggle_block_fly(piece))
            m.add_separator()
            st = sb.skill_state(dep, self._now)
            m.add_command(label=self._skill_text(dep, st), state="disabled")
            m.add_command(label="挡住的敌人：%d 只" % sb.blocked_count(piece,
                                                                     self._now),
                          state="disabled")
        m.tk_popup(self.winfo_pointerx(), self.winfo_pointery())

    def _skill_text(self, dep, st: dict) -> str:
        """技能状态的单行描述，右键菜单与悬停共用。"""
        if st.get("passive"):
            return "技能：被动 / 无 SP"
        if st.get("active"):
            if st.get("next_in") is not None:
                return "技能中，还剩 %.1fs" % st["next_in"]
            return "技能中"
        if st.get("ready"):
            return "技能就绪（SP 已满）"
        if st.get("next_in") is not None:
            return "SP %.0f/%.0f，还需 %.1fs" % (st.get("sp", 0),
                                                 st.get("need", 0),
                                                 st["next_in"])
        return "SP %.0f/%.0f" % (st.get("sp", 0), st.get("need", 0))

    def _retreat_piece(self, piece) -> None:
        sb = self.sandbox
        if sb is None:
            return
        name = piece.name
        if sb.retreat(piece.row, piece.col, self._now):
            sb.push_history()
            self.lbl_detail.configure(
                text="%s 已在 %.1fs 撤退，粗轴已记录" % (name, self._now))
            self._after_change()

    def _use_skill(self, dep) -> None:
        sb = self.sandbox
        if sb is None:
            return
        # 先取状态再记录：记录之后 SP 并不会跳变（这里只记时刻），但如果
        # 先记后取，用户看到的那句话就对不上「点之前屏幕上的数」。
        st = sb.skill_state(dep, self._now)
        if not sb.use_skill(dep, self._now):
            return
        sb.push_history()
        who = dep.name or dep.op_id
        if st.get("passive"):
            note = "被动技能，没有 SP 回转，只记了时刻"
        elif st.get("active"):
            note = "技能本来就在进行中，又记了一次施放时刻"
        elif st.get("ready"):
            note = "SP 已满，记下了这次施放"
        else:
            # 这句是关键：说清「记的是计划点，不是真的开成功」。
            note = ("SP 只有 %.0f/%.0f，还没转好；只记下这个时刻，"
                    "SP 回转仍按模拟结果算" % (st.get("sp", 0),
                                               st.get("need", 0)))
        self.lbl_detail.configure(
            text="%s 在 %.1fs 开技能：%s（只记时刻与回转，不模拟技能效果）"
                 % (who, self._now, note))
        self._after_change()

    def _set_facing(self, piece, facing: str) -> None:
        piece.facing = facing
        piece.range_cells = None
        sb = self.sandbox
        if sb is not None:
            sb.push_history()
        self._after_change()

    def _toggle_block_fly(self, piece) -> None:
        sb = self.sandbox
        if sb is None:
            return
        want = not bool(getattr(piece, "can_block_fly", False))
        sb.set_block_fly(piece, want)
        sb.push_history()
        self.lbl_detail.configure(
            text="%s %s 阻挡飞行敌人" % (piece.name,
                                        "现在可以" if want else "不再"))
        self._after_change()

    def _menu_cell(self, r: int, c: int) -> None:
        sb = self.sandbox
        if sb is None:
            return
        m = self._new_menu()
        if (r, c) in sb.boxes:
            m.add_command(label="移除箱子 (%d,%d)" % (r, c),
                          command=lambda: self._toggle_box(r, c))
        else:
            m.add_command(label="放箱子 (%d,%d)" % (r, c),
                          command=lambda: self._toggle_box(r, c))
        routes = sb.routes_through(r, c)
        m.add_command(label=("路线 %s 经过这里"
                             % "、".join(str(x) for x in routes[:6]))
                      if routes else "没有路线经过这里", state="disabled")
        tp = self._portal_text(r, c)
        if tp:
            m.add_command(label=tp, state="disabled")
        m.tk_popup(self.winfo_pointerx(), self.winfo_pointery())

    def _toggle_box(self, r: int, c: int) -> None:
        sb = self.sandbox
        if sb is None:
            return
        if (r, c) in sb.boxes:
            sb.remove_box(r, c)
            sb.push_history()
            self.lbl_detail.configure(text="已移除 (%d,%d) 的箱子" % (r, c))
        else:
            ok, why = sb.box_check(r, c)
            if not ok:
                # 用户的硬要求：箱子不能堵死通往蓝门的路线
                self.lbl_detail.configure(
                    text="不能放在 (%d,%d)：%s" % (r, c, why))
                return
            sb.place_box(r, c)
            sb.push_history()
            self.lbl_detail.configure(text="已在 (%d,%d) 放箱子" % (r, c))
        self._after_change()

    def _menu_enemy(self, enemy) -> None:
        sb = self.sandbox
        if sb is None:
            return
        ev = self._event_of(enemy)
        if ev is None:
            m = self._new_menu()
            m.add_command(label="（这张图上没匹配到这只怪）", state="disabled")
            m.tk_popup(self.winfo_pointerx(), self.winfo_pointery())
            return
        self._menu_enemy_ev(ev)

    def _event_of(self, enemy):
        """把画布给的敌人 dict 对回出怪事件。

        画布 ``frame_enemies`` 用 ``(route_index, seq)`` 就能唯一定位；
        对不上时退回「同 enemy_id 且出场时刻最接近」，误差超过 3 秒
        就认为不是同一只。
        """
        sb = self.sandbox
        if sb is None or not isinstance(enemy, dict):
            return None
        evs = sb.events()
        ri = enemy.get("route_index")
        seq = enemy.get("seq")
        if ri is not None and seq is not None:
            for ev in evs:
                if (getattr(ev, "route_index", None) == ri
                        and getattr(ev, "seq", None) == seq):
                    return ev
        eid = enemy.get("enemy_id") or enemy.get("id")
        t = enemy.get("time")
        best, best_d = None, 1e9
        for ev in evs:
            if eid and getattr(ev, "enemy_id", None) != eid:
                continue
            if t is None:
                continue
            d = abs(float(getattr(ev, "time", 0.0)) - float(t))
            if d < best_d:
                best, best_d = ev, d
        return best if best_d <= 3.0 else None

    def _add_stop(self, ev, duration: float, mult: float) -> None:
        sb = self.sandbox
        if sb is None:
            return
        # mult 允许 0（=完全停住）。夹到 0.05 会把「停顿 3 秒」变成
        # 20 倍慢放，凭空多出几十秒行程。
        sb.add_slow(ev, max(0.0, min(1.0, float(mult))), float(duration),
                    start=self._now)
        sb.push_history()
        name = getattr(ev, "enemy_name", "") or getattr(ev, "enemy_id", "")
        if mult <= 0:
            self.lbl_detail.configure(
                text="%s 从 %.1fs 起停顿 %.1fs（动画会跟着变）"
                     % (name, self._now, duration))
        else:
            self.lbl_detail.configure(
                text="%s 从 %.1fs 起减速到 ×%.2f，持续 %.1fs"
                     % (name, self._now, mult, duration))
        self._after_change()

    def _ask_stop(self, ev) -> None:
        """自定义时长 / 倍率的小对话框。"""
        top = tk.Toplevel(self)
        top.title("自定义停顿 / 减速")
        top.configure(background=BG_PANEL)
        top.transient(self)
        top.resizable(False, False)
        name = getattr(ev, "enemy_name", "") or getattr(ev, "enemy_id", "")
        tk.Label(top, text="%s　从 %.1fs 起" % (name, self._now),
                 background=BG_PANEL, foreground=FG,
                 font=(FONT_UI, FS_SMALL)).grid(row=0, column=0, columnspan=2,
                                                padx=PAD_M,
                                                pady=(PAD_M, PAD_S),
                                                sticky="w")
        var_d = tk.StringVar(value="3")
        var_m = tk.StringVar(value="0.0")
        for i, (text, var) in enumerate((("持续（秒）", var_d),
                                         ("速度倍率（0=停住）", var_m)), start=1):
            tk.Label(top, text=text, background=BG_PANEL, foreground=FG_DIM,
                     font=(FONT_UI, FS_SMALL)).grid(
                row=i, column=0, sticky="e", padx=(PAD_M, PAD_S), pady=PAD_XS)
            tk.Entry(top, textvariable=var, width=8, background=BG_INPUT,
                     foreground=FG, insertbackground=FG, relief="flat",
                     font=(FONT_UI, FS_SMALL)).grid(
                row=i, column=1, sticky="w", padx=(0, PAD_M), pady=PAD_XS)

        def ok():
            try:
                dd = float(var_d.get())
                mm = float(var_m.get())
            except (TypeError, ValueError):
                return
            top.destroy()
            self._add_stop(ev, max(0.1, dd), max(0.0, min(1.0, mm)))

        bf = tk.Frame(top, background=BG_PANEL)
        bf.grid(row=3, column=0, columnspan=2, pady=PAD_M)
        tk.Button(bf, text="确定", relief="flat", background=ACCENT_SOFT,
                  foreground=FG, activebackground=ACCENT, activeforeground=BG,
                  font=(FONT_UI, FS_SMALL), highlightthickness=0,
                  cursor="hand2", padx=PAD_M, pady=1,
                  command=ok).pack(side="left", padx=PAD_XS)
        tk.Button(bf, text="取消", relief="flat", background=BG_DEEP,
                  foreground=FG_DIM, activebackground=ACCENT_SOFT,
                  activeforeground=FG, font=(FONT_UI, FS_SMALL),
                  highlightthickness=1, highlightbackground=BORDER,
                  cursor="hand2", padx=PAD_M, pady=1,
                  command=top.destroy).pack(side="left", padx=PAD_XS)
        top.grab_set()

    def _kick_toggle(self, ev) -> None:
        sb = self.sandbox
        if sb is None:
            return
        if sb.is_kicked(ev):
            sb.unkick(ev)
        else:
            sb.kick(ev)
        sb.push_history()
        self._after_change()

    def _clear_one(self, ev) -> None:
        sb = self.sandbox
        if sb is None:
            return
        sb.clear_buffs(ev)
        sb.push_history()
        self._after_change()

    def _new_menu(self):
        m = tk.Menu(self, tearoff=0, background=BG_PANEL, foreground=FG,
                    activebackground=ACCENT, activeforeground=BG,
                    font=(FONT_UI, FS_SMALL), bd=0)
        self._menu = m
        return m

    # ============================================================ 悬停

    def _on_object_hover(self, kind, payload) -> None:
        if kind == "enemy":
            self._hover_enemy(payload)
        elif kind == "tile":
            self._hover_tile(payload)
        else:
            self.lbl_hover.configure(text="")

    def _hover_enemy(self, enemy) -> None:
        """悬停敌人：是否被阻挡 / 是否罚站且还剩多久 / 是否被减速。"""
        sb = self.sandbox
        if sb is None:
            return
        ev = self._event_of(enemy)
        if ev is None:
            nm = (enemy.get("enemy_name") or enemy.get("enemy_id") or "敌人")
            self.lbl_hover.configure(text="%s（未匹配到出怪表条目）" % nm)
            return
        f = sb.enemy_flags(ev, self._now)
        name = getattr(ev, "enemy_name", "") or getattr(ev, "enemy_id", "")
        parts = [name]
        if f["flying"]:
            parts.append("飞行")
        if f["gone"]:
            parts.append("已离场")
        if f["blocked"]:
            pc = f["blocked_by"]
            parts.append("被 %s 阻挡" % (getattr(pc, "name", "") or "干员"))
        else:
            parts.append("未被阻挡")
        if f["waiting"]:
            parts.append("罚站中，还剩 %.1fs" % f["wait_left"])
        else:
            parts.append("未罚站")
        if f["slowed"] < 0.999:
            parts.append("速度 ×%.2f" % f["slowed"])
        arr = sb.arrival_time(ev)
        if arr is not None:
            # arrival_time 返回的是**历时**（从出场算起走完全程要多久），
            # 悬停时用户真正想知道的是「第几秒到蓝门」，所以补一个绝对
            # 时刻。两者都给，免得用户自己加一遍出场时间。
            parts.append("到达 %.1fs（历时 %.1fs）"
                         % (float(getattr(ev, "time", 0.0)) + arr, arr))
        self.lbl_hover.configure(text="　·　".join(parts))

    def _hover_tile(self, pos) -> None:
        """悬停地块：高度 / 可部署 / 装置名称与功能 / 传送门去向。"""
        sb = self.sandbox
        if self.game_map is None:
            return
        r, c = int(pos[0]), int(pos[1])
        tile = sb.tile_at(r, c) if sb else None
        parts = ["(%d,%d)" % (r, c)]
        if tile is None:
            # 地图边界外：以前这里只显示一个坐标就结束，看着像「功能坏了」。
            # 明说落在图外，用户才知道该往格子里挪。
            parts.append("地图外（本图 %s）"
                         % ("%d×%d" % (sb.game_map.width, sb.game_map.height)
                            if sb is not None and sb.game_map is not None
                            else "范围外"))
        if tile is not None:
            ht = str(getattr(tile, "height_type", "") or "").upper()
            parts.append("高台" if ht == "HIGHLAND" else "地面")
            bt = str(getattr(tile, "buildable_type", "") or "")
            parts.append({"MELEE": "可放近战", "RANGED": "可放远程",
                          "ALL": "可放任意"}.get(bt, "不可部署"))
            key = str(getattr(tile, "tile_key", "") or "")
            rec = ME.info(key) if key else None
            if rec:
                # 装置名称 + 一句话功能（core/mechanisms 里 96 个 tileKey）
                parts.append("%s：%s" % (rec[1], rec[2]) if rec[2] else rec[1])
        op = sb.operator_at(r, c) if sb else None
        if op is not None:
            # 悬停干员必须能直接看出「技能转好没有」，否则判断什么时候开
            # 技能得先右键一次、再读弹窗，等于每回合多两步操作。
            # 这里复用右键弹窗的同一套文案（_skill_text），两处口径一致。
            head = "干员 %s（%s）" % (op.name,
                                     FACING_CN.get(op.facing, op.facing))
            blk = int(getattr(op, "block_count", 0) or 0)
            if not getattr(op, "is_ranged", False) and blk:
                head += " 阻挡 %d" % blk
            dep = sb.track.get(int(getattr(op, "uid", 0) or 0)) if sb else None
            if dep is not None:
                try:
                    sk_txt = self._skill_text(dep, sb.skill_state(dep, self._now))
                except Exception:
                    sk_txt = ""
                if sk_txt:
                    head += "　·　" + sk_txt
            parts.append(head)
        if sb is not None and (r, c) in sb.boxes:
            parts.append("箱子")
        tp = self._portal_text(r, c)
        if tp:
            parts.append(tp)
        self.lbl_hover.configure(text="　·　".join(parts))

    def _portal_text(self, r: int, c: int) -> str:
        """这一格是传送门的话，说明它送去哪（含配对可信度）。"""
        hit = self._portal_map.get((r, c))
        if not hit:
            return ""
        dest, certain = hit
        return "传送门 → (%d,%d)%s" % (dest[0], dest[1],
                                       "" if certain else "（配对为推断）")

    def _portal_path(self, r: int, c: int):
        """算「从这扇门进去，从对面哪一格出来，再往blue门怎么走」。

        解包数据里几乎没有传送门的配对字段（``ME.portals`` 是按曼哈顿
        距离最近原则**推断**出来的），所以这里除了给出路径，还要把「配对
        是否可信」一并交回去，界面上才能标成琥珀色的推断线。

        两段路分开算，因为它们性质完全不同：

        * ``jump``：入口格 → 出口格。传送是**空间跳跃**，这一段的实际
          可达路径通常不存在（中间隔着不可通行区），用 ``force_open``
          强行算出来只会在走廊里绕一圈，没有意义。有就用，没有就让渲染
          器画虚线直连。
        * ``exit_path``：出口格 → 最近的蓝门。这才是用户要看的——「从这
          儿冒出来的敌人会往哪走」。按地面单位口径算，箱子算障碍。
        """
        hit = self._portal_map.get((r, c))
        gm = self.game_map
        if not hit or gm is None:
            return None
        dest, certain = hit
        src = (int(r), int(c))
        dst = (int(dest[0]), int(dest[1]))
        blocked = set(self.sandbox.boxes) if self.sandbox else set()

        jump = []
        try:
            res = PF.find_path(gm, src, dst, flying=False, blocked=blocked,
                               force_open={src, dst})
            if getattr(res, "found", False):
                jump = list(res.path or [])
        except Exception:
            jump = []

        # 出口 -> 最近的蓝门 / 终点：逐个候选取最短
        exit_path = []
        goals = []
        try:
            for rt in (gm.routes or []):
                end = tuple(getattr(rt, "end", ()) or ())
                if len(end) == 2 and end not in goals:
                    goals.append(end)
            # GameMap 只有 goal_tiles（没有 goals）。原先写成 gm.goals，
            # 被 getattr 的默认值掩盖，于是蓝门候选只剩「路线终点」这一路
            # 来源；若某关的 goal_tiles 与路线终点不重合，出口路径就会算空。
            for gp in (getattr(gm, "goal_tiles", None) or []):
                g = tuple(gp) if not hasattr(gp, "row") else (gp.row, gp.col)
                if len(g) == 2 and g not in goals:
                    goals.append(g)
        except Exception:
            goals = []
        best = None
        for g in goals:
            if g == dst:
                continue
            try:
                res = PF.find_path(gm, dst, g, flying=False, blocked=blocked,
                                   force_open={dst, g})
            except Exception:
                continue
            if getattr(res, "found", False) and res.path:
                if best is None or res.length < best[0]:
                    best = (float(res.length), list(res.path))
        if best is not None:
            exit_path = best[1]

        return {"src": src, "dst": dst, "certain": bool(certain),
                "jump": jump, "exit_path": exit_path}

    def _show_portal_path(self, r: int, c: int) -> bool:
        """在地图上标出这扇门的去向，并把路径摘要写进悬停栏。

        只画线是不够的：线在密集格子里容易看糊，也不告诉你「从哪进、
        从哪出、出去之后往哪走」。所以这里同时把摘要写进 ``lbl_hover``，
        让点击传送门这件事有**文字结果**，而不只是多了一条线。
        """
        link = self._portal_path(r, c)
        if not link:
            self.canvas.portal_link = None
            self.lbl_hover.configure(text="(%d,%d)　不是传送门" % (r, c))
            self.canvas.redraw()
            return False
        self.canvas.portal_link = link
        self.canvas.redraw()
        # 摘要：入口 → 出口（配对可信度）→ 出口后走多远到蓝门
        # 注意 _portal_path 返回的是 **dict**（不是对象），用 link.get 取。
        dst = link.get("dst")
        parts = ["传送门 (%d,%d)" % (r, c)]
        if dst is not None:
            parts.append("出口 (%d,%d)" % (int(dst[0]), int(dst[1])))
        if not link.get("certain", True):
            parts.append("配对为推断")
        n_exit = len(link.get("exit_path") or [])
        if n_exit > 1:
            parts.append("出去后 %d 格到蓝门" % (n_exit - 1))
        else:
            parts.append("出口到不了蓝门")
        self.lbl_hover.configure(text="　·　".join(parts))
        return True

    def _clear_portal_path(self) -> None:
        if getattr(self.canvas, "portal_link", None) is not None:
            self.canvas.portal_link = None
            self.canvas.redraw()

    def _on_enemy_click(self, enemy) -> None:
        """左键点敌人：定位到它的出场时刻并选中。"""
        sb = self.sandbox
        if sb is None:
            return
        ev = self._event_of(enemy)
        if ev is None:
            return
        self.selected_event = ev
        self._shift_to(float(getattr(ev, "time", 0.0)))
        self._hover_enemy(enemy)

    # ============================================================ 地图左键

    def _on_cell_click(self, r: int, c: int) -> None:
        sb = self.sandbox
        if sb is None:
            return
        self._sel_cell = (r, c)
        if self.mode == MODE_OPERATOR:
            if (r, c) in sb.operators:
                sb.retreat(r, c, self._now)
            else:
                piece = sb.place_operator(r, c, op_id="", name="干员",
                                          profession="", facing=self.facing)
                piece.is_ranged = bool(
                    sb.tile_at(r, c) is not None
                    and getattr(sb.tile_at(r, c), "buildable_ranged", False)
                    and not getattr(sb.tile_at(r, c), "buildable_melee", False))
                piece.block_count = 0 if piece.is_ranged else 1
                piece.ground = "HIGH" if piece.is_ranged else "LOW"
            sb.push_history()
            self._after_change()
            return
        if self.mode == MODE_BOX:
            self._toggle_box(r, c)
            return
        routes = sb.routes_through(r, c)
        op = sb.operator_at(r, c)
        parts = ["格 (%d,%d)" % (r, c)]
        if (r, c) in sb.boxes:
            parts.append("这里有箱子（已改变寻路）")
        if op:
            parts.append("干员 %s（%s）"
                         % (op.name, FACING_CN.get(op.facing, op.facing)))
            dep = sb.track.get(int(getattr(op, "uid", 0) or 0))
            if dep is not None:
                parts.append(self._skill_text(dep,
                                              sb.skill_state(dep, self._now)))
        if routes:
            parts.append("路线 %s 会经过"
                         % "、".join(str(x) for x in routes[:8]))
        else:
            parts.append("没有路线经过")
        if (r, c) in sb.overlap():
            parts.append("⚠ 干员站在路线上：敌人会在这里被阻挡")
        tp = self._portal_text(r, c)
        if tp:
            parts.append(tp)
        # 点传送门：把「进去之后从哪出来、往蓝门怎么走」画出来
        link = self._portal_path(r, c)
        if link:
            self.canvas.portal_link = link
            if link["exit_path"]:
                parts.append("出口→蓝门 %d 格%s"
                             % (len(link["exit_path"]) - 1,
                                "" if link["certain"]
                                else "（传送门配对为推断，仅供参考）"))
            else:
                parts.append("出口→蓝门这段算不通（出口被围死或本图没路线）")
        else:
            self.canvas.portal_link = None
        self.lbl_detail.configure(text="\n".join(parts))
        self._after_change()

    def _after_change(self) -> None:
        sb = self.sandbox
        if not sb:
            return
        self.canvas.set_map(sb.game_map, sb.analyses)
        self.canvas.set_spawn_points(self._spawn_points())
        self._apply_layers()
        self._refresh_frame(self._now)
        self.canvas.set_sandbox(self._render_state())
        self._fill_events()
        self._refresh_track()
        self.set_mode(self.mode)
        self._refresh_history_buttons()

    def _refresh_history_buttons(self) -> None:
        """撤销/重做按钮的可用态（工具栏每步都跟着刷新）。"""
        sb = self.sandbox
        has_undo = bool(sb and sb._undo_stack)
        has_redo = bool(sb and sb._redo_stack)
        for name, on in (("undo", has_undo), ("redo", has_redo)):
            b = getattr(self, "_btn_" + name, None)
            if b is None:
                continue
            try:
                b.configure(state="normal" if on else "disabled")
            except Exception:
                pass

    def _on_undo(self) -> None:
        sb = self.sandbox
        if sb is None or not sb.undo():
            return
        self._sel_cell = None
        self.lbl_detail.configure(text="已撤一步。Ctrl+Z 可继续回退。")
        self._after_change()

    def _on_redo(self) -> None:
        sb = self.sandbox
        if sb is None or not sb.redo():
            return
        self._sel_cell = None
        self.lbl_detail.configure(text="已重做一步。Ctrl+Y 可继续重做。")
        self._after_change()

    def _render_state(self) -> dict:
        """把 Sandbox 摊成渲染器要的 dict。

        ``slow`` 必须是**格子坐标集合**（渲染器直接 ``for (r, c) in``
        画标记），不能是敌人对象——那样解包就直接报错。
        """
        sb = self.sandbox
        if not sb:
            return {}
        slow_cells = set()
        for ev in sb.live_events():
            if not sb.buffs_of(ev):
                continue
            pose = sb.pose_at(ev, self._now)
            if pose is not None:
                slow_cells.add((int(round(pose[0])), int(round(pose[1]))))
        ops = sb.operators_at(self._now)
        return {
            "boxes": set(sb.boxes),
            "operators": ops,
            "range": self._range_cells(ops),
            "block": sb.overlap(self._now),
            "slow": slow_cells,
            "selected_op": self._selected_op,
        }

    @property
    def _selected_op(self):
        if not self.sandbox:
            return None
        p = getattr(self, "_sel_cell", None)
        if p and p in self.sandbox.operators_at(self._now):
            return p
        return None

    def _range_cells(self, ops: Optional[dict] = None) -> set:
        """选中干员的攻击范围格。

        只对「选中」的那一枚算——全部常驻算一遍既没必要也拖慢重绘。
        取不到干员自身范围时给一个近战 3x3 兜底。
        """
        p = self._selected_op
        if not p:
            return set()
        if ops is None:
            ops = self.sandbox.operators_at(self._now)
        piece = ops.get(p)
        if piece is None:
            return set()
        cells = getattr(piece, "range_cells", None)
        if cells:
            return set(cells)
        r0, c0 = p
        gm = self.game_map
        out = set()
        for dr in (-1, 0, 1):
            for dc in (-1, 0, 1):
                r, c = r0 + dr, c0 + dc
                if gm and not (0 <= r < gm.height and 0 <= c < gm.width):
                    continue
                out.add((r, c))
        return out

    # ============================================================ 粗轴刷新

    def _refresh_track(self) -> None:
        sb = self.sandbox
        if sb is None:
            return
        total = self._track_total()
        cycles: Dict[int, List[tuple]] = {}
        for dep in sb.track.all():
            try:
                raw = sb.skill_sim.cycles(dep.skill, total, dep.deploy_time,
                                          boost=float(dep.sp_boost or 0.0))
            except Exception:
                raw = []
            cycles[dep.uid] = [(a, b) for (a, _x, b) in raw]
        self.track_canvas.set_track(sb.track, total=total, cycles=cycles,
                                    keep_view=True)
        n = len(sb.track.deployments)
        n_ret = sum(1 for d in sb.track.all() if d.retreat_time is not None)
        self.lbl_track.configure(text="（%d 次部署 / %d 次撤退）" % (n, n_ret))
        self._draw_buff_axis()

    def _track_total(self) -> float:
        """粗轴总长：取「时间轴总时长」与「最后一个动作」的较大者。

        必须覆盖**走完全程**，不能只用 ``timeline.duration`` —— 那只是最后
        一只敌人**出场**的时刻。实测几乎所有关都短：``main_08-04`` 出怪到
        163s 但最后一只 193s 才到蓝门，``hard_08-04`` 176s vs 274s（平民
        还罚站 270 秒），``act1multi_football`` 80s vs 357s。按出场时刻收尾
        的话动画在敌人刚抬脚时就结束，看起来像「站着没动」。

        口径与寻路面板的 ``Timeline.span(analyses)`` 保持一致（那边本来就
        是这么算的），额外再算上**出场罚站**——角兽的【休憩】不在路线的
        ``total_time`` 里，``arrival_time`` 才是含它的历时。
        """
        dur = 0.0
        if self.timeline is not None:
            dur = float(getattr(self.timeline, "duration", 0.0) or 0.0)
        if self.sandbox is not None:
            dur = max(dur, self.sandbox.track.span())
            for ev in (self.timeline.events if self.timeline else []):
                # arrival_time 返回的历时**已含**出场罚站，不用再加 head
                _arr = self.sandbox.arrival_time(ev)
                if _arr is None:
                    continue
                dur = max(dur, float(getattr(ev, "time", 0.0) or 0.0) + _arr)
        return max(60.0, dur)

    def _draw_buff_axis(self) -> None:
        """画 buff 轴：一段一段的减速区块。"""
        cv = self.buff_canvas
        cv.delete("all")
        sb = self.sandbox
        w = max(cv.winfo_width(), 200)
        h = max(cv.winfo_height(), 24)
        total = max(1.0, self._track_total())

        def x_of(t):
            return 46 + max(0.0, min(1.0, t / total)) * max(1, w - 62)

        cv.create_line(46, h - 5, w - 16, h - 5, fill="#3b4554")
        if sb is None or not sb.buffs:
            cv.create_text(w / 2, h / 2, text="（本次模拟没有设置 buff）",
                           fill="#9aa5b4", font=("Microsoft YaHei UI", 8))
            self.lbl_buff.configure(text="（右键敌人设置停顿/减速）")
            return
        names = {}
        for ev in sb.events():
            try:
                names[sb._event_key(ev)] = (
                    getattr(ev, "enemy_name", "")
                    or getattr(ev, "enemy_id", "") or "敌人")
            except Exception:
                continue
        rows: Dict[str, list] = {}
        for (key, a, b, m) in sb.buffs:
            rows.setdefault(key, []).append((a, b, m))
        items = list(rows.items())[:6]
        rh = max(3, int((h - 8) / max(1, len(items))))
        for i, (key, spans) in enumerate(items):
            y = 4 + i * rh
            nm = names.get(key, "敌人")
            cv.create_text(42, y + rh / 2, text=nm[:4], anchor="e",
                           fill="#9aa5b4", font=("Microsoft YaHei UI", 6))
            for (a, b, m) in spans:
                x0, x1 = x_of(a), x_of(b)
                col = "#c0392b" if m < 0.2 else "#e67e22"
                cv.create_rectangle(x0, y, max(x1, x0 + 2), y + max(3, rh - 2),
                                    fill=col, outline="")
        cv.create_line(x_of(self._now), 2, x_of(self._now), h - 4,
                       fill="#4ea1f7", width=1)
        self.lbl_buff.configure(text="（%d 段 buff）" % len(sb.buffs))

    # ============================================================ 导出导入

    def _on_export(self) -> None:
        sb = self.sandbox
        if sb is None:
            messagebox.showinfo("导出粗轴", "请先载入关卡。", parent=self)
            return
        if not sb.track.deployments:
            messagebox.showinfo("导出粗轴",
                                "还没有任何部署记录，先放几个干员吧。",
                                parent=self)
            return
        name = (sb.track.stage_id or "sandbox").replace("/", "_")
        path = filedialog.asksaveasfilename(
            parent=self, title="导出粗轴", defaultextension=".json",
            initialfile="%s_粗轴.json" % name,
            filetypes=[("JSON", "*.json"), ("全部文件", "*.*")])
        if not path:
            return
        buffs = [{"kind": "slow", "key": k, "t": round(a, 3),
                  "dur": round(b - a, 3), "mult": round(m, 3)}
                 for (k, a, b, m) in sb.buffs]
        data = sb.track.dump(boxes=sb.boxes, buffs=buffs)
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except OSError as e:
            messagebox.showerror("导出失败", str(e), parent=self)
            return
        self.lbl_detail.configure(
            text="粗轴已导出到：\n%s\n\n把这个文件发给别人，他导入后就能"
                 "看到同样的轴（含关卡 id、箱子与 buff），方便交流思路。"
                 % path)

    def _on_import(self) -> None:
        path = filedialog.askopenfilename(
            parent=self, title="导入粗轴",
            filetypes=[("JSON", "*.json"), ("全部文件", "*.*")])
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                text = f.read()
        except OSError as e:
            messagebox.showerror("导入失败", str(e), parent=self)
            return
        try:
            raw = json.loads(text)
            tr = CoarseTrack.from_dict(raw)
        except ValueError as e:
            messagebox.showerror("导入失败", str(e), parent=self)
            return
        self._apply_imported(tr, raw)

    def _apply_imported(self, tr: CoarseTrack, raw: dict) -> None:
        """把导入的粗轴套到当前地图上。

        关卡对不上时**不硬套**：位置会错到别的格子。先提示，用户确认
        才继续（有时他们就是想在同一张换皮图上复用）。
        """
        sb = self.sandbox
        if sb is None or self.game_map is None:
            messagebox.showinfo(
                "导入粗轴",
                "请先载入关卡，再导入粗轴。\n"
                "粗轴里记录的部署位置与具体地图绑定。", parent=self)
            return
        cur = sb.track.stage_id or ""
        if tr.stage_id and cur and tr.stage_id != cur:
            ok = messagebox.askyesno(
                "关卡不一致",
                "粗轴来自「%s」，当前是「%s」。\n\n"
                "强行导入会按格子坐标落位，位置可能不对。要继续吗？"
                % (tr.stage_name or tr.stage_id,
                   getattr(self.stage, "label", "") or cur), parent=self)
            if not ok:
                return
        tr.stage_id = tr.stage_id or cur
        tr.stage_name = tr.stage_name or (getattr(self.stage, "label", "")
                                         or cur)
        sb.track = tr
        # 箱子会影响寻路，逐格走 box_check，被拒绝的就不放
        boxes = raw.get("boxes")
        if isinstance(boxes, list):
            for item in boxes:
                if not isinstance(item, (list, tuple)) or len(item) < 2:
                    continue
                try:
                    r, c = int(item[0]), int(item[1])
                except (TypeError, ValueError):
                    continue
                if (r, c) in sb.boxes:
                    continue
                ok, _why = sb.box_check(r, c)
                if ok:
                    sb.place_box(r, c)
        # 部署：只在「当前游标时刻还活着」的时候落到场上
        for dep in tr.all():
            if (dep.row, dep.col) in sb.operators:
                continue
            if not dep.alive_at(self._now):
                continue
            sb.deploy(dep.row, dep.col, dep)
        # buff：空列表也是有效结果——导入一个没有 buff 的轴，就该把当前
        # 界面上的 buff 清掉，否则「导入」等于没导入干净。
        #
        # 两种格式都要认：
        #   * ``{"key","t","dur","mult"}``（写进 JSON 后的规范形态）
        #   * ``[key, t0, t1, mult]`` / ``(key, t0, t1, mult)``
        #     ——``Sandbox.buffs`` 内部就是 4 元组，直接 dump 后经 JSON
        #     往返会变成 4 元素数组。以前这里只按 dict 取 ``b.get("key")``，
        #     于是「导出的轴导回来」buff 全部丢失（数量 0），用户看到的
        #     是导入成功但减速范围没了。
        slot = []
        buffs = raw.get("buffs")
        if isinstance(buffs, list):
            for b in buffs:
                key = ""
                t0 = dur = 0.0
                mult = 1.0
                if isinstance(b, dict):
                    key = str(b.get("key") or "")
                    try:
                        t0 = float(b.get("t") or 0.0)
                        dur = max(0.0, float(b.get("dur") or 0.0))
                        mult = max(0.0, min(1.0, float(b.get("mult") or 1.0)))
                    except (TypeError, ValueError):
                        continue
                elif isinstance(b, (list, tuple)) and len(b) >= 4:
                    key = str(b[0] or "")
                    try:
                        t0 = float(b[1])
                        t1 = float(b[2])
                        mult = max(0.0, min(1.0, float(b[3])))
                    except (TypeError, ValueError):
                        continue
                    dur = max(0.0, t1 - t0)
                else:
                    continue
                if not key or dur <= 0:
                    continue
                slot.append((key, t0, t0 + dur, mult))
        sb.buffs = slot
        sb.push_history()
        self._refresh_frame(self._now)
        self._fill_events()
        self._refresh_track()
        self.canvas.set_sandbox(self._render_state())
        self._refresh_history_buttons()
        self.lbl_detail.configure(
            text="已导入粗轴：%d 次部署、%d 个箱子、%d 段 buff（关卡 %s）"
                 % (len(tr.deployments), len(sb.boxes), len(slot),
                    tr.stage_name or tr.stage_id))

    # ============================================================ 敌人列表

    def _fill_events(self) -> None:
        for w in self.ev_inner.winfo_children():
            w.destroy()
        self._ev_rows = []
        sb = self.sandbox
        if not sb:
            return
        live = self._visible_events()
        all_ev = sb.events()
        n_harm_all = sum(1 for e in all_ev if getattr(e, "harmless", False))
        if n_harm_all and not self.var_hide_harmless.get():
            self.lbl_sum.configure(
                text="%d / %d（含 %d 无害）"
                     % (len(sb.live_events()), len(all_ev), n_harm_all))
        elif n_harm_all:
            self.lbl_sum.configure(
                text="%d / %d（已撇 %d 无害）"
                     % (len(live), len(all_ev), n_harm_all))
        else:
            self.lbl_sum.configure(text="%d / %d" % (len(live), len(all_ev)))
        if not live:
            tk.Label(self.ev_inner, text="（没有可出场的敌人）",
                     background=BG_SUNKEN, foreground=FG_DIM,
                     font=(FONT_UI, FS_SMALL)).pack(pady=PAD_M)
            return
        for ev in live:
            arr = sb.arrival_time(ev)
            buffs = sb.buffs_of(ev)
            blocks = [
                ("敌人", getattr(ev, "enemy_name", "")
                 or getattr(ev, "enemy_id", "")),
                ("路线", str(getattr(ev, "route_index", "-"))),
                ("出场", "%5.1fs" % float(getattr(ev, "time", 0.0) or 0.0)),
                ("到达", ("%5.1fs" % arr) if arr is not None else "  不可达"),
            ]
            if buffs:
                blocks.append(("减速", "×%.2f" % min(b[2] for b in buffs)))
            row = tk.Frame(self.ev_inner, background=BG_SUNKEN)
            row.pack(fill="x", pady=1)
            for i, (k, v) in enumerate(blocks):
                tk.Label(row, text=k, background=BG_SUNKEN, foreground=FG_DIM,
                         font=(FONT_UI, FS_MICRO)).grid(
                    row=0, column=i * 2, sticky="w", padx=(PAD_S, 1))
                tk.Label(row, text=v, background=BG_SUNKEN,
                         foreground=FG if i < 3 else ACCENT_TXT,
                         font=(FONT_UI, FS_MICRO)).grid(
                    row=0, column=i * 2 + 1, sticky="w", padx=(0, PAD_S))
            row.bind("<Button-1>", lambda e, ev=ev: self._pick_event(ev))
            row.bind("<Button-3>", lambda e, ev=ev: self._menu_enemy_ev(ev))
            for ch in row.winfo_children():
                ch.bind("<Button-1>", lambda e, ev=ev: self._pick_event(ev))
                ch.bind("<Button-3>",
                        lambda e, ev=ev: self._menu_enemy_ev(ev))
            self._ev_rows.append({"ev": ev, "frame": row})

    def _menu_enemy_ev(self, ev) -> None:
        """出怪列表里右键也能设 buff（不必去地图上找那只怪）。"""
        sb = self.sandbox
        m = self._new_menu()
        name = getattr(ev, "enemy_name", "") or getattr(ev, "enemy_id", "")
        m.add_command(label="%s：" % name, state="disabled")
        for sec in STOP_PRESETS:
            m.add_command(label="停顿 %.0f 秒" % sec,
                          command=lambda s=sec: self._add_stop(ev, s, 0.0))
        m.add_command(label="自定义…", command=lambda: self._ask_stop(ev))
        m.add_separator()
        # add_command 的 label 不经过 % 格式化，写 "%%" 会原样显示成两个百分号
        m.add_command(label="减速 50% 持续 10 秒",
                      command=lambda: self._add_stop(ev, 10.0, 0.5))
        m.add_command(label="减速 30% 持续 15 秒",
                      command=lambda: self._add_stop(ev, 15.0, 0.7))
        if sb is not None:
            m.add_separator()
            m.add_command(label=("恢复这只" if sb.is_kicked(ev) else "踢掉这只"),
                          command=lambda: self._kick_toggle(ev))
            if sb.buffs_of(ev):
                m.add_command(label="清除它的减速",
                              command=lambda: self._clear_one(ev))
        m.tk_popup(self.winfo_pointerx(), self.winfo_pointery())

    def _pick_event(self, ev) -> None:
        """点敌人列表：选中它；若当前是踢人模式就顺手踢掉。"""
        self.selected_event = ev
        for r in self._ev_rows:
            on = (r["ev"] is ev)
            bg = ACCENT_SOFT if on else BG_SUNKEN
            r["frame"].configure(background=bg)
            for ch in r["frame"].winfo_children():
                ch.configure(background=bg)
        sb = self.sandbox
        if sb is None:
            return
        if self.mode == MODE_KICK:
            sb.kick(ev)
            sb.push_history()
            self._after_change()
            return
        if self.mode == MODE_SLOW:
            self._ask_stop(ev)
            return
        lines = [getattr(ev, "enemy_name", "") or getattr(ev, "enemy_id", "")]
        lines.append("出场 %.1fs　路线 %s"
                     % (float(getattr(ev, "time", 0.0)),
                        getattr(ev, "route_index", "-")))
        arr = sb.arrival_time(ev)
        if arr is not None:
            lines.append("到达 %.1fs" % arr)
        ra = sb.analysis_for(ev)
        note = getattr(ra, "note", "") if ra is not None else ""
        if note:
            lines.append(note)
        self.lbl_detail.configure(text="\n".join(lines))
        self._shift_to(float(getattr(ev, "time", 0.0)))

    # ============================================================ 底部按钮

    def _on_reset(self) -> None:
        if self.sandbox:
            self.sandbox.reset()
            self.sandbox.push_history()
            self._picked = []
            self._pending_idx = None
            self._sel_cell = None
            self._fill_picked()
            self.lbl_pending.configure(text="")
            self._after_change()

    def _on_clear_buff(self) -> None:
        if self.sandbox:
            self.sandbox.clear_buffs()
            self.sandbox.push_history()
            self._after_change()

    def _on_restore(self) -> None:
        if self.sandbox:
            self.sandbox.restore_all()
            self.sandbox.push_history()
            self._after_change()

    # ============================================================ 生命周期

    def suspend(self) -> None:
        """面板切走时停播。

        ``after`` 定时器不会因为控件被 ``pack_forget`` 消失，不停的话
        切到别的页还会在后台跑，既占 CPU 又在用户看不见的地方改游标。
        """
        try:
            self.playback.suspend()
        except Exception:
            pass



def _cycle_of(skill, interval: float = 1.0) -> SkillCycle:
    """``Skill`` → ``SkillCycle``。

    放在模块级而不是方法里：``_default_skill`` 的排序、悬停文案、右键菜单
    三处都要用，做成实例方法会让「没绑定 self 的调用」静默退化成全默认值
    （``except`` 把异常吞掉），排查起来极其费劲。

    技能数据是 ``Skill(index, name, tree_type, trigger_type,
    levels={key: SkillLevel})``——**没有 blackboard 列表**，SP 参数就在
    ``max_level_key`` 那一档 ``SkillLevel`` 上（``cost`` / ``initial`` /
    ``duration``），回复类型看 ``tree_type``。取不到满级档时退回最后一档，
    不能拿 ``max(int(k))``：``levels`` 的键是字符串等级序号，直接取
    最大值会摸到 1 级专精前数据（spCost 常常是 0）。
    """
    cyc = SkillCycle()
    if skill is None:
        return cyc
    tt = str(getattr(skill, "tree_type", "") or "")
    if "攻击" in tt:
        cyc.recover = SP_ATTACK
    elif "受击" in tt or "被击" in tt:
        cyc.recover = SP_DEFENSE
    elif "被动" in tt:
        cyc.recover = SP_NONE
    elif "自动" in tt:
        cyc.recover = SP_AUTO
    else:
        cyc.recover = SP_NONE
    lv = None
    try:
        key = getattr(skill, "max_level_key", "") or ""
        if key:
            lv = skill.level(key)
        if lv is None:
            levels = getattr(skill, "levels", None) or {}
            if isinstance(levels, dict) and levels:
                lv = levels[list(levels.keys())[-1]]
    except Exception:
        lv = None
    if lv is not None:
        cyc.sp_cost = max(0.0, float(getattr(lv, "cost", 0.0) or 0.0))
        cyc.init_sp = max(0.0, float(getattr(lv, "initial", 0.0) or 0.0))
        cyc.duration = max(0.0, float(getattr(lv, "duration", 0.0) or 0.0))
    if cyc.sp_cost <= 0:
        cyc.recover = SP_NONE
    cyc.infer_attack = (cyc.recover == SP_ATTACK)
    return cyc


def _default_skill_of(skills, interval: float = 1.0):
    """选一个「默认技能」——挑最值得看回转的那个，不是无脑 ``skills[0]``。

    用户要求「悬停干员显示技能回转」。以前取 ``skills[0]``，而银灰的第一个
    技能是「强力击·γ型」：``spCost=2、duration=0``，属于 ``is_continuous``
    的持续型。``SkillSim.state_at`` 对这类永远返回 ``active=True``，于是悬停
    不管在哪个时刻都只剩一句「技能中」——SP 多少、还差几秒一次都看不到，
    功能等于没做。

    按「信息量」排序：

    1. 有 ``duration`` 且有 ``cost`` 的主动技能（真银斩这类）——能同时看到
       攒 SP 和技能持续，回转曲线最完整；
    2. 有 ``cost`` 但无 ``duration`` 的（充能类）；
    3. 被动 / 无 SP 的（``sp_cost<=0``）——放最后，它本来就没有回转。

    同一档内按 SP 从多到少（大招优先），再相同时保持原顺序，避免「同一个
    干员每次选出来不一样」。全库 441 个有技能的干员实测：0 个落到无 SP，
    0 个在「还有带 duration 的主动技能」时落到持续型。
    """
    cands = list(skills or [])
    if not cands:
        return None

    def _info(s):
        try:
            cyc = _cycle_of(s, interval)
        except Exception:
            return (3, 0.0)
        cost = float(getattr(cyc, "sp_cost", 0) or 0)
        dur = float(getattr(cyc, "duration", 0) or 0)
        if cost > 0:
            return (0 if dur > 0 else 1, -cost)
        return (2, 0.0)

    return min(cands, key=_info)