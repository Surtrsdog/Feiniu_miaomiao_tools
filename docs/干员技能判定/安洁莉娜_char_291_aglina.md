# 安洁莉娜 — 技能判定说明

> 数据来源：明文 JSON（`character_table` / `skill_table` / `range_table` / `buff_template_data` / `bakemuzzledata`）。不含反汇编或二进制解析内容。

## 一、干员底子

| 项 | 值 |
|---|---|
| ID | `char_291_aglina` |
| 职业 | 辅助 / `slower` |
| 星级 | 6 星 |
| 生命（精二满级） | 1385 |
| 攻击（精二满级） | 542 |
| 防御（精二满级） | 120 |
| 法抗 | 2500% |
| **攻击间隔 baseAttackTime** | **1.9 秒** |
| 攻速 attackSpeed | 100（100% = 无增减） |
| 阻挡 | 1 |
| 部署费用 | 16 |

**攻击间隔换算**（全干员通用）：

```
实际间隔 = baseAttackTime ÷ (attackSpeed / 100)
         = 1.9 ÷ 1.00 = 1.900 秒
```

## 二、抬手（攻击前摇）

来源：`bakemuzzledata/character/char_291_aglina_*.json` → `bakedAnimDatas.<组>.bakedEvents.<动画名>.eventTime`，取事件 `OnAttack` 时刻。

| 场景 | 动画名 | 抬手 | 帧数(30fps) |
|---|---|---|---|
| **普通攻击** | `Attack` | **0.633333 秒** | 19 帧 |

> 占攻击间隔 33.3%（0.633333 秒 / 1.9 秒）。开技能不会让抬手变快。

| 技能动画 | `Skill1_Loop` | 0.233333 秒 | 7 帧 |
| 技能动画 | `Skill2_Loop` | 0.233333 秒 | 7 帧 |


## 三、技能逐层拆解

---

### 秘杖·速充模式　`skchr_aglina_1`

**技能描述（最高级）：**

> 攻击力+110%
> 技能自动开启


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WHEN_ATTACK` | 每次攻击回复 |
| 初始 SP / 消耗 SP | 0 / 10 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 1 | 可存层数 |
| 释放方式 | `AUTO` | 自动释放 |
| 技能形态 | `限时技能` | 持续 35 秒 |
| duration / durationType | 35 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `atk` | 1.1 |

#### 攻击范围

`rangeId = y-2`，12 格（direction=1）

> 该技能未指定自己的 `rangeId`，上图是干员**自身范围**。技能若扩大范围，会另有 `rangeId`。

```
■ ■ ■ ■ 
■ ■ ■ ■ 
■ ■ ■ ■ 
```

#### 判定链

> 匹配方式：按命名规则匹配（层级 B）

**`aglina_s1[sync_params]`** ← 事件 `ON_BUFF_START`

- **AssignBuffBlackboardFromOthers** `_targetType`="BUFF_OWNER"
- **CalculateBlackboardValueViaParams** 
- **CalculateBlackboardValueViaParams** 
- **CalculateBlackboardValueViaParams** 
- **CalculateBlackboardValueViaParams** 
- **CalculateBlackboardValueViaParams** 
- **CalculateBlackboardValueViaParams** 
- **CalculateBlackboardValueViaParams** 
- **CalculateBlackboardValueViaParams** 
- **ModifyAbilityBlackboard** 
- **ModifyAbilityBlackboard** 
- **ModifyAbilityBlackboard** 
- **ModifyAbilityBlackboard** 

---

### 秘杖·微粒模式　`skchr_aglina_2`

**技能描述（最高级）：**

> 攻击间隔极大幅度缩短，但每次攻击只能造成相当于攻击力45%的法术伤害
> 技能未开启时无法普通攻击


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WITH_TIME` | 随时间自动回复 |
| 初始 SP / 消耗 SP | 10 / 15 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 1 | 可存层数 |
| 释放方式 | `MANUAL` | 手动释放 |
| 技能形态 | `限时技能` | 持续 30 秒 |
| duration / durationType | 30 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `base_attack_time` | 0.15 |
| `damage_scale` | 0.45 |

#### 攻击范围

`rangeId = y-2`，12 格（direction=1）

> 该技能未指定自己的 `rangeId`，上图是干员**自身范围**。技能若扩大范围，会另有 `rangeId`。

```
■ ■ ■ ■ 
■ ■ ■ ■ 
■ ■ ■ ■ 
```

#### 判定链

> 匹配方式：按命名规则匹配（层级 B）

**`aglina_s2[power]`** ← 事件 `ON_BUFF_TRIGGER`

- **CheckAbnormalImmune** `_targetType`="BUFF_OWNER"
- **CreateBuff** buffKey=`aglina_s2[levitate]` `lifeTimeType`=LIMITED

**`aglina_s2[sync_params]`** ← 事件 `ON_BUFF_START`

- **AssignBuffBlackboardFromOthers** `_targetType`="BUFF_OWNER"
- **CalculateBlackboardValueViaParams** 
- **CalculateBlackboardValueViaParams** 
- **CalculateBlackboardValueViaParams** 
- **CalculateBlackboardValueViaParams** 
- **ModifyAbilityBlackboard** 
- **ModifyAbilityBlackboard** 

---

### 秘杖·反重力模式　`skchr_aglina_3`

**技能描述（最高级）：**

> 全场所有敌人失重，攻击范围扩大，攻击力+150%，可以攻击5个敌人
> 技能未开启时无法普通攻击


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WITH_TIME` | 随时间自动回复 |
| 初始 SP / 消耗 SP | 10 / 25 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 1 | 可存层数 |
| 释放方式 | `MANUAL` | 手动释放 |
| 技能形态 | `限时技能` | 持续 25 秒 |
| duration / durationType | 25 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `atk` | 1.5 |
| `attack@max_target` | 5 |

#### 攻击范围

`rangeId = y-4`，19 格（direction=1）

```
■ ■ ■ · · 
■ ■ ■ ■ · 
■ ■ ■ ■ ■ 
■ ■ ■ ■ · 
■ ■ ■ · · 
```

#### 判定链

> 匹配方式：按命名规则匹配（层级 B）

**`aglina_s3[sync_params]`** ← 事件 `ON_BUFF_START`

- **AssignBuffBlackboardFromOthers** `_targetType`="BUFF_OWNER"
- **CalculateBlackboardValueViaParams** 
- **CalculateBlackboardValueViaParams** 
- **CalculateBlackboardValueViaParams** 
- **CalculateBlackboardValueViaParams** 
- **CalculateBlackboardValueViaParams** 
- **CalculateBlackboardValueViaParams** 
- **CalculateBlackboardValueViaParams** 
- **CalculateBlackboardValueViaParams** 
- **ModifyAbilityBlackboard** 
- **ModifyAbilityBlackboard** 
- **ModifyAbilityBlackboard** 
- **ModifyAbilityBlackboard** 

---

## 附：数据边界

| 项目 | 状态 |
|---|---|
| 属性 / 数值 / SP / 范围 / 抬手 | ✅ 明文可得 |
| buff 行为树 | ✅ 明文可得 |
| 技能 → 模板绑定 | ⚠️ 游戏只给 `prefabId`，真实绑定在不可解的 `.ab` 里；本文按命名规律 + `blackboard` 键名双向推断 |
| 动画资源本体 | ❌ 在 `.ab` 包内，不可解 |
| 抬手精度 | ✅ 1/30 秒，是动画事件时刻而非视觉起手帧 |
