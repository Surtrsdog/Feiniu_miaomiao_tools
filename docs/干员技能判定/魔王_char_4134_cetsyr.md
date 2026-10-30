# 魔王 — 技能判定说明

> 数据来源：明文 JSON（`character_table` / `skill_table` / `range_table` / `buff_template_data` / `bakemuzzledata`）。不含反汇编或二进制解析内容。

## 一、干员底子

| 项 | 值 |
|---|---|
| ID | `char_4134_cetsyr` |
| 职业 | 辅助 / `bard` |
| 星级 | 6 星 |
| 生命（精二满级） | 1628 |
| 攻击（精二满级） | 369 |
| 防御（精二满级） | 236 |
| 法抗 | 0% |
| **攻击间隔 baseAttackTime** | **1.3 秒** |
| 攻速 attackSpeed | 100（100% = 无增减） |
| 阻挡 | 1 |
| 部署费用 | 10 |

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

### 往昔萦绕身旁　`skchr_cetsyr_1`

**技能描述（最高级）：**

> 自身特性效果提高至35%，“微尘”的重生速度加快
> 持续时间无限


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WITH_TIME` | 随时间自动回复 |
| 初始 SP / 消耗 SP | 0 / 65 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 1 | 可存层数 |
| 释放方式 | `AUTO` | 自动释放 |
| 技能形态 | `无限持续` | 开启后一直生效，直到手动关闭或条件结束 |
| duration / durationType | -1 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `attack@atk_to_hp_recovery_ratio` | 0.35 |
| `talent_cool_down` | 3 |

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

**`cetsyr_s_1[trigger_talent]`** ← 事件 `ON_BUFF_START`

- **SwitchMode** `_modeIndex`=1 `_targetType`="TARGET"
- **ModifyAbilityBlackboard** 
- **ModifyAbilityBlackboard** 
- **ModifyAbilityBlackboard** 
- **TriggerAbility** `_targetType`="BUFF_OWNER"

---

### 明日渺远不及　`skchr_cetsyr_2`

**技能描述（最高级）：**

> “微尘”上限+3，立刻获得6枚“微尘”，“微尘”旋转半径扩大，攻击范围内所有其他友方单位获得相当于魔王100%攻击力的鼓舞效果，“微尘”不再碰撞友方干员，“微尘”碰撞敌方单位时造成相当于魔王攻击力275%的真实伤害，并使目标束缚3.5秒


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WITH_TIME` | 随时间自动回复 |
| 初始 SP / 消耗 SP | 20 / 35 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 1 | 可存层数 |
| 释放方式 | `MANUAL` | 手动释放 |
| 技能形态 | `限时技能` | 持续 35 秒 |
| duration / durationType | 35 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `extra_cnt` | 6 |
| `outside_radius` | 2 |
| `attack@atk` | 1 |
| `atk_scale` | 2.75 |
| `unmoveable_duration` | 3.5 |
| `dynamic_spd` | 0.9 |

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

**`cetsyr_s_2`** ← 事件 `ON_OUTPUT_DAMAGE`

- **CreateBuff** buffKey=`cetsyr_s_2[unmoveable]` `lifeTimeType`=LIMITED

**`cetsyr_s_2`** ← 事件 `ON_BUFF_START`

- **ModifyAbilityBlackboard** 
- **ModifyAbilityBlackboard** 
- **ModifyAbilityBlackboard** 
- **ModifyAbilityBlackboard** 
- **ModifyAbilityBlackboard** 
- **ModifyAbilityBlackboard** 
- **TriggerAbility** `_targetType`="BUFF_OWNER"
- **SwitchMode** `_modeIndex`=2 `_targetType`="TARGET"

**`cetsyr_s_2`** ← 事件 `ON_BUFF_FINISH`

- **ModifyAbilityBlackboard** 
- **ModifyAbilityBlackboard** 
- **ModifyAbilityBlackboard** 
- **ModifyAbilityBlackboard** 
- **ModifyAbilityBlackboard** 
- **ModifyAbilityBlackboard** 
- **TriggerAbility** `_targetType`="BUFF_OWNER"
- **SwitchMode** `_modeIndex`=0 `_targetType`="TARGET"

---

### 编织重构现世　`skchr_cetsyr_3`

**技能描述（最高级）：**

> 攻击范围扩大，自身特性效果提高至90%，“微尘”不再消失，攻击范围内所有其它友方单位获得相当于魔王100%的最大生命值的鼓舞效果，每隔2秒重新分配攻击范围内所有友方单位的生命


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WITH_TIME` | 随时间自动回复 |
| 初始 SP / 消耗 SP | 35 / 55 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 1 | 可存层数 |
| 释放方式 | `MANUAL` | 手动释放 |
| 技能形态 | `限时技能` | 持续 30 秒 |
| duration / durationType | 30 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `attack@atk_to_hp_recovery_ratio` | 0.9 |
| `max_hp` | 1 |
| `attack@cetsyr_s_3[cal_hp_ratio].interval` | 2 |
| `attack@cetsyr_s_3[collect_hp_ratio].interval` | 2 |

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

**`cetsyr_s_3`** ← 事件 `ON_BUFF_START`

- **SwitchMode** `_modeIndex`=3 `_targetType`="TARGET"
- **ModifyAbilityBlackboard** 
- **ModifyAbilityBlackboard** 
- **TriggerAbility** `_targetType`="BUFF_OWNER"

**`cetsyr_s_3`** ← 事件 `ON_BUFF_FINISH`

- **SwitchMode** `_modeIndex`=0 `_targetType`="TARGET"
- **ModifyAbilityBlackboard** 
- **ModifyAbilityBlackboard** 
- **TriggerAbility** `_targetType`="BUFF_OWNER"

**`cetsyr_s_3[cal_hp_ratio]`** ← 事件 `ON_BUFF_TRIGGER`

- **CalculateBlackboardValueViaParams** 
- **CreateBuffInRange** `_targetType`="BUFF_OWNER" targetOptions(targetSide=ALLY, targetMotion=ALL, targetCategory=DEFAULT, abnormalFlag=STUNNED)
- **AssignValueToBB** 
- **AssignValueToBB** 
- **AssignValueToBB** 

**`cetsyr_s_3[collect_hp_ratio]`** ← 事件 `ON_BUFF_TRIGGER`

- **CreateBuffInRange** `_targetType`="BUFF_OWNER" targetOptions(targetSide=ALLY, targetMotion=ALL, targetCategory=DEFAULT, abnormalFlag=STUNNED)
- **CreateEffect** `_targetType`="BUFF_OWNER"

**`cetsyr_s_3[record_cur_hp_ratio]`** ← 事件 `ON_BUFF_START`

- **IfTarget** `_targetType`="BUFF_OWNER"
- **RecordCurrentHpRatio** 
- **AssignBuffBlackboard** `_targetType`="BUFF_SOURCE"
- **AddBuffBlackboard** `_targetType`="BUFF_SOURCE"
- **RecordCurrentHpRatio** 
- **AssignBuffBlackboard** `_targetType`="BUFF_SOURCE"
- **AddBuffBlackboard** `_targetType`="BUFF_SOURCE"

**`cetsyr_s_3[set_hp_ratio]`** ← 事件 `ON_BUFF_START`

- **EqualizeTargetHpRatio** `_target`="BUFF_OWNER" `_source`="SOURCE"

---

## 附：数据边界

| 项目 | 状态 |
|---|---|
| 属性 / 数值 / SP / 范围 / 抬手 | ✅ 明文可得 |
| buff 行为树 | ✅ 明文可得 |
| 技能 → 模板绑定 | ⚠️ 游戏只给 `prefabId`，真实绑定在不可解的 `.ab` 里；本文按命名规律 + `blackboard` 键名双向推断 |
| 动画资源本体 | ❌ 在 `.ab` 包内，不可解 |
| 抬手精度 | ✅ 1/30 秒，是动画事件时刻而非视觉起手帧 |
