"""程序入口。

用法：
    python run.py            # 开图形界面
    python run.py --mcp      # 以 MCP 服务端运行（stdio），给外接 AI 用
"""
import io
import os
import sys

# Windows 控制台默认 GBK，中文输出会报错；统一转 UTF-8。
# --mcp 模式下 stdout 是 JSON-RPC 通道，这里的包装正好保证协议是 UTF-8
# 而不是 GBK（否则客户端按 UTF-8 解会乱码）。
if sys.stdout and hasattr(sys.stdout, "buffer"):
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")
    except (ValueError, AttributeError):
        pass

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

if __name__ == "__main__":
    # --mcp 分支必须在 import app 之前：那个 import 会拉起 tkinter 和
    # 一整套 UI 面板，而 MCP 是纯数据服务，不需要也不该依赖 GUI。
    if "--mcp" in sys.argv:
        from akcalc.mcp.server import main as _mcp_main
        raise SystemExit(_mcp_main([a for a in sys.argv[1:] if a != "--mcp"]))

    from akcalc.ui.app import main
    main()