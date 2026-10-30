# 蒂比 — 技能判定说明

> 数据来源：明文 JSON（`character_table` / `skill_table` / `range_table` / `buff_template_data` / `bakemuzzledata`）。不含反汇编或二进制解析内容。

## 一、干员底子

| 项 | 值 |
|---|---|
| ID | `char_4191_tippi` |
| 职业 | 特种 / `skywalker` |
| 星级 | 5 星 |
| 生命（精二满级） | 2368 |
| 攻击（精二满级） | 745 |
| 防御（精二满级） | 390 |
| 法抗 | 0% |
| **攻击间隔 baseAttackTime** | **1.5 秒** |
| 攻速 attackSpeed | 100（100% = 无增减） |
| 阻挡 | 2 |
| 部署费用 | 17 |

**攻击间隔换算**（全干员通用）：

```
实际间隔 = baseAttackTime ÷ (attackSpeed / 100)
         = 1.5 ÷ 1.00 = 1.500 秒
```

## 二、抬手（攻击前摇）

来源：`bakemuzzledata/character/char_4191_tippi_*.json` → `bakedAnimDatas.<组>.bakedEvents.<动画名>.eventTime`，取事件 `OnAttack` 时刻。

| 场景 | 动画名 | 抬手 | 帧数(30fps) |
|---|---|---|---|
| **普通攻击** | `Attack` | **0 秒** | 0 帧 |

> 占攻击间隔 0.0%（0 秒 / 1.5 秒）。开技能不会让抬手变快。

| 技能动画 | `Skill_2_Loop` | 0 秒 | 0 帧 |
| 技能动画 | `Skill_Loop` | 0 秒 | 0 帧 |


> ⚠️ **本条需实测复核**：`Attack` 动画的 `OnAttack` 事件落在第 0 帧（t = 0）。
>
> 含义：该循环动画的伤害帧就是循环起点帧。但**首次**攻击的抬手可能由另一段入场攻击动画决定，不能直接当成 0。
>
> 该干员其他含 `OnAttack` 的动画：`Skill_2_Loop` 0.200 秒

## 三、技能逐层拆解

---

### 专业喷绘技巧　`skchr_tippi_1`

**技能描述（最高级）：**

> 立刻起飞，攻击范围扩大，攻击力+100%


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WITH_TIME` | 随时间自动回复 |
| 初始 SP / 消耗 SP | 10 / 20 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 1 | 可存层数 |
| 释放方式 | `MANUAL` | 手动释放 |
| 技能形态 | `限时技能` | 持续 40 秒 |
| duration / durationType | 40 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `atk` | 1 |
| `attack@height_offset` | 0.8 |

#### 攻击范围

`rangeId = 2-3`，7 格（direction=1）

```
■ ■ · 
■ ■ ■ 
■ ■ · 
```

#### 判定链

> 匹配方式：按命名规则匹配（层级 B）

**`tippi_s_1[swtich_mode]`** ← 事件 `ON_BUFF_START`

- **SwitchMode** `_modeIndex`=1 `_targetType`="BUFF_OWNER"

**`tippi_s_1[swtich_mode]`** ← 事件 `ON_BUFF_FINISH`

- **SwitchMode** `_modeIndex`=3 `_targetType`="BUFF_OWNER"

---

### 紧急赶场通知　`skchr_tippi_2`

**技能描述（最高级）：**

> 立刻起飞，攻击范围扩大，攻击力+50%，攻击变为3连射
> 受到攻击后触发，并闪避本次物理或法术伤害


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WITH_TIME` | 随时间自动回复 |
| 初始 SP / 消耗 SP | 5 / 10 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 1 | 可存层数 |
| 释放方式 | `AUTO` | 自动释放 |
| 技能形态 | `限时技能` | 持续 15 秒 |
| duration / durationType | 15 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `atk` | 0.5 |
| `attack@height_offset` | 0.8 |

#### 攻击范围

`rangeId = y-1`，10 格（direction=1）

```
■ ■ ■ · 
■ ■ ■ ■ 
■ ■ ■ · 
```

#### 判定链

> 匹配方式：按命名规则匹配（层级 B）

**`tippi_s_2[switch_mode]`** ← 事件 `ON_BUFF_START`

- **SwitchMode** `_modeIndex`=4 `_targetType`="BUFF_OWNER"

**`tippi_s_2[switch_mode]`** ← 事件 `ON_BUFF_FINISH`

- **SwitchMode** `_modeIndex`=6 `_targetType`="BUFF_OWNER"

**`tippi_s_2[trigger]`** ← 事件 `ON_APPLYING_MODIFIER`

- **IsDamage** 
- **CheckUnitCurrentMode** `_targetType`="BUFF_OWNER"
- **TriggerAutoSkill** `_targetType`="BUFF_OWNER"
- **Evade** 

---

## 附：数据边界

| 项目 | 状态 |
|---|---|
| 属性 / 数值 / SP / 范围 / 抬手 | ✅ 明文可得 |
| buff 行为树 | ✅ 明文可得 |
| 技能 → 模板绑定 | ⚠️ 游戏只给 `prefabId`，真实绑定在不可解的 `.ab` 里；本文按命名规律 + `blackboard` 键名双向推断 |
| 动画资源本体 | ❌ 在 `.ab` 包内，不可解 |
| 抬手精度 | ✅ 1/30 秒，是动画事件时刻而非视觉起手帧 |
