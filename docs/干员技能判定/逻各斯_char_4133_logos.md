# 逻各斯 — 技能判定说明

> 数据来源：明文 JSON（`character_table` / `skill_table` / `range_table` / `buff_template_data` / `bakemuzzledata`）。不含反汇编或二进制解析内容。

## 一、干员底子

| 项 | 值 |
|---|---|
| ID | `char_4133_logos` |
| 职业 | 术师 / `corecaster` |
| 星级 | 6 星 |
| 生命（精二满级） | 1663 |
| 攻击（精二满级） | 671 |
| 防御（精二满级） | 119 |
| 法抗 | 2000% |
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

来源：`bakemuzzledata/character/char_4133_logos_*.json` → `bakedAnimDatas.<组>.bakedEvents.<动画名>.eventTime`，取事件 `OnAttack` 时刻。

| 场景 | 动画名 | 抬手 | 帧数(30fps) |
|---|---|---|---|
| **普通攻击** | `Attack_1` | **0.5 秒** | 15 帧 |

> 占攻击间隔 31.2%（0.5 秒 / 1.6 秒）。开技能不会让抬手变快。

| 技能动画 | `Skill_1_Attack` | 0.433333 秒 | 13 帧 |
| 技能动画 | `Skill_3_Attack` | 0.666667 秒 | 20 帧 |
| 技能动画 | `Skill_3_End` | 0.333333 秒 | 10 帧 |


## 三、技能逐层拆解

---

### 殁亡　`skchr_logos_1`

**技能描述（最高级）：**

> 攻击范围扩大，攻击力+100%，使攻击范围内生命值低于逻各斯攻击力150%的敌人立刻倒下、并对另一个随机目标造成与倒下单位生命值相等的法术伤害
> 持续时间无限


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WITH_TIME` | 随时间自动回复 |
| 初始 SP / 消耗 SP | 0 / 60 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 1 | 可存层数 |
| 释放方式 | `AUTO` | 自动释放 |
| 技能形态 | `无限持续` | 开启后一直生效，直到手动关闭或条件结束 |
| duration / durationType | -1 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `atk` | 1 |
| `attack@kill_atk_scale` | 1.5 |
| `attack@kill_damage` | 9999999 |

#### 攻击范围

`rangeId = 3-3`，12 格（direction=1）

```
■ ■ ■ ■ 
■ ■ ■ ■ 
■ ■ ■ ■ 
```

#### 判定链

> 匹配方式：按命名规则匹配（层级 B）

**`logos_s_1`** ← 事件 `ON_BUFF_TRIGGER`

- **IfTarget** `_targetType`="BUFF_OWNER"
- **AssignAttributeAsDynamicVarToBB** `_targetType`="BUFF_SOURCE"
- **ModifyBlackboard** 
- **AlwaysNext** 
- **FilterByTargetHp** `_condType`="LT" `_targetType`="BUFF_OWNER"
- **SaveHpToDynamicVar** `_targetType`="BUFF_OWNER"
- **AlwaysNext** 
- **NoSourceDamage** 
- **AlwaysNext** 
- **PlayAudio** `_target`="BUFF_OWNER"
- **AlwaysNext** 
- **CreateEffect** `_targetType`="BUFF_OWNER"
- **AlwaysNext** 
- **FinishBuff** 
- **CheckUnitAlive** 
- **IfNot** 
- …（共 20 个节点，已截断）

---

### 提喻　`skchr_logos_2`

**技能描述（最高级）：**

> 法术抗性+70，攻击改为锁定一个目标对其每0.5秒造成一次相当于攻击力75%的法术伤害，对相同目标的伤害逐渐提高至3倍并使其移动速度逐渐降低至40%(锁定5秒后达到上限)，被打断或目标倒下时重新索敌且效果重置


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
| `magic_resistance` | 70 |
| `attack@cooldown` | 0.5 |
| `attack@atk_scale_base` | 0.75 |
| `attack@atk_scale_delta` | 0.15 |
| `attack@move_speed` | -0.06 |
| `attack@max_stack_cnt` | 10 |

#### 攻击范围

`rangeId = 3-1`，10 格（direction=1）

> 该技能未指定自己的 `rangeId`，上图是干员**自身范围**。技能若扩大范围，会另有 `rangeId`。

```
■ ■ ■ · 
■ ■ ■ ■ 
■ ■ ■ · 
```

#### 判定链

> 匹配方式：按命名规则匹配（层级 B）

**`logos_s_2`** ← 事件 `ON_BUFF_START`

- **ResetBuffAbilityAtkScaleWithBuffCnt** `_targetType`="BUFF_OWNER"

**`logos_s_2[effect]`** ← 事件 `ON_BUFF_ENABLE`

- **CreateBuff** buffKey=`logos_s_2[effect_1]` `lifeTimeType`=INFINITY
- **CreateBuff** buffKey=`logos_s_2[effect_2]` `lifeTimeType`=INFINITY

**`logos_s_2[effect]`** ← 事件 `ON_BUFF_DISABLE`

- **FinishDerivedBuff** 

**`logos_s_2[focus]`** ← 事件 `ON_BUFF_DISABLE`

- **FinishDerivedBuff** 

**`logos_s_2[focus]`** ← 事件 `ON_BUFF_TRIGGER`

- **CheckUnitInAttackState** 
- **FinishDerivedBuff** 

**`logos_s_2[lock]`** ← 事件 `ON_BUFF_ENABLE`

- **CreateLineEffect** `_targetType`="BUFF_OWNER"
- **AlwaysNext** 
- **AttachAsDerivedBuffById** 
- **AlwaysNext** 
- **CreateBuff** buffKey=`logos_s_2[lock][audio]` `lifeTimeType`=INFINITY

**`logos_s_2[lock]`** ← 事件 `ON_BUFF_START`

- **CheckUnitAlive** 
- **IfNot** 
- **FinishBuff** 

---

### 延异视阈　`skchr_logos_3`

**技能描述（最高级）：**

> 攻击范围扩大，攻击力+300%，同时攻击4个目标，使攻击范围内敌方子弹的飞行速度大幅降低、并在技能结束时将其全部清除


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WITH_TIME` | 随时间自动回复 |
| 初始 SP / 消耗 SP | 30 / 45 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 1 | 可存层数 |
| 释放方式 | `MANUAL` | 手动释放 |
| 技能形态 | `限时技能` | 持续 30 秒 |
| duration / durationType | 30 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `atk` | 3 |
| `attack@max_target` | 4 |
| `projectile_move_scale` | 0.05 |

#### 攻击范围

`rangeId = 3-4`，18 格（direction=1）

```
■ ■ ■ · 
■ ■ ■ ■ 
■ ■ ■ ■ 
■ ■ ■ ■ 
■ ■ ■ · 
```

#### 判定链

> 匹配方式：按命名规则匹配（层级 B）

**`logos_s_3`** ← 事件 `ON_BUFF_START`

- **SwitchMode** `_modeIndex`=3 `_targetType`="TARGET"
- **TriggerAbility** `_targetType`="BUFF_OWNER"

**`logos_s_3`** ← 事件 `ON_BUFF_FINISH`

- **IfElse** 
  - **CheckCanUseAtkOrCbt** `_targetType`="BUFF_OWNER"
  - **SwitchMode** `_modeIndex`=4 `_targetType`="TARGET"
  - **InterruptAbility** 
  - **AlwaysNext** 
  - **SwitchMode** `_modeIndex`=0 `_targetType`="TARGET"

**`logos_s_3[end]`** ← 事件 `ON_BUFF_FINISH`

- **InterruptAbility** 
- **AlwaysNext** 
- **SwitchMode** `_modeIndex`=0 `_targetType`="TARGET"

**`logos_s_3[end]`** ← 事件 `ON_ABILITY_SPELL_ON`

- **FilterAbilityFamily** 
- **InterruptAbility** 

**`logos_s_3[force_end]`** ← 事件 `ON_BUFF_TRIGGER`

- **CheckContainsBuff** `_buffKeys`=["logos_s_3[end]"] `_targetType`="BUFF_OWNER"
- **IfNot** 
- **CheckCanUseAtkOrCbt** `_targetType`="BUFF_OWNER"
- **IfNot** 
- **CreateBuff** buffKey=`logos_s_3[end]` templateKey=`logos_s_3[end]` `lifeTimeType`=IMMEDIATELY

---

## 附：数据边界

| 项目 | 状态 |
|---|---|
| 属性 / 数值 / SP / 范围 / 抬手 | ✅ 明文可得 |
| buff 行为树 | ✅ 明文可得 |
| 技能 → 模板绑定 | ⚠️ 游戏只给 `prefabId`，真实绑定在不可解的 `.ab` 里；本文按命名规律 + `blackboard` 键名双向推断 |
| 动画资源本体 | ❌ 在 `.ab` 包内，不可解 |
| 抬手精度 | ✅ 1/30 秒，是动画事件时刻而非视觉起手帧 |
