# -*- coding: utf-8 -*-
"""MCP 客户端配置生成。

外接 AI（Claude Desktop / Cursor / Cline / Cherry Studio…）都要在 JSON
里填「用哪个命令拉起服务端」。这一步最容易劝退用户：路径要带引号、
Windows 反斜杠要转义、``--mcp`` 参数不能漏、打包版和源码版命令完全
不同。所以这里统一生成，设置界面直接给用户复制。

两个形态
--------
* **打包版**：命令就是 exe 自身路径 + ``--mcp``。exe 在哪里就填哪里，
  用户移动了安装位置就重新复制一次。
* **源码版**：``<python> -m akcalc.mcp``，并带上项目目录当 ``cwd``
  （否则 python 找不到 akcalc 包）。

设计取舍
--------
* 只生成、不写别人的配置文件。各家客户端配置路径不一样（Claude
  Desktop 在 ``%APPDATA%\\Claude\\claude_desktop_config.json``，Cursor
  在用户目录 ``.cursor\\mcp.json``，Cline 在 VS Code 扩展存储里），
  而且用户可能已经配了别的 server，我们**贸然合并会覆盖掉**。
  所以给「复制配置」按钮，让用户自己粘。
* 输出永远是标准 JSON（``ensure_ascii=False``），中文名不乱码。
"""
from __future__ import annotations

import json
import os
import sys
from typing import Dict, List, Optional


def _is_frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


def exe_path() -> str:
    """当前可执行文件路径。打包版是 exe 本身，源码版是 python。"""
    if _is_frozen():
        return os.path.abspath(sys.executable)
    return os.path.abspath(sys.executable)


def _project_root() -> str:
    """源码版的项目根目录（含 akcalc 包的上一层）。"""
    here = os.path.dirname(os.path.abspath(__file__))       # akcalc/mcp
    return os.path.dirname(os.path.dirname(here))           # 项目根


def command() -> List[str]:
    """拉起 MCP 服务端的完整命令（列表形式）。"""
    if _is_frozen():
        return [exe_path(), "--mcp"]
    return [exe_path(), "-m", "akcalc.mcp"]


def client_config(name: str = "feiniu-akcalc") -> Dict[str, object]:
    """生成 MCP 客户端配置片段（``mcpServers`` 结构）。"""
    entry: Dict[str, object] = {"command": command()[0]}
    args = command()[1:]
    if args:
        entry["args"] = args
    if not _is_frozen():
        # 源码版必须指定工作目录，否则 python -m akcalc.mcp 找不到包
        entry["cwd"] = _project_root()
    entry["env"] = {"PYTHONIOENCODING": "utf-8"}
    return {"mcpServers": {name: entry}}


def config_json(name: str = "feiniu-akcalc", indent: int = 2) -> str:
    return json.dumps(client_config(name), ensure_ascii=False, indent=indent)


def claude_desktop_path() -> str:
    """Claude Desktop 的配置文件位置（仅供参考，不自动写）。"""
    appdata = os.environ.get("APPDATA") or ""
    if not appdata:
        return ""
    return os.path.join(appdata, "Claude", "claude_desktop_config.json")


def quickstart() -> str:
    """给设置界面显示的一段说明（纯文本，不含 tkinter）。"""
    lines = []
    if _is_frozen():
        lines.append("把下面的配置粘进 MCP 客户端的配置文件，重启客户端即可。")
    else:
        lines.append("源码运行：把下面的配置粘进客户端，注意 cwd 要指向项目目录。")
    lines.append("")
    lines.append(config_json())
    p = claude_desktop_path()
    if p:
        lines.append("")
        lines.append("Claude Desktop 的配置文件：")
        lines.append(p)
    return "\n".join(lines)


def status() -> Dict[str, object]:
    """给设置界面显示的状态摘要。"""
    from . import server
    try:
        n_tools = len(server.tools())
    except Exception:                                       # noqa: BLE001
        n_tools = 0
    return {
        "frozen": _is_frozen(),
        "command": " ".join(command()),
        "tool_count": n_tools,
        "protocol": server.PROTOCOL_VERSION,
        "server_version": server.SERVER_VERSION,
    }
