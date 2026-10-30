# 史尔特尔 — 技能判定说明

> 数据来源：明文 JSON（`character_table` / `skill_table` / `range_table` / `buff_template_data` / `bakemuzzledata`）。不含反汇编或二进制解析内容。

## 一、干员底子

| 项 | 值 |
|---|---|
| ID | `char_350_surtr` |
| 职业 | 近卫 / `artsfghter` |
| 星级 | 6 星 |
| 生命（精二满级） | 2916 |
| 攻击（精二满级） | 672 |
| 防御（精二满级） | 414 |
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

来源：`bakemuzzledata/character/char_350_surtr_*.json` → `bakedAnimDatas.<组>.bakedEvents.<动画名>.eventTime`，取事件 `OnAttack` 时刻。

| 场景 | 动画名 | 抬手 | 帧数(30fps) |
|---|---|---|---|
| **普通攻击** | `Attack` | **0.4 秒** | 12 帧 |

> 占攻击间隔 32.0%（0.4 秒 / 1.25 秒）。开技能不会让抬手变快。

| 技能动画 | `Skill_2` | 0.433333 秒 | 13 帧 |
| 技能动画 | `Skill_2_Down` | 0.433333 秒 | 13 帧 |
| 技能动画 | `Skill_3_Loop` | 0.4 秒 | 12 帧 |


## 三、技能逐层拆解

---

### 烈焰魔剑　`skchr_surtr_1`

**技能描述（最高级）：**

> 下次攻击的攻击力提升至310%，如果将目标击倒则立即恢复所有技力


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WHEN_ATTACK` | 每次攻击回复 |
| 初始 SP / 消耗 SP | 0 / 2 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 1 | 可存层数 |
| 释放方式 | `AUTO` | 自动释放 |
| 技能形态 | `瞬发技能` | 无持续时间，效果立即结算 |
| duration / durationType | 0 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `atk_scale` | 3.1 |

#### 攻击范围

`rangeId = 1-1`，2 格（direction=1）

> 该技能未指定自己的 `rangeId`，上图是干员**自身范围**。技能若扩大范围，会另有 `rangeId`。

```
■ ■ 
```

#### 判定链

> 匹配方式：按命名规则匹配（层级 B）

**`surtr_s_1`** ← 事件 `ON_TARGET_KILLED`

- **ModifySp** `_targetType`="BUFF_OWNER" `_forceFlag`=True

---

### 熔核巨影　`skchr_surtr_2`

**技能描述（最高级）：**

> 攻击力+120%，攻击距离+1，攻击目标数+1，仅攻击到一个敌人时对其攻击力提升至160%


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WITH_TIME` | 随时间自动回复 |
| 初始 SP / 消耗 SP | 12 / 18 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 1 | 可存层数 |
| 释放方式 | `MANUAL` | 手动释放 |
| 技能形态 | `限时技能` | 持续 18 秒 |
| duration / durationType | 18 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `atk` | 1.2 |
| `ability_range_forward_extend` | 1 |
| `attack@max_target` | 2 |
| `attack@surtr_s_2[critical].atk_scale` | 1.6 |

#### 攻击范围

`rangeId = 1-1`，2 格（direction=1）

> 该技能未指定自己的 `rangeId`，上图是干员**自身范围**。技能若扩大范围，会另有 `rangeId`。

```
■ ■ 
```

#### 判定链

> 匹配方式：按命名规则匹配（层级 B）

**`surtr_s_2`** ← 事件 `ON_BUFF_FINISH`

- **SwitchMode** `_modeIndex`=0 `_targetType`="TARGET"
- **FinishBuffsById** `_targetType`="BUFF_OWNER"

**`surtr_s_2`** ← 事件 `ON_BUFF_START`

- **SwitchMode** `_modeIndex`=1 `_targetType`="TARGET"

**`surtr_s_2[critical]`** ← 事件 `ON_TARGET_KILLED`

- **CreateBuff** buffKey=`surtr_s_2[kill_one]` `lifeTimeType`=INFINITY

**`surtr_s_2[critical]`** ← 事件 `ON_CALCULATE_DAMAGE`

- **CheckContainsBuff** `_buffKeys`=["surtr_s_2[kill_one]"] `_targetType`="BUFF_OWNER"
- **IfNot** 
- **FilterAbilityValidCastTargetCnt** `_condType`="EQUALS"
- **AtkScaleUp** 

**`surtr_s_2[mark]`** ← 事件 `ON_BUFF_START`

- **CreateBuff** buffKey=`surtr_s_2[critical]` templateKey=`surtr_s_2[critical]` `lifeTimeType`=INFINITY

**`surtr_s_2[refresh]`** ← 事件 `ON_BUFF_FINISH`

- **FinishBuffsById** `_targetType`="BUFF_OWNER"
- **FinishBuffsById** `_targetType`="BUFF_OWNER"

---

### 黄昏　`skchr_surtr_3`

**技能描述（最高级）：**

> 立即恢复所有生命；攻击力+330%，攻击距离+2，攻击目标数+3，生命上限+5000，逐渐流失生命（60秒后到达最大生命20%/秒）；持续时间无限


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WITH_TIME` | 随时间自动回复 |
| 初始 SP / 消耗 SP | 0 / 5 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 1 | 可存层数 |
| 释放方式 | `MANUAL` | 手动释放 |
| 技能形态 | `无限持续` | 开启后一直生效，直到手动关闭或条件结束 |
| duration / durationType | -1 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `atk` | 3.3 |
| `ability_range_forward_extend` | 2 |
| `max_hp` | 5000 |
| `interval` | 0.2 |
| `hp_ratio` | 0.2 |
| `duration` | 60 |
| `attack@max_target` | 4 |

#### 攻击范围

`rangeId = 1-1`，2 格（direction=1）

> 该技能未指定自己的 `rangeId`，上图是干员**自身范围**。技能若扩大范围，会另有 `rangeId`。

```
■ ■ 
```

#### 判定链

> 匹配方式：按命名规则匹配（层级 B）

**`surtr_s_3`** ← 事件 `ON_BUFF_START`

- **SwitchMode** `_modeIndex`=1 `_targetType`="TARGET"
- **HealViaMaxHpRatio** 

**`surtr_s_3[bleeding]`** ← 事件 `ON_BUFF_START`

- **BleedingDamageIncreasingReset** 

**`surtr_s_3[bleeding]`** ← 事件 `ON_BUFF_TRIGGER`

- **BleedingDamagePerSec** 

---

## 附：数据边界

| 项目 | 状态 |
|---|---|
| 属性 / 数值 / SP / 范围 / 抬手 | ✅ 明文可得 |
| buff 行为树 | ✅ 明文可得 |
| 技能 → 模板绑定 | ⚠️ 游戏只给 `prefabId`，真实绑定在不可解的 `.ab` 里；本文按命名规律 + `blackboard` 键名双向推断 |
| 动画资源本体 | ❌ 在 `.ab` 包内，不可解 |
| 抬手精度 | ✅ 1/30 秒，是动画事件时刻而非视觉起手帧 |
