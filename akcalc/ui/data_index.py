# -*- coding: utf-8 -*-
"""数据索引视图：干员数据 / 怪物数据图鉴。

从主页的「数据索引」两栏进入。两边都是「左边搜索列表 + 右边详情」，
数据全部来自本地缓存，不联网也能用。

干员档案参考 PRTS 风格：大头像、稀有度星标、职业/分支徽章、精英化与
等级选择器、面板 / 信赖 / 潜能 / 模组 / 天赋 / 技能分卡片展示。
怪物图鉴增加「级别 / 位置 / 种族 / 伤害」分类筛选。
"""
from __future__ import annotations

import re
import tkinter as tk
from tkinter import ttk
from typing import Dict, List, Optional, Tuple

from ..core import enemy_class as ECLS
from ..core import enemy_codex as EC
from ..core import enemy_icons as EI
from ..core import operator_icons as OI
from ..core import skilldata as SD
from ..core import skills as SK
from .code_viewer import CodeViewerDialog
from .widgets import (ACCENT, ACCENT_SOFT, ACCENT_TXT, BG, BG_DEEP, BG_PANEL, BG_SUNKEN,
                      BORDER, CARD, DIVIDER, FG, FG_DIM, FONT_NUM, FONT_UI,
                      FS_BODY, FS_H1, FS_MICRO, FS_SMALL, FS_TITLE, PAD_L,
                      PAD_M, PAD_S, PAD_XS, WARN, Card, ComboBox, ScrollFrame,
                      harmonize)

_RARITY = {0: "1★", 1: "2★", 2: "3★", 3: "4★", 4: "5★", 5: "6★"}
_GOLD = "#f5c542"

#: 攻击类型 -> 中文
_ATTACK_CN = {"PHYSICAL": "物理", "MAGICAL": "法术", "HEALING": "治疗",
              "ALL": "混合", "NONE": "无"}

#: 技能等级键的排序顺序：1~7 后面是专精三级
_LV_ORDER = {"1": 1, "2": 2, "3": 3, "4": 4, "5": 5, "6": 6, "7": 7,
             "专一": 8, "专二": 9, "专三": 10}

#: 面板随等级增长的字段
_PHASE_FIELDS = ("hp", "atk", "defense", "magic_resist", "cost", "block",
                 "attack_interval", "redeploy")

#: 潜能加成字段 -> 中文名 + 单位
_POT_CN = {
    "hp": ("生命上限", ""), "atk": ("攻击力", ""), "def": ("防御力", ""),
    "cost": ("部署费用", ""), "re_deploy": ("再部署时间", " 秒"),
    "interval": ("攻击间隔", ""), "res": ("法术抗性", ""),
}

#: 信赖加成字段 -> 中文名
_TRUST_CN = {"hp": "生命上限", "atk": "攻击力", "def": "防御力"}

#: 官方解包源文件（GitHub 主分支），「查看原代码」跳转用
_GITHUB_BASE = "https://github.com/Kengxxiao/ArknightsGameData/blob/master"
_SKILL_TABLE_GH = _GITHUB_BASE + "/zh_CN/gamedata/excel/skill_table.json"
_ENEMY_DB_GH = _GITHUB_BASE + "/zh_CN/gamedata/levels/enemydata/enemy_database.json"

#: 潜能编号 -> 中文（潜能 1 是初始无加成，从 2 开始）
_POT_RANK_CN = {2: "潜能2", 3: "潜能3", 4: "潜能4", 5: "潜能5", 6: "潜能6"}

#: 潜能类型 -> 人类可读（potential_ranks[].type 与 _POT_CN 键对齐）
_POT_TYPE_CN = {"cost": "部署费用", "atk": "攻击力", "def": "防御力",
                "re_deploy": "再部署时间", "hp": "生命上限",
                "interval": "攻击间隔", "res": "法术抗性"}

#: 技能黑板上会出现的状态时长键（官方 skill_table.json blackboard），
#: 值单位是「秒」。精简缓存里不存这些键，展示时按 skillId 回原始表补上。
_STATUS_KEYS = (
    ("stun_duration", "晕眩"), ("stun", "晕眩"), ("stun_time", "晕眩"),
    ("bound", "束缚"), ("frozen", "冻结"), ("frozen_duration", "冻结"),
    ("freeze", "冻结"), ("cold", "寒冷"), ("sleep", "沉睡"),
    ("silence", "沉默"), ("fear", "恐惧"), ("levitate", "浮空"),
    ("levitate_duration", "浮空"), ("slow_down_duration", "减速"),
    ("attack@stun", "晕眩"), ("attack@silence", "沉默"),
    ("attack@sleep", "沉睡"), ("attack@fear", "恐惧"),
    ("attack@levitate", "浮空"), ("attack@slow_down_time", "减速"),
    ("attack@frozen_duration", "冻结"), ("attack@cold", "寒冷"),
)


def _pot_value_text(rank: dict) -> str:
    """把一条潜能提升明细转成可读文字。"""
    if not rank:
        return ""
    txt = (rank.get("text") or "").strip()
    if txt:
        return txt
    typ = rank.get("type") or ""
    val = rank.get("value")
    if not typ and val is None:
        return "天赋效果增强"
    label = _POT_TYPE_CN.get(typ, typ or "天赋")
    if val is None:
        return "%s 效果增强" % label
    try:
        num = "%+g" % float(val)
    except (TypeError, ValueError):
        num = str(val)
    unit = ""
    if typ == "re_deploy":
        unit = " 秒"
    return "%s%s%s" % (label, num, unit)


def _render_skill_desc(text: str) -> str:
    """把 PRTS 富文本（{{color|...}}/{{*|...}}）剥成可读文字。"""
    if not text:
        return ""
    s = _strip_color(str(text))
    s = SK.plain(s)
    return s


def _blackboard_map(level: dict) -> Dict[str, float]:
    """把 raw 技能等级的 blackboard 转成 key->float（兼容 list 与 dict）。"""
    out: Dict[str, float] = {}
    bb = level.get("blackboard")
    if isinstance(bb, dict):
        for k, v in bb.items():
            try:
                out[k] = float(v)
            except (TypeError, ValueError):
                continue
    elif isinstance(bb, list):
        for b in bb:
            if not isinstance(b, dict):
                continue
            k = b.get("key")
            if not k:
                continue
            try:
                out[k] = float(b.get("value"))
            except (TypeError, ValueError):
                continue
    return out


def _status_summary(level: dict) -> str:
    """从 raw 技能等级取状态时长摘要（晕眩/束缚/冻结…，单位秒）。"""
    bb = _blackboard_map(level)
    bits = []
    seen = set()
    for key, label in _STATUS_KEYS:
        v = bb.get(key)
        if v is None:
            continue
        try:
            v = float(v)
        except (TypeError, ValueError):
            continue
        if v <= 0:
            continue
        if label in seen:
            continue
        seen.add(label)
        bits.append("%s%gs" % (label, v))
    return " ".join(bits)


def _last_level_key(levels: dict) -> str:
    """取技能最高等级的键（专三 > 7 > … > 1）。"""
    best, best_v = "", -1
    for k in levels.keys():
        v = _LV_ORDER.get(str(k), 0)
        if v > best_v:
            best, best_v = str(k), v
    return best


def _strip_color(text: str) -> str:
    """去掉 PRTS 富文本模板，只留最终显示的文字。

    模板语法是 ``{{模板名|参数1|参数2|...}}``，显示的是**最后一个参数**，
    而且参数里可以再嵌模板。典型例子::

        {{*|30%|{{color|#0098DC|+30%}}}}
        -> +30%

    老实现用 ``text.find("}}")`` 找闭合括号，遇到嵌套时找到的是**内层**的
    闭合符，内层处理完剩下外层那两个 ``}}`` 没人管，于是图鉴里出现了
    「攻击力+30%}}」这种尾巴（幽灵鲨、能天使等所有带颜色的技能描述都中招）。

    这里改成按括号深度找真正的闭合位置（递归处理嵌套），
    找不到闭合的裸 ``{{`` 原样保留，不会把文本吃掉。
    """
    if not text:
        return ""
    text = str(text)

    def parse(s: str) -> str:
        out = []
        i, n = 0, len(s)
        while i < n:
            if s.startswith("{{", i):
                depth, j = 0, i
                while j < n:
                    if s.startswith("{{", j):
                        depth += 1
                        j += 2
                    elif s.startswith("}}", j):
                        depth -= 1
                        j += 2
                        if depth == 0:
                            break
                    else:
                        j += 1
                if depth != 0:
                    # 没有闭合，原样保留剩余内容
                    out.append(s[i:])
                    break
                inner = s[i + 2:j - 2]
                # 按顶层 | 切分（跳过嵌套模板内部的 |）
                parts, buf, d2, k = [], [], 0, 0
                while k < len(inner):
                    if inner.startswith("{{", k):
                        d2 += 1
                        buf.append("{{")
                        k += 2
                    elif inner.startswith("}}", k):
                        d2 -= 1
                        buf.append("}}")
                        k += 2
                    elif inner[k] == "|" and d2 == 0:
                        parts.append("".join(buf))
                        buf = []
                        k += 1
                    else:
                        buf.append(inner[k])
                        k += 1
                parts.append("".join(buf))
                # 显示文字 = 最后一个参数；单参数模板直接当文本
                shown = parts[-1] if len(parts) >= 2 else ""
                out.append(parse(shown))
                i = j
                continue
            out.append(s[i])
            i += 1
        return "".join(out)

    return parse(text)


def _phase_at(phase: dict, level: int) -> dict:
    """从精英阶段里取某等级的面板值（压缩表线性插值，兼容未压缩表）。"""
    if not phase:
        return {}
    if "lo" in phase and "hi" in phase and "a" in phase and "b" in phase:
        lo, hi = int(phase["lo"]), int(phase["hi"])
        level = max(lo, min(hi, level))
        a = phase.get("a") or {}
        b = phase.get("b") or {}
        t = (level - lo) / max(1, hi - lo)
        out = {}
        for f in _PHASE_FIELDS:
            va, vb = a.get(f), b.get(f)
            if va is None and vb is None:
                continue
            if va is None:
                va = vb
            if vb is None:
                vb = va
            v = va + (vb - va) * t
            out[f] = int(round(v)) if f in ("cost", "block") else v
        return out
    # 未压缩：键是数字等级
    keys = [int(k) for k in phase if str(k).isdigit()]
    if not keys:
        return {}
    k = min(keys, key=lambda x: abs(x - level))
    return phase.get(str(k)) or phase.get(k) or {}


def _fnum(v, dec: int = 0) -> str:
    try:
        f = float(v)
    except (TypeError, ValueError):
        return "—"
    if dec <= 0:
        return "%d" % int(round(f))
    return ("%." + str(dec) + "f") % f


def _fsign(v) -> str:
    try:
        return "%+g" % float(v)
    except (TypeError, ValueError):
        return "—"


def _back_bar(master, app, title: str, subtitle: str) -> tk.Frame:
    """顶部返回条，跟伤害 / 寻路视图保持一致。"""
    bar = tk.Frame(master, background=BG_PANEL, highlightthickness=1,
                   highlightbackground=DIVIDER)
    bar.pack(fill="x")
    inner = tk.Frame(bar, background=BG_PANEL)
    inner.pack(fill="x", padx=PAD_L, pady=PAD_S)

    back = tk.Label(inner, text="←  返回", background=BG_PANEL,
                    foreground=ACCENT, font=(FONT_UI, FS_BODY), cursor="hand2")
    back.pack(side="left")
    back.bind("<Button-1>", lambda e: app.show_view("home"))

    tk.Label(inner, text=title, background=BG_PANEL, foreground=FG,
             font=(FONT_UI, FS_H1, "bold")).pack(side="left", padx=(PAD_L, 0))
    if subtitle:
        tk.Label(inner, text=subtitle, background=BG_PANEL, foreground=FG_DIM,
                 font=(FONT_UI, FS_SMALL)).pack(side="left", padx=(PAD_S, 0))
    return bar


def _chip(master, text: str, color: str = ACCENT) -> tk.Label:
    """小徽章：用于级别 / 位置 / 种族 / 伤害等标签。"""
    return tk.Label(master, text=text, background=BG_DEEP, foreground=color,
                    font=(FONT_UI, FS_SMALL, "bold"), padx=8, pady=2)


def _fmt_num(v) -> str:
    """数值文本：整数不带小数点，其余最多 4 位有效数字。"""
    if v is None:
        return "—"
    try:
        f = float(v)
    except (TypeError, ValueError):
        return str(v)
    if abs(f - round(f)) < 1e-6:
        return "%d" % int(round(f))
    return "%g" % f


def _module_type_cn(t) -> str:
    """模组类型英文代码 -> 中文。

    ``ADVANCED`` 是**真正的模组**（有战斗数值），以前图鉴直接显示
    英文代码，跟旁边的「基础证章」摆在一起很不协调。
    """
    if not t:
        return ""
    s = str(t)
    return {"ADVANCED": "模组", "INITIAL": "基础证章", "ORIGINAL": "原初证章",
            "MISSION": "任务证章", "STAGE": "关卡证章",
            "ACTIVITY": "活动证章", "CHALLENGE": "挑战证章"}.get(s, s)


def _favors_text(v) -> str:
    """解析模组的 ``unlockFavors``；解析不出可靠含义时返回空串。

    这个字段在官方数据里是**字典**而不是数字，例如幽灵鲨的模组二::

        {"1": 0, "2": 2732, "3": 10070}

    旧代码写的是 ``" · 信赖%d" % m["unlock_favors"]``，遇到 dict 直接抛
    ``TypeError: %d format: a real number is required, not dict``——而整个
    ``_render_modules`` 没有 try/except，于是这 388 个干员的天赋卡和技能卡
    也一起被吞掉了（只剩 10 个卫戍协议干员能正常显示）。所以这里必须对
    dict / int / None 都能处理，绝不能抛异常。

    为什么不显示 dict 里的数字
    --------------------------
    503 个模组里 500 个都是同一个 ``{"1":0,"2":2732,"3":10070}``，另 3 个是
    ``{"1":0,"2":0,"3":0}``——这个值对区分模组没有任何信息量。而且它的三个
    键（1/2/3）对应什么、2732 / 10070 是什么单位，在解包数据里没有任何
    线索，凭猜测标成「信赖 2732」会变成新的错误信息。模组的真实解锁条件
    用 ``unlock_phase`` / ``unlock_level`` 两个字段已经表达得很清楚
    （「精英2 · 等级50」），所以这里直接不显示，比编一个含义更靠谱。
    """
    if not v or isinstance(v, dict):
        return ""
    try:
        return "信赖%d" % int(v)
    except (TypeError, ValueError):
        return ""


class _IndexView(tk.Frame):
    """左列表 + 右详情的通用骨架。"""

    def __init__(self, master, app, title: str, subtitle: str):
        super().__init__(master, background=BG)
        self.app = app
        _back_bar(self, app, title, subtitle)

        body = tk.Frame(self, background=BG)
        body.pack(fill="both", expand=True, padx=PAD_L, pady=PAD_M)
        body.columnconfigure(0, weight=0, minsize=280)
        body.columnconfigure(1, weight=1)
        body.rowconfigure(0, weight=1)

        left = tk.Frame(body, background=BG_PANEL, highlightthickness=1,
                        highlightbackground=DIVIDER)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, PAD_M))

        self.var_q = tk.StringVar()
        box = tk.Frame(left, background=BG_PANEL)
        box.pack(fill="x", padx=PAD_S, pady=(PAD_S, PAD_XS))
        tk.Label(box, text="搜索", background=BG_PANEL, foreground=FG_DIM,
                 font=(FONT_UI, FS_SMALL)).pack(side="left")
        self.e_q = tk.Entry(box, textvariable=self.var_q, background=BG_DEEP,
                            foreground=FG, insertbackground=FG,
                            relief="flat", font=(FONT_UI, FS_BODY),
                            highlightthickness=1,
                            highlightbackground=BORDER, bd=0)
        self.e_q.pack(side="left", fill="x", expand=True, padx=(PAD_XS, 0), ipady=3)
        self.var_q.trace_add("write", lambda *a: self._refresh_list())

        # 子类往里塞筛选下拉
        self.filter_bar = tk.Frame(left, background=BG_PANEL)
        self.filter_bar.pack(fill="x", padx=PAD_S, pady=(0, PAD_XS))

        self.lbl_n = tk.Label(left, text="", background=BG_PANEL,
                              foreground=FG_DIM, font=(FONT_NUM, FS_SMALL),
                              anchor="w")
        self.lbl_n.pack(fill="x", padx=PAD_S)

        self.lb = tk.Listbox(left, background=BG_SUNKEN, foreground=FG,
                             selectbackground=ACCENT, selectforeground="#0b1220",
                             relief="flat", highlightthickness=0,
                             font=(FONT_UI, FS_BODY), activestyle="none",
                             bd=0)
        vsb = ttk.Scrollbar(left, orient="vertical", command=self.lb.yview)
        self.lb.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y", pady=(0, PAD_S))
        self.lb.pack(side="left", fill="both", expand=True,
                     padx=(PAD_S, 0), pady=(PAD_XS, PAD_S))
        self.lb.bind("<<ListboxSelect>>", lambda e: self._on_pick())
        # 拖动滚动条 / 按住鼠标划过列表时，<<ListboxSelect>> 会连发几十次，
        # 每次都重建右侧详情（干员面板要 300ms+）。这三个绑定用来判断
        # 「用户还在拖」，拖的时候只记目标不渲染，见 _on_pick 的说明。
        self.lb.bind("<ButtonPress-1>", self._on_press, add="+")
        self.lb.bind("<ButtonRelease-1>", self._on_release, add="+")
        self.lb.bind("<Up>", self._on_key_pick, add="+")
        self.lb.bind("<Down>", self._on_key_pick, add="+")
        self.lb.bind("<Prior>", self._on_key_pick, add="+")
        self.lb.bind("<Next>", self._on_key_pick, add="+")

        # 右侧详情可滚动：内容（面板/技能/模组）通常超过一屏，
        # 用 ScrollFrame 包一层，所有子控件都塞进 self.right.inner。
        self.right = ScrollFrame(body)
        self.right.grid(row=0, column=1, sticky="nsew")
        #: 详情内容的真正挂载点（子类 show_item 都把控件 pack 到这里）
        self.right_inner = self.right.inner

        self._names: List[str] = []
        self._keys: List[str] = []
        #: 拖动节流状态（见 _on_pick）：_dragging 表示左键按在列表上没松，
        #: _pending_idx 是拖动期间最新的目标索引，_last_idx 是已经渲染过的。
        self._dragging = False
        self._pending_idx: Optional[int] = None
        self._last_idx: Optional[int] = None
        self._render_timer = None
        harmonize(self, BG)

    # ------------------------------------------------------------ 列表

    def _set_names(self, pairs: List) -> None:
        """pairs: [(显示名, 键)]"""
        self._names = [p[0] for p in pairs]
        self._keys = [p[1] for p in pairs]
        self._refresh_list(keep=False)

    def _filter_ok(self, key: str, name: str) -> bool:
        """子类覆写：额外的筛选条件（除搜索外）。"""
        return True

    def _refresh_list(self, keep: bool = True) -> None:
        q = (self.var_q.get() or "").strip().lower()
        self.lb.delete(0, "end")
        shown = 0
        self._shown_keys = []
        for nm, key in zip(self._names, self._keys):
            if q and q not in nm.lower() and q not in key.lower() \
                    and q not in self._search_blob(key):
                continue
            if not self._filter_ok(key, nm):
                continue
            self.lb.insert("end", nm)
            self._shown_keys.append(key)
            shown += 1
        self.lbl_n.config(text="%d / %d" % (shown, len(self._names)))
        if keep and self._shown_keys:
            self.lb.selection_set(0)
            self._on_pick()

    def _search_blob(self, key: str) -> str:
        """给搜索用的额外文本（子类覆写）。

        显示名只有「分类 · 名字〔活动〕」这一行，但用户可能搜的是
        机制说明里的词、活动全名、关卡 ID。把这些也拼进来，搜索才不会
        出现「明明有这一条却搜不到」。
        """
        return ""

    def _on_pick(self) -> None:
        """列表选中 -> 立即显示，但「拖动中」先攒着。

        为什么需要攒：每次重建右侧详情要 110~330ms（干员面板最贵）。
        用户按住滚动条快速拖动时，``<<ListboxSelect>>`` 会以每几毫秒
        一个的速度连发，每次都在主线程里建几十个控件，Tk 根本没机会
        把已经排队的中断处理完 —— 表现就是右侧内容「黏成一团」，旧
        条目的残影和新条目的控件叠在一起。

        修法不是在 UI 线程里硬跑，而是判断「用户是不是还在拖」：
        拖动期间只在 ``self._pending_idx`` 记下最新目标，等手松开
        （``ButtonRelease``）或停顿 90ms 后再渲染一次。中间那些索引
        全部丢掉 —— 反正用户已经划过去了，画它们纯属浪费。
        """
        sel = self.lb.curselection()
        if not sel:
            return
        idx = int(sel[0])
        if idx >= len(getattr(self, "_shown_keys", [])):
            return
        # 拖动中：只记目标，不渲染
        if getattr(self, "_dragging", False):
            self._pending_idx = idx
            return
        if self._render_timer is not None:
            try:
                self.after_cancel(self._render_timer)
            except Exception:
                pass
            self._render_timer = None
        self._last_idx = idx
        self.show_item(self._shown_keys[idx])

    # ---------------------------------------------------------- 拖动节流

    def _on_press(self, event=None) -> None:
        self._dragging = True

    def _on_release(self, event=None) -> None:
        """松手：把拖动期间攒下的最后一个目标渲染出来。"""
        if not self._dragging:
            return
        self._dragging = False
        idx = self._pending_idx
        self._pending_idx = None
        if idx is None or idx == self._last_idx:
            return
        if idx >= len(getattr(self, "_shown_keys", [])):
            return
        # 再等一小会儿：避免「松手瞬间又按下」时白渲染一次
        self._render_timer = self.after(16, lambda i=idx: self._flush_pick(i))

    def _flush_pick(self, idx: int) -> None:
        self._render_timer = None
        if idx == self._last_idx:
            return
        if idx >= len(getattr(self, "_shown_keys", [])):
            return
        self._last_idx = idx
        try:
            self.show_item(self._shown_keys[idx])
        except Exception:
            pass

    def _on_key_pick(self, event=None) -> None:
        """方向键上下选：直接渲染（键盘没有「拖动中」这个概念）。"""
        self._dragging = False
        self._pending_idx = None
        self._on_pick()

    def show_item(self, key: str) -> None:
        raise NotImplementedError

    def _clear_right(self) -> None:
        """清空右侧详情。

        先 ``pack_forget`` 再 ``destroy``：直接 destroy 会让所有子控件
        在同一帧里消失，而新内容要等下一帧才排好版，中间那一帧就是
        一片空白 —— 快速划列表时看起来就是「内容黏成一团、闪一下」。
        先摘掉（瞬间，不涉及销毁）再销毁，Tk 只需要重排一次。

        另外顺手把滚动位置复位：新条目从顶部看起，否则如果上一条滚到
        了底部，新条目的内容高度不够时会被钳在中间的怪位置。
        """
        kids = self.right_inner.winfo_children()
        if not kids:
            try:
                self.right.reset_scroll()
            except Exception:
                pass
            return
        for w in kids:
            try:
                w.pack_forget()
            except Exception:
                pass
        for w in kids:
            try:
                w.destroy()
            except Exception:
                pass
        try:
            self.right.reset_scroll()
        except Exception:
            pass
        # 内容换了一整套，让可滚动区域立刻重新量一次（不等用户去拖滚动条）
        try:
            self.right.refresh()
        except Exception:
            pass


class OperatorIndexView(_IndexView):
    """干员数据：头像 / 职业分支 / 面板（可选精英化等级）/ 信赖 / 潜能 / 模组 / 天赋 / 技能。"""

    def __init__(self, master, app):
        super().__init__(master, app, "干员数据", "输入名字筛选，点条目看档案")
        self.ops: Dict[str, dict] = {}
        self._photo = None
        self._filters = {}
        self._load()

    def _load(self) -> None:
        try:
            import json
            d = json.load(open(self.app.paths.operators_cache, encoding="utf-8"))
            self.ops = d.get("operators") or {}
        except Exception:
            self.ops = {}
        if not self.ops:
            tk.Label(self.right_inner, text="还没有干员数据。\n回到主页点「同步数据」下载一次即可。",
                     background=BG, foreground=FG_DIM,
                     font=(FONT_UI, FS_BODY), justify="left").pack(anchor="nw")
            return
        pairs = []
        for name, o in self.ops.items():
            prof = o.get("profession") or ""
            sub = o.get("sub_profession") or ""
            rar = _RARITY.get(int(o.get("rarity") or 0), "")
            pairs.append(("%s%s  %s %s" % (name, "　" + rar if rar else "",
                                           prof, sub), name))
        pairs.sort(key=lambda p: p[0])

        # 职业筛选
        profs = sorted({(o.get("profession") or "") for o in self.ops.values()
                        if o.get("profession")})
        if profs:
            cb = self._add_filter("职业", profs)
            self._filters["profession"] = cb
            # 换了职业就同步收窄「分支」下拉的可选值（近卫 30+ 个分支
            # 全摊在一个下拉里很难找，按职业收窄到 3~8 个）。
            cb.bind("<<ComboboxSelected>>",
                    lambda e: self._sync_sub_filter(), add="+")

        # 子分支（细分职业）筛选
        subs = sorted({(o.get("sub_profession") or "") for o in self.ops.values()
                       if o.get("sub_profession")})
        if subs:
            cb = self._add_filter("分支", subs)
            self._filters["sub_profession"] = cb

        # 星级筛选：按 1★~6★ 收窄
        rars = []
        for o in self.ops.values():
            r = _RARITY.get(int(o.get("rarity") or 0))
            if r and r not in rars:
                rars.append(r)
        if rars:
            rars.sort()
            cb = self._add_filter("星级", rars)
            self._filters["rarity"] = cb

        self._set_names(pairs)

    def _sync_sub_filter(self) -> None:
        """按当前职业刷新「分支」下拉的可选值。

        职业选了具体值时只留该职业下的分支；选「全部」则放开全部。
        原来选中的分支如果不在新集合里，就退回「全部」。
        """
        cb = self._filters.get("sub_profession")
        if cb is None:
            return
        pc = self._filters.get("profession")
        prof = pc.get() if pc is not None else "全部"
        subs = set()
        for o in self.ops.values():
            sub = o.get("sub_profession") or ""
            if not sub:
                continue
            if prof and prof != "全部" and (o.get("profession") or "") != prof:
                continue
            subs.add(sub)
        vals = ["全部"] + sorted(subs)
        cur = cb.get()
        try:
            cb.configure(values=vals)
        except tk.TclError:
            return
        cb.set(cur if cur in vals else "全部")

    def _add_filter(self, label: str, values: List[str]) -> ComboBox:
        row = tk.Frame(self.filter_bar, background=BG_PANEL)
        row.pack(fill="x", pady=1)
        tk.Label(row, text=label, background=BG_PANEL, foreground=FG_DIM,
                 font=(FONT_UI, FS_SMALL)).pack(side="left")
        cb = ComboBox(row, compact=True, values=["全部"] + list(values),
                      width=15)
        cb.set("全部")
        cb.bind("<<ComboboxSelected>>", lambda e: self._refresh_list(keep=True))
        cb.pack(side="left", fill="x", expand=True, padx=(PAD_XS, 0))
        return cb

    def _filter_ok(self, key: str, name: str) -> bool:
        o = self.ops.get(key) or {}
        cb = self._filters.get("profession")
        if cb is not None:
            val = cb.get()
            if val and val != "全部" and (o.get("profession") or "") != val:
                return False
        cb = self._filters.get("sub_profession")
        if cb is not None:
            val = cb.get()
            if val and val != "全部" and (o.get("sub_profession") or "") != val:
                return False
        cb = self._filters.get("rarity")
        if cb is not None:
            val = cb.get()
            if val and val != "全部":
                r = _RARITY.get(int(o.get("rarity") or 0), "")
                if r != val:
                    return False
        return True

    # ------------------------------------------------------------ 详情

    def show_item(self, name: str) -> None:
        o = self.ops.get(name)
        self._clear_right()
        if not o:
            return
        self._o = o
        self._photo = None
        self._build_header(o)

        # 精英化 / 等级选择器
        ctrl = Card(self.right_inner, title="面板数值")
        ctrl.pack(fill="x", pady=(0, PAD_S))
        row = tk.Frame(ctrl.body, background=CARD)
        row.pack(fill="x", pady=(0, PAD_S))
        elites = self._elite_options(o)
        tk.Label(row, text="精英化", background=CARD, foreground=FG_DIM,
                 font=(FONT_UI, FS_SMALL)).pack(side="left")
        self._elite_cb = ComboBox(row, compact=True, values=elites[0], width=8)
        self._elite_cb.set(elites[0][-1])
        self._elite_cb.bind("<<ComboboxSelected>>",
                            lambda e: self._on_elite(o))
        self._elite_cb.pack(side="left", padx=(PAD_XS, PAD_M))
        tk.Label(row, text="等级", background=CARD, foreground=FG_DIM,
                 font=(FONT_UI, FS_SMALL)).pack(side="left")
        lv0 = self._level_options(o, self._cur_elite())
        self._level_cb = ComboBox(row, compact=True, values=lv0, width=8)
        self._level_cb.set(lv0[-1])
        self._level_cb.bind("<<ComboboxSelected>>", lambda e: self._render_stats(o))
        self._level_cb.pack(side="left", padx=(PAD_XS, 0))
        ctrl.harmonize()

        # 潜能选择（第 2 行）：按选择的潜能数重算累计加成
        pot_row = tk.Frame(ctrl.body, background=CARD)
        pot_row.pack(fill="x", pady=(0, PAD_S))
        tk.Label(pot_row, text="潜能", background=CARD, foreground=FG_DIM,
                 font=(FONT_UI, FS_SMALL)).pack(side="left")
        pot_vals = [self._pot_label(o, r) for r in range(0, 6)]
        self._pot_cb = ComboBox(pot_row, compact=True, values=pot_vals, width=26)
        self._pot_cb.set(pot_vals[0])
        self._pot_cb.bind("<<ComboboxSelected>>",
                          lambda e: self._render_stats(o))
        self._pot_cb.pack(side="left", padx=(PAD_XS, 0))

        # 信赖选择（第 3 行）：0~100，信赖加成按比例折算
        trust_row = tk.Frame(ctrl.body, background=CARD)
        trust_row.pack(fill="x", pady=(0, PAD_S))
        tk.Label(trust_row, text="信赖", background=CARD, foreground=FG_DIM,
                 font=(FONT_UI, FS_SMALL)).pack(side="left")
        self._trust_cb = ComboBox(trust_row, compact=True,
                                  values=["0%（无）", "50%（半信赖）",
                                          "100%（满信赖）"], width=18)
        self._trust_cb.set("0%（无）")
        self._trust_cb.bind("<<ComboboxSelected>>",
                            lambda e: self._render_stats(o))
        self._trust_cb.pack(side="left", padx=(PAD_XS, 0))

        # 面板（会随精英化/等级/潜能重建）+ 信赖 + 潜能
        self._stat_host = tk.Frame(self.right_inner, background=BG)
        self._stat_host.pack(fill="x")
        self._render_stats(o)

        # 模组
        # 单独包 try：模组渲染一旦抛异常，以前会把后面的天赋卡和技能卡
        # 一起吞掉（整块 _build_detail 中断），388 个干员看不到天赋/技能。
        # 模组再怎么出问题也不该连累其它卡片。
        try:
            self._render_modules(o)
        except Exception:
            import traceback
            traceback.print_exc()
            self._text_card("模组", ["模组数据渲染失败，请查看控制台日志。"])

        if o.get("talents"):
            self._text_card("天赋", ["　".join(str(x) for x in t)
                                     for t in o["talents"] if t])
        try:
            self._render_skills(o)
        except Exception:
            import traceback
            traceback.print_exc()
            self._text_card("技能", ["技能数据渲染失败，请查看控制台日志。"])

    # ------------------------------------------------------------ 头部

    def _build_header(self, o: dict) -> None:
        name = o.get("name") or ""
        card = Card(self.right_inner)
        card.pack(fill="x", pady=(0, PAD_S))
        row = tk.Frame(card.body, background=CARD)
        row.pack(fill="x")

        # 头像
        size = 132
        canvas = tk.Canvas(row, width=size, height=size, background=BG_SUNKEN,
                           highlightthickness=1, highlightbackground=BORDER,
                           bd=0)
        canvas.pack(side="left", padx=(0, PAD_M))
        self._avatar_canvas = canvas
        self._avatar_size = size
        try:
            im = OI.load_icon(self.app.paths, name, 128)
        except Exception:
            im = None
        if im is not None:
            try:
                from PIL import ImageTk
                self._photo = ImageTk.PhotoImage(im)
                canvas.create_image(size // 2, size // 2, image=self._photo)
            except Exception:
                im = None
        if im is None:
            canvas.create_text(size // 2, size // 2, text=(name or "?")[:1],
                               fill=FG_DIM, font=(FONT_UI, 34, "bold"))
            # 后台补图（不阻塞）；完成后切回主线程刷新画布
            try:
                OI.load_icon_async(self.app.paths, name, 128,
                                   on_done=lambda im2, n=name: self._after(
                                       self._on_avatar_ready, n, im2))
            except Exception:
                pass

        # 右侧信息
        info = tk.Frame(row, background=CARD)
        info.pack(side="left", fill="both", expand=True)

        rarity = int(o.get("rarity") or 0)
        stars = "★" * (rarity + 1)
        head = tk.Frame(info, background=CARD)
        head.pack(fill="x")
        tk.Label(head, text=name, background=CARD, foreground=FG,
                 font=(FONT_UI, FS_TITLE, "bold")).pack(side="left")
        tk.Label(head, text=stars, background=CARD, foreground=_GOLD,
                 font=(FONT_UI, FS_H1)).pack(side="left", padx=(PAD_S, 0))

        # 职业 / 分支 / 位置 / 攻击类型徽章
        chips = tk.Frame(info, background=CARD)
        chips.pack(fill="x", pady=(PAD_S, 0))
        meta = [
            o.get("profession") or "",
            o.get("sub_profession") or "",
            o.get("position") or "",
            _ATTACK_CN.get(o.get("attack_type") or "", o.get("attack_type") or ""),
        ]
        for m in meta:
            if m:
                c = _chip(chips, m)
                c.pack(side="left", padx=(0, PAD_XS))

        char_id = o.get("char_id") or ""
        if char_id:
            tk.Label(info, text=char_id, background=CARD, foreground=FG_DIM,
                     font=(FONT_NUM, FS_SMALL), anchor="w").pack(fill="x",
                     pady=(PAD_S, 0))
        card.harmonize()

    def _after(self, fn, *args) -> None:
        """后台线程回调 -> 主线程（Tk after 必须是主线程调用）。"""
        try:
            self.after(0, fn, *args)
        except Exception:
            pass

    def _on_avatar_ready(self, name: str, im) -> None:
        """后台头像下载完成，刷新画布（切回主线程后调用）。"""
        if im is None:
            return
        try:
            from PIL import ImageTk
            canvas = getattr(self, "_avatar_canvas", None)
            size = getattr(self, "_avatar_size", 132)
            if canvas is None or not canvas.winfo_exists():
                return
            self._photo = ImageTk.PhotoImage(im)
            canvas.delete("all")
            canvas.create_image(size // 2, size // 2, image=self._photo)
        except Exception:
            pass

    # ------------------------------------------------------------ 面板

    def _elite_options(self, o: dict) -> Tuple[List[str], List[int]]:
        phases = o.get("phases") or {}
        elites = sorted((int(k) for k in phases.keys()))
        labels = ["精英%d" % e for e in elites]
        return labels, elites

    def _cur_elite(self) -> int:
        lbl = self._elite_cb.get() if hasattr(self, "_elite_cb") else ""
        for e in (2, 1, 0):
            if lbl == "精英%d" % e:
                return e
        try:
            return int(lbl.replace("精英", ""))
        except (ValueError, AttributeError):
            return 2

    def _level_options(self, o: dict, elite: int) -> List[str]:
        phase = (o.get("phases") or {}).get(str(elite)) or {}
        if "lo" in phase and "hi" in phase:
            lo, hi = int(phase["lo"]), int(phase["hi"])
            return [str(x) for x in range(lo, hi + 1)]
        keys = [int(k) for k in phase if str(k).isdigit()]
        return [str(k) for k in sorted(keys)] or ["1"]

    def _cur_level(self, o: dict, elite: int) -> int:
        try:
            return int(self._level_cb.get())
        except (ValueError, AttributeError):
            lv = self._level_options(o, elite)
            return int(lv[-1]) if lv else 1

    def _on_elite(self, o: dict) -> None:
        elite = self._cur_elite()
        lv = self._level_options(o, elite)
        self._level_cb.configure(values=lv)
        self._level_cb.set(lv[-1])
        self._render_stats(o)

    def _render_stats(self, o: dict) -> None:
        for w in self._stat_host.winfo_children():
            w.destroy()
        elite = self._cur_elite()
        level = self._cur_level(o, elite)
        phase = (o.get("phases") or {}).get(str(elite)) or {}
        st = _phase_at(phase, level)

        # 信赖加成：按当前信赖比例折算到面板
        trust = o.get("trust_bonus") or {}
        trust_ratio = self._cur_trust() / 100.0
        adj = {}
        for k, v in trust.items():
            if k in _TRUST_CN:
                try:
                    adj[k] = float(v) * trust_ratio
                except (TypeError, ValueError):
                    adj[k] = 0.0

        items = [
            ("生命上限", _fnum(st.get("hp") + adj.get("hp", 0.0))),
            ("攻击力", _fnum(st.get("atk") + adj.get("atk", 0.0))),
            ("防御力", _fnum(st.get("defense") + adj.get("def", 0.0))),
            ("法术抗性", _fnum(st.get("magic_resist"))),
            ("部署费用", _fnum(st.get("cost"))),
            ("再部署", _fnum(st.get("redeploy"), 0) + " 秒"),
            ("阻挡数", _fnum(st.get("block"))),
            ("攻击间隔", _fnum(st.get("attack_interval"), 1) + " 秒"),
        ]
        self._stat_grid(self._stat_host, "精英%d · 等级 %s" % (elite, level),
                        items, cols=4)

        tlines = ["%s %s" % (_TRUST_CN[k], _fsign(v * trust_ratio))
                  for k, v in trust.items()
                  if k in _TRUST_CN and abs(float(v)) > 1e-9]
        if tlines:
            self._chip_card(self._stat_host,
                            "信赖加成（%d%%）" % self._cur_trust(), tlines)

        plines, pot_num = self._pot_lines(o)
        if plines:
            self._chip_card(self._stat_host, "潜能加成（%s）" % pot_num,
                            plines)

    def _cur_trust(self) -> int:
        """当前选择的信赖值（0 / 50 / 100）。

        注意：下拉项的文案是「50%（半信赖）」，百分号会粘在数字后面，
        早先用 ``token.isdigit()`` 逐个判断，``"50%"`` 不是纯数字，
        于是**永远**回退到 0，半信赖/满信赖选了也不生效。
        这里改成直接抠出开头的数字。
        """
        txt = ""
        try:
            txt = self._trust_cb.get()
        except Exception:
            pass
        m = re.match(r"\s*(\d+)", str(txt))
        if not m:
            return 0
        return max(0, min(100, int(m.group(1))))

    def _cur_pot(self) -> int:
        """当前选择的潜能数（0~5，0=未选择潜能/初始）。"""
        idx = 0
        try:
            idx = self._pot_cb.current()
        except Exception:
            pass
        if idx < 0:
            txt = self._pot_cb.get()
            try:
                idx = int(str(txt).split("（")[0])
            except (ValueError, AttributeError):
                idx = 0
        return max(0, min(5, idx))

    def _pot_label(self, o: dict, rank: int) -> str:
        """潜能下拉项：rank 0=初始，1~5 对应潜能 2~6。"""
        if rank == 0:
            return "0（无潜能）"
        ranks = o.get("potential_ranks") or []
        detail = ""
        for r in ranks:
            if int(r.get("rank") or 0) == rank + 1:
                detail = _pot_value_text(r)
                break
        suffix = "：%s" % detail if detail else ""
        return "%d（%s%s）" % (rank, _POT_RANK_CN.get(rank + 1, ""), suffix)

    def _pot_lines(self, o: dict):
        """按当前潜能数累加得到加成明细；返回 (行列表, 潜能数)。"""
        n = self._cur_pot()
        ranks = o.get("potential_ranks") or []
        sums = {}
        for r in ranks:
            rk = int(r.get("rank") or 0)
            if rk - 1 > n or rk <= 1:
                continue
            typ = r.get("type") or ""
            val = r.get("value")
            if not typ:
                continue
            if val is None:
                continue
            try:
                sums[typ] = sums.get(typ, 0.0) + float(val)
            except (TypeError, ValueError):
                continue
        lines = []
        for k, v in sums.items():
            if k not in _POT_CN:
                continue
            label, unit = _POT_CN[k]
            lines.append("%s %s%s" % (label, _fsign(v), unit))
        return lines, n

    # ------------------------------------------------------------ 技能

    def _render_skills(self, o: dict) -> None:
        """技能卡片：每个技能一节，含各级描述 + 数值 + 查看原代码。"""
        skills = o.get("skills") or []
        if not skills:
            return
        char_id = o.get("char_id") or ""

        # 先加载完整原始表 + 技能名索引（7MB，一次性）
        full = None
        name_index = None
        try:
            full = SD.load_full()
            name_index = SD.build_name_index(full)
        except Exception:
            full, name_index = None, None

        card = Card(self.right_inner, title="技能")
        card.pack(fill="x", pady=(0, PAD_S))

        for sk in skills:
            nm = sk.get("name") or ""
            levels = sk.get("levels") or {}
            if not isinstance(levels, dict) or not levels:
                continue

            # 该技能的 raw 等级对象（按等级标签 -> blackboard），用于补出
            # 状态时长等精简缓存里没存的信息。
            raw_levels: Dict[str, dict] = {}
            sid = self._skill_id(full, name_index, char_id, nm,
                                 sk.get("index"))
            if sid and full:
                raw_entry = full.get(sid) or {}
                raw_list = raw_entry.get("levels") or []
                for rk, rlv in zip(SD.LEVEL_INDEX.keys(), raw_list):
                    raw_levels[rk] = rlv

            blk = tk.Frame(card.body, background=CARD)
            blk.pack(fill="x", pady=(0, PAD_M))

            hd = tk.Frame(blk, background=CARD)
            hd.pack(fill="x")
            tk.Label(hd, text="■ %s" % nm, background=CARD, foreground=FG,
                     font=(FONT_UI, FS_BODY, "bold")).pack(side="left")

            # 技能类型（攻击回复 / 自动触发 等）
            meta = []
            for key in ("tree_type", "trigger_type"):
                v = (sk.get(key) or "").strip()
                if v and v != "无":
                    meta.append(v)
            if meta:
                tk.Label(hd, text="　".join(meta), background=CARD,
                         foreground=FG_DIM, font=(FONT_UI, FS_MICRO)).pack(
                    side="left", padx=(PAD_S, 0))

            # 查看原代码：等级选择 + 按钮。官方表里一个技能是 levels 数组
            # （1~7 级 + 专一/专二/专三 共 10 个等级），每个等级结构相同、
            # 仅 blackboard/description 数值不同。这里只展示所选等级的单条
            # 原始数据，避免把 10 个几乎一样的对象全部堆出来（用户反馈的
            # 「代码重复」正是这个原因，属官方数据结构，非渲染 bug）。
            lv_opt = sorted(levels.keys(), key=lambda k: _LV_ORDER.get(str(k), 0))
            code_lv = ComboBox(hd, compact=True, values=lv_opt, width=7)
            code_lv.set(lv_opt[-1])
            code_lv.pack(side="right", padx=(PAD_XS, PAD_XS))
            btn = tk.Button(hd, text="查看原代码", relief="flat",
                            background=BG_DEEP, foreground=ACCENT,
                            activebackground=BG_PANEL,
                            activeforeground=ACCENT,
                            font=(FONT_UI, FS_MICRO),
                            highlightthickness=1, highlightbackground=BORDER,
                            cursor="hand2", padx=8, pady=1,
                            command=lambda sid=self._skill_id(
                                full, name_index, char_id, nm,
                                sk.get("index")), cb=code_lv:
                                self._open_skill_code(sid, cb.get()))
            btn.pack(side="right")

            # 各级数值表格：技能等级 -> 数值列
            keys = sorted(levels.keys(), key=lambda k: _LV_ORDER.get(str(k), 0))
            grid = tk.Frame(blk, background=CARD)
            grid.pack(fill="x", pady=(PAD_XS, 0))
            for i, lk in enumerate(keys):
                cell = levels[lk] or {}
                desc = _render_skill_desc(cell.get("description")
                                          or cell.get("desc") or "")
                nums = self._skill_num_text(cell)
                status = _status_summary(raw_levels.get(str(lk)) or {})
                if status:
                    nums = (nums + "  " + status).strip()
                row = tk.Frame(grid, background=CARD)
                row.pack(fill="x", pady=1)
                tk.Label(row, text=str(lk), background=CARD, foreground=ACCENT,
                         font=(FONT_NUM, FS_SMALL, "bold"), width=4,
                         anchor="w").pack(side="left")
                tk.Label(row, text=nums, background=CARD, foreground=FG_DIM,
                         font=(FONT_NUM, FS_MICRO), anchor="w").pack(
                    side="left", padx=(0, PAD_S))
                tk.Label(row, text=desc, background=CARD, foreground=FG,
                         font=(FONT_UI, FS_SMALL), anchor="w",
                         justify="left", wraplength=430).pack(
                    side="left", fill="x", expand=True)
        card.harmonize()

    def _skill_id(self, full, name_index, char_id, skill_name, slot):
        """解析该技能在 skill_table.json 里的 skchr_* id；找不到返回空串。"""
        if not full:
            return ""
        try:
            entry = SD.lookup(full, name_index or {}, char_id, skill_name,
                              int(slot or 0))
        except Exception:
            entry = None
        return (entry.get("skillId") if isinstance(entry, dict)
                else "") or ""

    def _open_skill_code(self, skill_id: str, level_label: str = "专三") -> None:
        """打开「查看原代码」：只展示所选技能等级的单条原始条目。

        官方 skill_table.json 里一个技能是 ``levels`` 数组（10 项：1~7 级
        + 专一/专二/专三），每项结构一致、仅数值不同。早期版本把整个数组
        都交给查看器，看起来像「同一段代码重复了 10 次」，其实是官方数据
        就是这样组织的。现在按等级单选展示，只 dump 那一项。
        """
        if not skill_id:
            return
        try:
            full = SD.load_full()
            entry = full.get(skill_id)
        except Exception:
            full, entry = {}, None
        if not isinstance(entry, dict):
            return
        levels = entry.get("levels") or []
        idx = SD.level_index(level_label)
        if not isinstance(levels, list) or not levels:
            payload = entry
            shown = level_label
            skill_name = ""
        else:
            idx = max(0, min(idx, len(levels) - 1))
            shown = level_label
            skill_name = str(levels[idx].get("name") or "")
            payload = {
                "skillId": entry.get("skillId"),
                "iconId": entry.get("iconId"),
                "hidden": entry.get("hidden"),
                "level": "%s（levels[%d]）" % (level_label, idx),
                "data": levels[idx],
            }
        title = skill_id
        if skill_name:
            title += " · %s" % skill_name
        CodeViewerDialog(
            self, title, payload,
            github_url=_SKILL_TABLE_GH,
            hint=("官方解包 zh_CN/gamedata/excel/skill_table.json 中该技能"
                  "「%s」等级的原始条目（spData / blackboard / description "
                  "未做任何改写）。同一技能的 1~7 级与专一/专二/专三共 10 个"
                  "等级结构相同、仅数值不同，这里只展示所选的一个等级，"
                  "避免重复堆叠。GitHub 上打开的是整张技能表，可用 Ctrl+F "
                  "搜索 skillId。") % shown)

    @staticmethod
    def _skill_num_text(cell: dict) -> str:
        """从单个技能等级取数值摘要。

        展示：攻x倍率 / 单发倍率 / 连击 / 技力 / 初始技力 / 持续 / 间隔 /
        攻速 / 固定攻击力。全部字段都可能缺席（0 或 1），逐个判空，
        避免刷出一串无意义数字。状态时长（晕眩/束缚/冻结…）由
        ``_status_summary`` 从 raw blackboard 单独补，不在这里处理。
        """
        bits = []

        def f(v, default=0.0):
            try:
                return float(v if v is not None else default)
            except (TypeError, ValueError):
                return default

        def fmt(v):
            return ("%g" % v) if abs(v - round(v)) < 1e-9 else ("%.2f" % v)

        atk = f(cell.get("atk_multiplier"), 1.0)
        if abs(atk - 1.0) > 1e-9:
            bits.append("攻x%.2f" % atk)
        dmg = f(cell.get("dmg_scale"), 1.0)
        if abs(dmg - 1.0) > 1e-9:
            bits.append("单发x%.2f" % dmg)
        try:
            if int(cell.get("hit_count", 1) or 1) > 1:
                bits.append("%d连" % int(cell.get("hit_count")))
        except (TypeError, ValueError):
            pass
        cost = f(cell.get("cost"))
        if cost:
            bits.append("技力%s" % fmt(cost))
        init = f(cell.get("initial"))
        if init:
            bits.append("初始%s" % fmt(init))
        dur = f(cell.get("duration"))
        if dur:
            bits.append("%ss" % fmt(dur))
        ivd = f(cell.get("interval_delta"))
        if abs(ivd) > 1e-9:
            bits.append("间隔%+gs" % ivd)
        spd = f(cell.get("attack_speed"))
        if abs(spd) > 1e-9:
            bits.append("攻速%+g" % spd)
        flat = f(cell.get("flat_atk"))
        if abs(flat) > 1e-9:
            bits.append("攻击+%s" % fmt(flat))

        return " ".join(bits)

    def _render_modules(self, o: dict) -> None:
        lib = getattr(self.app, "module_lib", None)
        char_id = o.get("char_id") or ""
        mods = lib.mods_of(char_id) if lib is not None and lib.loaded else []
        if lib is None or not getattr(lib, "loaded", False):
            card = Card(self.right_inner, title="模组")
            card.pack(fill="x", pady=(0, PAD_S))
            tk.Label(card.body, text="模组数据未缓存。", background=CARD,
                     foreground=FG_DIM, font=(FONT_UI, FS_SMALL)).pack(
                anchor="w")
            card.harmonize()
            return
        if not mods:
            self._text_card("模组", ["该干员暂无模组。"])
            return
        card = Card(self.right_inner, title="模组")
        card.pack(fill="x", pady=(0, PAD_S))
        lib = getattr(self.app, "module_lib", None)
        for m in mods:
            blk = tk.Frame(card.body, background=CARD)
            blk.pack(fill="x", pady=(0, PAD_S))
            hd = tk.Frame(blk, background=CARD)
            hd.pack(fill="x")
            tk.Label(hd, text=m.get("name") or "", background=CARD,
                     foreground=FG, font=(FONT_UI, FS_BODY, "bold")).pack(
                side="left")
            if m.get("type"):
                _chip(hd, _module_type_cn(m["type"]), FG_DIM).pack(
                    side="left", padx=(PAD_S, 0))
            unlock = "解锁：%s" % (m.get("unlock_phase") or "")
            if m.get("unlock_level"):
                unlock += " · 等级%d" % m["unlock_level"]
            fav = _favors_text(m.get("unlock_favors"))
            if fav:
                unlock += " · " + fav
            tk.Label(blk, text=unlock, background=CARD, foreground=FG_DIM,
                     font=(FONT_UI, FS_MICRO), anchor="w", justify="left").pack(
                fill="x")

            # ---- 三阶段具体数值（L1/L2/L3 的属性、特性、天赋）
            phases = []
            if lib is not None:
                try:
                    phases = lib.phases_of(m.get("id") or "")
                except Exception:
                    phases = []
            if phases:
                self._render_module_phases(blk, phases)
            elif m.get("desc"):
                tk.Label(blk, text=m["desc"], background=CARD, foreground=FG,
                         font=(FONT_UI, FS_SMALL), anchor="w", justify="left",
                         wraplength=560).pack(fill="x", pady=(PAD_XS, 0))

            # 查看原代码：展示 battle_equip_table.json 里该模组的原始条目
            mid = m.get("id") or ""
            if mid:
                btn = tk.Button(hd, text="查看原代码", relief="flat",
                                background=BG_DEEP, foreground=ACCENT,
                                activebackground=BG_PANEL,
                                activeforeground=ACCENT,
                                font=(FONT_UI, FS_MICRO),
                                highlightthickness=1, highlightbackground=BORDER,
                                cursor="hand2", padx=8, pady=0,
                                command=lambda mid=mid: self._open_module_code(mid))
                btn.pack(side="right")
        card.harmonize()

    def _render_module_phases(self, master, phases) -> None:
        """画模组的三阶段数值：L1 / L2 / L3 各一块。

        模组等级 1/2/3 的 ``attributeBlackboard`` 存的是**累加总量**而非
        增量（1097/1097 单调不减），所以这里直接显示「攻击 +34」这样的
        当前总量，并在括号里补出相对上一级的增量，方便看出每级升了什么。
        """
        prev = {}
        for ph in phases:
            lvl = ph.get("level") or 0
            box = tk.Frame(master, background=CARD)
            box.pack(fill="x", pady=(PAD_XS, 0))
            # 等级标签
            tk.Label(box, text="Lv%d" % lvl, background=BG_DEEP,
                     foreground=ACCENT, font=(FONT_NUM, FS_MICRO, "bold"),
                     padx=6).pack(side="left", anchor="n")

            body = tk.Frame(box, background=CARD)
            body.pack(side="left", fill="x", expand=True, padx=(PAD_S, 0))

            attrs = ph.get("attrs") or []
            if attrs:
                line = []
                for a in attrs:
                    txt = a.get("text") or ""
                    k = a.get("key")
                    try:
                        cur = float(a.get("value"))
                        old = prev.get(k)
                        if old is not None and abs(cur - old) > 1e-9:
                            d = cur - old
                            txt += "（%s%s）" % ("+" if d >= 0 else "",
                                                 _fmt_num(d))
                        prev[k] = cur
                    except (TypeError, ValueError):
                        pass
                    line.append(txt)
                tk.Label(body, text="　".join(line), background=CARD,
                         foreground=FG, font=(FONT_NUM, FS_SMALL),
                         anchor="w", justify="left").pack(fill="x")
            else:
                tk.Label(body, text="（该等级无数值加成）", background=CARD,
                         foreground=FG_DIM, font=(FONT_UI, FS_MICRO),
                         anchor="w").pack(fill="x")

            for t in (ph.get("traits") or []):
                self._module_text_row(body, "特性", t.get("text") or "")
            for t in (ph.get("talents") or []):
                nm = t.get("name") or "天赋"
                self._module_text_row(body, nm, t.get("text") or "")

    def _module_text_row(self, master, tag: str, text: str) -> None:
        if not text:
            return
        row = tk.Frame(master, background=CARD)
        row.pack(fill="x", pady=(1, 0))
        tk.Label(row, text="%s：" % tag, background=CARD, foreground=ACCENT_TXT,
                 font=(FONT_UI, FS_MICRO), anchor="nw").pack(side="left")
        tk.Label(row, text=text, background=CARD, foreground=FG_DIM,
                 font=(FONT_UI, FS_MICRO), anchor="w", justify="left",
                 wraplength=520).pack(side="left", fill="x", expand=True)

    def _open_module_code(self, mod_id: str) -> None:
        """打开模组的原始 battle_equip_table.json 条目。"""
        lib = getattr(self.app, "module_lib", None)
        entry = lib.raw_entry(mod_id) if lib is not None else {}
        CodeViewerDialog(
            self, mod_id, entry, github_url=_GITHUB_BASE +
            "/zh_CN/gamedata/excel/battle_equip_table.json",
            hint=("官方解包 zh_CN/gamedata/excel/battle_equip_table.json 中该"
                  "模组的原始条目（equipLevel / parts / blackboard / 天赋与"
                  "特性数据，未做任何改写）。本地若未缓存完整表，这里只会"
                  "显示空对象；GitHub 上可看整张模组表。"))

    # ------------------------------------------------------------ 通用卡片

    def _stat_grid(self, master, title: str, items, cols: int = 4) -> None:
        card = Card(master, title=title)
        card.pack(fill="x", pady=(0, PAD_S))
        g = tk.Frame(card.body, background=CARD)
        g.pack(fill="x")
        for c in range(cols):
            g.columnconfigure(c, weight=1, uniform="st%d" % cols)
        for i, (label, val) in enumerate(items):
            cell = tk.Frame(g, background=CARD)
            cell.grid(row=i // cols, column=i % cols, sticky="w", pady=2)
            tk.Label(cell, text=str(label), background=CARD,
                     foreground=FG_DIM, font=(FONT_UI, FS_MICRO)).pack(anchor="w")
            tk.Label(cell, text=str(val), background=CARD, foreground=FG,
                     font=(FONT_NUM, FS_BODY, "bold")).pack(anchor="w")
        card.harmonize()

    def _chip_card(self, master, title: str, lines: List[str]) -> None:
        card = Card(master, title=title)
        card.pack(fill="x", pady=(0, PAD_S))
        txt = "　".join(lines)
        tk.Label(card.body, text=txt, background=CARD, foreground=FG,
                 font=(FONT_NUM, FS_BODY), anchor="w", justify="left",
                 wraplength=560).pack(fill="x")
        card.harmonize()

    def _text_card(self, title: str, lines: List[str]) -> None:
        card = Card(self.right_inner, title=title)
        card.pack(fill="x", pady=(0, PAD_S))
        for ln in lines:
            tk.Label(card.body, text=ln, background=CARD, foreground=FG,
                     font=(FONT_UI, FS_SMALL), anchor="w", justify="left",
                     wraplength=560).pack(fill="x", pady=1)
        card.harmonize()


class MonsterIndexView(_IndexView):
    """怪物数据图鉴：列表 + 分类筛选 + 详情（特性 / 技能 / 抗性）。"""

    def __init__(self, master, app):
        super().__init__(master, app, "怪物数据图鉴", "输入名字或按分类筛选")
        self.by_id: Dict[str, list] = {}
        self.names: Dict[str, str] = {}
        self.classmap: Dict[str, dict] = {}
        self._filters: Dict[str, ComboBox] = {}
        self._photo = None
        self._load()

    def _load(self) -> None:
        lib = getattr(self.app, "enemy_lib", None)
        if lib is not None and getattr(lib, "loaded", False):
            self.by_id = lib.by_id
        for eid, ents in self.by_id.items():
            nm = ""
            if ents:
                ed = ents[0].get("enemyData") or {}
                nm = EC._clean(str(EC._mv(ed.get("name"), "") or ""))
                self.classmap[eid] = ECLS.classify(ed)
            self.names[eid] = nm or eid
        if not self.names:
            try:
                import json
                seed = self.app._read_bundled_json("enemy_names.json") or {}
                self.names = dict(seed)
            except Exception:
                self.names = {}

        # 分类筛选
        dims = ECLS.all_dimensions(self.by_id)
        for dim in ECLS.CATEGORY_DIMS:
            vals = dims.get(dim)
            if vals:
                cb = self._add_filter(dim, vals)
                self._filters[dim] = cb

        pairs = sorted(((nm, eid) for eid, nm in self.names.items()),
                       key=lambda p: p[0])
        self._set_names(pairs)

    def _add_filter(self, label: str, values: List[str]) -> ComboBox:
        row = tk.Frame(self.filter_bar, background=BG_PANEL)
        row.pack(fill="x", pady=1)
        tk.Label(row, text=label, background=BG_PANEL, foreground=FG_DIM,
                 font=(FONT_UI, FS_SMALL)).pack(side="left")
        cb = ComboBox(row, compact=True, values=["全部"] + list(values),
                      width=14)
        cb.set("全部")
        cb.bind("<<ComboboxSelected>>", lambda e: self._refresh_list(keep=True))
        cb.pack(side="left", fill="x", expand=True, padx=(PAD_XS, 0))
        return cb

    def _filter_ok(self, key: str, name: str) -> bool:
        cls = self.classmap.get(key, {})
        for dim, cb in self._filters.items():
            val = cb.get()
            if val and val != "全部" and cls.get(dim) != val:
                return False
        return True

    def show_item(self, eid: str) -> None:
        self._clear_right()
        nm = self.names.get(eid) or eid
        entries = self.by_id.get(eid)
        entry = EC.codex_entry(entries, 0, eid) if entries else None

        head = Card(self.right_inner)
        head.pack(fill="x", pady=(0, PAD_S))
        hrow = tk.Frame(head.body, background=CARD)
        hrow.pack(fill="x")

        icon = tk.Canvas(hrow, width=96, height=96, background=BG_SUNKEN,
                         highlightthickness=1, highlightbackground=BORDER, bd=0)
        icon.pack(side="left", padx=(0, PAD_M))
        self._mon_icon_canvas = icon
        self._photo = None
        had_real = False
        try:
            im = EI.load_icon(self.app.paths, nm, 96)
        except Exception:
            im = None
        if im is not None:
            try:
                from PIL import ImageTk
                self._photo = ImageTk.PhotoImage(im)
                icon.create_image(48, 48, image=self._photo)
                had_real = True
            except Exception:
                im = None
        if im is None:
            # 无头像：画带首字的占位块（内存生成，不落盘），再后台补图
            try:
                im = EI.placeholder_icon(nm, 96)
            except Exception:
                im = None
            if im is not None:
                try:
                    from PIL import ImageTk
                    self._photo = ImageTk.PhotoImage(im)
                    icon.create_image(48, 48, image=self._photo)
                except Exception:
                    im = None
        if im is None:
            icon.create_text(48, 48, text=(nm or "?")[:1], fill=FG_DIM,
                             font=(FONT_UI, FS_TITLE, "bold"))
        if not had_real:
            try:
                EI.load_icon_async(self.app.paths, nm, 96,
                                   on_done=lambda im2, n=nm: self._after(
                                       self._on_mon_icon_ready, n, im2))
            except Exception:
                pass

        tb = tk.Frame(hrow, background=CARD)
        tb.pack(side="left", fill="both", expand=True)
        tk.Label(tb, text=nm, background=CARD, foreground=FG,
                 font=(FONT_UI, FS_TITLE, "bold"), anchor="w").pack(fill="x")
        idrow = tk.Frame(tb, background=CARD)
        idrow.pack(fill="x")
        tk.Label(idrow, text=eid, background=CARD, foreground=FG_DIM,
                 font=(FONT_NUM, FS_MICRO), anchor="w").pack(side="left")
        if entries:
            btn = tk.Button(idrow, text="查看原代码", relief="flat",
                            background=BG_DEEP, foreground=ACCENT,
                            activebackground=BG_PANEL,
                            activeforeground=ACCENT,
                            font=(FONT_UI, FS_MICRO),
                            highlightthickness=1, highlightbackground=BORDER,
                            cursor="hand2", padx=8, pady=0,
                            command=lambda: self._open_enemy_code(eid,
                                                                  entries))
            btn.pack(side="right")

        # 分类徽章
        cls = self.classmap.get(eid, {})
        chips = tk.Frame(tb, background=CARD)
        chips.pack(fill="x", pady=(PAD_XS, 0))
        for dim in ECLS.CATEGORY_DIMS:
            if dim in cls:
                _chip(chips, cls[dim]).pack(side="left", padx=(0, PAD_XS))

        if entry and entry.get("desc"):
            tk.Label(tb, text=entry["desc"], background=CARD,
                     foreground=FG_DIM, font=(FONT_UI, FS_SMALL),
                     anchor="w", justify="left", wraplength=460).pack(
                fill="x", pady=(PAD_S, 0))
        head.harmonize()

        if not entry:
            tk.Label(self.right_inner, text="本地敌人库缺这条数据（可能尚未下载）。",
                     background=BG, foreground=FG_DIM,
                     font=(FONT_UI, FS_BODY)).pack(anchor="w")
            return

        self._grid_card("基础面板", entry["stats"], 4)
        res = entry["resists"] + entry.get("extra", [])
        self._grid_card("抗性", res, 4)
        if entry.get("immunes"):
            self._grid_card("免疫", [("状态", "、".join(entry["immunes"]))], 2)
        if entry.get("skills"):
            self._line_card("技能", entry["skills"])
        if entry.get("talent"):
            self._line_card("天赋 / 光环", [entry["talent"]])

    def _open_enemy_code(self, eid: str, entries) -> None:
        """打开敌人原始 enemyData JSON（enemy_database.json）。"""
        # 选 level 0 那一档（默认档），并把 id 也带进去便于阅读
        best = None
        for e in entries or []:
            if int(e.get("level", 0) or 0) == 0:
                best = e
                break
        if best is None and entries:
            best = entries[0]
        if not isinstance(best, dict):
            return
        payload = {"enemy_id": eid, **best}
        CodeViewerDialog(
            self, eid, payload, github_url=_ENEMY_DB_GH,
            hint=("官方解包 zh_CN/gamedata/levels/enemydata/"
                  "enemy_database.json 中该敌人的原始条目（enemyData 含 "
                  "attributes / skills / talentBlackboard / motion 等字段，"
                  "未做任何改写）。GitHub 上打开的是整张敌人库，可用 "
                  "Ctrl+F 搜索 enemy_id。"))

    def _after(self, fn, *args) -> None:
        try:
            self.after(0, fn, *args)
        except Exception:
            pass

    def _on_mon_icon_ready(self, name: str, im) -> None:
        """后台敌人图标下载完成，刷新画布（主线程）。"""
        if im is None:
            return
        try:
            from PIL import ImageTk
            canvas = getattr(self, "_mon_icon_canvas", None)
            if canvas is None or not canvas.winfo_exists():
                return
            self._photo = ImageTk.PhotoImage(im)
            canvas.delete("all")
            canvas.create_image(48, 48, image=self._photo)
        except Exception:
            pass

    def _grid_card(self, title: str, items, cols: int) -> None:
        card = Card(self.right_inner, title=title)
        card.pack(fill="x", pady=(0, PAD_S))
        g = tk.Frame(card.body, background=CARD)
        g.pack(fill="x")
        for c in range(cols):
            g.columnconfigure(c, weight=1, uniform="mg%d" % cols)
        for i, (label, val) in enumerate(items):
            cell = tk.Frame(g, background=CARD)
            cell.grid(row=i // cols, column=i % cols, sticky="w", pady=1)
            tk.Label(cell, text=str(label), background=CARD,
                     foreground=FG_DIM, font=(FONT_UI, FS_MICRO)).pack(anchor="w")
            tk.Label(cell, text=str(val), background=CARD, foreground=FG,
                     font=(FONT_NUM, FS_SMALL, "bold")).pack(anchor="w")
        card.harmonize()

    def _line_card(self, title: str, lines) -> None:
        card = Card(self.right_inner, title=title)
        card.pack(fill="x", pady=(0, PAD_S))
        for ln in lines:
            tk.Label(card.body, text=ln, background=CARD, foreground=FG,
                     font=(FONT_UI, FS_SMALL), anchor="w", justify="left",
                     wraplength=560).pack(fill="x", pady=1)
        card.harmonize()


#: 数据字段图鉴的数据文件（由 codex_fields.json 提供）
FIELDS_JSON = "codex_fields.json"


class FieldsIndexView(_IndexView):
    """数据字段图鉴：解包数据里每个字段 / token 到底存了什么。

    数据来自 ``data/codex_fields.json``（145 个字段 + 200 个 token）。
    左列表按「分类 · 名字」排列并支持搜索，右侧显示路径、类型、
    真实取值样例和中文解释。

    这个视图解决的是「套用套用」那类问题：官方解包字段名很多是
    Unity 序列化残留（``m_defined`` / ``m_value``）、拼写错误
    （``overrideDescripton`` 少个 i）、或者语义完全反直觉
    （``checkpointType`` 其实叫 ``type``；``prefabKey`` 在四处
    含义各不相同）。把每一条摊开写清楚，比让用户猜要靠谱。
    """

    def __init__(self, master, app):
        super().__init__(master, app, "数据字段图鉴",
                         "搜索字段名 / 路径 / 说明 / 活动名，查看真实取值")
        self.fields: List[dict] = []
        self.tokens: List[dict] = []
        self._kind: Dict[str, tuple] = {}
        self._items: List[dict] = []
        #: 分类 -> 该分类下的条目数，用来填「分类」下拉
        self._cats: Dict[str, int] = {}

        # 种类筛选：字段 / 参数 / 机制 / 状态机
        cb = self._add_filter("种类", ["字段", "参数", "机制", "状态机"])
        self._cb_kind = cb
        # 分类筛选：敌人数据 / 关卡地图 / 干员数据 / 活动机制 ...
        # 放在种类下面单独一行，两者是「与」关系。
        self._cb_cat = self._add_filter("分类", [])

        self._load()

    def _add_filter(self, label: str, values: List[str]) -> ComboBox:
        row = tk.Frame(self.filter_bar, background=BG_PANEL)
        row.pack(fill="x", pady=1)
        tk.Label(row, text=label, background=BG_PANEL, foreground=FG_DIM,
                 font=(FONT_UI, FS_SMALL)).pack(side="left")
        cb = ComboBox(row, compact=True, values=["全部"] + list(values),
                      width=14)
        cb.set("全部")
        cb.bind("<<ComboboxSelected>>", lambda e: self._refresh_list(keep=True))
        cb.pack(side="left", fill="x", expand=True, padx=(PAD_XS, 0))
        return cb

    def _fill_categories(self) -> None:
        """把实际出现过的分类灌进下拉，按条目数从多到少排。"""
        cats = sorted(self._cats.items(), key=lambda kv: (-kv[1], kv[0]))
        vals = ["全部"] + ["%s(%d)" % (c, n) for c, n in cats]
        try:
            self._cb_cat.configure(values=vals)
        except Exception:
            pass
        self._cb_cat.set("全部")

    def _load(self) -> None:
        data = {}
        try:
            import json
            data = self.app._read_bundled_json(FIELDS_JSON) or {}
        except Exception:
            data = {}
        self.fields = data.get("fields") or []
        self.tokens = data.get("tokens") or []
        # 活动机制图鉴（各活动关卡独有的特殊机制）单独一份数据
        self.mechs = data.get("mechanics") or []
        self._mech_by_key: Dict[str, dict] = {}
        # 状态机图鉴（干员技能生命周期）
        self.states = data.get("statemachines") or []

        items = []
        self._cats = {}
        for i, f in enumerate(self.fields):
            nm = f.get("name") or "字段%d" % i
            key = "F%d" % i
            cat = f.get("category") or ""
            self._kind[key] = ("字段", f)
            if cat:
                self._cats[cat] = self._cats.get(cat, 0) + 1
            items.append((("%s · %s" % (cat, nm)) if cat else nm, key))
        for i, t in enumerate(self.tokens):
            nm = t.get("key") or "token%d" % i
            key = "T%d" % i
            cat = t.get("category") or ""
            self._kind[key] = ("参数", t)
            if cat:
                self._cats[cat] = self._cats.get(cat, 0) + 1
            items.append((("%s · %s" % (cat, nm)) if cat else nm, key))
        for i, m in enumerate(self.mechs):
            nm = m.get("name") or "机制%d" % i
            key = "M%d" % i
            cat = m.get("category") or "活动机制"
            self._kind[key] = ("机制", m)
            self._mech_by_key[key] = m
            if cat:
                self._cats[cat] = self._cats.get(cat, 0) + 1
            # 活动名也进显示名，这样搜索「将进酒」这种活动名能命中。
            # 只放前 2 个活动，否则标签会长到把列表撑爆；完整列表在右侧。
            acts = m.get("events") or []
            label = "%s · %s" % (cat, nm)
            if acts:
                head = "、".join(acts[:2])
                more = "等%d个" % len(acts) if len(acts) > 2 else ""
                label += "  〔%s%s〕" % (head, more)
            items.append((label, key))
        for i, s in enumerate(self.states):
            nm = s.get("name") or "技能%d" % i
            key = "S%d" % i
            cat = s.get("category") or "状态机"
            self._kind[key] = ("状态机", s)
            if cat:
                self._cats[cat] = self._cats.get(cat, 0) + 1
            cyc = (s.get("metrics") or {}).get("循环周期")
            label = "%s · %s" % (cat, nm)
            if cyc:
                label += "  〔周期 %s〕" % cyc
            items.append((label, key))
        self._items = items
        self.lbl_hint = tk.Label(
            self, text="", background=BG, foreground=FG_DIM,
            font=(FONT_NUM, FS_MICRO))
        self._fill_categories()
        self._set_names(items)
        if not items:
            self.lbl_n.config(text="未找到 codex_fields.json")

    def _search_blob(self, key: str) -> str:
        """让搜索能命中活动名 / 关卡 ID / 说明正文。

        机制条目最常被搜的是「这活动有什么特殊机制」，用户会直接打
        活动名（如「连阴雨季」），而活动名并不在显示名的前两格里。
        状态机条目则要能用技能 id（skchr_svrash_3）搜到。
        """
        kind, rec = self._kind.get(key, ("", {}))
        if kind == "机制":
            parts = []
            parts.extend(rec.get("events") or [])
            parts.extend(rec.get("stages") or [])
            for f in ("desc", "effect", "impl", "data", "kind"):
                v = rec.get(f)
                if v:
                    parts.append(str(v))
            return " ".join(parts).lower()
        if kind == "状态机":
            parts = [str(rec.get("skill_id") or ""), str(rec.get("desc") or "")]
            parts.extend(str(k2) for k2 in (rec.get("metrics") or {}))
            return " ".join(parts).lower()
        return ""

    def _filter_ok(self, key: str, name: str) -> bool:
        want = self._cb_kind.get()
        if want and want != "全部":
            kind = (self._kind.get(key) or ("", {}))[0]
            if kind != want:
                return False
        # 分类下拉的值带计数后缀，比如「敌人数据(42)」，比较时剥掉
        cat = self._cb_cat.get() or "全部"
        if cat != "全部":
            base = cat.rsplit("(", 1)[0]
            rec = (self._kind.get(key) or ("", {}))[1]
            if (rec.get("category") or "") != base:
                return False
        return True

    def show_item(self, key: str) -> None:
        self._clear_right()
        kind, rec = self._kind.get(key, ("", {}))
        if not rec:
            return
        if kind == "参数":
            self._show_token(rec)
        elif kind == "机制":
            self._show_mech(rec)
        elif kind == "状态机":
            self._show_state(rec)
        else:
            self._show_field(rec)

    # ------------------------------------------------------------ 详情

    def _show_field(self, rec: dict) -> None:
        card = Card(self.right_inner)
        card.pack(fill="x", pady=(0, PAD_S))
        hd = tk.Frame(card.body, background=CARD)
        hd.pack(fill="x")
        tk.Label(hd, text=rec.get("name") or "", background=CARD,
                 foreground=FG, font=(FONT_UI, FS_TITLE, "bold")).pack(side="left")
        if rec.get("category"):
            _chip(hd, rec["category"], ACCENT).pack(side="left",
                                                   padx=(PAD_S, 0))
        if rec.get("type"):
            _chip(hd, str(rec["type"]), FG_DIM).pack(side="left",
                                                    padx=(PAD_S, 0))
        path = rec.get("path") or ""
        if path:
            self._kv(card.body, "路径", path, mono=True)
        desc = rec.get("desc") or ""
        if desc:
            self._kv(card.body, "说明", desc, wrap=560)
        card.harmonize()

        # 使用样例：光有字段说明还是不知道怎么用，直接给一段能跑的代码
        usage = rec.get("usage") or ""
        if usage:
            card_u = Card(self.right_inner, title="使用样例")
            card_u.pack(fill="x", pady=(0, PAD_S))
            tk.Label(card_u.body, text=usage, background=BG_DEEP,
                     foreground=ACCENT_TXT, font=(FONT_NUM, FS_SMALL),
                     anchor="w", justify="left", wraplength=600).pack(
                fill="x", padx=PAD_S, pady=PAD_S)
            card_u.harmonize()

        # 易错点：这一条比说明更有用，都是踩过的坑
        pit = rec.get("pitfall") or ""
        if pit:
            card_p = Card(self.right_inner, title="易错点")
            card_p.pack(fill="x", pady=(0, PAD_S))
            tk.Label(card_p.body, text="⚠ " + pit, background=CARD,
                     foreground=WARN, font=(FONT_UI, FS_SMALL), anchor="w",
                     justify="left", wraplength=560).pack(fill="x")
            card_p.harmonize()

        ex = rec.get("examples") or []
        if ex:
            card2 = Card(self.right_inner, title="真实取值")
            card2.pack(fill="x", pady=(0, PAD_S))
            for e in ex:
                tk.Label(card2.body, text="· " + str(e), background=CARD,
                         foreground=FG, font=(FONT_NUM, FS_SMALL), anchor="w",
                         justify="left", wraplength=560).pack(fill="x", pady=1)
            card2.harmonize()

    def _show_token(self, rec: dict) -> None:
        card = Card(self.right_inner)
        card.pack(fill="x", pady=(0, PAD_S))
        hd = tk.Frame(card.body, background=CARD)
        hd.pack(fill="x")
        tk.Label(hd, text=str(rec.get("key") or ""), background=CARD,
                 foreground=ACCENT, font=(FONT_NUM, FS_TITLE, "bold")).pack(
            side="left")
        if rec.get("category"):
            _chip(hd, rec["category"], FG_DIM).pack(side="left",
                                                   padx=(PAD_S, 0))
        cnt = rec.get("count")
        if cnt:
            _chip(hd, "出现 %s 次" % _fmt_num(cnt), ACCENT).pack(
                side="left", padx=(PAD_S, 0))
        desc = rec.get("desc") or ""
        if desc:
            self._kv(card.body, "含义", desc, wrap=560)
        card.harmonize()
        usage = rec.get("usage") or ""
        if usage:
            card_u = Card(self.right_inner, title="使用样例")
            card_u.pack(fill="x", pady=(0, PAD_S))
            tk.Label(card_u.body, text=usage, background=BG_DEEP,
                     foreground=ACCENT_TXT, font=(FONT_NUM, FS_SMALL),
                     anchor="w", justify="left", wraplength=600).pack(
                fill="x", padx=PAD_S, pady=PAD_S)
            card_u.harmonize()

    def _show_mech(self, rec: dict) -> None:
        """活动关卡特殊机制：重点是「用在哪一关」，不是抽象说明。"""
        card = Card(self.right_inner)
        card.pack(fill="x", pady=(0, PAD_S))
        hd = tk.Frame(card.body, background=CARD)
        hd.pack(fill="x")
        tk.Label(hd, text=str(rec.get("name") or ""), background=CARD,
                 foreground=FG, font=(FONT_UI, FS_TITLE, "bold")).pack(
            side="left")
        if rec.get("category"):
            _chip(hd, rec["category"], ACCENT).pack(side="left",
                                                   padx=(PAD_S, 0))
        if rec.get("kind"):
            _chip(hd, str(rec["kind"]), FG_DIM).pack(side="left",
                                                    padx=(PAD_S, 0))
        desc = rec.get("desc") or ""
        if desc:
            self._kv(card.body, "机制", desc, wrap=560)
        if rec.get("effect"):
            self._kv(card.body, "效果", rec["effect"], wrap=560)
        card.harmonize()

        # 用在哪：活动 / 关卡列表，这是用户最想查的
        acts = rec.get("events") or []
        stages = rec.get("stages") or []
        if acts or stages:
            card_w = Card(self.right_inner, title="出现位置")
            card_w.pack(fill="x", pady=(0, PAD_S))
            if acts:
                self._kv(card_w.body, "活动", "、".join(acts), wrap=560)
            if stages:
                self._kv(card_w.body, "关卡", "、".join(stages), wrap=560)
            card_w.harmonize()

        # 对应程序实现：告诉用户这个机制在我们的代码/数据里怎么落地
        impl = rec.get("impl") or ""
        if impl:
            card_i = Card(self.right_inner, title="程序实现")
            card_i.pack(fill="x", pady=(0, PAD_S))
            tk.Label(card_i.body, text=impl, background=BG_DEEP,
                     foreground=ACCENT_TXT, font=(FONT_NUM, FS_SMALL),
                     anchor="w", justify="left", wraplength=600).pack(
                fill="x", padx=PAD_S, pady=PAD_S)
            card_i.harmonize()

        data = rec.get("data") or ""
        if data:
            card_d = Card(self.right_inner, title="解包字段")
            card_d.pack(fill="x", pady=(0, PAD_S))
            tk.Label(card_d.body, text=data, background=BG_DEEP,
                     foreground=ACCENT_TXT, font=(FONT_NUM, FS_SMALL),
                     anchor="w", justify="left", wraplength=600).pack(
                fill="x", padx=PAD_S, pady=PAD_S)
            card_d.harmonize()

        pit = rec.get("pitfall") or ""
        if pit:
            card_p = Card(self.right_inner, title="易错点")
            card_p.pack(fill="x", pady=(0, PAD_S))
            tk.Label(card_p.body, text="⚠ " + pit, background=CARD,
                     foreground=WARN, font=(FONT_UI, FS_SMALL), anchor="w",
                     justify="left", wraplength=560).pack(fill="x")
            card_p.harmonize()

    def _show_state(self, rec: dict) -> None:
        """状态机图鉴：状态表 + 稳态指标 + 时间条。

        时间条不是装饰：用户真正想知道的是「这技能多少秒能开一次、
        覆盖率多少」。把 CHARGING / ACTIVE 按真实秒数等比画成色带，
        比读一堆数字直观。
        """
        card = Card(self.right_inner)
        card.pack(fill="x", pady=(0, PAD_S))
        hd = tk.Frame(card.body, background=CARD)
        hd.pack(fill="x")
        tk.Label(hd, text=str(rec.get("name") or ""), background=CARD,
                 foreground=FG, font=(FONT_UI, FS_TITLE, "bold")).pack(
            side="left")
        if rec.get("category"):
            _chip(hd, rec["category"], ACCENT).pack(side="left",
                                                   padx=(PAD_S, 0))
        if rec.get("kind"):
            _chip(hd, str(rec["kind"]), FG_DIM).pack(side="left",
                                                    padx=(PAD_S, 0))
        if rec.get("skill_id"):
            _chip(hd, str(rec["skill_id"]), FG_DIM).pack(side="left",
                                                         padx=(PAD_S, 0))
        desc = rec.get("desc") or ""
        if desc:
            self._kv(card.body, "技能", desc, wrap=560)
        card.harmonize()

        # 时间条：把 CHARGING 与 ACTIVE 按真实比例画成色带
        metrics = rec.get("metrics") or {}
        try:
            cyc = float(str(metrics.get("循环周期", "")).replace("秒", ""))
        except (TypeError, ValueError):
            cyc = 0.0
        dur = 0.0
        for st in (rec.get("states") or []):
            if str(st.get("state") or "").startswith("ACTIVE"):
                try:
                    dur = float(str(st.get("duration", "")).replace("秒", ""))
                except (TypeError, ValueError):
                    dur = 0.0
                break
        if cyc > 0 and dur > 0:
            card_b = Card(self.right_inner, title="循环时间条")
            card_b.pack(fill="x", pady=(0, PAD_S))
            cv = tk.Canvas(card_b.body, height=54, background=BG_DEEP,
                           highlightthickness=0, bd=0)
            cv.pack(fill="x", padx=PAD_S, pady=PAD_S)

            def _paint(_e=None):
                cv.delete("all")
                w = max(120, cv.winfo_width())
                x0, y0 = 8, 10
                bw, bh = w - 16, 22
                charge = max(0.0, cyc - dur)
                wc = bw * charge / cyc
                cv.create_rectangle(x0, y0, x0 + wc, y0 + bh,
                                    fill=DIVIDER, outline="")
                cv.create_rectangle(x0 + wc, y0, x0 + bw, y0 + bh,
                                    fill=ACCENT, outline="")
                cv.create_text(x0 + wc / 2, y0 + bh / 2,
                               text="充能 %.0fs" % charge,
                               fill=FG_DIM, font=(FONT_NUM, FS_MICRO))
                cv.create_text(x0 + wc + (bw - wc) / 2, y0 + bh / 2,
                               text="技能 %.0fs" % dur,
                               fill="#0b1220", font=(FONT_NUM, FS_MICRO))
                cv.create_text(x0, y0 + bh + 12, text="0s", anchor="w",
                               fill=FG_DIM, font=(FONT_NUM, FS_MICRO))
                cv.create_text(x0 + bw, y0 + bh + 12,
                               text="%.0fs" % cyc, anchor="e",
                               fill=FG_DIM, font=(FONT_NUM, FS_MICRO))
            cv.bind("<Configure>", _paint)
            _paint()
            card_b.harmonize()

        # 稳态指标
        if metrics:
            card_m = Card(self.right_inner, title="稳态指标")
            card_m.pack(fill="x", pady=(0, PAD_S))
            for k, v in metrics.items():
                self._kv(card_m.body, str(k), str(v), wrap=520)
            card_m.harmonize()

        # 状态表
        states = rec.get("states") or []
        if states:
            card_s = Card(self.right_inner, title="状态转移")
            card_s.pack(fill="x", pady=(0, PAD_S))
            head = tk.Frame(card_s.body, background=CARD)
            head.pack(fill="x")
            for t, w in (("状态", 26), ("时长", 20), ("依据", 40)):
                tk.Label(head, text=t, width=w, anchor="w", background=CARD,
                         foreground=FG_DIM,
                         font=(FONT_UI, FS_MICRO)).pack(side="left")
            for st in states:
                row = tk.Frame(card_s.body, background=CARD)
                row.pack(fill="x", pady=1)
                tk.Label(row, text=str(st.get("state") or ""), width=26,
                         anchor="w", background=CARD, foreground=ACCENT_TXT,
                         font=(FONT_UI, FS_SMALL)).pack(side="left")
                tk.Label(row, text=str(st.get("duration") or ""), width=20,
                         anchor="w", background=CARD, foreground=FG,
                         font=(FONT_NUM, FS_SMALL)).pack(side="left")
                tk.Label(row, text=str(st.get("note") or ""), anchor="w",
                         background=CARD, foreground=FG_DIM,
                         font=(FONT_UI, FS_MICRO)).pack(side="left",
                                                        fill="x", expand=True)
            card_s.harmonize()

        data = rec.get("data") or ""
        if data:
            card_d = Card(self.right_inner, title="数据来源")
            card_d.pack(fill="x", pady=(0, PAD_S))
            tk.Label(card_d.body, text=data, background=BG_DEEP,
                     foreground=ACCENT_TXT, font=(FONT_NUM, FS_SMALL),
                     anchor="w", justify="left", wraplength=600).pack(
                fill="x", padx=PAD_S, pady=PAD_S)
            card_d.harmonize()

        pit = rec.get("pitfall") or ""
        if pit:
            card_p = Card(self.right_inner, title="易错点")
            card_p.pack(fill="x", pady=(0, PAD_S))
            tk.Label(card_p.body, text="⚠ " + pit, background=CARD,
                     foreground=WARN, font=(FONT_UI, FS_SMALL), anchor="w",
                     justify="left", wraplength=560).pack(fill="x")
            card_p.harmonize()

    def _kv(self, master, label: str, value: str, mono: bool = False,
            wrap: int = 0) -> None:
        row = tk.Frame(master, background=CARD)
        row.pack(fill="x", pady=(PAD_XS, 0))
        tk.Label(row, text=label, background=CARD, foreground=FG_DIM,
                 font=(FONT_UI, FS_MICRO), width=6, anchor="nw").pack(side="left")
        kw = {}
        if wrap:
            kw["wraplength"] = wrap
        tk.Label(row, text=value, background=CARD,
                 foreground=FG if not mono else ACCENT_TXT,
                 font=(FONT_NUM if mono else FONT_UI, FS_SMALL), anchor="w",
                 justify="left", **kw).pack(side="left", fill="x", expand=True)