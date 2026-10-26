# -*- coding: utf-8 -*-
"""单实例守卫：同一个程序只允许开一个窗口。

实现用 Windows 命名互斥体（CreateMutexW）。互斥体是内核对象，进程
一退出就自动释放，不会留下「上次崩溃把锁占死了」的脏状态——这比写
一个 lock 文件靠谱得多。

第二次启动时：
  1. 找到已经在跑的那个窗口；
  2. 把它提到前台（最小化了就还原）；
  3. 自己直接退出，不再建第二个窗口。
"""

from __future__ import annotations

import ctypes
import os
from typing import Optional

ERROR_ALREADY_EXISTS = 183
_MUTEX_HANDLE = None          # 必须保住句柄，否则会被 GC 掉导致锁失效


def _mutex_name(key: str) -> str:
    """按程序标识拼一个全局互斥体名（Local\\ 前缀只在当前会话生效）。"""
    safe = "".join(c if c.isalnum() else "_" for c in key)[:80]
    return "Local\\FeiNiuMiaoMiao_%s" % safe


def acquire(key: str = "feiniu_miaomiao") -> bool:
    """尝试取得单实例锁。True 表示我是第一个，可以继续启动。"""
    global _MUTEX_HANDLE
    if os.name != "nt":
        return True                       # 非 Windows 不做限制
    try:
        k32 = ctypes.windll.kernel32
        k32.CreateMutexW.restype = ctypes.c_void_p
        k32.CreateMutexW.argtypes = [ctypes.c_void_p, ctypes.c_bool,
                                     ctypes.c_wchar_p]
        k32.GetLastError.restype = ctypes.c_uint
        handle = k32.CreateMutexW(None, False, _mutex_name(key))
        if not handle:
            return True                   # 拿不到锁就当第一个，别拦住用户
        err = k32.GetLastError()
        if err == ERROR_ALREADY_EXISTS:
            # 已经有人在跑：把那个窗口调到前台，然后调用方应当退出
            try:
                k32.CloseHandle(handle)
            except Exception:
                pass
            focus_existing(key)
            return False
        _MUTEX_HANDLE = handle
        return True
    except Exception:
        return True                       # 任何异常都放行，别让程序起不来


# ------------------------------------------------------------ 找已有窗口

def _window_title() -> str:
    """和 App.APP_TITLE 保持一致（这里不 import UI，避免循环依赖）。"""
    return "肥牛妙妙工具"


def focus_existing(key: str = "") -> bool:
    """把已经在运行的那个窗口提到前台并还原。找不到就返回 False。"""
    if os.name != "nt":
        return False
    try:
        user32 = ctypes.windll.user32
    except Exception:
        return False
    found = []

    @ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
    def _cb(hwnd, _lparam):
        try:
            n = user32.GetWindowTextLengthW(hwnd)
            if n <= 0:
                return True
            buf = ctypes.create_unicode_buffer(n + 1)
            user32.GetWindowTextW(hwnd, buf, n + 1)
            if buf.value.startswith(_window_title()):
                found.append(hwnd)
        except Exception:
            pass
        return True

    try:
        user32.EnumWindows(_cb, 0)
    except Exception:
        return False
    if not found:
        return False

    SW_RESTORE = 9
    for hwnd in found:
        try:
            if user32.IsIconic(hwnd):
                user32.ShowWindow(hwnd, SW_RESTORE)
            user32.SetForegroundWindow(hwnd)
            user32.BringWindowToTop(hwnd)
        except Exception:
            pass
    return True


def warn_already_running() -> None:
    """告诉用户「已经开了一个」，用系统消息框（此时还没有 tkinter 窗口）。"""
    try:
        ctypes.windll.user32.MessageBoxW(
            None,
            "肥牛妙妙工具已经在运行了。\n\n"
            "为了避免两份程序抢同一份缓存，这里不会再打开新窗口——"
            "已经把你的那个窗口调到前面了。",
            "肥牛妙妙工具",
            0x00000040 | 0x00001000,   # MB_ICONINFORMATION | MB_SYSTEMMODAL
        )
    except Exception:
        pass
