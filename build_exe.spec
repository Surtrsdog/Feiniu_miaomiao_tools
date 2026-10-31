# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller 打包配置：生成单文件 exe。

用法（在 F:\mini api 下）：
    .build\pylibs\bin\pyinstaller build_exe.spec  --noconfirm

说明：
* 把 akcalc/data/cache 全量作为种子数据打进 exe，首次运行自动复制到
  exe 同目录，装完即离线可用（463 位干员 + 26 个关卡 + 敌人库）。
* onefile + windowed：单个 exe，无黑框。
"""
import os

# spec 与项目根同目录，据此定位资源，避免受工作目录影响
ROOT = os.path.dirname(os.path.abspath(SPEC))

CACHE = os.path.join(ROOT, 'akcalc', 'data', 'cache')
ICON = os.path.join(ROOT, '.build', 'app.ico')

# ---- 种子数据：把缓存目录整体带进 exe，落到 _MEIPASS/data/cache
seed = []
if os.path.isdir(CACHE):
    for name in ('operators.json', 'enemy_database.json', 'uniequip_table.json',
                 'battle_equip_table.json', 'module_stats.json',
                 # 召唤物数值（28 个会输出的 token）。缺了它「召唤物」下拉
                 # 会只剩「不计入」，点「重新下载数据」用户也未必知道要下。
                 'summon_stats.json',
                 # 敌人档案（abilityList / description）。这是「敌人图鉴
                 # 没有天赋与能力描写」唯一的源头：enemy_database.json
                 # 里只有数值和 prefabKey，一句人话都没有。
                 # paths.seed_if_needed() 会把它复制到可写目录，但前提是
                 # 它先得在 _MEIPASS 里存在——漏在这里，复制会静默跳过，
                 # exe 版图鉴的天赋/能力卡就整片空白，源码跑却完全正常。
                 'enemy_handbook_table.json',
                  'char_ranges.json'):
        p = os.path.join(CACHE, name)
        if os.path.isfile(p):
            seed.append((p, os.path.join('data', 'cache')))
    levels = os.path.join(CACHE, 'levels')
    if os.path.isdir(levels):
        seed.append((levels, os.path.join('data', 'cache', 'levels')))

# ---- 随包数据表：关卡目录（4521 关）+ 敌人中文名
DATA = os.path.join(ROOT, 'akcalc', 'data')
for name in ('catalog.json', 'enemy_names.json', 'skill_table.json',
             'skill_table_full.json', 'enemy_icon_alias.json',
             'codex_fields.json',
             # 敌人技能名 -> prefabKey（PRTS 抓取）。图鉴「技能」卡靠它
             # 把中文技能名和解包代码对上，漏了覆盖率会掉一半。
             'enemy_skills_prts.json',
             # 集成战略（肉鸽）关卡索引。官方 stage_table.json 里一条肉鸽
             # 关卡都没有，这 1033 条全靠这张表；缺了「集成战略」分类
             # 会整个变空，所以必须随包。
             'roguelike_topic_table.json',
             # 敌人抬手（攻击前摇）。数据来自解包 bakemuzzledata——
             # 2109 个文件 89MB，构建期解析成 0.22MB 的这张表。
             # 缺了它图鉴的「抬手」卡不显示，且不会有任何报错，
             # 属于典型静默降级，必须随包。
             'enemy_attack_timing.json',
             # 干员抬手（攻击前摇）+ 登场 + 技能抬手。同一套 bake，
             # 465 个文件 72MB，构建期解析成 45KB 的这张表。
             # 同样属于漏了就静默降级（干员页抬手整块不显示），必须随包。
             'operator_attack_timing.json',
             # ---- 批次 B 新增数据文件 ----
             # 攻击范围形状表（B4 §7，73 个 id，18.7KB）。
             # 沙盘 _load_char_ranges 按 __file__ 相对路径读
             # akcalc/data/range_table.json；漏了它所有干员范围退回 3×3。
             'range_table.json',
             # 装置目录（批次 C S0，207 种装置，75KB）。
             # maps.py _token_catalog() 按 __file__ 相对路径读
             # akcalc/data/token_catalog.json；漏了它所有装置降级 D 类，
             # 寻路不再被装置阻挡（好梦在何方的石箱墙直接消失）。
             'token_catalog.json',
             # 技能判定机制（图鉴「机制」卡 + MCP skill_mechanics_*）。
             # 由 buff_template_data.json（8681 模板 / 28MB）提炼成 0.37MB。
             # 漏了它图鉴机制卡显示「数据不可用」，MCP 三个工具报错。
             'skill_mechanics.json',
             # 全库出怪时间轴（MCP stage_timeline / stage_field_at）。
             # 由 akcalc/tools/gen_stage_waves.py 从 4010 个关卡文件
             # （waves/fragments/actions 三层 preDelay 累加，走同一个
             # parse_timeline）抽取成 4.8MB / 4007 关 / 13.1 万出怪批次。
             # 漏了它两个工具直接报「没有出怪数据」，少人课题没法做；
             # 与 core/paths.py 的 seed 白名单是两份，必须成对维护。
             'stage_waves.json',
             # 战斗逻辑数据（IL2CPP 逆向提取，802KB）。
             # MCP battle_target_logic / battle_blackboard_dict /
             # battle_talent_triggers / battle_fps_info 的数据源。
             'battle_logic.json'):
    p = os.path.join(DATA, name)
    if os.path.isfile(p):
        seed.append((p, os.path.join('akcalc', 'data')))

# ---- 图标：干员/敌人头像
# 只带「最高一档」，其余尺寸由 operator_icons / enemy_icons 在运行时
# 就近缩放（这两个模块本来就支持按任意已有尺寸缩放）。
# 刻意不带敌人 44/64/128 三档：四档合计 132MB，而 96 档向下能覆盖
# 44/64/16，向上 128 只放 1.33 倍，肉眼看不出差别。
# 干员只有 128 一档（461 张，15MB），必须带——不带的话选择器里全是
# 名字缩写，用户明确投诉过这一点。
for sub in (('icons', 'operator', '128'), ('icons', 'enemy', '96')):
    src_dir = os.path.join(DATA, *sub)
    if os.path.isdir(src_dir):
        seed.append((src_dir,
                     os.path.join('akcalc', 'data', *sub)))

# ---- 窗口图标 png：exe 图标由 icon= 指定，窗口/任务栏小图标用这张 png
_ICON_PNG = os.path.join(ROOT, '.build', 'app_256.png')
if os.path.isfile(_ICON_PNG):
    seed.append((_ICON_PNG, '.'))

# ---- 版本资源：让 exe 属性里能看到版本号（否则右键属性一片空白）
_VERSION_FILE = os.path.join(ROOT, '.build', 'winver.txt')
if not os.path.isfile(_VERSION_FILE):
    _VERSION_FILE = None

# ---- 硬检查：catalog.json 必须存在，否则寻路面板会在 exe 里显示
# 「关卡目录尚未载入」。宁可打包时报错，也不要发出一个坏 exe。
_CATALOG = os.path.join(DATA, 'catalog.json')
if not os.path.isfile(_CATALOG):
    raise SystemExit('build_exe.spec: 缺少 akcalc/data/catalog.json，无法打包')

hiddenimports = [
    'akcalc',
    'akcalc.core',
    'akcalc.core.blocking',
    'akcalc.core.buffs',
    'akcalc.core.catalog',
    'akcalc.core.interactions',
    'akcalc.core.catalog',
    'akcalc.core.constants',
    'akcalc.core.coords',
    'akcalc.core.gamedata',
    'akcalc.core.timeline',
    'akcalc.core.compare',
    'akcalc.core.curves',
    'akcalc.core.damage',
    'akcalc.core.damage_type',
    'akcalc.core.enemies',
    'akcalc.core.maps',
    'akcalc.core.models',
    'akcalc.core.net',
    'akcalc.core.op_index',
    'akcalc.core.pathfinding',
    'akcalc.core.paths',
    'akcalc.core.prts_operator',
    'akcalc.core.routes',
    'akcalc.core.skills',
    'akcalc.core.skilldata',
    'akcalc.core.summons',
    'akcalc.core.talents',
    'akcalc.core.enemy_class',
    'akcalc.core.operator_icons',
    'akcalc.core.operator_modules',
    # ---- 以下这批曾经漏在清单外，打出来的 exe 一点就 ModuleNotFoundError。
    # 光看源码「import 得好好的」查不出来：它们大多是**函数内延迟导入**
    # （为了缩短启动时间、也为了 tkinter 未就绪时不炸），PyInstaller 的
    # 静态分析看不到，只能在这里手工点名。
    'akcalc.core.annotations',
    'akcalc.core.enemy_codex',
    'akcalc.core.enemy_icons',
    'akcalc.core.enemy_skills',
    'akcalc.core.enemy_timing',
    'akcalc.core.extra_mechanics',       # 图鉴「代码实现」卡（纯延迟导入）
    'akcalc.core.handbook',              # 敌人档案（纯延迟导入）
    'akcalc.core.mechanisms',            # 特殊地块/机关参数
    'akcalc.core.sandbox',               # 沙盘推演核心
    'akcalc.core.sandbox_track',         # 粗轴 / Deployment
    'akcalc.core.settings',
    'akcalc.core.single_instance',
    'akcalc.core.skill_instructions',    # 技能指令栏（纯延迟导入）
    'akcalc.core.update_check',
    'akcalc.ui',
    'akcalc.ui.app',
    'akcalc.ui.damage_panel',
    'akcalc.ui.home_panel',
    'akcalc.ui.map_canvas',
    'akcalc.ui.map_render',
    'akcalc.ui.playback',
    'akcalc.ui.timeline_canvas',
    'akcalc.ui.path_panel',
    'akcalc.ui.code_viewer',
    'akcalc.ui.widgets',
    'akcalc.ui.annotation_card',
    'akcalc.ui.data_index',
    'akcalc.ui.monster_codex',           # 图鉴弹窗（纯延迟导入）
    'akcalc.ui.sandbox_panel',           # 沙盘面板（纯延迟导入）
    'akcalc.ui.settings_dialog',
    'akcalc.ui.skill_render',
    'akcalc.ui.track_canvas',
    # ---- MCP 服务端（供外接 AI 读取数据）。
    # 整个包只在 app.main() 里被 `--mcp` 分支延迟导入，静态分析看不到。
    # 少一个都会让打包版 `肥牛妙妙工具.exe --mcp` 直接 ModuleNotFoundError，
    # 而源码模式完全正常 —— 这类问题只有打包后才知道。
    'akcalc.mcp',
    'akcalc.mcp.server',
    'akcalc.mcp.common',
    'akcalc.mcp.client_config',
    'akcalc.mcp.tool_enemies',
    'akcalc.mcp.tool_operators',
    'akcalc.mcp.tool_maps',
    'akcalc.mcp.tool_routes',
    # ---- 批次 B 新增模块（延迟导入，静态分析看不到） ----
    # 7 个战斗计算工具（tool_battle.py）。--mcp 模式下 tools() 延迟
    # 导入它们，漏了打包版 MCP 只有 19 个工具且战斗计算全部 404。
    'akcalc.mcp.tool_battle',
    # 攻击范围模块（B4 §7）。sandbox._load_char_ranges() 函数内延迟
    # 导入，漏了所有干员范围退回 3×3 兜底。
    'akcalc.core.ranges',
    # DP 经济系统（B2 §5）。sandbox.__init__ 函数内延迟导入，
    # 漏了沙盘部署直接崩（deploy_check 调 self.dp.can_afford）。
    'akcalc.core.dp',
    'tkinter',
    'tkinter.ttk',
    'tkinter.font',
    'tkinter.messagebox',
    'PIL',
    'PIL.Image',
    'PIL.ImageDraw',
    'PIL.ImageFilter',
    'PIL.ImageFont',
    'PIL.ImageTk',
    'PIL._tkinter_finder',
    # Pillow 11+ 的 C 扩展，PyInstaller 有时不会自动收集
    'PIL._imaging',
]

a = Analysis(
    [os.path.join(ROOT, 'run_gui.py')],
    pathex=[ROOT],
    binaries=[],
    datas=seed,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[os.path.join(ROOT, '.build', 'rt_hook.py')],
    excludes=['numpy', 'pandas', 'matplotlib', 'scipy', 'pytest',
              'setuptools', 'pip', 'test', 'unittest', 'pydoc_data'],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='肥牛妙妙工具',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=ICON if os.path.isfile(ICON) else None,
    version=_VERSION_FILE,
)