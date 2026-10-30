# 丰川祥子 — 技能判定说明

> 数据来源：明文 JSON（`character_table` / `skill_table` / `range_table` / `buff_template_data` / `bakemuzzledata`）。不含反汇编或二进制解析内容。

## 一、干员底子

| 项 | 值 |
|---|---|
| ID | `char_4182_oblvns` |
| 职业 | 近卫 / `lord` |
| 星级 | 6 星 |
| 生命（精二满级） | 2056 |
| 攻击（精二满级） | 725 |
| 防御（精二满级） | 425 |
| 法抗 | 1000% |
| **攻击间隔 baseAttackTime** | **1.3 秒** |
| 攻速 attackSpeed | 100（100% = 无增减） |
| 阻挡 | 2 |
| 部署费用 | 20 |

**攻击间隔换算**（全干员通用）：

```
实际间隔 = baseAttackTime ÷ (attackSpeed / 100)
         = 1.3 ÷ 1.00 = 1.300 秒
```

## 二、抬手（攻击前摇）

来源：`bakemuzzledata/character/char_4182_oblvns_*.json` → `bakedAnimDatas.<组>.bakedEvents.<动画名>.eventTime`，取事件 `OnAttack` 时刻。

| 场景 | 动画名 | 抬手 | 帧数(30fps) |
|---|---|---|---|
| **普通攻击** | `Attack` | **0.266667 秒** | 8 帧 |

> 占攻击间隔 20.5%（0.266667 秒 / 1.3 秒）。开技能不会让抬手变快。

| 技能动画 | `Skill_1` | 0.266667 秒 | 8 帧 |
| 技能动画 | `Skill_2_Loop_A` | 0.266667 秒 | 8 帧 |
| 技能动画 | `Skill_2_Loop_B` | 0.266667 秒 | 8 帧 |
| 技能动画 | `Skill_3_Loop` | 0.2 秒 | 6 帧 |


## 三、技能逐层拆解

---

### 新月的苏醒　`skchr_oblvns_1`

**技能描述（最高级）：**

> 演奏出8个音符。每个音符造成的法术伤害依次从攻击力的100%逐渐降低至5%。
> 可充能2次，充能至最大层数时自动释放一次


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WHEN_ATTACK` | 每次攻击回复 |
| 初始 SP / 消耗 SP | 0 / 3 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 2 | 可存层数 |
| 释放方式 | `MANUAL` | 手动释放 |
| 技能形态 | `无限持续` | 开启后一直生效，直到手动关闭或条件结束 |
| duration / durationType | -1 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `atk_scale` | 1 |
| `atk_scale_2` | 0.92 |
| `atk_scale_3` | 0.75 |
| `atk_scale_4` | 0.58 |
| `atk_scale_5` | 0.42 |
| `atk_scale_6` | 0.33 |
| `atk_scale_7` | 0.17 |
| `atk_scale_8` | 0.05 |
| `angle` | 15 |

#### 攻击范围

`rangeId = 3-12`，8 格（direction=1）

> 该技能未指定自己的 `rangeId`，上图是干员**自身范围**。技能若扩大范围，会另有 `rangeId`。

```
■ ■ · · 
■ ■ ■ ■ 
■ ■ · · 
```

#### 判定链

> 匹配方式：按命名规则匹配（层级 B）

**`oblvns_s_1[clear_full]`** ← 事件 `ON_BUFF_FINISH`

- **FinishBuffsById** `_targetType`="BUFF_OWNER"

**`oblvns_s_1[clear_full]`** ← 事件 `ON_BUFF_START`

- **IfConditions** 
  - **IsInFever** 
  - **IsFeverFull** 
  - **PlayAudio** `_target`="BUFF_OWNER"

**`oblvns_s_1[fever]`** ← 事件 `ON_AFTER_ATTACK`

- **ModifySp** `_targetType`="BUFF_OWNER" `_forceFlag`=True

**`oblvns_s_1[self]`** ← 事件 `ON_BUFF_TRIGGER`

- **IfElse** 
  - **FilterByTargetSpRatio** `_condType`="GE" `_targetType`="BUFF_OWNER"
  - **IfElse** 
    - **CheckCharSkillAffecting** `_targetType`="BUFF_OWNER"
    - **IfElse** 
      - **CheckContainsBuff** `_buffKeys`=["oblvns_s_1[self][no_auto_fever]"] `_targetType`="BUFF_OWNER"
      - **CreateBuff** buffKey=`oblvns_s_1[self][no_auto_fever]` templateKey=`oblvns_s_1[self][no_auto_fever]` `lifeTimeType`=INFINITY

**`oblvns_s_1[self][no_auto_fever]`** ← 事件 `ON_BUFF_TRIGGER`

- **TriggerSkill** `_targetType`="BUFF_OWNER"

---

### 满月的舞会　`skchr_oblvns_2`

**技能描述（最高级）：**

> 可以切换钢琴（初始）或风琴音色演奏：
> 钢琴：攻击力+110%，音符飞行速度加快，命中目标后穿过敌人造成物理伤害
> 风琴：攻击速度+140，音符造成法术伤害且飞行速度减缓 
> Fever期间变为当前音色的二连击


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WHEN_ATTACK` | 每次攻击回复 |
| 初始 SP / 消耗 SP | 0 / 5 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 1 | 可存层数 |
| 释放方式 | `MANUAL` | 手动释放 |
| 技能形态 | `无限持续` | 开启后一直生效，直到手动关闭或条件结束 |
| duration / durationType | -1 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `attack@attack_speed` | 140 |
| `attack@atk` | 1.1 |
| `attack@passby_delay` | 0.5 |

#### 攻击范围

`rangeId = 3-12`，8 格（direction=1）

> 该技能未指定自己的 `rangeId`，上图是干员**自身范围**。技能若扩大范围，会另有 `rangeId`。

```
■ ■ · · 
■ ■ ■ ■ 
■ ■ · · 
```

#### 判定链

> 匹配方式：按命名规则匹配（层级 B）

**`oblvns_s_2[fever]`** ← 事件 `ON_BUFF_FINISH`

- **TriggerBuffsByKeys** `_buffKeys`=["oblvns_s_2[switch]"] `_targetType`="BUFF_OWNER"

**`oblvns_s_2[switch]`** ← 事件 `ON_TOGGLE_SKILL_START`

- **IfElse** 
  - **CheckUnitCurrentMode** `_targetType`="BUFF_OWNER"
  - **IfConditions** 
    - **IsFeverFull** 
    - **IsInFever** 
    - **SwitchMode** `_modeIndex`=5 `_targetType`="BUFF_OWNER"
    - **IfElse** 
      - **IsFeverFull** 
      - **TryActiveFeverIfFull** 
      - **SwitchMode** `_modeIndex`=2 `_targetType`="BUFF_OWNER"
      - **PlayAudio** `_target`="BUFF_OWNER"
  - **IfElse** 
    - **CheckUnitCurrentMode** `_targetType`="BUFF_OWNER"
    - **IfConditions** 
      - **IsFeverFull** 
      - **IsInFever** 
- …（共 28 个节点，已截断）

**`oblvns_s_2[switch]`** ← 事件 `ON_BUFF_TRIGGER`

- **IfElse** 
  - **CheckUnitCurrentMode** `_targetType`="BUFF_OWNER"
  - **IfConditions** 
    - **IsFeverFull** 
    - **IsInFever** 
    - **SwitchMode** `_modeIndex`=5 `_targetType`="BUFF_OWNER"
    - **IfElse** 
      - **IsFeverFull** 
      - **TryActiveFeverIfFull** 
      - **SwitchMode** `_modeIndex`=2 `_targetType`="BUFF_OWNER"
  - **IfElse** 
    - **CheckUnitCurrentMode** `_targetType`="BUFF_OWNER"
    - **IfConditions** 
      - **IsFeverFull** 
      - **IsInFever** 
      - **SwitchMode** `_modeIndex`=3 `_targetType`="BUFF_OWNER"
- …（共 26 个节点，已截断）

**`oblvns_s_2[switch][in_fever]`** ← 事件 `ON_BUFF_START`

- **SpShowBuff** `_targetType`="BUFF_OWNER"

---

### 残月的余响　`skchr_oblvns_3`

**技能描述（最高级）：**

> 攻击范围扩大，攻击同时使用钢琴和风琴音色演奏，各自演奏2个造成相当于攻击力220%物理和法术伤害的音符，且分别追踪法术抗性和防御力最高的敌人。
> Fever期间Ave Mujica成员受到致命伤害时不撤退，Fever结束后退场


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WHEN_ATTACK` | 每次攻击回复 |
| 初始 SP / 消耗 SP | 34 / 42 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 1 | 可存层数 |
| 释放方式 | `MANUAL` | 手动释放 |
| 技能形态 | `限时技能` | 持续 25 秒 |
| duration / durationType | 25 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `attack@attack_speed` | 0 |
| `attack@atk_scale` | 2.2 |

#### 攻击范围

`rangeId = 3-21`，16 格（direction=1）

```
■ ■ · · 
■ ■ ■ ■ 
■ ■ ■ ■ 
■ ■ ■ ■ 
■ ■ · · 
```

#### 判定链

> 匹配方式：按命名规则匹配（层级 B）

**`oblvns_s_3[fever]`** ← 事件 `ON_BUFF_START`

- **TriggerAbility** `_targetType`="BUFF_OWNER"

**`oblvns_s_3[fever]`** ← 事件 `ON_BUFF_FINISH`

- **IfElse** 
  - **IfTarget** `_targetType`="BUFF_OWNER"
  - **InterruptAbility** 

**`oblvns_s_3[fever_undead]`** ← 事件 `ON_BEFORE_TRY_SET_HP_ZERO`

- **ConsumeTrySetHpZeroModifier** 

**`oblvns_s_3[fever_undead]`** ← 事件 `ON_POST_TRY_SET_HP_ZERO`

- **IsConsumerOfTrySetHpZeroModifier** 
- **AddBuffBlackboard** `_targetType`="BUFF_OWNER"

**`oblvns_s_3[fever_undead]`** ← 事件 `ON_BUFF_FINISH`

- **IfElse** 
  - **CheckContainsBuff** `_buffKeys`=["oblvns_s_3[fever_undead]"] `_targetType`="BUFF_OWNER"
  - **AddBuffBlackboard** `_targetType`="BUFF_OWNER"
  - **IfElse** 
    - **FilterByBlackboardValue** `_condType`="GT" `_targetType`="BUFF_OWNER"
    - **Withdraw** 

**`oblvns_s_3[switch]`** ← 事件 `ON_BUFF_START`

- **SwitchMode** `_modeIndex`=4 `_targetType`="BUFF_OWNER"

**`oblvns_s_3[switch]`** ← 事件 `ON_BUFF_FINISH`

- **SwitchMode** `_modeIndex`=0 `_targetType`="BUFF_OWNER"

**`oblvns_s_3[switch_mode]`** ← 事件 `ON_BUFF_START`

- **SwitchMode** `_modeIndex`=4 `_targetType`="BUFF_OWNER"
- **IfConditions** 
  - **IsInFever** 
  - **IsFeverFull** 
  - **CreateBuff** buffKey=`oblvns_s_3[loop]` `lifeTimeType`=INFINITY
  - **PlayAudio** `_target`="BUFF_OWNER"

**`oblvns_s_3[switch_mode]`** ← 事件 `ON_BUFF_TRIGGER`

- **CheckCharSkillAffecting** `_targetType`="BUFF_OWNER"
- **IfNot** 
- **FinishBuff** 

**`oblvns_s_3[switch_mode]`** ← 事件 `ON_BUFF_FINISH`

- **SwitchMode** `_modeIndex`=0 `_targetType`="BUFF_OWNER"

**`oblvns_s_3[trigger_ability_ranged]`** ← 事件 `ON_BUFF_FINISH`

- **TriggerAbility** `_targetType`="BUFF_OWNER"

---

## 附：数据边界

| 项目 | 状态 |
|---|---|
| 属性 / 数值 / SP / 范围 / 抬手 | ✅ 明文可得 |
| buff 行为树 | ✅ 明文可得 |
| 技能 → 模板绑定 | ⚠️ 游戏只给 `prefabId`，真实绑定在不可解的 `.ab` 里；本文按命名规律 + `blackboard` 键名双向推断 |
| 动画资源本体 | ❌ 在 `.ab` 包内，不可解 |
| 抬手精度 | ✅ 1/30 秒，是动画事件时刻而非视觉起手帧 |
