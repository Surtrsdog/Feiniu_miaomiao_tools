# 娜仁图亚 — 技能判定说明

> 数据来源：明文 JSON（`character_table` / `skill_table` / `range_table` / `buff_template_data` / `bakemuzzledata`）。不含反汇编或二进制解析内容。

## 一、干员底子

| 项 | 值 |
|---|---|
| ID | `char_4138_narant` |
| 职业 | 狙击 / `loopshooter` |
| 星级 | 6 星 |
| 生命（精二满级） | 2500 |
| 攻击（精二满级） | 675 |
| 防御（精二满级） | 170 |
| 法抗 | 0% |
| **攻击间隔 baseAttackTime** | **1 秒** |
| 攻速 attackSpeed | 100（100% = 无增减） |
| 阻挡 | 1 |
| 部署费用 | 16 |

**攻击间隔换算**（全干员通用）：

```
实际间隔 = baseAttackTime ÷ (attackSpeed / 100)
         = 1 ÷ 1.00 = 1.000 秒
```

## 二、抬手（攻击前摇）

来源：`bakemuzzledata/character/char_4138_narant_*.json` → `bakedAnimDatas.<组>.bakedEvents.<动画名>.eventTime`，取事件 `OnAttack` 时刻。

| 场景 | 动画名 | 抬手 | 帧数(30fps) |
|---|---|---|---|
| **普通攻击** | `Attack` | **0.533333 秒** | 16 帧 |

> 占攻击间隔 53.3%（0.533333 秒 / 1 秒）。开技能不会让抬手变快。

| 技能动画 | `Skill_1` | 0.366667 秒 | 11 帧 |
| 技能动画 | `Skill_2_Loop` | 0.333333 秒 | 10 帧 |
| 技能动画 | `Skill_3_Loop` | 0.4 秒 | 12 帧 |
| 技能动画 | `Skill_Down_1` | 0.366667 秒 | 11 帧 |
| 技能动画 | `Skill_Down_2_Loop` | 0.333333 秒 | 10 帧 |
| 技能动画 | `Skill_Down_3_Loop` | 0.4 秒 | 12 帧 |


## 三、技能逐层拆解

---

### 旋刃　`skchr_narant_1`

**技能描述（最高级）：**

> 可以在下列状态和初始状态间切换：
> 攻击距离-1，回旋投射物造成相当于攻击力190%的物理伤害，并且可以在敌人间重复弹射（最多弹跳3次）


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WITH_TIME` | 随时间自动回复 |
| 初始 SP / 消耗 SP | 0 / 5 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 1 | 可存层数 |
| 释放方式 | `MANUAL` | 手动释放 |
| 技能形态 | `瞬发技能` | 无持续时间，效果立即结算 |
| duration / durationType | 0 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `attack@times` | 3 |
| `attack@atk_scale` | 1.9 |
| `ability_range_forward_extend` | -1 |

#### 攻击范围

`rangeId = y-7`，15 格（direction=1）

> 该技能未指定自己的 `rangeId`，上图是干员**自身范围**。技能若扩大范围，会另有 `rangeId`。

```
■ ■ ■ ■ ■ 
■ ■ ■ ■ ■ 
■ ■ ■ ■ ■ 
```

#### 判定链

> 匹配方式：按命名规则匹配（层级 B）

**`narant_s_1`** ← 事件 `ON_BUFF_START`

- **ModifyBoomberangMaxCnt** `_targetType`="BUFF_OWNER"

**`narant_s_1`** ← 事件 `ON_BUFF_DISABLE`

- **ModifyBoomberangMaxCnt** `_targetType`="BUFF_OWNER"

---

### 恶魇　`skchr_narant_2`

**技能描述（最高级）：**

> 每次攻击造成相当于攻击力250%的物理伤害并使目标停顿1秒，投射物命中目标后会在短暂突进后折返，返回时对穿过的所有敌人造成一次相当于攻击力200%的物理伤害


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WHEN_ATTACK` | 每次攻击回复 |
| 初始 SP / 消耗 SP | 8 / 15 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 1 | 可存层数 |
| 释放方式 | `MANUAL` | 手动释放 |
| 技能形态 | `限时技能` | 持续 30 秒 |
| duration / durationType | 30 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `attack@move_ahead_time` | 0.5 |
| `attack@projectile_range` | 1 |
| `attack@atk_scale` | 2.5 |
| `attack@atk_scale_comeback` | 2 |
| `attack@sluggish` | 1 |

#### 攻击范围

`rangeId = y-7`，15 格（direction=1）

> 该技能未指定自己的 `rangeId`，上图是干员**自身范围**。技能若扩大范围，会另有 `rangeId`。

```
■ ■ ■ ■ ■ 
■ ■ ■ ■ ■ 
■ ■ ■ ■ ■ 
```

#### 判定链

> 匹配方式：按命名规则匹配（层级 B）

**`narant_s_2`** ← 事件 `ON_BUFF_START`

- **ModifyBoomberangMaxCnt** `_targetType`="BUFF_OWNER"
- **IfElse** 
  - **CheckCharacterDefaultDirection** `_target`="BUFF_OWNER"
  - **SwitchMode** `_modeIndex`=3 `_targetType`="TARGET"
  - **SwitchMode** `_modeIndex`=2 `_targetType`="TARGET"

**`narant_s_2`** ← 事件 `ON_BUFF_DISABLE`

- **ModifyBoomberangMaxCnt** `_targetType`="BUFF_OWNER"
- **SwitchMode** `_modeIndex`=0 `_targetType`="TARGET"

---

### 吞日　`skchr_narant_3`

**技能描述（最高级）：**

> 每次攻击发射3个回旋投射物（每个造成相当于攻击力175%的物理伤害），投射物全部回收时娜仁图亚对周围8格内至多3名敌人造成一次相当于攻击力160%的物理伤害并使其停顿1秒


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WITH_TIME` | 随时间自动回复 |
| 初始 SP / 消耗 SP | 20 / 30 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 1 | 可存层数 |
| 释放方式 | `MANUAL` | 手动释放 |
| 技能形态 | `限时技能` | 持续 20 秒 |
| duration / durationType | 20 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `attack@atk_scale` | 1.75 |
| `atk_scale_aoe` | 1.6 |
| `sluggish` | 1 |
| `attack@aoe.max_target` | 3 |
| `cnt` | 3 |

#### 攻击范围

`rangeId = y-7`，15 格（direction=1）

> 该技能未指定自己的 `rangeId`，上图是干员**自身范围**。技能若扩大范围，会另有 `rangeId`。

```
■ ■ ■ ■ ■ 
■ ■ ■ ■ ■ 
■ ■ ■ ■ ■ 
```

#### 判定链

> 匹配方式：按命名规则匹配（层级 B）

**`narant_s_3`** ← 事件 `ON_BUFF_START`

- **ModifyBoomberangMaxCnt** `_targetType`="BUFF_OWNER"
- **IfElse** 
  - **CheckCharacterDefaultDirection** `_target`="BUFF_OWNER"
  - **SwitchMode** `_modeIndex`=5 `_targetType`="TARGET"
  - **SwitchMode** `_modeIndex`=4 `_targetType`="TARGET"

**`narant_s_3`** ← 事件 `ON_BUFF_DISABLE`

- **ModifyBoomberangMaxCnt** `_targetType`="BUFF_OWNER"
- **SwitchMode** `_modeIndex`=0 `_targetType`="TARGET"

**`narant_s_3[AOE]`** ← 事件 `ON_BUFF_START`

- **CheckContainsBuff** `_buffKeys`=["narant_s_3"] `_targetType`="BUFF_OWNER"
- **AOEDamage** `_targetType`="BUFF_OWNER" targetOptions(targetSide=ENEMY, targetMotion=ALL, targetCategory=DEFAULT, abnormalFlag=STUNNED)
- **CreateEffect** `_targetType`="BUFF_OWNER"
- **CreateBuff** buffKey=`narant_s3_audio_2` `lifeTimeType`=IMMEDIATELY

---

## 附：数据边界

| 项目 | 状态 |
|---|---|
| 属性 / 数值 / SP / 范围 / 抬手 | ✅ 明文可得 |
| buff 行为树 | ✅ 明文可得 |
| 技能 → 模板绑定 | ⚠️ 游戏只给 `prefabId`，真实绑定在不可解的 `.ab` 里；本文按命名规律 + `blackboard` 键名双向推断 |
| 动画资源本体 | ❌ 在 `.ab` 包内，不可解 |
| 抬手精度 | ✅ 1/30 秒，是动画事件时刻而非视觉起手帧 |
