# 死芒 — 技能判定说明

> 数据来源：明文 JSON（`character_table` / `skill_table` / `range_table` / `buff_template_data` / `bakemuzzledata`）。不含反汇编或二进制解析内容。

## 一、干员底子

| 项 | 值 |
|---|---|
| ID | `char_450_necras` |
| 职业 | 术师 / `soulcaster` |
| 星级 | 6 星 |
| 生命（精二满级） | 1924 |
| 攻击（精二满级） | 633 |
| 防御（精二满级） | 133 |
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

来源：`bakemuzzledata/character/char_450_necras_*.json` → `bakedAnimDatas.<组>.bakedEvents.<动画名>.eventTime`，取事件 `OnAttack` 时刻。

| 场景 | 动画名 | 抬手 | 帧数(30fps) |
|---|---|---|---|
| **普通攻击** | `Attack` | **0.5 秒** | 15 帧 |

> 占攻击间隔 31.2%（0.5 秒 / 1.6 秒）。开技能不会让抬手变快。

| 技能动画 | `Skill_1` | 0.5 秒 | 15 帧 |
| 技能动画 | `Skill_2_Begin` | 0.666667 秒 | 20 帧 |
| 技能动画 | `Skill_3_Begin` | 0.566667 秒 | 17 帧 |
| 技能动画 | `Skill_3_Loop` | 0.566667 秒 | 17 帧 |


## 三、技能逐层拆解

---

### 噩愿　`skchr_necras_1`

**技能描述（最高级）：**

> 被动：每个悲叹的仆役生成和升级时对周围所有敌人造成相当于死芒攻击力450%的法术伤害
> 开启：立刻重新召唤所有悲叹的仆役，若场上没有悲叹的仆役存在则召唤1个


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WITH_TIME` | 随时间自动回复 |
| 初始 SP / 消耗 SP | 8 / 13 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 1 | 可存层数 |
| 释放方式 | `MANUAL` | 手动释放 |
| 技能形态 | `无限持续` | 开启后一直生效，直到手动关闭或条件结束 |
| duration / durationType | -1 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `atk_scale` | 4.5 |
| `range_radius` | 1.5 |

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

**`necras_s_1`** ← 事件 `ON_BUFF_START`

- **IfElse** 
  - **CheckContainsBuff** `_buffKeys`=["necras_t_1[upgrade]"] `_targetType`="BUFF_OWNER"
  - **CreateBuff** buffKey=`necras_t_1[spawn_token]` templateKey=`necras_t_1[spawn_token]` `maxStackCnt`=-1 `overrideType`=STACK `lifeTimeType`=INFINITY
  - **CreateBuff** buffKey=`necras_t_1[spawn_token]` templateKey=`necras_t_1[spawn_token]` `maxStackCnt`=-1 `overrideType`=STACK `lifeTimeType`=INFINITY
  - **CreateBuff** buffKey=`necras_t_1[spawn_token]` templateKey=`necras_t_1[spawn_token]` `maxStackCnt`=-1 `overrideType`=STACK `lifeTimeType`=INFINITY
- **Withdraw** 
- **FinishBuffsById** `_targetType`="BUFF_SOURCE"

**`necras_s_1[fallback]`** ← 事件 `ON_BUFF_START`

- **CheckContainsBuff** `_buffKeys`=["necras_s_1[no_token_mark]"] `_targetType`="BUFF_OWNER"
- **AssignTokenCntToBB** 
- **FilterByBlackboardValue** `_condType`="EQUALS" `_targetType`="BUFF_OWNER"
- **CreateBuff** buffKey=`necras_t_1[spawn_token]` templateKey=`necras_t_1[spawn_token]` `maxStackCnt`=-1 `overrideType`=STACK `lifeTimeType`=INFINITY
- **FinishBuffsById** `_targetType`="BUFF_OWNER"

---

### 折朽　`skchr_necras_2`

**技能描述（最高级）：**

> 令最多2名攻击范围内的敌人陷入沉睡，每0.5秒对目标造成相当于攻击力160%的法术伤害；技能期间目标被击倒时额外召唤2个悲叹的仆役


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WITH_TIME` | 随时间自动回复 |
| 初始 SP / 消耗 SP | 14 / 20 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 1 | 可存层数 |
| 释放方式 | `MANUAL` | 手动释放 |
| 技能形态 | `限时技能` | 持续 12 秒 |
| duration / durationType | 12 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `atk_scale` | 1.6 |
| `additional_token_cnt` | 2 |
| `hit_duration` | 12 |
| `interval` | 0.5 |
| `max_target` | 2 |

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

**`necras_s_2`** ← 事件 `ON_BUFF_TRIGGER`

- **AdvancedApplyDamage** `_targetType`="BUFF_OWNER"
- **CreateEffect** `_targetType`="BUFF_OWNER"
- **PlayAudio** `_target`="TARGET"

**`necras_s_2`** ← 事件 `ON_OWNER_FINISH`

- **CreateBuffStacked** buffKey=`necras_t_1[spawn_token]` templateKey=`necras_t_1[spawn_token]` `maxStackCnt`=-1 `overrideType`=STACK `lifeTimeType`=INFINITY

**`necras_s_2[damage_sleep]`** ← 事件 `ON_OUTPUT_MODIFIER`

- **SetSharedFlag** 

**`necras_s_2[damage_sleep]`** ← 事件 `ON_BUFF_START`

- **ModifyAbilityBlackboard** 

---

### 冠死以冕　`skchr_necras_3`

**技能描述（最高级）：**

> 被动：最多1名悲叹的仆役变为特殊形态，此形态下只能通过技能升级，最多升级6次
> 开启：立刻对范围内所有敌人造成攻击力800%的法术伤害，之后消耗一个悲叹的仆役使特殊仆役升级并回复20%生命（若悲叹的仆役已升级则翻倍），重复3次


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WITH_TIME` | 随时间自动回复 |
| 初始 SP / 消耗 SP | 5 / 16 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 1 | 可存层数 |
| 释放方式 | `MANUAL` | 手动释放 |
| 技能形态 | `无限持续` | 开启后一直生效，直到手动关闭或条件结束 |
| duration / durationType | -1 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `attack@atk` | 0.8 |
| `attack@atk_scale` | 8 |
| `attack@max_stack_cnt` | 6 |
| `attack@max_valid_stack_cnt` | -1 |
| `attack@necras_s_3[attack_cnt].max_stack_cnt` | 3 |
| `attack@hp_ratio` | 0.2 |
| `attack@def` | 0.4 |
| `attack@max_hp` | 0.8 |
| `attack@magic_resistance` | 0 |
| `attack@block_cnt` | 1 |
| `attack@ability_range_forward_extend` | 1 |

#### 攻击范围

`rangeId = 3-3`，12 格（direction=1）

```
■ ■ ■ ■ 
■ ■ ■ ■ 
■ ■ ■ ■ 
```

#### 判定链

> 匹配方式：按命名规则匹配（层级 B）

**`necras_s_3`** ← 事件 `ON_BUFF_START`

- **IfElse** 
  - **CheckContainsBuff** `_buffKeys`=["necras_t_1[upgrade]"] `_targetType`="BUFF_OWNER"
  - **TriggerAbilityUseSelectorMergeBB** `_targetType`="BUFF_SOURCE"
  - **CreateEffect** `_targetType`="BUFF_OWNER"
  - **CreateBuff** buffKey=`necras_s_3[delay_upgrade]` templateKey=`necras_s_3[delay_upgrade]` `lifeTimeType`=INFINITY
  - **Withdraw** 
  - **TriggerAbilityUseSelectorMergeBB** `_targetType`="BUFF_SOURCE"
  - **CreateEffect** `_targetType`="BUFF_OWNER"
  - **Withdraw** 

**`necras_s_3[after_attack]`** ← 事件 `ON_BUFF_START`

- **CreateBuffToToken** `_targetType`="BUFF_SOURCE"
- **FinishBuffsById** `_targetType`="BUFF_OWNER"
- **IfElse** 
  - **FilterByBuffStackCount** `_condType`="EQUALS" `_targetType`="BUFF_OWNER"
  - **CheckUnitAlive** 
  - **FinishBuffsById** `_targetType`="BUFF_OWNER"
  - **FinishBuffsById** `_targetType`="BUFF_OWNER"
  - **InterruptCharacterSkill** `_charFrom`="BUFF_OWNER"
  - **FinishBuffsById** `_targetType`="BUFF_OWNER"
  - **FinishBuffsById** `_targetType`="BUFF_OWNER"

**`necras_s_3[before_attack]`** ← 事件 `ON_BUFF_START`

- **CreateBuff** buffKey=`necras_s_3[attack_cnt]` `overrideType`=STACK `lifeTimeType`=INFINITY
- **CreateBuff** buffKey=`necras_s_3[kill_checker]` templateKey=`necras_s_3[kill_checker]` `overrideType`=STACK `lifeTimeType`=INFINITY
- **FinishBuffsById** `_targetType`="BUFF_OWNER"

**`necras_s_3[delay_upgrade]`** ← 事件 `ON_BUFF_TRIGGER`

- **TriggerAbilityUseSelectorMergeBB** `_targetType`="BUFF_OWNER"
- **FinishBuff** 

**`necras_s_3[kill_checker]`** ← 事件 `ON_TARGET_KILLED`

- **CheckTargetTokenOrHost** 
- **CreateBuff** buffKey=`necras_s_3[kill_mark]` `overrideType`=UNIQUE `lifeTimeType`=INFINITY

---

## 附：数据边界

| 项目 | 状态 |
|---|---|
| 属性 / 数值 / SP / 范围 / 抬手 | ✅ 明文可得 |
| buff 行为树 | ✅ 明文可得 |
| 技能 → 模板绑定 | ⚠️ 游戏只给 `prefabId`，真实绑定在不可解的 `.ab` 里；本文按命名规律 + `blackboard` 键名双向推断 |
| 动画资源本体 | ❌ 在 `.ab` 包内，不可解 |
| 抬手精度 | ✅ 1/30 秒，是动画事件时刻而非视觉起手帧 |
