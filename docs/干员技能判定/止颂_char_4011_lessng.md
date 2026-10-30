# 止颂 — 技能判定说明

> 数据来源：明文 JSON（`character_table` / `skill_table` / `range_table` / `buff_template_data` / `bakemuzzledata`）。不含反汇编或二进制解析内容。

## 一、干员底子

| 项 | 值 |
|---|---|
| ID | `char_4011_lessng` |
| 职业 | 近卫 / `fearless` |
| 星级 | 6 星 |
| 生命（精二满级） | 3682 |
| 攻击（精二满级） | 1044 |
| 防御（精二满级） | 277 |
| 法抗 | 0% |
| **攻击间隔 baseAttackTime** | **1.5 秒** |
| 攻速 attackSpeed | 100（100% = 无增减） |
| 阻挡 | 1 |
| 部署费用 | 21 |

**攻击间隔换算**（全干员通用）：

```
实际间隔 = baseAttackTime ÷ (attackSpeed / 100)
         = 1.5 ÷ 1.00 = 1.500 秒
```

## 二、抬手（攻击前摇）

来源：`bakemuzzledata/character/char_4011_lessng_*.json` → `bakedAnimDatas.<组>.bakedEvents.<动画名>.eventTime`，取事件 `OnAttack` 时刻。

| 场景 | 动画名 | 抬手 | 帧数(30fps) |
|---|---|---|---|
| **普通攻击** | `Attack` | **0.466667 秒** | 14 帧 |

> 占攻击间隔 31.1%（0.466667 秒 / 1.5 秒）。开技能不会让抬手变快。

| 技能动画 | `Skill_2_Loop` | 0.3 秒 | 9 帧 |
| 技能动画 | `Skill_3_Loop` | 0.666667 秒 | 20 帧 |


## 三、技能逐层拆解

---

### 强力击·γ型　`skchr_lessng_1`

**技能描述（最高级）：**

> 下次攻击的攻击力提高至290%


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
| `atk_scale` | 2.9 |

#### 攻击范围

`rangeId = 1-1`，2 格（direction=1）

> 该技能未指定自己的 `rangeId`，上图是干员**自身范围**。技能若扩大范围，会另有 `rangeId`。

```
■ ■ 
```

#### 判定链

本技能**没有独立 buff 模板**。它属于「一段式数值强化」：开技能只改 `blackboard` 参数与动画，不挂 buff 节点树。

可核对的替代证据：

- 描述中的每个花括号参数都能在 `blackboard` 中找到对应值（见上表）

---

### 虔修对决　`skchr_lessng_2`

**技能描述（最高级）：**

> 部署后，第一天赋效果提升至2.2倍，攻击力+60%，攻击变为2连击


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `8` | — |
| 初始 SP / 消耗 SP | 0 / 0 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 1 | 可存层数 |
| 释放方式 | `PASSIVE` | 被动 |
| 技能形态 | `限时技能` | 持续 24 秒 |
| duration / durationType | 24 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `atk` | 0.6 |
| `talent_scale` | 2.2 |

#### 攻击范围

`rangeId = 1-1`，2 格（direction=1）

> 该技能未指定自己的 `rangeId`，上图是干员**自身范围**。技能若扩大范围，会另有 `rangeId`。

```
■ ■ 
```

#### 判定链

> 匹配方式：按命名规则匹配（层级 B）

**`lessng_s2[eff_manager]`** ← 事件 `ON_BUFF_TRIGGER`

- **IfElse** 
  - **CheckBlocked** `_targetType`="BUFF_OWNER"
  - **CheckContainsBuff** `_buffKeys`=["lessng_s2[buff_eff]"] `_targetType`="BUFF_OWNER"
  - **IfNot** 
  - **CreateBuff** buffKey=`lessng_s2[buff_eff]` `lifeTimeType`=INFINITY
  - **CheckContainsBuff** `_buffKeys`=["lessng_s2[buff_eff]"] `_targetType`="BUFF_OWNER"
  - **FinishBuffsById** `_targetType`="BUFF_OWNER"

**`lessng_s2[switch_mode]`** ← 事件 `ON_BUFF_FINISH`

- **SwitchMode** `_modeIndex`=0 `_targetType`="TARGET"

---

### 苦修破誓　`skchr_lessng_3`

**技能描述（最高级）：**

> 自身免疫异常状态，生命值+110%，攻击被阻挡目标时，造成相当于攻击力220%的物理伤害
> 干员处于异常状态时可以释放技能并清除异常状态，但会对自身造成600点法术伤害


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WITH_TIME` | 随时间自动回复 |
| 初始 SP / 消耗 SP | 30 / 40 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 1 | 可存层数 |
| 释放方式 | `MANUAL` | 手动释放 |
| 技能形态 | `限时技能` | 持续 20 秒 |
| duration / durationType | 20 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `max_hp` | 1.1 |
| `lessng_s3[atk_scale].atk_scale` | 2.2 |
| `magical_value` | 600 |

#### 攻击范围

`rangeId = 1-1`，2 格（direction=1）

> 该技能未指定自己的 `rangeId`，上图是干员**自身范围**。技能若扩大范围，会另有 `rangeId`。

```
■ ■ 
```

#### 判定链

> 匹配方式：由 `blackboard` 键名精确指认（层级 A）

**`lessng_s3[anti]`** ← 事件 `ON_BUFF_START`

- **IfElse** 
  - **CheckContainsResistableAbnormalFlagsBuff** `_targetType`="BUFF_OWNER"
  - **FixedValueDamage** `_targetType`="BUFF_OWNER"
  - **AlwaysNext** 
  - **CreateBuff** buffKey=`lassng_s3[buff_eff]` `lifeTimeType`=INFINITY
  - **IfElse** 
    - **CheckContainsStatusResistableBuff** `_targetType`="BUFF_OWNER"
    - **FixedValueDamage** `_targetType`="BUFF_OWNER"
    - **AlwaysNext** 
    - **CreateBuff** buffKey=`lassng_s3[buff_eff]` `lifeTimeType`=INFINITY
    - **CreateBuff** buffKey=`lassng_s3[normal_audio]` `lifeTimeType`=IMMEDIATELY
- **FinishAllStatusResistableBuffs** `_targetType`="BUFF_OWNER"
- **CreateBuffById** 
- **CreateBuffById** 
- **CreateBuff** buffKey=`lessng_s3[max_hp]` 属性修改=[MAX_HP MULTIPLIER blackboard] `lifeTimeType`=INFINITY
- **CheckContainsBuff** `_buffKeys`=["lassng_s3[buff_eff]"] `_targetType`="BUFF_OWNER"
- …（共 18 个节点，已截断）

**`lessng_s3[atk_scale]`** ← 事件 `ON_CALCULATE_DAMAGE`

- **CheckBlocked** `_targetType`="TARGET"
- **AtkScaleUp** 

---

## 附：数据边界

| 项目 | 状态 |
|---|---|
| 属性 / 数值 / SP / 范围 / 抬手 | ✅ 明文可得 |
| buff 行为树 | ✅ 明文可得 |
| 技能 → 模板绑定 | ⚠️ 游戏只给 `prefabId`，真实绑定在不可解的 `.ab` 里；本文按命名规律 + `blackboard` 键名双向推断 |
| 动画资源本体 | ❌ 在 `.ab` 包内，不可解 |
| 抬手精度 | ✅ 1/30 秒，是动画事件时刻而非视觉起手帧 |
