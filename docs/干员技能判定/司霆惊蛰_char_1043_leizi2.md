# 司霆惊蛰 — 技能判定说明

> 数据来源：明文 JSON（`character_table` / `skill_table` / `range_table` / `buff_template_data` / `bakemuzzledata`）。不含反汇编或二进制解析内容。

## 一、干员底子

| 项 | 值 |
|---|---|
| ID | `char_1043_leizi2` |
| 职业 | 近卫 / `librator` |
| 星级 | 6 星 |
| 生命（精二满级） | 3863 |
| 攻击（精二满级） | 360 |
| 防御（精二满级） | 491 |
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

### 浩气长存　`skchr_leizi2_1`

**技能描述（最高级）：**

> 攻击范围朝前方和两侧扩大。对三个方向的地面敌人各造成相当于攻击力355%的物理伤害
> 可充能3次，充能耗尽前特性不重置


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WITH_TIME` | 随时间自动回复 |
| 初始 SP / 消耗 SP | 17 / 11 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 3 | 可存层数 |
| 释放方式 | `MANUAL` | 手动释放 |
| 技能形态 | `无限持续` | 开启后一直生效，直到手动关闭或条件结束 |
| duration / durationType | -1 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `attack@atk_scale_s1` | 3.55 |

#### 攻击范围

`rangeId = 3-19`，10 格（direction=1）

```
■ · · · 
■ · · · 
■ · · · 
■ ■ ■ ■ 
■ · · · 
■ · · · 
■ · · · 
```

#### 判定链

> 匹配方式：按命名规则匹配（层级 B）

**`leizi2_s_1`** ← 事件 `ON_BUFF_START`

- **SwitchMode** `_modeIndex`=1 `_targetType`="BUFF_OWNER"

**`leizi2_s_1`** ← 事件 `ON_BUFF_FINISH`

- **SwitchMode** `_modeIndex`=2 `_targetType`="BUFF_OWNER"

**`leizi2_s_1[effect_controller]`** ← 事件 `ON_BUFF_TRIGGER`

- **IfElse** 
  - **CompareCharSkillAvailableCnt** `_condType`="LE" `_count`=0 `_targetType`="BUFF_OWNER"
  - **FinishDerivedBuff** 
  - **IfElse** 
    - **CheckContainsBuff** `_buffKeys`=["leizi2_s_1[effect_1]"] `_targetType`="BUFF_OWNER"
    - **CreateBuff** buffKey=`leizi2_s_1[effect_1]` `lifeTimeType`=INFINITY
  - **AlwaysNext** 
  - **IfElse** 
    - **CompareCharSkillAvailableCnt** `_condType`="LE" `_count`=1 `_targetType`="BUFF_OWNER"
    - **FinishBuffsById** `_targetType`="BUFF_OWNER"
    - **AlwaysNext** 
    - **FinishBuffsById** `_targetType`="BUFF_OWNER"
    - **IfElse** 
      - **CheckContainsBuff** `_buffKeys`=["leizi2_s_1[effect_2]"] `_targetType`="BUFF_OWNER"
      - **CreateBuff** buffKey=`leizi2_s_1[effect_2]` `lifeTimeType`=INFINITY
  - **AlwaysNext** 
- …（共 22 个节点，已截断）

**`leizi2_s_1[effect_controller]`** ← 事件 `ON_SKILL_FINISH`


**`leizi2_s_1[ready]`** ← 事件 `ON_SKILL_START`

- **FinishBuff** 
- **TriggerBuffsByKeys** `_buffKeys`=["leizi2_s_1[effect_controller]"] `_targetType`="BUFF_OWNER"

**`leizi2_s_1[ready]`** ← 事件 `ON_BUFF_START`

- **TriggerBuffsByKeys** `_buffKeys`=["leizi2_s_1[effect_controller]"] `_targetType`="BUFF_OWNER"

**`leizi2_s_1[revert]`** ← 事件 `ON_BUFF_START`

- **FinishBuffsById** `_targetType`="BUFF_OWNER"
- **AlwaysNext** 
- **FinishBuffsById** `_targetType`="BUFF_OWNER"

**`leizi2_s_1[times]`** ← 事件 `ON_BUFF_START`

- **IfElse** 
  - **CompareCharSkillAvailableCnt** `_condType`="LE" `_count`=0 `_targetType`="BUFF_OWNER"
  - **ModifyAbilityBlackboard** 
  - **AlwaysNext** 
  - **ModifyAbilityBlackboard** 
  - **AlwaysNext** 
  - **ModifyAbilityBlackboard** 

**`leizi2_s_1[times]`** ← 事件 `ON_BUFF_FINISH`

- **ModifyAbilityBlackboard** 
- **AlwaysNext** 
- **ModifyAbilityBlackboard** 
- **AlwaysNext** 
- **ModifyAbilityBlackboard** 

---

### 正霆摄威　`skchr_leizi2_2`

**技能描述（最高级）：**

> 攻击范围沿地面地块扩展至最远三格，攻击对4个目标造成相当于攻击力150%的物理伤害。技能期间每次落雷使攻击力+10%（最多可叠加25次）


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WITH_TIME` | 随时间自动回复 |
| 初始 SP / 消耗 SP | 22 / 43 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 1 | 可存层数 |
| 释放方式 | `MANUAL` | 手动释放 |
| 技能形态 | `限时技能` | 持续 36 秒 |
| duration / durationType | 36 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `attack@atk_scale_s2` | 1.5 |
| `attack@max_target_s2` | 4 |
| `thunder_atk` | 0.1 |
| `thunder_max_stack_cnt` | 25 |

#### 攻击范围

`rangeId = 1-2`，4 格（direction=1）

> 该技能未指定自己的 `rangeId`，上图是干员**自身范围**。技能若扩大范围，会另有 `rangeId`。

```
■ · 
■ ■ 
■ · 
```

#### 判定链

> 匹配方式：按命名规则匹配（层级 B）

**`leizi2_s_2`** ← 事件 `ON_BUFF_START`

- **SwitchMode** `_modeIndex`=3 `_targetType`="BUFF_OWNER"

**`leizi2_s_2`** ← 事件 `ON_BUFF_FINISH`

- **SwitchMode** `_modeIndex`=5 `_targetType`="BUFF_OWNER"
- **AlwaysNext** 
- **FinishBuffsById** `_targetType`="BUFF_OWNER"

**`leizi2_s_2[range]`** ← 事件 `ON_BUFF_START`

- **ForceUpdateRange** 

**`leizi2_s_2[try_add_atk]`** ← 事件 `ON_BUFF_START`

- **IfElse** 
  - **CheckContainsBuff** `_buffKeys`=["leizi2_s_2"] `_targetType`="BUFF_OWNER"
  - **AssignBuffBlackboardFromOthers** `_targetType`="BUFF_OWNER"
  - **AssignBuffBlackboardFromOthers** `_targetType`="BUFF_OWNER"
  - **CreateBuff** buffKey=`leizi2_s_2[atk]` 属性修改=[ATK MULTIPLIER blackboard] `overrideType`=STACK `lifeTimeType`=INFINITY

---

### 天地通明　`skchr_leizi2_3`

**技能描述（最高级）：**

> 攻击范围扩大，攻击间隔大幅延长，攻击造成攻击力300%的范围物理伤害，目标位置产生朝四周流动三格的电流。电流碰到自身或高台时反弹，电流所在地块上所有敌人每0.6秒受到司霆惊蛰攻击力70%的法术伤害，且有15%概率战栗3秒


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WITH_TIME` | 随时间自动回复 |
| 初始 SP / 消耗 SP | 21 / 36 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 1 | 可存层数 |
| 释放方式 | `MANUAL` | 手动释放 |
| 技能形态 | `限时技能` | 持续 24 秒 |
| duration / durationType | 24 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `attack@atk_scale_s3` | 3 |
| `base_attack_time` | 1.7 |
| `attack@range_radius` | 1.65 |
| `attack@atk_scale_current` | 0.7 |
| `prob` | 0.15 |
| `not_combat` | 3 |

#### 攻击范围

`rangeId = 2-1`，9 格（direction=1）

```
■ · · 
■ ■ · 
■ ■ ■ 
■ ■ · 
■ · · 
```

#### 判定链

> 匹配方式：按命名规则匹配（层级 B）

**`leizi2_s_3`** ← 事件 `ON_BUFF_START`

- **SwitchMode** `_modeIndex`=6 `_targetType`="BUFF_OWNER"

**`leizi2_s_3`** ← 事件 `ON_BUFF_FINISH`

- **SwitchMode** `_modeIndex`=8 `_targetType`="BUFF_OWNER"

**`leizi2_s_3`** ← 事件 `ON_OUTPUT_MODIFIER`

- **IfElse** 
  - **FilterDamageModifer** `_source`="BUFF_OWNER"
  - **IfElse** 
    - **CheckModifierContainsKey** 
    - **Dice** 
    - **CreateBuff** buffKey=`disarmed_combat` `lifeTimeType`=LIMITED

---

## 附：数据边界

| 项目 | 状态 |
|---|---|
| 属性 / 数值 / SP / 范围 / 抬手 | ✅ 明文可得 |
| buff 行为树 | ✅ 明文可得 |
| 技能 → 模板绑定 | ⚠️ 游戏只给 `prefabId`，真实绑定在不可解的 `.ab` 里；本文按命名规律 + `blackboard` 键名双向推断 |
| 动画资源本体 | ❌ 在 `.ab` 包内，不可解 |
| 抬手精度 | ✅ 1/30 秒，是动画事件时刻而非视觉起手帧 |
