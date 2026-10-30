"""MCP（Model Context Protocol）服务端。

让外接 AI（Claude Desktop / Cursor / Cline / 任何 MCP 客户端）能直接读取
本工具的干员、敌人、地图、路线四类数据，不必自己下载 89MB 解包。

## 为什么是 stdio 而不是 HTTP

MCP 的标准传输是「客户端拉起子进程，走 stdin/stdout 的 JSON-RPC」。
这样做好处是：零端口、零防火墙、进程随客户端退出而结束，用户不用
配 IP 和令牌。本模块只做协议层，一次读一行 JSON、写一行 JSON。

**致命细节**：stdout 是协议通道，任何 ``print()`` 都会污染 JSON-RPC
流，客户端会直接断连。所以本模块所有日志都走 stderr。

## 支持的方法

* ``initialize`` / ``notifications/initialized`` —— 握手
* ``tools/list`` —— 列出工具
* ``tools/call`` —— 调用工具
* ``ping`` —— 心跳（很多客户端会发）
* ``resources/list`` / ``prompts/list`` —— 返回空表，避免客户端报错

协议版本 ``2024-11-05``（Claude Desktop / Cline / Cursor 广泛支持）。

## 工具怎么注册

每个工具是一个 ``Tool``：名字、标题、描述、JSON Schema、执行函数。
执行函数签名统一 ``fn(args: dict) -> dict``，返回
``{"content": [{"type": "text", "text": ...}]}``。异常由 ``_call_tool``
兜住转成 ``isError``，坏参数不会打断整个会话。
"""
from __future__ import annotations

import io
import json
import sys
import traceback
from typing import Any, Callable, Dict, List, Optional

PROTOCOL_VERSION = "2024-11-05"
SERVER_NAME = "feiniu-akcalc"

# 版本号只认包里的 __version__，不要在这里再写死一份——
# 之前写死 "2.3.0"，exe 属性已经是 2.4.0.0，客户端看到的还是旧版本。
try:
    from .. import __version__ as _pkg_ver
    SERVER_VERSION = _pkg_ver
except Exception:                                           # noqa: BLE001
    SERVER_VERSION = "0.0"


def log(msg: str) -> None:
    """日志只能走 stderr——stdout 是 JSON-RPC 通道。"""
    try:
        sys.stderr.write("[mcp] %s\n" % msg)
        sys.stderr.flush()
    except Exception:
        pass


# ---------------------------------------------------------------- 工具表

class Tool:
    __slots__ = ("name", "title", "description", "schema", "fn")

    def __init__(self, name: str, title: str, description: str,
                 schema: Dict[str, Any], fn: Callable[[dict], dict]):
        self.name = name
        self.title = title
        self.description = description
        self.schema = schema
        self.fn = fn

    def to_mcp(self) -> dict:
        return {
            "name": self.name,
            "description": "%s\n\n%s" % (self.title, self.description),
            "inputSchema": self.schema,
        }


_REGISTRY: Dict[str, Tool] = {}

#: tool_* 模块是否已导入。**不要**拿 _REGISTRY 空不空来判断——
#: 别处单独 import 一个 tool 模块会让注册表非空，从而永远跳过后面的，
#: 工具列表静默缺一半（实测：19 个变 6 个）。
_loaded = False


def tool(name: str, title: str, description: str, schema: dict):
    """注册装饰器。"""
    def deco(fn):
        _REGISTRY[name] = Tool(name, title, description, schema, fn)
        return fn
    return deco


def tools() -> List[Tool]:
    # 延迟导入：把数据层 import 放在真正要调用时才做，
    # 这样 tools/list 在数据没下载完时也能秒回。
    global _loaded
    if not _loaded:
        _loaded = True          # 先置位，防循环 import 时无限递归
        from . import (tool_operators, tool_enemies, tool_maps,
                       tool_routes, tool_battle, tool_mechanics,
                       tool_stage, tool_range,
                       tool_battle_logic)  # noqa: F401
    return [_REGISTRY[k] for k in sorted(_REGISTRY)]


# ---------------------------------------------------------------- 结果包装

def ok(payload) -> dict:
    """成功结果：MCP 要求 content 是数组，text 里放序列化 JSON。"""
    text = payload if isinstance(payload, str) else json.dumps(
        payload, ensure_ascii=False, indent=2, default=str)
    return {"content": [{"type": "text", "text": text}]}


def error(msg: str) -> dict:
    return {"content": [{"type": "text", "text": msg}], "isError": True}


# ---------------------------------------------------------------- 分发

def _resolve(name: str) -> Optional[Tool]:
    if not _loaded:
        try:
            tools()
        except Exception as e:  # noqa: BLE001
            log("工具注册失败: %r" % e)
            traceback.print_exc(file=sys.stderr)
    return _REGISTRY.get(name)


def _call_tool(name: str, args: dict) -> dict:
    t = _resolve(name)
    if t is None:
        return error("没有这个工具：%s" % name)
    try:
        return t.fn(args or {})
    except Exception as e:  # noqa: BLE001
        log("工具 %s 抛错: %r" % (name, e))
        traceback.print_exc(file=sys.stderr)
        return error("工具执行失败：%s: %s" % (type(e).__name__, e))


def handle(req: dict) -> Optional[dict]:
    """处理一条 JSON-RPC 请求，返回响应（通知返回 None）。"""
    method = req.get("method") or ""
    rid = req.get("id")
    is_notification = "id" not in req

    def ok_resp(result):
        return {"jsonrpc": "2.0", "id": rid, "result": result}

    def err_resp(code, message):
        return {"jsonrpc": "2.0", "id": rid,
                "error": {"code": code, "message": message}}

    if method == "initialize":
        params = req.get("params") or {}
        client_ver = params.get("protocolVersion") or PROTOCOL_VERSION
        log("initialize: client=%r version=%r"
            % ((params.get("clientInfo") or {}).get("name"), client_ver))
        return ok_resp({
            "protocolVersion": PROTOCOL_VERSION,
            "capabilities": {"tools": {"listChanged": False}},
            "serverInfo": {"name": SERVER_NAME, "version": SERVER_VERSION},
            "instructions": (
                "肥牛妙妙工具的数据接口。可读取明日方舟的干员、敌人、"
                "地图、路线数据。敌人抬手（攻击前摇）来自解包 "
                "bakemuzzledata，其余来自 enemy_database / "
                "enemy_handbook_table / levels。所有时间为秒，坐标为"
                "「行, 列」，行 0 在最上方。"
            ),
        })

    if method in ("notifications/initialized", "initialized",
                  "notifications/cancelled"):
        return None

    if method == "ping":
        return ok_resp({})

    if method == "tools/list":
        try:
            return ok_resp({"tools": [t.to_mcp() for t in tools()]})
        except Exception as e:  # noqa: BLE001
            log("tools/list 失败: %r" % e)
            return err_resp(-32603, str(e))

    if method == "tools/call":
        params = req.get("params") or {}
        name = params.get("name") or ""
        args = params.get("arguments") or {}
        log("tools/call %s args=%r" % (name, args))
        return ok_resp(_call_tool(name, args))

    if method == "resources/list":
        return ok_resp({"resources": []})

    if method == "resources/templates/list":
        return ok_resp({"resourceTemplates": []})

    if method == "prompts/list":
        return ok_resp({"prompts": []})

    if method == "shutdown":
        return ok_resp({})

    if is_notification:
        return None
    return err_resp(-32601, "不支持的方法：%s" % method)


# ---------------------------------------------------------------- 主循环

def _stream_encoding(stream) -> str:
    """取流的编码名，归一化成小写无分隔符形式。"""
    enc = getattr(stream, "encoding", None) or ""
    return str(enc).lower().replace("-", "").replace("_", "").strip()


def _needs_utf8(stream) -> bool:
    """该流是否需要用 UTF-8 重建。

    None 要重建；已是非 UTF-8 编码（打包版是 cp936）也要重建。
    """
    if stream is None:
        return True
    # 只认 UTF-8。ascii 看着「安全」，但写中文会静默变成 '?'，
    # 和 GBK 一样属于坏编码，必须一起换掉。
    return _stream_encoding(stream) not in ("utf8", "utf8sig")


def _fix_stream(name: str, fd: int, mode: str, empty: str):
    """把 sys.<name> 修成 UTF-8 文本流。返回修好后的流（可能原样返回）。"""
    cur = getattr(sys, name, None)
    if not _needs_utf8(cur):
        return cur

    # 已有流：优先 reconfigure，这样不会丢掉已经缓冲的字节。
    if cur is not None:
        recfg = getattr(cur, "reconfigure", None)
        if recfg is not None:
            try:
                recfg(encoding="utf-8", errors="replace")
                setattr(sys, name, cur)
                return cur
            except Exception:  # noqa: BLE001 —— 有的流不支持 reconfigure
                pass

    # 走 fd 重建。closefd=False 很关键：不能把 fd 也关掉，
    # 否则旧的包装器被 GC 时会把 0/1/2 一起关了。
    try:
        new = io.open(fd, mode, encoding="utf-8", errors="replace",
                      newline="\n", closefd=False)
        setattr(sys, name, new)
        return new
    except OSError:
        pass

    # 兜底：原来有流就留着（GBK 总比 None 强），没有就给个空的。
    if cur is not None:
        return cur
    fb = io.StringIO(empty)
    setattr(sys, name, fb)
    return fb


def _ensure_stdio() -> None:
    """把 stdio 统一修成 UTF-8。

    两条独立的坑，都要治：

    1. **流为 None**（无控制台的窗口模式）：fd 0/1/2 仍然连着客户端
       给的管道，重新 open 就能用。
    2. **流是 GBK**（PyInstaller 打包版实测）：Python 按系统区域设置
       初始化 stdio，中文入站被解成乱码、出站也编成乱码，而且
       `operator_professions` 这类以中文为字典键的工具会因为乱码撞键
       而**静默丢数据**（8 个职业变 6 个）。这个比 None 更阴险，
       因为源码模式永远复现不了。

    stdout 是协议通道，所以一律强制 UTF-8，不看环境。
    """
    _fix_stream("stdin", 0, "r", "")
    _fix_stream("stdout", 1, "w", "")
    _fix_stream("stderr", 2, "w", "")


def serve(stdin=None, stdout=None) -> int:
    """阻塞式主循环。返回进程退出码。

    退出时会把 sys.stdin/stdout/stderr **还原**。这一步不是洁癖：
    ``_ensure_stdio()`` 改的是全局流，如果进程内还有人要接着用标准
    输出（比如测试、或将来嵌入式调用），不复原就等于把 stdout 偷走了。
    """
    # 无条件调用：打包版流不是 None 而是 GBK，条件调用会漏掉。
    _orig = (sys.stdin, sys.stdout, sys.stderr)
    try:
        _ensure_stdio()
        return _serve_loop(stdin, stdout)
    finally:
        sys.stdin, sys.stdout, sys.stderr = _orig


def _serve_loop(stdin=None, stdout=None) -> int:
    if stdin is not None:
        sys.stdin = stdin
    if stdout is not None:
        sys.stdout = stdout
    stdin = sys.stdin
    stdout = sys.stdout
    log("启动，协议版本 %s（utf-8 已就绪）" % PROTOCOL_VERSION)

    for line in stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
        except ValueError as e:
            log("JSON 解析失败: %s" % e)
            resp = {"jsonrpc": "2.0", "id": None,
                    "error": {"code": -32700, "message": "JSON 解析失败"}}
            stdout.write(json.dumps(resp, ensure_ascii=False) + "\n")
            stdout.flush()
            continue

        if not isinstance(req, dict):
            continue

        try:
            resp = handle(req)
        except Exception as e:  # noqa: BLE001
            log("handle 抛错: %r" % e)
            traceback.print_exc(file=sys.stderr)
            resp = {"jsonrpc": "2.0", "id": req.get("id"),
                    "error": {"code": -32603, "message": str(e)}}

        if resp is not None:
            stdout.write(json.dumps(resp, ensure_ascii=False) + "\n")
            stdout.flush()

    log("stdin 关闭，退出")
    return 0


def main(argv: Optional[List[str]] = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if "--self-test" in argv:
        return self_test()
    if "--list-tools" in argv:
        # 走 stderr：窗口模式下 print 到 None 的 stdout 会崩，
        # 而且 stdout 是协议通道，人工输出不该混进去。
        ts = tools()
        sys.stderr.write("共 %d 个工具\n" % len(ts))
        for t in ts:
            sys.stderr.write("%-30s %s\n" % (t.name, t.title))
        sys.stderr.flush()
        return 0
    return serve()


def self_test() -> int:
    """不依赖外部客户端，自己走一遍握手 + 工具列表。"""
    import io as _io
    reqs = [
        {"jsonrpc": "2.0", "id": 1, "method": "initialize",
         "params": {"protocolVersion": PROTOCOL_VERSION,
                    "clientInfo": {"name": "self-test"}}},
        {"jsonrpc": "2.0", "method": "notifications/initialized"},
        {"jsonrpc": "2.0", "id": 2, "method": "ping"},
        {"jsonrpc": "2.0", "id": 3, "method": "tools/list"},
        {"jsonrpc": "2.0", "id": 9, "method": "tools/call",
         "params": {"name": "__no_such_tool__", "arguments": {}}},
    ]
    ts = tools()
    # 注意：这里是 err（流对象），不是 err.write（绑定方法）。
    # 写 W = sys.stderr.write 再 W.flush() 会 AttributeError，
    # 而异常发生在最后一行，前面的输出都正常，极难发现。
    err = sys.stderr
    err.write("工具数: %d\n" % len(ts))
    for t in ts:
        err.write("  %-30s %s\n" % (t.name, t.title))
    err.write("\n")

    buf = "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in reqs)
    out = _io.StringIO()
    serve(_io.StringIO(buf), out)
    err.write("--- 响应 ---\n")
    body = out.getvalue()
    for line in body.splitlines():
        err.write(line[:300] + "\n")
    err.flush()

    # 顺手做几条断言：--self-test 是给构建脚本判断成败用的，
    # 只打印不打分的话 CI 里看不出坏没坏。
    bad = []
    try:
        parsed = [json.loads(x) for x in body.splitlines() if x.strip()]
    except ValueError as e:
        parsed = []
        bad.append("响应不是合法 JSON: %s" % e)
    got_init = any((o.get("result") or {}).get("protocolVersion")
                   for o in parsed)
    got_tools = False
    for o in parsed:
        tl = (o.get("result") or {}).get("tools")
        if tl:
            got_tools = len(tl) == len(ts)
    if not got_init:
        bad.append("initialize 没有返回 protocolVersion")
    if not got_tools:
        bad.append("tools/list 数量与注册表不一致")
    if bad:
        err.write("\n[自检失败] %s\n" % "; ".join(bad))
        err.flush()
        return 1
    err.write("\n[自检通过] %d 个工具，协议 %s，服务端版本 %s\n"
              % (len(ts), PROTOCOL_VERSION, SERVER_VERSION))
    err.flush()
    return 0


if __name__ == "__main__":
    sys.exit(main())
