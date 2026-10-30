# 弑君者 — 技能判定说明

> 数据来源：明文 JSON（`character_table` / `skill_table` / `range_table` / `buff_template_data` / `bakemuzzledata`）。不含反汇编或二进制解析内容。

## 一、干员底子

| 项 | 值 |
|---|---|
| ID | `char_1502_crosly` |
| 职业 | 特种 / `executor` |
| 星级 | 6 星 |
| 生命（精二满级） | 1695 |
| 攻击（精二满级） | 545 |
| 防御（精二满级） | 325 |
| 法抗 | 0% |
| **攻击间隔 baseAttackTime** | **0.93 秒** |
| 攻速 attackSpeed | 100（100% = 无增减） |
| 阻挡 | 1 |
| 部署费用 | 12 |

**攻击间隔换算**（全干员通用）：

```
实际间隔 = baseAttackTime ÷ (attackSpeed / 100)
         = 0.93 ÷ 1.00 = 0.930 秒
```

## 二、抬手（攻击前摇）

来源：`bakemuzzledata/character/char_1502_crosly_*.json` → `bakedAnimDatas.<组>.bakedEvents.<动画名>.eventTime`，取事件 `OnAttack` 时刻。

| 场景 | 动画名 | 抬手 | 帧数(30fps) |
|---|---|---|---|
| **普通攻击** | `Attack_A` | **0.433333 秒** | 13 帧 |

> 占攻击间隔 46.6%（0.433333 秒 / 0.93 秒）。开技能不会让抬手变快。

| 技能动画 | `Skill_1_A` | 0.433333 秒 | 13 帧 |
| 技能动画 | `Skill_1_B` | 0.433333 秒 | 13 帧 |
| 技能动画 | `Skill_2_End` | 0.6 秒 | 18 帧 |


## 三、技能逐层拆解

---

### 尘烟蔽目　`skchr_crosly_1`

**技能描述（最高级）：**

> 部署后攻击力+100%，并获得50%物理和法术闪避


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `8` | — |
| 初始 SP / 消耗 SP | 0 / 0 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 0 | 可存层数 |
| 释放方式 | `PASSIVE` | 被动 |
| 技能形态 | `限时技能` | 持续 10 秒 |
| duration / durationType | 10 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `atk` | 1 |
| `prob` | 0.5 |

#### 攻击范围

`rangeId = 1-1`，2 格（direction=1）

```
■ ■ 
```

#### 判定链

> 匹配方式：按命名规则匹配（层级 B）

**`crosly_s_1[mode]`** ← 事件 `ON_BUFF_FINISH`

- **SwitchMode** `_modeIndex`=0 `_targetType`="BUFF_OWNER"

---

### 硝烟震爆　`skchr_crosly_2`

**技能描述（最高级）：**

> 部署后8秒内停止攻击，自身不容易成为敌人的攻击目标，第一天赋使地面敌人物理与法术命中率降低的效果提高至2.5倍，并在技能结束时对烟雾内的所有地面敌人造成相当于攻击力500%的物理伤害


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `8` | — |
| 初始 SP / 消耗 SP | 0 / 0 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 0 | 可存层数 |
| 释放方式 | `PASSIVE` | 被动 |
| 技能形态 | `无限持续` | 开启后一直生效，直到手动关闭或条件结束 |
| duration / durationType | -1 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `duration` | 8 |
| `taunt_level` | -1 |
| `attack@atk_scale_s2` | 5 |
| `talent_scale` | 2.5 |

#### 攻击范围

`rangeId = 1-1`，2 格（direction=1）

```
■ ■ 
```

#### 判定链

> 匹配方式：按命名规则匹配（层级 B）

**`crosly_s_2[end]`** ← 事件 `ON_BUFF_FINISH`

- **SwitchMode** `_modeIndex`=0 `_targetType`="BUFF_OWNER"

**`crosly_s_2[end]`** ← 事件 `ON_ABNORMAL_FLAG_DIRTY`

- **IfElse** 
  - **CheckAbnormalFlags** `_targetType`="BUFF_OWNER"
  - **FinishBuff** 

**`crosly_s_2[end]`** ← 事件 `ON_BUFF_START`

- **IfElse** 
  - **CheckAbnormalFlags** `_targetType`="BUFF_OWNER"
  - **FinishBuff** 

**`crosly_s_2[safe]`** ← 事件 `ON_BUFF_START`

- **FinishBuffsById** `_targetType`="BUFF_OWNER"

**`crosly_s_2[start]`** ← 事件 `ON_BUFF_FINISH`

- **SwitchMode** `_modeIndex`=4 `_targetType`="BUFF_OWNER"

---

### 烽烟行刑场　`skchr_crosly_3`

**技能描述（最高级）：**

> 部署后第一天赋的生效范围扩大，弑君者消失在烟雾中，获得隐匿且阻挡数变为0，每2秒现身对烟雾内的一名地面敌人造成两次相当于攻击力250%的物理伤害并使目标晕眩4秒（对同一目标6秒内只会触发一次）


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `8` | — |
| 初始 SP / 消耗 SP | 0 / 0 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 0 | 可存层数 |
| 释放方式 | `PASSIVE` | 被动 |
| 技能形态 | `限时技能` | 持续 16 秒 |
| duration / durationType | 16 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `attack@s3_cd` | 2 |
| `attack@times` | 2 |
| `attack@hit_interval` | 0.1 |
| `attack@atk_scale_s3` | 2.5 |
| `attack@stun` | 4 |
| `mark_duration` | 6 |

#### 攻击范围

`rangeId = x-1`，13 格（direction=1）

```
· · ■ · · 
· ■ ■ ■ · 
■ ■ ■ ■ ■ 
· ■ ■ ■ · 
· · ■ · · 
```

#### 判定链

> 匹配方式：按命名规则匹配（层级 B）

**`crosly_s_3[mode]`** ← 事件 `ON_BUFF_FINISH`

- **FinishBuffsById** `_targetType`="BUFF_OWNER"
- **AlwaysNext** 
- **SwitchMode** `_modeIndex`=0 `_targetType`="BUFF_OWNER"

**`crosly_s_3[mode]`** ← 事件 `ON_OUTPUT_MODIFIER`

- **CreateBuff** buffKey=`crosly_s_3[mark]` `lifeTimeType`=LIMITED

---

## 附：数据边界

| 项目 | 状态 |
|---|---|
| 属性 / 数值 / SP / 范围 / 抬手 | ✅ 明文可得 |
| buff 行为树 | ✅ 明文可得 |
| 技能 → 模板绑定 | ⚠️ 游戏只给 `prefabId`，真实绑定在不可解的 `.ab` 里；本文按命名规律 + `blackboard` 键名双向推断 |
| 动画资源本体 | ❌ 在 `.ab` 包内，不可解 |
| 抬手精度 | ✅ 1/30 秒，是动画事件时刻而非视觉起手帧 |
