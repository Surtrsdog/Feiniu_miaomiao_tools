# Feiniu_miaomiao_tools · 肥牛妙妙工具

明日方舟的伤害计算器、寻路推演与沙盘工具（Windows 桌面程序）。

## 功能

- **伤害计算**：干员面板 / 天赋 / 技能 / 模组全量计算，支持多干员对比曲线
- **寻路推演**：关卡地图解析、敌人路线还原（含停驻、瞬移、半格偏移）
- **沙盘推演**：按秒回放敌人行进；放箱子改道、部署干员、踢除敌人、加减速，
  实时看重算后的路线与到达时间
- **敌人图鉴**：面板数值、天赋与能力、抗性免疫、**抬手（攻击前摇，帧+秒+30/60/120 帧率档）**
- **干员图鉴**：463 位干员，各精英化等级面板、天赋、技能
- **出怪时间轴**：任意关卡的完整出怪时刻表（第几秒出什么、走哪条路线、多久进蓝门），
  以及「第 t 秒场上有什么」；关卡内的属性覆盖按本关数值给出
- **攻击范围**：某干员站在某格、朝某方向能覆盖哪几格（可平移到任意位置）
- **MCP 数据接口**：把上述数据开放给外接 AI（Claude Desktop / Cursor / Cline…）

## 下载

到 [Releases](https://github.com/Surtrsdog/Feiniu_miaomiao_tools/releases) 下载
最新版安装包；程序内置更新检查，也可以从菜单里一键升级。

## 外接 AI（MCP）

本工具自带 MCP 服务端，可以让 Claude Desktop、Cursor、Cline 等客户端直接
读取干员、敌人、地图、路线、出怪波次、攻击范围数据——**包括 PRTS 查不到的
敌人抬手时间，以及少人课题最缺的「第 t 秒场上会出现什么」**。

**配置方式：打开软件 → 设置 → 「MCP 接口」→ 点「复制配置」**，
粘进客户端配置文件后重启客户端。卡片上还会直接显示当前命令，并提供
一个「自检」按钮（不用装客户端就能确认服务端活着）。

手写配置长这样（路径换成你的实际位置）：

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

共 34 个工具：敌人 6（含抬手与帧秒换算）、干员 5、地图 4、路线 4、
战斗 7、技能机制 3、**出怪时间轴 3**、**攻击范围 2**。
完整说明见 [docs/MCP接口说明.md](docs/MCP接口说明.md)。

## 数据来源

- 游戏数据：[Kengxxiao/ArknightsGameData](https://github.com/Kengxxiao/ArknightsGameData)（zh_CN）
- 干员与技能：[PRTS.wiki](https://prts.wiki)
- 敌人抬手：解包 `bakemuzzledata` 动作烘焙数据（2109 个文件 / 89.2 MB）
- 出怪波次：解包 `levels/**/level_*.json` 的 `waves` 字段，构建期跑
  `python akcalc/tools/gen_stage_waves.py` 生成 `akcalc/data/stage_waves.json`

## 界面

tkinter 桌面界面，`build_exe.spec` 打包，入口 `run_gui.py`（`run.py` 也进同一套界面）。

## 构建

```powershell
# tkinter 版
.build\pylibs\bin\pyinstaller build_exe.spec --noconfirm
```

产物在 `dist\`。

## 目录

```
akcalc/
├── core/       # 数据层：解包解析、面板计算、寻路、沙盘推演
├── ui/         # 界面层（tkinter）
├── mcp/        # MCP 服务端（stdio JSON-RPC）
├── tools/      # 构建期数据生成脚本（不随包）
└── data/       # 随包数据表与缓存
docs/           # 开发文档
```

## 说明

非官方工具，与鹰角网络无关。数据版权归原权利方所有，仅供学习与个人使用。
