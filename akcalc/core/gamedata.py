"""统一的游戏数据下载通道。

为什么要单独一层
----------------
* `raw.githubusercontent.com` 在部分网络下会被重置连接，
  实测可用的裸文件通道是 jsDelivr：
  https://cdn.jsdelivr.net/gh/<owner>/<repo>@master/<path>
* 大文件（stage_table 19MB、enemy_database 15MB）需要长超时 + 重试；
  jsDelivr 偶尔返回不完整响应，故流式读取并校验长度。
* 目录列举用 GitHub 的 tree API（jsDelivr 的 package API 已 403）。

所有函数都返回 bytes / dict，失败抛 FetchError。
"""
from __future__ import annotations

import io
import json
import socket
import time
import urllib.error
import urllib.request
from typing import Dict, List, Optional

from .net import FetchError

GH_OWNER = "Kengxxiao"
GH_REPO = "ArknightsGameData"
GH_BRANCH = "master"

#: 裸文件通道（按可用性排序）
CDN_BASES = [
    "https://cdn.jsdelivr.net/gh/%s/%s@%s/" % (GH_OWNER, GH_REPO, GH_BRANCH),
    "https://fastly.jsdelivr.net/gh/%s/%s@%s/" % (GH_OWNER, GH_REPO, GH_BRANCH),
    "https://raw.githubusercontent.com/%s/%s/%s/" % (GH_OWNER, GH_REPO, GH_BRANCH),
]

UA = "akcalc/1.0 (+https://prts.wiki)"

#: zh_CN/gamedata/ 之后的部分
EXCEL_STAGE = "excel/stage_table.json"
EXCEL_ZONE = "excel/zone_table.json"
EXCEL_HANDBOOK = "excel/enemy_handbook_table.json"
EXCEL_CHAR = "excel/character_table.json"
ENEMY_DB = "levels/enemydata/enemy_database.json"

_ENEMY_DB_ALT = [
    "levels/enemydata/enemy_database.json",
    "levels/enemydata/enemy_database_CN.json",
]


def _read_all(resp, expected: int = 0) -> bytes:
    buf = io.BytesIO()
    while True:
        chunk = resp.read(262144)
        if not chunk:
            break
        buf.write(chunk)
    data = buf.getvalue()
    if expected and len(data) < expected:
        raise FetchError("下载不完整：%d/%d 字节" % (len(data), expected))
    return data


def fetch(path: str, timeout: float = 240.0, tries: int = 3) -> bytes:
    """按 `zh_CN/gamedata/` 之后的相对路径下载裸文件。"""
    last = None
    for attempt in range(max(1, tries)):
        for base in CDN_BASES:
            url = base + "zh_CN/gamedata/" + path
            try:
                req = urllib.request.Request(url, headers={"User-Agent": UA})
                with urllib.request.urlopen(req, timeout=timeout) as r:
                    expected = int(r.headers.get("Content-Length") or 0)
                    return _read_all(r, expected)
            except urllib.error.HTTPError as e:
                last = e
                if e.code == 404:
                    continue
            except Exception as e:      # 断连 / 超时 / 不完整
                last = e
        if attempt + 1 < tries:
            time.sleep(1.5 * (attempt + 1))
    raise FetchError("下载失败：%s（%s）" % (path, last))


def fetch_json(path: str, timeout: float = 240.0, tries: int = 3) -> dict:
    raw = fetch(path, timeout=timeout, tries=tries)
    try:
        return json.loads(raw.decode("utf-8", "replace"))
    except ValueError as e:
        raise FetchError("JSON 解析失败：%s（%s）" % (path, e))


def fetch_enemy_database(tries: int = 3) -> dict:
    """敌人库（15MB），试几个可能的文件名。"""
    last = None
    for path in _ENEMY_DB_ALT:
        try:
            return fetch_json(path, timeout=480.0, tries=tries)
        except FetchError as e:
            last = e
    raise last or FetchError("敌人库下载失败")


def list_level_paths(tries: int = 3) -> List[str]:
    """列出仓库里全部关卡文件路径（不含 zh_CN/gamedata/ 前缀）。"""
    url = ("https://api.github.com/repos/%s/%s/git/trees/%s?recursive=1"
           % (GH_OWNER, GH_REPO, GH_BRANCH))
    last = None
    for attempt in range(max(1, tries)):
        try:
            req = urllib.request.Request(url, headers={
                "User-Agent": UA, "Accept": "application/vnd.github+json"})
            with urllib.request.urlopen(req, timeout=300) as r:
                data = _read_all(r)
            tree = (json.loads(data.decode("utf-8", "replace"))
                    .get("tree") or [])
            out = []
            for node in tree:
                p = node.get("path") or ""
                if not p.startswith("zh_CN/gamedata/"):
                    continue
                rel = p[len("zh_CN/gamedata/"):]
                if rel.startswith("levels/") and rel.endswith(".json"):
                    out.append(rel)
            if out:
                return out
        except Exception as e:
            last = e
        time.sleep(2.0 * (attempt + 1))
    raise FetchError("文件列表获取失败（%s）" % last)