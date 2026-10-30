# 凯尔希·思衡托 — 技能判定说明

> 数据来源：明文 JSON（`character_table` / `skill_table` / `range_table` / `buff_template_data` / `bakemuzzledata`）。不含反汇编或二进制解析内容。

## 一、干员底子

| 项 | 值 |
|---|---|
| ID | `char_1052_kalts2` |
| 职业 | 医疗 / `watchman` |
| 星级 | 6 星 |
| 生命（精二满级） | 1620 |
| 攻击（精二满级） | 510 |
| 防御（精二满级） | 276 |
| 法抗 | 0% |
| **攻击间隔 baseAttackTime** | **2.85 秒** |
| 攻速 attackSpeed | 100（100% = 无增减） |
| 阻挡 | 1 |
| 部署费用 | 19 |

**攻击间隔换算**（全干员通用）：

```
实际间隔 = baseAttackTime ÷ (attackSpeed / 100)
         = 2.85 ÷ 1.00 = 2.850 秒
```

## 二、抬手（攻击前摇）

来源：`bakemuzzledata/character/char_1052_kalts2_*.json` → `bakedAnimDatas.<组>.bakedEvents.<动画名>.eventTime`，取事件 `OnAttack` 时刻。

| 场景 | 动画名 | 抬手 | 帧数(30fps) |
|---|---|---|---|
| **普通攻击** | `Attack_Loop` | **0.6 秒** | 18 帧 |

> 占攻击间隔 21.1%（0.6 秒 / 2.85 秒）。开技能不会让抬手变快。

| 技能动画 | `Skill_2_Attack` | 0.533333 秒 | 16 帧 |
| 技能动画 | `Skill_3_Attack` | 0.4 秒 | 12 帧 |
| 技能动画 | `Skill_3_Restart_Begin` | 0.666667 秒 | 20 帧 |
| 技能动画 | `Skill_Down_2_Attack` | 0.533333 秒 | 16 帧 |
| 技能动画 | `Skill_Down_3_Attack` | 0.433333 秒 | 13 帧 |


## 三、技能逐层拆解

---

### 应急肃正防线　`skchr_kalts2_1`

**技能描述（最高级）：**

> 攻击力+90%，攻击速度+50，所有其他起飞的友方干员阻挡范围扩大


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WITH_TIME` | 随时间自动回复 |
| 初始 SP / 消耗 SP | 28 / 35 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 1 | 可存层数 |
| 释放方式 | `MANUAL` | 手动释放 |
| 技能形态 | `限时技能` | 持续 35 秒 |
| duration / durationType | 35 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `atk` | 0.9 |
| `attack@block_radius_scale` | 0.23 |
| `attack_speed` | 50 |

#### 攻击范围

`rangeId = y-6`，16 格（direction=1）

> 该技能未指定自己的 `rangeId`，上图是干员**自身范围**。技能若扩大范围，会另有 `rangeId`。

```
· ■ ■ · 
■ ■ ■ ■ 
■ ■ ■ ■ 
■ ■ ■ ■ 
· ■ ■ · 
```

#### 判定链

本技能**没有独立 buff 模板**。它属于「一段式数值强化」：开技能只改 `blackboard` 参数与动画，不挂 buff 节点树。

可核对的替代证据：

- 描述中的每个花括号参数都能在 `blackboard` 中找到对应值（见上表）

---

### 保护性拒止　`skchr_kalts2_2`

**技能描述（最高级）：**

> 攻击范围扩大，攻击力+150%，攻击变为射出医疗单元（优先选择敌人），击中时对目标周围所有敌人造成相当于攻击力380%的真实伤害，使其停顿5秒并回复目标周围所有友方干员相当于攻击力200%的生命
> 攻击装有10发弹药，可以随时停止技能


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WITH_TIME` | 随时间自动回复 |
| 初始 SP / 消耗 SP | 28 / 35 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 1 | 可存层数 |
| 释放方式 | `MANUAL` | 手动释放 |
| 技能形态 | `弹药制` | 技能持续到弹药打完 |
| duration / durationType | -1 / `AMMO` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `atk` | 1.5 |
| `attack@atk_scale` | 3.8 |
| `attack@heal_scale` | 2 |
| `attack@sluggish` | 5 |
| `attack@trigger_time` | 10 |

#### 攻击范围

`rangeId = y-11`，19 格（direction=1）

```
· ■ ■ · · 
■ ■ ■ ■ ■ 
■ ■ ■ ■ ■ 
■ ■ ■ ■ ■ 
· ■ ■ · · 
```

#### 判定链

本技能**没有独立 buff 模板**。它属于「一段式数值强化」：开技能只改 `blackboard` 参数与动画，不挂 buff 节点树。

可核对的替代证据：

- 描述中的每个花括号参数都能在 `blackboard` 中找到对应值（见上表）

---

### 破梏重生　`skchr_kalts2_3`

**技能描述（最高级）：**

> 立刻获得战术锚点，攻击力+150%，攻击间隔大幅缩小，额外治疗1个目标，部署战术锚点后，自身移动至该位置，并使攻击范围内最多2名友方干员可以部署至自身攻击范围的另一位置


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WITH_TIME` | 随时间自动回复 |
| 初始 SP / 消耗 SP | 35 / 50 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 1 | 可存层数 |
| 释放方式 | `MANUAL` | 手动释放 |
| 技能形态 | `限时技能` | 持续 35 秒 |
| duration / durationType | 35 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `atk` | 1.5 |
| `base_attack_time` | -1.55 |

#### 攻击范围

`rangeId = y-6`，16 格（direction=1）

> 该技能未指定自己的 `rangeId`，上图是干员**自身范围**。技能若扩大范围，会另有 `rangeId`。

```
· ■ ■ · 
■ ■ ■ ■ 
■ ■ ■ ■ 
■ ■ ■ ■ 
· ■ ■ · 
```

#### 判定链

> 匹配方式：按命名规则匹配（层级 B）

**`kalts2_s_3`** ← 事件 `ON_BUFF_START`

- **CreateBuff** buffKey=`kalts2_s_3[core]` templateKey=`kalts2_s_3[core]` 属性修改=[BASE_ATTACK_TIME ADDITION blackboard, ATK MULTIPLIER blackboard] `lifeTimeType`=INFINITY

**`kalts2_s_3[core]`** ← 事件 `ON_BUFF_FINISH`

- **SwitchMode** `_modeIndex`=0 `_targetType`="TARGET"
- **AlwaysNext** 
- **FinishBuffsById** `_targetType`="BUFF_OWNER"

**`kalts2_s_3[core]`** ← 事件 `ON_BUFF_START`

- **SwitchMode** `_modeIndex`=1 `_targetType`="BUFF_OWNER"
- **IfElse** 
  - **FilterByCharacterSharedBlackboard** `_condType`="GT" `_target`="BUFF_OWNER"
  - **CreateBuff** buffKey=`kalts2_s_3_fx[ctrl][trigger]` templateKey=`kalts2_s_3_fx[ctrl][trigger]` `lifeTimeType`=INFINITY
  - **CreateBuff** buffKey=`kalts2_s_3[token_ctrl]` templateKey=`kalts2_s_3[token_ctrl]` `lifeTimeType`=INFINITY
  - **CreateBuff** buffKey=`kalts2_s_3_fx[ctrl]` templateKey=`kalts2_s_3_fx[ctrl]` `lifeTimeType`=INFINITY

**`kalts2_s_3[core]`** ← 事件 `ON_SKILL_FINISH`

- **FinishBuff** 

**`kalts2_s_3[core]`** ← 事件 `ON_GAME_OVER`

- **Kalts2S3CancelExtraBuildableChecker** 
- **Kalts2S3ResetCardRecord** 

**`kalts2_s_3[disarm]`** ← 事件 `ON_BUFF_START`

- **SwitchMode** `_modeIndex`=2 `_targetType`="BUFF_OWNER"

**`kalts2_s_3[finish_indicator_fx]`** ← 事件 `ON_BUFF_START`

- **FinishBuffsById** `_targetType`="BUFF_OWNER"

**`kalts2_s_3[indicator]`** ← 事件 `ON_BUFF_START`

- **CheckUnitCurrentMode** `_targetType`="BUFF_OWNER"
- **IfNot** 
- **FilterCardState** `_target`="BUFF_OWNER"
- **IfNot** 
- **CreateBuffUseAbilitySelector** buffKey=`kalts2_s_3[indicator_fx]` templateKey=`kalts2_s_3[indicator_fx]` `lifeTimeType`=LIMITED `_targetType`="BUFF_OWNER"

**`kalts2_s_3[indicator]`** ← 事件 `ON_BUFF_TRIGGER`

- **CheckUnitCurrentMode** `_targetType`="BUFF_OWNER"
- **IfNot** 
- **FilterCardState** `_target`="BUFF_OWNER"
- **IfNot** 
- **CreateBuffUseAbilitySelector** buffKey=`kalts2_s_3[indicator_fx]` templateKey=`kalts2_s_3[indicator_fx]` `lifeTimeType`=LIMITED `_targetType`="BUFF_OWNER"

**`kalts2_s_3[indicator_fx]`** ← 事件 `ON_BUFF_START`

- **CheckContainsBuff** `_buffKeys`=["kalts2_s_3[indicator_fx][fx]"] `_targetType`="BUFF_OWNER"
- **IfNot** 
- **CreateBuff** buffKey=`kalts2_s_3[indicator_fx][fx]` templateKey=`kalts2_s_3[indicator_fx][fx]` `lifeTimeType`=INFINITY

**`kalts2_s_3[indicator_fx][fx]`** ← 事件 `ON_BUFF_TRIGGER`

- **CheckContainsBuff** `_buffKeys`=["kalts2_s_3[indicator_fx]"] `_targetType`="BUFF_OWNER"
- **IfNot** 
- **FinishBuff** 

**`kalts2_s_3[on_token_born]`** ← 事件 `ON_BUFF_START`

- **AddAbilityBlackboard** 
- **TriggerAbility** `_targetType`="BUFF_OWNER"
- **LockCharacterSkillProgress** `_targetType`="BUFF_OWNER"
- **CreateBuffUseAbilitySelector** buffKey=`kalts2_s_3[withdraw]` templateKey=`kalts2_s_3[withdraw]` `lifeTimeType`=INFINITY `_targetType`="BUFF_OWNER"
- **FinishBuffsById** `_targetType`="BUFF_OWNER"
- **AlwaysNext** 
- **FinishBuff** 

**`kalts2_s_3[restore]`** ← 事件 `ON_BUFF_START`

- **CreateBuff** buffKey=`kalts2_s_3` templateKey=`kalts2_s_3` `lifeTimeType`=LIMITED
- **FilterByCharacterSharedBlackboard** `_condType`="GT" `_target`="BUFF_OWNER"
- **TriggerAbility** `_targetType`="BUFF_OWNER"

**`kalts2_s_3[token_ctrl]`** ← 事件 `ON_BUFF_FINISH`

- **WithdrawTokens** 
- **AlwaysNext** 
- **RechargeToken** 

**`kalts2_s_3[token_ctrl]`** ← 事件 `ON_BUFF_START`

- **RechargeToken** 

**`kalts2_s_3[withdraw]`** ← 事件 `ON_BUFF_TRIGGER`

- **IfElse** 
  - **CheckUnitAlive** 
  - **CheckCharSkillAffecting** `_targetType`="BUFF_SOURCE"
  - **CreateCardBuff** `_target`="BUFF_OWNER"
  - **CreateCardBuff** `_target`="BUFF_OWNER"
  - **CreateDeckBuff** `_target`="BUFF_OWNER"
  - **Kalts2S3RecordSkillAffectedCardInfo** `_targetType`="BUFF_OWNER"
  - **Kalts2S3ApplyExtraBuildableChecker** `_targetType`="BUFF_OWNER"
  - **SetWithdrawCostRecoverRatio** `_targetType`="BUFF_OWNER"
  - **Withdraw** 
  - **FinishBuff** 

**`kalts2_s_3[withdraw]`** ← 事件 `ON_BUFF_START`

- **CreateEffect** `_targetType`="BUFF_OWNER"

---

## 附：数据边界

| 项目 | 状态 |
|---|---|
| 属性 / 数值 / SP / 范围 / 抬手 | ✅ 明文可得 |
| buff 行为树 | ✅ 明文可得 |
| 技能 → 模板绑定 | ⚠️ 游戏只给 `prefabId`，真实绑定在不可解的 `.ab` 里；本文按命名规律 + `blackboard` 键名双向推断 |
| 动画资源本体 | ❌ 在 `.ab` 包内，不可解 |
| 抬手精度 | ✅ 1/30 秒，是动画事件时刻而非视觉起手帧 |
