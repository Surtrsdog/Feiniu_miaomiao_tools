"""PyInstaller 打包入口（最终版）。

无控制台窗口；启动异常会弹窗并写入 exe 同目录的 akcalc_error.log。
"""
import os
import sys
import traceback


def _log_path() -> str:
    base = os.path.dirname(os.path.abspath(sys.executable)) \
        if getattr(sys, "frozen", False) else os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, "akcalc_error.log")


def _log(msg: str) -> None:
    try:
        with open(_log_path(), "a", encoding="utf-8") as f:
            f.write(msg + "\n")
    except OSError:
        pass


def main() -> None:
    from akcalc.ui.app import main as app_main
    app_main()


if __name__ == "__main__":
    try:
        main()
    except Exception:
        tb = traceback.format_exc()
        _log("启动异常：\n" + tb)
        try:
            import tkinter as tk
            from tkinter import messagebox
            r = tk.Tk()
            r.withdraw()
            messagebox.showerror(
                "启动失败",
                "程序启动时出错，详细信息已写入：\n\n"
                f"{_log_path()}\n\n{tb[-1200:]}")
            r.destroy()
        except Exception:
            pass
        sys.exit(1)