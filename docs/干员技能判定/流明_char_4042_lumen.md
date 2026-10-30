# 流明 — 技能判定说明

> 数据来源：明文 JSON（`character_table` / `skill_table` / `range_table` / `buff_template_data` / `bakemuzzledata`）。不含反汇编或二进制解析内容。

## 一、干员底子

| 项 | 值 |
|---|---|
| ID | `char_4042_lumen` |
| 职业 | 医疗 / `healer` |
| 星级 | 6 星 |
| 生命（精二满级） | 1825 |
| 攻击（精二满级） | 540 |
| 防御（精二满级） | 111 |
| 法抗 | 1000% |
| **攻击间隔 baseAttackTime** | **2.85 秒** |
| 攻速 attackSpeed | 100（100% = 无增减） |
| 阻挡 | 1 |
| 部署费用 | 23 |

**攻击间隔换算**（全干员通用）：

```
实际间隔 = baseAttackTime ÷ (attackSpeed / 100)
         = 2.85 ÷ 1.00 = 2.850 秒
```

## 二、抬手（攻击前摇）

来源：`bakemuzzledata/character/char_4042_lumen_*.json` → `bakedAnimDatas.<组>.bakedEvents.<动画名>.eventTime`，取事件 `OnAttack` 时刻。

| 场景 | 动画名 | 抬手 | 帧数(30fps) |
|---|---|---|---|
| **普通攻击** | `Attack` | **0.4 秒** | 12 帧 |

> 占攻击间隔 14.0%（0.4 秒 / 2.85 秒）。开技能不会让抬手变快。

| 技能动画 | `Skill_1` | 0.466667 秒 | 14 帧 |
| 技能动画 | `Skill_2` | 0.8 秒 | 24 帧 |
| 技能动画 | `Skill_3_Loop` | 0.366667 秒 | 11 帧 |


## 三、技能逐层拆解

---

### 沐雨　`skchr_lumen_1`

**技能描述（最高级）：**

> 下次攻击使目标和周围的友军每秒受到相当于55%流明攻击力的治疗效果，持续5秒


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WITH_TIME` | 随时间自动回复 |
| 初始 SP / 消耗 SP | 0 / 10 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 1 | 可存层数 |
| 释放方式 | `AUTO` | 自动释放 |
| 技能形态 | `无限持续` | 开启后一直生效，直到手动关闭或条件结束 |
| duration / durationType | -1 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `aura.heal_scale` | 0.55 |
| `aura.projectile_life_time` | 5 |
| `aura.interval` | 1 |

#### 攻击范围

`rangeId = 3-4`，18 格（direction=1）

> 该技能未指定自己的 `rangeId`，上图是干员**自身范围**。技能若扩大范围，会另有 `rangeId`。

```
■ ■ ■ · 
■ ■ ■ ■ 
■ ■ ■ ■ 
■ ■ ■ ■ 
■ ■ ■ · 
```

#### 判定链

> 匹配方式：按命名规则匹配（层级 B）

**`lumen_s_1`** ← 事件 `ON_BUFF_START`

- **TriggerAbility** `_targetType`="BUFF_OWNER"
- **CreateBuff** buffKey=`lumen_s_1[effect]` `lifeTimeType`=LIMITED

**`lumen_s_1[heal]`** ← 事件 `ON_BUFF_TRIGGER`

- **FilterByTargetHpRatio** `_condType`="LT" `_targetType`="BUFF_OWNER"
- **AdvancedApplyHeal** `_targetType`="BUFF_OWNER"
- **CreateEffect** `_targetType`="BUFF_OWNER"

---

### 沛霖　`skchr_lumen_2`

**技能描述（最高级）：**

> 立刻恢复攻击范围内最多3名友方单位相当于攻击力260%的生命；
> 蓄力额外效果：并解除目标所受的异常状态


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WITH_TIME` | 随时间自动回复 |
| 初始 SP / 消耗 SP | 5 / 13 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 2 | 可存层数 |
| 释放方式 | `MANUAL` | 手动释放 |
| 技能形态 | `无限持续` | 开启后一直生效，直到手动关闭或条件结束 |
| duration / durationType | -1 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `heal_scale` | 2.6 |
| `max_target` | 3 |

#### 攻击范围

`rangeId = 3-4`，18 格（direction=1）

> 该技能未指定自己的 `rangeId`，上图是干员**自身范围**。技能若扩大范围，会另有 `rangeId`。

```
■ ■ ■ · 
■ ■ ■ ■ 
■ ■ ■ ■ 
■ ■ ■ ■ 
■ ■ ■ · 
```

#### 判定链

> 匹配方式：按命名规则匹配（层级 B）

**`lumen_s_2`** ← 事件 `ON_BUFF_START`

- **CheckContainsBuff** `_buffKeys`=["lumen_s_2[enhance]"] `_targetType`="BUFF_SOURCE"
- **CreateBuffById** 

**`lumen_s_2[eff_cond]`** ← 事件 `ON_BUFF_TRIGGER`

- **IfElse** 
  - **CompareCharSkillAvailableCnt** `_condType`="LT" `_count`=1 `_targetType`="BUFF_OWNER"
  - **FinishDerivedBuff** 
  - **IfElse** 
    - **CompareCharSkillAvailableCnt** `_condType`="EQUALS" `_count`=1 `_targetType`="BUFF_OWNER"
    - **FinishDerivedBuffById** 
    - **CheckContainsBuff** `_buffKeys`=["lumen_s_2[effect_1]"] `_targetType`="BUFF_OWNER"
    - **IfNot** 
    - **CreateBuff** buffKey=`lumen_s_2[effect_1]` `overrideType`=UNIQUE `lifeTimeType`=INFINITY
    - **CheckContainsBuff** `_buffKeys`=["lumen_s_2[effect_2]"] `_targetType`="BUFF_OWNER"
    - **IfNot** 
    - **CompareCharSkillAvailableCnt** `_condType`="GE" `_count`=2 `_targetType`="BUFF_OWNER"
    - **FinishDerivedBuffById** 
    - **CreateBuff** buffKey=`lumen_s_2[effect_2]` `lifeTimeType`=INFINITY

---

### 灯火不灭　`skchr_lumen_3`

**技能描述（最高级）：**

> 攻击力+55%，攻击速度+30，优先治疗处于异常状态中的单位；只在治疗异常状态中的单位时会消耗子弹，使该次治疗量提升至攻击力的200%并解除目标所受的异常状态
> 攻击装有8发子弹，打完后技能结束（期间可随时停止技能）


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WITH_TIME` | 随时间自动回复 |
| 初始 SP / 消耗 SP | 0 / 50 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 1 | 可存层数 |
| 释放方式 | `MANUAL` | 手动释放 |
| 技能形态 | `弹药制` | 技能持续到弹药打完 |
| duration / durationType | -1 / `AMMO` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `attack_speed` | 30 |
| `heal_scale` | 2 |
| `attack@trigger_time` | 8 |
| `atk` | 0.55 |

#### 攻击范围

`rangeId = 3-4`，18 格（direction=1）

> 该技能未指定自己的 `rangeId`，上图是干员**自身范围**。技能若扩大范围，会另有 `rangeId`。

```
■ ■ ■ · 
■ ■ ■ ■ 
■ ■ ■ ■ 
■ ■ ■ ■ 
■ ■ ■ · 
```

#### 判定链

> 匹配方式：按命名规则匹配（层级 B）

**`lumen_s_3[ammo]`** ← 事件 `ON_OUTPUT_MODIFIER`

- **FilterAbilityName** 
- **ModifierScaleUp** 
- **CreateBuffById** 

---

## 附：数据边界

| 项目 | 状态 |
|---|---|
| 属性 / 数值 / SP / 范围 / 抬手 | ✅ 明文可得 |
| buff 行为树 | ✅ 明文可得 |
| 技能 → 模板绑定 | ⚠️ 游戏只给 `prefabId`，真实绑定在不可解的 `.ab` 里；本文按命名规律 + `blackboard` 键名双向推断 |
| 动画资源本体 | ❌ 在 `.ab` 包内，不可解 |
| 抬手精度 | ✅ 1/30 秒，是动画事件时刻而非视觉起手帧 |
