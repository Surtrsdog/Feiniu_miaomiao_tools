# 怒潮凛冬 — 技能判定说明

> 数据来源：明文 JSON（`character_table` / `skill_table` / `range_table` / `buff_template_data` / `bakemuzzledata`）。不含反汇编或二进制解析内容。

## 一、干员底子

| 项 | 值 |
|---|---|
| ID | `char_1051_headb2` |
| 职业 | 近卫 / `hammer` |
| 星级 | 6 星 |
| 生命（精二满级） | 2950 |
| 攻击（精二满级） | 1262 |
| 防御（精二满级） | 408 |
| 法抗 | 0% |
| **攻击间隔 baseAttackTime** | **1.8 秒** |
| 攻速 attackSpeed | 100（100% = 无增减） |
| 阻挡 | 2 |
| 部署费用 | 20 |

**攻击间隔换算**（全干员通用）：

```
实际间隔 = baseAttackTime ÷ (attackSpeed / 100)
         = 1.8 ÷ 1.00 = 1.800 秒
```

## 二、抬手（攻击前摇）

来源：`bakemuzzledata/character/char_1051_headb2_*.json` → `bakedAnimDatas.<组>.bakedEvents.<动画名>.eventTime`，取事件 `OnAttack` 时刻。

| 场景 | 动画名 | 抬手 | 帧数(30fps) |
|---|---|---|---|
| **普通攻击** | `Attack` | **0.9 秒** | 27 帧 |

> 占攻击间隔 50.0%（0.9 秒 / 1.8 秒）。开技能不会让抬手变快。

| 技能动画 | `Skill_1` | 0.9 秒 | 27 帧 |
| 技能动画 | `Skill_2_Loop` | 0.666667 秒 | 20 帧 |
| 技能动画 | `Skill_3` | 1.1 秒 | 33 帧 |


## 三、技能逐层拆解

---

### 誓不低头　`skchr_headb2_1`

**技能描述（最高级）：**

> 攻击力+50%，攻击速度+50


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WITH_TIME` | 随时间自动回复 |
| 初始 SP / 消耗 SP | 20 / 30 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 1 | 可存层数 |
| 释放方式 | `MANUAL` | 手动释放 |
| 技能形态 | `限时技能` | 持续 30 秒 |
| duration / durationType | 30 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `atk` | 0.5 |
| `attack_speed` | 50 |

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

### 绝不罢休　`skchr_headb2_2`

**技能描述（最高级）：**

> 被动效果：每次有高台触发第一天赋的效果时，获得1点技力
> 自动开启：攻击范围扩大，攻击力+90%，防御力+60%
> 第二次及以后使用时能力加成变为最初的两倍，且持续时间无限


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WITH_TIME` | 随时间自动回复 |
| 初始 SP / 消耗 SP | 36 / 50 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 1 | 可存层数 |
| 释放方式 | `AUTO` | 自动释放 |
| 技能形态 | `限时技能` | 持续 16 秒 |
| duration / durationType | 16 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `atk` | 0.9 |
| `def` | 0.6 |
| `headb2_s_2[second].atk` | 1.8 |
| `headb2_s_2[second].def` | 1.2 |
| `sp_per_highland` | 1 |

#### 攻击范围

`rangeId = 2-5`，7 格（direction=1）

```
· ■ ■ 
■ ■ ■ 
· ■ ■ 
```

#### 判定链

> 匹配方式：由 `blackboard` 键名精确指认（层级 A）

**`headb2_s_2[sp]`** ← 事件 `ON_BUFF_LATE_ENABLE`

- **AssignBuffBlackboard** `_targetType`="BUFF_OWNER"

---

### 无可抵挡　`skchr_headb2_3`

**技能描述（最高级）：**

> 攻击力+100%，对前方一格持续进行五次溅射范围更大的锤击，每次造成相当于攻击力240%的物理伤害并使攻击力额外+30%；技能期间触发第一天赋的高台会向四周高台扩散该效果（扩散次数随攻击次数递增），并使伤害效果提升至3.5倍，控制效果变为2秒束缚


#### 触发条件

| 项 | 值 | 说明 |
|---|---|---|
| SP 回复 | `INCREASE_WITH_TIME` | 随时间自动回复 |
| 初始 SP / 消耗 SP | 20 / 27 | 部署即刻拥有 / 每次开启扣除 |
| 充能层数 | 1 | 可存层数 |
| 释放方式 | `MANUAL` | 手动释放 |
| 技能形态 | `瞬发技能` | 无持续时间，效果立即结算 |
| duration / durationType | 0 / `NONE` | 原始字段 |

#### 数值（最高级）

| blackboard 键 | 值 |
|---|---|
| `atk_scale` | 2.4 |
| `atk_step` | 0.3 |
| `splash_atk_scale_bonus` | 3.5 |
| `unmovable` | 2 |
| `atk_base` | 1 |

#### 攻击范围

`rangeId = 1-1`，2 格（direction=1）

> 该技能未指定自己的 `rangeId`，上图是干员**自身范围**。技能若扩大范围，会另有 `rangeId`。

```
■ ■ 
```

#### 判定链

> 匹配方式：按命名规则匹配（层级 B）

**`headb2_s_3`** ← 事件 `ON_ABILITY_SPELL_ON`

- **AddBuffBlackboard** `_targetType`="TARGET"
- **CalculateBlackboardValueViaParams** 
- **CalculateBlackboardValueViaParams** 
- **UpdateBuffAttributeModifier** 

**`headb2_s_3`** ← 事件 `ON_BUFF_START`

- **CalculateBlackboardValueViaParams** 
- **CalculateBlackboardValueViaParams** 
- **UpdateBuffAttributeModifier** 
- **AddAbilityBlackboard** 

**`headb2_s_3`** ← 事件 `ON_OUTPUT_MODIFIER`

- **IfElse** 
  - **CheckIfDamageHasSharedFlags** 
  - **SetSharedFlag** 
  - **IfElse** 
    - **CheckIfDamageHasSharedFlags** 
    - **SetSharedFlag** 

---

## 附：数据边界

| 项目 | 状态 |
|---|---|
| 属性 / 数值 / SP / 范围 / 抬手 | ✅ 明文可得 |
| buff 行为树 | ✅ 明文可得 |
| 技能 → 模板绑定 | ⚠️ 游戏只给 `prefabId`，真实绑定在不可解的 `.ab` 里；本文按命名规律 + `blackboard` 键名双向推断 |
| 动画资源本体 | ❌ 在 `.ab` 包内，不可解 |
| 抬手精度 | ✅ 1/30 秒，是动画事件时刻而非视觉起手帧 |
