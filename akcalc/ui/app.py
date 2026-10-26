"""主窗口：整合伤害计算与寻路计算两大功能。"""
from __future__ import annotations

import os
import sys
import shutil
import threading
import tkinter as tk
from tkinter import messagebox, ttk
from typing import List, Optional

from ..core import op_index as OPI
from ..core import prts_operator as PO
from ..core.catalog import StageCatalog
from ..core.enemies import EnemyLibrary
from ..core.maps import LevelCache
from ..core.operator_modules import ModuleLibrary
from ..core.models import EnemyStats, Operator
from ..core import settings as SET
from ..core import single_instance as SI
from ..core.paths import Paths
from .damage_panel import DamagePanel
from .data_index import FieldsIndexView, MonsterIndexView, OperatorIndexView
from .home_panel import HomePanel
from .path_panel import PathPanel
from .settings_dialog import SettingsDialog
from . import widgets as _W
from .widgets import (ACCENT, AppBar, BG, BG_DEEP, BG_INPUT, BG_PANEL,
                      BORDER, ComboBox, DIVIDER, FG, FG_DIM, FONT_NUM, FONT_UI,
                      FS_BODY, FS_H1, FS_SMALL, PAD_M, PAD_S, PAD_XS, StatusBar,
                      apply_dark_style, enable_dark_titlebar)

APP_BRAND = "肥牛妙妙工具"
APP_TITLE = "肥牛妙妙工具 · 明日方舟伤害与寻路"
APP_SUB = "伤害计算 · 寻路分析"
WINDOW_W, WINDOW_H = 1420, 900
WINDOW_MIN_W, WINDOW_MIN_H = 1180, 720


class App(tk.Tk):
    """应用主窗口。"""

    def __init__(self):
        super().__init__()
        self.title(APP_TITLE)
        self._place_window()
        self.configure(background=BG)

        self.paths = Paths.default()
        self.paths.ensure()
        apply_dark_style(self)

        # 数据层
        self.op_cache = PO.OperatorCache.load(self.paths.operators_cache)
        self.op_index = OPI.OperatorIndex.from_cache(self.op_cache.data)
        self.level_cache = LevelCache(self.paths.levels_cache_dir)
        self.enemy_lib = EnemyLibrary(self.paths.enemies_cache)
        self.enemy_lib.load_cached()
        self.module_lib = ModuleLibrary(self.paths)
        self.module_lib.load_cached()
        self.module_lib.ensure_raw()
        self.stage_catalog = self._load_stage_catalog()
        self.enemy_names = self._load_enemy_names()

        self.current_operator: Optional[Operator] = None

        # 用户设置（字号等）：先读出来，建 UI 时就用正确字号
        self.settings = SET.load(self.paths.settings_file)
        _W.set_font_scale(SET.scale_of(self.settings.get("font_size", "")))

        self._set_icon()
        self._build_ui()
        # 建完之后再重设一遍控件的字号（建的时候可能还有硬编码字号）
        try:
            _W.apply_font_scale(self, _W.FONT_SCALE)
        except Exception:
            pass
        self._settings_win = None
        self._load_operator_index()
        self.status.set_right(self.paths.human_report())
        # 原生标题栏刷深色 + 屏蔽标题栏图标（青蛙头）上的系统菜单
        # （都只是外观优化，失败不影响功能）
        self.after(30, self._polish_titlebar)

    # ------------------------------------------------------------ 布局

    def _polish_titlebar(self) -> None:
        """标题栏外观：深色 + 禁用图标上的系统菜单。"""
        try:
            enable_dark_titlebar(self)
        except Exception:
            pass
        try:
            _W.suppress_titlebar_menu(self)
        except Exception:
            pass

    def _set_icon(self) -> None:
        """设置窗口 / 任务栏图标（打包后 exe 自带，源码运行时读 png 兜底）。"""
        try:
            base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            png = os.path.join(os.path.dirname(base), ".build", "app_256.png")
            if not os.path.isfile(png):
                # 打包后资源解包在 _MEIPASS 里
                png = os.path.join(getattr(sys, "_MEIPASS", base), "app_256.png")
            if os.path.isfile(png):
                self._icon_img = tk.PhotoImage(file=png)
                self.iconphoto(True, self._icon_img)
                return
            ico = os.path.join(os.path.dirname(base), ".build", "app.ico")
            if os.path.isfile(ico):
                self.iconbitmap(ico)
        except Exception:
            pass  # 图标失败不影响功能

    # ------------------------------------------------------------ 设置

    def open_settings(self) -> None:
        """打开设置窗口（已经开着就置前，不重复开）。"""
        win = getattr(self, "_settings_win", None)
        if win is not None:
            try:
                if win.winfo_exists():
                    win.lift()
                    win.focus_set()
                    return
            except Exception:
                pass
        self._settings_win = SettingsDialog(self, self,
                                            on_close=self._settings_closed)

    def _settings_closed(self) -> None:
        self._settings_win = None
        # 字号变过就得重画曲线（画布上的文字是 create_text 画的）；
        # 面板还没建过就不必管，首次进入会用新字号从头建。
        if self._damage_panel is not None:
            try:
                self._damage_panel.recompute()
            except Exception:
                pass

    def set_font_scale(self, scale: float, label: str = "") -> None:
        """应用字号缩放：更新常量、重设控件字体、重画图画、存盘。

        ``label`` 由设置窗口在用户点「完成」时传入；不传则按 scale 反查。
        注意这里才是**真正**的全局应用点——设置窗口的预览不再走这里，
        否则每点一个单选项就整窗重排一次，连点会明显卡。
        """
        effective = _W.set_font_scale(scale)
        try:
            _W.apply_font_scale(self, effective)
        except Exception:
            pass
        # ttk 样式里的字号不会跟着 tk 控件走，重建样式
        try:
            apply_dark_style(self)
        except Exception:
            pass
        label = label or SET.label_of(effective)
        self.settings["font_size"] = label
        SET.save(self.paths.settings_file, self.settings)
        # 曲线画布上的字号是绘图时算的，重算一次
        if self._damage_panel is not None:
            try:
                self._damage_panel.recompute()
            except Exception:
                pass
            try:
                self._damage_panel.chart._redraw()
            except Exception:
                pass
        try:
            self.status.set("字号已切换为「%s」" % label)
        except Exception:
            pass

    def _place_window(self) -> None:
        """按屏幕工作区决定初始大小并居中，避免窗口超出屏幕留下黑边。"""
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        # 留出任务栏与标题栏，保证整窗可见
        avail_h = sh - 96
        avail_w = sw - 80
        w = min(WINDOW_W, avail_w)
        h = min(WINDOW_H, avail_h)
        self.minsize(min(WINDOW_MIN_W, w), min(WINDOW_MIN_H, h))
        x = max(0, (sw - w) // 2)
        y = max(0, (avail_h - h) // 2 + 16)
        self.geometry("%dx%d+%d+%d" % (w, h, x, y))

    def _build_ui(self) -> None:
        # ---- 顶部品牌栏
        self.appbar = AppBar(self, APP_BRAND,
                             "伤害计算 · 寻路分析　·　PRTS 数据")
        self.appbar.pack(fill="x")
        self.lbl_count = tk.Label(self.appbar.actions, text="",
                                  background=BG_DEEP, foreground=FG_DIM,
                                  font=(FONT_UI, FS_SMALL))
        self.lbl_count.pack(side="left", padx=(0, PAD_M))
        self._btn_settings = ttk.Button(self.appbar.actions, text="设置",
                                        style="Ghost.TButton",
                                        command=self.open_settings)
        self._btn_settings.pack(side="left", padx=PAD_XS)
        self._btn_cache = ttk.Button(self.appbar.actions, text="缓存信息",
                                     style="Ghost.TButton",
                                     command=self.show_cache)
        self._btn_cache.pack(side="left", padx=PAD_XS)
        self.btn_sync = ttk.Button(self.appbar.actions, text="同步全图鉴",
                                   style="App.TButton",
                                   command=self.sync_all_operators)
        self.btn_sync.pack(side="left", padx=PAD_XS)
        self._btn_enemy = ttk.Button(self.appbar.actions, text="下载敌人库",
                                     style="App.TButton",
                                     command=self.download_enemy_lib)
        self._btn_enemy.pack(side="left", padx=PAD_XS)

        # 这些按钮只在主界面显示
        self._appbar_data_widgets = [self.lbl_count, self._btn_cache,
                                     self.btn_sync, self._btn_enemy]

        # ---- 主区：三个视图互斥切换（主界面 / 伤害计算 / 寻路分析）
        # 用容器 + place 覆盖的方式切换，避免 Notebook 标签页占地方，
        # 也避免两个功能共享同一套顶部控件。
        self._view_wrap = tk.Frame(self, background=BG)
        self._view_wrap.pack(fill="both", expand=True)

        self.home_panel = HomePanel(self._view_wrap, self)

        # 伤害 / 寻路两大面板最重（约 0.4s + 0.4s 的控件构建），
        # 延迟到首次进入对应功能页才建，启动只留轻量的主界面。
        self._damage_panel = None
        self._path_panel = None

        # 数据索引两栏：延迟构建，首次进入才建，避免启动时白等。
        self._op_view = None
        self._monster_view = None
        self._field_view = None

        self._views = {
            "home": self.home_panel,
        }
        self._current_view = ""

        # ---- 状态栏
        self.status = StatusBar(self)
        self.status.pack(fill="x", side="bottom")

        self.show_view("home")
    # ------------------------------------------------------------ 数据装载

    def _load_stage_catalog(self) -> "StageCatalog":
        """关卡目录：多处查找，最后才尝试现场构建。

        打包后 ``paths.data_dir`` 是 **exe 同级目录**，而随包资源在
        ``sys._MEIPASS`` 里，两边不是同一个地方；以前只认前者，结果
        exe 版永远显示「关卡目录尚未载入」。这里按优先级逐个找。
        """
        cands = []
        # 1) 可写数据目录（用户目录 / exe 同级），运行期可能已生成
        cands.append(os.path.join(self.paths.data_dir, "catalog.json"))
        # 2) 随包资源目录：开发期 akcalc/data，打包后 _MEIPASS/akcalc/data
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        cands.append(os.path.join(base, "data", "catalog.json"))
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            cands.append(os.path.join(meipass, "akcalc", "data", "catalog.json"))
            cands.append(os.path.join(meipass, "data", "catalog.json"))
        for cp in cands:
            try:
                if not os.path.isfile(cp):
                    continue
                cat = StageCatalog.load(cp)
            except Exception:
                continue
            if cat and cat.total() > 0:
                # 顺手往可写目录放一份，下次启动就是第 1 条命中
                try:
                    dst = os.path.join(self.paths.data_dir, "catalog.json")
                    if os.path.abspath(cp) != os.path.abspath(dst):
                        shutil.copy2(cp, dst)
                except OSError:
                    pass
                return cat
        # 兜底：用随包的表现场构建（离线也可用）
        stage_tbl = self._read_bundled_json("stage_table.json")
        zone_tbl = self._read_bundled_json("zone_table.json")
        if not stage_tbl or not zone_tbl:
            return StageCatalog()
        try:
            cat = StageCatalog.build(stage_tbl, zone_tbl)
        except Exception:
            return StageCatalog()
        try:
            cat.save(os.path.join(self.paths.data_dir, "catalog.json"))
        except Exception:
            pass
        return cat

    def _load_enemy_names(self) -> dict:
        """敌人 id -> 中文名（随包的 enemy_names.json）。"""
        raw = self._read_bundled_json("enemy_names.json")
        return raw if isinstance(raw, dict) else {}

    @staticmethod
    def _read_bundled_json(name: str):
        """读随包数据文件（开发期在 akcalc/data，打包后在 _MEIPASS）。"""
        import json
        cands = []
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        cands.append(os.path.join(base, "data", name))
        if getattr(sys, "_MEIPASS", None):
            cands.append(os.path.join(sys._MEIPASS, name))
            cands.append(os.path.join(sys._MEIPASS, "akcalc", "data", name))
        for p in cands:
            try:
                with open(p, "r", encoding="utf-8") as f:
                    return json.load(f)
            except (OSError, ValueError):
                continue
        return None

    # ------------------------------------------------------------ 视图切换

    def _ensure_view(self, key: str):
        """视图延迟构建：首次进入才建，之后复用。

        伤害 / 寻路面板控件很多（构建各约 0.4s），数据索引要读
        463 个干员 + 2186 个敌人。全部留在启动时建会让主窗口白等，
        这里统一改成「用到才建」。
        """
        if key == "op_index":
            if self._op_view is None:
                self._op_view = OperatorIndexView(self._view_wrap, self)
                self._views["op_index"] = self._op_view
            return self._op_view
        if key == "monster_index":
            if self._monster_view is None:
                self._monster_view = MonsterIndexView(self._view_wrap, self)
                self._views["monster_index"] = self._monster_view
            return self._monster_view
        if key == "field_index":
            if self._field_view is None:
                self._field_view = FieldsIndexView(self._view_wrap, self)
                self._views["field_index"] = self._field_view
            return self._field_view
        if key == "damage":
            if self._damage_panel is None:
                self._damage_panel = DamagePanel(self._view_wrap, self)
                self._views["damage"] = self._damage_panel
                # 面板刚建好，把已加载的干员索引填进筛选/下拉
                self._populate_operator_controls()
            return self._damage_panel
        if key == "path":
            if self._path_panel is None:
                self._path_panel = PathPanel(self._view_wrap, self)
                self._views["path"] = self._path_panel
            return self._path_panel
        return self._views.get(key)

    def _populate_operator_controls(self) -> None:
        """伤害面板建好后，把干员索引数据填进筛选栏与下拉。"""
        if not hasattr(self, "op_index"):
            return
        if hasattr(self, "cmb_prof"):
            self.cmb_prof.config(values=[OPI.ALL] + self.op_index.professions())
            self.cmb_star.config(values=[OPI.ALL] + [
                OPI.rarity_label(r) for r in self.op_index.rarities()])
            self.cmb_pos.config(values=[OPI.ALL] + self.op_index.positions())
        self._on_prof_change()

    @property
    def damage_panel(self) -> DamagePanel:
        return self._ensure_view("damage")

    @property
    def path_panel(self) -> PathPanel:
        return self._ensure_view("path")

    def show_view(self, key: str) -> None:
        """切换到某个视图（home / damage / path / op_index / monster_index）"""
        target = self._ensure_view(key)
        if target is None:
            return
        if key == self._current_view:
            return
        # 离开前先让旧视图「收尾」：寻路分析的播放定时器不会因为
        # pack_forget 自动消失，不叫停就会在后台一直跑动画。
        prev = self._views.get(self._current_view)
        if prev is not None:
            hook = getattr(prev, "suspend", None)
            if callable(hook):
                try:
                    hook()
                except Exception:
                    pass
        for other in self._views.values():
            if other is not target:
                other.pack_forget()
        target.pack(fill="both", expand=True)
        self._current_view = key
        # 品牌栏右侧的按钮只在主界面显示
        self._update_appbar_for_view(key)
        if key == "home":
            self.status.set("选择上方的功能进入")
        elif key == "damage":
            self.status.set("伤害计算：选干员后自动计算")
        elif key == "path":
            self.status.set("寻路分析：选关卡后加载地图与时间轴")
        elif key == "op_index":
            self.status.set("干员数据：左侧搜索，右侧看面板与技能")
        elif key == "monster_index":
            self.status.set("怪物图鉴：左侧搜索，右侧看特性与抗性")

    def _update_appbar_for_view(self, key: str) -> None:
        """主界面显示数据按钮，功能页收起，避免干扰。"""
        widgets = getattr(self, "_appbar_data_widgets", [])
        for w in widgets:
            if not w.winfo_exists():
                continue
            if key == "home":
                w.pack(side="left", padx=PAD_XS)
            else:
                w.pack_forget()
        if hasattr(self, "lbl_count") and self.lbl_count.winfo_exists():
            if key == "home":
                self.lbl_count.pack(side="left", padx=(0, PAD_M))
            else:
                self.lbl_count.pack_forget()

    def build_panel_header(self, parent, title: str, tag: str,
                           desc: str) -> tk.Frame:
        """在功能页顶部画「返回 + 标题」，返回主界面用。"""
        box = tk.Frame(parent, background=BG_PANEL, highlightthickness=1,
                       highlightbackground=DIVIDER)
        box.pack(fill="x")
        inner = tk.Frame(box, background=BG_PANEL)
        inner.pack(fill="x", padx=PAD_S, pady=PAD_S - 1)

        back = tk.Label(inner, text="←  返回", background=BG_PANEL,
                        foreground=ACCENT, font=(FONT_UI, FS_BODY),
                        cursor="hand2")
        back.pack(side="left", padx=(PAD_XS, PAD_M))
        back.bind("<Button-1>", lambda e: self.show_view("home"))

        tk.Frame(inner, background=DIVIDER, width=1).pack(
            side="left", fill="y", padx=(0, PAD_M), pady=1)

        tk.Label(inner, text=title, background=BG_PANEL, foreground=FG,
                 font=(FONT_UI, FS_H1, "bold")).pack(side="left")
        tk.Label(inner, text="  " + tag, background=BG_PANEL,
                 foreground=FG_DIM,
                 font=(FONT_NUM, FS_SMALL)).pack(side="left", padx=(0, PAD_M))
        tk.Label(inner, text=desc, background=BG_PANEL, foreground=FG_DIM,
                 font=(FONT_UI, FS_SMALL)).pack(side="left")
        return box

    # ------------------------------------------------------------ 分类筛选

    def _build_filter_bar(self, parent=None, *, compact: bool = False) -> None:
        """职业 / 细分职业 / 星级 / 站位 / 搜索。

        463 位干员只按名字翻太费劲，这里按游戏内分类逐级收窄，
        再展开「干员」下拉就只剩同一类的几个人。

        parent  : 挂到哪个容器。默认挂在干员选择器所在的那张卡片里，
                  这样筛选和干员下拉挨在一起，不用上下翻找。
        compact : 紧凑模式（和干员下拉挤在同一行时用）。
        """
        if parent is None:
            parent = getattr(self, "_tools_card", None) or self
        fb = tk.Frame(parent, background=BG_PANEL)
        if compact:
            fb.pack(side="left", fill="x", expand=True, padx=(PAD_M, PAD_XS))
        else:
            fb.pack(fill="x", padx=PAD_S, pady=(PAD_S, PAD_S - 2))

        lpad = 3 if compact else 4

        def add_label(text, pad=(PAD_S if not compact else 4, lpad)):
            tk.Label(fb, text=text, background=BG_PANEL, foreground=FG_DIM,
                     font=(FONT_UI, FS_SMALL)).pack(side="left", padx=pad)

        add_label("筛选", (0, lpad))

        self.var_prof = tk.StringVar(value=OPI.ALL)
        add_label("职业")
        self.cmb_prof = ComboBox(fb, textvariable=self.var_prof,
                                 width=5 if compact else 6,
                                 state="readonly")
        self.cmb_prof.pack(side="left", padx=(0, PAD_S))
        self.cmb_prof.bind("<<ComboboxSelected>>",
                           lambda e: self._on_prof_change())

        self.var_sub = tk.StringVar(value=OPI.ALL)
        add_label("细分")
        self.cmb_sub = ComboBox(fb, textvariable=self.var_sub,
                                width=8 if compact else 10,
                                state="readonly")
        self.cmb_sub.pack(side="left", padx=(0, PAD_S))
        self.cmb_sub.bind("<<ComboboxSelected>>", lambda e: self._apply_filter())

        self.var_star = tk.StringVar(value=OPI.ALL)
        add_label("星级")
        self.cmb_star = ComboBox(fb, textvariable=self.var_star,
                                 width=4 if compact else 5,
                                 state="readonly")
        self.cmb_star.pack(side="left", padx=(0, PAD_S))
        self.cmb_star.bind("<<ComboboxSelected>>", lambda e: self._apply_filter())

        self.var_pos = tk.StringVar(value=OPI.ALL)
        add_label("站位")
        self.cmb_pos = ComboBox(fb, textvariable=self.var_pos,
                                width=5 if compact else 6,
                                state="readonly")
        self.cmb_pos.pack(side="left", padx=(0, PAD_S))
        self.cmb_pos.bind("<<ComboboxSelected>>", lambda e: self._apply_filter())

        add_label("搜索", (PAD_M if not compact else 6, lpad))
        self.var_search = tk.StringVar()
        ent = ttk.Entry(fb, textvariable=self.var_search, style="App.TEntry",
                        width=9 if compact else 12)
        ent.pack(side="left", padx=(0, PAD_S))
        self.var_search.trace_add("write", lambda *a: self._apply_filter())

        ttk.Button(fb, text="重置", style="Ghost.TButton",
                   command=self.reset_filter).pack(side="left", padx=PAD_XS)

        self.lbl_filter = tk.Label(fb, text="", background=BG_PANEL,
                                   foreground=ACCENT,
                                   font=(FONT_UI, FS_SMALL))
        self.lbl_filter.pack(side="left", padx=(6 if compact else PAD_M, 0))
    def _on_prof_change(self) -> None:
        """换职业时，细分职业候选项跟着收窄。"""
        # 筛选栏在伤害面板里，延迟构建：还没建就跳过。
        if not hasattr(self, "var_prof"):
            return
        prof = self.var_prof.get()
        subs = self.op_index.subs_of(prof) if hasattr(self, "op_index") else []
        self.cmb_sub.config(values=[OPI.ALL] + subs)
        self.var_sub.set(OPI.ALL)
        self._apply_filter()

    def reset_filter(self) -> None:
        if not hasattr(self, "var_prof"):
            return
        self.var_prof.set(OPI.ALL)
        self.var_star.set(OPI.ALL)
        self.var_pos.set(OPI.ALL)
        self.var_search.set("")
        self._on_prof_change()

    def _apply_filter(self) -> None:
        """按当前分类收窄干员下拉列表。"""
        if not hasattr(self, "var_prof"):
            return
        if not hasattr(self, "op_index") or not len(self.op_index):
            return
        rarity = OPI.parse_rarity_label(self.var_star.get())
        names = self.op_index.filter(
            profession=self.var_prof.get(),
            sub=self.var_sub.get(),
            rarity=rarity,
            position=self.var_pos.get(),
            query=self.var_search.get(),
        )
        self.cmb_op.config(values=names)
        n = len(names)
        total = len(self.op_index)
        # 未筛选时不刷小结（反正就是全图鉴），筛过才显示分类统计
        if n == total and not self.var_search.get().strip():
            self.lbl_filter.config(text="")
        elif not n:
            self.lbl_filter.config(text="无匹配")
        else:
            self.lbl_filter.config(
                text="%d 位 · %s" % (n, self.op_index.summary(names)))
        if hasattr(self, "lbl_count") and self.lbl_count.winfo_exists():
            self.lbl_count.config(
                text=("共 %d 位（筛出 %d）" % (total, n)) if n != total
                else "共 %d 位" % total)

    # ------------------------------------------------------------ 干员

    def _load_operator_index(self) -> None:
        """载入干员名列表（缓存优先，避免每次联网）。"""
        total = len(self.op_cache.data)
        if not total:
            self.op_index = OPI.OperatorIndex.from_cache({})
            if hasattr(self, "cmb_op"):
                self.cmb_op.config(values=[])
            if hasattr(self, "lbl_count"):
                self.lbl_count.config(text="无缓存")
            self.status.set("请输入干员名后点击「从 PRTS 获取」（首次需联网）")
            return

        # 重建分类索引 + 靠分类下拉的候选项
        self.op_index = OPI.OperatorIndex.from_cache(self.op_cache.data)
        # 控件若已建（伤害面板已经打开过），同步填充；否则等首次构建再填
        self._populate_operator_controls()
        self.status.set("已载入 %d 位干员，可按分类筛选、直接输入或搜索" % total)

    # ------------------------------------------------------------ 对比模式取数

    def operator_names(self) -> List[str]:
        """对比槽位的候选名（与当前分类筛选无关，始终是全图鉴）。"""
        if hasattr(self, "op_index") and len(self.op_index):
            return [r.name for r in self.op_index]
        return sorted(self.op_cache.data.keys())

    def find_operator(self, name: str) -> Optional[Operator]:
        """按名字取干员（缓存里直接构造，不联网）。"""
        name = (name or "").strip()
        if not name:
            return None
        cached = self.op_cache.get(name)
        if not cached:
            # 容忍前面带了职业后缀的情况，比如「能天使｜狙击」
            base = name.split("｜")[0].strip()
            cached = self.op_cache.get(base)
        if not cached:
            return None
        try:
            return PO.dict_to_op(cached)
        except Exception:
            return None

    def pick_operator(self) -> None:
        name = self.var_op.get().strip()
        if not name:
            return
        # 命中缓存直接返回
        cached = self.op_cache.get(name)
        if cached:
            op = PO.dict_to_op(cached)
            self._apply_operator(op)
            return
        self.status.set(f"正在从 PRTS 获取「{name}」…")
        self.btn_fetch.config(state="disabled")
        threading.Thread(target=self._fetch_worker, args=(name,), daemon=True).start()

    def _fetch_worker(self, name: str) -> None:
        try:
            op = PO.load_operator(name, self.op_cache)
        except Exception as e:
            self.after(0, lambda: self._fetch_done(None, str(e)))
            return
        self.after(0, lambda: self._fetch_done(op, ""))

    def _fetch_done(self, op: Optional[Operator], err: str) -> None:
        self.btn_fetch.config(state="normal")
        if not op:
            self.status.set(f"获取失败：{err or '页面不存在或网络异常'}")
            messagebox.showwarning("获取失败",
                                   f"未能从 PRTS 获取该干员。\n{err}\n\n"
                                   "请确认名称与 PRTS 页面标题一致（如「能天使」「史尔特尔」）。")
            return
        self._load_operator_index()
        self._apply_operator(op)
        self.status.set(f"已获取 {op.name}（{len(op.phases)} 个精英阶段）")
        self.status.set_right(self.paths.human_report())

    def _apply_operator(self, op: Operator) -> None:
        self.current_operator = op
        self.var_op.set(op.name)
        self.damage_panel.set_operator(op)

    def sync_all_operators(self) -> None:
        """后台同步 PRTS 全图鉴干员。"""
        if getattr(self, "_syncing", False):
            return
        total = len(self.op_cache.data)
        if not messagebox.askyesno(
                "同步全图鉴",
                "将从 PRTS 抓取全部干员（约 460 位，含技能数据）。\n\n"
                "现有缓存：%d 位。\n\n"
                "增量同步只补缺失的，通常 1 分钟内完成。现在开始？" % total):
            return
        self._syncing = True
        self.btn_sync.config(state="disabled", text="同步中…")
        self.status.set("正在同步 PRTS 全图鉴…")
        threading.Thread(target=self._sync_worker, daemon=True).start()

    def _sync_worker(self) -> None:
        import sync_operators as SYNC
        try:
            SYNC.main(["sync_operators.py"])
            self.after(0, self._sync_done, "")
        except Exception as e:
            self.after(0, self._sync_done, "%s: %s" % (type(e).__name__, e))

    def _sync_done(self, err: str) -> None:
        self._syncing = False
        self.btn_sync.config(state="normal", text="同步全图鉴")
        # 重新加载缓存
        self.op_cache = PO.OperatorCache.load(self.paths.operators_cache)
        self._load_operator_index()
        self.status.set_right(self.paths.human_report())
        if err:
            self.status.set("同步失败：%s" % err)
            messagebox.showwarning("同步失败", err)
        else:
            self.status.set("同步完成，共 %d 位干员" % len(self.op_cache.data))

    # ------------------------------------------------------------ 敌人

    def use_enemy(self, enemy: EnemyStats) -> None:
        """从寻路面板点敌人 -> 切到伤害面板并填入。"""
        self.damage_panel.set_enemy(enemy)
        self.show_view("damage")
        self.status.set(f"已把敌人「{enemy.name}」填入伤害计算")

    def download_enemy_lib(self) -> None:
        if self.enemy_lib.loaded:
            messagebox.showinfo("敌人库", f"敌人库已就绪（{len(self.enemy_lib._by_id)} 条）。")
            return
        if not messagebox.askyesno(
                "下载敌人库",
                "需要下载约 15 MB 的敌人数据库（仅一次，之后离线可用）。\n\n"
                "用于让「寻路计算」显示关卡敌人面板，并一键填入伤害计算。\n\n"
                "现在开始下载？"):
            return

        self.status.set("正在下载敌人库…")

        def worker():
            try:
                self.enemy_lib.download(progress=lambda m: self.after(0, lambda: self.status.set(m)))
            except Exception as e:
                self.after(0, lambda: messagebox.showerror("下载失败", str(e)))
                return
            self.after(0, lambda: self._enemy_lib_done())

        threading.Thread(target=worker, daemon=True).start()

    def _enemy_lib_done(self) -> None:
        self.status.set(f"敌人库下载完成：{len(self.enemy_lib._by_id)} 条")
        self.status.set_right(self.paths.human_report())
        # 若已打开过寻路面板且已有地图，刷新敌人列表；没建过就不必管
        if self._path_panel is not None and self._path_panel.game_map:
            self._path_panel._load_enemies(self._path_panel.game_map.level_id)

    # ------------------------------------------------------------ 杂项

    def show_cache(self) -> None:
        self.status.set_right(self.paths.human_report())
        n_ops = len(self.op_cache.data)
        n_skill = sum(1 for d in self.op_cache.data.values() if d.get("skills"))
        enemy_txt = "已就绪" if self.enemy_lib.loaded else "未下载"
        n_lv = len(self.level_cache.list_cached())
        messagebox.showinfo(
            "缓存信息",
            "缓存目录：\n%s\n\n%s\n\n"
            "干员缓存：%d 位（带技能：%d）\n"
            "敌人库：%s\n"
            "关卡缓存：%d 个"
            % (self.paths.cache_dir, self.paths.human_report(),
               n_ops, n_skill, enemy_txt, n_lv))

    def run(self) -> None:
        self.mainloop()


def main() -> None:
    # 单实例：本程序会用一份共享缓存，开两个会互相踩，所以第二个直接退出。
    # --selftest-compare 是自动化自检入口，不做这个限制。
    if "--selftest-compare" not in sys.argv and "--allow-multi" not in sys.argv:
        if not SI.acquire():
            SI.warn_already_running()
            return
    app = App()
    # 开发自检：--selftest-compare 自动开对比模式并填 5 位，用于打包后验证
    if "--selftest-compare" in sys.argv:
        app.after(600, lambda: _selftest_compare(app))
    app.run()


def _selftest_compare(app: "App") -> None:
    """自动开启对比模式、填入 5 位干员，再把结果打到 stderr 便于打包验证。"""
    import sys as _sys
    try:
        dp = app.damage_panel
        dp.var_compare.set(True)
        dp.toggle_compare()
        picked = []
        for slot, name in zip(dp.cmp_panel.slots,
                              ["能天使", "史尔特尔", "克莱门莎", "艾雅法拉", "银灰"]):
            op = app.find_operator(name)
            if op is None:
                continue
            slot.set_operator(op)
            slot.refresh_skills()
            picked.append(op.name)
        dp.recompute()
        app.update_idletasks()
        n_series = len(dp._chart.series) if dp._chart else 0
        print("[selftest] 对比模式=%s 槽位=%d 曲线=%d 名字=%s 高度=%d" % (
            bool(dp._cmp_packed), len(dp.cmp_panel.slots), n_series,
            picked, dp.chart.winfo_height()), file=_sys.stderr, flush=True)
        print("[selftest] 汇总=%s" % dp.lbl_cmp_table.cget("text"),
              file=_sys.stderr, flush=True)
    except Exception as e:  # 自检失败也要留下痕迹
        import traceback
        traceback.print_exc(file=_sys.stderr)