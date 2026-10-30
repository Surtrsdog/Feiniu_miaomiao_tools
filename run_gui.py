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
    # --mcp：MCP 服务端模式（stdio 传输），供外接 AI 读取数据。
    # 必须放在 `from akcalc.ui.app import ...` 之前——那个 import 会把
    # tkinter 和整套 UI 面板全拉起来，而 MCP 是纯数据服务，既不需要
    # GUI，也不该在无桌面会话 / 无控制台时依赖它。
    if "--mcp" in sys.argv:
        try:
            from akcalc.mcp.server import main as mcp_main
            raise SystemExit(mcp_main([a for a in sys.argv[1:] if a != "--mcp"]))
        except SystemExit:
            raise
        except Exception:
            import traceback
            tb = traceback.format_exc()
            _log("MCP 启动异常：\n" + tb)
            try:
                sys.stderr.write("[mcp] 致命错误：\n" + tb)
                sys.stderr.flush()
            except Exception:
                pass
            sys.exit(1)

    from akcalc.ui.app import main as app_main
    try:
        with open(_diag, "a", encoding="utf-8") as f:
            f.write("about to call app_main()\n")
    except Exception:
        pass
    app_main()


if __name__ == "__main__":
    try:
        main()
    except Exception:
        tb = traceback.format_exc()
        _log("启动异常：\n" + tb)
        # --mcp 模式下绝不弹窗：那是 stdio 服务，弹窗只会让客户端超时，
        # 而且无桌面会话时 Tk() 自己就抛，错误反而彻底看不见。
        if "--mcp" in sys.argv:
            try:
                sys.stderr.write("[mcp] 致命错误：\n" + tb)
                sys.stderr.flush()
            except Exception:
                pass
            sys.exit(1)
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