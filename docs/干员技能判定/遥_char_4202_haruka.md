# 遥 — 技能判定说明

> 数据来源：明文 JSON（`character_table` / `skill_table` / `range_table` / `buff_template_data` / `bakemuzzledata`）。不含反汇编或二进制解析内容。

## 一、干员底子

| 项 | 值 |
|---|---|
| ID | `char_4202_haruka` |
| 职业 | 辅助 / `blessing` |
| 星级 | 6 星 |
| 生命（精二满级） | 1887 |
| 攻击（精二满级） | 480 |
| 防御（精二满级） | 178 |
| 法抗 | 2500% |
| **攻击间隔 baseAttackTime** | **1.6 秒** |
| 攻速 attackSpeed | 100（100% = 无增减） |
| 阻挡 | 1 |
| 部署费用 | 13 |

**攻击间隔换算**（全干员通用）：

```
实际间隔 = baseAttackTime ÷ (attackSpeed / 100)
         = 1.6 ÷ 1.00 = 1.600 秒
```

## 二、抬手（攻击前摇）

来源：`bakemuzzledata/character/char_4202_haruka_*.json` → `bakedAnimDatas.<组>.bakedEvents.<动画名>.eventTime`，取事件 `OnAttack` 时刻。

| 场景 | 动画名 | 抬手 | 帧数(30fps) |
|---|---|---|---|
| **普通攻击** | `Attack` | **0.5 秒** | 15 帧 |

> 占攻击间隔 31.2%（0.5 秒 / 1.6 秒）。开技能不会让抬手变快。

| 技能动画 | `Skill_2_loop` | 0.533333 秒 | 16 帧 |
| 技能动画 | `Skill_3_Loop_A` | 0.333333 秒 | 10 帧 |
| 技能动画 | `Skill_3_Loop_B` | 0.333333 秒 | 10 帧 |
| 技能动画 | `Skill_Loop` | 0.2 秒 | 6 帧 |


## 三、技能逐层拆解

---

### 夜啼彩羽　`skchr_haruka_1`

**技能描述（最高级）：**

> 攻击速度+60，技能期间浮泡破碎时，立即使周围8格一名没有浮泡的友方单位获得浮泡


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WITH_TIME` | 随时间自动回复 |
| 初始 SP / 消耗 SP | 15 / 25 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 1 | 可存层数 |
| 释放方式 | `MANUAL` | 手动释放 |
| 技能形态 | `限时技能` | 持续 20 秒 |
| duration / durationType | 20 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `attack_speed` | 60 |

#### 攻击范围

`rangeId = y-6`，16 格（direction=1）

> 该技能未指定自己的 `rangeId`，上图是干员**自身范围**。技能若扩大范围，会另有 `rangeId`。

```
· ■ ■ · 
■ ■ ■ ■ 
■ ■ ■ ■ 
■ ■ ■ ■ 
· ■ ■ · 
```

#### 判定链

本技能**没有独立 buff 模板**。它属于「一段式数值强化」：开技能只改 `blackboard` 参数与动画，不挂 buff 节点树。

可核对的替代证据：

- 描述中的每个花括号参数都能在 `blackboard` 中找到对应值（见上表）

---

### 幽隙栖萤　`skchr_haruka_2`

**技能描述（最高级）：**

> 治疗目标数+1，浮光泡影的目标数+1；友方单位受到遥的治疗效果时，对周围3名敌人造成相当于治疗量200%的法术伤害
> 第二次及以后使用时攻击力+40%，且持续时间无限


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WITH_TIME` | 随时间自动回复 |
| 初始 SP / 消耗 SP | 0 / 17 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 1 | 可存层数 |
| 释放方式 | `MANUAL` | 手动释放 |
| 技能形态 | `限时技能` | 持续 26 秒 |
| duration / durationType | 26 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `atk` | 0.4 |
| `haruka_s_2[first].atk` | 0 |
| `attack@max_target_heal_add` | 1 |
| `max_target_shield_add` | 1 |
| `ability_range_radius` | 1.7 |
| `max_target_extra` | 3 |
| `atk_scale_extra` | 2 |

#### 攻击范围

`rangeId = y-6`，16 格（direction=1）

> 该技能未指定自己的 `rangeId`，上图是干员**自身范围**。技能若扩大范围，会另有 `rangeId`。

```
· ■ ■ · 
■ ■ ■ ■ 
■ ■ ■ ■ 
■ ■ ■ ■ 
· ■ ■ · 
```

#### 判定链

> 匹配方式：由 `blackboard` 键名精确指认（层级 A）

**`haruka_s_2`** ← 事件 `ON_BUFF_START`

- **SwitchMode** `_modeIndex`=0 `_targetType`="BUFF_OWNER"

**`haruka_s_2`** ← 事件 `ON_AFTER_OUTPUT_HEAL`

- **AssignModifierValueIntoBlackboard** 
- **FilterByBlackboardValue** `_condType`="GT" `_targetType`="BUFF_OWNER"
- **CreateBuffUseAbilitySelector** buffKey=`haruka_s_2[damage]` templateKey=`haruka_s_2[damage]` `lifeTimeType`=IMMEDIATELY `_targetType`="MODIFIER_TARGET"
- **AlwaysNext** 
- **CreateEffect** `_targetType`="MODIFIER_TARGET"
- **PlayAudio** `_target`="MODIFIER_TARGET"

**`haruka_s_2`** ← 事件 `ON_BUFF_FINISH`

- **SwitchMode** `_modeIndex`=0 `_targetType`="BUFF_OWNER"

**`haruka_s_2[damage]`** ← 事件 `ON_BUFF_START`

- **FixedValueDamage** `_targetType`="BUFF_OWNER"
- **CreateEffect** `_targetType`="BUFF_OWNER"

---

### 夏末游鳞　`skchr_haruka_3`

**技能描述（最高级）：**

> 攻击力+55%，攻击范围扩大，攻击间隔缩短，技能期间浮泡提供的庇护提升至2倍；攻击我方浮泡的敌人将浮空4秒，在此浮空期间每秒受到相当于遥攻击力80%的法术伤害


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WITH_TIME` | 随时间自动回复 |
| 初始 SP / 消耗 SP | 53 / 60 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 1 | 可存层数 |
| 释放方式 | `MANUAL` | 手动释放 |
| 技能形态 | `限时技能` | 持续 40 秒 |
| duration / durationType | 40 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `base_attack_time` | -0.6 |
| `damage_resistance_scale` | 2 |
| `atk` | 0.55 |
| `levitate_duration` | 4 |
| `interval` | 1 |
| `atk_scale` | 0.8 |

#### 攻击范围

`rangeId = y-8`，23 格（direction=1）

```
■ ■ ■ ■ · 
■ ■ ■ ■ ■ 
■ ■ ■ ■ ■ 
■ ■ ■ ■ ■ 
■ ■ ■ ■ · 
```

#### 判定链

> 匹配方式：按命名规则匹配（层级 B）

**`haruka_s_3[talent]`** ← 事件 `ON_BUFF_START`

- **TriggerAbility** `_targetType`="BUFF_OWNER"
- **AlwaysNext** 
- **CreateBuff** buffKey=`haruka_s_3_fx` `lifeTimeType`=INFINITY

---

## 附：数据边界

| 项目 | 状态 |
|---|---|
| 属性 / 数值 / SP / 范围 / 抬手 | ✅ 明文可得 |
| buff 行为树 | ✅ 明文可得 |
| 技能 → 模板绑定 | ⚠️ 游戏只给 `prefabId`，真实绑定在不可解的 `.ab` 里；本文按命名规律 + `blackboard` 键名双向推断 |
| 动画资源本体 | ❌ 在 `.ab` 包内，不可解 |
| 抬手精度 | ✅ 1/30 秒，是动画事件时刻而非视觉起手帧 |
