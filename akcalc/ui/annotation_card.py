# -*- coding: utf-8 -*-
"""图鉴批注编辑卡 + 导出 / 导入按钮。

为什么单独一个模块
------------------
批注要出现在三个地方：干员索引、怪物索引、怪物图鉴弹窗。三处的卡片
长得一样、行为也必须一样（防抖落盘、切条目自动保存、导入后立刻刷新）。
复制三份的必然结果是「弹窗里能保存、图鉴页保存不了」这类只在某条路径
上复现的差异，所以抽成一个 ``AnnotationCard``，三个入口只是建它。

为什么不给「保存」按钮当主交互
------------------------------
批注是随手写的备忘，用户不会记得点保存。主交互必须是「输入即保存」：
``<KeyRelease>`` 起 400ms 防抖（每敲一个字就写盘太浪费，而且写盘是
``os.replace``，连续几百次会让 cache 目录很难看），``<FocusOut>`` 和
切条目时强制落盘。仍然留 Ctrl+S 和「清空」，前者给不放心的用户一个
确定的手感，后者是唯一需要确认的破坏性操作。

关于「清空」的语义
-----------------
清空文本框 = 删掉这条批注（``store.set`` 收到空正文就会删记录）。这样
「有记录」和「有内容」永远等价，不会出现一堆空记录混在导出文件里。因为
不可撤销，所以先 askyesno 确认。
"""
from __future__ import annotations

import json
import os
import tkinter as tk
from tkinter import filedialog, messagebox

from ..core import annotations as ANNO
from .widgets import (ACCENT, ACCENT_TXT, BG_DEEP, BG_SUNKEN, BORDER, CARD,
                      DIVIDER, FG, FG_DIM, FONT_UI, FS_MICRO, FS_SMALL, PAD_S,
                      PAD_XS, WARN, Card)

#: 防抖落盘延迟（毫秒）。手速再慢也不会慢过这个值，正常打字过程中一次
#: 盘都不写，停手 0.4 秒才落一次。
SAVE_DELAY_MS = 400


def _small_button(master, text: str, command) -> tk.Button:
    """返回条 / 卡片角上那种小按钮，和 data_index 里的「查看原代码」一致。"""
    btn = tk.Button(master, text=text, relief="flat", background=BG_DEEP,
                    foreground=ACCENT_TXT, activebackground=CARD,
                    activeforeground=ACCENT, font=(FONT_UI, FS_MICRO),
                    highlightthickness=1, highlightbackground=BORDER,
                    cursor="hand2", padx=8, pady=0, bd=0, command=command)
    return btn


class AnnotationCard(Card):
    """「我的批注」卡片。

    ``kind`` 是 ``core.annotations.KINDS`` 里的种类，``key`` 是稳定的
    条目 id（敌人 enemy_id / 干员 char_id）。这里不做任何缓存，读写都走
    ``annotations.store_for(app)`` 那唯一一份内存表，所以三个入口看到的
    永远是同一份内容。
    """

    def __init__(self, master, app, kind: str, key: str, *, name: str = "",
                 on_saved=None, with_io: bool = False):
        super().__init__(master, title="我的批注")
        self.app = app
        self.kind = kind
        self.key = str(key or "")
        self.name = name or ""
        self._on_saved = on_saved
        self._timer = None
        self._dirty = False
        self.store = ANNO.store_for(app)

        self.text = tk.Text(
            self.body, height=4, wrap="word", background=BG_SUNKEN,
            foreground=FG, insertbackground=FG, relief="flat", bd=0,
            font=(FONT_UI, FS_SMALL), highlightthickness=1,
            highlightbackground=BORDER, highlightcolor=ACCENT,
            padx=PAD_S, pady=PAD_XS, spacing1=2, spacing3=2)
        self.text.pack(fill="x")

        foot = tk.Frame(self.body, background=CARD)
        foot.pack(fill="x", pady=(PAD_XS, 0))
        self.lbl_hint = tk.Label(foot, text="", background=CARD,
                                 foreground=FG_DIM, font=(FONT_UI, FS_MICRO),
                                 anchor="w")
        self.lbl_hint.pack(side="left")
        self.btn_clear = _small_button(foot, "清空", self._on_clear)
        self.btn_clear.pack(side="right")

        # 图鉴页把导出 / 导入放在顶部返回条上（那是整类操作）；但怪物图鉴
        # 弹窗没有返回条，卡片自己得带上入口，否则从路线分析点进来的用户
        # 找不到导出。放在标题条右侧插槽里，位置与 Card 其它按钮一致。
        self.btn_export = self.btn_import = None
        if with_io and self.head_right is not None:
            self.btn_import = _small_button(
                self.head_right, "导入",
                lambda: import_dialog(self, self.app, self.kind,
                                      self._on_imported))
            self.btn_import.pack(side="right")
            self.btn_export = _small_button(
                self.head_right, "导出",
                lambda: export_dialog(self, self.app, self.kind))
            self.btn_export.pack(side="right", padx=(0, PAD_XS))

        self.text.bind("<KeyRelease>", self._on_key)
        self.text.bind("<FocusOut>", self._on_focus_out)
        self.text.bind("<Control-s>", self._on_ctrl_s)
        self.text.bind("<Destroy>", self._on_destroy)
        self.text.bind("<Control-Return>", self._on_ctrl_s)
        # harmonize 不处理 Text（它是 BG_SUNKEN 的凹陷块，不能刷成卡片色），
        # 但仍然要把 body 里其余控件统一底色。
        self.harmonize()
        self.reload()

    # ------------------------------------------------------------ 读取

    def reload(self) -> None:
        """从内存表重新灌一遍正文（导入之后调用，让合并结果立刻可见）。"""
        txt = ""
        if self.key and self.kind:
            try:
                txt = self.store.get(self.kind, self.key)
            except Exception:
                txt = ""
        try:
            self.text.delete("1.0", "end")
            if txt:
                self.text.insert("1.0", txt)
        except Exception:
            return
        self._dirty = False
        self._set_hint()

    def _set_hint(self) -> None:
        """底部提示：这条到底存下来了没有。"""
        if not self.key:
            self.lbl_hint.config(text="这条数据没有稳定 id，批注无法保存。",
                                 foreground=WARN)
            return
        if self._dirty:
            self.lbl_hint.config(text="正在输入…（停手 0.4 秒后自动保存）",
                                 foreground=FG_DIM)
            return
        txt = ""
        try:
            txt = self.text.get("1.0", "end-1c")
        except Exception:
            pass
        n = len(txt.strip())
        if n:
            self.lbl_hint.config(text="已保存 · %d 字 · 仅存在本机" % n,
                                 foreground=FG_DIM)
        else:
            self.lbl_hint.config(
                text="写点备忘（机制坑点 / 打法），输入即自动保存",
                foreground=FG_DIM)

    # ------------------------------------------------------------ 写入

    def _cancel_timer(self) -> None:
        if self._timer is not None:
            try:
                self.after_cancel(self._timer)
            except Exception:
                pass
            self._timer = None

    def _on_key(self, event=None) -> None:
        self._dirty = True
        self._set_hint()
        self._cancel_timer()
        try:
            self._timer = self.after(SAVE_DELAY_MS, self.flush)
        except Exception:
            # 控件已经在销毁中：直接同步写掉，别把内容丢了
            self.flush()

    def _on_focus_out(self, event=None) -> None:
        self.flush()

    def _on_ctrl_s(self, event=None) -> str:
        self.flush()
        return "break"

    def _on_destroy(self, event=None) -> None:
        """控件被销毁（切条目 / 关窗口）前把没落盘的字写掉。"""
        if event is not None and getattr(event, "widget", None) is not self.text:
            return
        try:
            self.flush()
        except Exception:
            pass

    def flush(self) -> bool:
        """把文本框内容立刻写进库；返回内容有没有真的变化。

        不拿 ``_dirty`` 当门：用户敲键盘会置脏，但程序化 ``insert``（脚本、
        回填、测试）不会触发 ``<KeyRelease>``，靠脏标记就会出现「内容在框
        里、库里没有」。``store.set`` 自己带「值没变就什么都不做」的短路，
        所以每次都试着写反而更保险，代价只是一次字符串比较。
        """
        self._cancel_timer()
        if not self.key:
            self._dirty = False
            return False
        try:
            body = self.text.get("1.0", "end-1c")
        except Exception:
            # Text 已经销毁（窗口正在关），内容无从取出
            self._dirty = False
            return False
        try:
            changed = self.store.set(self.kind, self.key, body,
                                     name=self.name)
        except Exception:
            changed = False
        self._dirty = False
        self._set_hint()
        if changed and callable(self._on_saved):
            try:
                self._on_saved(self.key)
            except Exception:
                pass
        return changed

    def _on_imported(self) -> None:
        """导入合并完成后把当前这条重新读一遍（别的 key 也变了，但这条最要紧）。"""
        self.reload()

    def _on_clear(self) -> None:
        if not self.key:
            return
        if not messagebox.askyesno(
                "清空批注", "确定清空这条批注吗？清空后无法恢复。",
                parent=self):
            return
        self._cancel_timer()
        try:
            self.text.delete("1.0", "end")
        except Exception:
            pass
        self._dirty = False
        try:
            self.store.remove(self.kind, self.key)
        except Exception:
            pass
        self._set_hint()


# ------------------------------------------------------------ 导出 / 导入

def _peek_kind(path: str) -> str:
    """读出文件头里声明的种类；读不出来就空串（不报错）。"""
    try:
        with open(path, "r", encoding="utf-8") as f:
            raw = json.load(f)
    except Exception:
        return ""
    if isinstance(raw, dict):
        k = raw.get("kind")
        if isinstance(k, str):
            return k
    return ""


def export_dialog(parent, app, kind: str) -> str:
    """弹保存框导出该类批注；返回实际写入的路径（取消 / 失败返回空串）。"""
    store = ANNO.store_for(app)
    cn = ANNO.kind_cn(kind)
    try:
        path = filedialog.asksaveasfilename(
            parent=parent, title="导出%s" % cn,
            initialfile=ANNO.default_file_name(kind),
            initialdir=os.path.expanduser("~"),
            defaultextension=".json",
            filetypes=[("JSON 文件", "*.json"), ("所有文件", "*.*")])
    except Exception as e:
        messagebox.showerror("导出失败", "打不开保存对话框：%s" % e,
                             parent=parent)
        return ""
    if not path:
        return ""
    try:
        n = store.export(kind, path)
    except ANNO.AnnotationError as e:
        messagebox.showerror("导出失败", str(e), parent=parent)
        return ""
    except Exception as e:
        # 兜底：导出再怎么样也不该把程序带崩
        messagebox.showerror("导出失败", "写入时出错：%s" % e, parent=parent)
        return ""
    messagebox.showinfo(
        "导出完成",
        "已导出 %d 条%s到：\n%s" % (n, cn, path), parent=parent)
    return path


def import_dialog(parent, app, kind: str, on_change=None) -> int:
    """弹打开框合并该类批注；返回合并进来的条数（取消 / 失败返回 0）。

    失败只弹 messagebox，绝不往上抛：用户选到一个坏文件是极常见的误操作
    （选错成 enemy_database.json 这种几十 MB 的不是 JSON 的文件），
    图鉴不该因此崩掉。
    """
    store = ANNO.store_for(app)
    cn = ANNO.kind_cn(kind)
    try:
        path = filedialog.askopenfilename(
            parent=parent, title="导入%s" % cn,
            initialdir=os.path.expanduser("~"),
            filetypes=[("JSON 文件", "*.json"), ("所有文件", "*.*")])
    except Exception as e:
        messagebox.showerror("导入失败", "打不开文件对话框：%s" % e,
                             parent=parent)
        return 0
    if not path:
        return 0
    other = _peek_kind(path)
    if other and other != kind:
        # 种类不符一律拦下。之前这里是「问一句，允许硬导」，但干员键
        # （char_xxx）和怪物键（enemy_xxx）在界面上长得一样，混进去以后
        # 怪物列表里会静静躺着几百条干员批注，用户根本发现不了。
        # 拒绝并直接说该导到哪一栏，比放行后让人自己找错要省事。
        messagebox.showerror(
            "种类不一致",
            "这份文件是「%s」，不能导进「%s」。\n"
            "它应当用「%s」那一栏的导入按钮。"
            % (ANNO.kind_cn(other), cn, ANNO.kind_cn(other)), parent=parent)
        return 0
    try:
        added, kept = store.import_(kind, path)
    except ANNO.AnnotationError as e:
        messagebox.showerror("导入失败", str(e), parent=parent)
        return 0
    except Exception as e:
        messagebox.showerror("导入失败", "读取时出错：%s" % e, parent=parent)
        return 0
    if added == 0 and kept == 0:
        messagebox.showinfo(
            "没有可导入的内容",
            "「%s」里没有一条可用的%s。\n（JSON 可能是空的，或结构不对）"
            % (os.path.basename(path), cn), parent=parent)
        return 0
    messagebox.showinfo(
        "导入完成",
        "合并 %d 条，保留本机较新的 %d 条。\n共 %d 条%s。"
        % (added, kept, store.count(kind), cn), parent=parent)
    if callable(on_change):
        try:
            on_change()
        except Exception:
            pass
    return added


def attach_buttons(master, app, kind: str, on_change=None):
    """在返回条右侧挂上「导出 / 导入」两个小按钮；返回按钮列表。"""
    if not kind:
        return []
    cn = ANNO.kind_cn(kind)
    b_import = _small_button(master, "导入%s" % cn,
                             lambda: import_dialog(master, app, kind, on_change))
    b_import.pack(side="right")
    b_export = _small_button(master, "导出%s" % cn,
                             lambda: export_dialog(master, app, kind))
    b_export.pack(side="right", padx=(0, PAD_XS))
    return [b_export, b_import]