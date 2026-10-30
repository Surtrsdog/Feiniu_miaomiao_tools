# 妮芙 — 技能判定说明

> 数据来源：明文 JSON（`character_table` / `skill_table` / `range_table` / `buff_template_data` / `bakemuzzledata`）。不含反汇编或二进制解析内容。

## 一、干员底子

| 项 | 值 |
|---|---|
| ID | `char_4146_nymph` |
| 职业 | 术师 / `primcaster` |
| 星级 | 6 星 |
| 生命（精二满级） | 1650 |
| 攻击（精二满级） | 655 |
| 防御（精二满级） | 129 |
| 法抗 | 1500% |
| **攻击间隔 baseAttackTime** | **1.6 秒** |
| 攻速 attackSpeed | 100（100% = 无增减） |
| 阻挡 | 1 |
| 部署费用 | 21 |

**攻击间隔换算**（全干员通用）：

```
实际间隔 = baseAttackTime ÷ (attackSpeed / 100)
         = 1.6 ÷ 1.00 = 1.600 秒
```

## 二、抬手（攻击前摇）

来源：`bakemuzzledata/character/char_4146_nymph_*.json` → `bakedAnimDatas.<组>.bakedEvents.<动画名>.eventTime`，取事件 `OnAttack` 时刻。

| 场景 | 动画名 | 抬手 | 帧数(30fps) |
|---|---|---|---|
| **普通攻击** | `Attack` | **0.533333 秒** | 16 帧 |

> 占攻击间隔 33.3%（0.533333 秒 / 1.6 秒）。开技能不会让抬手变快。

| 技能动画 | `Skill_2` | 0.266667 秒 | 8 帧 |
| 技能动画 | `Skill_3_Attack` | 0.533333 秒 | 16 帧 |


## 三、技能逐层拆解

---

### 笞心击　`skchr_nymph_1`

**技能描述（最高级）：**

> 攻击力+110%，攻击附带造成法术伤害15%的凋亡损伤，若目标处于凋亡损伤爆发期间则对其额外造成相当于攻击力50%的元素伤害


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WITH_TIME` | 随时间自动回复 |
| 初始 SP / 消耗 SP | 20 / 30 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 1 | 可存层数 |
| 释放方式 | `MANUAL` | 手动释放 |
| 技能形态 | `限时技能` | 持续 20 秒 |
| duration / durationType | 20 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `atk` | 1.1 |
| `attack@ep_damage_ratio` | 0.15 |
| `attack@extra_ep_damage_scale` | 0.5 |

#### 攻击范围

`rangeId = 3-1`，10 格（direction=1）

> 该技能未指定自己的 `rangeId`，上图是干员**自身范围**。技能若扩大范围，会另有 `rangeId`。

```
■ ■ ■ · 
■ ■ ■ ■ 
■ ■ ■ · 
```

#### 判定链

> 匹配方式：按命名规则匹配（层级 B）

**`nymph_s_1[ep_damage]`** ← 事件 `ON_BUFF_START`

- **CheckCharSkillAffecting** `_targetType`="BUFF_SOURCE"
- **FilterEPBreakRecoveryType** `_target`="BUFF_OWNER"
- **AdvancedApplyDamage** `_targetType`="TARGET"

---

### 怵然震爆　`skchr_nymph_2`

**技能描述（最高级）：**

> 对敌人造成一次相当于攻击力400%的法术伤害、使其恐惧5秒，并对目标周围造成一次等额法术溅射伤害，均附带造成法术伤害25%的凋亡损伤；若攻击到的单位处于凋亡损伤爆发期间，使第一天赋造成的伤害效果提高至攻击力的100%
> 可充能2次


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WITH_TIME` | 随时间自动回复 |
| 初始 SP / 消耗 SP | 9 / 12 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 2 | 可存层数 |
| 释放方式 | `MANUAL` | 手动释放 |
| 技能形态 | `无限持续` | 开启后一直生效，直到手动关闭或条件结束 |
| duration / durationType | -1 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `atk_scale` | 4 |
| `ep_damage_ratio` | 0.25 |
| `fear` | 5 |
| `element_atk_scale` | 1 |
| `projectile_range` | 1.5 |
| `ct` | 2 |

#### 攻击范围

`rangeId = 3-1`，10 格（direction=1）

> 该技能未指定自己的 `rangeId`，上图是干员**自身范围**。技能若扩大范围，会另有 `rangeId`。

```
■ ■ ■ · 
■ ■ ■ ■ 
■ ■ ■ · 
```

#### 判定链

> 匹配方式：按命名规则匹配（层级 B）

**`nymph_s_2`** ← 事件 `ON_BUFF_START`

- **IfElse** 
  - **FilterEPBreakRecoveryType** `_target`="BUFF_OWNER"
  - **CreateBuff** buffKey=`nymph_t_1[ep_damage]` templateKey=`nymph_t_1[ep_damage]` `lifeTimeType`=INFINITY
  - **FinishBuff** 
  - **FinishBuff** 

**`nymph_s_2[damage]`** ← 事件 `ON_BUFF_START`

- **CheckUnitAlive** 
- **AdvancedApplyDamage** `_targetType`="TARGET"
- **CalculateBlackboardValueViaParams** 
- **ApplyElementDamage** `_targetType`="BUFF_OWNER"
- **AlwaysNext** 
- **CheckUnitInRebornState** 
- **IfNot** 
- **CreateBuff** buffKey=`nymph_s_2` templateKey=`nymph_s_2` `lifeTimeType`=IMMEDIATELY

**`nymph_s_2[trace_taregt]`** ← 事件 `ON_BUFF_START`

- **CheckUnitAlive** 
- **IfElse** 
  - **IsCharacterOrTokenOrTrap** `_targetType`="BUFF_OWNER"
  - **CheckUnitAlive** 
  - **CreateBuff** buffKey=`fear` `lifeTimeType`=LIMITED
- **AdvancedApplyDamage** `_targetType`="TARGET"
- **CalculateBlackboardValueViaParams** 
- **ApplyElementDamage** `_targetType`="BUFF_OWNER"
- **AlwaysNext** 
- **CheckUnitInRebornState** 
- **IfNot** 
- **CreateBuff** buffKey=`nymph_s_2` templateKey=`nymph_s_2` `lifeTimeType`=IMMEDIATELY

---

### 心防溃决　`skchr_nymph_3`

**技能描述（最高级）：**

> 攻击范围扩大，攻击力+220%，攻击速度+60，同时攻击2个目标，若目标处于凋亡损伤爆发期间，攻击造成元素伤害


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WITH_TIME` | 随时间自动回复 |
| 初始 SP / 消耗 SP | 36 / 55 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 1 | 可存层数 |
| 释放方式 | `MANUAL` | 手动释放 |
| 技能形态 | `限时技能` | 持续 35 秒 |
| duration / durationType | 35 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `atk` | 2.2 |
| `attack_speed` | 60 |
| `attack@max_target` | 2 |
| `attack@split_atk_scale` | 1 |
| `attack@magic_atk_scale` | 0 |

#### 攻击范围

`rangeId = 3-3`，12 格（direction=1）

```
■ ■ ■ ■ 
■ ■ ■ ■ 
■ ■ ■ ■ 
```

#### 判定链

本技能**没有独立 buff 模板**。它属于「一段式数值强化」：开技能只改 `blackboard` 参数与动画，不挂 buff 节点树。

可核对的替代证据：

- 描述中的每个花括号参数都能在 `blackboard` 中找到对应值（见上表）

---

## 附：数据边界

| 项目 | 状态 |
|---|---|
| 属性 / 数值 / SP / 范围 / 抬手 | ✅ 明文可得 |
| buff 行为树 | ✅ 明文可得 |
| 技能 → 模板绑定 | ⚠️ 游戏只给 `prefabId`，真实绑定在不可解的 `.ab` 里；本文按命名规律 + `blackboard` 键名双向推断 |
| 动画资源本体 | ❌ 在 `.ab` 包内，不可解 |
| 抬手精度 | ✅ 1/30 秒，是动画事件时刻而非视觉起手帧 |
