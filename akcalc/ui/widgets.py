"""共享 UI 控件与深色主题。

配色沿用原有深灰蓝（BG / BG_PANEL / ACCENT …），重做的是层级与形态：

- ``Card``：带强调色竖条标题、细分隔线的卡片；
- ``harmonize``：自动把卡片内部所有控件改成卡片底色。以前卡片里塞的是
  ``BG`` 底色的 ttk 控件，会在 ``BG_PANEL`` 上留下一块块更深的矩形，
  这是界面显脏的主因；这里统一递归修掉，新增控件也自动生效；
- 标签页改胶囊式，选中态直接铺强调色；
- 按钮分主 / 次 / 幽灵三档。
"""
from __future__ import annotations

import ctypes
import tkinter as tk
from tkinter import ttk
from typing import Dict, List, Optional, Sequence, Tuple

# ---------------------------------------------------------------- 主题色
# 基础三色（保持原值，其它模块按名字导入）
BG = "#171a21"
BG_PANEL = "#1f242e"
BG_INPUT = "#2a303c"
FG = "#e8ecf1"
#: 次要文字。原来是 #9aa5b4，在 #1f242e 卡片底上只有 4.4:1，
#: 在 #12151b 深底上勉强 4.9:1，小字号下偏灰。提亮一档到 6.5:1 以上，
#: 仍然是「次要」的观感，但不用凑近看。
FG_DIM = "#aab6c6"
ACCENT = "#4ea1f7"
BORDER = "#333c4a"

# 层级：卡片沿用 BG_PANEL，只把标题条提亮一档，不引入新主色
BG_DEEP = "#12151b"       # 窗口最底 / 标签栏槽
BG_SUNKEN = "#161a21"     # 凹陷区（文本块、图表底）
CARD = BG_PANEL           # 卡片底色
CARD_HEAD = "#252b36"     # 卡片标题条
HOVER = "#303845"
ACTIVE = "#39434f"
DIVIDER = "#2f3745"

#: 强调色的「文字版」。原来的 #2c4a6b 是深底浅字的**背景**色，
#: 后来被当成前景色用了十几处（字段图鉴的路径、模组特性名、技能
#: prefabKey……），结果深蓝印在 #12151b 上，对比度只有 2.06:1，
#: 肉眼几乎看不见。这里拆成两个常量：
#:   ACCENT_SOFT —— 只当**背景**（选中行底色），保持深色
#:   ACCENT_TXT  —— 只当**前景**（文字），提亮到 9:1 以上
ACCENT_SOFT = "#2c4a6b"   # 背景：Treeview 选中行
ACCENT_TXT = "#8fc2f0"    # 前景：等宽/次要强调文字（对比度 9.2:1）
ACCENT_DIM = "#3d8ad6"

#: 语义色。全部收敛到 ACCENT 这一支蓝，和「伤害计算」页保持一致。
#:
#: 原来的 OK 是绿 #2ecc71、WARN 是黄 #f1c40f，在深底上和 ACCENT 蓝并列时
#: 会出现三种色相；寻路分析、干员数据、怪物图鉴、字段图鉴这几个页面又各自
#: 用了橙/紫/青做标题，整机看下来有七八种颜色，视线找不到落点。
#:
#: 现在「正常」和「需要注意」都只靠**文字和措辞**区分，颜色统一表达
#: 「这是本页的强调元素」。DANGER 保留红色——它是真的错误态（
#: 更新检查失败），红色在语义上不可替代。
OK = ACCENT_TXT
WARN = ACCENT_TXT
DANGER = "#e74c3c"
#: 图表多曲线兜底色。第一条是 ACCENT 蓝，其余用蓝的深浅档；
#: 红色只留给「技能中」这类对比曲线（damage_panel 里显式指定的）。
SERIES = ["#4ea1f7", "#e74c3c", "#8fc2f0", "#ff8a7a", "#3d8ad6", "#c0392b"]

# 下拉弹层/选中项：浅底黑字，保证在任何主题下都清晰可读
CMB_BG = "#e6e9ee"       # 下拉框底色（浅）
CMB_FG = "#10141a"       # 下拉框文字（近黑）
CMB_SEL_BG = "#9ec9f5"   # 选中项底色（浅蓝）
CMB_POP = "#ffffff"      # 弹出列表底色（白）
CMB_POP_FG = "#10141a"   # 弹出列表文字（黑）
CMB_POP_SEL_BG = "#9ec9f5"   # 弹出列表选中底色（浅蓝）
CMB_POP_SEL_FG = "#10141a"   # 弹出列表选中文字（黑）

# ---------------------------------------------------------------- 字号 / 间距

FONT_UI = "Microsoft YaHei UI"
FONT_NUM = "Consolas"

# 字号基准值。运行时可整体放大/缩小（见 set_font_scale），
# 这样「设置」里换字体大小不用重启程序。
FS_BASE = {
    "FS_TITLE": 18,
    "FS_H1": 14,
    "FS_BODY": 11,
    "FS_SMALL": 10,
    "FS_MICRO": 9,
    "FS_NUM": 11,
}
FS_TITLE = FS_BASE["FS_TITLE"]
FS_H1 = FS_BASE["FS_H1"]
FS_BODY = FS_BASE["FS_BODY"]
FS_SMALL = FS_BASE["FS_SMALL"]
FS_MICRO = FS_BASE["FS_MICRO"]
FS_NUM = FS_BASE["FS_NUM"]

# 当前缩放档位（1.0 = 标准）。UI 层用它做「字体大小」设置。
FONT_SCALE = 1.0


def font_scale() -> float:
    """当前字号缩放比例。"""
    return FONT_SCALE


def scaled(base: int) -> int:
    """把基准字号按当前比例换算成实际字号（至少 7 号，再小看不清）。"""
    return max(7, int(round(base * FONT_SCALE)))


def set_font_scale(scale: float) -> float:
    """改字号缩放，返回实际生效的比例。

    各面板里的 tk 控件在创建时就把字号写进了 font= 参数，改模块级常量
    只能影响之后新建的控件。所以这里除了更新常量，还要把已经建好的
    控件逐个重设字体——`apply_font_scale(widget)` 做那件事。
    """
    global FONT_SCALE, FS_TITLE, FS_H1, FS_BODY, FS_SMALL, FS_MICRO, FS_NUM
    try:
        scale = float(scale)
    except (TypeError, ValueError):
        return FONT_SCALE
    FONT_SCALE = min(2.0, max(0.75, scale))
    FS_TITLE = scaled(FS_BASE["FS_TITLE"])
    FS_H1 = scaled(FS_BASE["FS_H1"])
    FS_BODY = scaled(FS_BASE["FS_BODY"])
    FS_SMALL = scaled(FS_BASE["FS_SMALL"])
    FS_MICRO = scaled(FS_BASE["FS_MICRO"])
    FS_NUM = scaled(FS_BASE["FS_NUM"])
    return FONT_SCALE


# 基准字号 -> 作用（用于把已建控件按角色重新放大）
_FS_ROLE = (("FS_TITLE", 18), ("FS_H1", 14), ("FS_BODY", 11),
            ("FS_SMALL", 10), ("FS_MICRO", 9), ("FS_NUM", 11))


def apply_font_scale(widget, scale: float = 0.0) -> None:
    """递归把 widget 及其子控件的字号按比例重设。

    只处理本项目 FONT_UI / FONT_NUM 的控件。做法是把控件当前的「基准
    字号」（缩放前的大小）挂在控件自身的 _base_font_size 上，之后每次
    都用「基准 x 比例」重算，所以反复切换不会越改越大，也不需要额外
    维护一张全局表（那会因为控件销毁而泄漏）。
    """
    if scale <= 0:
        scale = FONT_SCALE
    try:
        cur = widget.cget("font")
    except Exception:
        cur = ""
    if cur:
        fam, size = _split_font(cur)
        if fam in (FONT_UI, FONT_NUM) and size:
            base = getattr(widget, "_base_font_size", 0)
            if not base:
                # 首次：按「当前值 / 上次全局比例」还原出基准
                prev = getattr(widget, "_base_font_scale", FONT_SCALE) or 1.0
                base = max(7, int(round(abs(size) / prev)))
                try:
                    widget._base_font_size = base
                except Exception:
                    base = abs(size)
            new = max(7, int(round(base * scale)))
            try:
                widget.configure(font=(fam, new))
            except Exception:
                pass
    for ch in widget.winfo_children():
        apply_font_scale(ch, scale)


def _split_font(spec) -> tuple:
    """把 tkinter 的 font 描述拆成 (字体名, 字号)。取不到时返回 ('', 0)。

    注意 cget("font") 对含空格的字体名会返回 "{Microsoft YaHei UI} 9"
    这种带大括号的字符串，必须先把大括号剥掉，否则永远匹配不上常量。
    """
    if isinstance(spec, str):
        txt = spec.strip()
        if txt.startswith("{"):
            close = txt.find("}")
            if close > 0:
                return txt[1:close].strip(), _int_after(txt[close + 1:])
            return "", 0
        parts = txt.rsplit(None, 1)
        if len(parts) >= 1 and parts[-1].lstrip("-").isdigit():
            fam = " ".join(txt.rsplit(" ", 1)[:-1]).strip() or txt
            return fam, int(parts[-1])
        return "", 0
    if isinstance(spec, (tuple, list)) and spec:
        fam = str(spec[0])
        for x in spec[1:]:
            if isinstance(x, int):
                return fam, x
        return fam, 0
    return "", 0


def _int_after(txt: str) -> int:
    """从 "9 bold" 之类的尾巴里取出第一个整数。"""
    num = ""
    for ch in txt.strip():
        if ch.isdigit() or (ch == "-" and not num):
            num += ch
        elif num:
            break
    try:
        return int(num) if num else 0
    except ValueError:
        return 0
    if isinstance(spec, (tuple, list)) and spec:
        fam = str(spec[0])
        size = 0
        for x in spec[1:]:
            if isinstance(x, int):
                size = x
                break
        return fam, size
    return "", 0

PAD_XS, PAD_S, PAD_M, PAD_L = 2, 6, 10, 14

# 卡片内 ttk 样式映射：harmonize 用它把 BG 底色的控件换成卡片底色
_CARD_STYLE_MAP = {
    "App.TFrame": "Card.TFrame",
    "App.TLabel": "Card.TLabel",
    "Hint.TLabel": "CardHint.TLabel",
    "Title.TLabel": "Card.TLabel",
    "App.TCheckbutton": "Card.TCheckbutton",
    "App.TRadiobutton": "Card.TRadiobutton",
    "App.TEntry": "App.TEntry",
}


def apply_dark_style(root: tk.Misc) -> ttk.Style:
    """应用深色主题（clam + 全套显式配色，不用系统默认值）。"""
    style = ttk.Style(root)
    try:
        style.theme_use("clam")
    except tk.TclError:
        pass

    # ---- 基础
    style.configure(".", background=BG, foreground=FG, borderwidth=0,
                    focuscolor=BG_INPUT, font=(FONT_UI, FS_BODY))

    # ---- 容器
    style.configure("App.TFrame", background=BG)
    style.configure("Deep.TFrame", background=BG_DEEP)
    style.configure("Panel.TFrame", background=BG_PANEL)
    style.configure("Card.TFrame", background=CARD)
    style.configure("CardHead.TFrame", background=CARD_HEAD)

    # ---- 文字
    style.configure("App.TLabel", background=BG, foreground=FG,
                    font=(FONT_UI, FS_BODY))
    style.configure("Hint.TLabel", background=BG, foreground=FG_DIM,
                    font=(FONT_UI, FS_SMALL))
    style.configure("Title.TLabel", background=BG, foreground=FG,
                    font=(FONT_UI, FS_H1, "bold"))
    style.configure("Card.TLabel", background=CARD, foreground=FG,
                    font=(FONT_UI, FS_BODY))
    style.configure("CardHint.TLabel", background=CARD, foreground=FG_DIM,
                    font=(FONT_UI, FS_SMALL))
    style.configure("Section.TLabel", background=CARD, foreground=ACCENT,
                    font=(FONT_UI, FS_BODY, "bold"))
    style.configure("Mono.TLabel", background=BG, foreground=FG,
                    font=(FONT_NUM, FS_NUM))
    style.configure("Brand.TLabel", background=BG_DEEP, foreground=FG,
                    font=(FONT_UI, FS_TITLE, "bold"))
    style.configure("BrandSub.TLabel", background=BG_DEEP, foreground=ACCENT,
                    font=(FONT_UI, FS_SMALL))

    # ---- 复选框 / 单选
    for name, bg in (("App.TCheckbutton", BG), ("App.TRadiobutton", BG),
                     ("Card.TCheckbutton", CARD), ("Card.TRadiobutton", CARD)):
        style.configure(name, background=bg, foreground=FG,
                        font=(FONT_UI, FS_BODY), focuscolor=bg,
                        padding=(0, 1))
        style.map(name,
                  background=[("active", bg), ("selected", bg)],
                  foreground=[("active", ACCENT)],
                  indicatorcolor=[("selected", ACCENT),
                                  ("pressed", ACCENT_DIM),
                                  ("!selected", BG_INPUT)])

    # ---- 按钮：主 / 次 / 幽灵
    style.configure("App.TButton", background=BG_INPUT, foreground=FG,
                    borderwidth=0, padding=(PAD_M, 5), relief="flat",
                    focusthickness=0, font=(FONT_UI, FS_BODY))
    style.map("App.TButton",
              background=[("pressed", ACTIVE), ("active", HOVER)],
              foreground=[("active", FG)])

    style.configure("Accent.TButton", background=ACCENT, foreground="#0c1017",
                    borderwidth=0, padding=(PAD_L, 6), relief="flat",
                    focusthickness=0, font=(FONT_UI, FS_BODY, "bold"))
    style.map("Accent.TButton",
              background=[("pressed", ACCENT_DIM), ("active", "#6bb4ff")],
              foreground=[("active", "#0c1017")])

    style.configure("Ghost.TButton", background=BG_DEEP, foreground=FG_DIM,
                    borderwidth=0, padding=(PAD_S, 4), relief="flat",
                    focusthickness=0, font=(FONT_UI, FS_SMALL))
    style.map("Ghost.TButton",
              background=[("active", BG_INPUT)],
              foreground=[("active", ACCENT)])

    # ---- 下拉框：浅底 + 黑字
    style.configure("App.TCombobox", fieldbackground=CMB_BG, background=BG_INPUT,
                    foreground=CMB_FG, arrowcolor=CMB_FG, borderwidth=0,
                    bordercolor=BORDER, lightcolor=BORDER, darkcolor=BORDER,
                    selectbackground=CMB_SEL_BG, selectforeground=CMB_FG,
                    insertcolor=CMB_FG, padding=(5, 3),
                    font=(FONT_UI, FS_BODY))
    style.map("App.TCombobox",
              fieldbackground=[("readonly", CMB_BG), ("disabled", BG_INPUT)],
              foreground=[("readonly", CMB_FG), ("disabled", FG_DIM)],
              selectbackground=[("readonly", CMB_SEL_BG)],
              selectforeground=[("readonly", CMB_FG)],
              arrowcolor=[("disabled", FG_DIM), ("active", ACCENT_DIM)])

    # ---- 紧凑下拉框（对比模式槽位用，省竖向空间）
    style.configure("Compact.TCombobox", fieldbackground=CMB_BG,
                    background=BG_INPUT, foreground=CMB_FG, arrowcolor=CMB_FG,
                    borderwidth=0, bordercolor=BORDER, lightcolor=BORDER,
                    darkcolor=BORDER, selectbackground=CMB_SEL_BG,
                    selectforeground=CMB_FG, padding=(3, 0),
                    font=(FONT_UI, FS_SMALL))
    style.map("Compact.TCombobox",
              fieldbackground=[("readonly", CMB_BG), ("disabled", BG_INPUT)],
              foreground=[("readonly", CMB_FG), ("disabled", FG_DIM)],
              selectbackground=[("readonly", CMB_SEL_BG)],
              selectforeground=[("readonly", CMB_FG)],
              arrowcolor=[("disabled", FG_DIM), ("active", ACCENT_DIM)])

    # ---- 输入框
    style.configure("App.TEntry", fieldbackground=BG_INPUT, foreground=FG,
                    insertcolor=FG, borderwidth=0, padding=(6, 4),
                    font=(FONT_UI, FS_BODY))
    style.map("App.TEntry", bordercolor=[("focus", ACCENT)])

    # ---- 标签页：胶囊式，选中铺强调色
    # 注意：不要自定义 App.TNotebook.Tab 的 layout 去掉 Notebook.padding，
    # 否则 padding 完全不生效，页签会缩成紧贴文字的一条，很难看。
    style.configure("App.TNotebook", background=BG_DEEP, borderwidth=0,
                    tabmargins=(PAD_M, PAD_M, PAD_M, 0))
    style.layout("App.TNotebook", [
        ("App.TNotebook.client", {"sticky": "nswe"}),
    ])
    style.layout("App.TNotebook.Tab", [
        ("Notebook.tab", {"sticky": "nswe", "children": [
            ("Notebook.padding", {"side": "top", "sticky": "nswe",
                                   "children": [
                ("Notebook.focus", {"side": "top", "sticky": "nswe",
                                     "children": [
                    ("Notebook.label", {"side": "top", "sticky": ""}),
                ]}),
            ]}),
        ]}),
    ])
    style.configure("App.TNotebook.Tab", background=BG_PANEL, foreground=FG_DIM,
                    padding=(22, 8), borderwidth=0, focusthickness=0,
                    font=(FONT_UI, FS_BODY, "bold"))
    style.map("App.TNotebook.Tab",
              background=[("selected", ACCENT), ("active", HOVER)],
              foreground=[("selected", "#0c1017"), ("active", FG)],
              expand=[("selected", (0, 0, 0, 0))])

    # ---- 表格
    style.configure("App.Treeview", background=BG_SUNKEN,
                    fieldbackground=BG_SUNKEN, foreground="#dbe3ee",
                    borderwidth=0, rowheight=24, font=(FONT_UI, FS_BODY))
    style.map("App.Treeview",
              background=[("selected", ACCENT_SOFT)],
              foreground=[("selected", "#ffffff")])
    style.configure("App.Treeview.Heading", background=CARD_HEAD,
                    foreground=FG_DIM, borderwidth=0, relief="flat",
                    font=(FONT_UI, FS_SMALL, "bold"), padding=(6, 5))
    style.map("App.Treeview.Heading", background=[("active", HOVER)],
              foreground=[("active", FG)])

    # ---- 滚动条
    for orient in ("Vertical", "Horizontal"):
        name = "%s.TScrollbar" % orient
        style.configure(name, background=BG_INPUT, troughcolor=BG_SUNKEN,
                        borderwidth=0, arrowcolor=FG_DIM,
                        width=10 if orient == "Vertical" else 10)
        style.map(name, background=[("active", HOVER)])

    style.configure("App.TSeparator", background=DIVIDER)
    style.configure("App.TSpinbox", fieldbackground=BG_INPUT, foreground=FG,
                    borderwidth=0, arrowcolor=FG)

    # 下拉弹层内框（ttk 内部画的那圈灰边）
    style.configure("ComboboxPopdownFrame", background=CMB_POP, borderwidth=0,
                    relief="flat", lightcolor=CMB_POP, darkcolor=CMB_POP,
                    bordercolor=CMB_POP)
    return style


# ---------------------------------------------------------------- 调色

def harmonize(widget: tk.Misc, bg: str = CARD) -> None:
    """把 ``widget`` 子树里所有用旧底色的控件改成 ``bg``。

    卡片里原本塞满 ``BG`` 底色的 Label/Frame/Checkbutton，在 ``BG_PANEL``
    卡片上就是一块块更深的矩形。这里一次性抹平，之后新加的控件也自动跟随。
    """
    for child in widget.winfo_children():
        cls = child.winfo_class()
        try:
            if cls in ("Frame", "Label", "Checkbutton", "Radiobutton",
                       "Canvas", "Message"):
                if str(child.cget("background")) == BG:
                    child.configure(background=bg)
                if cls == "Checkbutton":
                    if str(child.cget("activebackground")) == BG:
                        child.configure(activebackground=bg)
                    if str(child.cget("selectcolor")) == BG:
                        child.configure(selectcolor=BG_INPUT)
                if cls == "Label" and str(child.cget("foreground")) == FG:
                    pass
            elif cls in ("TFrame", "TLabel", "TCheckbutton", "TRadiobutton"):
                cur = str(child.cget("style"))
                if cur in _CARD_STYLE_MAP:
                    child.configure(style=_CARD_STYLE_MAP[cur])
                elif cur == "" and cls in ("TFrame", "TLabel"):
                    child.configure(style="Card.TFrame" if cls == "TFrame"
                                    else "Card.TLabel")
        except tk.TclError:
            pass
        harmonize(child, bg)


# ---------------------------------------------------------------- 控件

class ComboBox(ttk.Combobox):
    """统一样式的下拉框。

    ttk.Combobox 的弹出列表是一个独立的 Tk listbox，不受 ttk 样式控制，
    必须直接改它的 -background/-foreground，否则会是系统色或出现白字。
    """

    def __init__(self, master, compact: bool = False, **kw):
        kw.setdefault("state", "readonly")
        if compact:
            kw.setdefault("style", "Compact.TCombobox")
        else:
            kw.setdefault("style", "App.TCombobox")
        super().__init__(master, **kw)
        # 弹层窗口首次展开时才创建并上色（_refresh_before_post 里做了），
        # 构造期就建会强制 Tk 立刻创建 listbox 弹层，38 个下拉框累计
        # 拖慢启动 0.15s+，且大部分用户根本不会挨个点开。
        self.bind("<Button-1>", self._refresh_before_post, add="+")
        self.bind("<Down>", self._refresh_before_post, add="+")
        self.bind("<F4>", self._refresh_before_post, add="+")

    def _refresh_before_post(self, _event=None) -> None:
        self.after(10, self._style_popdown)

    def _style_popdown(self) -> None:
        def setopt(path, *pairs) -> None:
            for opt, val in pairs:
                try:
                    self.tk.call(path, "configure", opt, val)
                except tk.TclError:
                    pass

        try:
            pop = str(self.tk.call("ttk::combobox::PopdownWindow", str(self)))
        except tk.TclError:
            return
        setopt(pop + ".f.l",
               ("-background", CMB_POP),
               ("-foreground", CMB_POP_FG),
               ("-selectbackground", CMB_POP_SEL_BG),
               ("-selectforeground", CMB_POP_SEL_FG),
               ("-borderwidth", 0),
               ("-highlightthickness", 0),
               ("-font", (FONT_UI, FS_BODY)))
        setopt(pop + ".f.sb",
               ("-background", CMB_POP),
               ("-troughcolor", CMB_POP),
               ("-bordercolor", CMB_POP),
               ("-arrowcolor", CMB_POP_FG),
               ("-lightcolor", CMB_POP),
               ("-darkcolor", CMB_POP),
               ("-borderwidth", 0))
        setopt(pop,
               ("-background", CMB_POP),
               ("-highlightbackground", CMB_POP),
               ("-highlightcolor", CMB_POP),
               ("-highlightthickness", 0),
               ("-borderwidth", 0))

    def post(self) -> None:
        """展开下拉前再刷一次弹层颜色（弹层可能被重建）。"""
        self._style_popdown()
        try:
            self.tk.call("ttk::combobox::Post", str(self))
        except tk.TclError:
            pass


class Card(tk.Frame):
    """卡片：可选标题条（强调色竖条 + 标题 + 右侧插槽）+ 细分隔线 + 内容区。"""

    def __init__(self, master, title: str = "", *, accent: str = ACCENT,
                 pad: Tuple[int, int] = (PAD_M, PAD_M), **kw):
        kw.pop("style", None)
        super().__init__(master, background=CARD,
                         highlightthickness=1,
                         highlightbackground=DIVIDER,
                         highlightcolor=DIVIDER, **kw)
        self._accent = accent
        self.head: Optional[tk.Frame] = None
        self.title_label: Optional[tk.Label] = None
        self.head_right: Optional[tk.Frame] = None

        outer = tk.Frame(self, background=CARD)
        outer.pack(fill="both", expand=True)

        if title:
            self.head = tk.Frame(outer, background=CARD)
            self.head.pack(fill="x", padx=pad[0], pady=(PAD_S, 0))
            stripe = tk.Frame(self.head, background=accent, width=3)
            stripe.pack(side="left", fill="y", padx=(0, 8))
            stripe.pack_propagate(False)
            self.title_label = tk.Label(
                self.head, text=title, background=CARD, foreground=FG,
                font=(FONT_UI, FS_BODY, "bold"))
            self.title_label.pack(side="left")
            self.head_right = tk.Frame(self.head, background=CARD)
            self.head_right.pack(side="right")
            tk.Frame(outer, background=DIVIDER, height=1).pack(
                fill="x", padx=pad[0], pady=(PAD_S, 0))

        self.body = tk.Frame(outer, background=CARD)
        self.body.pack(fill="both", expand=True, padx=pad[0],
                       pady=(PAD_S if title else PAD_M, pad[1]))

    def harmonize(self) -> None:
        """把 body 内的控件统一成卡片底色（建完子控件后调用）。"""
        harmonize(self.body)

    def set_title(self, text: str) -> None:
        if self.title_label is not None:
            self.title_label.config(text=text)


class SectionFrame(Card):
    """带标题的分区块（卡片的语义化别名，保留旧调用方式）。"""

    def __init__(self, master, title: str, **kw):
        kw.pop("style", None)
        super().__init__(master, title=title, **kw)


class LabeledEntry(tk.Frame):
    """标签 + 输入框。"""

    def __init__(self, master, label: str, default: str = "",
                 width: int = 12, **kw):
        super().__init__(master, background=CARD, **kw)
        self.var = tk.StringVar(value=default)
        lbl = tk.Label(self, text=label, background=CARD, foreground=FG_DIM,
                       font=(FONT_UI, FS_SMALL), anchor="w")
        lbl.pack(fill="x")
        self.entry = tk.Entry(self, textvariable=self.var, width=width,
                              background=BG_INPUT, foreground=FG,
                              insertbackground=FG, relief="flat",
                              font=(FONT_NUM, FS_NUM + 1),
                              highlightthickness=1,
                              highlightbackground=BORDER, highlightcolor=ACCENT)
        self.entry.pack(fill="x", pady=(2, PAD_S), ipady=3)

    @property
    def value(self) -> str:
        return self.var.get()

    def set(self, text: str) -> None:
        self.var.set(text)


class ResultBox(tk.Frame):
    """结果展示：上方指标格 + 下方计算过程。"""

    KEY_LABELS = ("单次伤害", "DPS", "DPH（每次攻击总伤害）", "DPH")

    def __init__(self, master, **kw):
        super().__init__(master, background=CARD, **kw)

        self.grid_frame = tk.Frame(self, background=CARD)
        self.grid_frame.pack(fill="x")

        bottom = self._bottom = tk.Frame(self, background=CARD)
        bottom.pack(fill="x", pady=(PAD_M, 0))
        head = tk.Frame(bottom, background=CARD)
        head.pack(fill="x", pady=(0, 3))
        tk.Frame(head, background=DIVIDER, height=1).pack(side="left", fill="x",
                                                         expand=True, pady=(6, 0))
        tk.Label(head, text="  计算过程  ", background=CARD, foreground=FG_DIM,
                 font=(FONT_UI, FS_SMALL)).pack(side="left")
        tk.Frame(head, background=DIVIDER, height=1).pack(side="left", fill="x",
                                                         expand=True, pady=(6, 0))
        self.steps = tk.Text(bottom, height=2, background=BG_SUNKEN,
                             foreground="#b8c4d4", relief="flat",
                             font=(FONT_NUM, FS_NUM), wrap="word",
                             insertbackground=FG, highlightthickness=1,
                             highlightbackground=DIVIDER, padx=10, pady=8,
                             spacing1=1, spacing3=1)
        self.steps.pack(fill="x")
        self.steps.pack_propagate(False)

    def set_rows(self, rows: Sequence[Tuple[str, str]]) -> None:
        """标签/值两列（备用；面板自己做网格时不会用到）。"""
        for w in self.grid_frame.winfo_children():
            w.destroy()
        for r, (label, value) in enumerate(rows):
            tk.Label(self.grid_frame, text=label, background=CARD,
                     foreground=FG_DIM, font=(FONT_UI, FS_BODY),
                     anchor="w").grid(row=r, column=0, sticky="w", padx=(0, 12))
            tk.Label(self.grid_frame, text=value, background=CARD,
                     foreground=ACCENT if label in self.KEY_LABELS else FG,
                     font=(FONT_NUM, FS_NUM, "bold"), anchor="w").grid(
                row=r, column=1, sticky="w")

    def set_steps(self, steps: Sequence[str]) -> None:
        self.steps.delete("1.0", "end")
        for i, s in enumerate(steps, 1):
            self.steps.insert("end", "%d. %s\n" % (i, s))

    def set_steps_visible(self, visible: bool, height: int = 3) -> None:
        """对比模式下收起「计算过程」，把高度让给曲线。"""
        if visible:
            if not self._bottom.winfo_ismapped():
                self._bottom.pack(fill="x", pady=(PAD_M, 0))
            self.steps.configure(height=height)
        else:
            self._bottom.pack_forget()


class ScrollFrame(tk.Frame):
    """可滚动容器。

    滚轮事件为什么不能各滚各的
    --------------------------
    旧实现每建一个 ``ScrollFrame`` 就 ``bind_all("<MouseWheel>")`` 一次。
    ``bind_all`` 挂的是 **"all" 绑定标签**，对**整个解释器**生效，于是：

    * 主界面里只要开着图鉴弹窗，弹窗里的 ``ScrollFrame`` 和后台页面的
      ``ScrollFrame`` **同时**收到同一个滚轮事件，两边一起动；
    * 弹窗盖住主页面时，滚轮实际滚的是被盖住的那个列表，用户看到的是
      「图鉴滚不动」；
    * 同一页面上有几个 ``ScrollFrame`` 时也是一起动。

    现在改成**只有一个**全局处理器，收到事件后先用
    ``winfo_containing`` 找出「鼠标指针底下真正是哪个控件」，再顺着
    parent 链找到它所属的 ``ScrollFrame``，只滚那一个。指针不在任何
    可滚动区域内就什么都不做——这样弹窗开着的时侯滚轮只作用于弹窗，
    关掉后才轮到主页面，完全符合「谁在最上层谁响应」的直觉。
    """

    #: canvas -> ScrollFrame，供全局滚轮处理器反查
    _BY_CANVAS: Dict[str, "ScrollFrame"] = {}
    #: 已经在哪些 root 上装过全局处理器
    _BOUND_ROOTS: set = set()

    def __init__(self, master, **kw):
        super().__init__(master, background=BG, **kw)
        self.canvas = tk.Canvas(self, background=BG, highlightthickness=0)
        self.vsb = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self.vsb.set)
        self.vsb.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)

        self.inner = tk.Frame(self.canvas, background=BG)
        self._win = self.canvas.create_window((0, 0), window=self.inner, anchor="nw")
        self.inner.bind("<Configure>", self._on_inner)
        self.canvas.bind("<Configure>", self._on_canvas)
        #: 高精度滚轮（触控板/部分鼠标）一次 delta 很小，累计到 120 再滚一格，
        #: 否则会出现「滚了半天没反应」或「一格跳三行」。
        self._wheel_acc = 0
        #: 待执行的 scrollregion 刷新（见 _schedule_region）
        self._region_after = None

        ScrollFrame._BY_CANVAS[str(self.canvas)] = self
        self._install_global()
        self.bind("<Destroy>", self._on_destroy, add="+")

    # ---------------------------------------------------------- 滚轮

    def _install_global(self) -> None:
        """在 root 上装全局滚轮处理器（每个 root 只装一次）。"""
        try:
            root = self.winfo_toplevel()
        except Exception:
            return
        key = str(root)
        if key in ScrollFrame._BOUND_ROOTS:
            return
        ScrollFrame._BOUND_ROOTS.add(key)
        try:
            root.bind_all("<MouseWheel>", ScrollFrame._wheel_dispatch, add="+")
        except Exception:
            ScrollFrame._BOUND_ROOTS.discard(key)

    @staticmethod
    def _wheel_dispatch(event):
        """全局滚轮入口：只滚鼠标指针底下那一个 ScrollFrame。"""
        sf = ScrollFrame._scroll_frame_at(event)
        if sf is None:
            return
        sf.scroll_wheel(event)
        # 返回 "break" 阻止继续冒泡到别的绑定，避免同一次滚动被执行两遍
        return "break"

    @staticmethod
    def _scroll_frame_at(event) -> Optional["ScrollFrame"]:
        """找鼠标指针所指控件所属的 ScrollFrame。

        先 ``winfo_containing`` 定位到指针下的控件，再沿 ``master`` 链
        上溯。找不到就返回 None（调用方据此不滚动任何东西）。
        """
        w = None
        try:
            w = event.widget.winfo_containing(event.x_root, event.y_root)
        except Exception:
            w = None
        if w is None:
            w = event.widget
        # 沿 parent 链上溯，最多 20 层（UI 层级不会更深，防死循环）
        for _ in range(20):
            if w is None:
                break
            sf = ScrollFrame._BY_CANVAS.get(str(w))
            if sf is not None:
                return sf
            try:
                w = w.master
            except Exception:
                w = None
        return None

    def scroll_wheel(self, event) -> None:
        """按事件滚动本容器。

        方向：滚轮向下滑 → 页面向下（看到下方内容），与 Windows 标准一致。
        """
        try:
            if not self.canvas.winfo_ismapped():
                return
        except tk.TclError:
            return
        d = int(getattr(event, "delta", 0) or 0)
        if d == 0:
            # X11 风格（Button-4/5）
            num = int(getattr(event, "num", 0) or 0)
            step = 1 if num == 5 else (-1 if num == 4 else 0)
        else:
            # Windows: delta>0 = 向上滚, delta<0 = 向下滚
            # 向下滚要看到下方内容 → yview_scroll(+1)
            self._wheel_acc += d
            step = 0
            while self._wheel_acc >= 120:
                self._wheel_acc -= 120
                step -= 1
            while self._wheel_acc <= -120:
                self._wheel_acc += 120
                step += 1
        if not step:
            return
        try:
            self.canvas.yview_scroll(step, "units")
        except tk.TclError:
            pass

    # 兼容旧调用点（曾经直接 bind 到 _on_wheel）
    def _on_wheel(self, event) -> None:
        self.scroll_wheel(event)

    def _on_destroy(self, event=None) -> None:
        """销毁时把自己的登记撤掉，别让静态表留下野指针。"""
        if event is not None and getattr(event, "widget", None) is not self:
            return
        if getattr(self, "_region_after", None) is not None:
            try:
                self.after_cancel(self._region_after)
            except Exception:
                pass
            self._region_after = None
        if getattr(self, "canvas", None) is not None:
            ScrollFrame._BY_CANVAS.pop(str(self.canvas), None)

    def _on_inner(self, event) -> None:
        """内容尺寸变化 -> 更新可滚动区域（合并到一次 idle 里做）。

        为什么不能直接 ``configure(scrollregion=...)``：
        切换详情条目时 inner 会先「清空变矮」再「填满变高」，中间连发
        好几次 ``<Configure>``，每次都重设 scrollregion 的话，滚动条
        拇指（thumb）会先被拉长、再被压短，用户按住拖动时看到的就是
        滚动条乱跳 + 内容错位 —— 也就是「数据黏成一团」。

        改成先把请求攒起来，等一轮 idle 结束、布局稳定下来再量一次
        ``bbox("all")``，全程只 configure 一次，拇指尺寸不会中间态抖动。
        """
        self._schedule_region()

    def _schedule_region(self) -> None:
        """把 scrollregion 的刷新合并到本轮 idle（多次调用只生效一次）。"""
        if getattr(self, "_region_after", None) is not None:
            return
        try:
            self._region_after = self.after_idle(self._update_region)
        except tk.TclError:
            self._region_after = None

    def _update_region(self) -> None:
        self._region_after = None
        try:
            bb = self.canvas.bbox("all")
        except tk.TclError:
            return
        if bb is None:
            return
        try:
            self.canvas.configure(scrollregion=bb)
        except tk.TclError:
            return
        # 内容比一屏矮时，把视口拉回顶部，否则滚动条会停在一个
        # 内容已经被销毁的位置（表现为「滚到底了但一片空白」）。
        try:
            h = self.canvas.winfo_height()
            if h > 1 and (bb[3] - bb[1]) <= h:
                self.canvas.yview_moveto(0.0)
        except tk.TclError:
            pass

    def refresh(self) -> None:
        """内容重建后主动调一次，让可滚动区域立刻跟上（不等用户操作）。"""
        self._schedule_region()

    def _on_canvas(self, event) -> None:
        try:
            self.canvas.itemconfigure(self._win, width=event.width)
        except tk.TclError:
            return
        # 宽度变了，文字换行位置跟着变，内容高度也会变 —— 必须重新量
        self._schedule_region()

    def reset_scroll(self) -> None:
        """滚回顶部（切换详情条目后调用，避免停留在上一屏）。"""
        try:
            self.canvas.yview_moveto(0.0)
        except tk.TclError:
            pass



class StatusBar(tk.Frame):
    """底部状态栏：左侧状态、右侧缓存信息，顶部一条细分隔线。"""

    def __init__(self, master, **kw):
        super().__init__(master, background=BG_DEEP, height=26, **kw)
        tk.Frame(self, background=DIVIDER, height=1).pack(fill="x", side="top")
        inner = tk.Frame(self, background=BG_DEEP)
        inner.pack(fill="x", expand=True)
        self.dot = tk.Label(inner, text="●", background=BG_DEEP, foreground=OK,
                            font=(FONT_UI, 6), padx=0)
        self.dot.pack(side="left", padx=(12, 4))
        self.label = tk.Label(inner, text="就绪", background=BG_DEEP,
                              foreground=FG_DIM, anchor="w",
                              font=(FONT_UI, FS_SMALL))
        self.label.pack(side="left", fill="x", expand=True)
        self.right = tk.Label(inner, text="", background=BG_DEEP,
                              foreground=FG_DIM, anchor="e",
                              font=(FONT_UI, FS_SMALL), padx=12)
        self.right.pack(side="right")

    def set(self, text: str) -> None:
        self.label.config(text=text)
        # 不再每次都 update_idletasks：状态栏文字很短，等 Tk 自然重绘即可，
        # 启动时状态栏被频繁调用，每次都强制同步布局会拖慢启动约 0.2s。

    def set_right(self, text: str) -> None:
        self.right.config(text=text)


class AppBar(tk.Frame):
    """顶部品牌栏：左侧品牌名 + 副标题，右侧动作按钮区。"""

    def __init__(self, master, brand: str, subtitle: str = "", **kw):
        super().__init__(master, background=BG_DEEP, **kw)
        inner = tk.Frame(self, background=BG_DEEP)
        inner.pack(fill="x", padx=PAD_L, pady=(PAD_S, PAD_S))

        mark = tk.Frame(inner, background=ACCENT, width=4, height=30)
        mark.pack(side="left", padx=(0, PAD_M))
        mark.pack_propagate(False)

        titles = tk.Frame(inner, background=BG_DEEP)
        titles.pack(side="left")
        tk.Label(titles, text=brand, background=BG_DEEP, foreground=FG,
                 font=(FONT_UI, FS_TITLE, "bold"), anchor="w").pack(
            side="top", anchor="w")
        self.subtitle = tk.Label(titles, text=subtitle, background=BG_DEEP,
                                 foreground=FG_DIM,
                                 font=(FONT_UI, FS_SMALL), anchor="w")
        self.subtitle.pack(side="top", anchor="w")

        self.actions = tk.Frame(inner, background=BG_DEEP)
        self.actions.pack(side="right")
        tk.Frame(self, background=DIVIDER, height=1).pack(fill="x", side="bottom")

# ---------------------------------------------------------------- 窗口外观

# 标题栏左端那个小图标（本程序里是青蛙图）被点/右键时会弹 Windows 系
# 统菜单（还原/移动/大小/最小化/关闭）。那个菜单和本程序的界面风格完全
# 不搭，用户反馈「点青蛙头不该出选项」，所以这里直接把图标区域上的
# 左键和右键吞掉，只保留正常拖动与右上角按钮。
WM_NCLBUTTONDOWN = 0x00A1
WM_NCLBUTTONDBLCLK = 0x00A3
WM_NCRBUTTONDOWN = 0x00A4
WM_NCRBUTTONUP = 0x00A5
HTSYSMENU = 3

_WNDPROC_REF = []          # 必须留住回调对象，否则会被 GC 掉导致崩溃


def suppress_titlebar_menu(window) -> bool:
    """让标题栏图标（青蛙头）不再弹出系统菜单。

    做法是把自己的窗口过程挂到顶层窗口的 frame 上：命中 HTSYSMENU 的
    鼠标消息直接返回 0，其余消息原样转给原来的窗口过程。失败也只是
    保持系统默认行为，不影响其它功能。
    """
    try:
        window.update_idletasks()
        hwnd = int(window.wm_frame(), 16)
    except Exception:
        return False
    try:
        user32 = ctypes.windll.user32
    except Exception:
        return False

    # 64 位下必须用 SetWindowLongPtr，32 位只有 SetWindowLong
    is64 = ctypes.sizeof(ctypes.c_void_p) == 8
    if is64:
        WNDPROC = ctypes.WINFUNCTYPE(ctypes.c_ssize_t, ctypes.c_void_p,
                                     ctypes.c_uint, ctypes.c_size_t,
                                     ctypes.c_ssize_t)
        set_ptr = user32.SetWindowLongPtrW
        set_ptr.restype = ctypes.c_ssize_t
        set_ptr.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_void_p]
    else:
        WNDPROC = ctypes.WINFUNCTYPE(ctypes.c_long, ctypes.c_void_p,
                                     ctypes.c_uint, ctypes.c_size_t,
                                     ctypes.c_long)
        set_ptr = user32.SetWindowLongW
        set_ptr.restype = ctypes.c_long
        set_ptr.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_void_p]

    call_prev = user32.CallWindowProcW
    call_prev.restype = ctypes.c_ssize_t
    call_prev.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_uint,
                          ctypes.c_size_t, ctypes.c_ssize_t]

    try:
        old = set_ptr(hwnd, -4, None)     # GWLP_WNDPROC
    except Exception:
        return False
    if not old:
        return False

    def wndproc(h, msg, wparam, lparam):
        if msg in (WM_NCLBUTTONDOWN, WM_NCLBUTTONDBLCLK,
                   WM_NCRBUTTONDOWN, WM_NCRBUTTONUP) and wparam == HTSYSMENU:
            return 0                       # 吞掉：不弹菜单，也不做任何事
        return call_prev(old, h, msg, wparam, lparam)

    proc = WNDPROC(wndproc)
    try:
        set_ptr(hwnd, -4, ctypes.cast(proc, ctypes.c_void_p))
    except Exception:
        return False
    _WNDPROC_REF.append((proc, old))
    return True


def enable_dark_titlebar(window, bg_ref: str = BG_DEEP) -> bool:
    """把 Windows 原生标题栏刷成深色，并让边框颜色跟随应用底色。

    tkinter 自己画不了标题栏，默认是系统亮色，放在深色界面上非常刺眼。
    这里用 DWM 的 DWMWA_USE_IMMERSIVE_DARK_MODE（Win10 1809+ 是 19，
    更早是 20），再用 DWMWA_CAPTION_COLOR / BORDER_COLOR 精确指定颜色。
    全部失败也只是保持系统默认，不影响功能。
    """
    ok = False
    try:
        window.update_idletasks()
        hwnd = int(window.wm_frame(), 16)
    except Exception:
        return False
    try:
        dwm = ctypes.windll.dwmapi
    except Exception:
        return False

    def set_attr(attr: int, value) -> None:
        nonlocal ok
        try:
            buf = ctypes.byref(ctypes.c_int(value))
            dwm.DwmSetWindowAttribute(hwnd, attr, buf, ctypes.sizeof(ctypes.c_int))
            ok = True
        except Exception:
            pass

    # 深色模式：19 是现行编号，20 兼容旧版
    set_attr(20, 1)
    set_attr(19, 1)

    # 精确配色（Win11 / build 22000+）；COLORREF 是 0x00BBGGRR
    def colorref(hex_color: str) -> int:
        h = hex_color.lstrip("#")
        r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
        return r | (g << 8) | (b << 16)

    for attr, col in ((35, bg_ref), (34, DIVIDER)):   # 35 标题栏, 34 边框
        set_attr(attr, colorref(col))

    # 标题栏文字用亮色
    set_attr(36, colorref(FG))
    return ok


def style_dialog(window) -> None:
    """统一的二级弹窗外观：深色原生标题栏 + 吞掉系统菜单。

    主窗口在 app._polish_titlebar 里单独做过这两件事，但所有
    ``tk.Toplevel`` 弹窗（设置、查看原代码、图鉴…）当初都漏了，
    于是标题栏是系统亮白色，夹在深色界面里非常突兀。
    这里抽成一个函数，新弹窗构造完直接调一次即可。
    """
    try:
        window.update_idletasks()
    except Exception:
        return
    try:
        enable_dark_titlebar(window)
    except Exception:
        pass
    try:
        suppress_titlebar_menu(window)
    except Exception:
        pass
    # 弹窗自己的背景也统一一下，避免 DWM 失败时露出一块白底
    try:
        window.configure(background=BG)
    except Exception:
        pass