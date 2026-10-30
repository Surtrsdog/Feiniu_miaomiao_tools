# 旅骨 — 技能判定说明

> 数据来源：明文 JSON（`character_table` / `skill_table` / `range_table` / `buff_template_data` / `bakemuzzledata`）。不含反汇编或二进制解析内容。

## 一、干员底子

| 项 | 值 |
|---|---|
| ID | `char_4232_hbound` |
| 职业 | 特种 / `alchemist` |
| 星级 | 5 星 |
| 生命（精二满级） | 1160 |
| 攻击（精二满级） | 461 |
| 防御（精二满级） | 100 |
| 法抗 | 3000% |
| **攻击间隔 baseAttackTime** | **1.5 秒** |
| 攻速 attackSpeed | 100（100% = 无增减） |
| 阻挡 | 1 |
| 部署费用 | 19 |

**攻击间隔换算**（全干员通用）：

```
实际间隔 = baseAttackTime ÷ (attackSpeed / 100)
         = 1.5 ÷ 1.00 = 1.500 秒
```

## 二、抬手（攻击前摇）

来源：`bakemuzzledata/character/char_4232_hbound_*.json` → `bakedAnimDatas.<组>.bakedEvents.<动画名>.eventTime`，取事件 `OnAttack` 时刻。

| 场景 | 动画名 | 抬手 | 帧数(30fps) |
|---|---|---|---|
| **普通攻击** | `Attack` | **0.433333 秒** | 13 帧 |

> 占攻击间隔 28.9%（0.433333 秒 / 1.5 秒）。开技能不会让抬手变快。

| 技能动画 | `Skill_1` | 0.433333 秒 | 13 帧 |
| 技能动画 | `Skill_2` | 0.433333 秒 | 13 帧 |


## 三、技能逐层拆解

---

### 触礁　`skchr_hbound_1`

**技能描述（最高级）：**

> 投掷一个炼金单元，在10秒内使落点周围的地面敌人移动速度-50%，每秒受到相当于攻击力80%的法术伤害
> 可充能2次


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WITH_TIME` | 随时间自动回复 |
| 初始 SP / 消耗 SP | 6 / 16 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 2 | 可存层数 |
| 释放方式 | `MANUAL` | 手动释放 |
| 技能形态 | `无限持续` | 开启后一直生效，直到手动关闭或条件结束 |
| duration / durationType | -1 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `projectile_delay_time` | 10 |
| `atk_scale` | 0.8 |
| `projectile_range` | 1.5 |
| `interval` | 1 |
| `move_speed` | -0.5 |

#### 攻击范围

`rangeId = 3-5`，13 格（direction=1）

> 该技能未指定自己的 `rangeId`，上图是干员**自身范围**。技能若扩大范围，会另有 `rangeId`。

```
■ ■ · 
■ ■ ■ 
■ ■ ■ 
■ ■ ■ 
■ ■ · 
```

#### 判定链

> 匹配方式：按命名规则匹配（层级 B）

**`hbound_s_1[dot]`** ← 事件 `ON_BUFF_TRIGGER`

- **NoSourceDamage** 
- **CreateEffectHookProjectileEffect** `_targetType`="BUFF_OWNER"
- **PlayAudio** `_target`="TARGET"

---

### 座浅　`skchr_hbound_2`

**技能描述（最高级）：**

> 投掷一个炼金单元，在35秒内使落点周围的地面敌人每秒受到相当于攻击力20%的法术伤害；重量大于等于3的敌人移动速度-70%，每秒额外受到相当于攻击力180%的法术伤害


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WITH_TIME` | 随时间自动回复 |
| 初始 SP / 消耗 SP | 32 / 50 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 1 | 可存层数 |
| 释放方式 | `MANUAL` | 手动释放 |
| 技能形态 | `无限持续` | 开启后一直生效，直到手动关闭或条件结束 |
| duration / durationType | -1 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `projectile_delay_time` | 35 |
| `atk_scale` | 0.2 |
| `projectile_range` | 2 |
| `interval` | 1 |
| `move_speed` | -0.7 |
| `heavy_atk_scale` | 1.8 |
| `value` | 3 |

#### 攻击范围

`rangeId = 3-5`，13 格（direction=1）

> 该技能未指定自己的 `rangeId`，上图是干员**自身范围**。技能若扩大范围，会另有 `rangeId`。

```
■ ■ · 
■ ■ ■ 
■ ■ ■ 
■ ■ ■ 
■ ■ · 
```

#### 判定链

> 匹配方式：按命名规则匹配（层级 B）

**`hbound_s_2[buff]`** ← 事件 `ON_BUFF_TRIGGER`

- **IfTargetSide** `_targetType`="BUFF_OWNER"
- **NoSourceDamage** 
- **CreateEffectHookProjectileEffect** `_targetType`="TARGET"

**`hbound_s_2[buff]`** ← 事件 `ON_BUFF_START`

- **ModifyBlackboard** 
- **CreateBuff** buffKey=`hbound_s_2[weight_detector]` templateKey=`hbound_s_2[weight_detector]` `lifeTimeType`=INFINITY

**`hbound_s_2[heavy_damage]`** ← 事件 `ON_BUFF_TRIGGER`

- **ModifyBlackboard** 
- **NoSourceDamage** 
- **PlayAudio** `_target`="TARGET"

**`hbound_s_2[weight_detector]`** ← 事件 `ON_BUFF_TRIGGER`

- **IfTargetSide** `_targetType`="BUFF_OWNER"
- **AssignAttributeToBB** `_targetType`="BUFF_OWNER"
- **FilterByBlackboardValue** `_condType`="EQUALS" `_targetType`="BUFF_OWNER"
- **IfNot** 
- **ModifyBlackboard** 
- **IfElse** 
  - **FilterByBlackboardValue** `_condType`="GE" `_targetType`="BUFF_OWNER"
  - **CheckContainsDerviedBuff** `_derviedBuffKey`="hbound_s_2[heavy_damage]"
  - **IfNot** 
  - **CreateBuff** buffKey=`hbound_s_2[heavy_damage]` templateKey=`hbound_s_2[heavy_damage]` 属性修改=[MOVE_SPEED FINAL_SCALER blackboard] `lifeTimeType`=INFINITY
  - **PlayAudio** `_target`="BUFF_OWNER"
  - **FinishDerivedBuffById** 

**`hbound_s_2[weight_detector]`** ← 事件 `ON_BUFF_START`

- **IfTargetSide** `_targetType`="BUFF_OWNER"
- **AssignAttributeToBB** `_targetType`="BUFF_OWNER"
- **IfElse** 
  - **FilterByTargetMassLevel** `_condType`="GE" `_target`="TARGET"
  - **CreateBuff** buffKey=`hbound_s_2[heavy_damage]` templateKey=`hbound_s_2[heavy_damage]` 属性修改=[MOVE_SPEED FINAL_SCALER blackboard] `lifeTimeType`=INFINITY
  - **PlayAudio** `_target`="BUFF_OWNER"

---

## 附：数据边界

| 项目 | 状态 |
|---|---|
| 属性 / 数值 / SP / 范围 / 抬手 | ✅ 明文可得 |
| buff 行为树 | ✅ 明文可得 |
| 技能 → 模板绑定 | ⚠️ 游戏只给 `prefabId`，真实绑定在不可解的 `.ab` 里；本文按命名规律 + `blackboard` 键名双向推断 |
| 动画资源本体 | ❌ 在 `.ab` 包内，不可解 |
| 抬手精度 | ✅ 1/30 秒，是动画事件时刻而非视觉起手帧 |
