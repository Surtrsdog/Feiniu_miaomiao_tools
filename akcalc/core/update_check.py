# -*- coding: utf-8 -*-
"""检查更新：从 GitHub Releases 读取最新版本号。

## 设计取舍

* **不自动下载、不自动替换**。这个程序是单文件 exe，正在运行的时候
  替换自身在 Windows 上会失败（文件被占用），硬做要写一堆「起个
  bat 等进程退出再覆盖」的脏活，而且用户中途取消就留下半个文件。
  所以只负责「告诉用户有没有新版 + 给个下载链接」，让用户自己点。
* **失败必须安静**。没网、被墙、GitHub 抽风都很常见；这种情况下
  不能让用户看到一个报错弹窗，那比不检查还烦。所以所有异常都收敛成
  一个「检查失败」的返回值，界面上显示一行灰字。
* **版本号比较不用字符串比大小**。字符串比会让 ``beta10 < beta2``。
  这里按 ``v?主.次.补[-后缀]`` 切碎后逐段比，后缀单独比。
"""
from __future__ import annotations

import json
import re
import socket
import urllib.error
import urllib.request

#: GitHub 仓库（发版后填实际地址）
REPO = "Surtrsdog/Feiniu_miaomiao_tools"

#: Releases API。用 ``/latest`` 而不是 ``/releases``：前者拿到的就是
#: 「最新正式版」，不用自己在列表里挑，也自动跳过 draft。
API_LATEST = "https://api.github.com/repos/%s/releases/latest"

_TIMEOUT = 8

#: 版本号拆解。主版本段是**可选**的，因为本项目早期就用了纯后缀
#: 形式（``beta1`` / ``beta2``，没有 ``1.0.0-`` 前缀）。缺了主版本段
#: 时按 ``0`` 处理，这样 ``beta2`` 与 ``beta10`` 能按数字比大小。
_VERSION_RE = re.compile(
    r"^v?(\d+(?:\.\d+)*)?(?:[-_.]?([A-Za-z]+)(\d*))?$"
)

#: 后缀优先级：正式版最高，测试版次之。数字越大越新。
_STAGE_RANK = {"alpha": 0, "beta": 1, "rc": 2, "": 3}


class UpdateInfo:
    """一次检查的结果。"""

    def __init__(self, ok: bool, current: str = "", latest: str = "",
                 url: str = "", notes: str = "", error: str = "",
                 published: str = ""):
        self.ok = ok
        self.current = current
        self.latest = latest
        self.url = url
        self.notes = notes
        self.error = error
        self.published = published

    @property
    def has_update(self) -> bool:
        return bool(self.ok and self.latest
                    and compare_versions(self.latest, self.current) > 0)

    def summary(self) -> str:
        if not self.ok:
            return self.error or "检查更新失败"
        if self.has_update:
            return "发现新版本 %s（当前 %s）" % (self.latest, self.current)
        return "已是最新版本（%s）" % self.current


def parse_version(text: str) -> tuple:
    """把版本号切成可比较的元组。

    ``"beta2"`` -> ``((0,), 1, 2, "beta2")``
    ``"v1.2.3-beta4"`` -> ``((1, 2, 3), 1, 4, "beta4")``

    纯后缀形式（``beta2`` 没有主版本号）按 ``0`` 处理，这样
    ``beta2`` 和 ``beta10`` 能正确比出大小，而不是按字符串比。
    """
    raw = str(text or "").strip()
    m = _VERSION_RE.match(raw)
    if not m:
        return ((0,), -1, 0, raw)
    # 主版本段可能整个缺失（``beta2``），此时按 0 处理
    major = m.group(1) or ""
    nums = tuple(int(x) for x in major.split(".") if x != "") or (0,)
    stage = (m.group(2) or "").lower()
    stage_no = int(m.group(3) or 0)
    rank = _STAGE_RANK.get(stage, 0)
    return (nums, rank, stage_no, raw)


def compare_versions(a: str, b: str) -> int:
    """返回 1 表示 a 比 b 新，-1 表示旧，0 表示相同。

    先比主版本号（补齐长度），再比测试阶段（正式版 > rc > beta > alpha），
    最后比阶段序号（beta10 > beta2）。
    """
    va, vb = parse_version(a), parse_version(b)
    na, nb = va[0], vb[0]
    n = max(len(na), len(nb))
    na = na + (0,) * (n - len(na))
    nb = nb + (0,) * (n - len(nb))
    if na != nb:
        return 1 if na > nb else -1
    if va[1] != vb[1]:
        return 1 if va[1] > vb[1] else -1
    if va[2] != vb[2]:
        return 1 if va[2] > vb[2] else -1
    return 0


def check_latest(current: str, repo: str = "", timeout: int = _TIMEOUT) -> UpdateInfo:
    """问 GitHub 要最新版本。**任何异常都不抛**，折成 ``ok=False``。"""
    slug = (repo or REPO or "").strip()
    if not slug or "/" not in slug or slug.startswith("owner/"):
        return UpdateInfo(False, current=current,
                          error="还没有配置仓库地址，暂时无法检查更新")
    url = API_LATEST % slug
    req = urllib.request.Request(url, headers={
        "User-Agent": "FeiNiuMiaoMiao-UpdateChecker",
        "Accept": "application/vnd.github+json",
    })
    # ``urlopen(timeout=)`` 只约束**已建立连接之后**的读写，DNS 解析不受它管。
    # 国内解析 api.github.com 经常被投毒到不可达的地址，那里会一路卡到
    # 系统默认的 21 秒——用户点了「检查更新」看着按钮灰二十秒，以为卡死。
    # 这里把全局默认超时临时压到 timeout，解析阶段也受约束。
    _prev = socket.getdefaulttimeout()
    socket.setdefaulttimeout(timeout)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as fh:
            data = json.loads(fh.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        if e.code == 404:
            # 仓库还没发过 Release 时也是 404，和仓库不存在同码，
            # 提示里把两种可能都写出来，免得用户以为是网络问题。
            return UpdateInfo(False, current=current,
                              error="还没找到发布页（仓库未建或尚未发版）")
        return UpdateInfo(False, current=current,
                          error="GitHub 返回 HTTP %d" % e.code)
    except urllib.error.URLError as e:
        return UpdateInfo(False, current=current,
                          error="网络不通：%s" % (getattr(e, "reason", e),))
    except Exception as e:                                  # noqa: BLE001
        return UpdateInfo(False, current=current,
                          error="检查失败：%s" % e)
    finally:
        socket.setdefaulttimeout(_prev)

    tag = str(data.get("tag_name") or data.get("name") or "").strip()
    html = str(data.get("html_url") or "").strip()
    notes = str(data.get("body") or "").strip()
    pub = str(data.get("published_at") or "")[:10]
    if not tag:
        return UpdateInfo(False, current=current, error="Release 没有版本号")
    return UpdateInfo(True, current=current, latest=tag, url=html,
                      notes=notes, published=pub)
