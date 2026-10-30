# 若叶睦 — 技能判定说明

> 数据来源：明文 JSON（`character_table` / `skill_table` / `range_table` / `buff_template_data` / `bakemuzzledata`）。不含反汇编或二进制解析内容。

## 一、干员底子

| 项 | 值 |
|---|---|
| ID | `char_4183_mortis` |
| 职业 | 特种 / `dollkeeper` |
| 星级 | 5 星 |
| 生命（精二满级） | 2211 |
| 攻击（精二满级） | 752 |
| 防御（精二满级） | 285 |
| 法抗 | 0% |
| **攻击间隔 baseAttackTime** | **1.2 秒** |
| 攻速 attackSpeed | 100（100% = 无增减） |
| 阻挡 | 2 |
| 部署费用 | 15 |

**攻击间隔换算**（全干员通用）：

```
实际间隔 = baseAttackTime ÷ (attackSpeed / 100)
         = 1.2 ÷ 1.00 = 1.200 秒
```

## 二、抬手（攻击前摇）

来源：`bakemuzzledata/character/char_4183_mortis_*.json` → `bakedAnimDatas.<组>.bakedEvents.<动画名>.eventTime`，取事件 `OnAttack` 时刻。

| 场景 | 动画名 | 抬手 | 帧数(30fps) |
|---|---|---|---|
| **普通攻击** | `Attack` | **0.433333 秒** | 13 帧 |

> 占攻击间隔 36.1%（0.433333 秒 / 1.2 秒）。开技能不会让抬手变快。

| 技能动画 | `Skill_1` | 0.433333 秒 | 13 帧 |
| 技能动画 | `Skill_2` | 0.333333 秒 | 10 帧 |


## 三、技能逐层拆解

---

### 多首野兽　`skchr_mortis_1`

**技能描述（最高级）：**

> 防御力+120%，阻挡数+2，更容易成为敌人的攻击目标；技能期间被击倒后，<替身>也能阻挡敌人且享受技能效果，直到<替身>退场


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WITH_TIME` | 随时间自动回复 |
| 初始 SP / 消耗 SP | 15 / 20 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 1 | 可存层数 |
| 释放方式 | `MANUAL` | 手动释放 |
| 技能形态 | `限时技能` | 持续 15 秒 |
| duration / durationType | 15 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `def` | 1.2 |
| `block_cnt` | 2 |
| `taunt_level` | 1 |

#### 攻击范围

`rangeId = 1-1`，2 格（direction=1）

> 该技能未指定自己的 `rangeId`，上图是干员**自身范围**。技能若扩大范围，会另有 `rangeId`。

```
■ ■ 
```

#### 判定链

> 匹配方式：按命名规则匹配（层级 B）

**`mortis_s1[add_attr]`** ← 事件 `ON_BUFF_START`

- **CreateBuff** buffKey=`mortis_s1[add_attr_core]` templateKey=`mortis_s1[add_attr_core]` 属性修改=[DEF MULTIPLIER blackboard, BLOCK_CNT ADDITION blackboard, TAUNT_LEVEL ADDITION blackboard] `lifeTimeType`=INFINITY

**`mortis_s1[add_attr_core]`** ← 事件 `ON_SKILL_FINISH`

- **CheckSkillIndex** 
- **IfElse** 
  - **CheckContainsBuff** `_buffKeys`=["mortis_to_stand_mark"] `_targetType`="BUFF_OWNER"
  - **FinishBuffsById** `_targetType`="BUFF_OWNER"
  - **CreateBuff** buffKey=`mortis_stand[block_dec]` 属性修改=[BLOCK_CNT ADDITION -2.0] `overrideType`=UNIQUE `lifeTimeType`=INFINITY
  - **FinishBuff** 

**`mortis_s1[switch_mode]`** ← 事件 `ON_BUFF_START`

- **SwitchMode** `_modeIndex`=0 `_targetType`="BUFF_OWNER"

**`mortis_s1[switch_mode]`** ← 事件 `ON_BUFF_TRIGGER`

- **CheckCharSkillAffecting** `_targetType`="BUFF_OWNER"
- **IfNot** 
- **FinishBuff** 

**`mortis_s1[switch_mode]`** ← 事件 `ON_BUFF_FINISH`

- **SwitchMode** `_modeIndex`=0 `_targetType`="BUFF_OWNER"

---

### 破坏与滋养　`skchr_mortis_2`

**技能描述（最高级）：**

> 攻击范围扩大，攻击间隔略微缩短，每次攻击变为攻击力120%法术伤害的三连发，随机攻击范围内的目标，每次攻击到敌人时自身受到20点法术伤害


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WITH_TIME` | 随时间自动回复 |
| 初始 SP / 消耗 SP | 11 / 25 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 1 | 可存层数 |
| 释放方式 | `MANUAL` | 手动释放 |
| 技能形态 | `限时技能` | 持续 15 秒 |
| duration / durationType | 15 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `base_attack_time` | -0.3 |
| `attack@atk_scale` | 1.2 |
| `value` | 20 |

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

**`mortis_s2[self_damage]`** ← 事件 `ON_BEFORE_TARGET_APPLY_MODIFIER`

- **IsDamage** 
- **CheckContainsBuff** `_buffKeys`=["char_mortis_self_mark"] `_targetType`="MODIFIER_TARGET"
- **IfNot** 
- **FixedValueDamage** `_targetType`="BUFF_OWNER"

**`mortis_s2[switch_mode]`** ← 事件 `ON_BUFF_START`

- **SwitchMode** `_modeIndex`=0 `_targetType`="BUFF_OWNER"

**`mortis_s2[switch_mode]`** ← 事件 `ON_BUFF_TRIGGER`

- **CheckCharSkillAffecting** `_targetType`="BUFF_OWNER"
- **IfNot** 
- **FinishBuff** 

**`mortis_s2[switch_mode]`** ← 事件 `ON_BUFF_FINISH`

- **SwitchMode** `_modeIndex`=0 `_targetType`="BUFF_OWNER"

---

## 附：数据边界

| 项目 | 状态 |
|---|---|
| 属性 / 数值 / SP / 范围 / 抬手 | ✅ 明文可得 |
| buff 行为树 | ✅ 明文可得 |
| 技能 → 模板绑定 | ⚠️ 游戏只给 `prefabId`，真实绑定在不可解的 `.ab` 里；本文按命名规律 + `blackboard` 键名双向推断 |
| 动画资源本体 | ❌ 在 `.ab` 包内，不可解 |
| 抬手精度 | ✅ 1/30 秒，是动画事件时刻而非视觉起手帧 |
