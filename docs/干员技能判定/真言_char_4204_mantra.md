# 真言 — 技能判定说明

> 数据来源：明文 JSON（`character_table` / `skill_table` / `range_table` / `buff_template_data` / `bakemuzzledata`）。不含反汇编或二进制解析内容。

## 一、干员底子

| 项 | 值 |
|---|---|
| ID | `char_4204_mantra` |
| 职业 | 术师 / `primcaster` |
| 星级 | 6 星 |
| 生命（精二满级） | 1428 |
| 攻击（精二满级） | 695 |
| 防御（精二满级） | 130 |
| 法抗 | 1500% |
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

来源：`bakemuzzledata/character/char_4204_mantra_*.json` → `bakedAnimDatas.<组>.bakedEvents.<动画名>.eventTime`，取事件 `OnAttack` 时刻。

| 场景 | 动画名 | 抬手 | 帧数(30fps) |
|---|---|---|---|
| **普通攻击** | `Attack` | **0.433333 秒** | 13 帧 |

> 占攻击间隔 27.1%（0.433333 秒 / 1.6 秒）。开技能不会让抬手变快。

| 技能动画 | `Skill_1` | 0.433333 秒 | 13 帧 |
| 技能动画 | `Skill_3_Loop` | 0.466667 秒 | 14 帧 |


## 三、技能逐层拆解

---

### 共鸣溃缩　`skchr_mantra_1`

**技能描述（最高级）：**

> 下次攻击造成攻击力325%的法术伤害并附带伤害30%的神经损伤，若目标处于神经损伤爆发期间则额外造成200%攻击力的元素伤害


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WHEN_ATTACK` | 每次攻击回复 |
| 初始 SP / 消耗 SP | 0 / 2 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 1 | 可存层数 |
| 释放方式 | `AUTO` | 自动释放 |
| 技能形态 | `无限持续` | 开启后一直生效，直到手动关闭或条件结束 |
| duration / durationType | -1 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `atk_scale` | 3.25 |
| `ep_damage_ratio` | 0.3 |
| `element_atk_scale` | 2 |

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

**`mantra_s_1`** ← 事件 `ON_BUFF_START`

- **ApplyElementDamage** `_targetType`="BUFF_OWNER"

---

### 意识联协　`skchr_mantra_2`

**技能描述（最高级）：**

> 攻击间隔缩短，攻击造成攻击力240%的法术伤害并以短暂间隔跳跃至其他3名敌人造成攻击力120%的法术伤害，均附带伤害18%的神经损伤，若目标处于神经损伤爆发期间附带25%攻击力的元素伤害


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WITH_TIME` | 随时间自动回复 |
| 初始 SP / 消耗 SP | 18 / 25 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 1 | 可存层数 |
| 释放方式 | `MANUAL` | 手动释放 |
| 技能形态 | `限时技能` | 持续 25 秒 |
| duration / durationType | 25 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `base_attack_time` | -0.8 |
| `attack@atk_scale` | 2.4 |
| `attack@chain.atk_scale` | 1.2 |
| `attack@ep_damage_ratio` | 0.18 |
| `attack@times` | 4 |
| `chain_times` | 3 |
| `attack@element_atk_scale` | 0.25 |

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

**`mantra_s_2[ep]`** ← 事件 `ON_BUFF_START`

- **ApplyElementDamage** `_targetType`="BUFF_OWNER"

---

### 无言为真　`skchr_mantra_3`

**技能描述（最高级）：**

> 攻击范围扩大，范围内敌人隐匿失效且麻痹层数上限降为2，攻击力+275%同时攻击2个目标，范围中干员开启技能时（包括自身）使范围内敌人获得2层麻痹（至多3次），范围内敌人麻痹层数每超过上限1层在目标及1名敌人间跳跃1次185%攻击力的元素伤害，跳跃间存在短暂间隔


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WITH_TIME` | 随时间自动回复 |
| 初始 SP / 消耗 SP | 31 / 40 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 1 | 可存层数 |
| 释放方式 | `MANUAL` | 手动释放 |
| 技能形态 | `限时技能` | 持续 40 秒 |
| duration / durationType | 40 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `atk` | 2.75 |
| `attack@max_target` | 2 |
| `atk_scale` | 1.85 |
| `max_target` | 2 |
| `chain_times` | 1 |
| `max_trigger_cnt` | 3 |
| `interval_projectile_trigger` | 1.5 |
| `per_active` | 2 |

#### 攻击范围

`rangeId = 3-17`，18 格（direction=1）

```
· ■ ■ ■ 
■ ■ ■ ■ 
■ ■ ■ ■ 
■ ■ ■ ■ 
· ■ ■ ■ 
```

#### 判定链

> 匹配方式：按命名规则匹配（层级 B）

**`mantra_s_3[ally]`** ← 事件 `ON_SKILL_START`

- **IfConditions** 
  - **FilterByBlackboardValue** `_condType`="LT" `_targetType`="BUFF_SOURCE"
  - **IfContainsTargetsInAttackRange** targetOptions(targetSide=ENEMY, targetMotion=ALL, targetCategory=DEFAULT, abnormalFlag=INVISIBLE)
  - **AddBuffBlackboard** `_targetType`="BUFF_SOURCE"
  - **Loop** 
    - **CreateBuffInRange** `_targetType`="BUFF_SOURCE" targetOptions(targetSide=ENEMY, targetMotion=ALL, targetCategory=DEFAULT, abnormalFlag=INVISIBLE)

**`mantra_s_3[ally]`** ← 事件 `ON_BUFF_START`

- **IfElse** 
  - **FilterInSourceSkillRangeId** `_target`="BUFF_OWNER" `_source`="BUFF_SOURCE"
  - **EnsureBlackboardDefaultValue** 
  - **FinishBuff** 

**`mantra_s_3[ally]`** ← 事件 `ON_TOGGLE_SKILL_START`

- **IfConditions** 
  - **FilterByBlackboardValue** `_condType`="LT" `_targetType`="BUFF_SOURCE"
  - **IfContainsTargetsInAttackRange** targetOptions(targetSide=ENEMY, targetMotion=ALL, targetCategory=DEFAULT, abnormalFlag=INVISIBLE)
  - **AddBuffBlackboard** `_targetType`="BUFF_SOURCE"
  - **Loop** 
    - **CreateBuffInRange** `_targetType`="BUFF_SOURCE" targetOptions(targetSide=ENEMY, targetMotion=ALL, targetCategory=DEFAULT, abnormalFlag=INVISIBLE)

**`mantra_s_3[enemy]`** ← 事件 `ON_BUFF_START`

- **EnsureBlackboardDefaultValue** 
- **CalculateBlackboardValueViaParams** 
- **CreateBuff** buffKey=`mantra_s_3[enemy_trigger]` templateKey=`mantra_s_3[enemy_trigger]` `overrideType`=UNIQUE `lifeTimeType`=INFINITY
- **EnsureBlackboardDefaultValue** 

**`mantra_s_3[enemy]`** ← 事件 `ON_PALSY_OVERFLOW`

- **AddBuffBlackboard** `_targetType`="BUFF_OWNER"

**`mantra_s_3[enemy]`** ← 事件 `ON_BUFF_FINISH`

- **PalsyBuffMaxCntUpdate** `_targetType`="BUFF_OWNER"

**`mantra_s_3[enemy]`** ← 事件 `ON_BUFF_TRIGGER`

- **PalsyBuffMaxCntUpdate** `_targetType`="BUFF_OWNER"

**`mantra_s_3[enemy_trigger]`** ← 事件 `ON_BUFF_TRIGGER`

- **IfElse** 
  - **FilterByBlackboardValue** `_condType`="GT" `_targetType`="BUFF_OWNER"
  - **IfElse** 
    - **FilterByBlackboardValue** `_condType`="GT" `_targetType`="BUFF_OWNER"
    - **CalculateBlackboardValueViaParams** 
    - **IfElse** 
      - **FilterByBlackboardValue** `_condType`="GT" `_targetType`="BUFF_OWNER"
      - **CalculateBlackboardValueViaParams** 
      - **EmitProjectile** `_targetType`="BUFF_OWNER"
        - **AdvancedApplyDamage** `_targetType`="TARGET"
        - **AlwaysNext** 
        - **PlayProjectileAudio** 
      - **CalculateBlackboardValueViaParams** 
    - **CalculateBlackboardValueViaParams** 
  - **IfElse** 
    - **FilterByBlackboardValue** `_condType`="GT" `_targetType`="BUFF_OWNER"
- …（共 23 个节点，已截断）

**`mantra_s_3[enemy_trigger]`** ← 事件 `ON_BUFF_START`

- **EnsureBlackboardDefaultValue** 

**`mantra_s_3[enemy_trigger]`** ← 事件 `ON_BUFF_FINISH`

- **IfConditions** 
  - **FilterByBlackboardValue** `_condType`="GT" `_targetType`="BUFF_OWNER"
  - **IfTarget** `_targetType`="BUFF_SOURCE"
  - **Loop** 
    - **EmitProjectile** `_targetType`="BUFF_OWNER"
      - **AdvancedApplyDamage** `_targetType`="TARGET"
      - **AlwaysNext** 
      - **PlayProjectileAudio** 

**`mantra_s_3[self]`** ← 事件 `ON_BUFF_START`

- **TriggerAbility** `_targetType`="BUFF_OWNER"
- **EnsureBlackboardDefaultValue** 

**`mantra_s_3[self]`** ← 事件 `ON_BUFF_FINISH`

- **InterruptAbility** 

**`mantra_s_3[self]`** ← 事件 `ON_BUFF_TRIGGER`

- **IfConditions** 
  - **FilterByBlackboardValue** `_condType`="LT" `_targetType`="BUFF_SOURCE"
  - **IfContainsTargetsInAttackRange** targetOptions(targetSide=ENEMY, targetMotion=ALL, targetCategory=DEFAULT, abnormalFlag=INVISIBLE)
  - **AddBuffBlackboard** `_targetType`="BUFF_SOURCE"
  - **Loop** 
    - **CreateBuffInRange** `_targetType`="BUFF_SOURCE" targetOptions(targetSide=ENEMY, targetMotion=ALL, targetCategory=DEFAULT, abnormalFlag=INVISIBLE)

---

## 附：数据边界

| 项目 | 状态 |
|---|---|
| 属性 / 数值 / SP / 范围 / 抬手 | ✅ 明文可得 |
| buff 行为树 | ✅ 明文可得 |
| 技能 → 模板绑定 | ⚠️ 游戏只给 `prefabId`，真实绑定在不可解的 `.ab` 里；本文按命名规律 + `blackboard` 键名双向推断 |
| 动画资源本体 | ❌ 在 `.ab` 包内，不可解 |
| 抬手精度 | ✅ 1/30 秒，是动画事件时刻而非视觉起手帧 |
