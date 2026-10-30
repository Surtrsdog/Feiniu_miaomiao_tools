# -*- coding: utf-8 -*-
import json, subprocess, sys, threading

exe = r"F:\mini api\dist\肥牛妙妙工具.exe"
proc = subprocess.Popen([exe, "--mcp"], stdin=subprocess.PIPE,
                        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                        text=True, encoding="utf-8")
lines = []

def reader():
    for line in proc.stdout:
        lines.append(line)
        if len(lines) >= 3:
            break

t = threading.Thread(target=reader, daemon=True)
t.start()

def send(obj):
    proc.stdin.write(json.dumps(obj) + "\n")
    proc.stdin.flush()

def wait_line(idx, timeout=90):
    import time
    start = time.time()
    while len(lines) <= idx:
        if time.time() - start > timeout:
            raise TimeoutError("line %d not received" % idx)
        time.sleep(0.2)
    return json.loads(lines[idx])

try:
    send({"jsonrpc": "2.0", "id": 1, "method": "initialize",
          "params": {"protocolVersion": "2024-11-05", "capabilities": {},
                     "clientInfo": {"name": "t", "version": "1"}}})
    wait_line(0, 120)
    print("initialize: OK")
    send({"jsonrpc": "2.0", "method": "notifications/initialized"})
    send({"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
    d = wait_line(1, 60)
    tools = d.get("result", {}).get("tools", [])
    names = sorted(t["name"] for t in tools)
    print("tool count:", len(names))
    battle = [n for n in names if n.startswith("battle_") or n == "operator_sp_rotation"]
    print("battle tools:", battle)
    assert len(names) == 26
    assert len(battle) == 7
    send({"jsonrpc": "2.0", "id": 3, "method": "tools/call",
          "params": {"name": "battle_damage_calc",
                     "arguments": {"attack": 630, "target_defense": 1000}}})
    d3 = wait_line(2, 60)
    text = d3.get("result", {}).get("content", [{}])[0].get("text", "")
    payload = json.loads(text)
    print("damage(630,1000):", payload.get("final_damage"))
    assert abs(payload.get("final_damage", 0) - 31.5) < 0.01
    print("EXE MCP SMOKE TEST PASSED")
finally:
    try:
        proc.stdin.close()
    except Exception:
        pass
    proc.terminate()
    proc.kill()