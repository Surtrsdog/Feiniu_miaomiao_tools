# Sharp — 技能判定说明

> 数据来源：明文 JSON（`character_table` / `skill_table` / `range_table` / `buff_template_data` / `bakemuzzledata`）。不含反汇编或二进制解析内容。

## 一、干员底子

| 项 | 值 |
|---|---|
| ID | `char_609_acguad` |
| 职业 | 近卫 / `fearless` |
| 星级 | 6 星 |
| 生命（精二满级） | 3472 |
| 攻击（精二满级） | 955 |
| 防御（精二满级） | 287 |
| 法抗 | 0% |
| **攻击间隔 baseAttackTime** | **1.5 秒** |
| 攻速 attackSpeed | 100（100% = 无增减） |
| 阻挡 | 1 |
| 部署费用 | 20 |

**攻击间隔换算**（全干员通用）：

```
实际间隔 = baseAttackTime ÷ (attackSpeed / 100)
         = 1.5 ÷ 1.00 = 1.500 秒
```

## 二、抬手（攻击前摇）

来源：`bakemuzzledata/character/char_609_acguad_*.json` → `bakedAnimDatas.<组>.bakedEvents.<动画名>.eventTime`，取事件 `OnAttack` 时刻。

| 场景 | 动画名 | 抬手 | 帧数(30fps) |
|---|---|---|---|
| **普通攻击** | `Attack` | **0.5 秒** | 15 帧 |

> 占攻击间隔 33.3%（0.5 秒 / 1.5 秒）。开技能不会让抬手变快。



## 三、技能逐层拆解

---

### 快刀　`skchr_acguad_1`

**技能描述（最高级）：**

> 攻击力+70%，每次攻击有20%概率变成二连击


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WITH_TIME` | 随时间自动回复 |
| 初始 SP / 消耗 SP | 15 / 30 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 1 | 可存层数 |
| 释放方式 | `MANUAL` | 手动释放 |
| 技能形态 | `限时技能` | 持续 30 秒 |
| duration / durationType | 30 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `attack@prob1` | 0.2 |
| `attack@prob2` | 0.8 |
| `atk` | 0.7 |

#### 攻击范围

`rangeId = 1-1`，2 格（direction=1）

```
■ ■ 
```

#### 判定链

本技能**没有独立 buff 模板**。它属于「一段式数值强化」：开技能只改 `blackboard` 参数与动画，不挂 buff 节点树。

可核对的替代证据：

- 描述中的每个花括号参数都能在 `blackboard` 中找到对应值（见上表）

---

### 亮剑　`skchr_acguad_2`

**技能描述（最高级）：**

> 防御力降至0，生命上限+50%，每次攻击的攻击力提升至220%


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WITH_TIME` | 随时间自动回复 |
| 初始 SP / 消耗 SP | 10 / 30 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 1 | 可存层数 |
| 释放方式 | `MANUAL` | 手动释放 |
| 技能形态 | `限时技能` | 持续 30 秒 |
| duration / durationType | 30 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `attack@atk_scale` | 2.2 |
| `max_hp` | 0.5 |

#### 攻击范围

`rangeId = 1-1`，2 格（direction=1）

> 该技能未指定自己的 `rangeId`，上图是干员**自身范围**。技能若扩大范围，会另有 `rangeId`。

```
■ ■ 
```

#### 判定链

本技能**没有独立 buff 模板**。它属于「一段式数值强化」：开技能只改 `blackboard` 参数与动画，不挂 buff 节点树。

可核对的替代证据：

- 描述中的每个花括号参数都能在 `blackboard` 中找到对应值（见上表）

---

### 力战不竭　`skchr_acguad_3`

**技能描述（最高级）：**

> 攻击力+60%；每次攻击时获得可叠加的攻击力+21%的增益（最多叠加8层），切换目标后层数清零，技能持续期间内干员的生命值始终不会低于1


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WITH_TIME` | 随时间自动回复 |
| 初始 SP / 消耗 SP | 30 / 40 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 1 | 可存层数 |
| 释放方式 | `MANUAL` | 手动释放 |
| 技能形态 | `限时技能` | 持续 20 秒 |
| duration / durationType | 20 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `atk` | 0.6 |
| `atk_each_stack` | 0.21 |
| `max_atk_stack_cnt` | 8 |

#### 攻击范围

`rangeId = 1-1`，2 格（direction=1）

> 该技能未指定自己的 `rangeId`，上图是干员**自身范围**。技能若扩大范围，会另有 `rangeId`。

```
■ ■ 
```

#### 判定链

> 匹配方式：按命名规则匹配（层级 B）

**`acguad_s_3[cleaner]`** ← 事件 `ON_BUFF_FINISH`

- **FinishBuffsById** `_targetType`="BUFF_OWNER"

---

## 附：数据边界

| 项目 | 状态 |
|---|---|
| 属性 / 数值 / SP / 范围 / 抬手 | ✅ 明文可得 |
| buff 行为树 | ✅ 明文可得 |
| 技能 → 模板绑定 | ⚠️ 游戏只给 `prefabId`，真实绑定在不可解的 `.ab` 里；本文按命名规律 + `blackboard` 键名双向推断 |
| 动画资源本体 | ❌ 在 `.ab` 包内，不可解 |
| 抬手精度 | ✅ 1/30 秒，是动画事件时刻而非视觉起手帧 |
