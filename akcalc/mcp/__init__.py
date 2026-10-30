"""MCP 服务端：把本工具的数据暴露给外接 AI。

启动方式（stdio 传输，MCP 标准方式）::

    python -m akcalc.mcp --self-test    # 自检
    python -m akcalc.mcp                # 作为 MCP server 运行

打包后的 exe 用::

    肥牛妙妙工具.exe --mcp              # 由 MCP 客户端拉起
"""
from __future__ import annotations


def main(argv=None):
    from .server import main as _main
    return _main(argv)


__all__ = ["main"]
