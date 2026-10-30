# 凛御银灰 — 技能判定说明

> 数据来源：明文 JSON（`character_table` / `skill_table` / `range_table` / `buff_template_data` / `bakemuzzledata`）。不含反汇编或二进制解析内容。

## 一、干员底子

| 项 | 值 |
|---|---|
| ID | `char_1045_svash2` |
| 职业 | 先锋 / `counsellor` |
| 星级 | 6 星 |
| 生命（精二满级） | 2218 |
| 攻击（精二满级） | 618 |
| 防御（精二满级） | 397 |
| 法抗 | 1500% |
| **攻击间隔 baseAttackTime** | **1.2 秒** |
| 攻速 attackSpeed | 100（100% = 无增减） |
| 阻挡 | 2 |
| 部署费用 | 13 |

**攻击间隔换算**（全干员通用）：

```
实际间隔 = baseAttackTime ÷ (attackSpeed / 100)
         = 1.2 ÷ 1.00 = 1.200 秒
```

## 二、抬手（攻击前摇）

来源：`bakemuzzledata/character/char_1045_svash2_*.json` → `bakedAnimDatas.<组>.bakedEvents.<动画名>.eventTime`，取事件 `OnAttack` 时刻。

| 场景 | 动画名 | 抬手 | 帧数(30fps) |
|---|---|---|---|
| **普通攻击** | `Attack_A` | **0.5 秒** | 15 帧 |

> 占攻击间隔 41.7%（0.5 秒 / 1.2 秒）。开技能不会让抬手变快。

| 技能动画 | `Skill_1_A` | 0.466667 秒 | 14 帧 |
| 技能动画 | `Skill_2` | 0.4 秒 | 12 帧 |
| 技能动画 | `Skill_3_Combat` | 0.5 秒 | 15 帧 |
| 技能动画 | `Skill_3_Deploy` | 0.533333 秒 | 16 帧 |


## 三、技能逐层拆解

---

### 周旋的谋略　`skchr_svash2_1`

**技能描述（最高级）：**

> 立刻获得10点部署费用。待部署区中距离“风雪之眼”最近的1名干员费用-5（优先选择右侧近卫/术师/狙击干员），且部署后获得相当于凛御银灰最大生命值50%的屏障


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WITH_TIME` | 随时间自动回复 |
| 初始 SP / 消耗 SP | 19 / 29 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 1 | 可存层数 |
| 释放方式 | `AUTO` | 自动释放 |
| 技能形态 | `无限持续` | 开启后一直生效，直到手动关闭或条件结束 |
| duration / durationType | -1 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `cost` | 10 |
| `svash2_s_1[deck].cost` | 5 |
| `svash2_s_1[deck].shield` | 0.5 |
| `token_cost_modify` | 0 |

#### 攻击范围

`rangeId = 1-1`，2 格（direction=1）

> 该技能未指定自己的 `rangeId`，上图是干员**自身范围**。技能若扩大范围，会另有 `rangeId`。

```
■ ■ 
```

#### 判定链

> 匹配方式：由 `blackboard` 键名精确指认（层级 A）

**`svash2_s_1`** ← 事件 `ON_BUFF_START`

- **ModifyAnimatorHookerReplacePair** `_modeIndex`=-1 `_target`="BUFF_OWNER"

**`svash2_s_1`** ← 事件 `ON_BUFF_FINISH`

- **ModifyAnimatorHookerReplacePair** `_modeIndex`=-1 `_target`="BUFF_OWNER"

**`svash2_s_1[deck]`** ← 事件 `ON_BUFF_START`

- **EnsureBlackboardDefaultValue** 
- **IfElse** 
  - **AlwaysNext** 
  - **AssignAttributeToBB** `_targetType`="BUFF_OWNER"
  - **CalculateBlackboardValueViaParams** 
  - **CalculateBlackboardValueViaParams** 
  - **IfElse** 
    - **AlwaysNext** 
    - **CreateDeckCardBuffsWithSelectOrderList** 
  - **AlwaysNext** 
  - **CalculateBlackboardValueViaParams** 
  - **CreateDeckCardBuffsWithSelectOrderList** 
- **AlwaysNext** 
- **SortDeck** `_source`="BUFF_OWNER"

---

### 御敌的锋锐　`skchr_svash2_2`

**技能描述（最高级）：**

> 对前方6名敌人造成攻击力380%的物理伤害，使其6秒内寒冷且隐匿失效；待部署区中距离“风雪之眼”最近的1名干员费用-11（优先选择右侧近卫/术师/狙击干员）；使“风雪之眼”左侧所有干员部署时以自身攻击力施放一次本技能的范围效果（最多叠加2次）
> 可充能2次


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WITH_TIME` | 随时间自动回复 |
| 初始 SP / 消耗 SP | 9 / 17 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 2 | 可存层数 |
| 释放方式 | `MANUAL` | 手动释放 |
| 技能形态 | `瞬发技能` | 无持续时间，效果立即结算 |
| duration / durationType | 0 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `cost` | 11 |
| `atk_scale` | 3.8 |
| `cold` | 6 |
| `max_target` | 6 |
| `range_id` | 0 |
| `cost_scale_display` | 7 |
| `cnt` | 1 |
| `max_stack_cnt` | 2 |
| `token_cost_modify` | 0 |

#### 攻击范围

`rangeId = 3-7`，16 格（direction=1）

```
■ · · · 
■ ■ · · 
■ ■ ■ · 
■ ■ ■ ■ 
■ ■ ■ · 
■ ■ · · 
■ · · · 
```

#### 判定链

> 匹配方式：按命名规则匹配（层级 B）

**`svash2_s_2`** ← 事件 `ON_BUFF_START`

- **EnsureBlackboardDefaultValue** 
- **CalculateBlackboardValueViaParams** 
- **CalculateBlackboardValueViaParams** 
- **CalculateBlackboardValueViaParams** 
- **CreateBuff** buffKey=`svash2_s_2[cost]` templateKey=`svash2_s_2[cost]` `lifeTimeType`=IMMEDIATELY
- **SortDeck** `_source`="BUFF_OWNER"
- **CalculateBlackboardValueViaParams** 
- **CreateBuff** buffKey=`svash2_s_2[build_set]` templateKey=`svash2_s_2[build_set]` `lifeTimeType`=IMMEDIATELY
- **PlayAudio** `_target`="BUFF_OWNER"
- **EnsureBlackboardDefaultValue** 

**`svash2_s_2[build]`** ← 事件 `ON_BUFF_TRIGGER`

- **IfElse** 
  - **FilterByBlackboardValue** `_condType`="GE" `_targetType`="BUFF_OWNER"
  - **EnsureBlackboardDefaultValue** 
  - **CalculateBlackboardValueViaParams** 
  - **AOEDamage** `_targetType`="BUFF_OWNER" targetOptions(targetSide=ENEMY, targetMotion=ALL, targetCategory=DEFAULT, abnormalFlag=INVISIBLE)
  - **AlwaysNext** 
  - **FinishBuff** 
  - **CalculateBlackboardValueViaParams** 
  - **CalculateBlackboardValueViaParams** 

**`svash2_s_2[build]`** ← 事件 `ON_BUFF_START`

- **EnsureBlackboardDefaultValue** 

**`svash2_s_2[build][effect]`** ← 事件 `ON_BUFF_TRIGGER`

- **IfElse** 
  - **FilterByBlackboardValue** `_condType`="GE" `_targetType`="BUFF_OWNER"
  - **CreateEffect** `_targetType`="BUFF_OWNER"
  - **PlayAudio** `_target`="BUFF_OWNER"
  - **FinishBuff** 
  - **CalculateBlackboardValueViaParams** 
  - **CalculateBlackboardValueViaParams** 

**`svash2_s_2[build][effect]`** ← 事件 `ON_BUFF_START`

- **EnsureBlackboardDefaultValue** 

**`svash2_s_2[build_set]`** ← 事件 `ON_BUFF_START`

- **EnsureBlackboardDefaultValue** 
- **CreateDeckBuffWithSelectOrder** 
- **EnsureBlackboardDefaultValue** 
- **CreateDeckBuffWithSelectOrder** 

**`svash2_s_2[cost]`** ← 事件 `ON_BUFF_START`

- **CreateDeckCardBuffsWithSelectOrderList** 

**`svash2_s_2[signal]`** ← 事件 `ON_BUFF_START`

- **CreateBuffById** 
- **CreateBuff** buffKey=`svash2_s_2[invi_immu]` `lifeTimeType`=LIMITED

---

### 变革已至　`skchr_svash2_3`

**技能描述（最高级）：**

> 攻击范围扩大并使敌人隐匿失效，攻击对直线范围造成攻击力200%的物理伤害和30%的脆弱；立即获得9点后持续获得24点部署费用
> 首次开启时交换待部署区中费用最高（优先选择近卫/术师/狙击干员）与最低干员的基础部署费用
> 技能期间“风雪之眼”变为可部署


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WITH_TIME` | 随时间自动回复 |
| 初始 SP / 消耗 SP | 46 / 55 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 1 | 可存层数 |
| 释放方式 | `MANUAL` | 手动释放 |
| 技能形态 | `限时技能` | 持续 48 秒 |
| duration / durationType | 48 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `svash2_s_3[start_cost].cost` | 9 |
| `svash2_s_3[cost].cost` | 1 |
| `svash2_s_3[cost].interval` | 2 |
| `change_cnt` | 1 |
| `bird_atk_scale` | 2 |
| `damage_scale` | 1.3 |
| `cnt` | 1 |
| `weak[limit]` | 2 |
| `range_id` | 0 |
| `damage_scale_display` | 0.3 |
| `cost_reduce_max` | 0 |

#### 攻击范围

`rangeId = 3-1`，10 格（direction=1）

```
■ ■ ■ · 
■ ■ ■ ■ 
■ ■ ■ · 
```

#### 判定链

> 匹配方式：由 `blackboard` 键名精确指认（层级 A）

**`svash2_s_3`** ← 事件 `ON_BUFF_START`

- **PlayAudio** `_target`="BUFF_OWNER"
- **CreateBuff** buffKey=`svash2_not_show_hint_s3` `overrideType`=UNIQUE `lifeTimeType`=INFINITY
- **AssignCardUIDToBlackBoard** `_targetType`="BUFF_OWNER"
- **CreateCardBuff** `_target`="BUFF_OWNER"
- **IfElse** 
  - **FilterByGlobalBlackboard** `_condType`="LE"
  - **CreateBuff** buffKey=`svash2_s_3[sort_once]` templateKey=`svash2_s_3[sort_once]` `lifeTimeType`=INFINITY
  - **EnsureBlackboardDefaultValue** 
- **AlwaysNext** 
- **TriggerAbility** `_targetType`="BUFF_OWNER"

**`svash2_s_3`** ← 事件 `ON_BUFF_FINISH`

- **IfElse** 
  - **AlwaysNext** 
  - **InterruptAbility** 
  - **AlwaysNext** 
  - **InterruptAbility** 
  - **AlwaysNext** 
  - **FinishCardBuffsByKey** 
- **AlwaysNext** 
- **FinishBuffsById** `_targetType`="BUFF_OWNER"
- **AlwaysNext** 
- **CreateEffect** `_targetType`="BUFF_OWNER"
- **AlwaysNext** 
- **FinishBuffsOfEveryCharacterById** 
- **AlwaysNext** 
- **FinishBuffsOfEveryCharacterById** 

**`svash2_s_3`** ← 事件 `ON_OWNER_FINISH`

- **InterruptAbility** 
- **AlwaysNext** 
- **InterruptAbility** 
- **AlwaysNext** 
- **FinishCardBuffsByKey** 
- **AlwaysNext** 
- **FinishBuffsOfEveryCharacterById** 
- **AlwaysNext** 
- **FinishBuffsOfEveryCharacterById** 

**`svash2_s_3`** ← 事件 `ON_BUFF_TRIGGER`

- **IfConditions** 
  - **FilterByBlackboardStrIsValue** `_targetType`="BUFF_OWNER"
  - **IfConditions** 
    - **FilterByBlackboardStrIsValue** `_targetType`="BUFF_OWNER"
    - **IfConditions** 
      - **FilterByBlackboardStrIsValue** `_targetType`="BUFF_OWNER"
      - **CreateBuffToCardUidCharacter** buffKey=`svash2_s_3[finish_summon_bird]` templateKey=`svash2_s_3[finish_summon_bird]` `lifeTimeType`=LIMITED
      - **AlwaysNext** 
      - **CreateBuff** buffKey=`svash2_s_3[1f_delay_create]` templateKey=`svash2_s_3[1f_delay_create]` `lifeTimeType`=LIMITED
    - **CreateBuff** buffKey=`svash2_s_3[1f_delay_create]` templateKey=`svash2_s_3[1f_delay_create]` `lifeTimeType`=LIMITED
  - **AlwaysNext** 
  - **AssignBuffBlackboard** `_targetType`="BUFF_OWNER"
  - **AssignBuffBlackboard** `_targetType`="BUFF_OWNER"
  - **IfConditions** 
    - **FilterByBlackboardStrIsValue** `_targetType`="BUFF_OWNER"
    - **FilterByBlackboardStrIsValue** `_targetType`="BUFF_OWNER"
- …（共 21 个节点，已截断）

**`svash2_s_3[1f_delay_create]`** ← 事件 `ON_BUFF_START`

- **FinishBuffsOfEveryCharacterById** 
- **InterruptAbility** 

**`svash2_s_3[1f_delay_create]`** ← 事件 `ON_BUFF_TRIGGER`

- **CreateBuffToCardUidCharacter** buffKey=`svash2_s_3[target_bird_onuse]` templateKey=`svash2_s_3[target_bird_onuse]` `lifeTimeType`=INFINITY

**`svash2_s_3[1f_delay_create_build]`** ← 事件 `ON_BUFF_START`

- **FinishBuffsOfEveryCharacterById** 
- **InterruptAbility** 

**`svash2_s_3[1f_delay_create_build]`** ← 事件 `ON_BUFF_TRIGGER`

- **CreateBuffToCardUidCharacter** buffKey=`svash2_s_3[target_bird_onuse]` templateKey=`svash2_s_3[target_bird_onuse]` `lifeTimeType`=INFINITY

**`svash2_s_3[assign_uid]`** ← 事件 `ON_BUFF_START`

- **AssignCardUIDToBlackBoard** `_targetType`="TARGET"
- **AssignBuffBlackboard** `_targetType`="BUFF_SOURCE"

**`svash2_s_3[bird_attached]`** ← 事件 `ON_BUFF_START`


**`svash2_s_3[bird_attached]`** ← 事件 `ON_BUFF_FINISH`


**`svash2_s_3[bird_eff]`** ← 事件 `ON_BUFF_START`

- **CreateEffect** `_targetType`="BUFF_OWNER"
- **CreateEffect** `_targetType`="BUFF_OWNER"

**`svash2_s_3[bird_on_self]`** ← 事件 `ON_BUFF_START`

- **EnsureBlackboardDefaultValue** 
- **Svash2EmitProjectileFixedDirection** targetOptions(targetSide=ENEMY, targetMotion=ALL, targetCategory=DEFAULT, abnormalFlag=STUNNED)
  - **AdvancedApplyDamage** `_targetType`="TARGET"

**`svash2_s_3[bird_on_target]`** ← 事件 `ON_BUFF_START`

- **EnsureBlackboardDefaultValue** 
- **Svash2EmitProjectileFixedDirection** targetOptions(targetSide=ENEMY, targetMotion=ALL, targetCategory=DEFAULT, abnormalFlag=STUNNED)
  - **AdvancedApplyDamage** `_targetType`="TARGET"

**`svash2_s_3[bird_on_target]`** ← 事件 `ON_BUFF_FINISH`

- **FinishBuffsById** `_targetType`="BUFF_OWNER"

**`svash2_s_3[deck_build]`** ← 事件 `ON_BUFF_START`

- **Svash2RemoveCardOverrideByCardUid** 

**`svash2_s_3[finish_summon_bird]`** ← 事件 `ON_BUFF_START`

- **FinishBuffsById** `_targetType`="BUFF_OWNER"

**`svash2_s_3[global]`** ← 事件 `ON_OWNER_POST_BORN`

- **IfElse** 
  - **IsCharacter** `_targetType`="BUFF_OWNER"
  - **IfElse** 
    - **FilterCharacterAdvancedBuildStateMask** 
    - **AssignCardUIDToBlackBoard** `_targetType`="BUFF_OWNER"
    - **AssignBuffBlackboard** `_targetType`="BUFF_SOURCE"

**`svash2_s_3[idle_anim]`** ← 事件 `ON_BUFF_FINISH`

- **TriggerAbility** `_targetType`="BUFF_OWNER"

**`svash2_s_3[not_show_check]`** ← 事件 `ON_BUFF_START`

- **IfElse** 
  - **FilterByGlobalBlackboard** `_condType`="LE"
  - **CreateBuff** buffKey=`svash2_not_show_hint_s3` `lifeTimeType`=INFINITY

**`svash2_s_3[self_bird_onuse]`** ← 事件 `ON_BUFF_START`

- **TriggerAbility** `_targetType`="BUFF_OWNER"

**`svash2_s_3[self_bird_onuse]`** ← 事件 `ON_BUFF_FINISH`

- **InterruptAbility** 

**`svash2_s_3[sort_once]`** ← 事件 `ON_BUFF_START`

- **Svash2LRCardPositionSwap** 
- **SortDeck** `_source`="BUFF_OWNER"
- **AddGlobalBlackboard** 

**`svash2_s_3[summon_bird]`** ← 事件 `ON_BUFF_TRIGGER`

- **CheckCanTriggerLikeAttack** `_targetType`="BUFF_SOURCE"
  - **CheckContainsTargetsInRangeId** targetOptions(targetSide=ENEMY, targetMotion=ALL, targetCategory=DEFAULT, abnormalFlag=STUNNED)
- **TriggerAbility** `_targetType`="BUFF_OWNER"

**`svash2_s_3[summon_bird]`** ← 事件 `ON_BUFF_START`

- **EnsureBlackboardDefaultValue** 

**`svash2_s_3[target_bird_onuse]`** ← 事件 `ON_BUFF_START`

- **EnsureBlackboardDefaultValue** 
- **TriggerAbility** `_targetType`="BUFF_OWNER"
- **CalculateBlackboardValueViaParams** 
- **CreateBuff** buffKey=`svash2_s_3[summon_bird]` templateKey=`svash2_s_3[summon_bird]` `lifeTimeType`=INFINITY

**`svash2_s_3[target_bird_onuse]`** ← 事件 `ON_BUFF_FINISH`

- **IfConditions** 
  - **FilterByBlackboardValue** `_condType`="GT" `_targetType`="BUFF_OWNER"
  - **AssignBuffBlackboard** `_targetType`="BUFF_SOURCE"
  - **AlwaysNext** 
  - **InterruptCharacterAbility** `_charFrom`="BUFF_SOURCE"

**`svash2_s_3[target_bird_onuse]`** ← 事件 `ON_BUFF_TRIGGER`

- **IfConditions** 
  - **CheckContainsBuff** `_buffKeys`=["svash2_s_3"] `_targetType`="BUFF_SOURCE"
  - **FinishBuff** 

**`svash2_s_3[trigger_self]`** ← 事件 `ON_BUFF_START`

- **TriggerAbility** `_targetType`="BUFF_SOURCE"

---

## 附：数据边界

| 项目 | 状态 |
|---|---|
| 属性 / 数值 / SP / 范围 / 抬手 | ✅ 明文可得 |
| buff 行为树 | ✅ 明文可得 |
| 技能 → 模板绑定 | ⚠️ 游戏只给 `prefabId`，真实绑定在不可解的 `.ab` 里；本文按命名规律 + `blackboard` 键名双向推断 |
| 动画资源本体 | ❌ 在 `.ab` 包内，不可解 |
| 抬手精度 | ✅ 1/30 秒，是动画事件时刻而非视觉起手帧 |
