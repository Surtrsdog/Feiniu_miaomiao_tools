# 归溟幽灵鲨 — 技能判定说明

> 数据来源：明文 JSON（`character_table` / `skill_table` / `range_table` / `buff_template_data` / `bakemuzzledata`）。不含反汇编或二进制解析内容。

## 一、干员底子

| 项 | 值 |
|---|---|
| ID | `char_1023_ghost2` |
| 职业 | 特种 / `dollkeeper` |
| 星级 | 6 星 |
| 生命（精二满级） | 2803 |
| 攻击（精二满级） | 737 |
| 防御（精二满级） | 322 |
| 法抗 | 0% |
| **攻击间隔 baseAttackTime** | **1.2 秒** |
| 攻速 attackSpeed | 100（100% = 无增减） |
| 阻挡 | 2 |
| 部署费用 | 16 |

**攻击间隔换算**（全干员通用）：

```
实际间隔 = baseAttackTime ÷ (attackSpeed / 100)
         = 1.2 ÷ 1.00 = 1.200 秒
```

## 二、抬手（攻击前摇）

来源：`bakemuzzledata/character/char_1023_ghost2_*.json` → `bakedAnimDatas.<组>.bakedEvents.<动画名>.eventTime`，取事件 `OnAttack` 时刻。

| 场景 | 动画名 | 抬手 | 帧数(30fps) |
|---|---|---|---|
| **普通攻击** | `Attack` | **0.4 秒** | 12 帧 |

> 占攻击间隔 33.3%（0.4 秒 / 1.2 秒）。开技能不会让抬手变快。

| 技能动画 | `Skill_3_Attack` | 0.833333 秒 | 25 帧 |
| 技能动画 | `Skill_3_Attack_Down` | 0.733333 秒 | 22 帧 |


## 三、技能逐层拆解

---

### 生存的技巧　`skchr_ghost2_1`

**技能描述（最高级）：**

> 开启时立即与范围内生命上限比例最低的其他我方干员交换生命上限比例，自身攻击力+150%


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WITH_TIME` | 随时间自动回复 |
| 初始 SP / 消耗 SP | 25 / 35 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 1 | 可存层数 |
| 释放方式 | `MANUAL` | 手动释放 |
| 技能形态 | `限时技能` | 持续 25 秒 |
| duration / durationType | 25 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `atk` | 1.5 |

#### 攻击范围

`rangeId = x-4`，9 格（direction=1）

```
■ ■ ■ 
■ ■ ■ 
■ ■ ■ 
```

#### 判定链

> 匹配方式：按命名规则匹配（层级 B）

**`ghost2_s_1[trigger_ability]`** ← 事件 `ON_BUFF_START`

- **TriggerAbility** `_targetType`="BUFF_OWNER"

**`ghost2_s_1[trigger_ability]`** ← 事件 `ON_BUFF_TRIGGER`

- **SwitchMode** `_modeIndex`=3 `_targetType`="TARGET"

---

### 生存的渴望　`skchr_ghost2_2`

**技能描述（最高级）：**

> 攻击力+130%，攻击速度+50，技能持续期间内干员的生命值不会低于1
> 技能结束后视为被击倒


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WITH_TIME` | 随时间自动回复 |
| 初始 SP / 消耗 SP | 25 / 35 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 1 | 可存层数 |
| 释放方式 | `MANUAL` | 手动释放 |
| 技能形态 | `限时技能` | 持续 20 秒 |
| duration / durationType | 20 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `atk` | 1.3 |
| `attack_speed` | 50 |

#### 攻击范围

`rangeId = 1-1`，2 格（direction=1）

> 该技能未指定自己的 `rangeId`，上图是干员**自身范围**。技能若扩大范围，会另有 `rangeId`。

```
■ ■ 
```

#### 判定链

> 匹配方式：按命名规则匹配（层级 B）

**`ghost2_s_2`** ← 事件 `ON_BUFF_START`

- **SwitchMode** `_modeIndex`=0 `_targetType`="TARGET"

**`ghost2_s_2`** ← 事件 `ON_BUFF_FINISH`

- **TriggerAbility** `_targetType`="BUFF_OWNER"

---

### 生存的重压　`skchr_ghost2_3`

**技能描述（最高级）：**

> 攻击间隔延长，攻击所有阻挡的敌人，攻击力+260%，生命上限+200%，攻击生命比例高于或等于自身的敌人时额外造成一次攻击力70%的物理伤害，否则自身流失3%生命


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WITH_TIME` | 随时间自动回复 |
| 初始 SP / 消耗 SP | 25 / 40 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 1 | 可存层数 |
| 释放方式 | `MANUAL` | 手动释放 |
| 技能形态 | `限时技能` | 持续 25 秒 |
| duration / durationType | 25 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `atk` | 2.6 |
| `max_hp` | 2 |
| `attack@atk_scale_ex` | 0.7 |
| `base_attack_time` | 1 |
| `attack@hp_ratio` | 0.03 |

#### 攻击范围

`rangeId = 1-1`，2 格（direction=1）

> 该技能未指定自己的 `rangeId`，上图是干员**自身范围**。技能若扩大范围，会另有 `rangeId`。

```
■ ■ 
```

#### 判定链

> 匹配方式：按命名规则匹配（层级 B）

**`ghost2_s_3[attack]`** ← 事件 `ON_BUFF_START`

- **IfElse** 
  - **FilterByTargetHpRatio** `_condType`="GE" `_targetType`="BUFF_OWNER"
  - **AdvancedApplyDamage** `_targetType`="TARGET"
  - **CreateEffect** `_targetType`="BUFF_OWNER"
  - **DamageViaMaxHpRatio** `_targetType`="BUFF_SOURCE"

---

## 附：数据边界

| 项目 | 状态 |
|---|---|
| 属性 / 数值 / SP / 范围 / 抬手 | ✅ 明文可得 |
| buff 行为树 | ✅ 明文可得 |
| 技能 → 模板绑定 | ⚠️ 游戏只给 `prefabId`，真实绑定在不可解的 `.ab` 里；本文按命名规律 + `blackboard` 键名双向推断 |
| 动画资源本体 | ❌ 在 `.ab` 包内，不可解 |
| 抬手精度 | ✅ 1/30 秒，是动画事件时刻而非视觉起手帧 |
