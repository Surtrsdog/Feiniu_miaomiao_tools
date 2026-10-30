# 可露希尔 — 技能判定说明

> 数据来源：明文 JSON（`character_table` / `skill_table` / `range_table` / `buff_template_data` / `bakemuzzledata`）。不含反汇编或二进制解析内容。

## 一、干员底子

| 项 | 值 |
|---|---|
| ID | `char_4228_closur` |
| 职业 | 先锋 / `tactician` |
| 星级 | 6 星 |
| 生命（精二满级） | 1762 |
| 攻击（精二满级） | 480 |
| 防御（精二满级） | 131 |
| 法抗 | 0% |
| **攻击间隔 baseAttackTime** | **1 秒** |
| 攻速 attackSpeed | 100（100% = 无增减） |
| 阻挡 | 1 |
| 部署费用 | 15 |

**攻击间隔换算**（全干员通用）：

```
实际间隔 = baseAttackTime ÷ (attackSpeed / 100)
         = 1 ÷ 1.00 = 1.000 秒
```

## 二、抬手（攻击前摇）

来源：`bakemuzzledata/character/char_4228_closur_*.json` → `bakedAnimDatas.<组>.bakedEvents.<动画名>.eventTime`，取事件 `OnAttack` 时刻。

| 场景 | 动画名 | 抬手 | 帧数(30fps) |
|---|---|---|---|
| **普通攻击** | `Attack_Loop` | **0.4 秒** | 12 帧 |

> 占攻击间隔 40.0%（0.4 秒 / 1 秒）。开技能不会让抬手变快。

| 技能动画 | `Skill_2_Loop` | 0.4 秒 | 12 帧 |
| 技能动画 | `Skill_3_Loop` | 0.133333 秒 | 4 帧 |
| 技能动画 | `Skill_Down_2_Loop` | 0.4 秒 | 12 帧 |
| 技能动画 | `Skill_Down_3_Loop` | 0.133333 秒 | 4 帧 |


## 三、技能逐层拆解

---

### 递归策略　`skchr_closur_1`

**技能描述（最高级）：**

> 立即使自身的援军获得1层护盾（不叠加），技能持续时间内逐渐获得3点部署费用；部署后每使用过一次技能，获得的部署费用+1（最多提升至7点）


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WITH_TIME` | 随时间自动回复 |
| 初始 SP / 消耗 SP | 1 / 8 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 1 | 可存层数 |
| 释放方式 | `AUTO` | 自动释放 |
| 技能形态 | `限时技能` | 持续 8 秒 |
| duration / durationType | 8 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `cost` | 3 |
| `cost_per_add` | 1 |
| `cost_add_max` | 7 |
| `shield_cnt` | 1 |

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

**`closur_s_1[cost]`** ← 事件 `ON_BUFF_START`

- **AlwaysExecuteNodeList** 
  - **EnsureBlackboardDefaultValue** 
  - **AssignBuffBlackboardFromOthers** `_targetType`="BUFF_OWNER"
  - **CalculateBlackboardValueViaParams** 
  - **CalculateBlackboardValueViaParams** 
  - **CalculateBlackboardValueViaParams** 
  - **CreateBuff** buffKey=`closur_s_1[trigger_modify_cost]` templateKey=`closur_s_1[trigger_modify_cost]` `lifeTimeType`=LIMITED
  - **AddBuffBlackboard** `_targetType`="BUFF_OWNER"

**`closur_s_1[shield]`** ← 事件 `ON_BUFF_START`

- **TriggerAbility** `_targetType`="BUFF_OWNER"

**`closur_s_1[trigger_modify_cost]`** ← 事件 `ON_BUFF_TRIGGER`

- **IfElse** 
  - **FilterByBlackboardValue** `_condType`="GT" `_targetType`="BUFF_OWNER"
  - **CalculateBlackboardValueViaParams** 
  - **ModifyCost** 

---

### 模型扩展　`skchr_closur_2`

**技能描述（最高级）：**

> 立即获得10点部署费用，持续时间内逐渐获得15点部署费用，自身的援军防御力+60%，阻挡数+1，自身攻击力+80%，同时攻击2个目标且能攻击到自身援军阻挡的敌人；在战术点效果范围内部署干员时，立即返还部署费用的40%


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WITH_TIME` | 随时间自动回复 |
| 初始 SP / 消耗 SP | 34 / 40 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 1 | 可存层数 |
| 释放方式 | `MANUAL` | 手动释放 |
| 技能形态 | `限时技能` | 持续 30 秒 |
| duration / durationType | 30 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `cost` | 10 |
| `cost_return` | 0.4 |
| `block_cnt` | 1 |
| `def` | 0.6 |
| `atk` | 0.8 |
| `attack@max_target` | 2 |
| `cost_period` | 15 |
| `closur_s_2[add_cost_period].cost` | 1 |
| `closur_s_2[add_cost_period].interval` | 2 |

#### 攻击范围

`rangeId = 3-3`，12 格（direction=1）

> 该技能未指定自己的 `rangeId`，上图是干员**自身范围**。技能若扩大范围，会另有 `rangeId`。

```
■ ■ ■ ■ 
■ ■ ■ ■ 
■ ■ ■ ■ 
```

#### 判定链

> 匹配方式：由 `blackboard` 键名精确指认（层级 A）

**`closur_s_2[friend]`** ← 事件 `ON_BUFF_TRIGGER`

- **IfConditions** 
  - **IsCharacter** `_targetType`="BUFF_OWNER"
  - **FilterByBlackboardValue** `_condType`="GT" `_targetType`="BUFF_OWNER"
  - **IfConditions** 
    - **FilterCharacterLastDeathReason** 
    - **FilterCharacterLastDeathReason** 
    - **AssignAttributeToBB** `_targetType`="BUFF_OWNER"
    - **CalculateBlackboardValueViaParams** 
    - **RoundBuffBlackboard** `_targetType`="BUFF_OWNER"
    - **ModifyCost** 
    - **CreateEffect** `_targetType`="BUFF_OWNER"

**`closur_s_2[friend]`** ← 事件 `ON_BUFF_START`

- **IfElse** 
  - **CheckCharacterInBornState** 
  - **EnsureBlackboardDefaultValue** 

**`closur_s_2[switch]`** ← 事件 `ON_BUFF_START`

- **AlwaysExecuteNodeList** 
  - **SwitchDirection** `_source`="BUFF_OWNER"
    - **ModifyAnimatorHookerReplacePair** `_modeIndex`=1 `_target`="TARGET"
    - **ModifyAnimatorHookerReplacePair** `_modeIndex`=1 `_target`="TARGET"
    - **ModifyAnimatorHookerReplacePair** `_modeIndex`=1 `_target`="TARGET"
    - **ModifyAnimatorHookerReplacePair** `_modeIndex`=1 `_target`="TARGET"
  - **SwitchMode** `_modeIndex`=0 `_targetType`="TARGET"
  - **TriggerAbility** `_targetType`="BUFF_OWNER"
  - **CreateBuffToToken** `_targetType`="BUFF_SOURCE"

**`closur_s_2[switch]`** ← 事件 `ON_BUFF_FINISH`

- **SwitchMode** `_modeIndex`=0 `_targetType`="TARGET"
- **InterruptAbility** 
- **AlwaysNext** 
- **FinishTokenBuffsById** 

**`closur_s_2[trigger_extra]`** ← 事件 `ON_BUFF_START`

- **TriggerAbility** `_targetType`="BUFF_OWNER"

---

### Q.E.D.　`skchr_closur_3`

**技能描述（最高级）：**

> 技能持续时间内逐渐获得18点部署费用，攻击间隔缩短，锁定自身和援军原本攻击范围内的敌人进行攻击，造成可露希尔250%攻击力的物理伤害并施加持续3秒的6%迟钝效果（可叠加，最高60%），每攻击9次后攻击目标数+1（最多触发6次）


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WITH_TIME` | 随时间自动回复 |
| 初始 SP / 消耗 SP | 23 / 30 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 1 | 可存层数 |
| 释放方式 | `MANUAL` | 手动释放 |
| 技能形态 | `限时技能` | 持续 30 秒 |
| duration / durationType | 30 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `cost` | 0 |
| `cost_attack_add` | 0 |
| `attack_trigger_cnt` | 9 |
| `max_trigger_cnt` | 6 |
| `attack@atk_scale` | 2.5 |
| `base_attack_time` | -0.5 |
| `attack@slow_down` | 0.06 |
| `attack@slow_down_time` | 3 |
| `attack@max_stack_cnt` | 10 |
| `attack@slow_down_max` | 0.6 |
| `cost_period` | 18 |
| `closur_s_3[add_cost_period].cost` | 1 |
| `closur_s_3[add_cost_period].interval` | 1.66 |

#### 攻击范围

`rangeId = 3-3`，12 格（direction=1）

> 该技能未指定自己的 `rangeId`，上图是干员**自身范围**。技能若扩大范围，会另有 `rangeId`。

```
■ ■ ■ ■ 
■ ■ ■ ■ 
■ ■ ■ ■ 
```

#### 判定链

> 匹配方式：由 `blackboard` 键名精确指认（层级 A）

**`closur_s_3[attack_trigger]`** ← 事件 `ON_BUFF_START`

- **TriggerBuffsByKeys** `_buffKeys`=["closur_s_3[data]"] `_targetType`="BUFF_OWNER"

**`closur_s_3[data]`** ← 事件 `ON_BUFF_TRIGGER`

- **CalculateBlackboardValueViaParams** 
- **IfConditions** 
  - **FilterByBlackboardValue** `_condType`="LT" `_targetType`="BUFF_OWNER"
  - **FilterByBlackboardValue** `_condType`="GE" `_targetType`="BUFF_OWNER"
  - **AlwaysExecuteNodeList** 
    - **CalculateBlackboardValueViaParams** 
    - **CalculateBlackboardValueViaParams** 
    - **UpdateAttackSelectorByBlackboard** `_modeIndex`=2 `_targetType`="BUFF_OWNER"
    - **CalculateBlackboardValueViaParams** 

**`closur_s_3[data]`** ← 事件 `ON_BUFF_START`

- **UpdateAttackSelectorByBlackboard** `_modeIndex`=2 `_targetType`="BUFF_OWNER"

**`closur_s_3[eff]`** ← 事件 `ON_BUFF_START`

- **IfElse** 
  - **CheckContainsBuff** `_buffKeys`=["closur_s_3[eff_airplane_mark]"] `_targetType`="BUFF_OWNER"
  - **EnsureBlackboardDefaultValue** 
  - **EnsureBlackboardDefaultValue** 
- **AlwaysNext** 
- **CreateBuff** buffKey=`closur_s_3[eff_airplane_mark]` `overrideType`=EXTEND `lifeTimeType`=LIMITED
- **FilterByBlackboardValue** `_condType`="GT" `_targetType`="BUFF_OWNER"
- **CreateEffect** `_targetType`="BUFF_OWNER"

**`closur_s_3[switch]`** ← 事件 `ON_BUFF_START`

- **AlwaysExecuteNodeList** 
  - **SwitchDirection** `_source`="BUFF_OWNER"
    - **ModifyAnimatorHookerReplacePair** `_modeIndex`=2 `_target`="TARGET"
    - **ModifyAnimatorHookerReplacePair** `_modeIndex`=2 `_target`="TARGET"
    - **ModifyAnimatorHookerReplacePair** `_modeIndex`=2 `_target`="TARGET"
    - **ModifyAnimatorHookerReplacePair** `_modeIndex`=2 `_target`="TARGET"
  - **SwitchMode** `_modeIndex`=0 `_targetType`="TARGET"
  - **TriggerAbility** `_targetType`="BUFF_OWNER"
  - **CreateBuffToToken** `_targetType`="BUFF_SOURCE"

**`closur_s_3[switch]`** ← 事件 `ON_BUFF_FINISH`

- **SwitchMode** `_modeIndex`=0 `_targetType`="TARGET"
- **InterruptAbility** 
- **AlwaysNext** 
- **FinishTokenBuffsById** 

---

## 附：数据边界

| 项目 | 状态 |
|---|---|
| 属性 / 数值 / SP / 范围 / 抬手 | ✅ 明文可得 |
| buff 行为树 | ✅ 明文可得 |
| 技能 → 模板绑定 | ⚠️ 游戏只给 `prefabId`，真实绑定在不可解的 `.ab` 里；本文按命名规律 + `blackboard` 键名双向推断 |
| 动画资源本体 | ❌ 在 `.ab` 包内，不可解 |
| 抬手精度 | ✅ 1/30 秒，是动画事件时刻而非视觉起手帧 |
