# 薇薇安娜 — 技能判定说明

> 数据来源：明文 JSON（`character_table` / `skill_table` / `range_table` / `buff_template_data` / `bakemuzzledata`）。不含反汇编或二进制解析内容。

## 一、干员底子

| 项 | 值 |
|---|---|
| ID | `char_4098_vvana` |
| 职业 | 近卫 / `artsfghter` |
| 星级 | 6 星 |
| 生命（精二满级） | 2920 |
| 攻击（精二满级） | 646 |
| 防御（精二满级） | 447 |
| 法抗 | 1500% |
| **攻击间隔 baseAttackTime** | **1.25 秒** |
| 攻速 attackSpeed | 100（100% = 无增减） |
| 阻挡 | 1 |
| 部署费用 | 21 |

**攻击间隔换算**（全干员通用）：

```
实际间隔 = baseAttackTime ÷ (attackSpeed / 100)
         = 1.25 ÷ 1.00 = 1.250 秒
```

## 二、抬手（攻击前摇）

来源：`bakemuzzledata/character/char_4098_vvana_*.json` → `bakedAnimDatas.<组>.bakedEvents.<动画名>.eventTime`，取事件 `OnAttack` 时刻。

| 场景 | 动画名 | 抬手 | 帧数(30fps) |
|---|---|---|---|
| **普通攻击** | `Attack` | **0.366667 秒** | 11 帧 |

> 占攻击间隔 29.3%（0.366667 秒 / 1.25 秒）。开技能不会让抬手变快。

| 技能动画 | `Skill_1_Attack` | 0.366667 秒 | 11 帧 |
| 技能动画 | `Skill_2_Loop` | 0.3 秒 | 9 帧 |
| 技能动画 | `Skill_3_Attack_A` | 0.5 秒 | 15 帧 |
| 技能动画 | `Skill_3_Attack_B` | 0.5 秒 | 15 帧 |
| 技能动画 | `Skill_Down_3_Attack_A` | 0.5 秒 | 15 帧 |


## 三、技能逐层拆解

---

### 光影迅捷剑　`skchr_vvana_1`

**技能描述（最高级）：**

> 下次攻击的攻击力提高至200%，并连续攻击两次；
> 蓄力额外效果：攻击距离+2，改为连续攻击三次


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WITH_TIME` | 随时间自动回复 |
| 初始 SP / 消耗 SP | 0 / 4 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 2 | 可存层数 |
| 释放方式 | `AUTO` | 自动释放 |
| 技能形态 | `无限持续` | 开启后一直生效，直到手动关闭或条件结束 |
| duration / durationType | -1 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `atk_scale` | 2 |

#### 攻击范围

`rangeId = 1-1`，2 格（direction=1）

> 该技能未指定自己的 `rangeId`，上图是干员**自身范围**。技能若扩大范围，会另有 `rangeId`。

```
■ ■ 
```

#### 判定链

> 匹配方式：按命名规则匹配（层级 B）

**`vvana_s_1[mode]`** ← 事件 `ON_BUFF_START`

- **IfElse** 
  - **CheckCharSkillAffecting** `_targetType`="BUFF_OWNER"
  - **SwitchMode** `_modeIndex`=0 `_targetType`="TARGET"
  - **SwitchMode** `_modeIndex`=0 `_targetType`="TARGET"
- **CheckContainsBuff** `_buffKeys`=["vvana_s_1_enhance_mark"] `_targetType`="BUFF_OWNER"
- **IfNot** 
- **CreateBuff** buffKey=`vvana_s_1_enhance_mark` `overrideType`=UNIQUE `lifeTimeType`=INFINITY

**`vvana_s_1[mode]`** ← 事件 `ON_BUFF_FINISH`

- **SwitchMode** `_modeIndex`=0 `_targetType`="TARGET"
- **FinishDerivedBuff** 

**`vvana_s_1[mode]`** ← 事件 `ON_SKILL_START`

- **ClearCharacterSp** `_forceFlag`=False `_charFrom`="BUFF_OWNER"

**`vvana_s_1[mode]`** ← 事件 `ON_SKILL_FINISH`

- **FinishBuff** 

---

### 烛燃影息　`skchr_vvana_2`

**技能描述（最高级）：**

> 攻击力+40%，防御力+160%，阻挡数+1，同时攻击阻挡的所有敌人。每次攻击有20%的概率变为150%攻击力的二连击，并偷取目标40点攻击速度（最多40点，持续至技能结束或薇薇安娜离场）


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WITH_TIME` | 随时间自动回复 |
| 初始 SP / 消耗 SP | 15 / 25 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 1 | 可存层数 |
| 释放方式 | `MANUAL` | 手动释放 |
| 技能形态 | `限时技能` | 持续 35 秒 |
| duration / durationType | 35 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `atk` | 0.4 |
| `def` | 1.6 |
| `block_cnt` | 1 |
| `attack@atk_scale_twice` | 1.5 |
| `attack@prob_once` | 0.8 |
| `attack@prob_twice` | 0.2 |
| `attack@steal_atk_speed` | 40 |
| `attack@steal_atk_speed_max` | 40 |

#### 攻击范围

`rangeId = 1-1`，2 格（direction=1）

> 该技能未指定自己的 `rangeId`，上图是干员**自身范围**。技能若扩大范围，会另有 `rangeId`。

```
■ ■ 
```

#### 判定链

> 匹配方式：按命名规则匹配（层级 B）

**`vvana_s_2[steal]`** ← 事件 `ON_BEFORE_TARGET_APPLY_MODIFIER`

- **IsDamage** 
- **IfTarget** `_targetType`="MODIFIER_TARGET"
- **TriggerAbility** `_targetType`="MODIFIER_TARGET"

---

### “明灭”　`skchr_vvana_3`

**技能描述（最高级）：**

> 攻击间隔延长，攻击力+110%，防御力+90%，法术抗性+25，攻击变为二连击，第二天赋的触发几率提升至2.5倍，优先攻击精英或领袖敌人
> 第二次及以后使用时，攻击距离+2，攻击变为三连击，持续时间延长至25秒


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WITH_TIME` | 随时间自动回复 |
| 初始 SP / 消耗 SP | 18 / 25 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 1 | 可存层数 |
| 释放方式 | `MANUAL` | 手动释放 |
| 技能形态 | `限时技能` | 持续 15 秒 |
| duration / durationType | 15 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `base_attack_time` | 0.5 |
| `atk` | 1.1 |
| `def` | 0.9 |
| `magic_resistance` | 25 |
| `enhance_duration` | 25 |
| `talent_scale` | 2.5 |
| `duration_plus` | 15 |

#### 攻击范围

`rangeId = 1-1`，2 格（direction=1）

```
■ ■ 
```

#### 判定链

> 匹配方式：按命名规则匹配（层级 B）

**`vvana_s_3`** ← 事件 `ON_BUFF_START`

- **IfElse** 
  - **CheckContainsBuff** `_buffKeys`=["vvana_s_3_enhance_mark"] `_targetType`="BUFF_OWNER"
  - **SwitchMode** `_modeIndex`=4 `_targetType`="TARGET"
  - **SwitchMode** `_modeIndex`=3 `_targetType`="TARGET"

**`vvana_s_3`** ← 事件 `ON_BUFF_FINISH`

- **SwitchMode** `_modeIndex`=0 `_targetType`="TARGET"
- **SwitchSkillRangeIdModeIndex** `_targetType`="BUFF_OWNER"

**`vvana_s_3[check]`** ← 事件 `ON_BUFF_START`

- **IfElse** 
  - **FilterSkillTriggerdCnt** `_count`=1 `_target`="BUFF_OWNER"
  - **CreateBuff** buffKey=`vvana_s_3_enhance_mark` `lifeTimeType`=INFINITY
  - **ModifyAbilityBlackboard** 
  - **ModifyAbilityBlackboard** 
- **AlwaysNext** 
- **ModifyAnimatorHookerReplacePair** `_modeIndex`=-1 `_target`="BUFF_OWNER"

**`vvana_s_3[start]`** ← 事件 `ON_BUFF_START`

- **ModifyAnimatorHookerReplacePair** `_modeIndex`=-1 `_target`="BUFF_OWNER"

---

## 附：数据边界

| 项目 | 状态 |
|---|---|
| 属性 / 数值 / SP / 范围 / 抬手 | ✅ 明文可得 |
| buff 行为树 | ✅ 明文可得 |
| 技能 → 模板绑定 | ⚠️ 游戏只给 `prefabId`，真实绑定在不可解的 `.ab` 里；本文按命名规律 + `blackboard` 键名双向推断 |
| 动画资源本体 | ❌ 在 `.ab` 包内，不可解 |
| 抬手精度 | ✅ 1/30 秒，是动画事件时刻而非视觉起手帧 |
