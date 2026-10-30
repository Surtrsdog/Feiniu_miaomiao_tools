# 三角初华 — 技能判定说明

> 数据来源：明文 JSON（`character_table` / `skill_table` / `range_table` / `buff_template_data` / `bakemuzzledata`）。不含反汇编或二进制解析内容。

## 一、干员底子

| 项 | 值 |
|---|---|
| ID | `char_4184_dolris` |
| 职业 | 辅助 / `bard` |
| 星级 | 5 星 |
| 生命（精二满级） | 1410 |
| 攻击（精二满级） | 309 |
| 防御（精二满级） | 253 |
| 法抗 | 0% |
| **攻击间隔 baseAttackTime** | **1.3 秒** |
| 攻速 attackSpeed | 100（100% = 无增减） |
| 阻挡 | 1 |
| 部署费用 | 7 |

**攻击间隔换算**（全干员通用）：

```
实际间隔 = baseAttackTime ÷ (attackSpeed / 100)
         = 1.3 ÷ 1.00 = 1.300 秒
```

## 二、抬手（攻击前摇）

⚠️ 本干员在 `bakemuzzledata` 中**没有 `OnAttack` 事件**，无法从明文数据得出抬手数值。

原始状态标记：`NO_ATTACK`

该干员只有技能动画（无普攻动画），属于 `skill_only` / `no_attack` 类，抬手需实测。

## 三、技能逐层拆解

---

### 我思念的　`skchr_dolris_1`

**技能描述（最高级）：**

> 攻击范围扩大，攻击范围内所有友方单位获得相当于三角初华55%攻击力与防御力的鼓舞效果，目标受到伤害时三角初华会为其治疗100点生命


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WITH_TIME` | 随时间自动回复 |
| 初始 SP / 消耗 SP | 25 / 35 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 1 | 可存层数 |
| 释放方式 | `MANUAL` | 手动释放 |
| 技能形态 | `限时技能` | 持续 30 秒 |
| duration / durationType | 30 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `attack@atk` | 0.55 |
| `attack@def` | 0.55 |
| `attack@heal_value_s1` | 100 |

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

**`dolris_s_1[audio]`** ← 事件 `ON_BUFF_START`

- **IsInFever** 
- **IfNot** 
- **IsFeverFull** 
- **IfNot** 
- **PlayAudio** `_target`="BUFF_OWNER"

**`dolris_s_1[buff]`** ← 事件 `ON_TAKE_DAMAGE`

- **CreateBuffUseAbilitySelector** buffKey=`dolris_s_1[heal]` templateKey=`instant_heal` `lifeTimeType`=LIMITED `_targetType`="BUFF_SOURCE"
- **IfNot** 
- **FixedValueHeal** `_targetType`="TARGET"
- **CreateEffect** `_targetType`="TARGET"

**`dolris_s_1[buff]`** ← 事件 `ON_BUFF_START`

- **AssignValueToBB** 

---

### 我悲悯的　`skchr_dolris_2`

**技能描述（最高级）：**

> 技能期间特性不再恢复生命，每0.3秒对攻击范围内随机一名敌人造成相当于攻击力100%的法术伤害并为一名友方治疗相当于攻击力25%的生命；攻击范围内所有其他友方单位获得相当于三角初华100%攻击力的鼓舞效果


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WITH_TIME` | 随时间自动回复 |
| 初始 SP / 消耗 SP | 20 / 30 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 1 | 可存层数 |
| 释放方式 | `MANUAL` | 手动释放 |
| 技能形态 | `限时技能` | 持续 12 秒 |
| duration / durationType | 12 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `attack@atk` | 1 |
| `interval` | 0.3 |
| `attack@atk_scale` | 1 |
| `attack@heal_scale` | 0.25 |

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

**`dolris_s_2[audio]`** ← 事件 `ON_BUFF_START`

- **IsInFever** 
- **IfNot** 
- **IsFeverFull** 
- **IfNot** 
- **PlayAudio** `_target`="BUFF_OWNER"

**`dolris_s_2[buff]`** ← 事件 `ON_BUFF_TRIGGER`

- **TriggerAbility** `_targetType`="BUFF_OWNER"
- **TriggerAbility** `_targetType`="BUFF_OWNER"

---

## 附：数据边界

| 项目 | 状态 |
|---|---|
| 属性 / 数值 / SP / 范围 / 抬手 | ✅ 明文可得 |
| buff 行为树 | ✅ 明文可得 |
| 技能 → 模板绑定 | ⚠️ 游戏只给 `prefabId`，真实绑定在不可解的 `.ab` 里；本文按命名规律 + `blackboard` 键名双向推断 |
| 动画资源本体 | ❌ 在 `.ab` 包内，不可解 |
| 抬手精度 | ✅ 1/30 秒，是动画事件时刻而非视觉起手帧 |
