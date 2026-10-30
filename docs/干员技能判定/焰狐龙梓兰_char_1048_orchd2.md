# 焰狐龙梓兰 — 技能判定说明

> 数据来源：明文 JSON（`character_table` / `skill_table` / `range_table` / `buff_template_data` / `bakemuzzledata`）。不含反汇编或二进制解析内容。

## 一、干员底子

| 项 | 值 |
|---|---|
| ID | `char_1048_orchd2` |
| 职业 | 狙击 / `closerange` |
| 星级 | 6 星 |
| 生命（精二满级） | 1788 |
| 攻击（精二满级） | 842 |
| 防御（精二满级） | 231 |
| 法抗 | 0% |
| **攻击间隔 baseAttackTime** | **1.6 秒** |
| 攻速 attackSpeed | 100（100% = 无增减） |
| 阻挡 | 1 |
| 部署费用 | 20 |

**攻击间隔换算**（全干员通用）：

```
实际间隔 = baseAttackTime ÷ (attackSpeed / 100)
         = 1.6 ÷ 1.00 = 1.600 秒
```

## 二、抬手（攻击前摇）

来源：`bakemuzzledata/character/char_1048_orchd2_*.json` → `bakedAnimDatas.<组>.bakedEvents.<动画名>.eventTime`，取事件 `OnAttack` 时刻。

| 场景 | 动画名 | 抬手 | 帧数(30fps) |
|---|---|---|---|
| **普通攻击** | `Attack_1` | **0.6 秒** | 18 帧 |

> 占攻击间隔 37.5%（0.6 秒 / 1.6 秒）。开技能不会让抬手变快。

| 技能动画 | `Skill_1_End_1` | 0.666667 秒 | 20 帧 |
| 技能动画 | `Skill_1_End_2` | 0.666667 秒 | 20 帧 |
| 技能动画 | `Skill_2_End` | 0.233333 秒 | 7 帧 |
| 技能动画 | `Skill_2_Loop_1` | 0.166667 秒 | 5 帧 |
| 技能动画 | `Skill_2_Loop_2` | 0.166667 秒 | 5 帧 |
| 技能动画 | `Skill_2_Loop_3` | 0.166667 秒 | 5 帧 |
| 技能动画 | `Skill_3_End` | 0.1 秒 | 3 帧 |
| 技能动画 | `Skill_Down_1_End_1` | 0.666667 秒 | 20 帧 |
| 技能动画 | `Skill_Down_1_End_2` | 0.666667 秒 | 20 帧 |
| 技能动画 | `Skill_Down_3_End` | 0.1 秒 | 3 帧 |


## 三、技能逐层拆解

---

### 刚射　`skchr_orchd2_1`

**技能描述（最高级）：**

> 发射4支攻击力160%的箭矢，若还有充能则额外消耗1层施展刚连射：发射5支攻击力200%的箭矢，每支箭矢有20%概率使目标晕眩2秒
> 可充能4次，充能至最大层数时自动释放一次


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WITH_TIME` | 随时间自动回复 |
| 初始 SP / 消耗 SP | 14 / 4 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 4 | 可存层数 |
| 释放方式 | `MANUAL` | 手动释放 |
| 技能形态 | `无限持续` | 开启后一直生效，直到手动关闭或条件结束 |
| duration / durationType | -1 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `atk_scale_1` | 1.6 |
| `atk_scale_2` | 2 |
| `stun_prob` | 0.2 |
| `stun` | 2 |

#### 攻击范围

`rangeId = 3-6`，9 格（direction=1）

> 该技能未指定自己的 `rangeId`，上图是干员**自身范围**。技能若扩大范围，会另有 `rangeId`。

```
■ ■ ■ 
■ ■ ■ 
■ ■ ■ 
```

#### 判定链

> 匹配方式：按命名规则匹配（层级 B）

**`orchd2_s_1[auto]`** ← 事件 `ON_BUFF_TRIGGER`

- **IfElse** 
  - **FilterByTargetSpRatio** `_condType`="GE" `_targetType`="BUFF_OWNER"
  - **IfElse** 
    - **CheckCharSkillAffecting** `_targetType`="BUFF_OWNER"
    - **TriggerSkill** `_targetType`="BUFF_OWNER"

**`orchd2_s_1[damage_scale]`** ← 事件 `ON_OUTPUT_DAMAGE`

- **DamageScale** 

**`orchd2_s_1[finish_recover_sp]`** ← 事件 `ON_BUFF_START`

- **FinishBuffsById** `_targetType`="BUFF_OWNER"

**`orchd2_s_1[recover_sp_checker]`** ← 事件 `ON_SKILL_FINISH`

- **IfConditions** 
  - **FilterByAbilityFinishReason** 
  - **ModifySp** `_targetType`="BUFF_OWNER" `_forceFlag`=False
- **AlwaysNext** 
- **FinishBuff** 

**`orchd2_s_1[reduce_sp]`** ← 事件 `ON_BUFF_START`

- **ModifySp** `_targetType`="BUFF_OWNER" `_forceFlag`=False

**`orchd2_s_1[stun_creator]`** ← 事件 `ON_BUFF_START`

- **RandomAction** 
  - **CreateBuff** buffKey=`stun` `lifeTimeType`=LIMITED

---

### 飞翔瞪射　`skchr_orchd2_2`

**技能描述（最高级）：**

> 立刻起飞并对前方范围的所有目标射击3次，分别射出3、4、5支攻击力提升至180%的箭矢；之后降落并对前方小范围内的所有敌人造成攻击力300%的物理伤害
> 可充能3次，部署后立即释放一次


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WITH_TIME` | 随时间自动回复 |
| 初始 SP / 消耗 SP | 17 / 20 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 3 | 可存层数 |
| 释放方式 | `MANUAL` | 手动释放 |
| 技能形态 | `限时技能` | 持续 4.2 秒 |
| duration / durationType | 4.2 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `attack@atk_scale_loop` | 1.8 |
| `attack@atk_scale_end` | 3 |
| `attack@fly_height` | 0.4 |
| `attack@fly_duration` | 0.2 |
| `attack@fly_end_duration` | 0.2 |

#### 攻击范围

`rangeId = 4-4`，9 格（direction=1）

```
■ ■ ■ 
■ ■ ■ 
■ ■ ■ 
```

#### 判定链

> 匹配方式：按命名规则匹配（层级 B）

**`orchd2_s_2[auto_once]`** ← 事件 `ON_BUFF_START`

- **SetSkillCastWithNoSp** `_targetType`="BUFF_OWNER"

**`orchd2_s_2[auto_once]`** ← 事件 `ON_BUFF_TRIGGER`

- **TriggerSkill** `_targetType`="BUFF_OWNER"

**`orchd2_s_2[auto_once]`** ← 事件 `ON_SKILL_CAST_SUCCEED`

- **SetSkillCastWithNoSp** `_targetType`="BUFF_OWNER"
- **FinishBuff** 

**`orchd2_s_2[direction_force]`** ← 事件 `ON_BUFF_START`

- **SetBodyDirection** `_targetType`="BUFF_OWNER"

**`orchd2_s_2[duration]`** ← 事件 `ON_BUFF_START`

- **SwitchMode** `_modeIndex`=1 `_targetType`="TARGET"
- **AlwaysNext** 
- **FinishBuffsById** `_targetType`="BUFF_OWNER"
- **AlwaysNext** 
- **FinishBuffsById** `_targetType`="BUFF_OWNER"
- **AlwaysNext** 
- **FinishBuffsById** `_targetType`="BUFF_OWNER"

**`orchd2_s_2[duration]`** ← 事件 `ON_BUFF_FINISH`

- **SwitchMode** `_modeIndex`=3 `_targetType`="TARGET"
- **AlwaysNext** 
- **FinishBuffsById** `_targetType`="BUFF_OWNER"
- **AlwaysNext** 
- **FinishBuffsById** `_targetType`="BUFF_OWNER"
- **AlwaysNext** 
- **FinishBuffsById** `_targetType`="BUFF_OWNER"

**`orchd2_s_2[fly_anim]`** ← 事件 `ON_BUFF_START`

- **ModifyGraphicHolderHeight** `_target`="BUFF_OWNER"
- **AlwaysNext** 
- **CreateEffect** `_targetType`="BUFF_OWNER"

**`orchd2_s_2[fly_end]`** ← 事件 `ON_BUFF_START`

- **ModifyGraphicHolderHeight** `_target`="BUFF_OWNER"

**`orchd2_s_2[fly_mode]`** ← 事件 `ON_BUFF_START`

- **ChangeCharBlockMode** `_target`="BUFF_OWNER"

**`orchd2_s_2[fly_mode]`** ← 事件 `ON_BUFF_FINISH`

- **ChangeCharBlockMode** `_target`="BUFF_OWNER"

**`orchd2_s_2[loop_finish]`** ← 事件 `ON_BUFF_START`

- **FinishBuffsById** `_targetType`="BUFF_OWNER"

**`orchd2_s_2[switch_mode]`** ← 事件 `ON_BUFF_START`

- **CheckUnitAlive** 
- **SwitchMode** `_modeIndex`=0 `_targetType`="BUFF_OWNER"

**`orchd2_s_2[try_ground]`** ← 事件 `ON_BUFF_START`

- **FinishBuffsById** `_targetType`="BUFF_OWNER"
- **AlwaysNext** 
- **ModifyGraphicHolderHeight** `_target`="BUFF_OWNER"

---

### 龙之箭　`skchr_orchd2_3`

**技能描述（最高级）：**

> 蓄力3秒后射出直线飞行的贯穿箭矢，箭矢以较大力度推动每个经过的敌人，每飞行一段距离都会对周围所有敌人造成攻击力360%的物理伤害和攻击力60%的法术伤害，箭矢射程无限
> 可充能2次


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WITH_TIME` | 随时间自动回复 |
| 初始 SP / 消耗 SP | 30 / 25 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 2 | 可存层数 |
| 释放方式 | `MANUAL` | 手动释放 |
| 技能形态 | `无限持续` | 开启后一直生效，直到手动关闭或条件结束 |
| duration / durationType | -1 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `atk_scale` | 3.6 |
| `atk_scale_magic` | 0.6 |
| `wait_duration` | 1.5 |
| `dist_interval` | 0.25 |
| `max_dist` | 99 |
| `force` | 2 |
| `knockback_duration` | 1 |

#### 攻击范围

`rangeId = 3-6`，9 格（direction=1）

> 该技能未指定自己的 `rangeId`，上图是干员**自身范围**。技能若扩大范围，会另有 `rangeId`。

```
■ ■ ■ 
■ ■ ■ 
■ ■ ■ 
```

#### 判定链

> 匹配方式：按命名规则匹配（层级 B）

**`orchd2_s_3[knockback]`** ← 事件 `ON_BUFF_ENABLE`

- **KnockBackWithCharacterDirection** `_target`="TARGET" `_source`="SOURCE"

**`orchd2_s_3[magic_damage]`** ← 事件 `ON_BUFF_START`

- **DamageViaAttr** `_targetType`="TARGET"

---

## 附：数据边界

| 项目 | 状态 |
|---|---|
| 属性 / 数值 / SP / 范围 / 抬手 | ✅ 明文可得 |
| buff 行为树 | ✅ 明文可得 |
| 技能 → 模板绑定 | ⚠️ 游戏只给 `prefabId`，真实绑定在不可解的 `.ab` 里；本文按命名规律 + `blackboard` 键名双向推断 |
| 动画资源本体 | ❌ 在 `.ab` 包内，不可解 |
| 抬手精度 | ✅ 1/30 秒，是动画事件时刻而非视觉起手帧 |
