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
                 'battle_equip_table.json', 'module_stats.json'):
        p = os.path.join(CACHE, name)
        if os.path.isfile(p):
            seed.append((p, os.path.join('data', 'cache')))
    levels = os.path.join(CACHE, 'levels')
    if os.path.isdir(levels):
        seed.append((levels, os.path.join('data', 'cache', 'levels')))

# ---- 随包数据表：关卡目录（3439 关）+ 敌人中文名
DATA = os.path.join(ROOT, 'akcalc', 'data')
for name in ('catalog.json', 'enemy_names.json', 'skill_table.json',
             'skill_table_full.json', 'enemy_icon_alias.json',
             'codex_fields.json',
             # 敌人技能名 -> prefabKey（PRTS 抓取）。图鉴「技能」卡靠它
             # 把中文技能名和解包代码对上，漏了覆盖率会掉一半。
             'enemy_skills_prts.json'):
    p = os.path.join(DATA, name)
    if os.path.isfile(p):
        seed.append((p, os.path.join('akcalc', 'data')))

# ---- 窗口图标 png：exe 图标由 icon= 指定，窗口/任务栏小图标用这张 png
_ICON_PNG = os.path.join(ROOT, '.build', 'app_256.png')
if os.path.isfile(_ICON_PNG):
    seed.append((_ICON_PNG, '.'))

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
    'akcalc.core.enemy_class',
    'akcalc.core.operator_icons',
    'akcalc.core.operator_modules',
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
]

a = Analysis(
    [os.path.join(ROOT, 'run_gui.py')],
    pathex=[ROOT],
    binaries=[],
    datas=seed,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
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
    name='FeiNiuMiaoMiao',
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
)