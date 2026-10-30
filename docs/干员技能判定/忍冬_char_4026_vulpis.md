# 忍冬 — 技能判定说明

> 数据来源：明文 JSON（`character_table` / `skill_table` / `range_table` / `buff_template_data` / `bakemuzzledata`）。不含反汇编或二进制解析内容。

## 一、干员底子

| 项 | 值 |
|---|---|
| ID | `char_4026_vulpis` |
| 职业 | 先锋 / `pioneer` |
| 星级 | 6 星 |
| 生命（精二满级） | 2030 |
| 攻击（精二满级） | 562 |
| 防御（精二满级） | 380 |
| 法抗 | 0% |
| **攻击间隔 baseAttackTime** | **1.05 秒** |
| 攻速 attackSpeed | 100（100% = 无增减） |
| 阻挡 | 2 |
| 部署费用 | 14 |

**攻击间隔换算**（全干员通用）：

```
实际间隔 = baseAttackTime ÷ (attackSpeed / 100)
         = 1.05 ÷ 1.00 = 1.050 秒
```

## 二、抬手（攻击前摇）

来源：`bakemuzzledata/character/char_4026_vulpis_*.json` → `bakedAnimDatas.<组>.bakedEvents.<动画名>.eventTime`，取事件 `OnAttack` 时刻。

| 场景 | 动画名 | 抬手 | 帧数(30fps) |
|---|---|---|---|
| **普通攻击** | `Attack` | **0.5 秒** | 15 帧 |

> 占攻击间隔 47.6%（0.5 秒 / 1.05 秒）。开技能不会让抬手变快。

| 技能动画 | `Skill_1` | 0.566667 秒 | 17 帧 |
| 技能动画 | `Skill_2` | 0.1 秒 | 3 帧 |
| 技能动画 | `Skill_3_Loop` | 0.833333 秒 | 25 帧 |
| 技能动画 | `Skill_Down_3_Loop` | 0.833333 秒 | 25 帧 |


## 三、技能逐层拆解

---

### 小施惩戒　`skchr_vulpis_1`

**技能描述（最高级）：**

> 下次攻击额外造成攻击力290%的法术伤害，并获得1点部署费用
> 可充能3次


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WITH_TIME` | 随时间自动回复 |
| 初始 SP / 消耗 SP | 8 / 4 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 3 | 可存层数 |
| 释放方式 | `AUTO` | 自动释放 |
| 技能形态 | `瞬发技能` | 无持续时间，效果立即结算 |
| duration / durationType | 0 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `cost` | 1 |
| `extra_damage_ratio` | 2.9 |
| `ct` | 3 |

#### 攻击范围

`rangeId = 1-1`，2 格（direction=1）

> 该技能未指定自己的 `rangeId`，上图是干员**自身范围**。技能若扩大范围，会另有 `rangeId`。

```
■ ■ 
```

#### 判定链

> 匹配方式：按命名规则匹配（层级 B）

**`vulpis_s_1`** ← 事件 `ON_BUFF_START`

- **SwitchMode** `_modeIndex`=0 `_targetType`="BUFF_OWNER"
- **ModifyCost** 

**`vulpis_s_1[damage]`** ← 事件 `ON_BUFF_START`

- **AdvancedApplyDamage** `_targetType`="TARGET"

**`vulpis_s_1[end]`** ← 事件 `ON_BUFF_START`

- **SwitchMode** `_modeIndex`=0 `_targetType`="BUFF_OWNER"

---

### 坠刃拷问　`skchr_vulpis_2`

**技能描述（最高级）：**

> 立即获得7点部署费用，对周围最多6名敌人造成相当于攻击力300%的法术伤害，并令击中目标停顿5秒；若敌人已经处于停顿状态，则额外使敌人晕眩5秒
> 可充能2次


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WITH_TIME` | 随时间自动回复 |
| 初始 SP / 消耗 SP | 20 / 20 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 2 | 可存层数 |
| 释放方式 | `MANUAL` | 手动释放 |
| 技能形态 | `瞬发技能` | 无持续时间，效果立即结算 |
| duration / durationType | 0 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `max_target` | 6 |
| `atk_scale` | 3 |
| `cost` | 7 |
| `sluggish` | 5 |
| `stun` | 5 |
| `ct` | 2 |

#### 攻击范围

`rangeId = 3-12`，8 格（direction=1）

```
■ ■ · · 
■ ■ ■ ■ 
■ ■ · · 
```

#### 判定链

> 匹配方式：按命名规则匹配（层级 B）

**`vulpis_s_2`** ← 事件 `ON_BUFF_START`

- **IfElse** 
  - **CheckContainsBuff** `_buffKeys`=["sluggish"] `_targetType`="BUFF_OWNER"
  - **CreateBuff** buffKey=`sluggish` `lifeTimeType`=LIMITED
  - **CreateBuff** buffKey=`stun` `lifeTimeType`=LIMITED
  - **CreateBuff** buffKey=`sluggish` `lifeTimeType`=LIMITED

**`vulpis_s_2[cost]`** ← 事件 `ON_BUFF_START`

- **ModifyCost** 

---

### 隐狐之艺　`skchr_vulpis_3`

**技能描述（最高级）：**

> 技能开启时立即获得9点部署费用，攻击距离+1，攻击力+110%，攻击速度从+180逐渐衰减至+0，同时攻击阻挡的所有敌人，每次攻击晕眩敌人0.2秒
> 若技能期间击倒敌人，则技能结束时进入迷彩状态，直至下一次开启技能


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WITH_TIME` | 随时间自动回复 |
| 初始 SP / 消耗 SP | 10 / 18 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 1 | 可存层数 |
| 释放方式 | `MANUAL` | 手动释放 |
| 技能形态 | `限时技能` | 持续 10 秒 |
| duration / durationType | 10 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `cost` | 9 |
| `atk` | 1.1 |
| `attack_speed` | 180 |
| `attack@stun` | 0.2 |

#### 攻击范围

`rangeId = 2-2`，3 格（direction=1）

```
■ ■ ■ 
```

#### 判定链

> 匹配方式：按命名规则匹配（层级 B）

**`vulpis_s_3`** ← 事件 `ON_BUFF_START`

- **IfElse** 
  - **CheckFaceDirection** `_target`="BUFF_OWNER"
  - **SwitchMode** `_modeIndex`=2 `_targetType`="BUFF_OWNER"
  - **SwitchMode** `_modeIndex`=1 `_targetType`="BUFF_OWNER"
- **RemainingRatioToAttributeModifier** 
- **ModifyCost** 

**`vulpis_s_3`** ← 事件 `ON_BUFF_FINISH`

- **SwitchMode** `_modeIndex`=0 `_targetType`="BUFF_OWNER"

**`vulpis_s_3`** ← 事件 `ON_BEFORE_ATTACK`

- **RemainingRatioToAttributeModifier** 

**`vulpis_s_3[cam]`** ← 事件 `ON_BUFF_TRIGGER`

- **IfElse** 
  - **CheckBlocked** `_targetType`="BUFF_OWNER"
  - **FinishBuffsById** `_targetType`="BUFF_OWNER"
  - **CheckContainsBuff** `_buffKeys`=["vulpis_s_3[cam][interval]"] `_targetType`="BUFF_OWNER"
  - **IfNot** 
  - **CreateBuff** buffKey=`vulpis_s_3[cam][interval]` `overrideType`=UNIQUE `lifeTimeType`=INFINITY

**`vulpis_s_3[finish_checker]`** ← 事件 `ON_BUFF_START`

- **IfElse** 
  - **CheckContainsBuff** `_buffKeys`=["vulpis_s_3[kill_mark]"] `_targetType`="BUFF_OWNER"
  - **CreateBuff** buffKey=`vulpis_s_3[cam]` templateKey=`vulpis_s_3[cam]` `lifeTimeType`=INFINITY
- **FinishBuffsById** `_targetType`="BUFF_OWNER"

**`vulpis_s_3[kill_checker]`** ← 事件 `ON_TARGET_KILLED`

- **CreateBuff** buffKey=`vulpis_s_3[kill_mark]` `lifeTimeType`=INFINITY

**`vulpis_s_3[kill_checker]`** ← 事件 `ON_BUFF_START`

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
