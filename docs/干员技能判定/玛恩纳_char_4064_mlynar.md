# 玛恩纳 — 技能判定说明

> 数据来源：明文 JSON（`character_table` / `skill_table` / `range_table` / `buff_template_data` / `bakemuzzledata`）。不含反汇编或二进制解析内容。

## 一、干员底子

| 项 | 值 |
|---|---|
| ID | `char_4064_mlynar` |
| 职业 | 近卫 / `librator` |
| 星级 | 6 星 |
| 生命（精二满级） | 3906 |
| 攻击（精二满级） | 355 |
| 防御（精二满级） | 502 |
| 法抗 | 1500% |
| **攻击间隔 baseAttackTime** | **1.2 秒** |
| 攻速 attackSpeed | 100（100% = 无增减） |
| 阻挡 | 3 |
| 部署费用 | 12 |

**攻击间隔换算**（全干员通用）：

```
实际间隔 = baseAttackTime ÷ (attackSpeed / 100)
         = 1.2 ÷ 1.00 = 1.200 秒
```

## 二、抬手（攻击前摇）

⚠️ 本干员在 `bakemuzzledata` 中**没有 `OnAttack` 事件**，无法从明文数据得出抬手数值。

原始状态标记：`SKILL_ONLY`

该干员只有技能动画（无普攻动画），属于 `skill_only` / `no_attack` 类，抬手需实测。

## 三、技能逐层拆解

---

### 未声张的怒火　`skchr_mlynar_1`

**技能描述（最高级）：**

> 攻击造成相当于200%攻击力的物理伤害，防御力+60%


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
| `attack@atk_scale` | 2 |
| `def` | 0.6 |

#### 攻击范围

`rangeId = 1-2`，4 格（direction=1）

> 该技能未指定自己的 `rangeId`，上图是干员**自身范围**。技能若扩大范围，会另有 `rangeId`。

```
■ · 
■ ■ 
■ · 
```

#### 判定链

本技能**没有独立 buff 模板**。它属于「一段式数值强化」：开技能只改 `blackboard` 参数与动画，不挂 buff 节点树。

可核对的替代证据：

- 描述中的每个花括号参数都能在 `blackboard` 中找到对应值（见上表）

---

### 未宽解的悲哀　`skchr_mlynar_2`

**技能描述（最高级）：**

> 攻击间隔延长，攻击范围扩大，攻击造成相当于190%攻击力的二连击。
> 技能期间若击倒敌人，技能结束时特性效果不重置，可主动关闭（期间可随时停止技能）


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WITH_TIME` | 随时间自动回复 |
| 初始 SP / 消耗 SP | 10 / 25 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 1 | 可存层数 |
| 释放方式 | `MANUAL` | 手动释放 |
| 技能形态 | `限时技能` | 持续 20 秒 |
| duration / durationType | 20 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `attack@atk_scale` | 1.9 |
| `base_attack_time` | 0.3 |

#### 攻击范围

`rangeId = 2-3`，7 格（direction=1）

```
■ ■ · 
■ ■ ■ 
■ ■ · 
```

#### 判定链

> 匹配方式：按命名规则匹配（层级 B）

**`mlynar_s_2`** ← 事件 `ON_BUFF_START`

- **SwitchMode** `_modeIndex`=0 `_targetType`="TARGET"

**`mlynar_s_2`** ← 事件 `ON_BUFF_FINISH`

- **SwitchMode** `_modeIndex`=0 `_targetType`="TARGET"

**`mlynar_s_2`** ← 事件 `ON_TARGET_KILLED`

- **FilterAbilityName** 
- **IsCharacterOrTokenOrTrap** `_targetType`="TARGET"
- **IfNot** 
- **CheckContainsBuff** `_buffKeys`=["mlynar_s_2[killmark]"] `_targetType`="BUFF_OWNER"
- **IfNot** 
- **CreateBuff** buffKey=`mlynar_s_2[killmark]` `lifeTimeType`=INFINITY

---

### 未照耀的荣光　`skchr_mlynar_3`

**技能描述（最高级）：**

> 攻击范围扩大，特性提升至2倍（每击倒一名敌人时特性倍率-10%），攻击对5个目标造成相当于180%攻击力的物理伤害。范围内所有敌人受到卡西米尔干员攻击时额外附带玛恩纳12%攻击力的真实伤害


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WITH_TIME` | 随时间自动回复 |
| 初始 SP / 消耗 SP | 20 / 42 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 1 | 可存层数 |
| 释放方式 | `MANUAL` | 手动释放 |
| 技能形态 | `限时技能` | 持续 28 秒 |
| duration / durationType | 28 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `attack@atk_scale` | 1.8 |
| `atk_scale` | 0.12 |
| `attack@max_target` | 5 |
| `trait_up` | 2 |
| `per_kill_reduce` | -0.1 |

#### 攻击范围

`rangeId = 3-18`，14 格（direction=1）

```
■ ■ · · 
■ ■ ■ · 
■ ■ ■ ■ 
■ ■ ■ · 
■ ■ · · 
```

#### 判定链

> 匹配方式：按命名规则匹配（层级 B）

**`mlynar_s_3`** ← 事件 `ON_BUFF_START`

- **SwitchMode** `_modeIndex`=0 `_targetType`="TARGET"
- **AttributeModifierWithCertainBuffCount** `_targetType`="BUFF_OWNER"
- **FinishBuffsById** `_targetType`="BUFF_OWNER"
- **TriggerBuffsByKeys** `_buffKeys`=["mlynar_tr"] `_targetType`="BUFF_OWNER"

**`mlynar_s_3`** ← 事件 `ON_BUFF_FINISH`

- **SwitchMode** `_modeIndex`=0 `_targetType`="TARGET"

**`mlynar_s_3`** ← 事件 `ON_AFTER_ATTACK`

- **IfElse** 
  - **IsBlackboardZero** 
  - **CalculateBlackboardValueViaParams** 
  - **CalculateBlackboardValueViaParams** 
  - **ModifyBlackboard** 
  - **AttributeModifierWithBB** `_targetType`="BUFF_OWNER"

**`mlynar_s_3`** ← 事件 `ON_TARGET_KILLED`

- **FilterAbilityName** 
- **IsCharacterOrTokenOrTrap** `_targetType`="TARGET"
- **IfNot** 
- **AddBuffBlackboard** `_targetType`="BUFF_OWNER"

**`mlynar_s_3[aura]`** ← 事件 `ON_TAKE_DAMAGE`

- **CheckCharacterGroupTag** `_targetType`="MODIFIER_SOURCE"
- **IfElse** 
  - **FilterDamageModifer** `_source`="BUFF_OWNER"
  - **DamageViaAttr** `_targetType`="BUFF_OWNER"
  - **FilterDamageModifer** `_source`="BUFF_OWNER"
  - **DamageViaAttr** `_targetType`="BUFF_OWNER"

---

## 附：数据边界

| 项目 | 状态 |
|---|---|
| 属性 / 数值 / SP / 范围 / 抬手 | ✅ 明文可得 |
| buff 行为树 | ✅ 明文可得 |
| 技能 → 模板绑定 | ⚠️ 游戏只给 `prefabId`，真实绑定在不可解的 `.ab` 里；本文按命名规律 + `blackboard` 键名双向推断 |
| 动画资源本体 | ❌ 在 `.ab` 包内，不可解 |
| 抬手精度 | ✅ 1/30 秒，是动画事件时刻而非视觉起手帧 |
