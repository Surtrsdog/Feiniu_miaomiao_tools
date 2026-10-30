# 肥牛妙妙工具 · MCP 数据接口

把明日方舟的**干员、敌人、地图、路线、出怪波次、攻击范围**六类数据暴露给任何支持
[MCP（Model Context Protocol）](https://modelcontextprotocol.io) 的 AI 客户端
—— Claude Desktop、Cursor、Cline、Continue、Cherry Studio 等。

不需要你自己下载 89MB 解包数据，也不需要懂解包格式：客户端拉起的进程直接读
本工具已经建好的本地缓存。

---

## 最省事的配法：在软件设置里复制

打开软件 → 右上角「设置」→ 滚到 **MCP 接口** 卡：

* 卡片上直接显示当前命令、`N 个工具　协议 2024-11-05`
* 点 **复制配置** → 配置 JSON 进剪贴板 → 粘进客户端配置文件 → 重启客户端
* 点 **自检** → 不用装客户端就能确认服务端活着
  （显示「自检通过：34 个工具，协议 2024-11-05」）

> 配置是**生成**给你复制的，不会自动写进客户端。各家客户端配置文件
> 路径不同，而且里面可能已经配了别的 server，自动合并容易覆盖用户的
> 东西——所以这一步留给你自己粘。

下面两种方式是手工配置的写法，内容与上面复制出来的一致。

---

## 一键配置

### 方式一：用打包好的 exe（推荐普通用户）

在 MCP 客户端的配置文件里加上这一段即可（把路径换成你的实际位置）：

```json
{
  "mcpServers": {
    "feiniu-akcalc": {
      "command": "D:\\肥牛妙妙工具\\肥牛妙妙工具.exe",
      "args": ["--mcp"]
    }
  }
}
```

### 方式二：从源码跑（开发者）

```json
{
  "mcpServers": {
    "feiniu-akcalc": {
      "command": "python",
      "args": ["run.py", "--mcp"],
      "cwd": "F:\\mini api"
    }
  }
}
```

> `cwd` 必须指向项目根目录（`run.py` 所在的那一层）。

### 客户端配置文件在哪

| 客户端 | 位置 |
| --- | --- |
| Claude Desktop (Windows) | `%APPDATA%\Claude\claude_desktop_config.json` |
| Cursor | 项目内 `.cursor/mcp.json`，或设置 → MCP |
| Cline (VSCode 插件) | 插件面板 → MCP Servers → Configure |
| Cherry Studio | 设置 → MCP 服务器 → 添加 |

改完配置**重启客户端**。客户端会在启动时拉起本进程，随客户端退出而结束。

---

## 能用 AI 问什么

配置好之后，直接在对话里问就行：

- 「源石虫的抬手是多少秒？血量、防御呢？」
- 「列出血量最高的 10 个飞行敌人」
- 「银灰精英 2 满级的三维和天赋、技能」
- 「4-4 有几条路线？最短多少秒进蓝门？」
- 「4-4 第 30 秒场上还有哪些敌人，各自在哪一格？」
- 「4-4 第 6 秒开始出怪，完整出怪时间轴是怎么排的？」
- 「4-4 的源石虫是不是本关血量被改过？基础值多少、本关多少？」
- 「银灰站在 3-12 的某个格子上，朝右能覆盖哪几格？换成朝下呢？」
- 「列所有六星术师」
- 「集成战略有哪些关卡，本地缓存了哪些？」
- 「不死的黑蛇有什么技能，抬手多久？」

---

## 34 个工具一览

### 敌人（6 个）

| 工具 | 作用 |
| --- | --- |
| `enemy_library_status` | 敌人库是否加载、条目数、抬手表覆盖率 |
| `enemy_search` | 按中文名或 id 片段搜敌人 |
| `enemy_get` | 单敌人完整数据：面板 + 天赋能力 + 标签 + 免疫 + **抬手**；带 `stage` 参数时返回**本关覆盖后**的数值 |
| `enemy_attack_timing` | **抬手时间**，同时返回帧和秒（可批量） |
| `attack_timing_convert` | **帧 ⇄ 秒换算**（30 帧/秒），也能直接查某敌人的抬手 |
| `enemy_list` | 按飞行/伤害类型/血量区间筛选并排序 |

### 干员（5 个）

| 工具 | 作用 |
| --- | --- |
| `operator_library_status` | 干员缓存状态、数量、版本 |
| `operator_search` | 按名字/char_id 搜，支持职业、星级、位置筛选 |
| `operator_get` | 干员完整数据：各精英化各等级面板、天赋、技能、信赖、潜能 |
| `operator_list` | 按条件列干员 |
| `operator_professions` | 职业/子职业/星级/位置的取值字典 |

### 地图（4 个）

| 工具 | 作用 |
| --- | --- |
| `map_catalog_status` | 关卡索引数、本地缓存数、玩法分类分布 |
| `map_search` | 按代号（`4-4`）、中文名、stage_id 找关卡 |
| `map_get` | 地图详情：尺寸、地形字符画、红门/蓝门、可部署位、路线概览 |
| `map_list` | 按玩法分类列关卡 |

### 路线（4 个）

| 工具 | 作用 |
| --- | --- |
| `route_summary` | 路线统计：步行/飞行条数、最短最长耗时、可达性 |
| `route_list` | 每条路线的起点、终点、总耗时、终点是否在蓝门上 |
| `route_pose` | **第 t 秒某条路线上敌人在哪一格**（含半格偏移、停驻状态） |
| `route_at_second` | 反查：第 t 秒场上还有哪些敌人，各在哪 |

### 战斗（7 个）

| 工具 | 作用 |
| --- | --- |
| `battle_damage_calc` | 单次伤害：攻击、防御、法抗、增伤减免、暴击 |
| `battle_mixed_damage` | 物理 + 法术混合伤害结算 |
| `battle_dps_curve` | 按时间轴出 DPS 曲线（含技能轴） |
| `battle_attack_interval` | 攻击间隔换算（攻速加成 → 实际间隔/每秒次数） |
| `battle_kill_time` | 打死某个敌人需要多久 |
| `battle_sandbox_spec` | 沙盘推演参数规范（给前端/调用方对齐字段用） |
| `operator_sp_rotation` | 技能轴与技力回转推演 |

### 技能机制（3 个）

| 工具 | 作用 |
| --- | --- |
| `skill_mechanics_status` | 机制库是否可用、覆盖干员/技能数、三档置信度分布 |
| `skill_mechanics_search` | 按技能名 / skill_id / 干员名查判定机制 |
| `skill_mechanics_operator` | 某位干员全部技能的判定机制摘要 |

#### 它回答的是「怎么判」，不是「打多少」

技能描述只写「造成相当于攻击力 200% 的伤害」，不写这些：

- **打谁** —— `targetMotion=WALK_ONLY` 只打地面移动单位；
  `targetSide=ALLY` 打友方；`abnormalFlag=STUNNED` 只对晕眩中的目标生效
- **能不能叠** —— `overrideType=STACK`（叠层）/ `EXTEND`（续时间）/ `UNIQUE`（顶替）
- **什么时候断** —— `lifeTimeType=INFINITY`（常驻）/ `LIMITED`（限时）/ `IMMEDIATELY`
- **在什么事件上触发** —— `ON_BUFF_START` / `ON_BUFF_TRIGGER` / `ON_ATTACK`

这些字段在描述文本里一个都没有，只能从 buff 模板的节点树里读。

#### 数据从哪来，以及哪一步是推导的

`buff_template_data.json` 有 8681 个模板、28MB，不适合随包。构建期提炼成
0.37MB 的 `skill_mechanics.json`（脚本：`akcalc/tools/gen_skill_mechanics.py`）。

**必须说清的边界**：`skill_table.json` 里只有 `prefabId`，而「哪个技能用哪个
buff 模板」的官方绑定表在加密资源包（`.ab`）里，本地解不出来。所以模板归属
是推导的，分三档：

| 置信度 | 判定依据 | 数量 |
| --- | --- | --- |
| `A` | `blackboard` 键名直接写了模板名（如 `mlyss_s_3[unmoveable].duration`） | 40 |
| `B` | 按 `skchr_X_N` → `X_s_N` 命名规则推断 | 355 |
| `D` | 找不到对应模板 | 613 |

`A` 可以说得确定，`B` 说「大概率」，`D` 要说成「没有独立判定逻辑」——
不是数据缺失。大量纯数值强化技能（如银灰三个技能全是 `D`）本身就不需要
独立模板，只改 blackboard 和动画。

### 出怪时间轴（3 个）

| 工具 | 作用 |
| --- | --- |
| `stage_waves_status` | 出怪表是否加载、覆盖多少关、多少条出怪批次、生成脚本 |
| `stage_timeline` | **某关完整出怪时间轴**：第几秒、出什么、几条、走哪条路线、多久进蓝门 |
| `stage_field_at` | **第 t 秒场上有什么**：每只敌人的格子、蓝门剩余时间、之后 5 只什么时候出 |

前两类问题以前算不了：「这个敌人在某处我打不打得动」是伤害计算，
而「第 t 秒场上会出现什么」是调度问题——少人课题全靠后者推进。

#### 时间是怎么算的

一波出怪的实际时刻是**加法累积**的，四段延迟都要加：

```
实际时刻 = 波次 preDelay
         + 它之前所有 fragment 的时长（preDelay + 出怪跨度 + postDelay）
         + 本 fragment 的 preDelay
         + 出怪动作的 preDelay
```

4-4 第一只源石虫就是这个算法的例子：波次 `preDelay=0`（但占 1 逻辑帧），
fragment 内 `preDelay=3`，动作 `preDelay=3` → **6.0 秒**。

返回里 `t_note` 会把这几段拆开写清楚，`spawns` 每行的 `t` 是已经加好的
绝对秒数。`to_goal` 是这只敌人走到蓝门的预计时刻（按它自己的移动速度算，
不是按统一速度——4-4 的 `move_multiplier` 是 0.5，不同敌人差很多）。

#### 隐藏编队与随机包

同一波里常有多套**互斥**编队（`hiddenGroup`），或随机包
（`randomSpawnGroupKey`）。工具默认全都列出来并用 flags 标记，
`stage_field_at` 默认只算实际会出场的那批（`include_branch=false`），
需要看分支时传 `include_branch=true`。

### 攻击范围（2 个）

| 工具 | 作用 |
| --- | --- |
| `operator_range` | 某干员/某个 range_id 在指定格子上、指定朝向覆盖哪些格 |
| `operator_range_list` | 范围表里有哪些 range_id、每个覆盖几格；或某干员各精英化的 range |

`range_table.json` 里存的是**相对偏移**（以干员所在格为原点、默认朝右）。
所以同一份表可以平移到任意格子、朝四个方向旋转。返回里：

- `cells` —— 相对偏移，直接喂给「这几格打不打得到」的判断
- `abs_cells` —— 传了 `row`/`col` 时的绝对坐标，方便和地图对齐
- `targets` —— 传了 `targets` 时逐个回答「这格在不在范围内」
- `art` —— 字符画，人眼看一眼对不对

干员档案里**没有** ranges 字段，range 要从 `char_ranges.json`
按 `char_id → {elite: rangeId}` 查。银灰 `char_172_svrash`：
精英 0 是 `2-3`（7 格），精英 1/2 是 `3-12`（8 格）。

### 敌人查询带关卡（`enemy_get` 的 `stage` 参数）

`enemy_get` 多了个可选参数 `stage`。传了之后返回的是**本关覆盖后**的数值，
不再是库里的基础值：

```
enemy_get(query="enemy_1002_nsabr", stage="4-4")
→ hp = 2200   （基础值 1650，本关被 attributes.maxHp 覆盖）
```

返回里 `stats_base` 是原值、`overridden` 是 `{字段: [原值, 本关值]}`、
`override_fields` 是改过的字段清单。不传 `stage` 时行为完全不变。

这一条很关键：拿基础血去算能不能打死，在改过关卡的图上会算错。


---

## 抬手（攻击前摇）是什么，为什么重要

「抬手」= 敌人攻击动画从第 0 帧播到真正打出伤害的那一刻，需要多少秒。
它**只存在于解包的动作烘焙数据里**（`bakemuzzledata`），PRTS 和各种 wiki
API 都查不到——那些地方只有攻击间隔，没有前摇。

有了它才能算对这类问题：

> 「这个敌人在我撤退前能不能打出这一下？」

- 攻击间隔 3 秒、抬手 0.333 秒 → 你在它抬手第 0.2 秒撤掉干员，它这一下是空砍。
- 攻击间隔 3 秒、抬手 2.767 秒 → 它从起手就锁定了，你撤了也白撤。

数据规模：解包 2109 个动画文件、89.2 MB，构建期解析成 0.22 MB 的
`enemy_attack_timing.json`。覆盖 1868 / 2186 个敌人 id（85.4%）。

### 帧和秒都给

解包是按 **30 帧/秒**烘焙的，`eventTime` 本质就是「帧号 / 30」，
所以帧数是**原始数据不是估算**——1857 条里换算再换回来误差 < 0.001 帧。

工具返回的字段：

```json
{
  "attack_windup_seconds": 0.4667,
  "attack_windup_frames": 14,
  "fps": 30,
  "by_animation": {"Attack": 0.4667},
  "by_animation_frames": {"Attack": 14}
}
```

要单独换算某个数字，用 `attack_timing_convert`：

| 用法 | 参数 | 返回 |
|---|---|---|
| 帧转秒 | `{"value": 14, "from_unit": "frame"}` | `14 帧 / 0.467 秒` |
| 秒转帧 | `{"value": 0.4667, "from_unit": "second"}` | `14 帧 / 0.467 秒` |
| 60fps 口径 | `{"value": 28, "from_unit": "frame", "fps": 60}` | 同上（28帧@60 == 14帧@30） |
| 120fps 口径 | `{"value": 56, "from_unit": "frame", "fps": 120}` | 同上 |
| 查敌人 | `{"enemy": "源石虫"}` | 该敌人的抬手（帧+秒） |
| 换算表 | `{}` 或 `{"count": 60}` | 0~60 帧各是多少秒（含 60/120 列） |

### 30 / 60 / 120 的关系

**明日方舟本质是 30 帧游戏**：逻辑固定 30 步/秒，解包帧号是「真帧」。
60/120fps 是高刷设备的**插值帧**——渲染在两帧/四帧之间补中间姿态，
逻辑不变。所以同一时长帧号成比例：

```
14 帧@30 == 28 帧@60 == 56 帧@120 == 0.467 秒
```

所有返回里的 `frames_at_fps` 都同时给出三档。


剩下 252 个是真的没有攻击动画（箱子、门、载具等非战斗单位），
68 个没有对应烘焙文件。

单位统一为**秒**，从动画第 0 帧起算。返回值里 `anim` 告诉你用的是哪个动画
（有些敌人普攻有 `Attack_A` / `Attack_B` 两种，`by_animation` 会全列出来）。

---

## 关卡数据说明

工具**只读本地缓存，不会自己下载**。本机已有 2629 张地图；要查没缓存过的
关卡，先在「肥牛妙妙工具」里打开一次那一关（会自动下载并缓存），再来问 AI。

这样做是有意的：外接 AI 不该在你不知情的时候触发十几 MB 流量。

**出怪时间轴是例外**：`stage_waves.json` 在构建期从解包数据一次性生成，
覆盖 4007 个关卡 / 13.1 万条出怪批次，随包发布，不需要你打开过关卡。
但其中部分关卡的地图本身还没缓存（路线格坐标要用地图），这时
`stage_field_at` 会缺 `cell`/`to_blue`，`stage_timeline` 仍能给出完整时间轴
和路线编号。`stage_waves_status` 能看当前加载情况。

---

## 手动自检

不确定配好没有，可以先在命令行跑自检：

```powershell
# 源码模式
python run.py --mcp --self-test

# 打包版
.\肥牛妙妙工具.exe --mcp --self-test
```

正常会打印 34 个工具的名字，再回一段 JSON-RPC 响应。

列出工具名（不进入服务循环）：

```powershell
python -m akcalc.mcp --list-tools
```

---

## 技术细节（给想改代码的人）

### 传输方式

stdio，一行一个 JSON-RPC 消息，协议版本 `2024-11-05`。
不占端口、不写注册表、不需要令牌，进程随客户端退出而结束。

**stdout 是协议通道**，任何 `print()` 都会污染流导致客户端断连。
所以服务端所有日志都走 stderr。

### 打包版的两个坑（都是「源码正常、打包才炸」）

**坑一：stdio 可能是 `None`。**
spec 里 `console=False`（窗口模式），Windows 不分配控制台，某些情况下
Python 的 `sys.stdin` / `sys.stdout` / `sys.stderr` 会是 `None`。
但文件描述符 0/1/2 仍然连着客户端给的管道，重新 `open()` 就能用。

**坑二（更阴险）：stdio 是 GBK，不是 UTF-8。**
实测打包后的 exe，三个流**不是 `None`**，而是编码为 `cp936` 的
`TextIOWrapper`——Python 按系统区域设置初始化了 stdio。后果：

- 入站 `银灰`（UTF-8 字节 `e9 93 b6 e7 81 b0`）被按 GBK 解成 `閾剁伆`，
  工具报「找不到干员」；
- 出站也编成 GBK，Claude Desktop 按 UTF-8 读就是满屏乱码；
- 最隐蔽的：`operator_professions` 这类**以中文为字典键**的工具，
  8 个职业名在乱码下有两对撞成同一串，字典键被合并——**静默只剩 6 类**。
  数据文件本身完全正常，看起来像「数据丢了」，其实是编码问题。

`server._ensure_stdio()` 无条件把三个流强制成 UTF-8（先试
`reconfigure()`，失败再按 fd 重新 `open(..., closefd=False)`），
所以不看 `PYTHONIOENCODING`、也不依赖用户的区域设置。

> 只判断 `is None` 是不够的：GBK 情况下流存在，条件兜底根本不会执行。
> 这是我在打包版上实测才发现的，源码模式永远复现不了。

### 坑三：MCP 模式不经过 GUI，种子数据没人播种

打包版把 `operators.json` / `enemy_database.json` /
`enemy_attack_timing.json` 等种子数据放在 `_MEIPASS` 里，要靠
`Paths.ensure()` → `seed_if_needed()` 复制到可写目录才能读。

GUI 启动时自然会调 `ensure()`。但 **MCP 模式根本不经过 GUI**：
用户装完软件就在客户端里配好 MCP、从没手动打开过界面的话，
可写目录里一个数据文件都没有，于是所有工具都报
「敌人库还没下载」——而用户完全不知道该去哪里点那个按钮。

现在 `mcp/common.py` 的 `paths()` 在首次获取时自己调一次
`ensure()`，所以**全新安装 + 直接跑 `--mcp`** 也能用
（首次会花约 20 秒把 34MB 种子数据复制出来，之后就是毫秒级）。

实测：全新空目录跑 `--mcp`，抬手 0.3333 / 职业 8 类 / 4-4 不要恐慌
全部正常，可写目录自动长出 `data\cache\`。

另外 `--mcp` 的判断必须在**所有 GUI import 之前**：`akcalc.ui.app` 会拉起
tkinter 和一整套面板，MCP 是纯数据服务，不该依赖 GUI。

### 代码结构

```
akcalc/mcp/
├── __init__.py         # main() 转发
├── __main__.py         # python -m akcalc.mcp
├── server.py           # 协议层：JSON-RPC 分发、工具注册表、stdio 主循环
├── common.py           # 数据层单例：Paths / EnemyLibrary / HandbookIndex / OperatorCache
├── tool_enemies.py     # 敌人 6 个工具（含 enemy_get 的 stage 覆盖）
├── tool_operators.py   # 干员 5 个工具
├── tool_maps.py        # 地图 4 个工具
├── tool_routes.py      # 路线 4 个工具
├── tool_battle.py      # 战斗 7 个工具
├── tool_mechanics.py   # 技能机制 3 个工具
├── tool_stage.py       # 出怪时间轴 3 个工具
└── tool_range.py       # 攻击范围 2 个工具
```

### 加一个新工具

```python
# akcalc/mcp/tool_xxx.py
from .server import ok, error, tool

@tool("my_tool", "标题", "描述（AI 会读这段来理解什么时候调用）",
      {"type": "object", "properties": {...}, "required": [...]})
def my_tool(args: dict) -> dict:
    return ok({"whatever": 1})
```

然后在 `server.py` 的 `tools()` 里加一行 import，在 `build_exe.spec` 的
`hiddenimports` 里加 `'akcalc.mcp.tool_xxx'`（整个包都是延迟导入，
静态分析看不到，漏了打包后会 ModuleNotFoundError）。

---

## 常见问题

**AI 说「敌人库还没下载」**
在「肥牛妙妙工具」主界面点一次「下载敌人库」（约 15 MB，仅首次）。

**AI 说「干员缓存还没建立」**
打开一次干员面板，让它抓取 463 位干员的数据。

**AI 说某关没有本地地图缓存**
先在软件里打开一次那一关。

**客户端里看不到工具**
1. 命令行跑 `--mcp --self-test`，确认工具数 = 34；
2. 检查 JSON 配置里的路径有没有写错、`args` 里有没有 `--mcp`；
3. 完全退出客户端（不是最小化）再重开。

**用 exe 时客户端报「进程立即退出」**
确认 exe 路径里没有中文全角字符之类的异常符号；必要时用引号包住路径。
另外查看 exe 同目录的 `akcalc_error.log`。
