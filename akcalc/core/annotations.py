# -*- coding: utf-8 -*-
"""图鉴批注：给敌人 / 干员各写一条本地备注，可导出成 JSON 分享。

为什么不用 core/settings.py
--------------------------
settings 的 ``load`` 只收标量（``isinstance(v, (str, int, float, bool))``），
而批注是「一个 id 对应一条记录」的嵌套字典，塞进去会被**静默丢弃**：
读回来永远是空的，还不报错，属于最难查的那类 bug。字号那种单值设置和
批注本来就是两类数据（生命周期也不同），所以另开一份文件。

为什么 key 用 enemy_id / char_id 而不是中文名
--------------------------------------------
中文名会变：官方改译名（「霜星」→「霜星，寒灾」）、活动限定带后缀、
同名不同形态（「日冕」/「日冕[狂暴]」各算一条敌人）。一旦改名，按名字
存的批注全成了孤儿，用户只会觉得「我写的字丢了」。enemy_id / char_id
是解包数据里的稳定标识，跨版本、跨设备都不变，导出的 JSON 也因此能
直接在别人机器上合并。

存哪里
------
``paths.cache_dir`` 下两个互不相干的文件（annotations_enemy.json /
annotations_operator.json）。选 cache 目录是因为 ``Paths.default()``
已经保证它可写（打包版会自动回退到 %LOCALAPPDATA%），而且
``seed_if_needed()`` 只补缺失文件、从不删用户文件，所以批注放这儿是
安全的；放程序目录反而会被下次更新覆盖掉。

写入策略（三件事，都是为了别丢用户手写的字）
------------------------------------------
1. 内存里的 dict 是唯一真相，``flush()`` 才落盘。UI 层每敲一个字只更新
   内存（快），防抖 400ms 后再落盘；
2. 落盘是「同目录临时文件 + ``os.replace``」。直接覆盖时若写到一半断电 /
   磁盘满，留下的是半截 JSON，下次读回来整份批注都没了；``os.replace``
   在同一分区上是原子的，要么旧文件要么新文件；
3. 读失败（文件缺失 / JSON 坏了 / 结构不对）一律返回空 dict，绝不抛异常。
   用户手改坏了文件，图鉴也不该打不开。
"""
from __future__ import annotations

import io
import json
import os
import threading
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from .paths import Paths

#: 批注种类。两类各自一个文件，导出也分两份：
#: 用户明确要求「怪物批注和干员批注可以分别导出分享」。
KINDS = ("enemy", "operator")

#: 种类 -> 中文名（UI 标题、消息框都用它）
KIND_CN = {"enemy": "怪物批注", "operator": "干员批注"}

#: 种类 -> 本地文件名
_FILE_NAME = {
    "enemy": "annotations_enemy.json",
    "operator": "annotations_operator.json",
}

#: 种类 -> core/paths.py 里可能提供的属性名（取不到就按 cache_dir 拼）
_FILE_ATTR = {
    "enemy": "annotations_enemy",
    "operator": "annotations_operator",
}

#: 文件结构版本。以后要往记录里加字段（评分、标签……）时靠它做兼容。
SCHEMA = 1


class AnnotationError(Exception):
    """批注文件读写失败。

    UI 层捕获后弹 messagebox（导入一个坏 JSON 要提示错误、不能崩），
    所以这里只负责把「为什么失败」说清楚，不负责吞异常。
    """


def kind_cn(kind: str) -> str:
    """种类 -> 中文名；不认识的种类原样返回，不抛异常。"""
    return KIND_CN.get(kind, kind or "")


def default_file_name(kind: str) -> str:
    """该类批注的默认文件名（本地存储与导出对话框的 initialfile 都用它）。"""
    return _FILE_NAME.get(kind, "annotations_%s.json" % (kind or "other"))


def _check_kind(kind: str) -> str:
    """校验种类。传错种类是编程错误（不是用户输入），直接抛。"""
    if kind not in KINDS:
        raise ValueError("未知的批注种类：%r（只支持 %s）"
                         % (kind, " / ".join(KINDS)))
    return kind


def now_iso() -> str:
    """当前时间，ISO 8601 带时区偏移，精确到秒。

    带时区是刻意的：导出文件会在别人的机器上合并，两边时区不同时，
    光比字符串会得出错的先后顺序；带偏移的时间能换算到同一条时间轴上
    再比。
    """
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _stamp(value) -> float:
    """ISO 时间字符串 -> 可比较的秒数；解析不出来返回 -1（视为最旧）。

    手改过的 JSON 里 ``updated_at`` 可能是空的、乱写的，甚至根本不在。
    这些记录归到「最旧」，合并时会被带正常时间戳的那条覆盖；但本机没有
    这个 key 时它们仍会被合并进来（见 ``AnnotationStore.import_``）。
    """
    if not isinstance(value, str) or not value:
        return -1.0
    try:
        return datetime.fromisoformat(value).timestamp()
    except (TypeError, ValueError):
        return -1.0


def _norm_record(rec) -> Optional[dict]:
    """把任意一条记录洗成 ``{"text", "updated_at", "name"}``。

    不合格（没有正文、正文不是字符串）返回 None：宁可丢掉一条，也不要
    让非字符串的 ``text`` 流进 UI（``Text.insert`` 会抛 TypeError）。
    记录本身是裸字符串时（``{"enemy_1001": "很硬"}``）当成正文——手改
    文件最省事的写法，认它一下成本很低。
    """
    if isinstance(rec, str):
        rec = {"text": rec}
    if not isinstance(rec, dict):
        return None
    text = rec.get("text")
    if not isinstance(text, str) or not text.strip():
        return None
    name = rec.get("name")
    ts = rec.get("updated_at")
    return {
        "text": text,
        "updated_at": ts if isinstance(ts, str) else "",
        "name": name if isinstance(name, str) else "",
    }


def _entries_of(raw) -> Dict[str, dict]:
    """从任意一份 JSON 里挖出 ``{key: 记录}``；结构不对就给空 dict。

    兼容三种写法：

    1. 现在导出的 ``{"schema": 1, "entries": {...}}``；
    2. 老版本 / 手写的「顶层直接就是 key -> 记录」；
    3. 顶层压根不是 dict（数组、字符串、null）—— 直接空 dict。

    这个函数是「宽容读」的落点：任何异常都就地消化，绝不往外抛。
    """
    if not isinstance(raw, dict):
        return {}
    src = raw.get("entries")
    if not isinstance(src, dict):
        src = raw
    out: Dict[str, dict] = {}
    for key, rec in src.items():
        if not isinstance(key, str) or not key:
            continue
        item = _norm_record(rec)
        if item is not None:
            out[key] = item
    return out


def _atomic_write_json(path: str, payload) -> None:
    """原子写一份 JSON（同目录临时文件 + ``os.replace``），失败抛 OSError。

    临时文件名带 pid，避免两个进程同时写时互相踩（选 cache 目录的一个
    副作用就是用户可能开了个自检脚本在读写同一份文件）。
    """
    d = os.path.dirname(path)
    if d:
        os.makedirs(d, exist_ok=True)
    tmp = "%s.%d.tmp" % (path, os.getpid())
    try:
        with io.open(tmp, "w", encoding="utf-8", newline="\n") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2,
                      sort_keys=True)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    except BaseException:
        # 写坏就清掉临时文件，别在 cache 目录里留垃圾
        try:
            os.remove(tmp)
        except OSError:
            pass
        raise


class AnnotationStore:
    """一类 / 两类批注的读写、导出、导入。

    一个进程里应该只有**一个**实例（用 ``store_for`` 取），因为内存缓存
    就是真相：各建各的会出现「图鉴页写了批注，弹窗里打开是空的」，然后
    后写的把先写的覆盖掉。
    """

    def __init__(self, paths: Paths):
        self.paths = paths
        #: 重入锁：flush / set 可能被 UI 定时器和关窗回调同时碰到
        self._lock = threading.RLock()
        #: kind -> {key: {"text", "updated_at", "name"}}
        self._data: Dict[str, Dict[str, dict]] = {}
        #: 只改过内存、还没落盘的种类
        self._dirty: set = set()

    # ------------------------------------------------------------ 路径

    def path_of(self, kind: str) -> str:
        """该类批注的本地文件路径。"""
        _check_kind(kind)
        p = getattr(self.paths, _FILE_ATTR.get(kind, ""), "")
        if isinstance(p, str) and p:
            return p
        return os.path.join(str(self.paths.cache_dir), default_file_name(kind))

    # -------------------------------------------------------------- 读

    @staticmethod
    def _read_file(path: str) -> Dict[str, dict]:
        """读一份批注文件；任何问题都返回空 dict，不抛异常。"""
        try:
            with io.open(path, "r", encoding="utf-8") as f:
                raw = json.load(f)
        except (OSError, ValueError):
            return {}
        return _entries_of(raw)

    def _data_of(self, kind: str) -> Dict[str, dict]:
        """取某类的内存表，首次访问时懒加载。"""
        _check_kind(kind)
        with self._lock:
            data = self._data.get(kind)
            if data is None:
                data = self._read_file(self.path_of(kind))
                self._data[kind] = data
            return data

    def reload(self, kind: Optional[str] = None) -> None:
        """丢掉内存缓存重读（外部改过文件时用）。"""
        with self._lock:
            if kind is None:
                self._data.clear()
            else:
                self._data.pop(_check_kind(kind), None)

    def get(self, kind: str, key: str) -> str:
        """取一条批注正文；没有就空串（UI 直接塞进 Text 也不用判空）。"""
        rec = self._data_of(kind).get(key or "")
        return str(rec.get("text") or "") if isinstance(rec, dict) else ""

    def has(self, kind: str, key: str) -> bool:
        """这个 key 有没有批注（列表里画小圆点靠它）。"""
        return bool(self.get(kind, key))

    def all(self, kind: str) -> Dict[str, dict]:
        """取整类的浅拷贝（调用方乱改也不会污染内存表）。"""
        return {k: dict(v) for k, v in self._data_of(kind).items()}

    def keys(self, kind: str) -> List[str]:
        """该类有批注的 key 列表，按最近更新排前面。"""
        items = list(self._data_of(kind).items())
        items.sort(key=lambda kv: -_stamp(kv[1].get("updated_at")))
        return [k for k, _rec in items]

    def count(self, kind: str) -> int:
        """该类有多少条批注。"""
        return len(self._data_of(kind))

    # -------------------------------------------------------------- 写

    def set(self, kind: str, key: str, text: str, *, name: str = "",
            persist: bool = True) -> bool:
        """写一条批注；正文为空等于删除这条（不留空记录）。

        ``persist=False`` 只更新内存并标脏，由调用方稍后统一 ``flush()``：
        UI 每敲一个字就落盘太浪费，防抖 400ms 之后写一次就够。万一进程被
        强杀，最多丢最后那几百毫秒的输入。

        返回「值有没有变」：没变就不落盘，也不刷新 ``updated_at``——否则
        每次打开图鉴都会把时间戳刷成现在，导入别人的批注时永远是「本机这
        条更新」，merge 就失效了。
        """
        _check_kind(kind)
        key = key or ""
        if not key:
            return False
        body = (text or "").replace("\r\n", "\n").replace("\r", "\n")
        with self._lock:
            data = self._data_of(kind)
            old = data.get(key) or {}
            old_text = str(old.get("text") or "")
            old_name = str(old.get("name") or "")
            # 末尾空白不算内容；中间的空行照留（用户可能故意分段）
            if not body.strip():
                if not old:
                    return False
                data.pop(key, None)
                self._dirty.add(kind)
                if persist:
                    self.flush()
                return True
            body = body.rstrip()
            new_name = name or old_name
            if body == old_text and new_name == old_name:
                return False
            data[key] = {
                "text": body,
                "updated_at": now_iso(),
                "name": new_name,
            }
            self._dirty.add(kind)
            if persist:
                self.flush()
            return True

    def remove(self, kind: str, key: str, *, persist: bool = True) -> bool:
        """删掉一条批注；返回有没有真的删掉。"""
        _check_kind(kind)
        with self._lock:
            data = self._data_of(kind)
            if (key or "") not in data:
                return False
            data.pop(key, None)
            self._dirty.add(kind)
            if persist:
                self.flush()
            return True

    def clear(self, kind: str, *, persist: bool = True) -> int:
        """清空一整类批注，返回清掉的条数。

        「导出 → 清空 → 再导入」是验收流程，也是用户怀疑自己写丢了时最
        直接的排查手段，所以做成公开接口而不是让调用方自己遍历 remove。
        """
        _check_kind(kind)
        with self._lock:
            data = self._data_of(kind)
            n = len(data)
            data.clear()
            if n:
                self._dirty.add(kind)
                if persist:
                    self.flush()
            return n

    def flush(self) -> bool:
        """把改过的种类全部落盘；任何一类写失败返回 False。

        不抛异常：写批注失败（磁盘满、目录只读）不该让图鉴崩掉，下一次
        修改还会再试一遍。
        """
        ok = True
        with self._lock:
            for kind in list(self._dirty):
                data = self._data.get(kind) or {}
                payload = {"schema": SCHEMA, "entries": data}
                try:
                    _atomic_write_json(self.path_of(kind), payload)
                except (OSError, ValueError, TypeError):
                    ok = False
                    continue
                self._dirty.discard(kind)
        return ok

    # -------------------------------------------------------- 导出 / 导入

    def export(self, kind: str, path: str) -> int:
        """把该类批注导出成 JSON，返回导出的条数（只含这一类）。

        导出前先 ``flush()``：用户刚打的字可能还在内存里，导出文件里必须
        有它，否则「我明明写了」和「导出来是空的」会同时成立。

        文件头带上 ``kind`` / ``kind_cn``，纯粹给人看——导出的 JSON 经常
        直接被贴进群里，「这是怪物批注还是干员批注」得一眼看出来。
        """
        _check_kind(kind)
        self.flush()
        # 导出到批注库自己的文件会**直接毁掉库**：紧接着任何一次
        # flush()（比如导入另一类时）都会拿内存里的旧内容把它盖回去，
        # 用户看到的是「导出成功，但文件里的东西没了」。真实场景里
        # 用户完全可能顺着 cache 目录点进 annotations_enemy.json。
        try:
            if os.path.abspath(str(path)) == os.path.abspath(
                    self.path_of(kind)):
                raise AnnotationError(
                    "不能把批注导出到它自己的库文件「%s」。\n"
                    "这是程序保存批注的地方，覆盖它会让已有批注丢失，"
                    "请换一个目录（例如桌面）另存。" % self.path_of(kind))
        except AnnotationError:
            raise
        except Exception:
            pass
        entries = {k: dict(v) for k, v in self._data_of(kind).items()}
        payload = {
            "schema": SCHEMA,
            "kind": kind,
            "kind_cn": kind_cn(kind),
            "exported_at": now_iso(),
            "count": len(entries),
            "entries": entries,
        }
        try:
            _atomic_write_json(path, payload)
        except OSError as e:
            raise AnnotationError("写入不了「%s」：%s" % (path, e))
        return len(entries)

    def import_(self, kind: str, path: str) -> Tuple[int, int]:
        """合并一份批注文件，返回 ``(合并进来的条数, 保留本机较新的条数)``。

        语义是 **merge**，不是整份覆盖：

        * 两边都有同一个 key 时比 ``updated_at``，取更新的那条；
        * 本机有、文件里没有的条目**原样保留**——从别人那儿导入一份怪物
          批注，不该把你自己写的那几只怪清掉；
        * 文件里多出来的 key 直接合并进来（别人的批注也该看见），所以
          导入是「并集 + 同 key 取新」。

        文件读不了 / 不是合法 JSON 时抛 ``AnnotationError``，UI 弹
        messagebox 提示，进程不受影响。

        **类型校验**：导出文件头里有 ``kind``，导入时会核对。用户点错
        文件是常事——把「干员批注」导进「怪物批注」，数据不会报错，
        只会让怪物列表里凭空多出一堆 ``char_172_svrash``，等发现时已经
        混了几百条。所以 ``kind`` 对不上直接拒绝，并说清是哪个文件该
        导到哪里。老版本导出没有 ``kind`` 字段，那种文件仍然放行（宁可
        兼容，也不把用户的历史备份锁死）。
        """
        _check_kind(kind)
        try:
            with io.open(path, "r", encoding="utf-8") as f:
                raw = json.load(f)
        except OSError as e:
            raise AnnotationError("打不开「%s」：%s" % (path, e))
        except ValueError as e:
            raise AnnotationError("「%s」不是合法的 JSON：%s" % (path, e))
        if isinstance(raw, dict):
            src_kind = str(raw.get("kind") or "").strip()
            if src_kind and src_kind != kind:
                src_cn = kind_cn(src_kind) if src_kind in KINDS else src_kind
                raise AnnotationError(
                    "这份文件是「%s」，不能导进「%s」。\n"
                    "它应当用「%s」那一栏的导入按钮。"
                    % (src_cn, kind_cn(kind), src_cn))
        incoming = _entries_of(raw)
        if not incoming:
            # 合法 JSON 但没有一条能用的记录：当成「空文件」提示，不算错
            return (0, 0)
        merged_n = kept = 0
        with self._lock:
            data = self._data_of(kind)
            for key, rec in incoming.items():
                old = data.get(key)
                if old is not None:
                    if _stamp(rec.get("updated_at")) <= _stamp(
                            old.get("updated_at")):
                        kept += 1
                        continue
                    old_name = str(old.get("name") or "")
                else:
                    old_name = ""
                data[key] = {
                    "text": rec["text"],
                    "updated_at": rec.get("updated_at") or now_iso(),
                    "name": rec.get("name") or old_name,
                }
                merged_n += 1
            if merged_n:
                self._dirty.add(kind)
                self.flush()
        return (merged_n, kept)


#: 进程内兜底缓存：owner 不接受新属性时用它，保证同一份 cache 目录共用一库。
_FALLBACK: Dict[str, AnnotationStore] = {}


def store_for(owner) -> AnnotationStore:
    """取（必要时创建）``owner`` 用的批注库；同一进程只建一份。

    三处图鉴（干员索引 / 怪物索引 / 怪物图鉴弹窗）都必须走这里拿 store，
    否则各建各的就会出现「图鉴页写了批注，弹窗里打开是空的」——两份内存
    缓存互不知道对方，后写的还会把先写的覆盖掉。

    ``owner`` 可以是 ``App``、任意 Toplevel（会顺着 ``.app`` 找）或
    ``Paths``（脚本里直接建库时用）。
    """
    app = getattr(owner, "app", None) or owner
    store = getattr(app, "_annotation_store", None)
    if isinstance(store, AnnotationStore):
        return store
    paths = getattr(app, "paths", None) or Paths.default()
    store = AnnotationStore(paths)
    try:
        app._annotation_store = store
    except Exception:
        key = os.path.abspath(str(getattr(paths, "cache_dir", "") or ""))
        store = _FALLBACK.setdefault(key, store)
    return store