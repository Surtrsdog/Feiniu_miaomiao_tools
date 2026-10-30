# 贝洛内 — 技能判定说明

> 数据来源：明文 JSON（`character_table` / `skill_table` / `range_table` / `buff_template_data` / `bakemuzzledata`）。不含反汇编或二进制解析内容。

## 一、干员底子

| 项 | 值 |
|---|---|
| ID | `char_4037_demetr` |
| 职业 | 近卫 / `fighter` |
| 星级 | 6 星 |
| 生命（精二满级） | 2625 |
| 攻击（精二满级） | 605 |
| 防御（精二满级） | 355 |
| 法抗 | 0% |
| **攻击间隔 baseAttackTime** | **0.78 秒** |
| 攻速 attackSpeed | 100（100% = 无增减） |
| 阻挡 | 1 |
| 部署费用 | 11 |

**攻击间隔换算**（全干员通用）：

```
实际间隔 = baseAttackTime ÷ (attackSpeed / 100)
         = 0.78 ÷ 1.00 = 0.780 秒
```

## 二、抬手（攻击前摇）

来源：`bakemuzzledata/character/char_4037_demetr_*.json` → `bakedAnimDatas.<组>.bakedEvents.<动画名>.eventTime`，取事件 `OnAttack` 时刻。

| 场景 | 动画名 | 抬手 | 帧数(30fps) |
|---|---|---|---|
| **普通攻击** | `Attack_A` | **0.333333 秒** | 10 帧 |

> 占攻击间隔 42.7%（0.333333 秒 / 0.78 秒）。开技能不会让抬手变快。

| 技能动画 | `Skill_1` | 0.233333 秒 | 7 帧 |
| 技能动画 | `Skill_2_Loop` | 0.333333 秒 | 10 帧 |
| 技能动画 | `Skill_3_Loop_A` | 0.333333 秒 | 10 帧 |
| 技能动画 | `Skill_3_Loop_B` | 0.333333 秒 | 10 帧 |
| 技能动画 | `Skill_3_ReStart_End` | 0.1 秒 | 3 帧 |


## 三、技能逐层拆解

---

### 家主的余裕　`skchr_demetr_1`

**技能描述（最高级）：**

> 下次攻击对目标造成两次相当于攻击力250%的物理伤害


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WHEN_ATTACK` | 每次攻击回复 |
| 初始 SP / 消耗 SP | 0 / 3 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 1 | 可存层数 |
| 释放方式 | `AUTO` | 自动释放 |
| 技能形态 | `瞬发技能` | 无持续时间，效果立即结算 |
| duration / durationType | 0 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `atk_scale` | 2.5 |

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

### 军师的手段　`skchr_demetr_2`

**技能描述（最高级）：**

> 攻击范围扩大，攻击速度+80，每次攻击对3名目标造成相当于攻击力200%的物理伤害；技能期间第一天赋使目标防御力降低的效果改为最多叠加8次，并且叠满后对目标造成持续的停顿效果


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WITH_TIME` | 随时间自动回复 |
| 初始 SP / 消耗 SP | 14 / 22 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 1 | 可存层数 |
| 释放方式 | `MANUAL` | 手动释放 |
| 技能形态 | `限时技能` | 持续 22 秒 |
| duration / durationType | 22 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `attack@atk_scale` | 2 |
| `attack@max_target` | 3 |
| `attack_speed` | 80 |

#### 攻击范围

`rangeId = 3-13`，8 格（direction=1）

```
· ■ ■ · 
■ ■ ■ ■ 
· ■ ■ · 
```

#### 判定链

本技能**没有独立 buff 模板**。它属于「一段式数值强化」：开技能只改 `blackboard` 参数与动画，不挂 buff 节点树。

可核对的替代证据：

- 描述中的每个花括号参数都能在 `blackboard` 中找到对应值（见上表）

---

### 清算　`skchr_demetr_3`

**技能描述（最高级）：**

> 攻击力+170%，攻击速度+50，攻击时有50%的几率造成相当于攻击力185%的物理伤害；技能开启后立即选取自身周围一定范围内的一名地面目标，若其所在位置可部署，自身会移动至目标所在位置进行攻击；自身攻击的精英、领袖敌人被击倒，或自身持续1秒未进行攻击时，会立即重新选取目标
> 受到致命伤害时不撤退但会结束技能，技能结束后返回初始位置


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WITH_TIME` | 随时间自动回复 |
| 初始 SP / 消耗 SP | 27 / 35 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 1 | 可存层数 |
| 释放方式 | `MANUAL` | 手动释放 |
| 技能形态 | `限时技能` | 持续 30 秒 |
| duration / durationType | 30 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `attack@demetr_s3[bonus].attack_speed` | 50 |
| `attack@demetr_s3[bonus].atk` | 1.7 |
| `attack@demetr_s3[bonus].prob_atk_scale` | 1.85 |
| `attack@demetr_s3[bonus].prob` | 0.5 |
| `attack@demetr_s3[target_timer].time_stack` | 2 |
| `attack@finish_listener_duration` | 3 |
| `attack@demetr_s3[target_timer].interval` | 0.5 |

#### 攻击范围

`rangeId = 1-1`，2 格（direction=1）

> 该技能未指定自己的 `rangeId`，上图是干员**自身范围**。技能若扩大范围，会另有 `rangeId`。

```
■ ■ 
```

#### 判定链

> 匹配方式：按命名规则匹配（层级 B）

**`demetr_s3[bonus]`** ← 事件 `ON_CALCULATE_DAMAGE`

- **Dice** 
- **AtkScaleUp** 

**`demetr_s3[disable_sp]`** ← 事件 `ON_BUFF_START`

- **ClearCharacterSp** `_forceFlag`=True `_charFrom`="BUFF_OWNER"
- **CreateBuff** buffKey=`demetr_s3[disable_sp_core]` `lifeTimeType`=INFINITY

**`demetr_s3[effect_1]`** ← 事件 `ON_BUFF_START`

- **CreateEffect** `_targetType`="BUFF_OWNER"

**`demetr_s3[elite_finish_listener]`** ← 事件 `ON_BUFF_START`

- **CheckUnitAlive** 
- **IfElse** 
  - **CheckContainsBuff** `_buffKeys`=["demetr_s3[elite_finish_listener_core]"] `_targetType`="BUFF_OWNER"
  - **CreateBuff** buffKey=`demetr_s3[elite_finish_listener_core]` templateKey=`demetr_s3[elite_finish_listener_core]` `overrideType`=EXTEND `lifeTimeType`=LIMITED
  - **TriggerBuffsByKeys** `_buffKeys`=["demetr_s3[target_holder]"] `_targetType`="BUFF_SOURCE"
  - **CheckEnemyLevelMask** `_targetType`="BUFF_OWNER"
  - **CreateBuff** buffKey=`demetr_s3[elite_finish_listener_core]` templateKey=`demetr_s3[elite_finish_listener_core]` `overrideType`=EXTEND `lifeTimeType`=LIMITED

**`demetr_s3[elite_finish_listener_core]`** ← 事件 `ON_BUFF_ENABLE`

- **CheckUnitAlive** 
- **AttachAsDerivedBuffById** 

**`demetr_s3[elite_finish_listener_core]`** ← 事件 `ON_OWNER_FINISH`

- **FilterDeathReason** `_source`="BUFF_OWNER"
- **CheckUnitAlive** 
- **CheckCharSkillAffecting** `_targetType`="BUFF_SOURCE"
- **TriggerAbilityUseSelector** `_targetType`="BUFF_SOURCE"

**`demetr_s3[finish_listener]`** ← 事件 `ON_OWNER_FINISH`

- **CheckUnitAlive** 
- **CheckCharSkillAffecting** `_targetType`="BUFF_SOURCE"
- **TriggerAbilityUseSelector** `_targetType`="BUFF_SOURCE"

**`demetr_s3[finish_listener]`** ← 事件 `ON_BUFF_START`

- **CheckUnitAlive** 
- **AttachAsDerivedBuffById** 

**`demetr_s3[range_update]`** ← 事件 `ON_BUFF_TRIGGER`

- **ForceUpdateRange** 

**`demetr_s3[restore]`** ← 事件 `ON_OWNER_LOCATE`

- **SwitchMode** `_modeIndex`=2 `_targetType`="BUFF_OWNER"
- **AlwaysNext** 
- **AddCharacterSharedBlackboard** `_target`="BUFF_OWNER"

**`demetr_s3[restore]`** ← 事件 `ON_BUFF_START`

- **ClearCharacterSp** `_forceFlag`=True `_charFrom`="BUFF_OWNER"

**`demetr_s3[restore]`** ← 事件 `ON_SKILL_START`

- **SwitchMode** `_modeIndex`=2 `_targetType`="BUFF_OWNER"
- **AlwaysNext** 
- **AddCharacterSharedBlackboard** `_target`="BUFF_OWNER"

**`demetr_s3[sharedBbPatch]`** ← 事件 `ON_BUFF_START`

- **AddCharacterSharedBlackboard** `_target`="BUFF_OWNER"

**`demetr_s3[switch_mode]`** ← 事件 `ON_BUFF_START`

- **SwitchMode** `_modeIndex`=0 `_targetType`="TARGET"
- **CreateEffect** `_targetType`="BUFF_OWNER"
- **TriggerAbility** `_targetType`="BUFF_OWNER"

**`demetr_s3[switch_mode]`** ← 事件 `ON_BUFF_FINISH`

- **SwitchMode** `_modeIndex`=0 `_targetType`="TARGET"

**`demetr_s3[target_holder]`** ← 事件 `ON_BUFF_TRIGGER`

- **FinishDerivedBuff** 

**`demetr_s3[target_timer]`** ← 事件 `ON_OUTPUT_DAMAGE`

- **FinishBuffsById** `_targetType`="BUFF_OWNER"
- **CreateBuff** buffKey=`demetr_s3[timer]` templateKey=`demetr_s3[timer]` `lifeTimeType`=INFINITY

**`demetr_s3[target_timer]`** ← 事件 `ON_BUFF_START`

- **CreateBuff** buffKey=`demetr_s3[timer]` templateKey=`demetr_s3[timer]` `lifeTimeType`=INFINITY

**`demetr_s3[target_timer]`** ← 事件 `ON_BUFF_TRIGGER`

- **TriggerAbilityUseSelector** `_targetType`="BUFF_OWNER"
- **FinishBuffsById** `_targetType`="BUFF_OWNER"
- **FinishBuffsById** `_targetType`="BUFF_OWNER"
- **CreateBuff** buffKey=`demetr_s3[timer]` templateKey=`demetr_s3[timer]` `lifeTimeType`=INFINITY
- **FinishDerivedBuffById** 

**`demetr_s3[timer]`** ← 事件 `ON_BUFF_TRIGGER`

- **CreateBuff** buffKey=`demetr_s3[time_stack]` `maxStackCnt`=1000 `overrideType`=STACK `lifeTimeType`=INFINITY
- **FilterByBuffStackCount** `_condType`="GE" `_targetType`="BUFF_OWNER"
- **TriggerBuffsByKeys** `_buffKeys`=["demetr_s3[target_timer]"] `_targetType`="BUFF_OWNER"

**`demetr_s3[undeadable]`** ← 事件 `ON_BEFORE_TRY_SET_HP_ZERO`

- **CreateBuff** buffKey=`demetr_s3[undeadable_core]` `lifeTimeType`=INFINITY
- **InterruptCharacterSkill** `_charFrom`="BUFF_OWNER"

---

## 附：数据边界

| 项目 | 状态 |
|---|---|
| 属性 / 数值 / SP / 范围 / 抬手 | ✅ 明文可得 |
| buff 行为树 | ✅ 明文可得 |
| 技能 → 模板绑定 | ⚠️ 游戏只给 `prefabId`，真实绑定在不可解的 `.ab` 里；本文按命名规律 + `blackboard` 键名双向推断 |
| 动画资源本体 | ❌ 在 `.ab` 包内，不可解 |
| 抬手精度 | ✅ 1/30 秒，是动画事件时刻而非视觉起手帧 |
