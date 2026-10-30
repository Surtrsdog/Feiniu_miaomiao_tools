# 火龙S黑角 — 技能判定说明

> 数据来源：明文 JSON（`character_table` / `skill_table` / `range_table` / `buff_template_data` / `bakemuzzledata`）。不含反汇编或二进制解析内容。

## 一、干员底子

| 项 | 值 |
|---|---|
| ID | `char_1030_noirc2` |
| 职业 | 近卫 / `musha` |
| 星级 | 5 星 |
| 生命（精二满级） | 3518 |
| 攻击（精二满级） | 726 |
| 防御（精二满级） | 351 |
| 法抗 | 0% |
| **攻击间隔 baseAttackTime** | **1.2 秒** |
| 攻速 attackSpeed | 100（100% = 无增减） |
| 阻挡 | 1 |
| 部署费用 | 25 |

**攻击间隔换算**（全干员通用）：

```
实际间隔 = baseAttackTime ÷ (attackSpeed / 100)
         = 1.2 ÷ 1.00 = 1.200 秒
```

## 二、抬手（攻击前摇）

来源：`bakemuzzledata/character/char_1030_noirc2_*.json` → `bakedAnimDatas.<组>.bakedEvents.<动画名>.eventTime`，取事件 `OnAttack` 时刻。

| 场景 | 动画名 | 抬手 | 帧数(30fps) |
|---|---|---|---|
| **普通攻击** | `Attack_1` | **0.466667 秒** | 14 帧 |

> 占攻击间隔 38.9%（0.466667 秒 / 1.2 秒）。开技能不会让抬手变快。

| 技能动画 | `Skill_1_End` | 0.066667 秒 | 2 帧 |
| 技能动画 | `Skill_2` | 0.466667 秒 | 14 帧 |


## 三、技能逐层拆解

---

### 居合拔刀气刃斩　`skchr_noirc2_1`

**技能描述（最高级）：**

> 纳刀后停止攻击，直到下一次受到攻击时抵挡此次伤害并选择范围内一名敌人造成4次相当于攻击力150%的物理伤害并立即触发一次第二天赋。
> 技能期间击倒敌人时再次纳刀触发技能


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WHEN_ATTACK` | 每次攻击回复 |
| 初始 SP / 消耗 SP | 5 / 8 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 1 | 可存层数 |
| 释放方式 | `MANUAL` | 手动释放 |
| 技能形态 | `限时技能` | 持续 6 秒 |
| duration / durationType | 6 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `multi_atk_scale` | 1.5 |
| `multi_times` | 4 |
| `multi_hit_interval` | 0.2 |
| `nadao_duration` | 5.6 |
| `nadaodonghua_duration` | 0.4 |

#### 攻击范围

`rangeId = 3-2`，4 格（direction=1）

```
■ ■ ■ ■ 
```

#### 判定链

> 匹配方式：按命名规则匹配（层级 B）

**`noirc2_s_1[checkTarget]`** ← 事件 `ON_TARGET_KILLED`

- **CreateBuff** buffKey=`noirc2_s_1[restartFlag]` `overrideType`=UNIQUE `lifeTimeType`=INFINITY
- **FinishBuff** 

**`noirc2_s_1[checkTarget]`** ← 事件 `ON_OUTPUT_DAMAGE`

- **CheckContainsBuff** `_buffKeys`=["noirc2_t_[affectedOnce]", "noirc2_t_2[redBlade]"] `_targetType`="BUFF_OWNER"
- **IfNot** 
- **CreateBuff** buffKey=`noirc2_t_[affectedOnce]` `overrideType`=UNIQUE `lifeTimeType`=INFINITY
- **IfElse** 
  - **CheckContainsBuff** `_buffKeys`=["noirc2_t_2[yellowBlade]"] `_targetType`="BUFF_OWNER"
  - **CreateBuff** buffKey=`noirc2_t_2[redBlade]` templateKey=`noirc2_t_2[redBlade]` 属性修改=[ATK MULTIPLIER blackboard] `maxStackCnt`=5 `overrideType`=UNIQUE
  - **IfElse** 
    - **CheckContainsBuff** `_buffKeys`=["noirc2_t_2[whiteBlade]"] `_targetType`="BUFF_OWNER"
    - **CreateBuff** buffKey=`noirc2_t_2[yellowBlade]` templateKey=`noirc2_t_2[yellowBlade]` 属性修改=[ATK MULTIPLIER blackboard] `maxStackCnt`=5 `overrideType`=UNIQUE
    - **CreateBuff** buffKey=`noirc2_t_2[whiteBlade]` templateKey=`noirc2_t_2[whiteBlade]` 属性修改=[ATK MULTIPLIER blackboard] `maxStackCnt`=5 `overrideType`=UNIQUE

**`noirc2_s_1[nadao]`** ← 事件 `ON_TAKE_DAMAGE`

- **BlockDamage** 
- **TriggerAbility** `_targetType`="BUFF_OWNER"
- **CreateBuff** buffKey=`noirc2_s_1[checkTarget]` templateKey=`noirc2_s_1[checkTarget]` `overrideType`=UNIQUE `lifeTimeType`=INFINITY
- **FinishBuff** 

**`noirc2_s_1[nadao]`** ← 事件 `ON_BUFF_START`

- **IfElse** 
  - **CheckContainsBuff** `_buffKeys`=["noirc2_s_1[start]"] `_targetType`="BUFF_OWNER"
  - **FinishBuff** 

**`noirc2_s_1[nadaodonghua]`** ← 事件 `ON_BUFF_START`

- **SwitchMode** `_modeIndex`=1 `_targetType`="TARGET"
- **TriggerAbility** `_targetType`="BUFF_OWNER"

**`noirc2_s_1[playingNadaoAnim]`** ← 事件 `ON_BUFF_FINISH`

- **CheckContainsBuff** `_buffKeys`=["noirc2_s_1[nadao]"] `_targetType`="BUFF_OWNER"
- **SwitchMode** `_modeIndex`=2 `_targetType`="TARGET"

**`noirc2_s_1[restart]`** ← 事件 `ON_BUFF_START`

- **FinishBuffsById** `_targetType`="BUFF_OWNER"
- **FinishBuffsById** `_targetType`="BUFF_OWNER"
- **IfElse** 
  - **CheckContainsBuff** `_buffKeys`=["noirc2_s_1[restartFlag]"] `_targetType`="BUFF_OWNER"
  - **FinishBuffsById** `_targetType`="BUFF_OWNER"
  - **RestartCastSkill** `_targetType`="BUFF_OWNER"
  - **AlwaysNext** 
  - **FinishBuff** 
  - **InterruptCharacterSkill** `_charFrom`="BUFF_OWNER"
  - **AlwaysNext** 
  - **FinishBuff** 

**`noirc2_s_1[start]`** ← 事件 `ON_ABNORMAL_FLAG_DIRTY`

- **IfElse** 
  - **CheckAbnormalFlag** `_targetType`="BUFF_OWNER"
  - **InterruptCharacterSkill** `_charFrom`="BUFF_OWNER"
  - **FinishBuffsById** `_targetType`="BUFF_OWNER"
  - **FinishBuffsById** `_targetType`="BUFF_OWNER"
  - **FinishBuff** 
  - **IfElse** 
    - **CheckAbnormalFlag** `_targetType`="BUFF_OWNER"
    - **InterruptCharacterSkill** `_charFrom`="BUFF_OWNER"
    - **FinishBuffsById** `_targetType`="BUFF_OWNER"
    - **FinishBuffsById** `_targetType`="BUFF_OWNER"
    - **FinishBuff** 

**`noirc2_s_1[start]`** ← 事件 `ON_BUFF_FINISH`

- **SwitchMode** `_modeIndex`=0 `_targetType`="TARGET"

---

### 气刃兜割　`skchr_noirc2_2`

**技能描述（最高级）：**

> 对前方范围内一名敌人造成7次相当于攻击力180%的物理伤害。
> 技能结束后损失一层第二天赋加成,可充能2次


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WITH_TIME` | 随时间自动回复 |
| 初始 SP / 消耗 SP | 10 / 22 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 2 | 可存层数 |
| 释放方式 | `MANUAL` | 手动释放 |
| 技能形态 | `限时技能` | 持续 1.4 秒 |
| duration / durationType | 1.4 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `multi_atk_scale` | 1.8 |
| `multi_times` | 7 |
| `cnt` | 2 |

#### 攻击范围

`rangeId = 1-1`，2 格（direction=1）

> 该技能未指定自己的 `rangeId`，上图是干员**自身范围**。技能若扩大范围，会另有 `rangeId`。

```
■ ■ 
```

#### 判定链

> 匹配方式：按命名规则匹配（层级 B）

**`noirc2_s_2[consumeBladeLevel]`** ← 事件 `ON_BUFF_START`

- **IfElse** 
  - **CheckContainsBuff** `_buffKeys`=["noirc2_t_2[redBlade]"] `_targetType`="BUFF_OWNER"
  - **FinishBuffsById** `_targetType`="BUFF_OWNER"
  - **IfElse** 
    - **CheckContainsBuff** `_buffKeys`=["noirc2_t_2[yellowBlade]"] `_targetType`="BUFF_OWNER"
    - **FinishBuffsById** `_targetType`="BUFF_OWNER"
    - **IfElse** 
      - **CheckContainsBuff** `_buffKeys`=["noirc2_t_2[whiteBlade]"] `_targetType`="BUFF_OWNER"
      - **FinishBuffsById** `_targetType`="BUFF_OWNER"

**`noirc2_s_2[start]`** ← 事件 `ON_BUFF_START`

- **SwitchMode** `_modeIndex`=3 `_targetType`="TARGET"
- **TriggerAbility** `_targetType`="BUFF_OWNER"

**`noirc2_s_2[start]`** ← 事件 `ON_BUFF_FINISH`

- **SwitchMode** `_modeIndex`=0 `_targetType`="TARGET"

---

## 附：数据边界

| 项目 | 状态 |
|---|---|
| 属性 / 数值 / SP / 范围 / 抬手 | ✅ 明文可得 |
| buff 行为树 | ✅ 明文可得 |
| 技能 → 模板绑定 | ⚠️ 游戏只给 `prefabId`，真实绑定在不可解的 `.ab` 里；本文按命名规律 + `blackboard` 键名双向推断 |
| 动画资源本体 | ❌ 在 `.ab` 包内，不可解 |
| 抬手精度 | ✅ 1/30 秒，是动画事件时刻而非视觉起手帧 |
