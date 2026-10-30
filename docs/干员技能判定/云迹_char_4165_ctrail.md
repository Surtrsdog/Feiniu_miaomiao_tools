# 云迹 — 技能判定说明

> 数据来源：明文 JSON（`character_table` / `skill_table` / `range_table` / `buff_template_data` / `bakemuzzledata`）。不含反汇编或二进制解析内容。

## 一、干员底子

| 项 | 值 |
|---|---|
| ID | `char_4165_ctrail` |
| 职业 | 特种 / `skywalker` |
| 星级 | 4 星 |
| 生命（精二满级） | 2255 |
| 攻击（精二满级） | 692 |
| 防御（精二满级） | 393 |
| 法抗 | 0% |
| **攻击间隔 baseAttackTime** | **1.5 秒** |
| 攻速 attackSpeed | 100（100% = 无增减） |
| 阻挡 | 2 |
| 部署费用 | 16 |

**攻击间隔换算**（全干员通用）：

```
实际间隔 = baseAttackTime ÷ (attackSpeed / 100)
         = 1.5 ÷ 1.00 = 1.500 秒
```

## 二、抬手（攻击前摇）

来源：`bakemuzzledata/character/char_4165_ctrail_*.json` → `bakedAnimDatas.<组>.bakedEvents.<动画名>.eventTime`，取事件 `OnAttack` 时刻。

| 场景 | 动画名 | 抬手 | 帧数(30fps) |
|---|---|---|---|
| **普通攻击** | `Attack` | **0.533333 秒** | 16 帧 |

> 占攻击间隔 35.6%（0.533333 秒 / 1.5 秒）。开技能不会让抬手变快。

| 技能动画 | `Skill_2_Begin` | 0.166667 秒 | 5 帧 |
| 技能动画 | `Skill_2_End` | 0.833333 秒 | 25 帧 |
| 技能动画 | `Skill_2_Loop` | 0.533333 秒 | 16 帧 |
| 技能动画 | `Skill_Begin` | 0.166667 秒 | 5 帧 |
| 技能动画 | `Skill_Down_2_Loop` | 0.533333 秒 | 16 帧 |
| 技能动画 | `Skill_Down_Loop` | 0.533333 秒 | 16 帧 |
| 技能动画 | `Skill_End` | 0.833333 秒 | 25 帧 |
| 技能动画 | `Skill_Loop` | 0.533333 秒 | 16 帧 |


## 三、技能逐层拆解

---

### 紧急升空　`skchr_ctrail_1`

**技能描述（最高级）：**

> 部署后立刻起飞，攻击范围扩大，攻击力+80%，获得60%的物理闪避


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `8` | — |
| 初始 SP / 消耗 SP | 0 / 0 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 0 | 可存层数 |
| 释放方式 | `PASSIVE` | 被动 |
| 技能形态 | `限时技能` | 持续 40 秒 |
| duration / durationType | 40 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `atk` | 0.8 |
| `prob` | 0.6 |
| `duration` | 40 |
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

**`ctrail_s_1`** ← 事件 `ON_TAKE_DAMAGE`

- **Evade** 

**`ctrail_s_1`** ← 事件 `ON_BUFF_START`

- **SwitchMode** `_modeIndex`=1 `_targetType`="BUFF_OWNER"

**`ctrail_s_1`** ← 事件 `ON_BUFF_FINISH`

- **SwitchMode** `_modeIndex`=3 `_targetType`="BUFF_OWNER"

---

### 掠空飞翎　`skchr_ctrail_2`

**技能描述（最高级）：**

> 立刻起飞，攻击范围扩大，攻击力+90%，同时攻击2个敌人且可额外攻击1个飞行敌人，击中飞行敌人时使其停顿1.5秒


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WITH_TIME` | 随时间自动回复 |
| 初始 SP / 消耗 SP | 5 / 15 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 1 | 可存层数 |
| 释放方式 | `MANUAL` | 手动释放 |
| 技能形态 | `限时技能` | 持续 30 秒 |
| duration / durationType | 30 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `atk` | 0.9 |
| `attack@sluggish` | 1.5 |
| `attack@max_walk_target` | 2 |
| `attack@max_target` | 3 |
| `attack@height_offset` | 0.8 |

#### 攻击范围

`rangeId = 3-1`，10 格（direction=1）

```
■ ■ ■ · 
■ ■ ■ ■ 
■ ■ ■ · 
```

#### 判定链

> 匹配方式：按命名规则匹配（层级 B）

**`ctrail_s_2`** ← 事件 `ON_BUFF_START`

- **SwitchMode** `_modeIndex`=4 `_targetType`="BUFF_OWNER"

**`ctrail_s_2`** ← 事件 `ON_BUFF_FINISH`

- **SwitchMode** `_modeIndex`=6 `_targetType`="BUFF_OWNER"

**`ctrail_s_2[sluggish]`** ← 事件 `ON_BUFF_START`

- **IfTarget** `_targetType`="TARGET"
- **CreateBuff** buffKey=`sluggish` `lifeTimeType`=LIMITED

---

## 附：数据边界

| 项目 | 状态 |
|---|---|
| 属性 / 数值 / SP / 范围 / 抬手 | ✅ 明文可得 |
| buff 行为树 | ✅ 明文可得 |
| 技能 → 模板绑定 | ⚠️ 游戏只给 `prefabId`，真实绑定在不可解的 `.ab` 里；本文按命名规律 + `blackboard` 键名双向推断 |
| 动画资源本体 | ❌ 在 `.ab` 包内，不可解 |
| 抬手精度 | ✅ 1/30 秒，是动画事件时刻而非视觉起手帧 |
