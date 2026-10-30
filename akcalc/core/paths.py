"""路径与缓存目录管理。

同时支持两种运行形态：

* **源码运行**：缓存放在 ``akcalc/data/cache``。
* **PyInstaller 打包**：程序与缓存目录可能都是只读的（例如装在
  ``Program Files``），因此缓存优先写到 **exe 所在目录**；若该目录不可写，
  自动退回到 ``%LOCALAPPDATA%\\ArknightsCalc``。

打包时会把已抓取的干员/关卡/敌人数据作为「种子」一起打进去，
首次运行自动复制到可写缓存目录，做到装完即离线可用。
"""
from __future__ import annotations

import os
import shutil
import sys
from dataclasses import dataclass, field
from typing import List, Optional


def is_frozen() -> bool:
    """是否运行在 PyInstaller 打包出的 exe 里。"""
    return bool(getattr(sys, "frozen", False))


def bundle_root() -> str:
    """只读资源根目录。

    打包后是 PyInstaller 的临时解包目录（``sys._MEIPASS``），
    源码运行时是 ``akcalc`` 包目录。
    """
    if is_frozen():
        return getattr(sys, "_MEIPASS", os.path.dirname(sys.executable))
    return app_root()


def exe_dir() -> str:
    """exe 所在目录；源码运行时是 akcalc 包目录。"""
    if is_frozen():
        return os.path.dirname(os.path.abspath(sys.executable))
    return app_root()


def app_root() -> str:
    """返回 akcalc 包目录（本文件位于 akcalc/core/ 下，需上溯两层）。"""
    here = os.path.dirname(os.path.abspath(__file__))  # akcalc/core
    return os.path.dirname(here)                        # akcalc


def _writable(path: str) -> bool:
    """探测目录（不存在则看其父目录）是否可写。"""
    probe_dir = path
    while probe_dir and not os.path.isdir(probe_dir):
        parent = os.path.dirname(probe_dir)
        if parent == probe_dir:
            break
        probe_dir = parent
    if not probe_dir or not os.path.isdir(probe_dir):
        return False
    try:
        probe = os.path.join(probe_dir, ".akcalc_write_test")
        with open(probe, "w", encoding="utf-8") as f:
            f.write("ok")
        os.remove(probe)
        return True
    except OSError:
        return False


def default_writable_root() -> str:
    """选一个可写的缓存根目录。"""
    candidates = [exe_dir()]
    local = os.environ.get("LOCALAPPDATA") or os.environ.get("APPDATA")
    if local:
        candidates.append(os.path.join(local, "ArknightsCalc"))
    for cand in candidates:
        if _writable(cand):
            return cand
    # 最后兜底：用户主目录
    return os.path.join(os.path.expanduser("~"), "ArknightsCalc")


@dataclass
class Paths:
    """所有本地路径集中管理。"""

    root: str
    #: 只读种子数据根目录（打包时内置），为 None 表示不启用种子复制
    seed_root: Optional[str] = None
    #: 实际使用的缓存根目录（可能因只读而回退）
    fallback_root: Optional[str] = field(default=None)

    @classmethod
    def default(cls) -> "Paths":
        if is_frozen():
            preferred = exe_dir()
            if _writable(preferred):
                return cls(root=preferred, seed_root=bundle_root())
            fb = default_writable_root()
            return cls(root=fb, seed_root=bundle_root(),
                       fallback_root=preferred)
        return cls(root=app_root())

    # ------------------------------------------------------------ 目录

    @property
    def data_dir(self) -> str:
        return os.path.join(self.root, "data")

    @property
    def cache_dir(self) -> str:
        return os.path.join(self.data_dir, "cache")

    @property
    def operators_cache(self) -> str:
        return os.path.join(self.cache_dir, "operators.json")

    @property
    def levels_cache_dir(self) -> str:
        return os.path.join(self.cache_dir, "levels")

    @property
    def enemies_cache(self) -> str:
        return os.path.join(self.cache_dir, "enemy_database.json")

    @property
    def handbook_cache(self) -> str:
        """敌人档案（excel/enemy_handbook_table.json）。

        图鉴里那些人话描述（abilityList / description）只在手册里有，
        ``enemy_database.json`` 只有数值与技能代码，两者要配合着看。
        """
        return os.path.join(self.cache_dir, "enemy_handbook_table.json")

    @property
    def settings_file(self) -> str:
        return os.path.join(self.cache_dir, "settings.json")

    @property
    def seed_cache_dir(self) -> Optional[str]:
        if not self.seed_root:
            return None
        return os.path.join(self.seed_root, "data", "cache")

    @property
    def seed_data_dir(self) -> Optional[str]:
        """随包的 ``akcalc/data`` 只读副本（打包后在 ``_MEIPASS`` 里）。

        注意与 :attr:`seed_cache_dir` **不是**同一个地方：spec 里缓存文件
        放到 ``data/cache``，而 catalog / 图标这类表放到 ``akcalc/data``。
        图标就靠这个属性才能在 exe 里找到——它们只在这里读，不往可写
        目录复制（84MB，复制一遍纯属浪费启动时间）。
        """
        if not self.seed_root:
            return None
        return os.path.join(self.seed_root, "akcalc", "data")

    # ------------------------------------------------------------ 初始化

    def ensure(self) -> None:
        """建目录，并在首次运行时把内置种子数据复制过来。"""
        os.makedirs(self.cache_dir, exist_ok=True)
        os.makedirs(self.levels_cache_dir, exist_ok=True)
        self.seed_if_needed()

    def seed_if_needed(self) -> List[str]:
        """把内置种子缓存复制到可写目录（只补缺失的文件）。

        返回实际复制的条目名，便于日志与 UI 提示。
        """
        src = self.seed_cache_dir
        if not src or not os.path.isdir(src):
            return []
        copied: List[str] = []

        # 单文件（缓存目录内）
        for name, dst in [
            ("operators.json", self.operators_cache),
            ("enemy_database.json", self.enemies_cache),
            ("uniequip_table.json",
             os.path.join(self.cache_dir, "uniequip_table.json")),
            ("battle_equip_table.json",
             os.path.join(self.cache_dir, "battle_equip_table.json")),
            # 模组三阶段数值表：图鉴要显示模组一/二/三级的属性、特性、
            # 天赋，全靠这份精简表。缺了它 exe 版只能显示模组名字。
            ("module_stats.json",
             os.path.join(self.cache_dir, "module_stats.json")),
            # 敌人档案：图鉴的「特性 / 技能描述」来自这里（abilityList）。
            ("enemy_handbook_table.json", self.handbook_cache),
            # 召唤物数值表。spec 已经把它打进 _MEIPASS，但**这里**漏了它，
            # 结果 exe 版「召唤物」下拉只剩「不计入」——文件明明在包里，
            # 却没被复制到可写目录，等于没有。
            ("summon_stats.json",
             os.path.join(self.cache_dir, "summon_stats.json")),
        ]:
            s = os.path.join(src, name)
            if os.path.isfile(s) and not os.path.isfile(dst):
                try:
                    shutil.copy2(s, dst)
                    copied.append(name)
                except OSError:
                    pass

        # 关卡目录表 catalog.json：打包时放在 <seed>/akcalc/data/ 下，
        # 与 cache 不是同一个目录，必须单独复制，否则 exe 版寻路面板
        # 一直显示「关卡目录尚未载入」。
        if self.seed_root:
            for name in ("catalog.json", "enemy_names.json", "skill_table.json",
                         "skill_table_full.json", "enemy_icon_alias.json",
                         "codex_fields.json",
                         # 敌人技能名 -> prefabKey 映射（PRTS 抓取生成）。
                         # 图鉴的「技能」卡靠它把中文技能名和解包代码对上，
                         # 漏了这份就只能退回启发式，覆盖率掉一半。
                         "enemy_skills_prts.json",
                         # 集成战略（肉鸽）关卡索引。官方 stage_table 里一条
                         # 肉鸽关卡都没有，1033 条全靠这张表；spec 把它打进
                         # 了包里，但这里漏了复制，exe 版「集成战略」分类
                         # 会整个变空——和 handbook 是同一类坑。
                         "roguelike_topic_table.json",
                         # 敌人抬手表（解包 bakemuzzledata 解析产物）。
                         # 与 spec 的 seed 是两份独立白名单，必须成对维护。
                         "enemy_attack_timing.json",
                         # 干员抬手表（同一套 bake，按 charKey 索引）。
                         # 图鉴「面板数值」的抬手/登场、「技能」卡的技能抬手
                         # 都读它；漏了这份，干员页抬手整块消失。
                         "operator_attack_timing.json",
                         # 攻击范围图案表。MCP operator_range 靠它算「站这格
                         # 能打到哪些格」；沙盘的攻击范围预览也读它。spec 里
                         # 已经打进包里了，但**这里**漏了复制，exe 版范围
                         # 查询会整块返回空——和 handbook 是同一个坑。
                         "range_table.json",
                         # 全库出怪时间轴（gen_stage_waves.py 构建期抽取）。
                         # MCP stage_timeline / stage_field_at 的数据源，
                         # 少人课题全靠它。与 spec 的 seed 是两份独立白名单。
                         "stage_waves.json",
                          "battle_logic.json"):
                s = os.path.join(self.seed_root, "akcalc", "data", name)
                d = os.path.join(self.data_dir, name)
                if os.path.isfile(s) and not os.path.isfile(d):
                    try:
                        shutil.copy2(s, d)
                        copied.append(name)
                    except OSError:
                        pass

        # 关卡目录
        src_levels = os.path.join(src, "levels")
        if os.path.isdir(src_levels):
            n = 0
            for f in os.listdir(src_levels):
                if not f.endswith(".json"):
                    continue
                s = os.path.join(src_levels, f)
                d = os.path.join(self.levels_cache_dir, f)
                if os.path.isfile(d):
                    continue
                try:
                    shutil.copy2(s, d)
                    n += 1
                except OSError:
                    pass
            if n:
                copied.append(f"levels×{n}")
        return copied

    # ------------------------------------------------------------ 展示

    def human_report(self) -> str:
        """给 UI 显示的缓存占用情况。"""
        lines = []
        for label, path in [
            ("干员缓存", self.operators_cache),
            ("敌人库", self.enemies_cache),
            ("关卡目录", self.levels_cache_dir),
        ]:
            if os.path.isfile(path):
                kb = os.path.getsize(path) / 1024
                lines.append(f"{label}: {kb:,.0f} KB")
            elif os.path.isdir(path):
                n = len([f for f in os.listdir(path) if f.endswith(".json")])
                lines.append(f"{label}: {n} 个关卡")
            else:
                lines.append(f"{label}: 未缓存")
        return " | ".join(lines)