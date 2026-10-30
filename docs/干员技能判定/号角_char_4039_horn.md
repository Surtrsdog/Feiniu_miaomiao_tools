# 号角 — 技能判定说明

> 数据来源：明文 JSON（`character_table` / `skill_table` / `range_table` / `buff_template_data` / `bakemuzzledata`）。不含反汇编或二进制解析内容。

## 一、干员底子

| 项 | 值 |
|---|---|
| ID | `char_4039_horn` |
| 职业 | 重装 / `fortress` |
| 星级 | 6 星 |
| 生命（精二满级） | 3067 |
| 攻击（精二满级） | 936 |
| 防御（精二满级） | 620 |
| 法抗 | 0% |
| **攻击间隔 baseAttackTime** | **2.8 秒** |
| 攻速 attackSpeed | 100（100% = 无增减） |
| 阻挡 | 3 |
| 部署费用 | 28 |

**攻击间隔换算**（全干员通用）：

```
实际间隔 = baseAttackTime ÷ (attackSpeed / 100)
         = 2.8 ÷ 1.00 = 2.800 秒
```

## 二、抬手（攻击前摇）

来源：`bakemuzzledata/character/char_4039_horn_*.json` → `bakedAnimDatas.<组>.bakedEvents.<动画名>.eventTime`，取事件 `OnAttack` 时刻。

| 场景 | 动画名 | 抬手 | 帧数(30fps) |
|---|---|---|---|
| **普通攻击** | `Attack_A` | **0.3 秒** | 9 帧 |

> 占攻击间隔 10.7%（0.3 秒 / 2.8 秒）。开技能不会让抬手变快。

| 技能动画 | `Skill_1_A` | 0.366667 秒 | 11 帧 |
| 技能动画 | `Skill_1_B` | 0.366667 秒 | 11 帧 |
| 技能动画 | `Skill_2_A_Loop` | 0.333333 秒 | 10 帧 |
| 技能动画 | `Skill_2_B_Loop` | 0.333333 秒 | 10 帧 |
| 技能动画 | `Skill_3_A_Loop` | 0.333333 秒 | 10 帧 |
| 技能动画 | `Skill_3_B_Loop` | 0.333333 秒 | 10 帧 |
| 技能动画 | `Skill_Down_1` | 0.366667 秒 | 11 帧 |
| 技能动画 | `Skill_Down_2_B_Loop` | 0.333333 秒 | 10 帧 |
| 技能动画 | `Skill_Down_3_Loop` | 0.333333 秒 | 10 帧 |


## 三、技能逐层拆解

---

### 照明榴弹　`skchr_horn_1`

**技能描述（最高级）：**

> 下次攻击时造成280%攻击力的物理伤害，若为远程攻击则溅射范围扩大且在周围产生一个持续8秒的照明区域使敌人隐匿失效
> 可充能2次


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WITH_TIME` | 随时间自动回复 |
| 初始 SP / 消耗 SP | 0 / 5 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 2 | 可存层数 |
| 释放方式 | `AUTO` | 自动释放 |
| 技能形态 | `无限持续` | 开启后一直生效，直到手动关闭或条件结束 |
| duration / durationType | -1 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `atk_scale` | 2.8 |
| `projectile_delay_time` | 8 |
| `projectile_range` | 1.7 |
| `cnt` | 2 |

#### 攻击范围

`rangeId = 4-6`，7 格（direction=1）

> 该技能未指定自己的 `rangeId`，上图是干员**自身范围**。技能若扩大范围，会另有 `rangeId`。

```
■ ■ · 
■ ■ ■ 
■ ■ · 
```

#### 判定链

本技能**没有独立 buff 模板**。它属于「一段式数值强化」：开技能只改 `blackboard` 参数与动画，不挂 buff 节点树。

可核对的替代证据：

- 描述中的每个花括号参数都能在 `blackboard` 中找到对应值（见上表）

---

### 暴风号令　`skchr_horn_2`

**技能描述（最高级）：**

> 每次攻击造成240%攻击力的物理溅射伤害
> 过载：每次攻击额外造成60%攻击力的法术溅射伤害，主动关闭时发射剩余全部弹药并流失60%生命值
> 技能拥有10枚弹药，可随时主动关闭


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WITH_TIME` | 随时间自动回复 |
| 初始 SP / 消耗 SP | 18 / 25 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 1 | 可存层数 |
| 释放方式 | `MANUAL` | 手动释放 |
| 技能形态 | `弹药制` | 技能持续到弹药打完 |
| duration / durationType | -1 / `AMMO` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `attack@s2.atk_scale` | 2.4 |
| `attack@s2.magic_atk_scale` | 0.6 |
| `attack@s2.hp_ratio` | 0.6 |
| `attack@s2.trigger_time` | 10 |
| `hp_ratio` | 0.6 |

#### 攻击范围

`rangeId = 4-6`，7 格（direction=1）

> 该技能未指定自己的 `rangeId`，上图是干员**自身范围**。技能若扩大范围，会另有 `rangeId`。

```
■ ■ · 
■ ■ ■ 
■ ■ · 
```

#### 判定链

> 匹配方式：按命名规则匹配（层级 B）

**`horn_s_2[create_start_buff_to_owner]`** ← 事件 `ON_BUFF_FINISH`

- **CreateBuffWithOverrideEffect** buffKey=`horn_s_2[s2_effect]` `lifeTimeType`=LIMITED

**`horn_s_2[overload_magic_damage]`** ← 事件 `ON_BUFF_START`

- **CheckContainsBuff** `_buffKeys`=["horn_s_2[overload_mark]"] `_targetType`="BUFF_SOURCE"
- **AdvancedApplyDamage** `_targetType`="TARGET"

**`horn_s_2[overload_self_instant]`** ← 事件 `ON_BUFF_START`

- **DamageViaMaxHpRatio** `_targetType`="BUFF_OWNER"

**`horn_s_2[overload_switch_effect]`** ← 事件 `ON_BUFF_TRIGGER`

- **IfElse** 
  - **CheckCharacterDefaultDirection** `_target`="TARGET"
  - **CheckContainsDerviedBuff** `_derviedBuffKey`="horn_s_2[overload_switch_effect_down]"
  - **IfNot** 
  - **FinishBuffsById** `_targetType`="BUFF_OWNER"
  - **CreateBuff** buffKey=`horn_s_2[overload_switch_effect_down]` `lifeTimeType`=INFINITY
  - **CheckContainsDerviedBuff** `_derviedBuffKey`="horn_s_2[overload_switch_effect_normal]"
  - **IfNot** 
  - **FinishBuffsById** `_targetType`="BUFF_OWNER"
  - **CreateBuff** buffKey=`horn_s_2[overload_switch_effect_normal]` `lifeTimeType`=INFINITY

**`horn_s_2[signal_melee]`** ← 事件 `ON_ABILITY_SPELL_ON`

- **IfElse** 
  - **CheckContainsBuff** `_buffKeys`=["horn_s_2[overload_mark]"] `_targetType`="BUFF_OWNER"
  - **CreateBuff** buffKey=`horn_s_2[signal_melee_overload_signal]` `lifeTimeType`=IMMEDIATELY
  - **CreateBuff** buffKey=`horn_s_2[signal_melee_normal_signal]` `lifeTimeType`=IMMEDIATELY

**`horn_s_2[signal_ranged]`** ← 事件 `ON_ABILITY_SPELL_ON`

- **IfElse** 
  - **CheckContainsBuff** `_buffKeys`=["horn_s_2[overload_mark]"] `_targetType`="BUFF_OWNER"
  - **CreateBuff** buffKey=`horn_s_2[signal_ranged_overload_signal]` `lifeTimeType`=IMMEDIATELY
  - **CreateBuff** buffKey=`horn_s_2[signal_ranged_normal_signal]` `lifeTimeType`=IMMEDIATELY

---

### 终极防线　`skchr_horn_3`

**技能描述（最高级）：**

> 攻击力+70%，攻击间隔大幅缩短
> 过载：攻击力改为+140%，逐渐流失生命（12秒后到达最大生命12%/秒）该技能可随时主动关闭


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WITH_TIME` | 随时间自动回复 |
| 初始 SP / 消耗 SP | 25 / 35 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 1 | 可存层数 |
| 释放方式 | `MANUAL` | 手动释放 |
| 技能形态 | `限时技能` | 持续 24 秒 |
| duration / durationType | 24 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `atk` | 0.7 |
| `base_attack_time` | -1.8 |
| `horn_s_3[overload_start].atk` | 1.4 |
| `horn_s_3[overload_start].interval` | 0.2 |
| `horn_s_3[overload_start].hp_ratio` | 0.12 |
| `horn_s_3[overload_start].damage_duration` | 12 |

#### 攻击范围

`rangeId = 4-6`，7 格（direction=1）

> 该技能未指定自己的 `rangeId`，上图是干员**自身范围**。技能若扩大范围，会另有 `rangeId`。

```
■ ■ · 
■ ■ ■ 
■ ■ · 
```

#### 判定链

> 匹配方式：由 `blackboard` 键名精确指认（层级 A）

**`horn_s_3[overload_start]`** ← 事件 `ON_BUFF_START`

- **BleedingDamageIncreasingReset** 
- **FinishBuffsById** `_targetType`="BUFF_OWNER"

**`horn_s_3[overload_start]`** ← 事件 `ON_BUFF_TRIGGER`

- **BleedingDamagePerSec** 

**`horn_s_3[overload_start]`** ← 事件 `ON_SKILL_FINISH`

- **BleedingDamageIncreasingReset** 

**`horn_s_3[overload_switch_effect]`** ← 事件 `ON_BUFF_TRIGGER`

- **IfElse** 
  - **CheckCharacterDefaultDirection** `_target`="TARGET"
  - **CheckContainsDerviedBuff** `_derviedBuffKey`="horn_s_3[overload_switch_effect_down]"
  - **IfNot** 
  - **FinishBuffsById** `_targetType`="BUFF_OWNER"
  - **CreateBuff** buffKey=`horn_s_3[overload_switch_effect_down]` `lifeTimeType`=INFINITY
  - **CheckContainsDerviedBuff** `_derviedBuffKey`="horn_s_3[overload_switch_effect_normal]"
  - **IfNot** 
  - **FinishBuffsById** `_targetType`="BUFF_OWNER"
  - **CreateBuff** buffKey=`horn_s_3[overload_switch_effect_normal]` `lifeTimeType`=INFINITY

**`horn_s_3[signal_melee]`** ← 事件 `ON_ABILITY_SPELL_ON`

- **IfElse** 
  - **CheckContainsBuff** `_buffKeys`=["horn_s_3[overload_start]"] `_targetType`="BUFF_OWNER"
  - **CreateBuff** buffKey=`horn_s_3[signal_melee_overload_signal]` `lifeTimeType`=IMMEDIATELY
  - **CreateBuff** buffKey=`horn_s_2[signal_melee_normal_signal]` `lifeTimeType`=IMMEDIATELY

**`horn_s_3[signal_ranged]`** ← 事件 `ON_ABILITY_SPELL_ON`

- **IfElse** 
  - **CheckContainsBuff** `_buffKeys`=["horn_s_3[overload_start]"] `_targetType`="BUFF_OWNER"
  - **CreateBuff** buffKey=`horn_s_3[signal_melee_overload_signal]` `lifeTimeType`=IMMEDIATELY
  - **CreateBuff** buffKey=`horn_s_2[signal_melee_normal_signal]` `lifeTimeType`=IMMEDIATELY

**`horn_s_3[switch_mode]`** ← 事件 `ON_BUFF_START`

- **ForceCharacterFaceDefaultDirection** `_target`="BUFF_OWNER"
- **IfElse** 
  - **CheckCharacterDefaultDirection** `_target`="BUFF_OWNER"
  - **SwitchMode** `_modeIndex`=3 `_targetType`="TARGET"
  - **SwitchMode** `_modeIndex`=2 `_targetType`="TARGET"

**`horn_s_3[switch_mode]`** ← 事件 `ON_BUFF_FINISH`

- **SwitchMode** `_modeIndex`=0 `_targetType`="TARGET"
- **FinishBuffsById** `_targetType`="BUFF_OWNER"
- **FinishBuffsById** `_targetType`="BUFF_OWNER"

---

## 附：数据边界

| 项目 | 状态 |
|---|---|
| 属性 / 数值 / SP / 范围 / 抬手 | ✅ 明文可得 |
| buff 行为树 | ✅ 明文可得 |
| 技能 → 模板绑定 | ⚠️ 游戏只给 `prefabId`，真实绑定在不可解的 `.ab` 里；本文按命名规律 + `blackboard` 键名双向推断 |
| 动画资源本体 | ❌ 在 `.ab` 包内，不可解 |
| 抬手精度 | ✅ 1/30 秒，是动画事件时刻而非视觉起手帧 |
