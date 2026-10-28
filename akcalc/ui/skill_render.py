# -*- coding: utf-8 -*-
"""技能卡片的共享渲染（弹窗与数据索引共用）。

## 为什么要单独一个模块

「技能」这块内容原来在两个地方各画一套：``ui/monster_codex.py`` 的图鉴
弹窗、``ui/data_index.py`` 的怪物详情。两边的排版、圆点、代码注解读法
都不一样，改一处忘一处就出现「同一条数据两个口径」——用户看到的技能
描述取决于他点的是哪个入口，这在查 bug 的场景里是致命的。

所以文本模型放 ``core/enemy_skills.py``（不 import tk，可单独测），
Tk 渲染放这里（只画，不做任何数据判断）。两个 UI 都调
:func:`render_skills`，排版天然一致。

## 为什么不用 ttk

整个项目统一用 tk 原生控件 + 手工配色（见 ``ui/widgets.py`` 的常量
说明）。这里沿用同一套常量，深浅两档底色和卡片边框都对齐，混进 ttk
会出现边框宽度和焦点框不一致的突兀感。
"""
from __future__ import annotations

import tkinter as tk
from typing import List, Optional

from ..core import enemy_skills as ES
from .widgets import (ACCENT, ACCENT_TXT, BG_PANEL, BORDER, DIVIDER, FG,
                      FG_DIM, FONT_NUM, FONT_UI, FS_BODY, FS_MICRO, FS_SMALL,
                      PAD_M, PAD_S, PAD_XS, WARN)

#: 描述正文的换行宽度。卡片左右各留 PAD_M，弹窗宽 620 → 正文约 470；
#: 数据索引右侧栏更宽，调用方自己传更大的值。
WRAP_DEFAULT = 470


def render_skills(master, blocks, env: Optional[dict] = None, *,
                  wrap: int = WRAP_DEFAULT, max_bb: int = 6,
                  show_source: bool = True) -> None:
    """把 ``ES.build_blocks()`` 的结果画成一个技能列表。

    每条块三行：

    1. 技能名（粗体强调色）+ 名字右边的「初始 / 消耗」圆点 + 来源标记；
    2. 效果原文，一行一条（PRTS 的 ``effect`` 本来就是分行的）；
    3. 若有解包代码，挂一行 ``↳ prefabKey`` 与其 blackboard 的中文释义。

    来源标记是必须的：PRTS 与敌人档案的措辞**不完全一样**（PRTS 更接近
    游戏内原文，档案有时是精简版）。不标来源，用户跨条目对比时会以为
    差异是 bug。
    """
    env = env or {}
    for block in blocks or []:
        box = tk.Frame(master, background=BG_PANEL)
        box.pack(fill="x", padx=PAD_M, pady=(PAD_S, 0))

        row = tk.Frame(box, background=BG_PANEL)
        row.pack(fill="x")
        tk.Label(row, text=str(block.get("name") or "（未命名）"),
                 background=BG_PANEL, foreground=ACCENT,
                 font=(FONT_UI, FS_BODY, "bold"), anchor="w").pack(side="left")
        _dots(row, block)
        if show_source:
            _source_tag(row, block)
        if block.get("silence"):
            tk.Label(row, text="可沉默", background=BG_PANEL, foreground=WARN,
                     font=(FONT_UI, FS_MICRO)).pack(side="right",
                                                    padx=(PAD_XS, 0))

        lines = list(block.get("lines") or [])
        if not lines and block.get("source") == "code":
            lines = ["（PRTS 与敌人档案都没有这个技能的描述，"
                     "只有解包里的 prefabKey 和参数表）"]
        for txt in lines:
            tk.Label(box, text=txt, background=BG_PANEL, foreground=FG,
                     font=(FONT_UI, FS_SMALL), anchor="w", justify="left",
                     wraplength=wrap).pack(fill="x", pady=(1, 0))

        # 档案补充：PRTS 已给原文、档案里还有额外句子的情况。刻意压成小字
        # 并标出来源——两份文案措辞不同（PRTS 更接近游戏内原文），不标
        # 来源的并排会被当成重复或矛盾。
        extra = [t for t in (block.get("extra") or []) if t]
        if extra:
            tk.Label(box, text="档案补充", background=BG_PANEL,
                     foreground=FG_DIM, font=(FONT_UI, FS_MICRO),
                     anchor="w").pack(fill="x", pady=(1, 0))
            for txt in extra:
                tk.Label(box, text=txt, background=BG_PANEL, foreground=FG_DIM,
                         font=(FONT_UI, FS_MICRO), anchor="w", justify="left",
                         wraplength=wrap).pack(fill="x")

        code = block.get("code")
        if code:
            annot = ES.annotate_code(code, block.get("rec"), env.get("tokens"),
                                     env.get("fields"), env.get("bb"))
            render_annot(box, annot, sure=bool(block.get("sure")),
                         max_bb=max_bb, wrap=wrap)


def _source_tag(master, block: dict) -> None:
    """来源标记：PRTS / 敌人档案 / 仅解包。

    ``source="code"`` 的块没有描述，标记写「仅解包」比写「解包」更清楚
    地表达了「这里没有文案」。
    """
    src = block.get("source")
    if src == "prts":
        txt, tip = "PRTS", "效果原文来自 PRTS 敌人页"
    elif src == "handbook":
        txt, tip = "敌人档案", "PRTS 未收录该技能，退回游戏内敌人档案文案"
    else:
        txt, tip = "仅解包", "PRTS 与敌人档案都没有该技能的描述"
    lbl = tk.Label(master, text=" %s" % txt, background=BG_PANEL,
                   foreground=FG_DIM, font=(FONT_UI, FS_MICRO))
    lbl.pack(side="left", padx=(PAD_S, 0))
    if src != "prts":
        # 非 PRTS 来源要显式说明，否则用户会拿它和 PRTS 页面逐字对比
        lbl.configure(foreground=WARN)


def _dots(master, block: dict) -> None:
    """技能名后面的节奏圆点：「初始 / 消耗」。

    0 也画（``●``）；只有 ``None``（这一列真没有）才跳过。旧实现遇到
    ``<= 0`` 就 continue，于是 PRTS 里 537 条「初始 0 秒（进图即可用）」
    和 153 条「消耗 0（不按技力循环）」全都没有圆点，看起来像数据缺失。
    """
    for sec, cn, solid in ES.dots(block):
        mark = "●" if solid else "○"
        tk.Label(master, text=" %s%s %s" % (mark, ES.fmt_num(sec), cn),
                 background=BG_PANEL,
                 foreground=FG_DIM if solid else FG_DIM,
                 font=(FONT_NUM, FS_MICRO)).pack(side="left",
                                                 padx=(PAD_XS, 0))


def render_annot(master, annot: dict, *, sure: bool = True,
                 max_bb: int = 6, wrap: int = WRAP_DEFAULT,
                 show_count: bool = True) -> None:
    """渲染结构注解（``↳ prefabKey`` + blackboard 释义）。

    ``↳`` 表示配对有数值锚点，``≈`` 表示只有语义推测。这个区别不能省：
    用户会照着参数算伤害，猜的东西必须自己先承认是猜的。

    查不到释义的 key **照原样列出**并标「暂无释义」+ 全库出现次数——
    删掉它才是真的在骗人：用户正是靠「哪个 key 没释义」判断解包版本
    有没有新增参数。
    """
    if not annot:
        return
    row = tk.Frame(master, background=BG_PANEL)
    row.pack(fill="x", pady=(1, 0))
    mark = "↳" if sure else "≈"
    tk.Label(row, text="%s %s" % (mark, annot.get("prefab") or ""),
             background=BG_PANEL, foreground=ACCENT_TXT,
             font=(FONT_NUM, FS_MICRO), anchor="w").pack(side="left")
    if not sure:
        tk.Label(row, text="　推测", background=BG_PANEL, foreground=WARN,
                 font=(FONT_UI, FS_MICRO)).pack(side="left")
    if annot.get("undocumented"):
        tk.Label(row, text="　%d 项参数暂无中文释义" % annot["undocumented"],
                 background=BG_PANEL, foreground=FG_DIM,
                 font=(FONT_UI, FS_MICRO)).pack(side="left")

    bb = annot.get("bb") or []
    limit = max_bb if max_bb and max_bb > 0 else len(bb)
    for item in bb[:limit]:
        if item.get("documented"):
            txt = "%s = %s　→ %s" % (item["key"], item["value"],
                                     item.get("desc") or "")
            color = FG_DIM
        else:
            cnt = item.get("count") or 0
            tail = ("　全库 %d 次" % cnt) if (cnt and show_count) else ""
            txt = "%s = %s　→ 暂无释义%s" % (item["key"], item["value"], tail)
            color = WARN
        tk.Label(master, text="　" + txt, background=BG_PANEL, foreground=color,
                 font=(FONT_NUM, FS_MICRO), anchor="w", justify="left",
                 wraplength=wrap).pack(fill="x")
    if limit < len(bb):
        tk.Label(master, text="　…另有 %d 项（「查看原代码」里可看全）"
                 % (len(bb) - limit), background=BG_PANEL, foreground=FG_DIM,
                 font=(FONT_UI, FS_MICRO), anchor="w").pack(fill="x")
    for note in annot.get("notes") or []:
        tk.Label(master, text="　※ " + note, background=BG_PANEL,
                 foreground=FG_DIM, font=(FONT_UI, FS_MICRO), anchor="w",
                 justify="left", wraplength=wrap).pack(fill="x")


def collapsible(master, title: str, lines: List[str], *,
                wrap: int = WRAP_DEFAULT, open_by_default: bool = False,
                mono: bool = True, note: str = "") -> Optional[tk.Frame]:
    """可折叠区块（收起/展开），返回内容容器。

    项目里没有现成的折叠控件（``widgets.py`` 只提到过「收起计算过程」的
    做法），这里用最朴素也最稳的方式：内容 Frame 已经创建好，靠
    ``pack_forget`` / ``pack`` 切换显隐。**不销毁控件**——重建会让
    ``ScrollFrame`` 的可滚区域反复抖动（见 ``widgets.py`` 里 scrollregion
    那段注释），收起时重新量一次高度就够了。

    默认收起：「解包数值」是给想深挖的人看的，默认展开会把屏幕占满，
    反而把上面的技能描述挤到看不见。
    """
    holder = tk.Frame(master, background=BG_PANEL)
    holder.pack(fill="x", padx=PAD_M, pady=(PAD_S, 0))
    head = tk.Frame(holder, background=BG_PANEL)
    head.pack(fill="x")

    body = tk.Frame(holder, background=BG_PANEL)
    for ln in lines or []:
        tk.Label(body, text=ln, background=BG_PANEL, foreground=FG_DIM,
                 font=((FONT_NUM if mono else FONT_UI), FS_MICRO),
                 anchor="w", justify="left", wraplength=wrap).pack(fill="x")
    if note:
        tk.Label(body, text=note, background=BG_PANEL, foreground=FG_DIM,
                 font=(FONT_UI, FS_MICRO), anchor="w", justify="left",
                 wraplength=wrap).pack(fill="x", pady=(PAD_XS, 0))

    state = {"open": bool(open_by_default)}

    def _toggle() -> None:
        state["open"] = not state["open"]
        if state["open"]:
            body.pack(fill="x", pady=(PAD_XS, 0))
            btn.configure(text="▾ %s" % title)
        else:
            body.pack_forget()
            btn.configure(text="▸ %s" % title)
        # 折叠改变高度，必须让外层 ScrollFrame 重新量一次，
        # 否则滚动条拇指会停在旧位置（表现为「滚不到底」）。
        try:
            top = master.winfo_toplevel()
            for child in _walk(master):
                refresh = getattr(child, "refresh", None)
                if callable(refresh):
                    refresh()
        except Exception:                                   # noqa: BLE001
            pass

    btn = tk.Button(head, text=("▾ %s" if state["open"] else "▸ %s") % title,
                    relief="flat", background=BG_PANEL, foreground=FG_DIM,
                    activebackground=BG_PANEL, activeforeground=ACCENT,
                    font=(FONT_UI, FS_MICRO), highlightthickness=0,
                    bd=0, cursor="hand2", anchor="w", padx=0, pady=0,
                    command=_toggle)
    btn.pack(side="left")
    if state["open"]:
        body.pack(fill="x", pady=(PAD_XS, 0))
    return body


def _walk(widget):
    """遍历控件树（找 ``ScrollFrame`` 用；深度很浅，不做递归保护）。"""
    try:
        for child in widget.winfo_children():
            yield child
            for sub in _walk(child):
                yield sub
    except Exception:                                       # noqa: BLE001
        return


def unpack_lines(codes) -> List[str]:
    """「解包数值」折叠区的文本：per-skill 的英文键原值摘要。

    这是 ``core/enemy_codex.codex_entry`` 那份 ``prefabKey / cooldown /
    initCooldown / spCost`` 摘要的延续。刻意做成英文键 + 中文括注：排查
    bug 时要能把屏幕上的字逐字对应到解包字段，写成纯中文反而对不上。

    放在这里而不是各自 UI 里，是因为两个入口都要有这一块——内容一旦
    分家，就又回到「同一只怪两个说法」的老问题上。
    """
    from ..core import enemy_codex as EC
    out: List[str] = []
    for code in codes or []:
        key = str(code.get("key") or "")
        if not key:
            continue
        bits = ["prefabKey %s" % key]
        for field, cn in (("cooldown", "cooldown（消耗）"),
                          ("init", "initCooldown（初始）"),
                          ("sp_cost", "spCost（技力）")):
            val = code.get(field)
            if val is None:
                continue
            try:
                bits.append("%s = %s" % (cn, EC._fmt(float(val))))
            except (TypeError, ValueError):
                bits.append("%s = %s" % (cn, val))
        out.append("\u3000".join(bits))
        for k, v, vs in (code.get("blackboard") or []):
            shown = vs if vs else (EC._fmt(float(v)) if v is not None else "—")
            out.append("    %s = %s" % (k, shown))
    return out


#: 「解包数值」折叠区的说明文案。两个入口必须一模一样，所以写成常量。
UNPACK_NOTE = ("上面是给人读的描述，这里是解包里的字段原值。对不上时以 "
               "PRTS 为准：`initCooldown` 对应「初始」，`cooldown` 对应"
               "「消耗」，`spCost` 只是技力消耗的旧字段，多数敌人技能恒为 0。")


def divider(master) -> None:
    """卡片内容结束的细线 + 一点留白（各卡片自己收尾用）。"""
    tk.Frame(master, background=DIVIDER, height=1).pack(
        fill="x", padx=PAD_M, pady=(PAD_S, 0))
    tk.Frame(master, background=BG_PANEL, height=2).pack(fill="x")


__all__ = ["render_skills", "render_annot", "collapsible", "divider",
           "unpack_lines", "UNPACK_NOTE", "WRAP_DEFAULT"]