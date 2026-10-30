# 圣聆初雪 — 技能判定说明

> 数据来源：明文 JSON（`character_table` / `skill_table` / `range_table` / `buff_template_data` / `bakemuzzledata`）。不含反汇编或二进制解析内容。

## 一、干员底子

| 项 | 值 |
|---|---|
| ID | `char_1046_sbell2` |
| 职业 | 术师 / `phalanx` |
| 星级 | 6 星 |
| 生命（精二满级） | 2058 |
| 攻击（精二满级） | 836 |
| 防御（精二满级） | 265 |
| 法抗 | 1500% |
| **攻击间隔 baseAttackTime** | **2 秒** |
| 攻速 attackSpeed | 100（100% = 无增减） |
| 阻挡 | 1 |
| 部署费用 | 24 |

**攻击间隔换算**（全干员通用）：

```
实际间隔 = baseAttackTime ÷ (attackSpeed / 100)
         = 2 ÷ 1.00 = 2.000 秒
```

## 二、抬手（攻击前摇）

⚠️ 本干员在 `bakemuzzledata` 中**没有 `OnAttack` 事件**，无法从明文数据得出抬手数值。

原始状态标记：`SKILL_ONLY`

该干员只有技能动画（无普攻动画），属于 `skill_only` / `no_attack` 类，抬手需实测。

## 三、技能逐层拆解

---

### 铃音吹雪　`skchr_sbell2_1`

**技能描述（最高级）：**

> 立即对范围内所有敌人造成相当于攻击力520%的法术伤害及3.5秒寒冷并将其中等力度地朝部署方向推动，之后积雪向前方地面扩散（最多向前扩散5格）
> 可充能2次


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WITH_TIME` | 随时间自动回复 |
| 初始 SP / 消耗 SP | 12 / 12 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 2 | 可存层数 |
| 释放方式 | `MANUAL` | 手动释放 |
| 技能形态 | `无限持续` | 开启后一直生效，直到手动关闭或条件结束 |
| duration / durationType | -1 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `atk_scale` | 5.2 |
| `force` | 1 |
| `cold` | 3.5 |
| `trig_cnt` | 5 |

#### 攻击范围

`rangeId = x-1`，13 格（direction=1）

> 该技能未指定自己的 `rangeId`，上图是干员**自身范围**。技能若扩大范围，会另有 `rangeId`。

```
· · ■ · · 
· ■ ■ ■ · 
■ ■ ■ ■ ■ 
· ■ ■ ■ · 
· · ■ · · 
```

#### 判定链

> 匹配方式：按命名规则匹配（层级 B）

**`sbell2_s1[push]`** ← 事件 `ON_BUFF_START`

- **CreateBuffById** 
- **CheckMotionMode** `_targetType`="BUFF_OWNER"
- **KnockBackWithCharacterDirection** `_target`="TARGET" `_source`="SOURCE"

**`sbell2_s1[snow_forward]`** ← 事件 `ON_BUFF_START`

- **ManageSbell2AttachListenerAbility** 

**`sbell2_s1[snow_forward]`** ← 事件 `ON_BUFF_TRIGGER`

- **ManageSbell2AttachListenerAbility** 

---

### 霜涛覆岭　`skchr_sbell2_2`

**技能描述（最高级）：**

> 每次攻击造成相当于攻击力380%的法术伤害，积雪超过5层时会向周围扩散一层（最多向外扩散20格），处于积雪上的地面敌人每秒受到攻击力20%的法术伤害，敌人离开积雪时获得5秒寒冷，积雪在目标点积累至5层时，使目标点变为冻结状态
> 持续时间无限，可主动关闭技能（期间可随时停止技能）


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WITH_TIME` | 随时间自动回复 |
| 初始 SP / 消耗 SP | 0 / 45 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 1 | 可存层数 |
| 释放方式 | `AUTO` | 自动释放 |
| 技能形态 | `无限持续` | 开启后一直生效，直到手动关闭或条件结束 |
| duration / durationType | -1 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `attack@atk_scale_s2` | 3.8 |
| `talent@s2_magic_scale` | 0.2 |
| `talent@max_cast_tile_count` | 20 |
| `talent@cold` | 5 |
| `talent@token_key` | 0 |

#### 攻击范围

`rangeId = x-1`，13 格（direction=1）

> 该技能未指定自己的 `rangeId`，上图是干员**自身范围**。技能若扩大范围，会另有 `rangeId`。

```
· · ■ · · 
· ■ ■ ■ · 
■ ■ ■ ■ ■ 
· ■ ■ ■ · 
· · ■ · · 
```

#### 判定链

> 匹配方式：按命名规则匹配（层级 B）

**`sbell2_s2[switch_back]`** ← 事件 `ON_BUFF_START`

- **FinishBuffsById** `_targetType`="BUFF_OWNER"

---

### 群山俯首　`skchr_sbell2_3`

**技能描述（最高级）：**

> 攻击范围扩大，立即诱导攻击范围内的所有敌人至自身周围的可达地面，持续10秒，积雪生成速度加快，攻击力+100%，攻击速度+30，攻击无视目标10点法术抗性，每次攻击造成相当于攻击力260%的法术伤害


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WITH_TIME` | 随时间自动回复 |
| 初始 SP / 消耗 SP | 42 / 50 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 1 | 可存层数 |
| 释放方式 | `MANUAL` | 手动释放 |
| 技能形态 | `限时技能` | 持续 35 秒 |
| duration / durationType | 35 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `atk` | 1 |
| `attack_speed` | 30 |
| `magic_resist_penetrate_fixed` | 10 |
| `attract_time` | 10 |
| `interval` | 1.5 |
| `attack@atk_scale_s3` | 2.6 |

#### 攻击范围

`rangeId = x-2`，21 格（direction=1）

```
· ■ ■ ■ · 
■ ■ ■ ■ ■ 
■ ■ ■ ■ ■ 
■ ■ ■ ■ ■ 
· ■ ■ ■ · 
```

#### 判定链

> 匹配方式：按命名规则匹配（层级 B）

**`sbell2_s3[attract_core]`** ← 事件 `ON_BUFF_START`

- **IfElse** 
  - **AddAttractToTargetNearestTileUseAbilitySelector** `_targetType`="BUFF_OWNER"
  - **PlayAudio** `_target`="BUFF_OWNER"
  - **CreateBuff** buffKey=`sbell2_s3[attract_effect]` `lifeTimeType`=INFINITY
  - **FinishBuff** 

**`sbell2_s3[snow_trigger]`** ← 事件 `ON_BUFF_TRIGGER`

- **TriggerAbility** `_targetType`="BUFF_OWNER"

**`sbell2_s3[snow_trigger]`** ← 事件 `ON_BUFF_START`

- **ManageSbell2AttachListenerAbility** 

**`sbell2_s3[snow_trigger]`** ← 事件 `ON_BUFF_FINISH`

- **ManageSbell2AttachListenerAbility** 

**`sbell2_s3[switch_mode]`** ← 事件 `ON_BUFF_START`

- **SwitchMode** `_modeIndex`=1 `_targetType`="TARGET"
- **CheckUnitAlive** 
- **CreateBuffUseAbilitySelector** buffKey=`sbell2_s3[attract_core]` templateKey=`sbell2_s3[attract_core]` `lifeTimeType`=LIMITED `_targetType`="TARGET"
- **CreateEffect** `_targetType`="BUFF_OWNER"

**`sbell2_s3[switch_mode]`** ← 事件 `ON_BUFF_FINISH`

- **SwitchMode** `_modeIndex`=0 `_targetType`="TARGET"

---

## 附：数据边界

| 项目 | 状态 |
|---|---|
| 属性 / 数值 / SP / 范围 / 抬手 | ✅ 明文可得 |
| buff 行为树 | ✅ 明文可得 |
| 技能 → 模板绑定 | ⚠️ 游戏只给 `prefabId`，真实绑定在不可解的 `.ab` 里；本文按命名规律 + `blackboard` 键名双向推断 |
| 动画资源本体 | ❌ 在 `.ab` 包内，不可解 |
| 抬手精度 | ✅ 1/30 秒，是动画事件时刻而非视觉起手帧 |
