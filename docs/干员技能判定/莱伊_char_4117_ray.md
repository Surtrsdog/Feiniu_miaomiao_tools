# 莱伊 — 技能判定说明

> 数据来源：明文 JSON（`character_table` / `skill_table` / `range_table` / `buff_template_data` / `bakemuzzledata`）。不含反汇编或二进制解析内容。

## 一、干员底子

| 项 | 值 |
|---|---|
| ID | `char_4117_ray` |
| 职业 | 狙击 / `hunter` |
| 星级 | 6 星 |
| 生命（精二满级） | 1933 |
| 攻击（精二满级） | 1072 |
| 防御（精二满级） | 228 |
| 法抗 | 0% |
| **攻击间隔 baseAttackTime** | **1.6 秒** |
| 攻速 attackSpeed | 100（100% = 无增减） |
| 阻挡 | 1 |
| 部署费用 | 21 |

**攻击间隔换算**（全干员通用）：

```
实际间隔 = baseAttackTime ÷ (attackSpeed / 100)
         = 1.6 ÷ 1.00 = 1.600 秒
```

## 二、抬手（攻击前摇）

来源：`bakemuzzledata/character/char_4117_ray_*.json` → `bakedAnimDatas.<组>.bakedEvents.<动画名>.eventTime`，取事件 `OnAttack` 时刻。

| 场景 | 动画名 | 抬手 | 帧数(30fps) |
|---|---|---|---|
| **普通攻击** | `Attack_Loop` | **0.366667 秒** | 11 帧 |

> 占攻击间隔 22.9%（0.366667 秒 / 1.6 秒）。开技能不会让抬手变快。

| 技能动画 | `Skill_1_Loop` | 0.266667 秒 | 8 帧 |
| 技能动画 | `Skill_2_Loop` | 0.4 秒 | 12 帧 |
| 技能动画 | `Skill_3_Loop` | 0.3 秒 | 9 帧 |
| 技能动画 | `Skill_Down_1_Loop` | 0.266667 秒 | 8 帧 |
| 技能动画 | `Skill_Down_2_Loop` | 0.4 秒 | 12 帧 |
| 技能动画 | `Skill_Down_3_Loop` | 0.3 秒 | 9 帧 |


## 三、技能逐层拆解

---

### 脱身矢　`skchr_ray_1`

**技能描述（最高级）：**

> 立即用额外特殊子弹攻击目标，造成相当于攻击力450%的物理伤害并将其较大力地推开，若将其击倒则使下次装填额外加装2发子弹
> 可充能2次


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WITH_TIME` | 随时间自动回复 |
| 初始 SP / 消耗 SP | 10 / 10 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 2 | 可存层数 |
| 释放方式 | `MANUAL` | 手动释放 |
| 技能形态 | `无限持续` | 开启后一直生效，直到手动关闭或条件结束 |
| duration / durationType | -1 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `atk_scale` | 4.5 |
| `cnt` | 2 |
| `force` | 2 |

#### 攻击范围

`rangeId = 4-9`，9 格（direction=1）

> 该技能未指定自己的 `rangeId`，上图是干员**自身范围**。技能若扩大范围，会另有 `rangeId`。

```
■ ■ · · · 
■ ■ ■ ■ ■ 
■ ■ · · · 
```

#### 判定链

> 匹配方式：按命名规则匹配（层级 B）

**`ray_s_1[bullet]`** ← 事件 `ON_BUFF_START`

- **CalculateTraitAbilityBlackboard** `_targetType`="BUFF_OWNER"

**`ray_s_1[fallkill]`** ← 事件 `ON_BEFORE_FALLDOWN`

- **CalculateTraitAbilityBlackboard** `_targetType`="BUFF_SOURCE"

**`ray_s_1[fallkill]`** ← 事件 `ON_BEFORE_EXIT_UNBALANCED_STATE`

- **FinishBuff** 

**`ray_s_1[kill_add_bullet]`** ← 事件 `ON_TARGET_KILLED`

- **FilterAbilityFamily** 
- **CreateBuff** buffKey=`ray_s_1[bullet]` templateKey=`ray_s_1[bullet]` `overrideType`=UNIQUE `lifeTimeType`=IMMEDIATELY

**`ray_s_1[konckback]`** ← 事件 `ON_BUFF_START`

- **Knockback** `_target`="TARGET" `_source`="SOURCE"
- **CheckEnemyUnbalanced** `_targetType`="BUFF_OWNER"
- **CreateBuff** buffKey=`ray_s_1[fallkill]` templateKey=`ray_s_1[fallkill]` `lifeTimeType`=INFINITY

---

### 广域警觉　`skchr_ray_2`

**技能描述（最高级）：**

> 被动效果：沙地兽撤退时回收命中该区域的子弹
> 自动开启：攻击范围扩大，攻击力+120%，沙地兽的再部署时间-40%
> 持续时间无限


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WHEN_ATTACK` | 每次攻击回复 |
| 初始 SP / 消耗 SP | 0 / 16 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 1 | 可存层数 |
| 释放方式 | `AUTO` | 自动释放 |
| 技能形态 | `无限持续` | 开启后一直生效，直到手动关闭或条件结束 |
| duration / durationType | -1 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `atk` | 1.2 |
| `respawn_time` | -0.4 |

#### 攻击范围

`rangeId = 4-10`，11 格（direction=1）

```
■ · · · · 
■ ■ · · · 
■ ■ ■ ■ ■ 
■ ■ · · · 
■ · · · · 
```

#### 判定链

> 匹配方式：按命名规则匹配（层级 B）

**`ray_s_2[colloct]`** ← 事件 `ON_BUFF_START`

- **CheckContainsBuff** `_buffKeys`=["ray_sndbst_aura"] `_targetType`="BUFF_OWNER"

**`ray_s_2[deck]`** ← 事件 `ON_BUFF_START`

- **CreateCardBuffToMyToken** 

**`ray_s_2[down_mode]`** ← 事件 `ON_BUFF_START`

- **CheckCharacterDefaultDirection** `_target`="BUFF_OWNER"
- **SwitchMode** `_modeIndex`=2 `_targetType`="TARGET"
- **FinishBuff** 

**`ray_s_2[mode]`** ← 事件 `ON_BUFF_START`

- **IfElse** 
  - **CheckCharacterDefaultDirection** `_target`="TARGET"
  - **SwitchMode** `_modeIndex`=2 `_targetType`="TARGET"
  - **SwitchMode** `_modeIndex`=1 `_targetType`="TARGET"

---

### “得见光芒”　`skchr_ray_3`

**技能描述（最高级）：**

> 立即停止攻击直至子弹装满，装填间隔大幅缩短，攻击范围扩大，攻击造成相当于攻击力330%的物理伤害并使目标束缚2秒
> 技能期间若击倒敌人，技能结束时获得10点技力


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WITH_TIME` | 随时间自动回复 |
| 初始 SP / 消耗 SP | 20 / 30 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 1 | 可存层数 |
| 释放方式 | `MANUAL` | 手动释放 |
| 技能形态 | `限时技能` | 持续 16 秒 |
| duration / durationType | 16 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `reload_interval` | -1.2 |
| `attack@atk_scale` | 3.3 |
| `attack@unmove_duration` | 2 |
| `sp` | 10 |

#### 攻击范围

`rangeId = 3-8`，13 格（direction=1）

```
■ ■ ■ ■ · 
■ ■ ■ ■ ■ 
■ ■ ■ ■ · 
```

#### 判定链

> 匹配方式：按命名规则匹配（层级 B）

**`ray_s_3[check_full]`** ← 事件 `ON_BUFF_START`

- **CheckTraitAbilityBlackboard** `_targetType`="BUFF_OWNER"
- **IfElse** 
  - **CheckCharacterDefaultDirection** `_target`="TARGET"
  - **SwitchMode** `_modeIndex`=5 `_targetType`="TARGET"
  - **SwitchMode** `_modeIndex`=4 `_targetType`="TARGET"

**`ray_s_3[mode]`** ← 事件 `ON_BUFF_START`

- **IfElse** 
  - **CheckTraitAbilityBlackboard** `_targetType`="BUFF_OWNER"
  - **IfElse** 
    - **CheckCharacterDefaultDirection** `_target`="TARGET"
    - **SwitchMode** `_modeIndex`=5 `_targetType`="TARGET"
    - **SwitchMode** `_modeIndex`=4 `_targetType`="TARGET"
  - **IfElse** 
    - **CheckCharacterDefaultDirection** `_target`="TARGET"
    - **SwitchMode** `_modeIndex`=6 `_targetType`="TARGET"
    - **SwitchMode** `_modeIndex`=3 `_targetType`="TARGET"

**`ray_s_3[mode]`** ← 事件 `ON_BUFF_FINISH`

- **SwitchMode** `_modeIndex`=0 `_targetType`="TARGET"

**`ray_s_3[reload]`** ← 事件 `ON_BUFF_FINISH`

- **CalculateTraitAbilityBlackboard** `_targetType`="BUFF_OWNER"

**`ray_s_3[reload]`** ← 事件 `ON_BUFF_START`

- **CalculateTraitAbilityBlackboard** `_targetType`="BUFF_OWNER"

**`ray_s_3[sp]`** ← 事件 `ON_BUFF_START`

- **FinishBuffsById** `_targetType`="BUFF_OWNER"

**`ray_s_3[sp]`** ← 事件 `ON_TARGET_KILLED`

- **CheckContainsBuff** `_buffKeys`=["ray_s_3[mark]"] `_targetType`="BUFF_OWNER"
- **IfNot** 
- **CreateBuff** buffKey=`ray_s_3[mark]` `lifeTimeType`=INFINITY

**`ray_s_3[sp]`** ← 事件 `ON_BUFF_FINISH`

- **CheckContainsBuff** `_buffKeys`=["ray_s_3[mark]"] `_targetType`="BUFF_OWNER"
- **ModifySp** `_targetType`="BUFF_OWNER" `_forceFlag`=True
- **FinishBuffsById** `_targetType`="BUFF_OWNER"

**`ray_s_3[unmove_effect]`** ← 事件 `ON_BUFF_START`

- **CheckAbnormalImmune** `_targetType`="BUFF_OWNER"
- **IfNot** 
- **CreateBuff** buffKey=`ray_s_3[effect]` `lifeTimeType`=INFINITY

---

## 附：数据边界

| 项目 | 状态 |
|---|---|
| 属性 / 数值 / SP / 范围 / 抬手 | ✅ 明文可得 |
| buff 行为树 | ✅ 明文可得 |
| 技能 → 模板绑定 | ⚠️ 游戏只给 `prefabId`，真实绑定在不可解的 `.ab` 里；本文按命名规律 + `blackboard` 键名双向推断 |
| 动画资源本体 | ❌ 在 `.ab` 包内，不可解 |
| 抬手精度 | ✅ 1/30 秒，是动画事件时刻而非视觉起手帧 |
