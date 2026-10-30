# 缇缇 — 技能判定说明

> 数据来源：明文 JSON（`character_table` / `skill_table` / `range_table` / `buff_template_data` / `bakemuzzledata`）。不含反汇编或二进制解析内容。

## 一、干员底子

| 项 | 值 |
|---|---|
| ID | `char_4056_titi` |
| 职业 | 医疗 / `incantationmedic` |
| 星级 | 6 星 |
| 生命（精二满级） | 1405 |
| 攻击（精二满级） | 548 |
| 防御（精二满级） | 117 |
| 法抗 | 2000% |
| **攻击间隔 baseAttackTime** | **1.6 秒** |
| 攻速 attackSpeed | 100（100% = 无增减） |
| 阻挡 | 1 |
| 部署费用 | 17 |

**攻击间隔换算**（全干员通用）：

```
实际间隔 = baseAttackTime ÷ (attackSpeed / 100)
         = 1.6 ÷ 1.00 = 1.600 秒
```

## 二、抬手（攻击前摇）

来源：`bakemuzzledata/character/char_4056_titi_*.json` → `bakedAnimDatas.<组>.bakedEvents.<动画名>.eventTime`，取事件 `OnAttack` 时刻。

| 场景 | 动画名 | 抬手 | 帧数(30fps) |
|---|---|---|---|
| **普通攻击** | `Attack` | **0.5 秒** | 15 帧 |

> 占攻击间隔 31.2%（0.5 秒 / 1.6 秒）。开技能不会让抬手变快。

| 技能动画 | `Skill_1_Loop` | 0.466667 秒 | 14 帧 |
| 技能动画 | `Skill_3_Loop` | 0.466667 秒 | 14 帧 |


## 三、技能逐层拆解

---

### 缓蚀　`skchr_titi_1`

**技能描述（最高级）：**

> 攻击力+100%，每次攻击有50%概率使目标沉睡3秒


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WITH_TIME` | 随时间自动回复 |
| 初始 SP / 消耗 SP | 18 / 40 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 1 | 可存层数 |
| 释放方式 | `MANUAL` | 手动释放 |
| 技能形态 | `限时技能` | 持续 17 秒 |
| duration / durationType | 17 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `attack@sleep` | 3 |
| `attack@prob` | 0.5 |
| `atk` | 1 |

#### 攻击范围

`rangeId = 3-3`，12 格（direction=1）

> 该技能未指定自己的 `rangeId`，上图是干员**自身范围**。技能若扩大范围，会另有 `rangeId`。

```
■ ■ ■ ■ 
■ ■ ■ ■ 
■ ■ ■ ■ 
```

#### 判定链

> 匹配方式：按命名规则匹配（层级 B）

**`titi_s_1[prob_sleep]`** ← 事件 `ON_BUFF_START`

- **Dice** 
- **CreateBuff** buffKey=`sleep` `lifeTimeType`=LIMITED

---

### 封护　`skchr_titi_2`

**技能描述（最高级）：**

> 停止攻击，攻击力+180%，技能开启时使自身与攻击范围内生命比例最低的干员陷入沉睡直到技能结束，期间持续使自身与该目标周围的敌人陷入沉睡，第一天赋效果提升至3.3倍
> 可主动关闭技能（期间可随时停止技能）


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WITH_TIME` | 随时间自动回复 |
| 初始 SP / 消耗 SP | 15 / 20 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 1 | 可存层数 |
| 释放方式 | `MANUAL` | 手动释放 |
| 技能形态 | `限时技能` | 持续 15 秒 |
| duration / durationType | 15 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `talent_scale` | 3.3 |
| `atk` | 1.8 |

#### 攻击范围

`rangeId = 3-3`，12 格（direction=1）

> 该技能未指定自己的 `rangeId`，上图是干员**自身范围**。技能若扩大范围，会另有 `rangeId`。

```
■ ■ ■ ■ 
■ ■ ■ ■ 
■ ■ ■ ■ 
```

#### 判定链

> 匹配方式：按命名规则匹配（层级 B）

**`titi_s_2`** ← 事件 `ON_BUFF_TRIGGER`

- **AlwaysExecuteNodeList** 
  - **CreateBuffInRange** `_targetType`="BUFF_OWNER" targetOptions(targetSide=ENEMY, targetMotion=ALL, targetCategory=DEFAULT, abnormalFlag=E_NUM)
  - **IfElse** 
    - **CheckContainsBuff** `_buffKeys`=["titi_s_2[self]"] `_targetType`="BUFF_SOURCE"
    - **FinishBuff** 

**`titi_s_2`** ← 事件 `ON_BUFF_START`

- **CreateBuff** buffKey=`doze[inf]` `lifeTimeType`=LIMITED
- **CreateBuff** buffKey=`titi_s_2[eff]` `lifeTimeType`=INFINITY
- **EnsureBlackboardDefaultValue** 

**`titi_s_2[self]`** ← 事件 `ON_BUFF_START`

- **TriggerAbility** `_targetType`="BUFF_OWNER"
- **AlwaysNext** 
- **CreateBuff** buffKey=`titi_s_2` templateKey=`titi_s_2` `lifeTimeType`=INFINITY

**`titi_s_2[self]`** ← 事件 `ON_BUFF_FINISH`

- **InterruptAbility** 

**`titi_s_2[sleep_enemy]`** ← 事件 `ON_BUFF_START`

- **IfTarget** `_targetType`="BUFF_OWNER"
- **CreateBuff** buffKey=`titi_s_2[sleep_enemy_internal]` `lifeTimeType`=INFINITY

---

### 旧日绽放　`skchr_titi_3`

**技能描述（最高级）：**

> 攻击力+180%，同时攻击两名敌人，攻击非沉睡目标时使其沉睡5秒，技能期间，全场敌人从沉睡状态醒来或于沉睡中被击倒时，受到法术伤害（随沉睡时长提高至攻击力460%），并使周围一名其他敌人沉睡5秒，攻击范围内的其他友方干员受到致命伤害时，陷入沉睡至生命值完全恢复或技能结束


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WITH_TIME` | 随时间自动回复 |
| 初始 SP / 消耗 SP | 28 / 37 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 1 | 可存层数 |
| 释放方式 | `MANUAL` | 手动释放 |
| 技能形态 | `限时技能` | 持续 25 秒 |
| duration / durationType | 25 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `atk` | 1.8 |
| `attack@max_target` | 2 |
| `attack@sleep` | 5 |
| `max_target` | 1 |
| `min_atk_scale` | 1 |
| `max_atk_scale` | 4.6 |
| `sleep` | 5 |
| `range_radius` | 1.5 |

#### 攻击范围

`rangeId = 3-3`，12 格（direction=1）

> 该技能未指定自己的 `rangeId`，上图是干员**自身范围**。技能若扩大范围，会另有 `rangeId`。

```
■ ■ ■ ■ 
■ ■ ■ ■ 
■ ■ ■ ■ 
```

#### 判定链

> 匹配方式：按命名规则匹配（层级 B）

**`titi_s_3[attack_sleep]`** ← 事件 `ON_BUFF_START`

- **IfConditions** 
  - **IfTarget** `_targetType`="BUFF_OWNER"
  - **CheckAbnormalCombo** `_targetType`="BUFF_OWNER"
  - **CreateBuff** buffKey=`sleep` `lifeTimeType`=LIMITED

**`titi_s_3[dmg_ticker]`** ← 事件 `ON_BUFF_TRIGGER`

- **AlwaysExecuteNodeList** 
  - **IfConditions** 
    - **CheckAbnormalFlag** `_targetType`="BUFF_OWNER"
    - **CheckAbnormalCombo** `_targetType`="BUFF_OWNER"
    - **CalculateBlackboardValueViaParams** 
    - **CalculateBlackboardValueViaParams** 
    - **CalculateBlackboardValueViaParams** 
    - **CalculateBlackboardValueViaParams** 
  - **IfConditions** 
    - **FilterByBlackboardValue** `_condType`="GT" `_targetType`="BUFF_OWNER"
    - **FilterByBlackboardValue** `_condType`="GT" `_targetType`="BUFF_OWNER"
    - **FilterByBlackboardValue** `_condType`="GT" `_targetType`="BUFF_OWNER"
    - **AlwaysExecuteNodeList** 
      - **IfTarget** `_targetType`="BUFF_OWNER"
      - **CalculateBlackboardValueViaParams** 
      - **CalculateBlackboardValueViaParams** 
- …（共 24 个节点，已截断）

**`titi_s_3[dmg_ticker]`** ← 事件 `ON_BUFF_START`

- **EnsureBlackboardDefaultValue** 
- **CalculateBlackboardValueViaParams** 
- **CalculateBlackboardValueViaParams** 

**`titi_s_3[dmg_ticker]`** ← 事件 `ON_BUFF_FINISH`

- **IfConditions** 
  - **FilterByBlackboardValue** `_condType`="GT" `_targetType`="BUFF_OWNER"
  - **FilterByBlackboardValue** `_condType`="GT" `_targetType`="BUFF_OWNER"
  - **IfTarget** `_targetType`="BUFF_OWNER"
  - **CalculateBlackboardValueViaParams** 
  - **CalculateBlackboardValueViaParams** 
  - **AdvancedApplyDamage** `_targetType`="BUFF_OWNER"
  - **CreateEffect** `_targetType`="BUFF_OWNER"
  - **PlayAudio** `_target`="BUFF_OWNER"

**`titi_s_3[dmg_ticker]`** ← 事件 `ON_OWNER_FINISH`

- **IfConditions** 
  - **FilterByBlackboardValue** `_condType`="GT" `_targetType`="BUFF_OWNER"
  - **FilterByBlackboardValue** `_condType`="GT" `_targetType`="BUFF_OWNER"
  - **CreateBuffInCircleRange** `_count`=1 `_targetType`="BUFF_OWNER" targetOptions(targetSide=ENEMY, targetMotion=ALL, targetCategory=DEFAULT, abnormalFlag=STUNNED)
  - **CreateBuffInCircleRange** `_count`=1 `_targetType`="BUFF_OWNER" targetOptions(targetSide=ENEMY, targetMotion=ALL, targetCategory=DEFAULT, abnormalFlag=STUNNED)
  - **IfConditions** 
    - **CheckAbnormalCombo** `_targetType`="BUFF_OWNER"
    - **CreateBuffInCircleRange** `_count`=1 `_targetType`="BUFF_OWNER" targetOptions(targetSide=ENEMY, targetMotion=ALL, targetCategory=DEFAULT, abnormalFlag=STUNNED)
    - **CreateBuffInCircleRange** `_count`=1 `_targetType`="BUFF_OWNER" targetOptions(targetSide=ENEMY, targetMotion=ALL, targetCategory=DEFAULT, abnormalFlag=STUNNED)

**`titi_s_3[doze]`** ← 事件 `ON_BEFORE_TRY_SET_HP_ZERO`

- **ConsumeTrySetHpZeroModifier** 
- **CheckContainsBuff** `_buffKeys`=["titi_s_3[doze_indoze]"] `_targetType`="BUFF_OWNER"
- **IfNot** 
- **CreateBuff** buffKey=`titi_s_3[doze_indoze]` templateKey=`titi_s_3[doze_indoze]` `maxStackCnt`=-1 `lifeTimeType`=INFINITY

**`titi_s_3[doze_indoze]`** ← 事件 `ON_BUFF_START`

- **CreateBuff** buffKey=`doze[inf]` `lifeTimeType`=LIMITED
- **CreateBuff** buffKey=`titi_s_3[heal]` 属性修改=[HP_RECOVERY_PER_SEC_BY_MAX_HP_RATIO ADDITION blackboard] `lifeTimeType`=INFINITY

**`titi_s_3[doze_indoze]`** ← 事件 `ON_OWNER_HP_FULL`

- **FinishBuff** 

**`titi_s_3[doze_indoze]`** ← 事件 `ON_BUFF_TRIGGER`

- **IfElse** 
  - **FilterByTargetHpRatio** `_condType`="EQUALS" `_targetType`="BUFF_OWNER"
  - **FinishBuff** 
  - **IfElse** 
    - **CheckAbnormalFlag** `_targetType`="BUFF_OWNER"
    - **FinishBuff** 

**`titi_s_3[effect_line]`** ← 事件 `ON_BUFF_START`

- **CreateLineEffect** `_targetType`="BUFF_OWNER"
- **PlayAudio** `_target`="BUFF_SOURCE"
- **PlayAudio** `_target`="BUFF_SOURCE"

**`titi_s_3[trigger_spread]`** ← 事件 `ON_BUFF_START`

- **TriggerAbility** `_targetType`="BUFF_OWNER"

**`titi_s_3[trigger_spread]`** ← 事件 `ON_BUFF_FINISH`

- **InterruptAbility** 

---

## 附：数据边界

| 项目 | 状态 |
|---|---|
| 属性 / 数值 / SP / 范围 / 抬手 | ✅ 明文可得 |
| buff 行为树 | ✅ 明文可得 |
| 技能 → 模板绑定 | ⚠️ 游戏只给 `prefabId`，真实绑定在不可解的 `.ab` 里；本文按命名规律 + `blackboard` 键名双向推断 |
| 动画资源本体 | ❌ 在 `.ab` 包内，不可解 |
| 抬手精度 | ✅ 1/30 秒，是动画事件时刻而非视觉起手帧 |
