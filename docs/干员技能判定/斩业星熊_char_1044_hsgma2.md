# 斩业星熊 — 技能判定说明

> 数据来源：明文 JSON（`character_table` / `skill_table` / `range_table` / `buff_template_data` / `bakemuzzledata`）。不含反汇编或二进制解析内容。

## 一、干员底子

| 项 | 值 |
|---|---|
| ID | `char_1044_hsgma2` |
| 职业 | 重装 / `artsprotector` |
| 星级 | 6 星 |
| 生命（精二满级） | 3551 |
| 攻击（精二满级） | 667 |
| 防御（精二满级） | 561 |
| 法抗 | 1500% |
| **攻击间隔 baseAttackTime** | **1.6 秒** |
| 攻速 attackSpeed | 100（100% = 无增减） |
| 阻挡 | 3 |
| 部署费用 | 26 |

**攻击间隔换算**（全干员通用）：

```
实际间隔 = baseAttackTime ÷ (attackSpeed / 100)
         = 1.6 ÷ 1.00 = 1.600 秒
```

## 二、抬手（攻击前摇）

来源：`bakemuzzledata/character/char_1044_hsgma2_*.json` → `bakedAnimDatas.<组>.bakedEvents.<动画名>.eventTime`，取事件 `OnAttack` 时刻。

| 场景 | 动画名 | 抬手 | 帧数(30fps) |
|---|---|---|---|
| **普通攻击** | `Attack` | **0.333333 秒** | 10 帧 |

> 占攻击间隔 20.8%（0.333333 秒 / 1.6 秒）。开技能不会让抬手变快。

| 技能动画 | `Skill_2_Begin` | 0.133333 秒 | 4 帧 |
| 技能动画 | `Skill_2_Loop` | 0.333333 秒 | 10 帧 |
| 技能动画 | `Skill_3_Loop_A` | 0.5 秒 | 15 帧 |
| 技能动画 | `Skill_3_Loop_B` | 0.5 秒 | 15 帧 |
| 技能动画 | `Skill_3_Loop_C` | 0.5 秒 | 15 帧 |


## 三、技能逐层拆解

---

### 恶业苦果　`skchr_hsgma2_1`

**技能描述（最高级）：**

> 攻击力+70%，防御力+70%，每次受到攻击时对目标造成相当于斩业星熊攻击力175%的法术伤害
> 持续时间无限


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WHEN_TAKEN_DAMAGE` | 受击回复 |
| 初始 SP / 消耗 SP | 0 / 15 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 1 | 可存层数 |
| 释放方式 | `AUTO` | 自动释放 |
| 技能形态 | `无限持续` | 开启后一直生效，直到手动关闭或条件结束 |
| duration / durationType | -1 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `atk` | 0.7 |
| `def` | 0.7 |
| `atk_scale` | 1.75 |

#### 攻击范围

`rangeId = 1-1`，2 格（direction=1）

> 该技能未指定自己的 `rangeId`，上图是干员**自身范围**。技能若扩大范围，会另有 `rangeId`。

```
■ ■ 
```

#### 判定链

> 匹配方式：按命名规则匹配（层级 B）

**`hsgma2_s_1`** ← 事件 `ON_TAKE_DAMAGE`

- **IfTargetSide** `_targetType`="MODIFIER_SOURCE"
- **AdvancedApplyDamage** `_targetType`="MODIFIER_SOURCE"
- **PlayAudio** `_target`="BUFF_OWNER"
- **CreateEffect** `_targetType`="MODIFIER_SOURCE"

---

### 无始无明　`skchr_hsgma2_2`

**技能描述（最高级）：**

> 投出盾牌并以攻击力90%的三连击攻击所有阻挡的敌人，盾牌会环绕斩业星熊飞行一圈；盾牌碰到敌人时使目标停顿，每0.5秒对其造成攻击力130%的法术伤害，自身回复盾牌造成伤害15%的生命


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WHEN_ATTACK` | 每次攻击回复 |
| 初始 SP / 消耗 SP | 0 / 6 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 1 | 可存层数 |
| 释放方式 | `AUTO` | 自动释放 |
| 技能形态 | `无限持续` | 开启后一直生效，直到手动关闭或条件结束 |
| duration / durationType | -1 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `attack@atk_scale` | 0.9 |
| `shield_atk_scale` | 1.3 |
| `sluggish` | 1 |
| `interval` | 0.5 |
| `heal_ratio` | 0.15 |

#### 攻击范围

`rangeId = 1-1`，2 格（direction=1）

> 该技能未指定自己的 `rangeId`，上图是干员**自身范围**。技能若扩大范围，会另有 `rangeId`。

```
■ ■ 
```

#### 判定链

> 匹配方式：按命名规则匹配（层级 B）

**`hsgma2_s_2[clear]`** ← 事件 `ON_BUFF_START`

- **FinishBuffsById** `_targetType`="BUFF_OWNER"

**`hsgma2_s_2[projectile]`** ← 事件 `ON_BUFF_TRIGGER`

- **CreateBuffById** 
- **AdvancedApplyDamage** `_targetType`="TARGET"
- **CreateEffect** `_targetType`="TARGET"
- **PlayAudio** `_target`="TARGET"
- **CalculateBlackboardValueViaParams** 
- **FixedValueHeal** `_targetType`="BUFF_SOURCE"

---

### 地狱变相　`skchr_hsgma2_3`

**技能描述（最高级）：**

> 攻击范围扩大，生命上限+100%，攻击力+230%，以二连击攻击最多3名敌人；主动关闭技能后11秒内保留技能加成且不会被击倒，攻击变为四连击，承担攻击范围内我方干员受到的致命伤害，11秒后强制退出战场
> 可主动关闭（期间可随时停止技能）


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WITH_TIME` | 随时间自动回复 |
| 初始 SP / 消耗 SP | 37 / 45 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 1 | 可存层数 |
| 释放方式 | `MANUAL` | 手动释放 |
| 技能形态 | `限时技能` | 持续 32 秒 |
| duration / durationType | 32 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `max_hp` | 1 |
| `atk` | 2.3 |
| `attack@max_target` | 3 |
| `before_dead_duration` | 11 |

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

**`hsgma2_s_3`** ← 事件 `ON_BUFF_START`

- **SwitchMode** `_modeIndex`=1 `_targetType`="BUFF_OWNER"

**`hsgma2_s_3`** ← 事件 `ON_BUFF_FINISH`

- **CheckUnitCurrentMode** `_targetType`="BUFF_OWNER"
- **IfNot** 
- **SwitchMode** `_modeIndex`=0 `_targetType`="BUFF_OWNER"
- **FinishBuffsById** `_targetType`="BUFF_OWNER"

**`hsgma2_s_3[ally]`** ← 事件 `ON_TAKE_DAMAGE`

- **AssignModifierValueIntoBlackboard** 
- **ModifierScaleUp** 
- **CalculateBlackboardValueViaParams** 
- **FixedValueDamage** `_targetType`="BUFF_SOURCE"

**`hsgma2_s_3[ally]`** ← 事件 `ON_BUFF_START`

- **AssignValueToBB** 
- **CalculateBlackboardValueViaParams** 

**`hsgma2_s_3[attack_cnt]`** ← 事件 `ON_BUFF_START`

- **FilterByBuffStackCount** `_condType`="GE" `_targetType`="BUFF_OWNER"
- **FinishBuffsById** `_targetType`="BUFF_OWNER"

**`hsgma2_s_3[before_dead]`** ← 事件 `ON_BUFF_FINISH`

- **PlayAudio** `_target`="BUFF_OWNER"
- **Withdraw** 

**`hsgma2_s_3[before_dead]`** ← 事件 `ON_BUFF_START`

- **PlayAudio** `_target`="BUFF_OWNER"
- **PlayAudio** `_target`="BUFF_OWNER"

**`hsgma2_s_3[before_dead][aura]`** ← 事件 `ON_TAKE_DAMAGE`

- **AssignOverflowDamageToBlackboard** `_target`="BUFF_OWNER"
- **CreateBuff** buffKey=`hsgma2_s_3[before_dead][aura][ref]` templateKey=`hsgma2_s_3[before_dead][aura][ref]` `lifeTimeType`=IMMEDIATELY

**`hsgma2_s_3[before_dead][aura][ref]`** ← 事件 `ON_BUFF_START`

- **FixedValueDamage** `_targetType`="BUFF_OWNER"

**`hsgma2_s_3[finish]`** ← 事件 `ON_BUFF_START`

- **SwitchMode** `_modeIndex`=4 `_targetType`="BUFF_OWNER"

**`hsgma2_s_3[heal]`** ← 事件 `ON_BUFF_START`

- **HealViaMaxHpRatio** 

**`hsgma2_s_3[override]`** ← 事件 `ON_AFTER_OUTPUT_DAMAGE`

- **CheckContainsBuff** `_buffKeys`=["hsgma2_s_3"] `_targetType`="BUFF_OWNER"
- **IfNot** 
- **AssignModifierRealDeltaToBB** 
- **CalculateBlackboardValueViaParams** 
- **FixedValueHeal** `_targetType`="BUFF_OWNER"

**`hsgma2_s_3[override]`** ← 事件 `ON_BUFF_START`

- **AssignBuffRemainingTimeIntoBlackboard** `_targetType`="BUFF_OWNER"
- **FinishBuffsById** `_targetType`="BUFF_OWNER"

**`hsgma2_s_3[override]`** ← 事件 `ON_BUFF_DISABLE`

- **CreateBuff** buffKey=`hsgma2_s_3` templateKey=`hsgma2_s_3` 属性修改=[MAX_HP MULTIPLIER blackboard, ATK MULTIPLIER blackboard] `overrideType`=EXTEND `lifeTimeType`=LIMITED

**`hsgma2_s_3[pause_checker]`** ← 事件 `ON_BUFF_TRIGGER`

- **IfElse** 
  - **CheckIfAtMinusHpState** `_targetType`="TARGET"
  - **PauseAbility** 
  - **AssignValueToBB** 
  - **ModifyAttackMaxTarget** `_modeIndex`=2 `_targetType`="BUFF_OWNER"
  - **PauseAbility** 
  - **AssignValueToBB** 
  - **ModifyAttackMaxTarget** `_modeIndex`=2 `_targetType`="BUFF_OWNER"

---

## 附：数据边界

| 项目 | 状态 |
|---|---|
| 属性 / 数值 / SP / 范围 / 抬手 | ✅ 明文可得 |
| buff 行为树 | ✅ 明文可得 |
| 技能 → 模板绑定 | ⚠️ 游戏只给 `prefabId`，真实绑定在不可解的 `.ab` 里；本文按命名规律 + `blackboard` 键名双向推断 |
| 动画资源本体 | ❌ 在 `.ab` 包内，不可解 |
| 抬手精度 | ✅ 1/30 秒，是动画事件时刻而非视觉起手帧 |
